# Architecture — Sanskrit Automaton v2

## Overview

A Windows-native, local-first pipeline for Sanskrit OCR, normalization, and AI translation.
The entire system runs on a single machine: Flask server, SQLite DB, local GPU/CPU OCR, and
LLM translation via API keys (Gemini / OpenAI).

```
Browser  ←→  Flask (port 5057)  ←→  SQLite (data/context.db)
                    │
                    ├─ Tesseract OCR  (ocr_pdf.py)
                    ├─ JSONL ingest   (ingest_jsonl_fast.py)
                    ├─ Translation    (translate_passages.py + infer_mt.py)
                    └─ HTML export    (export_html.py)
```

---

## Entry Points

| File | Purpose |
|---|---|
| `run.bat` | Start Flask server (`python scripts/dashboard.py`) |
| `scripts/dashboard.py` | Flask app — all API routes + job management |
| `scripts/dashboard_static.html` | Single-file SPA served at `/` |

**Do not start multiple Flask instances** — the in-memory `JOBS` dict and `JOBS_LOCK` are
process-local; job state would split across instances.

---

## Database (`data/context.db`)

Schema family: **`join_docs`** — passages reference docs via FK.

```sql
docs        id, code, title, category, source_path, …
passages    id, doc_id→docs.id, page_no, idx, text, translation, quality_score, …
```

Key constraints:
- `passages.translation` column (NOT `english` — older schema used that name)
- `passages.doc_id` is a FK to `docs.id` (not `docs.code`)
- Category is stored in `docs.category`; NULL category means doc won't appear in corpus stats

Cost/budget tables: `budget_state`, `usage_log`, `usage_totals` (managed by `cost_tracker.py`).

---

## Pipeline Steps

Each step is a standalone script, called as a subprocess by `dashboard.py`:

```
1. OCR      scripts/ocr_pdf.py          inbox/DocName_NNNN.pdf → data/raw/DocName_NNNN.jsonl
2. Ingest   scripts/ingest_jsonl_fast.py data/raw/ → passages rows in context.db
3. Translate scripts/translate_passages.py context.db passages → translation column
4. Export   scripts/export_html.py       context.db → exports/DocName_translation.html
```

