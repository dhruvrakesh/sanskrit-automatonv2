#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_variants.py - the apparatus criticus, as data. (2026-08-30)  READ-ONLY.

Where Tesseract and vision read the same scan differently. Vision is the source
of record because it is right roughly eight times in nine, but the losing
reading is kept (passages.ocr_variants) so nothing is silently discarded - on a
sampled page Tesseract carried the correct reading for तरुण (vision: the
non-word तरुश), उषितं (उपितं) and अथातः (अथवातः).

Exists as a script because the equivalent PowerShell one-liner failed four
separate times on nested quoting. Inline python -c with SQL in it is a trap on
Windows; put it in a file.

  python scripts\\diag_variants.py
  python scripts\\diag_variants.py --doc 2015_405693_Shatpath-Brahmanam --show 20
  python scripts\\diag_variants.py --doc <CODE> --page 42
"""
from __future__ import annotations
import argparse, collections, json, sqlite3, sys


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--page", type=int, default=None)
    ap.add_argument("--show", type=int, default=12, help="sample variants to print")
    args = ap.parse_args()

    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "ocr_variants" not in cols:
        sys.exit("passages.ocr_variants does not exist - re-ingest a merged doc first.")

    where = ["p.ocr_variants IS NOT NULL", "d.code NOT LIKE '%-RETIRED'"]
    params = []
    if args.doc:
        where.append("d.code = ?"); params.append(args.doc)
    if args.page is not None:
        where.append("p.page_no = ?"); params.append(args.page)

    rows = con.execute(
        f"""SELECT d.code, p.page_no, p.verse_ref, p.ocr_variants, p.text,
                   COALESCE(p.ocr_engine,'')
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE {' AND '.join(where)}""", params).fetchall()
    con.close()
    if not rows:
        sys.exit("no passages carry variants yet.")

    parsed = []
    for code, pg, vref, raw, text, eng in rows:
        try:
            v = json.loads(raw)
        except Exception:
            continue
        if v:
            parsed.append((code, pg, vref, v, text, eng))
    total = sum(len(v) for *_x, v, _t, _e in [(a,b,c,d,e,f) for a,b,c,d,e,f in parsed])

    print("=" * 74)
    print("ENGINE DISAGREEMENTS" + (f": {args.doc}" if args.doc else " (corpus)"))
    print("=" * 74)
    print(f"  passages carrying variants : {len(parsed):,}")
    print(f"  total variant readings     : {total:,}")
    print(f"  mean per passage           : {total/max(len(parsed),1):.1f}")

    print("\n  by document:")
    per = collections.Counter()
    perp = collections.Counter()
    for code, pg, vref, v, text, eng in parsed:
        per[code] += len(v); perp[code] += 1
    for code, n in per.most_common(12):
        print(f"    {code[:44]:44s} {n:>7,} variants across {perp[code]:>5,} passages")

    print("\n  similarity distribution (how close the two readings are):")
    band = collections.Counter()
    for *_a, v, _t, _e in [(a,b,c,d,e,f) for a,b,c,d,e,f in parsed]:
        for d in v:
            s = d.get("sim") or 0
            band[f"{int(s*10)/10:.1f}"] += 1
    for k in sorted(band):
        n = band[k]
        print(f"    {k}-{float(k)+0.1:.1f}  {'#'*min(50,n//max(1,total//400))} {n:,}")
    print("    Higher similarity = a one-character OCR difference, the classic")
    print("    confusion pair. Lower = the engines read genuinely different words.")

    print("\n" + "=" * 74)
    print("SAMPLE (tesseract -> vision, as the reader shows on hover)")
    print("=" * 74)
    shown = 0
    for code, pg, vref, v, text, eng in sorted(parsed, key=lambda r: -len(r[3])):
        print(f"\n  {code[:40]} page {pg} {vref or ''}  [{eng or 'unrecorded'}]  "
              f"{len(v)} variant(s)")
        for d in v[: max(1, args.show // 3)]:
            print(f"      {str(d.get('t'))[:30]:30s} -> {str(d.get('v'))[:30]:30s} "
                  f"sim={d.get('sim')}")
        shown += 1
        if shown * 3 >= args.show:
            break

    print("\n  NOT YET DONE: nothing adjudicates these. A third opinion on the")
    print("  disputed token alone would be cheap - they are a small fraction of the")
    print("  text - and is the natural next step. Until then the reader shows both")
    print("  readings and lets a human decide, which is the honest state.")


if __name__ == "__main__":
    main()
