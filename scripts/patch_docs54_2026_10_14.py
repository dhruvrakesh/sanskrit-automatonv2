#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs54_2026_10_14.py  DOCS54_2026_10_14

Records the late night of 14 Oct: scholar-v2's pilot (15 passed, 5 flagged, 4 failed, $0.256) and why;
SCHOLAR_V21_2026_10_14 (a sentence's passage kept as written; a failed sentence verse by verse; an answer cut off
asked again; the rows ordered by their passage's place; the importer's appendix count); READER_SOURCES_2026_10_14
(Srangam S2: C17, public.corpus_reader_sources, and the reader naming the reading); MBh01's prose plan; the Hindi
sample; what the judge marks in the Shatapatha. docs/SCHOLAR_V21_2026-10-14.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 57), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 44), each needing DOCS53_2026_10_14.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs54_<date>), line endings kept.

  python scripts/patch_docs54_2026_10_14.py --check
  python scripts/patch_docs54_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS54_2026_10_14"

PLATFORM = """

## 57. The scholarly English 2.1; the reading named on the site (DOCS54_2026_10_14)

**14 Oct (IST), the late night.** docs/SCHOLAR_V21_2026-10-14.md has the details.
- **scholar-v2 on MBh01 1.1.0-1.1.24 (21:13, $0.256):** 15 passed, 5 flagged (1.1.15-1.1.19, one sentence), 4 failed
  (1.1.20-1.1.23, one sentence). Three sentences over verses passed whole. The second judge preferred the scholarly
  English 13 times in 20, the working one twice (a minor ambiguity). Read whole, the working English of
  1.1.15-1.1.19 scores fidelity 2.
- **Why the flags and the failures:** v2 replaced a sentence's passage with its segments joined (the Sanskrit's
  order), so 1.1.15-1.1.19 read as fragments; a reply cut off at the token limit was asked again only when it was
  empty, and how it ended was not logged.
- **SCHOLAR_V21_2026_10_14 (scholar-v2.1):**
  - the passage is kept as the draft wrote it, in English order; the segments say which words render which verse;
  - an answer cut off and not JSON is asked again with room; a draft still not JSON once more; a failure says how
    it ended; a failed sentence goes verse by verse;
  - priced by scholar-v2's rows until it has its own; the pages order rows by their passage's place now and show
    such a passage whole after its verse range;
  - the importer counts the e-text's appendix passages (5,028 '@' lines in book 1) as excluded, not "NOT READ".
- **MBh01's prose:** the e-text read, 7,197 passages; the plan changes 4 pages (241 in, 1 out: 1.3.1's speaker line,
  replaced by its whole prose).
- **READER_SOURCES_2026_10_14 (Srangam S2):** C17 adds public.corpus_reader_sources (read-only, signed-in readers);
  the reader names where a passage's Sanskrit comes from. An e-text is never "OCR" or a hard-to-read scan; a passage
  without a recorded engine is as before.
- **The Hindi sample:** 8 verses; 1.1.11 at fidelity 1 (subject and speaker inverted).
- **The judge's marks:** in the Shatapatha two of three are the scan's misreading (tan na read tatra), not the English.
- **The translate lock:** one translate job at a time; queue small texts before a long one.

**Tests:**
- `tests/test_scholar_v21_2026_10_14.py` (14);
- `tests/test_reader_sources_pg_2026_10_14.py` (2, with CORPUS_TEST_DSN);
- Srangam `src/__tests__/reader-sources.test.tsx` (8).
"""

RUNBOOK = """

## The scholarly English 2.1 (DOCS54_2026_10_14)

1. A sentence flagged or failed under scholar-v2 is made again with v2.1, the dry run first (free):

       python scripts\\scholar_translate.py --doc MBh01 --pages 1 --from-ref 1.1.15 --limit 9 --redo

2. Its `NEXT:` line runs it (capped).
3. A failure now says how the answer ended ("it ended MAX_TOKENS, ..."); a sentence that fails is translated verse by
   verse, and the summary counts it ("split").
4. The pages show a v2.1 sentence whole after its range (1.1.15-19); "Verse by verse" opens its segments.

## The reading on the site (DOCS54_2026_10_14)

1. In the Lovable Cloud SQL editor: docs/cloud/C17_checks_2026-10-14.sql E1 and P1, then
   docs/cloud/C17_reader_sources_2026-10-14.sql in one paste, then V1 and V2.
2. Srangam's reader then names each page's reading. Before C17 it shows what it showed before.
3. Rollback: `DROP FUNCTION IF EXISTS public.corpus_reader_sources(text);`

## Queueing translations (DOCS54_2026_10_14)

The dashboard runs one translate job at a time. Queue the small texts first and a long one (MBh01's Hindi, about 13
hours) last, or the small ones wait behind it.
"""

EP = """

## Addendum 2026-10-14 (44) (DOCS54_2026_10_14)

| # | Item | State |
|---|---|---|
| SC3 | Sentences over verses; a second judge | Run (scholar-v2): 15 passed, 5 flagged, 4 failed; the flags and failures mended in SCHOLAR_V21 |
| SC6 | A failed sentence verse by verse; how an answer ended | Built and tested (SCHOLAR_V21_2026_10_14) |
| MB1 | MBh01's lost prose | The e-text read (7,197 passages); the plan: 241 in, 1 out; apply when no writer runs |
| S2 | Srangam: name the reading | Built and tested (READER_SOURCES_2026_10_14, C17); C17 to paste, Srangam to push |
| HI2 | A Debroy-grade Hindi, from the accepted scholarly English | Not built; after a chapter's English is accepted |
| JR1 | The judge's marks that are the scan's misreading (Shatapatha) | Read the Sanskrit first: an e-text witness or a scan repair |
| Q1 | The translate lock: small texts behind a 13-hour job | Queue small texts first; a priority for short jobs is a later change |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS53_2026_10_14"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS53_2026_10_14"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS53_2026_10_14")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs54_" + stamp))
        t = p.with_name(p.name + ".tmp_docs54"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
