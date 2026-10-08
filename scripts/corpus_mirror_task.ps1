$ErrorActionPreference = "Continue"
# Sanskrit Automaton - corpus mirror tick (CORPUS_MIRROR_C4_2026_10_08). ASCII ONLY: Windows
# PowerShell 5.1 reads a BOM-less .ps1 in the system codepage.
# Sends to the private PostgreSQL mirror only what changed since the last run
# (docs/CORPUS_MIRROR_2026-10-08.md). READ-ONLY on data\context.db, so it is safe while a
# translation runs and it does not wait for the dashboard to be idle. At most --max-mb per tick;
# the next tick carries on. Exits 0 without doing anything until CORPUS_SYNC_SECRET is in .env.
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$log  = "D:\backups\corpus_mirror_log.txt"
New-Item -ItemType Directory -Force -Path "D:\backups" | Out-Null
Set-Location $root
function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}
Log "TICK - corpus mirror (user=$env:USERNAME)"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }
$t0 = Get-Date
& $py scripts\corpus_sync.py --apply --if-configured --max-mb 80 2>&1 | ForEach-Object { "$_" } | Add-Content $log
$rc = $LASTEXITCODE
Log ("DONE - corpus mirror rc={0} {1:n0}s" -f $rc, ((Get-Date) - $t0).TotalSeconds)
exit $rc
