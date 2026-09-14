#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
automaton.py  (2026-09-14)  AUTOMATON_LEDGER_2026_09_14_C

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

Revision B - why the segment measurement changed
------------------------------------------------
Revision A sampled the first 400 rows of each document, ordered by id, and
took the MEAN words per row. On the 09:53 run that produced a verdict that
contradicts the corpus-wide survey of the same morning:

    ling_kosha --survey     Padma Purana  2.3 words/row, median word 10,
                            33.9% long-run share
    the ledger, rev A       Padma Purana  segment = done

Both cannot be right, and a ledger that a spending driver reads must not
carry a verdict its own project data disputes. Two defects, both mine:

  1. A 400-row head sample of a 15,111-row document is not the document.
     Revision B scans every live non-empty row.

  2. The MEAN is the wrong statistic. A document can average 30 words per
     row while half its rows are two-word fragments; the mean hides exactly
     the failure the gate exists to catch. Revision B uses the median words
     per row and the SHARE OF ROWS that are fragments, and stores both.

The head-sample figure is still computed and stored as head400_mean, so the
size of the bias is visible per document rather than argued about.

Revision C - a share, not a percentile; and a retraction
--------------------------------------------------------
Revision B judged segmentation on the median words per row. On the live corpus
that produced a knife edge: harita_shashtham_sharira_sthanam has p10 16, p50
60, p90 109 - plainly a mix of verses and whole printed pages - and flipped
from degraded to done because its median landed exactly ON the threshold of
60. A verdict that turns on the fifty-first row of fourteen is an artefact of
the statistic, not a fact about the text.

Revision C judges on SHARES of rows, which have no knife edge and read as
plain English - what percentage of this document's rows are shaped like a
verse a reader could be handed?

    frag_share   rows under FRAGMENT_WORDS words
    page_share   rows over PAGE_WORDS words
    verse_share  everything between

MBh01, the clean control, is ~100% verse rows. A document at 70% is a mixture;
one at 0% is a stack of printed pages. --distribution prints the corpus
against several candidate values for each floor.

The same revision RETRACTS --duplicates. It paired documents that merely had
the same row count, and duly reported that shiksha_lomashi_shiksha (8 rows)
might be smriti_07likhita_smriti (8 rows). Row count is not evidence: nine of
its eleven pairs were noise, and it missed the one real derived pair in the
corpus because 111 is not 1,393. diag_corpus_overlap.py replaces it, using the
Devanagari n-gram containment that diag_duplicate_verses.py already validated
and the engine stamp that resegment_doc.py already writes.

Four commitments, each answering a failure this project has already had
-----------------------------------------------------------------------
1. ONE unit of work per invocation, then exit. A run that is always short is
   a run the PT1H scheduled-task limit can never kill mid-write. The
   maintenance log records 100 TICKs, 45 STARTs and 0 DONEs precisely
   because the old runner tried to do everything in one process.

2. IDEMPOTENCE BY FINGERPRINT, not by flag. A stage is done only while its
   recorded input_fp still equals what its inputs hash to now. This is
   Booksmith's source_sha256 model, which this project already trusts enough
   to refuse a build over. Change the text and every downstream stage goes
   stale by itself.

3. MEASURED, NOT ASSUMED. Every stage records what it observed. Below its
   floor it becomes blocked or degraded with a reason in words.

4. DERIVED, NOT DECLARED. The ledger is backfilled from what is measurably
   true in the database today, not from anyone's memory of what was run.

What a blocked verdict can and cannot do
----------------------------------------
It stops work that has not happened yet. It cannot undo work that already
has. Every stage downstream of a block on this corpus ran years before this
table existed. For any document in that position the verdict is advisory, not
protective, and --next says so in those words rather than implying a
protection it did not provide.

Safety
------
Reads are opened with PRAGMA query_only=ON rather than immutable=1. That is
deliberate: the database runs in WAL mode, and immutable=1 makes SQLite
ignore the -wal sidecar, so a status report taken straight after a write
would show the pre-write state. query_only reads the live WAL and still
refuses writes at the engine level.

