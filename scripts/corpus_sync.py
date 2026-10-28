#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
corpus_sync.py  (2026-10-08)  CORPUS_MIRROR_C4_2026_10_08

Keeps a PRIVATE PostgreSQL copy of the local brain (data/context.db) current, idempotently.
Design and commands: docs/CORPUS_MIRROR_2026-10-08.md. Schema: docs/cloud/C4_corpus_mirror_2026-10-08.sql.

What travels: every live document's passages (Sanskrit, IAST, English and their scores), the
other translations (translations_l10n: Hindi), entities and mentions, stories (all statuses),
pipeline stages, and the passage vectors cut from 3,072 to their first 1,536 dims and
renormalised. What stays at home: raw OCR (passages.norm), OCR variants, the SQLite search
index, mt_cache, usage and budget tables, retired documents.
SCHOLAR_MIRROR_2026_10_18: the scholarly English (scholar_translations) travels too, as two translation rows a verse:
en-x-scholar (its English; translation_score its fidelity, translation_qa its fluency) and en-x-scholar-meta (JSON:
status, review, notes, doubts, a sentence's range). The site reads them with public.corpus_reader_scholar (C18).

How it is idempotent:
  - every row gets row_hash = md5 of its mirrored columns;
  - the server's corpus_manifest() gives, per table and document, a count and a digest of
    (key, row_hash); the same digest is made here; equal digests mean nothing to do;
  - for a document that differs, corpus_keys() lists the server's (key, row_hash) and only rows
    whose hash differs are sent; corpus_ingest() ignores a row whose hash is unchanged, so a
    repeated or interrupted run is harmless and the next run finishes the job;
  - a row gone here is RETIRED there (retired_at set), never deleted; it comes back if it returns.
No ledger file is kept here: the server is compared afresh every run, so nothing can drift.

Read-only on context.db (mode=ro; immutable=1 with --immutable for a backup copy).

Sinks:
  --sink edge   the corpus-ingest edge function in Lovable Cloud (HMAC-signed requests; the
                service role never leaves Supabase). Needs CORPUS_SYNC_SECRET in .env; the URL
                and publishable key are read from the Srangam repo's .env.
  --sink pg     a PostgreSQL you own (--dsn or CORPUS_SYNC_DSN), with C4 applied; same functions.
  --sink none   no network: what a first full push would send.
  --sink auto   (default) edge when CORPUS_SYNC_SECRET is set, else none.

  python scripts\\corpus_sync.py                          # plan only: what would be sent
  python scripts\\corpus_sync.py --apply                  # send it
  python scripts\\corpus_sync.py --apply --doc markandeya_purana
  python scripts\\corpus_sync.py --apply --max-mb 50 --if-configured   # the maintenance step
  python scripts\\corpus_sync.py --sink none --db "D:\\backups\\context_20261008.db" --immutable
  python scripts\\corpus_sync.py --status                 # mirror rows against rows here, per table
A run prints what it is doing as it goes ([m:ss] lines, flushed): a first push takes minutes.
Test: python -m unittest tests.test_corpus_sync_2026_10_08 -v
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import hmac
import json
import math
import ntpath
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

MARK = "CORPUS_MIRROR_C4_2026_10_08"
SCHEMA_VERSION = "c4.1"          # part of every row_hash: changing the mirrored columns re-sends all
DIGEST_SCHEME = "sum64.1"        # CORPUS_MIRROR_C4B_2026_10_08: must match corpus_manifest()'s "_scheme"
CLIENT_VERSION = "4.3"          # SYNC_SPLIT_2026_10_09: a timed-out batch is sent again in halves
CLIENT = "corpus_sync.py %s (rows %s, digests %s)" % (CLIENT_VERSION, SCHEMA_VERSION, DIGEST_SCHEME)
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "context.db"
LOG_PATH = ROOT / "data" / "corpus_sync_log.jsonl"
DEFAULT_SITE_ENV = r"D:\srangam-42267\.env"
TABLES = ["docs", "entities", "passages", "translations", "mentions", "stories", "stages", "vectors"]
GLOBAL_TABLES = ["docs", "entities"]
PER_DOC_TABLES = ["passages", "translations", "mentions", "stories", "stages", "vectors"]
VEC_DIMS = 1536
MAX_ROWS_PER_CALL = 1000         # server limit is 2000
MAX_VEC_ROWS_PER_CALL = 25       # about 12 KB of text per vector; SYNC_SPLIT_2026_10_09: 150 (and 50)
                                 # timed out on 2026-10-09, each row an insert into the HNSW index
MAX_KEYS_PER_RETIRE = 5000
MAX_VEC_KEYS_PER_RETIRE = 25     # MIRROR_CAP_2026_10_12: a vector retired is a new entry in the HNSW index, as an
                                 # insert is: the Bodhicaryavatara's 824 in one call timed out on 2026-10-12
DEFAULT_BATCH_BYTES = 1_500_000  # JSON bytes per call, before gzip

sys.path.insert(0, str(Path(__file__).resolve().parent))


class SinkError(RuntimeError):
    pass


class Budget(Exception):
    """Raised inside a run when --max-mb is reached; the next run carries on."""


# --------------------------------------------------------------------------- local side

def open_ro(db: str, immutable: bool = False) -> sqlite3.Connection:
    p = Path(db).resolve()
    if not p.exists():
        raise SystemExit("database not found: %s" % p)
    uri = p.as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro")
    con = sqlite3.connect(uri, uri=True, isolation_level=None)
    con.execute("PRAGMA query_only=1")
    try:
        con.execute("PRAGMA busy_timeout=30000")
    except sqlite3.OperationalError:
        pass
    return con


def _cols(con, table: str) -> set:
    return {r[1] for r in con.execute("PRAGMA table_info(%s)" % table)}


def _has_table(con, name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _clean(v):
    """JSON- and PostgreSQL-safe value: no NUL in text, no NaN/Infinity."""
    if isinstance(v, str):
        return v.replace("\x00", "") if "\x00" in v else v
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, bytes):
        return None
    return v


def row_hash(table: str, values: list) -> str:
    s = json.dumps([SCHEMA_VERSION, table] + values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def digest(keyed: dict) -> str:
    """Same as the server (C4b, corpus._digest): 'count:sum1:sum2', where every row adds the two
    64-bit halves of md5(key + ' ' + row_hash) and the sums are taken modulo 2^64. Order-free, so
    the server keeps it current row by row and never re-reads a table (the C4 digest sorted every
    key on every call and timed out on 2026-10-08 once the vectors were in)."""
    m64 = 1 << 64
    s1 = s2 = 0
    for k, h in keyed.items():
        d = hashlib.md5(("%s %s" % (k, h)).encode("utf-8")).hexdigest()
        s1 += int(d[:16], 16)
        s2 += int(d[16:], 16)
    return "%d:%d:%d" % (len(keyed), s1 % m64, s2 % m64)


def load_titles() -> dict:
    try:
        import collections_cfg as _cc
        return _cc.load_titles() or {}
    except Exception:
        return {}


def _in_repair_docs() -> set:
    """REPAIR_HEAL_2026_10_11: the texts whose latest record in data/source_verdicts.jsonl (repair_text.py's
    register) is "in_repair": their passages were replaced and are being translated again, so the site
    keeps its last version of them. SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "in_repair"}


def _witness_docs() -> set:
    """ETEXT_WITNESS_2026_10_11: e-text witnesses (scripts/etext_witness.py) stay local until they are adopted:
    the latest record of their code in data/source_verdicts.jsonl is "witness" (repair_text.py --release, once
    translated, makes it "released"). SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "witness"}


def _withdrawn_docs() -> set:
    """PATH_2026_10_12: the texts withdrawn from the site (repair_text.py --withdraw): the latest record of their code in
    data/source_verdicts.jsonl is "withdrawn". They are not live here, so a full run retires their rows on the site, as
    for a retired text (and the guard on many texts gone at once holds); --restore makes them live again, and the
    next run sends them back. SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "withdrawn"}


def live_docs(con, include_retired: bool = False):
    """[(id, code, category, src_path, glossary, created_at)] of documents to mirror."""
    cols = _cols(con, "docs")
    sel = ["id", "code"] + [c if c in cols else "NULL" for c in ("category", "src_path", "glossary", "created_at")]
    rows = con.execute("SELECT %s FROM docs ORDER BY id" % ", ".join(sel)).fetchall()
    retired = set()
    if _has_table(con, "doc_stage"):
        retired = {r[0] for r in con.execute(
            "SELECT doc_code FROM doc_stage WHERE stage='retired' AND status='done'")}
    out = []
    witness = _witness_docs()   # ETEXT_WITNESS_2026_10_11: local until adopted
    withdrawn = _withdrawn_docs()   # PATH_2026_10_12: off the site until restored
    for r in rows:
        code = r[1]
        if not code:
            continue
        if not include_retired and (code.endswith("-RETIRED") or code in retired):
            continue
        if code in witness or code in withdrawn:
            continue
        out.append(r)
    return out


INT_COLS = {"page_no", "idx", "padas", "image_id", "from_page", "from_idx", "to_page", "to_idx", "attempts",
            "story_id", "source_dim"}
FLOAT_COLS = {"quality_score", "translation_score", "translation_qa"}


def _coerce(name: str, v):
    """A value for an INTEGER / DOUBLE PRECISION column of the mirror, or None if it is not one."""
    if isinstance(v, bool):
        return int(v)
    if name in INT_COLS:
        if isinstance(v, int):
            return v if -2 ** 31 <= v < 2 ** 31 else None
        if isinstance(v, float) and math.isfinite(v) and v.is_integer():
            return _coerce(name, int(v))
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return _coerce(name, int(v.strip()))
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    if isinstance(v, str):
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    return None


class Group:
    """One table's rows for one group (a document code, or '*'): key -> (hash, row)."""

    def __init__(self, table: str, group: str):
        self.table, self.group = table, group
        self.rows = {}           # key -> row dict (for vectors: dict with _pid, filled later)
        self.hashes = {}         # key -> row_hash
        self.skipped = 0
        self.coerced = 0

    def add(self, key: str, values: list, row: dict):
        # `row` is dict(zip(names, values)); typed columns are coerced first so that a stray
        # value (SQLite does not enforce types) cannot make the server refuse the whole batch.
        for k, v in row.items():
            if v is not None and (k in INT_COLS or k in FLOAT_COLS):
                c = _coerce(k, v)
                if c is not v:
                    row[k] = c
                    self.coerced += 1
        h = row_hash(self.table, list(row.values()))
        row["row_hash"] = h
        self.rows[key] = row
        self.hashes[key] = h

    def add_hashed(self, key: str, h: str, row: dict):
        row["row_hash"] = h
        self.rows[key] = row
        self.hashes[key] = h

    def digest(self) -> str:
        return digest(self.hashes)


def build_docs(con, docs, titles) -> Group:
    g = Group("docs", "*")
    for (did, code, category, src_path, glossary, created_at) in docs:
        src_name = ntpath.basename(src_path) if src_path else None
        vals = [_clean(x) for x in (code, did, titles.get(code) or None, category, src_name, glossary, created_at)]
        row = dict(zip(("doc_code", "local_id", "title", "category", "src_name", "glossary", "created_at_local"), vals))
        g.add(code, vals, row)
    return g


def build_entities(con) -> Group:
    g = Group("entities", "*")
    if not _has_table(con, "entities"):
        return g
    variants = {}
    if _has_table(con, "entity_variants"):
        for eid, v in con.execute("SELECT entity_id, variant FROM entity_variants WHERE variant IS NOT NULL"):
            variants.setdefault(eid, set()).add(_clean(v))
    cols = _cols(con, "entities")
    sel = ["id", "canonical"] + [c if c in cols else "NULL" for c in ("kind", "notes", "created_at")]
    for eid, canonical, kind, notes, created_at in con.execute("SELECT %s FROM entities" % ", ".join(sel)):
        canonical = _clean(canonical)
        if not canonical or not canonical.strip():
            g.skipped += 1
            continue
        var = sorted(variants.get(eid, ()))
        vals = [canonical, eid, _clean(kind), _clean(notes), var, _clean(created_at)]
        row = dict(zip(("canonical", "local_id", "kind", "notes", "variants", "created_at_local"), vals))
        g.add(canonical, vals, row)
    return g


PASSAGE_COLS = ("text", "iast", "translation", "verse_ref", "chapter", "text_type", "chandas", "padas",
                "quality_score", "translation_score", "translation_qa", "engine", "mt_prompt_version",
                "translated_at", "ocr_engine", "sandhi", "morph", "source")
L10N_COLS = ("translation", "engine", "mt_prompt_version", "translation_score", "translation_qa", "translated_at")

# --- RIGHTS_FRONTMATTER_2026_10_28: an edition in copyright keeps its own matter off the site ----------------------
# configs/edition_rights.json names the texts whose scan is a modern edition with a copyright notice of its own (the
# publisher's or the editor's, as its title page prints it). Of such a text, a passage typed 'frontmatter' (its
# preface, introduction and notes, its editor's translation: the edition's own words, not the Sanskrit) goes to the
# mirror with its place and its type only: its words, IAST, English, Hindi, names and vector stay on the desk. The
# Sanskrit goes as before (whether an edition's Sanskrit may be shown is decided apart, as for the BORI text).
# A text not listed, or listed with "withhold_frontmatter": false, is sent as before.
# RIGHTS_NOISE_2026_10_28: a passage of such a text typed 'noise' goes the same way: there it is the edition's
# apparatus of variant readings (the Mallapurana's, tagged on 3 Oct by classify_apparatus.py; the Hayasirsa's, read
# clearly since its vision repair) or a page's debris, never its Sanskrit.
WITHHELD_TYPES = ("frontmatter", "noise")
RIGHTS_PATH = ROOT / "configs" / "edition_rights.json"
WITHHELD_TEXT = "[The edition's own matter, not shown on the site: %s.]"
_RIGHTS = {}


def edition_rights(path=None) -> dict:
    """RIGHTS_FRONTMATTER_2026_10_28: {doc_code: entry} of configs/edition_rights.json (SA_EDITION_RIGHTS overrides
    the path); {} when it is missing or unreadable."""
    p = Path(path or os.environ.get("SA_EDITION_RIGHTS") or RIGHTS_PATH)
    key = str(p)
    if key not in _RIGHTS:
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            texts = j.get("texts") if isinstance(j, dict) else None
            _RIGHTS[key] = {k: v for k, v in (texts or {}).items() if isinstance(v, dict)}
        except (OSError, ValueError):
            _RIGHTS[key] = {}
    return _RIGHTS[key]


def withheld_notice(code) -> str:
    """RIGHTS_FRONTMATTER_2026_10_28: the notice of a text whose own matter is withheld, else ''."""
    r = edition_rights().get(code) or {}
    if not r.get("withhold_frontmatter"):
        return ""
    return str(r.get("notice") or "its edition is in copyright").strip()


def _withheld(vals: list, notice: str) -> list:
    """A passage row (doc_code, page_no, idx, local_id, PASSAGE_COLS...) with the edition's words taken out."""
    out = list(vals)
    for c, v in (("text", WITHHELD_TEXT % notice), ("iast", None), ("translation", None), ("sandhi", None),
                 ("morph", None), ("padas", None), ("chandas", None), ("translation_score", None),
                 ("translation_qa", None), ("engine", None), ("mt_prompt_version", None), ("translated_at", None)):
        out[4 + PASSAGE_COLS.index(c)] = v
    return out
STORY_COLS = ("image_id", "status", "title", "title_hi", "why", "from_page", "from_idx", "to_page", "to_idx",
              "story_en", "story_hi", "quote_sa", "quote_ref", "notes", "cites", "verify", "model", "provenance",
              "created_at", "updated_at", "approved_at")
STORY_OUT = STORY_COLS[:-3] + ("created_at_local", "updated_at_local", "approved_at_local")
STAGE_COLS = ("status", "reason", "attempts", "measured", "updated_at")
STAGE_OUT = ("status", "reason", "attempts", "measured", "updated_at_local")


def _sel(cols_present: set, wanted, prefix: str) -> str:
    return ", ".join(("%s.%s" % (prefix, c)) if c in cols_present else "NULL" for c in wanted)


# --- SCHOLAR_MIRROR_2026_10_18: the scholarly English, as rows of the translations table ----------
SCHOLAR_LANG = "en-x-scholar"            # a verse's scholarly English (scholar_translations, scholar_translate.py)
SCHOLAR_META_LANG = "en-x-scholar-meta"  # its status, review, notes, doubts and range, as JSON in `translation`
SCHOLAR_META_VERSION = "scholar-meta-1"  # in mt_prompt_version of a meta row
_SCHOLAR_COLS = ("id", "passage_id", "verse_ref", "src_hash", "translation", "notes", "doubts", "fidelity", "fluency",
                 "status", "engine", "judge_engine", "prompt_version", "created_at", "review_verdict", "group_ref",
                 "group_translation")
_L10N_OUT = ("doc_code", "page_no", "idx", "lang") + L10N_COLS


def _scholar_range(u, pinfo) -> str:
    """SCHOLAR_MIRROR_2026_10_18: a sentence's range from its verses' own references (81.18-19), as the edition gives it
    (export_html.py, EDITION_REFS_2026_10_18); scholar_translate's _range when none has one."""
    import scholar_translate as ST
    refs = [str((pinfo.get(r.get("passage_id")) or (None, None))[1] or "").strip() for r in u]
    refs = [x for x in refs if x]
    if not refs:
        return ST._range(u)
    a_, b_ = refs[0], refs[-1]
    return a_ if a_ == b_ else "%s\u2013%s" % (a_, b_.split(".")[-1])


def scholar_rows(con, code, passages, pinfo) -> list:
    """SCHOLAR_MIRROR_2026_10_18: [(key, values, row)] of one text's scholarly English, for its translations group.
    A verse with a current scholarly English gets an en-x-scholar row (its English; translation_score its fidelity and
    translation_qa its fluency, as the judge gave them) and an en-x-scholar-meta row (JSON: status, flag, a person's
    acceptance, the judge; notes and doubts on a sentence's first verse; a sentence over several verses has its range
    on the first verse and "with" on the others, which have no English row of their own). As the edition takes them
    (export_html.py --scholar): a verse's latest version, made from its Sanskrit as it reads now, not rejected by a
    person. passages: id -> (page, idx); pinfo: id -> (Sanskrit, verse_ref)."""
    if not passages or not _has_table(con, "scholar_translations"):
        return []
    import scholar_translate as ST
    have = _cols(con, "scholar_translations")
    sel = ", ".join(c if c in have else "NULL" for c in _SCHOLAR_COLS)
    order = "page_no, idx, id" if {"page_no", "idx"} <= have else "id"
    rows = [dict(zip(_SCHOLAR_COLS, r)) for r in con.execute(
        "SELECT %s FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM scholar_translations "
        "WHERE doc_code = ? GROUP BY passage_id) ORDER BY %s" % (sel, order), (code, code))]
    live = []
    for r in rows:
        t = (pinfo.get(r["passage_id"]) or (None, None))[0]
        if r["passage_id"] in passages and t is not None and ST.src_hash(t) == r["src_hash"]:
            live.append(r)
    out = []
    for u in ST._units(live):
        r0 = u[0]
        if r0.get("review_verdict") == "reject":
            continue
        notes = []
        for n in ST._loads(r0.get("notes"), []):
            if isinstance(n, dict) and str(n.get("note") or "").strip():
                notes.append({k: str(n.get(k) or "").strip() for k in ("anchor", "note", "kind")
                              if str(n.get(k) or "").strip()})
        doubt = str(r0.get("doubts") or "").strip()
        status = str(r0.get("status") or "")
        flag = status in ("flagged", "source_doubt") and r0.get("review_verdict") != "accept"
        inline = ST._inline(u)
        rng = _scholar_range(u, pinfo) if len(u) > 1 else ""
        for k, r in enumerate(u):
            page, idx = passages[r["passage_id"]]
            meta = {"status": status, "flag": flag, "accepted": r.get("review_verdict") == "accept"}
            if r.get("judge_engine"):
                meta["judge"] = str(r["judge_engine"])
            if inline or k == 0:
                text = str((r.get("translation") if inline else (r0.get("group_translation") or r0.get("translation")))
                           or "")
                if k == 0:
                    if notes:
                        meta["notes"] = notes
                    if doubt:
                        meta["doubts"] = doubt
                    if rng and not inline:
                        meta["range"] = rng
            else:
                text = ""
                meta["with"] = rng
            if not text.strip() and not meta.get("with"):
                continue
            at = _clean(r.get("created_at"))
            if text.strip():
                vals = [code, page, idx, SCHOLAR_LANG, _clean(text), _clean(r.get("engine")),
                        _clean(r.get("prompt_version")), _clean(r.get("fidelity")), _clean(r.get("fluency")), at]
                out.append(("%d|%d|%s" % (page, idx, SCHOLAR_LANG), vals, dict(zip(_L10N_OUT, vals))))
            mj = json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            vals = [code, page, idx, SCHOLAR_META_LANG, _clean(mj), None, SCHOLAR_META_VERSION, None, None, at]
            out.append(("%d|%d|%s" % (page, idx, SCHOLAR_META_LANG), vals, dict(zip(_L10N_OUT, vals))))
    return out


def scholar_count(con, docs) -> int:
    """SCHOLAR_MIRROR_2026_10_18: the scholarly English's translation rows of these texts (for --status)."""
    if not _has_table(con, "scholar_translations"):
        return 0
    have = {r[0] for r in con.execute("SELECT DISTINCT doc_code FROM scholar_translations")}
    pcols = _cols(con, "passages")
    n = 0
    for d in docs:
        if d[1] not in have:
            continue
        pos_, info_ = {}, {}
        for pid_, page_, idx_, text_, vref_ in con.execute(
                "SELECT p.id, p.page_no, p.idx, %s FROM passages p WHERE p.doc_id=?"
                % _sel(pcols, ("text", "verse_ref"), "p"), (d[0],)):
            pos_[pid_] = (page_, idx_)
            info_[pid_] = (text_, vref_)
        n += len({k for k, _v, _r in scholar_rows(con, d[1], pos_, info_)})
    return n


def build_doc_groups(con, doc, tables, ent_ok: set) -> dict:
    """All per-document groups of one document, read inside one read transaction so that the
    child rows match the passages they point to."""
    did, code = doc[0], doc[1]
    out = {}
    con.execute("BEGIN")
    try:
        pcols = _cols(con, "passages")
        passages = {}
        pinfo = {}   # SCHOLAR_MIRROR_2026_10_18: id -> (Sanskrit, verse_ref), for the scholarly English
        rows = con.execute(
            "SELECT p.id, p.page_no, p.idx, %s FROM passages p WHERE p.doc_id=? ORDER BY p.page_no, p.idx"
            % _sel(pcols, PASSAGE_COLS, "p"), (did,)).fetchall()
        g = Group("passages", code)
        notice = withheld_notice(code)   # RIGHTS_FRONTMATTER_2026_10_28
        held = set()
        for r in rows:
            pid, page, idx = r[0], r[1], r[2]
            key = "%d|%d" % (page, idx)
            passages[pid] = (page, idx)
            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])
            vals = [code, page, idx, pid] + [_clean(x) for x in r[3:]]
            if notice and r[3 + PASSAGE_COLS.index("text_type")] in WITHHELD_TYPES:   # RIGHTS_NOISE_2026_10_28
                held.add(pid)
                vals = _withheld(vals, notice)
            row = dict(zip(("doc_code", "page_no", "idx", "local_id") + PASSAGE_COLS, vals))
            g.add(key, vals, row)
        out["passages"] = g

        if "translations" in tables:
            g = Group("translations", code)
            if _has_table(con, "translations_l10n"):
                lcols = _cols(con, "translations_l10n")
                for r in con.execute(
                        "SELECT l.passage_id, l.lang, %s FROM translations_l10n l JOIN passages p ON p.id = l.passage_id "
                        "WHERE p.doc_id=?" % _sel(lcols, L10N_COLS, "l"), (did,)):
                    pos = passages.get(r[0])
                    if pos is None or not r[1] or r[0] in held:   # RIGHTS_FRONTMATTER_2026_10_28
                        g.skipped += 1
                        continue
                    key = "%d|%d|%s" % (pos[0], pos[1], r[1])
                    vals = [code, pos[0], pos[1], r[1]] + [_clean(x) for x in r[2:]]
                    row = dict(zip(("doc_code", "page_no", "idx", "lang") + L10N_COLS, vals))
                    g.add(key, vals, row)
            held_at = {passages[x] for x in held}   # RIGHTS_FRONTMATTER_2026_10_28
            for key, vals, row in scholar_rows(con, code, passages, pinfo):   # SCHOLAR_MIRROR_2026_10_18
                if key in g.rows or (vals[1], vals[2]) in held_at:
                    g.skipped += 1
                    continue
                g.add(key, vals, row)
            out["translations"] = g

        if "mentions" in tables:
            g = Group("mentions", code)
            if _has_table(con, "entity_mentions") and _has_table(con, "entities"):
                for pid, canonical, surface in con.execute(
                        "SELECT m.passage_id, e.canonical, m.surface FROM entity_mentions m "
                        "JOIN passages p ON p.id = m.passage_id JOIN entities e ON e.id = m.entity_id "
                        "WHERE p.doc_id=?", (did,)):
                    pos = passages.get(pid)
                    canonical = _clean(canonical)
                    if pos is None or canonical not in ent_ok or pid in held:   # RIGHTS_FRONTMATTER_2026_10_28
                        g.skipped += 1
                        continue
                    key = "%d|%d|%s" % (pos[0], pos[1], canonical)
                    if key in g.rows:
                        g.skipped += 1
                        continue
                    vals = [code, pos[0], pos[1], canonical, _clean(surface)]
                    row = dict(zip(("doc_code", "page_no", "idx", "canonical", "surface"), vals))
                    g.add(key, vals, row)
            out["mentions"] = g

        if "stories" in tables:
            g = Group("stories", code)
            if _has_table(con, "doc_stories"):
                scols = _cols(con, "doc_stories")
                for r in con.execute("SELECT s.id, %s FROM doc_stories s WHERE s.doc_id=? ORDER BY s.id"
                                     % _sel(scols, STORY_COLS, "s"), (did,)):
                    vals = [code, r[0]] + [_clean(x) for x in r[1:]]
                    row = dict(zip(("doc_code", "story_id") + STORY_OUT, vals))
                    g.add(str(r[0]), vals, row)
            out["stories"] = g

        if "stages" in tables:
            g = Group("stages", code)
            if _has_table(con, "doc_stage"):
                tcols = _cols(con, "doc_stage")
                for r in con.execute("SELECT t.stage, %s FROM doc_stage t WHERE t.doc_code=?"
                                     % _sel(tcols, STAGE_COLS, "t"), (code,)):
                    if not r[0]:
                        continue
                    vals = [code, r[0]] + [_clean(x) for x in r[1:]]
                    row = dict(zip(("doc_code", "stage") + STAGE_OUT, vals))
                    g.add(r[0], vals, row)
            out["stages"] = g

        if "vectors" in tables:
            g = Group("vectors", code)
            if _has_table(con, "passage_embeddings"):
                for pid, model, dim, blob in con.execute(
                        "SELECT e.passage_id, e.model, e.dim, e.vec FROM passage_embeddings e "
                        "JOIN passages p ON p.id = e.passage_id WHERE p.doc_id=?", (did,)):
                    pos = passages.get(pid)
                    if (pos is None or blob is None or not dim or int(dim) < VEC_DIMS or len(blob) != 4 * int(dim)
                            or pid in held):   # RIGHTS_FRONTMATTER_2026_10_28
                        g.skipped += 1
                        continue
                    h = hashlib.md5(("%s|vectors|%s|%d|%d|" % (SCHEMA_VERSION, model, int(dim), VEC_DIMS)).encode("utf-8")
                                    + blob).hexdigest()
                    key = "%d|%d" % pos
                    g.add_hashed(key, h, {"doc_code": code, "page_no": pos[0], "idx": pos[1], "model": model,
                                          "source_dim": int(dim), "_pid": pid})
            out["vectors"] = g
    finally:
        con.execute("COMMIT")
    return out


