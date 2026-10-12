#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs45_2026_10_11.py  DOCS45_2026_10_11

Records QUALITY_2026_10_11 (after BENCHMARK, 26d0806): are we sure of the texts? The Devanagari itself measured
(noise, plausibility against the GRETIL Adiparvan), Tesseract's garbage of plates and title pages refused by the
merge (19 pages in 5 texts), a witness no cleaner than Tesseract refused, and what is not yet known (the meaning of
the translations: no LLM judge has read them). docs/QUALITY_2026-10-11.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 48), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 35), each needing DOCS44_2026_10_11.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs45_<date>), line endings kept.

  python scripts/patch_docs45_2026_10_11.py --check
  python scripts/patch_docs45_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS45_2026_10_11"

PLATFORM = """

## 48. Are we sure of the texts? The Devanagari measured (DOCS45_2026_10_11)

**11 Oct, night (IST), after the release of BENCHMARK (`26d0806`).** docs/QUALITY_2026-10-11.md has
the table.
- **Noise** is the share of Devanagari words that are malformed, have a Latin letter or a stray mark
  glued on, or are stray marks. **Plausibility** is the share of letter trigrams found in the BORI
  Adiparvan from GRETIL, which has 0.0% noise.
- **Where vision read the text, the Devanagari is clean:** 0.06-0.86% of the words, against
  2.7-7.4% for Tesseract. Vision is also the more plausible reading (87-95% against 82-90%).
- **The repair's noise came from 19 garbage pages in 5 texts:** Tesseract's text on plates, yantras
  and title pages. The merge now refuses it: vision's line is kept, or the page is written blank.
  Merged again, the Tantric Texts go from 3.3% to 0.9% and Karan from 1.9% to 0.2%.
- **The Rgveda vol. ii's vision** reads a printed pratika mark as "V": 8,602 words on 230 pages.
  None of it is translated; it waits for the cleanup (VC1).
- **Archive.org's OCR of the 1960 Bodhicaryavatara** has noise in 9.4% of its words and our
  Tesseract 5.6%, with 11.5% Latin debris. Neither is clean. A witness no cleaner than Tesseract
  (over 3%) is now refused.
- **Not known yet:** well-formed misreadings (no text has a critical e-text), and the translations'
  meaning. The QA (0.93-0.995) is structural, and no LLM judge has read these texts. That is T1.

**QUALITY_2026_10_11** (`scripts/patch_quality_2026_10_11.py`) patches merge_ocr_sources.py,
ocr_consensus.py, etext_witness.py, benchmark_sources.py, source_desk.py (loads .env; an archive.org
error is a verdict) and dashboard.py (the Noise and Plausible columns).

**Tests:** `tests/test_quality_2026_10_11.py` (18).
"""

RUNBOOK = """

## Are we sure of a text? (DOCS45_2026_10_11)

1. **The figures:** `python scripts\\benchmark_sources.py --all` (free, read-only). Read the noise
   beside the misread letters:
   - vision OCR of a clean print is under 1%;
   - Tesseract is 2.7-7.4%;
   - over 3% is a damaged text.
2. **A repaired text merged before QUALITY_2026_10_11, with no English yet:**
   - merge again: `python scripts\\merge_ocr_sources.py --doc tantric_texts_series_edited_by_arthur_av`,
     then the same with `--apply`;
   - use the repaired text through the dashboard (its translate lock): the repair page's button when
     Assess offers it, or `Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/repair` with
     the body `{"doc": "...", "step": "use"}` (by hand, `--use-repaired` refuses while the dashboard
     runs another job);
   - a text with English waits for R3.
3. **A witness** with noise over 3% is refused. It is no cleaner than Tesseract; look for an e-text.
4. **The translation's QA figure is structural.** The meaning is read by `scripts\\judge_sample.py`
   (an LLM judge of fidelity and fluency on a sample, into mt_reviews; a dry run first, `--yes` to
   call it, capped by `--limit`), and by a person's spot check of about 20 passages.
"""

EP = """

## Addendum 2026-10-11 (35) (DOCS45_2026_10_11)

| # | Item | State |
|---|---|---|
| B1 | The benchmark | **Released** (26d0806) |
| Q1 | The Devanagari measured (noise, plausibility); the merge refuses Tesseract's garbage; a noisy witness refused | Built and tested (QUALITY_2026_10_11) |
| O4 | Tantric Texts and Karan merged again and re-ingested; Hayashirsha, the Tantric Texts and Karan translated | The user's |
| VC1 | Vision's artefacts cleaned before ingest (the Rgveda's "V", Hayashirsha's sup tags) | Next |
| T1 | The translation judged on a sample: judge_sample.py (built in August; mt_reviews holds no review of these texts), then against a clean e-text; a person's spot check | Next; the user's first runs |
| R3 | The in-place re-ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS44_2026_10_11"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS44_2026_10_11"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS44_2026_10_11")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs45_" + stamp))
        t = p.with_name(p.name + ".tmp_docs45"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
