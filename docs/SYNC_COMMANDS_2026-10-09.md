# Keeping the site in step with the desk: every command (2026-10-09)

Marker: SYNC_COMMANDS_2026_10_09. Everything below is idempotent: it compares first and sends only what differs, so running it again is harmless. Every PowerShell command runs from `D:\Sanksrit Automatons\sanskrit-automatonv2` unless it says otherwise.

## 1. What travels, and how

| What | From the desk | To the site | Command | On a schedule |
|---|---|---|---|---|
| Texts, passages (Sanskrit, IAST, English), Hindi, names, stories (all statuses), pipeline stages, passage vectors | `data\context.db` | schema `corpus` (private mirror, C4) through `corpus-ingest` | `scripts\corpus_sync.py` | SanskritCorpusMirror, every 2 h (`corpus_mirror_task.ps1`) |
| Pictures (two sizes), graphic novels (plan, pages, cast) | `doc_images`, `doc_novels`, `data\images\` | `corpus.media`, `corpus.novels`; files in the Shared Drive "Srangam corpus media" through `corpus-media` (C8) | `scripts\corpus_media.py` | The same task, after the mirror |
| Researchers' requests and their results | the site → the desk | `corner.requests` (C9) through `corpus-desk` | `scripts\corner_worker.py` | SanskritCornerWorker, every 10 min (`corner_task.ps1`) |
| Published texts (`/texts`, public) | `context.db` | `srangam_texts`, `srangam_text_passages` | `scripts\publish_srangam.py --emit-sql`, then paste the files in the SQL editor | No (a deliberate act) |
| Vectors of published texts | the site | `srangam_passage_vectors` | pg_cron job 9 (04:15 UTC), or C2's R3 by hand | Yes (cloud) |
| Local vectors, names, brain items, checks | `context.db` | (local; the mirror carries them) | SanskritMaintenance, every 3 h when the dashboard is idle | Yes |
| The database backup | `context.db` | `D:\backups\context_<date>.db` | `python scripts\db_backup.py` | SanskritDBBackup, nightly |

## 2. The mirror (C4): `corpus_sync.py`

```powershell
python scripts\corpus_sync.py --hello                       # the function answers: version, documents in the mirror
python scripts\corpus_sync.py                               # plan: what would be sent (nothing is sent)
python scripts\corpus_sync.py --status                      # mirror rows against rows here, per table
python scripts\corpus_sync.py --apply                       # send what differs (ends "verify: N groups equal, 0 different")
python scripts\corpus_sync.py --apply --doc markandeya_purana             # one text only (never retires texts)
python scripts\corpus_sync.py --apply --doc nilamata_seg --tables docs,stories   # one text's stories only (seconds)
python scripts\corpus_sync.py --apply --max-mb 80 --if-configured        # what the task runs
python scripts\corpus_sync.py --sink none --db "D:\backups\context_20261009.db" --immutable   # a dry run on a backup
Get-Content data\corpus_sync_log.jsonl -Tail 3
```

## 3. Pictures and graphic novels (C8): `corpus_media.py`

```powershell
python scripts\corpus_media.py --hello                      # {"fn": "corpus-media c8.1 (...)", "drive": true}
python scripts\corpus_media.py                              # plan: pictures here, renditions to upload, rows to send
python scripts\corpus_media.py --status                     # site: pictures, novels, renditions, Drive folder; here: the same
python scripts\corpus_media.py --apply                      # upload missing renditions, then the rows; retire what is gone
python scripts\corpus_media.py --apply --doc nilamata_seg   # one text (never retires)
python scripts\corpus_media.py --apply --max-mb 40 --if-configured       # what the task runs
Get-Content data\corpus_media_log.jsonl -Tail 3
```

## 4. The Researchers' Corner (C9): `corner_worker.py`

```powershell
python scripts\corner_worker.py --hello                     # {"fn": "corpus-desk c9.1 (...)", "state": {...}}
python scripts\corner_worker.py                             # waiting for an editor / queued / running; when the desk last came
python scripts\corner_worker.py --apply --max 1             # take one approved request now and do it
python scripts\corner_worker.py --apply --max 3 --if-configured          # what the task runs
Start-ScheduledTask -TaskName SanskritCornerWorker          # a round now
Get-Content D:\backups\corner_worker_log.txt -Tail 20
Get-Content data\corner_worker_log.jsonl -Tail 3
```

## 5. The tasks, and their logs

```powershell
Get-ScheduledTask -TaskName "SanskritCorpusMirror","SanskritCornerWorker","SanskritMaintenance","SanskritDBBackup" |
  Get-ScheduledTaskInfo | Format-Table TaskName,LastRunTime,LastTaskResult,NextRunTime -AutoSize
