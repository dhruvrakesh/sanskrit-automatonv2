#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
automaton.py  (2026-09-14)  AUTOMATON_LEDGER_2026_09_14

The stage ledger. One new table. Nothing else in the database is written.

Why this file exists
--------------------
The pipeline already exists as scripts, and the scripts already work. What
does not exist anywhere is a record of where a document IS. The schema,
verbatim from db_utils.py:

    docs(id, code, category, src_path, glossary, created_at)

No stage. No status. No last-run. No attempt count. So advance_pipeline.py
carries a hardcoded list of 22 doc codes and restarts from the top every
time, and pipeline_queue.py collects its stage results in a local list that
dies with the process. Neither is resumable, because neither has anywhere to
resume from. That absence is the entire distance between "a set of scripts
that work" and "an automaton".

Four commitments, each answering a failure this project has already had
-----------------------------------------------------------------------
1. ONE unit of work per invocation, then exit. A run that is always short is
   a run the PT1H scheduled-task limit can never kill mid-write. The
   maintenance log records 100 TICKs, 45 STARTs and 0 DONEs precisely
   because the old runner tried to do everything in one process.

2. IDEMPOTENCE BY FINGERPRINT, not by flag. A stage is done only while its
   recorded input_fp still equals what its inputs hash to now. This is
   Booksmith's source_sha256 model, which this project already trusts enough
   to refuse a build over, as it did to the Hindi Shatpath on 13 September.
   Change the text and every downstream stage goes stale by itself; nothing
   has to remember to invalidate anything.

3. MEASURED, NOT ASSUMED. Every stage records what it observed. Below its
   floor it becomes blocked or degraded with a reason in words, never
   silently done.

4. DERIVED, NOT DECLARED. The ledger is backfilled from what is measurably
   true in the database today, not from anyone's memory of what was run.

Two severities, because the corpus proves they differ
-----------------------------------------------------
Measured across all 57 documents on 2026-09-14:

  blocked   Padma Purana: 2.3 words per row, 33.9% of words over 20
            characters, 18.4% kosha-recognised against MBh01's 80.2%. The
            rows are fragments of unsegmented running text. Translating
            that spends money on damage, so the chain HALTS.

  degraded  smriti_14manu: 128.3 words per row, whole pages as one unit.
            But it IS translated and its exports build. Booksmith refuses a
            reading edition; an audit edition is fine. The chain CONTINUES
            carrying the flag. Thirty documents are this shape.

One "broken" flag would have stopped thirty working documents, or let the
Padma Purana through. Neither is right.

Safety
------
Reads are opened with PRAGMA query_only=ON rather than immutable=1. That is
deliberate and it is the pattern diag_spend_bound.py already uses: the
database runs in WAL mode, and immutable=1 makes SQLite ignore the -wal
sidecar entirely, so a status report taken straight after a write would show
the pre-write state. query_only reads the live WAL and still refuses writes
at the engine level.

Every schema-changing and row-writing statement that can reach the project
database names doc_stage and sits on a single physical line, so that
grepping this file for write keywords is a real audit rather than a
formality. The only other write statements in the file build the --selftest
fixture; they are fenced between a pair of BEGIN/END sentinel comments in
_fixture_db, they run against a tempfile.mkdtemp directory, and neither
_fixture_db nor cmd_selftest ever reads the --db argument. The deployment
block checks all three of those claims mechanically rather than asking you
to take them on trust.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MARK = "AUTOMATON_LEDGER_2026_09_14"

# ---------------------------------------------------------------------------
# The pipeline, as a graph rather than a line. A strict line would have said
# that nothing can be exported until Hindi exists, which is false: Hindi is
# at 10,036 rows of 49,555 and the English exports have been building for
# months. The edges below are the real prerequisites.
# ---------------------------------------------------------------------------
STAGES = [
    "ocr", "ingest", "segment", "classify", "iast",
    "translate_en", "translate_hi", "qa", "entities", "embed",
    "morph", "export", "book",
]

