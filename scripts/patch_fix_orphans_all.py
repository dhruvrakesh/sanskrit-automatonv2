#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_orphans_all.py  (2026-09-14)  FIX_ORPHANS_ALLTABLES_2026_09_14

fix_orphans.py was written on 2026-09-07, found 746 orphaned vectors and
1,231 orphaned entity mentions, cleaned them, and installed AFTER DELETE
triggers so it could not recur. It worked: both counts are still zero today.

On 2026-09-14 an independent verifier - one that shares no code with it -
found 439 orphaned rows in translations_l10n. They are Hindi translations
pointing at passages that no longer exist.

They survived because of one line:

    CHILDREN = (("passage_embeddings", "passage_id"), ("entity_mentions", "passage_id"))

Two tables, hardcoded. translations_l10n and translation_history are also
keyed by passage_id, were never in that tuple, were never cleaned, and never
got a cascade trigger. The file's own diagnosis of the original bug applies
word for word to its own fix: "No referential integrity, and enforcement off.
A DELETE FROM passages removes the parent and silently strands every child."

Four changes, all anchored, none structural:

1. CHILDREN is DISCOVERED from the schema - every table carrying a
   passage_id column - instead of listed. A hardcoded list is a list that
   goes stale the next time a table is added. This one cannot.

2. The read connection drops immutable=1 for query_only. immutable=1 makes
   SQLite ignore the -wal sidecar, so the AFTER report - taken immediately
   after a write - was reading the pre-write state. It reported zero because
   it could not see the deletion it had just performed.

3. The backup stops being shutil.copy2. A file copy of a live WAL database
   can capture a torn page set, which is the exact failure db_backup.py was
   written to prevent. It now uses the sqlite3 online backup API, and writes
   to D:\\backups under the context_pre_* name the retirement policy already
   defines for pre-change snapshots.

4. VACUUM moves behind --vacuum. Reclaiming the pages behind a few hundred
   deleted rows is not worth an exclusive lock on a 640 MB live database, and
   SQLite reuses freed pages anyway.

Usage:
  python scripts/patch_fix_orphans_all.py scripts/fix_orphans.py --check
  python scripts/patch_fix_orphans_all.py scripts/fix_orphans.py
