#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs69_2026_10_17.py  DOCS69_2026_10_17

Records 17 Oct: BM3's check read (docs/BM3_CHECK_2026-10-17.md), the SOP drafted (docs/SOP_TRANSLATION_2026-10-17.md),
and the translation desk (TRANSLATION_DESK_2026_10_17, docs/TRANSLATION_DESK_2026-10-17.md).

Appends to docs/PLATFORM_2026-10-04.md (section 72), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 59), each needing DOCS68_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs69_<date>), line endings kept.

  python scripts/patch_docs69_2026_10_17.py --check
  python scripts/patch_docs69_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS69_2026_10_17"

PLATFORM = """

## 72. BM3's check; the SOP; the translation desk (DOCS69_2026_10_17)

**17 Oct (IST).** docs/BM3_CHECK_2026-10-17.md, docs/SOP_TRANSLATION_2026-10-17.md and
docs/TRANSLATION_DESK_2026-10-17.md have the details.
- **BM3's check** (the pilot's 40 units, the scholarly arm's notes withheld; 74 readings, $3.14; BM3 so far $6.40):
  the scholarly pipeline above Sonnet alone 0.51 [0.35, 0.67] (gemini-2.5-pro) and 0.52 [0.35, 0.68] (Claude Opus),
  against 0.80 and 0.79 with the notes shown: its lead was its notes. Both above flash with or without them (0.68 to
  0.79). Major errors per ten verses (withheld): scholar 0.24 / 0.71, sonnet1 1.90 / 0.71, flash 4.52 / 3.81.
- **The SOP (a draft until BM2):** the gate (the register and the path before any translation); Tier W, the working
  English (flash, one pass, a draft); Tier R, Sonnet in one pass per job (a proposal, after BM2; MT_ENGINE unchanged);
  Tier S, the scholarly edition (the flags of 15 Oct, planned then capped, about $0.043 a verse, its value its notes);
  a person's review; publishing; money; the benchmarks as the regression test.
- **TRANSLATION_DESK_2026_10_17** (scripts/translation_desk.py; dashboard.py and dashboard_static.html by
  scripts/patch_translation_desk_2026_10_17.py): /desk, every text by its stage (the scholarly edition, ready,
  translated: to judge, done, the reading first, not charted) with its next step, the caps and Chart the path again;
  /desk/<doc>, the scholarly English's steps (Plan them, free; Run, the plan's own cap, at most $12.00 a press;
  Status, Report, Triage, free); the guard: /api/translate and /api/pipeline/translate-doc answer 409 for a text whose
  path says the reading comes first, the buttons ask and go on with force; a chip of each text's path on the main
  page. The chart is read again only when its file changes. No database change; MT_ENGINE unchanged.

**Tests:** `tests/test_translation_desk_2026_10_17.py` (13); test_bench_duel_desk_2026_10_16 and
test_bench_gold_desk_2026_10_16 follow (.bak_transdesk_).
"""

RUNBOOK = """

## The translation desk (DOCS69_2026_10_17)

1. http://127.0.0.1:5057/desk: every text by its stage. If the chart is old (three days or more), Chart the path
   again (free) or `python scripts\\text_path.py`.
2. A text's page (/desk/<doc>): its path's next step first (the repair page for the reading first).
3. The scholarly English: Plan them (free), read the verdict and the price, then Run these verses (the plan's own cap,
   at most $12.00; it asks). Then Triage and Report (free); accept or reject by hand:
   `python scripts\\scholar_translate.py --doc ... --review 1.1.8,1.1.9 --verdict accept --by Dhruv`.
4. Translate on a text the path holds: the button says why and asks; going on sends force.
5. The SOP: docs/SOP_TRANSLATION_2026-10-17.md.
"""

EP = """

## Addendum 2026-10-17 (59) (DOCS69_2026_10_17)

| # | Item | State |
|---|---|---|
| BM3c | BM3's check, the notes withheld | Done (40 units, $3.14): the scholarly lead over Sonnet was its notes |
| SOP | The translation SOP (docs/SOP_TRANSLATION_2026-10-17.md) | Drafted; confirmed after BM2 |
| D0-D2 | The guard, the chips, the desk, the scholarly steps (TRANSLATION_DESK_2026_10_17) | Built and tested; to apply |
| D3 | The review in the browser (accept, reject, glossary) | Next; free |
| D4 | BM2's 40 units read; Tier R decided (the credit ends 11 Nov) | A person's time; your decision |
| D5 | S4, the scholarly layer on the site | Design first; after Srangam's TEST_WAIT and D3 |
| D6 | The source-first queue (34 repairs, vision about $24 then about $71 of English) | Needs the cap and an order, yours |
| D7 | The chart charted again after OCR, repair and ingest jobs | Next; free |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS68_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS68_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS68_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs69_" + stamp))
        t = p.with_name(p.name + ".tmp_docs69"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
