#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs17_2026_10_07.py  DOCS17_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 20), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: what is live on Srangam and in every repo at 17:10 on
2026-10-07, the first production run of C2, and C3a (search the texts by meaning).
Marker-idempotent per file, backup first.

  python scripts/patch_docs17_2026_10_07.py --check
  python scripts/patch_docs17_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS17_2026_10_07"

PLATFORM = """

## 20. What is live (17:10, 2026-10-07); C2 in production; C3a, search by meaning (SEARCH_TEXTS_C3A - DOCS17_2026_10_07)

**The site, checked in a browser:**
- **/sanskrit-translator status panel.** "Corpus figures measured on 2026-10-07": 66 works, 75,734 passages, 21,673 English, 12,502 Hindi and 21,689 embedded. Under "Not yet true": "Only 2 of the 66 works in the corpus can be read on this site so far (1,655 passages at /texts ...)". This is SITE_LINE, live after the Publish.
- **/texts.** Both texts show "translated with gemini:gemini-2.5-flash", and the second reads "Markandeya Purana" in IAST (S4 M2, M3).
- **/research-network.** 1,392 connections. The article title no longer ends in ".docx (1)" (S4 M5).
- **Cron after the S3 revoke.** The watchdog succeeded at every 5-minute run from 10:45 to 11:10 UTC (S4 M6), so the lockdown broke nothing.

**The repos, from their .git files (no git command run): every local branch equals its origin.**
- **sanskrit-automatonv2:** main 9f12415f.
- **srangam-42267:** main 596aaf80, which is "Redeployed all 30 edge functions" by gpt-engineer-app[bot] on top of ee13e94 (C2) and 220eeea (status panel).
  - The working copy also shows bun.lock modified (same size, not committed); nothing of ours touches it.
- **Unchanged since 2026-09:** srangam-hub (bd85c23b, 09-27), nartiang-booksmith (60dcffb8, 09-27), sanskrit-symphony (85c76d9d, 09-30), panchang, wisdomlib, nartiang-legacy-web and remix-of-dkegl-website.

**C2 in production.**
- **First dry run (request 371, 11:19 UTC).** It answered 404 "Requested function was not found": it ran before the function was deployed.
- **After the redeploy.** The first real call (request 372) stored 500 vectors: one model, 1536 dimensions. 1,155 remain, which is three more R3 calls.

**C3a - search the published texts by meaning** (`docs/cloud/C3_search-texts/`; `scripts/patch_texts_search_2026_10_07.py` installs it in the Srangam repo).
- **Edge function `search-texts`** (public).
  - **Request.** A question of 3-300 characters is embedded as RETRIEVAL_QUERY with gemini-embedding-001 at 1536 dimensions.
  - **Matching.** match_text_passages runs with the anon key, so RLS shows published texts only. k is at most 20.
  - **Brakes.** 20 searches a minute per client per instance, plus a small cache of repeated questions.
  - **Results.** Each hit carries its title, reference, translation, similarity, and its position in the text in the reader's order. Nothing is generated.
  - **Cost.** About $0.000003 a question.
  - 7 Deno tests; type-checks against supabase-js 2.58.0.
- **/texts.**
  - A "Search the texts by meaning" card above the list. It is shown only when the texts load.
  - Results show the title, `p60.10`-style reference and translation (420 characters at most), and "Read it in the text", which links to `/texts/<doc>?p=<page>#p<page_no>-<idx>`.
  - Failure is never shown as "nothing found": the corpusSearch.ts contract is the same as corpusTexts.ts.
- **/texts/:docCode.**
  - Once the passages arrive, it scrolls to the linked passage and marks it. The browser looks for the anchor before the passages exist, and :target never applies to an element added later.
  - An in-page anchor click still marks the passage via :target.
- **Checked on a copy of the Srangam source in the sandbox (npm ci, 894 packages).**
  - **Typecheck.** `tsc -p tsconfig.app.json` reports no new error. Its one error is from the snapshot, which left out supabase/functions.
  - **Tests.** corpus-search (6 new), corpus-texts-loader and query-bounds: 18 of 18 pass.
  - **Build.** `vite build` succeeds.
  - **In a browser, with the Supabase endpoints mocked:**
    - the search posts {q, k: 10} and renders two hits, linking to `?p=21#p60-10` and `?p=18#p50-3`;
    - a reader opened at `?p=21#p60-10` shows "Page 21 of 25", scrolls the passage to 96 px from the top (scroll-mt-24) and marks it.
  - **No page errors.**
- **Load-time note** (measured on that build). The entry chunk is 505 kB minified (177 kB gzip). MapboxBujangNetwork is 1.6 MB and MapsData 0.99 MB, both lazy. The search adds a few kB to the /texts chunk only.
"""

RUNBOOK = """

## Finish C2; install search by meaning (C3a) (DOCS17_2026_10_07)

- **C2.** Run `docs\\cloud\\C2_run_and_schedule_2026-10-07.sql` R3, then R2, three more times, until R4 shows 1,655 vectors. Then run R5, and R6 if you want it nightly.
- **C3a**, in `D:\\srangam-42267` on main:
  1. `git pull --ff-only origin main`.
  2. `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_texts_search_2026_10_07.py" --check`, then the same without `--check`.
  3. `npm run typecheck`.
  4. `npx vitest run src/__tests__/corpus-search.test.ts src/__tests__/corpus-texts-loader.test.ts src/__tests__/query-bounds.test.ts`.
  5. `npm run build`.
  6. Commit the 8 paths, push main yourself, then ask Lovable to deploy the edge functions and Publish.
  7. Open /texts and search, for example "why did the king sell his wife and son".
- **The patch refuses** if any of its files already exists with other content, or if an anchor moved. Nothing is written in either case.
"""

EP = """

## Addendum 2026-10-07 (7): live state and search (DOCS17_2026_10_07)

| # | Item | State |
|---|---|---|
| S3 | Function lockdown | Done and confirmed: cron ran at every 5-minute run after the revoke |
| W1 | Status panel | Live, measured 2026-10-07 |
| W3 / W7 | Article title; Markandeya label and IAST title | Done |
| C2 | embed-published-passages | Deployed (Lovable redeploy 596aaf80); 500 of 1,655 vectors stored; three more R3 calls |
| C3a | Search the published texts by meaning: `search-texts` edge function + /texts card + reader anchor | Built and checked on a copy (tsc, vitest 18/18, vite build, browser with mocked APIs); patch ready for the Srangam repo |
| C3b | Ask: a generated answer that cites only the matched passages (signed-in users first, as it costs per answer) | Next, after C3a is live |
| W8 | Load time: 505 kB entry chunk (177 kB gzip) | Open: measure what the entry pulls in before splitting |
| W5 / W6 | "<decorative line>" markers on the reader; Hindi on the reader | Open |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs17_" + stamp))
        t = p.with_name(p.name + ".tmp_docs17"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
