#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs38_2026_10_10.py  DOCS38_2026_10_10

Records the desk as found at midday on 10 Oct and its repair: DESK_HEAL_2026_10_10 (the dashboard, its
page and the maintenance task) and HUB_V2_2026_10_10 (the Srangam Hub). docs/DESK_HEAL_2026-10-10.md has
the findings and the design.
Appends to docs/PLATFORM_2026-10-04.md (section 41), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 28) and docs/SYNC_COMMANDS_2026-10-09.md (section 13), each needing DOCS37_2026_10_10.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs38_<date>), line endings kept.

  python scripts/patch_docs38_2026_10_10.py --check
  python scripts/patch_docs38_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS38_2026_10_10"

PLATFORM = """

## 41. The desk, healed: the hub, the Library, the queue, maintenance (DOCS38_2026_10_10)

**10 Oct, midday (IST). Reported:**
- The hub showed the dashboard "down (ReadTimeout)" and refused Start ("already running").
- The Library's "Add Hindi" on Karan Aagama said "queued" and nothing followed.
- Usage showed "undefined"; History showed held runs as "fail"; the Queue's list was empty.

**Found** (`docs/DESK_HEAL_2026-10-10.md` section 2):
- **The translator worked:** runs ended ok at 09:39.
- **The hub made the dashboard look down.**
  - Hub v1 checked it with `/api/status`, the dashboard's heaviest read (7.2 s), every 5 s, with a
    2.5 s limit.
  - The dashboard's own page asks the same read every 5 s while a job runs. The reads overlapped.
- **Karan Aagama is held by the debris guard (exit 3, 0.5 s).** Its Tesseract OCR carries debris and
  its 183 page PDFs are in the inbox. The next step is OCR consensus (a plan; no spend).
- **Ganita Yukti Bhasa:** its last English run translated 1 of 180; 180 were below the OCR quality bar.
- **Usage** read the old cache's fields, not cost_tracker's summary.
- **The brain:** SanskritMaintenance skipped six times from 9 Oct 15:00, held by one OCR of 1,983
  pages (Yoga Vasistha, at page 498). An OCR job writes page files only.
- **The network:** the 10:32 mirror and pictures runs failed on DNS (`getaddrinfo`). The 08:32 run was
  clean: 392 groups equal, 0 different.

**DESK_HEAL_2026_10_10** (`scripts/patch_desk_heal_2026_10_10.py`):
- **`dashboard.py`** (takes effect on a restart, when idle):
  - `/api/status` is built once at a time, shared by callers that arrive meanwhile, and kept 10 s.
    A job that ends, an import, or `?fresh=1` clears it.
  - `/api/health` is new and answers from memory.
  - The Library says why a press cannot help (held; nothing left; below the OCR bar), and follows the
    run a button starts to its outcome.
- **`dashboard_static.html`** (takes effect on a reload):
  - Usage reads cost_tracker's summary.
  - History tells held and nothing apart from fail; a row opens to the run's last lines; the tab loads
    when opened.
  - The Queue is never empty.
  - There is one status read at a time; Refresh asks for a fresh one.
- **`maintenance_runner.ps1`** (takes effect at the next run): an OCR job no longer holds maintenance.
  Between steps it looks again and stops when a database writer has started.

**HUB_V2_2026_10_10** (`scripts/patch_hub_v2_2026_10_10.py`; the hub is its own repository):
- It checks the dashboard with `/api/health` (or `/api/jobs/running`), never `/api/status`. One round of
  checks serves every page for 8 s. A slow dashboard is "busy", not down.
- Start runs `restart_dashboard.ps1`: no window, logs to files.
- The page shows the corpus end to end:
  - this PC: the engine, the database, the brain;
  - the cloud: the mirror, the pictures, the Corner desk, from their own logs and the tasks' next runs;
  - the site and its working corpus.
- The database is counted read-only in the background every 10 min.

**Tests:** `tests/test_desk_heal_2026_10_10.py` (13) and `tests/test_hub_v2_2026_10_10.py` (16). The
existing dashboard tests still pass.
"""

RUNBOOK = """

## The desk, healed; the hub v2 (DOCS38_2026_10_10)

1. **The hub, at once.** From the automaton folder:
   - `python scripts\\patch_hub_v2_2026_10_10.py --check`, then without `--check`.
   - Close the hub's console window and run `start-hub.bat`.
   - The hub works against the dashboard as it runs now.
2. **The dashboard's files.**
   - `python scripts\\patch_desk_heal_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard page and the Library (Ctrl+F5).
   - The maintenance task takes it at its next run.
3. **The dashboard itself, only when idle.** `scripts\\restart_dashboard.ps1` refuses while jobs run.
   - While the OCR of Yoga Vasistha runs (about a day at a page a minute), you can wait: maintenance no
     longer waits for it.
   - Or press Pause All, restart, then start that text's OCR again. It resumes from the missing pages.
4. **A text the Library marks "held":** run the OCR consensus plan it shows (no spend). Translate it
   after the repair, or start the dashboard with `SA_ALLOW_DEBRIS=1` to translate it anyway.
5. **Check:**
   - `Invoke-RestMethod http://127.0.0.1:5057/api/health` (after the restart).
   - `Get-Content D:\\backups\\maintenance_log.txt -Tail 6` (after the next tick).
"""

EP = """

## Addendum 2026-10-10 (28) (DOCS38_2026_10_10)

| # | Item | State |
|---|---|---|
| D1 | The dashboard: one status read at a time, `/api/health`, the Library says why and follows its runs, Usage, History, Queue | Built and tested (DESK_HEAL_2026_10_10). Next: patch; restart when idle |
| D2 | Maintenance beside an OCR job, looking again between steps | Built and tested. Next: patch (takes effect at the next run) |
| H2 | The Srangam Hub v2: the corpus end to end (this PC, the cloud, the site); light checks; detached Start | Built and tested (HUB_V2_2026_10_10). Next: patch; restart the hub; commit in the hub's repository |
| O1 | Karan Aagama's source | Held by the debris guard. Next: the OCR consensus plan (no spend), then translate |
| O2 | Ganita Yukti Bhasa | Its last English run: 1 of 180 translated, 180 below the OCR quality bar. Next: re-OCR, not translation |
| C13 | Researchers see the work in progress | As in addendum 27: your paste, when chosen |
"""

SYNC = """

## 13. The desk at a glance: the hub (DOCS38_2026_10_10)

- **Where:** the Srangam Hub (http://127.0.0.1:5050, v2 HUB_V2_2026_10_10). Its middle column shows
  what the mirror, the pictures and the Corner desk last did. Each comes from its own log:
  - `data\\corpus_sync_log.jsonl`: the last run and the last good run, groups equal and different,
    rows sent, a final check that could not run;
  - `data\\corpus_media_log.jsonl`: files on Drive at the end of the run;
  - `data\\corner_worker_log.jsonl`: rounds today, requests, mail.
- **When the tasks run next:** from the Task Scheduler.
- **A network error** (`getaddrinfo`, unreachable, timed out) is marked as such: the next run retries.
- **Without the hub:**
  ```powershell
  Get-Content -Tail 1 -Encoding UTF8 data\\corpus_sync_log.jsonl
  Get-ScheduledTaskInfo -TaskName SanskritCorpusMirror
  ```
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS37_2026_10_10"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS37_2026_10_10"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS37_2026_10_10"),
           (Path("docs/SYNC_COMMANDS_2026-10-09.md"), SYNC, "DOCS37_2026_10_10")]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs.encode() not in raw:
            print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, needs)); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs38_" + stamp))
        t = p.with_name(p.name + ".tmp_docs38"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
