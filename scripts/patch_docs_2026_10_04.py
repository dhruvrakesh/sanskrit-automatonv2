#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs_2026_10_04.py  DOCS_2026_10_04

Appends the 2026-10-04 findings to three documents. Marker-idempotent per file
(a file that already carries the marker is skipped), backup first, atomic replace.

  docs/OCR_CONSENSUS_2026-09-30.md        section 9: the hi-v5 gate, paired, and the decision
  docs/EDITIONS_AND_IMAGES_2026-10-03.md  section 6: I4 shipped, Booksmith plates bridge
  RUNBOOK.md                              "Is the corpus up to date?" (corpus_status.py)

  python scripts/patch_docs_2026_10_04.py --check
  python scripts/patch_docs_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS_2026_10_04"

OCR_S9 = """

## 9. The hi-v5 gate, paired, and the decision (2026-10-04, DOCS_2026_10_04)

hi-v5 (`hi-file-37e6ff9a2b`) was put into production on 2026-10-03 before its gate was read. The four v5 runs are now compared with the v4 runs of the same morning. For three books the 40 verses are **the same verses** (passage ids overlap 40 of 40), so the comparison is paired. All runs use arm d (no English reference) and the lacuna population.

| Book (same 40 verses) | Verses with a lacuna, v4 / v5 | Lacuna tokens, v4 / v5 | Conjectures, v4 / v5 | Unmarked damage, v4 / v5 |
|---|---|---|---|---|
| HAYASHIRSHA_PANCARATRA | 16 / 25 | 28 / 38 | 94 / 124 | 2 / 0 |
| harita_tritiya_sthanam | 28 / 33 | 100 / 146 | 344 / 523 | 2 / 0 |
| nilamata_seg | 18 / 24 | 23 / 29 | 49 / 56 | 1 / 1 |
| **Total (120 verses)** | **62 / 82** | **151 / 213** | **487 / 703** | **5 / 1** |

markandeya_purana is not paired (the samples share 1 verse). Its unpaired figures are v4 12/40 and v5 16/40.

**Hand check.** I read six verses where the two prompts disagree on whether to mark a lacuna:

- v4 is better in four:
  - `facta` gave v4 \u27e8\u0935\u093f\u0926\u0940\u0930\u094d\u0923 \u0915\u0930\u094b\u27e9; v5 left the sentence without its verb.
  - `SHEET` gave v4 \u27e8\u0926\u0947\u0916\u0915\u0930\u27e9; v5 both marked the gap and guessed.
  - Verse 60251 is fluent under v4.
  - In verse 101301, v5 put the readable \u091a\u0948\u0935 in \u27e8\u27e9, breaking its own rule 11(\u0916).
- v5 is better in one. In 101221, v4 echoed the Sanskrit lines into the Hindi. Echoes are rare under both prompts: v4 1-2 per 40 verses, v5 1-4.
- Neither is right in one. In 101423, \u0936\u0930\u0917\u0941\u0937\u094d\u0935 is \u0936\u0943\u0923\u0941\u0937\u094d\u0935 ("listen"), and both prompts missed it.

**Decision: production goes back to v4.** Copy `prompts/hi-v4-candidate.txt` over `prompts/hi-production.txt`; the version becomes `hi-file-18a0d5f5eb`. v5 has one real gain, "every damaged spot is marked" (unmarked 5 to 1), and it costs 20 more verses with gaps out of 120. The candidate for that gain is a v6 that adds only rule 11(\u0918) to v4, gated paired against v4 on the same 120 verses before any switch.

**What prompts cannot do.** The source-junk column of the A/B files shows that 29 to 40 of every 40 sampled verses carry Tesseract debris (Latin fragments inside Devanagari). After the production `--only-lacuna` runs, these books still carry lacunas on 37-57% of their Hindi rows: markandeya, HAYASHIRSHA, nilamata. The damage is in the source text. The order that converges is:

1. vision consensus;
2. wipe and re-ingest from raw_merged;
3. translate. Changed text is a new cache key, so only changed verses are paid for.

`scripts/corpus_status.py` now says this per book (RUNBOOK, "Is the corpus up to date?").

**Upsert caveat, verified in `ingest_jsonl_fast.py`.** On re-ingest, `ON CONFLICT ... DO UPDATE` replaces `text` but deliberately not `translation`. Re-ingesting changed text on top of a doc, without `wipe_doc.py` first, would therefore leave old translations attached to new text, possibly to different verses if segmentation moved. `reingest_commands()` always wipes first. Keep it that way.
"""

