#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs63_2026_10_16.py  DOCS63_2026_10_16

Records 16 Oct: the scholarly English in the Library and the reader (LIBRARY_SCHOLAR_2026_10_16); the footnote marks
and the measured price (READY_PRICE_2026_10_16); whether the two Agamas are done; the working English made from the
Karanagama edition's Hindi (H1); what our own rows say of the gain; the external benchmarks that exist (Mitrasamgraha
first) and the plan (BM1-BM4); the Indic question. docs/LIBRARY_SCHOLAR_2026-10-16.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 66), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 53), each needing DOCS62_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs63_<date>), line endings kept.

  python scripts/patch_docs63_2026_10_16.py --check
  python scripts/patch_docs63_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS63_2026_10_16"

PLATFORM = """

## 66. The scholarly English in the Library; the Agamas' remainder; the benchmarks (DOCS63_2026_10_16)

**16 Oct (IST).** docs/LIBRARY_SCHOLAR_2026-10-16.md has the details.
- **LIBRARY_SCHOLAR_2026_10_16 (dashboard.py):** a Library card carries "SC n" beside "EN n/N" and a line with its
  scholarly English (passed, flagged, source doubts; links verse by verse and as prose); the header counts the verses
  (2,460); the reader shows a verse's scholarly English above its working English, with its status and a link to its
  checks. Read-only; counted once in two minutes (0.6 s on the backup), a reader page about 0.01 s.
- **The two Agamas are done for their verse**, but for 17 verses of the Hayasirsa (15 held by the vision OCR's
  <sup>n</sup> footnote marks, 2 left) and 10 of the Karanagama: about $1.25. The rest not translated is the
  apparatus, the contents, the edition's Hindi, the scan's watermark, title pages and indexes.
- **READY_PRICE_2026_10_16:** scholar_translate's readiness does not take <sup>n</sup> for debris; redeem.py prices a
  passage of working English on the rows since 15 Oct ($0.00247 on flash; the Library's estimates were about 5 times
  low).
- **H1 (a finding):** of the Karanagama's 368 passages of working English, 159 were made from the edition's own Hindi
  (Prof. Pandey's): translate_passages.py has no guard for it. Finish EN would make some 490 more. Not to be pressed on
  the Karanagama until H1 is decided; a read-only SQL counts what the site has.
- **The gain, by our own rows:** the flash judge scores both Englishes alike (Karanagama, 168 verses: 4.70 against
  4.73); the blind pairwise judge with the context favours the scholarly English (23 to 5, 9 equal, on 37 verses). Not
  yet shown on an objective measure; it is measured before the credit goes to new texts.
- **What exists:** Mitrasamgraha (Jan 2026; 391,548 pairs; a post-corrected test set of 5,552; chrF, BLEURT and GEMBA
  for Google Translate, GPT-4o, Claude, Gemini, with and without retrieval) is the external benchmark; nothing public
  covers the Agamas, so a gold set of our own is made too.
- A correction to docs/TRIAGE_2026-10-16.md: a working-English call cost $0.00247 on 15 Oct (808 output tokens), not
  $0.0052.

**Tests:**
- `tests/test_library_scholar_2026_10_16.py` (6), `tests/test_ready_price_2026_10_16.py` (5);
- the replay chains of test_cost_truth_2026_10_15 (.bak_libsch_), test_triage_2026_10_16 and
  test_provisional_2026_10_14 (.bak_readyprice_) follow.
"""

RUNBOOK = """

## The scholarly English in the Library (DOCS63_2026_10_16)

- The Library's cards: "SC n" is the scholarly English (scholar_translations); "EN n/N" is the working English, the
  one the site shows. The reader shows both, the scholarly above. Read-only; restart the dashboard (when no job runs)
  after the patch.
- After READY_PRICE_2026_10_16: `python scripts\\redeem.py` (free) writes the Library's estimates at the measured price.
- Do not press Finish EN or Add Hindi on a bilingual edition (the Karanagama) until H1 is decided: the working English
  would translate the editor's Hindi.
"""

EP = """

## Addendum 2026-10-16 (53) (DOCS63_2026_10_16)

| # | Item | State |
|---|---|---|
| LS1 | The scholarly English in the Library and the reader (LIBRARY_SCHOLAR_2026_10_16) | Built and tested |
| RP1 | The footnote marks are not debris; the working English priced as measured (READY_PRICE_2026_10_16) | Built and tested |
| AG2b | The Agamas' remainder: 17 + 10 verses | After RP1 (the dry run says which) |
| H1 | The edition's own Hindi: a guard in translate_passages.py, a text_type, the site's copy | Found; a person decides |
| BM1 | External: 200 pairs of Mitrasamgraha's test set, three Englishes, chrF and a judge | After the dataset is seen |
| BM2 | Our gold set: 60 verses of the two Agamas, a person's reference | To start |
| BM3 | Blind, pairwise, with the context: 100 verses, scholarly against working | After BM2's sample is drawn |
| BM4 | The person's review of the triage CSVs (the KPI) | Ongoing |
| S4 | The scholarly English on the site, as a layer of its own | Design next |
| IN1 | Hindi from the scholarly English and the Sanskrit, on a Hindi gold set | After BM1-BM3 |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS62_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS62_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS62_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs63_" + stamp))
        t = p.with_name(p.name + ".tmp_docs63"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
