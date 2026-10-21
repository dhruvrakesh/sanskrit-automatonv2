#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs79_2026_10_21.py  DOCS79_2026_10_21

Records the evening of 21 Oct: the Surya Siddhanta's references (ETEXT_REFS_2026_10_21: the value in brackets at the
end of 18 verses had been read as their reference; the others had none; the chapters were the colophons'); the
scholars' shelf, step 2 (CLAIMS_2026_10_21: Raychaudhuri's Political History of Ancient India, 1923, read into claims
with their pages); an e-text's noise named on the site (ETEXT_NOISE_2026_10_21, the Srangam kit); the estimate of the
verses of numbers owned; docs/CLAIMS_AND_REFS_2026-10-21.md.

Appends to docs/PLATFORM_2026-10-04.md (section 82), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 69)
and docs/STATE_2026-10-18.md (section 14), each needing DOCS78_2026_10_21. Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs79_<date>), line endings kept.

  python scripts\\patch_docs79_2026_10_21.py --check
  python scripts\\patch_docs79_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS79_2026_10_21"

PLATFORM = """

## 82. The Surya's references; the scholars' shelf, step 2: Raychaudhuri as claims (DOCS79_2026_10_21)

**21 Oct, evening.** docs/CLAIMS_AND_REFS_2026-10-21.md.
- **ETEXT_REFS_2026_10_21:** each verse of GRETIL's Suryasiddhanta is a line that begins with its pada label (1.31a:);
  a verse of numbers ends with the value of its word-numerals in brackets ((364220)). etext_witness.take_ref() read the
  bracket as the verse's reference: 18 verses had a verse_ref of 364220, 225, 260.40 (chapter "260") and the value
  taken out of their text; the other 485 had none, and every chapter was the colophons' count (1, then 2). Now a line
  that begins with a label (after a chapter's title in brackets, too) keeps its text and takes the label's reference
  and chapter (1 to 14); take_ref(labels=False) reads as before. mend_witness.py reads each line again from the source
  file when its sha256 is the witness's: the reference only (485), or the value put back (18, re-based, the same
  English); the latest scholarly row of the 485 gets the verse's reference, its English untouched; the e-text's three
  doubled references (3.13, 10.13, 13.21) are named, not mended.
- **CLAIMS_2026_10_21:** scripts/scholar_claims.py reads H. C. Raychaudhuri's Political History of Ancient India
  (University of Calcutta, 1923; public domain) page by page with gemini-2.5-flash into data/shelf/claims.db: each
  claim with its printed page (pdf - 18; the Foreword i-v), relation, stance and hedge, a quotation checked against the
  page's own text (exact, close, none), and its cites read into the works they name and whether our corpus holds the
  place. Part I (pdf 14-112) about $0.69; --show NAME puts a name's claims beside the indexes (step 1) and our texts.
- **The verses of numbers:** Gemini 2.5 Pro (judged by Gemini Flash), 18 verses: 15 passed, 3 flagged, $2.01.
- **ETEXT_NOISE_2026_10_21 (Srangam):** noise in an e-text is named "Not the text: the e-text's own header or notes.",
  not scanner noise.

**Tests:** test_etext_refs_2026_10_21 (6), test_scholar_claims_2026_10_21 (8), test_srangam_etext_noise_kit_2026_10_21
(4), test_docs79_2026_10_21 (3); the replay chain of test_etext_ortho_2026_10_21 (.bak_etextrefs_).
"""

RUNBOOK = """

## The Surya's references; Raychaudhuri as claims; an e-text's noise named (DOCS79_2026_10_21)

docs/CLAIMS_AND_REFS_2026-10-21.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `scripts\\patch_etext_refs_2026_10_21.py` and `scripts\\patch_docs79_2026_10_21.py`, each with
   `--check`, then without it; then `python -m unittest tests.test_etext_refs_2026_10_21 tests.test_etext_ortho_2026_10_21
   tests.test_witness_mend_2026_10_21 tests.test_etext_page_2026_10_18 tests.test_etext_witness_2026_10_11
   tests.test_scholar_claims_2026_10_21 tests.test_srangam_etext_noise_kit_2026_10_21 tests.test_docs79_2026_10_21`.
2. When the Gemini run of the verses of numbers has finished: `python scripts\\mend_witness.py --doc
   jyotish_surya_siddhanta__w_etext` (the plan: respelled 18, the reference only 485), then `--yes` (a backup first).
   The scheduled mirror sends it; docs/cloud/CHECKS_surya_refs_2026-10-21.sql (read-only) before and after.
3. The claims: `python scripts\\scholar_claims.py --extract` (free), `--pages 1-3 --yes` (about $0.02), `--report`,
   `--show Janamejaya`; then `--part 1 --yes` (about $0.69).
4. Srangam (`Set-Location D:\\srangam-42267`; `git pull --rebase --autostash`): `python
   "$A\\scripts\\patch_srangam_etext_noise_2026_10_21.py" --check`, then without it; `npm run typecheck`; `npx vitest
   run`; `npm run build`; then the `git add` line it prints, a commit and a push.
5. Release the automaton with COMMIT_MSG_refsclaims_20261021.txt.
"""

EP = """

## Addendum 2026-10-21 (69) (DOCS79_2026_10_21)

| # | Item | State |
|---|---|---|
| S2 | The Surya's 18 verses of numbers | Done (Gemini 2.5 Pro, Gemini Flash judge, 17:08-17:48 IST): 15 passed, 3 flagged, $2.01. Addendum 68 had said "about $0.30 of Google's cap": wrong; the dry runs said $0.65 on Sonnet and $1.84 on Gemini 2.5 Pro |
| S4 | The Surya's references and chapters | Fixed: ETEXT_REFS_2026_10_21; mended in place by mend_witness.py (18 values put back, 485 references, 14 chapters) |
| H3 | Raychaudhuri's Political History (1923) as claims, page by page | Built: CLAIMS_2026_10_21 (data/shelf/claims.db, on the PC); Part I about $0.69: yours to run |
| H4 | The claims on the site | Yours: the claims are Raychaudhuri's words (public domain); the indexes are CC BY-NC-SA 3.0 |
| R1 | An e-text's noise named on the site | Kit: ETEXT_NOISE_2026_10_21 (Srangam; yours to apply, test and push) |
"""

STATE = """

## 14. 21 Oct, evening: the Surya's references; Raychaudhuri as claims (DOCS79_2026_10_21)

- **The Surya Siddhanta's references:** the value in brackets at the end of 18 verses had been their verse_ref (and was
  missing from their text); the other 485 verses had none; the chapters were the colophons' (1, 2). Fixed
  (ETEXT_REFS_2026_10_21); to be mended in place now that the Gemini run of the verses of numbers has finished
  (17:48 IST: 15 passed, 3 flagged, $2.01; data/scholar/jyotish_surya_siddhanta__w_etext_20261021_170823.jsonl).
- **The scholars' shelf, step 2:** scholar_claims.py and the scan of Raychaudhuri's 1923 Political History (GIPE-004595,
  md5 75e8d7bd...) at data/shelf/phai1923/ on the PC; Part I not yet read (about $0.69).
- **Srangam:** the e-text's noise named (ETEXT_NOISE_2026_10_21), a kit to apply; the repo is at beedafe5 until then.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS78_2026_10_21"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS78_2026_10_21"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS78_2026_10_21"),
           (Path("docs/STATE_2026-10-18.md"), STATE, "DOCS78_2026_10_21")]

def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"



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
        nl = nl_of(raw)
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs79_" + stamp))
        t = p.with_name(p.name + ".tmp_docs79"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