def vector_literal(blob: bytes, dims: int = VEC_DIMS) -> str:
    """First `dims` float32 values, L2-renormalised, in pgvector text form (5 decimals, as C2)."""
    try:
        import numpy as np
        a = np.frombuffer(blob, dtype="<f4")[:dims].astype("float64")
        n = float(np.sqrt((a * a).sum()))
        vals = (a / n).tolist() if n > 0 else None
    except ImportError:
        from array import array
        arr = array("f")
        arr.frombytes(blob[: 4 * dims])
        if sys.byteorder != "little":
            arr.byteswap()
        n = math.sqrt(sum(x * x for x in arr))
        vals = [x / n for x in arr] if n > 0 else None
    if not vals or len(vals) != dims:
        raise ValueError("vector is empty or shorter than %d" % dims)
    return "[" + ",".join("0" if abs(x) < 5e-6 else "%.5f" % x for x in vals) + "]"


def fill_vectors(con, rows: list) -> list:
    """Attach the embedding text to vector rows chosen for sending (read now, by local id)."""
    out = []
    for i in range(0, len(rows), 200):
        chunk = rows[i:i + 200]
        pids = [r["_pid"] for r in chunk]
        q = "SELECT passage_id, vec FROM passage_embeddings WHERE passage_id IN (%s)" % ",".join("?" * len(pids))
        blobs = dict(con.execute(q, pids).fetchall())
        for r in chunk:
            blob = blobs.get(r["_pid"])
            if blob is None:
                continue  # gone since the scan; the next run sees it
            rr = {k: v for k, v in r.items() if k != "_pid"}
            rr["embedding"] = vector_literal(blob)
            out.append(rr)
    return out


