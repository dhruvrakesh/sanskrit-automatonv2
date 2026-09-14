#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_block_u_lockfree.py  (2026-09-14)  BLOCKU_LOCKFREE_2026_09_14

Block U gate 1 died on 2026-09-14 09:03 with

    Get-Content : The process cannot access the file
    'D:\\backups\\maintenance_log.txt' because it is being used by another
    process.

followed by three ArgumentNullExceptions, because $logText was null and
[regex]::Matches was then called on it. The block then printed

    START=  DONE=  FAIL=
    STOP: fewer than two starts recorded. This is not the log I measured.

which is a misleading message: the log was fine, it was locked. The scheduled
maintenance task appends to it, so a lock means a run is very probably IN
FLIGHT - which is the one condition under which Block U must not start a
second runner.

Two fixes, both minimal:

  1. ReadShared(): opens the file with FileShare.ReadWrite so a writer holding
     it does not block the read. This is the same discipline the project
     already uses for SQLite - diag_spend_bound.py opens the database
     query-only rather than mode=ro precisely so it can attach to a live
     WAL, and ling_kosha.py uses immutable=1. A log being appended to is the
     same problem.

  2. A null guard after the first read, so a locked log reports itself as a
     locked log instead of as an empty one.

Every Get-Content of $LOG is converted. Get-Item $LOG at lines 168 and 174 is
left alone: it reads directory metadata, not content, and does not lock.
"""

import argparse
import os
import sys

MARK = "BLOCKU_LOCKFREE_2026_09_14"

HELPER = r'''
# BLOCKU_LOCKFREE_2026_09_14 - read a file that another process may be
# appending to. FileShare.ReadWrite is the whole point: without it,
# Get-Content throws IOException the moment the scheduled maintenance task
# holds the log, and every regex against the result then throws
# ArgumentNullException. Returns $null if the file genuinely cannot be read.
function ReadShared {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $fs = $null; $sr = $null
  try {
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
          [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $sr = New-Object System.IO.StreamReader($fs)
    return $sr.ReadToEnd()
  } catch {
    return $null
  } finally {
    if ($sr) { $sr.Dispose() }
    if ($fs) { $fs.Dispose() }
  }
}
'''

A1_OLD = """
$ErrorActionPreference = 'Continue'
$A   = 'D:\\Sanksrit Automatons\\sanskrit-automatonv2'
"""
A1_NEW = """
$ErrorActionPreference = 'Continue'
""" + HELPER + """
$A   = 'D:\\Sanksrit Automatons\\sanskrit-automatonv2'
"""

A2_OLD = """$logText = Get-Content $LOG -Raw
$starts = ([regex]::Matches($logText, 'START maintenance')).Count"""
A2_NEW = """$logText = ReadShared $LOG
if ($null -eq $logText) {
  Write-Host '  STOP: the log is LOCKED by another process, not missing and not' -ForegroundColor Red
  Write-Host '        empty. The scheduled maintenance task appends to it, so a'
  Write-Host '        run is very probably in flight. Starting a second runner'
  Write-Host '        now is exactly what this block must not do. Wait for it.'
  Pop-Location; return
}
$starts = ([regex]::Matches($logText, 'START maintenance')).Count"""

A3_OLD = """$logText = Get-Content $LOG -Raw
$newDones = ([regex]::Matches($logText, 'DONE maintenance')).Count"""
A3_NEW = """$logText = ReadShared $LOG
if ($null -eq $logText) { $logText = '' }
$newDones = ([regex]::Matches($logText, 'DONE maintenance')).Count"""

A4_OLD = "Get-Content $LOG | Select-String -Pattern"
A4_NEW = "((ReadShared $LOG) -split \"`r?`n\") | Select-String -Pattern"

A5_OLD = "$tail = (Get-Content $LOG | Select-Object -Last 6) -join ' '"
A5_NEW = "$tail = (((ReadShared $LOG) -split \"`r?`n\") | Select-Object -Last 6) -join ' '"

PATCHES = [
    (A1_OLD, A1_NEW, "ReadShared helper"),
    (A2_OLD, A2_NEW, "gate 1 read + locked-log guard"),
    (A3_OLD, A3_NEW, "gate 3 read"),
    (A4_OLD, A4_NEW, "control-line listing"),
    (A5_OLD, A5_NEW, "tail for the failure message"),
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

    print("anchor                                  found")
    print("-" * 52)
    ok = True
    for old, _new, name in PATCHES:
        n = src.count(old)
        good = (n == 1) or (name == "control-line listing" and n >= 1)
        print("%-39s %s" % (name, ("OK (%d)" % n) if good else ("MISSING" if n == 0 else "%d TIMES" % n)))
        if not good:
            ok = False
    print("-" * 52)
    if not ok:
        print("FAIL: anchors did not match. Nothing written.")
        return 2
    if a.check:
        print("--check only: nothing written.")
        return 0

    for old, new, name in PATCHES:
        if src.count(old) < 1:
            print("FAIL: anchor %r vanished mid-apply." % name)
            return 2
        src = src.replace(old, new, 1)

    if "Get-Content $LOG" in src:
        print("FAIL: a locking Get-Content of the log survived the patch:")
        for i, line in enumerate(src.split("\n"), 1):
            if "Get-Content $LOG" in line:
                print("  line %d: %s" % (i, line.strip()))
        return 2

    open(a.target, "wb").write(src.replace("\n", nl).encode("utf-8"))
    print("Patched %s (%s endings preserved)" % (os.path.basename(a.target),
                                                 "CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    print("Remaining Get-Item $LOG calls are metadata only and do not lock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())