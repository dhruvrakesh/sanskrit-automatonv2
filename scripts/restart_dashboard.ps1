# Sanskrit Automaton - restart the dashboard DETACHED, then health-check it.
# ASCII ONLY (Windows PowerShell 5.1 reads a BOM-less .ps1 in the system codepage).
#
# NOTE: param() MUST be the first executable statement in a .ps1 - only comments may
# precede it. Putting $ErrorActionPreference above it made PowerShell parse "param" as
# a command call ("Cannot convert System.Object[] to System.Int32"), fixed 2026-08-28.
#
# Why this exists: running "python scripts\dashboard.py" in the foreground blocks the
# terminal, so pressing Ctrl+C to get the prompt back KILLS the server. This starts it
# in its own window, returns the prompt immediately, and verifies the port is live.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
param(
    [int]$Port = 5057,
    [switch]$NoNewWindow
)
$ErrorActionPreference = "Stop"
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
Set-Location $root

Write-Host "[1/3] stopping any listener on port $Port ..."
$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
$pidList   = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
if ($pidList.Count -gt 0) {
    foreach ($procId in $pidList) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
    Write-Host ("      stopped PID(s): " + ($pidList -join ', '))
    Start-Sleep -Seconds 2
} else {
    Write-Host "      nothing was listening"
}

Write-Host "[2/3] starting dashboard (detached) ..."
if ($NoNewWindow) {
    Start-Process -FilePath "python" -ArgumentList "scripts\dashboard.py" `
        -WorkingDirectory $root -WindowStyle Hidden | Out-Null
} else {
    Start-Process -FilePath "powershell" `
        -ArgumentList "-NoExit","-NoProfile","-Command","Set-Location '$root'; python scripts\dashboard.py" `
        -WorkingDirectory $root | Out-Null
}

Write-Host "[3/3] waiting for the port to come up ..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 700
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { $ok = $true; break }
}
if ($ok) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/library" -TimeoutSec 10 -UseBasicParsing
        Write-Host ("OK - dashboard is up (HTTP " + $r.StatusCode + ") at http://127.0.0.1:$Port/") -ForegroundColor Green
    } catch {
        Write-Host "Port is listening but /library did not respond cleanly: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "FAILED - port $Port never came up. Check the new window for a Python traceback." -ForegroundColor Red
    exit 1
}
