# Operating model: corpus, editions, site (2026-09-27)

Marker `OPERATING_MODEL_2026_09_27`. This page is the map of what feeds what, how
often, and who presses the button. Every statement below was checked against
files on this machine on 2026-09-27. Anything that could not be checked from
here is marked **not verified**.

## 1. Systems and their single source of truth

| System | Lives in | Source of truth for | Git (local = origin, 2026-09-27) |
|---|---|---|---|
| Sanskrit Automaton | `D:\Sanksrit Automatons\sanskrit-automatonv2` | passages, English (`passages.translation`), Hindi (`translations_l10n`), the outcome ledger (`data/translate_outcomes.jsonl`), display titles (`configs/doc_titles.json`) | `1ba4e5c` = origin/main |
| Srangam Hub | `D:\Sanksrit Automatons\srangam-hub` | the launcher and health page (:5050) | `7c95ee3` = origin/main |
| Booksmith | `D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith` | printed and audit editions, human review findings | `60dcffb` = origin/main |
| Srangam site | `D:\srangam-42267` (Lovable + Supabase) | articles, and the public copy of published texts | local `80fa530` = the origin ref as last fetched **on 2026-09-12**. Lovable commits to GitHub directly, so origin may be ahead: **not verified** from here (block BD fetches it). |
| Register | `D:\sanskrit-symphony` | where everything is (`SOURCES_OF_TRUTH.md`) | `d0f1ea1` = origin/main |

`context.db` is the only writable corpus. `query_snapshot.db` (Datasette) is a
copy made on demand. Supabase `srangam_texts` / `srangam_text_passages` are a
published copy that is **never** edited by hand except for `title` and
`published`.

## 2. The four flows out of the corpus

| Flow | Mechanism | Cadence before today | Cadence from today |
|---|---|---|---|
| Corpus to Booksmith editions | `booksmith_build.py --mode tri / hi` (block BA `-Rebuild`) | after a document's jobs finish | unchanged. Routine 3h, step 3 |
| Corpus to Srangam texts | `publish_srangam.py --emit-sql` → paste in the Lovable SQL editor (no service key, by rule) | once (Aphorisms, 439 passages, published 2026-09-27) | per document, after its review. Re-paste after retries (idempotent, keeps `published` and the site title) |
| Corpus to the Srangam **status panel** | `srangam-42267/scripts/emit_project_status.py` → `src/data/projectStatus.ts` → commit → Lovable Publish | **once, 2026-09-12.** It appeared in no runbook, so the panel was 15 days stale | routine 3h, step 5 (block BD `-Emit -Commit`), after every translate sweep and at least weekly |
| Srangam site to GitHub | Lovable commits to `main`; the local clone must pull before it pushes | ad hoc | block BD fetches first and refuses to commit on divergence |

The status panel is a generated file, not a live query, by design. The site has
no key to the local database, and the file's own rule is "no number enters this
file without a command that produced it". "Up to date" therefore means "the
routine was run".

## 3. What was wrong on 2026-09-27, and what fixes it

| Found (evidence) | Fix | Marker |
|---|---|---|
| The panel said "MBh01 complete at 100%" (Lovable issue report) | curated titles in `configs/doc_titles.json`; an unknown code stays a code, nothing is invented | STATUS_TRUTH_2026_09_27 |
| The panel said "zero came back empty or as a refusal … not yet established". The ledger now shows 70+ unusable answers, none stored | caveat measured from the ledger, dated | STATUS_TRUTH_2026_09_27 |
| The panel said "nothing is loaded". One text of 439 passages is published (`99_verify.sql`) | `SITE_CORPUS`, measured in the SQL editor and dated, like `CONTAMINATION` | STATUS_TRUTH_2026_09_27 |
| The generator opened `context.db` with `immutable=1`, which never reads the `-wal` file. Rows not yet checkpointed were not counted (reproduced: 1 of 501 rows seen) | `mode=ro` + `query_only` | STATUS_TRUTH_2026_09_27 |
| A second `dashboard.py` (pid 21432, 15:05) was running beside the queue holder (pid 41088, 14:53) | dashboard refuses to start on a taken port; the hub also checks the port by TCP | SINGLE_INSTANCE / HUB_SINGLE_2026_09_27 |
| One network drop held the only translate lane for 33 min (15:14 → 15:48, then killed). The SDK waits 600 s per call × 3 retries | `request_options={"timeout": MT_REQUEST_TIMEOUT}` (120 s) | MT_TIMEOUT_2026_09_27 |
| The queue died at 14:46:42 (rc `0xC000013A`: the console was closed or got Ctrl+C) | rule in RUNBOOK 3h; the plan rebuilds the queue from the database | RUNBOOK_OPS_2026_09_27 |
| Verses the model can only call illegible were paid for on every plan | parking after 2 identical answers; listed as re-OCR work | PARK_ILLEGIBLE_2026_09_27 |

