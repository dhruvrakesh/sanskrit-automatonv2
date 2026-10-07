#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs16_2026_10_07.py  DOCS16_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 19), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: Markandeya on /texts, S3 applied, the recall measurement
that chose 1536 dimensions, C1 final, the C2 edge function, the status-panel fix (SITE_LINE),
the publisher's engine label (PUBLISH_ENGINE) and the small site one-offs (S4).
Marker-idempotent per file, backup first.

  python scripts/patch_docs16_2026_10_07.py --check
  python scripts/patch_docs16_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS16_2026_10_07"

PLATFORM = """

## 19. Markandeya on /texts; S3 applied; 1536 dimensions; C1 final and the C2 edge function (EMBED_PUBLISHED_C2, RECALL_768, SITE_LINE, PUBLISH_ENGINE - 2026-10-07; DOCS16_2026_10_07)

**Done on Srangam this afternoon** (your SQL editor exports, 15:43-16:14, and a browser check):
- **S2 G1-G5 and S3 L1-L5.**
  - L1, before: anon could execute all four functions.
  - L3, after: anon can execute none of them. authenticated keeps only the two correlation functions; service_role keeps all four.
  - L4 now lists only has_role and the two search functions.
  - L5 was exported at 10:44 UTC, while the last watchdog run it shows was 10:40, before the revoke. S4 M6 checks the runs after it.
- **markandeya_purana is published.**
  - The gate withheld 42 of 1,258 translated passages: 39 tagged noise, 3 page furniture.
  - The 9 SQL files (00, 01-07, 99) put 1,216 passages on the site, and 99_verify shows 1,216 local and on site, with 0 stale. `published` was then set to true.
  - /texts lists it with 1,216 passages, and /texts/markandeya_purana reads in 25 pages of 50, showing Devanagari, IAST and English.
  - Seen there: no "translated with ..." line (engine label empty; S4 M2 and PUBLISH_ENGINE), a title without diacritics (S4 M3), and two passages (p1.4, p1.6) that show the OCR marker "<decorative line>" (W5). There is no Hindi, because B1 has no Hindi column (W6).
- **Commits.** e82aacb carries the commit message of b45e74d by mistake, though it holds the S3 SQL, the docs15 patch and COMMIT_MSG_s3. d5fccda holds the docs15 text under the right message. History is left as it is.
- **The status panel was not refreshed.** The block_BE_reader.ps1 text was pasted into the console instead of run as a file, so it ran with no switches (transcript block_BE_20261007_161246.log): a read-only report.

**RECALL_768_2026_10_07** (`scripts/recall_check_768.py`, read-only, no API call).
- **Method.** It compares each passage's nearest neighbours under the local 3,072-dimension vectors with those under their first N dimensions, renormalised. It ran on 21,645 vectors (noise and frontmatter left out) in the 14:30 backup, with 300 sampled passages and seed 7.
- **N = 768:** recall@12 0.893 (worst passage 0.583) and recall@5 0.875. The full search's nearest passage is in the 768 top 12 for 99.7% of the sample.
- **N = 1536:** recall@12 0.956 (worst 0.750) and recall@5 0.948; nearest passage 100%.
- **Decision.** The plan's bar was 0.90 at k=12, so the cloud stores 1536 dimensions. halfvec(1536) is 3 KB a vector, about 5 MB for the 1,655 published passages.

**C1 final** (`docs/cloud/C1_corpus_brain_2026-10-07.sql`; the DRAFT file is superseded).
- halfvec(1536).
- `srangam_passages_to_embed(p_limit, p_doc_code)` returns what C2 still has to embed: passages of published texts with no vector, or whose text changed since (md5 of the embedded text), plus total_pending. The embedded text is the local brain's: "<iast> -- <translation>", or the translation alone.
- Grants are spelled out, after the S3 lesson: match_text_passages for anon, authenticated and service_role; the queue for service_role only.
- Re-tested on PostgreSQL 16 + pgvector 0.8.0 with Supabase-like default privileges:
  - V1 shows 14 of 14 objects and V3 shows the expected grants.
  - The queue returns only published, non-empty passages. It drops a passage once its vector is stored with the same hash, and returns it again after its translation changes.
  - anon gets "permission denied" on the queue.
  - A vector in the function's own text form is accepted by halfvec(1536), and anon's match finds it at similarity 1.000.

**C2, the edge function `embed-published-passages`** (`docs/cloud/C2_embed-published-passages/`: index.ts, lib.ts, lib_test.ts; for the Srangam repo's `supabase/functions/`).
- **Gate.** The same as every cost-bearing function there: requireAdminOrCron.
- **Request.**
  - It takes up to `limit` (1-1000, default 200) passages from the queue.
  - It embeds them in batches of `batch` (1-100, default 50) with gemini-embedding-001 batchEmbedContents: RETRIEVAL_DOCUMENT, outputDimensionality 1536, at most 2,000 characters each, as the local brain.
- **Key and retries.** The key travels in the x-goog-api-key header, never in the URL. Calls are retried on 429 and 5xx (2, 4 and 8 s), not on other 4xx.
- **Writes.** Each vector is L2-normalised and upserted on passage_id, 25 rows a request, with its source hash.
- **Failures.** A run stops at the first failure and says which batch and why; a re-run resumes. No new batch starts after 100 s, because `_cron_invoke_edge` waits 120 s. `dry_run` writes nothing.
- **Tests.** 10 Deno tests pass, with no network. index.ts type-checks against the real `_shared/auth-gate.ts` and supabase-js 2.58.0.
- **Not yet done:**
  - It has not been deployed, and has not been run against the live project.
  - The key is the GEMINI_API_KEY that `_shared/ai-provider.ts` already uses; that it is set is not verified from here.
- **Cost.** The local ledger's rate (56 passages for $0.0015) puts the 1,655 published passages at about $0.05.
- **Running it.** `docs/cloud/C2_run_and_schedule_2026-10-07.sql`: R1 dry run, R2 read the answer from net._http_response, R3 embed 500 a call, R4 count, R5 a real neighbourhood (passage 60.10), R6 an optional nightly schedule at 04:15 UTC.

**SITE_LINE_2026_10_07** (`scripts/patch_site_line_2026_10_07.py`, which edits the Srangam repo's `scripts/emit_project_status.py`).
- SITE_CORPUS becomes the 2026-10-07 measurement: 2 texts, 2 published, 1,655 passages, reader page true.
- With the reader page live, the "Not yet true" line now reads "Only 2 of the 65 works in the corpus can be read on this site so far (1,655 passages at /texts, measured 2026-10-07); the rest exist only in the working corpus." It previously said "loaded ... no reading page yet".
- Without a reader page the old wording stays.

**PUBLISH_ENGINE_2026_10_07** (`scripts/publish_srangam.py`). Without `--engine`, the text row is labelled with the one engine that every translated passage records. If there are several, it guesses nothing and prints the counts.
"""

