# Sanskrit Automaton v2 — Windows README

This guide shows how to run the **server + UI dashboard** and how to run the **OCR → ingest → translate → export** pipeline from **PowerShell** and **CMD**.

---

## 0) Folder layout (repo root)
```
./inbox/           # put PDFs here (single- or multi‑page)
./data/raw/        # OCR JSONL lands here
./data/context.db  # SQLite DB (auto-created by ingest)
./exports/         # HTML exports
./scripts/         # project scripts
```
Create folders that don’t exist yet.

---

## 1) Prerequisites

### Software
- **Python 3.10+**
- **Tesseract OCR** (Windows installer) — ensure `san`, `hin`, `eng` language packs are present
- **Poppler** for Windows (provides `pdftoppm`/`pdftocairo`)
- **Python packages**
  - Required for the dashboard: `Flask`
  - Optional for better pre‑processing: `opencv-python-headless`

**Install packages (PowerShell)**
```powershell
pip install Flask opencv-python-headless
```

**Install packages (CMD)**
```cmd
pip install Flask opencv-python-headless
```

### Paths / environment
If Tesseract or Poppler aren’t on PATH, set these variables for your shell session.

**PowerShell**
```powershell
$env:TESSERACT_EXE = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:POPPLER_BIN   = "C:\poppler\bin"
# (optional) If tessdata isn’t alongside tesseract.exe
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata"
```

**CMD**
```cmd
set TESSERACT_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe
set POPPLER_BIN=C:\poppler\bin
set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
```

If you plan to use the OpenAI translation engine:

**PowerShell**
```powershell
$env:OPENAI_API_KEY = "sk-..."
```

**CMD**
```cmd
set OPENAI_API_KEY=sk-...
```

---

## 2) Run the server + UI dashboard
From the **repo root**:

**PowerShell**
```powershell
python scripts/dashboard.py `
  --inbox inbox `
  --db data/context.db `
  --raw data/raw `
  --exports exports `
  --host 127.0.0.1 `
  --port 5057
```

**CMD**
```cmd
python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057
```

Open the UI: **http://127.0.0.1:5057/**

### What the dashboard shows
- **PDFs**: PDFs discovered under `inbox/<doc>/...` or top‑level `inbox/` names
- **JSONL**: OCR outputs found in `data/raw`
- **Ingested pages**: pages present in the DB
- **Lines / Translated / Exports**: DB status per doc

### Buttons (Actions)
- **OCR missing** – Runs OCR for PDFs without JSONL (you’ll be prompted for options).
- **Ingest** – Loads JSONL into `data/context.db`.
- **Translate (50)** – Translates up to 50 pending passages for that doc.
- **Export** – Writes HTML to `exports/`.

> Tip: Progress prints in the server console. Refresh the browser (F5) to see updated counts.

---

## 3) Full pipeline from the command line (without the UI)

### 3.1 OCR a PDF to JSONL
**PowerShell**
```powershell
python scripts/ocr_pdf.py --pdf inbox/bodhyana_0043.pdf `
  --out data/raw/bodhyana_0043.jsonl `
  --dpi 400 --max-dpi 600 `
  --lang-tries san+hin+eng san hin eng
```

**CMD**
```cmd
python scripts\ocr_pdf.py --pdf inbox\bodhyana_0043.pdf --out data\raw\bodhyana_0043.jsonl --dpi 400 --max-dpi 600 --lang-tries san+hin+eng san hin eng
```

Batch example (PowerShell):
```powershell
Get-ChildItem inbox\bodhyana_*.pdf | ForEach-Object {
  $name = [IO.Path]::GetFileNameWithoutExtension($_.FullName)
  $out  = "data/raw/$name.jsonl"
  if (-not (Test-Path $out)) {
    python scripts/ocr_pdf.py --pdf $_.FullName --out $out --dpi 400 --max-dpi 600 --lang-tries san+hin+eng san hin eng
  }
}
```

### 3.2 Ingest JSONL into the DB
**PowerShell**
```powershell
python scripts/ingest_jsonl_fast.py --doc bodhyana --glob data/raw/bodhyana_*.jsonl --db data/context.db
```

**CMD**
```cmd
python scripts\ingest_jsonl_fast.py --doc bodhyana --glob data\raw\bodhyana_*.jsonl --db data\context.db
```

### 3.3 Translate passages
**PowerShell**
```powershell
python scripts/translate_passages.py `
  --db data/context.db `
  --doc bodhyana `
  --engine openai:gpt-4o-mini `
  --sleep 0.6 `
  --limit 100
```

**CMD**
```cmd
python scripts\translate_passages.py --db data\context.db --doc bodhyana --engine openai:gpt-4o-mini --sleep 0.6 --limit 100
```

### 3.4 Export HTML
**PowerShell**
```powershell
python scripts/export_html.py `
  --db data/context.db `
  --doc bodhyana `
  --out exports `
  --no-sanskrit `
  --title "bodhyana — English Translation"
```

**CMD**
```cmd
python scripts\export_html.py --db data\context.db --doc bodhyana --out exports --no-sanskrit --title "bodhyana — English Translation"
```

---

## 4) Troubleshooting

- **`ModuleNotFoundError: No module named 'flask'`** → `pip install Flask`
- **Tesseract not found** → set `TESSERACT_EXE` to the full path; ensure `san`, `hin`, `eng` are installed under `tessdata` (or set `TESSDATA_PREFIX`).
- **Poppler not found** → set `POPPLER_BIN` to the folder containing `pdftoppm.exe`/`pdftocairo.exe`.
- **Buttons seem to do nothing** → watch the terminal running `dashboard.py`. The grid updates after work completes; hit **F5** in the browser.
- **Very low OCR character counts** → retry with higher DPI once: `--dpi 600 --max-dpi 600`. Installing `opencv-python-headless` enables stronger pre‑processing.

---

## 5) PowerShell vs CMD quick cheatsheet
- **Line continuation**: PowerShell uses backtick `` ` ``; CMD uses caret `^` (or put everything on one line).
- **Env vars**: PowerShell `$env:NAME = "value"`; CMD `set NAME=value`.
- **Paths**: Use `\` in CMD; PowerShell accepts `/` or `\`.

---

## 6) Stop the server
Press **Ctrl+C** in the terminal where `dashboard.py` is running.

---

That’s it. If you get stuck on a particular PDF page (very low OCR), note its filename and I can add a tailored pre‑proc recipe for that case.

