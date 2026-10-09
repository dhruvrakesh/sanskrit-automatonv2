#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_media_task_2026_10_09.py  (2026-10-09)  CORPUS_MEDIA_C8_2026_10_09

Two additions to scripts/corpus_mirror_task.ps1, the two-hourly SanskritCorpusMirror tick:
  1. after the mirror, the pictures and graphic novels: scripts\\corpus_media.py --apply
     --if-configured --max-mb 40 (it exits 0 quietly until C8 is applied and corpus-media is
     deployed, and when nothing changed it only asks the site what it has);
  2. the PC is kept awake while the tick runs (SetThreadExecutionState, ES_CONTINUOUS |
     ES_SYSTEM_REQUIRED, released at the end), because the tick of 2026-10-08 night took 7.5 h when
     the PC slept in the middle of it. It does not wake a sleeping PC; it may sleep again afterwards.
The task's exit code is the mirror's when that failed, else the pictures'.
Anchored, all-or-nothing, marker-idempotent; the file stays ASCII with its own line endings
(CRLF); backup .bak_mediatask_<date>. Needs scripts/corpus_media.py.

  python scripts/patch_media_task_2026_10_09.py --check
  python scripts/patch_media_task_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "CORPUS_MEDIA_C8_2026_10_09"
TASK = Path("scripts/corpus_mirror_task.ps1")

EDITS = [
    ("header",
     "# the next tick carries on. Exits 0 without doing anything until CORPUS_SYNC_SECRET is in .env.\n",
     "# the next tick carries on. Exits 0 without doing anything until CORPUS_SYNC_SECRET is in .env.\n"
     "# " + MARK + ": then the pictures and graphic novels (scripts\\corpus_media.py,\n"
     "# docs/MEDIA_AND_CORNER_2026-10-09.md), at most 40 MB per tick; it exits 0 quietly until C8 is\n"
     "# applied and corpus-media is deployed. The PC is kept awake while the tick runs (the tick of\n"
     "# 2026-10-08 night took 7.5 h because the PC slept in the middle); it may sleep again after.\n"),
    ("keep awake",
     'Log "TICK - corpus mirror (user=$env:USERNAME)"\n',
     'Log "TICK - corpus mirror (user=$env:USERNAME)"\n'
     "# Keep the PC awake for this tick: ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x1).\n"
     "$awake = $false\n"
     "try {\n"
     "    Add-Type -Namespace SanskritAutomaton -Name Power -ErrorAction Stop -MemberDefinition "
     "'[DllImport(\"kernel32.dll\")] public static extern uint SetThreadExecutionState(uint esFlags);'\n"
     "    [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483649)\n"
     "    $awake = $true\n"
     "} catch { Log (\"keep-awake unavailable: \" + $_.Exception.Message) }\n"),
    ("pictures step",
     'Log ("DONE - corpus mirror rc={0} {1:n0}s" -f $rc, ((Get-Date) - $t0).TotalSeconds)\n'
     "exit $rc",
     'Log ("DONE - corpus mirror rc={0} {1:n0}s" -f $rc, ((Get-Date) - $t0).TotalSeconds)\n'
     "$t1 = Get-Date\n"
     "& $py scripts\\corpus_media.py --apply --if-configured --max-mb 40 2>&1 | ForEach-Object { \"$_\" } | Add-Content $log\n"
     "$rcm = $LASTEXITCODE\n"
     'Log ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)\n'
     "if ($awake) { [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483648) }\n"
     "if ($rc -ne 0) { exit $rc }\n"
     "exit $rcm"),
]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not TASK.exists():
        print("FAIL: %s not found. Run from the repo root." % TASK); return 2
    if not Path("scripts/corpus_media.py").exists():
        print("REFUSE: scripts/corpus_media.py is missing (release it first). Nothing written."); return 1
    raw = TASK.read_bytes()
    if MARK.encode() in raw:
        print("skip %s (already carries %s)" % (TASK, MARK)); return 0
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    text = raw.decode("ascii").replace("\r\n", "\n")
    for name, anchor, new in EDITS:
        c = text.count(anchor)
        if c != 1:
            print("REFUSE: anchor '%s' found %d times (want 1). Nothing written." % (name, c)); return 1
        text = text.replace(anchor, new, 1)
    data = text.replace("\n", nl).encode("ascii")
    if a.check:
        print("CHECK OK: %s gets the pictures step and the keep-awake (%d -> %d bytes). Nothing written."
              % (TASK, len(raw), len(data)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(TASK, TASK.with_name(TASK.name + ".bak_mediatask_" + stamp))
    tmp = TASK.with_name(TASK.name + ".tmp_mediatask")
    tmp.write_bytes(data)
    os.replace(tmp, TASK)
    print("patched %s" % TASK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
