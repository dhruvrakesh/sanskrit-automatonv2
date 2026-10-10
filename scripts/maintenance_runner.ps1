$ErrorActionPreference = "Stop"
# Sanskrit Automaton - idle maintenance (2026-08-28). ASCII ONLY: Windows
# PowerShell 5.1 reads a BOM-less .ps1 in the system codepage, so Unicode
# box-drawing/arrows in comments corrupt the parse (that broke the first version).
# Keeps the search index + QA scores current using spare runtime, but ONLY when
# safe: the dashboard must be idle (no DB-write contention with the single writer)
# and the Gemini API must be reachable. Every step is idempotent + incremental.
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$log  = "D:\backups\maintenance_log.txt"
New-Item -ItemType Directory -Force -Path "D:\backups" | Out-Null
Set-Location $root
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
# MAINT_CONVERGE_2026_09_12: stamp each line at the time it is WRITTEN. This
# captured $stamp once at script start, so every line of an hour-long run
# carried the same second and the log read as if nothing took any time.
function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}

# DESK_HEAL_2026_10_10: the guard below lets maintenance run beside an OCR job. When that OCR ends the
# dashboard may start its ingest and translation stage, and a person may start a run meanwhile. So
# between the steps it looks again, and leaves the rest for the next tick when a database writer has
# started. (A writer that starts inside a step waits on SQLite's lock: WAL, busy_timeout 30-60 s.)
function Test-Writer($after) {
    try {
        $now = Invoke-RestMethod -Uri "http://127.0.0.1:5057/api/jobs/running" -TimeoutSec 6
    } catch {
        return $false
    }
    $w = @(@($now.running) | Where-Object { $_.kind -ne "ocr" })
    if ($w.Count -eq 0) { return $false }
    $what = (@($w | Select-Object -First 3 | ForEach-Object { [string]$_.kind + " " + [string]$_.doc }) -join ", ")
    Log ("SKIP rest after step " + $after + ": the dashboard started " + $what + " - the next tick goes on")
    return $true
}

# Always record that the runner fired, before any guard, so a silent task is
# never a mystery again.
Log "TICK - maintenance runner started (user=$env:USERNAME)"

# Guard 1: dashboard must be idle. If any job is running or queued, skip this tick.
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:5057/api/jobs/running" -TimeoutSec 6
    $busy = [int]$r.count
    # DESK_HEAL_2026_10_10: an OCR job writes page files only, never the database, so it does not hold
    # maintenance. One OCR of 1,983 pages (Yoga Vasistha) held every run from 2026-10-09 15:00: no new
    # vectors, QA or names for a day.
    $writers = @(@($r.running) | Where-Object { $_.kind -ne "ocr" })
    if ($writers.Count -gt 0) { Log "SKIP: dashboard busy ($busy job(s) running/queued)"; exit 0 }
    if ($busy -gt 0) { Log "dashboard runs $busy OCR job(s) only (page files, not the database) - ok to maintain" }
    else { Log "dashboard idle (0 jobs) - ok to maintain" }
} catch {
    Log "dashboard not reachable - proceeding (no in-process writer)"
}

# Guard 2: Gemini API must be reachable (embeddings/entities need it).
$net = Test-NetConnection generativelanguage.googleapis.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $net) { Log "SKIP: no API connectivity"; exit 0 }

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }

Log "START maintenance"
$t0 = Get-Date
try {
    # a) refresh QA scores (FREE, no API) - keeps translation_qa current
    $ta = Get-Date
    & $py scripts\qa_scan.py --db data\context.db --lang en --write 2>&1 | Add-Content $log
    Log ("STEP a qa_scan      {0:n0}s" -f ((Get-Date) - $ta).TotalSeconds)
    if (Test-Writer "a") { exit 0 }   # DESK_HEAL_2026_10_10

    # b) incremental semantic index (CHEAP) - embeds only new/changed verses
    $tb = Get-Date
    & $py scripts\build_embeddings.py --db data\context.db 2>&1 | Add-Content $log
    Log ("STEP b embeddings   {0:n0}s" -f ((Get-Date) - $tb).TotalSeconds)
    if (Test-Writer "b") { exit 0 }   # DESK_HEAL_2026_10_10

    # b2) BRAIN_ITEMS_2026_10_07: stories, found episodes and drawn images into the Ask index (CHEAP,
    #     incremental: only new or changed items are embedded; retired ones are dropped)
    #     A failure here is logged and skipped; it never stops step c.
    $tb2 = Get-Date
    try {
        & $py scripts\brain_items.py --db data\context.db 2>&1 | Add-Content $log
        Log ("STEP b2 brain items {0:n0}s" -f ((Get-Date) - $tb2).TotalSeconds)
    } catch {
        Log ("STEP b2 brain items SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $tb2).TotalSeconds, $_)
    }
    if (Test-Writer "b2") { exit 0 }   # DESK_HEAL_2026_10_10

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
    & $py scripts\extract_entities.py --db data\context.db --limit 1500 2>&1 | Add-Content $log
    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)

    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)
    exit 0
} catch {
    Log ("FAIL after {0:n0}s: {1}" -f ((Get-Date) - $t0).TotalSeconds, $_)
    exit 1
}