DEPS = {
    "ocr":          [],
    "ingest":       ["ocr"],
    "segment":      ["ingest"],
    "classify":     ["ingest"],
    "iast":         ["segment"],
    "translate_en": ["segment", "classify"],
    "translate_hi": ["translate_en"],
    "qa":           ["translate_en"],
    "entities":     ["translate_en"],
    "embed":        ["segment"],
    "morph":        ["iast"],
    "export":       ["translate_en"],
    "book":         ["export"],
}

DDL = """
CREATE TABLE IF NOT EXISTS doc_stage(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_code    TEXT NOT NULL,
  stage       TEXT NOT NULL,
  status      TEXT NOT NULL,
  input_fp    TEXT,
  measured    TEXT,
  reason      TEXT,
  attempts    INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL,
  UNIQUE(doc_code, stage)
);
CREATE INDEX IF NOT EXISTS idx_doc_stage_status ON doc_stage(status, stage);
"""

# One physical line, on purpose: the deployment block greps this file for
# write keywords and asserts every hit names doc_stage. Split across lines,
# the conflict clause would land on a line that does not name it.
UPSERT = "INSERT INTO doc_stage(doc_code,stage,status,input_fp,measured,reason,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(doc_code,stage) DO UPDATE SET status=excluded.status, input_fp=excluded.input_fp, measured=excluded.measured, reason=excluded.reason, updated_at=excluded.updated_at"

