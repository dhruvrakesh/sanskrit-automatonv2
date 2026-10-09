# The whole brain in PostgreSQL, kept current (2026-10-08)

Marker: CORPUS_MIRROR_C4_2026_10_08. Built and tested; not yet applied to Lovable Cloud.

## Why this is new

Until today only **published** text reached PostgreSQL.
- `publish_srangam.py --emit-sql` fills `srangam_texts` and `srangam_text_passages`.
- C2 makes vectors in the cloud for those passages.
- That covers 2 texts and about 1,655 passages.

The cloud plan (`docs/CLOUD_BRAIN_2026-10-07.md`) deliberately left the rest at home. The rest of the brain lives only in `data/context.db`: 63 live documents, 75,734 passages, the Hindi, the entities, the stories and the vectors.

C4 adds a **private mirror** of all of it. You can query it in SQL from anywhere, and it is kept current while translation goes on.

## What moves, measured

Measured on 2026-10-08 from `context_20261008.db`, opened read-only and immutable: `corpus_sync.py --sink none`.

| Part of the 983 MB file | Size | Mirrored? |
|---|---|---|
| `passages`, without the two OCR columns: 75,734 rows | about 85 MB as JSON | yes |
| `passages.norm`: the raw OCR page, repeated on every passage of that page | 286 MB | no |
| `passages.ocr_variants` | 1.7 MB | no |
| `passage_embeddings`: 21,931 x 3,072 float32 | 281 MB | yes, cut to 1,536 dims (about 290 MB as text, about 85 MB gzipped) |
| SQLite's own search index (`passages_fts_*`) | 216 MB | no; PostgreSQL builds its own |
| `mt_cache` | 48 MB | no (translation stays local) |
| `translations_l10n` (Hindi): 12,517 rows | 11.8 MB | yes |
| entities 8,269, with 22,427 variants; mentions 32,861 | 7.4 MB | yes |
| stories 44, pipeline stages 767 | 0.8 MB | yes |
| usage, budget and job tables | 9 MB | no |
| 3 retired documents | | no |

The first push sends about 115 MB over the wire. After that, each run sends only what changed.

**In PostgreSQL.** A full-size test copy took 265 MB (75,720 passages, 22,040 vectors with their HNSW index, 12,500 Hindi rows). Real text makes the word-search index larger, so plan on 300 to 400 MB. Check the space first with P1.

## How it works

```
this PC (source of truth)                         Lovable Cloud (Supabase)
  data/context.db  --read only-->  corpus_sync.py  --HTTPS, signed-->  edge fn corpus-ingest
                                    (row hashes,                          | service_role
                                     digests)                             v
                                                       public.corpus_manifest / _keys / _ingest / _retire / _run
                                                                          |
                                                       schema corpus: docs, passages, translations, entities,
                                                       mentions, stories, stages, passage_vectors, sync_runs
                                                       (private: no Data API, no anon, RLS on, no policy)
```

**Idempotent by construction.**
- **Row hashes.** Every row carries `row_hash`, the md5 of its mirrored columns.
- **Digests.** `corpus_manifest()` returns, per table and per document, a count and a digest: the md5 of the "key row_hash" lines in byte order.
- **What is sent.** `corpus_sync.py` makes the same digest locally. Equal digests mean nothing to send. For a document that differs, it fetches the server's keys and sends only the rows whose hash differs.
- **Repeats are harmless.** `corpus_ingest()` upserts with `ON CONFLICT ... WHERE row_hash IS DISTINCT FROM ...`, so sending a batch twice changes nothing. An interrupted run is finished by the next one.
- **No local ledger.** The server is compared afresh every run, so nothing can drift.
- **Retire, never delete.** A row gone locally is marked `retired_at` in the mirror. If it comes back, it is restored.
- **Guards.** These are held unless you pass `--allow-mass-retire`:
  - more than half of a group of over 100 rows retired at once;
  - a group emptied entirely when it held more than 5 rows;
  - more than 3 documents (or 10 percent) vanishing at once.
- **Verify.** At the end of a run, every group the run settled is compared with the server again; it reports "N groups equal, 0 different".