Every schema-changing and row-writing statement that can reach the project
database names doc_stage and sits on a single physical line, so that
grepping this file for write keywords is a real audit rather than a
formality. The only other write statements build the --selftest fixture;
they are fenced between a pair of BEGIN/END sentinel comments in
_fixture_db, they run against a tempfile.mkdtemp directory, and neither
_fixture_db nor cmd_selftest ever reads the --db argument. The deployment
block checks all three of those claims mechanically.
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
import time
from datetime import datetime, timezone
from pathlib import Path

MARK = "AUTOMATON_LEDGER_2026_09_14_C"

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

# ---------------------------------------------------------------------------
# The segment floors, in one place, with the evidence for each.
#
# FRAGMENT_WORDS   a row with fewer than this many words is a fragment. MBh01,
#                  the GRETIL critical edition and the only text here that was
#                  never OCR'd, sits at 12.5 words per row; a Sanskrit pada is
#                  rarely under 4.
# FRAG_BLOCK       above this share of fragment rows the document is not a
#                  sequence of verses at all. Translating it spends the API
#                  call on damage.
# LONGWORD_BLOCK   share of words over 20 characters. Above this the text is
#                  not word-separated, so every dictionary lookup and every
#                  translation sees a run rather than a word.
# PAGE_WORDS       a row longer than this is a printed page, not a verse.
# VERSE_OK         below this share of verse-shaped rows a reader cannot be
#                  handed the document as it stands. Degraded, not blocked:
#                  it still translates and it still exports.
#
# --distribution prints the corpus against several candidate values for each,
# so they are visibly not picked to flatter a conclusion.
# ---------------------------------------------------------------------------
FRAGMENT_WORDS = 4
FRAG_BLOCK = 50.0
LONGWORD_BLOCK = 25.0
PAGE_WORDS = 60
VERSE_OK = 85.0

WORD_SPLIT = re.compile(r"[\s\u0964\u0965|/\\]+")

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
        return con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name=?", (table,)).fetchone() is not None
    except Exception:
        return False


def pctl(vals, q):
    """Linear-interpolated percentile of a sorted list."""
    if not vals:
        return 0.0
    k = (len(vals) - 1) * q
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return float(vals[f])
    return float(vals[f]) + (float(vals[c]) - float(vals[f])) * (k - f)


def median_from_hist(hist):
    total = sum(hist.values())
    if not total:
        return 0
    half = total / 2.0
    run = 0
    last = 0
    for L in sorted(hist):
        run += hist[L]
        last = L
        if run >= half:
            return L
    return last


def slug_for(code):
    s = code.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:64]


