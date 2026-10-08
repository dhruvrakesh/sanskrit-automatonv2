#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs26_2026_10_08.py  DOCS26_2026_10_08

Records the evening's applied work (C5b, READER_NAV, search-corpus deployed) and the library over
the working corpus (CORPUS_LIBRARY_C6_2026_10_08: docs/cloud/C6, the Srangam patch, the shelf
emitter), with a parity map of the desk's local app against the site and the next phases.
Appends to docs/PLATFORM_2026-10-04.md (section 29), RUNBOOK.md,
docs/ENTERPRISE_PATH_2026-10-04.md (addendum 16) and docs/CORPUS_MIRROR_2026-10-08.md.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs26_2026_10_08.py --check
  python scripts/patch_docs26_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS26_2026_10_08"

PLATFORM = """

## 29. The desk's library on the site (DOCS26_2026_10_08)

**Applied the same evening.**
- **C5b.** Applied; N1 showed anon false and authenticated true.
- **Releases.** Automaton 6669f377 (READER_NAV payload, docs25). Srangam 4b853181 (the two readers' navigation and layout, search-corpus with its own embed.ts).
- **search-corpus.** Lovable deployed it this time. An unsigned call was refused with 401, as designed.
- **The 10 withheld verses.** srangam_text_passages still 1,655: the six --only files are not pasted yet.
- **Security scan.** Lovable's scan lists the open `spatial_ref_sys` table of the mapping add-on (PostGIS) as critical. It was already recorded as an accepted risk and did not block publishing.

**Which app.**
- **The calibre-like app.** The desk's own library is the dashboard at 127.0.0.1:5057 (Flask): Shelf (`library_web.py`, `configs/collections.json`), Stories (`stories_web.py`), Images, the scholarly reader, Ask, QA and Usage.
- **The Streamlit app.** The only Streamlit app on the PC is Panchang/Jyotish (`D:\\panchang\\app.py`, port 8501). Srangam's `/jyotish-horoscope` is a page about it, not a port.

**What C6 brings (CORPUS_LIBRARY_C6_2026_10_08).**
- **The functions.** `docs/cloud/C6_corpus_library_2026-10-08.sql`: five gated, signed-in-only functions and one index (mentions by name):
  - `corpus_reader_progress` (each text's 13 pipeline stages with the desk's reasons);
  - `corpus_reader_stories` (approved for readers; drafts and candidates also for admins; never retired or rejected);
  - `corpus_reader_names`, `corpus_reader_name` (the names index, and every passage that names one);
  - `corpus_reader_page_names` (the names of one reader page).
- **Tested.** 7 PostgreSQL tests. On 8,000 names and 32,000 mentions: 27 ms, 21 ms and 4 ms.

**What the site gains.**
- **`/corpus` is the Shelf.**
  - Every text on the desk's shelves, with its title: confirmed, or derived from the code and marked so.
  - Its series, English and Hindi coverage, 13 stage dots with the desk's reasons, and its stories.
  - A filter that ignores diacritics, four sorts, and "with stories" and "published".
- **`/corpus/stories`.** The stories, and one story with its Sanskrit line, English and Hindi, its citations as links and its check.
- **`/corpus/names`.** The names index, by kind, and one name with every passage that names it.
- **The corpus reader.** Name chips per passage, each a card with a link to the name's page, and `?at=<page>.<passage>` links.
- **Shelf data.** The shelves reach the site as `src/data/corpusShelf.json`, written by `scripts/emit_corpus_shelf.py` from `configs/collections.json`. They are configuration, so they do not travel through the mirror.
- **Tested.** 12 vitest tests. The full suite is 163 passed, apart from the one sandbox-only check. The entry chunk is 487.8 kB (+0.6 kB); the new pages are lazy.

**Parity: the desk's app and the site.**

| Desk (local) | Site (signed in) | State |
|---|---|---|
| Shelf: shelves, titles, series, coverage, stages | /corpus | L1 (this) |
| Scholarly reader: three columns, OCR variants, kinds, quality | /corpus/:doc | READER_NAV + L1. OCR variants not mirrored (L2) |
| Stories: read, approve, edit, variants, novels | /corpus/stories (read) | L1 read-only; editing stays on the desk (L4) |
| Names, entity mentions | /corpus/names, name chips | L1 |
| Search: words, meaning | /corpus, find in this text | done |
| Images, covers | none | L2 (Storage bucket, uploaded by the mirror run) |
| Exports: HTML, PDF, Booksmith editions | none | L2 (Storage) |
| Ask (answers with citations) | none | L3 (C3b) |
| QA, Usage, budget, jobs | none | stay local (operator tools) |
"""

