# Why a book can stop between stages, and the plan to make that impossible (2026-09-30)

Marker `PIPELINE_STATE_2026_09_30`. The evidence below was read on 2026-09-30 from
`inbox/`, `data/raw/`, `data/jobs.jsonl`, `scripts/dashboard.py`,
`scripts/dashboard_static.html`, `ARCHITECTURE.md`, `ENTERPRISE_ROADMAP.md`,
`README.md` and `STEPS_TO_RUN.md`. Database counts come from
`scripts/pipeline_inventory.py`, which is read-only.

## 1. What happened to Mallapurana

The book was imported five times on 2026-09-29, at 11:37, 11:38, 11:41, 11:42 and 17:57:

- three times by **Upload** (`/api/upload`);
- twice by **Add from disk** (`/api/import_path`).

All five splits succeeded (137/137 pages each time). No OCR job was ever created for it. There is no `data/manifests/ocr_Mallapurana.txt` and no `data/raw/Mallapurana_*.jsonl`.

## 2. Root causes (design, not a single bug)

1. **Three entry points with different meanings for "add a book".**

   | Entry point | Endpoint | What it does |
   |---|---|---|
   | Corpus browser, **Import & Run Pipeline** | `/api/corpus/import`, then `/api/queue/run` | split, then OCR, ingest and translate |
   | Corpus browser, **Import** | `/api/corpus/import` | split only |
   | **Upload** (file picker) | `/api/upload` | split only |
   | **Add from disk** | `/api/import_path` | split only |

   Only one path continues past the split, and it works only for files under `CORPUS_ROOT`. A file anywhere else can only take a split-only path. `ARCHITECTURE.md` lists only `/api/corpus/import`; `README.md` describes Add from disk without saying that it does not OCR.

2. **The only split → OCR chain lives in the browser.**
   - `_waitSplitThenRun()` in `dashboard_static.html` polls `/api/job/<id>` every 2 s and then calls `/api/queue/run`. Close or reload the tab, or restart the dashboard, and the chain is gone.
   - The server already has durable-enough chaining for OCR → ingest (`launch(..., then=_launch_rest)` in `/api/queue/run`), but `_do_import()` launches the split with no `then`.

3. **Nothing derives or shows a book's pipeline state.**
   - `JOBS` lives in memory (`ARCHITECTURE.md`: "Server restart loses all running job handles"). `jobs.jsonl` is history only.
   - `/library` lists only documents in `context.db`. A book that is split but not OCR'd appears only as a row in the pipeline table (for Mallapurana: 137 PDFs, OCR 0), and no screen says it is stranded.
   - The roadmap (2026-08-26) covers the database, concurrency and quality; it never covers pipeline state.

4. **The same pattern is older than Mallapurana.** On 2026-09-30, 10 books had pages in `inbox/` with no OCR output (run `pipeline_inventory.py` for the live list):
   - `gandharva_veda_natya_shastra`: 507 pages, split 2026-06-14, never OCR'd.
   - `476948-Rgveda-samhita_Vol-ii`: 18 of 1,064 pages OCR'd. Four OCR attempts failed (2026-08-26 to 08-29), all before the manifest fix for the Windows command-line length limit.
   - `yajur_veda_taittiriya_krishna_yajur_veda` 12/496, `upapurana_saura_purana` 11/289, `upapurana_samba_purana` 11/241 and `upapurana_parashara_purana` 10/72. Each was split 2026-06-14, and on 2026-08-18 an ingest loaded only the OCR'd pages.
   - Three one-page items (`sharada_tilaka_tantra_ii`, `siddhanta_shiromani`, `Surya_Siddhanta…`).

   The coverage figures on the Srangam status panel are computed from `context.db` only. These pages never reached it, so they are not counted anywhere.

Two further failures from the same week have the same root. The queue was lost on a console close (2026-09-27, twice), and the status panel was 15 days stale. In each case progress depended on a person, a browser tab or a console window carrying state from one step to the next.

## 3. Design principle for the fix

**Derive state from the artifacts; persist only intent.**

- The files and the database already record exactly how far each book got: `inbox` pages, `raw` JSONL, `passages`, translations. Recording the same facts again in a second store would drift from them. So a book's stage is computed, not stored (`pipeline_inventory.py`).
- The one thing that is not recoverable from artifacts is **intent**: "the user asked for this book to go all the way". Only that is persisted, in an append-only `data/pipeline_intents.jsonl`. The dashboard re-reads it at start-up, so a restart resumes work instead of forgetting it.

## 4. Phases (surgical, each reversible, each at a controlled moment)

