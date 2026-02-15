#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fts_hotfix.py
- Makes sure data/context.db exists with baseline schema.
- Forces journal_mode=DELETE (Windows-friendly).
- Rebuilds the FTS index from the authoritative 'passages' table when present.
- Safe to run any time (before or after ingestion).

Usage:
  python scripts/fts_hotfix.py
"""
import os, shutil, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB   = Path(os.environ.get("SA_DB_PATH") or (ROOT / "data" / "context.db"))
DB.parent.mkdir(parents=True, exist_ok=True)

BASELINE_SQL = """
PRAGMA journal_mode=DELETE;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS docs(
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY,
  doc_id    INTEGER,
  doc_code  TEXT,
  src_hash  TEXT,
  started_at TEXT,
  status     TEXT,
  budget_usd REAL,
  spent_usd  REAL,
  finished_at TEXT,
  error       TEXT
);

CREATE TABLE IF NOT EXISTS passages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id INTEGER NOT NULL,
  page_no INTEGER NOT NULL,
  idx INTEGER NOT NULL,
  text TEXT,
  norm TEXT,
  sandhi TEXT,
  morph TEXT,
  ents TEXT,
  translation TEXT,
  UNIQUE(doc_id,page_no,idx)
);

CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts
USING fts5(text, translation, tokenize='unicode61');
"""

def quick_check(con: sqlite3.Connection) -> str:
    try:
        return con.execute("PRAGMA quick_check").fetchone()[0]
    except sqlite3.DatabaseError as e:
        return f"error: {e}"

def rebuild_fts(con: sqlite3.Connection):
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS passages_fts;")
    cur.execute("CREATE VIRTUAL TABLE passages_fts USING fts5(text, translation, tokenize='unicode61');")
    # Repopulate if we have any passages
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='passages'")
    if cur.fetchone():
        cur.execute("SELECT id, COALESCE(text,''), COALESCE(translation,'') FROM passages")
        rows = cur.fetchall()
        for rid, t, tr in rows:
            cur.execute("INSERT INTO passages_fts(rowid, text, translation) VALUES (?,?,?)", (rid, t, tr))
    con.commit()

def main():
    if DB.exists():
        bak = DB.with_suffix(".bak")
        shutil.copyfile(DB, bak)
        print(f"Backup created → {bak}")
    con = sqlite3.connect(str(DB))
    try:
        con.executescript(BASELINE_SQL)
        qc = quick_check(con)
        if qc != "ok":
            print("quick_check:", qc, "→ rebuilding FTS …")
        rebuild_fts(con)
        print("FTS ready.")
        print("quick_check:", quick_check(con))
    finally:
        con.close()

if __name__ == "__main__":
    main()
