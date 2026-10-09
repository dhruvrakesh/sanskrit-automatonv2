#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs34_2026_10_09.py  DOCS34_2026_10_09

Records the evening of 9 Oct: STATE_LEARN_2026_10_09 live (automaton ffdacb5f, Srangam 84409ca, C11,
desk worker 1.1), the order slip (worker 1.1 went on before C10a was pasted, with no request in
between) and its remedy, the desk asleep from 17:18 to 19:37 IST with the mirror's missed run made up
at 19:38, the first load as measured, and a correction: db_backup.py takes a source and a destination.
Run it AFTER C10a's V1 and V2 pass: its text says C10a went in.
Appends to docs/PLATFORM_2026-10-04.md (section 37), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 24) and docs/SYNC_COMMANDS_2026-10-09.md (section 10). Needs DOCS33_2026_10_09 in each.
Marker-idempotent per file, backup first (.bak_docs34_<date>), each file's line endings kept.

  python scripts/patch_docs34_2026_10_09.py --check
  python scripts/patch_docs34_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS34_2026_10_09"
NEEDS = "DOCS33_2026_10_09"

PLATFORM = """

## 37. State and Learn live; the order slip; the desk asleep (DOCS34_2026_10_09)

**Live on the evening of 9 Oct (IST).**
- 19:44: automaton release ffdacb5f (31 files): STATE_LEARN_2026_10_09 and DOCS33.
- Desk worker 1.1 (md5 e80a552537625743b853e6d7a5eb3d39): 32 tests OK, 2 skipped without a test database.
  - Its first round, at 19:48, ended done.
  - Its heartbeat carries the sync block. The Corner's strip showed "Mirror: in step at 19:38", "Pictures: 114 of 114 files on Drive at 19:38" and "Desk spend: $5.34 of $32 left".
- C11 applied. `/corpus/learn` showed 23 quests to the super admin, two already done from request #1 (40 XP), computed from `corner.requests`.
- 19:47: Srangam 84409ca (12 files), published. The live entry chunk (`index-CNIpR4_Q.js`) carries `/corpus/learn`.

**The order slip.** Worker 1.1 went on before C10a was pasted.
- At about 19:42:
  - P1 said `has_progress` false;
  - V1 returned no row;
  - V2 returned one row (no `corner_request_track`);
  - D1 failed with "column r.progress does not exist".
- The site's call to `corner_request_track` answered 404. The Corner fell back to the C9 view, as designed ("Taken by the desk" without its time).
- No request was taken in between (every round: 0 queued), so no result was overwritten by a progress report.
- C10a then went in (RUNBOOK, "State and Learn: if worker 1.1 went on before C10a").

**The desk asleep.** No Corner round ran from 17:18 to 19:37: the PC was asleep.
- When the PC woke, Task Scheduler made up the missed 18:31 mirror run at 19:38.
  - It ended done with client 4.3: 392 groups equal, 0 different, in 86 s.
  - Pictures: 114 of 114 on Drive.
- `corpus_sync.py --status` then showed all eight tables at 100%: docs 65, entities 8,340, passages 90,192, translations 14,886, mentions 33,183, stories 50, stages 767, vectors 22,380.
- Researchers see a sleeping desk on the Corner's strip ("Desk last seen").

**The first load, as built at 19:47.**
- The entry chunk is 498.92 kB (175.78 kB gzip).
- The largest chunks load only on their own pages:
  - MapboxBujangNetwork 1,616.88 kB (449.26 kB gzip);
  - MapsData 989.35 kB;
  - mermaid.core 537.54 kB;
  - ReadingRoom 434.37 kB.
- This is where L2 starts.

**Correction.** `db_backup.py` takes a source and a destination: `python scripts\\db_backup.py` on its own prints its usage. The nightly SanskritDBBackup had made `D:\\backups\\context_20261009.db` at 06:45 (SYNC_COMMANDS section 10).
"""

RUNBOOK = """

## State and Learn: if worker 1.1 went on before C10a (DOCS34_2026_10_09)

C10a must go in before the desk runs worker 1.1. Without C10a, C9's `corner_desk_report` takes each progress report as the request's result and as a new start.
1. **SQL editor, read-only:** `SELECT id, status FROM corner.requests WHERE status IN ('claimed', 'running');`
2. **No rows:** nothing was touched. Paste C10a (`docs/cloud/C10a_corner_state_2026-10-09.sql`) in one paste, then its V1 and V2.
3. **A request ran under 1.1 before C10a:**
   - Its result is right once it is done, because the done report carries the whole result.
   - Its `started_at` is the time of its last progress report.
   - `corner.events` has one `desk_running` row per report.
   - Nothing needs repairing by hand. Paste C10a as in step 2.

**A backup by hand.** `db_backup.py` takes a source and a destination:

```powershell
python scripts\\db_backup.py "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\data\\context.db" "D:\\backups\\context_$(Get-Date -Format yyyyMMdd_HHmm).db"
powershell -ExecutionPolicy Bypass -File scripts\\backup_runner.ps1     # what SanskritDBBackup runs nightly
```
"""

EP = """

## Addendum 2026-10-09 (24) (DOCS34_2026_10_09)

| # | Item | State |
|---|---|---|
| C10a, S1 | The Corner as it happens | Live: ffdacb5f, Srangam 84409ca, C10a, desk worker 1.1 |
| T1 | Learn: quests, XP, levels, badges, toolbox, Team panel | Live: C11, Srangam 84409ca |
| C10 | The Corner level with the desk's own pages | Next |
| L2 | The first load: entry 498.92 kB (175.78 kB gzip) | Next: measure what the home and corpus pages fetch first |
| T2 | Learn, second round | After C10 |
| R5, B1, P2, R6 | As in addendum 21 | As before |
"""

SYNC = """

## 10. Corrections and the sleeping desk (DOCS34_2026_10_09)

**The backup.** In section 1 and in `docs/RESEARCHERS_CORNER_2026-10-09.md` section 4, step 1, `db_backup.py` needs a source and a destination:

```powershell
python scripts\\db_backup.py "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\data\\context.db" "D:\\backups\\context_$(Get-Date -Format yyyyMMdd_HHmm).db"
powershell -ExecutionPolicy Bypass -File scripts\\backup_runner.ps1     # the nightly SanskritDBBackup
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
Get-Content data\\corner_worker_log.jsonl -Tail 3
```
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/SYNC_COMMANDS_2026-10-09.md"), SYNC)]


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
        if NEEDS.encode() not in raw:
            print("REFUSE: %s has no %s section (apply patch_docs33 first). Nothing written." % (p, NEEDS)); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs34_" + stamp))
        t = p.with_name(p.name + ".tmp_docs34"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
