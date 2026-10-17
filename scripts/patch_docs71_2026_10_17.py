#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs71_2026_10_17.py  DOCS71_2026_10_17

Records 17 Oct (night): Tier R on the desk and the scholarly English begun at a verse (TIER_R_2026_10_17), and the
plan for the next books (docs/NEXT_BOOKS_2026-10-17.md: the Devimahatmya before Ashtami, the Surya Siddhanta, the
Ganita Yukti Bhasa).

Appends to docs/PLATFORM_2026-10-04.md (section 74), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md (addendum 61),
each needing DOCS70_2026_10_17. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs71_<date>), line
endings kept.

  python scripts/patch_docs71_2026_10_17.py --check
  python scripts/patch_docs71_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS71_2026_10_17"

PLATFORM = """

## 74. Tier R on the desk; the next books (DOCS71_2026_10_17)

**17 Oct (IST, night).** Decided: the working English by Sonnet in one pass (Tier R); the Markandeya Purana's scholarly
English. docs/NEXT_BOOKS_2026-10-17.md has the plan.
- **TIER_R_2026_10_17** (translation_desk.py, dashboard.py, dashboard_static.html): on a text's desk page, the working
  English by Claude Sonnet 5.5 in one pass, the rest or every verse again (the English before kept in
  translation_history), priced at BM1's $0.0052 a verse, the Claude credit shown; /api/translate takes retranslate;
  the scholarly English begins at a verse ("Begin at", --from-ref); Sonnet among the main page's engines, one text at
  a time (Translate All refuses Claude). MT_ENGINE unchanged.
- **Found:** our Markandeya Purana is adhyayas 1 to 15; the Devimahatmya (81 to 93) comes from GRETIL's e-text (1 to
  93, Sansknet, CC BY-NC-SA 4.0) as a witness. The Kashi edition of the Surya Siddhanta in the inbox is a cut-short
  download (no end-of-file marker); GRETIL has Michio Yano's e-text.

**Tests:** `tests/test_tier_r_2026_10_17.py` (8); test_buttons_2026_10_17 and test_bench_gold_fair_2026_10_17 follow
(.bak_tierr_).
"""

RUNBOOK = """

## Tier R; the Devimahatmya from GRETIL (DOCS71_2026_10_17)

1. Tier R: a text's desk page, "The working English by Sonnet in one pass": the rest, or every verse again. It asks,
   bills the Claude credit, stops when the credit does.
2. The Devimahatmya: `python scripts\\etext_witness.py --doc markandeya_purana --url https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_mArkaNDeyapurANa1-93.htm` (the
   preview, free; the file is kept in sources\\markandeya_purana), then
   `python scripts\\etext_witness.py --doc markandeya_purana --file sources\\markandeya_purana\\sa_mArkaNDeyapurANa1-93.htm --write`,
   then `python scripts\\etext_witness.py --doc markandeya_purana --ingest`; `python scripts\\text_path.py`; on the desk
   page of markandeya_purana__w_gretil: Begin at 81.1, Plan them (free), Run.
"""

EP = """

## Addendum 2026-10-17 (61) (DOCS71_2026_10_17)

| # | Item | State |
|---|---|---|
| D4 | Tier R on the desk (TIER_R_2026_10_17) | Built and tested; to apply |
| E3 | The Devimahatmya (MkP 81 to 93) from GRETIL, scholarly | About $25 to $30; before Ashtami (19 Oct) |
| E4 | The Surya Siddhanta: GRETIL's e-text, or the Kashi edition downloaded again | The preview first (free) |
| G1 | The Ganita Yukti Bhasa: restore, vision repair, re-ingest | About $1.4 to $3.0 (Google); its English after |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS70_2026_10_17"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS70_2026_10_17"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS70_2026_10_17")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs71_" + stamp))
        t = p.with_name(p.name + ".tmp_docs71"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