**Keys that survive re-ingest.** Passages are keyed by (document, page_no, idx), the local UNIQUE key, not by the local id. The local id changes when a document is re-ingested: the highest id is 229,781 for 75,734 rows.

**No Supabase key on this PC.**
- The edge function runs as service_role inside Supabase.
- The PC holds only `CORPUS_SYNC_SECRET`, a random 64-character value. It signs each request: HMAC-SHA256 over the timestamp and the body, with 5 minutes allowed for clock difference. It can write to the mirror and nothing else.
- The URL and the publishable key come from the Srangam repo's `.env`; both are already public.
- Schema changes still go through the SQL editor.

**What the site sees.** Nothing.
- The reader keeps reading `srangam_texts` and `srangam_text_passages`, which only the publish gate fills.
- anon and authenticated have no privilege on the schema, the tables, the view or the functions. C4's V2 check shows this.

## Steps

1. **Pre-flight.** Run `docs/cloud/C4_preflight_2026-10-08.sql` (P1, then P2). Expect:
   - vector 0.8.0 in public;
   - schema corpus absent;
   - service_role present.

   Note the database size. Then check the room left in Lovable Cloud: Advanced settings, and the Usage page.
2. **Build.** Paste `docs/cloud/C4_corpus_mirror_2026-10-08.sql` into the SQL editor and run it once. Then run V1 to V4 one at a time:
   - V1: 31 rows, all true;
   - V2: every column false;
   - V3: 5 rows, true;
   - V4: eight empty objects.
3. **The secret.**
   - In PowerShell, in the automaton folder, make it once. The value goes into `.env` and onto the clipboard, and never into a chat.
   - In Lovable Cloud, open Secrets and add `CORPUS_SYNC_SECRET`, pasting the value.
4. **The edge function.**
   - `supabase/functions/corpus-ingest/` (index.ts, lib.ts) is in the Srangam repo. Push it.
   - Ask Lovable to deploy `corpus-ingest` without changing its code. `verify_jwt = false` is fine, because the function checks its own signature.
   - The tests are `docs/cloud/C4_corpus-ingest/lib_test.ts` here, run with `deno test`.
5. **Hello.** Run `python scripts\corpus_sync.py --hello`. It should answer with the version and `docs_in_mirror` 0.
6. **Plan, then the text.**
   - `python scripts\corpus_sync.py` prints the plan.
   - Then: `python scripts\corpus_sync.py --apply --tables docs,entities,passages,translations,mentions,stories,stages`
7. **The vector gate.**
   - Run `python scripts\corpus_sync.py --apply --tables vectors --doc markandeya_purana`.
   - Then run M4 in `docs/cloud/C4_verify_2026-10-08.sql`. It compares the mirror's vectors (local, cut to 1,536 dims) with the site's (made in the cloud by C2). They share the model, task type and text.
   - Expect avg_cos >= 0.99 and min_cos >= 0.95.
   - If they fall short, keep vectors out: leave `vectors` off `--tables` and add `--tables` to the scheduled task. Then a cloud-side embedder for the mirror would be the next step, about $1 for everything at the ledger's rate.
8. **Everything.** Run `python scripts\corpus_sync.py --apply`. It ends with "verify: N groups equal, 0 different".
9. **Keep it current.**
   - Register `scripts\corpus_mirror_task.ps1` as a scheduled task every 2 hours. It sends at most 80 MB per tick.
   - It is read-only on `context.db`, so it runs while translation runs and does not wait for an idle dashboard.
   - Log: `D:\backups\corpus_mirror_log.txt`; each run is also recorded in `data\corpus_sync_log.jsonl` and in `corpus.sync_runs`.

## Querying

In the Lovable Cloud SQL editor (`docs/cloud/C4_verify_2026-10-08.sql`):
- M1 `corpus.v_docs`: per document, the counts of passages, English, Hindi, vectors and stories.
- M5 `corpus.search('cremation ground', 20)`: words in the English (stemmed) and the IAST.
- M6 `corpus.match_passages(vector, k)`: passages nearest in meaning, across all documents.
- M7: what is still untranslated, per document.