## 4. Guardrails (unchanged, restated)

- **Keys:** no service-role key on this machine. Privileged Supabase SQL goes through the Lovable Cloud SQL editor only.
- **Dashboard:** one only. Never restart it while jobs are queued, because the queue lives in its memory.
- **Git:** run by you, from PowerShell blocks, never through the device bridge.
- **Before writes:**
  - back up first;
  - never `VACUUM`;
  - never `purge_empty_cache.py --yes`;
  - never hand-edit `translations_l10n`.
- **Patches:**
  - anchored, all-or-nothing and marker-idempotent;
  - backups kept, atomic replace;
  - tests fail before the patch and pass after, or the block rolls back.
- **Translation route:** Hindi is translated from Sanskrit directly. English is only a reference, and only when it passed QA.

## 5. Path forward

**Phase 1 - stability (2026-09-27, in progress)**

- Parking, titles and the SQL bridge are committed (`1ba4e5c`).
- Single instance, bounded model calls and status truth: block BD.
- The 35-job retry queue drains. Then rebuild the Aphorisms and Shatpath editions, refresh the snapshot, re-emit Aphorisms SQL, and refresh the status.

**Phase 2 - the site shows the corpus (needs Lovable-side decisions)**

1. **Reader page.** `src/lib/corpusTexts.ts` and its tests already read `srangam_texts` / `srangam_text_passages`, but no route uses it. A `/texts` and `/texts/:doc_code` page is a Lovable prompt, not a schema change.
2. **Hindi on the site.** This needs a new migration: either a `translation_hi` column, or a `srangam_text_passages_l10n` table mirroring `translations_l10n`. It also needs `prompt_version` columns. `publish_srangam.py --emit-sql` would then carry Hindi. Recommended: the l10n table, because it matches the corpus shape.
3. **Titles.** `publish_srangam.py` should read `configs/doc_titles.json` before Booksmith `book.yaml`, so that one file names a work everywhere.
4. **Migration history.** `supabase_migrations.schema_migrations` has no row for `20260718120000`. Record it through the SQL editor after checking what the Lovable migration runner expects. **Not verified**: whether Lovable re-applies migrations without a history row.

**Phase 3 - quality work the numbers now point at**

- **Re-OCR worklist.** Take the planner's parked list (after the queue: Bodhicaryavatara, Karan_Aagama, Shatpath) and run it through RUNBOOK §3b / §3f. Re-OCR'd text un-parks itself.
- **Human review.** The 28 trilingual and 24 Hindi Booksmith findings, and the 86-passage blinded draw.
- **Datasette canned queries.** Move `docs/DATASETTE_QUERIES.sql` into Datasette's own query config. Check `datasette --version` first: 0.x takes `-m metadata.json`, 1.x takes `-c datasette.yaml`.

**Phase 4 - automation, only after two clean weeks of the manual routine**

- A Windows scheduled task for `plan_empty_retries` (read-only) and `emit_project_status.py --check`, both reporting drift only.
- Nothing that writes or commits runs unattended until the manual runs have stayed clean.
