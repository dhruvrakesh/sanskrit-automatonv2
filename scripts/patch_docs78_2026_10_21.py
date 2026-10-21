#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs78_2026_10_21.py  DOCS78_2026_10_21

Records 21 Oct: the Surya Siddhanta's last Sonnet run (70 verses); its GRETIL e-text read wrongly (the visarga, the
avagraha, the labels, the sigla, GRETIL's English header) and mended (ETEXT_ORTHO_2026_10_21, WITNESS_MEND_2026_10_21);
its 18 verses of numbers no longer taken for an index (NUMERAL_VERSE_2026_10_21); the scholars' shelf, step 1
(SHELF_2026_10_21); docs/SHELF_AND_SURYA_2026-10-21.md.

Appends to docs/PLATFORM_2026-10-04.md (section 81), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 68)
and docs/STATE_2026-10-18.md (section 13), each needing DOCS77_2026_10_19; corrects docs/LEAK_GUARD_2026-10-19.md
(a Gemini run cannot have a Claude judge: scholar_translate.py refuses it, CLAUDE_FIRST_2026_10_15); adds data/shelf/
to .gitignore (the indexes stay on the PC). Marker-idempotent per file, all-or-nothing, backup first
(.bak_docs78_<date>), line endings kept.

  python scripts\\patch_docs78_2026_10_21.py --check
  python scripts\\patch_docs78_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS78_2026_10_21"

PLATFORM = """

## 81. The Surya's spelling mended; its verses of numbers; the scholars' shelf, step 1 (DOCS78_2026_10_21)

**21 Oct.** docs/SHELF_AND_SURYA_2026-10-21.md.
- **The last Sonnet run:** 70 verses of the Surya Siddhanta (pages 25 to 28): 63 passed, 7 flagged, $3.21. The Claude
  credit: $189.08 of $190 spent, $0.92 left (to 11 Nov).
- **ETEXT_ORTHO_2026_10_21:** the GRETIL e-text writes IAST with H for the visarga and +a for an a merged into the vowel
  before it; etext_witness.to_deva() lowered the text first, so 362 of the witness's 515 passages had h with a virama
  for the visarga, 101 kept "+", the pada labels and sigla became Devanagari consonants, and 11 lines of GRETIL's
  English header stood on page 1 as verses (the scholarly English had translated 7 of them). Read as meant now.
- **WITNESS_MEND_2026_10_21:** scripts/mend_witness.py reads an ingested witness again from its romanized lines: the
  ids stay; a verse's scholarly English gets a new version made from the new spelling (the same English); the header
  lines are kept in Latin letters as noise and their English is not carried over. The Markandeya's GRETIL witness:
  its 5,231 other passages read the same; 9 header lines.
- **NUMERAL_VERSE_2026_10_21:** in a typed edition the values in brackets after a verse's word-numerals are not an
  index: the Surya's 18 verses of numbers can be translated.
- **SHELF_2026_10_21:** scripts/scholar_shelf.py: the Vedic Index (3,834 entries), Soerensen's Mahabharata names
  (12,647) and Dikshitar's Purana Index (17,512), from Cologne (CC BY-NC-SA 3.0), in shelf_ tables tied to our names;
  on the PC only.
- **OPS_GUARD_TEST_2026_10_21:** tests/test_ops_guard.py had failed since SPEND_TRUTH_2026_10_04 (it took _gen's own
  calls for calls that bypass it); it now asserts what it means.

**Tests:** test_etext_ortho_2026_10_21 (5), test_numeral_verse_2026_10_21 (4), test_witness_mend_2026_10_21 (3),
test_scholar_shelf_2026_10_21 (4), test_docs78_2026_10_21 (3).
"""

RUNBOOK = """

## The Surya's spelling, its verses of numbers, the scholars' shelf (DOCS78_2026_10_21)

docs/SHELF_AND_SURYA_2026-10-21.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; each of `scripts\\patch_etext_ortho_2026_10_21.py`, `scripts\\patch_numeral_verse_2026_10_21.py`,
   `scripts\\patch_ops_guard_test_2026_10_21.py`, `scripts\\patch_docs78_2026_10_21.py` with `--check`, then without
   it; then `python -m unittest tests.test_ops_guard
   tests.test_etext_ortho_2026_10_21 tests.test_numeral_verse_2026_10_21 tests.test_witness_mend_2026_10_21
   tests.test_scholar_shelf_2026_10_21 tests.test_docs78_2026_10_21 tests.test_etext_page_2026_10_18
   tests.test_scholar_ref_2026_10_18 tests.test_etext_witness_2026_10_11`.
2. `python scripts\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext` (the plan), then `--yes` (a backup first);
   the same for `markandeya_purana__w_gretil`. Both are released, so the scheduled mirror sends the mended text (do
   not --hold a released text to mend it: the site would keep the misspelt version until it is released again).
3. The shelf: download the three txt zips (the doc's section 2), `python scripts\\scholar_shelf.py` (the plan), `--yes`,
   `--show Janaka`.
4. Release with COMMIT_MSG_orthoshelf_20261021.txt.
"""

