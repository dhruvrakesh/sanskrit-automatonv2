#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_index_task_every_2026_11_18.py  (2026-11-18)  VAMSA_EVERY_2026_11_18

P2a's last step: the scheduled task (scripts\\corpus_mirror_task.ps1, its index_sync.py --apply --if-configured) sends
the dynasties of every work read (--dynasty-works every). Apply it ONLY after Srangam's DYNASTIES_WORKS_2026_11_18 is
published (the Dynasties page loading one work at a time), and in the same sitting as the first
index_sync.py --dynasty-works every --apply; else the next scheduled run takes the 14 works of G6 off the site again.
Needs index_sync.py with VAMSA_SITE_2026_11_18 (the option). Undo: the .bak_indexevery_<date> copy.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_indexevery_<date> copies.

  python scripts\\patch_index_task_every_2026_11_18.py --check
  python scripts\\patch_index_task_every_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_EVERY_2026_11_18'
TAG = 'indexevery'
FILES = ['scripts/corpus_mirror_task.ps1']
NEEDS = {'scripts/corpus_mirror_task.ps1': 'INDEX_SITE_2026_10_25'}
REQUIRES = {'scripts/index_sync.py': 'VAMSA_SITE_2026_11_18'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_mirror_task.ps1', 1, 'Log ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)\n$t2 = Get-Date\n& $py scripts\\index_sync.py --apply --if-configured 2>&1 | ForEach-Object { "$_" } | Add-Content $log\n$rci = $LASTEXITCODE\nLog ("DONE - index genealogies rc={0} {1:n0}s" -f $rci, ((Get-Date) - $t2).TotalSeconds)',
     'Log ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)\n$t2 = Get-Date\n# VAMSA_EVERY_2026_11_18: the dynasties of every work read (index_sync.py --dynasty-works every), from the day the\n# site\'s Dynasties page loads one work at a time (Srangam\'s DYNASTIES_WORKS_2026_11_18); without it this run would\n# take the 14 works of G6 off the site again.\n& $py scripts\\index_sync.py --apply --if-configured --dynasty-works every 2>&1 | ForEach-Object { "$_" } | Add-Content $log\n$rci = $LASTEXITCODE\nLog ("DONE - index genealogies rc={0} {1:n0}s" -f $rci, ((Get-Date) - $t2).TotalSeconds)')


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

