#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs88_2026_10_22.py  DOCS88_2026_10_22

Records the night of 22 Oct: the release b0ba93c3 and Srangam's c4849e8 (pushed, not yet published); the eight
GRETIL witnesses written, ingested and measured on the PC; what GRETIL taught us about our own reading
(OCR_BENCHMARK_2026_10_22: vision, Tesseract and archive.org's OCR measured against the e-texts); the gaps a witness
fills, and how; the asks collated (docs/ASKS_2026-10-22.md, DOC_REGISTER_2026_10_22) and four corrections to the
record; a command printed as its shape, mended (GRETIL_NEXT_2026_10_22); the site's corpus for those texts (K1, K2).

Appends docs/DEBT_2026-10-22.md section 9, STATE section 23, a RUNBOOK section, PLATFORM section 91 and
ENTERPRISE_PATH addendum 78, each needing DOCS87_2026_10_22. Refuses unless what it records is here:
docs/ASKS_2026-10-22.md, scripts/ocr_benchmark.py, scripts/doc_register.py (they come with this release) and
scripts/gretil_library.py patched by GRETIL_NEXT_2026_10_22 (apply that first). Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs88_<date>), line endings kept.

  python scripts\\patch_docs88_2026_10_22.py --check
  python scripts\\patch_docs88_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS88_2026_10_22"
NEEDS = "DOCS87_2026_10_22"
REQUIRES = {"docs/ASKS_2026-10-22.md": "DOCS88_2026_10_22",
            "scripts/ocr_benchmark.py": "OCR_BENCHMARK_2026_10_22",
            "scripts/doc_register.py": "DOC_REGISTER_2026_10_22",
            "scripts/gretil_library.py": "GRETIL_NEXT_2026_10_22"}