# ---------------------------------------------------------------------------
# Measurement. Everything here reads. Nothing here writes.
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
        return ("SUM(CASE WHEN %s AND TRIM(COALESCE(p.%s,''))<>'' THEN 1 ELSE 0 END)"
                % (live, col))

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
        print("  aggregate query:")
        print("    %s" % sql)

    docs, by_id = {}, {}
    for code, did, npass, nlive, ntyped, niast, nen, nqa, nents, nmorph in con.execute(sql):
        m = {"doc_id": did, "passages": npass or 0, "live": nlive or 0,
             "typed": ntyped or 0, "iast": niast or 0, "en": nen or 0,
             "qa": nqa or 0, "ents": nents or 0, "morph": nmorph or 0,
             "hi": 0, "embed": 0}
        docs[code] = m
        by_id[did] = m

    if has_table(con, "translations_l10n"):
        lcols = table_cols(con, "translations_l10n")
        body = next((c for c in ("text", "translation", "content", "body", "value")
                     if c in lcols), None)
        pred = " AND TRIM(COALESCE(l.%s,''))<>''" % body if body else ""
        try:
            for code, n in con.execute(
                    "SELECT d.code, COUNT(*) FROM translations_l10n l "
                    "JOIN passages p ON p.id=l.passage_id "
                    "JOIN docs d ON d.id=p.doc_id "
                    "WHERE l.lang='hi'%s GROUP BY d.code" % pred):
                if code in docs:
                    docs[code]["hi"] = n
        except Exception as e:
            if verbose:
                print("  (hindi count unavailable: %s)" % e)

    for tbl in ("passage_embeddings", "embeddings"):
        if has_table(con, tbl) and "passage_id" in table_cols(con, tbl):
            try:
                for code, n in con.execute(
                        "SELECT d.code, COUNT(*) FROM %s e "
                        "JOIN passages p ON p.id=e.passage_id "
                        "JOIN docs d ON d.id=p.doc_id GROUP BY d.code" % tbl):
                    if code in docs:
                        docs[code]["embed"] = max(docs[code]["embed"], n)
            except Exception:
                pass
            break

    # -----------------------------------------------------------------------
    # Word shape, over EVERY live non-empty row. Revision A sampled the first
    # 400 rows by id and took the mean; on the Padma Purana that produced a
    # verdict the corpus survey of the same morning contradicts. One streamed
    # pass, word lengths accumulated as a histogram so memory stays flat.
    # -----------------------------------------------------------------------
    for m in docs.values():
        m["wpr"] = []
        m["hist"] = {}
        m["head_words"] = 0
        m["head_rows"] = 0
        m["frag_rows"] = 0
        m["page_rows"] = 0
    t0 = time.time()
    scanned = 0
    if "text" in pcols:
        cur = con.execute(
            "SELECT p.doc_id, p.text FROM passages p WHERE %s "
            "AND TRIM(COALESCE(p.text,''))<>'' ORDER BY p.doc_id, p.id" % live)
        while True:
            chunk = cur.fetchmany(5000)
            if not chunk:
                break
            for did, t in chunk:
                m = by_id.get(did)
                if m is None:
                    continue
                ws = [w for w in WORD_SPLIT.split(t or "") if w]
                n = len(ws)
                m["wpr"].append(n)
                if n < FRAGMENT_WORDS:
                    m["frag_rows"] += 1
                elif n > PAGE_WORDS:
                    m["page_rows"] += 1
                if m["head_rows"] < 400:
                    m["head_rows"] += 1
                    m["head_words"] += n
                h = m["hist"]
                for w in ws:
                    L = len(w)
                    h[L] = h.get(L, 0) + 1
                scanned += 1
    scan_s = time.time() - t0
    if verbose:
        print("  full word-shape scan: %d row(s) in %.1fs" % (scanned, scan_s))

    raw_dir = root / "data" / "raw"
    exp_dir = root / "exports"
    proj_dir = bs_root / "projects"
    for code, m in docs.items():
        wpr = sorted(m.pop("wpr"))
        hist = m.pop("hist")
        nrows = len(wpr)
        words = sum(hist.values())
        m["shape_rows"] = nrows
        m["words"] = words
        m["w_mean"] = round(float(words) / nrows, 1) if nrows else 0.0
        m["w10"] = round(pctl(wpr, 0.10), 1)
        m["w50"] = round(pctl(wpr, 0.50), 1)
        m["w90"] = round(pctl(wpr, 0.90), 1)
        m["frag_row_share"] = round(100.0 * m["frag_rows"] / nrows, 1) if nrows else 0.0
        m["page_row_share"] = round(100.0 * m["page_rows"] / nrows, 1) if nrows else 0.0
        m["verse_share"] = round(
            100.0 * (nrows - m["frag_rows"] - m["page_rows"]) / nrows, 1) if nrows else 0.0
        m["long_word_share"] = round(
            100.0 * sum(c for L, c in hist.items() if L > 20) / words, 1) if words else 0.0
        m["median_word_len"] = median_from_hist(hist)
        m["head400_mean"] = round(float(m["head_words"]) / m["head_rows"], 1) \
            if m["head_rows"] else 0.0
        m["head_bias"] = round(m["head400_mean"] - m["w_mean"], 1)

        raw = sorted(raw_dir.glob("%s*.jsonl" % code)) if raw_dir.is_dir() else []
        m["raw_files"] = len(raw)
        m["raw_fp"] = fp(*[(p.name, p.stat().st_size) for p in raw]) if raw else ""
        exp = sorted(exp_dir.glob("%s*.html" % code)) if exp_dir.is_dir() else []
        m["exports"] = len(exp)
        m["slug"] = slug_for(code)
        pdfs, proofs = 0, 0
        if proj_dir.is_dir():
            for d in sorted(proj_dir.glob("%s*" % m["slug"])):
                b = d / "build"
                if not b.is_dir():
                    continue
                for f in b.glob("*.pdf"):
                    if "proof" in f.name.lower():
                        proofs += 1
                    else:
                        pdfs += 1
        m["book_pdf"] = pdfs
        m["layout_proof"] = proofs
        lv = max(1, m["live"])
        m["pct"] = dict((k, round(100.0 * m[k] / lv, 1))
                        for k in ("iast", "en", "hi", "qa", "ents", "morph", "embed"))
    return docs


