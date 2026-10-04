#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs2_2026_10_04.py  DOCS2_2026_10_04

Appends the findings of the first corpus-wide status run (2026-10-04 09:16) and
the fixes that followed. Marker-idempotent per file, backup first, atomic replace.

  docs/OCR_CONSENSUS_2026-09-30.md        section 10: corpus status v1 -> v2, calibration, provenance
  docs/EDITIONS_AND_IMAGES_2026-10-03.md  section 7: the first illustrated runs
  RUNBOOK.md                              verdicts as of v2

  python scripts/patch_docs2_2026_10_04.py --check
  python scripts/patch_docs2_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS2_2026_10_04"

OCR_S10 = """

## 10. The first corpus-wide status, and why v1 of it was wrong (2026-10-04, DOCS2_2026_10_04)

`corpus_status.py` v1 ran on 36 docs (at least 20 passages each). It returned NEEDS-OCR for 15 and NEEDS-TRANSLATION for 21. It judged source damage from **lacuna rates**, which is the wrong evidence. It went wrong in two directions:

- **It sent clean-English books to OCR on Hindi lacunae alone.** For example, vasishtha_dhanur_veda had English 0.0% and Hindi 72.7%, and harita_prathama_sthanam had English 2.7% and Hindi 56.4%. Older Hindi prompts produce those lacunae.
- **It sent untranslated Tesseract books to translation.** A book with no translations has no lacunae, so v1 read it as clean. Examples are 476948-Rgveda-samhita_Vol-ii (7,053 passages) and SP_4214_Pataal_Khanda (19,071 passages). Translating Tesseract debris is the most expensive mistake available.

**v2 (`CORPUS_STATUS2_2026_10_04`) measures the source.** Source debris is the share of passages with at least 8 Devanagari characters that contain Latin-letter runs. It is the same JUNK test that `diag_hindi_ab.py` uses. I calibrated it on the page files on 2026-10-04, counting per text line:

| Producer | Debris |
|---|---|
| Tesseract (`data/raw`) | Ganita 10.3%, Karan 13.5%, manu 17.7%, jyotish 19.4%, upapurana_nilamata 20.2%, harita smriti 21.3%, harita_tritiya 22.2%, nirukta 24.5%, markandeya 26.4%, Natyasastra 29.6%, Bodhicaryavatara 33.8%, tantric texts 35.2%, vasishtha 35.8%, shukla yajur 35.8%, HAYASHIRSHA 36.0%, Sandilya 38.4%, Mallapurana 43.6%, Pataal Khanda 48.5%, LalitaVistara 49.6%, Rgveda 53.9%, Shatapatha 58.5%, bodhyana 70.9% |
| Vision (`data/raw_vision`) | Shatapatha 0.0% (merged 0.9%), Rgveda 0.5%, Sandilya 1.8%. Mallapurana is 10.4% (merged 11.7%); that comes from plate captions and its 5 refused pages. |
| E-text | MBh01 0.0% (raw engine `gretil-bori-etext`) |

So `--debris-ok` defaults to 5%. NEEDS-OCR now means: debris above 5%, fewer than half the passages from vision, and page PDFs present in inbox. No translation is recommended until consensus is done.

**Provenance is read from the page files, not inferred.** Three docs carry engine `resegment-devnum` with `meta.src_doc`:

| Derived doc | Source doc |
|---|---|
| nilamata_seg | upapurana_nilamata_purana |
| smriti_14manu_smriti_seg | smriti_14manu_smriti |
| smriti_16harita_smriti_seg | smriti_16harita_smriti |

Their pages match their sources' pages at only 0.06-0.19 similarity (sampled pages 10, 30 and 60). That is expected, because they are the same text cut at different places. So a derived doc is never re-OCR'd itself. The order is:

1. vision on the source;
2. re-ingest the source;
3. `resegment_doc.py`;
4. wipe the derived doc and ingest it with `--no-segment`.

The verdict for these is DERIVED-NEEDS-OCR. This follows the rule `diag_corpus_overlap.py` records: row counts are not evidence.

**Source PDFs.** vision needs `inbox/<code>_NNNN.pdf`. None exist for LalitaVistara, Bodhicaryavatara, bodhyana, vasishtha_dhanur_veda or shiva_dhanur_veda; their verdict is NO-SOURCE-PDF. MBh01 is e-text and needs none.

For vasishtha_dhanur_veda and shiva_dhanur_veda, inbox holds `dhanur_veda_vasishtha_dhanur_veda_*` (32 pages) and `dhanur_veda_shiva_dhanur_veda_*` (19 pages), the same page counts as their raw files. That is a hint only; their raw pages 10, 30 and 60 matched at 0.47, 0.10 and 1.0. The report offers a copy-with-rename command, to run after a person compares two pages.

**Fixed with it (`MAINT_2026_10_04`):**

- `resegment_doc.py` wrote one file per source page but opened it once per source passage. On a segmented source, only each page's last passage survived. Consecutive entries are now merged. Page-blob sources give identical output.
- `images.py approve` stopped at the first already-approved id (`approve 3 4 5 6 10` left 6 and 10 as drafts). It now skips and continues.
- `tests/test_translation_filters2.py` asserted the built-in Hindi version, so it failed whenever a reviewed prompt file was active. It now checks the built-in prompt in a child process with the file switched off. That was the one failure in the 117-test suite.
"""

