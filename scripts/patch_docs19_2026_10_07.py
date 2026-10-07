#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs19_2026_10_07.py  DOCS19_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 22), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: the state at the end of 2026-10-07 (C2 complete and nightly,
W8 and W5 live, the story fixes applied), what reading today's editions and graphic novel found,
and the fixes in scripts/patch_exports_gate_2026_10_07.py. Marker-idempotent per file, backup first.

  python scripts/patch_docs19_2026_10_07.py --check
  python scripts/patch_docs19_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS19_2026_10_07"

PLATFORM = """

## 22. End of 2026-10-07: what is live, what today's outputs showed, and the fixes (DOCS19_2026_10_07)

**Live, checked.**
- **C2 is complete.**
  - Request 375 embedded the last 155 passages; R4 shows 1,655 vectors, one model, 1536 dimensions, and nothing pending.
  - R6 created cron job 9 ('15 4 * * *', 04:15 UTC). New or changed published passages are embedded every night.
- **Srangam a3600fe is published.**
  - The shell carries LOAD_W8_2026_10_07, with no static hero preload.
  - The entry is index-DFgFqJzJ.js, 494 kB (the same as the local build).
  - On /texts/markandeya_purana, p1.4 shows the drawn rule and no "<decorative line>".
- **The automaton.** It is at 183d2d02 (story fixes, W8/W5 patches, docs18). The story fixes are applied: 13 of 13 Markandeya stories pass; #3 is approved, the other 12 are drafts that pass and wait for a reader.

**What reading today's outputs found** (measured on backups/context_pre_storyfix_20261007.db, read-only).
- **siddhanta_shiromani_1-180.html.**
  - **What it was.** 180 empty "Page N" headings, 180 lines of contents and "(No content matched your filters.)". The text has 1,146 passages and none is translated.
  - **Where it came from.** pipeline_queue.py exports after each run, with the title "<code> - Sanskrit with English Translation", so the raw code was the book title.
- **markandeya_purana_1-100_tri_img.html.** The Hindi line of the title page was missing from every Hindi export: the provenance query joined translations_l10n to passages, both have engine / mt_prompt_version / translation_qa, the unqualified names were ambiguous, and the error was swallowed.
- **The 16-page novel PDF (novel #1, Nilamata, story 22).**
  - **Blank pages.** Pages 3 and 8 were blank but for a page number: a long caption pushed the number under it onto a page of its own.
  - **The cover range.** It said "passages 13.11-14.10" while the pages cite 13.9 and 13.10 too (the story's window).
  - **The source name.** It said "from nilamata seg" (no curated title).
  - **The cover picture.** It repeats page 1's.
  - **The plough.** Four pictures draw Ananta's plough as a pickaxe; the pictures are the only part this cannot fix.
- **The publication gate.**
  - **Withheld with the verse.** It withheld a passage when its first line was page furniture. Corpus-wide that is 404 translated passages, 402 with the verse below. Ten of them are on the published texts: Markandeya p11.2, p73.3, p99.2 (a stray folio mark) and Sandilya p57.6, 57.7, 69.8, 72.2, 72.3, 72.6, 75.6 (the source of a quotation above the quoted verse).
  - **Digits.** Separately, re.escape() had turned the decoration class's digit ranges into the characters 0, - and 9, so a page number such as "23" was not seen as furniture.

**The fixes** (scripts/patch_exports_gate_2026_10_07.py; tests/test_exports_gate_2026_10_07.py, 10 tests that all fail before and pass after).
- **Run against a copy of the repo on this machine:**
  - with the related suites (publish, novel, export, stories): 80 tests pass;
  - siddhanta_shiromani now exports a 4 kB page that says no passage has English text yet, and the run prints a WARNING;
  - Markandeya's title page reads "Hindi: 1244 verses, gemini:gemini-2.5-flash, mean QA 0.994".
- **export_html.py** (EXPORT_EMPTY_2026_10_07):
  - sections with nothing to show are left out, unless an approved picture is anchored there;
  - an empty run says what is missing and warns;
  - the Hindi provenance query is qualified;
  - a title beginning with the doc code uses configs/doc_titles.json, else the code made readable.
- **novel.py** (NOVEL_PRINT_2026_10_07):
  - each page is one page tall, the picture shrinks to leave room for the caption, and the number sits inside the caption box. With a deliberately long caption the old layout printed 13 pages, the new 10 (1 cover, 8 pages, sources);
  - the cover states the cited span;
  - the sources drop "//";
  - `build --cover N` picks the cover picture (default 1, as before).
- **publish_srangam.py** (PUBLISH_GATE_LINES_2026_10_07):
  - **Withheld only when it is all furniture.** A passage is withheld only when every line is page furniture. That is 6 corpus-wide: Sandilya p43.9 and p72.11, a reference with no verse, and four bare numbers with an invented translation such as Shatapatha p17.3.
  - **Digits.** The digit ranges are restored.
  - **Effect on the published texts.** Markandeya 1,216 -> 1,219 and Sandilya 439 -> 446; nothing published is withdrawn.
  - **--emit-sql --only P.I,...** writes just those passages; the text row and the check still use the whole publishable set.
- **configs/doc_titles.json.**
  - markandeya_purana gets its IAST title (as on the site since S4 M3).
  - nilamata_seg gets "Nilamata Purana" in IAST. This is proposed: the retired upapurana_nilamata_purana is the same work, and story 22 is the draining of the lake and Jalodbhava. Remove it if wrong.

**Noted, not changed.**
- **The "_tri" suffix** marks any edition with Hindi, Sanskrit or not; the uploaded _tri_img file is English + Hindi. Not renamed here.
- **The PowerShell console** prints "?" for IAST and Devanagari: the console code page, not the data (stories.py verify passes on those names). `chcp 65001` plus `$env:PYTHONIOENCODING = "utf-8"`, in Windows Terminal, shows them.
"""