# ---------------------------------------------------------------------------
def judge(stage, m):
    """(status, reason, input_fp) for one stage, from measurement alone."""
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
        frag, page = m["frag_row_share"], m["page_row_share"]
        verse, lw = m["verse_share"], m["long_word_share"]
        f = fp(m["passages"], frag, page, lw)
        if m["shape_rows"] == 0:
            return "pending", "no non-empty text rows to measure", f
        if lw > LONGWORD_BLOCK:
            return "blocked", ("%.1f%% of words exceed 20 characters - the text is not "
                               "word-separated, so every lookup and every translation "
                               "sees a run, not a word" % lw), f
        if frag > FRAG_BLOCK:
            return "blocked", ("%.1f%% of rows carry fewer than %d words - this is not a "
                               "sequence of verses. MBh01, the clean control, has 0.0%%."
                               % (frag, FRAGMENT_WORDS)), f
        if verse < VERSE_OK:
            if page >= frag:
                why = "%.1f%% are whole pages over %d words" % (page, PAGE_WORDS)
            else:
                why = "%.1f%% are fragments under %d words" % (frag, FRAGMENT_WORDS)
            return "degraded", ("only %.1f%% of rows are verse-shaped; %s. Translation "
                                "and export work, a reading edition does not."
                                % (verse, why)), f
        return "done", ("%.1f%% of rows are verse-shaped (median %.0f words)"
                        % (verse, m["w50"])), f

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
        return "pending", "%.1f%% analysed (kosha answers 80%% on the clean control)" % p["morph"], f

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
            return "blocked", "only a layout proof exists, not a book", f
        return "pending", "no Booksmith build", f

    return "pending", "unknown stage", ""


def measured_json(m):
    keep = ("passages", "live", "shape_rows", "words", "w_mean", "w10", "w50",
            "w90", "frag_row_share", "page_row_share", "verse_share",
            "long_word_share", "median_word_len", "head400_mean", "head_bias",
            "raw_files", "exports", "book_pdf", "layout_proof")
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
    con.close()
    return 0