**Your own PostgreSQL** works the same way, for example a local one or DBeaver.
- Apply the same C4 file there.
- Then run `python scripts\corpus_sync.py --sink pg --dsn postgresql://user:pw@host/db --apply`.
- The same five functions are used, so the behaviour is identical. This needs `psycopg`.

## Cost

- **Database.** About 300 to 400 MB more.
- **Edge function calls.** About 300 for the first push; after that, a handful every 2 hours (two manifest calls, the keys of documents that changed, and the batches).
- **AI.** No call to an AI model. Nothing is embedded in the cloud for the mirror.
- **Where it is billed.** Lovable Cloud bills usage through Lovable. Read the Usage page after the first push.

## Limits

- **One way, PC to cloud.** Nothing is pulled back.
- **Formats kept as they are.** `translated_at` and the other local times are kept verbatim as text, because their formats are mixed.
- **Vectors are the local ones.** A passage is in the mirror's vector table only after maintenance has embedded it here.
- **No Ask yet.** Ask over the whole corpus is not wired. `corpus.match_passages` is ready for an admin-only scope in `search-texts` (C3b).

## If something fails

| What you see | Meaning | What to do |
|---|---|---|
| `HTTP 404` on `--hello` | The function is not deployed | Step 4 (ask Lovable to deploy `corpus-ingest`) |
| `HTTP 503 ... CORPUS_SYNC_SECRET is not set` | The secret is missing in Lovable Cloud | Step 3, second half |
| `HTTP 401 bad signature` | The two secrets differ | Paste the `.env` value into Lovable Cloud again |
| `HTTP 401 ... more than 5 minutes off` | The PC clock is wrong | Settings -> Time -> Sync now |
| `HTTP 422 ... Could not find the function public.corpus_manifest` | The API has not seen C4 yet | In the SQL editor: `NOTIFY pgrst, 'reload schema';` |
| `HTTP 422 ... statement timeout` | A batch was too big for the instance | Add `--batch-kb 500` |
| `HTTP 422 ... violates foreign key` | A child row came before its passage, for example with `--tables` but without passages | Run without `--tables`, or include `passages` |
| `HELD: ...` | A large retire is waiting for you | Read it; re-run with `--allow-mass-retire` if it is right |

None of these leaves the mirror half-written in a harmful way. Fix the cause and re-run; the run sends only what is still missing.

## Rollback

The DROP statements are in the header of `C4_corpus_mirror_2026-10-08.sql`. Nothing else depends on the mirror. Delete the scheduled task and the secret.

## Tests

- **`tests/test_corpus_sync_2026_10_08.py`: 21 tests.** No PostgreSQL and no network.
  - An in-memory server follows the C4 rules.
  - An HTTP stub on 127.0.0.1 checks signature and gzip as the edge function does.
  - Golden values tie the digest to PostgreSQL 16 and the signature to `lib_test.ts`.
- **`tests/test_corpus_sync_pg_2026_10_08.py`: 7 tests.** They run only when `CORPUS_TEST_DSN` names a throwaway database.
  - C4 is applied twice.
  - A full sync is followed by a second one that sends 0.
  - Changes and removals travel.
  - Stray values do not block a batch.
  - Search and vectors answer.
  - anon and authenticated are refused.
- **`docs/cloud/C4_corpus-ingest/lib_test.ts`: 7 Deno tests.**
- **End to end in the sandbox.** The real `index.ts` ran with stand-ins only for its two web imports, in front of PostgreSQL as service_role:
  - first push, then a second push sending 0;
  - a wrong secret got 401 with no retry;
  - a foreign-key refusal got 422 with no retry.
- **Full size.** A 75,720-passage, 22,040-vector copy took 248 s in one push and 3.1 s for the run after it, 374 groups equal.
- **The real backup.** Planned with `--sink none` in 19 s. A type audit of every row found 0 values that PostgreSQL would refuse.


## Watching a push (DOCS22_2026_10_08)

