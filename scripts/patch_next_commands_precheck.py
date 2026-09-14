#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_next_commands_precheck.py  (2026-09-14)  PRECHECK_2026_09_14

next_commands.py v1 printed twenty-five morph commands, every one of
which dies on line 130 with ModuleNotFoundError. Emitting a command is
not the same as the command being runnable, and a driver that cannot
tell those apart is the same defect this project keeps finding,
wearing my own name.

This adds a PRECHECK. A stage in the playbook may carry

    "precheck": "import vidyut"

and the tool runs it once, in this interpreter, before emitting any
command for that stage. A stage whose precheck fails is listed as
BLOCKED with the real error rather than printed as work.

Two anchored edits and a version bump. Nothing is restructured.

  python scripts/patch_next_commands_precheck.py scripts/next_commands.py --check
  python scripts/patch_next_commands_precheck.py scripts/next_commands.py
"""

import argparse
import os
import sys

MARK = "PRECHECK_2026_09_14"

P = [
    ('''FILE_VERSION = "2026-09-14.01"
MARK = "NEXT_COMMANDS_2026_09_14"

HERE = os.path.dirname(os.path.abspath(__file__))
''',
     '''FILE_VERSION = "2026-09-14.02"
MARK = "NEXT_COMMANDS_2026_09_14"

# PRECHECK_2026_09_14
import subprocess

_PRECHECK_CACHE = {}


def precheck_ok(stage, expr):
    """Run a stage's one-line precheck once. Emitting a command that cannot
    run is worse than emitting nothing: it looks like work."""
    if not expr:
        return True, ""
    if stage in _PRECHECK_CACHE:
        return _PRECHECK_CACHE[stage]
    try:
        r = subprocess.run([sys.executable, "-c", expr],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120)
        if r.returncode == 0:
            out = (True, "")
        else:
            txt = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
            out = (False, txt[-1] if txt else "exit %d" % r.returncode)
    except Exception as e:
        out = (False, str(e))
    _PRECHECK_CACHE[stage] = out
    return out


HERE = os.path.dirname(os.path.abspath(__file__))
''',
     "the precheck helper and a version bump"),
    ('''        spec = pb.get(stage) or {}
        cmd = spec.get("cmd")
        cost = spec.get("cost", "unknown")
        if spec.get("driver") is False and not a.allow_supervised:
''',
     '''        spec = pb.get(stage) or {}
        cmd = spec.get("cmd")
        cost = spec.get("cost", "unknown")
        good, why = precheck_ok(stage, spec.get("precheck"))
        if not good:
            blocked[stage] = (blocked.get(stage, (0, why))[0] + 1, why)
            continue
        if spec.get("driver") is False and not a.allow_supervised:
''',
     "check before emitting"),
    ('''    emitted = []
    skipped_paid = 0
    skipped_unknown = {}
    supervised = {}
''',
     '''    emitted = []
    skipped_paid = 0
    skipped_unknown = {}
    supervised = {}
    blocked = {}
''',
     "declare the blocked bucket"),
    ('''    if supervised:
        print("  SUPERVISED, not emitted - these are step one of a gated sequence,")
''',
     '''    if blocked:
        print("  BLOCKED - the precheck for these stages FAILED, so no command was")
        print("  emitted. Fix the environment, not the playbook:")
        for k in sorted(blocked):
            n, why = blocked[k]
            print("    %-14s %4d unit(s)   %s" % (k, n, why[:90]))
        print("")
    if supervised:
        print("  SUPERVISED, not emitted - these are step one of a gated sequence,")
''',
     "report the blocked stages"),
    # The version also appears in the docstring header. Write-Script in the ops
    # blocks reads the FIRST FILE_VERSION it finds, so leaving the docstring at
    # .01 would make a later block think this file is older than it is and
    # happily write over it. Two lines, one truth.
    ('''FILE_VERSION = "2026-09-14.01"
MARK = "NEXT_COMMANDS_2026_09_14"

automaton.py''',
     '''FILE_VERSION = "2026-09-14.02"
MARK = "NEXT_COMMANDS_2026_09_14"

automaton.py''',
     "the same version in the docstring header"),
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
    print("Patched %s" % os.path.basename(a.target))
    print("Marker: %s" % MARK)
    return 0


if __name__ == "__main__":
    sys.exit(main())