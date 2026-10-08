#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs25_2026_10_08.py  DOCS25_2026_10_08

Records the checks of 2026-10-08 evening (C5 grants, mirror size, cron job 9), the search-corpus
deploy failure and its cure, and the navigation and layout of the two readers
(READER_NAV_2026_10_08, docs/cloud/C5b). Appends to docs/PLATFORM_2026-10-04.md (section 28),
RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 15) and docs/CORPUS_MIRROR_2026-10-08.md.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs25_2026_10_08.py --check
  python scripts/patch_docs25_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS25_2026_10_08"

PLATFORM = """

## 28. Checks of the evening; a deploy that could not see a folder; reading the texts (DOCS25_2026_10_08)

**Applied and confirmed.**
- **Srangam.** The sign-in fix (AUTH_ROLE_2026_10_08) is Srangam commit 4ffb5cbf, on origin/main.
- **Automaton.** The hidden dashboard launcher and docs24 are automaton a0e4515a.
  - The launcher takes effect at the next idle restart. At the time of writing `D:\\backups\\dashboard_logs` did not exist yet, so the dashboard still ran the old way.
- **C5 R1.** On all six reader functions, anon false and authenticated true.
- **M3.** Mirror 360 MB; database 453 MB.
  - Counts: docs 63, passages 75,734, English 21,915, Hindi 13,522, entities 8,269, mentions 32,861, vectors 21,931, stories 44.
- **Cron job 9.** Run 38688 at 04:15 UTC on 2026-10-08: succeeded.

**search-corpus did not deploy.**
- **What failed.** Lovable reported "deploy failed on a cross-folder import". The function imported its embedding helpers from `../search-texts/lib.ts`, and a deploy packages only the function's own folder and `_shared/`.
- **The cure.**
  - `supabase/functions/search-corpus/embed.ts` is a verbatim copy of those helpers: same model, size, task type, limits and normalisation.
  - `index.ts` imports `./embed.ts` instead.
  - `src/__tests__/search-corpus-embed.test.ts` fails if the copy drifts, or if the function imports from another folder.
  - search-texts is not touched.

**Reading the texts (READER_NAV_2026_10_08).**
- **Shared pieces.** `/texts/:docCode` and `/corpus/:docCode` now share a passage block, a reading bar and a contents panel.
- **Navigation.**
  - **The bar.** It stays under the site header from tablet width up, with Previous, Next, any page from a list, and the arrow keys.
  - **Contents.** Every page with its scan-page range, the colophons (chapter ends), and "go to a scan page".
  - **Find in this text.** By words or by meaning in the corpus, and by meaning for published texts.
- **Layout.**
  - **Wide screens.** Sanskrit and IAST on the left, English and Hindi on the right (the "source + translation" layout of the Booksmith editions and the HTML exports). Stacked on phones.
  - **Reference.** In the margin: scan page.passage, with the edition's number under it.
  - **Toggles.** IAST, English, Hindi, side by side and scanner noise, remembered in the browser.
- **Honest marks.**
  - A line with Latin letters and no Devanagari letter, inside a Devanagari passage, is shown muted as misread ("ay Trae:" in nirukta 1.1).
  - Passages typed noise are folded.
  - Tooltips and a small popover per passage carry the OCR confidence, the engine and date, and the automatic check.
  - Nothing stored changes.
- **Speed.** The next page is fetched ahead; the contents are read only when opened.
- **Why no chapter list.** corpus.passages.chapter mostly holds the division word without its number (nirukta: 5 distinct values on 179 of 2,095 passages). The contents use scan pages and colophons instead.
- **Database.** `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql` adds one gated function, `corpus_reader_outline()`. On 21,128 passages it took 30 ms.
- **Tested.**
  - 5 PostgreSQL tests (`tests/test_corpus_reader_nav_pg_2026_10_08.py`).
  - 15 new vitest tests. The existing reader tests pass unchanged; the full suite is 151 passed, apart from the one sandbox-only meta-freshness check.
  - Typecheck is clean. The build's entry chunk is 487.2 kB (unchanged); the reader pages are lazy (CorpusDoc 11.1 kB, TextReader 8.3 kB).
- **Delivery.**
  - The Srangam files travel in this repository under `docs/srangam/READER_NAV_2026-10-08/`.
  - `scripts/patch_reader_nav_2026_10_08.py` copies them in. It writes over only the exact versions they were made from (md5), and only after checking everything.
"""

RUNBOOK = """

## Reading the texts: apply READER_NAV; search-corpus deploy (DOCS25_2026_10_08)

1. **Lovable Cloud SQL editor.** Paste `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql`, then run N1: anon false, authenticated true.
2. **Srangam, in `D:\\srangam-42267` on main.**
   - Run `git pull --ff-only origin main`.
   - Run `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_reader_nav_2026_10_08.py" --check`, then the same without `--check`.
   - Run `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Add the 16 paths it names, commit, and push main yourself.
3. **Lovable.** Deploy `search-corpus` (it now imports only from its own folder), then Publish.
4. **Check.**
   - Open `/corpus/nirukta` and choose Contents: pages with scan ranges.
   - Go to scan page 18.
   - Find "earth" by words, then by meaning.
   - Read `/texts/markandeya_purana` with "Side by side" on a wide screen.
- **If Contents says "not available yet".** C5b is not applied. The pages are still listed.
- **If find by meaning says "not switched on yet".** search-corpus is not deployed.
"""

EP = """

## Addendum 2026-10-08 (15) (DOCS25_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Sign-in loop | Applied: Srangam 4ffb5cbf |
| D3 | Runs die with the console | Released (a0e4515a); in effect at the next idle restart of the dashboard |
| C2 | Cron job 9 | Ran 2026-10-08 04:15 UTC, succeeded |
| C5 | Reader functions | R1 confirmed; search-corpus failed to deploy (cross-folder import). Fixed in code (embed.ts). To apply: the Srangam patch, push, deploy |
| R1 | Navigation and layout of the readers | Built (READER_NAV_2026_10_08, C5b). To apply: C5b SQL, the Srangam patch, push, Publish |
| R2 | Next for the readers | Hindi on the published reader (W6), entity tooltips from mentions, and a chapter list once the chapter field carries numbers |
"""

MIRROR = """

## Contents for the corpus reader (C5b, DOCS25_2026_10_08)

- **What it is.** `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql` adds `corpus_reader_outline(p_doc, p_per_page)`. It has the same gate as the C5 functions, and only signed-in callers may execute it.
- **What it returns.**
  - One 'page' row per 50 passages: the first passage and the last scan page reached.
  - One 'colophon' row per passage typed colophon, with 160 characters of its English (or its Sanskrit).
- **Used by.** The Contents panel and "go to a scan page" on `/corpus/:docCode`. It is read only when the panel opens.
- **Speed.** 30 ms on 21,128 passages.
- **Rollback.** `DROP FUNCTION public.corpus_reader_outline(text, integer);`
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs25_" + stamp))
        t = p.with_name(p.name + ".tmp_docs25"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
