#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_automaton_backfill_count.py  (2026-09-14)  BACKFILL_COUNT_2026_09_14

automaton.py --backfill prints

    wrote 767 ledger row(s) across 61 document(s)

767 is 13 stages x 59 documents. The line above it says "skipping 2
retired document(s)", so 59 is the number that was written to and 61 is
len(docs) - every document measured, including the two skipped.

Nobody is harmed by two. The reason to fix it anyway is that this is the
tool whose entire claim is "Nothing below is declared. Every status is
derived from the data", printed two lines earlier in the same output. A
summary line that does not match its own loop is the smallest possible
version of the defect this project keeps finding in bigger forms.

Three anchored edits: declare the counter, increment it where the loop
actually does work, print it instead of len(docs).

Usage:
  python scripts/patch_automaton_backfill_count.py scripts/automaton.py --check
  python scripts/patch_automaton_backfill_count.py scripts/automaton.py
"""

import argparse
import os
import sys

MARK = "BACKFILL_COUNT_2026_09_14"

P = [
    ('''    ts = now()
    wrote = 0
    changes = []
''',
     '''    ts = now()
    wrote = 0
    touched = 0   # BACKFILL_COUNT_2026_09_14 - documents actually written to
    changes = []
''',
     "declare the counter"),
    ('''        if code in gone:
            continue
        m = docs[code]
''',
     '''        if code in gone:
            continue
        touched += 1
        m = docs[code]
''',
     "increment where work happens"),
    ('''          % (wrote, len(docs), len(changes)))
''',
     '''          % (wrote, touched, len(changes)))
''',
     "print what the loop did, not what it saw"),
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
    print("anchor                                             found")
    print("-" * 60)
    ok = True
    for old, _new, name in P:
        n = src.count(old)
        print("%-50s %s" % (name, "OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)))
        if n != 1:
            ok = False
    print("-" * 60)
    if not ok:
        print("FAIL: anchors did not match. Nothing written.")
        return 2
    if a.check:
        print("--check only: nothing written.")
        return 0
    for old, new, _name in P:
        src = src.replace(old, new, 1)
    open(a.target, "wb").write(src.replace("\n", nl).encode("utf-8"))
    print("Patched %s (%s endings preserved)"
          % (os.path.basename(a.target), "CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    return 0


if __name__ == "__main__":
    sys.exit(main())