# --------------------------------------------------------------------------- sinks

class NoneSink:
    """No network. Behaves as an empty mirror, so the plan is a full first push."""
    name = "none"

    def hello(self):
        return {"ok": True, "fn": "none"}

    def manifest(self, tables):
        out = {t: {} for t in tables}
        out["_scheme"] = DIGEST_SCHEME
        return out

    def keys(self, table, group):
        return {}

    def ingest(self, table, rows, run_id):
        return {"received": len(rows), "changed": len(rows)}

    def retire(self, table, group, keys, run_id):
        return {"retired": len(keys)}

    def run(self, run_id, info, finish):
        return {"ok": True}


class PgSink:
    name = "pg"

    def __init__(self, dsn: str):
        try:
            import psycopg
            self.con = psycopg.connect(dsn, autocommit=True)
        except ImportError:
            try:
                import psycopg2
            except ImportError:
                raise SystemExit("--sink pg needs psycopg (pip install psycopg[binary]) or psycopg2")
            self.con = psycopg2.connect(dsn)
            self.con.autocommit = True

    def _one(self, sql: str, args: tuple):
        try:
            cur = self.con.cursor()
            cur.execute(sql, args)
            v = cur.fetchone()[0]
        except Exception as e:  # driver errors carry the server message
            raise SinkError(str(e).strip().splitlines()[0][:400])
        return json.loads(v) if isinstance(v, str) else v

    def hello(self):
        m = self.manifest(["docs"])
        return {"ok": True, "fn": "pg", "docs_in_mirror": int((m.get("docs", {}).get("*") or [0])[0])}

    def manifest(self, tables):
        return self._one("SELECT public.corpus_manifest(%s::text[])", (list(tables),))

    def keys(self, table, group):
        return self._one("SELECT public.corpus_keys(%s, %s)", (table, group))

    def ingest(self, table, rows, run_id):
        return self._one("SELECT public.corpus_ingest(%s, %s::jsonb, %s::uuid)",
                         (table, json.dumps(rows, ensure_ascii=False, separators=(",", ":")), run_id))

    def retire(self, table, group, keys, run_id):
        return self._one("SELECT public.corpus_retire(%s, %s, %s::jsonb, %s::uuid)",
                         (table, group, json.dumps(keys, ensure_ascii=False), run_id))

    def run(self, run_id, info, finish):
        return self._one("SELECT public.corpus_run(%s::uuid, %s::jsonb, %s)",
                         (run_id, json.dumps(info, ensure_ascii=False), bool(finish)))


