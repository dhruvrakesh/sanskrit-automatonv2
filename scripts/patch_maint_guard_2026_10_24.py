#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
MAINT_GUARD_2026_10_24: the maintenance task never stops in silence.

The fault (24 Oct): the scheduled task (it fires every 3 hours: 00:00, 03:00 ... 21:00) wrote at 15:00 "TICK" and
"dashboard idle - ok to maintain", and nothing more: no START, no SKIP, no FAIL. The runner sets
$ErrorActionPreference = "Stop", so an error in the API check (Test-NetConnection) or any other line outside a step's
own try/catch ends the script without a word. The next tick (18:00) ran in full.

The fix, two guards in scripts\\maintenance_runner.ps1: the API check in a try/catch that logs "SKIP: the API check
failed: ..." and leaves the work to the next tick; and a trap that logs "FAIL: the runner stopped on an error no step
caught: ..." and exits 1 (health_watch.py reads a FAIL after the last DONE as a failure, so the alert mail tells you).
Nothing else changes.

Run from the repo root:  python scripts\\patch_maint_guard_2026_10_24.py --check   then without --check.
Backup: scripts\\maintenance_runner.ps1.bak_maint_guard_ and the date. Test: tests\\test_maint_guard_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'MAINT_GUARD_2026_10_24'
TAG = 'maint_guard'
FILES = ['scripts/maintenance_runner.ps1']
NEEDS = {'scripts/maintenance_runner.ps1': 'ENTITY_LINKS_SCHED_2026_10_23'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/maintenance_runner.ps1', 1, '}\n\n# Always record that the runner fired, before any guard, so a silent task is\n# never a mystery again.',
     '}\n\n# MAINT_GUARD_2026_10_24: an error that nothing else catches is logged as a FAIL line (health_watch.py reads it)\n# instead of ending the tick in silence: on 24 Oct the 15:00 tick wrote "dashboard idle" and nothing more.\ntrap {\n    Log ("FAIL: the runner stopped on an error no step caught: " + $_.Exception.Message)\n    exit 1\n}\n\n# Always record that the runner fired, before any guard, so a silent task is\n# never a mystery again.')

edit('scripts/maintenance_runner.ps1', 2, '\n# Guard 2: Gemini API must be reachable (embeddings/entities need it).\n$net = Test-NetConnection generativelanguage.googleapis.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue\nif (-not $net) { Log "SKIP: no API connectivity"; exit 0 }\n',
     '\n# Guard 2: Gemini API must be reachable (embeddings/entities need it).\ntry {   # MAINT_GUARD_2026_10_24: the check itself may raise (no network, no DNS); that is a skip, logged\n    $net = Test-NetConnection generativelanguage.googleapis.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue\n} catch {\n    Log ("SKIP: the API check failed: " + $_.Exception.Message); exit 0\n}\nif (-not $net) { Log "SKIP: no API connectivity"; exit 0 }\n')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
