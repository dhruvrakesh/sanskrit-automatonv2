#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs58_2026_10_15.py  DOCS58_2026_10_15

Records 15 Oct, evening: the decision (claude-sonnet-5-5 for the Hayasirsa Pancaratra and the Karanagama) and its
guardrails; AUDIT_2026_10_15 (--audit-every: Gemini's critic reads one sentence in N of a Claude run and decides its
status; --status). docs/SONNET_RUN_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 61), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 48), each needing DOCS57_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs58_<date>), line endings kept.

  python scripts/patch_docs58_2026_10_15.py --check
  python scripts/patch_docs58_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS58_2026_10_15"

PLATFORM = """

## 61. The two Agamas on claude-sonnet-5-5; the audit (DOCS58_2026_10_15)

**15 Oct (IST), evening.** docs/SONNET_RUN_2026-10-15.md has the details.
- **The decision (Dhruv):** claude-sonnet-5-5 (effort high, its own) for the Hayasirsa Pancaratra and the Karanagama:
  $0.036 a verse, about 20 seconds; the judge of the other family read it best in 3 of 5 spans, with no major error.
  The evidence is ten verses of one text, so it stands on guardrails: a canary (the first patala of each, the audit on
  1 in 3, a gate: 70% passed after the audit, no repeated error, $0.05 a verse at most), the audit on 1 in 10 and the
  second judge on 1 in 10 in the whole, the caps, --fill-engine, append-only rows, a person's review, a backup, the
  release before the run, --status.
- **AUDIT_2026_10_15 (scholar_translate.py):** --audit-every N: in a Claude run gemini-2.5-pro's critic reads the last
  version of one sentence in N (by hash); its reading is the last critique ("by") and decides the status; it does not
  revise. --status: per engine, the verses of those ready, passed, flagged, source doubts, stale, audited, $, the last
  row; and the credit. The NEXT line keeps --audit-every and --min-quality.
- **The ranges:** the Hayasirsa from page 17 (pages 6-7 are its table of contents; 1,418 verses at --min-quality 0.5),
  the Karanagama from page 27 (1,019); about $88 of the credit and $10 of Google's for the two.

**Tests:**
- `tests/test_audit_2026_10_15.py` (9);
- the replay chain of `test_pilot_fix_2026_10_15` ends at the .bak_audit_ copy.
"""

RUNBOOK = """

## A long scholarly run (DOCS58_2026_10_15)

1. Back up first, under the run's name: `python scripts\\db_backup.py data\\context.db
   D:\\backups\\context_pre_sonnet_20261015.db`.
2. The canary: a few pages with `--audit-every 3`; read the flagged verses and the audits (`--report`) before the
   whole.
3. The whole: one window a range (Start-Process powershell -ArgumentList "-NoExit", ...), each with `--fill-engine
   --audit-every 10 --compare-every 10` and its own `--max-usd`.
4. Watch from another window: `--status` (free). A window that stopped goes on with its own command.
"""

EP = """

## Addendum 2026-10-15 (48) (DOCS58_2026_10_15)

| # | Item | State |
|---|---|---|
| CE4 | The engine for the Agamas: claude-sonnet-5-5 | Decided 15 Oct; guardrails in docs/SONNET_RUN_2026-10-15.md |
| AU1 | An independent reading of a Claude run (--audit-every) | Built and tested (AUDIT_2026_10_15) |
| AU2 | --status, to watch a run | Built and tested |
| AG2 | The Hayasirsa (1,418) and the Karanagama (1,019) whole | The canary first; then three windows a text |
| AG3 | The Tantrik Texts vol. I (2,538 verses) | After its re-ingest; about $91 of the credit left after AG2 |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS57_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS57_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS57_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs58_" + stamp))
        t = p.with_name(p.name + ".tmp_docs58"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