def sign(secret: str, ts: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), ts.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()


class EdgeSink:
    name = "edge"

    def __init__(self, base_url: str, anon_key: str, secret: str, timeout: int = 150, retries: int = 3):
        self.url = base_url.rstrip("/") + "/functions/v1/corpus-ingest"
        self.anon, self.secret, self.timeout, self.retries = anon_key, secret, timeout, retries
        self.bytes_sent = 0

    def _call(self, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        body = gzip.compress(raw, 6)
        last = None
        for attempt in range(self.retries):
            ts = str(int(time.time()))
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Content-Type": "application/octet-stream",
                "x-corpus-encoding": "gzip",
                "x-corpus-ts": ts,
                "x-corpus-sig": sign(self.secret, ts, body),
                "apikey": self.anon,
                "Authorization": "Bearer " + self.anon,
            })
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                self.bytes_sent += len(body)
                if not data.get("ok"):
                    raise SinkError("corpus-ingest: %s" % str(data.get("error"))[:400])
                return data.get("result")
            except urllib.error.HTTPError as e:
                text = e.read()[:600].decode("utf-8", "replace")
                last = SinkError("corpus-ingest HTTP %d: %s" % (e.code, text))
                if e.code in (429, 500, 502, 503, 504) and attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = SinkError("corpus-ingest unreachable: %s" % e)
                if attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
        raise last or SinkError("corpus-ingest: no answer")

    def hello(self):
        return self._call({"action": "hello"})

    def manifest(self, tables):
        return self._call({"action": "manifest", "tables": list(tables)})

    def keys(self, table, group):
        return self._call({"action": "keys", "table": table, "group": group})

    def ingest(self, table, rows, run_id):
        return self._call({"action": "ingest", "table": table, "rows": rows, "run_id": run_id})

    def retire(self, table, group, keys, run_id):
        return self._call({"action": "retire", "table": table, "group": group, "keys": keys, "run_id": run_id})

    def run(self, run_id, info, finish):
        return self._call({"action": "run", "run_id": run_id, "info": info, "finish": bool(finish)})


