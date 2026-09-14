#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_resegment_yield.py - what would resegment_doc.py recover, per document?
v1, 2026-09-14.

READ-ONLY. Writes nothing, calls no API, touches no document.
Run it on WINDOWS - SQLite over the Claude device bridge fails with
'disk I/O error' because the -shm lock file cannot be mapped.

THE CONSTRAINT THIS MEASURES
----------------------------
The stage ledger says 39 of 60 documents are degraded at segment: whole printed
pages arrived as a single passage, median 100 to 148 words per row against
MBh01's 12. Those documents translate and export perfectly well. What they
cannot become is a reading edition - Booksmith refuses a source it judges
under-segmented, and a reader handed a 140-word block is not being handed a
verse.

That is the real distance between this corpus and "trilingual texts of the kind
users want to read", and it is a bigger distance than translation coverage:
translation is done on 22 of 60 documents, readable segmentation on 17.

THE TOOL ALREADY EXISTS AND HAS ALREADY WORKED
----------------------------------------------
resegment_doc.py was written on 2026-08-02 for exactly this shape, and the
corpus carries its result: upapurana_nilamata_purana, 111 page-blobs at a
median of 137 words per row, became nilamata_seg, 1,393 verses at a median of
9, which is translated into English and Hindi, exported, and has a Booksmith
build. One document has already made the whole journey.

So the open question is not "how do we fix this", it is "on which of the other
38 does the same splitter work". This file answers that, for free, before any
document is touched.

HOW
---
It imports split_verses() and _frac_dev() FROM resegment_doc.py rather than
copying them, so what is measured here is exactly the code that would run. For
each document it reports the page-blob shape now, the verses the splitter finds,
how many survive the Devanagari-fraction gate, and the median words per row
that would result - the number that decides whether a reading edition becomes
reachable.

WHAT IT CANNOT TELL YOU
-----------------------
The splitter keys on a trailing Devanagari sloka-number. A text printed without
them will yield one verse per page, and this report will show that plainly as a
ratio near 1.0. That is a true answer, not a failure: it means that document
needs a different splitter (danda-based, as in segment_verses.py) or a
different source, and it should not be put through this one.

Nothing is adopted here. resegment_doc.py is non-destructive by design - it
writes new JSONL under a NEW doc code and never touches the source - and its
own docstring says to "ingest the output as a NEW doc, translate it, compare,
and only then adopt it as canonical". Adoption is a decision. This is evidence.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from resegment_doc import split_verses, _frac_dev
except Exception as e:  # pragma: no cover
    sys.exit("cannot import resegment_doc.py from %s: %s" % (HERE, e))

MARK = "RESEGMENT_YIELD_2026_09_14"
WORD_SPLIT = re.compile("[\\s\u0964\u0965|/\\\\]+")


def words(t):
    return [w for w in WORD_SPLIT.split(t or "") if w]


def median(v):
    if not v:
        return 0.0
    v = sorted(v)
    n = len(v)
    return float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", action="append", default=None,
                    help="limit to these doc codes; repeatable")
    ap.add_argument("--from-ledger", action="store_true",
                    help="take the document list from doc_stage where segment "
                         "is degraded or blocked")
    ap.add_argument("--min-dev", type=float, default=0.4,
                    help="same gate resegment_doc.py applies (default 0.4)")
    ap.add_argument("--min-rows", type=int, default=1)
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit("not found: %s - run from the repo root" % a.db)
    con = sqlite3.connect("file:%s?mode=ro" % a.db.replace("\\", "/"), uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")

    if a.doc:
        codes = list(a.doc)
        src = "--doc"
    elif a.from_ledger:
        try:
            codes = [r[0] for r in con.execute(
                "SELECT doc_code FROM doc_stage WHERE stage='segment' "
                "AND status IN ('degraded','blocked') ORDER BY doc_code")]
            src = "doc_stage (degraded or blocked at segment)"
        except Exception:
            sys.exit("doc_stage not present - run automaton.py --init --backfill, "
                     "or pass --doc")
    else:
        codes = [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code")]
        src = "every document"

    print("%s  what the existing splitter would recover" % MARK)
    print("document list from: %s  (%d document(s))" % (src, len(codes)))
    print("imported split_verses() from %s" % os.path.join(HERE, "resegment_doc.py"))
    print("")
    print("  %-32s %6s %7s %8s %7s %7s %7s  %s" % (
        "document", "rows", "med now", "verses", "kept", "med aft", "x", "verdict"))
    print("  " + "-" * 118)

    rows_out = []
    for code in codes:
        r = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
        if not r:
            continue
        did = r[0]
        blobs = con.execute(
            "SELECT text FROM passages WHERE doc_id=? AND text IS NOT NULL "
            "AND COALESCE(text_type,'mula') NOT IN ('noise','frontmatter') "
            "ORDER BY page_no, idx", (did,)).fetchall()
        if len(blobs) < a.min_rows:
            continue
        now = [len(words(t)) for (t,) in blobs if (t or "").strip()]
        found = kept = dropped = 0
        after = []
        for (t,) in blobs:
            for v in split_verses(t or ""):
                found += 1
                txt = v["text"]
                if _frac_dev(txt) < a.min_dev or len(txt.strip()) < 4:
                    dropped += 1
                    continue
                kept += 1
                after.append(len(words(txt)))
        mn, ma = median(now), median(after)
        ratio = (float(kept) / len(blobs)) if blobs else 0.0
        if kept == 0:
            verdict = "splitter finds nothing - needs a different one"
        elif ratio < 1.5:
            verdict = "no real split - text has no trailing sloka numbers"
        elif ma == 0:
            verdict = "everything dropped by the Devanagari gate"
        elif ma <= 60 and mn > 60:
            verdict = "RECOVERS a reading edition"
        elif ma < mn * 0.6:
            verdict = "improves, still not verse-shaped"
        else:
            verdict = "little change"
        print("  %-32s %6d %7.0f %8d %7d %7.0f %6.1fx  %s" % (
            code[:32], len(blobs), mn, found, kept, ma, ratio, verdict))
        rows_out.append((code, len(blobs), mn, found, kept, ma, ratio, verdict))

    print("  " + "-" * 118)
    win = [r for r in rows_out if r[7] == "RECOVERS a reading edition"]
    part = [r for r in rows_out if r[7] == "improves, still not verse-shaped"]
    none = [r for r in rows_out if r[7].startswith(("no real split", "splitter finds"))]
    print("")
    print("  %d document(s) would become verse-shaped by running the EXISTING tool"
          % len(win))
    if win:
        tot = sum(r[4] for r in win)
        src_rows = sum(r[1] for r in win)
        print("     %d page-blobs -> %d verses" % (src_rows, tot))
        print("     " + ", ".join(r[0] for r in win[:12]) + (" ..." if len(win) > 12 else ""))
    print("  %d would improve but not reach verse shape" % len(part))
    print("  %d have no trailing sloka numbers - a different splitter or source"
          % len(none))
    print("")
    print("  For any single document, the next step is the tool's own dry run,")
    print("  which prints the first verses it would emit so you can read them:")
    if win:
        print("     python scripts\\resegment_doc.py --src-doc %s \\" % win[0][0])
        print("            --new-doc %s_seg --dry-run" % win[0][0])
    print("")
    print("  Adopting a re-segmented copy is a separate decision with a cost:")
    print("  upapurana_nilamata_purana and nilamata_seg are BOTH translated, which")
    print("  is what happens when the compare-then-adopt step in resegment_doc.py's")
    print("  workflow is never closed out. Run diag_corpus_overlap.py before")
    print("  translating any new segmented copy.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())