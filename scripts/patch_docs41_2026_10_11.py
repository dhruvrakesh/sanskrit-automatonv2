#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs41_2026_10_11.py  DOCS41_2026_10_11

Records the evening of 11 Oct: the repair path's first use, what stopped it, and REPAIR_HEAL_2026_10_11
with the Source desk (SOURCE_DESK_2026_10_11). docs/REPAIR_HEAL_2026-10-11.md has the findings, the
debris judged for the held texts, and the enterprise path (R1.1, S1-S3, R3, R4).

Appends to docs/PLATFORM_2026-10-04.md (section 44), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 31), each needing DOCS40_2026_10_10.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs41_<date>), line endings kept.

  python scripts/patch_docs41_2026_10_11.py --check
  python scripts/patch_docs41_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS41_2026_10_11"

PLATFORM = """

## 44. The repair path, healed; the debris judged; the Source desk (DOCS41_2026_10_11)

**11 Oct, evening (IST). Built and tested; to apply.**

**What the first evening of use showed** (`data/jobs.jsonl`, 18:45-18:57):
- Every *Repair the scan* refused itself. `ocr_consensus.py --yes` stops while the dashboard runs a
  job for the text, and the repair is such a job. The Tantric Texts were then set aside.
- Karan Aagama's repaired text went in at 18:51:
  - debris 32% to 9%, vision 0% to 87%, drift 183 of 183 current;
  - backup `D:\\backups\\context_pre_repair_Karan_..._20261011_185037.db`.

  Then the path stopped: no English, no translate button, a stale *held* note, and "open the Library".
- The Log did show the runs, but cut a repair's verdict to *done*. The Live tab showed only
  translations.
- The next mirror run would have sent Karan's new Sanskrit to the site without its English.

**The debris, judged.** The guard's "two Latin letters in a verse" is now split into:
- furniture (a watermark or a running head, repeated on many pages);
- notes (English);
- numbering (Roman numerals);
- misread letters (Devanagari read as Latin), which is the only kind that harms the text.

Vision agreement is measured where vision pages exist. The levels are cosmetic (translate as is),
moderate, and material.

On the backup of 10 Oct:

| Text | Judged |
|---|---|
| Natyasastra | material (misread in 50% of verses) |
| Tantric Texts | material (46%; vision agreement 0.78) |
| Hayashirsha | material (44%) |
| Karan Aagama, before its repair | moderate (11%; two-thirds of its debris was the eGangotri watermark; agreement 0.95) |
| Ganita | not held; what is left is English front and back matter read as Devanagari: accept as complete |

**REPAIR_HEAL_2026_10_11** (`scripts/patch_repair_heal_2026_10_11.py`) changes:
- `ocr_consensus.py` looks past the job that asked for the repair;
- `translate_passages.py` lets a text through when it is to be translated as is;
- `corpus_sync.py` does not send a text in repair, so the site keeps its last version until
  `--release`;
- in `dashboard.py` (on a restart):
  - the Library shows the states, and offers *Translate it now* after a repair;
  - *Not yet readable* offers the texts with no English their translation;
  - the repair page shows the debris judged and the Source desk;
  - a job record keeps its verdict in full;
- in the page (on a reload), the Live tab shows *Running now*.

`scripts/repair_text.py` gains `--as-is`, `--accept`, `--hold`, `--release` and `--find-source`.
`scripts/source_desk.py` (new) does the following:
- searches archive.org, the local wisdomlib archive and the e-text sites (links);
- ranks the editions, with reasons;
- optionally asks the AI (one call, about $0.002);
- fetches a PDF or a pure OCR text into `sources\\<doc>\\` with its provenance.

**Tests:**
- `tests/test_repair_heal_2026_10_11.py` (28);
- `tests/test_repair_text_2026_10_10.py` and `tests/test_repair_path_2026_10_10.py`, updated.

Nothing that passed before fails.
"""

RUNBOOK = """

## The repair path, healed (DOCS41_2026_10_11)

1. **Before a re-ingest replaces translations,** the text is held from the site. `--use-repaired` does
   this by itself. By hand: `python scripts\\repair_text.py --doc <code> --hold`.
   - Publish it when it is translated again: `--release`.
   - A text in repair is named in the mirror run's *held* list.
2. **Debris that is cosmetic:**
   - `python scripts\\repair_text.py --doc <code>` judges it;
   - `--as-is "debris judged cosmetic"` lets the guard pass it;
   - `--restore` undoes that.
3. **What is left is not Sanskrit** (English front and back matter, lone dandas): `--accept "what is
   left is not Sanskrit"`.
4. **A better edition:**
   - On the repair page, the Source desk: *Find a better source*, *Preview here*, *Fetch the PDF*.
   - By hand: `python scripts\\source_desk.py --doc <code>`, then `--fetch <identifier> --kind pdf`.
   - A fetched PDF lands in `sources\\<code>\\`. Import it as a new witness (Import path to inbox) once
     you have looked at it.
5. **Pause the mirror** while a text is being rebuilt and the patch is not in place:
   - `Disable-ScheduledTask -TaskName SanskritCorpusMirror`;
   - `Enable-ScheduledTask -TaskName SanskritCorpusMirror` afterwards.
"""

EP = """

## Addendum 2026-10-11 (31) (DOCS41_2026_10_11)

| # | Item | State |
|---|---|---|
| R1.1 | The repair path healed: the repair no longer refuses itself; states (as is, complete, in repair, set aside); Translate it now; the site keeps its version while a text is rebuilt | Built and tested (REPAIR_HEAL_2026_10_11). Next: patch, hold Karan, restart when idle |
| J1 | The debris judged: furniture, notes, numbering, misread letters; vision agreement; cosmetic, moderate, material | Built and tested; shown on the repair page and in the assessment |
| S1 | The Source desk: archive.org, the wisdomlib archive and the e-text sites; ranking with reasons; AI judgement (about $0.002); preview in the page; fetch to `sources\\` | Built and tested (SOURCE_DESK_2026_10_11) |
| O1 | Karan Aagama | Re-ingested at 18:51 (moderate; agreement 0.95). Next: hold from the site, translate English and Hindi, release |
| O3 | Natyasastra, Tantric Texts, Hayashirsha | Material. Next: repair the scan (Tantric: restore first, 72 pages left); else the Source desk |
| O5 | Ganita | What is left is not Sanskrit. Next: accept as complete |
| S2 | An e-text (GRETIL, sanskritdocuments.org, wisdomlib) ingested as a witness, no OCR | Next |
| S3 | The missing page sourced from a fetched witness (n-gram alignment), offered on the repair page | Designed |
| R3 | In-place re-ingest that keeps passage ids and re-anchors pictures and stories | Designed |
| C14 | "Sources wanted" in the Researchers' Corner, from the register and the Source desk | Designed; needs a table and the mirror |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS40_2026_10_10"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS40_2026_10_10"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS40_2026_10_10")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs41_" + stamp))
        t = p.with_name(p.name + ".tmp_docs41"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
