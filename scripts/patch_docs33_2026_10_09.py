#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs33_2026_10_09.py  DOCS33_2026_10_09

Records the mirror's stop and recovery of 9 Oct (SYNC_SPLIT_2026_10_09, client 4.3, released 67b45ce3)
with its cause in numbers, the first Corner round trip, and the release STATE_LEARN_2026_10_09 (C10a,
desk worker 1.1, C11, the site's state-aware Corner and Learn), with the order to switch it on.
Appends to docs/PLATFORM_2026-10-04.md (section 36), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 23), docs/RESEARCHERS_CORNER_2026-10-09.md (section 8) and docs/SYNC_COMMANDS_2026-10-09.md
(sections 8 and 9). Needs DOCS32_2026_10_09 in the first four and SYNC_COMMANDS_2026_10_09 in the last.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs33_2026_10_09.py --check
  python scripts/patch_docs33_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS33_2026_10_09"

PLATFORM = """

## 36. The mirror stopped and recovered; the first round trip; state and Learn (DOCS33_2026_10_09)

**The mirror (9 Oct).**
- The 12:32 and 14:32 IST runs stopped at `vectors nilamata_seg: 50 to send` with "corpus_ingest: canceling statement due to statement timeout". A run stops at its first error, so the texts after nilamata_seg were not compared on those two runs.
- Names, passages and mentions had gone through at 12:32.
- **The cause, in numbers:**
  - the `authenticator` role, through which the edge functions write, has `statement_timeout=8s` and `lock_timeout=8s`;
  - `service_role` has no setting of its own, so 8 s is the limit for every desk write;
  - the vector index (HNSW, 22,380 vectors) is 87 MB, the vectors table 181 MB in all, and `shared_buffers` 224 MB, so one batch of 50 inserts took longer than 8 s;
  - no advisory lock was held.
- **The recovery:**
  - 15:29 IST: the 50 vectors went about 10 to a call (`--batch-kb 120`).
  - 15:30: a full run with client 4.3 sent 58 passages, 20 translations, 171 mentions and 399 vectors, and ended "392 groups equal, 0 different".
- **The fix.** SYNC_SPLIT_2026_10_09 (client 4.3, released 67b45ce3): a batch the database cancels for its timeout is sent again in halves, down to one row, and vectors go 25 to a call.

**The first round trip.** Request #1 (story_mine, Markandeya) was asked at 14:58:00 IST, taken at 14:58:18 and done at 14:59:30: 6 episodes proposed, on the site at once, for $0.0341 (estimate $0.09). LOAD_L1 is live: one role check per page.

**STATE_LEARN_2026_10_09** (`docs/RESEARCHER_EXPERIENCE_2026-10-09.md`):
- **C10a:** a request's progress, `started_at` kept, and `corner_request_track`.
- **Desk worker 1.1:**
  - it reports each step;
  - its heartbeat carries the mirror's and the pictures' last run;
  - it stops reporting progress after one failed report.
- **C11:** the `learn` schema (23 quests).
- **The site:**
  - the Corner as it happens: next round, stages, progress, next steps, live refresh, notices; editors get chips and a Sync tab;
  - `/corpus/learn`: quests, XP, levels, badges, toolbox, how the desk works, the editors' Team panel.
- **Tests:** C10a 16, C11 9, worker 22 plus the C9 10 unchanged, site 22 + 13; full site suite 244 passing.
"""