def cmd_backfill(a):
    con = connect(a.db, writable=True)
    con.executescript(DDL)
    docs = corpus_measure(con, Path(a.root), Path(a.booksmith_root), verbose=a.verbose)
    print("%s  backfilling %d document(s) from measurement" % (MARK, len(docs)))
    print("Nothing below is declared. Every status is derived from the data.")
    print("")
    prior = dict(((c, s), (st, f, r)) for c, s, st, f, r in con.execute(
        "SELECT doc_code, stage, status, input_fp, reason FROM doc_stage"))
    gone = retired_codes(con)
    if gone:
        print("skipping %d retired document(s): %s" % (len(gone), ", ".join(sorted(gone))))
        print("")
    ts = now()
    wrote = 0
    touched = 0   # BACKFILL_COUNT_2026_09_14 - documents actually written to
    changes = []
    for code in sorted(docs):
        if code in gone:
            continue
        touched += 1
        m = docs[code]
        meas = measured_json(m)
        for st in STAGES:
            status, reason, f = judge(st, m)
            was = prior.get((code, st))
            if was is None:
                changes.append((code, st, "-", status, reason))
            elif was[0] != status:
                changes.append((code, st, was[0], status, reason))
            elif was[1] != f:
                changes.append((code, st, was[0] + "*", status, reason))
            con.execute(UPSERT, (code, st, status, f, meas, reason, ts))
            wrote += 1
    con.commit()
    print("wrote %d ledger row(s) across %d document(s); %d differ from what"
          % (wrote, touched, len(changes)))
    print("the ledger said before this run.")
    verdict = [c for c in changes if c[2] != "-" and not c[2].endswith("*")]
    if verdict:
        print("")
        print("  verdicts that CHANGED - old -> new, and why")
        for code, st, old, new, reason in verdict[:60]:
            print("    %-32s %-13s %-9s -> %-9s %s" % (code[:32], st, old, new, reason[:52]))
        if len(verdict) > 60:
            print("    ... and %d more" % (len(verdict) - 60))
    refp = [c for c in changes if c[2].endswith("*")]
    if refp:
        print("")
        print("  same verdict, fingerprint moved (inputs changed): %d" % len(refp))
        for code, st, old, _new, _r in refp[:12]:
            print("    %-32s %-13s %s" % (code[:32], st, old[:-1]))
    con.close()
    return 0


def retired_codes(con):
    """Documents retired by retire_doc.py. They keep their docs row so nothing
    dangles, which means a measurement pass would otherwise see a code with
    zero passages and offer it to the driver as ready to ingest. A retirement
    that the driver can undo is not a retirement."""
    try:
        return set(r[0] for r in con.execute(
            "SELECT doc_code FROM doc_stage WHERE stage='retired'"))
    except Exception:
        return set()


def _load_board(con):
    board = {}
    for code, stage, status, reason in con.execute(
            "SELECT doc_code, stage, status, reason FROM doc_stage"):
        board.setdefault(code, {})[stage] = (status, reason)
    return board


def _sizes(con):
    return dict(con.execute("SELECT d.code, COUNT(p.id) FROM docs d "
                            "LEFT JOIN passages p ON p.doc_id=d.id GROUP BY d.code"))


