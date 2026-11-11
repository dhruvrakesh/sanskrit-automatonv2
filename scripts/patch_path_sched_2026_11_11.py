#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_path_sched_2026_11_11.py  (2026-11-11)  PATH_SCHED_2026_11_11

The desk (/desk/<doc>) reads each text's path from data\\text_path.json. Nothing charted it on a schedule: on 11 Nov it
was of 28 Oct, and the Gandharva Veda's desk said "vision has read 0 of its 507 pages" two days after vision (the
repair's round, step e of the maintenance task) had read them. This adds step f to scripts\\maintenance_runner.ps1 (the
task SanskritMaintenance, every 3 hours when the dashboard writes nothing): text_path.py (free; the database read
only) when the chart is 20 hours old or more. A failure is logged and skipped, as the other steps'.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_pathsched_<date> copies.

  python scripts\\patch_path_sched_2026_11_11.py --check
  python scripts\\patch_path_sched_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'PATH_SCHED_2026_11_11'
TAG = 'pathsched'
FILES = ['scripts/maintenance_runner.ps1']
NEEDS = {'scripts/maintenance_runner.ps1': 'AUTO_REPAIR_2026_10_25'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/maintenance_runner.ps1', 1, '    }\n\n    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)\n    exit 0',
     '    }\n\n    # f) PATH_SCHED_2026_11_11: the path of every text charted again (scripts\\text_path.py: FREE, the database read\n    #    only) when the chart is 20 hours old or more, after the repair\'s round (step e) has changed a text. The desk\n    #    (/desk/<doc>) reads it: on 11 Nov the Gandharva Veda\'s desk still said "vision has read 0 of its 507 pages",\n    #    from a chart of 28 Oct, two days after vision had read them. A failure here is logged and skipped.\n    $tf = Get-Date\n    try {\n        $chart = "data\\text_path.json"\n        $stale = (-not (Test-Path $chart)) -or (((Get-Date) - (Get-Item $chart).LastWriteTime).TotalHours -ge 20)\n        if ($stale -and (Test-Path "scripts\\text_path.py")) {\n            & $py scripts\\text_path.py 2>&1 | Select-Object -Last 3 | Add-Content $log\n            Log ("STEP f path         {0:n0}s" -f ((Get-Date) - $tf).TotalSeconds)\n        } else {\n            Log "STEP f path         the chart is less than 20 hours old"\n        }\n    } catch {\n        Log ("STEP f path SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $tf).TotalSeconds, $_)\n    }\n\n    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)\n    exit 0')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

