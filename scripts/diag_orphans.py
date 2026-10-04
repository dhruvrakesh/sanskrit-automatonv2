#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
diag_orphans.py  (2026-10-04)  DIAG_ORPHANS_2026_10_04

Read-only. Where did the orphans come from, and is it safe to leave them?

fix_orphans.py counts orphans and shows ONE id window, for the first table only.
That is enough to delete them, not to understand them. This shows, for every
table keyed by passage_id:

  - how many rows point at a passage that no longer exists;
  - the orphaned ids in contiguous blocks, and for each block the live docs
    whose passages sit just below and just above it (the deleted text lay
    between them; retired docs keep their docs row, so they show here too);
  - how many orphaned ids are ABOVE the current highest passage id. passages.id
    is a plain INTEGER PRIMARY KEY unless the table says AUTOINCREMENT, so SQLite
    may hand those ids out again to the next ingest - and an orphan would then
    silently attach to an unrelated new passage. If this count is not zero,
    clean before the next ingest;
  - a few sample rows (all columns) and, for entity_mentions, the entities they
    name;
  - the cascade triggers installed (fix_orphans.py --guard).

--db can point at a backup, to see whether the orphans were already there:
  python scripts\\diag_orphans.py
  python scripts\\diag_orphans.py --db "D:\\backups\\context_pre_guards_20261004_122916.db"

Never writes: the database is opened with mode=ro and PRAGMA query_only.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

MARK = "DIAG_ORPHANS_2026_10_04"


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=60000")
    return con


def children(con) -> list[str]:
    out = []
    for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                               "AND name <> 'passages' ORDER BY name"):
        try:
            cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % name)]
        except sqlite3.Error:
            continue
        if "passage_id" in cols:
            out.append(name)
    return out


def blocks(ids: list[int], gap: int = 50) -> list[tuple[int, int, int]]:
    """Contiguous runs (lo, hi, count); a jump larger than `gap` starts a new run."""
    out = []
    for i in sorted(set(ids)):
        if out and i - out[-1][1] <= gap:
            lo, _hi, n = out[-1]
            out[-1] = (lo, i, n + 1)
        else:
            out.append((i, i, 1))
    return out


def neighbour(con, pid: int, below: bool):
    op, order = ("<", "DESC") if below else (">", "ASC")
    r = con.execute("SELECT p.id, d.code FROM passages p JOIN docs d ON d.id = p.doc_id WHERE p.id %s ? "
                    "ORDER BY p.id %s LIMIT 1" % (op, order), (pid,)).fetchone()
    return ("%s (passage %d)" % (r[1], r[0])) if r else "-"


def run(db: str, samples: int = 3, out=print) -> dict:
    con = open_ro(db)
    try:
        maxid = con.execute("SELECT COALESCE(MAX(id), 0) FROM passages").fetchone()[0]
        psql = (con.execute("SELECT sql FROM sqlite_master WHERE name='passages'").fetchone() or [""])[0] or ""
        autoinc = "AUTOINCREMENT" in psql.upper()
        out("%s  db=%s" % (MARK, db))
        out("  passages: %d rows, max id %d, ids %s" % (
            con.execute("SELECT COUNT(*) FROM passages").fetchone()[0], maxid,
            "never reused (AUTOINCREMENT)" if autoinc else "MAY BE REUSED above the max (no AUTOINCREMENT)"))
        trig = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_passages_delete_cascade%' "
            "ORDER BY name")]
        out("  cascade triggers: %d %s" % (len(trig), ", ".join(trig) if trig else "(NONE: deletes strand children)"))
        result = {"max_id": maxid, "autoincrement": autoinc, "triggers": trig, "tables": {}}
        for t in children(con):
            ids = [r[0] for r in con.execute(
                'SELECT c.passage_id FROM "%s" c LEFT JOIN passages p ON p.id = c.passage_id '
                'WHERE p.id IS NULL AND c.passage_id IS NOT NULL' % t)]
            total = con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
            above = sum(1 for i in ids if i > maxid)
            result["tables"][t] = {"orphans": len(ids), "total": total, "above_max": above,
                                   "blocks": blocks(ids)}
            out("")
            out("  %-22s %7d orphaned of %8d" % (t, len(ids), total))
            if not ids:
                continue
            for lo, hi, n in blocks(ids)[:12]:
                out("    ids %d..%d  (%d passage ids)   below: %s   above: %s"
                    % (lo, hi, n, neighbour(con, lo, True), neighbour(con, hi, False)))
            if len(blocks(ids)) > 12:
                out("    ... %d more blocks" % (len(blocks(ids)) - 12))
            if above:
                out("    WARNING: %d orphaned row(s) point ABOVE the current max passage id. %s" % (
                    above, "AUTOINCREMENT prevents reuse." if autoinc else
                    "The next ingest may reuse those ids and adopt these rows. Clean before ingesting."))
            cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % t)]
            for row in con.execute('SELECT c.* FROM "%s" c LEFT JOIN passages p ON p.id = c.passage_id '
                                   'WHERE p.id IS NULL LIMIT ?' % t, (samples,)):
                out("    sample: " + ", ".join("%s=%s" % (k, (str(v)[:40] if v is not None else "NULL"))
                                             for k, v in zip(cols, row) if k not in ("vec", "embedding")))
            if t == "entity_mentions" and "entity_id" in cols:
                try:
                    names = con.execute(
                        """SELECT e.canonical, COUNT(*) FROM entity_mentions m JOIN entities e ON e.id = m.entity_id
                           LEFT JOIN passages p ON p.id = m.passage_id WHERE p.id IS NULL
                           GROUP BY e.id ORDER BY COUNT(*) DESC LIMIT 12""").fetchall()
                    out("    entities named: " + "; ".join("%s x%d" % (n, c) for n, c in names))
                except sqlite3.Error:
                    pass
        n = sum(v["orphans"] for v in result["tables"].values())
        out("")
        if n:
            out("  %d orphaned row(s) in all. Deleting them is safe by construction: fix_orphans.py removes ONLY"
                % n)
            out("  rows whose passage id has no passage. Stop the dashboard or wait for idle, then:")
            out("    python scripts\\fix_orphans.py --apply")
        else:
            out("  No orphans.")
        return result
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only: where orphans came from")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--samples", type=int, default=3)
    a = ap.parse_args()
    if not Path(a.db).exists():
        print("FAIL: %s not found. Run from the repo root, or pass --db." % a.db); return 2
    run(a.db, a.samples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