RUNBOOK = """

## Exports, novel layout and the publication gate (DOCS19_2026_10_07)

- **Apply.** From the automaton root: `python scripts\\patch_exports_gate_2026_10_07.py --check`, then the same without `--check`.
- **Test.** `python -m unittest tests.test_exports_gate_2026_10_07 tests.test_publish_bridge tests.test_publish_engine_2026_10_07 tests.test_novel_2026_10_07 tests.test_export_images tests.test_export_pdf`.
- **The ten withheld verses**, published without re-pasting whole texts:
  1. `python scripts\\publish_srangam.py --doc markandeya_purana --emit-sql D:\\backups\\srangam_sql --only 11.2,73.3,99.2`
  2. `python scripts\\publish_srangam.py --doc AphorismsOfSandilya --emit-sql D:\\backups\\srangam_sql --only 57.6,57.7,69.8,72.2,72.3,72.6,75.6`
  3. Paste each doc's 00_text.sql, 01_passages.sql and 99_verify.sql in the Lovable Cloud SQL editor. 99_verify should show local = remote (1,219 and 446) and stale_on_site 0.
  4. Cron job 9 embeds them at 04:15 UTC, or run R3 once now (expect "taken":10).
  5. The folder for each doc then holds only these files (emit_sql writes a fresh set each time).
- **Novel #1, rebuilt.** `python scripts\\novel.py build --id 1 --cover 8`, then `python scripts\\export_pdf.py "<the html it names>"`.
"""

EP = """

## Addendum 2026-10-07 (9): end of day (DOCS19_2026_10_07)

| # | Item | State |
|---|---|---|
| C2 | Passage vectors | Complete, 1,655; nightly cron job 9 |
| W8 / W5 | Load time; reader marks | Live (a3600fe) |
| ST1 | Story corrections | Applied; 13/13 pass; #3 approved, 12 drafts to read and approve |
| EX1 | Empty exports, missing Hindi provenance, raw code titles | Fixed in patch_exports_gate (to apply) |
| NV1 | Novel print layout, cover span, sources | Fixed (to apply); redraw the 4 pickaxe pictures; choose a cover with --cover |
| G1 | Gate withheld verses below a furniture line | Fixed (to apply); republish 10 verses with --only |
| ST2 | Approved stories on the site (srangam_stories) | Next |
| W6 | Hindi on the reader | Next, planned in section 21 |
| C3b | Ask | After C3a has run a while |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs19_" + stamp))
        t = p.with_name(p.name + ".tmp_docs19"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