ED_S6 = """

## 6. Images in the editions (2026-10-04, EXPORT_IMAGES_2026_10_04, BOOKSMITH_PLATES_2026_10_04, DOCS_2026_10_04)

Until today an approved image appeared nowhere but the Images tab. There are now two opt-in paths, and both defaults are unchanged.

| | HTML / PDF edition (`export_html.py --images approved`, then `export_pdf.py`) | Booksmith (`booksmith_build.py --plates approved`) |
|---|---|---|
| Placement | Right after the verse it is anchored to. If that verse is filtered out (noise or frontmatter), it goes at the end of the section holding that page. | Evenly spaced through the book. Booksmith has no anchors (renderer.py 305-310). |
| Which images | Every approved image: generated, edition-plate, diagram. | Approved **generated** images only. Booksmith captions every plate "Symbolic editorial artwork; not a textual witness", which would be false for a scan of the source edition. |
| Caption | Title; English and/or Hindi caption (following the edition's languages); the context note; and for generated images the label "Illustration - generated, not a historical source." (Hindi equivalent in a Hindi edition). | Booksmith's fixed caption. Ours are not shown. |
| Files | Images are embedded (data: URI, 1400 px JPEG), so the HTML is self-contained and prints from `exports/_print/`. The name gains `_img`, so the plain edition is never overwritten. | Copied to `<project>/assets/plates/imglib_<id>_v<ver>.<ext>`. The project's own plates are kept first; at most 12 plates in all. |
| Default | `--images none`: byte-for-byte the old output. This matters because Booksmith freezes the witness sha256, so a changed default would clear every project's manifest. | `--plates none`: book.yaml is untouched. |
| Safety | Read-only on the DB. | Idempotent: an unchanged list writes nothing. If `work/decisions.jsonl` holds human decisions, it **refuses** before copying anything. Otherwise it backs up book.yaml to `work/book.yaml.bak_plates_<stamp>`, clears the derived manifest and PDFs (as a changed witness does), and saves through Booksmith's own BookConfig model. |

Recommendation: use the HTML/PDF edition for illustrated books. Use Booksmith plates only when a Booksmith audit or proof is the deliverable.

Tests: `tests/test_export_images.py` (5), `tests/test_booksmith_plates.py` (6). Both fail before their patch and pass after. The default export was compared byte for byte, before and after, in three modes.
"""

RUNBOOK = """

## Is the corpus up to date? (CORPUS_STATUS_2026_10_04, DOCS_2026_10_04)

`python scripts/corpus_status.py` is read-only and safe while jobs run. It gives one line per text.

It measures:

- OCR source share;
- drift against raw_merged;
- English and Hindi completeness, prompt currency and lacuna rate;
- approved images.

It returns one verdict in pipeline order: NEEDS-OCR, then NEEDS-REINGEST, then NEEDS-TRANSLATION, then AGED, then CURRENT.

`--commands` prints the next commands, in that order. Every one of them is idempotent, so running the status, then the commands, then the status again converges. "Negligible lacunae" is `--lacuna-ok` (default 5%). AGED means complete and clean, with some rows on older prompt versions; that is acceptable, and re-translation there is a choice, not a repair.
"""

TARGETS = [(Path("docs/OCR_CONSENSUS_2026-09-30.md"), OCR_S9),
           (Path("docs/EDITIONS_AND_IMAGES_2026-10-03.md"), ED_S6),
           (Path("RUNBOOK.md"), RUNBOOK)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs_" + stamp))
        t = p.with_name(p.name + ".tmp_docs"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
