#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs46_2026_10_12.py  DOCS46_2026_10_12

Records REINGEST_2026_10_12 (after QUALITY, 76a8b5c): the spend cap reached overnight; --use-repaired refused the
Tantric Texts (1,333 English) and Karan (13 pictures), as it should; reingest_pages.py (R3) changes only the pages
that differ from the repaired text; the LLM judge's first reading (a wrong meaning in 5-18% of the English of the
texts read from vision, 38% of the Bodhicaryavatara's); judge_review.py. docs/REINGEST_2026-10-12.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 49), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 36), each needing DOCS45_2026_10_11.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs46_<date>), line endings kept.

  python scripts/patch_docs46_2026_10_12.py --check
  python scripts/patch_docs46_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS46_2026_10_12"

PLATFORM = """

## 49. Only the pages that changed; the judge's first reading (DOCS46_2026_10_12)

**12 Oct, morning (IST), after the release of QUALITY (`76a8b5c`).** docs/REINGEST_2026-10-12.md has
the details.
- **The spend cap ($32.00) was reached overnight**, and every paid job stopped:
  - the Natyasastra's vision at page 297 of 546;
  - the Tantric Texts' translation after 1,333 English;
  - Karan's translation before its first.
- ***Use the repaired text* refused the Tantric Texts (1,333 English) and Karan (13 pictures)**, as it
  should. On the repair page, Karan's `--replace 0` was never sent; that is mended.
- **The judge (judge_sample.py) read 200 English passages** of five texts, for $0.04:
  - a wrong meaning (fidelity 2 or less) in 5-18% of the passages of the four texts read from vision;
  - 38% in the Bodhicaryavatara, whose Sanskrit is Tesseract's;
  - fluency high everywhere.
  It is a sample, judged by a model of the translator's family.

**REINGEST_2026_10_12:**
- `scripts/reingest_pages.py` (R3) changes only the pages that differ from the repaired text:
  - a passage whose text is unchanged keeps its translations, vectors and reviews, and its pictures
    and stories move with it;
  - the result equals a full re-ingest (tested);
  - the plan is free; `--apply` makes a backup first and needs `--replace N` for what it removes.
- Measured on the 11 Oct backup:
  - the Tantric Texts: 7 pages, 145 garbage passages out, 3 in;
  - Karan: 7 pages, 91 out, 6 in.
- `scripts/judge_review.py` (read-only) gives the judge's figures and the passages it marks.
- The patch:
  - the merge's SyntaxWarning is gone;
  - vision is priced from what it cost ($0.0111 a page for the Natyasastra, not $0.0004);
  - `reingest_pages.py` is offered where `--use-repaired` would replace translations;
  - the benchmark gives the judge's share of wrong meanings;
  - the repair page has the new steps.

**Tests:** `tests/test_reingest_2026_10_12.py` (13).
"""

RUNBOOK = """

## Re-ingest only the pages that changed (DOCS46_2026_10_12)

1. **Plan (free, read-only):** `python scripts\\reingest_pages.py --doc tantric_texts_series_edited_by_arthur_av`.
   It lists each changed page: passages kept, new and gone, and what goes with them.
2. **Apply:** the same with `--apply`.
   - A backup is made first.
   - If it removes English, Hindi, a picture or a story, it refuses and prints the exact line with
     `--replace N`.
   - It is refused while the dashboard runs a database writer.
3. **Restarted, the dashboard** has *Plan: only the changed pages* and *Re-ingest the changed pages* on
   the repair page.
4. **After it:** the drift check should find the changed pages current. The site gets the change at the
   next mirror run.

## The judge's reading (DOCS46_2026_10_12)

1. **A dry run first:** `python scripts\\judge_sample.py --doc Mallapurana --sample-pct 4 --limit 40`
   prints its cost (about $0.00015 a passage). Then the same with `--yes`.
2. **The figures, and the passages it marks:**
   `python scripts\\judge_review.py --html exports\\judge_review.html`.
3. **A person reads what it marks** before a translation is called wrong or right.
"""

EP = """

## Addendum 2026-10-12 (36) (DOCS46_2026_10_12)

| # | Item | State |
|---|---|---|
| Q1 | The Devanagari measured; the merge refuses Tesseract's garbage | **Released** (76a8b5c) |
| R3 | The in-place re-ingest (reingest_pages.py) | Built and tested (REINGEST_2026_10_12) |
| T1 | The translation judged on a sample | **First run**: 200 passages, a wrong meaning in 5-18% (vision texts), 38% (Bodhicaryavatara) |
| T2 | The marked passages translated again (gemini-2.5-pro), then judged again | Next; paid, capped, dry run first |
| B2 | The spend cap ($32) reached | The user's decision |
| VC1 | Vision's artefacts cleaned before ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS45_2026_10_11"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS45_2026_10_11"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS45_2026_10_11")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs46_" + stamp))
        t = p.with_name(p.name + ".tmp_docs46"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
