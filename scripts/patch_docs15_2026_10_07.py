#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs15_2026_10_07.py  DOCS15_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 18), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: what the live Srangam site shows, the function
lockdown (S3), the C0 results, and a second correction on Ganita (it needs OCR before
any more translation). Marker-idempotent per file, backup first.

  python scripts/patch_docs15_2026_10_07.py --check
  python scripts/patch_docs15_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS15_2026_10_07"

PLATFORM = """

## 18. What the live Srangam site shows; function lockdown (S3); cloud pre-flight passed; Ganita needs OCR first (SRANGAM_LOCKDOWN_S3 - 2026-10-07; DOCS15_2026_10_07)

**Release b45e74d7 (15:05).** `verify-all` on markandeya_purana: 11 pass and 2 fail (#5, #10), as predicted. #3, #6 and #11 now pass. Nothing is approved yet.

**Second correction on Ganita (to sections 16 and 17).** With the right code, corpus_status says NEEDS-OCR:
- source debris is 21.9% of passages, and 0% of passages come from vision;
- 339 page PDFs are in the inbox, 1,729 English rows and 4 Hindi rows exist, and the estimate is $1.08.

The advice to resume translate_both was wrong. Re-ingesting replaces the text, and only changed verses are paid for again. So the order is:
1. vision OCR (`ocr_consensus.py`);
2. re-ingest;
3. translate.

`python scripts\\corpus_status.py --commands --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` prints the exact commands.

**S2 results (15:05-15:06, read-only).**
- **G1.** The unfiled migration 20260201064547 is 736 characters long. It ends with GRANT EXECUTE on `increment_term_usage_counts` to service_role and authenticated.
- **G2.** Live, only service_role can execute it; anon and authenticated cannot. The repo's N.7 lockdown (20260517042601) holds.
- **G3.** Two policies apply: "Admin manage cross references" (ALL, authenticated, has_role admin), and the public read policy, which needs both articles to be published.
- **G4.** Of the 1,561 references: 1,392 published/published, 120 draft/published, 46 published/draft and 3 draft/draft.
- **G5.** An anonymous visitor can execute 7 SECURITY DEFINER functions. Three are public on purpose: has_role, srangam_search_articles_fulltext and srangam_search_articles_semantic. Four were never meant to be:
  - `_cron_invoke_edge(text, jsonb)` reads CRON_SECRET from vault and POSTs to any edge function with the x-cron-secret header.
  - `reconcile_stuck_admin_jobs()` marks running admin jobs failed.
  - `get_corpus_correlations(int,int)` and `get_corpus_correlations_v2(...)` read correlations across all articles, drafts included.

**Root cause, and S3.**
- The later migrations re-created or defined these functions with only `REVOKE ... FROM PUBLIC`. Supabase's default privileges grant EXECUTE on new functions to anon and authenticated by name, so revoking from PUBLIC alone leaves both able to call them through /rest/v1/rpc. The first version of `_cron_invoke_edge` (20260531075801) did revoke from anon and authenticated, and the enqueuers still do.
- `docs/cloud/S3_srangam_function_lockdown_2026-10-07.sql` has six blocks:
  - L1: before (read-only).
  - L2: one transaction that revokes anon (and authenticated where the design is service-role only). Authenticated keeps the two correlation functions, which the admin page calls.
  - L3: after.
  - L4: the G5 check, expecting the 3 intended functions.
  - L5: pg_cron runs.
  - L6: undo.
- Callers checked in the repo: pg_cron runs as postgres (the owner); the enqueuers are SECURITY DEFINER; the admin page calls signed in; correlate-corpus uses the service role. Nothing in src/ or supabase/functions calls these as an anonymous visitor.
- S3 was tested on PostgreSQL 16 with Supabase-like default privileges: the problem was reproduced, L2 fixed it, and a second run of L2 is harmless.
- From now on, any SECURITY DEFINER function added through Lovable must revoke from PUBLIC, anon and authenticated by name. Re-run L4 after such changes.

**C0 pre-flight results (15:07), all as C1 needs.**
- **Extensions:** pg_cron 1.6.4, pg_net 0.19.5, and vector 0.8.0 in schema public. halfvec is available.
- **C1 objects:** none present yet.
- **B1 in place:** 1 text, 1 published, 439 passages; has_role and srangam_update_updated_at present.
- **Existing vectors:** the only vector column is srangam_article_metadata.embeddings vector(1536).
- **Size:** the database is 78 MB.

C1 is not applied. It is additive and stays empty until C2 fills it, so it goes in with C2.

**The live site (checked in a browser, 2026-10-07 about 15:15).**
- **/research-network** reads "1392 scholarly connections across 50 articles", average 6.7/10, 2 reference types, and "Graph shows the 1,000 strongest of 1,392 connections". Since S1 these totals are exact; no deploy was needed.
  - The type filter lists 5 types, while 2 exist.
  - One published article is titled "Reassessing the Antiquity of the Rigveda.docx (1)".
- **/texts** lists the Sandilya Bhakti Sutra, 439 passages. It is live.
- **The status panel** (/sanskrit-translator and /jyotish-horoscope) is stale.
  - It reads "measured on 2026-09-27": 62 works, 54,292 passages, 18,631 English, 9,596 Hindi, 18,440 embedded.
  - It still says the loaded text has "no reading page yet", which is false since /texts went live.
  - The regenerated panel is commit 6b15ee7. It was measured 2026-10-04 (65 works, 74,543 passages, 20,273 English, 11,261 Hindi, 19,905 embedded) and says the reading page exists. It was made by `block_BE_reader.ps1 -ReaderLive -NoPush` at 20:28 on 2026-10-04, on the local branch feat/s1-nartiang-backlink. It was never pushed (that branch's remote ref was last pushed 2026-09-30 19:49) and is not on main, which is what Lovable publishes. This was read from the .git files; no git command was run.
- **Not on the site yet:**
  - markandeya_purana: CURRENT, with 1,219 English and 1,216 Hindi rows.
  - Every story, picture and the Ask brain: local until C1-C3.
- **The completeWorks rule.** emit_project_status lists a work as complete only at 100% English. markandeya (1,219 of 1,222, with 3 rows that cannot be translated as printed) will not be listed. This is a rule in the Srangam generator, to change there.
"""

