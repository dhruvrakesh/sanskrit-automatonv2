#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs59_2026_10_15.py  DOCS59_2026_10_15

Records 15 Oct, night: the canary on claude-sonnet-5-5 (the Hayasirsa: 25 of 31 passed; the gate passes, the cost at
the line; the Karanagama stopped by a dashboard pipeline) and RUN_FIX_2026_10_15 (an unread critic; a pipeline past
its ingest). docs/CANARY_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 62), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 49), each needing DOCS58_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs59_<date>), line endings kept.

  python scripts/patch_docs59_2026_10_15.py --check
  python scripts/patch_docs59_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS59_2026_10_15"

PLATFORM = """

## 62. The canary on claude-sonnet-5-5; RUN_FIX (DOCS59_2026_10_15)

**15 Oct (IST), 16:27 to 16:40.** docs/CANARY_2026-10-15.md has the details.
- **The Hayasirsa** (pages 17-19, and 20.5-21.4 again; the audit on 1 in 3): 31 verses, 25 passed (81%), 5 flagged,
  1 source doubt; $1.63 all in by the rows, $0.052 a verse; 32 to 39 seconds a verse in a window. The gate passes
  (70% passed; no repeated error by the machines' reading), the cost is at the line ($0.05; about $0.046 expected at
  the whole's 1 audit in 10). It goes on to the whole.
- **The Karanagama** stopped before its first verse: a dashboard pipeline job was making its working English.
- **RUN_FIX_2026_10_15 (scholar_translate.py):** parse_json reads the first whole JSON object whatever follows it; a
  Claude critic not answering in JSON is asked once more; an answer still unread is kept (unparsed_<doc>.jsonl
  beside the run's log) and named in the row's doubts (3 of 29 critiques; 20.6 and 20.8 were flagged for that
  alone). A running pipeline job whose output has reached "Translate <doc>" or "Export <doc>" no longer stops a run
  (it writes no Sanskrit); queued, earlier, or unknown, it stops it as before.
- **The credit:** $186.25 left after the canary; about $100 for the two texts' rest.

**Tests:**
- `tests/test_run_fix_2026_10_15.py` (12);
- `test_claude_engine_2026_10_15` (a critic is asked once more) and `test_audit_2026_10_15` (its replay chain ends at
  the .bak_runfix_ copy) follow.
"""

RUNBOOK = """

## A scholarly run that stops (DOCS59_2026_10_15)

- "the dashboard changes <doc> now (...)": see the dashboard's jobs (`Invoke-RestMethod
  http://127.0.0.1:5057/api/jobs/running`, read-only). A pipeline that is translating or exporting no longer stops a
  run (RUN_FIX_2026_10_15); anything else that changes the text does. Run the same command again when it is done.
- "this run's --max-usd ... is reached": the same command again goes on (--fill-engine); the cap is a window's.
- "the critic's answer could not be read" in a verse's doubts: the answer is in data\\scholar\\unparsed_<doc>.jsonl.
  Redo that verse alone, as 20.6 was: `--only-page 20 --only-idx 6 --redo --fill-engine --audit-every 1`.
- Watch every window with `--status` (free); a person reads the flagged and the source doubts (`--report`).
"""

EP = """

## Addendum 2026-10-15 (49) (DOCS59_2026_10_15)

| # | Item | State |
|---|---|---|
| AG1 | The canary | The Hayasirsa passed (25 of 31); the Karanagama's to run again after RUN_FIX |
| RF1 | An unread critic; a pipeline past its ingest (RUN_FIX_2026_10_15) | Built and tested |
| AG2 | The Hayasirsa whole (about 1,387 verses left) | Three windows: pages 17-61, 62-110, 111-189 |
| AG2b | The Karanagama whole (1,018) | After its canary: pages 27-79, 80-122, 123-183 |
| CE5 | Prompt caching of the draft's system prompt | Left for after the Hayasirsa (about 7%, some $7) |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS58_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS58_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS58_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs59_" + stamp))
        t = p.with_name(p.name + ".tmp_docs59"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
