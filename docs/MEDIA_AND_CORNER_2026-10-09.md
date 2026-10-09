# Pictures, graphic novels, and the Researchers' Corner (2026-10-09)

Marker: CORPUS_MEDIA_C8_2026_10_09. The desk's image library (`images.py`) and graphic novels (`novel.py`) go to the site's working corpus: phase M1, built and tested here. This document also charts what follows: the Researchers' Corner (R1-R4), where researchers, admins and the super admin ask the desk for new stories, pictures and novels.

## 1. The question: keep the pictures in Google Drive?

**Yes**, as built in M1. It holds as long as the pictures stay private and pass the reader gate. Speed is the price, and it is paid only once per picture and device.

| Option | Cost | Privacy | First view | Decision |
|---|---|---|---|---|
| **Srangam Shared Drive, private folder, through an edge function** | Within the Workspace storage already held; no new service, key or plan | Not shared by link; every byte passes the reader's JWT and C8's rule | Slower (function + database check + Drive), then cached in the browser | **Chosen (M1)** |
| Private Supabase Storage bucket with signed URLs | Lovable Cloud storage and egress, billed by use | Good | Fast (CDN) | Kept for later (P1): only the function and `media_files.storage` change |
| Public bucket or Drive links | Lowest | Drafts and unreviewed pictures public; outside the corpus gate (C5/C7) | Fastest | Rejected |
| Pictures inside the database | Database size (the plan's tightest limit) | Good | Slow | Rejected |

**The numbers, measured on 2026-10-09 from the backup `context_20261009.db`.**
- **Pictures.** 57 would travel:
  - 31 library pictures: 18 approved and 13 drafts, over 6 texts;
  - 26 pictures of the 2 graphic novels, both still being drawn (20 pages, 6 cast sheets).
- **Not drawn yet.** 71 briefs stay home.
- **The renditions.** Made for all 57 in 4.4 s: 114 files, 14.3 MB.
  - thumb: about 31 KB;
  - display: about 264 KB.
- **The originals.** 62 MB, on this PC only.
- **At scale.** 1,000 pictures would be about 300 MB on Drive.

## 2. M1: pictures and graphic novels on the site (this release)

- **On the site** (Srangam: `docs/CORPUS_MEDIA_2026-10-09.md` there).
  - `/corpus/images`: the gallery, by text. Each picture is linked to its passage. `?pic=` opens one at full size, with its caption in English and Hindi, its story and the generated label.
  - `/corpus/novels` and `/corpus/novels/:id`: the novels. Each has its cast, then each page's picture beside its caption, in English, Hindi or both. Citations are links. Every spoken line carries its verse. Each page has "the scene the artist was asked for", and the novel ends with the check against its citations.
  - On the story pages: the story's picture, and "Read it as a graphic novel".
- **Who sees what** (C8, the same rule as the stories, C6).
  - Readers see approved pictures and approved novels.
  - Admins and the super admin also see drafts and novels still being drawn.
  - Retired is never shown.
  - Researchers are readers here; see R2.
- **The database.** `docs/cloud/C8_corpus_media_2026-10-09.sql`: one transaction, purely additive. The four tables `corpus.media`, `corpus.media_files`, `corpus.novels` and `corpus.media_config` are closed.
  - Readers have 4 functions.
  - The desk has 8, for service_role only.
  - Tests: `tests/test_corpus_media_pg_2026_10_09.py`, 8 tests.
  - Checks: `docs/cloud/C8_checks_2026-10-09.sql`: P1-P3, V1-V3 and D1-D5.
- **The edge function** `corpus-media`: `docs/cloud/C8_corpus-media/`, copied into Srangam's `supabase/functions/corpus-media/`.
  - **POST from the desk.** It is signed with `CORPUS_SYNC_SECRET`, exactly as `corpus-ingest`. An upload's bytes are checked against their sha256. The folder "Srangam corpus media" is made once, and nothing is ever shared.
  - **GET for a reader.** The JWT goes in a header. The database is asked as that reader, and Drive only after a yes. The answer is `private, max-age=2592000, immutable` with an ETag and 304.
  - **Tests.** `deno test`: 6 for `lib_test.ts` and 4 for `_test/handler_test.ts`.
- **The desk.** `scripts/corpus_media.py`.
  - **What it does.** It plans by default and sends with `--apply`. It uses the mirror's secret, URL and key, and is read-only on `context.db`.
  - **The order.** Renditions first. A row is sent only when both of its renditions are on Drive. Then the novels, then the pictures. Whatever is gone here is retired there.
  - **Guards.**
    - `--max-mb` limits a run.
    - A picture whose file is missing here is kept on the site, not retired.
    - Mass retirement is refused (more than half and more than 10) without `--allow-mass-retire`.
    - With `--if-configured` it exits 0 until C8 and the function are in.
  - **Log.** `data/corpus_media_log.jsonl`.
  - **Tests.** `tests/test_corpus_media_2026_10_09.py`, 15 tests, including the push into a real PostgreSQL with C8 and a read back as reader and as admin.
- **The schedule.** `scripts/patch_media_task_2026_10_09.py` adds `corpus_media.py --apply --if-configured --max-mb 40` after the mirror in `corpus_mirror_task.ps1`.
  - It also keeps the PC awake for the tick (SetThreadExecutionState), because the tick of 2026-10-08 night took 7.5 h when the PC slept in the middle of it.
  - It does not wake a sleeping PC. That is the task's own "Wake the computer to run this task" setting, which is your choice.

## 3. The path after M1

| Phase | What | Where it runs | Writes |
|---|---|---|---|
| **M2** | **Editors from the site.** On a draft picture or novel page, "approve", "retire" or "draw again (with a note)". Each is recorded as a request for the desk (R2's queue), and the desk applies it with `images.py` or `novel.py`. Also a Drive report: files of retired pictures (C8 D5) and the space used | Site (the request), desk (the change) | The desk only |
| **R1** | **The Researchers' Corner** at `/corpus/corner`, for researchers, admins and the super admin. Saved passages with private notes, one's own collections, and "my requests" with their status. A new closed schema `corner`, RLS by owner; editors read all | Site + database | The researcher (own rows) |
| **R2** | **Requests.** A story from a passage range, a picture for a passage, a graphic novel from an approved story, or a correction to a translation, each with a reason. A cost-bearing request from a researcher waits for an admin's or the super admin's approval, which shows the desk ledger's estimate | Site + database | The researcher, then an admin |
| **R3** | **The desk worker.** `corner_worker.py` takes approved requests through a signed function `corpus-corner` (the same HMAC scheme). It runs the existing CLIs (`stories.py`, `images.py`, `novel.py`) inside the desk's live budget and a daily cap. Results land as drafts in `context.db` and reach the site through the mirror and `corpus_media.py`. Nothing is approved automatically | Desk | The desk only |
| **R4** | **Accountability.** Per request: who asked, who approved, cost and outcome. Per researcher: spend. Daily and monthly caps. A "what the desk did" log on the Corner | Site + database | Desk and database functions |
| P1 | **Only if first views feel slow.** Display renditions move to a private bucket with signed URLs; thumbnails can stay on Drive | Cloud | The function |

**Why the desk executes requests, not the cloud.**
- **One source of truth.** `context.db` stays the only writer of texts, stories and pictures.
- **Reuse.** The prompts, the citation checks, the quality gates, the image-quality checks and the cost meter already exist there, and are tested.
- **No new spending.** No generation key or spending path is added to the cloud.
- **The price.** A request waits for the PC: up to two hours on the mirror tick, or less with its own task.
- **The alternative.** Generation in edge functions would duplicate the pipeline and its cost controls, and make a second writer. It is not proposed.

**Defaults taken for R1-R4, unless you say otherwise.**
1. Requests run on the desk (above).
2. A researcher's cost-bearing request needs one approval, by an admin or the super admin. An admin's own request needs none, but stays inside the caps.
3. A daily cap for requests, inside the desk's live budget. Its value is set at R2, from the ledger's prices.
4. The person who asked sees the draft their own request produced. Other readers see it only after approval.

## 4. Guardrails kept

- **SQL.** Privileged SQL only in the Lovable Cloud SQL editor, one block per paste, with read-only checks before and after. Nothing goes in `supabase/migrations` and no history rows are added (S1/S2 precedent).
- **Edge functions.** Deployed by Lovable "as is".
- **The secret.** `CORPUS_SYNC_SECRET` stays in `.env` and Lovable Secrets only. It is never printed or read back.
- **context.db.** Read-only, by the desk scripts only. No VACUUM. A backup first (`db_backup.py`).
- **Patches.** Anchored, all-or-nothing, marker-idempotent, md5-guarded, with backups `.bak_<tag>_<date>` and `--check` first.
- **Repos.** You push each repo by hand. Srangam `git add` lists explicit paths, never `bun.lock` or `*.bak_*`.
- **Pictures.**
  - No picture is public.
  - Generated pictures carry "Illustration - generated, not a historical source."
  - No beneficiary PII is involved. The pictures are of the texts only.

## 5. Rollback

- **Site.** Each replaced or edited Srangam file has `.bak_media_<date>` next to it. The new files can be removed. Without C8, the pages fall back quietly.
- **Function.** Ask Lovable to delete `corpus-media`. The site then shows "not available".
- **Database.** The DROP list in the header of C8. The files stay on Drive; delete the folder "Srangam corpus media" there if wanted.
- **Schedule.** `scripts/corpus_mirror_task.ps1.bak_mediatask_<date>`.
