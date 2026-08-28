#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_noise.py - tag OCR fragments (page furniture, running heads, stray marks) as
text_type='noise', so they stop inflating the untranslated count. (2026-08-28)

Examples this catches, all seen in AphorismsOfSandilya:
    "।"                                  (a bare dandas)
    "Ind । . 212, 35"                    (a running head + page ref)
    "0 011९1 . JAS 181... 0$ 1939 क् ।"  (catalogue junk)

DELIBERATELY CONSERVATIVE - a passage is noise only when it has almost no real content:
fewer than `--min-dev` Devanagari letters AND fewer than `--min-lat` Latin letters. A
genuine short verse ("ॐ नमः शिवाय") has plenty of Devanagari and is never touched.

SAFE: dry-run by default; only considers passages with NO stored translation; never
re-tags something already 'frontmatter'/'noise'. Reversible (set text_type back to
'mula'). Writes via db_utils.connect (WAL + busy_timeout); run with the dashboard idle.

  python scripts/classify_noise.py                       # preview all docs
  python scripts/classify_noise.py --doc AphorismsOfSandilya --show
  python scripts/classify_noise.py --apply
"""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import connect as _connect


def content_counts(s: str) -> tuple[int, int]:
    """(devanagari_letters, latin_letters) - the only things that carry meaning.
    Devanagari DIGITS (U+0966-U+096F) and the DANDAS (U+0964 danda, U+0965 double
    danda) are excluded: a page number like '५४०७' and verse punctuation are furniture,
    not content. Counting them hid catalogue junk from the filter."""
    return (len(re.findall(r"[ऀ-ॣ॰-ॿ]", s or "")),
            len(re.findall(r"[A-Za-z]", s or "")))


def is_noise(s: str, min_dev: int, min_lat: int) -> bool:
    dev, lat = content_counts(s)
    return dev < min_dev and lat < min_lat


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--min-dev", type=int, default=3, help="fewer than this many Devanagari letters (default 3)")
    ap.add_argument("--min-lat", type=int, default=10, help="AND fewer than this many Latin letters (default 10)")
    ap.add_argument("--show", action="store_true", help="print a sample of what would be tagged")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = _connect(args.db)
    if "text_type" not in {r[1] for r in con.execute("PRAGMA table_info(passages)")}:
        print("passages has no text_type column; nothing to do."); con.close(); return

    where = ("WHERE TRIM(COALESCE(p.translation,''))='' "
             "AND COALESCE(p.text_type,'mula') NOT IN ('frontmatter','noise')")
    params = []
    if args.doc:
        where += " AND d.code=?"; params.append(args.doc)
    rows = con.execute(
        f"SELECT p.id, d.code, p.text FROM passages p JOIN docs d ON d.id=p.doc_id {where}",
        params).fetchall()

    hits = [(pid, code, text) for pid, code, text in rows if is_noise(text or "", args.min_dev, args.min_lat)]
    by = {}
    for _, code, _ in hits:
        by[code] = by.get(code, 0) + 1

    print(f"OCR fragments to tag as 'noise'  ({'APPLY' if args.apply else 'DRY-RUN'}; "
          f"dev<{args.min_dev} AND lat<{args.min_lat}):")
    if not hits:
        print("  none found."); con.close(); return
    for code, n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {code}: {n}")
    print(f"Total: {len(hits)}")

    if args.show:
        print("\nsample (first 15):")
        for _, code, text in hits[:15]:
            flat = " ".join((text or "").split())[:70]
            print(f"  [{code[:22]:22s}] {flat!r}")

    if not args.apply:
        print("\nDRY-RUN. Inspect with --show, then re-run with --apply. Reversible.")
        con.close(); return

    con.executemany("UPDATE passages SET text_type='noise' WHERE id=?", [(pid,) for pid, _, _ in hits])
    con.commit(); con.close()
    print(f"\nTagged {len(hits)} passages as 'noise'. Coverage now counts real verses only.")


if __name__ == "__main__":
    main()
