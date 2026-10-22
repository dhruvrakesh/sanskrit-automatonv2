#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs84_2026_10_22.py  DOCS84_2026_10_22

Records the letter fidelity measured on 22 Oct (FIDELITY_2026_10_22, scripts/source_fidelity.py, docs/FIDELITY_2026-10-
22.md): our vision text misreads or loses 3.6 aksharas in 100 of its own (the Markandeya 3.58, the Satapatha's kanda 14
3.62), Tesseract on the same pages 18 and 24; archive.org's text layers of Samasrami's Satapatha agree with GRETIL in 49
to 55 aksharas in 100; the Surya's scan (Tesseract) 78.79%; the judge's "cosmetic" does not see vision's fluent errors.
What it means per text, the path (F1 to F4, R4, D1b revised) and the commands.

Appends the brain page's section 10, PLATFORM section 87, a RUNBOOK section, ENTERPRISE_PATH addendum 74 and STATE
section 19, each needing DOCS83_2026_10_22; and in QUALITY_METHODOLOGY.md, a paragraph after section 1's known blind
spot and a word on its last line; and data/source_fidelity/ to .gitignore (the reports are made again). Marker-idempotent
per file, all-or-nothing, backup first (.bak_docs84_<date>), line endings kept.

  python scripts\\patch_docs84_2026_10_22.py --check
  python scripts\\patch_docs84_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS84_2026_10_22"
BP = "docs/BRAIN_PATH_2026-10-21.md"
QM = "QUALITY_METHODOLOGY.md"
NEEDS = "DOCS83_2026_10_22"

QM_BLIND = '"probably readable", and confirm by eye or by the translation\'s own QA.'
QM_TEXT = QM_BLIND + """

**Measured letter by letter (2026-10-22, DOCS84_2026_10_22).** The blind spot holds for vision OCR too, in another
form. `scripts/source_fidelity.py` (FIDELITY_2026_10_22) reads a text's letters against an e-text, akshara by akshara,
and against a second reading of the same page, so that another edition's readings do not count as errors. Our vision
text misreads or loses about **3.6 aksharas in 100** of its own (the Markandeya 3.58, the Satapatha's kanda 14 3.62),
about one a sloka; Tesseract on the same pages 18 and 24. Vision's errors are well-formed Devanagari (a plausible word
for the printed one, a syllable written once where the print has it twice), so `quality_score`, the noise measure and
the judge's "cosmetic" do not see them. archive.org's text layers of the 1903 to 1911 Calcutta Satapatha agree with
GRETIL in 49 to 55 aksharas in 100. Where an e-text exists it is the better text to translate; the method, its limits
and the numbers are in `docs/FIDELITY_2026-10-22.md`."""
QM_LAST = "*Last reviewed 2026-08-28. "
QM_LAST_NEW = "*Last reviewed 2026-08-28; the letter fidelity in section 1 on 2026-10-22 (DOCS84_2026_10_22). "

EDITS = {
    QM: [(QM_BLIND, QM_TEXT), (QM_LAST, QM_LAST_NEW)],
}