A first push takes minutes. While it runs:
- **The run's own lines.** It prints `[m:ss]` lines: what the mirror holds, each table and document as it is sent, the batches of large ones, every 10 documents compared, and the final check.
- **Status from a second window.** `python scripts\corpus_sync.py --status` prints, per table, the rows in the mirror against the rows here, with the share. It is read-only on both sides. Equal counts are not proof of equal content; the digest check at the end of an `--apply` run is.
- **Stopping and resuming.** Ctrl+C is safe at any point; the next run sends only what is missing.

Live state on 2026-10-08:
- P1 showed PostgreSQL 17.6, 93 MB, vector 0.8.0 in public, schema corpus absent, and 1,655 published passages with 1,655 vectors.
- C4 was applied at 15:21 IST.
- corpus-ingest was deployed with verify_jwt off. An unsigned request gets 401.
- The signed hello answered docs_in_mirror 0 at 10:03:54 UTC.
- **The text push** finished at 10:09:41 UTC: 343 s, 101.4 MB, 317 groups equal, 0 different. It sent 63 documents, 75,734 passages, 13,040 translations, 8,269 entities, 32,861 mentions, 44 stories and 767 stages.
- **markandeya_purana vectors.** 1,258 in 38 s.


## C4b: digests that do not re-read the mirror (DOCS23_2026_10_08)

- **The timeout.** After all 21,931 vectors were in, the run's final check failed with `corpus_manifest: canceling statement due to statement timeout`. The C4 manifest re-read and sorted every row of every table on every call.
- **The cure.** `docs/cloud/C4b_mirror_digests_2026-10-08.sql` keeps `corpus.row_index` (key and row_hash) and `corpus.group_digest` (count and running sums) current inside `corpus_ingest`/`corpus_retire`.
  - The digest is order-free: `count:sum1:sum2` over md5(key + ' ' + row_hash), modulo 2^64. A change subtracts the old row and adds the new one.
  - The manifest reads a few hundred small rows (8 ms on a full-size copy), and `corpus_keys` reads an index range.
- **Apply.**
  - Step A: the file once.
  - Step B: `SELECT corpus._rebuild_index('<table>');` for each of the 8 tables, one at a time.
  - Then K1-K3. Then corpus_sync.py 4.2, which checks `"_scheme": "sum64.1"` and refuses an older server.

## Reading it: /corpus for signed-in readers (DOCS23_2026_10_08)

- **SQL.** `docs/cloud/C5_corpus_reader_2026-10-08.sql` adds six functions:
  - `corpus_reader_allowed`;
  - `corpus_reader_docs`, `corpus_reader_page`, `corpus_reader_search`;
  - `corpus_reader_similar`, `corpus_reader_match`.
- **Access.** Each reads the closed schema for the caller after one check:
  - an admin may always read;
  - otherwise `corpus.reader_access.mode` decides: `signed_in` (default), `readers` (the list in `corpus.readers`) or `admins`.
  - Not signed in is refused. Nothing in the schema is granted to anyone.
- **Site (Srangam repo).**
  - `src/lib/corpusMirror.ts`.
  - `src/pages/corpus/CorpusHome.tsx` (/corpus: documents with counts, search by words and by meaning).
  - `src/pages/corpus/CorpusDoc.tsx` (/corpus/:docCode: Sanskrit, IAST, English, Hindi, similar passages).
  - `src/components/corpus/CorpusGate.tsx`.
  - `src/lib/safeNext.ts` (/auth?next= brings a reader back).
  - Wired by `scripts/patch_corpus_reader_2026_10_08.py` (App.tsx routes, Auth.tsx next, a link on /texts).
- **Meaning search.** `supabase/functions/search-corpus` embeds the question as search-texts does and calls `corpus_reader_match` as the reader. M4 showed the mirror's vectors and the cloud's are the same (cosine 1.0000), so questions and passages share one space.
- **Sign-up on Srangam is open.** `signed_in` means anyone with an account. The pages say that nothing is reviewed, and they are marked noindex.


## Kept current: the first scheduled runs (DOCS24_2026_10_08)

