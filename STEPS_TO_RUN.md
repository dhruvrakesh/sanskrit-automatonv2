# Steps to run Sanskrit Automaton v2

## 1. Prerequisites

- **Python 3.10+**
- **Tesseract OCR** (Windows: install from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki); ensure `san`, `hin`, `eng` tessdata are installed)
- **Poppler** (for PDF → images): [Windows builds](https://github.com/oschwartz10612/poppler-windows/releases) — put `bin` on PATH or set `POPPLER_BIN`
- **Pip packages** (from repo root):

```powershell
cd d:\sanskrit-automatonv2
pip install -r requirements.txt
```

For the **dashboard** you need `Flask` (included in requirements). For **translation** you need `openai` and an API key:

```powershell
pip install openai
```

---

## 2. Optional: environment variables

Set these if Tesseract/Poppler aren’t on PATH or you use OpenAI translation.

**PowerShell (current session):**
```powershell
$env:TESSERACT_EXE = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:POPPLER_BIN   = "C:\poppler\bin"
$env:OPENAI_API_KEY = "sk-your-key-here"
```

**CMD:**
```cmd
set TESSERACT_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe
set POPPLER_BIN=C:\poppler\bin
set OPENAI_API_KEY=sk-your-key-here
```

---

## 3. Create folders (if missing)

From the repo root:

```powershell
New-Item -ItemType Directory -Force -Path inbox, data\raw, exports
```

`data/context.db` is created automatically when you run **Ingest**.

---

## 4. Run the dashboard (recommended)

From the **repo root**:

**PowerShell:**
```powershell
cd d:\sanskrit-automatonv2
python scripts/dashboard.py --inbox inbox --db data/context.db --raw data/raw --exports exports --host 127.0.0.1 --port 5057
```

**CMD:**
```cmd
cd d:\sanskrit-automatonv2
python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057
```

Open in a browser: **http://127.0.0.1:5057/**

### Using the dashboard

1. Put **PDFs** in `inbox/`. Name them like `DocName_0001.pdf`, `DocName_0002.pdf`, etc. (doc code + 4-digit page number.)
2. In the table, click **OCR** for a doc → runs Tesseract for missing pages, writes JSONL to `data/raw/`.
3. Click **Ingest** → loads that doc’s JSONL into `data/context.db`.
4. Click **Translate (50)** → translates up to 50 untranslated lines (uses OpenAI if `OPENAI_API_KEY` is set).
5. Click **Export** → writes HTML to `exports/`.

Refresh the page (F5) to update counts after each action.

---

## 5. Alternative: run without the UI (command line)

From the repo root (`d:\sanskrit-automatonv2`), with `inbox`, `data/raw`, `exports` present.

### 5.1 OCR a PDF to JSONL

```powershell
python scripts/ocr_pdf.py --pdf inbox/MyDoc_0001.pdf --out data/raw/MyDoc_0001.jsonl --dpi 400 --max-dpi 600 --lang-tries san+hin+eng san hin eng
```

### 5.2 Ingest JSONL into the DB

```powershell
python scripts/ingest_jsonl_fast.py --doc MyDoc --glob "data/raw/MyDoc_*.jsonl" --db data/context.db
```

### 5.3 Translate passages

```powershell
python scripts/translate_passages.py --db data/context.db --doc MyDoc --engine openai:gpt-4o-mini --sleep 0.6 --limit 100
```

### 5.4 Export to HTML

```powershell
python scripts/export_html.py --db data/context.db --doc MyDoc --out exports --no-sanskrit --title "MyDoc — English Translation"
```

---

## 6. Other ways to run

- **Export API (FastAPI):**  
  `uvicorn api:app --reload --port 8000`  
  Then open http://localhost:8000 (API + static export UI).

- **Analyze/translate API (publish_api):**  
  `uvicorn scripts.publish_api:app --reload --port 8000`  
  Provides `/analyze`, `/entities`, `/translate?explain=true` and a small web UI.

- **Sanskrit-only CLI** (no DB, no translation):
  ```powershell
  echo "धर्मक्षेत्रे कुरुक्षेत्रे" | python scripts/normalize_text.py --from-script DEVANAGARI --to-script SLP1
  echo "धर्मक्षेत्रे कुरुक्षेत्रे" | python scripts/sandhi_split.py
  echo "धर्मक्षेत्रे कुरुक्षेत्रे" | python scripts/morph_parse.py
  ```

---

## 7. Troubleshooting

| Problem | What to do |
|--------|------------|
| `ModuleNotFoundError: No module named 'flask'` | `pip install Flask` |
| Tesseract not found | Set `TESSERACT_EXE` to the full path; ensure `san`, `hin`, `eng` are in `tessdata` |
| Poppler not found | Set `POPPLER_BIN` to the folder containing `pdftoppm.exe` / `pdftocairo.exe` |
| Dashboard buttons do nothing | Watch the terminal where `dashboard.py` is running; refresh the browser (F5) after the job finishes |
| Translation fails | Set `OPENAI_API_KEY` and run `pip install openai` |
| Very poor OCR | Use higher DPI once: `--dpi 600 --max-dpi 600`; install `opencv-python-headless` for better pre-processing |

To stop the dashboard server, press **Ctrl+C** in the terminal where it’s running.
