$ErrorActionPreference = "Continue"
# Sanskrit Automaton - the Researchers' Corner, the desk's round (CORNER_C9_2026_10_09). ASCII ONLY:
# Windows PowerShell 5.1 reads a BOM-less .ps1 in the system codepage.
# Takes up to 3 requests that researchers and editors made on the site and an editor approved, and
# carries each one out with the desk's own scripts (scripts\corner_worker.py,
# docs/RESEARCHERS_CORNER_2026-10-09.md); the results go to the site at once, as drafts. When nothing
# is waiting it only tells the site it came by. It exits 0 quietly until C9 is applied and
# corpus-desk is deployed. One run at a time (data\corner_worker.lock); the PC is kept awake while
# it runs. Registered as the task SanskritCornerWorker, every 10 minutes.
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$log  = "D:\backups\corner_worker_log.txt"
New-Item -ItemType Directory -Force -Path "D:\backups" | Out-Null
Set-Location $root
function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}
# Keep the PC awake for this round: ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x1).
$awake = $false
try {
    Add-Type -Namespace SanskritAutomaton -Name Power -ErrorAction Stop -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
    [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483649)
    $awake = $true
} catch { Log ("keep-awake unavailable: " + $_.Exception.Message) }
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }
$t0 = Get-Date
$out = & $py scripts\corner_worker.py --apply --if-configured --max 3 2>&1 | ForEach-Object { "$_" }
$rc = $LASTEXITCODE
# a round with nothing to do writes one line; a round that did something writes all it said
if ($out -match "^\s+#\d+") { $out | Add-Content $log }
Log ("ROUND - corner rc={0} {1:n0}s {2}" -f $rc, ((Get-Date) - $t0).TotalSeconds, (($out | Select-Object -Last 1) -join ""))
if ($awake) { [void][SanskritAutomaton.Power]::SetThreadExecutionState([uint32]2147483648) }
exit $rc