ED_S7 = """

## 7. First illustrated runs (2026-10-04, DOCS2_2026_10_04)

- **HTML/PDF route.** `export_html.py --images approved` on Mallapurana placed 3 of 3 approved images (#3, #4, #5), with 0 outside the pages. `export_pdf.py` printed `Mallapurana_1-137_tri_img.pdf`: 81 pages A4, 2,057 KB, in 32.6 s.
- **Booksmith route.** `booksmith_build.py --doc Mallapurana --mode hi --plates approved` ran as follows:
  - The witness had changed (new Hindi rows), so it cleared the manifest, as designed.
  - It wrote plates `imglib_3_v1`, `imglib_4_v1` and `imglib_5_v1` into book.yaml (`illustrations_per_volume` 3).
  - The audit found 86 findings, none at error level: 19 missing-language and 67 ocr-intrusion. The 19 match the 19 passages without Hindi in corpus_status.
  - `book.pdf` came out at 192 pages, 3,571,743 bytes, and QA passed.
  - `font_scan` stderr shows "No display font for 'Symbol' / 'ArialUnicode'". That is the PDF font scanner's own warning, and `unembedded` is empty.
- Images #6 and #10 stayed drafts because `approve` stopped early (fixed in MAINT_2026_10_04). After approving them, re-run both routes. Booksmith rewrites plates idempotently and spaces 5 evenly.
"""

RUNBOOK2 = """

### Verdicts as of corpus_status v2 (CORPUS_STATUS2_2026_10_04, DOCS2_2026_10_04)

The verdicts, in order:

1. DERIVED-NEEDS-OCR
2. NEEDS-OCR
3. NO-SOURCE-PDF
4. NEEDS-REINGEST
5. NEEDS-TRANSLATION
6. AGED
7. CURRENT

Source damage is judged from **source debris** (`--debris-ok`, default 5%), never from lacuna rates. A derived doc (`resegment-devnum`) is repaired through its source. Each command line carries a cost estimate:

- vision at $0.0015 per page;
- translation at the measured $/passage from usage_log, which is a lower bound.

Work one book at a time, only when the dashboard reads idle, and re-run the status after each book.
"""

TARGETS = [(Path("docs/OCR_CONSENSUS_2026-09-30.md"), OCR_S10),
           (Path("docs/EDITIONS_AND_IMAGES_2026-10-03.md"), ED_S7),
           (Path("RUNBOOK.md"), RUNBOOK2)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs2_" + stamp))
        t = p.with_name(p.name + ".tmp_docs2"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
