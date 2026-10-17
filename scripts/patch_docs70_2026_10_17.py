#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs70_2026_10_17.py  DOCS70_2026_10_17

Records 17 Oct (evening): BM2's first reading (docs/BM2_FIRST_READING_2026-10-17.md), the scholarly books and the
edition's format (SCHOLAR_EDITION_2026_10_17, docs/EDITIONS_2026-10-17.md), the main page's buttons
(BUTTONS_2026_10_17, docs/BUTTONS_2026-10-17.md), the repair's next step (REPAIR_NEXT_2026_10_17) and BM2's fair
comparison (BENCH_GOLD_FAIR_2026_10_17).

Appends to docs/PLATFORM_2026-10-04.md (section 73), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md (addendum 60),
each needing DOCS69_2026_10_17, and an addendum to docs/SOP_TRANSLATION_2026-10-17.md (needing
TRANSLATION_DESK_2026_10_17). Marker-idempotent per file, all-or-nothing, backup first (.bak_docs70_<date>), line
endings kept.

  python scripts/patch_docs70_2026_10_17.py --check
  python scripts/patch_docs70_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS70_2026_10_17"

PLATFORM = """

## 73. BM2's first reading; the scholarly edition; the buttons; the repair's next step (DOCS70_2026_10_17)

**17 Oct (IST, evening).** docs/BM2_FIRST_READING_2026-10-17.md, docs/EDITIONS_2026-10-17.md and
docs/BUTTONS_2026-10-17.md have the details.
- **BM2, 24 units read blind:** the reader's best was Sonnet in one pass in 50% (by verses), flash 19%, the published
  English 19%, the scholarly English (its notes withheld) 8%; scholar over sonnet1 0.13 [0.00, 0.33]; sonnet1 over
  flash 0.72 [0.50, 0.91]. The judges' best was the reader's at or near chance (0.08 and 0.12 against the pilot's
  readings, with the notes shown; 0.23 and 0.32 of the units against the check's, as the reader read).
- **BENCH_GOLD_FAIR_2026_10_17** (scripts/bench_gold.py, dashboard.py): the report sets the reader beside the judges
  as the reader read (judges_as_read) as well as beside the pilot.
- **SCHOLAR_EDITION_2026_10_17** (export_html.py --scholar; dashboard.py, dashboard_static.html): the scholarly
  English in the exporter's edition, its notes and doubts as each chapter's notes, a dagger on what a person has not
  read, the working English marked where there is none; Export As "The scholarly edition"; the desk's "Make the
  edition (free)" and /desk/<doc>/edition. The first: the Hayasirsa Pancaratra (1,431 verses).
- **BUTTONS_2026_10_17** (dashboard.py, dashboard_static.html): Translate All OCR'd retired (advance_pipeline.py, 8 Sep:
  22 texts ingested again from Tesseract's pages and translated whatever their path); Ingest and Full ask first for a
  text with English (reingest_pages.py is the safe way); Full asks the path's question; Ingest All leaves and names
  the texts with English.
- **REPAIR_NEXT_2026_10_17** (repair_text.py): "nothing holds it" no longer says "translate it" for a Tesseract
  reading whose debris is moderate or material and whose scan is here: the path's next step (the pages vision has not
  read; the re-ingest of the changed pages). Found on the Padma Purana's Patala Khanda (vision stopped at its cap
  with 218 of 364 pages read).
- **Found:** the Ganita Yukti Bhasa's reading is Tesseract's only (474 of its English passages carry [ILLEGIBLE]); a
  flash verse of the Markandeya Purana (page 4, passage 8) carries an invented gloss with a QA of 1.0.

**Tests:** `tests/test_scholar_edition_2026_10_17.py` (7), `tests/test_buttons_2026_10_17.py` (7),
`tests/test_repair_next_2026_10_17.py` (5), `tests/test_bench_gold_fair_2026_10_17.py` (3); the replay chains of
test_translation_desk_2026_10_17 (.bak_scholaredition_) and test_read_in_2026_10_13 (.bak_repairnext_) follow.
"""

RUNBOOK = """

## The scholarly edition; the buttons; the repair's next step (DOCS70_2026_10_17)

1. The edition of a text with scholarly English: its desk page, "Make the edition (free)", then "Open the newest";
   or Export As "The scholarly edition"; or
   `python scripts\\export_html.py --db data\\context.db --doc HAYASHIRSHA_PANCARATRA --scholar --sanskrit --side-by-side`.
2. Translate All OCR'd is retired; the desk has each text's next step.
3. Ingest or Full on a text with English asks first: the Repair page's re-ingest of the changed pages (the plan free)
   is the safe way.
4. BM2: read on (/benchmarks/bm2), then `python scripts\\bench_gold.py --report` (free): both comparisons.
"""

EP = """

## Addendum 2026-10-17 (60) (DOCS70_2026_10_17)

| # | Item | State |
|---|---|---|
| BM2 | Your blind reading | 24 units read: Sonnet in one pass first (50%), the scholarly English without notes last (8%); 16 more of the 40 to read |
| BM2f | The judges as the reader read (BENCH_GOLD_FAIR_2026_10_17) | Built and tested; to apply |
| E1 | The scholarly edition (SCHOLAR_EDITION_2026_10_17) | Built and tested; the Hayasirsa's made; to apply |
| B1 | The buttons (BUTTONS_2026_10_17) | Built and tested; to apply |
| R1 | The repair's next step (REPAIR_NEXT_2026_10_17) | Built and tested; to apply |
| D4 | Tier R, Sonnet in one pass for the working English | Recommended by BM1, BM3 and BM2; your decision; the credit ends 11 Nov |
| E2 | The next scholarly book (the Markandeya Purana about $43 to $52, the Sandilya Bhakti Sutra about $19 to $35) | Your choice; the desk plans it free |
| G1 | The Ganita Yukti Bhasa's vision repair (about $1.4 to $3.0) | Its register's "complete" to be reopened; your decision |
"""

SOP = """

## Addendum (17 Oct, evening): BM2's first reading (DOCS70_2026_10_17)

docs/BM2_FIRST_READING_2026-10-17.md. A person read 24 units blind: Sonnet in one pass was the best in 50% (by verses),
flash 19%, the published English 19%, the scholarly English read without its notes 8%.
- **Tier R is recommended** for the working English, a job at a time (the engine `anthropic:claude-sonnet-5-5` given to
  the job; `MT_ENGINE` unchanged): the reader, both judges of BM3 and BM1's chrF agree, at flash's price. Your
  decision; I am Claude, and the arm is Claude's.
- **Tier S is read with its notes.** Its English without them is the reader's least preferred: it puts its
  explanations in the notes. The scholarly edition (SCHOLAR_EDITION_2026_10_17) prints them; a short gloss inline is
  one variable to measure before it is changed.
- **The judges are a screen, not a verdict:** their best was this reader's at or near chance.
- **"Done" is not "correct":** a flash verse of the Markandeya Purana with an invented gloss passed with a QA of 1.0;
  the Ganita Yukti Bhasa, "complete" in the register, is a Tesseract reading with 474 [ILLEGIBLE] passages in its
  English. A book is made from a clean reading (the gate, section 1) and read by a person (section 5).
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS69_2026_10_17"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS69_2026_10_17"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS69_2026_10_17"),
           (Path("docs/SOP_TRANSLATION_2026-10-17.md"), SOP, "TRANSLATION_DESK_2026_10_17")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs70_" + stamp))
        t = p.with_name(p.name + ".tmp_docs70"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
