#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs22_2026_10_08.py  DOCS22_2026_10_08

Records the first C4 steps on the live project (2026-10-08), why the first push looked stuck
and what now shows its progress (PROGRESS_2026_10_08: [m:ss] lines and --status in
scripts/corpus_sync.py), and the job-log test race (JOBLOG_RACE_2026_10_08). Appends to
docs/PLATFORM_2026-10-04.md (section 25), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 12) and docs/CORPUS_MIRROR_2026-10-08.md. Marker-idempotent per file, backup first,
each file's line endings kept.

  python scripts/patch_docs22_2026_10_08.py --check
  python scripts/patch_docs22_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS22_2026_10_08"

PLATFORM = """

## 25. C4 on the live project; a push that looked stuck; a test race (DOCS22_2026_10_08)

**Applied on 2026-10-08.**
- **Releases.** 834c96e3 (LIVE_BUDGET, DOCS20) and f0a212b6 (C4, DOCS21), both pushed.
- **P1 (15:18 IST).**
  - PostgreSQL 17.6, database 93 MB, vector 0.8.0 in public.
  - Schema corpus absent, service_role present.
  - srangam_text_passages 1,655, srangam_passage_vectors 1,655.
- **C4 SQL.** Run in the editor at 15:21: "Query succeeded".
- **The edge function.** Lovable deployed `corpus-ingest` unchanged, with verify_jwt off. Its unsigned test request got 401 "missing or malformed x-corpus-ts", as designed.
- **The signed hello (10:03:54 UTC)** answered `docs_in_mirror: 0`. So the five functions exist, and the PC's secret matches the project's.
- **The first text push.** It finished at 10:09:41 UTC: 343 s and 101.4 MB, with "verify: 317 groups equal, 0 different". It sent:
  - 63 documents;
  - 8,269 entities;
  - 75,734 passages;
  - 13,040 translations (more Hindi than in the morning backup's 12,517, because translation kept running);
  - 32,861 mentions;
  - 44 stories and 767 stages.
- **Vectors for markandeya_purana.** 1,258 in 38 s (16.6 MB), 1 group equal. Next is the M4 gate.

**"Seems stuck."** It was not stuck: it was silent. The text push printed nothing until its summary at the end, and it took almost 6 minutes.
- **Now (PROGRESS_2026_10_08)** a run prints flushed `[m:ss]` lines as it goes:
  - what the mirror holds;
  - each table and document as it is sent, with batch counts and sizes for large ones;
  - every 10 documents compared;
  - the final check.
- **`--status`** compares the mirror's rows with the rows here, per table. It is read-only on both sides, and can run in a second window during a push.
- **Stopping is safe.** Ctrl+C at any point loses nothing: the next run sends only what is missing.

**Test race (JOBLOG_RACE_2026_10_08).**
- **What failed.** `tests/test_export_mode_joblog.py::test_mode_persisted_only_when_set` raised KeyError on Windows.
- **Why.** The dashboard sets `job.ok` before it appends the end record (the `finally:` in `_run_job`). The test slept a fixed 0.3 s while 14 translation jobs kept the machine busy.
- **The fix.** The test now polls the log for both records. Reproduced here by delaying `_persist_job` 0.5 s: it fails before the fix and passes after.
- **The dashboard is unchanged.**
"""

RUNBOOK = """

## Watching a mirror push (DOCS22_2026_10_08)

- **Lines while it runs.** A run prints `[m:ss]` lines: what the mirror holds, each document as it is sent, batches of large ones, and "compared N/63 documents".
- **From a second window.** `python scripts\\corpus_sync.py --status` shows mirror rows against rows here, per table. It is read-only and safe during a push.
- **No new line for several minutes?** Run --status twice, a minute apart. If the mirror's counts rise, it is working. If they do not, press Ctrl+C and run it again; it sends only what is missing.
"""

EP = """

## Addendum 2026-10-08 (12) (DOCS22_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror | Schema applied, function deployed. Text pushed 10:09 UTC (75,734 passages, 13,040 translations, 317 groups equal). markandeya_purana vectors 1,258. Next: M4, then all vectors, then the 2-hourly task |
| C4p | A push showed nothing until its end | Fixed: [m:ss] progress lines and --status (PROGRESS_2026_10_08) |
| T1 | test_export_mode_joblog race on Windows | Fixed in the test (JOBLOG_RACE_2026_10_08); dashboard unchanged |
"""

MIRROR = """

## Watching a push (DOCS22_2026_10_08)

A first push takes minutes. While it runs:
- **The run's own lines.** It prints `[m:ss]` lines: what the mirror holds, each table and document as it is sent, the batches of large ones, every 10 documents compared, and the final check.
- **Status from a second window.** `python scripts\\corpus_sync.py --status` prints, per table, the rows in the mirror against the rows here, with the share. It is read-only on both sides. Equal counts are not proof of equal content; the digest check at the end of an `--apply` run is.
- **Stopping and resuming.** Ctrl+C is safe at any point; the next run sends only what is missing.

Live state on 2026-10-08:
- P1 showed PostgreSQL 17.6, 93 MB, vector 0.8.0 in public, schema corpus absent, and 1,655 published passages with 1,655 vectors.
- C4 was applied at 15:21 IST.
- corpus-ingest was deployed with verify_jwt off. An unsigned request gets 401.
- The signed hello answered docs_in_mirror 0 at 10:03:54 UTC.
- **The text push** finished at 10:09:41 UTC: 343 s, 101.4 MB, 317 groups equal, 0 different. It sent 63 documents, 75,734 passages, 13,040 translations, 8,269 entities, 32,861 mentions, 44 stories and 767 stages.
- **markandeya_purana vectors.** 1,258 in 38 s.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP), (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR)]


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
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs22_" + stamp))
        t = p.with_name(p.name + ".tmp_docs22"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