RUNBOOK = """

## The library on the site: apply C6 and the Srangam patch (DOCS26_2026_10_08)

1. **Lovable Cloud SQL editor.** Paste `docs/cloud/C6_corpus_library_2026-10-08.sql`. Then run L1 at its end: anon false and authenticated true on all five functions.
2. **Srangam, in `D:\\srangam-42267` on main.**
   - Run `git pull --ff-only origin main`.
   - Run `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_library_l1_2026_10_08.py" --check`, then the same without `--check`.
   - Run `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Add the 15 paths it names, commit, push, then Publish in Lovable. There is no edge function in this one.
3. **When the shelves change** (the Shelf page's "move to", or an edit of collections.json):
   - Run `python scripts\\emit_corpus_shelf.py --srangam D:\\srangam-42267 --check`.
   - If it says STALE, run it without `--check`, then commit `src/data/corpusShelf.json` in Srangam.
4. **Stories appear on the site** when they are approved on the desk. Use `python scripts\\stories.py approve --id N`, or the Stories page; the next mirror run carries the approval. Editors (admins) see drafts on the site, marked as drafts.
"""

EP = """

## Addendum 2026-10-08 (16) (DOCS26_2026_10_08)

| # | Item | State |
|---|---|---|
| C5b | Contents for the reader | Applied (N1 confirmed) |
| R1 | Reader navigation and layout | Applied: Srangam 4b853181; search-corpus deployed (anon 401 as designed) |
| L1 | The desk's library on the site (Shelf, Stories, Names, name chips, ?at=) | Built (C6, CORPUS_LIBRARY_C6_2026_10_08). To apply: C6 SQL, the Srangam patch, push, Publish |
| L2 | Covers, images and editions (HTML, PDF, Booksmith) on the site | Next: a private Storage bucket filled by the mirror run, read through signed URLs |
| L3 | Ask over the corpus (C3b) | Next: answers with citations over corpus_reader_match |
| L4 | Editor actions from the site (approve, titles, shelves) | Design: a request queue the desk pulls and applies; the desk stays the source of truth |
| P1 | Panchang/Jyotish (Streamlit) | A separate app; /jyotish-horoscope describes it. Compare before porting anything |
| V10 | The 10 withheld verses | Still 1,655 on 2026-10-08 evening: paste the six --only files |
"""

MIRROR = """

## The library (C6, DOCS26_2026_10_08)

- **What it adds.** `docs/cloud/C6_corpus_library_2026-10-08.sql` adds five gated, signed-in-only functions over the mirror tables that were already here:
  - corpus.stages: `corpus_reader_progress`;
  - corpus.stories: `corpus_reader_stories`;
  - corpus.entities and corpus.mentions: `corpus_reader_names`, `corpus_reader_name` and `corpus_reader_page_names`.
  - It also adds one index, `corpus_mentions_canonical`.
- **No change to the mirror run.** The mirror run itself is unchanged: no new table, no new row hash, nothing re-sent.
- **Stories.** Readers see status 'approved'. Admins also see 'draft' and 'candidate'. Retired and rejected stories are never returned.
- **Shelves.** These are configuration, not corpus data, so they reach the site as a generated file (`scripts/emit_corpus_shelf.py`).
- **Rollback.** At the head of the C6 file.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP), (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR)]


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
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs26_" + stamp))
        t = p.with_name(p.name + ".tmp_docs26"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
