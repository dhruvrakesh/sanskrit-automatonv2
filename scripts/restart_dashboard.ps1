$ErrorActionPreference = "Stop"
# Sanskrit Automaton - restart the dashboard DETACHED, then health-check it.
# ASCII ONLY (Windows PowerShell 5.1 reads a BOM-less .ps1 in the system codepage).
#
# Why this exists: running "python scripts\dashboard.py" in the foreground blocks the
# terminal, so pressing Ctrl+C to get the prompt back KILLS the server. This starts it
# in its own window, returns the prompt immediately, and verifies the port is live.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
param(
    [int]$Port = 5057,
    [switch]$NoNewWindow   # run hidden instead of in a visible log window
)
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
Set-Location $root

Write-Host "[1/3] stopping any listener on port $Port ..."
$pids = (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).OwningProcess |
        Select-Object -Unique
if ($pids) {
    $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "      stopped PID(s): $($pids -join ', ')"
    Start-Sleep -Seconds 2
} else {
    Write-Host "      nothing was listening"
}

Write-Host "[2/3] starting dashboard (detached) ..."
if ($NoNewWindow) {
    Start-Process -FilePath "python" -ArgumentList "scripts\dashboard.py" `
        -WorkingDirectory $root -WindowStyle Hidden | Out-Null
} else {
    # Visible window keeps the Flask log where you can read it; -NoExit so it stays open.
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
        Write-Host "OK - dashboard is up (HTTP $($r.StatusCode)) at http://127.0.0.1:$Port/" -ForegroundColor Green
    } catch {
        Write-Host "Port is listening but /library did not respond cleanly: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "FAILED - port $Port never came up. Check the new window for a Python traceback." -ForegroundColor Red
    exit 1
}