**Phase 0 — measure (read-only; delivered).**
`scripts/pipeline_inventory.py` gives one row per book, showing its stage, whether it is stuck and why. The last attempt of each step comes from `jobs.jsonl`.

**Phase 1 — one server-side import, chained on the server.**
- `_do_import()` accepts `run: "none" | "ocr" | "all"` and launches the split with `then=` the same OCR → ingest (→ translate) chain `/api/queue/run` already uses. The `then=` machinery in `launch()` is unchanged.
- Upload, Add from disk and the corpus browser all send the same choice, from one "after import" selector (default: OCR + ingest, no translation, so spending stays a decision).
- `_waitSplitThenRun()` is kept as a no-op fallback for one release, then removed.
- Tests: each of the three endpoints, with `run=ocr`, schedules OCR on split success, and none does with `run=none`.
- Takes effect at the next dashboard restart, with the queue empty.

**Phase 2 — intents survive restarts.**
- Append `{doc, run, requested_at}` to `data/pipeline_intents.jsonl` on import and on "Run pipeline".
- At start-up the dashboard re-derives each intended book's stage (Phase 0 logic) and re-launches only the missing step.
- The retry queue gets the same treatment. Queued translate jobs become intents, so the lost-on-close queue (27 Sep) cannot recur. Today `block_BA -Queue` rebuilds that queue by hand.
- Tests: kill the dashboard mid-queue, restart it, and check that the same work is re-queued once, not twice.

**Phase 3 — the UI says where each book is.**
- The pipeline table gets a Stage column (split / OCR x/N / ingested / translated) and a "Stuck: why" line.
- `/library` gets an "In progress" group for books not yet in the database, with a Continue button that calls the Phase 1 chain.
- The import toast says what will happen next ("split 137 pages; OCR queued"), never just "done".

**Phase 4 — documentation and operations.**
- `ARCHITECTURE.md`: all import endpoints and the state model.
- `README.md` and `STEPS_TO_RUN.md`: one "add a book" procedure.
- `RUNBOOK.md` routine 3h gains `pipeline_inventory.py`.
- The Srangam status generator reports stranded pages, so public coverage figures stop implying the pipeline has seen every page.

**Stranded books (operator decision, per book).** Each book is re-OCR'd by its own Continue or `/api/queue/run` call, not in bulk. Several were ingested from only their first pages, and a full OCR changes their passage set. Each one is reviewed with `pipeline_inventory.py` and a Datasette look before it is resumed.

## 5. Inventory results (run on this machine, 2026-09-30 13:37; `inventory_20260930.json`)

The inventory covered 68 books: 15 translated, 27 translating, 9 ingested and not translated, and 17 marked stuck. Reading the rows one by one sorts the stuck books into five kinds of failure. Each needs a different decision.

| Kind | Books (from the inventory) | What it means |
|---|---|---|
| **Split, never OCR'd** | Mallapurana 137, gandharva_veda_natya_shastra 507, 3 one-page items | the gap described in section 2 |
| **OCR stopped part-way** | Rgveda Vol II 18/1064 (4 failed attempts, Aug 26-29), yajur_veda_taittiriya 12/496, upapurana saura 11/289, samba 11/241, parashara 10/72 | OCR was never resumed; ingest ran on the pages that existed |
| **OCR finished, never ingested** | sama_veda_sama_veda 257, dhanur_veda_niti_prakashika 44 | standalone OCR does not chain to ingest |
| **Ingested before OCR finished** | upapurana_narasimha_purana (309 OCR pages, 12 in the database), SP_4214 Pataal Khanda (364 / 280) | ingest is never re-run when more OCR pages appear |
| **Same work under two codes** (legacy) | smriti_14manu_smriti (208 page-sized passages) and smriti_14manu_smriti_seg (2,568); smriti_16harita_smriti and _seg; upapurana_nilamata_purana and nilamata_seg; dhanur_veda_vasishtha_dhanur_veda and vasishtha_dhanur_veda; dhanur_veda_shiva_dhanur_veda and shiva_dhanur_veda (both translated) | the first inventory reported these as stranded; v2 recognises them as aliases |

Separately, 2015_368408_Natyasastra-With (2,916 live passages) and SP_4214 (15,111) were ingested and never translated. The retry planner queues only verses a previous run went past, so books that have never been started are never queued. That is a policy decision, not a fault.

**Corrections in v2 of `pipeline_inventory.py`:**
- An empty book no longer counts as 1 live passage (a LEFT JOIN artefact).
- Aliases are matched on the distinctive tokens of the code **and** an equal OCR page count. They are reported, never merged.
- An ingested book whose passages are page-sized (at most one per page, average over 600 characters) is flagged as not verse-segmented.
