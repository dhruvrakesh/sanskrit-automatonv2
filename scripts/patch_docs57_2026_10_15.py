#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs57_2026_10_15.py  DOCS57_2026_10_15

Records 15 Oct, evening: the pilot of 15:18 to 15:40 IST (the Hayasirsa 20.5-21.4 on four engines, two of them cut off
by Ctrl-C; the head to head on five spans) and PILOT_FIX_2026_10_15 (an OCR reading's verse number is not a reference;
--fill-engine; --compare-every; a span is its verses; the judge's own model left out of its tally); the hub and the
mirror do not use the Claude key. docs/PILOT_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 60), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 47), each needing DOCS56_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs57_<date>), line endings kept.

  python scripts/patch_docs57_2026_10_15.py --check
  python scripts/patch_docs57_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS57_2026_10_15"

PLATFORM = """

## 60. The pilot of 15 Oct; PILOT_FIX (DOCS57_2026_10_15)

**15 Oct (IST), 15:18 to 15:40.** docs/PILOT_2026-10-15.md has the details.
- **The Hayasirsa 20.5-21.4 on four engines:** claude-sonnet-5-5 (10 verses, 8 passed, $0.036 a verse, about 20
  seconds a verse), claude-sonnet-5-5@medium (10, 8, $0.032), claude-opus-5-5 (10, 7, $0.063, 1.4 minutes),
  gemini-2.5-pro (2 before Ctrl-C, $0.071, 2.4 minutes). The loop waited for the slowest; Ctrl-C stopped all four.
- **The head to head (5 spans):** the Gemini judge's best was Sonnet in 3, and it found no major error in Sonnet's
  (2 each in Opus's and Sonnet@medium's); the Opus judge's best was Opus in 3 (its own model). They agree in 1 of 4.
- **PILOT_FIX_2026_10_15:**
  - scholar_translate.py: an OCR reading's verse_ref is not a reference (page.idx); --fill-engine (this engine's own
    rows as done and as context: a stopped run goes on); --compare-every N (by hash, not by parity);
  - scholar_duel.py: a span is its verses (one span on the page; --pick takes the old name); the tally gives each
    judge's best with its own model left out;
  - test_scholar_2026_10_14: its .gitignore replay ends at .bak_hygiene_ (the failure after 88370ae).
- **The hub and the mirror do not use the Claude key:** only claude_engine.py reads it. The vectors stay on Google's
  embedding model (Anthropic offers none). The scholarly English reaches the site through S4.

**Tests:**
- `tests/test_pilot_fix_2026_10_15.py` (10);
- the replay chain of `test_claude_engine_2026_10_15` ends at the .bak_pilotfix_ copies.
"""

RUNBOOK = """

## Engines side by side, without stopping them (DOCS57_2026_10_15)

1. Start each run in its own window (Start-Process powershell -ArgumentList "-NoExit", ...): its progress shows, and
   Ctrl-C in one window stops only that run.
2. A run that stopped goes on with the same command and `--fill-engine` (no `--redo`, which redoes everything).
3. Never set MT_ENGINE to an anthropic: engine: the working translation would fall back to echo.
"""

EP = """

## Addendum 2026-10-15 (47) (DOCS57_2026_10_15)

| # | Item | State |
|---|---|---|
| CE2 | The head to head, blind | The Hayasirsa read on 5 spans; the Karanagama and gemini-2.5-pro's 8 verses to finish; then the person's picks |
| PF1 | An OCR reading's verse number is not a reference | Built and tested (PILOT_FIX_2026_10_15) |
| PF2 | --fill-engine, --compare-every | Built and tested |
| PF3 | A judge's own model left out of its tally | Built and tested |
| AG2 | The Hayasirsa (1,437 verses) and the Karanagama (1,043) whole | After the picks: about $90 on Sonnet, $155 on Opus, by the pilot |
| AG4 | The 139 and 172 passages left out as OCR debris | A vision repair; some are the editor's English notes |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS56_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS56_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS56_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs57_" + stamp))
        t = p.with_name(p.name + ".tmp_docs57"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
