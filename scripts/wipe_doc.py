#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wipe_doc.py — Delete all passages (and their FTS rows) for one doc, safely.

Why this exists (2026-07-20): the standalone sqlite3.exe CLI on Windows is
built without the FTS5 module, so any DELETE touching passages_fts fails with
"no such module: fts5" and aborts the whole statement batch. Python's sqlite3
(the same library the dashboard server uses) has FTS5. Use this script, not
the CLI, for destructive maintenance.

The doc row itself is kept (category, code unchanged) so re-ingest reuses it.
Translations are deleted with the passages — only run this when the passages
themselves are wrong (e.g. the pre-2026-07-20 idx-collision ingest).

Usage:
  python scripts/wipe_doc.py --doc MBh01 --dry-run
  python scripts/wipe_doc.py --doc MBh01 --yes
"""
import argparse
import sqlite3
import sys

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser(description="Wipe all passages for one doc")
    ap.add_argument("--doc", required=True, help="doc code, e.g. MBh01")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--dry-run", action="store_true", help="report counts, delete nothing")
    ap.add_argument("--yes", action="store_true", help="confirm deletion (required to delete)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    row = cur.execute("SELECT id FROM docs WHERE code=?", (args.doc,)).fetchone()
    if not row:
        sys.exit(f"ERROR: doc code {args.doc!r} not found.")
    doc_id = row[0]

    n_total, n_translated = cur.execute(
        "SELECT count(*), sum(CASE WHEN translation IS NOT NULL AND translation!='' THEN 1 ELSE 0 END) "
        "FROM passages WHERE doc_id=?",
        (doc_id,),
    ).fetchone()
    n_translated = n_translated or 0
    print(f"doc={args.doc} (id={doc_id}): {n_total} passages, {n_translated} translated.")

    if args.dry_run:
        print("Dry run — nothing deleted.")
        return
    if not args.yes:
        sys.exit("Refusing to delete without --yes. "
                 f"This would remove {n_total} passages including {n_translated} translations.")

    cur.execute(
        "DELETE FROM passages_fts WHERE rowid IN (SELECT id FROM passages WHERE doc_id=?)",
        (doc_id,),
    )
    n_fts = cur.rowcount
    cur.execute("DELETE FROM passages WHERE doc_id=?", (doc_id,))
    n_del = cur.rowcount
    con.commit()
    print(f"Deleted {n_del} passages and {n_fts} FTS rows for {args.doc}. Doc row kept for re-ingest.")


if __name__ == "__main__":
    main()