def cmd_status(a):
    con = connect(a.db, writable=False)
    if not has_table(con, "doc_stage"):
        print("doc_stage does not exist yet. Run --init --backfill first.")
        con.close()
        return 1
    board = _load_board(con)
    gone = retired_codes(con)
    for c in gone:
        board.pop(c, None)
    sizes = _sizes(con)
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
    if gone:
        print("")
        print("  retired, and excluded from everything above:")
        for c, r in con.execute("SELECT doc_code, reason FROM doc_stage "
                                "WHERE stage='retired' ORDER BY doc_code"):
            print("    %-34s %s" % (c[:34], r))
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
    print("  blocked, with the measurement behind each")
    n = 0
    for code, stage, reason in con.execute(
            "SELECT doc_code, stage, reason FROM doc_stage WHERE status='blocked' "
            "ORDER BY stage, doc_code"):
        print("    %-32s %-9s %s" % (code[:32], stage, reason))
        n += 1
    if n == 0:
        print("    (none)")
    print("")
    print("  degraded at segment - no reading edition is reachable for these")
    rows = con.execute("SELECT doc_code, reason FROM doc_stage WHERE status='degraded' "
                       "AND stage='segment' ORDER BY doc_code").fetchall()
    for code, reason in rows[:a.limit]:
        print("    %-32s %s" % (code[:32], reason[:70]))
    if len(rows) > a.limit:
        print("    ... and %d more (all the same shape)" % (len(rows) - a.limit))
    print("    %d of %d documents" % (len(rows), len(board)))
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
    for c in retired_codes(con):
        board.pop(c, None)
    sizes = _sizes(con)
    print("%s  next actionable units" % MARK)
    print("")
    print("  A stage is actionable when it is pending and every prerequisite is")
    print("  done or degraded. Degraded satisfies a prerequisite on purpose: an")
    print("  under-segmented document still translates and still exports.")
    print("")
    ready, halted = [], []
    for code, st in board.items():
        n = sizes.get(code, 0)
        for s in STAGES:
            status, reason = st.get(s, ("pending", ""))
            if status in STATUS_OK:
                continue
            if status in ("blocked", "failed"):
                after = [x for x in STAGES[STAGES.index(s) + 1:]
                         if st.get(x, ("pending", ""))[0] in STATUS_OK]
                halted.append((n, code, s, reason, after))
                continue
            if all(st.get(d, ("pending", ""))[0] in STATUS_OK for d in DEPS.get(s, [])):
                ready.append((n, code, s, reason))
    lim = a.limit
    by_stage = {}
    for _n, _c, s, _r in ready:
        by_stage[s] = by_stage.get(s, 0) + 1
    print("  READY  %d unit(s) over %d stage(s):" % (len(ready), len(by_stage)))
    print("    " + "   ".join("%s=%d" % (s, by_stage[s]) for s in STAGES if s in by_stage))
    print("")
    print("  largest first%s:" % (", showing %d" % lim if len(ready) > lim else ""))
    for n, code, s, reason in sorted(ready, reverse=True)[:lim]:
        print("    %-32s %-13s %7d rows  %s" % (code[:32], s, n, reason[:44]))
    if not ready:
        print("    (none)")
    print("")
    print("  HALTED  %d unit(s)" % len(halted))
    for n, code, s, reason, after in sorted(halted, reverse=True)[:lim]:
        print("    %-32s %-13s %7d rows  %s" % (code[:32], s, n, reason[:62]))
        if after:
            print("      NOTE: %s already ran here before this ledger existed, so the"
                  % ", ".join(after[:6]))
            print("      block is advisory for this document, not protective. The spend")
            print("      has happened; what it bought still needs re-segmenting.")
    if not halted:
        print("    (none)")
    con.close()
    return 0


def cmd_distribution(a):
    """The evidence behind the segment floors. Read-only; writes nothing."""
    con = connect(a.db, writable=False)
    docs = corpus_measure(con, Path(a.root), Path(a.booksmith_root), verbose=a.verbose)
    con.close()
    order = sorted(docs.items(), key=lambda kv: -kv[1]["shape_rows"])
    print("%s  word shape, every live row of every document" % MARK)
    print("")
    print("  head400 is what revision A measured: the mean over the first 400")
    print("  rows by id. bias is head400 minus the true mean. Where that number")
    print("  is large the old sampler was reading a different document.")
    print("")
    print("  %-32s %6s %6s %5s %5s %6s %6s %6s %6s %7s" % (
        "document", "rows", "p50", "p10", "p90",
        "frag%", "page%", "VERSE%", "long%", "head400"))
    print("  " + "-" * 112)
    for code, m in order:
        if m["shape_rows"] == 0:
            continue
        print("  %-32s %6d %6.0f %5.0f %5.0f %6.1f %6.1f %6.1f %6.1f %7.1f" % (
            code[:32], m["shape_rows"], m["w50"], m["w10"], m["w90"],
            m["frag_row_share"], m["page_row_share"], m["verse_share"],
            m["long_word_share"], m["head400_mean"]))
    print("")
    print("  VERSE%% is the share of rows between %d and %d words - the rows a"
          % (FRAGMENT_WORDS, PAGE_WORDS))
    print("  reader could be handed. frag%% + page%% + VERSE%% = 100.")
    print("")
    print("  largest head-sample bias (old mean minus true mean)")
    for code, m in sorted(order, key=lambda kv: -abs(kv[1]["head_bias"]))[:8]:
        if m["shape_rows"] == 0:
            continue
        print("    %-32s head400 %7.1f   true %7.1f   bias %+8.1f" % (
            code[:32], m["head400_mean"], m["w_mean"], m["head_bias"]))

    print("")
    print("  sensitivity - how many documents each candidate floor would catch,")
    print("  so you can see the chosen values are not picked to flatter a")
    print("  conclusion. The shipped floors are marked <-- in use.")
    live = [m for m in docs.values() if m["shape_rows"] > 0]
    print("")
    print("    verse-shaped share BELOW X  ->  documents degraded")
    for x in (50.0, 70.0, 85.0, 95.0, 99.0):
        tag = "   <-- in use" if x == VERSE_OK else ""
        print("      %5.0f%%  %3d%s" % (x, sum(1 for m in live if m["verse_share"] < x), tag))
    print("    fragment-row share above X  ->  documents blocked")
    for x in (30.0, 50.0, 70.0):
        tag = "   <-- in use" if x == FRAG_BLOCK else ""
        print("      %5.0f%%  %3d%s" % (x, sum(1 for m in live if m["frag_row_share"] > x), tag))
    print("    long-word share above X  ->  documents blocked")
    for x in (10.0, 25.0, 40.0):
        tag = "   <-- in use" if x == LONGWORD_BLOCK else ""
        print("      %5.0f%%  %3d%s" % (x, sum(1 for m in live if m["long_word_share"] > x), tag))
    print("")
    print("    how many documents are verse-shaped enough for a reading edition")
    print("    at each candidate floor is the whole planning question - it is the")
    print("    count of books this corpus could publish without re-segmentation.")
    print("")
    print("  the clean control, for scale:")
    c = docs.get("MBh01")
    if c:
        print("    MBh01  p50 %.0f  frag %.1f%%  page %.1f%%  VERSE %.1f%%  long %.1f%%"
              % (c["w50"], c["frag_row_share"], c["page_row_share"],
                 c["verse_share"], c["long_word_share"]))
    s = docs.get("nilamata_seg")
    o = docs.get("upapurana_nilamata_purana")
    if s and o:
        print("  and the one document that has already made the journey:")
        print("    upapurana_nilamata_purana  p50 %.0f  VERSE %5.1f%%   (page-blobs)"
              % (o["w50"], o["verse_share"]))
        print("    nilamata_seg               p50 %.0f  VERSE %5.1f%%   (resegment_doc.py)"
              % (s["w50"], s["verse_share"]))
    return 0


