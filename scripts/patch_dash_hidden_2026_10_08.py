#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_dash_hidden_2026_10_08.py  DASH_HIDDEN_2026_10_08  (ENTERPRISE_PATH D3)

Runs closed when their console closed: nine ended with exit 3221225786 (0xC000013A,
STATUS_CONTROL_C_EXIT) since 2026-09-08, and on 2026-10-07 a run died with the dashboard.
The dashboard ran in a visible window; the runs it starts share that console; closing the
window ended them all.

  scripts/restart_dashboard.ps1  replaced (only if it is exactly the 2026-08-28 version):
      - by default the dashboard runs in a console with no window (cmd /s /c with
        CreateNoWindow), its output in D:\backups\dashboard_logs\dashboard_<stamp>.out.log
        and .err.log (UTF-8, kept 14 days);
      - it refuses to restart or stop while a job is running or queued (-Force overrides);
      - -Status (read-only), -Stop, -Window (the old visible window); -NoNewWindow is accepted.
  scripts/dashboard.py           one anchored insertion before app.run: when
      SA_QUIET_REQUESTS=1 (set only by the launcher) the werkzeug request lines are left out
      of the log. Errors and tracebacks are still written. Nothing else changes.

All-or-nothing: both files are checked before either is written; backups first
(.bak_dashhidden_<date>); dashboard.py is compiled before it replaces the old one; each
file keeps its line endings. Re-running changes nothing.

  python scripts/patch_dash_hidden_2026_10_08.py --check
  python scripts/patch_dash_hidden_2026_10_08.py
Then, with the dashboard idle:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "DASH_HIDDEN_2026_10_08"
PS1 = Path("scripts/restart_dashboard.ps1")
DASH = Path("scripts/dashboard.py")
PS1_OLD_MD5 = "a92ec0e1a778ed17560771730c77392c"     # LF-normalised, the 2026-08-28 version
ANCHOR = "    app.run(host=args.host, port=args.port, debug=False)\n"
INSERT = (
    "    # DASH_HIDDEN_2026_10_08. scripts\\restart_dashboard.ps1 now runs this server with no window\n"
    "    # and its output in a log file. The page polls several times a second, so the launcher asks\n"
    "    # (SA_QUIET_REQUESTS=1) for the per-request lines to be left out. Errors still reach the log.\n"
    "    if os.environ.get(\"SA_QUIET_REQUESTS\") == \"1\":\n"
    "        import logging as _dh_logging\n"
    "        _dh_logging.getLogger(\"werkzeug\").setLevel(_dh_logging.WARNING)\n"
    "        print(\"[log] request lines left out (SA_QUIET_REQUESTS=1); errors are still written\")\n"
)

