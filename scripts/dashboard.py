#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanskrit Automaton v2 — Enhanced Dashboard (Flask)

Features:
- Rich dark-mode UI with Sanskrit-inspired gold/saffron palette
- Corpus Browser: browse D: drive categories, select & import PDFs
- Per-doc pipeline progress (OCR → Ingest → Translate → Export)
- Engine selector: OpenAI / Gemini (configurable per run)
- Auto-split multi-page PDFs on import
- Live job log with stdout/stderr streaming
- Batch actions: OCR All, Ingest All, Translate All

Run:
  python scripts/dashboard.py --inbox inbox --db data/context.db --raw data/raw --exports exports --host 127.0.0.1 --port 5057
"""
from __future__ import annotations
import os, sys, re, json, time, threading, uuid, pathlib, subprocess, sqlite3, traceback, shutil
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from flask import Flask, jsonify, request, send_from_directory, Response

ROOT   = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# Load .env early so CORPUS_ROOT etc. are available
def _load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        k, sep, v = s.partition("=")
        if sep:
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env()

CORPUS_ROOT = pathlib.Path(os.environ.get("CORPUS_ROOT", r"D:\hindu.holy.scriptures.all.sanskrit.pdf.entIDity"))

app = Flask("dashboard")

# ──────────────────────────────────────────────────────────────────────────────
# Job runner
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Job:
    id: str
    kind: str
    doc: str
    cmd: List[str]
    start: float = field(default_factory=time.time)
    end: Optional[float] = None
    ok: Optional[bool] = None
    out: str = ""
    err: str = ""
    proc: Optional[object] = field(default=None, repr=False)  # subprocess.Popen, not serialized
    killed: bool = False
    active: bool = False   # True once the job's semaphore is acquired and it is
                           # ACTUALLY executing (vs. still queued behind the lock).

JOBS: Dict[str, Job] = {}
JOBS_LOCK = threading.Lock()

# ── Persistent job log (survives restarts) ────────────────────────────────────
JOBS_LOG_PATH = ROOT / "data" / "jobs.jsonl"

def _persist_job(job: Job):
    """Append a completed job record to data/jobs.jsonl."""
    try:
        JOBS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "id":    job.id,
            "kind":  job.kind,
            "doc":   job.doc,
            "start": job.start,
            "end":   job.end,
            "ok":    job.ok,
            "duration_s": round((job.end or job.start) - job.start, 1),
            "out_lines": len((job.out or "").splitlines()),
            "err_preview": (job.err or "")[:300],
        }
        with open(JOBS_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # never let logging crash the server

def _load_job_history(limit: int = 200) -> List[dict]:
    """Read last N records from jobs.jsonl."""
    if not JOBS_LOG_PATH.exists():
        return []
    lines = JOBS_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    records = []
    for line in reversed(lines[-limit:]):
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return records

def _kill_proc(proc) -> bool:
    """Kill a subprocess and its entire process tree (Windows-safe)."""
    if proc is None:
        return False
    try:
        import signal
        pid = proc.pid
        # On Windows use taskkill /F /T to kill the whole tree
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=10)
        else:
            import os, signal
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        return True
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        return False

def _child_env() -> dict:
    """Child processes inherit our env plus a hard UTF-8 stdio guarantee.
    Without this, a child printing Devanagari/IAST to its captured pipe on
    Windows encodes as cp1252 and raises UnicodeEncodeError('charmap'), which
    shows up as spurious per-verse errors (the infamous err:NNN counter)."""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"                 # interpreter-wide UTF-8 mode
    env["PYTHONIOENCODING"] = "utf-8:replace"
    return env

def _run_job(job: Job):
    try:
        proc = subprocess.Popen(
            job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), env=_child_env()
        )
        job.proc = proc  # store so it can be killed
        out, err = proc.communicate()
        if job.killed:
            job.ok  = False
            job.err = "[KILLED by user]"
        else:
            job.ok  = proc.returncode == 0
            job.out = (out or b"").decode("utf-8", "replace")
            job.err = (err or b"").decode("utf-8", "replace")
    except Exception as e:
        job.ok  = False
        job.err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    finally:
        job.end  = time.time()
        job.proc = None  # clear reference
        _persist_job(job)  # write to disk immediately

# ── Job concurrency limits ───────────────────────────────────────────────────
# Max parallel OCR jobs (Tesseract is RAM/CPU heavy — 2 is the safe max on most machines)
_OCR_SEM       = threading.Semaphore(2)
# Max parallel translation jobs (API rate limit protection)
_TRANSLATE_SEM = threading.Semaphore(1)
# General semaphore for other jobs
_GENERAL_SEM   = threading.Semaphore(3)

_KIND_SEM = {
    "ocr":              _OCR_SEM,
    "translate":        _TRANSLATE_SEM,
    "advance_pipeline": _TRANSLATE_SEM,
    "pipeline":         _TRANSLATE_SEM,
}

# ── Keep-awake: don't let the PC sleep while it is translating ────────────────
def _any_unfinished_job() -> bool:
    with JOBS_LOCK:
        return any(j.ok is None for j in JOBS.values())

def _keep_awake_loop():
    """While ANY job is unfinished, ask Windows to keep the SYSTEM awake (the
    display may still sleep to save the panel) so long overnight translation runs
    are never paused by idle sleep. The request is released as soon as all jobs
    finish, so the machine sleeps normally when the automaton is idle. No-op off
    Windows. This maximises unattended translation time (2026-08-26)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except Exception:
        return
    ES_CONTINUOUS        = 0x80000000
    ES_SYSTEM_REQUIRED   = 0x00000001
    ES_AWAYMODE_REQUIRED = 0x00000040
    held = False
    while True:
        try:
            busy = _any_unfinished_job()
            if busy and not held:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
                held = True
                print("[keep-awake] jobs running — system sleep suppressed")
            elif not busy and held:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                held = False
                print("[keep-awake] idle — normal sleep restored")
        except Exception:
            pass
        time.sleep(20)

