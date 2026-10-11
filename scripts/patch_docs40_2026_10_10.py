#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs40_2026_10_10.py  DOCS40_2026_10_10

Records the evening of 10 Oct: the request "rather than crashing, the resolution path and action
should be there and then, else we discard that PDF and look for a better resolution", and its answer,
REPAIR_PATH_2026_10_10 (scripts/repair_text.py, scripts/patch_repair_path_2026_10_10.py).
docs/REPAIR_PATH_2026-10-10.md has the design and the enterprise path (R1-R4).

Appends to docs/PLATFORM_2026-10-04.md (section 43), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 30), each needing DOCS39_2026_10_10.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs40_<date>), line endings kept.

  python scripts/patch_docs40_2026_10_10.py --check
  python scripts/patch_docs40_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS40_2026_10_10"

PLATFORM = """

## 43. The repair path, there and then (DOCS40_2026_10_10)

**10 Oct, evening (IST). Built and tested; to apply.**

**Asked:** "In case re-OCR is needed to start translation, rather than crashing, the resolution path and
action should be there and then; else we discard that PDF and look for a better resolution. We need a
clean corpus with the distillate of the best quality translations."

**REPAIR_PATH_2026_10_10** (docs/REPAIR_PATH_2026-10-10.md):
- **`scripts/repair_text.py`** (new) is the one place the advice lives. Every step ends with
  `VERDICT:` and `NEXT:`. The steps:
  - assess (free, database read-only);
  - `--repair` (vision OCR through `ocr_consensus.py --yes`, capped by `--max-usd`; above the cap it
    spends nothing and names the cap it needs);
  - `--use-repaired [--replace N]` (backup, wipe, ingest the repaired pages, classify, drift; refuses
    unless every page is covered and readable, nothing is lost or N is named, and no other writer runs);
  - `--set-aside "why"` / `--restore` (`data/source_verdicts.jsonl`; files are kept);
  - `--list`.
- **`scripts/patch_repair_path_2026_10_10.py`**:
  - `dashboard.py` (on a restart): `POST /api/repair` (each step a run of `repair_text.py`; `use` under
    the translate lock; at most $5.00 a press); `/repair/<doc>`, the text's repair page, with live
    output.
  - The Library: a repair bar under a hold or a quality note; a text set aside shows why and Restore;
    texts with no English yet that a run could not translate are listed under *Waiting for a better
    source*.
  - The dashboard page (on a reload): a [HELD] run, a run stuck below the OCR bar, and a repair step's
    [REPAIR] verdict are followed in the Log by a line to the repair page (the command until the
    restart).

**Tests:** `tests/test_repair_text_2026_10_10.py` (9) and `tests/test_repair_path_2026_10_10.py` (12).
The DESK_HEAL and LIVE_LOG tests still pass.

**Decisions it puts in front of you:**
- Natyasastra and the Tantric Texts: none (nothing to lose).
- Hayashirsha (1,174 Hindi) and Karan Aagama (1,603 English, 1,425 Hindi, 14 pictures): the path names
  what a re-ingest replaces. R3 (an in-place re-ingest that keeps passage ids) would make it a refresh.
"""

RUNBOOK = """

## The repair path (DOCS40_2026_10_10)

1. **Patch:**
   - `python scripts\\patch_repair_path_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard with Ctrl+F5.
2. **Restart the dashboard when idle** (`scripts\\restart_dashboard.ps1`) for the Library's repair bars
   and `/repair/<doc>`.
3. **A text a run could not translate because of its scan:**
   - In the Library press *Repair path: what now?*, or open `http://127.0.0.1:5057/repair/<code>`.
   - Press the button it offers next:
     - Repair the scan (capped);
     - Use the repaired text (a backup first);
     - Set aside.
   - By hand: `python scripts\\repair_text.py --doc <code>`, then the step its NEXT line names.
4. **Put a database back after a failed re-ingest:**
   - the step prints its backup (`context_pre_repair_<code>_<stamp>.db`);
   - stop the dashboard (`scripts\\restart_dashboard.ps1 -Stop`);
   - copy the backup over `data\\context.db`;
   - start the dashboard.
5. **The texts set aside:** `python scripts\\repair_text.py --list`. Restore one with `--restore` when a
   better scan is in the inbox.
"""

EP = """

## Addendum 2026-10-10 (30) (DOCS40_2026_10_10)

| # | Item | State |
|---|---|---|
| R1 | The repair path, there and then: assess, repair the scan (capped), use the repaired text (backup first), set aside | Built and tested (REPAIR_PATH_2026_10_10). Next: patch, reload, restart when idle |
| O3 | Natyasastra, Tantric Texts | Next: Repair path, then Repair the scan, then Use the repaired text, then translate |
| O1, O4 | Karan Aagama, Hayashirsha | Your decision, now one press with its cost named: replace N English, or `--allow-debris`, or wait for R3 |
| R2 | Sources wanted: the texts set aside listed in the hub and the Corner; a better scan as a new witness; a second vision try at a higher resolution | Next |
| R3 | In-place re-ingest that keeps passage ids (and the Hindi, vectors and pictures), clearing only changed translations | Designed (docs/REPAIR_PATH_2026-10-10.md section 6); needs its own tests |
| R4 | The distillate: per passage the best reading among witnesses and the best translation, with provenance; the corpus publishes it | Charted |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS39_2026_10_10"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS39_2026_10_10"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS39_2026_10_10")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs40_" + stamp))
        t = p.with_name(p.name + ".tmp_docs40"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