DEBT = """
## 9. What GRETIL taught us about our own reading; the gaps it fills; the asks collated (DOCS88_2026_10_22)

- **Released:** `b0ba93c3` (GRETIL_LIBRARY, TEST_ENV, ETEXT_ANALYSIS, DOCS87), pushed. Srangam `c4849e8` (another
  session's SEO Phase AN), pushed, not yet published: the curl.exe checks ran in the same paste, before Publish, and
  read the old page (a static canonical, 0 data-rh tags, 77 sitemap URLs, 3 retired slugs).
- **The eight witnesses, on the PC (22 Oct, 19:01 to 19:04):** each extracted with its provenance, previewed ("the
  same work, in the same order"), written, ingested as its own text (local only; a backup first) and measured. Against
  its witness, the text in our database:

  | Text | Agrees | Units found | Gaps |
  |---|---|---|---|
  | Yamasmrti | 85.09% | 81 of 81 | 0 |
  | Narasimha Purana | 83.22% | 3,555 of 3,582 | 27 |
  | Manusmrti | 81.99% | 2,674 of 2,984 | 309 |
  | Parasarasmrti | 80.57% | 577 of 941 | 363 |
  | Yajnavalkyasmrti | 75.36% | 1,033 of 1,055 | 20 |
  | Bodhicaryavatara | 72.66% | 813 of 924 | 110 |
  | Samaveda | 65.29% | 454 of 468 | 12 |
  | Gautama Dharmasutra | 56.07% | 716 of 1,012 | 294 |

- **A benchmark of our reading (OCR_BENCHMARK_2026_10_22):** `scripts\\ocr_benchmark.py`, free and read-only, sets
  the 24 readings of 13 texts against their 12 witnesses side by side. Where one print has two readings, each
  engine's own misreadings (the other reading has the e-text's letter there, so the print has it), in 100 aksharas:
  the Markandeya, vision 3.58 and Tesseract 18.15 (shared 5.09); the Nirukta, vision 4.95 and Tesseract 9.57 (shared
  16.37); the Satapatha's kanda 14, vision 3.34 and archive.org's OCR 25.20 (shared 6.88). Over all: vision 4.33,
  Tesseract 12.02, archive.org 25.20. Agreement weighted by aksharas: vision 80.19% (4 texts), Tesseract 75.37% (5),
  the engine not recorded 77.07% (5), archive.org 53.2% (2). Agreement counts every place where our print and the
  e-text's edition differ as well; the own misreadings are the engine's error rate on that print. The commonest
  substitutions are in exports\\ocr_confusions.csv, those two engines make on one text marked (more likely the print
  or the e-text's convention than a misreading).
- **Is it a learning system?** Not yet. The benchmark now measures what merge_ocr_sources.py (29 Aug) had to infer
  from vision against vision: vision is the source of record, and on these prints it misreads about a third as often
  as Tesseract. Nothing feeds back on its own. Three uses, in order: a vision pass of the eight witnessed texts read
  from Tesseract's pages alone (about $4.80) gives each two readings, the first measured test of vision on those
  prints; the Pro pilot (about $0.31) on pages that have a witness, so it is measured, not judged; ocr_triage.py's
  threshold set against a witness instead of against vision, which needs Tesseract's word confidence on the pages
  (the older runs, the Narasimha's among them, did not record it). The substitutions are for a person to read
  first: a correction drawn from them alone would be a guess.
- **The gaps a witness fills:** the witness's units, inside the span our scan covers, that our reading lacks: the
  Parasara 363 of 941, the Manu 309, the Gautama 294, the Bodhicaryavatara 110 (its scan reads 3 of its 253 pages,
  and the witness still finds 199 of them), the Markandeya 64 (vision) and 103 (Tesseract), the Nirukta 39 and 53,
  the Narasimha 27, the Yajnavalkya 20, the Samaveda 12, the Surya 3, the Yama none. A witness fills them as a whole
  text, its edition named, adopted once translated (repair_text.py --release), with our scan kept beside it; not by
  setting its verses into our scan, which would make one text of two editions. Where its edition is not our print's
  (the Nirukta's shared 16.37 in 100), the difference is to be read, not mended. The 34 texts GRETIL does not read
  keep their gaps (F4c).
- **The asks, collated:** docs/ASKS_2026-10-22.md, the register under keys that do not change, and
  `scripts\\doc_register.py` (DOC_REGISTER_2026_10_22), its check: the ENTERPRISE_PATH's 471 rows are 329 items under
  200 labels, and 63 labels name more than one item; 190 items read as open by their last state, 97 of them last
  recorded before 15 Oct. Four corrections: GRETIL's licence was decided on 18 Oct (L1), so DOCS87's Y4 is narrower
  than it said; T10 (test_mbh_prose) is closed by TEST_ENV; F3b no longer matters (the zip is the listing); F3 is
  done but for the Rgveda.
- **Found, and mended (GRETIL_NEXT_2026_10_22):** `gretil_library.py --match` printed "NEXT: python
  scripts\\gretil_library.py --extract MEMBER --doc DOC", and it was run as printed ("not in 1_sanskr.zip: MEMBER").
  It now prints the commands themselves for the strong matches without a witness, and names ocr_benchmark.py when
  each has one.
- **The site, read-only (K1, K2):** its corpus holds the Nirukta's 2,095 passages, 2,031 with English (made from the
  Tesseract text), the Manu's 2,568 (18), the Narasimha's 445 (13), the Samaveda's 524 (0), the Gautama's 109 (85),
  the Yajnavalkya's 82 (52), the Parasara's 47 (0) and the Yama's 7 (1); the Bodhicaryavatara none (withdrawn on 12
  Oct). None of them is listed on the public site (no row in public.srangam_texts).
- **The brain page** ("Our Sanskritic Brain: Where We Stand") has a section for 22 Oct, evening.
- **Open:** docs/ASKS_2026-10-22.md, section 3.
"""

STATE = """
## 23. 22 Oct, night: the benchmark; the asks collated (DOCS88_2026_10_22)

- **Released:** the Automaton `b0ba93c3`; Srangam `c4849e8`, pushed, not yet published.
- **Measured:** the eight GRETIL witnesses on the PC; our readings against all 12 witnesses (ocr_benchmark.py):
  vision misreads 4.33 aksharas in 100 on its own, Tesseract 12.02, archive.org's OCR 25.20.
- **Collated:** docs/ASKS_2026-10-22.md (the register) and doc_register.py (its check). **Mended:** GRETIL_NEXT.
"""

