#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs61_2026_10_15.py  DOCS61_2026_10_15

Records 15 Oct, about 18:55 IST: Gemini checks a Claude English (the flash judge on every verse; Opus for the audit and
the second judge), and REJUDGE_2026_10_15 (--rejudge: the Gemini judge reads again what a Claude judge read).
docs/GEMINI_CHECKS_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 64), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 51), each needing DOCS60_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs61_<date>), line endings kept.

  python scripts/patch_docs61_2026_10_15.py --check
  python scripts/patch_docs61_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS61_2026_10_15"

PLATFORM = """

## 64. Gemini checks a Claude English; the re-judge (DOCS61_2026_10_15)

**15 Oct (IST), about 18:55.** docs/GEMINI_CHECKS_2026-10-15.md has the details.
- **The decision (Dhruv):** "Gemini being used to check makes sense." A Claude run of the scholarly English: the
  translator and its critic claude-sonnet-5-5; the judge of every verse gemini-2.5-flash (the default
  --judge-engine: another family, about $0.0002 a call); the audit and the second judge claude-opus-5-5
  (--compare-engine), on the credit. Google's spend cap gates these runs again.
- **The Claude-only windows** (18:47 to the switch, Haiku judging) were not stuck: 82 verses by 18:58, 65 passed,
  none failed, $0.034 a verse.
- **REJUDGE_2026_10_15 (CF2), --rejudge:** the latest rows of --engine that a Claude judge read (unchanged, not
  reviewed) are read again by the Gemini judge, and their status decided again as a run decides it; a new version
  of each, the same English; a verse redone meanwhile, or a judge that does not answer, leaves the row alone.

**Tests:**
- `tests/test_rejudge_2026_10_15.py` (7);
- test_claude_first_2026_10_15 (its replay chain ends at the .bak_rejudge_ copy) follows.
"""

RUNBOOK = """

## A Claude run, checked by Gemini (DOCS61_2026_10_15)

- **The standing flags:** `--engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5`, and the
  default --judge-engine (gemini-2.5-flash). The dry run says "the judge gemini:gemini-2.5-flash (Google's bill, in
  the spend cap); the second judge and the audit anthropic:claude-opus-5-5 (the Claude credit)".
- **The spend cap:** a run stops when Google's spend cap is reached; `set_budget.py` shows it.
- **Rows a Claude judge read:** `--engine anthropic:claude-sonnet-5-5 --rejudge` (a dry run: counted, free), then with
  `--limit 2000 --yes`. Run it when the windows of that text are stopped or done, or let it leave the verses they
  redo alone.
"""

EP = """

## Addendum 2026-10-15 (51) (DOCS61_2026_10_15)

| # | Item | State |
|---|---|---|
| CF2 | --rejudge: a Gemini judge for the rows a Claude judge read (REJUDGE_2026_10_15) | Built and tested |
| CF5 | The standing checks of a Claude run: the flash judge (Gemini), the audit and the second judge (Opus) | Decided 15 Oct |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS60_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS60_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS60_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs61_" + stamp))
        t = p.with_name(p.name + ".tmp_docs61"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
