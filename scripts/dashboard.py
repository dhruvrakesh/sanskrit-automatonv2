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

def _run_job(job: Job):
    try:
        proc = subprocess.Popen(
            job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT)
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

def launch(kind: str, doc: str, argv: List[str]) -> str:
    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv)
    with JOBS_LOCK:
        JOBS[job.id] = job
    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return job.id


# ──────────────────────────────────────────────────────────────────────────────
# Inbox / JSONL scanner
# ──────────────────────────────────────────────────────────────────────────────

PDF_RE  = re.compile(r"^([A-Za-z0-9_]+)_(\d{4})\.pdf$",           re.IGNORECASE)
JSONL_RE = re.compile(r"^([A-Za-z0-9_]+)_(\d{4})(?:_norm)?\.jsonl$", re.IGNORECASE)

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
        with connect(dbp) as con:
            schema = detect_schema(con)
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
        return rows
    except Exception:
        traceback.print_exc()
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Corpus Browser API
# ──────────────────────────────────────────────────────────────────────────────

def _corpus_tree() -> List[dict]:
    """Return list of {category, pdfs:[{name, size, path}]} from CORPUS_ROOT."""
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
    return categories


def _sanitize_doc_name(stem: str) -> str:
    """Convert a raw filename stem to a safe doc code."""
    s = re.sub(r"[^A-Za-z0-9_\-]", "_", stem)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def _count_pdf_pages(pdf_path: pathlib.Path) -> int:
    """Count pages in a PDF using pypdf (fast, no rendering needed)."""
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 1


@app.get("/api/corpus")
def api_corpus():
    return jsonify({"corpus_root": str(CORPUS_ROOT), "categories": _corpus_tree()})


