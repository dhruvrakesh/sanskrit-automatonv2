#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
purge_empty_cache.py — Remove poisoned rows from the translation cache.

Background (2026-07-20): until the _cache_insert_many guard landed, EMPTY and
REFUSAL outputs were cached. One transient failure — API credit exhausted,
rate limit, safety block — poisoned that verse's cache entry permanently:
every re-run got the empty back instantly instead of calling the API.
Measured at fix time: 4,895 empty + 1,004 boilerplate rows = ~60% of mt_cache.

This tool deletes those rows. Passages whose stored translation is empty are
then genuinely re-attempted by the next translate run (translated passages
are untouched — nothing is ever re-billed).

Read-only by default; --yes to delete.
Do NOT run while a translate job is writing (SQLite single-writer).

Usage:
  python scripts/purge_empty_cache.py           # report only
  python scripts/purge_empty_cache.py --yes     # delete
"""
from __future__ import annotations
import argparse
import sqlite3

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

from text_filters import is_translation_boilerplate


def main():
    ap = argparse.ArgumentParser(description="Purge empty/refusal rows from mt_cache")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--yes", action="store_true", help="actually delete (default: report)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    total = cur.execute("SELECT count(*) FROM mt_cache").fetchone()[0]

    # Empty outputs: pure SQL.
    empty_ids = [r[0] for r in cur.execute(
        "SELECT id FROM mt_cache WHERE TRIM(COALESCE(output,''))=''")]

    # Boilerplate/refusals: reuse the canonical junk detector so this tool and
    # the write-path guard can never disagree.
    junk_ids = [rid for rid, out in cur.execute(
        "SELECT id, output FROM mt_cache WHERE TRIM(COALESCE(output,''))<>''")
        if is_translation_boilerplate(out)]

    by_engine: dict[str, int] = {}
    if empty_ids or junk_ids:
        all_ids = empty_ids + junk_ids
        for i in range(0, len(all_ids), 500):
            chunk = all_ids[i:i + 500]
            q = ",".join("?" for _ in chunk)
            for eng, n in cur.execute(
                    f"SELECT engine, count(*) FROM mt_cache WHERE id IN ({q}) "
                    f"GROUP BY engine", chunk):
                by_engine[eng] = by_engine.get(eng, 0) + n

    print(f"mt_cache: {total} rows total")
    print(f"  poisoned — empty outputs   : {len(empty_ids)}")
    print(f"  poisoned — refusal outputs : {len(junk_ids)}")
    for eng in sorted(by_engine):
        print(f"    {eng:<32} {by_engine[eng]}")
    keep = total - len(empty_ids) - len(junk_ids)
    print(f"  clean rows kept            : {keep}")

    if not args.yes:
        print("\nReport only — nothing deleted. Re-run with --yes to purge.")
        return

    all_ids = empty_ids + junk_ids
    for i in range(0, len(all_ids), 500):
        chunk = all_ids[i:i + 500]
        q = ",".join("?" for _ in chunk)
        cur.execute(f"DELETE FROM mt_cache WHERE id IN ({q})", chunk)
    con.commit()
    # Reclaim space — the purge can halve the table.
    try:
        con.execute("VACUUM")
    except sqlite3.OperationalError:
        pass  # e.g. another connection holds the DB; VACUUM is optional
    print(f"\nPurged {len(all_ids)} poisoned cache rows. "
          f"Empty passages will be genuinely re-attempted on the next run.")


if __name__ == "__main__":
    main()