Full pipeline (serial, one doc): `scripts/pipeline_queue.py`
Batch translation (all OCR'd docs in priority order): `scripts/advance_pipeline.py`

### Translation engine string format

```
gemini:gemini-2.5-flash    ← default (fastest, cheapest)
gemini:gemini-2.5-pro      ← highest quality
openai:gpt-4o
openai:gpt-4o-mini
echo                       ← test mode (no API calls)
```

Set globally in the UI engine selector, or per-doc via the row-level engine dropdown.

---

## Job System

Jobs are Python threads, tracked in the in-memory `JOBS: dict` (protected by `JOBS_LOCK`).
On startup, running jobs from `data/jobs.jsonl` are NOT restarted (they were killed when the
server stopped). `jobs.jsonl` is append-only and used only for history display.

API: `GET /api/job/<jid>` returns `{running, ok, out, err}`.
Kill: `POST /api/job/<jid>/kill` sends `SIGTERM` to the subprocess.

---

## API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serve `dashboard_static.html` |
| GET | `/api/status` | Pipeline table rows (per-doc progress) |
| GET | `/api/corpus` | D: drive corpus tree (60s cache) |
| POST | `/api/corpus/import` | Copy PDFs into inbox/ |
| GET | `/api/job/<jid>` | Job status + stdout tail |
| POST | `/api/job/<jid>/kill` | Kill running job |
| POST | `/api/jobs/kill_all` | Kill all running jobs |
| GET | `/api/jobs/running` | List active jobs |
| GET | `/api/jobs/history` | Last N completed jobs |
| POST | `/api/doc/<doc>/stop` | Stop all jobs for a doc |
| GET | `/api/progress` | Live translation progress (from `data/translation_progress.json`) |
| GET | `/api/usage` | Cost/usage summary |
| GET/POST | `/api/budget` | Budget cap management |
| POST | `/api/ocr` | Launch OCR job |
| POST | `/api/ingest` | Launch ingest job |
| POST | `/api/translate` | Launch translate job |
| POST | `/api/export` | Launch export job |
| POST | `/api/queue/run` | Launch full pipeline job |
| POST | `/api/pipeline/translate-doc` | Translate a single doc (queue aware) |
| POST | `/api/pipeline/advance` | Advance all OCR'd docs |
| GET | `/api/passages/<doc>` | Passage list for reader/queue view |
| GET | `/api/queue/<doc>` | Queue stats for a doc |
| POST | `/api/queue/<doc>/skip` | Mark low-quality passages as skipped |
| GET | `/reader/<doc>` | Scholarly reader HTML |

---

## Configuration

`.env` (never committed — in `.gitignore`):
```
OPENAI_API_KEY=sk-…
GEMINI_API_KEY=AIza…
SA_SAFE_MODE=1
```

`SA_SAFE_MODE=1` must remain set — disables destructive bulk operations.

`data/translation_config.json` — per-doc skip lists (`skip_rowids`), quality thresholds.

---

## Corpus Browser

The sidebar scans `CORPUS_ROOT` (default: `D:/`) for `*.pdf` files under category subdirectories.
Results are cached in-memory for 60 seconds to avoid hammering Google Drive sync.
Cache is invalidated immediately after a successful `/api/corpus/import`.

---

## Key Constraints / Gotchas

- **bindfs mount**: `.git/index.lock` cannot be `unlink()`ed — must `os.rename()` it.
  All git operations in the dev environment need lock-clearing first.
- **Edit tool truncation**: The file editor truncates files >~1000 lines when inserting large
  blocks. Use Python `open().write()` for large file rewrites in this repo.
- **Schema**: Always use `passages.translation` (not `passages.english`).
  Always join `passages.doc_id → docs.id` (not `docs.code`).
- **Job state**: `JOBS` is in-memory only. Server restart loses all running job handles;
  orphaned subprocesses must be killed manually if they survive.
- **Translation progress**: `data/translation_progress.json` is written by
  `translate_passages.py` during a run. Deleted on job completion.

---

## Translation Cost Estimates (June 2026)

| Engine | Cost per 1K passages | 10,763 remaining |
|---|---|---|
| Gemini 2.5 Flash | ~$0.05 | ~$0.54 |
| Gemini 2.5 Pro | ~$0.50 | ~$5–7 |
| GPT-4o-mini | ~$0.08 | ~$0.86 |

**Recommended strategy**: Flash for bulk; Pro for high-priority texts (Natya Shastra,
core Mahabharata books) set via per-doc engine dropdown in the dashboard.

Budget cap: currently $8.00 ($0.93 spent, $7.07 remaining as of audit).

---

## Corrections & additions since 2026-08 (reconciliation, 2026-08-27)

This file predates the Phase-Q and Phase-HI work. Corrections:

- **`docs` has NO `title` column.** Code must use `COALESCE(d.title, d.code)` only after
  checking the column exists, or just `d.code` (the `/library` crash was this). The line
  above showing `docs … title …` is aspirational, not current.
- **Two quality columns, two axes.** `passages.quality_score` is the **source**
  Devanagari/OCR gate (skip < 0.35). Translation quality is `passages.translation_qa`
  (Phase-Q scorer, `qa_scan.py`). Do not conflate them.
- **Provenance columns exist on `passages`:** `engine`, `mt_prompt_version`,
  `translated_at`, plus `translation_qa` (see `QUALITY_LOOP_DESIGN`).
- **Hindi track added:** table `translations_l10n(passage_id, lang, translation, engine,
  mt_prompt_version, translation_qa, translated_at, UNIQUE(passage_id,lang))`;
  `translation_history` gained a `lang` column. Hindi is translated DIRECTLY sa→hi with
  QA-passed English as a meaning reference (see `HINDI_TRACK_DESIGN`).
- **Also present now:** `passage_embeddings` (semantic search), `entities` /
  `entity_variants` / `entity_mentions` / `footnotes` (entity layer), `passages_fts` (FTS5),
  `translation_history`, `mt_cache`.
- **Concurrency:** OCR uses a 2-slot semaphore (parallel with translation); all
  translate/heal/pipeline jobs share ONE translate semaphore (single SQLite writer). The
  pipeline now runs OCR under the OCR lock, then chains ingest+translate (see RUNBOOK §2).
- **DB connection hygiene:** `db_utils.connect()` sets WAL + `busy_timeout=30000`; some raw
  `sqlite3.connect()` sites default to 5s — unify at the next restart (ROADMAP Phase 1).
- **Storage reality:** `context.db` (~419 MB) is on a LOCAL fixed NTFS disk (not a
  Drive/stream mount); no sync client covers the folder. WAL is safe locally.
- **System context:** this repo is the `automaton/` sibling of the `sanskrit-symphony`
  monorepo (`hub`, `panchang`, `wisdomlib`); a live Srangam site (Lovable + Supabase) is
  fed by `publish_srangam.py`.
- **The genuine open item** is Q4 (sampled LLM-judge, `judge_sample.py` + `mt_reviews`) —
  semantic fidelity certification. Designed in `QUALITY_LOOP_DESIGN`, not yet built.

## The genealogies' road (DOCS122_2026_11_18, 18 Nov 2026)

How the lines of kings travel from the Sanskrit verses to the desk and to the site. Only the first step spends, and step 7 (our findings, DOCS124_2026_11_19) after it.

| Step | Where | Reads | Writes | Cost |
|---|---|---|---|---|
| 1. Read | scripts\vamsa_read.py (G5a, G6a, G6b) | the genealogical chapters of 17 works on this PC (vip4, vipc4, bhp9, bhp12, hv, ram1, ram2, mbh1, matsya, brahma, bndp1, bndp2, linga1, kurma1, garuda1, agni, markp) | data\vamsa_read\<work>\*.json: kinship statements, each checked by machine against its verse (verified, words, unsupported, bad) | paid: Claude Sonnet (claude-sonnet-5-5), prompt vamsa-read-v1 for vip4, bhp9, bhp12 and v2 for the rest; 323 calls, $11.19 to 18 Nov; a run resumes where it stopped |
| 2. Align | scripts\vamsa_align.py (G6c) | step 1 | exports\vamsa_align.md and .csv; data\vamsa_read\aligned.json | free |
| 3. Register | scripts\vamsa_register.py (G6d; VAMSA_NAMES) | steps 1 and 2 | data\vamsa_read\register.json; exports\vamsa_register.csv and .md | free |
| 4. Join | scripts\vamsa_join.py (G5b; VAMSA_SITE) | step 1; data\shelf\kin.db (the Purana Index, kin_index.py); data\context.db | data\vamsa_read\dynasties.json (vip4, bhp9, bhp12), dynasties_every.json (--work every) | free |
| 5. Send | scripts\index_sync.py --dynasty-works every; nightly from scripts\corpus_mirror_task.ps1 | step 4 and the indexes (kin.db, vamsa.db, claims.db) | Srangam's corpus.index_* tables through the edge function corpus-index (the dynasties in corpus.index_dynasties, docs\cloud\C28; the vamsas in corpus.index_vamsas, C29); only rows whose row_hash changed | free |
| 6. Show, site | public.corpus_reader_index_dynasties(p_work), behind corpus._reader_gate; /corpus/genealogies/dynasties asks for one work at a time (Srangam's DYNASTIES_WORKS_2026_11_18) | step 5 | nothing | free |
| 6. Show, site, by vamsa | public.corpus_reader_index_vamsas(p_key) (C29), behind corpus._reader_gate: the list without generations, one dynasty with them; /corpus/genealogies/vamsas (Srangam's VAMSA_WAYIN_2026_11_18, DOCS123_2026_11_18) | step 5's vamsas: G6c's aligned.json (step 2), each name tied to its line of step 4, Dikshitar's person and Raychaudhuri's claims the site carries | nothing | free |
| 6. Show, desk | /vamsa (scripts\vamsa.html; /api/vamsa through scripts\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |
| 7. Our findings (R1) | scripts\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6's vamsas (generations, verses, Dikshitar, Raychaudhuri's claims on the site); B. C. Law's claims in claims.db, for the model only | data\vamsa_findings\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |
| 8. Watch, admin | public.corpus_admin_status() (C30, the super admin only, read-only); /admin/desk-site (Srangam's ADMIN_STATUS_2026_11_19, DOCS125_2026_11_19) | the mirror's runs, the index tables, the desk's worker, who may read, srangam_ai_usage | nothing | free |

The rules of the road:
- The site shows what the desk last sent: on 18 Nov, 17 works and 517 rows. Every send carries --dynasty-works every
  (the nightly task does since VAMSA_EVERY_2026_11_18); a send without it takes the 14 works of G6 off the site.
- Who may read on the site: corpus_reader_allowed() (admins and super admins; corpus.reader_access's mode, "readers"
  since 9 Oct: the listed readers and researchers). The public may not; changing that is the owner's decision.
- What is shown is what the texts state, each step with its verse. A join of two works' persons is ours (one name, one
  father and, where both give him, one grandfather); a second name only where a verse says it; names that differ are
  shown side by side, never ruled on.
- G6c's aligned.json is written by vamsa_align.py: run it after a new reading, before the send (DOCS123_2026_11_18).
- A scholar's claim is shown only when the site carries it already (C23's rule: the public-domain works, the quotation
  found on the page); B. C. Law's book (in copyright) never; what we find with it comes as our own findings (R1).
- Not yet on the road: the approved findings on the vamsa page (C30, once a person has approved some), Raychaudhuri
  beside each step of the per-work page (P2d); the 17 works on the desk's /vamsa page (P3); a review list for the
  proposed names and the names kept apart (P4).