Get-Content D:\backups\corpus_mirror_log.txt -Tail 40 | Select-String "DONE|HELD|ERROR|keep-awake"
Get-Content D:\backups\maintenance_log.txt -Tail 20
Get-Content D:\backups\backup_log.txt -Tail 5
powercfg /requests                                          # during a run: python.exe / powershell.exe under SYSTEM
```

## 6. The checks in the Lovable Cloud SQL editor (read-only, one query per paste)

- **The mirror and the cloud's jobs.** `docs/cloud/OPS_health_2026-10-08.sql`:
  - H1 is cron.
  - H2 is the nightly embed.
  - H3 is passages against vectors of the published texts.
  - H5 to H8 cover the mirror's runs, totals and digests.
- **Pictures and novels.** `docs/cloud/C8_checks_2026-10-09.sql`:
  - D1 is what is on the site.
  - D2 is pictures without both sizes (expect 0).
  - D3 is the space on Drive.
  - D5 is the files no picture uses any more.
- **The Corner.** `docs/cloud/C9_checks_2026-10-09.sql`:
  - D1 is requests by status.
  - D2 is the last 30 requests.
  - D3 is when the desk last came.
  - D4 is today against the cap.
  - D5 is the anthologies.
  - D6 is the events.

## 7. The published texts (`/texts`): a deliberate act, never scheduled

```powershell
python scripts\publish_srangam.py --list
python scripts\publish_srangam.py --doc markandeya_purana --gate-report
python scripts\publish_srangam.py --doc markandeya_purana --emit-sql D:\backups\srangam_sql
Get-Content -Raw -Encoding UTF8 "D:\backups\srangam_sql\markandeya_purana\01_passages.sql" | Set-Clipboard   # paste, run; then the next file
```

After the paste:
- New texts land with `published=false`. Set the flag in the SQL editor:

  ```sql
  UPDATE public.srangam_texts SET published = true WHERE doc_code = '<code>';
  ```
- The night's job 9 embeds the new passages.


## 8. When the mirror stops on a statement timeout (DOCS33_2026_10_09)

The database gives each write 8 seconds (the `authenticator` role). On 9 Oct a batch of 50 vectors took longer; the vector index is 87 MB against 224 MB of shared buffers.

```powershell
python scripts\corpus_sync.py --apply --doc nilamata_seg --tables vectors --batch-kb 120   # about 10 a call
python scripts\corpus_sync.py --apply                                                     # then everything else
```

Client 4.3 (SYNC_SPLIT_2026_10_09) halves a timed-out batch by itself, down to one row, and sends vectors 25 to a call.

## 9. The desk's own report on the site (DOCS33_2026_10_09)

With desk worker 1.1, every 10-minute round tells the site the last run of the mirror and of the pictures (the last line of `data\corpus_sync_log.jsonl` and `data\corpus_media_log.jsonl`).
- **Where editors see it:** the Corner's strip and its Sync tab, with the command to run when a channel is out of step.
- **In the SQL editor:** `SELECT info FROM corner.worker;`


## 10. Corrections and the sleeping desk (DOCS34_2026_10_09)

**The backup.** In section 1 and in `docs/RESEARCHERS_CORNER_2026-10-09.md` section 4, step 1, `db_backup.py` needs a source and a destination:

```powershell
python scripts\db_backup.py "D:\Sanksrit Automatons\sanskrit-automatonv2\data\context.db" "D:\backups\context_$(Get-Date -Format yyyyMMdd_HHmm).db"
powershell -ExecutionPolicy Bypass -File scripts\backup_runner.ps1     # the nightly SanskritDBBackup
```

A name of the form `context_2*.db` is kept with the 14 newest.

**A sleeping PC.**
- The desk works only while the PC is awake. On 9 Oct no round ran from 17:18 to 19:37 IST.
- Task Scheduler makes up a missed mirror run when the PC wakes: the 18:31 run ran at 19:38.
- What to look at:
  - The Corner's strip says "Desk last seen" and when the next round is due.
  - On the desk:

```powershell
Get-ScheduledTask -TaskName SanskritCornerWorker, SanskritCorpusMirror | Get-ScheduledTaskInfo | Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime
Get-Content data\corner_worker_log.jsonl -Tail 3
```
