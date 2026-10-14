#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs53_2026_10_14.py  DOCS53_2026_10_14

Records the night of 14 Oct: the scholarly English's pilot (MBh01 1.1.0-1.1.24: 23 passed, 1 flagged, $0.238);
SCHOLAR_V2_2026_10_14 (sentences over verses drafted whole, a second judge that reads both Englishes side by side,
notes held to three, the price by prompt version, a prose view); ETEXT_META_2026_10_14 (scripts/heal_etext_meta.py:
an e-text's passages say they are one, so MBh01 stops showing "Q:53%" and "OCR confidence 52%"); and the evening's
runs. docs/SCHOLAR_V2_2026-10-14.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 56), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 43), each needing DOCS52_2026_10_14.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs53_<date>), line endings kept.

  python scripts/patch_docs53_2026_10_14.py --check
  python scripts/patch_docs53_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS53_2026_10_14"

PLATFORM = """

## 56. The scholarly English after its pilot; an e-text that says so (DOCS53_2026_10_14)

**14 Oct (IST), the night.** docs/SCHOLAR_V2_2026-10-14.md has the details.
- **The pilot (MBh01 1.1.0-1.1.24, scholar-v1):** 24 verses, 23 passed, 1 flagged (1.1.8, accepted by a person);
  $0.238, $0.0099 a verse (the prior said $0.051). It names the persons right where the working English does not
  (1.1.5: the narrator, not his father; 1.1.8: Janamejaya's own patronymic, after the critic's revision).
- **What it showed to mend:** a Sanskrit sentence over several verses (1.1.15-1.1.19) came out in fragments; the
  flash judge reads a verse alone and gave the working English of 1.1.5 5 of 5; notes ran to six a verse, with
  common words and one misspelling.
- **SCHOLAR_V2_2026_10_14 (scholar-v2, scholar-critic-v2):**
  - sentences: one call (scholar-groups-v1) says where each Sanskrit sentence ends (6 verses at most); a sentence
    over verses is drafted, criticised and judged as one, stored verse by verse with `group_ref` and
    `group_translation`; an answer that does not fit is not used (`--no-groups`: as before);
  - a second judge (scholar-compare-v1, gemini-2.5-pro) reads both Englishes side by side in an order it is not
    told; a major error in the scholarly English flags the verse (`--no-compare`: as before);
  - notes: three at most, none for a common word, the Sanskrit spelt as the IAST given is; the critic reads them;
  - the price is the prompt version's own mean after 10 rows; before that about $0.015 a verse;
  - the pages: a sentence is one block; the second judge's verdict; the earlier version under the fold;
    `/scholar/<doc>/prose` and `exports\\scholar_<doc>_prose.html`, the text read as a book;
  - new columns are added in place; the old rows stay as version 1.
- **The importer:** `import_mbh_gretil.py --src` with a missing file says so (no traceback).
- **ETEXT_META_2026_10_14:** MBh01's "Q:53%" is the OCR formula (0.6 x Devanagari share + 0.4 x dandas up to 5)
  on an e-text without dandas: 0.48 to 0.58 whatever its quality. It is not the Hindi's score and it does not change
  what is translated (the bar is 0.35). It does tell the site's readers "OCR confidence 52%", and on 267 verses "the
  printed page was hard to read". `scripts/heal_etext_meta.py` sets the engine and 0.98 (the ingest's e-text value)
  where the page file's e-text record has the same verse and text; plan by default, backup, one transaction, a log
  and `--undo`. On the 14 Oct backup, all 496 passages of MBh01's first three pages match.
- **The evening's runs:** the release `838e6a4` went in and was pushed; the dashboard was not restarted
  (`--force` is not PowerShell's `-Force`); the Yoga Vasistha is retired by the full mirror (`--doc` refuses a
  withdrawn text); T2: 7 mended, 9 to a person, 2 failed; Karan and the Hayashirsha refused `--release` (their
  English is not back); 11 vectors on passages without English are debris of two scans to repair.

**Tests:**
- `tests/test_scholar_v2_2026_10_14.py` (16);
- `tests/test_etext_meta_2026_10_14.py` (2);
- `tests/test_scholar_2026_10_14.py` and `tests/test_mbh_prose_2026_10_14.py` follow v2.
"""

RUNBOOK = """

## The scholarly English, version 2 (DOCS53_2026_10_14)

`scholar_translate.py` now reads sentences, not only verses, and asks a second judge. Both are on by default.

1. The dry run says how many sentences run over verses, and what it costs (free):

       python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --redo

2. The run, capped: its `NEXT:` line, or `--redo --yes --max-usd 0.75` (about $0.36 for the pilot's 24 verses).
3. Read it two ways:
   - as verses: http://127.0.0.1:5057/scholar/MBh01 (the earlier version is under each verse);
   - as prose: http://127.0.0.1:5057/scholar/MBh01/prose;
   - or `--report`: exports\\scholar_MBh01.html and exports\\scholar_MBh01_prose.html.
4. A verse the second judge calls worse, or flags, is read by a person (`--review`).
5. `--no-groups` and `--no-compare` give the v1 behaviour.

The dashboard serves `/scholar/<doc>/prose` only after a restart. Restart when it is idle:

    .\\scripts\\restart_dashboard.ps1 -Status
    .\\scripts\\restart_dashboard.ps1

`-Force` cuts the running jobs off; `--force` is not a PowerShell form.

## An e-text that says it is one (DOCS53_2026_10_14)

A text that came in from an e-text before 20 Jul 2026 has the OCR formula's quality (no dandas: 0.6 at most) and no
engine. The site then calls it "OCR confidence" and marks verses "hard to read".

1. The plan (free, read-only):

       python scripts\\heal_etext_meta.py --doc MBh01

2. `--apply` (a backup to D:\\backups first, the values before to data\\heal\\). Refused while the dashboard changes
   that text; a Hindi job does not stop it.
3. The mirror: `python scripts\\corpus_sync.py`, then its `--apply`.
4. To put it back: `--undo data\\heal\\etext_meta_MBh01_<stamp>.jsonl` (the file the apply printed).
"""

EP = """

## Addendum 2026-10-14 (43) (DOCS53_2026_10_14)

| # | Item | State |
|---|---|---|
| SC1 | A scholarly English | Pilot done (scholar-v1): 24 verses, 23 passed, $0.238 |
| SC3 | Sentences over verses; a second judge; notes held | Built and tested (SCHOLAR_V2_2026_10_14); the pilot again with v2, about $0.36 |
| SC4 | The prose view (the text read as a book) | Built (`/scholar/<doc>/prose`, `--report`) |
| SC5 | MBh01 chapter 1, then the whole book | After the v2 pilot is read: about $3, then about $105 |
| EM1 | An e-text's passages say they are one (MBh01's Q:53%) | Built and tested (ETEXT_META_2026_10_14); plan, apply, then the mirror |
| MB1 | MBh01's lost prose | The e-text is not in sources yet; the importer can fetch it (no `--src`) |
| YV1 | The Yoga Vasistha | Withdrawn here; the full mirror retires it on the site |
| S2 | Srangam: name the reading (e-text, vision OCR, Tesseract), not "OCR confidence" for all | A read-only function; after EM1 |
| S4 | Srangam: the scholarly English in the reader (rows a person accepted) | After SC3's pilot is read |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS52_2026_10_14"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS52_2026_10_14"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS52_2026_10_14")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs53_" + stamp))
        t = p.with_name(p.name + ".tmp_docs53"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
