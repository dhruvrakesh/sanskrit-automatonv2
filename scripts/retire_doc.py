#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retire_doc.py - retire a superseded document, with every link it owns.
v1, 2026-09-14.

Run diag_retire_check.py FIRST. This tool refuses to run without --supersedes,
so a retirement always records what replaced it.

WHY THIS IS NOT wipe_doc.py
---------------------------
wipe_doc.py deletes passages and their FTS rows, and says so honestly. What it
does not delete is everything else keyed to those passage ids:

    passage_embeddings.passage_id
    entity_mentions.passage_id
    translations_l10n.passage_id
    translation_history.passage_id

Those rows survive pointing at ids that no longer exist. diag_brain.py exists
to find exactly that condition, and its closing note says why: "a wipe +
re-ingest gives passages NEW ids. Vectors and entity mentions keyed to the OLD
ids become orphans." The corpus is at zero orphans today. Retiring a document
with wipe_doc.py would put 106 vectors and several hundred mentions into that
state in one command.

The foreign keys in db_utils.BASE_SCHEMA do declare ON DELETE CASCADE, but
SQLite enforces that only when PRAGMA foreign_keys=ON, which is not in the
PRAGMAS list db_utils.connect applies. This tool therefore deletes every
dependent row explicitly, in one transaction, and never relies on a cascade it
has not verified.

WHAT IT KEEPS
-------------
The docs row. It is one row, it carries the code and the original src_path,
and keeping it means nothing in the corpus dangles and a future re-ingest can
reuse it - the same reasoning wipe_doc.py gives. The retirement is recorded in
doc_stage as (doc_code, 'retired') with the superseding code in the reason,
so the fact survives in the database and not only in a commit message.

WHAT IT DOES NOT DO
-------------------
It does not VACUUM. Reclaiming a few megabytes is not worth taking an
exclusive lock on a 640 MB live database, and the freed pages are reused.
It does not delete entities that lose their last mention; they are counted and
reported, because an entity row is small and removing one could break
entity_variants rows that point at it.

USAGE
  python scripts/retire_doc.py --doc <retiree> --supersedes <keeper> --dry-run
  python scripts/retire_doc.py --doc <retiree> --supersedes <keeper> --sql out.sql
  python scripts/retire_doc.py --doc <retiree> --supersedes <keeper> --yes
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

MARK = "RETIRE_DOC_2026_09_14"

