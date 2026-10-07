#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs18_2026_10_07.py  DOCS18_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 21), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: search by meaning is live (checked in a browser), C2 at
1,500 of 1,655 with the NULL guard applied, the story corrections (#3, #5, #10) as a checked fix
file, and two Srangam patches (W8 load time, W5 reader marks) with their measurements; W6 (Hindi
on the reader) planned. Marker-idempotent per file, backup first.

  python scripts/patch_docs18_2026_10_07.py --check
  python scripts/patch_docs18_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS18_2026_10_07"

PLATFORM = """

## 21. Search is live; story corrections; load time and reader marks (DOCS18_2026_10_07)

**What changed on Srangam (checked on 2026-10-07, after 12:19 UTC)**
- **Lovable at 12:19 UTC.** Commit ad52f0b "Changes" switched the one import in `supabase/functions/_shared/ai-usage.ts` to the esm.sh supabase-js 2.58.0 form the other functions use. Lovable said it fixed build errors and redeployed five functions, embed-published-passages among them. Merge 117ce57 "Deployed search-texts edge fn" followed. Our two functions do not import that file.
- **search-texts is deployed.**
  - **The PowerShell probe.** Its 404 came before this deploy; asked from the live site afterwards, the function answers.
  - **Short-question probe from the live site.** POST {"q":"ab"} answers 400 "Ask with at least 3 characters."
  - **A real search on /texts.** "why did the king sell his wife and son" returned 10 Markandeya passages in 3.6 s (first call, cold): p49.11, p60.8, p62.5, p49.6, p70.2, p47.4, p53.2, p49.4, p65.3, p61.6.
  - **Links.** Each hit links to `?p=<page>#p<page_no>-<idx>`. `/texts/markandeya_purana?p=15#p60-8` opens "Page 15 of 25" with the passage 96 px from the top, marked, and steady over 10 s.
- **C2.**
  - **Request 374.** 500 more vectors stored; R4 shows markandeya_purana 155 pending (total_pending 155). One more R3 finishes it.
  - **R5, rerun.** 60.10 itself at 1.000, then 44.11 (0.876), 60.9 (0.876), 61.9 (0.873), 49.4 (0.868), 60.12 (0.867): the cremation-ground and sale episodes, as expected.
- **C1c (docs/cloud/C1c_match_null_guard_2026-10-07.sql), applied.** match_text_passages now returns no row for a NULL question vector (G3 = 0); the R5 symptom (six rows with NULL similarity) cannot recur. G2: the grants are unchanged, `{=X/postgres,postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}`. The PUBLIC entry has been there since C1 (PostgreSQL's default for a new function; the function is public on purpose).

**Story corrections (STORY_FIX_2026_10_07).**
- **What was wrong.** Read against their passages:
  - **#3** makes the Apsaras Vapuh the rakshasa's widow. The widow is Madamika [8.8, 9.11], a daughter of Menaka [10.2]; Vapuh is their daughter Taci, born under the sage's curse [10.3].
  - **#5** names "Draupadi". The passage says "the one daughter of Drupada" [25.8], and the check accepts only names the passages give.
  - **#10** had all 15 citations in one bracket at the end (8 sentences without a citation).
- **The tool.** `scripts/story_fix.py` applies a reviewed fix file the way the dashboard's Edit does:
  - stories.verify() runs against the same passage window (pad 2, cap 60);
  - the check and citations are stored, the story goes back to draft and approved_at is cleared;
  - it is all or nothing, marker-idempotent and guarded by updated_at;
  - an anchor must occur once, a whole-field replacement must match the reviewed md5, and a corrected text must pass the check;
  - unlike the dashboard's Edit, it can change `why`, the summary the illustration prompt reads.
- **The fix file.** `docs/stories/fix_markandeya_2026-10-07.json`:
  - #3: span replacements in English and Hindi, a new why, a note;
  - #5: one phrase in each language;
  - #10: rewritten in both languages, guarded by md5, 13 sentences each with its own citation.
- **Checked on a copy of the 13 stories and 1,276 passages** (from backups/context_pre_vnames_20261007_154009.db):
  - the check passes for all three (#3: 228 words, 35 citations; #5: 181, 22; #10: 218, 22);
  - a second run skips all three;
  - `stories.py verify-all` then reports 13 pass, 0 fail.
  - 9 unit tests (tests/test_story_fix_2026_10_07.py): 8 fail without the script, all pass with it.

**W8 load time (patch_load_w8_2026_10_07.py, Srangam).**
- **Measured on the production build with sourcemaps.** The entry is 505.47 kB (176.64 kB gzip). Its largest parts:
  - src/data/articles/meta.ts 85.6 kB (the card registry, pulled in by Home);
  - @tanstack/query-core 34.2 kB;
  - sonner 33.0 kB;
  - radix-select 18.0 kB (Home);
  - the shadcn sidebar 12.9 kB, which comes only from AdminLayout, imported eagerly.
- **Live, in the browser.**
  - **Hero preload.** The home page's hero (172 KB WebP) was preloaded at high priority on every route, /texts included, because index.html is the shell of every route.
  - **The shell itself.** A warm fetch takes 43-87 ms (Cloudflare, no-cache, must-revalidate).
- **What the patch does.**
  - **The hero preload.** It moves into a four-line inline script that adds the same link only on "/".
  - **AdminLayout** becomes lazy (the routes already sit in Suspense).
- **Result on the same build.**
  - **Entry.** 485.72 kB (171.87 kB gzip); AdminLayout is its own 18.30 kB chunk.
  - **In a browser.** "/" preloads the hero once at high priority; /texts neither preloads nor requests it; /admin still redirects to /auth for a visitor; no page errors.
  - **Tests.** The new test fails 3 of 4 before the patch and passes after. vitest 30/30 across 5 files; tsc reports no new error.
- **Considered and not done.** Lazy Home would take about 130 kB out of the entry, but it adds a round trip to the landing page. meta.ts is already the light registry (Phase 1.1); shrinking it means changing how Home loads its cards.

**W5 reader marks (patch_reader_marks_2026_10_07.py, Srangam).**
- **The problem.** Two published passages, Markandeya p1.4 and p1.6, begin their Devanagari and IAST with the OCR line "<decorative line>".
- **The fix.** splitDecoration() in corpusDisplay.ts drops lines that are exactly that marker; the reader draws a short rule (aria-hidden) instead. Nothing else in the text changes.
- **Checks.** Test: 3 fail before, 33/33 pass after across 6 files. In a browser: the rule appears, the marker text is gone, and neighbouring passages are unchanged.
- **Running heads.** Of 16 "Markandeya Purana //" passages, the publication gate already withholds 14. p1.1 is the book's title line (keep). p8.1 is a running head with a stray "t" that the furniture detector missed. Removing it needs the local text_type set to noise first, then a DELETE on the site: the bridge never deletes, and a republish would bring it back.
- **Sandilya's "Thus." passages** translate "iti" and are text, not noise.

**W6 Hindi on the reader, planned (not built).**
- **Coverage.** Hindi exists locally for 1,212 of 1,216 Markandeya and 437 of 440 Sandilya passages (translations_l10n, lang hi). srangam_text_passages has no Hindi column.
- **Three steps, in order:**
  1. an additive `translation_hi TEXT` column (SQL);
  2. publish_srangam.py emits it (ON CONFLICT ... translation_hi = EXCLUDED.translation_hi); C2 re-embeds nothing, since the vectors are made from iast and English;
  3. the reader shows Hindi under the English. The loader falls back to the old select if the column is missing, so the order of deploys cannot break /texts.
"""

RUNBOOK = """

## Finish C2; story fixes; Srangam W8 and W5 (DOCS18_2026_10_07)

- **C2.** Run R3 once more, then R2: expect "taken":155 and "pending_after_estimate":0. Then R4: 1655 | 1 | 1536 | 1536, and no pending rows. R6 (nightly at 04:15 UTC) is optional.
- **Story fixes**, from the automaton root, with the dashboard idle:
  1. Back up: `python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_storyfix_20261007.db`.
  2. `python scripts\\story_fix.py --file docs\\stories\\fix_markandeya_2026-10-07.json --check`, then the same without `--check`.
  3. `python scripts\\stories.py verify-all --doc markandeya_purana`: expect 13 pass, 0 fail.
  4. Read each story (`stories.py show --id N` or the Stories page), then approve it: `python scripts\\stories.py approve --id N`. Approval stays a person's decision.
- **Srangam**, in `D:\\srangam-42267` on main after `git pull --ff-only origin main`:
  1. `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_load_w8_2026_10_07.py" --check`, then the same without `--check`.
  2. The same two steps for `patch_reader_marks_2026_10_07.py`.
  3. Checks: `npm run typecheck`; `npx vitest run src/__tests__/load-w8.test.ts src/__tests__/reader-marks.test.ts src/__tests__/texts-reader.test.tsx src/__tests__/corpus-search.test.ts src/__tests__/query-bounds.test.ts`; `npm run build`.
  4. Commit the 6 paths, push main yourself, then click Publish in Lovable. No edge function changes.
"""

EP = """

## Addendum 2026-10-07 (8): search live, stories, load time (DOCS18_2026_10_07)

| # | Item | State |
|---|---|---|
| C2 | embed-published-passages | 1,500 of 1,655; one more R3; NULL guard (C1c) applied |
| C3a | Search the texts by meaning | Live: deployed 12:19 UTC; real search 10 hits; reader link lands and marks |
| ST1 | Story corrections #3, #5, #10 | story_fix.py + fix file; on a copy 13/13 pass; run it, then approve after reading |
| ST2 | Approved stories on the site (srangam_stories) | Next: an --emit-sql bridge for approved stories, like the passages |
| W8 | Load time | Patch: entry 505 -> 486 kB, hero 172 KB off every non-home page; further cuts need Home changes |
| W5 | "<decorative line>" on the reader | Patch ready; p8.1 running head needs a local noise mark, then a site DELETE |
| W6 | Hindi on the reader | Planned: column, publisher, reader (coverage 99.7%) |
| C3b | Ask (generated answer citing only matched passages) | After C3a has run for a while; signed-in users first |
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs18_" + stamp))
        t = p.with_name(p.name + ".tmp_docs18"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
