#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_categories.py - assign a category to docs that have none, by code prefix, so the
Srangam Library files them correctly instead of dumping them under 'other'. (2026-08-28)

SAFE: dry-run by default (prints the plan, writes nothing); --apply only sets docs whose
category is currently NULL/empty (never overwrites an existing one). Reversible: to undo,
set the affected codes back to NULL. Writes via db_utils.connect (WAL + busy_timeout);
run when the dashboard is idle.

  python scripts/set_categories.py            # preview the plan
  python scripts/set_categories.py --apply     # write it
"""
from __future__ import annotations
import argparse, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, _HERE)
try:
    from db_utils import connect as _connect
except Exception:
    import sqlite3
    def _connect(p):
        c = sqlite3.connect(p, timeout=30); c.execute("PRAGMA busy_timeout=30000"); return c

# Ordered (substring-in-lowercase-code -> category). First match wins. Edit freely
# to match your taxonomy before --apply; unmatched docs are reported, left untouched.
RULES = [
    ("smriti_",        "smriti"),
    ("harita_",        "ayurveda"),          # Harita Samhita (sthanas) = Ayurveda
    ("dhanur_veda_",   "dhanur_veda"),
    ("jyotish",        "jyotisha"),
    ("gandharva_veda", "gandharva_veda"),
    ("natya_shastra",  "gandharva_veda"),
    ("tantric_texts",  "tantra"),
    ("pancaratra",     "agama"),
    ("shatpath",       "brahmana"),          # Shatapatha Brahmana
    ("brahmanam",      "brahmana"),
    ("aphorismsofsandilya", "bhakti"),       # Sandilya Bhakti Sutra
]


def categorize(code: str) -> str | None:
    lc = code.lower()
    for needle, cat in RULES:
        if needle in lc:
            return cat
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry-run)")
    args = ap.parse_args()

    con = _connect(args.db)
    rows = con.execute(
        "SELECT code FROM docs WHERE category IS NULL OR TRIM(COALESCE(category,''))='' ORDER BY code"
    ).fetchall()
    if not rows:
        print("No uncategorized docs. Nothing to do."); con.close(); return

    plan, unmatched = [], []
    for (code,) in rows:
        cat = categorize(code)
        (plan if cat else unmatched).append((code, cat))

    print(f"{'doc':44s} -> category    ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("-" * 70)
    for code, cat in plan:
        print(f"{code[:44]:44s} -> {cat}")
    if unmatched:
        print("\nUNMATCHED (left as-is; add a rule if you want these categorized):")
        for code, _ in unmatched:
            print(f"  {code}")

    if not args.apply:
        print(f"\n{len(plan)} would be set, {len(unmatched)} unmatched. Re-run with --apply to write.")
        con.close(); return

    n = 0
    for code, cat in plan:
        con.execute("UPDATE docs SET category=? WHERE code=? AND (category IS NULL OR TRIM(COALESCE(category,''))='')",
                    (cat, code))
        n += 1
    con.commit(); con.close()
    print(f"\nApplied: set category on {n} doc(s). Reload the Library to see them filed correctly.")


if __name__ == "__main__":
    main()
