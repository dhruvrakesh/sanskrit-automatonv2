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