- After C4b and the 8 rebuilds, K1 showed indexed = digested in all 8 tables, and K2 showed none.
- The two-hourly task ran at 16:35 (rc=0) and again at 17:18.
  - At 17:18 it sent 4 new Ganita translations and nothing else.
  - Its check found 380 groups equal and 0 different, in 9.3 s.
  - New translations reach the mirror within two hours, and nothing is uploaded twice.
- The log is `D:\backups\corpus_mirror_log.txt`. `python scripts\corpus_sync.py --status` compares counts on demand.


## Contents for the corpus reader (C5b, DOCS25_2026_10_08)

- **What it is.** `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql` adds `corpus_reader_outline(p_doc, p_per_page)`. It has the same gate as the C5 functions, and only signed-in callers may execute it.
- **What it returns.**
  - One 'page' row per 50 passages: the first passage and the last scan page reached.
  - One 'colophon' row per passage typed colophon, with 160 characters of its English (or its Sanskrit).
- **Used by.** The Contents panel and "go to a scan page" on `/corpus/:docCode`. It is read only when the panel opens.
- **Speed.** 30 ms on 21,128 passages.
- **Rollback.** `DROP FUNCTION public.corpus_reader_outline(text, integer);`


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


## Researchers (C7, DOCS27_2026_10_08)

- **Who reads, by mode.** `corpus_reader_allowed()` now reads:
  - mode 'signed_in': anyone signed in;
  - mode 'readers': researchers (role 'researcher', by invitation), users on corpus.readers, admins and the super admin;
  - mode 'admins': admins and the super admin.
- **Signed out.** No one reads while signed out.
- **Setting the mode.** The super admin sets it on /admin/researchers (`corpus_access_mode_set`), and every change goes to rbac.audit.
- **Researchers and stories.** Researchers see approved stories, like any reader. Drafts and candidates stay for admins (C6).
- **No change to the mirror run.**


## Health on 2026-10-08 evening (DOCS29_2026_10_08)

- **Runs.** 16:35, 18:32 and 20:33 IST, all rc=0. At 20:33: 14,458 passages, 374 translations and 21 stories sent; the check found 392 groups equal and 0 different.
- **Vectors.** No new vectors since the full push, because maintenance at 21:00 found nothing to embed among the 21,915 translated passages. A passage gets a mirror vector only after an idle maintenance run embeds it on the PC.
- **Checking it from the cloud side.** `docs/cloud/OPS_health_2026-10-08.sql`: H5 for the runs, H6 for the totals, H7 for English without vectors, H8 for the digests.
- **C7.** Nothing in the mirror changed. `corpus_reader_allowed()` now also admits the super admin always, and researchers in mode 'readers'. The mode is still signed_in.


## The pictures in the same tick (DOCS30_2026_10_09)

- After the mirror, `corpus_mirror_task.ps1` runs `scripts\corpus_media.py --apply --if-configured --max-mb 40`, once `scripts/patch_media_task_2026_10_09.py` is applied.
  - It uses the same secret, URL and key, and the same signature, against the function `corpus-media`.
  - It is read-only on `context.db`.
  - When nothing changed, it only asks the site what it has.
- Its log lines go to the same `D:\backups\corpus_mirror_log.txt` ("DONE - corpus media rc=..."), and each run is also recorded in `data\corpus_media_log.jsonl`.
- A picture can travel only for a text that is already in schema corpus, so the mirror runs first.
- The tick keeps the PC awake while it runs. The night tick of 2026-10-08 stretched to 7.5 h when the PC slept in the middle of it.


## The Corner sends its results on (DOCS31_2026_10_09)

- After each request, `scripts/corner_worker.py` runs these, so a result is on the site within a minute of the desk finishing, not two hours later:
  - `corpus_sync.py --apply --if-configured --doc <code> --tables docs,stories` for stories;
  - `corpus_media.py --apply --if-configured --doc <code>` for pictures and novels.
- Both are the same idempotent pushes the two-hourly task runs, limited to that text.
- Every sync command is in `docs/SYNC_COMMANDS_2026-10-09.md`.