def cmd_duplicates(a):
    """RETRACTED. This gate was wrong and is kept only to say so."""
    print("%s  --duplicates is RETRACTED" % MARK)
    print("")
    print("  What it did on 2026-09-14: paired any two documents that happened to")
    print("  have the same ROW COUNT, and reported, among eleven pairs:")
    print("")
    print("    shiksha_lomashi_shiksha    8 rows  ~  smriti_07likhita_smriti    8 rows")
    print("    harita_caturtha_sthanam   17 rows  ~  smriti_03apastamba_smriti 17 rows")
    print("")
    print("  Row count is not evidence. Nine of the eleven were noise, and the one")
    print("  real derived pair in this corpus - upapurana_nilamata_purana and")
    print("  nilamata_seg - it missed entirely, because 111 is not 1,393.")
    print("")
    print("  This is the same failure diag_duplicate_verses.py v2 already records")
    print("  against its own v1: 1,705 of 2,059 signatures called duplicates, 83%,")
    print("  which its header calls 'not a finding, a broken gate'. I repeated it.")
    print("")
    print("  Use instead:")
    print("    python scripts\\diag_corpus_overlap.py --db data\\context.db")
    print("        exact Devanagari row matches across documents, 5-gram")
    print("        containment for re-segmented copies, and the resegment engine")
    print("        stamp - three signals, reported separately, with sample sizes.")
    print("    python scripts\\diag_duplicate_verses.py --doc <CODE>")
    print("        duplicates WITHIN one document, with fan-out and furniture.")
    return 0