# --------------------------------------------------------------------------- configuration

def _read_env_file(path) -> dict:
    out = {}
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


def load_config(env_path=None, site_env_path=None) -> dict:
    """CORPUS_SYNC_* from the environment or this repo's .env; the site URL and publishable key
    from the Srangam repo's .env unless CORPUS_SYNC_URL / CORPUS_SYNC_ANON_KEY are set."""
    try:
        import env_loader
        env_loader.load_env()
    except Exception:
        pass
    local = _read_env_file(env_path or (ROOT / ".env"))
    get = lambda k: os.environ.get(k) or local.get(k) or ""
    site = _read_env_file(site_env_path or get("CORPUS_SITE_ENV") or DEFAULT_SITE_ENV)
    return {
        "secret": get("CORPUS_SYNC_SECRET"),
        "url": get("CORPUS_SYNC_URL") or site.get("VITE_SUPABASE_URL", ""),
        "anon": get("CORPUS_SYNC_ANON_KEY") or site.get("VITE_SUPABASE_PUBLISHABLE_KEY", ""),
        "dsn": get("CORPUS_SYNC_DSN"),
    }


def make_sink(kind: str, cfg: dict, dsn: str | None = None):
    if kind == "auto":
        kind = "edge" if cfg.get("secret") else "none"
    if kind == "none":
        return NoneSink()
    if kind == "pg":
        d = dsn or cfg.get("dsn")
        if not d:
            raise SystemExit("--sink pg needs --dsn or CORPUS_SYNC_DSN")
        return PgSink(d)
    if kind == "edge":
        missing = [n for n, k in (("CORPUS_SYNC_SECRET", "secret"), ("the site URL", "url"),
                                  ("the publishable key", "anon")) if not cfg.get(k)]
        if missing:
            raise SystemExit("edge sink is not configured: missing %s (docs/CORPUS_MIRROR_2026-10-08.md, step 3)"
                             % ", ".join(missing))
        return EdgeSink(cfg["url"], cfg["anon"], cfg["secret"])
    raise SystemExit("unknown sink %r" % kind)


