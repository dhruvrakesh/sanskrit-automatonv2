#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs64_2026_10_16.py  DOCS64_2026_10_16

Records 16 Oct (afternoon): an edition's own Hindi kept out of the translation at the classification stage
(CLASSIFY_HINDI_2026_10_16), the serious flags read, the thinking probe's result, and what Mitrasamgraha is made of.
docs/CLASSIFY_HINDI_2026-10-16.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 67), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 54), each needing DOCS63_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs64_<date>), line endings kept.

  python scripts/patch_docs64_2026_10_16.py --check
  python scripts/patch_docs64_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS64_2026_10_16"

PLATFORM = """

## 67. An edition's own Hindi, kept out of the translation; the serious flags; the benchmark's make-up (DOCS64_2026_10_16)

**16 Oct (IST).** docs/CLASSIFY_HINDI_2026-10-16.md has the details.
- **The gap:** classify_doc.py (the stage after every ingest) promised to sort "English/Hindi body text and front
  matter" from the Sanskrit; classify_frontmatter.py reads Latin letters only, so an edition's Hindi in Devanagari
  stayed 'mula' and was translated. The Karanagama: 815 passages of its editor's Hindi; 194 with working English and
  99 with scholarly English made from them (89 passed by the flash judge); the site's copy 291 English rows on them.
- **CLASSIFY_HINDI_2026_10_16:** scripts/edition_hindi.py reads a passage's words; scripts/classify_hindi.py tags
  such passages 'frontmatter' (by default only what carries no English; --with-english archives and clears English
  made from the Hindi, with its search row and vector; --reject-scholarly --by; logged; --undo); classify_doc.py runs
  it as a stage; scholar_translate and the dashboard set such rows aside; Srangam's corpus reader folds them.
- **The serious flags, read:** most are corrupt readings the translator emended and said so (the Hayasirsa 66 of 85,
  the Karanagama 35 of 62); the Karanagama also has the editor's footnotes (8), Hindi (7), mantras kept in IAST (3).
  Another model would re-emend them: the Opus pass waits for CLASSIFY_HINDI, a judge told the emendations, and a
  person.
- **The thinking probe (TB1):** the judge without gemini-2.5-flash's thinking costs 4% of it with it; fidelity the
  same in 9 of 12, within one in 11; pass or flag the same in 11. google-generativeai 0.8.5 cannot set it (the REST
  call can). A 60-verse probe before any change.
- **Mitrasamgraha:** 50 texts, 393,189 pairs, 11% Buddhist; its test set 8 files of the Hindu tradition (4,000
  pairs), the Gita (a sectarian Vaishnava reference), 3 Buddhist files (1,332); IAST with its words split. BM1, if
  run, takes the 8 files only, judged on the Sanskrit; BM2 (our gold set) decides.

**Tests:** `tests/test_classify_hindi_2026_10_16.py` (8); test_library_scholar_2026_10_16 and
test_ready_price_2026_10_16 follow (.bak_hindi_). Srangam: src/__tests__/reader-frontmatter.test.tsx (2).
"""

RUNBOOK = """

## An edition's own Hindi (DOCS64_2026_10_16)

1. `python scripts\\classify_hindi.py --show 3` (free): every text, what reads as Hindi, and what carries English.
2. A text whose Hindi carries no English: `python scripts\\classify_hindi.py --doc <code> --apply`.
3. A text whose Hindi was translated: back up first, then `--with-english --reject-scholarly --by <name> --apply`.
4. `--undo --apply` puts back what the log says; `python scripts\\build_embeddings.py --doc <code>` remakes the
   vectors of English put back.
5. New texts: classify_doc.py runs it after every ingest (only what carries no English).
"""

EP = """

## Addendum 2026-10-16 (54) (DOCS64_2026_10_16)

| # | Item | State |
|---|---|---|
| H1 | An edition's own Hindi kept out of the translation (CLASSIFY_HINDI_2026_10_16) | Built and tested; to apply per text |
| H1b | The Karanagama on the site (291 English rows on its Hindi) | Withdraw now, or replace at its release: a person decides |
| SH1 | A scholarly Hindi from the Sanskrit (with the passed scholarly English as a reference) | After BM; a 20-verse canary first |
| J2 | A judge told the translator's emendations, with the thinking off | Proposed; a 60-verse probe first |
| A2 | The editor's footnotes cut as verses (the Karanagama's Vedic sources) | To tag, as classify_apparatus.py does |
| OP1 | Opus on the serious flags | Waits for H1, J2 and a person |
| BM1 | Mitrasamgraha: the 8 files of the Hindu tradition only, judged on the Sanskrit | After a go |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS63_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS63_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS63_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs64_" + stamp))
        t = p.with_name(p.name + ".tmp_docs64"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