RUNBOOK = """

## Srangam: refresh the status panel, lock down functions, publish a text; Ganita OCR first (DOCS15_2026_10_07)

- **Ganita.** Do not resume translation. Run `python scripts\\corpus_status.py --commands --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` and follow its order: `ocr_consensus.py` plan (free), then `--yes --max-usd`, then `--drift-only` (the re-ingest block), then translate.
- **S3.** Paste L1, L2, L3 and L4, then L5 ten minutes later, and L5 again the next day for the nightly jobs. Re-run L4 after any Lovable change that adds a database function.
- **The status panel.** Git runs by hand, in `D:\\srangam-42267`; no script pushes main.
  1. Look first: `git status -sb`, `git fetch origin`, `git rev-list --left-right --count HEAD...origin/main`.
  2. Switch and update: `git switch main`, then `git pull --ff-only origin main`.
  3. Run `block_BE_reader.ps1 -ReaderLive -NoPush`. It regenerates the panel with fresh numbers and the reading page, and commits locally.
  4. Read `git show --stat HEAD`.
  5. Push main yourself, then Publish in Lovable.
  - Branch feat/s1-nartiang-backlink (6b15ee7) is then superseded; delete it when you are content.
- **Publishing a text to /texts.**
  1. `python scripts\\publish_srangam.py --doc <code> --gate-report`, then `--dry-run`, then `--emit-sql <dir>`.
  2. Paste 00_text.sql, each NN_passages.sql and 99_verify.sql. The text lands unpublished.
  3. After review, run `UPDATE public.srangam_texts SET published = true WHERE doc_code = '<code>';`, then `block_BE_reader.ps1 -Verify`.
"""

EP = """

## Addendum 2026-10-07 (5): Srangam state and lockdown (DOCS15_2026_10_07)

| # | Item | State |
|---|---|---|
| S2 | Read-only follow-up (G1-G5) | Done 15:05-15:06 |
| S3 | Revoke anon (and authenticated where service-role only) on `_cron_invoke_edge`, `reconcile_stuck_admin_jobs`, `get_corpus_correlations`, `get_corpus_correlations_v2` | Ready to run; tested |
| C0 | Cloud pre-flight | Done 15:07: every C1 precondition met |
| C1 | Vectors, stories, RLS, `match_text_passages` | Ready; apply together with C2 |
| C2 | Edge function `embed-published-passages` (GEMINI_API_KEY is already referenced by Srangam edge functions; confirm it is set in Lovable Cloud secrets) | Next |
| W1 | Status panel stale (2026-09-27) and says there is no reading page; the fix (6b15ee7) is local on a feature branch | Open: manual git on main, then Publish |
| W2 | Publish markandeya_purana to /texts (gate report, SQL, review, flip) | Open: your decision |
| W3 | Article titled "....docx (1)"; network type filter offers 5 types, 2 exist | Open: Srangam admin / Lovable |
| W4 | completeWorks needs 100% English; texts whose only gaps cannot be translated as printed are never "complete" | Open: Srangam generator |
| T1 | Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V is NEEDS-OCR (21.9% debris, 0% vision, 339 pages, est $1.08): OCR and re-ingest before translating (corrects addendum 4) | Open |
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs15_" + stamp))
        t = p.with_name(p.name + ".tmp_docs15"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