BRAIN = """

## 10. How faithfully the brain's Sanskrit reads (DOCS84_2026_10_22)

docs/FIDELITY_2026-10-22.md has the method and every number; scripts/source_fidelity.py (FIDELITY_2026_10_22) measures
it, read-only and free.

**Our vision text is close, not faithful.** Against a second reading of the same page, so that another edition's
readings do not count, it misreads or loses about 3.6 aksharas in 100 of its own: the Markandeya 3.58 (Tesseract on the
same pages 18.15), the Satapatha's kanda 14 3.62 (Tesseract 24.49). About one akshara a sloka, and fluent: a plausible
word for the printed one (gatvayodhyajanam read gatva yojanam), a syllable written once where the print has it twice.
The judge called both texts "cosmetic"; it sees Latin debris, not these.

**archive.org's text layers are worse than our OCR, by far.** Samasrami's Satapatha (seven volumes): 49 to 55 aksharas
in 100 agree with GRETIL in the kandikas that can be found, and about two in three cannot be found at all. Our
Tesseract on kanda 14 agrees in 58, our vision text in 82 (most of the rest the print's own way of printing each kandika
twice, the second time with its sandhi undone). The same-scan test, archive.org's layer of the very scan we read (DLI
2015.405693), is the RUNBOOK's next step.

**What it means for the brain.** Where an e-text exists it is the Sanskrit to translate: the Surya's (released 21 Oct),
GRETIL's Markandeya (5,240 passages, released, no working English yet; its working English, names and vectors cost
about $4.12 by the meter, against $4.42 left under the $85 cap). Our scans stay as the prints, each a witness. GRETIL's
Satapatha stays a local witness: its ch is lost, and Samasrami's archive.org text cannot restore it (D1b now reads
Samasrami's images instead, if you download them). GRETIL also has the Nirukta, Aufrecht's Rgveda and the Samaveda:
three more witnesses, then measured.
"""

PLATFORM = """

## 87. Letter fidelity: our scans, archive.org's text layers, the e-texts (DOCS84_2026_10_22)

- **Built:** `scripts/source_fidelity.py` (FIDELITY_2026_10_22, new, read-only, free; the database opened `?mode=ro`,
  `--immutable` for a backup). `--ref` an e-text (`db:`, `witness:`, `file:`; `--prefix` a kanda), `--cand` the readings
  (`db:`, `vision:`, `raw:`, `file:`, `witness:`), `--pair A,B` one print read twice, `--ledger [--csv]` every text.
  Both sides folded alike (spaces, punctuation, numbers, accents, avagraha, nukta; a nasal before a consonant, a final m
  and the candrabindu as the anusvara; a final consonant joined to its vowel, never across a danda; a colon as the
  visarga; `--fold-ch` for GRETIL's Satapatha), counted in aksharas; 7-letter anchors unique in the reference find a
  unit, at two places where the reading gives it twice; difflib aligns it (upper bounds); the pair splits each reading's
  own misreadings from the shared ones. Reports: `data/source_fidelity/<ref>[__<prefix>]__<reading>.json` (ignored by
  git: made again).
- **Measured (the backup of 22 Oct, 09:18 IST):**

  | Reading | Reference | Aksharas agreeing | Own misread / 100 |
  |---|---|---|---|
  | Markandeya, our vision text | GRETIL (adhyayas 1 to 93) | 89.50% of 32,094 | 3.58 (Tesseract 18.15) |
  | Satapatha 14.4 to 14.9, our text | GRETIL kanda 14 | 82.23% of 33,815 | 3.62 (Tesseract 24.49) |
  | Surya Siddhanta, our scan (Tesseract) | the e-text | 78.79% of 16,273 | - |
  | Samasrami's Satapatha, archive.org's text, vols 1 to 3, 5 to 7, 9 | GRETIL | 48.94% to 55.39% | - |

- **Found:** vision's errors are fluent (plausible words, haplography), invisible to the judge and to the noise
  measure; the shared column for the Satapatha is mostly its print giving each kandika twice; repair_text.py's fallback
  vision price ($0.0004 a page) is an eighth of October's meter ($0.0032: 2,987 calls, $9.57).
- **Tests:** test_source_fidelity_2026_10_22 (20), test_docs84_2026_10_22 (3).
"""

