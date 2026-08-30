#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_ocr_engine.py - which engine produced each line? (2026-08-30)  READ-ONLY.

Reads passages.ocr_engine, the provenance column added when the OCR standard was
settled (RUNBOOK 3d). Exists as a script because the equivalent PowerShell
one-liner is a nested-quote minefield and failed three times running.

Answers:
  1. Corpus-wide engine mix, and how much text still has no provenance at all
     (anything ingested before 2026-08-30 - not an error, just unknown).
  2. Per-document mix, so a book that is quietly 100% Tesseract is visible.
  3. The tesseract-fallback rows specifically: pages where vision failed and
     Tesseract was used instead. Those carry KNOWN-weaker text - measured at
     34-73% of achievable word accuracy - and are the natural queue for a
     later re-OCR attempt.

  python scripts\\diag_ocr_engine.py
  python scripts\\diag_ocr_engine.py --doc 2015_405693_Shatpath-Brahmanam
"""
from __future__ import annotations
import argparse, sqlite3, sys


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    args = ap.parse_args()

    # NOT mode=ro: a read-only URI cannot attach to the -wal of a database another
    # process is writing, and fails with a bare "disk I/O error".
    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")

    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "ocr_engine" not in cols:
        sys.exit("passages.ocr_engine does not exist yet - run an ingest first "
                 "(the column is added automatically).")

    where, params = "d.code NOT LIKE '%-RETIRED'", []
    if args.doc:
        where, params = "d.code = ?", [args.doc]

    print("=" * 70)
    print("OCR PROVENANCE" + (f": {args.doc}" if args.doc else " (corpus)"))
    print("=" * 70)
    rows = con.execute(
        f"""SELECT COALESCE(p.ocr_engine,'(unrecorded)'), COUNT(*)
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE {where} GROUP BY 1 ORDER BY 2 DESC""", params).fetchall()
    total = sum(n for _, n in rows) or 1
    for eng, n in rows:
        bar = "#" * int(40 * n / total)
        print(f"  {str(eng)[:34]:34s} {n:>7,} ({100.0*n/total:5.1f}%) {bar}")
    print(f"  {'TOTAL':34s} {total:>7,}")

    unrec = dict((str(e), n) for e, n in rows).get("(unrecorded)", 0)
    if unrec:
        print(f"\n  {unrec:,} passages predate the provenance column. Not an error -")
        print("  they simply were not recorded. They resolve as each book is re-ingested.")

    if not args.doc:
        print("\n" + "=" * 70)
        print("BY DOCUMENT (documents with any recorded provenance)")
        print("=" * 70)
        docs = con.execute(
            """SELECT d.code,
                      SUM(CASE WHEN p.ocr_engine LIKE 'gemini-vision%' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN p.ocr_engine = 'tesseract-fallback' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN p.ocr_engine IS NULL THEN 1 ELSE 0 END),
                      COUNT(*)
               FROM passages p JOIN docs d ON d.id = p.doc_id
               WHERE d.code NOT LIKE '%-RETIRED'
               GROUP BY d.code HAVING SUM(CASE WHEN p.ocr_engine IS NOT NULL THEN 1 ELSE 0 END) > 0
               ORDER BY 3 DESC, 1""").fetchall()
        if not docs:
            print("  none yet - re-ingest a document to populate it.")
        else:
            print(f"  {'document':44s} {'vision':>7} {'fallbk':>7} {'unrec':>7}")
            print("  " + "-" * 68)
            for code, v, f, u, t in docs:
                print(f"  {code[:44]:44s} {v:>7,} {f:>7,} {u:>7,}")

    print("\n" + "=" * 70)
    print("TESSERACT-FALLBACK ROWS (known-weaker text, queue for re-OCR)")
    print("=" * 70)
    fb = con.execute(
        f"""SELECT d.code, p.page_no, COUNT(*)
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE {where} AND p.ocr_engine = 'tesseract-fallback'
            GROUP BY d.code, p.page_no ORDER BY d.code, p.page_no""", params).fetchall()
    if not fb:
        print("  none - every recorded passage came from vision.")
    else:
        for code, pg, n in fb:
            print(f"  {code[:44]:44s} page {pg:>4}  {n:>3} passage(s)")
        print(f"\n  {len(fb)} page(s), {sum(r[2] for r in fb)} passage(s).")
        print("  Vision failed on these; Tesseract text was used so the book has no hole.")
        print("  Re-try one with:")
        print("    python scripts\\ocr_vision.py --pdf inbox\\<CODE>_<PAGE>.pdf "
              "--out data\\raw_vision\\<CODE>_<PAGE>.jsonl --doc <CODE> --yes")
    con.close()


if __name__ == "__main__":
    main()
