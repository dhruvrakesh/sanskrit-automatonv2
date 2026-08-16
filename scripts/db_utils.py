#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_utils.py — Single source of truth for SQLite schema.

All other scripts import ensure_schema and migrate_schema from here.
Never define schema in any other file.

Phase Q (2026-07-20): translation provenance + quality loop.
- passages gains mt_prompt_version, translated_at, translation_qa
- new table translation_history: superseded translations are archived here,
  never deleted — every retranslation keeps its predecessor comparable.
"""
from __future__ import annotations
import sqlite3, os, datetime, shutil, pathlib

PRAGMAS = [
    ("foreign_keys", "ON"),
    ("journal_mode", "WAL"),
    ("synchronous",  "NORMAL"),
    ("temp_store",   "MEMORY"),
    ("cache_size",   "-32000"),   # 32 MB page cache
    # busy_timeout (2026-08-02): a second writer WAITS up to 30s for the lock
    # instead of failing instantly with SQLITE_BUSY. WAL already allows 1 writer
    # + N readers; this makes a dashboard job and a CLI job that happen to write
    # at the same moment queue politely rather than erroring. Translations are
    # never overwritten, so a brief serialization is harmless.
    ("busy_timeout", "30000"),
]

# ── Canonical base schema ────────────────────────────────────────────────────
BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  code     TEXT UNIQUE,
  category TEXT,        -- upapurana | jyotish | nirukta | veda | etc.
  src_path TEXT,        -- original corpus path on D: drive
  glossary TEXT,        -- JSON: {proper_noun: {iast, type, epithets}}
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS passages(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id           INTEGER NOT NULL,
  page_no          INTEGER NOT NULL,
  idx              INTEGER NOT NULL,

  -- Source text
  text             TEXT,     -- raw Sanskrit (Devanagari), dandas preserved
  norm             TEXT,     -- whitespace-normalized form
  iast             TEXT,     -- IAST transliteration (indic_transliteration)
  sandhi           TEXT,     -- sandhi-resolved form (JSON list of words)
  morph            TEXT,     -- morphological parse (JSON)

  -- Structural metadata (Phase 1: verse segmenter output)
  verse_ref        TEXT,     -- "1.2.3" | "12" | null
  chapter          TEXT,     -- adhyaya/parva/kanda number/name
  text_type        TEXT,     -- mula | tika | prose | colophon | noise | frontmatter
  chandas          TEXT,     -- anustubh | tristubh | sloka | arya | etc.
  padas            INTEGER,  -- number of padas (2 or 4 for standard slokas)
  quality_score    REAL,     -- 0.0–1.0 (Devanagari density + danda presence)

  -- NER
  ents             TEXT,     -- JSON: [{entity, type, iast}]

  -- Translation
  translation      TEXT,     -- English translation
  translation_score REAL,    -- 0.0–1.0 length-ratio score (legacy)
  engine           TEXT,     -- e.g. gemini:gemini-2.5-pro

  -- Phase Q: translation provenance + quality
  mt_prompt_version TEXT,    -- infer_mt.PROMPT_VERSION at translation time
  translated_at    TEXT,     -- ISO timestamp of translation write
  translation_qa   REAL,     -- 0.0–1.0 heuristic QA (text_filters.score_translation_quality)

  -- Provenance
  source           TEXT,
  created_at       TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),

  UNIQUE(doc_id, page_no, idx),
  FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE
);

-- FTS: trigram tokenizer for Devanagari partial matching
CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts
USING fts5(text, iast, translation, tokenize='trigram case_sensitive 0');

-- Main translation cache (content-addressed)
CREATE TABLE IF NOT EXISTS mt_cache(
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  engine     TEXT NOT NULL,
  lang_in    TEXT NOT NULL,
  lang_out   TEXT NOT NULL,
  text_hash  TEXT NOT NULL,
  text       TEXT NOT NULL,
  output     TEXT NOT NULL,
  context_hash TEXT,          -- hash of the context window used (for cache invalidation)
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(engine, lang_in, lang_out, text_hash)
);

-- Source provenance (original PDFs)
CREATE TABLE IF NOT EXISTS sources(
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id     INTEGER NOT NULL,
  path       TEXT,
  page_lo    INTEGER,
  page_hi    INTEGER,
  sha256     TEXT,
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE
);

-- Phase Q: superseded translations are archived, never deleted.
-- Every retranslation writes its predecessor here first with a reason,
-- giving before/after pairs for measuring each prompt/engine iteration.
CREATE TABLE IF NOT EXISTS translation_history(
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  passage_id         INTEGER NOT NULL,
  translation        TEXT,
  engine             TEXT,
  mt_prompt_version  TEXT,
  translation_score  REAL,
  translation_qa     REAL,
  translated_at      TEXT,
  superseded_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  reason             TEXT,   -- 'qa<0.6' | 'prompt-upgrade' | 'retranslate-overwrite' | ...
  FOREIGN KEY(passage_id) REFERENCES passages(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_translation_history_passage
  ON translation_history(passage_id);

-- Phase HI (2026-08-01): additional-language translations (Hindi first).
-- English stays in passages.translation (load-bearing across dashboard, FTS,
-- exports, context windows). Other languages live here, one row per
-- (passage, lang), anchored by the verified English at generation time.
CREATE TABLE IF NOT EXISTS translations_l10n(
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  passage_id         INTEGER NOT NULL,
  lang               TEXT NOT NULL,          -- 'hi', extensible
  translation        TEXT,
  engine             TEXT,
  mt_prompt_version  TEXT,
  translation_score  REAL,                   -- length-ratio (legacy-style)
  translation_qa     REAL,                   -- lang-aware heuristic QA
  translated_at      TEXT,
  UNIQUE(passage_id, lang),
  FOREIGN KEY(passage_id) REFERENCES passages(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_translations_l10n_passage
  ON translations_l10n(passage_id);
CREATE INDEX IF NOT EXISTS idx_translations_l10n_lang
  ON translations_l10n(lang);
"""

