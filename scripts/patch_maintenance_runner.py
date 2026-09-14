#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_maintenance_runner.py  (2026-09-12)  MAINT_CONVERGE_2026_09_12

THE MEASUREMENT
---------------
D:\\backups\\maintenance_log.txt, over its whole history:

    START maintenance   41
    DONE  maintenance    0
    FAIL                 0

The context maintenance job has started forty-one times and finished zero
times. It has never logged a failure either, because the task's PT1H
ExecutionTimeLimit kills the process before either the DONE line or the
catch block can run. Windows records SCHED_S_TASK_TERMINATED and nothing
else, which is why this was invisible until the log was read.

WHY IT CANNOT FINISH
--------------------
Step (c) is `extract_entities.py --retry-empty`. Measured against the live
database, with the script's own WHERE filters applied:

    translated passages it selects with --retry-empty : 6,295
      of which genuinely unprocessed (ents NULL or '') :   809
      of which already processed, result '[]'          : 5,486

A verse that contains no named entity returns '[]'. It will return '[]'
again next time, and the time after that. --retry-empty re-selects all
5,486 of them on EVERY run, for ever. So 87% of each hour is spent
re-confirming that verses with no names have no names, at batch=10 that
is 630 API calls, and at Gemini-2.5-Flash latencies for a ten-verse
extraction that lands at or past the one-hour wall. Terminated. Repeat.

Nothing was lost. extract_entities commits after every batch - its own
docstring says "commits every batch, so Ctrl+C then re-run continues" -
so the terminations wasted API budget and wall-clock, they did not
destroy work. That is the one piece of good news here.

WHAT CHANGES
------------
1. --retry-empty comes off the schedule. It is a recovery tool for a
   specific past failure (JSON parses that silently dropped a batch), not
   a heartbeat. The remaining real work is 809 rows, about 81 calls, call
   it three minutes - so this job should log DONE for the first time in
   its life. The manual recovery command is in the block's closing notes.

2. --limit 1500 goes on as a hard ceiling. It does not bind today (the
   set is 809). It binds later, when translation grows the corpus, and it
   is the difference between a tick that ends cleanly and a tick that
   gets killed.

3. Each step is timed and logged. When something does run long again, the
   log will name it in one line instead of requiring this archaeology.

4. Log() stamps the CURRENT time. It was capturing $stamp once at script
   start, so every line of an hour-long run carried the same second -
   which is exactly why the log looked like nothing was taking any time.

The task's PT1H limit is deliberately NOT changed. With the re-work gone
the run is minutes, and raising a limit to accommodate a job that should
not be slow would hide the next problem rather than surface it.

Run from the repo root:  python scripts/patch_maintenance_runner.py
Add --check to verify anchors without writing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARK = "MAINT_CONVERGE_2026_09_12"
RUNNER = Path("scripts/maintenance_runner.ps1")

LOG_OLD = '''$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
function Log($m) { Add-Content -Path $log -Value "[$stamp] $m" }'''
LOG_NEW = '''$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
# MAINT_CONVERGE_2026_09_12: stamp each line at the time it is WRITTEN. This
# captured $stamp once at script start, so every line of an hour-long run
# carried the same second and the log read as if nothing took any time.
function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}'''

STEPS_OLD = '''Log "START maintenance"
try {
    # a) refresh QA scores (FREE, no API) - keeps translation_qa current
    & $py scripts\\qa_scan.py --db data\\context.db --lang en --write 2>&1 | Add-Content $log
    # b) incremental semantic index (CHEAP) - embeds only new/changed verses
    & $py scripts\\build_embeddings.py --db data\\context.db 2>&1 | Add-Content $log
    # c) incremental entity layer (MODERATE) - new verses + retry prior empties
    & $py scripts\\extract_entities.py --db data\\context.db --retry-empty 2>&1 | Add-Content $log
    Log "DONE maintenance"
    exit 0
} catch {
    Log "FAIL: $_"
    exit 1
}'''

STEPS_NEW = '''Log "START maintenance"
$t0 = Get-Date
try {
    # a) refresh QA scores (FREE, no API) - keeps translation_qa current
    $ta = Get-Date
    & $py scripts\\qa_scan.py --db data\\context.db --lang en --write 2>&1 | Add-Content $log
    Log ("STEP a qa_scan      {0:n0}s" -f ((Get-Date) - $ta).TotalSeconds)

    # b) incremental semantic index (CHEAP) - embeds only new/changed verses
    $tb = Get-Date
    & $py scripts\\build_embeddings.py --db data\\context.db 2>&1 | Add-Content $log
    Log ("STEP b embeddings   {0:n0}s" -f ((Get-Date) - $tb).TotalSeconds)

    # c) incremental entity layer (MODERATE) - NEW verses only.
    #
    # MAINT_CONVERGE_2026_09_12. This carried --retry-empty, which also
    # re-selects every verse whose ents is '[]'. A verse with no names
    # returns '[]' every time, so that set never shrinks: 5,486 rows
    # re-processed on every run, for ever, about 87% of the budget spent
    # re-confirming nothing. 630 API calls at batch=10 ran past the task's
    # PT1H limit and the run was killed - 41 starts, 0 completions, no
    # error logged because a killed process cannot log one.
    #
    # Without it the set is the 809 genuinely unprocessed verses. --limit
    # is a ceiling that does not bind today and will bind later, when
    # translation grows the corpus. To recover verses that were dropped by
    # an old JSON-parse failure, run --retry-empty BY HAND with a --limit.
    $tc = Get-Date
    & $py scripts\\extract_entities.py --db data\\context.db --limit 1500 2>&1 | Add-Content $log
    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)

    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)
    exit 0
} catch {
    Log ("FAIL after {0:n0}s: {1}" -f ((Get-Date) - $t0).TotalSeconds, $_)
    exit 1
}'''


def replace_one(text: str, old: str, new: str, label: str):
    n = text.count(old)
    if n != 1:
        return text, ["%s: matched %d times, expected exactly 1" % (label, n)]
    return text.replace(old, new), []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not RUNNER.exists():
        print("FAIL: %s not found. Run from the repo root." % RUNNER)
        return 2

    raw = RUNNER.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf > lf else "\n"

    src = RUNNER.read_text(encoding="utf-8")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if "--retry-empty" not in src:
        print("FAIL: --retry-empty is not in the runner. Either this was already")
        print("      changed by hand, or this is not the file the task runs.")
        return 2

    problems: list[str] = []
    src, p = replace_one(src, LOG_OLD, LOG_NEW, "Log timestamp"); problems += p
    src, p = replace_one(src, STEPS_OLD, STEPS_NEW, "maintenance steps"); problems += p

    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1

    # The file's own header insists on ASCII: PowerShell 5.1 reads a BOM-less
    # .ps1 in the system codepage, and non-ASCII in a comment broke the parse
    # once already. Enforce that rather than trusting myself to have typed it.
    try:
        src.encode("ascii")
    except UnicodeEncodeError as e:
        print("REFUSING TO WRITE: the result is not pure ASCII (%s)." % e)
        print("  This file's header explains why that breaks PowerShell 5.1.")
        return 1

    if args.check:
        print("Both anchors matched exactly once, result is pure ASCII.")
        print("--check: nothing written.")
        return 0

    RUNNER.write_text(src, encoding="ascii", newline=newline)
    after = RUNNER.read_bytes()
    print("Patched: %s  (2 edits, endings preserved as %s, +%d lines)"
          % (RUNNER, "CRLF" if newline == "\r\n" else "LF",
             after.count(b"\n") - raw.count(b"\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
