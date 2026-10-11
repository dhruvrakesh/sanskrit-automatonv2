#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs42_2026_10_11.py  DOCS42_2026_10_11

Records the night of 11 Oct: the heal applied and released (79aedee), Karan Aagama released too early
and held again, the repair running, and JUDGE_DESK_2026_10_11 (the debris judged on the cards; Sources
& repairs). docs/JUDGE_DESK_2026-10-11.md has the details and the path (S2, S3, R3, R4, C14).

Appends to docs/PLATFORM_2026-10-04.md (section 45), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 32), each needing DOCS41_2026_10_11.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs42_<date>), line endings kept.

  python scripts/patch_docs42_2026_10_11.py --check
  python scripts/patch_docs42_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS42_2026_10_11"

PLATFORM = """

## 45. The debris judged on the cards; Sources & repairs (DOCS42_2026_10_11)

**11 Oct, night (IST).**
- **The heal is applied and released** (`79aedee`). The dashboard was restarted; `/api/repair` reports
  `heal: REPAIR_HEAL_2026_10_11`.
- **Karan Aagama** was held (the mirror plan listed it under HELD). It was released at 19:47 before it
  was translated, and held again at 19:54, with the counts from before its re-ingest (1,603 English,
  1,425 Hindi).
- **The repair works.** The Tantric Texts' vision step ran the 72 pages left (about one page every 17
  s). The Natyasastra, Hayashirsha and Ganita follow in the same chain.

**JUDGE_DESK_2026_10_11** (`scripts/patch_judge_desk_2026_10_11.py`):
- `repair_text.py` caches every assessment (`data/source_judged/<doc>.json`);
- `--judge-all` judges every text that needs it;
- `--release` refuses until the translation is back (`--force` to override);
- the Library's cards show "Debris judged MATERIAL (date): misread letters in N% of verses; vision
  agreement A";
- `/sources` (*Sources & repairs*) lists every text whose scan stops its translation, with its state,
  the debris judged, what is next, and the best edition found;
- the repair page shows the judgement; the headers link to `/sources`.

**Tests:** `tests/test_judge_desk_2026_10_11.py` (11). Run them with `python -m unittest` (pytest is not
installed on this PC).
"""

RUNBOOK = """

## The debris judged; Sources & repairs (DOCS42_2026_10_11)

1. **Patch:**
   - `python scripts\\patch_judge_desk_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle;
   - `python scripts\\repair_text.py --judge-all` (free, read-only, about a minute).
2. **Open `http://127.0.0.1:5057/sources`.** Held texts come first, then material, moderate, cosmetic.
   Each row links to the text's repair page.
3. **Publish a text in repair** only when it is translated again:
   - `python scripts\\repair_text.py --doc <code> --release` refuses until then;
   - `--release --force` publishes as it is.
4. **Tests without pytest:** `python -m unittest tests.test_judge_desk_2026_10_11 tests.test_repair_heal_2026_10_11 -v`.
   Or `python -m pip install pytest` once.
"""

EP = """

## Addendum 2026-10-11 (32) (DOCS42_2026_10_11)

| # | Item | State |
|---|---|---|
| R1.1 | The heal | **Released** (79aedee); repair running (Tantric 72 pages; Natyasastra, Hayashirsha next) |
| J1.1 | The debris judged on the Library's cards and on the repair page; Sources & repairs (`/sources`); judge all | Built and tested (JUDGE_DESK_2026_10_11). Next: patch, restart, judge all |
| O1 | Karan Aagama | Held again 19:54 (released early at 19:47). Next: translate English and Hindi; release when back |
| S2 | An e-text (GRETIL, sanskritdocuments.org, archive.org OCR text) as a witness | Next, against the first fetched file |
| S3 | The missing page from a witness, offered on the repair page (local) | Designed |
| C14 | Sources wanted on the site: a corpus table filled by the mirror, shown in the Corner | Designed; the corpus-ingest function and schema are read first |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS41_2026_10_11"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS41_2026_10_11"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS41_2026_10_11")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs42_" + stamp))
        t = p.with_name(p.name + ".tmp_docs42"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