def launch(kind: str, doc: str, argv: List[str], then=None) -> str:
    """Launch a job under its kind's semaphore. Optional `then(job)` runs AFTER the
    job finishes AND its semaphore is released, but only if the job succeeded — this
    is how the pipeline chains OCR (OCR lock, parallel to translation) → ingest →
    translate (translate lock) without holding the translate lock during OCR."""
    # ── Duplicate job prevention ──────────────────────────────────────────────
    with JOBS_LOCK:
        for j in JOBS.values():
            if j.ok is None and j.kind == kind and j.doc == doc:
                print(f"[launch] SKIPPED duplicate: kind={kind} doc={doc} (job {j.id} still running)")
                return j.id  # Return existing job ID

    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv)
    with JOBS_LOCK:
        JOBS[job.id] = job

    # Any translation-family kind (translate, translate_hi, advance_pipeline,
    # pipeline) shares the single translate semaphore so DB writers serialize —
    # even across languages. This is what keeps English and Hindi jobs from
    # writing concurrently (2026-08-02). The QA-panel writers (qa_scan, qa_heal)
    # also mutate the DB (translation_qa / archive+clear+refill) so they share
    # the same semaphore — a heal can never run while a translate is writing,
    # and vice versa (2026-08-16).
    if (kind.startswith("translate")
            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal")):
        sem = _TRANSLATE_SEM
    else:
        sem = _KIND_SEM.get(kind, _GENERAL_SEM)

    def run_with_sem():
        sem.acquire()
        job.active = True   # semaphore held → this job is now REALLY executing
        try:
            _run_job(job)
        finally:
            sem.release()
        # Chain the next stage only on success, AFTER our semaphore is released so
        # the follow-up can take whatever lock it needs (e.g. the translate lock).
        if then is not None and job.ok:
            try:
                then(job)
            except Exception as e:
                print(f"[chain] then() for job {job.id} ({kind}/{doc}) failed: {e}")

    threading.Thread(target=run_with_sem, daemon=True).start()
    return job.id


# ──────────────────────────────────────────────────────────────────────────────
# Inbox / JSONL scanner
# ──────────────────────────────────────────────────────────────────────────────

# Doc part allows hyphens (e.g. "2015_405693_Shatpath-Brahmanam") to match
# _sanitize_doc_name / DOC_RE — otherwise hyphenated docs' pages were scanned as
# non-matching and the whole document stayed invisible in the dashboard (2026-08-26).
PDF_RE  = re.compile(r"^([A-Za-z0-9_\-]+)_(\d{4})\.pdf$",           re.IGNORECASE)
JSONL_RE = re.compile(r"^([A-Za-z0-9_\-]+)_(\d{4})(?:_norm)?\.jsonl$", re.IGNORECASE)

def scan_inbox(inbox: pathlib.Path) -> Dict[str, List[int]]:
    docs: Dict[str, List[int]] = {}
    if not inbox.exists():
        return docs
    for p in inbox.iterdir():
        m = PDF_RE.match(p.name)
        if not m:
            continue
        doc, pg = m.group(1), int(m.group(2))
        docs.setdefault(doc, []).append(pg)
    for k in docs:
        docs[k].sort()
    return docs

def scan_jsonl(raw: pathlib.Path) -> Dict[str, List[int]]:
    docs: Dict[str, List[int]] = {}
    if not raw.exists():
        return docs
    for p in raw.iterdir():
        m = JSONL_RE.match(p.name)
        if not m:
            continue
        doc, pg = m.group(1), int(m.group(2))
        docs.setdefault(doc, []).append(pg)
    for k in docs:
        docs[k].sort()
    return docs

def connect(db_path: pathlib.Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con

def _tables(con):
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def _cols(con, t):
    try:
        return {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
    except sqlite3.OperationalError:
        return set()

def detect_schema(con):
    pc = _cols(con, "passages")
    pg_col  = "page_no" if "page_no" in pc else ("pageno" if "pageno" in pc else ("page" if "page" in pc else "rowid"))
    idx_col = "idx" if "idx" in pc else "rowid"
    tset = _tables(con)
    if "docs" in tset and {"id", "code"}.issubset(_cols(con, "docs")) and "doc_id" in pc:
        doc_mode = "join_docs"
    elif "doc" in pc:
        doc_mode = "passages_doc"
    elif "doc_code" in pc:
        doc_mode = "passages_doc_code"
    else:
        doc_mode = "unknown"
    return {"pg_col": pg_col, "idx_col": idx_col, "doc_mode": doc_mode}

def count_ingested(con, schema, doc):
    pg = schema["pg_col"]
    dm = schema["doc_mode"]
    if dm == "join_docs":
        sql = f"SELECT COUNT(DISTINCT p.{pg}) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?"
    elif dm == "passages_doc":
        sql = f"SELECT COUNT(DISTINCT {pg}) FROM passages WHERE doc=?"
    elif dm == "passages_doc_code":
        sql = f"SELECT COUNT(DISTINCT {pg}) FROM passages WHERE doc_code=?"
    else:
        return 0, 0, 0
    pages = int(con.execute(sql, (doc,)).fetchone()[0] or 0)
    if dm == "join_docs":
        sql_tot = "SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?"
        sql_tr  = "SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''"
    elif dm == "passages_doc":
        sql_tot = "SELECT COUNT(*) FROM passages WHERE doc=?"
        sql_tr  = "SELECT COUNT(*) FROM passages WHERE doc=? AND TRIM(COALESCE(translation,''))<>''"
    else:
        sql_tot = "SELECT COUNT(*) FROM passages WHERE doc_code=?"
        sql_tr  = "SELECT COUNT(*) FROM passages WHERE doc_code=? AND TRIM(COALESCE(translation,''))<>''"
    total = int(con.execute(sql_tot, (doc,)).fetchone()[0] or 0)
    trans = int(con.execute(sql_tr,  (doc,)).fetchone()[0] or 0)
    return pages, total, trans

def count_exports(exports_dir: pathlib.Path, doc: str) -> int:
    if not exports_dir.exists():
        return 0
    pref = f"{doc}_"
    return sum(1 for p in exports_dir.iterdir() if p.suffix.lower() == ".html" and p.name.startswith(pref))


# ──────────────────────────────────────────────────────────────────────────────
# Doc name validation
# ──────────────────────────────────────────────────────────────────────────────

DOC_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

def _validate_doc(doc) -> Optional[str]:
    if not doc or not isinstance(doc, str):
        return None
    return doc if DOC_RE.match(doc) else None

def py(*args: str) -> List[str]:
    return [sys.executable, *args]

def script(name: str) -> str:
    return str(SCRIPTS / name)


# ──────────────────────────────────────────────────────────────────────────────
# Status API
# ──────────────────────────────────────────────────────────────────────────────

def build_status(inbox, raw, dbp, exports):
    try:
        inbox_map = scan_inbox(inbox)
        raw_map   = scan_jsonl(raw)
        rows = []
        seen = set()
        with connect(dbp) as con:
            schema = detect_schema(con)
            # Docs with PDFs in inbox (primary — being actively processed)
            for doc, pdf_pages in sorted(inbox_map.items()):
                jsonl_pages = set(raw_map.get(doc, []))
                ing_pages, total_lines, trans_lines = count_ingested(con, schema, doc)
                rows.append({
                    "doc":              doc,
                    "pdf_count":        len(pdf_pages),
                    "jsonl_count":      len(jsonl_pages),
                    "ingested_pages":   int(ing_pages),
                    "total_lines":      int(total_lines),
                    "translated_lines": int(trans_lines),
                    "exports":          count_exports(exports, doc),
                })
                seen.add(doc)
            # Docs already in DB (inbox empty after prior import — show them too)
            try:
                # Retired docs (code suffixed '-RETIRED') are hidden from the
                # sidebar but never deleted — fully reversible by renaming back.
                db_docs = [r[0] for r in con.execute(
                    "SELECT code FROM docs WHERE code NOT LIKE '%-RETIRED' ORDER BY code")]
            except Exception:
                db_docs = []
            for doc in db_docs:
                if doc in seen:
                    continue
                jsonl_pages = set(raw_map.get(doc, []))
                ing_pages, total_lines, trans_lines = count_ingested(con, schema, doc)
                rows.append({
                    "doc":              doc,
                    "pdf_count":        0,          # not in inbox — already imported
                    "jsonl_count":      len(jsonl_pages),
                    "ingested_pages":   int(ing_pages),
                    "total_lines":      int(total_lines),
                    "translated_lines": int(trans_lines),
                    "exports":          count_exports(exports, doc),
                })
        rows.sort(key=lambda r: r["doc"])
        return rows
    except Exception:
        traceback.print_exc()
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Corpus Browser API
# ──────────────────────────────────────────────────────────────────────────────

_CORPUS_CACHE: dict = {"ts": 0.0, "data": []}
_CORPUS_CACHE_TTL = 60  # seconds — D: drive scan is expensive (Google Drive sync)

def _corpus_tree() -> List[dict]:
    """Return list of {category, pdfs:[{name, size, path}]} from CORPUS_ROOT.
    Result is cached for CORPUS_CACHE_TTL seconds to avoid hammering the D: drive."""
    now = time.time()
    if now - _CORPUS_CACHE["ts"] < _CORPUS_CACHE_TTL:
        return _CORPUS_CACHE["data"]
    if not CORPUS_ROOT.exists():
        return []
    categories = []
    for cat_dir in sorted(CORPUS_ROOT.iterdir()):
        if not cat_dir.is_dir():
            continue
        pdfs = sorted(
            [
                {"name": p.name, "size": p.stat().st_size, "path": str(p)}
                for p in cat_dir.glob("*.pdf")
            ],
            key=lambda x: x["name"],
        )
        if pdfs:
            categories.append({"category": cat_dir.name, "pdfs": pdfs})
    _CORPUS_CACHE["data"] = categories
    _CORPUS_CACHE["ts"]   = now
    return categories


def _invalidate_corpus_cache():
    """Call after a successful import so the sidebar reflects new inbox state."""
    _CORPUS_CACHE["ts"] = 0.0


def _sanitize_doc_name(stem: str) -> str:
    """Convert a raw filename stem to a safe doc code."""
    s = re.sub(r"[^A-Za-z0-9_\-]", "_", stem)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def _count_pdf_pages(pdf_path: pathlib.Path) -> int:
    """Count pages in a PDF. Tries pypdf in tolerant mode, then Poppler's pdfinfo
    (reliable on large/linearised/slightly-malformed scans where pypdf throws).
    Returns 0 when the count truly can't be determined — callers must NOT treat 0
    as '1 page' (that silently dumps a whole book as one un-OCRable blob)."""
    try:
        from pypdf import PdfReader
        n = len(PdfReader(str(pdf_path), strict=False).pages)
        if n > 0:
            return n
    except Exception:
        pass
    try:
        import subprocess
        try:
            from env_loader import poppler_path as _pp
            pp = _pp()
        except Exception:
            pp = ""
        exe = str(pathlib.Path(pp) / "pdfinfo") if pp else "pdfinfo"
        out = subprocess.run([exe, str(pdf_path)], capture_output=True, text=True, timeout=90)
        for line in (out.stdout or "").splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return 0


@app.get("/api/corpus")
def api_corpus():
    return jsonify({"corpus_root": str(CORPUS_ROOT), "categories": _corpus_tree()})


def _do_import(inbox_dir, files, auto_split):
    """Copy a list of {path, doc} PDFs into the inbox, splitting multi-page PDFs.
    Shared by the corpus browser and the from-disk importer."""
    inbox_dir.mkdir(parents=True, exist_ok=True)
    try:
        inbox_resolved = inbox_dir.resolve()
    except Exception:
        inbox_resolved = inbox_dir
    split_script = ROOT / "tools" / "split_pdf_pages.py"
    if not split_script.exists():
        split_script = ROOT / "inbox" / "split_pdf_pages.py"
    have_splitter = split_script.exists()

    results = []
    for item in files:
        src_path = pathlib.Path(item.get("path", ""))
        doc_name = _sanitize_doc_name(item.get("doc") or src_path.stem)
        if not src_path.exists():
            results.append({"path": str(src_path), "error": "file not found"})
            continue
        # Already an inbox page (X_NNNN.pdf living in the inbox)? Leave it — importing
        # the inbox folder must not re-copy the thousands of pages already there.
        try:
            already = (src_path.resolve().parent == inbox_resolved) and bool(PDF_RE.match(src_path.name))
        except Exception:
            already = False
        if already:
            results.append({"doc": doc_name, "action": "already-in-inbox"})
            continue

        n_pages = _count_pdf_pages(src_path)          # 0 when unknown
        is_pdf  = src_path.suffix.lower() == ".pdf"
        # Split when auto_split is on AND the file is a PDF that is NOT definitively
        # single-page (n_pages != 1). Unknown count (0, e.g. a big scan pypdf can't
        # parse) routes to the splitter too — the splitter reports a real error in
        # the job log instead of silently dumping the whole book as one blob.
        if auto_split and is_pdf and have_splitter and n_pages != 1:
            cmd = py(str(split_script), str(src_path), "-o", str(inbox_dir), "-p", doc_name)
            jid = launch("import_split", doc_name, cmd)
            results.append({"doc": doc_name, "pages": (n_pages or "?"),
                            "action": "splitting", "job": jid})
        else:
            # Definitely single page, or splitting off/unavailable → copy as _0001
            stem = src_path.stem
            m = re.match(r"^([A-Za-z0-9_\-]+)_(\d+)$", stem, re.I) if PDF_RE.match(src_path.name) else None
            if m:
                d, pg = _sanitize_doc_name(m.group(1)), m.group(2).zfill(4)
                dest = inbox_dir / f"{d}_{pg}.pdf"
            else:
                dest = inbox_dir / f"{doc_name}_0001.pdf"
            shutil.copy2(str(src_path), str(dest))
            results.append({"doc": doc_name, "pages": (n_pages or 1),
                            "action": "copied", "dest": dest.name})
    _invalidate_corpus_cache()
    return results


@app.post("/api/corpus/import")
def api_corpus_import():
    """Copy selected corpus PDFs into inbox/. Body: {inbox, files:[{path,doc}], auto_split}."""
    data       = request.get_json(force=True) or {}
    inbox_dir  = pathlib.Path(data.get("inbox") or "inbox")
    auto_split = bool(data.get("auto_split", True))
    files      = data.get("files", [])
    if not files:
        return jsonify({"error": "no files specified"}), 400
    return jsonify({"imported": _do_import(inbox_dir, files, auto_split)})


@app.post("/api/import_path")
def api_import_path():
    """Import a PDF (or every PDF in a folder) from ANY absolute path on the local
    disk — the 'choose from disk' path the corpus browser (limited to CORPUS_ROOT)
    can't reach. Body: {path, inbox, auto_split}. The dashboard runs locally, so it
    can read any path the user names."""
    data       = request.get_json(force=True) or {}
    raw        = (data.get("path") or "").strip().strip('"').strip("'")
    inbox_dir  = pathlib.Path(data.get("inbox") or "inbox")
    auto_split = bool(data.get("auto_split", True))
    if not raw:
        return jsonify({"error": "no path given"}), 400
    p = pathlib.Path(raw)
    if not p.exists():
        return jsonify({"error": f"path not found: {raw}"}), 400
    files = []
    if p.is_dir():
        for pdf in sorted(p.glob("*.pdf")):
            files.append({"path": str(pdf), "doc": pdf.stem})
        if not files:
            return jsonify({"error": f"no PDFs found in folder: {raw}"}), 400
    elif p.suffix.lower() == ".pdf":
        files.append({"path": str(p), "doc": p.stem})
    else:
        return jsonify({"error": "path must be a .pdf file or a folder containing PDFs"}), 400
    return jsonify({"imported": _do_import(inbox_dir, files, auto_split), "count": len(files)})


@app.post("/api/upload")
def api_upload():
    """Receive PDF file(s) chosen via the browser's native OS file dialog (multipart)
    and import them — no path typing. The uploaded bytes are saved into the inbox and
    split like any other import. Works for a file anywhere on the user's computer."""
    inbox_dir  = pathlib.Path(request.form.get("inbox") or "inbox")
    auto_split = (request.form.get("auto_split", "true").lower() != "false")
    uploads = request.files.getlist("files")
    if not uploads:
        return jsonify({"error": "no files uploaded"}), 400
    inbox_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for f in uploads:
        name = f.filename or ""
        if not name.lower().endswith(".pdf"):
            continue
        doc = _sanitize_doc_name(pathlib.Path(name).stem)
        # Persist the uploaded source under a name scan_inbox ignores (not _NNNN);
        # _do_import then splits it into <doc>_NNNN.pdf pages.
        src = inbox_dir / f"{doc}__upload.pdf"
        try:
            f.save(str(src))
        except Exception as e:
            items.append({"doc": doc, "error": f"save failed: {e}"})
            continue
        items.append({"path": str(src), "doc": doc})
    good = [i for i in items if "path" in i]
    if not good:
        return jsonify({"error": "no PDF files in upload", "imported": items}), 400
    return jsonify({"imported": _do_import(inbox_dir, good, auto_split), "count": len(good)})


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline Action Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_from_directory(str(SCRIPTS), "dashboard_static.html")

@app.get("/api/status")
def api_status():
    inbox   = pathlib.Path(request.args.get("inbox")   or "inbox")
    raw     = pathlib.Path(request.args.get("raw")     or "data/raw")
    dbp     = pathlib.Path(request.args.get("db")      or "data/context.db")
    exports = pathlib.Path(request.args.get("exports") or "exports")
    return jsonify(build_status(inbox, raw, dbp, exports))

@app.get("/api/job/<jid>")
def api_job(jid):
    with JOBS_LOCK:
        job = JOBS.get(jid)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify({
        "id": job.id, "kind": job.kind, "doc": job.doc,
        "ok": job.ok, "start": job.start, "end": job.end,
        "out": job.out[-6000:], "err": job.err[-2000:],
        "running": job.ok is None, "killed": job.killed,
        # active=True: executing now; False while ok is None: queued behind its lock.
        "active": bool(job.active), "state": ("running" if job.active else "queued") if job.ok is None else "done",
    })

@app.post("/api/job/<jid>/kill")
def api_job_kill(jid):
    """Kill a single running job."""
    with JOBS_LOCK:
        job = JOBS.get(jid)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    if job.ok is not None:
        return jsonify({"message": "job already finished", "ok": job.ok})
    job.killed = True
    killed = _kill_proc(job.proc)
    return jsonify({"killed": killed, "jid": jid, "doc": job.doc, "kind": job.kind})

@app.post("/api/jobs/kill_all")
def api_jobs_kill_all():
    """Pause/stop ALL currently running jobs."""
    killed = []
    with JOBS_LOCK:
        running = [j for j in JOBS.values() if j.ok is None]
    for job in running:
        job.killed = True
        ok = _kill_proc(job.proc)
        killed.append({"jid": job.id, "doc": job.doc, "kind": job.kind, "killed": ok})
    return jsonify({"stopped": len(killed), "jobs": killed})

@app.get("/api/jobs/running")
def api_jobs_running():
    """List all currently running jobs."""
    with JOBS_LOCK:
        unfinished = [
            {"id": j.id, "kind": j.kind, "doc": j.doc,
             "start": j.start, "elapsed_s": round(time.time() - j.start, 1),
             # active=True → executing now; active=False → queued behind its lock
             # (e.g. waiting for the single translate lock). This lets the UI show
             # "1 running · 4 queued" instead of a misleading "5 running".
             "active": bool(j.active), "state": "running" if j.active else "queued"}
            for j in JOBS.values() if j.ok is None
        ]
    active_n = sum(1 for j in unfinished if j["active"])
    return jsonify({"running": unfinished, "count": len(unfinished),
                    "active": active_n, "queued": len(unfinished) - active_n})

@app.post("/api/doc/<doc>/stop")
def api_doc_stop(doc):
    """Kill all running jobs for a specific doc (translate, pipeline, etc.)."""
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    killed = []
    with JOBS_LOCK:
        running = [j for j in JOBS.values() if j.ok is None and j.doc == doc]
    for job in running:
        job.killed = True
        ok = _kill_proc(job.proc)
        killed.append({"jid": job.id, "kind": job.kind, "killed": ok})
    return jsonify({"doc": doc, "stopped": len(killed), "jobs": killed})


@app.get("/api/jobs/history")
def api_jobs_history():
    """Return persistent job history from data/jobs.jsonl (survives restarts)."""
    limit = int(request.args.get("limit", 200))
    doc   = request.args.get("doc", "").strip()
    kind  = request.args.get("kind", "").strip()
    records = _load_job_history(limit=limit * 4)   # load extra, then filter
    if doc:
        records = [r for r in records if r.get("doc") == doc]
    if kind:
        records = [r for r in records if r.get("kind") == kind]
    return jsonify(records[:limit])

@app.get("/api/usage")
def api_usage():
    """Return real cost tracking data: usage_log totals, budget state, per-engine breakdown."""
    db_path = request.args.get("db", "data/context.db")
    try:
        import sys as _sys
        _sys.path.insert(0, str(SCRIPTS))
        try:
            from cost_tracker import get_summary, ensure_usage_schema, migrate_cache_costs
            with sqlite3.connect(db_path) as con:
                ensure_usage_schema(con)
                # Backfill from mt_cache on first call (idempotent)
                totals = con.execute("SELECT SUM(total_calls) FROM usage_totals").fetchone()[0] or 0
                cache_entries = con.execute("SELECT COUNT(*) FROM mt_cache").fetchone()[0]
                if totals == 0 and cache_entries > 0:
                    migrate_cache_costs(con)
                return jsonify(get_summary(con))
        except ImportError:
            pass  # fall through to legacy estimation

        # ── Legacy fallback: estimate from mt_cache ──────────────────────────
        # FIXED: column is 'output' not 'translation'
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "mt_cache" not in tables:
            return jsonify({"error": "mt_cache table not found"})

        # Pricing: (in_usd_per_M_tokens, out_usd_per_M_tokens), 4 chars ≈ 1 token
        PRICING = {
            "gemini:gemini-2.5-pro":   (1.25,  10.00),
            "gemini:gemini-2.0-flash": (0.075,  0.30),
            "openai:gpt-4o-mini":      (0.15,   0.60),
            "openai:gpt-4o":           (2.50,  10.00),
        }

        rows = con.execute(
            # mt_cache real schema: engine, lang_in, lang_out, text_hash, text, output, context_hash, created_at
            "SELECT engine, COUNT(*) as calls, "
            "SUM(LENGTH(text)) as in_chars, SUM(LENGTH(output)) as out_chars "
            "FROM mt_cache GROUP BY engine ORDER BY calls DESC"
        ).fetchall()
        total_calls = con.execute("SELECT COUNT(*) FROM mt_cache").fetchone()[0]
        cost_estimate = 0.0
        by_engine = []
        for r in rows:
            eng = r["engine"] or "unknown"
            calls = r["calls"]
            in_chars  = r["in_chars"]  or 0
            out_chars = r["out_chars"] or 0
            in_tok  = in_chars  / 4 / 1_000_000
            out_tok = out_chars / 4 / 1_000_000
            # Match engine string to pricing
            in_p, out_p = (1.25, 10.00)  # default: Gemini 2.5 Pro
            for k, (ip, op) in PRICING.items():
                if k in eng or eng in k:
                    in_p, out_p = ip, op
                    break
            cost = in_p * in_tok + out_p * out_tok
            cost_estimate += cost
            by_engine.append({
                "engine": eng, "calls": calls,
                "in_chars": in_chars, "out_chars": out_chars,
                "cost_usd": round(cost, 6),
            })
        budget_usd = float(os.environ.get("SA_GPT_BUDGET_USD", "8.0"))
        con.close()
        return jsonify({
            "budget": {"budget_usd": budget_usd, "spent_usd": round(cost_estimate, 6), "paused": False},
            "by_engine": {r["engine"]: {
                "calls": r["calls"], "cost_usd": r["cost_usd"],
                "in_chars": r["in_chars"], "out_chars": r["out_chars"]
            } for r in by_engine},
            "recent": [],
            "total_calls": total_calls,
            "note": "Legacy estimate from mt_cache (install cost_tracker.py for real tracking)"
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.get("/api/budget")
def api_budget_get():
    """Get current budget state: {budget_usd, spent_usd, paused, remaining_usd}."""
    db_path = request.args.get("db", "data/context.db")
    try:
        import sys as _sys; _sys.path.insert(0, str(SCRIPTS))
        from cost_tracker import ensure_usage_schema, get_summary
        con = sqlite3.connect(db_path)
        ensure_usage_schema(con)
        s = get_summary(con)
        b = s["budget"]
        b["remaining_usd"] = round(b["budget_usd"] - b["spent_usd"], 6)
        con.close()
        return jsonify(b)
    except Exception as e:
        return jsonify({"error": str(e), "budget_usd": 8.0, "spent_usd": 0.0, "paused": False})


@app.post("/api/budget")
def api_budget_set():
    """Set/resume budget. Body: {budget_usd: 15.0} or {resume: true}."""
    db_path = request.args.get("db", "data/context.db")
    data = request.get_json(force=True) or {}
    try:
        import sys as _sys; _sys.path.insert(0, str(SCRIPTS))
        from cost_tracker import ensure_usage_schema, set_budget, resume_budget
        con = sqlite3.connect(db_path)
        ensure_usage_schema(con)
        if data.get("resume"):
            resume_budget(con)
            return jsonify({"resumed": True})
        if "budget_usd" in data:
            set_budget(con, float(data["budget_usd"]))
            return jsonify({"budget_usd": float(data["budget_usd"]), "set": True})
        con.close()
        return jsonify({"error": "specify budget_usd or resume:true"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.get("/api/progress")
def api_progress():
    """Return live translation progress from data/translation_progress.json."""
    prog_path = ROOT / "data" / "translation_progress.json"
    try:
        if prog_path.exists():
            return jsonify(json.loads(prog_path.read_text(encoding="utf-8")))
        return jsonify({"status": "idle"})
    except Exception as e:
        return jsonify({"status": "idle", "error": str(e)})

@app.post("/api/ocr")
def api_ocr():
    data  = request.get_json(force=True) or {}
    doc   = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    dpi        = str(data.get("dpi") or 400)
    langs      = str(data.get("langs") or "san+hin+eng").strip()
    lang_tries = [langs]
    for fb in ("san", "hin", "eng"):
        if fb not in lang_tries:
            lang_tries.append(fb)
    inbox = pathlib.Path(data.get("inbox") or "inbox")
    raw   = pathlib.Path(data.get("raw")   or "data/raw")
    missing: List[pathlib.Path] = []
    for p in inbox.glob(f"{doc}_*.pdf"):
        m = PDF_RE.match(p.name)
        if not m:
            continue
        pg = m.group(2)
        if not (raw / f"{doc}_{pg}.jsonl").exists() and not (raw / f"{doc}_{pg}_norm.jsonl").exists():
            missing.append(p)
    if not missing:
        return jsonify({"message": "Nothing to OCR"}), 200
    batch_script = str(SCRIPTS / "ocr_batch.py")
    cmd = py(batch_script,
             "--pdfs",      *[str(p) for p in sorted(missing)],
             "--outdir",    str(raw.resolve()),
             "--dpi",       dpi,
             "--max-dpi",   "600",
             "--lang-tries", *lang_tries)
    jid = launch("ocr", doc, cmd)
    return jsonify({"job": jid})


@app.post("/api/ingest")
def api_ingest():
    data = request.get_json(force=True) or {}
    doc  = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db   = data.get("db")  or "data/context.db"
    raw  = data.get("raw") or "data/raw"
    glob = str(pathlib.Path(raw) / f"{doc}_*.jsonl")
    cmd = py(script("ingest_jsonl_fast.py"), "--doc", doc, "--glob", glob, "--db", db)
    return jsonify({"job": launch("ingest", doc, cmd)})

@app.post("/api/translate")
def api_translate():
    data    = request.get_json(force=True) or {}
    doc     = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db      = data.get("db")      or "data/context.db"
    engine  = data.get("engine")  or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    # A blank/0 limit means "translate the whole doc" (finish it in one press), which
    # is what users expect from Start/Full. A positive number still caps the run.
    try:
        _lim = int(data.get("limit"))
    except (TypeError, ValueError):
        _lim = 0
    limit   = str(_lim if _lim > 0 else 1000000)
    sleep   = str(data.get("sleep")   or 0.8)
    context = str(data.get("context") or 5)   # 5-verse sliding context window
    min_quality = str(data.get("min_quality") or 0.35)  # Phase Q default (was 0.25)
    lang    = (data.get("lang") or "en").strip()   # Phase HI ('both' => EN then HI)

    # One-job EN+HI: run the English pass then the Hindi pass back to back via the
    # translate_both.py orchestrator. Each pass is the UNCHANGED translate_passages.py
    # (Hindi is translated directly from Sanskrit, English used only as an optional
    # reference). Shares the translate semaphore, so it serializes with other jobs.
    if lang == "both":
        cmd = py(script("translate_both.py"),
                 "--db", db, "--doc", doc, "--engine", engine,
                 "--sleep", sleep, "--limit", limit, "--context", context,
                 "--min-quality", min_quality)
        if data.get("hi_pure"):
            cmd += ["--hi-pure"]
        return jsonify({"job": launch("translate_both", doc, cmd), "lang": "both"})

    cmd = py(script("translate_passages.py"),
             "--db", db, "--doc", doc, "--engine", engine,
             "--sleep", sleep, "--limit", limit, "--context", context,
             "--min-quality", min_quality)
    kind = "translate"
    if lang != "en":
        cmd += ["--lang", lang]
        kind = f"translate_{lang}"   # distinct dedup identity; shares translate sem
    return jsonify({"job": launch(kind, doc, cmd), "lang": lang})


@app.post("/api/translate-one")
def api_translate_one():
    """Translate a SINGLE verse on demand (the reader's per-verse button). Fills
    doc/page_no/idx in the requested language and saves it to the corpus. Shares
    the translate semaphore, so it serializes safely with any running job."""
    data = request.get_json(force=True) or {}
    doc  = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    try:
        page_no = int(data.get("page_no"))
        idx     = int(data.get("idx"))
    except (TypeError, ValueError):
        return jsonify({"error": "page_no and idx must be integers"}), 400
    db     = data.get("db") or "data/context.db"
    engine = data.get("engine") or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    lang   = (data.get("lang") or "en").strip()
    argv = py(script("translate_passages.py"),
              "--db", db, "--doc", doc, "--engine", engine,
              "--only-page", str(page_no), "--only-idx", str(idx), "--limit", "1")
    if lang != "en":
        argv += ["--lang", lang]
    # Unique label per (verse, lang) so the dup-guard never collapses two verses.
    jid = launch("translate_one", f"{doc}:{page_no}.{idx}:{lang}", argv)
    return jsonify({"job": jid, "doc": doc, "page_no": page_no, "idx": idx, "lang": lang})


@app.post("/api/export")
def api_export():
    data  = request.get_json(force=True) or {}
    doc   = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db    = data.get("db")  or "data/context.db"
    out   = data.get("out") or "exports"
    # Phase HI export modes:
    #   mode 'en'  (default) → English only (unchanged)
    #   mode 'hi'            → Hindi only
    #   mode 'tri'           → Sanskrit + English + Hindi, side by side
    mode  = (data.get("mode") or ("hi" if data.get("hindi_only")
             else "tri" if data.get("hindi") else "en")).strip()
    cmd = py(script("export_html.py"), "--db", db, "--doc", doc, "--out", out)
    if mode == "hi":
        cmd += ["--hindi-only", "--title", data.get("title") or f"{doc} — Hindi Translation"]
    elif mode == "tri":
        cmd += ["--sanskrit", "--hindi", "--side-by-side",
                "--title", data.get("title") or f"{doc} — Sanskrit / English / Hindi"]
    else:
        cmd += ["--no-sanskrit", "--title", data.get("title") or f"{doc} — English Translation"]
    return jsonify({"job": launch("export", doc, cmd), "mode": mode})


@app.post("/api/queue/run")
def api_queue_run():
    """Run the full pipeline (OCR→Ingest→Translate→Export) for one doc serially."""
    data   = request.get_json(force=True) or {}
    doc    = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db      = data.get("db")      or "data/context.db"
    inbox   = data.get("inbox")   or "inbox"
    raw     = data.get("raw")     or "data/raw"
    exports = data.get("exports") or "exports"
    engine  = data.get("engine")  or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    dpi     = str(data.get("dpi") or 400)
    sleep   = str(data.get("sleep") or 0.6)
    skip_ocr       = bool(data.get("skip_ocr"))
    skip_ingest    = bool(data.get("skip_ingest"))
    skip_translate = bool(data.get("skip_translate"))
    skip_export    = bool(data.get("skip_export"))

    base = [script("pipeline_queue.py"),
            "--doc",     doc,
            "--inbox",   inbox,
            "--raw",     raw,
            "--db",      db,
            "--exports", exports,
            "--engine",  engine,
            "--dpi",     dpi,
            "--sleep",   sleep]

    # Stage 2 (ingest → translate → export): holds the TRANSLATE lock, so it
    # serializes safely with every other translation (single SQLite writer).
    def _launch_rest(_prev=None):
        rest = py(*base, "--skip-ocr")
        if skip_ingest:    rest.append("--skip-ingest")
        if skip_translate: rest.append("--skip-translate")
        if skip_export:    rest.append("--skip-export")
        return launch("pipeline", doc, rest)

    # If OCR is skipped (or the doc is already OCR'd), there is no OCR stage to run
    # in parallel — go straight to the translate-locked remainder.
    if skip_ocr:
        return jsonify({"job": _launch_rest(),
                        "message": "Ingest/Translate/Export queued (translate lock)."})

    # Stage 1 (OCR only): runs under the OCR semaphore, so it executes IN PARALLEL
    # with any ongoing translation instead of blocking it. When OCR finishes
    # successfully, `then` auto-launches Stage 2. This is the fix for
    # "OCR and translation can't run at the same time" (2026-08-26).
    ocr_cmd = py(*base, "--skip-ingest", "--skip-translate", "--skip-export")
    jid = launch("ocr", doc, ocr_cmd, then=_launch_rest)
    return jsonify({"job": jid,
                    "message": "OCR started in parallel with translation; "
                               "Ingest + Translate will run automatically when OCR completes."})


@app.post("/api/pipeline/translate-doc")
def api_translate_doc():
    """Translate a single already-ingested doc. Skips OCR — DB passages only.
    
    POST body: {"doc": "nirukta", "engine": "gemini:gemini-2.5-pro", "context": 5}
    """
    data    = request.get_json(force=True) or {}
    doc     = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    engine      = data.get("engine")      or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    context     = str(data.get("context", 5))
    sleep_s     = str(data.get("sleep", 0.8))
    min_quality = str(data.get("min_quality") or 0.35)  # Phase Q default (was 0.25)
    db          = data.get("db") or "data/context.db"
    lang        = (data.get("lang") or "en").strip()   # Phase HI
    # 'both' is NOT a language — it means "English then Hindi". It must route to
    # translate_both.py (two real passes), never be passed as --lang both, which
    # would file English into translations_l10n under the bogus code 'both' and
    # leave passages.translation empty (the AphorismsOfSandilya bug, 2026-08-28).
    if lang == "both":
        cmd = py(script("translate_both.py"),
                 "--db", db, "--doc", doc, "--engine", engine,
                 "--sleep", sleep_s, "--context", context, "--min-quality", min_quality)
        if data.get("hi_pure"):
            cmd += ["--hi-pure"]
        return jsonify({"job": launch("translate_both", doc, cmd),
                        "doc": doc, "engine": engine, "lang": "both"})
    cmd = py(script("translate_passages.py"),
             "--doc",         doc,
             "--db",          db,
             "--engine",      engine,
             "--context",     context,
             "--sleep",       sleep_s,
             "--min-quality", min_quality)
    kind = "translate"
    if lang != "en":
        cmd += ["--lang", lang]
        kind = f"translate_{lang}"
    jid = launch(kind, doc, cmd)
    return jsonify({"job": jid, "doc": doc, "engine": engine, "lang": lang})


@app.post("/api/pipeline/advance")
def api_pipeline_advance():
    """Run advance_pipeline.py — translate ALL OCR'd docs in priority order.
    
    Runs Re-ingest (safe) -> Translate -> Export for all 22 docs.
    Does NOT trigger new OCR. Already-translated passages are skipped.
    """
    cmd = py(script("advance_pipeline.py"))
    jid = launch("advance_pipeline", "all_docs", cmd)
    return jsonify({"job": jid, "message": "Advancing all OCRd docs through pipeline"})


# ──────────────────────────────────────────────────────────────────────────────
# QA panel API (Phase Q UI — 2026-08-16)
# Surfaces the CLI QA runbook (qa_scan / retranslate / refill) into the
# dashboard. /api/qa/summary and /api/qa/passages are READ-ONLY. The two writer
# actions (scan, heal) go through launch() so they serialize on the single
# translate semaphore and stream into the job log like every other job.
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/qa/summary")
def api_qa_summary():
    """Per-doc QA histogram for a language, computed from stored translation_qa.

    lang='en' (default) aggregates passages.translation_qa; any other code
    aggregates translations_l10n rows of that language. Read-only — never writes.
    """
    db_path = request.args.get("db", "data/context.db")
    lang    = (request.args.get("lang") or "en").strip()
    is_l10n = lang != "en"
    try:
        con   = sqlite3.connect(db_path)
        tset  = _tables(con)
        pcols = _cols(con, "passages")
        # Only count real verse rows when the schema records text_type.
        noise = ""
        if "text_type" in pcols:
            noise = "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"

        if is_l10n and "translations_l10n" not in tset:
            con.close()
            return jsonify({"lang": lang, "docs": [], "totals": {},
                            "note": "translations_l10n table not present — "
                                    "no target-language track yet."})

        if is_l10n:
            tcol, qcol = "l.translation", "l.translation_qa"
            join   = "LEFT JOIN translations_l10n l ON l.passage_id=p.id AND l.lang=?"
            params = [lang]
        else:
            tcol, qcol = "p.translation", "p.translation_qa"
            join, params = "", []

        sql = f"""
            SELECT d.code AS doc,
              COUNT(*) AS total,
              SUM(CASE WHEN TRIM(COALESCE({tcol},'')) <> '' THEN 1 ELSE 0 END) AS translated,
              SUM(CASE WHEN TRIM(COALESCE({tcol},'')) <> '' AND {qcol} IS NULL THEN 1 ELSE 0 END) AS unscored,
              AVG(CASE WHEN {qcol} IS NOT NULL THEN {qcol} END) AS mean_qa,
              SUM(CASE WHEN {qcol} IS NOT NULL AND {qcol} <  0.2 THEN 1 ELSE 0 END) AS b0,
              SUM(CASE WHEN {qcol} >= 0.2 AND {qcol} < 0.4 THEN 1 ELSE 0 END) AS b1,
              SUM(CASE WHEN {qcol} >= 0.4 AND {qcol} < 0.6 THEN 1 ELSE 0 END) AS b2,
              SUM(CASE WHEN {qcol} >= 0.6 AND {qcol} < 0.8 THEN 1 ELSE 0 END) AS b3,
              SUM(CASE WHEN {qcol} >= 0.8 THEN 1 ELSE 0 END) AS b4
            FROM passages p JOIN docs d ON d.id=p.doc_id
            {join}
            WHERE 1=1 {noise}
            GROUP BY d.code
            ORDER BY d.code
        """
        rows = con.execute(sql, params).fetchall()
        con.close()

        docs = []
        tot  = {"total": 0, "translated": 0, "pending": 0, "low": 0, "unscored": 0}
        for r in rows:
            doc, total, translated, unscored, mean_qa, b0, b1, b2, b3, b4 = r
            total      = int(total or 0)
            translated = int(translated or 0)
            unscored   = int(unscored or 0)
            buckets    = [int(b0 or 0), int(b1 or 0), int(b2 or 0), int(b3 or 0), int(b4 or 0)]
            scored     = sum(buckets)
            pending    = max(0, total - translated)
            docs.append({
                "doc": doc, "total": total, "translated": translated,
                "pending": pending, "scored": scored, "unscored": unscored,
                "low": buckets[0],
                "mean_qa": round(mean_qa, 3) if mean_qa is not None else None,
                "buckets": buckets,
            })
            tot["total"]      += total
            tot["translated"] += translated
            tot["pending"]    += pending
            tot["low"]        += buckets[0]
            tot["unscored"]   += unscored
        return jsonify({"lang": lang, "docs": docs, "totals": tot})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.get("/api/qa/passages/<doc>")
def api_qa_passages(doc):
    """List the weakest rows for a doc/lang (for inspection in the QA panel)."""
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    db_path = request.args.get("db", "data/context.db")
    lang    = (request.args.get("lang") or "en").strip()
    below   = float(request.args.get("below", 0.6))
    limit   = min(int(request.args.get("limit", 40)), 200)
    is_l10n = lang != "en"
    try:
        con   = sqlite3.connect(db_path)
        pcols = _cols(con, "passages")
        vref  = "p.verse_ref" if "verse_ref" in pcols else "NULL"
        # Same real-verse filter the summary uses, so the inspector never lists a
        # noise/frontmatter row the histogram already excluded.
        noise = ("AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
                 if "text_type" in pcols else "")
        if is_l10n:
            sql = f"""SELECT p.page_no, p.idx, {vref}, l.translation_qa,
                             substr(p.text,1,140), substr(l.translation,1,180)
                      FROM translations_l10n l
                      JOIN passages p ON p.id=l.passage_id
                      JOIN docs d ON d.id=p.doc_id
                      WHERE d.code=? AND l.lang=? AND l.translation_qa IS NOT NULL
                            AND l.translation_qa < ? {noise}
                      ORDER BY l.translation_qa ASC, p.page_no, p.idx LIMIT ?"""
            params = (doc, lang, below, limit)
        else:
            sql = f"""SELECT p.page_no, p.idx, {vref}, p.translation_qa,
                             substr(p.text,1,140), substr(p.translation,1,180)
                      FROM passages p JOIN docs d ON d.id=p.doc_id
                      WHERE d.code=? AND p.translation_qa IS NOT NULL
                            AND p.translation_qa < ? {noise}
                      ORDER BY p.translation_qa ASC, p.page_no, p.idx LIMIT ?"""
            params = (doc, below, limit)
        rows = con.execute(sql, params).fetchall()
        con.close()
        return jsonify({
            "doc": doc, "lang": lang, "below": below,
            "rows": [{"page_no": r[0], "idx": r[1], "verse_ref": r[2], "qa": r[3],
                      "text": r[4] or "", "translation": r[5] or ""} for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/qa/scan")
def api_qa_scan():
    """Run qa_scan.py --write to (re)score stored translations. Idempotent.

    Body: {doc?: str, lang?: 'en'|'hi', db?: str}. Omit doc to scan the whole
    corpus. Shares the translate semaphore (it writes translation_qa)."""
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    lang = (data.get("lang") or "en").strip()
    doc  = data.get("doc")
    argv = py(script("qa_scan.py"), "--db", db, "--lang", lang, "--write")
    label_doc = "all_docs"
    if doc:
        doc = _validate_doc(doc)
        if not doc:
            return jsonify({"error": "invalid doc"}), 400
        argv += ["--doc", doc]
        label_doc = doc
    jid = launch("qa_scan", label_doc, argv)
    return jsonify({"job": jid, "doc": label_doc, "lang": lang})


@app.post("/api/qa/heal")
def api_qa_heal():
    """One-click heal for a doc: qa_scan -> retranslate(below-qa) -> refill.

    Body: {doc: str, lang?: 'en'|'hi', below_qa?: float, engine?: str,
           limit?: int, skip_scan?: bool}. Non-destructive (archives every
           superseded translation to translation_history). Shares the translate
           semaphore, so it never writes concurrently with a translate job."""
    data = request.get_json(force=True) or {}
    doc  = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db     = data.get("db") or "data/context.db"
    lang   = (data.get("lang") or "en").strip()
    below  = str(data.get("below_qa") or 0.2)
    engine = data.get("engine") or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    argv = py(script("heal_lowqa.py"), "--db", db, "--doc", doc,
              "--below-qa", below, "--lang", lang, "--engine", engine)
    if data.get("limit"):
        argv += ["--limit", str(int(data["limit"]))]
    if data.get("skip_scan"):
        argv += ["--skip-scan"]
    jid = launch("qa_heal", doc, argv)
    return jsonify({"job": jid, "doc": doc, "lang": lang, "below_qa": below, "engine": engine})


@app.get("/api/passages/<doc>")
def api_passages(doc):
    """Live JSON feed of passages for the reader page. Returns all verse metadata."""
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    db_path = request.args.get("db", "data/context.db")
    page    = int(request.args.get("page", 1))
    limit   = min(int(request.args.get("limit", 50)), 200)
    offset  = (page - 1) * limit
    text_type_filter = request.args.get("text_type", "")  # e.g. "mula" to see only root text
    try:
        con = sqlite3.connect(db_path)
        # Dynamically detect which columns exist (handles old DBs)
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        tset = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        extra_selects = ", ".join([
            f"p.{c}" for c in
            ["verse_ref", "chapter", "text_type", "chandas", "iast", "quality_score", "translation_score"]
            if c in cols
        ])
        if extra_selects:
            extra_selects = ", " + extra_selects

        # Language-aware translation source: 'en' reads passages.translation; any
        # other code reads translations_l10n for that language (Phase HI). This is
        # what makes the /reader page multilingual.
        lang = (request.args.get("lang") or "en").strip()
        if lang != "en" and "translations_l10n" in tset:
            join_l10n  = "LEFT JOIN translations_l10n l ON l.passage_id=p.id AND l.lang=?"
            trans_col  = "l.translation"
            l10n_param = [lang]
        else:
            lang = "en"
            join_l10n, trans_col, l10n_param = "", "p.translation", []

        # Which languages actually have content for this doc (drives the switcher).
        available_langs = ["en"]
        if "translations_l10n" in tset:
            for (lg,) in con.execute(
                "SELECT DISTINCT l.lang FROM translations_l10n l "
                "JOIN passages p ON p.id=l.passage_id JOIN docs d ON d.id=p.doc_id "
                "WHERE d.code=? AND TRIM(COALESCE(l.translation,''))<>'' ORDER BY l.lang",
                (doc,)
            ):
                if lg and lg not in available_langs:
                    available_langs.append(lg)

        type_clause = ""
        type_params = []
        if text_type_filter:
            type_clause = " AND COALESCE(p.text_type,'mula')=?"
            type_params = [text_type_filter]

        total = con.execute(
            f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?{type_clause}",
            (doc, *type_params)
        ).fetchone()[0]
        translated = con.execute(
            f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id {join_l10n} "
            f"WHERE d.code=? AND TRIM(COALESCE({trans_col},''))<>''{type_clause}",
            (*l10n_param, doc, *type_params)
        ).fetchone()[0]
        # Count by text_type
        type_counts = {}
        if "text_type" in cols:
            for row in con.execute(
                "SELECT COALESCE(text_type,'mula'), COUNT(*) FROM passages p "
                "JOIN docs d ON d.id=p.doc_id WHERE d.code=? GROUP BY text_type", (doc,)
            ):
                type_counts[row[0]] = row[1]

        rows = con.execute(
            f"SELECT p.page_no, p.idx, p.text, {trans_col}{extra_selects} "
            f"FROM passages p JOIN docs d ON d.id=p.doc_id {join_l10n} "
            f"WHERE d.code=?{type_clause} ORDER BY p.page_no, p.idx LIMIT ? OFFSET ?",
            (*l10n_param, doc, *type_params, limit, offset)
        ).fetchall()
        con.close()

        def row_to_dict(r):
            d = {"page_no": r[0], "idx": r[1], "text": r[2] or "", "translation": r[3] or ""}
            col_names = ["verse_ref","chapter","text_type","chandas","iast","quality_score","translation_score"]
            for i, c in enumerate(col_names):
                if c in cols and 4 + i < len(r):
                    d[c] = r[4 + i]
            return d

        return jsonify({
            "doc": doc,
            "total": total,
            "translated": translated,
            "lang": lang,
            "available_langs": available_langs,
            "type_counts": type_counts,
            "page": page,
            "limit": limit,
            "passages": [row_to_dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.get("/api/queue/<doc>")
def api_queue_passages(doc):
    """Return pending untranslated passages with quality scores for a doc."""
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    db_path = request.args.get("db", "data/context.db")
    limit = int(request.args.get("limit", 200))
    try:
        con = sqlite3.connect(db_path)
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        extra_sel = []
        if "quality_score" in cols: extra_sel.append("p.quality_score")
        if "verse_ref"     in cols: extra_sel.append("p.verse_ref")
        if "text_type"     in cols: extra_sel.append("p.text_type")
        extra_sql = (", " + ", ".join(extra_sel)) if extra_sel else ""
        rows = con.execute(
            f"""SELECT p.rowid, p.page_no, p.idx, p.text{extra_sql}
                FROM passages p JOIN docs d ON d.id=p.doc_id
                WHERE d.code=?
                  AND COALESCE(TRIM(p.translation),'')=''
                  AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
                ORDER BY p.page_no, p.idx LIMIT ?""",
            (doc, limit)
        ).fetchall()
        con.close()
        extra_names = []
        if "quality_score" in cols: extra_names.append("quality_score")
        if "verse_ref"     in cols: extra_names.append("verse_ref")
        if "text_type"     in cols: extra_names.append("text_type")
        def row_to_dict(r):
            d = {"rowid": r[0], "page_no": r[1], "idx": r[2], "text": (r[3] or "")[:200]}
            for i, c in enumerate(extra_names):
                if 4 + i < len(r):
                    d[c] = r[4 + i]
            return d
        return jsonify({"doc": doc, "pending": [row_to_dict(r) for r in rows], "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/queue/<doc>/skip")
def api_queue_skip(doc):
    """Add rowids to skip_rowids in translation_config.json."""
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    data = request.get_json(force=True) or {}
    rowids_raw = data.get("rowids", [])
    rowids = [int(r) for r in rowids_raw if str(r).isdigit() or (isinstance(r, int))]
    if not rowids:
        return jsonify({"error": "no valid rowids"}), 400
    config_path = ROOT / "data" / "translation_config.json"
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        existing = set(cfg.get("skip_rowids", []))
        existing.update(rowids)
        cfg["skip_rowids"] = sorted(existing)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"skipped": len(rowids), "total_skipped": len(existing)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _md_to_html(md: str) -> str:
    """Minimal, dependency-free Markdown -> HTML for the methodology page (handles the
    subset used in QUALITY_METHODOLOGY.md: #/##/### headings, fenced + inline code,
    **bold**, *italic*, - lists, --- rules, [text](url) links, paragraphs)."""
    lines = md.split("\n")
    out, i, in_ul = [], 0, False
    def esc(s): return _html.escape(s, quote=False)
    def inline(s):
        s = esc(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(esc(lines[i])); i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>"); i += 1; continue
        if in_ul and not ln.lstrip().startswith("- "):
            out.append("</ul>"); in_ul = False
        if ln.startswith("### "):   out.append("<h3>" + inline(ln[4:]) + "</h3>")
        elif ln.startswith("## "):  out.append("<h2>" + inline(ln[3:]) + "</h2>")
        elif ln.startswith("# "):   out.append("<h1>" + inline(ln[2:]) + "</h1>")
        elif ln.strip() == "---":   out.append("<hr/>")
        elif ln.lstrip().startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>" + inline(ln.lstrip()[2:]) + "</li>")
        elif ln.strip():            out.append("<p>" + inline(ln) + "</p>")
        i += 1
    if in_ul: out.append("</ul>")
    return "\n".join(out)


@app.get("/methodology")
def methodology():
    """Transparent, human-readable quality methodology (renders QUALITY_METHODOLOGY.md)."""
    try:
        md = (ROOT / "QUALITY_METHODOLOGY.md").read_text(encoding="utf-8")
    except Exception:
        md = "# Quality methodology\n\n(QUALITY_METHODOLOGY.md is not present on this install.)"
    inner = _md_to_html(md)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Srangam &mdash; How we measure quality</title>
<style>
:root{{--bg:#0b0a08;--card:#161410;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58;--green:#5aaa7a}}
*{{box-sizing:border-box}} body{{background:var(--bg);color:var(--cream);font-family:'EB Garamond',Georgia,serif;line-height:1.65;margin:0}}
header{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 24px;position:sticky;top:0}}
header a{{color:var(--muted);text-decoration:none;font-family:Inter,sans-serif;font-size:12px}} header a:hover{{color:var(--gold)}}
main{{max-width:820px;margin:0 auto;padding:28px 22px 70px}}
h1{{color:var(--gold);font-family:Inter,sans-serif;font-size:25px;margin:0 0 8px}}
h2{{color:var(--gold);font-family:Inter,sans-serif;font-size:18px;margin:26px 0 8px;border-bottom:1px solid var(--border);padding-bottom:4px}}
h3{{color:var(--cream);font-family:Inter,sans-serif;font-size:14px;margin:16px 0 4px}}
pre{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px 14px;overflow-x:auto}}
code{{font-family:'JetBrains Mono',monospace;font-size:13px;background:var(--card);padding:1px 5px;border-radius:4px;color:var(--gold)}}
pre code{{background:none;padding:0;color:var(--green)}}
ul{{padding-left:22px}} li{{margin:3px 0}} hr{{border:none;border-top:1px solid var(--border);margin:22px 0}}
em{{color:var(--muted)}} strong{{color:var(--cream)}} a{{color:var(--gold)}}
</style></head><body>
<header><a href="/library">&#8592; Library</a> &nbsp;&middot;&nbsp; <a href="/">Dashboard</a></header>
<main>{inner}</main></body></html>"""


@app.get("/library")
def library():
    """Reader front door: every translated text, grouped by category, with
    EN/HI availability and a Read link into the multilingual reader."""
    import html as _html
    from collections import OrderedDict
    db_path = request.args.get("db", "data/context.db")
    try:
        con = sqlite3.connect(db_path)
        tset = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        # docs has no 'title' column in this schema (id, code, category, src_path,
        # glossary, created_at) — referencing it crashed /library. Detect it so the
        # page works whether or not a future migration adds a title (2026-08-23).
        dcols = {r[1] for r in con.execute("PRAGMA table_info(docs)")}
        title_expr = "COALESCE(d.title, d.code)" if "title" in dcols else "d.code"
        rows = con.execute(
            f"SELECT d.code, {title_expr}, COALESCE(d.category,'other'), "
            "COUNT(p.id), "
            "SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) "
            "FROM docs d LEFT JOIN passages p ON p.doc_id=d.id "
            "WHERE d.code NOT LIKE '%-RETIRED' "        # hide retired docs (reversible)
            "GROUP BY d.id ORDER BY COALESCE(d.category,'other'), d.code"
        ).fetchall()
        hi = {}
        if "translations_l10n" in tset:
            for code, n in con.execute(
                "SELECT d.code, COUNT(*) FROM translations_l10n l "
                "JOIN passages p ON p.id=l.passage_id JOIN docs d ON d.id=p.doc_id "
                "WHERE l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>'' GROUP BY d.code"):
                hi[code] = n
        # Mean STRUCTURAL translation QA per doc (translation_qa) — surfaced as a badge
        # with a link to the methodology, so quality is transparent, not hidden.
        qa = {}
        try:
            for code, avgqa in con.execute(
                "SELECT d.code, AVG(p.translation_qa) FROM passages p "
                "JOIN docs d ON d.id=p.doc_id WHERE p.translation_qa IS NOT NULL GROUP BY d.code"):
                if avgqa is not None:
                    qa[code] = round(float(avgqa), 2)
        except Exception:
            qa = {}
        con.close()
    except Exception as e:
        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500

    cats = OrderedDict()
    total_docs = total_en = total_hi = 0
    for code, title, cat, total, en in rows:
        en = int(en or 0)
        if en == 0:
            continue  # only list readable texts
        total_docs += 1; total_en += en
        h = int(hi.get(code, 0) or 0); total_hi += h
        cats.setdefault(cat, []).append((code, title, int(total or 0), en, h, qa.get(code)))

    body = ""
    if not cats:
        body = ('<div class="empty">No translated texts yet. '
                'Translate a document, then it appears here.</div>')
    for cat, docs in cats.items():
        body += f'<h2 class="cat">{_html.escape(cat)}</h2><div class="grid">'
        for code, title, total, en, h, qadoc in docs:
            pct = round(100 * en / total) if total else 0
            hi_badge = f'<span class="badge hi">&#2361;&#2367; {h}</span>' if h else ''
            qa_badge = ''
            if qadoc is not None:
                qcls = 'q-hi' if qadoc >= 0.8 else ('q-mid' if qadoc >= 0.6 else 'q-lo')
                qa_badge = (f'<span class="badge {qcls}" title="Mean structural translation QA '
                            f'(translation_qa {qadoc:.2f}). Click “Quality methodology” to see how this is computed.">'
                            f'QA {int(round(qadoc*100))}</span>')
            # "Proceed with pending translation" affordance: offer to finish the
            # English, and to add Hindi wherever English exists but Hindi does not.
            acts = ''
            if pct < 100:
                acts += (f'<button class="tr-rest" title="Translate the remaining English verses"'
                         f' onclick="translateRest(\'{code}\',\'en\',this)">&#9889; Finish EN</button>')
            if h < en:
                acts += (f'<button class="tr-rest hi" title="Translate Hindi for verses that have English but no Hindi"'
                         f' onclick="translateRest(\'{code}\',\'hi\',this)">&#2361;&#2367; Add Hindi</button>')
            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
            body += (
                f'<div class="card-wrap">'
                f'<a class="card" href="/reader/{code}">'
                f'<div class="ttl">{_html.escape(title)}</div>'
                f'<div class="code">{_html.escape(code)}</div>'
                f'<div class="bar"><i style="width:{pct}%"></i></div>'
                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{hi_badge}{qa_badge}'
                f'<span class="pct">{pct}%</span></div></a>'
                f'{acts_html}</div>'
            )
        body += '</div>'

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Srangam &mdash; Corpus Library</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@500;700&family=EB+Garamond&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58;--green:#5aaa7a;--blue:#5b9bd5}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--cream);font-family:'EB Garamond',Georgia,serif;min-height:100vh}}
header{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:10}}
header .back{{color:var(--muted);font-size:12px;text-decoration:none;font-family:'Inter',sans-serif}}
header .back:hover{{color:var(--gold)}}
header h1{{font-size:20px;color:var(--gold);font-family:'Inter',sans-serif;font-weight:700;letter-spacing:.5px}}
header .sub{{color:var(--muted);font-size:12px;font-family:'Inter',sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:24px 20px 60px}}
.cat{{font-family:'Inter',sans-serif;font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--gold);margin:26px 0 12px;border-bottom:1px solid var(--border);padding-bottom:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.card{{display:block;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;text-decoration:none;color:inherit;transition:all .15s}}
.card:hover{{border-color:var(--gold);background:var(--card2);transform:translateY(-2px)}}
.ttl{{font-size:17px;color:var(--cream);margin-bottom:2px;font-weight:500}}
.code{{font-family:'Inter',monospace;font-size:10px;color:var(--muted);margin-bottom:10px}}
.bar{{height:5px;background:var(--border);border-radius:4px;overflow:hidden;margin-bottom:8px}}
.bar i{{display:block;height:100%;background:linear-gradient(90deg,var(--gold),var(--green))}}
.meta{{display:flex;gap:6px;align-items:center;font-family:'Inter',sans-serif;font-size:10px}}
.badge{{border-radius:20px;padding:2px 8px;font-weight:600}}
.badge.en{{background:#22304a;color:var(--blue)}}
.badge.hi{{background:#3a2a0f;color:var(--gold);font-family:'Noto Serif Devanagari',serif}}
.badge.q-hi{{background:#12351f;color:var(--green)}}
.badge.q-mid{{background:#3a2f0f;color:var(--gold)}}
.badge.q-lo{{background:#3a1616;color:#d98a8a}}
.pct{{margin-left:auto;color:var(--muted)}}
.empty{{color:var(--muted);text-align:center;padding:60px 20px;font-family:'Inter',sans-serif}}
.card-wrap{{display:flex;flex-direction:column}}
.cardacts{{display:flex;gap:6px;margin-top:6px}}
.tr-rest{{flex:1;background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 8px;font-family:'Inter',sans-serif;font-size:10.5px;font-weight:600;cursor:pointer;transition:all .15s}}
.tr-rest:hover{{border-color:var(--gold);color:var(--gold)}}
.tr-rest.hi{{font-family:'Noto Serif Devanagari',serif}}
.tr-rest:disabled{{opacity:.6;cursor:default}}
</style></head><body>
<header>
  <a class="back" href="/">&#8592; Dashboard</a>
  <h1>&#2384; Srangam Library</h1>
  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses</span>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
</header>
<main>{body}</main>
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-family:'Inter',sans-serif;font-size:13px;display:none;z-index:50"></div>
<script>
function _toast(m){{var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){{t.style.display='none';}},4200);}}
async function translateRest(doc, lang, btn){{
  btn.disabled=true; var orig=btn.textContent; btn.textContent='starting…';
  try{{
    var r=await fetch('/api/translate',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{doc:doc,lang:lang,limit:100000}})}});
    var d=await r.json();
    if(d.job){{ _toast('Translating '+(lang==='both'?'EN+हि':lang.toUpperCase())+' for '+doc+' — watch the Dashboard for progress.'); btn.textContent='queued ✓'; }}
    else{{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; }}
  }}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}
}}
</script>
</body></html>"""


@app.post("/api/quick_translate")
def api_quick_translate():
    """Ad-hoc, on-demand translation of arbitrary Sanskrit into English + Hindi.

    Synchronous (the caller clicked and waits a few seconds). Uses a THROWAWAY
    in-memory DB so it never contends with the live context.db — safe to use
    even while translate/heal jobs are writing. No corpus row is touched."""
    data   = request.get_json(force=True) or {}
    text   = (data.get("text") or "").strip()
    engine = data.get("engine") or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    want   = data.get("langs") or ["en", "hi"]
    if not text:
        return jsonify({"error": "no text supplied"}), 400
    if len(text) > 8000:
        return jsonify({"error": "text too long (max 8000 chars) — translate in parts"}), 400
    try:
        import sys as _sys
        _sys.path.insert(0, str(SCRIPTS))
        from infer_mt import translate_batch
        from db_utils import ensure_schema, migrate_schema
        mem = sqlite3.connect(":memory:")
        ensure_schema(mem)
        try:
            migrate_schema(mem)
        except Exception:
            pass
        out = {}
        for lg in want:
            if lg not in ("en", "hi"):
                continue
            try:
                res = translate_batch(mem, [text], engine=engine, tgt=lg)
                out[lg] = (res[0] if res else "") or ""
            except Exception as e:
                out[lg] = f"[error: {type(e).__name__}: {e}]"
        mem.close()
        return jsonify({"engine": engine, "text": text, "translations": out})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.get("/translate")
def quick_translate_page():
    """On-demand translator: paste any Sanskrit, get English + Hindi right now."""
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Srangam &mdash; Quick Translate</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;500;600&family=EB+Garamond:ital@0;1&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58;--green:#5aaa7a;--blue:#5b9bd5}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'EB Garamond',Georgia,serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:10}
header a.back{color:var(--muted);font-size:12px;text-decoration:none;font-family:'Inter',sans-serif}
header a.back:hover{color:var(--gold)}
header h1{font-size:20px;color:var(--gold);font-family:'Inter',sans-serif;font-weight:700;letter-spacing:.5px}
main{max-width:1100px;margin:0 auto;padding:24px 20px 60px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;font-family:'Inter',sans-serif;font-size:12px}
select,textarea{background:var(--card2);border:1px solid var(--border);color:var(--cream);border-radius:8px;font-size:15px}
select{padding:7px 10px;font-family:'Inter',sans-serif;font-size:12px}
textarea{width:100%;min-height:120px;padding:14px 16px;font-family:'Noto Serif Devanagari',serif;line-height:1.9;resize:vertical}
.langs{display:flex;gap:6px}
.chip{border:1px solid var(--border);border-radius:20px;padding:4px 12px;cursor:pointer;color:var(--muted);font-weight:600;user-select:none}
.chip.on{background:var(--gold);color:#000;border-color:var(--gold)}
.btn{background:linear-gradient(135deg,#3a2a0f,#2a1f0a);color:var(--gold);border:1px solid var(--gold);border-radius:8px;padding:9px 22px;font-size:14px;font-weight:700;cursor:pointer;font-family:'Inter',sans-serif}
.btn:hover{background:var(--gold);color:#000}
.btn:disabled{opacity:.5;cursor:wait}
.results{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:20px}
@media(max-width:720px){.results{grid-template-columns:1fr}}
.rescard{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px 18px;min-height:80px}
.rescard h3{font-family:'Inter',sans-serif;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}
.rescard .en{color:var(--blue)} .rescard .hi{color:var(--gold)}
.res-en{font-size:16px;line-height:1.7;color:var(--cream)}
.res-hi{font-family:'Noto Serif Devanagari',serif;font-size:16px;line-height:1.95;color:var(--cream)}
.copy{font-family:'Inter',sans-serif;font-size:10px;color:var(--muted);border:1px solid var(--border);border-radius:5px;padding:2px 8px;cursor:pointer;background:transparent}
.copy:hover{color:var(--gold);border-color:var(--gold)}
.muted{color:var(--muted);font-family:'Inter',sans-serif;font-size:12px}
</style></head><body>
<header>
  <a class="back" href="/">&#8592; Dashboard</a>
  <h1>&#9889; Quick Translate</h1>
  <span class="muted">paste Sanskrit &rarr; get English + Hindi, on demand</span>
</header>
<main>
  <div class="row">
    <span class="muted">Engine</span>
    <select id="engine">
      <option value="gemini:gemini-2.5-flash">Gemini 2.5 Flash (default)</option>
      <option value="gemini:gemini-2.5-pro">Gemini 2.5 Pro (higher quality)</option>
      <option value="openai:gpt-4o">GPT-4o</option>
    </select>
    <span class="muted" style="margin-left:12px">Into</span>
    <div class="langs">
      <span class="chip on" id="chip-en" onclick="toggleLang('en')">English</span>
      <span class="chip on" id="chip-hi" onclick="toggleLang('hi')">&#2361;&#2367;&#2344;&#2381;&#2342;&#2368;</span>
    </div>
  </div>
  <textarea id="src" placeholder="Paste Devanagari Sanskrit here (a verse, a line, a paragraph)&hellip;"></textarea>
  <div class="row" style="margin-top:12px">
    <button class="btn" id="go" onclick="run()">&#9889; Translate</button>
    <span class="muted" id="status"></span>
  </div>
  <div class="results" id="results" style="display:none">
    <div class="rescard" id="card-en"><h3><span class="en">&#x1F4DC; English</span><button class="copy" onclick="copyRes('en')">copy</button></h3><div class="res-en" id="out-en"></div></div>
    <div class="rescard" id="card-hi"><h3><span class="hi">&#2361;&#2367;&#2344;&#2381;&#2342;&#2368; Hindi</span><button class="copy" onclick="copyRes('hi')">copy</button></h3><div class="res-hi" id="out-hi"></div></div>
  </div>
</main>
<script>
var LANGS = {en:true, hi:true};
function toggleLang(l){ LANGS[l]=!LANGS[l]; document.getElementById('chip-'+l).classList.toggle('on',LANGS[l]); }
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function copyRes(l){ var t=document.getElementById('out-'+l).textContent||''; navigator.clipboard && navigator.clipboard.writeText(t); }
async function run(){
  var text=document.getElementById('src').value.trim();
  var want=Object.keys(LANGS).filter(function(k){return LANGS[k];});
  if(!text){ document.getElementById('status').textContent='Enter some Sanskrit first.'; return; }
  if(!want.length){ document.getElementById('status').textContent='Pick at least one language.'; return; }
  var btn=document.getElementById('go'); btn.disabled=true;
  document.getElementById('status').textContent='Translating… (a few seconds)';
  document.getElementById('results').style.display='grid';
  document.getElementById('card-en').style.display = LANGS.en?'block':'none';
  document.getElementById('card-hi').style.display = LANGS.hi?'block':'none';
  document.getElementById('out-en').textContent=''; document.getElementById('out-hi').textContent='';
  try{
    var r=await fetch('/api/quick_translate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:text,engine:document.getElementById('engine').value,langs:want})});
    var d=await r.json();
    if(d.error){ document.getElementById('status').textContent='Error: '+d.error; btn.disabled=false; return; }
    var tr=d.translations||{};
    if('en' in tr) document.getElementById('out-en').textContent = tr.en || '(empty — source may be illegible)';
    if('hi' in tr) document.getElementById('out-hi').textContent = tr.hi || '(empty — source may be illegible)';
    document.getElementById('status').textContent='Done · engine '+esc(d.engine);
  }catch(e){ document.getElementById('status').textContent='Failed: '+e; }
  btn.disabled=false;
}
document.getElementById('src').addEventListener('keydown',function(e){ if((e.ctrlKey||e.metaKey)&&e.key==='Enter') run(); });
</script>
</body></html>"""


@app.get("/reader/<doc>")
def reader(doc):
    """Scholarly three-column reader: Sanskrit | English | Footnotes/Metadata."""
    doc = _validate_doc(doc)
    if not doc:
        return "Invalid document name", 400
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{doc} — Sanskrit Reader</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;500;600;700&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
:root{{
  --bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;
  --gold:#c9952a;--gold-dim:#c9952a50;--cream:#ede4cc;--muted:#7a6d58;
  --green:#5aaa7a;--blue:#5b9bd5;--red:#c06060;--amber:#d4852a;
  --dev-col:#e8dcc8;--en-col:#c8d4e8;--meta-col:#9aaa8a;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--cream);font-family:'EB Garamond',Georgia,serif;min-height:100vh;font-size:16px}}
/* ── Header ── */
header{{background:var(--card);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:20;backdrop-filter:blur(8px)}}
.back{{color:var(--muted);font-size:12px;text-decoration:none;font-family:'Inter',sans-serif}}
.back:hover{{color:var(--gold)}}
h1{{font-size:17px;color:var(--gold);font-weight:600;font-family:'Inter',sans-serif;letter-spacing:.5px}}
.prog-wrap{{flex:1;max-width:240px}}
.prog-bar{{background:var(--border);border-radius:8px;height:4px;overflow:hidden}}
.prog-bar i{{display:block;height:100%;background:linear-gradient(90deg,var(--gold),var(--amber));border-radius:8px;transition:width .6s ease}}
.prog-pct{{font-size:10px;color:var(--muted);margin-top:3px;font-family:'Inter',sans-serif}}
.filter-bar{{display:flex;gap:6px;align-items:center}}
.filter-btn{{background:var(--card2);color:var(--muted);border:1px solid var(--border);border-radius:20px;padding:3px 10px;font-size:10px;cursor:pointer;font-family:'Inter',sans-serif;transition:all .2s}}
.filter-btn.active{{background:var(--gold-dim);color:var(--gold);border-color:var(--gold)}}
.lang-bar{{display:flex;gap:6px;align-items:center}}
.lang-btn{{background:var(--card2);color:var(--muted);border:1px solid var(--border);border-radius:20px;padding:3px 12px;font-size:11px;cursor:pointer;font-family:'Inter',sans-serif;transition:all .2s;font-weight:600}}
.lang-btn.active{{background:var(--gold);color:#000;border-color:var(--gold)}}
.refresh-label{{font-size:10px;color:var(--muted);font-family:'Inter',sans-serif}}
/* ── Main ── */
main{{max-width:1400px;margin:0 auto;padding:20px 16px 48px}}
/* ── Page group ── */
.page-group{{margin-bottom:40px}}
.page-label{{
  font-family:'Inter',sans-serif;font-size:10px;color:var(--muted);
  text-transform:uppercase;letter-spacing:2px;
  border-bottom:1px solid var(--border);padding-bottom:6px;margin-bottom:14px;
  display:flex;gap:12px;align-items:center
}}
.chapter-badge{{background:var(--gold-dim);color:var(--gold);border-radius:10px;padding:1px 8px;font-size:9px}}
/* ── Three-column verse card ── */
.verse-card{{
  display:grid;grid-template-columns:2fr 2fr 1fr;gap:0;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  margin-bottom:10px;overflow:hidden;transition:border-color .2s;
}}
.verse-card:hover{{border-color:var(--gold-dim)}}
.col-dev,.col-en,.col-meta{{padding:14px 16px}}
.col-dev{{border-right:1px solid var(--border);background:linear-gradient(135deg,var(--card),#1a1710)}}
.col-en{{border-right:1px solid var(--border)}}
.col-meta{{background:var(--card2);font-family:'Inter',sans-serif}}
/* ── Column labels ── */
.col-label{{font-family:'Inter',sans-serif;font-size:9px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.col-label-dev{{color:var(--gold)}}
.col-label-en{{color:var(--blue)}}
.col-label-meta{{color:var(--meta-col)}}
/* ── Sanskrit text ── */
.dev-text{{font-family:'Noto Serif Devanagari',serif;font-size:15px;line-height:2.0;color:var(--dev-col);white-space:pre-wrap}}
/* ── English text ── */
.en-text{{font-size:15px;line-height:1.75;color:var(--en-col);font-style:italic}}
.en-text em{{font-style:normal;color:var(--cream)}}
/* Localized (e.g. Hindi) translation: Devanagari face, upright, not italic. */
.hi-text{{font-family:'Noto Serif Devanagari',serif;font-size:15px;line-height:1.9;color:var(--cream)}}
.en-pending{{color:var(--muted);font-style:italic;font-size:13px;font-family:'Inter',sans-serif}}
.en-illegible{{color:#c06060;font-style:italic;font-size:12px;font-family:'Inter',sans-serif}}
.tr-one-btn{{margin-top:8px;background:#3a2a0f;border:1px solid #7a5a1a;color:#e0b050;border-radius:5px;padding:4px 11px;font-size:11px;cursor:pointer;font-family:'Inter',sans-serif;font-weight:600}}
.tr-one-btn:hover{{background:var(--gold);color:#000}}
.tr-one-btn:disabled{{opacity:.6;cursor:wait}}
/* ── Metadata column ── */
.meta-row{{display:flex;flex-direction:column;gap:8px}}
.meta-item{{font-size:11px;line-height:1.4}}
.meta-key{{color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:1px}}
.meta-val{{color:var(--meta-col)}}
.verse-ref-badge{{
  display:inline-block;background:var(--gold-dim);color:var(--gold);
  border-radius:4px;padding:1px 7px;font-size:11px;font-weight:600;margin-bottom:6px
}}
.type-badge{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.type-mula{{background:#5aaa7a20;color:var(--green)}}
.type-tika{{background:#5b9bd520;color:var(--blue)}}
.type-prose{{background:#c0606020;color:var(--red)}}
.type-colophon{{background:#d4852a20;color:var(--amber)}}
.type-noise{{background:#44444420;color:#666}}
.quality-bar{{height:3px;border-radius:2px;background:var(--border);overflow:hidden;margin-top:3px}}
.quality-bar i{{display:block;height:100%;border-radius:2px}}
.iast-text{{font-family:'EB Garamond',serif;font-size:12px;color:var(--muted);margin-top:4px;line-height:1.5;word-break:break-all}}
/* ── Loading / Empty ── */
.loading{{text-align:center;padding:60px;color:var(--muted);font-family:'Inter',sans-serif;font-size:14px}}
/* ── Pagination ── */
.pagination{{display:flex;gap:8px;justify-content:center;padding:20px;align-items:center}}
.pag-btn{{background:var(--card);color:var(--gold);border:1px solid var(--border);padding:6px 18px;border-radius:6px;cursor:pointer;font-family:'Inter',sans-serif;font-size:12px;transition:all .2s}}
.pag-btn:hover{{border-color:var(--gold);background:var(--gold-dim)}}
.pag-label{{color:var(--muted);font-family:'Inter',sans-serif;font-size:12px}}
footer{{text-align:center;padding:20px;color:var(--muted);font-size:12px;font-family:'Inter',sans-serif;border-top:1px solid var(--border)}}
</style>
</head>
<body>
<header>
  <a href="/" class="back">&#8592; Dashboard</a>
  <h1 id="docTitle">{doc.replace('_',' ').title()}</h1>
  <div class="prog-wrap">
    <div class="prog-bar"><i id="progBar" style="width:0%"></i></div>
    <div class="prog-pct"><span id="progText">Loading&hellip;</span></div>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" id="filter-all"    onclick="setFilter('')">All</button>
    <button class="filter-btn"        id="filter-mula"   onclick="setFilter('mula')">M&#363;la</button>
    <button class="filter-btn"        id="filter-tika"   onclick="setFilter('tika')">&#7788;&#299;k&#257;</button>
    <button class="filter-btn"        id="filter-prose"  onclick="setFilter('prose')">Prose</button>
  </div>
  <div class="lang-bar" id="langBar" title="Translation language"></div>
  <span class="refresh-label" id="refreshLabel">Auto &#8635;</span>
</header>
<main id="main"><div class="loading">Loading passages&hellip;</div></main>
<footer>Sanskrit Automaton v2 &mdash; Scholarly Reader &mdash; {doc}</footer>
<script>
const DOC = {json.dumps(doc)};
let currentPage = 1; const LIMIT = 50;
let refreshTimer = null; let activeFilter = '';
let activeLang = 'en';
const LANG_LABELS = {{ en: '&#x1F4DC; English', hi: '&#2361;&#2367;&#2344;&#2381;&#2342;&#2368; Hindi', sa: '&#2360;&#2306;&#2360;&#2381;&#2325;&#2371;&#2340;' }};
const LANG_SHORT  = {{ en: 'EN', hi: '&#2361;&#2367;', sa: 'SA' }};

function renderLangBar(available, current){{
  const bar = document.getElementById('langBar');
  if (!available || available.length <= 1){{ bar.innerHTML=''; return; }}
  bar.innerHTML = available.map(function(l){{
    const cls = 'lang-btn' + (l === current ? ' active' : '');
    const lab = LANG_SHORT[l] || String(l).toUpperCase();
    return '<button class="'+cls+'" onclick="setLang(\\''+l+'\\')" title="'+(LANG_LABELS[l]||l)+'">'+lab+'</button>';
  }}).join('');
}}

function setLang(l){{
  if (l === activeLang) return;
  activeLang = l;
  loadPage(1);
}}

// Garbage-OCR heuristic: low Devanagari density with notable Latin noise means
// the SOURCE is unreadable, so an empty translation is correct — the fix is
// re-OCR, not re-translation. We surface that instead of offering a translate.
function looksIllegible(t){{
  if (!t) return false;
  var s = String(t);
  var dev = (s.match(/[ऀ-ॿ]/g) || []).length;
  var lat = (s.match(/[A-Za-z]/g) || []).length;
  var tot = s.replace(/\\s/g,'').length || 1;
  return (dev / tot) < 0.45 && lat > 6;
}}

// On-demand translate of ONE verse into the active language; saves to the corpus.
async function translateVerse(page, idx, btn){{
  btn.disabled = true; var old = btn.innerHTML; btn.innerHTML = '&#8987; translating&hellip;';
  try{{
    var r = await fetch('/api/translate-one', {{method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{doc: DOC, page_no: page, idx: idx, lang: activeLang}})}});
    var j = await r.json();
    if (j.error){{ btn.innerHTML = old; btn.disabled = false; alert('Translate: ' + j.error); return; }}
    await pollOne(j.job);
    loadPage(currentPage);
  }} catch(e){{ btn.innerHTML = old; btn.disabled = false; }}
}}

async function pollOne(jid){{
  for (var i = 0; i < 150; i++){{
    await new Promise(function(res){{ setTimeout(res, 2000); }});
    try{{ var j = await (await fetch('/api/job/' + jid)).json(); if (!j.running) return; }}
    catch(e){{ return; }}
  }}
}}

function esc(s){{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

function chandas_display(c){{
  const map = {{
    anustubh:'Anu&#7779;&#7789;ubh (8&#215;4)',
    tristubh:'Tri&#7779;&#7789;ubh (11&#215;4)',
    jagati:'Jagat&#299; (12&#215;4)',
    sardula_vikridata:'&#346;&#257;rd&#363;lavikr&#299;&#7693;ita',
    malini:'M&#257;lin&#299;',
    vasantatilaka:'Vasantatilak&#257;',
    sloka:'&#346;loka',
  }};
  return map[c] || c || '';
}}

function quality_color(q){{
  if (!q && q!==0) return '#444';
  if (q >= 0.7) return '#5aaa7a';
  if (q >= 0.4) return '#d4852a';
  return '#c06060';
}}

function setFilter(f){{
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(function(b){{ b.classList.remove('active'); }});
  document.getElementById('filter-' + (f||'all')).classList.add('active');
  loadPage(1);
}}

async function loadPage(p){{
  currentPage = p;
  try{{
    let url = '/api/passages/' + DOC + '?page=' + p + '&limit=' + LIMIT + '&lang=' + activeLang;
    if (activeFilter) url += '&text_type=' + activeFilter;
    const r = await fetch(url);
    const d = await r.json();
    if (d.error){{ document.getElementById('main').innerHTML='<div class="loading">Error: '+esc(d.error)+'</div>'; return; }}
    // Sync to the language the server actually served (falls back to 'en' if the
    // requested track has no rows) and (re)draw the switcher from availability.
    activeLang = d.lang || 'en';
    renderLangBar(d.available_langs || ['en'], activeLang);
    const pct = d.total ? Math.round(100*d.translated/d.total) : 0;
    document.getElementById('progBar').style.width = pct + '%';
    document.getElementById('progText').textContent = d.translated + '/' + d.total + ' translated (' + pct + '%)';

    let html = '';
    let curPage = null; let curChapter = null;
    d.passages.forEach(function(p){{
      // Page group header
      if (p.page_no !== curPage){{
        if (curPage !== null) html += '</div>';
        let chBadge = '';
        if (p.chapter && p.chapter !== curChapter){{
          curChapter = p.chapter;
          chBadge = '<span class="chapter-badge">Adhy&#257;ya ' + esc(p.chapter) + '</span>';
        }}
        html += '<div class="page-group"><div class="page-label">Page ' + p.page_no + chBadge + '</div>';
        curPage = p.page_no;
      }}

      const hasTr = p.translation && p.translation.trim();
      const ttype = p.text_type || 'mula';
      const ref   = p.verse_ref;
      const chan  = p.chandas;
      const qual  = p.quality_score;
      const iast  = p.iast;

      // Type badge
      const typeBadge = '<span class="type-badge type-' + esc(ttype) + '">' + esc(ttype) + '</span>';

      // Quality bar
      const qPct = qual ? Math.round(qual * 100) : 0;
      const qColor = quality_color(qual);
      const qBar = '<div class="quality-bar"><i style="width:'+qPct+'%;background:'+qColor+'"></i></div>';

      // Build metadata column
      let metaHtml = '<div class="meta-row">';
      if (ref) metaHtml += '<div class="verse-ref-badge">&#2383; ' + esc(ref) + '</div>';
      metaHtml += typeBadge;
      if (chan){{
        metaHtml += '<div class="meta-item"><span class="meta-key">Chandas</span><span class="meta-val">' + chandas_display(chan) + '</span></div>';
      }}
      if (qual !== null && qual !== undefined){{
        metaHtml += '<div class="meta-item"><span class="meta-key">Quality ' + qPct + '%</span>' + qBar + '</div>';
      }}
      if (iast && iast.trim()){{
        metaHtml += '<div class="iast-text">' + esc(iast.substring(0,120)) + (iast.length>120?'&hellip;':'') + '</div>';
      }}
      metaHtml += '</div>';

      html += '<div class="verse-card">' +
        // Column 1: Sanskrit Devanagari
        '<div class="col-dev">' +
          '<div class="col-label col-label-dev">&#2344;&#2350;&#2307; Sanskrit</div>' +
          '<div class="dev-text">' + esc(p.text) + '</div>' +
        '</div>' +
        // Column 2: translation (English or localized, e.g. Hindi)
        '<div class="col-en">' +
          '<div class="col-label col-label-en">' + (LANG_LABELS[activeLang] || activeLang) + '</div>' +
          (hasTr
            ? '<div class="' + (activeLang === 'en' ? 'en-text' : 'hi-text') + '">' + esc(p.translation) + '</div>'
            : (looksIllegible(p.text)
                ? '<div class="en-illegible">&#9888; Source illegible &mdash; needs re-OCR, not translation</div>'
                : '<div class="en-pending">&#x231B; Not yet translated</div>'
                  + '<button class="tr-one-btn" onclick="translateVerse(' + p.page_no + ',' + p.idx + ',this)">&#9889; Translate to ' + (LANG_SHORT[activeLang] || String(activeLang).toUpperCase()) + '</button>')) +
        '</div>' +
        // Column 3: Metadata / Footnotes
        '<div class="col-meta">' +
          '<div class="col-label col-label-meta">&#x1F4CC; Notes</div>' +
          metaHtml +
        '</div>' +
      '</div>';
    }});
    if (curPage !== null) html += '</div>';
    if (d.passages.length === 0) html = '<div class="loading">No passages found for this filter. Try "All".</div>';

    // Pagination
    const totalPages = Math.ceil(d.total / LIMIT);
    if (totalPages > 1){{
      html += '<div class="pagination">';
      if (currentPage > 1) html += '<button class="pag-btn" onclick="loadPage('+(currentPage-1)+')">&#8592; Prev</button>';
      html += '<span class="pag-label">Page ' + currentPage + ' / ' + totalPages + '</span>';
      if (currentPage < totalPages) html += '<button class="pag-btn" onclick="loadPage('+(currentPage+1)+')">Next &#8594;</button>';
      html += '</div>';
    }}
    document.getElementById('main').innerHTML = html;
  }} catch(e){{
    document.getElementById('main').innerHTML = '<div class="loading">Error: ' + esc(String(e)) + '</div>';
  }}
}}

function scheduleRefresh(){{
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(function(){{ loadPage(currentPage); scheduleRefresh(); }}, 30000);
}}

loadPage(1);
scheduleRefresh();
</script>
</body>
</html>"""





# ──────────────────────────────────────────────────────────────────────────────
# Ask the Corpus — retrieval-augmented Q&A over the growing translations.
# FTS retrieves the most relevant translated verses; the chosen Gemini model
# answers USING ONLY those verses and cites each with a [doc verse_ref] tag.
# Read-only on the DB (safe while jobs write); the translation engine is untouched.
# ──────────────────────────────────────────────────────────────────────────────
_ASK_STOP = set(
    "the a an of to and or in on at for with is are was were be by that this those "
    "these he she it they his her its their who whom which what when where why how "
    "did do does said say once also then thus there here into from as not but".split()
)
try:                                   # reuse the engine's safety config if importable
    from infer_mt import _GEMINI_SAFETY as _ASK_SAFETY
except Exception:
    _ASK_SAFETY = None

_ASK_TOKEN_RE = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ'ऀ-ॿ]+")

def _ask_fts_query(q: str):
    toks = [t for t in _ASK_TOKEN_RE.findall((q or "").lower())
            if len(t) >= 3 and t not in _ASK_STOP]
    if not toks:
        return None
    return " OR ".join('"%s"' % t.replace('"', '') for t in toks[:12])

def _ask_retrieve(con, q, k=12):
    m = _ask_fts_query(q)
    if not m:
        return []
    try:
        return con.execute(
            """SELECT d.code, p.verse_ref, p.page_no, p.idx, p.translation
               FROM passages_fts f
               JOIN passages p ON p.rowid = f.rowid
               JOIN docs d ON d.id = p.doc_id
               WHERE passages_fts MATCH ?
                 AND TRIM(COALESCE(p.translation,'')) <> ''
                 AND d.code NOT LIKE '%-RETIRED'
               ORDER BY bm25(passages_fts) LIMIT ?""",
            (m, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def _ask_semantic_retrieve(con, q, k=12):
    """Vector (meaning-based) retrieval using passage_embeddings, if it exists
    and is populated. Returns a list of (code, verse_ref, page, idx, translation)
    ranked by cosine similarity, or None to signal 'fall back to keyword FTS'.
    Read-only; brute-force cosine over ~10^4 vectors is a few ms."""
    try:
        if not con.execute("SELECT COUNT(*) FROM passage_embeddings").fetchone()[0]:
            return None
    except sqlite3.OperationalError:
        return None                      # table not built yet → FTS fallback
    try:
        import numpy as np
        import google.generativeai as genai
    except Exception:
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    row = con.execute("SELECT model, dim FROM passage_embeddings "
                      "GROUP BY model ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    if not row:
        return None
    model, dim = row[0], int(row[1] or 0)
    try:
        genai.configure(api_key=key)
        res = genai.embed_content(model=model, content=q, task_type="retrieval_query")
        qv = np.asarray(res["embedding"] if isinstance(res, dict) else res.embedding,
                        dtype="float32")
    except Exception:
        return None                      # query-embed failed → FTS fallback
    n = float(np.linalg.norm(qv))
    if n > 0:
        qv = qv / n
    ids, mats = [], []
    for pid, blob in con.execute(
            "SELECT passage_id, vec FROM passage_embeddings WHERE model=?", (model,)):
        v = np.frombuffer(blob, dtype="float32")
        if dim and v.shape[0] != dim:
            continue
        ids.append(pid); mats.append(v)
    if not ids:
        return None
    sims = np.vstack(mats) @ qv          # both L2-normalised → dot == cosine
    order = np.argsort(-sims)[: max(k * 3, k)]   # over-fetch, then filter retired
    top_ids = [ids[j] for j in order]
    ph = ",".join("?" * len(top_ids))
    got = {r[0]: r for r in con.execute(
        f"""SELECT p.id, d.code, p.verse_ref, p.page_no, p.idx, p.translation
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE p.id IN ({ph}) AND d.code NOT LIKE '%-RETIRED'
              AND TRIM(COALESCE(p.translation,'')) <> ''""", top_ids)}
    out = []
    for pid in top_ids:
        r = got.get(pid)
        if r:
            out.append((r[1], r[2], r[3], r[4], r[5]))
        if len(out) >= k:
            break
    return out or None


_ASK_SYSTEM = (
    "You are a careful scholar of Sanskrit scripture. Answer the user's question "
    "USING ONLY the numbered passages provided, which are English translations of "
    "verses from a Sanskrit corpus. Cite every claim with the passage's bracket tag "
    "exactly as given, e.g. [MBh01 1.1.0]. If the passages do not contain the answer, "
    "say so plainly instead of inventing one. Be concise, precise, and scholarly; do "
    "not add outside knowledge unless you clearly label it as background context."
)

@app.post("/api/ask")
def api_ask():
    data = request.get_json(force=True) or {}
    q = (data.get("q") or "").strip()
    if not q:
        return jsonify({"error": "empty question"}), 400
    db = data.get("db") or "data/context.db"
    try:
        k = max(3, min(24, int(data.get("k") or 12)))
    except (TypeError, ValueError):
        k = 12
    engine = data.get("engine") or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    model = engine.split(":", 1)[1] if ":" in engine else engine
    # 1. Retrieve (read-only — never contends with the writer lock)
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except Exception as e:
        return jsonify({"error": f"cannot open db: {e}"}), 500
    mode = "keyword"
    try:
        rows = _ask_semantic_retrieve(con, q, k)   # meaning-based if embeddings built
        if rows:
            mode = "semantic"
        else:
            rows = _ask_retrieve(con, q, k)        # else keyword FTS
    finally:
        con.close()
    if not rows:
        return jsonify({"answer": "No matching passages were found in the corpus for that "
                        "question. Try different or more specific wording.", "sources": []})
    sources, ctx = [], []
    for i, (code, vref, page, idx, tr) in enumerate(rows, 1):
        tag = f"{code} {vref}" if vref else f"{code} p{page}.{idx}"
        sources.append({"n": i, "tag": tag, "doc": code, "verse_ref": vref,
                        "page_no": page, "idx": idx, "english": tr})
        ctx.append(f"[{i}] [{tag}] {(tr or '')[:600]}")
    user_msg = "PASSAGES:\n" + "\n".join(ctx) + f"\n\nQUESTION: {q}\n\nAnswer, citing [tags]:"
    # 2. LLM answer — self-contained Gemini config so the translation engine is untouched
    try:
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            return jsonify({"error": "GEMINI_API_KEY not set in .env", "sources": sources}), 500
        genai.configure(api_key=key)
        kwargs = dict(model_name=model,
                      generation_config=genai.GenerationConfig(temperature=0.2,
                                                               max_output_tokens=2048),
                      system_instruction=_ASK_SYSTEM)
        if _ASK_SAFETY is not None:
            kwargs["safety_settings"] = _ASK_SAFETY
        resp = genai.GenerativeModel(**kwargs).generate_content(user_msg)
        answer = (getattr(resp, "text", "") or "").strip() or \
                 "(The model returned no text — try rephrasing or a smaller k.)"
    except Exception as e:
        return jsonify({"error": f"LLM error: {e}", "sources": sources}), 500
    return jsonify({"answer": answer, "sources": sources, "engine": engine,
                    "k": k, "mode": mode})


@app.get("/ask")
def ask_page():
    return send_from_directory(str(SCRIPTS), "ask.html")


# ── Launch Datasette (SQL explorer) on a consistent snapshot, from the UI ──────
_DATASETTE = {"proc": None, "port": 8001}

def _port_serving(host, port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.4)
    try:
        s.connect((host, int(port))); return True
    except Exception:
        return False
    finally:
        try: s.close()
        except Exception: pass

@app.post("/api/db/open")
def api_db_open():
    """Open the corpus in Datasette for SQL querying. Snapshots the live DB
    (consistent copy — never opens the writable DB in a GUI), then launches
    Datasette read-only on the snapshot. Idempotent: if something is already
    serving the port, just returns its URL."""
    import shutil, subprocess as sp
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    port = int(_DATASETTE["port"])
    url  = f"http://127.0.0.1:{port}"
    if _port_serving("127.0.0.1", port):
        return jsonify({"url": url, "status": "already-running"})
    if not shutil.which("datasette"):
        return jsonify({"error": "Datasette is not installed. Run:  pip install datasette"}), 500
    snap = str((ROOT / "query_snapshot.db").resolve())
    try:
        r = sp.run(py(script("db_backup.py"), db, snap),
                   capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "")[-300:]
            return jsonify({"error": f"snapshot failed (is a job writing the DB?): {tail}"}), 500
    except Exception as e:
        return jsonify({"error": f"snapshot error: {e}"}), 500
    try:
        _DATASETTE["proc"] = sp.Popen(
            ["datasette", snap, "-h", "127.0.0.1", "--port", str(port),
             "--setting", "sql_time_limit_ms", "8000"],
            stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    except Exception as e:
        return jsonify({"error": f"could not launch Datasette: {e}"}), 500
    return jsonify({"url": url, "status": "starting", "snapshot": snap})


# ──────────────────────────────────────────────────────────────────────────────
# Static dashboard is maintained in scripts/dashboard_static.html (canonical).
# The embedded fallback below is intentionally minimal — it is only written to
# disk if dashboard_static.html is missing entirely (e.g. fresh clone without
# the file). It redirects the user to regenerate the file.
# ──────────────────────────────────────────────────────────────────────────────

_DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sanskrit Automaton \u2014 dashboard file missing</title>
<style>
 body{font-family:system-ui,-apple-system,sans-serif;background:#12100e;color:#e8e0d0;
      max-width:640px;margin:60px auto;padding:0 22px;line-height:1.65}
 h1{color:#e0b062;font-size:20px;font-weight:600}
 code{background:#221e18;padding:2px 7px;border-radius:5px;color:#e0b062;
      font-family:ui-monospace,Consolas,monospace}
 p{margin:14px 0}
</style></head>
<body>
<h1>\u0938\u0902\u0938\u094d\u0915\u0943\u0924 \u00b7 Dashboard file not found</h1>
<p>The canonical UI file <code>scripts/dashboard_static.html</code> is missing, so this
minimal placeholder is served in its place. The full dashboard cannot render without it.</p>
<p>Restore it from version control and restart the dashboard:</p>
<p><code>git checkout -- scripts/dashboard_static.html</code></p>
<p>The API (<code>/api/status</code>, <code>/api/translate</code>, \u2026), the reader
(<code>/reader/&lt;doc&gt;</code>), the library (<code>/library</code>) and Ask
(<code>/ask</code>) pages keep working \u2014 only this landing page is degraded.</p>
</body></html>"""

# Write the static HTML to disk only if it doesn't already exist
# (dashboard_static.html is maintained separately; don't overwrite it on startup)
_static_html = SCRIPTS / "dashboard_static.html"
if not _static_html.exists():
    _static_html.write_text(_DASHBOARD_HTML, encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox",   default="inbox")
    ap.add_argument("--raw",     default="data/raw")
    ap.add_argument("--db",      default="data/context.db")
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--host",    default="127.0.0.1")
    ap.add_argument("--port",    type=int, default=5057)
    args = ap.parse_args()

    # Ensure required dirs exist
    for d in [args.inbox, args.raw, args.exports]:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'─'*60}")
    print(f"  Sanskrit Automaton v2 — Dashboard")
    print(f"  URL:     http://{args.host}:{args.port}/")
    print(f"  Inbox:   {pathlib.Path(args.inbox).resolve()}")
    print(f"  DB:      {pathlib.Path(args.db).resolve()}")
    print(f"  Corpus:  {CORPUS_ROOT}")
    print(f"  Engine:  {os.environ.get('MT_ENGINE','gemini:gemini-2.5-flash')}")
    print(f"{'─'*60}\n")

    # Keep the machine awake while translation/OCR jobs run (overnight throughput).
    threading.Thread(target=_keep_awake_loop, daemon=True).start()

    app.run(host=args.host, port=args.port, debug=False)