RUNBOOK = """

## State and Learn: switching on (DOCS33_2026_10_09)

The order matters: C10a goes in before the desk gets worker 1.1.
1. **SQL editor.**
   - `docs/cloud/C10a_checks_2026-10-09.sql` P1, then C10a in one paste, then V1-V2.
   - `docs/cloud/C11_checks_2026-10-09.sql` P1-P2, then C11 in one paste, then V1-V3.
2. **The desk.**
   - `python scripts\\patch_corner_worker_state_2026_10_09.py --check`, then without `--check`.
   - Then `python -m unittest tests.test_corner_worker_2026_10_09 tests.test_corner_worker_state_2026_10_09`.
   - Release.
   - The next SanskritCornerWorker round runs 1.1.
3. **Srangam.**
   - `patch_srangam_state_learn_2026_10_09.py --check`, then without `--check`.
   - Typecheck, tests and build.
   - Commit the paths it names, pull before you push, push, then Publish.
4. **Look.**
   - The Corner says "Next round about HH:MM".
   - Editors see the Mirror, Pictures and Desk spend chips and the Sync tab.
   - `/corpus/learn` shows 20 quests to a researcher, 23 to an editor.

**When a mirror run stops with a statement timeout.** The database allows each write 8 seconds.
- Send that table in small batches: `python scripts\\corpus_sync.py --apply --doc <code> --tables vectors --batch-kb 120`.
- Client 4.3 does the halving by itself.
- If one row times out, check for locks and long transactions (`docs/RESEARCHER_EXPERIENCE_2026-10-09.md`; the Sync Console's "Diagnose a timeout").
"""

EP = """

## Addendum 2026-10-09 (23) (DOCS33_2026_10_09)

| # | Item | State |
|---|---|---|
| L1 | Fewer questions per page | Live (e2d53dd): one role check per page |
| S0 | The mirror past a timed-out batch | Live (client 4.3, 67b45ce3); the mirror back in step at 15:30 (392 groups equal, 0 different) |
| C10a, S1 | The Corner as it happens | Built and tested: progress, stages, next steps, live refresh; editors' Sync tab. Next: switch on (RUNBOOK) |
| T1 | Learn: quests, XP, levels, badges, toolbox, Team panel | Built and tested (C11 + the site). Next: switch on |
| C10 | The Corner level with the desk's own pages | Next: story_edit, story_verify, picture_edit, picture_restore, novel_page_edit, picture_ideas, picture_cover, draw again |
| L2 | The first load (entry 491 KB, 173 KB gzip) | Next: measure first |
| T2 | Learn, second round | After C10 |
| R5, B1, P2, R6 | As in addendum 21 | As before |
"""

CORNER = """

## 8. The Corner as it happens; Learn (DOCS33_2026_10_09)

**The first round trip (9 Oct).** Request #1 (story_mine, Markandeya) took 1 min 30 s from the ask to done. Its 6 proposed episodes appeared at once under "Write a proposed episode".

**State (C10a, worker 1.1, the site).**
- The desk tells the site each step of a request. The site shows:
  - the stages with their times and the step;
  - when the next round is due;
  - what to do next.
- Editors see the mirror's and the pictures' last run, both on the strip and on the Sync tab.

**Learn (C11, the site).** `/corpus/learn` teaches every tool with 23 quests. The Corner's quests are checked from its own records, and a quest never starts a paid request.

The design, the rules and the order to switch it on are in `docs/RESEARCHER_EXPERIENCE_2026-10-09.md`.
"""

SYNC = """

## 8. When the mirror stops on a statement timeout (DOCS33_2026_10_09)

The database gives each write 8 seconds (the `authenticator` role). On 9 Oct a batch of 50 vectors took longer; the vector index is 87 MB against 224 MB of shared buffers.

```powershell
python scripts\\corpus_sync.py --apply --doc nilamata_seg --tables vectors --batch-kb 120   # about 10 a call
python scripts\\corpus_sync.py --apply                                                     # then everything else
```

Client 4.3 (SYNC_SPLIT_2026_10_09) halves a timed-out batch by itself, down to one row, and sends vectors 25 to a call.

## 9. The desk's own report on the site (DOCS33_2026_10_09)

With desk worker 1.1, every 10-minute round tells the site the last run of the mirror and of the pictures (the last line of `data\\corpus_sync_log.jsonl` and `data\\corpus_media_log.jsonl`).
- **Where editors see it:** the Corner's strip and its Sync tab, with the command to run when a channel is out of step.
- **In the SQL editor:** `SELECT info FROM corner.worker;`
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS32_2026_10_09"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS32_2026_10_09"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS32_2026_10_09"),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER, "DOCS32_2026_10_09"),
           (Path("docs/SYNC_COMMANDS_2026-10-09.md"), SYNC, "SYNC_COMMANDS_2026_10_09")]


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
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs33_" + stamp))
        t = p.with_name(p.name + ".tmp_docs33"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