RUNBOOK = """
## The benchmark; the register (DOCS88_2026_10_22)

docs/DEBT_2026-10-22.md, section 9; docs/ASKS_2026-10-22.md. In a new PowerShell window: `$A = "D:\\Sanksrit
Automatons\\sanskrit-automatonv2"`, then `Set-Location $A`. Nothing below spends.
1. Apply, each with `--check` first: `scripts\\patch_gretil_next_2026_10_22.py`, then `scripts\\patch_docs88_2026_10_22.py`.
   Then `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.
2. The benchmark: `python scripts\\ocr_benchmark.py` (exports\\ocr_benchmark.csv, ocr_confusions.csv,
   ocr_benchmark.json). Run it again after any `source_fidelity.py` measure.
3. The register's check: `python scripts\\doc_register.py`, then `python scripts\\doc_register.py --open --before
   2026-10-15` (the old items, to close with the release that did them or to bring into ASKS section 3).
4. Srangam: Lovable Publish first; only then SEO_GSC_STATUS section 5's checks with curl.exe (the DOCS87 section,
   step 5); then Search Console (its section 4).
5. The decisions: ASKS section 3 (Yours and Money).
"""

PLATFORM = """
## 91. The benchmark; the register (DOCS88_2026_10_22)

| Marker | Files | What |
|---|---|---|
| OCR_BENCHMARK_2026_10_22 | scripts/ocr_benchmark.py, tests/test_ocr_benchmark_2026_10_22.py | every source_fidelity report side by side: agreement by engine, own misreadings where a print has two readings, gaps, substitutions, the cost of a vision pass for a text read by Tesseract alone |
| DOC_REGISTER_2026_10_22 | scripts/doc_register.py, tests/test_doc_register_2026_10_22.py | the ENTERPRISE_PATH's tables as one register: reused labels kept apart, last state and date per item, the old open ones listed |
| GRETIL_NEXT_2026_10_22 | scripts/gretil_library.py (+ tests/test_gretil_next_2026_10_22.py) | --match prints the commands themselves for the strong matches without a witness |
| DOCS88_2026_10_22 | docs/ASKS_2026-10-22.md (new), DEBT 9, STATE 23, RUNBOOK, this section, ENTERPRISE_PATH 78 | the register of our asks; the record |

- **From here on:** a new ENTERPRISE_PATH row cites a key of docs/ASKS_2026-10-22.md; doc_register.py reads those
  keys too.
"""

EP = """
## Addendum 2026-10-22 (78) (DOCS88_2026_10_22)

| Key | Item | State |
|---|---|---|
| witness-check | Our readings benchmarked against the e-texts (vision 4.33, Tesseract 12.02, archive.org 25.20 own misreadings in 100) | Done: OCR_BENCHMARK_2026_10_22 |
| witness-adopt | The eight new GRETIL witnesses, written, ingested and measured on the PC | Yours, text by text, after its English (ASKS 3) |
| witness-vision-pairs | A vision pass of the eight witnessed texts read from Tesseract's pages alone | Money: about $4.80 |
| docs-coherence | The asks collated under keys that do not change | Done: docs/ASKS_2026-10-22.md; DOC_REGISTER_2026_10_22 |
| F4a | Eight new witnesses: the Yama, Manu, Narasimha, Yajnavalkya, Parasara, Gautama, Samaveda, Bodhicaryavatara | Done: written, ingested and measured on the PC (22 Oct, 19:01 to 19:04); their adoption is witness-adopt |
| T10 | test_mbh_prose: 3 errors on the PC alone | Closed: the cp1252 pipe, mended by TEST_ENV_2026_10_22 |
| F3b | GRETIL's Rgveda and Samaveda | Closed: the cumulative zip is the listing |
| F3 | GRETIL's Nirukta, Rgveda (Aufrecht) and Samaveda as witnesses | Done for the Nirukta and the Samaveda; the Rgveda is rgveda-witness |
| Y4 | GRETIL's terms (CC BY-NC-SA 4.0; legacy files: reference only) and the editions of 1960 or later | Superseded: the TEI texts were decided on 18 Oct (L1); open are gretil-legacy-terms and witness-adopt |
| srangam-seo-publish | Srangam's SEO Phase AN, pushed (c4849e8) | Yours: Lovable Publish, then the curl.exe checks |
"""

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first, or it comes with this release). Nothing written." % (f, m))
            return 1
    plan = {}
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (p, NEEDS)); return 1
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs88_" + stamp))
        t = p.with_name(p.name + ".tmp_docs88"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