# ── New columns added over time — for existing DBs that predate this schema ──
_MIGRATIONS = [
    # table,            column,              type + default
    # NOTE: ALTER TABLE ADD COLUMN only allows constant defaults (NULL, integer, string literal).
    # Never use DEFAULT (strftime(...)) here — use NULL and set value in application code.
    ("docs",     "category",          "TEXT"),
    ("docs",     "src_path",          "TEXT"),
    ("docs",     "glossary",          "TEXT"),
    ("docs",     "created_at",        "TEXT"),  # was: DEFAULT (strftime...) — not allowed in ALTER TABLE
    ("passages", "iast",              "TEXT"),
    ("passages", "verse_ref",         "TEXT"),
    ("passages", "chapter",           "TEXT"),
    ("passages", "text_type",         "TEXT"),
    ("passages", "chandas",           "TEXT"),
    ("passages", "padas",             "INTEGER"),
    ("passages", "quality_score",     "REAL"),
    ("passages", "translation_score", "REAL"),
    ("passages", "engine",            "TEXT"),
    ("passages", "norm",              "TEXT"),
    ("passages", "sandhi",            "TEXT"),
    ("passages", "morph",             "TEXT"),
    ("passages", "ents",              "TEXT"),
    ("passages", "source",            "TEXT"),
    ("mt_cache", "context_hash",      "TEXT"),
    # Phase Q (2026-07-20)
    ("passages", "mt_prompt_version", "TEXT"),
    ("passages", "translated_at",     "TEXT"),
    ("passages", "translation_qa",    "REAL"),
    # Phase HI (2026-08-01): tag which language a history row superseded.
    ("translation_history", "lang",   "TEXT"),
]


def connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    for k, v in PRAGMAS:
        try:
            con.execute(f"PRAGMA {k}={v}")
        except sqlite3.OperationalError:
            pass
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    """Create all tables if not present, then run safe column migrations."""
    con.executescript(BASE_SCHEMA)
    con.commit()
    migrate_schema(con)


def migrate_schema(con: sqlite3.Connection) -> None:
    """Safely add any columns that exist in the canonical schema but not in the DB.

    This handles DBs created by older versions of this code.
    ALTER TABLE ADD COLUMN is safe — it never drops data.
    """
    table_cols: dict[str, set[str]] = {}

    def _get_cols(table: str) -> set[str]:
        if table not in table_cols:
            try:
                rows = con.execute(f"PRAGMA table_info({table})").fetchall()
                table_cols[table] = {r[1] for r in rows}
            except Exception:
                table_cols[table] = set()
        return table_cols[table]

    changed = False
    for table, col, typedef in _MIGRATIONS:
        if col not in _get_cols(table):
            try:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
                table_cols.pop(table, None)  # invalidate cache
                changed = True
                print(f"[migrate_schema] Added {table}.{col}")
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    pass  # column is already there — silent
                elif "non-constant" in msg or "default" in msg:
                    # SQLite rejected function-based default — try without default
                    bare = typedef.split(" DEFAULT")[0].strip()
                    try:
                        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {bare}")
                        table_cols.pop(table, None)
                        changed = True
                        print(f"[migrate_schema] Added {table}.{col} (no default)")
                    except sqlite3.OperationalError:
                        pass  # truly already exists
                else:
                    print(f"[migrate_schema] WARNING: {e}")
    if changed:
        con.commit()


def ensure_doc(con: sqlite3.Connection, code: str,
               category: str = None, src_path: str = None) -> int:
    row = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
    if row:
        if category or src_path:
            con.execute(
                "UPDATE docs SET category=COALESCE(?,category), src_path=COALESCE(?,src_path) WHERE id=?",
                (category, src_path, row[0])
            )
            con.commit()
        return row[0]
    cur = con.cursor()
    cur.execute("INSERT INTO docs(code, category, src_path) VALUES(?,?,?)",
                (code, category, src_path))
    con.commit()
    return cur.lastrowid


def rebuild_fts(con: sqlite3.Connection) -> None:
    """Rebuild FTS index from scratch. Run after bulk imports or schema changes."""
    try:
        con.execute("DELETE FROM passages_fts")
        con.execute("""
            INSERT INTO passages_fts(rowid, text, iast, translation)
            SELECT id, COALESCE(text,''), COALESCE(iast,''), COALESCE(translation,'')
            FROM passages
        """)
        con.commit()
        print("[rebuild_fts] FTS index rebuilt successfully")
    except Exception as e:
        print(f"[rebuild_fts] ERROR: {e}")


def backup_db(db_path: str) -> str:
    p = pathlib.Path(db_path)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = str(p.with_name(p.stem + f"_backup_{ts}").with_suffix(p.suffix))
    shutil.copy2(db_path, dest)
    return dest
