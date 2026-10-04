#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs5_2026_10_04.py  DOCS5_2026_10_04

Appends to docs/PLATFORM_2026-10-04.md (sections 6-8) and RUNBOOK.md: image quality
and covers, the Shelf, and the spend audit. Marker-idempotent per file, backup first.

  python scripts/patch_docs5_2026_10_04.py --check
  python scripts/patch_docs5_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS5_2026_10_04"

PLATFORM = """

## 6. Image quality and covers (IMAGE_QUALITY_2026_10_04, COVERS_2026_10_04, DOCS5_2026_10_04)

**Looked at on 2026-10-04:** Mallapurana #3 and #6, Karan_Aagama #25, Sandilya #53. All 12 generated files are 1408 x 768.

- **Usable:**
  - Sandilya #53 (Rama enthroned, Hanuman, an attendant with a chamara) is coherent.
  - Mallapurana #3 (three arena plans) is clean.
  - Mallapurana #6 (a procession) is lively, but reads as a modern storybook wash rather than manuscript painting.
- **Not usable as drawn:** Karan_Aagama #25 shows a five-faced Siva drawn as one face with four heads stuck on sideways and two arms. It also has floating emblems and a scroll of script-like squiggles. The brief did not state the iconography, so the model improvised it.
- **Size:** 16:9 at 1408 x 768 is fine on screen. On a portrait page it is a strip, and it is too small for a full-page plate or a cover.

**What changed:**

- Aspect ratio and size are now opt-in, for example `SA_IMAGE_ASPECT=3:4` and `SA_IMAGE_SIZE=2K`.
  - The API is asked for them, and the returned size is checked; a WARN prints if they were ignored.
  - Google's pricing page (read 2026-10-04) prices 3.1 Flash Image by size: 1K $0.067, 2K $0.101, 4K $0.151 per image.
- Three style presets: `SA_IMAGE_STYLE=pahari`, `palm-leaf` or `mural`.
- Idea prompts now ask for iconography.
- Covers:
  - Each cover is one idea per text, kind `cover`, with the same review steps as any other image.
  - It is drawn at 2:3 with a calm upper third and **no lettering**; the title is typeset by the edition.
  - With `--images approved`, `export_html` puts the approved cover on the title page.
  - Covers are never placed among the verse figures or sent to Booksmith as plates.

## 7. The Shelf (SHELF_2026_10_04, COLLECTIONS_2026_10_04)

`/shelf` is the library as a reader sees it. Every live text (retired ones are hidden) sits under a collection header, with:

- its cover (approved cover art, or a typographic cover);
- its display title, marked `*` when it is only derived from the code;
- its series number (for example Harita Samhita 1-6, the eighteen Smrtis);
- English and Hindi progress;
- every edition on disk: exports HTML/PDF, and the Booksmith builds.

From each text you can open the reader or the image library. Two edits are possible, both to human-owned config files, both backed up:

- confirm a display title or Devanagari title (`configs/doc_titles.json`);
- move a text to another collection (`configs/collections.json`).

Collections start as a rule-based draft (`collections_cfg.py --show`). `--draft` writes the draft as a file to edit.

## 8. Spend: is it leak-proof? (SPEND_TRUTH_2026_10_04, SPEND_AUDIT_2026_10_04)

No money leaves without a record. But the record read low, so the budget cap tripped late. Four causes, from the code:

1. **gemini-2.5-flash was priced at $0.15 / $0.60 per 1M tokens.** Two price trackers give $0.30 / $2.50; Google's page no longer lists 2.5 Flash.
2. **Translation was metered from characters (chars/4).** It never used provider tokens, so thinking tokens and the MAX_TOKENS ladder's extra calls went uncounted.
3. **The `ocr_consensus --max-usd` estimate used $0.00028 per page**, against a measured $0.00089-0.00097 (at the old prices).
4. **The maintenance task's embeddings never asked the budget**, and neither did image idea requests.

All four are fixed. `spend_audit.py` reprices the whole ledger, shows which rows were estimated, and lists every paid call site with whether it meters and whether it asks the budget.

Still metered but not gated: `extract_entities.py`, the dashboard's Ask, `judge_sample.py`, `ab_source_quality.py`, `diag_hindi_ab.py`.

The ledger is not the bill. A hard stop has to live in Google Cloud: a billing budget alert, and a lowered requests-per-day quota on the Generative Language API for the key's project.

Separately, the MAX_TOKENS ladder's default fallback model is `gemini-2.0-flash`, which a third-party price page reports was shut down on 2026-06-01. If so, that rung now fails and costs nothing. `MT_FALLBACK_MODEL` in `.env` selects another model; this is **not verified** from here.
"""

RUNBOOK = """

## Shelf, covers, spend (DOCS5_2026_10_04)

- **Shelf:** `http://127.0.0.1:5057/shelf`, after one restart while idle.
  - Collections: `python scripts/collections_cfg.py --show`. `--draft` writes `configs/collections.json` for editing.
  - Titles confirmed on the page go to `configs/doc_titles.json`.
- **Covers:** `python scripts/images.py cover --doc <code> --yes` (or `--brief "..."` to write the idea yourself). Then approve the idea, generate, and approve the image. Use `export_html --images approved` to put it on the title page.
- **Plates at book proportions:** `$env:SA_IMAGE_ASPECT="3:4"; $env:SA_IMAGE_SIZE="2K"` before `images.py generate` or `regenerate`. A WARN means the API ignored the setting.
- **Spend:**
  - `python scripts/spend_audit.py` shows recorded vs repriced spend, estimated rows, and the call sites.
  - Check the budget before translating after SPEND_TRUTH; recorded prices rose.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs5_" + stamp))
        t = p.with_name(p.name + ".tmp_docs5"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
