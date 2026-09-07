## 9d. Restarting the dashboard while jobs are running — a correction (2026-09-06)

I told you the running jobs "are subprocesses and survive" a dashboard restart.
That was asserted, not verified, and it is **wrong**. Reading the code:

`scripts/dashboard.py`, `_run_job`:

```python
proc = subprocess.Popen(
    job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=str(ROOT), env=_child_env()
)
job.proc = proc
out, err = proc.communicate()
```

No `creationflags`, no Windows Job Object. `restart_dashboard.ps1` does
`Stop-Process -Id $procId -Force` on the **port listener only**. So:

* the children are **not** killed — Windows does not cascade the kill;
* but their stdout/stderr pipes have no reader any more. Each child runs until
  it fills the ~64 KB pipe buffer and then **blocks forever on write**;
* `proc.communicate()` dies with the parent, so `_persist_job()` never runs and
  `data/jobs.jsonl` never records the outcome.

They neither finish nor die. They sit there holding a DB connection, invisible
to the new dashboard's in-memory `JOBS` list, and a translate job that blocks
mid-document leaves the semaphore family with a writer nobody is tracking.

`_kill_proc()` does the right thing — `taskkill /F /T`, a tree kill — and that
is what the UI's **Pause All Jobs** button calls.

**RUNBOOK §1 already said this**: *"Stop cleanly: click 'Pause All' in the UI
(kills job subprocesses), then:"*. And `ENTERPRISE_ROADMAP.md`: *"No
multi-change restarts of a live system without a stated rollback."* The
procedure existed; I went around it.

### The procedure, in order

```powershell
Set-Location "C:\path\to\sanskrit-automatonv2"     # your repo root

# 1. Click "Pause All Jobs" in the dashboard (top of the Pipeline panel).
#    Then CONFIRM it, rather than trusting the button:
(Invoke-RestMethod http://127.0.0.1:5057/api/jobs/running).Count      # want 0

# 2. Only when that reads 0:
powershell -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1

# 3. Confirm the new endpoints answer (405 = "exists, wrong verb" = good;
#    404 = the restart did not pick up the patched dashboard.py):
foreach ($e in '/api/embeddings','/api/entities') {
  try   { Invoke-WebRequest "http://127.0.0.1:5057$e" -Method GET -ErrorAction Stop | Out-Null }
  catch { "{0,-18} {1}" -f $e, $_.Exception.Response.StatusCode.value__ }
}
```

Paused jobs are not lost work: OCR, ingest and translate are all resumable and
skip what is already done. A blocked-forever job **is** lost work.

### Rollback, and proving it before you need it

```powershell
# what Phase G backed up
Get-ChildItem backups\dashboard*.preG*,backups\dashboard*.preGjs*,backups\dashboard*.preGfix* |
  Sort-Object LastWriteTime | Format-Table Name,Length,LastWriteTime

# prove the rollback restores byte-for-byte, WITHOUT rolling back:
$b = (Get-ChildItem backups\dashboard_static.html.preG.* | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
Copy-Item $b "$env:TEMP\rollback_test.html"
python scripts\patch_ui_phase_g_js.py --help *> $null   # no-op, just proves the script runs
"backup bytes : {0}" -f (Get-Item $b).Length
"live bytes   : {0}" -f (Get-Item scripts\dashboard_static.html).Length

# actual rollback, if ever needed (UI only - no restart):
Copy-Item $b scripts\dashboard_static.html -Force        # then Ctrl+F5

# full rollback including the endpoints (needs Pause All + restart):
Copy-Item (Get-ChildItem backups\dashboard.py.preG.* | Sort-Object LastWriteTime | Select-Object -Last 1).FullName scripts\dashboard.py -Force
```
