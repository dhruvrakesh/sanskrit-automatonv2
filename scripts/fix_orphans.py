#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_orphans.py — remove rows that point at passages which no longer exist,
and stop the leak that created them. (2026-09-07)

═══ WHAT IS WRONG ══════════════════════════════════════════════════════════
Measured in data/context.db on 2026-09-07:

    passage_embeddings with no passage : 746
    entity_mentions    with no passage : 1,231

Every one points into passage ids 102,523 .. 107,362. That window is 4,840 ids
wide and NOT ONE of those passages still exists — a whole document was deleted
(HAYASHIRSHA_PANCARATRA ends at 102,519; Shatpatha begins at 112,177, so the
window sat between them) and its children were left behind.

They were left behind because there is nothing to take them away:

    CREATE TABLE passage_embeddings(...)   -- no FOREIGN KEY clause at all
    CREATE TABLE entity_mentions(...)      -- no FOREIGN KEY clause at all
    PRAGMA foreign_keys = 0

No referential integrity, and enforcement off. A DELETE FROM passages removes
the parent and silently strands every child.

═══ WHY IT MATTERS, CONCRETELY ═════════════════════════════════════════════
Search ranks over passage_embeddings. 746 of 15,758 vectors — 4.7% — can never
resolve to text, so every semantic query wastes part of its neighbourhood on
rows that cannot be displayed. entity_mentions drives the entity counts on the
dashboard: 1,231 of 26,975 mentions (4.6%) inflate terms that have no citable
occurrence left. Both are the same failure this estate keeps producing — a
number that describes work whose subject no longer exists.

═══ WHAT THIS SCRIPT DOES ══════════════════════════════════════════════════
  --report   (default)  count them, show the id blocks, change nothing
  --apply               back up the DB, delete ONLY rows whose passage_id has
                        no matching passages.id, VACUUM, re-verify
  --guard               additionally install the prevention (see below)

Deletion predicate, exactly:
    DELETE FROM <child> WHERE passage_id NOT IN (SELECT id FROM passages)
A row is removed only when its parent is provably absent. Nothing else is
touched: no passage, no doc, no translation, no entity.

═══ PREVENTION (--guard) ═══════════════════════════════════════════════════
SQLite cannot add a FOREIGN KEY to an existing table without rebuilding it, and
rebuilding a 560 MB live table on a running system is exactly the kind of
change this project cannot afford. So --guard installs TRIGGERS instead, which
are additive and instant:

    CREATE TRIGGER trg_passages_delete_cascade_emb
    AFTER DELETE ON passages BEGIN
      DELETE FROM passage_embeddings WHERE passage_id = OLD.id;
    END;

    ... and the same for entity_mentions.

Triggers fire regardless of PRAGMA foreign_keys, so they work even though
enforcement is off. From then on, deleting a passage takes its children with it
and this cannot recur.

  python scripts/fix_orphans.py                 # report only
  python scripts/fix_orphans.py --apply --guard # clean up AND prevent
"""
from __future__ import annotations
import argparse, os, shutil, sqlite3, sys, time

DB = os.path.join("data", "context.db")
CHILDREN = (("passage_embeddings", "passage_id"), ("entity_mentions", "passage_id"))


def counts(cur):
    out = {}
    for tbl, col in CHILDREN:
        cur.execute(f"SELECT count(*) FROM {tbl} WHERE {col} NOT IN (SELECT id FROM passages)")
        out[tbl] = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {tbl}")
        out[tbl + "_total"] = cur.fetchone()[0]
    return out


def report(cur):
    c = counts(cur)
    print("  table                 orphaned      total     share")
    for tbl, _ in CHILDREN:
        n, t = c[tbl], c[tbl + "_total"]
        print(f"  {tbl:<20}{n:>9,}{t:>11,}{(100*n/t if t else 0):>9.1f}%")
    cur.execute(f"""SELECT min({CHILDREN[0][1]}), max({CHILDREN[0][1]})
                    FROM {CHILDREN[0][0]} WHERE {CHILDREN[0][1]} NOT IN (SELECT id FROM passages)""")
    lo, hi = cur.fetchone()
    if lo is not None:
        cur.execute("SELECT count(*) FROM passages WHERE id BETWEEN ? AND ?", (lo, hi))
        alive = cur.fetchone()[0]
        print(f"\n  orphan id window : {lo:,} .. {hi:,}  ({hi-lo+1:,} ids)")
        print(f"  passages still alive in that window : {alive:,}")
        if alive == 0:
            print("  -> the entire window is deleted. These children have no possible parent.")
    return c


def guards(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_passages_delete_cascade%'")
    return [r[0] for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="delete the orphaned rows")
    ap.add_argument("--guard", action="store_true", help="install the AFTER DELETE triggers")
    a = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit(f"not found: {DB} - run from the sanskrit-automatonv2 repo root")

    # read-only first, so a report can never disturb a running dashboard
    ro = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
    print("BEFORE")
    before = report(ro.cursor())
    existing = guards(ro.cursor())
    print(f"\n  cascade triggers installed : {existing or 'NONE'}")
    ro.close()

    if not (a.apply or a.guard):
        print("\nReport only. To act:")
        print("  1. STOP the dashboard on :5057 first — SQLite will not take a write")
        print("     lock while another process holds the file.")
        print("  2. python scripts/fix_orphans.py --apply --guard")
        return

    print("\n  NOTE: this needs an exclusive write lock. If it fails with")
    print("  'database is locked', stop the dashboard on :5057 and re-run.\n")

    os.makedirs("backups", exist_ok=True)
    bak = os.path.join("backups", f"context.db.preOrphanFix.{time.strftime('%Y%m%d_%H%M%S')}")
    print(f"  backing up {DB} -> {bak} (560 MB, this takes a moment)")
    shutil.copy2(DB, bak)
    print("  backup done")

    con = sqlite3.connect(DB, timeout=30)
    cur = con.cursor()
    try:
        if a.apply:
            for tbl, col in CHILDREN:
                cur.execute(f"DELETE FROM {tbl} WHERE {col} NOT IN (SELECT id FROM passages)")
                print(f"  deleted {cur.rowcount:,} orphaned rows from {tbl}")
        if a.guard:
            for tbl, col in CHILDREN:
                name = f"trg_passages_delete_cascade_{tbl}"
                cur.execute(f"DROP TRIGGER IF EXISTS {name}")
                cur.execute(f"""CREATE TRIGGER {name}
                                AFTER DELETE ON passages BEGIN
                                  DELETE FROM {tbl} WHERE {col} = OLD.id;
                                END""")
                print(f"  installed trigger {name}")
        con.commit()
        if a.apply:
            print("  VACUUM (reclaims space; may take a minute on 560 MB)")
            con.execute("VACUUM")
    except Exception as exc:
        con.rollback(); con.close()
        print(f"\nFAILED: {exc}")
        print(f"The database is unchanged. Restore from {bak} only if you doubt that.")
        sys.exit(1)
    con.close()

    ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("\nAFTER")
    after = report(ro.cursor())
    print(f"\n  cascade triggers installed : {guards(ro.cursor()) or 'NONE'}")
    ro.close()

    ok = all(after[t] == 0 for t, _ in CHILDREN)
    print("\n" + ("  VERIFIED: zero orphaned rows remain." if ok
                  else "  *** ORPHANS REMAIN — investigate before trusting this ***"))
    print(f"  backup kept at {bak}")
    if a.guard:
        print("\n  Prove the trigger works, on a throwaway row:")
        print("    (the next re-ingest will now clean up after itself)")


if __name__ == "__main__":
    main()
