#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs52_2026_10_14.py  DOCS52_2026_10_14

Records the evening of 14 Oct: the question "is a Debroy-grade translation done?" (no: the working English is one
flash pass); SCHOLAR_2026_10_14 (scripts/scholar_translate.py, a scholarly English beside the working one: context,
glossary, notes, a critic, revisions, a judge of both Englishes; /scholar); HOLD_2026_10_14 (no paid translation where
the scan or the source comes first; a withdrawn or set-aside text refused); MBH_PROSE_2026_10_14 (MBh01's lost prose,
and why); the Yoga Vasistha found to be a Hindi book. docs/SCHOLAR_2026-10-14.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 55), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 42), each needing DOCS51_2026_10_14.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs52_<date>), line endings kept.

  python scripts/patch_docs52_2026_10_14.py --check
  python scripts/patch_docs52_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS52_2026_10_14"

PLATFORM = """

## 55. A scholarly English, and holding what is not ready (DOCS52_2026_10_14)

**14 Oct (IST), the evening.** docs/SCHOLAR_2026-10-14.md has the details.
- **Asked:** is a Debroy-grade translation done? **No.** The working English is one gemini-2.5-flash pass with five
  verses of context: no glossary kept, no notes, no critic. A judge reads a sample. Two examples in MBh01's chapter
  1: 1.1.8 makes Janamejaya's patronymic a second man; 1.1.5 calls the narrator by his father's name.
- **SCHOLAR_2026_10_14:** `scripts/scholar_translate.py` makes a scholarly English beside the working one, which it
  never touches. For each verse:
  - the verse with 6 verses before (Sanskrit and English) and 2 after, and the text's glossary;
  - a draft, a critic word by word, up to two revisions (gemini-2.5-pro);
  - the judge of both Englishes (judge-v1).
  It is stored append-only with the Sanskrit's hash (a changed reading makes a row stale), and costs about $0.05 a
  verse (a prior until 10 are measured). It is a dry run by default; `/scholar` shows it, read-only.
- **HOLD_2026_10_14:** the Library no longer offers Finish EN / Add Hindi where the path says repair the scan, a
  better source or retire (31 cards on 14 Oct). `translate_passages.py` refuses a whole text that is withdrawn or set
  aside (exit 4).
- **MBH_PROSE_2026_10_14:** MBh01 lacks every prose passage of the critical edition (1.1.1, 1.3.2-59 ...). A prose
  line ends in a capital letter (the e-text's readme) and the importer read lower case only. Fixed: the importer, and
  `reingest_pages.py --no-segment`. The e-text itself is saved by a person.
- **The Yoga Vasistha** is Lala Baijnath's Hindi bhasha-tika with the Sanskrit in it: 317 of 325 pages sampled carry
  Hindi prose, and the Tesseract reading carries Latin debris. It is on the site as Sanskrit (70,292 passages):
  withdraw it, then separate the Sanskrit.

**Tests:**
- `tests/test_scholar_2026_10_14.py` (17);
- `tests/test_mbh_prose_2026_10_14.py` (6).
"""

RUNBOOK = """

## The scholarly English (DOCS52_2026_10_14)

`scripts/scholar_translate.py` is a dry run unless `--yes`: what it sends, what it leaves out, what it costs.

1. The dry run, and the prompt the first verse gets (free):

       python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --show-prompt

2. The run, capped: the `NEXT:` line it prints, or `--yes --max-usd 1.50`.
3. Read it: http://127.0.0.1:5057/scholar/MBh01, or `--report` (exports\\scholar_MBh01.html).
4. A person's word:
   - `--review 1.1.8 --verdict accept --by NAME` on the current version;
   - `--term T --rendering R --kind K --note N` for a glossary entry that wins.
5. A verse the critic calls a **source doubt** wants another edition, not another run.

It refuses a text withdrawn, set aside or in repair (exit 3). It stops at `--max-usd`, at the spend cap, and while
the dashboard changes the text's Sanskrit or English. A Hindi job does not stop it.

## A text held by the register (DOCS52_2026_10_14)

`translate_passages.py` refuses a whole-text run on a text withdrawn or set aside: "REFUSING (HOLD_2026_10_14)",
exit 4.
- One page (`--only-page`) is not held.
- To translate it anyway: `--allow-held`, or start the dashboard with `SA_ALLOW_HELD=1`.

The Library holds the buttons of a text whose path is repair the scan, a better source or retire. Chart again on
The path after a repair.

## MBh01's prose (DOCS52_2026_10_14)

1. Save the book's e-text by hand from the GRETIL or BORI page to `sources\\mbh_01_u.htm`. Mind BORI's terms: not to
   be passed on.
2. The dry run:

       python scripts\\import_mbh_gretil.py --book 1 --src sources\\mbh_01_u.htm --out data\\raw_mbh01_ce --dry-run

   It says how many prose lines it read, and "NOT READ" if a reference-like line was not.
3. The same without `--dry-run`.
4. The plan (free):

       python scripts\\reingest_pages.py --doc MBh01 --merged-dir data\\raw_mbh01_ce --no-segment

5. Its `--apply` line only when the verses stay and only the prose comes in.
"""

EP = """

## Addendum 2026-10-14 (42) (DOCS52_2026_10_14)

| # | Item | State |
|---|---|---|
| SC1 | A scholarly English (context, glossary, notes, critic, revisions, judge of both) | Built and tested (SCHOLAR_2026_10_14); the pilot is MBh01 1.1.0-1.1.23, about $1.23 |
| SC2 | A person's review and glossary | Built (`--review`, `--term`) |
| H1 | No paid translation where the scan or the source comes first | Built and tested (HOLD_2026_10_14) |
| MB1 | MBh01's lost prose | Importer fixed (MBH_PROSE_2026_10_14); the e-text is saved by a person, then the plan |
| YV1 | The Yoga Vasistha is a Hindi book with the Sanskrit in it | Withdraw it from the site; finish the OCR; separate the Sanskrit (vision), or find a Sanskrit edition |
| L1 | BORI's terms on the e-text and the site's MBh01 | A decision for the owner |
| S4 | Srangam: the scholarly English in the reader (C16; only rows passed and accepted by a person) | After the pilot is read |
| SC3 | A chapter-level pass for consistency (names, epithets, terms across a chapter) | After the pilot |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS51_2026_10_14"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS51_2026_10_14"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS51_2026_10_14")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs52_" + stamp))
        t = p.with_name(p.name + ".tmp_docs52"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