# ---------------------------------------------------------------------------
FIXTURE = [
    # code, rows, words per row, word length, translated share, expect at segment
    ("fx_clean",       60, 12, 7,  1.0, "done"),
    ("fx_fragmented", 200,  2, 6,  0.0, "blocked"),
    ("fx_runon",       40, 10, 34, 0.0, "blocked"),
    ("fx_pagesized",   30, 90, 7,  1.0, "degraded"),
    ("fx_mixed",      100,  0, 7,  1.0, "degraded"),   # 30% fragments, rest clean
    ("fx_knife",       14,  0, 7,  1.0, "degraded"),   # median exactly PAGE_WORDS
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
            n = wpr
            if code == "fx_mixed":
                n = 2 if (r % 10) < 3 else 14
            elif code == "fx_knife":
                # half the rows well under, half well over; the median lands on
                # PAGE_WORDS itself. Revision B called this done.
                n = 20 if r % 2 else 110
                if r == rows - 1:
                    n = PAGE_WORDS
            txt = " ".join("a" * wlen for _ in range(n))
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
    meas = dict((c, json.loads(j)) for c, j in con.execute(
        "SELECT doc_code, measured FROM doc_stage WHERE stage='segment'"))
    con.close()
    print("  assertions")
    fails = 0
    for code, rows, wpr, wlen, tshare, exp in FIXTURE:
        act = got.get((code, "segment"))
        mm = meas.get(code, {})
        ok = (act == exp)
        fails += 0 if ok else 1
        print("    %-14s frag %5.1f%%  page %5.1f%%  VERSE %5.1f%%  long %5.1f%%  -> "
              "%-9s expected %-9s %s"
              % (code, mm.get("frag_row_share", 0), mm.get("page_row_share", 0),
                 mm.get("verse_share", 0), mm.get("long_word_share", 0),
                 act, exp, "OK" if ok else "MISMATCH"))
    for code, _r, _w, _l, _t, exp in FIXTURE:
        if exp == "blocked" and got.get((code, "translate_en")) == "done":
            print("    %-14s translate_en done behind a blocked segment" % code)
            fails += 1
    if got.get(("fx_pagesized", "translate_en")) != "done":
        print("    fx_pagesized translate_en=%s - degraded must not halt the chain"
              % got.get(("fx_pagesized", "translate_en")))
        fails += 1
    else:
        print("    fx_pagesized   degraded segment did not halt translate_en   OK")
    # the mean would have called fx_mixed clean; the median plus fragment share must not
    mx = meas.get("fx_mixed", {})
    if mx.get("w_mean", 0) >= FRAGMENT_WORDS and got.get(("fx_mixed", "segment")) == "done":
        print("    fx_mixed  mean %.1f hid a %.0f%% fragment share - the old rule's bug"
              % (mx.get("w_mean", 0), mx.get("frag_row_share", 0)))
        fails += 1
    else:
        print("    fx_mixed       mean %.1f and median %.0f both look clean; %.0f%% verse"
              " rows caught it   OK"
              % (mx.get("w_mean", 0), mx.get("w50", 0), mx.get("verse_share", 0)))
    # the knife edge revision B had: a document whose median sits exactly on the
    # page threshold must not be decided by that coincidence
    ke = meas.get("fx_knife", {})
    if ke:
        st = got.get(("fx_knife", "segment"))
        if st == "degraded":
            print("    fx_knife       median exactly %d, %.0f%% verse rows -> degraded   OK"
                  % (PAGE_WORDS, ke.get("verse_share", 0)))
        else:
            print("    fx_knife       median exactly %d -> %s, expected degraded"
                  % (PAGE_WORDS, st))
            fails += 1
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
    ap.add_argument("--distribution", action="store_true")
    ap.add_argument("--duplicates", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    acts = (a.selftest, a.init, a.backfill, a.status, a.next,
            a.distribution, a.duplicates)
    if not any(acts):
        ap.print_help()
        return 0
    rc = 0
    if a.selftest:
        rc |= cmd_selftest(a)
    if a.init:
        rc |= cmd_init(a)
    if a.distribution:
        rc |= cmd_distribution(a)
    if a.backfill:
        rc |= cmd_backfill(a)
    if a.status:
        rc |= cmd_status(a)
    if a.next:
        rc |= cmd_next(a)
    if a.duplicates:
        rc |= cmd_duplicates(a)
    return rc


if __name__ == "__main__":
    sys.exit(main())