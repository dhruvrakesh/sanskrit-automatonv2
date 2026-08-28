$ErrorActionPreference = "Stop"
# ── Sanskrit Automaton — idle maintenance (2026-08-28) ────────────────────────
# Keeps the SEARCH INDEX and QA SCORES current using spare PC runtime, but ONLY
# when it is safe: the dashboard must be idle (no active jobs → no DB-write
# contention with the single writer) and the Gemini API must be reachable.
# Every step is idempotent + incremental (embeds only NEW verses, re-scores QA,
# retries empty entity rows), so a no-op run is cheap. All output is logged.
$root = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$log  = "D:\backups\maintenance_log.txt"
New-Item -ItemType Directory -Force -Path "D:\backups" | Out-Null
Set-Location $root
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
function Log($m) { Add-Content $log "[$stamp] $m" }

# Guard 1 — dashboard must be idle. If any job is running OR queued, skip this
# tick (a translation is the single DB writer; maintenance must not contend).
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:5057/api/jobs/running" -TimeoutSec 6
    $busy = [int]$r.count
    if ($busy -gt 0) { Log "SKIP: dashboard busy ($busy job(s) running/queued)"; exit 0 }
    Log "dashboard idle (0 jobs) — ok to maintain"
} catch {
    Log "dashboard not reachable — proceeding (no in-process writer)"
}

# Guard 2 — Gemini API must be reachable (embeddings/entities need it).
$net = Test-NetConnection generativelanguage.googleapis.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $net) { Log "SKIP: no API connectivity"; exit 0 }

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }

Log "START maintenance"
try {
    # a) refresh QA scores (FREE, no API) — keeps translation_qa current
    & $py scripts\qa_scan.py --db data\context.db --lang en --write 2>&1 | Add-Content $log
    # b) incremental semantic index (CHEAP) — embeds only new/changed verses
    & $py scripts\build_embeddings.py --db data\context.db 2>&1 | Add-Content $log
    # c) incremental entity layer (MODERATE) — new verses + retry prior empties
    & $py scripts\extract_entities.py --db data\context.db --retry-empty 2>&1 | Add-Content $log
    Log "DONE maintenance"
    exit 0
} catch {
    Log "FAIL: $_"
    exit 1
}
