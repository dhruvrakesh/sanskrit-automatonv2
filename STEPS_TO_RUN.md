# Sanskrit Automaton v2 — How to Run

## Quick start (recommended)

```cmd
cd D:\Sanksrit Automatons\sanskrit-automatonv2
run.bat
```

This starts two servers and opens the dashboard in your browser:
- **Dashboard** → http://127.0.0.1:5057/
- **Export API** → http://127.0.0.1:8000/

---

## Prerequisites

| Tool | Install |
|------|---------|
| Python 3.10+ | https://python.org |
| Tesseract OCR | https://github.com/UB-Mannheim/tesseract/wiki — install `san`, `hin`, `eng` tessdata |
| Poppler | https://github.com/oschwartz10612/poppler-windows/releases — put `bin` on PATH |
| Pip packages | `pip install -r requirements.txt` |

---

## Environment (.env)

Create `.env` in the project root (never committed to git):

```env
GEMINI_API_KEY=your-gemini-key-here
OPENAI_API_KEY=sk-your-openai-key-here   # optional
MT_ENGINE=gemini:gemini-2.5-flash         # default engine
```

**Default engine is Gemini 2.5 Flash** — best cost/quality ratio ($0.15/M in, $0.60/M out).
Switch to `gemini:gemini-2.5-pro` for highest quality or `openai:gpt-4o-mini` as fallback.

---

## Dashboard walkthrough

1. **Add PDFs** to `inbox/`. Name them `DocCode_0001.pdf`, `DocCode_0002.pdf`, etc.
2. **OCR** — click OCR in the pipeline table → Tesseract runs, writes JSONL to `data/raw/`.
3. **Ingest** — loads the doc's JSONL into `data/context.db`, segments into verses.
4. **Translate** — sends up to 50 untranslated passages to the MT engine (5-verse context window). Passages with OCR quality < 25% are skipped automatically.
5. **Live▶ tab** — shows the current verse being translated, progress bar, quality badge, recent 10 verses side-by-side (Sanskrit / English).
6. **Queue tab** — pick a doc, see its pending passages with quality scores; skip individual rows or bulk-skip anything below 25% quality. Skips are written to `data/translation_config.json` and take effect immediately.
7. **Export** — writes HTML to `exports/`.

---

## Advance all docs (batch mode)

```cmd
python scripts\advance_pipeline.py
```

Processes all 22 OCR'd docs in priority order (nirukta → shiksha → puranas → vedas → bauddha). Each doc goes through Ingest → Translate → Export. Ctrl+C pauses safely. Uses Gemini 2.5 Flash with 0.25 quality threshold and 5-verse context window.

---

## Key files

| File | Purpose |
|------|---------|
| `scripts/dashboard.py` | Flask dashboard server (port 5057) |
| `scripts/dashboard_static.html` | Dashboard UI (served by Flask, all features) |
| `scripts/translate_passages.py` | Core MT loop — calls Gemini/OpenAI, writes progress |
| `scripts/infer_mt.py` | MT engine dispatch (Gemini + OpenAI, caching) |
| `scripts/ingest_jsonl_fast.py` | Ingests OCR JSONL into SQLite, verse segmentation |
| `scripts/advance_pipeline.py` | Batch runner for all docs |
| `scripts/cost_tracker.py` | Budget tracking, usage logging |
| `scripts/db_utils.py` | SQLite schema + safe migrations |
| `data/context.db` | Main SQLite DB (not committed) |
| `data/translation_progress.json` | Live progress state (written by translate_passages.py, polled by dashboard every 2s) |
| `data/translation_config.json` | Runtime config — pause flag, skip_rowids, engine override |
| `run.bat` | One-click launcher |
| `.env` | API keys and MT_ENGINE setting (never committed) |

---

## Cost tracking

Budget ceiling: **$8.00** (edit in dashboard via Usage tab or `data/context.db` → `budget_state`).
Current spend: ~$0.93. The pipeline auto-pauses when budget is reached.

---

## Command-line reference

### OCR one page
```cmd
python scripts\ocr_pdf.py --pdf inbox\MyDoc_0001.pdf --out data\raw\MyDoc_0001.jsonl --dpi 400 --lang-tries san+hin+eng san hin eng
```

### Ingest a doc
```cmd
python scripts\ingest_jsonl_fast.py --doc MyDoc --glob "data/raw/MyDoc_*.jsonl" --db data/context.db
```

### Translate passages
```cmd
python scripts\translate_passages.py --db data/context.db --doc MyDoc --engine gemini:gemini-2.5-flash --sleep 0.8 --limit 100 --context 5 --min-quality 0.25
```

### Export HTML
```cmd
python scripts\export_html.py --db data/context.db --doc MyDoc --out exports
```

### Run dashboard manually
```cmd
python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: flask` | `pip install Flask` |
| Tesseract not found | Set `TESSERACT_EXE=C:\...\tesseract.exe` in `.env` |
| Poppler not found | Set `POPPLER_BIN=C:\poppler\bin` in `.env` |
| Translation fails | Check `GEMINI_API_KEY` in `.env`; check dashboard Job Log |
| Budget paused | Dashboard → Usage → Resume Budget |
| Dashboard shows stale data | Hard-refresh: Ctrl+Shift+R |
| Engine still shows Pro | Ctrl+Shift+R to bust browser cache |