EP = """

## Addendum 2026-10-21 (68) (DOCS78_2026_10_21)

| # | Item | State |
|---|---|---|
| S2 | The Surya Siddhanta's scholarly English | 485 of its 503 verses (394 passed, 90 flagged, 1 doubted); 18 verses of numbers left (yours: Gemini 2.5 Pro, about $0.30 of Google's cap, or Sonnet with new credit) |
| S3 | The Surya's e-text read wrongly (visarga, avagraha, header) | Fixed: ETEXT_ORTHO_2026_10_21; mended in place by mend_witness.py (WITNESS_MEND_2026_10_21) |
| H1 | The scholars' shelf, step 1: three indexes of names | Built: SHELF_2026_10_21; on the PC only |
| H2 | The shelf on the site | Yours: CC BY-NC-SA 3.0 (non-commercial, the credit as given, the same licence for what is derived) |
| H3 | Raychaudhuri's Political History (1923) as claims, page by page | Next: public domain in India; about $1 on Gemini Flash |
"""

STATE = """

## 13. 21 Oct: the Surya's spelling mended; the scholars' shelf (DOCS78_2026_10_21)

- **The Surya Siddhanta:** 70 more verses on Sonnet (63 passed, 7 flagged, $3.21); the Claude credit $0.92 left. Its
  GRETIL e-text had been read wrongly (the visarga as h with a virama in 362 of 515 passages; +a kept; the labels and
  sigla made Devanagari; 11 lines of GRETIL's English header read as verses, 7 of them given a scholarly English).
  Fixed in etext_witness.py and mended in place by mend_witness.py: 503 verses, 485 with their scholarly English kept
  (a new version from the new spelling), 18 verses of numbers now ready.
- **On the site before the mend:** the e-text was released on 21 Oct at 16:03 IST and the 16:31 mirror run sent it
  (515 passages, 915 scholarly rows) with the misspelt Sanskrit; the mend changes it in place, and the next mirror run
  sends the corrected text (the 7 header rows retire there).
- **The scholars' shelf, step 1:** the Vedic Index, Soerensen's Mahabharata names and Dikshitar's Purana Index, tied to
  our names (scholar_shelf.py), on the PC only.
- **Our Satapatha is book 14 only** (the Brihadaranyaka with a commentary): the passages on Janamejaya's horse sacrifice
  (book 13) and on Janaka's other dialogues (book 11) are not in the corpus; GRETIL has books 1 to 11 and 13 to 14.
"""

LEAK_EDITS = [
    ("""Gemini 2.5 Pro (judged by Claude Haiku, so that no family judges its own). The Ganita's scholarly English (about 1,800
""", """Gemini 2.5 Pro (judged by Gemini Flash: scholar_translate.py refuses a Claude judge for a Gemini run, CLAUDE_FIRST_2026_10_15;
corrected on 21 Oct, DOCS78_2026_10_21). The Ganita's scholarly English (about 1,800
"""),
    ("""1. The Surya's last 88 verses: Gemini 2.5 Pro with a Claude Haiku judge now (about $1.45 Google), or Sonnet when there
   is credit again (about $4.45).
""", """1. The Surya's last 88 verses: Gemini 2.5 Pro with the Gemini Flash judge now (about $1.45 Google), or Sonnet when there
   is credit again (about $4.45). (21 Oct, DOCS78_2026_10_21: a Claude judge for a Gemini run is refused by
   scholar_translate.py; 70 of them were done on Sonnet that day, docs/SHELF_AND_SURYA_2026-10-21.md.)
"""),
]

GITIGNORE = """
# DOCS78_2026_10_21: the scholars' shelf's indexes (Cologne, CC BY-NC-SA 3.0) stay on the PC
data/shelf/
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS77_2026_10_19"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS77_2026_10_19"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS77_2026_10_19"),
           (Path("docs/STATE_2026-10-18.md"), STATE, "DOCS77_2026_10_19")]
LEAK = Path("docs/LEAK_GUARD_2026-10-19.md")
IGNORE = Path(".gitignore")


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


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
        nl = nl_of(raw)
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if not LEAK.exists() or not IGNORE.exists():
        print("FAIL: %s or %s not found. Run from the repo root." % (LEAK, IGNORE)); return 2
    raw = LEAK.read_bytes()
    if MARK.encode() in raw:
        print("skip %s (already carries %s)" % (LEAK, MARK))
    else:
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if "LEAK_GUARD_2026_10_19" not in src:
            print("REFUSE: %s does not carry LEAK_GUARD_2026_10_19. Nothing written." % LEAK); return 1
        for k, (old, new) in enumerate(LEAK_EDITS, 1):
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (LEAK, k, src.count(old))); return 1
            src = src.replace(old, new, 1)
        todo.append((LEAK, src.replace("\n", nl).encode("utf-8")))
    raw = IGNORE.read_bytes()
    if MARK.encode() in raw:
        print("skip %s (already carries %s)" % (IGNORE, MARK))
    else:
        nl = nl_of(raw)
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((IGNORE, raw + sep + GITIGNORE.lstrip("\n").replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs78_" + stamp))
        t = p.with_name(p.name + ".tmp_docs78"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