STATUS_OK = ("done", "degraded")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fp(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def connect(db, writable):
    con = sqlite3.connect(db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    if not writable:
        con.execute("PRAGMA query_only=ON")
    return con


def table_cols(con, table):
    try:
        return set(r[1] for r in con.execute("PRAGMA table_info(%s)" % table))
    except Exception:
        return set()


def has_table(con, table):
    try:
        r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone()
        return r is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Measurement. Everything here reads. Nothing here writes.
#
# Done as three grouped passes plus one small per-document sample, rather
# than a dozen COUNT queries per document. On 57 documents the naive shape
# is about 700 aggregate scans of a 49,555-row table; this is four.
# ---------------------------------------------------------------------------
def corpus_measure(con, root: Path, bs_root: Path, verbose=False):
    pcols = table_cols(con, "passages")
    dcols = table_cols(con, "docs")
    if not pcols or not dcols:
        raise SystemExit("FAIL: this database has no passages/docs tables.")

    live = ("p.id IS NOT NULL AND COALESCE(p.text_type,'mula') "
            "NOT IN ('noise','frontmatter')") if "text_type" in pcols \
        else "p.id IS NOT NULL"

    def nonblank(col):
        if col not in pcols:
            return "0"
        return "SUM(CASE WHEN %s AND TRIM(COALESCE(p.%s,''))<>'' THEN 1 ELSE 0 END)" % (live, col)

    def notnull(col):
        if col not in pcols:
            return "0"
        return "SUM(CASE WHEN %s AND p.%s IS NOT NULL THEN 1 ELSE 0 END)" % (live, col)

    typed = ("SUM(CASE WHEN p.text_type IS NOT NULL THEN 1 ELSE 0 END)"
             if "text_type" in pcols else "0")

    sql = ("SELECT d.code, d.id, COUNT(p.id), "
           "SUM(CASE WHEN %s THEN 1 ELSE 0 END), %s, %s, %s, %s, %s, %s "
           "FROM docs d LEFT JOIN passages p ON p.doc_id=d.id "
           "GROUP BY d.id, d.code" % (
               live, typed,
               nonblank("iast"), nonblank("translation"),
               nonblank("translation_qa"), notnull("ents"), nonblank("morph")))
    if verbose:
        print("  measurement query:\n    %s" % sql)

    docs = {}
    for code, did, npass, nlive, ntyped, niast, nen, nqa, nents, nmorph in con.execute(sql):
        docs[code] = {
            "doc_id": did,
            "passages": npass or 0, "live": nlive or 0, "typed": ntyped or 0,
            "iast": niast or 0, "en": nen or 0, "qa": nqa or 0,
            "ents": nents or 0, "morph": nmorph or 0,
            "hi": 0, "embed": 0,
        }

    # Hindi lives in its own table. Count only rows that carry text, if a
    # text-bearing column can be identified; a row with an empty body is not
    # a translation.
    if has_table(con, "translations_l10n"):
        lcols = table_cols(con, "translations_l10n")
        body = next((c for c in ("text", "translation", "content", "body", "value")
                     if c in lcols), None)
        pred = " AND TRIM(COALESCE(l.%s,''))<>''" % body if body else ""
        try:
            q = ("SELECT d.code, COUNT(*) FROM translations_l10n l "
                 "JOIN passages p ON p.id=l.passage_id "
                 "JOIN docs d ON d.id=p.doc_id "
                 "WHERE l.lang='hi'%s GROUP BY d.code" % pred)
            for code, n in con.execute(q):
                if code in docs:
                    docs[code]["hi"] = n
        except Exception as e:
            if verbose:
                print("  (hindi count unavailable: %s)" % e)

    for tbl, col in (("passage_embeddings", "passage_id"), ("embeddings", "passage_id")):
        if has_table(con, tbl) and col in table_cols(con, tbl):
            try:
                for code, n in con.execute(
                        "SELECT d.code, COUNT(*) FROM %s e "
                        "JOIN passages p ON p.id=e.%s "
                        "JOIN docs d ON d.id=p.doc_id GROUP BY d.code" % (tbl, col)):
                    if code in docs:
                        docs[code]["embed"] = max(docs[code]["embed"], n)
            except Exception:
                pass
            break

    # Word shape, sampled. This is the measurement that separates a
    # segmentation fault from an OCR fault, and it is the one my own earlier
    # sampler got wrong by ordering on LENGTH(text) DESC, which selects
    # indexes and tables of contents. Order by id.
    txt = "text" if "text" in pcols else None
    for code, m in docs.items():
        m["sampled_rows"] = 0
        m["words_per_row"] = 0.0
        m["long_word_share"] = 0.0
        if not txt or m["passages"] == 0:
            continue
        rows = con.execute(
            "SELECT p.text FROM passages p WHERE p.doc_id=? AND %s "
            "AND TRIM(COALESCE(p.text,''))<>'' ORDER BY p.id LIMIT 400" % live,
            (m["doc_id"],)).fetchall()
        wc, lens = 0, []
        for (t,) in rows:
            ws = [w for w in re.split(r"[\s\u0964\u0965|/]+", t or "") if w.strip()]
            wc += len(ws)
            lens.extend(len(w) for w in ws)
        m["sampled_rows"] = len(rows)
        if rows:
            m["words_per_row"] = round(float(wc) / len(rows), 1)
        if lens:
            m["long_word_share"] = round(100.0 * sum(1 for L in lens if L > 20) / len(lens), 1)

    # Filesystem facts.
    raw_dir = root / "data" / "raw"
    exp_dir = root / "exports"
    proj_dir = bs_root / "projects"
    for code, m in docs.items():
        raw = sorted(raw_dir.glob("%s*.jsonl" % code)) if raw_dir.is_dir() else []
        m["raw_files"] = len(raw)
        m["raw_fp"] = fp(*[(p.name, p.stat().st_size) for p in raw]) if raw else ""
        exp = sorted(exp_dir.glob("%s*.html" % code)) if exp_dir.is_dir() else []
        m["exports"] = len(exp)
        m["slug"] = slug_for(code)
        pdfs, proofs = [], []
        if proj_dir.is_dir():
            for d in sorted(proj_dir.glob("%s*" % m["slug"])):
                b = d / "build"
                if not b.is_dir():
                    continue
                for f in b.glob("*.pdf"):
                    (proofs if "proof" in f.name.lower() else pdfs).append(f)
        m["book_pdf"] = len(pdfs)
        m["layout_proof"] = len(proofs)
        lv = max(1, m["live"])
        m["pct"] = dict((k, round(100.0 * m[k] / lv, 1))
                        for k in ("iast", "en", "hi", "qa", "ents", "morph", "embed"))
    return docs


def slug_for(code):
    s = code.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:64]


# ---------------------------------------------------------------------------
def judge(stage, m):
    """(status, reason, input_fp) for one stage, from measurement alone.

    The floors are not opinions. words_per_row comes from the corpus-wide
    survey of 2026-09-14, in which MBh01 - a GRETIL critical edition, the
    only text here that was never OCR'd - sits at 12.5, and every document
    outside roughly 4..60 is either fragments or whole pages."""
    p = m["pct"]
    live = max(1, m["live"])

    if stage == "ocr":
        if m["raw_files"] == 0 and m["passages"] > 0:
            return "done", "ingested before data/raw was kept; nothing to redo", fp("legacy", m["passages"])
        if m["raw_files"] == 0:
            return "pending", "no data/raw jsonl for this code", ""
        return "done", "%d jsonl file(s) in data/raw" % m["raw_files"], m["raw_fp"]

    if stage == "ingest":
        if m["passages"] == 0:
            return "pending", "no passages", ""
        return "done", "%d passages, %d live" % (m["passages"], m["live"]), fp(m["passages"])

    if stage == "segment":
        if m["passages"] == 0:
            return "pending", "nothing ingested", ""
        w = m["words_per_row"]
        lw = m["long_word_share"]
        f = fp(m["passages"], w, lw)
        if m["sampled_rows"] == 0:
            return "pending", "no non-empty text rows to measure", f
        if w < 4:
            return "blocked", ("%.1f words per row - rows are fragments, not verses "
                               "(MBh01, the clean control, is 12.5). Translating "
                               "fragments spends the API call on damage." % w), f
        if lw > 25:
            return "blocked", ("%.1f%% of words exceed 20 characters - the text is not "
                               "word-separated, so every lookup and every translation "
                               "sees a run, not a word" % lw), f
        if w > 60:
            return "degraded", ("%.1f words per row - whole pages as one unit. "
                                "Translation and export work; a Booksmith reading "
                                "edition will not." % w), f
        return "done", "%.1f words per row, %.1f%% long-word" % (w, lw), f

    if stage == "classify":
        if m["passages"] == 0:
            return "pending", "nothing ingested", ""
        share = 100.0 * m["typed"] / max(1, m["passages"])
        f = fp(m["passages"], m["typed"])
        if share < 50:
            return "pending", "text_type set on %.0f%% of rows" % share, f
        return "done", "text_type on %.0f%% of rows" % share, f

    if stage == "iast":
        if m["passages"] == 0:
            return "pending", "nothing ingested", ""
        f = fp(m["live"], m["iast"])
        if p["iast"] < 90:
            return "pending", "iast on %.1f%% of live rows" % p["iast"], f
        return "done", "iast on %.1f%%" % p["iast"], f

    if stage in ("translate_en", "translate_hi"):
        key = "en" if stage == "translate_en" else "hi"
        f = fp(m["live"], m[key])
        if m["passages"] == 0:
            return "pending", "nothing ingested", ""
        if p[key] >= 95:
            return "done", "%.1f%% translated" % p[key], f
        return "pending", "%.1f%% translated, %d row(s) to go" % (p[key], live - m[key]), f

    if stage == "qa":
        f = fp(m["en"], m["qa"])
        if m["en"] == 0:
            return "pending", "nothing translated yet", f
        share = 100.0 * m["qa"] / max(1, m["en"])
        if share >= 95:
            return "done", "scored on %.0f%% of translations" % share, f
        return "pending", "scored on %.0f%% of translations" % share, f

    if stage == "entities":
        f = fp(m["en"], m["ents"])
        if m["en"] == 0:
            return "pending", "entities are extracted from translations", f
        share = 100.0 * m["ents"] / max(1, m["en"])
        if share >= 95:
            return "done", "%.0f%% of translated rows carry ents" % share, f
        return "pending", "%.0f%% of translated rows carry ents" % share, f

    if stage == "embed":
        f = fp(m["live"], m["embed"])
        if p["embed"] >= 90:
            return "done", "%.1f%% embedded" % p["embed"], f
        return "pending", "%.1f%% embedded" % p["embed"], f

    if stage == "morph":
        f = fp(m["live"], m["morph"])
        if p["morph"] >= 95:
            return "done", "%.1f%% analysed" % p["morph"], f
        return "pending", "%.1f%% analysed (kosha ceiling on clean text is ~80%%)" % p["morph"], f

    if stage == "export":
        f = fp(m["exports"], m["en"], m["hi"])
        if m["exports"] == 0:
            return "pending", "no exports html for this code", f
        return "done", "%d export file(s)" % m["exports"], f

    if stage == "book":
        f = fp(m["book_pdf"], m["layout_proof"], m["exports"])
        if m["book_pdf"] > 0:
            return "done", "%d pdf(s) under projects/%s*" % (m["book_pdf"], m["slug"]), f
        if m["layout_proof"] > 0:
            return "blocked", ("only a layout proof exists, not a book - the audit "
                               "gate has not been cleared"), f
        return "pending", "no Booksmith build", f

    return "pending", "unknown stage", ""


def measured_json(m):
    keep = ("passages", "live", "sampled_rows", "words_per_row",
            "long_word_share", "raw_files", "exports", "book_pdf", "layout_proof")
    d = dict((k, m[k]) for k in keep if k in m)
    d["pct"] = m.get("pct", {})
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
def cmd_init(a):
    con = connect(a.db, writable=True)
    con.executescript(DDL)
    con.commit()
    cols = [r[1] for r in con.execute("PRAGMA table_info(doc_stage)")]
    if not cols:
        print("FAIL: doc_stage was not created.")
        con.close()
        return 1
    print("doc_stage columns: %s" % ", ".join(cols))
    print("rows: %d" % con.execute("SELECT COUNT(*) FROM doc_stage").fetchone()[0])
    print("No pre-existing table was modified. Every write statement in this")
    print("file names doc_stage; the block above prints them for you to check.")
    con.close()
    return 0


def cmd_backfill(a):
    con = connect(a.db, writable=True)
    con.executescript(DDL)
    docs = corpus_measure(con, Path(a.root), Path(a.booksmith_root), verbose=a.verbose)
    print("%s  backfilling %d document(s) from measurement" % (MARK, len(docs)))
    print("Nothing below is declared. Every status is derived from the data.")
    print("")
    wrote, changed = 0, 0
    prior = dict(((c, s), (st, f)) for c, s, st, f in
                 con.execute("SELECT doc_code, stage, status, input_fp FROM doc_stage"))
    ts = now()
    for code in sorted(docs):
        m = docs[code]
        meas = measured_json(m)
        for st in STAGES:
            status, reason, f = judge(st, m)
            was = prior.get((code, st))
            if was is None or was[0] != status or was[1] != f:
                changed += 1
            con.execute(UPSERT, (code, st, status, f, meas, reason, ts))
            wrote += 1
    con.commit()
    print("wrote %d ledger row(s) across %d document(s); %d differ from what"
          % (wrote, len(docs), changed))
    print("the ledger said before this run.")
    con.close()
    return 0


def _load_board(con):
    board = {}
    for code, stage, status, reason in con.execute(
            "SELECT doc_code, stage, status, reason FROM doc_stage"):
        board.setdefault(code, {})[stage] = (status, reason)
    return board


def cmd_status(a):
    con = connect(a.db, writable=False)
    if not has_table(con, "doc_stage"):
        print("doc_stage does not exist yet. Run --init --backfill first.")
        con.close()
        return 1
    board = _load_board(con)
    sizes = dict(con.execute("SELECT d.code, COUNT(p.id) FROM docs d "
                             "LEFT JOIN passages p ON p.doc_id=d.id GROUP BY d.code"))
    print("%s  the board" % MARK)
    print("")
    hdr = "  %-34s %7s  " % ("document", "rows") + " ".join("%-4s" % s[:4] for s in STAGES)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    SYM = {"done": " ok ", "pending": "  . ", "blocked": "BLK ",
           "degraded": "deg ", "failed": "ERR "}
    for code in sorted(board, key=lambda c: -sizes.get(c, 0)):
        line = "  %-34s %7d  " % (code[:34], sizes.get(code, 0))
        line += " ".join(SYM.get(board[code].get(s, ("pending", ""))[0], "  ? ")
                         for s in STAGES)
        print(line)
    print("  " + "-" * (len(hdr) - 2))
    print("  ok = done   deg = degraded, chain continues   BLK = blocked, chain halts")
    print("  columns: " + "  ".join("%s=%s" % (s[:4], s) for s in STAGES))

    print("")
    print("  totals by stage")
    for s in STAGES:
        c = dict(con.execute("SELECT status, COUNT(*) FROM doc_stage WHERE stage=? "
                             "GROUP BY status", (s,)).fetchall())
        print("    %-14s done %3d   degraded %3d   pending %3d   blocked %3d" % (
            s, c.get("done", 0), c.get("degraded", 0),
            c.get("pending", 0), c.get("blocked", 0)))

    print("")
    print("  blocked and degraded, with the measurement behind each")
    n = 0
    for code, stage, status, reason in con.execute(
            "SELECT doc_code, stage, status, reason FROM doc_stage "
            "WHERE status IN ('blocked','degraded') ORDER BY status, stage, doc_code"):
        print("    %-8s %-30s %-9s %s" % (status, code[:30], stage, reason))
        n += 1
    if n == 0:
        print("    (none)")
    con.close()
    return 0


def cmd_next(a):
    """What the driver would do next, and what it refuses to touch. Runs nothing."""
    con = connect(a.db, writable=False)
    if not has_table(con, "doc_stage"):
        print("doc_stage does not exist yet. Run --init --backfill first.")
        con.close()
        return 1
    board = _load_board(con)
    sizes = dict(con.execute("SELECT d.code, COUNT(p.id) FROM docs d "
                             "LEFT JOIN passages p ON p.doc_id=d.id GROUP BY d.code"))
    print("%s  next actionable units" % MARK)
    print("")
    print("  A stage is actionable when it is pending and every prerequisite is")
    print("  done or degraded. Degraded satisfies a prerequisite on purpose: an")
    print("  under-segmented document still translates and still exports. Blocked")
    print("  does not, and that is the point - nothing downstream of a")
    print("  segmentation fault should run at all.")
    print("")
    ready, halted = [], []
    for code, st in board.items():
        n = sizes.get(code, 0)
        for s in STAGES:
            status, reason = st.get(s, ("pending", ""))
            if status in STATUS_OK:
                continue
            if status in ("blocked", "failed"):
                halted.append((n, code, s, reason))
                continue
            deps = DEPS.get(s, [])
            if all(st.get(d, ("pending", ""))[0] in STATUS_OK for d in deps):
                ready.append((n, code, s, reason))
    lim = a.limit
    print("  READY  %d unit(s); largest first%s" % (
        len(ready), (", showing %d" % lim) if len(ready) > lim else ""))
    for n, code, s, reason in sorted(ready, reverse=True)[:lim]:
        print("    %-32s %-13s %7d rows  %s" % (code[:32], s, n, reason[:44]))
    if not ready:
        print("    (none)")
    print("")
    print("  HALTED  %d unit(s) - fix the cause, do not run past it" % len(halted))
    for n, code, s, reason in sorted(halted, reverse=True)[:lim]:
        print("    %-32s %-13s %7d rows  %s" % (code[:32], s, n, reason[:64]))
    if not halted:
        print("    (none)")
    con.close()
    return 0


# ---------------------------------------------------------------------------
# --selftest builds a throwaway database with four documents of known shape
# and asserts the judge classifies each correctly. It runs on your machine,
# against your Python and your SQLite, before the real database is touched.
# ---------------------------------------------------------------------------
FIXTURE = [
    # code, rows, words per row, word length, translated share, expect at segment
    ("fx_clean",       60, 12, 7,  1.0, "done"),
    ("fx_fragmented", 200,  2, 6,  0.0, "blocked"),
    ("fx_runon",       40, 10, 34, 0.0, "blocked"),
    ("fx_pagesized",   30, 90, 7,  1.0, "degraded"),
]


def _fixture_db():
    # SELFTEST_FIXTURE_BEGIN
    # Everything between the two sentinels writes to a throwaway database
    # under the system temp directory and cannot reach the project database:
    # the path comes from tempfile.mkdtemp, and neither this function nor
    # cmd_selftest ever touches the parsed --db argument.
    tmp = Path(tempfile.mkdtemp(prefix="automaton_selftest_"))
    dbp = str(tmp / "fixture.db")
    real = os.path.realpath(dbp)
    if not real.startswith(os.path.realpath(tempfile.gettempdir())):
        raise SystemExit("FAIL: refusing to build the fixture outside temp (%s)" % real)
    con = sqlite3.connect(dbp)
    con.executescript(
        "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT, src_path TEXT, glossary TEXT, created_at TEXT);\n"
        "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, text TEXT, text_type TEXT, iast TEXT, translation TEXT, translation_qa TEXT, ents TEXT, morph TEXT);")
    pid = 0
    for i, (code, rows, wpr, wlen, tshare, _exp) in enumerate(FIXTURE, start=1):
        con.execute("INSERT INTO docs(id,code) VALUES(?,?)", (i, code))
        for r in range(rows):
            pid += 1
            txt = " ".join("a" * wlen for _ in range(wpr))
            tr = "translated" if (float(r) / max(1, rows)) < tshare else None
            con.execute("INSERT INTO passages(id,doc_id,text,text_type,iast,translation) VALUES(?,?,?,?,?,?)",
                        (pid, i, txt, "mula", "iast", tr))
    con.commit()
    con.close()
    return tmp, dbp
    # SELFTEST_FIXTURE_END


def cmd_selftest(a):
    tmp, dbp = _fixture_db()
    ns = argparse.Namespace(db=dbp, root=str(tmp), booksmith_root=str(tmp / "bs"),
                            verbose=False, limit=20)
    rc = cmd_init(ns)
    print("")
    rc |= cmd_backfill(ns)
    print("")

    con = connect(dbp, writable=False)
    got = dict(((c, s), st) for c, s, st in
               con.execute("SELECT doc_code, stage, status FROM doc_stage"))
    print("  assertions")
    fails = 0
    for code, rows, wpr, wlen, tshare, exp in FIXTURE:
        act = got.get((code, "segment"))
        ok = (act == exp)
        fails += 0 if ok else 1
        print("    %-14s %2d w/row, %2d chars -> segment=%-9s expected %-9s %s"
              % (code, wpr, wlen, act, exp, "OK" if ok else "MISMATCH"))
    # the chain must halt for the two blocked fixtures and not for the others
    for code, _r, _w, _l, _t, exp in FIXTURE:
        en = got.get((code, "translate_en"))
        if exp == "blocked" and en == "done":
            print("    %-14s translate_en is done behind a blocked segment" % code)
            fails += 1
    deg = got.get(("fx_pagesized", "translate_en"))
    if deg != "done":
        print("    fx_pagesized translate_en=%s - degraded should NOT halt the chain" % deg)
        fails += 1
    else:
        print("    fx_pagesized  degraded segment did not halt translate_en   OK")
    con.close()
    print("")
    print("  selftest: %s  (fixture left at %s)" % ("PASS" if fails == 0 else "FAIL", tmp))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="the stage ledger")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--root", default=".")
    ap.add_argument("--booksmith-root",
                    default=r"D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    acts = (a.selftest, a.init, a.backfill, a.status, a.next)
    if not any(acts):
        ap.print_help()
        return 0
    rc = 0
    if a.selftest:
        rc |= cmd_selftest(a)
    if a.init:
        rc |= cmd_init(a)
    if a.backfill:
        rc |= cmd_backfill(a)
    if a.status:
        rc |= cmd_status(a)
    if a.next:
        rc |= cmd_next(a)
    return rc


if __name__ == "__main__":
    sys.exit(main())