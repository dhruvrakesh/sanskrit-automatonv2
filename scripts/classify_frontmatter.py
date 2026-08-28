#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_frontmatter.py - tag coherent-English SOURCE passages (book title pages,
editorial prefaces, publisher front-matter) as text_type='frontmatter', so they are
excluded from translation-coverage and QA counts instead of masquerading as untranslated
Sanskrit verses. (2026-08-28)

Mirrors the reader's looksEnglish() heuristic exactly, so the UI label and the data tag
agree. SAFE: dry-run by default; only tags passages whose SOURCE reads as English AND
that have NO stored English translation (so a real translated verse is never touched);
never overwrites an existing 'frontmatter'/'noise' tag. Reversible (set text_type back).
Writes via db_utils.connect (WAL + busy_timeout); run with the dashboard idle.

  python scripts/classify_frontmatter.py                 # preview all docs
  python scripts/classify_frontmatter.py --doc AphorismsOfSandilya
  python scripts/classify_frontmatter.py --apply
"""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import connect as _connect

_WORDS = [" the "," of "," and "," to "," in "," is "," was "," this "," that ",
          " with "," by "," for "," as "," which "," work "," published "," edited ",
          " commentary "," following "," printed "," society "," college "," preface ",
          " aphorisms "," oriental "," collection "]


def looks_english(s: str) -> bool:
    if not s:
        return False
    lat = len(re.findall(r"[A-Za-z]", s))
    dev = len(re.findall(r"[ऀ-ॿ]", s))
    letters = lat + dev or 1
    if lat / letters < 0.85 or lat < 12:
        return False
    lc = " " + re.sub(r"[^a-z]+", " ", s.lower()) + " "
    return sum(1 for w in _WORDS if w in lc) >= 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="limit to one doc code")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = _connect(args.db)
    pcols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "text_type" not in pcols:
        print("passages has no text_type column; nothing to do."); con.close(); return

    where = "WHERE TRIM(COALESCE(p.translation,''))='' AND COALESCE(p.text_type,'mula') NOT IN ('frontmatter','noise')"
    params = []
    if args.doc:
        where += " AND d.code=?"; params.append(args.doc)
    rows = con.execute(
        f"SELECT p.id, d.code, p.text FROM passages p JOIN docs d ON d.id=p.doc_id {where}",
        params).fetchall()

    hits = [(pid, code) for pid, code, text in rows if looks_english(text or "")]
    by = {}
    for _, code in hits:
        by[code] = by.get(code, 0) + 1
    print(f"English-source passages to tag as 'frontmatter'  ({'APPLY' if args.apply else 'DRY-RUN'}):")
    if not hits:
        print("  none found."); con.close(); return
    for code, n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {code}: {n}")
    print(f"Total: {len(hits)}")

    if not args.apply:
        print("\nDRY-RUN. Re-run with --apply to tag them (excludes them from coverage/QA). Reversible.")
        con.close(); return

    con.executemany("UPDATE passages SET text_type='frontmatter' WHERE id=?", [(pid,) for pid, _ in hits])
    con.commit(); con.close()
    print(f"\nTagged {len(hits)} passages as 'frontmatter'. Reload the Library/reader; "
          "coverage % now reflects real verses only.")


if __name__ == "__main__":
    main()