# Dependent rows, in deletion order. Each is (table, column) keyed to
# passages.id; the table is skipped if it or the column is absent.
DEPENDENTS = [
    ("passages_fts", "rowid"),
    ("entity_mentions", "passage_id"),
    ("passage_embeddings", "passage_id"),
    ("translations_l10n", "passage_id"),
    ("translation_history", "passage_id"),
    ("footnotes", "passage_id"),
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def has_table(con, t):
    return con.execute("SELECT name FROM sqlite_master WHERE type IN "
                       "('table','view') AND name=?", (t,)).fetchone() is not None


def cols(con, t):
    try:
        return set(r[1] for r in con.execute("PRAGMA table_info(%s)" % t))
    except Exception:
        return set()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True, help="the document to retire")
    ap.add_argument("--supersedes", required=True,
                    help="the document that replaces it; required, so a retirement "
                         "always records what took its place")
    ap.add_argument("--sql", default=None,
                    help="write the statements to this file and run nothing")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="actually apply")
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit("not found: %s - run from the repo root" % a.db)
    if a.doc == a.supersedes:
        sys.exit("a document cannot supersede itself")

    con = sqlite3.connect(a.db, timeout=120)
    con.execute("PRAGMA busy_timeout=120000")

    def one(sql, *args):
        r = con.execute(sql, args).fetchone()
        return r[0] if r else None

    sid = one("SELECT id FROM docs WHERE code=?", a.doc)
    kid = one("SELECT id FROM docs WHERE code=?", a.supersedes)
    if sid is None:
        sys.exit("doc %r not found" % a.doc)
    if kid is None:
        sys.exit("superseding doc %r not found - retire nothing until it exists"
                 % a.supersedes)

    n_src = one("SELECT COUNT(*) FROM passages WHERE doc_id=?", sid)
    n_keep = one("SELECT COUNT(*) FROM passages WHERE doc_id=?", kid)
    print("%s" % MARK)
    print("  retire     %-40s %6d passage(s)" % (a.doc, n_src))
    print("  superseded by %-37s %6d passage(s)" % (a.supersedes, n_keep))
    if n_keep == 0:
        sys.exit("the superseding document has no passages. Refusing.")
    if n_keep < n_src:
        print("")
        print("  REFUSING: the keeper has FEWER passages than the retiree (%d < %d)."
              % (n_keep, n_src))
        print("  A re-segmented copy should have more rows, not fewer. If this is")
        print("  deliberate, retire by hand and say why in the commit.")
        return 2

    sel = "SELECT id FROM passages WHERE doc_id=%d" % sid
    print("")
    print("  rows that would be deleted:")
    stmts = []
    for tbl, col in DEPENDENTS:
        if not has_table(con, tbl):
            print("    %-22s (table absent)" % tbl)
            continue
        if tbl != "passages_fts" and col not in cols(con, tbl):
            print("    %-22s (no %s column)" % (tbl, col))
            continue
        try:
            n = one("SELECT COUNT(*) FROM %s WHERE %s IN (%s)" % (tbl, col, sel))
        except Exception as e:
            print("    %-22s (uncountable: %s)" % (tbl, e))
            continue
        print("    %-22s %8d" % (tbl, n))
        stmts.append("DELETE FROM %s WHERE %s IN (%s);" % (tbl, col, sel))
    print("    %-22s %8d" % ("passages", n_src))
    stmts.append("DELETE FROM passages WHERE doc_id=%d;" % sid)

    lost = one("SELECT COUNT(*) FROM (SELECT m.entity_id FROM entity_mentions m "
               "JOIN passages p ON p.id=m.passage_id GROUP BY m.entity_id "
               "HAVING SUM(CASE WHEN p.doc_id=? THEN 0 ELSE 1 END)=0)", sid)
    print("")
    print("    entities left with no mention anywhere: %d  (kept, not deleted)" % lost)
    print("    the docs row for %s is KEPT, so nothing dangles and a future" % a.doc)
    print("    re-ingest can reuse the code.")

    ledger = ("INSERT INTO doc_stage(doc_code,stage,status,input_fp,measured,reason,updated_at) "
              "VALUES('%s','retired','done','','{}','superseded by %s on %s','%s') "
              "ON CONFLICT(doc_code,stage) DO UPDATE SET status=excluded.status, "
              "reason=excluded.reason, updated_at=excluded.updated_at;"
              % (a.doc, a.supersedes, now()[:10], now()))
    if has_table(con, "doc_stage"):
        stmts.append(ledger)
        stmts.append("DELETE FROM doc_stage WHERE doc_code='%s' AND stage<>'retired';" % a.doc)

    body = ("-- %s\n-- retire %s, superseded by %s\n"
            "-- generated %s; review before running.\n"
            "-- Take a backup first:  python scripts/db_backup.py "
            "\"data/context.db\" \"D:/backups/context_pre_retire.db\"\n\n"
            "BEGIN IMMEDIATE;\n%s\nCOMMIT;\n"
            % (MARK, a.doc, a.supersedes, now(), "\n".join(stmts)))

    if a.sql:
        with open(a.sql, "w", encoding="utf-8") as f:
            f.write(body)
        print("")
        print("  wrote %s - nothing was applied." % a.sql)
        print("  NOTE: passages_fts is an FTS5 virtual table. The standalone")
        print("  sqlite3.exe on Windows is built WITHOUT fts5, so running this file")
        print("  through the CLI fails with 'no such module: fts5' and aborts the")
        print("  batch. That is why wipe_doc.py exists. Apply it with --yes here,")
        print("  or through python's sqlite3, never through the CLI.")
        con.close()
        return 0

    if a.dry_run or not a.yes:
        print("")
        print("  the statements that --yes would run:")
        for s in stmts:
            print("    %s" % s)
        print("")
        print("  Dry run - nothing applied. Re-run with --yes after a backup.")
        con.close()
        return 0

    print("")
    print("  applying, in one transaction...")
    try:
        con.execute("BEGIN IMMEDIATE")
        for s in stmts:
            con.execute(s)
        con.commit()
    except Exception as e:
        con.rollback()
        print("  ROLLED BACK: %s" % e)
        con.close()
        return 1

    left = one("SELECT COUNT(*) FROM passages WHERE doc_id=?", sid)
    ov = one("SELECT COUNT(*) FROM passage_embeddings e LEFT JOIN passages p "
             "ON p.id=e.passage_id WHERE p.id IS NULL")
    om = one("SELECT COUNT(*) FROM entity_mentions m LEFT JOIN passages p "
             "ON p.id=m.passage_id WHERE p.id IS NULL")
    fts = one("SELECT COUNT(*) FROM passages_fts")
    pas = one("SELECT COUNT(*) FROM passages")
    print("  done.")
    print("    %s now has %d passage(s)" % (a.doc, left))
    print("    orphaned vectors corpus-wide  : %d" % ov)
    print("    orphaned mentions corpus-wide : %d" % om)
    print("    passages_fts %d vs passages %d  %s"
          % (fts, pas, "(aligned)" if fts == pas else "(REBUILD FTS)"))
    if ov or om:
        print("    NON-ZERO ORPHANS. Something dependent was missed; investigate")
        print("    before the next retirement.")
    con.close()
    return 1 if (ov or om or left) else 0


if __name__ == "__main__":
    sys.exit(main())