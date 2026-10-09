$ErrorActionPreference = "Continue"
# Sanskrit Automaton - corpus mirror tick (CORPUS_MIRROR_C4_2026_10_08). ASCII ONLY: Windows
# PowerShell 5.1 reads a BOM-less .ps1 in the system codepage.
# Sends to the private PostgreSQL mirror only what changed since the last run
# (docs/CORPUS_MIRROR_2026-10-08.md). READ-ONLY on data\context.db, so it is safe while a
# translation runs and it does not wait for the dashboard to be idle. At most --max-mb per tick;
# the next tick carries on. Exits 0 without doing anything until CORPUS_SYNC_SECRET is in .env.
# CORPUS_MEDIA_C8_2026_10_09: then the pictures and graphic novels (scripts\corpus_media.py,
# docs/MEDIA_AND_CORNER_2026-10-09.md), at most 40 MB per tick; it exits 0 quietly until C8 is
# applied and corpus-media is deployed. The PC is kept awake while the tick runs (the tick of
# 2026-10-08 night took 7.5 h because the PC slept in the middle); it may sleep again after.
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$log  = "D:\backups\corpus_mirror_log.txt"
New-Item -ItemType Directory -Force -Path "D:\backups" | Out-Null
Set-Location $root
function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}
Log "TICK - corpus mirror (user=$env:USERNAME)"
# Keep the PC awake for this tick: ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x1).
$awake = $false
try {
    Add-Type -Namespace SanskritAutomaton -Name Power -ErrorAction Stop -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
    [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483649)
    $awake = $true
} catch { Log ("keep-awake unavailable: " + $_.Exception.Message) }
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }
$t0 = Get-Date
& $py scripts\corpus_sync.py --apply --if-configured --max-mb 80 2>&1 | ForEach-Object { "$_" } | Add-Content $log
$rc = $LASTEXITCODE
Log ("DONE - corpus mirror rc={0} {1:n0}s" -f $rc, ((Get-Date) - $t0).TotalSeconds)
$t1 = Get-Date
& $py scripts\corpus_media.py --apply --if-configured --max-mb 40 2>&1 | ForEach-Object { "$_" } | Add-Content $log
$rcm = $LASTEXITCODE
Log ("DONE - corpus media rc={0} {1:n0}s" -f $rcm, ((Get-Date) - $t1).TotalSeconds)
if ($awake) { [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483648) }
if ($rc -ne 0) { exit $rc }
exit $rcm