# --------------------------------------------------------------------------- the run

def batches(rows: list, max_bytes: int, max_rows: int):
    cur, size = [], 2
    for r in rows:
        n = len(json.dumps(r, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1
        if cur and (size + n > max_bytes or len(cur) >= max_rows):
            yield cur, size
            cur, size = [], 2
        cur.append(r)
        size += n
    if cur:
        yield cur, size


def check_scheme(manifest: dict):
    """C4B: refuse to compare digests made two different ways (that would re-send everything)."""
    got = manifest.get("_scheme") if isinstance(manifest, dict) else None
    if got != DIGEST_SCHEME:
        raise SinkError("the mirror answers with digest scheme %r, this client needs %r: apply "
                        "docs/cloud/C4b_mirror_digests_2026-10-08.sql (steps A and B) first"
                        % (got, DIGEST_SCHEME))


class Run:
    def __init__(self, con, sink, apply: bool, max_bytes_total=None, batch_bytes=DEFAULT_BATCH_BYTES,
                 allow_mass_retire=False, no_retire=False, out=print, progress=None):
        self.con, self.sink, self.apply = con, sink, apply
        # PROGRESS_2026_10_08: a first push takes minutes; say what is happening as it happens,
        # flushed, so a console or a log never sits silent (it looked "stuck" on 2026-10-08).
        self.progress = progress if progress is not None else (lambda m: print(m, flush=True))
        self.t0 = time.time()
        self.max_bytes_total = max_bytes_total
        self.batch_bytes = batch_bytes
        self.allow_mass_retire, self.no_retire = allow_mass_retire, no_retire
        self.out = out
        self.run_id = str(uuid.uuid4())
        self.stats = {t: {"groups_changed": 0, "upsert": 0, "changed": 0, "retire": 0, "retired": 0,
                          "held": 0, "skipped": 0, "coerced": 0, "bytes": 0} for t in TABLES}
        self.bytes_total = 0
        self.held = []
        self.hold_docs = False
        self.expected = {}       # (table, group) -> (count, digest), or None for "absent"

    def _p(self, msg: str):
        e = int(time.time() - self.t0)
        try:
            self.progress("[%3d:%02d] %s" % (e // 60, e % 60, msg))
        except Exception:
            pass

    def _send(self, table: str, rows: list):
        if not rows:
            return
        st = self.stats[table]
        if not self.apply:
            st["upsert"] += len(rows)
            st["bytes"] += (len(rows) * 12000 if table == "vectors" else
                            sum(len(json.dumps(r, ensure_ascii=False).encode("utf-8")) for r in rows))
            return
        if table == "vectors":
            rows = fill_vectors(self.con, rows)
        max_rows = MAX_VEC_ROWS_PER_CALL if table == "vectors" else MAX_ROWS_PER_CALL
        plan = list(batches(rows, self.batch_bytes, max_rows))
        for i, (chunk, size) in enumerate(plan, 1):
            if (self.max_bytes_total is not None and self.bytes_total > 0
                    and self.bytes_total + size > self.max_bytes_total):
                self._p("--max-mb reached after %.1f MB; the next run carries on" % (self.bytes_total / 1e6))
                raise Budget()
            tb = time.time()
            res = self._ingest(table, chunk)   # SYNC_SPLIT_2026_10_09
            st["upsert"] += len(chunk)
            st["changed"] += int(res.get("changed", 0))
            st["bytes"] += size
            self.bytes_total += size
            if len(plan) > 1:
                self._p("    %s batch %d/%d: %d rows, %.1f MB, %.1f s (run total %.1f MB)"
                        % (table, i, len(plan), len(chunk), size / 1e6, time.time() - tb, self.bytes_total / 1e6))

    def _ingest(self, table: str, chunk: list) -> dict:
        """SYNC_SPLIT_2026_10_09: a batch the database cancels for its statement timeout was rolled
        back whole, and corpus_ingest is idempotent, so it is sent again as two halves, down to one
        row. Any other error, and a one-row timeout, is raised as before."""
        try:
            return self.sink.ingest(table, chunk, self.run_id) or {}
        except SinkError as e:
            if "statement timeout" not in str(e) or len(chunk) <= 1:
                raise
            half = len(chunk) // 2
            self._p("    %s: the database timed out on %d rows; sending them as %d + %d"
                    % (table, len(chunk), half, len(chunk) - half))
            a = self._ingest(table, chunk[:half])
            b = self._ingest(table, chunk[half:])
            return {"received": len(chunk),
                    "changed": int(a.get("changed", 0)) + int(b.get("changed", 0))}

    def _retire(self, table: str, group: str, keys: list, remote_n: int, local_n: int, whole_doc=False) -> bool:
        """True when the keys were retired (or would be, in a plan); False when held."""
        if not keys:
            return True
        st = self.stats[table]
        if self.no_retire:
            st["held"] += len(keys)
            return False
        mass = (local_n == 0 and remote_n > 5) or (len(keys) > 100 and len(keys) > 0.5 * max(remote_n, 1))
        if mass and not whole_doc and not self.allow_mass_retire:
            st["held"] += len(keys)
            self.held.append("%s/%s: %d of %d rows would be retired (use --allow-mass-retire if that is right)"
                             % (table, group, len(keys), remote_n))
            return False
        st["retire"] += len(keys)
        if self.apply:
            step = MAX_VEC_KEYS_PER_RETIRE if table == "vectors" else MAX_KEYS_PER_RETIRE
            for i in range(0, len(keys), step):
                st["retired"] += self._retire_keys(table, group, keys[i:i + step])
        return True

    def _retire_keys(self, table: str, group: str, keys: list) -> int:
        """MIRROR_CAP_2026_10_12: as _ingest: a call the database cancels for its statement timeout was rolled back
        whole, and corpus_retire is idempotent (it retires only rows still live), so it is sent again as two
        halves, down to one key. Any other error, and a one-key timeout, is raised as before."""
        try:
            res = self.sink.retire(table, group, keys, self.run_id) or {}
            return int(res.get("retired", 0))
        except SinkError as e:
            if "statement timeout" not in str(e) or len(keys) <= 1:
                raise
            half = len(keys) // 2
            self._p("    %s %s: the database timed out retiring %d rows; sending them as %d + %d"
                    % (table, group, len(keys), half, len(keys) - half))
            return self._retire_keys(table, group, keys[:half]) + self._retire_keys(table, group, keys[half:])

    def diff_group(self, g: Group, remote_manifest: dict, retire: bool = True):
        st = self.stats[g.table]
        st["skipped"] += g.skipped
        st["coerced"] += g.coerced
        rem = remote_manifest.get(g.table, {}).get(g.group)
        local_n = len(g.hashes)
        local_d = g.digest()
        if retire:
            self.expected[(g.table, g.group)] = (local_n, local_d) if local_n else None
        if rem and int(rem[0]) == local_n and rem[1] == local_d:
            return
        if not rem and local_n == 0:
            return
        st["groups_changed"] += 1
        remote_keys = self.sink.keys(g.table, g.group) if rem else {}
        send = [g.rows[k] for k, h in g.hashes.items() if remote_keys.get(k) != h]
        gone = sorted(k for k in remote_keys if k not in g.hashes)
        if self.apply and (send or gone):
            self._p("%s %s: %d to send, %d gone here (mirror had %d, here %d)"
                    % (g.table, g.group, len(send), len(gone), len(remote_keys), local_n))
        tg = time.time()
        self._send(g.table, send)
        if retire and gone and not self._retire(g.table, g.group, gone, len(remote_keys), local_n):
            self.expected.pop((g.table, g.group), None)
        if self.apply and (send or gone):
            self._p("%s %s: done in %.1f s" % (g.table, g.group, time.time() - tg))

    def execute(self, tables, docs, only_docs=None):
        t0 = time.time()
        stopped, error = "done", None
        partial = bool(only_docs)
        sel_docs = [d for d in docs if not partial or d[1] in only_docs]
        self._p("asking the mirror what it holds (%s) ..." % self.sink.name)
        remote = self.sink.manifest(TABLES)
        check_scheme(remote)
        held_rows = sum(int(v[0]) for t in TABLES for v in remote.get(t, {}).values())
        self._p("mirror holds %d rows; %d live documents here; %s"
                % (held_rows, len(sel_docs), "sending changes" if self.apply else "plan only, nothing is sent"))
        live = {d[1] for d in docs}
        gone_docs = [] if partial else sorted(
            {g for t in PER_DOC_TABLES if t in tables for g in remote.get(t, {}) if g not in live})
        n_remote_docs = int((remote.get("docs", {}).get("*") or [0, ""])[0])
        if len(gone_docs) > max(3, int(0.1 * n_remote_docs)) and not self.allow_mass_retire:
            self.hold_docs = True
            self.held.append("%d documents are in the mirror but not live here (%s); nothing of them is retired. "
                             "Use --allow-mass-retire if that is right" % (len(gone_docs), ", ".join(gone_docs[:5])))
        if self.apply:
            self.sink.run(self.run_id, {"client": CLIENT, "tables": tables,
                                        "docs": sorted(only_docs) if partial else "all"}, False)
        titles = load_titles()
        try:
            if "docs" in tables:
                self.diff_group(build_docs(self.con, sel_docs, titles), remote,
                                retire=not partial and not self.hold_docs)
            ent_ok = set()
            if "entities" in tables or "mentions" in tables:
                ge = build_entities(self.con)
                ent_ok = set(ge.hashes)
                if "entities" in tables:
                    self.diff_group(ge, remote, retire=not partial)
            per_doc = [t for t in PER_DOC_TABLES if t in tables]
            if per_doc:
                in_repair = _in_repair_docs()   # REPAIR_HEAL_2026_10_11
                for n_doc, doc in enumerate(sel_docs, 1):
                    if doc[1] in in_repair:
                        self.held.append("%s: in repair (data/source_verdicts.jsonl): not compared or sent; the site "
                                         "keeps its last version until repair_text.py --release" % doc[1])
                        continue
                    groups = build_doc_groups(self.con, doc, set(per_doc), ent_ok)
                    for t in per_doc:
                        self.diff_group(groups[t], remote)
                    if n_doc % 10 == 0 or n_doc == len(sel_docs):
                        self._p("compared %d/%d documents (%.1f MB sent so far)"
                                % (n_doc, len(sel_docs), self.bytes_total / 1e6))
            if gone_docs and not self.hold_docs:
                for code in gone_docs:
                    for t in reversed(per_doc):
                        rem = remote.get(t, {}).get(code)
                        if rem:
                            self.stats[t]["groups_changed"] += 1
                            keys = sorted(self.sink.keys(t, code).keys())
                            if self._retire(t, code, keys, int(rem[0]), 0, whole_doc=True):
                                self.expected[(t, code)] = None
        except Budget:
            stopped = "budget"
        except SinkError as e:
            stopped, error = "error", str(e)
        if self.apply and stopped == "done":
            self._p("checking every group against the mirror ...")
        verified = None
        if self.apply and stopped == "done":
            try:
                verified = self.verify()
            except SinkError as e:
                # the rows are in; only the final check could not run. Say so, keep the record.
                verified = {"groups_equal": 0, "groups_different": None, "different": [],
                            "error": str(e)[:300]}
        summary = {"run_id": self.run_id, "sink": self.sink.name, "apply": self.apply, "stopped": stopped,
                   "error": error, "seconds": round(time.time() - t0, 1), "bytes": self.bytes_total,
                   "tables": {t: s for t, s in self.stats.items() if t in tables}, "held": self.held,
                   "verified": verified}
        if self.apply:
            try:
                self.sink.run(self.run_id, {"summary": {"stopped": stopped, "bytes": self.bytes_total,
                                                        "verified": verified, "error": error}}, True)
            except SinkError:
                pass
        return summary

    def verify(self):
        """After a run, the server's digest of every group this run settled must equal what was
        read here at the start of the run (a fresh read could differ while translation runs)."""
        remote = self.sink.manifest(TABLES)
        check_scheme(remote)
        bad = []
        for (t, g), exp in sorted(self.expected.items()):
            rem = remote.get(t, {}).get(g)
            same = (exp is None and not rem) or (exp is not None and rem is not None
                                                  and int(rem[0]) == exp[0] and rem[1] == exp[1])
            if not same:
                bad.append("%s/%s" % (t, g))
        return {"groups_equal": len(self.expected) - len(bad), "groups_different": len(bad), "different": bad[:20]}


def local_counts(con, docs) -> dict:
    """Rows this PC would mirror, counted cheaply (no hashing), for --status."""
    ids = [d[0] for d in docs]
    codes = [d[1] for d in docs]
    out = {t: 0 for t in TABLES}
    out["docs"] = len(docs)
    if not ids:
        return out
    q = ",".join("?" * len(ids))
    one = lambda sql, args=(): con.execute(sql, args).fetchone()[0] or 0
    out["passages"] = one("SELECT count(*) FROM passages WHERE doc_id IN (%s)" % q, ids)
    if _has_table(con, "entities"):
        out["entities"] = one("SELECT count(*) FROM entities WHERE trim(coalesce(canonical,'')) <> ''")
    if _has_table(con, "translations_l10n"):
        out["translations"] = one("SELECT count(*) FROM translations_l10n l JOIN passages p ON p.id = l.passage_id "
                                  "WHERE p.doc_id IN (%s)" % q, ids)
    if _has_table(con, "scholar_translations"):   # SCHOLAR_MIRROR_2026_10_18: and the scholarly English's rows
        out["translations"] += scholar_count(con, docs)
    if _has_table(con, "entity_mentions") and _has_table(con, "entities"):
        out["mentions"] = one("SELECT count(*) FROM entity_mentions m JOIN passages p ON p.id = m.passage_id "
                              "JOIN entities e ON e.id = m.entity_id WHERE p.doc_id IN (%s) "
                              "AND trim(coalesce(e.canonical,'')) <> ''" % q, ids)
    if _has_table(con, "doc_stories"):
        out["stories"] = one("SELECT count(*) FROM doc_stories WHERE doc_id IN (%s)" % q, ids)
    if _has_table(con, "doc_stage"):
        out["stages"] = one("SELECT count(*) FROM doc_stage WHERE stage IS NOT NULL AND doc_code IN (%s)"
                            % ",".join("?" * len(codes)), codes)
    if _has_table(con, "passage_embeddings"):
        out["vectors"] = one("SELECT count(*) FROM passage_embeddings e JOIN passages p ON p.id = e.passage_id "
                             "WHERE p.doc_id IN (%s) AND e.dim >= ? AND length(e.vec) = 4 * e.dim" % q,
                             ids + [VEC_DIMS])
    return out


def status(con, sink, docs, out=print) -> dict:
    """PROGRESS_2026_10_08: what the mirror holds against what is here (read-only both sides)."""
    m = sink.manifest(TABLES)
    check_scheme(m)
    here = local_counts(con, docs)
    rows = {}
    out("corpus mirror status  sink=%s  digests %s  (read-only; counts, not hashes)" % (sink.name, m.get("_scheme")))
    out("  %-13s %10s %10s %7s" % ("table", "mirror", "here", "share"))
    for t in TABLES:
        n = sum(int(v[0]) for v in m.get(t, {}).values())
        rows[t] = {"mirror": n, "here": here[t]}
        share = ("%6.1f%%" % (100.0 * n / here[t])) if here[t] else "      -"
        out("  %-13s %10d %10d %7s" % (t, n, here[t], share))
    out("  Equal counts are not proof of equal content: the digest check of an --apply run is.")
    return rows


def print_summary(s: dict, out=print):
    mode = "SENT" if s["apply"] else "PLAN (nothing sent; add --apply)"
    out("corpus_sync %s  sink=%s  %s" % (CLIENT_VERSION, s["sink"], mode))
    out("  %-13s %8s %9s %9s %8s %6s %8s %9s" % ("table", "groups", "upsert", "changed", "retire", "held", "skipped", "MB"))
    for t, st in s["tables"].items():
        out("  %-13s %8d %9d %9s %8d %6d %8d %9.1f" % (
            t, st["groups_changed"], st["upsert"], st["changed"] if s["apply"] else "-", st["retire"],
            st["held"], st["skipped"], st["bytes"] / 1e6))
    coerced = {t: st["coerced"] for t, st in s["tables"].items() if st.get("coerced")}
    if coerced:
        out("  coerced (a value that did not fit its column was sent as empty): %s" % coerced)
    for h in s["held"]:
        out("  HELD: " + h)
    if s["verified"] and s["verified"].get("error"):
        out("  verify: COULD NOT RUN (%s). The rows above were sent; run --status, then run again."
            % s["verified"]["error"])
    elif s["verified"]:
        v = s["verified"]
        out("  verify: %d groups equal, %d different%s" % (
            v["groups_equal"], v["groups_different"], (" (" + ", ".join(v["different"]) + ")") if v["different"] else ""))
    out("  stopped=%s  %.1f s  %.1f MB sent%s" % (
        s["stopped"], s["seconds"], s["bytes"] / 1e6,
        ("  ERROR: " + s["error"]) if s["error"] else ""))
    if s["stopped"] == "budget":
        out("  --max-mb reached; the next run carries on from here.")


def log_run(s: dict, path: Path = LOG_PATH):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = dict(s)
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except OSError:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Keep the private PostgreSQL corpus mirror current (C4).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--immutable", action="store_true", help="the --db file is a backup copy (adds immutable=1)")
    ap.add_argument("--sink", default="auto", choices=["auto", "edge", "pg", "none"])
    ap.add_argument("--dsn", default=None, help="for --sink pg (else CORPUS_SYNC_DSN)")
    ap.add_argument("--apply", action="store_true", help="send; without it only the plan is printed")
    ap.add_argument("--doc", action="append", default=[], help="only this document (repeatable); never retires documents")
    ap.add_argument("--tables", default=",".join(TABLES), help="comma list, default all: " + ",".join(TABLES))
    ap.add_argument("--max-mb", type=float, default=None, help="stop after sending about this many MB (resume next run)")
    ap.add_argument("--batch-kb", type=int, default=DEFAULT_BATCH_BYTES // 1000)
    ap.add_argument("--no-retire", action="store_true")
    ap.add_argument("--allow-mass-retire", action="store_true")
    ap.add_argument("--include-retired-docs", action="store_true")
    ap.add_argument("--if-configured", action="store_true",
                    help="exit 0 quietly when the edge sink is not configured (for the maintenance runner)")
    ap.add_argument("--hello", action="store_true", help="check the sink answers, then exit")
    ap.add_argument("--status", action="store_true",
                    help="rows in the mirror against rows here, per table (read-only), then exit")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    a = ap.parse_args(argv)

    tables = [t.strip() for t in a.tables.split(",") if t.strip()]
    bad = [t for t in tables if t not in TABLES]
    if bad:
        print("unknown table(s): %s" % ", ".join(bad))
        return 1
    tables = [t for t in TABLES if t in tables]
    cfg = load_config()
    if a.if_configured and a.sink in ("auto", "edge") and not (cfg["secret"] and cfg["url"] and cfg["anon"]):
        print("corpus mirror: not configured (CORPUS_SYNC_SECRET); skipped")
        return 0
    sink = make_sink(a.sink, cfg, a.dsn)
    if a.hello:
        try:
            print(json.dumps(sink.hello()))
            return 0
        except SinkError as e:
            print("hello failed: %s" % e)
            return 2
    con = open_ro(a.db, a.immutable)
    docs = live_docs(con, a.include_retired_docs)
    if a.status:
        try:
            status(con, sink, docs)
            return 0
        except SinkError as e:
            print("status failed: %s" % e)
            return 2
    only = set(a.doc) if a.doc else None
    if only:
        known = {d[1] for d in docs}
        missing = sorted(only - known)
        if missing:
            print("not a live document here: %s" % ", ".join(missing))
            return 1
    run = Run(con, sink, a.apply, None if a.max_mb is None else int(a.max_mb * 1e6), a.batch_kb * 1000,
              a.allow_mass_retire, a.no_retire)
    try:
        s = run.execute(tables, docs, only)
    except SinkError as e:
        print("corpus_sync: %s" % e)
        if a.apply:
            log_run({"run_id": run.run_id, "sink": sink.name, "apply": True, "stopped": "error",
                     "error": str(e)[:500], "seconds": round(time.time() - run.t0, 1), "bytes": run.bytes_total,
                     "tables": {t: st for t, st in run.stats.items() if t in tables}, "held": run.held,
                     "verified": None, "client": CLIENT})
        return 2
    print(json.dumps(s, indent=1)) if a.json else print_summary(s)
    if a.apply:
        s["client"] = CLIENT
        log_run(s)
    if s["stopped"] == "error" or (s["verified"] or {}).get("error"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