"""

import argparse
import os
import sys

MARK = "FIX_ORPHANS_ALLTABLES_2026_09_14"

A1_OLD = '''DB = os.path.join("data", "context.db")
CHILDREN = (("passage_embeddings", "passage_id"), ("entity_mentions", "passage_id"))
'''

A1_NEW = '''DB = os.path.join("data", "context.db")

# FIX_ORPHANS_ALLTABLES_2026_09_14
# This was a hardcoded pair. translations_l10n and translation_history are
# also keyed by passage_id, were never in it, and still held 439 orphaned
# Hindi rows on 2026-09-14 - seven days after this file reported the corpus
# clean. A list of children is a list that goes stale the next time a table
# is added. Discover them instead.
CHILDREN = []
FALLBACK = (("passage_embeddings", "passage_id"), ("entity_mentions", "passage_id"))


def discover(con):
    """Every table with a passage_id column, from the schema itself."""
    out = []
    for (name,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if name == "passages":
            continue
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % name)]
        except Exception:
            continue
        if "passage_id" in cols:
            out.append((name, "passage_id"))
    return out or list(FALLBACK)
'''

A2_OLD = '''    ap.add_argument("--apply", action="store_true", help="delete the orphaned rows")
    ap.add_argument("--guard", action="store_true", help="install the AFTER DELETE triggers")
'''

A2_NEW = '''    ap.add_argument("--apply", action="store_true", help="delete the orphaned rows")
    ap.add_argument("--guard", action="store_true", help="install the AFTER DELETE triggers")
    ap.add_argument("--vacuum", action="store_true",
                    help="VACUUM after --apply. Off by default: reclaiming the "
                         "pages behind a few hundred rows is not worth an "
                         "exclusive lock on a 640 MB live database, and SQLite "
                         "reuses freed pages anyway.")
'''

A3_OLD = '''    # read-only first, so a report can never disturb a running dashboard
    ro = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
    print("BEFORE")
'''

A3_NEW = '''    # read-only first, so a report can never disturb a running dashboard.
    # FIX_ORPHANS_ALLTABLES_2026_09_14: query_only, NOT immutable=1. The
    # database runs in WAL mode and immutable=1 makes SQLite ignore the -wal
    # sidecar, so the AFTER report below was reading the state before its own
    # deletion. query_only reads the live WAL and still refuses writes.
    ro = sqlite3.connect(DB, timeout=60)
    ro.execute("PRAGMA busy_timeout=60000")
    ro.execute("PRAGMA query_only=ON")
    CHILDREN[:] = discover(ro)
    print("  passage-keyed child tables discovered: %s"
          % ", ".join("%s.%s" % (t, c) for t, c in CHILDREN))
    print("BEFORE")
'''

A4_OLD = '''    os.makedirs("backups", exist_ok=True)
    bak = os.path.join("backups", f"context.db.preOrphanFix.{time.strftime('%Y%m%d_%H%M%S')}")
    print(f"  backing up {DB} -> {bak} (560 MB, this takes a moment)")
    shutil.copy2(DB, bak)
    print("  backup done")
'''

A4_NEW = '''    # FIX_ORPHANS_ALLTABLES_2026_09_14: shutil.copy2 of a live WAL database can
    # capture a torn page set - the -wal moves while the copy is in flight.
    # That is precisely what db_backup.py was written to prevent. Use the
    # sqlite3 online backup API, which snapshots consistently, and write it
    # under the context_pre_* name the retirement policy defines for
    # pre-change snapshots (so backup_runner.ps1's context_2*.db rotation
    # leaves it alone).
    bdir = r"D:\\backups"
    if not os.path.isdir(bdir):
        bdir = "backups"
        os.makedirs(bdir, exist_ok=True)
    bak = os.path.join(bdir, "context_pre_orphanfix_%s.db" % time.strftime("%Y%m%d_%H%M%S"))
    print(f"  online backup {DB} -> {bak}")
    _s = sqlite3.connect(DB, timeout=180)
    _s.execute("PRAGMA busy_timeout=180000")
    _d = sqlite3.connect(bak)
    with _d:
        _s.backup(_d)
    _d.close()
    _s.close()
    print("  backup done (%.1f MB)" % (os.path.getsize(bak) / 1048576.0))
'''

A5_OLD = '''        if a.apply:
            print("  VACUUM (reclaims space; may take a minute on 560 MB)")
            con.execute("VACUUM")
'''

A5_NEW = '''        if a.apply and a.vacuum:
            print("  VACUUM (reclaims space; may take a minute on 640 MB)")
            con.execute("VACUUM")
        elif a.apply:
            print("  no VACUUM - freed pages are reused, and an exclusive lock")
            print("  on a 640 MB live database is not worth a few hundred rows.")
            print("  Pass --vacuum if you want one.")
'''

A6_OLD = '''    ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("\\nAFTER")
'''

A6_NEW = '''    ro = sqlite3.connect(DB, timeout=60)
    ro.execute("PRAGMA busy_timeout=60000")
    ro.execute("PRAGMA query_only=ON")
    print("\\nAFTER")
'''

PATCHES = [
    (A1_OLD, A1_NEW, "CHILDREN discovered, not hardcoded"),
    (A2_OLD, A2_NEW, "--vacuum flag"),
    (A3_OLD, A3_NEW, "BEFORE read: query_only, not immutable=1"),
    (A4_OLD, A4_NEW, "online backup instead of shutil.copy2"),
    (A5_OLD, A5_NEW, "VACUUM behind --vacuum"),
    (A6_OLD, A6_NEW, "AFTER read: query_only"),
]


def read_src(p):
    s = open(p, "rb").read().decode("utf-8")
    crlf, lf = s.count("\r\n"), s.count("\n")
    if crlf and crlf != lf:
        raise SystemExit("FAIL: %s has mixed line endings (%d CRLF of %d LF)" % (p, crlf, lf))
    return s.replace("\r\n", "\n"), ("\r\n" if crlf else "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.target):
        print("FAIL: %s not found" % a.target)
        return 2
    src, nl = read_src(a.target)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0

    print("anchor                                        found")
    print("-" * 56)
    ok = True
    for old, _new, name in PATCHES:
        n = src.count(old)
        print("%-45s %s" % (name, "OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)))
        if n != 1:
            ok = False
    print("-" * 56)
    if not ok:
        print("FAIL: anchors did not match. Nothing written.")
        return 2
    if a.check:
        print("--check only: nothing written.")
        return 0

    for old, new, _name in PATCHES:
        src = src.replace(old, new, 1)

    # Only CODE lines matter. The replacement text explains why immutable=1 is
    # wrong, so a naive substring check would reject its own explanation - the
    # same class of mistake as a gate that fires on its own documentation.
    live = [(i, l) for i, l in enumerate(src.split("\n"), 1)
            if "immutable=1" in l and not l.strip().startswith("#")]
    if live:
        print("FAIL: an immutable=1 read survived the patch:")
        for i, l in live:
            print("  line %d: %s" % (i, l.strip()))
        return 2
    if "shutil.copy2(DB" in src:
        print("FAIL: the file copy survived the patch.")
        return 2

    open(a.target, "wb").write(src.replace("\n", nl).encode("utf-8"))
    print("Patched %s (%s endings preserved)" % (os.path.basename(a.target),
                                                 "CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    print("")
    print("The trigger loop in main() iterates CHILDREN, so making CHILDREN")
    print("dynamic also makes --guard install a cascade trigger for every")
    print("passage-keyed table, not just the two it knew about in September.")
    return 0


if __name__ == "__main__":
    sys.exit(main())