@app.post("/api/corpus/import")
def api_corpus_import():
    """
    Copy selected PDFs from D: drive into inbox/.
    Body: {inbox: str, files: [{path: str, doc: str}], auto_split: bool}
    - If auto_split=true and PDF has >1 page → split into per-page PDFs
    - Otherwise copy/rename as DocName_0001.pdf
    """
    data       = request.get_json(force=True) or {}
    inbox_dir  = pathlib.Path(data.get("inbox") or "inbox")
    auto_split = bool(data.get("auto_split", True))
    files      = data.get("files", [])

    if not files:
        return jsonify({"error": "no files specified"}), 400

    inbox_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for item in files:
        src_path = pathlib.Path(item.get("path", ""))
        doc_name = _sanitize_doc_name(item.get("doc") or src_path.stem)

        if not src_path.exists():
            results.append({"path": str(src_path), "error": "file not found"})
            continue

        try:
            n_pages = _count_pdf_pages(src_path)
        except Exception:
            n_pages = 1

        if auto_split and n_pages > 1:
            # Launch split job
            split_script = str(ROOT / "tools" / "split_pdf_pages.py")
            if not pathlib.Path(split_script).exists():
                # Also try inbox/ (original location)
                split_script = str(ROOT / "inbox" / "split_pdf_pages.py")
            if not pathlib.Path(split_script).exists():
                # fallback: copy as _0001.pdf
                dest = inbox_dir / f"{doc_name}_0001.pdf"
                shutil.copy2(str(src_path), str(dest))
                results.append({"doc": doc_name, "pages": 1, "action": "copied"})
            else:
                # split_pdf_pages.py uses positional input_pdf, -o output_dir, -p prefix
                cmd = py(split_script,
                         str(src_path),
                         "-o", str(inbox_dir),
                         "-p", doc_name)
                jid = launch("import_split", doc_name, cmd)
                results.append({"doc": doc_name, "pages": n_pages, "action": "splitting", "job": jid})
        else:
            # Single-page or no split: copy as _0001.pdf (or keep existing naming)
            stem = src_path.stem
            if PDF_RE.match(src_path.name):
                # Already in DocName_NNNN format — copy as-is with sanitized name
                m = re.match(r"^([A-Za-z0-9_]+)_(\d+)$", stem, re.I)
                if m:
                    d, pg = _sanitize_doc_name(m.group(1)), m.group(2).zfill(4)
                    dest = inbox_dir / f"{d}_{pg}.pdf"
                else:
                    dest = inbox_dir / f"{doc_name}_0001.pdf"
            else:
                dest = inbox_dir / f"{doc_name}_0001.pdf"
            shutil.copy2(str(src_path), str(dest))
            results.append({"doc": doc_name, "pages": n_pages, "action": "copied", "dest": dest.name})

    return jsonify({"imported": results})


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
        running = [
            {"id": j.id, "kind": j.kind, "doc": j.doc,
             "start": j.start, "elapsed_s": round(time.time() - j.start, 1)}
            for j in JOBS.values() if j.ok is None
        ]
    return jsonify({"running": running, "count": len(running)})

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
    """Return translation usage stats from the mt_cache table."""
    db_path = request.args.get("db", "data/context.db")
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        # mt_cache schema: engine, src, tgt, src_hash, translation, ts
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "mt_cache" not in tables:
            return jsonify({"error": "mt_cache table not found", "stats": {}})
        rows = con.execute(
            "SELECT engine, COUNT(*) as calls, SUM(LENGTH(translation)) as out_chars "
            "FROM mt_cache GROUP BY engine ORDER BY calls DESC"
        ).fetchall()
        total_calls = con.execute("SELECT COUNT(*) FROM mt_cache").fetchone()[0]
        total_chars = con.execute("SELECT SUM(LENGTH(COALESCE(translation,''))) FROM mt_cache").fetchone()[0] or 0
        # Estimate cost: Gemini 2.5 Pro ~$0.000010/char, OpenAI gpt-4o-mini ~$0.000015/char
        cost_estimate = 0.0
        by_engine = []
        for r in rows:
            eng = r["engine"] or "unknown"
            calls = r["calls"]
            chars = r["out_chars"] or 0
            rate = 0.000010 if "gemini" in eng.lower() else 0.000015
            cost = chars * rate
            cost_estimate += cost
            by_engine.append({"engine": eng, "calls": calls, "out_chars": chars, "cost_usd": round(cost, 4)})
        con.close()
        return jsonify({
            "total_calls": total_calls,
            "total_out_chars": total_chars,
            "cost_estimate_usd": round(cost_estimate, 4),
            "by_engine": by_engine,
            "note": "Cost estimate: Gemini ~$0.01/1k chars, OpenAI ~$0.015/1k chars (output only, rough)"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    data   = request.get_json(force=True) or {}
    doc    = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db     = data.get("db")     or "data/context.db"
    engine = data.get("engine") or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-pro")
    limit  = str(data.get("limit") or 50)
    sleep  = str(data.get("sleep") or 0.6)
    cmd = py(script("translate_passages.py"),
             "--db", db, "--doc", doc, "--engine", engine,
             "--sleep", sleep, "--limit", limit)
    return jsonify({"job": launch("translate", doc, cmd)})

@app.post("/api/export")
def api_export():
    data  = request.get_json(force=True) or {}
    doc   = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db    = data.get("db")  or "data/context.db"
    out   = data.get("out") or "exports"
    title = data.get("title") or f"{doc} — English Translation"
    cmd = py(script("export_html.py"),
             "--db", db, "--doc", doc, "--out", out, "--title", title, "--no-sanskrit")
    return jsonify({"job": launch("export", doc, cmd)})


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
    engine  = data.get("engine")  or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-pro")
    dpi     = str(data.get("dpi") or 400)
    sleep   = str(data.get("sleep") or 0.6)
    skip_ocr       = bool(data.get("skip_ocr"))
    skip_ingest    = bool(data.get("skip_ingest"))
    skip_translate = bool(data.get("skip_translate"))
    skip_export    = bool(data.get("skip_export"))

    cmd = py(script("pipeline_queue.py"),
             "--doc",     doc,
             "--inbox",   inbox,
             "--raw",     raw,
             "--db",      db,
             "--exports", exports,
             "--engine",  engine,
             "--dpi",     dpi,
             "--sleep",   sleep)
    if skip_ocr:       cmd.append("--skip-ocr")
    if skip_ingest:    cmd.append("--skip-ingest")
    if skip_translate: cmd.append("--skip-translate")
    if skip_export:    cmd.append("--skip-export")

    jid = launch("pipeline", doc, cmd)
    return jsonify({"job": jid})


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
        extra_selects = ", ".join([
            f"p.{c}" for c in
            ["verse_ref", "chapter", "text_type", "chandas", "iast", "quality_score", "translation_score"]
            if c in cols
        ])
        if extra_selects:
            extra_selects = ", " + extra_selects

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
            f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id "
            f"WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''{type_clause}",
            (doc, *type_params)
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
            f"SELECT p.page_no, p.idx, p.text, p.translation{extra_selects} "
            f"FROM passages p JOIN docs d ON d.id=p.doc_id "
            f"WHERE d.code=?{type_clause} ORDER BY p.page_no, p.idx LIMIT ? OFFSET ?",
            (doc, *type_params, limit, offset)
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
            "type_counts": type_counts,
            "page": page,
            "limit": limit,
            "passages": [row_to_dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
.en-pending{{color:var(--muted);font-style:italic;font-size:13px;font-family:'Inter',sans-serif}}
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
  <span class="refresh-label" id="refreshLabel">Auto &#8635;</span>
</header>
<main id="main"><div class="loading">Loading passages&hellip;</div></main>
<footer>Sanskrit Automaton v2 &mdash; Scholarly Reader &mdash; {doc}</footer>
<script>
const DOC = {json.dumps(doc)};
let currentPage = 1; const LIMIT = 50;
let refreshTimer = null; let activeFilter = '';

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
    let url = '/api/passages/' + DOC + '?page=' + p + '&limit=' + LIMIT;
    if (activeFilter) url += '&text_type=' + activeFilter;
    const r = await fetch(url);
    const d = await r.json();
    if (d.error){{ document.getElementById('main').innerHTML='<div class="loading">Error: '+esc(d.error)+'</div>'; return; }}
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
        // Column 2: English translation
        '<div class="col-en">' +
          '<div class="col-label col-label-en">&#x1F4DC; English</div>' +
          (hasTr
            ? '<div class="en-text">' + esc(p.translation) + '</div>'
            : '<div class="en-pending">&#x231B; Awaiting translation&hellip;</div>') +
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
# Static Dashboard HTML — rich, dark-mode, Sanskrit-inspired
# ──────────────────────────────────────────────────────────────────────────────

_DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sanskrit Automaton — Pipeline Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
/* ─── Design tokens ─────────────────────────────────────────────────────── */
:root {
  --bg:        #0e0d0b;
  --bg2:       #161411;
  --bg3:       #1e1b16;
  --bg4:       #28231b;
  --border:    #35302600;
  --border-v:  #35302680;
  --gold:      #d4a017;
  --gold-dim:  #9a721080;
  --saffron:   #f47c20;
  --cream:     #f0e6cc;
  --muted:     #8a7d67;
  --ink:       #e8dcc8;
  --green:     #4caf7d;
  --red:       #e05f5f;
  --blue:      #6b9bd2;
  --purple:    #a07dd6;
  --r:         10px;
  --r-sm:      6px;
  --shadow:    0 4px 24px #00000060;
  --glow:      0 0 20px #d4a01730;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; font-family: "Inter", system-ui, sans-serif; background: var(--bg); color: var(--ink); font-size: 14px; overflow: hidden; }

/* ─── Layout ────────────────────────────────────────────────────────────── */
.app { display: grid; grid-template-columns: 320px 1fr 340px; grid-template-rows: 56px 1fr; height: 100vh; }
.top-bar { grid-column: 1/-1; display: flex; align-items: center; gap: 16px; padding: 0 20px; background: var(--bg2); border-bottom: 1px solid var(--border-v); }
.sidebar  { grid-row: 2; background: var(--bg2); border-right: 1px solid var(--border-v); display: flex; flex-direction: column; overflow: hidden; }
.main     { grid-row: 2; overflow-y: auto; padding: 20px; }
.log-panel { grid-row: 2; background: var(--bg2); border-left: 1px solid var(--border-v); display: flex; flex-direction: column; overflow: hidden; }

/* ─── Top bar ────────────────────────────────────────────────────────────── */
.brand { display: flex; align-items: center; gap: 10px; }
.brand-deva { font-family: "Noto Serif Devanagari", serif; font-size: 22px; color: var(--gold); letter-spacing: 0.02em; }
.brand-sub  { font-size: 11px; color: var(--muted); font-weight: 500; }
.top-bar-spacer { flex: 1; }
.engine-wrap { display: flex; align-items: center; gap: 8px; }
.engine-label { font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: .05em; text-transform: uppercase; }
select.engine-select {
  background: var(--bg3); border: 1px solid var(--border-v); color: var(--ink);
  padding: 6px 10px; border-radius: var(--r-sm); font-size: 12px; cursor: pointer;
  font-family: "JetBrains Mono", monospace;
}
select.engine-select:focus { outline: none; border-color: var(--gold); }
.btn-refresh { padding: 7px 14px; background: transparent; border: 1px solid var(--border-v); border-radius: var(--r-sm); color: var(--muted); font-size: 12px; cursor: pointer; transition: all .2s; }
.btn-refresh:hover { border-color: var(--gold); color: var(--gold); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

/* ─── Sidebar: corpus browser ────────────────────────────────────────────── */
.sidebar-header { padding: 14px 16px 10px; border-bottom: 1px solid var(--border-v); }
.sidebar-title { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }
.corpus-path   { font-size: 10px; color: var(--muted); font-family: "JetBrains Mono", monospace; word-break: break-all; }
.sidebar-search { margin: 10px 12px 0; position: relative; }
.sidebar-search input { width: 100%; background: var(--bg3); border: 1px solid var(--border-v); border-radius: var(--r-sm); padding: 7px 10px 7px 30px; color: var(--ink); font-size: 12px; }
.sidebar-search input:focus { outline: none; border-color: var(--gold-dim); }
.sidebar-search .si { position: absolute; left: 9px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 13px; }
.corpus-tree { flex: 1; overflow-y: auto; padding: 8px 0; }
.cat-item { }
.cat-header {
  display: flex; align-items: center; gap: 8px; padding: 7px 16px;
  cursor: pointer; transition: background .15s; user-select: none;
}
.cat-header:hover { background: var(--bg3); }
.cat-arrow { font-size: 9px; color: var(--muted); transition: transform .2s; display: inline-block; }
.cat-item.open .cat-arrow { transform: rotate(90deg); }
.cat-name { font-size: 12px; font-weight: 600; color: var(--cream); flex: 1; }
.cat-count { font-size: 10px; color: var(--muted); font-family: "JetBrains Mono", monospace; }
.cat-pdfs { display: none; padding: 0 0 4px 16px; }
.cat-item.open .cat-pdfs { display: block; }
.pdf-item { display: flex; align-items: center; gap: 8px; padding: 4px 10px 4px 20px; border-radius: var(--r-sm); cursor: pointer; transition: background .12s; }
.pdf-item:hover { background: var(--bg3); }
.pdf-item input[type=checkbox] { accent-color: var(--gold); cursor: pointer; flex-shrink: 0; }
.pdf-name { font-size: 11px; color: var(--ink); flex: 1; font-family: "JetBrains Mono", monospace; }
.pdf-size { font-size: 10px; color: var(--muted); white-space: nowrap; }
.sidebar-actions { padding: 12px; border-top: 1px solid var(--border-v); display: flex; flex-direction: column; gap: 8px; }
.sel-count { font-size: 11px; color: var(--muted); text-align: center; }
.btn-import { width: 100%; padding: 9px; background: linear-gradient(135deg, var(--saffron), var(--gold)); border: none; border-radius: var(--r-sm); color: #0e0d0b; font-weight: 700; font-size: 12px; cursor: pointer; transition: opacity .2s, transform .15s; letter-spacing: .03em; }
.btn-import:hover { opacity: .9; transform: translateY(-1px); }
.btn-import:active { transform: translateY(0); }
.import-split-row { display: flex; align-items: center; gap: 8px; }
.import-split-row label { font-size: 11px; color: var(--muted); }
.import-split-row input { accent-color: var(--gold); }

/* ─── Main: pipeline table ───────────────────────────────────────────────── */
.section-title { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 14px; display: flex; align-items: center; gap: 10px; }
.section-title::after { content:""; flex:1; height:1px; background: var(--border-v); }
.batch-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.btn-batch { padding: 6px 12px; background: var(--bg3); border: 1px solid var(--border-v); border-radius: var(--r-sm); color: var(--muted); font-size: 11px; font-weight: 600; cursor: pointer; transition: all .15s; letter-spacing: .02em; }
.btn-batch:hover { border-color: var(--gold-dim); color: var(--cream); }
.pipeline-table { width: 100%; border-collapse: collapse; }
.pipeline-table th { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .07em; padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border-v); }
.pipeline-table td { padding: 10px 12px; border-bottom: 1px solid #ffffff08; vertical-align: middle; }
.pipeline-table tr:last-child td { border-bottom: none; }
.pipeline-table tr:hover td { background: var(--bg3); }
.doc-name { font-weight: 600; color: var(--cream); font-size: 13px; font-family: "JetBrains Mono", monospace; }
.num-cell { font-family: "JetBrains Mono", monospace; font-size: 12px; color: var(--muted); }
.prog-wrap { display: flex; flex-direction: column; gap: 3px; }
.prog-bar { height: 6px; background: var(--bg4); border-radius: 999px; overflow: hidden; width: 80px; }
.prog-bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--gold), var(--saffron)); transition: width .4s ease; }
.prog-bar.tr i { background: linear-gradient(90deg, var(--green), #6dd4a0); }
.prog-pct { font-size: 10px; color: var(--muted); font-family: "JetBrains Mono", monospace; }
.actions-cell { display: flex; gap: 6px; flex-wrap: wrap; }
.btn-act { padding: 5px 10px; border: 1px solid var(--border-v); border-radius: var(--r-sm); background: var(--bg3); color: var(--muted); font-size: 11px; font-weight: 600; cursor: pointer; transition: all .15s; white-space: nowrap; }
.btn-act:hover { background: var(--bg4); color: var(--cream); border-color: var(--gold-dim); }
.btn-act.ocr  :hover, .btn-act:hover.ocr   { color: var(--blue); border-color: var(--blue); }
.btn-act.tr   { }
.btn-act.tr:hover { color: var(--green); border-color: var(--green); }
.btn-act.exp:hover { color: var(--purple); border-color: var(--purple); }
.btn-act.ing:hover { color: var(--saffron); border-color: var(--saffron); }

/* ─── Log panel ──────────────────────────────────────────────────────────── */
.log-header { padding: 14px 16px 10px; border-bottom: 1px solid var(--border-v); display: flex; align-items: center; gap: 10px; }
.log-title { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); flex: 1; }
.job-badges { display: flex; gap: 6px; flex-wrap: wrap; padding: 8px 12px; border-bottom: 1px solid var(--border-v); min-height: 36px; }
.badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 999px; font-size: 10px; font-weight: 600; border: 1px solid; animation: fadeIn .3s; }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }
.badge.running { border-color: var(--gold-dim); color: var(--gold); background: #d4a01715; }
.badge.ok      { border-color: #4caf7d50; color: var(--green); background: #4caf7d10; }
.badge.fail    { border-color: #e05f5f50; color: var(--red); background: #e05f5f10; }
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.badge.running .badge-dot { animation: pulse 1s infinite; }
.log-body { flex: 1; overflow-y: auto; padding: 10px 14px; font-family: "JetBrains Mono", monospace; font-size: 11px; color: #9a8f7a; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
.log-line-ok  { color: var(--green); }
.log-line-err { color: var(--red); }
.log-line-info { color: var(--gold); }
.log-clear { padding: 8px 12px; border-top: 1px solid var(--border-v); }
.btn-clear { background: none; border: none; color: var(--muted); font-size: 11px; cursor: pointer; }
.btn-clear:hover { color: var(--red); }

/* ─── Toast ──────────────────────────────────────────────────────────────── */
#toast { position: fixed; right: 20px; bottom: 20px; background: var(--bg3); color: var(--ink); padding: 10px 16px; border-radius: var(--r); border: 1px solid var(--border-v); font-size: 13px; box-shadow: var(--shadow); display: none; z-index: 9999; animation: slideIn .25s; }
@keyframes slideIn { from{transform:translateX(30px);opacity:0} to{transform:none;opacity:1} }
#toast.ok   { border-color: var(--green); }
#toast.fail { border-color: var(--red); }

/* ─── Scrollbars ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 999px; }

/* ─── Empty state ────────────────────────────────────────────────────────── */
.empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
.empty-state .e-icon { font-size: 40px; margin-bottom: 12px; }
.empty-state h3 { font-size: 16px; color: var(--cream); margin-bottom: 8px; }
.empty-state p  { font-size: 13px; line-height: 1.6; max-width: 360px; margin: 0 auto; }
</style>
</head>
<body>
<div class="app">

  <!-- ── Top bar ──────────────────────────────────────── -->
  <header class="top-bar">
    <div class="brand">
      <div class="brand-deva">संस्कृत</div>
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--cream)">Sanskrit Automaton</div>
        <div class="brand-sub">OCR · Normalize · Translate · Export</div>
      </div>
    </div>
    <div class="top-bar-spacer"></div>
    <div class="engine-wrap">
      <span class="engine-label">Engine</span>
      <select id="engineSelect" class="engine-select" title="Translation engine">
        <option value="gemini:gemini-2.5-pro">✦ Gemini 2.5 Pro (highest quality)</option>
        <option value="gemini:gemini-2.0-flash">⚡ Gemini 2.0 Flash (fast)</option>
        <option value="openai:gpt-4o">🔵 GPT-4o</option>
        <option value="openai:gpt-4o-mini">🔵 GPT-4o-mini (cheap)</option>
        <option value="echo">🔁 Echo (test)</option>
      </select>
    </div>
    <div class="status-dot" title="Server running"></div>
    <button class="btn-refresh" onclick="refresh()">⟳ Refresh</button>
  </header>

  <!-- ── Corpus browser sidebar ────────────────────────── -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">📚 Scripture Corpus</div>
      <div class="corpus-path" id="corpusPath">Loading…</div>
    </div>
    <div class="sidebar-search">
      <span class="si">🔍</span>
      <input type="text" id="corpusSearch" placeholder="Search scriptures…" oninput="filterCorpus(this.value)"/>
    </div>
    <div class="corpus-tree" id="corpusTree">
      <div class="empty-state"><div class="e-icon">🔄</div><p>Loading corpus…</p></div>
    </div>
    <div class="sidebar-actions">
      <div class="sel-count" id="selCount">No files selected</div>
      <div class="import-split-row">
        <input type="checkbox" id="autoSplit" checked/>
        <label for="autoSplit">Auto-split multi-page PDFs</label>
      </div>
      <button class="btn-import" onclick="importSelected()">⬇ Import to Inbox</button>
    </div>
  </aside>

  <!-- ── Pipeline dashboard main ───────────────────────── -->
  <main class="main">
    <div class="section-title">Pipeline Status</div>
    <div class="batch-bar">
      <button class="btn-batch" onclick="batchAction('ocr')">▶ OCR All</button>
      <button class="btn-batch" onclick="batchAction('ingest')">⬆ Ingest All</button>
      <button class="btn-batch" onclick="batchAction('translate')">✦ Translate All</button>
      <button class="btn-batch" onclick="batchAction('export')">⤓ Export All</button>
    </div>
    <div id="pipelineWrap">
      <div class="empty-state">
        <div class="e-icon">📂</div>
        <h3>No documents in inbox</h3>
        <p>Use the corpus browser on the left to select scriptures from the D: drive and import them into the inbox.</p>
      </div>
    </div>
  </main>

  <!-- ── Job log panel ─────────────────────────────────── -->
  <aside class="log-panel">
    <div class="log-header">
      <span class="log-title">Job Log</span>
      <span id="runningCount" style="font-size:10px;color:var(--muted)">idle</span>
    </div>
    <div class="job-badges" id="jobBadges"></div>
    <div class="log-body" id="logBody"><span style="color:var(--muted)">Awaiting jobs…</span></div>
    <div class="log-clear"><button class="btn-clear" onclick="clearLog()">✕ Clear log</button></div>
  </aside>

</div>
<div id="toast"></div>

<script>
// ── Config ─────────────────────────────────────────────────────────────────
const params = new URLSearchParams(window.location.search);
const cfg = {
  inbox:   params.get("inbox")   || "inbox",
  raw:     params.get("raw")     || "data/raw",
  db:      params.get("db")      || "data/context.db",
  exports: params.get("exports") || "exports",
};

// ── State ───────────────────────────────────────────────────────────────────
let corpusData    = [];
let pdfRegistry   = {};  // id -> {path, doc, name}  — avoids JSON-in-HTML-attr bugs
let pdfIdCounter  = 0;
let selectedIds   = new Set();   // Set of numeric registry IDs
let activeJobs    = {};          // jid -> {kind, doc, label}
let logLines      = [];

// ── Utilities ───────────────────────────────────────────────────────────────
function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1024*1024) return (b/1024).toFixed(0) + " KB";
  return (b/(1024*1024)).toFixed(1) + " MB";
}
function pct(a, b) { return b ? Math.round(100*a/b) : 0; }
function toast(msg, type="") {
  const t = document.getElementById("toast");
  t.className = type;
  t.textContent = msg;
  t.style.display = "block";
  setTimeout(() => t.style.display = "none", 2800);
}
function addLog(line, cls="") {
  logLines.push({line, cls});
  if (logLines.length > 600) logLines.shift();
  renderLog();
}
function renderLog() {
  const el = document.getElementById("logBody");
  el.innerHTML = logLines.map(({line,cls}) =>
    `<span${cls ? ` class="${cls}"` : ""}>${escHtml(line)}</span>\n`
  ).join("");
  el.scrollTop = el.scrollHeight;
}
function clearLog() { logLines = []; renderLog(); }
function escHtml(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function engine() { return document.getElementById("engineSelect").value; }

// ── Pipeline status ─────────────────────────────────────────────────────────
async function refresh() {
  try {
    const r = await fetch(`/api/status?inbox=${encodeURIComponent(cfg.inbox)}&raw=${encodeURIComponent(cfg.raw)}&db=${encodeURIComponent(cfg.db)}&exports=${encodeURIComponent(cfg.exports)}`);
    const data = await r.json();
    renderPipeline(data);
  } catch(e) { toast("Refresh failed: " + e, "fail"); }
}

function renderPipeline(rows) {
  const wrap = document.getElementById("pipelineWrap");
  if (!rows.length) {
    wrap.innerHTML = `<div class="empty-state"><div class="e-icon">📂</div><h3>No documents in inbox</h3><p>Use the corpus browser to import scriptures.</p></div>`;
    return;
  }
  wrap.innerHTML = `
    <table class="pipeline-table">
      <thead><tr>
        <th>Document</th><th>PDFs</th><th>JSONL</th><th>Ingested</th>
        <th>Lines</th><th>Translated</th><th>Exports</th><th>Actions</th>
      </tr></thead>
      <tbody id="pipelineTbody"></tbody>
    </table>`;
  const tb = document.getElementById("pipelineTbody");
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><div class="doc-name">${escHtml(r.doc)}</div></td>
      <td><span class="num-cell">${r.pdf_count}</span></td>
      <td>${progCell(r.jsonl_count, r.pdf_count)}</td>
      <td>${progCell(r.ingested_pages, r.pdf_count)}</td>
      <td><span class="num-cell">${r.total_lines}</span></td>
      <td>${progCell(r.translated_lines, r.total_lines, true)}</td>
      <td><span class="num-cell">${r.exports}</span></td>
      <td class="actions-cell">
        <button class="btn-act ocr"  data-act="ocr"       data-doc="${escHtml(r.doc)}">OCR</button>
        <button class="btn-act ing"  data-act="ingest"    data-doc="${escHtml(r.doc)}">Ingest</button>
        <button class="btn-act tr"   data-act="translate" data-doc="${escHtml(r.doc)}">Translate</button>
        <button class="btn-act exp"  data-act="export"    data-doc="${escHtml(r.doc)}">Export</button>
      </td>`;
    tb.appendChild(tr);
  }
}

function progCell(a, b, green=false) {
  const p = pct(a, b);
  return `<div class="prog-wrap">
    <div class="prog-bar${green?" tr":""}"><i style="width:${p}%"></i></div>
    <span class="prog-pct">${a}/${b || "?"} (${p}%)</span>
  </div>`;
}

// ── Action buttons ──────────────────────────────────────────────────────────
document.addEventListener("click", async ev => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  const doc = b.dataset.doc;
  const act = b.dataset.act;
  await triggerAction(act, doc);
});

async function triggerAction(act, doc) {
  if (act === "ocr") {
    const dpi  = prompt("DPI for OCR? (Higher = better but slower)", "400") || "400";
    const langs = prompt("Tesseract language string?", "san+hin+eng") || "san+hin+eng";
    const r = await fetch("/api/ocr", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, dpi, langs, inbox: cfg.inbox, raw: cfg.raw})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, `OCR ${doc}`, "ocr", doc); toast(`OCR started for ${doc}`); }
    else toast(j.message || "No OCR work needed", "ok");
  }
  if (act === "ingest") {
    const r = await fetch("/api/ingest", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db: cfg.db, raw: cfg.raw})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, `Ingest ${doc}`, "ingest", doc); toast(`Ingest started for ${doc}`); }
  }
  if (act === "translate") {
    const eng   = engine();
    const limit = prompt("Max passages per run?", "100") || "100";
    const r = await fetch("/api/translate", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db: cfg.db, engine: eng, limit})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, `Translate ${doc}`, "translate", doc); toast(`Translation started (${eng})`); }
  }
  if (act === "export") {
    const r = await fetch("/api/export", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db: cfg.db, out: cfg.exports})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, `Export ${doc}`, "export", doc); toast(`Export started for ${doc}`); }
  }
}

async function batchAction(act) {
  const rows = document.querySelectorAll("button[data-act='" + act + "']");
  for (const b of rows) { await triggerAction(act, b.dataset.doc); }
}

// ── Job tracking ────────────────────────────────────────────────────────────
function trackJob(jid, label, kind, doc) {
  activeJobs[jid] = {label, kind, doc, done: false};
  addLog(`▶ ${label}`, "log-line-info");
  reasync function importSelected() {
  if (!selectedIds.size) { toast("Select files first"); return; }
  const autoSplit = document.getElementById("autoSplit").checked;
  const files = [...selectedIds].map(id => {
    const r = pdfRegistry[id];
    return {path: r.path, doc: r.doc};
  });
  toast(`Importing ${files.length} file(s)…`);
  try {
    const r = await fetch("/api/corpus/import", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({inbox: cfg.inbox, files, auto_split: autoSplit})
    });
    const d = await r.json();
    const splitting = (d.imported || []).filter(i => i.action === "splitting");
    const copied    = (d.imported || []).filter(i => i.action === "copied");
    let msg = `Imported: ${copied.length} copied`;
    if (splitting.length) {
      msg += `, ${splitting.length} splitting (multi-page)`;
      for (const s of splitting) {
        if (s.job) trackJob(s.job, `Split ${s.doc}`, "import_split", s.doc);
      }
    }
    toast(msg, "ok");
    addLog(`[OK] ${msg}`, "log-line-ok");
    // Uncheck all
    selectedIds.clear();
    document.querySelectorAll(".pdf-cb:checked").forEach(cb => cb.checked = false);
    updateSelCount();
    setTimeout(refresh, 1500);
  } catch(e) {
    toast("Import failed: " + e, "fail");
    addLog(`[ERR] Import error: ${e}`, "log-line-err");
  }
}
etElementById("runningCount").textContent =
    running.length ? `${running.length} running` : "idle";
  el.innerHTML = [...running.map(j =>
    `<span class="badge running"><span class="badge-dot"></span>${escHtml(j.label)}</span>`
  ), ...recent.map(j =>
    `<span class="badge ${j.ok?"ok":"fail"}"><span class="badge-dot"></span>${escHtml(j.label)}</span>`
  )].join("");
}

// ── Corpus browser ──────────────────────────────────────────────────────────
async function loadCorpus() {
  try {
    const r = await fetch("/api/corpus");
    const d = await r.json();
    corpusData = d.categories || [];
    document.getElementById("corpusPath").textContent = d.corpus_root || "";
    renderCorpus(corpusData);
  } catch(e) {
    document.getElementById("corpusTree").innerHTML =
      `<div class="empty-state"><div class="e-icon">⚠️</div><p>Could not load corpus from D: drive.<br/><small>${e}</small></p></div>`;
  }
}

function renderCorpus(cats) {
  const tree = document.getElementById("corpusTree");
  if (!cats.length) {
    tree.innerHTML = `<div class="empty-state"><div class="e-icon">📭</div><p>No PDFs found in corpus root.</p></div>`;
    return;
  }
  // Rebuild registry for the visible set
  pdfRegistry  = {};
  pdfIdCounter = 0;
  // Preserve previous selections by path
  const prevSelected = new Set(
    [...selectedIds].map(id => pdfRegistry[id] ? pdfRegistry[id].path : null).filter(Boolean)
  );
  selectedIds.clear();

  const html = cats.map(cat => {
    const rows = cat.pdfs.map(pdf => {
      const id  = ++pdfIdCounter;
      const doc = guessDoc(pdf.name, cat.category);
      pdfRegistry[id] = {path: pdf.path, doc, name: pdf.name};
      // Re-check if this path was previously selected
      const chk = prevSelected.has(pdf.path) ? ' checked' : '';
      if (chk) selectedIds.add(id);
      return `<div class="pdf-item">
        <input type="checkbox" class="pdf-cb" data-pid="${id}"${chk}/>
        <span class="pdf-name">${escHtml(pdf.name)}</span>
        <span class="pdf-size">${fmtSize(pdf.size)}</span>
      </div>`;
    }).join("");
    return `<div class="cat-item" data-cat="${escHtml(cat.category)}">
      <div class="cat-header">
        <span class="cat-arrow">▶</span>
        <span class="cat-name">${escHtml(cat.category.replace(/_/g," "))}</span>
        <span class="cat-count">${cat.pdfs.length}</span>
      </div>
      <div class="cat-pdfs">${rows}</div>
    </div>`;
  }).join("");
  tree.innerHTML = html;
  updateSelCount();
}

// Single delegated listener on the corpus tree handles both cat-header clicks
// and checkbox changes — no more inline handlers that break on JSON strings
document.getElementById("corpusTree").addEventListener("change", ev => {
  const cb = ev.target.closest(".pdf-cb");
  if (!cb) return;
  const id = parseInt(cb.dataset.pid, 10);
  if (cb.checked) selectedIds.add(id);
  else            selectedIds.delete(id);
  updateSelCount();
});

document.getElementById("corpusTree").addEventListener("click", ev => {
  const hdr = ev.target.closest(".cat-header");
  if (!hdr) return;
  hdr.closest(".cat-item").classList.toggle("open");
});

function guessDoc(filename, category) {
  const stem = filename.replace(/\.pdf$/i, "");
  const m = stem.match(/^([A-Za-z0-9_]+?)_?(\d{1,6})$/);
  if (m) return m[1].toLowerCase().replace(/[^a-z0-9]/g, "_");
  return (category + "_" + stem).toLowerCase().replace(/[^a-z0-9]/g, "_").replace(/__+/g, "_").slice(0, 40);
}

function updateSelCount() {
  const n = selectedIds.size;
  document.getElementById("selCount").textContent =
    n ? `${n} file${n > 1 ? "s" : ""} selected` : "No files selected";
}

function filterCorpus(q) {
  q = q.trim().toLowerCase();
  if (!q) { renderCorpus(corpusData); return; }
  const filtered = corpusData.map(cat => ({
    ...cat,
    pdfs: cat.pdfs.filter(p => p.name.toLowerCase().includes(q) || cat.category.toLowerCase().includes(q))
  })).filter(cat => cat.pdfs.length);
  renderCorpus(filtered);
}

async function importSelected() {
  if (!selectedFiles.size) { toast("Select files first"); return; }
  const autoSplit = document.getElementById("autoSplit").checked;
  const files = [...selectedFiles].map(k => JSON.parse(k));
  toast(`Importing ${files.length} file(s)…`);
  try {
    const r = await fetch("/api/corpus/import", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({inbox: cfg.inbox, files, auto_split: autoSplit})
    });
    const d = await r.json();
    const splitting = (d.imported||[]).filter(i => i.action === "splitting");
    const copied    = (d.imported||[]).filter(i => i.action === "copied");
    let msg = `Imported: ${copied.length} copied`;
    if (splitting.length) {
      msg += `, ${splitting.length} splitting (multi-page)`;
      for (const s of splitting) {
        if (s.job) trackJob(s.job, `Split ${s.doc}`, "import_split", s.doc);
      }
    }
    toast(msg, "ok");
    addLog(`✓ ${msg}`, "log-line-ok");
    selectedFiles.clear();
    updateSelCount();
    setTimeout(refresh, 1500);
  } catch(e) {
    toast("Import failed: " + e, "fail");
    addLog(`✗ Import error: ${e}`, "log-line-err");
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────
loadCorpus();
refresh();
setInterval(refresh, 15000);
setInterval(renderBadges, 2000);
</script>
</body>
</html>"""

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
    print(f"  Engine:  {os.environ.get('MT_ENGINE','gemini:gemini-2.5-pro')}")
    print(f"{'─'*60}\n")

    app.run(host=args.host, port=args.port, debug=False)