NEW_PS1 = r'''# Sanskrit Automaton - restart the dashboard DETACHED, then health-check it.
# ASCII ONLY (Windows PowerShell 5.1 reads a BOM-less .ps1 in the system codepage).
#
# NOTE: param() MUST be the first executable statement in a .ps1 - only comments may
# precede it. Putting $ErrorActionPreference above it made PowerShell parse "param" as
# a command call ("Cannot convert System.Object[] to System.Int32"), fixed 2026-08-28.
#
# Why this exists: running "python scripts\dashboard.py" in the foreground blocks the
# terminal, so pressing Ctrl+C to get the prompt back KILLS the server. This starts it
# detached, returns the prompt immediately, and verifies the port is live.
#
# DASH_HIDDEN_2026_10_08 (D3). By default the dashboard now runs in a console that has no
# window, and its output goes to log files. Before, it ran in a visible window, and closing
# that window ended the dashboard AND every run it had started (exit 3221225786, that is
# 0xC000013A, STATUS_CONTROL_C_EXIT; nine runs since 2026-09-08). A console with no window
# cannot be closed by mistake, and the runs the dashboard starts share it.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
#       restart; refuses while a job is running or queued
#   ... -Status       what listens on the port, the jobs, the newest logs; changes nothing
#   ... -Stop         stop it; refuses while a job is running or queued
#   ... -Force        restart or stop even while jobs run (they are cut off: RUNBOOK 9d)
#   ... -Window       the old way: a visible window that must stay open
#   ... -NoNewWindow  accepted as before; it is now the default
#
# Logs: D:\backups\dashboard_logs\dashboard_<yyyyMMdd_HHmmss>.out.log and .err.log, kept
# 14 days. Follow one with:  Get-Content -Wait -Tail 40 -Encoding UTF8 <path>
param(
    [int]$Port = 5057,
    [switch]$NoNewWindow,
    [switch]$Window,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Force,
    [string]$LogDir = "D:\backups\dashboard_logs",
    [int]$KeepDays = 14
)
$ErrorActionPreference = "Stop"
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
Set-Location $root
$script:BusyInfo = $null

function Get-ListenerPids {
    $l = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    return @($l | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Get-Busy {
    # -1 when the dashboard does not answer; otherwise the number of unfinished jobs
    # (running or queued), as maintenance_runner.ps1 reads it.
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/jobs/running" -TimeoutSec 6
        $script:BusyInfo = $r
        return [int]$r.count
    } catch {
        return -1
    }
}

function Show-Busy {
    if ($null -eq $script:BusyInfo) { return }
    foreach ($j in @($script:BusyInfo.running)) {
        Write-Host ("      {0,-8} {1,-18} {2,-28} {3,8}s" -f $j.state, $j.kind, $j.doc, $j.elapsed_s)
    }
}

function Get-Logs {
    if (-not (Test-Path $LogDir)) { return @() }
    return @(Get-ChildItem -Path $LogDir -Filter "dashboard_*.log" -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Descending)
}

if ($Status) {
    $pidList = Get-ListenerPids
    if ($pidList.Count -gt 0) {
        foreach ($procId in $pidList) {
            $cmdLine = ""
            try { $cmdLine = (Get-CimInstance Win32_Process -Filter ("ProcessId=" + $procId)).CommandLine } catch { }
            Write-Host ("listening on port " + $Port + ": PID " + $procId + "  " + $cmdLine)
        }
    } else {
        Write-Host ("nothing is listening on port " + $Port)
    }
    $busy = Get-Busy
    if ($busy -lt 0) {
        Write-Host "the dashboard does not answer /api/jobs/running"
    } else {
        Write-Host ("jobs running or queued: " + $busy)
        Show-Busy
    }
    $logs = Get-Logs
    if ($logs.Count -gt 0) {
        Write-Host "newest logs:"
        foreach ($f in @($logs | Select-Object -First 2)) {
            Write-Host ("      " + $f.FullName + "  " + $f.Length + " bytes  " + $f.LastWriteTime)
        }
    }
    exit 0
}

$busy = Get-Busy
if ($busy -gt 0 -and -not $Force) {
    Write-Host ("REFUSED - " + $busy + " job(s) running or queued:") -ForegroundColor Yellow
    Show-Busy
    Write-Host "Stopping the dashboard now would cut them off (RUNBOOK 9d). Press Pause All in the"
    Write-Host "dashboard and wait for the count to reach 0, or add -Force to cut them off anyway."
    exit 2
}

Write-Host "[1/3] stopping any listener on port $Port ..."
$pidList = Get-ListenerPids
if ($pidList.Count -gt 0) {
    foreach ($procId in $pidList) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
    Write-Host ("      stopped PID(s): " + ($pidList -join ', '))
    Start-Sleep -Seconds 2
} else {
    Write-Host "      nothing was listening"
}
if ($Stop) {
    Write-Host "Stopped. Start it again with scripts\restart_dashboard.ps1" -ForegroundColor Green
    exit 0
}

Write-Host "[2/3] starting dashboard (detached) ..."
$proc = $null
$outLog = $null
$errLog = $null
if ($Window) {
    Write-Host "      in a visible window. Closing that window ends the dashboard and every run it started." -ForegroundColor Yellow
    Start-Process -FilePath "powershell" `
        -ArgumentList "-NoExit","-NoProfile","-Command","Set-Location '$root'; python scripts\dashboard.py" `
        -WorkingDirectory $root | Out-Null
} else {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $cut = (Get-Date).AddDays(-$KeepDays)
    foreach ($old in @(Get-Logs | Where-Object { $_.LastWriteTime -lt $cut })) {
        Remove-Item -LiteralPath $old.FullName -ErrorAction SilentlyContinue
    }
    $stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
    $outLog = Join-Path $LogDir ("dashboard_" + $stamp + ".out.log")
    $errLog = Join-Path $LogDir ("dashboard_" + $stamp + ".err.log")
    $py = (Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $py) {
        Write-Host "FAILED - python is not on PATH." -ForegroundColor Red
        exit 1
    }
    $shell = $env:ComSpec
    if (-not $shell) { $shell = "cmd.exe" }
    # cmd /s /c "<line>" keeps <line> as written, so quoted paths with spaces survive.
    $line = '"' + $py + '" -u scripts\dashboard.py 1>>"' + $outLog + '" 2>>"' + $errLog + '"'
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $shell
    $psi.Arguments = '/d /s /c "' + $line + '"'
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true          # a console with no window: nothing to close by mistake
    # Output to a file is not a console: without this Python writes it in the ANSI code page
    # and the banner's box-drawing characters would stop it at startup.
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8:backslashreplace"
    # The page polls several times a second; leave those request lines out of the log.
    # Errors and tracebacks are still written (dashboard.py, DASH_HIDDEN_2026_10_08).
    $psi.EnvironmentVariables["SA_QUIET_REQUESTS"] = "1"
    $proc = [System.Diagnostics.Process]::Start($psi)
    Write-Host ("      python: " + $py)
    Write-Host ("      log:    " + $outLog)
    Write-Host ("      errors: " + $errLog)
}

Write-Host "[3/3] waiting for the port to come up ..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { $ok = $true; break }
    if ($null -ne $proc -and $proc.HasExited) { break }
}
if ($ok) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/library" -TimeoutSec 10 -UseBasicParsing
        Write-Host ("OK - dashboard is up (HTTP " + $r.StatusCode + ") at http://127.0.0.1:$Port/") -ForegroundColor Green
    } catch {
        Write-Host "Port is listening but /library did not respond cleanly: $_" -ForegroundColor Yellow
    }
    if (-not $Window) {
        Write-Host "It runs with no window. Status: scripts\restart_dashboard.ps1 -Status   Stop: -Stop"
        Write-Host ("Follow its log:  Get-Content -Wait -Tail 40 -Encoding UTF8 '" + $errLog + "'")
    }
} else {
    Write-Host "FAILED - port $Port never came up." -ForegroundColor Red
    if ($Window) {
        Write-Host "Check the new window for a Python traceback."
    } else {
        if ($null -ne $proc -and $proc.HasExited) { Write-Host ("      it exited with code " + $proc.ExitCode) }
        foreach ($f in @($errLog, $outLog)) {
            if ($f -and (Test-Path $f)) {
                Write-Host ("---- last lines of " + $f)
                Get-Content -Tail 25 -Encoding UTF8 $f
            }
        }
    }
    exit 1
}
'''


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def plan():
    """Return ([(path, new_bytes)], messages) or raise SystemExit(2) on any refusal."""
    todo, msgs = [], []
    for p in (PS1, DASH):
        if not p.exists():
            print("FAIL: %s not found. Run from the automaton root." % p); raise SystemExit(2)
    if not NEW_PS1.isascii() or MARK not in NEW_PS1:
        print("FAIL: the embedded launcher is not ASCII or lacks the marker."); raise SystemExit(2)

    raw = PS1.read_bytes()
    if MARK.encode() in raw:
        msgs.append("skip %s (already carries %s)" % (PS1, MARK))
    else:
        md5 = hashlib.md5(raw.replace(b"\r\n", b"\n")).hexdigest()
        if md5 != PS1_OLD_MD5:
            print("FAIL: %s is not the version this patch replaces (md5 %s, expected %s)."
                  " Nothing written." % (PS1, md5, PS1_OLD_MD5)); raise SystemExit(2)
        nl = nl_of(raw)
        todo.append((PS1, NEW_PS1.replace("\n", nl).encode("ascii")))
        msgs.append("replace %s (%s line endings)" % (PS1, "CRLF" if nl == "\r\n" else "LF"))

    raw = DASH.read_bytes()
    if MARK.encode() in raw:
        msgs.append("skip %s (already carries %s)" % (DASH, MARK))
    else:
        nl = nl_of(raw)
        text = raw.decode("utf-8")
        anchor = ANCHOR.replace("\n", nl)
        n = text.count(anchor)
        if n != 1:
            print("FAIL: the anchor occurs %d times in %s (expected 1). Nothing written." % (n, DASH))
            raise SystemExit(2)
        if "import os" not in text and "import os," not in text:
            print("FAIL: %s does not import os. Nothing written." % DASH); raise SystemExit(2)
        new = text.replace(anchor, INSERT.replace("\n", nl) + anchor, 1)
        try:
            compile(new, str(DASH), "exec")
        except SyntaxError as e:
            print("FAIL: the patched %s does not compile: %s. Nothing written." % (DASH, e))
            raise SystemExit(2)
        todo.append((DASH, new.encode("utf-8")))
        msgs.append("insert %d lines in %s before app.run" % (INSERT.count("\n"), DASH))
    return todo, msgs


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    todo, msgs = plan()
    for m in msgs:
        print(m)
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do."); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    try:
        for p, data in todo:
            bak = p.with_name(p.name + ".bak_dashhidden_" + stamp)
            shutil.copy2(p, bak)
            tmp = p.with_name(p.name + ".tmp_dashhidden")
            tmp.write_bytes(data)
            if p.suffix == ".py":
                py_compile.compile(str(tmp), cfile=os.path.join(tempfile.gettempdir(), "dashhidden.pyc"),
                                   doraise=True)
            os.replace(tmp, p)
            done.append((p, bak))
            print("wrote %s (backup %s)" % (p, bak.name))
    except Exception as e:
        print("FAIL while writing: %s: %s. Restoring." % (type(e).__name__, e))
        for p, bak in done:
            shutil.copy2(bak, p); print("restored %s" % p)
        for p, _ in todo:
            t = p.with_name(p.name + ".tmp_dashhidden")
            if t.exists():
                t.unlink()
        return 2
    print("Done. Restart the dashboard while it is idle:")
    print("  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
