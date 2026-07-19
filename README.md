# Sanskrit Automaton v2

Local-first pipeline for Sanskrit OCR, normalization, and AI-assisted translation.
Processes scanned PDFs → Sanskrit text → English translation → HTML export.

> See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, API reference, and DB schema.

---

## Quick Start

```bat
REM 1. Copy .env.example to .env and fill in API keys
copy .env.example .env

REM 2. Install dependencies
pip install -r requirements.txt

REM 3. Start the dashboard
run.bat
```

Open **http://localhost:5057** in your browser.

---

## Prerequisites

- Python 3.10+
- Tesseract OCR (`tesseract` on PATH) with Sanskrit + Hindi language packs
- Gemini API key (`GEMINI_API_KEY`) and/or OpenAI API key (`OPENAI_API_KEY`) in `.env`
- `SA_SAFE_MODE=1` in `.env` (must remain set)

---

## Project Layout

```
sanskrit-automatonv2/
├── run.bat                          # Start Flask server
├── .env                             # API keys (never committed)
├── .env.example                     # Template
├── requirements.txt
├── ARCHITECTURE.md                  # System design, API routes, DB schema
│
├── scripts/
│   ├── dashboard.py                 # Flask server (port 5057) — all API routes
│   ├── dashboard_static.html        # Single-file SPA (the UI)
│   ├── pipeline_queue.py            # Full pipeline runner (OCR→Ingest→Translate→Export)
│   ├── advance_pipeline.py          # Batch translate all OCR'd docs
│   ├── ocr_pdf.py                   # Tesseract OCR → JSONL
│   ├── ingest_jsonl_fast.py         # JSONL → SQLite passages
│   ├── translate_passages.py        # Translate passages via LLM
│   ├── infer_mt.py                  # LLM inference (Gemini / OpenAI)
│   ├── export_html.py               # passages → HTML translation
│   ├── cost_tracker.py              # Budget tracking
│   └── …                           # Other utilities
│
├── data/
│   ├── context.db                   # SQLite — docs + passages + translations
│   ├── jobs.jsonl                   # Job history (append-only)
│   ├── translation_progress.json    # Live progress (written during translate runs)
│   ├── raw/                         # OCR output (*.jsonl)
│   └── exports/                     # HTML translation outputs
│
└── inbox/                           # PDFs staged for processing (DocName_NNNN.pdf)
```

---

## Pipeline

```
PDF corpus (D: drive)
      ↓  [Import via corpus browser]
inbox/DocName_NNNN.pdf
      ↓  [OCR]
data/raw/DocName_NNNN.jsonl
      ↓  [Ingest]
context.db → passages table
      ↓  [Translate]
passages.translation (Gemini 2.5 Flash by default)
      ↓  [Export]
data/exports/DocName_translation.html
```

Use the **⚡ Import & Run Pipeline** button in the corpus browser sidebar to run all steps
for a new document in one click.

---

## Translation Engines

Select globally in the top-bar engine dropdown, or per-document via the row-level dropdown
in the pipeline table:

| Engine | Speed | Quality | Cost |
|---|---|---|---|
| Gemini 2.5 Flash | Fast | Good | Cheapest |
| Gemini 2.5 Pro | Slow | Excellent | ~10× Flash |
| GPT-4o-mini | Fast | Good | Low |
| GPT-4o | Slow | Excellent | High |

**Recommended**: Flash for bulk corpus; Pro for priority texts set via per-doc dropdown.

---

## Security Notes

- `.env` is in `.gitignore` — never commit API keys
- `SA_SAFE_MODE=1` must remain set to prevent destructive bulk operations
- The server binds to `127.0.0.1:5057` (localhost only)