RUNBOOK = """

## Letter fidelity: measure a text against its e-text (DOCS84_2026_10_22)

docs/FIDELITY_2026-10-22.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\\patch_docs84_2026_10_22.py --check`, then without `--check`; then `python -m
   unittest tests.test_source_fidelity_2026_10_22 tests.test_docs84_2026_10_22`.
2. Free, read-only: `python scripts\\source_fidelity.py --ref db:markandeya_purana__w_gretil --cand db:markandeya_purana
   --cand raw:markandeya_purana --pair db:markandeya_purana,raw:markandeya_purana`; the same for the Satapatha
   (`--ref witness:satapatha_madhyandina__w_gretil --prefix 14. --fold-ch`) and the Surya (`--ref
   db:jyotish_surya_siddhanta__w_etext --cand db:jyotish_surya_siddhanta`); then `python scripts\\source_fidelity.py
   --ledger --csv exports\\source_ledger.csv`.
3. The same scan: archive.org's metadata for `in.ernet.dli.2015.405693` (a listing); if it has a `_djvu.txt` and you
   approve, it is saved as `sources\\2015_405693_Shatpath-Brahmanam\\archive_dli_2015_405693_djvu.txt` with its
   provenance beside it, then read with `--cand file:sources/2015_405693_Shatpath-Brahmanam/archive_dli_2015_405693_djvu.txt`
   and `--pair` against `db:2015_405693_Shatpath-Brahmanam`, the reference `witness:satapatha_madhyandina__w_gretil
   --prefix 14. --fold-ch`.
4. Where you replace a scan with its e-text, regenerate in full: a backup (db_backup.py), `translate_passages.py --doc
   WITNESS --engine gemini:gemini-2.5-flash` (`--limit 20` first), `qa_scan.py --doc WITNESS --lang en --write`,
   `extract_entities.py --doc WITNESS`, `build_embeddings.py --doc WITNESS --plan`, then without `--plan`. The cap
   first: `python scripts\\set_budget.py`.
"""

EP = """

## Addendum 2026-10-22 (74) (DOCS84_2026_10_22)

| # | Item | State |
|---|---|---|
| F1 | Letter fidelity, akshara by akshara, against an e-text and a second reading | Built: source_fidelity.py (FIDELITY_2026_10_22); three texts and seven archive.org volumes measured |
| F2 | archive.org's text layer of the very scans we read (DLI 2015.405693, 2015.368408) | Next: the listing, then yours to download |
| F3 | GRETIL's Nirukta, Rgveda (Aufrecht) and Samaveda as witnesses | Next: preview, write, ingest; then F1 |
| F4 | The mend: Tesseract's reading offered where vision's own misreading is shown | Designed |
| E2b | GRETIL's Markandeya in full (5,240 passages: English, names, vectors) | Yours: about $4.12 against $4.42 under the cap |
| D1b | The Satapatha's ch | Revised: from our vision of Samasrami's images, not archive.org's text (49 to 55%) |
"""

STATE = """

## 19. 22 Oct, late morning: how faithfully our Sanskrit reads (DOCS84_2026_10_22)

- **Measured:** our vision text 3.6 own misread aksharas in 100 (the Markandeya, the Satapatha's kanda 14); Tesseract
  18 and 24; archive.org's Samasrami text layers 49 to 55% agreement; the Surya's scan 78.79%.
- **Meaning:** the e-texts are the Sanskrit to translate where they exist; our scans stay as the prints.
- **The repos:** the Automaton `4c22133b` and Srangam `aec5d41`, pushed, until this release.
"""

GITIGNORE = """
# FIDELITY_2026_10_22 (DOCS84_2026_10_22): the letter-fidelity reports are made again by scripts/source_fidelity.py
# (free, read-only)
data/source_fidelity/
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, NEEDS),
           (Path("RUNBOOK.md"), RUNBOOK, NEEDS),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, NEEDS),
           (Path("docs/STATE_2026-10-18.md"), STATE, NEEDS),
           (Path(BP), BRAIN, NEEDS),
           (Path(QM), "", QM_BLIND),
           (Path(".gitignore"), GITIGNORE, "data/source_judged/")]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    plan = {}
    if not Path("docs/FIDELITY_2026-10-22.md").exists():
        print("FAIL: docs/FIDELITY_2026-10-22.md not found (it comes with this release). Nothing written."); return 2
    for p, text, needs in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if needs not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (p, needs[:40])); return 1
        for k, (old, new) in enumerate(EDITS.get(str(p).replace("\\", "/"), []), 1):
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (p, k, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if text:
            src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs84_" + stamp))
        t = p.with_name(p.name + ".tmp_docs84"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
