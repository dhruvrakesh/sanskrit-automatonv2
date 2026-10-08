#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs20_2026_10_08.py  DOCS20_2026_10_08

Appends to docs/PLATFORM_2026-10-04.md (section 23), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: why the Ganita translation looked stuck, the spend cap on the
dashboard (scripts/patch_live_budget_2026_10_08.py), and what the scheduled jobs did overnight.
Marker-idempotent per file, backup first.

  python scripts/patch_docs20_2026_10_08.py --check
  python scripts/patch_docs20_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS20_2026_10_08"

PLATFORM = """

## 23. A stopped run that looked stuck; the spend cap on the dashboard (DOCS20_2026_10_08)

**Ganita was not stuck; its run had died.** Checked 2026-10-08 07:05 UTC.
- **No job.** /api/jobs/running answered 0 jobs.
- **A stale file.** data/translation_progress.json was last written 2026-10-07 14:18:05 UTC (19:48 IST): p221.2, 242 of 830 verses, "translating...".
- **No end record.** data/jobs.jsonl has no end record for that run, so it died together with the dashboard. The computer or the dashboard's console was closed that evening; the next maintenance tick was 07:27 IST.
- **A recurring pattern.** Nine earlier runs since 2026-09-08 ended with exit code 3221225786 (0xC000013A: the console was closed or got Ctrl+C): Shatapatha, Karan Aagama, Mallapurana and Ganita.
- **Keep-awake does not help here.** It stops idle sleep while a job runs, but not a closed console or a shutdown.
- **Resume.** Translate resumes where it stopped: verses already translated are skipped.

**The fix (LIVE_BUDGET_2026_10_08).**
- **/api/progress.** It reports such a file as "interrupted" when no translation-family job is unfinished in this dashboard and the file is 20 minutes old. A recent file is left alone, because a run from a terminal writes it too.
- **The Live tab** shows "stopped" with what was done and how to continue.
- **The budget.**
  - **Before.** The cap was $25.00, $22.72 spent, $2.28 left, not paused. /api/budget could already change it, but no page called it.
  - **The Usage tab** now shows spent, cap and left, with a field to set a new cap, and Resume when the cap has paused paid work.
  - **The endpoint** accepts a number above 0 and at most $1000, always closes its connection, and warns when the cap is at or below what is spent.
  - **The log.** Every change is appended to data/budget_changes.jsonl, which is git-ignored.
- **Tested.** tests/test_live_budget_2026_10_08.py (5 tests, all fail before, pass after). In a browser with mocked APIs: the stopped notice renders, and Set cap posts {"budget_usd": 40}; after the reload the panel reads "of $40.00" and keeps "Saved. Cap $40.00, left $17.28."

**Scheduled jobs overnight.**
- **Local maintenance.** It ran on 2026-10-08 at 07:27, 08:22, 09:00 and 12:00 IST. At 11:31 it skipped: no API connectivity.
- **Daily backup.** context_20261008.db was written at 07:27 IST, with integrity ok (docs=66, en_translated=21,915, hi=12,502).
- **Srangam.**
  - **The ten verses.** They are not on the site yet: /texts still shows 1,216 and 439 passages, and search does not find them. The --only SQL files were written but not pasted.
  - **Cron job 9.** Its runs are read with SQL (cron.job_run_details).

**Tests on Windows.** The 4 errors in tests/test_exports_gate_2026_10_07.py were tearDown PermissionErrors: the tests left SQLite connections open, and Windows cannot delete an open file. The tests now close them.
"""

RUNBOOK = """

## When the Live tab says "stopped"; the spend cap (DOCS20_2026_10_08)

- **"Stopped."** The run ended without finishing. Start Translate for that text again: verses already translated are skipped. Keep the dashboard's console open while a translation runs; closing it ends the run (exit code 3221225786).
- **Spend cap.** In the dashboard, open Usage, press Reload, set "New cap" and press Set cap; Resume appears when the cap has paused paid work. From a terminal: `python scripts\\set_budget.py --cap 40 --unpause`.
- **Load the dashboard change.** `python scripts\\patch_live_budget_2026_10_08.py --check`, then the same without `--check`, then restart the dashboard while it is idle.
"""

EP = """

## Addendum 2026-10-08 (10) (DOCS20_2026_10_08)

| # | Item | State |
|---|---|---|
| D1 | Live tab showed a dead run as "Calling API" | Fixed: "stopped" with how to continue (to apply; restart the dashboard) |
| D2 | Spend cap from the dashboard | Added to the Usage tab (to apply) |
| D3 | Runs die when the console closes (nine ended with exit 3221225786 since 2026-09-08; the 2026-10-07 run died with the dashboard) | Open: run the dashboard so a closed window cannot end it (a scheduled task, or pythonw with a log file) |
| G1 | Ten withheld verses | SQL written; paste it (still 1,216 and 439 on the site) |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs20_" + stamp))
        t = p.with_name(p.name + ".tmp_docs20"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
