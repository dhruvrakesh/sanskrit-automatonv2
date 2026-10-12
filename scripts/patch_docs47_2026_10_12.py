#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs47_2026_10_12.py  DOCS47_2026_10_12

Records PATH_2026_10_12 (after REINGEST, 9d4eb66): one way forward for every text (scripts/text_path.py); the
Natyasastra's repair that read no page (five pages failed the night before stopped it), now written down and
tried last; the repair's cap that fits its estimate; --withdraw (off the site and out of Ask the Corpus, kept
here; --restore undoes it); the dashboard's /path. docs/PATH_2026-10-12.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 50), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 37), each needing DOCS46_2026_10_12.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs47_<date>), line endings kept.

  python scripts/patch_docs47_2026_10_12.py --check
  python scripts/patch_docs47_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS47_2026_10_12"

PLATFORM = """

## 50. The path of every text (DOCS47_2026_10_12)

**12 Oct, midday (IST), after the release of REINGEST (`9d4eb66`).** docs/PATH_2026-10-12.md has the
details.
- **Asked:** each text fixable, retirable, or a critical edition or better scan to be found. Are we done?
- **The Natyasastra's repair read no page:** five pages vision had failed on the night before came first,
  failed again, and the five-in-a-row stop ended the run. The repair's NEXT also said `--max-usd 1.00`
  under an estimate of $3.08.
- **The site still holds the Tantric Texts' 145 garbage passages** (seven plate pages), until their
  re-ingest is applied and mirrored.

**PATH_2026_10_12:**
- `scripts/text_path.py` (new, read-only) charts one way forward for every text, with its reason in
  numbers, its next command and its cost: use the repair, retire, ingest, repair the scan, find a source,
  translate, translate again, judge a sample, in repair, done. A repair not all in the database goes in
  before anything is translated.
- On the 11 Oct 22:30 backup: 69 texts; 12 use the repair (free), 2 retire, 10 ingest, 28 repair the scan
  (about $12, up to $26 at the dearest text's price, then about $68 of translation), 6 find a source,
  4 translate, 4 judge, 2 in repair (Hayashirsha's database still holds Tesseract's reading on 185 pages),
  1 done, 3 retired.
- The patch:
  - a page vision fails on is written down and tried last, and is left to Tesseract after two failed runs
    (a page below the last one read with no reading counts as failed once); the cap is asked before each page;
  - the repair's cap fits its estimate;
  - `--withdraw` takes a damaged text off the site and out of Ask the Corpus, kept here (`--restore`);
  - the dashboard's `/path`.

**Tests:** `tests/test_path_2026_10_12.py` (28).
"""

RUNBOOK = """

## The path of every text (DOCS47_2026_10_12)

1. **Chart it (free, read-only):** `python scripts\\text_path.py --html exports\\text_path.html`, or
   *Chart the path again* on `http://127.0.0.1:5057/path` (after a restart). One text with every fact:
   `--doc nirukta`.
2. **Follow each text's NEXT**, in the order of the groups. The free ones first: use the repair, retire
   (dry run first), ingest. Then the paid ones, each capped: repair the scan, translate, judge.
3. **Chart it again** after a run: the next step and the price change with what was done (a repaired text's
   own price replaces the corpus price after its first 20 pages).

## Withdraw a damaged text from the site (DOCS47_2026_10_12)

1. `python scripts\\repair_text.py --doc Bodhicaryavatara --withdraw "its text is damaged: a better source is wanted"`
   writes the register; nothing is deleted.
2. **The next full mirror run** (`python scripts\\corpus_sync.py`, then `--apply`; not `--doc`) retires its
   rows on the site. Ask the Corpus here leaves it out at once.
3. **`--restore`** undoes it; the next mirror run sends it back.
"""

EP = """

## Addendum 2026-10-12 (37) (DOCS47_2026_10_12)

| # | Item | State |
|---|---|---|
| R3 | The in-place re-ingest (reingest_pages.py) | **Released** (9d4eb66); the Tantric Texts, Karan and Hayashirsha wait for their translations |
| P1 | The path of every text (text_path.py, /path) | Built and tested (PATH_2026_10_12) |
| P2 | A failed vision page written down, tried last | Built and tested (PATH_2026_10_12) |
| P3 | Withdraw a damaged text from the site (reversible) | Built and tested; the Bodhicaryavatara is the user's decision |
| T2 | The marked passages translated again, then judged again | Next; paid, capped, dry run first |
| B2 | The spend: $45 cap, $32.41 recorded, $55.45 repriced | The user's decision |
| VC1 | Vision's artefacts cleaned before ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS46_2026_10_12"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS46_2026_10_12"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS46_2026_10_12")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs47_" + stamp))
        t = p.with_name(p.name + ".tmp_docs47"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
