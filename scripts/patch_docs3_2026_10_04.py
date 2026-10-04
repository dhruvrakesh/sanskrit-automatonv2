#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs3_2026_10_04.py  DOCS3_2026_10_04

Appends the 2026-10-04 afternoon findings (the guards) to
docs/OCR_CONSENSUS_2026-09-30.md (section 11) and RUNBOOK.md.
Marker-idempotent per file, backup first, atomic replace.

  python scripts/patch_docs3_2026_10_04.py --check
  python scripts/patch_docs3_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS3_2026_10_04"

OCR_S11 = """

## 11. Two doors, two guards (2026-10-04 afternoon, DOCS3_2026_10_04)

**The pilot did not run.** `ocr_consensus.py --doc markandeya_purana --threshold 101 --yes` stopped at triage: "100 page(s) have no confidence recorded (OCR'd before 2026-08-30)". Pages OCR'd before that date carry no Tesseract confidence, so triage has nothing to rank. `--include-unassessed` queues every inbox page; corpus_status now prints it on every consensus command. Nothing was spent and nothing was written.

**INGEST_SOURCE_2026_10_04 (scripts/ingest_jsonl_fast.py).** Two faults were found in the code and files:

- *The glob caught other books.* The glob `<doc>_*.jsonl` also matches docs whose code starts with `<doc>_`. data/raw holds 208 `smriti_14manu_smriti_seg_*` files beside the 208 `smriti_14manu_smriti_*` files, and the same holds for `smriti_16harita_smriti`. Ingesting the source doc therefore also ingested the derived doc's files on the same page numbers. Both manu docs show 2,568 rows, which is consistent with this.
  - Only `<doc>_NNNN.jsonl` and `<doc>_NNNN_norm.jsonl` are taken now.
  - The others are named in the log.
- *Ingest could undo consensus.* The dashboard Ingest button and `advance_pipeline.py` ("Translate All OCR'd") ingest `data/raw/<doc>_*.jsonl`, which is Tesseract text. For a doc with consensus, that put Tesseract text back over vision text, and upsert keeps the old translations on the new text. Now:

  | Situation | What ingest does |
  |---|---|
  | `data/raw_merged` covers every page | ingests raw_merged and says so |
  | `data/raw_merged` covers only some pages | refuses (exit 3) |
  | `--source raw` | Tesseract, deliberately |
  | `--source given` | the glob exactly as given (the old behaviour) |

  This fixes plan item C2 at the one place every path goes through.

**TRANSLATE_DEBRIS_GUARD_2026_10_04 (scripts/translate_passages.py).** Before any API call, it refuses (exit 3) when all three of these hold:

- more than 30% of passages carry debris (`--debris-max`, env `SA_DEBRIS_MAX`);
- fewer than half the passages come from vision;
- inbox holds page PDFs for the doc.

On the page-file measurements, that stops Rgveda Vol-ii (53.9%), Pataal Khanda (48.5%) and HAYASHIRSHA (36.0%). It lets these through:

- Ganita (10.3%), whose translation was running at 12:21 (1,069 of 2,592 verses);
- Natyasastra (29.6%);
- every book with no source PDF.

You can override it with `--allow-debris`, or with env `SA_ALLOW_DEBRIS=1` for dashboard runs. Single-verse reader requests are never blocked.

**Measured translation cost:** $0.00021 per passage (corpus_status, from usage_log). For example, Ganita's 2,592 verses cost about $0.54, a lower bound. A Tesseract-to-vision re-ingest later changes nearly every verse's text, so those translations are paid for again.

**Release:** `release.ps1` without `-Apply` is a dry run. The 2026-10-04 dry run listed 19 clean paths.
"""

RB3 = """

### Ingest and translate guards (INGEST_SOURCE_2026_10_04, TRANSLATE_DEBRIS_GUARD_2026_10_04, DOCS3_2026_10_04)

**Ingest:**

- If complete OCR consensus exists in `data/raw_merged`, ingest uses it, even when it is asked for `data/raw`.
- With only partial consensus, ingest refuses. Finish the consensus, or pass `--source raw` deliberately.
- The plain glob `<doc>_*.jsonl` no longer picks up another doc's files (for example `<doc>_seg_*`).

**Translate:** it refuses repairable Tesseract text when all of these hold:

- more than 30% of passages carry debris;
- fewer than half the passages come from vision;
- page PDFs are in inbox.

Run `ocr_consensus.py --threshold 101 --include-unassessed` first. Override with `--allow-debris`, or with `SA_ALLOW_DEBRIS=1` for the dashboard.

Both refusals exit with code 3 and print the next command.
"""

TARGETS = [(Path("docs/OCR_CONSENSUS_2026-09-30.md"), OCR_S11), (Path("RUNBOOK.md"), RB3)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs3_" + stamp))
        t = p.with_name(p.name + ".tmp_docs3"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
