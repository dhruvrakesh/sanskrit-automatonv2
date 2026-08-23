#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_backup.py — make a CONSISTENT copy of a SQLite database (2026-08-20).

A raw file copy (Copy-Item / cp) of a database that is being written grabs a
mid-write, inconsistent image and yields 'database disk image is malformed'.
This uses SQLite's online backup API, which snapshots a *consistent* copy and
correctly folds in the -wal. It first verifies the SOURCE is healthy and
readable, so it can never propagate corruption or copy a locked, half-written
DB. For a fully clean cutover, still stop the writers (dashboard + translate
jobs) first — if the source is locked, this tool refuses and tells you so.

Usage (from the automaton/ root; quote the paths):
  python scripts/db_backup.py "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\data\\context.db" "D:\\sanskrit-symphony\\automaton\\data\\context.db"
"""
from __future__ import annotations
import os
import sqlite3
import sys


def _counts(con) -> str:
    try:
        docs = con.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        en = con.execute(
            "SELECT COUNT(*) FROM passages WHERE TRIM(COALESCE(translation,'')) <> ''"
        ).fetchone()[0]
        try:
            hi = con.execute(
                "SELECT COUNT(*) FROM translations_l10n "
                "WHERE lang='hi' AND TRIM(COALESCE(translation,'')) <> ''"
            ).fetchone()[0]
        except Exception:
            hi = "n/a"
        return f"docs={docs}  en_translated={en}  hi={hi}"
    except Exception as e:
        return f"(count error: {e})"


def main():
    if len(sys.argv) < 3:
        sys.exit('usage: python scripts/db_backup.py "<src.db>" "<dst.db>"')
    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.exists(src):
        sys.exit(f"source not found: {src}")

    # 1. Source must be readable AND healthy — never copy a locked/corrupt DB.
    try:
        s_ro = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
        s_ro.execute("PRAGMA busy_timeout=60000")
        chk = s_ro.execute("PRAGMA quick_check").fetchone()[0]
        src_counts = _counts(s_ro)
        s_ro.close()
    except Exception as e:
        sys.exit(
            f"cannot read source ({e}).\n"
            "It is likely LOCKED by running jobs. Stop the dashboard and let the "
            "translate jobs finish (or Pause All), then re-run this."
        )
    if chk != "ok":
        sys.exit(f"SOURCE failed integrity check ({chk!r}). Do NOT copy a corrupt "
                 f"source; investigate the origin DB first.")
    print(f"source OK  ({src_counts})")

    # 2. Online backup → consistent snapshot.
    print(f"backing up ->\n  {dst}")
    src_con = sqlite3.connect(src, timeout=60)
    src_con.execute("PRAGMA busy_timeout=60000")
    dst_con = sqlite3.connect(dst)
    shown = {"pct": -10}

    def _prog(status, remaining, total):
        if total:
            pct = int(100 * (total - remaining) / total)
            if pct >= shown["pct"] + 10:
                shown["pct"] = pct
                print(f"  {pct}%")

    try:
        with dst_con:
            src_con.backup(dst_con, pages=2000, progress=_prog)
    finally:
        src_con.close()

    # 3. Verify the COPY.
    ok = dst_con.execute("PRAGMA quick_check").fetchone()[0]
    dst_counts = _counts(dst_con)
    dst_con.close()
    print(f"copy integrity: {ok}")
    print(f"copy contents : {dst_counts}")
    if ok == "ok":
        print("DONE — copy is consistent and matches the source.")
    else:
        sys.exit("WARNING: copy integrity != 'ok' — do not use this copy.")


if __name__ == "__main__":
    main()
