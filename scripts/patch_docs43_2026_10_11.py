#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs43_2026_10_11.py  DOCS43_2026_10_11

Records the late night of 11 Oct: the judge desk released (0e352ff) and the first judge-all (47 texts),
the repair chain as read on the PC, and ETEXT_WITNESS_2026_10_11 (an e-text as a witness; the missing
page offered on the repair page; judge v2). docs/ETEXT_WITNESS_2026-10-11.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 46), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 33), each needing DOCS42_2026_10_11.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs43_<date>), line endings kept.

  python scripts/patch_docs43_2026_10_11.py --check
  python scripts/patch_docs43_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS43_2026_10_11"

PLATFORM = """

## 46. An e-text as a witness; the missing page offered; judge v2 (DOCS43_2026_10_11)

**11 Oct, late night (IST).**
- **The judge desk is released** (`0e352ff`; `python -m unittest`: 109 tests, OK).
- **`--judge-all` judged 47 texts:** 24 material, 11 moderate, 12 cosmetic; 32 held by the guard.
- **Judge v2** makes two of those verdicts exact:
  - a page vision failed on is no disagreement, and agreement counts only from five pages;
  - the share of letters misread counts for texts cut into long passages (2% material, 1% moderate).
- **The repair chain:**
  - Tantric Texts: repaired, 212 pages (ready to use);
  - Natyasastra: no vision page; its cap refused before spending;
  - Hayashirsha: 92 of 189 at 21:46;
  - Karan Aagama: in repair, to be translated.

**ETEXT_WITNESS_2026_10_11** (`scripts/etext_witness.py`, `scripts/patch_etext_witness_2026_10_11.py`):
- **An e-text becomes a text of its own** (`<doc>__w_<site>`): GRETIL, sanskritdocuments.org or an
  archive.org OCR text, in Devanagari, IAST, Harvard-Kyoto, Velthuis or ITRANS. Its lines are grouped
  into verses by their references and put into Devanagari.
- **It is measured against the scan, page by page,** on six-letter n-grams of the consonant skeleton:
  - how much the witness reads, and in what order;
  - for each page the scan cannot read, the witness's verses between its neighbours: the missing
    page, offered on the repair page.
- **`--write` / `--ingest`:**
  - its pages, then a backup and the ingest;
  - the register says `witness`, and the mirror leaves it alone until `repair_text.py --release`,
    which waits for the translation.
- **The repair page's Source desk:**
  - the files fetched, and a pasted e-text link;
  - each witness, with *Ingest*, *Translate* and *Adopt*;
  - the pages the scan cannot read, as the witness reads them.

**Tests:** `tests/test_etext_witness_2026_10_11.py` (23).
"""

RUNBOOK = """

## An e-text as a witness (DOCS43_2026_10_11)

1. **Patch:**
   - `python scripts\\patch_etext_witness_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle;
   - `python scripts\\repair_text.py --judge-all`.
2. **Stop tracking the judged cache:** `git rm -r --cached data/source_judged`. It is in
   `.gitignore` now; the files stay on disk.
3. **Find an e-text:**
   - the repair page's Source desk: *Find a better source*, then a GRETIL or sanskritdocuments.org
     link;
   - or download the file into `sources\\<doc>\\`.
4. **Read it as a witness (free, read-only):**
   `python scripts\\etext_witness.py --doc <doc> --file "sources\\<doc>\\<file>"`. Or paste the link on
   the repair page.
   - `WITNESS:` says whether it is the same work.
   - `--page N` shows the witness's reading of one page of the scan.
5. **Make it a witness:**
   - `--write`, then `python scripts\\etext_witness.py --doc <doc> --ingest` (a backup first; the scan
     is not touched);
   - translate the witness from the Library;
   - `python scripts\\repair_text.py --doc <doc>__w_<site> --release` to adopt it.
6. **Only if the witness replaces the scan:**
   - `python scripts\\diag_retire_check.py --src <doc> --keep <doc>__w_<site>`;
   - then `python scripts\\retire_doc.py --doc <doc> --supersedes <doc>__w_<site> --dry-run`.
"""

EP = """

## Addendum 2026-10-11 (33) (DOCS43_2026_10_11)

| # | Item | State |
|---|---|---|
| J1.1 | The debris judged; Sources & repairs | **Released** (0e352ff); judge all: 47 texts, 24 material |
| J2 | Judge v2: failed vision pages, five pages for agreement, letters misread | Built and tested (ETEXT_WITNESS_2026_10_11) |
| S2 | An e-text as a witness (GRETIL, sanskritdocuments.org, archive.org OCR text) | Built and tested. Next: the first real file (its preview calibrates the thresholds) |
| S3 | The missing page from a witness, offered on the repair page | Offered (shown); taking it into the scan's passages is R3 |
| R3 | The in-place re-ingest: keeps passage ids, takes an offered page | Next |
| C14 | Sources wanted on the site | Designed: a corpus table from the judged cache, the Source desk and the witnesses; SQL next |
| O2 | Tantric Texts: use the repaired text; Natyasastra: repair with a higher cap; Hayashirsha: let it finish; Karan Aagama: translate, then release | The user's |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS42_2026_10_11"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS42_2026_10_11"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS42_2026_10_11")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs43_" + stamp))
        t = p.with_name(p.name + ".tmp_docs43"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
