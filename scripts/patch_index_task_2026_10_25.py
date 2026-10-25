#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_index_task_2026_10_25.py  (2026-10-25)  INDEX_SITE_2026_10_25

The corpus mirror's scheduled tick (scripts\\corpus_mirror_task.ps1) sends the indexes' genealogies too, last: after
corpus_sync.py and corpus_media.py, python scripts\\index_sync.py --apply --if-configured (what differs only; it exits 0
doing nothing until CORPUS_SYNC_SECRET is set, C21 is pasted and corpus-index is deployed). The tick's exit code is the
first that failed. docs/INDEX_SITE_2026-10-25.md.

Anchored edits, all-or-nothing, marker-idempotent, line endings kept, .bak_indextask_<date> backups.
Needs CORPUS_MEDIA_C8_2026_10_09 in the task and scripts\\index_sync.py (INDEX_SITE_2026_10_25).

  python scripts\\patch_index_task_2026_10_25.py --check
  python scripts\\patch_index_task_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'INDEX_SITE_2026_10_25'
TAG = 'indextask'
FILES = ['scripts/corpus_mirror_task.ps1']
NEEDS = {'scripts/corpus_mirror_task.ps1': 'CORPUS_MEDIA_C8_2026_10_09'}
REQUIRES = {'scripts/index_sync.py': 'INDEX_SITE_2026_10_25'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_mirror_task.ps1', 1, '# applied and corpus-media is deployed. The PC is kept awake while the tick runs (the tick of\n# 2026-10-08 night took 7.5 h because the PC slept in the middle); it may sleep again after.\n$root = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"\n$log  = "D:\\backups\\corpus_mirror_log.txt"',
     '# applied and corpus-media is deployed. The PC is kept awake while the tick runs (the tick of\n# 2026-10-08 night took 7.5 h because the PC slept in the middle); it may sleep again after.\n# INDEX_SITE_2026_10_25: last, the indexes\' genealogies (scripts\\index_sync.py, docs/INDEX_SITE_2026-10-25.md):\n# what differs only; it exits 0 quietly until C21 is pasted and corpus-index is deployed.\n$root = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"\n$log  = "D:\\backups\\corpus_mirror_log.txt"')

edit('scripts/corpus_mirror_task.ps1', 2, '$rcm = $LASTEXITCODE\nLog ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)\nif ($awake) { [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483648) }\nif ($rc -ne 0) { exit $rc }\nexit $rcm\n',
     '$rcm = $LASTEXITCODE\nLog ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)\n$t2 = Get-Date\n& $py scripts\\index_sync.py --apply --if-configured 2>&1 | ForEach-Object { "$_" } | Add-Content $log\n$rci = $LASTEXITCODE\nLog ("DONE - index genealogies rc={0} {1:n0}s" -f $rci, ((Get-Date) - $t2).TotalSeconds)\nif ($awake) { [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483648) }\nif ($rc -ne 0) { exit $rc }\nif ($rcm -ne 0) { exit $rcm }\nexit $rci\n')


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