RUNBOOK = """

## Srangam: refresh the status panel, apply C1, deploy and run C2 (DOCS16_2026_10_07)

- **Run an ops script as a file, never by pasting its text:** `& 'D:\\Sanksrit Automatons\\_ops_2026-09-10\\block_BE_reader.ps1' -Verify`. Pasted text runs with no switches.
- **The status panel** (git by hand, in `D:\\srangam-42267`):
  1. `git status -sb`, then `git switch main`, then `git pull --ff-only origin main`.
  2. `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_site_line_2026_10_07.py" --check`, then the same without `--check`.
  3. `python scripts\\emit_project_status.py --db "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\data\\context.db" --site-reader --check`, then the same without `--check`.
  4. `git diff --stat`, then commit the two files.
  5. Push main yourself, then Publish in Lovable.
- **C1.** Paste `docs\\cloud\\C1_corpus_brain_2026-10-07.sql` whole, run it once, then V1-V4 one at a time.
- **C2.**
  1. On main in `D:\\srangam-42267`, copy `index.ts` and `lib.ts` from `docs\\cloud\\C2_embed-published-passages` into `supabase\\functions\\embed-published-passages\\`.
  2. Append `[functions.embed-published-passages]` / `verify_jwt = false` to `supabase\\config.toml`.
  3. Commit, push, Publish.
  4. Confirm the function is listed in Lovable Cloud (Edge functions); if it is not, ask Lovable in its chat to deploy it.
  5. Then run `docs\\cloud\\C2_run_and_schedule_2026-10-07.sql` R1-R5.
- **Recall check, any time:** `python scripts\\recall_check_768.py --db "D:\\backups\\<a backup>.db" --immutable` (add `--dims 1536` to measure 1536).
"""

EP = """

## Addendum 2026-10-07 (6): the cloud brain's first real step (DOCS16_2026_10_07)

| # | Item | State |
|---|---|---|
| S3 | Function lockdown | Applied 16:13; L3/L4 as expected; post-revoke cron runs to confirm (S4 M6) |
| W2 | markandeya_purana on /texts | Done 16:1x: 1,216 passages, 25 pages |
| W7 | Engine label and IAST title for markandeya (S4 M2/M3); publisher labels by itself from now on (PUBLISH_ENGINE) | M2/M3 ready to run; patch built |
| W1 | Status panel: SITE_CORPUS 2026-10-07 and the "readable on this site" line (SITE_LINE) | Patch built; manual git on main, then Publish |
| R768 | 768 vs 1536 dimensions, measured: recall@12 0.893 vs 0.956 | Done; 1536 chosen |
| C1 | Final file: halfvec(1536), embed queue, explicit grants | Ready to apply; re-tested |
| C2 | `embed-published-passages` edge function + run/schedule SQL | Built and tested offline; deploy, then R1-R5 |
| C3 | Ask on the site: embed the question (RETRIEVAL_QUERY, 1536), match_text_passages, answer with citations | Next, after C2 has run |
| W5 | "<decorative line>" OCR markers shown on the reader (2 passages, p1.4 and p1.6) | Open: strip in the publisher or the reader |
| W6 | Hindi on the reader (B1 has no Hindi column) | Open: needs a column, the publisher and the reader page |
| W3 | Article titled "....docx (1)" | S4 M4/M5 ready |
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs16_" + stamp))
        t = p.with_name(p.name + ".tmp_docs16"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
