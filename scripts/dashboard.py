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
    rc: Optional[int] = None   # child exit code, copied off proc before it is
                               # cleared. (JOB_DIAG_2026_09_06)
    killed: bool = False
    active: bool = False   # True once the job's semaphore is acquired and it is
                           # ACTUALLY executing (vs. still queued behind the lock).
    mode: str = ""         # EXPORT_MODE_JOBLOG_2026_09_30: edition (en/hi/tri) for exports; "" otherwise.

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
            # (JOB_DIAG_2026_09_06) "ok: false" on its own is not a diagnosis.
            # rc separates a crash (1) from bad arguments (2) from a kill, and
            # out_tail is usually the last thing the job managed to say.
            "rc": job.rc,
            "out_tail": (job.out or "")[-400:],
        }
        if job.mode:  # EXPORT_MODE_JOBLOG_2026_09_30 - only when set; other records keep their shape
            record["mode"] = job.mode
        # REPAIR_HEAL_2026_10_11: a repair step's verdict in full (the 400-character tail can lose its start)
        _v = [ln.strip() for ln in (job.out or "").splitlines() if ln.startswith(("VERDICT: ", "NEXT: "))]
        if _v:
            for _ln in _v:
                record["verdict" if _ln.startswith("VERDICT: ") else "next"] = _ln.split(": ", 1)[1][:700]
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

LIVE_LINES = 200   # LIVE_LOG_2026_10_10: how many of a running job's last lines /api/job shows


def _pump(stream, chunks: list, job: Job, attr: str) -> None:
    """LIVE_LOG_2026_10_10: read one of a job's pipes line by line while it runs. Every line is kept for
    the end, as communicate() kept them, and the job's .out/.err show the last LIVE_LINES meanwhile, so
    /api/job and the page's Log follow the run instead of waiting for it to end."""
    try:
        for raw in iter(stream.readline, b""):
            chunks.append(raw)
            setattr(job, attr, b"".join(chunks[-LIVE_LINES:]).decode("utf-8", "replace"))
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _run_job(job: Job):
    if job.killed:   # COST_TRUTH_2026_10_15: stopped while it waited for its lock: it never starts
        job.ok, job.out, job.err = False, "", "[KILLED by user] while queued: it never started"
        job.end = time.time()
        _persist_job(job)
        try:
            _status_forget()
        except NameError:
            pass
        return
    try:
        proc = subprocess.Popen(
            job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), env=_child_env()
        )
        job.proc = proc  # store so it can be killed
        # LIVE_LOG_2026_10_10: two readers, as communicate() has, so neither pipe fills and blocks the job
        out_chunks: list = []
        err_chunks: list = []
        readers = [threading.Thread(target=_pump, args=(proc.stdout, out_chunks, job, "out"), daemon=True),
                   threading.Thread(target=_pump, args=(proc.stderr, err_chunks, job, "err"), daemon=True)]
        for t in readers:
            t.start()
        proc.wait()
        for t in readers:
            t.join(timeout=15)
        out, err = b"".join(out_chunks), b"".join(err_chunks)
        job.rc = proc.returncode          # (JOB_DIAG_2026_09_06)
        if job.killed:
            job.ok  = False
            job.out = (out or b"").decode("utf-8", "replace")   # LIVE_LOG_2026_10_10: what it did before
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
        try:
            _status_forget()   # DESK_HEAL_2026_10_10: the counts changed
        except NameError:
            pass

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

def launch(kind: str, doc: str, argv: List[str], then=None, mode: str = "") -> str:
    """Launch a job under its kind's semaphore. Optional `then(job)` runs AFTER the
    job finishes AND its semaphore is released, but only if the job succeeded — this
    is how the pipeline chains OCR (OCR lock, parallel to translation) → ingest →
    translate (translate lock) without holding the translate lock during OCR."""
    # ── Duplicate job prevention ──────────────────────────────────────────────
    with JOBS_LOCK:
        for j in JOBS.values():
            # EXPORT_MODE_JOBLOG_2026_09_30: mode is part of the identity, so a
            # trilingual export is not swallowed by a running Hindi one.
            if j.ok is None and j.kind == kind and j.doc == doc and j.mode == mode:
                print(f"[launch] SKIPPED duplicate: kind={kind} doc={doc} (job {j.id} still running)")
                return j.id  # Return existing job ID

    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv, mode=mode)
    with JOBS_LOCK:
        JOBS[job.id] = job

    # Any translation-family kind (translate, translate_hi, advance_pipeline,
    # pipeline) shares the single translate semaphore so DB writers serialize —
    # even across languages. This is what keeps English and Hindi jobs from
    # writing concurrently (2026-08-02). The QA-panel writers (qa_scan, qa_heal)
    # also mutate the DB (translation_qa / archive+clear+refill) so they share
    # the same semaphore — a heal can never run while a translate is writing,
    # and vice versa (2026-08-16).
    # 'classify' UPDATEs passages.text_type, so it is a DB writer and must
    # serialize with the translators like qa_scan/qa_heal do (2026-08-29).
    # embeddings and entities WRITE to the DB (passage_embeddings, entity_*),
    # so they serialize with the translators exactly as classify/qa_scan do.
    # Leaving them out would reintroduce concurrent writers. (PHASE_G_2026_09_06)
    if (kind.startswith("translate")
            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal", "classify",
                        "embeddings", "entities",
                        "repair_use")):   # REPAIR_PATH_2026_10_10: re-ingesting a repaired text writes the DB
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
    # busy_timeout 30s (Python's default is 5s), matching db_utils: a dashboard read that
    # overlaps a translate/maintenance write WAITS rather than raising "database is
    # locked". Additive only — WAL already allows readers alongside one writer.
    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        con.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
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
    # Non-verse rows (English front matter, noise) are excluded from the translation
    # counts so the pipeline table matches the Library and the QA panel — all three
    # now count real Sanskrit verses only (2026-08-28).
    try:
        _has_tt = "text_type" in {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    except Exception:
        _has_tt = False
    _ttp = " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if _has_tt else ""
    _tt  = " AND COALESCE(text_type,'mula') NOT IN ('noise','frontmatter')"   if _has_tt else ""
    if dm == "join_docs":
        sql_tot = f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?{_ttp}"
        sql_tr  = f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''{_ttp}"
    elif dm == "passages_doc":
        sql_tot = f"SELECT COUNT(*) FROM passages WHERE doc=?{_tt}"
        sql_tr  = f"SELECT COUNT(*) FROM passages WHERE doc=? AND TRIM(COALESCE(translation,''))<>''{_tt}"
    else:
        sql_tot = f"SELECT COUNT(*) FROM passages WHERE doc_code=?{_tt}"
        sql_tr  = f"SELECT COUNT(*) FROM passages WHERE doc_code=? AND TRIM(COALESCE(translation,''))<>''{_tt}"
    total = int(con.execute(sql_tot, (doc,)).fetchone()[0] or 0)
    trans = int(con.execute(sql_tr,  (doc,)).fetchone()[0] or 0)
    return pages, total, trans

def doc_times(inbox, raw, doc: str) -> dict:
    """When was this book added, and when did work last touch it?

    /api/status carried no dates at all, so the pipeline table could not be
    ordered by anything but name. first_seen is the OLDEST inbox page (when the
    book arrived); last_ocr is the NEWEST OCR output (when work last ran).
    Epoch seconds, or None. Cheap: a directory stat, no DB. (PHASE_G_2026_09_06)
    """
    out = {"first_seen": None, "last_ocr": None, "last_activity": None}
    try:
        ins = [p.stat().st_mtime for p in pathlib.Path(inbox).glob(f"{doc}_*.pdf")]
        if ins:
            out["first_seen"] = min(ins)
    except Exception:
        pass
    try:
        js = [p.stat().st_mtime for p in pathlib.Path(raw).glob(f"{doc}_*.jsonl")]
        if js:
            out["last_ocr"] = max(js)
    except Exception:
        pass
    cands = [v for v in (out["first_seen"], out["last_ocr"]) if v]
    out["last_activity"] = max(cands) if cands else None
    return out


def doc_composition(con, doc: str) -> dict:
    """What IS this book? Counts of passages by text_type, so the UI can show
    that e.g. a 664-passage edition is 453 Sanskrit verses + 180 English preface
    + 31 OCR crumbs, instead of implying 664 untranslated verses (2026-08-29)."""
    try:
        pcols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        if "text_type" not in pcols:
            return {}
        rows = con.execute(
            """SELECT COALESCE(p.text_type,'mula'), COUNT(*)
               FROM passages p JOIN docs d ON d.id = p.doc_id
               WHERE d.code = ? GROUP BY 1""", (doc,)).fetchall()
        return {str(tt): int(n) for tt, n in rows}
    except Exception:
        return {}


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
    # -u is load-bearing. (JOB_DIAG_2026_09_06)
    # _run_job pipes stdout and stderr, and CPython block-buffers stdout at 8 KB
    # when it is a pipe. A job that does not exit cleanly therefore loses
    # EVERYTHING it printed - which is how the entities job on 2026-09-06 came to
    # be recorded as ok:false, out_lines:0, err_preview:"" after 32.9 seconds of
    # work. Unbuffered, each line is delivered as it is printed.
    return [sys.executable, "-u", *args]

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
                    "composition":      doc_composition(con, doc),
                    **doc_times(inbox, raw, doc),
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
                    "composition":      doc_composition(con, doc),
                    **doc_times(inbox, raw, doc),
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
    try:
        _status_forget()   # DESK_HEAL_2026_10_10: a copied page shows on the next status read
    except NameError:
        pass
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

# DESK_HEAL_2026_10_10 -------------------------------------------------------------------------
# /api/status is the dashboard's heaviest read: the inbox, data/raw and two queries per text (7.2 s
# on 2026-10-10 with 68 texts, 2,166 inbox pages and 10,903 page files). The page asked for it every
# 5 s while a job ran and the Srangam Hub every 5 s more, so the reads overlapped and each slowed the
# next ("Automaton down (ReadTimeout)" in the hub). It is now worked out once at a time, shared by
# every caller that arrives meanwhile, and kept STATUS_TTL_S seconds; a job that ends clears it.
STATUS_TTL_S = 10.0
_STATUS_LOCK = threading.Lock()
_STATUS_CACHE: dict = {}      # (inbox, raw, db, exports) -> (time, rows)
_STATUS_GEN = [0]             # bumped by _status_forget: a read that began before it is not kept
_STARTED_AT = time.time()


def _status_forget() -> None:
    _STATUS_GEN[0] += 1
    _STATUS_CACHE.clear()


def _status_cached(inbox, raw, dbp, exports):
    key = (str(inbox), str(raw), str(dbp), str(exports))
    hit = _STATUS_CACHE.get(key)
    if hit and time.time() - hit[0] < STATUS_TTL_S:
        return hit[1]
    with _STATUS_LOCK:        # one read at a time; a caller that waited finds the fresh answer here
        hit = _STATUS_CACHE.get(key)
        if hit and time.time() - hit[0] < STATUS_TTL_S:
            return hit[1]
        gen = _STATUS_GEN[0]
        rows = build_status(inbox, raw, dbp, exports)
        if gen == _STATUS_GEN[0]:   # nothing ended or was imported meanwhile
            _STATUS_CACHE[key] = (time.time(), rows)
        return rows


@app.get("/api/status")
def api_status():
    inbox   = pathlib.Path(request.args.get("inbox")   or "inbox")
    raw     = pathlib.Path(request.args.get("raw")     or "data/raw")
    dbp     = pathlib.Path(request.args.get("db")      or "data/context.db")
    exports = pathlib.Path(request.args.get("exports") or "exports")
    if request.args.get("fresh") == "1":
        _status_forget()
    return jsonify(_status_cached(inbox, raw, dbp, exports))


@app.get("/api/health")
def api_health():
    """DESK_HEAL_2026_10_10: is the dashboard up, and what is it doing - from memory only (no disk, no
    database), so it answers in milliseconds while jobs run. For the Srangam Hub and the scripts."""
    now = time.time()
    with JOBS_LOCK:
        running = [{"id": j.id, "kind": j.kind, "doc": j.doc, "state": "running" if j.active else "queued",
                    "elapsed_s": round(now - j.start, 1)} for j in JOBS.values() if j.ok is None]
    active = sum(1 for r in running if r["state"] == "running")
    return jsonify({"ok": True, "mark": "DESK_HEAL_2026_10_10", "pid": os.getpid(),
                    "up_s": round(now - _STARTED_AT, 1),
                    "jobs": {"count": len(running), "active": active, "queued": len(running) - active,
                             "running": running}})

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
        "running": job.ok is None, "killed": job.killed, "mode": job.mode or None,
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
    return jsonify({"killed": killed, "jid": jid, "doc": job.doc, "kind": job.kind,
                    "queued": not job.active})   # COST_TRUTH_2026_10_15: a queued job will not start

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
             "active": bool(j.active), "state": "running" if j.active else "queued",
             "mode": j.mode or None}   # REPAIR_HEAL_2026_10_11: a vision repair and an assessment differ
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
    """Set the cap or resume. Body: {budget_usd: 30} or {resume: true}. LIVE_BUDGET_2026_10_08: the
    value is checked (a number above 0, at most BUDGET_MAX_USD), the connection is always closed,
    the answer carries the new state, and every change is appended to data/budget_changes.jsonl."""
    db_path = request.args.get("db", "data/context.db")
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("resume") and "budget_usd" not in data:
        return jsonify({"error": "specify budget_usd or resume:true"}), 400
    new = None
    if "budget_usd" in data:
        try:
            new = float(data["budget_usd"])
        except (TypeError, ValueError):
            return jsonify({"error": "budget_usd must be a number"}), 400
        if new != new or new <= 0 or new > BUDGET_MAX_USD:   # NaN, zero, negative, or absurd
            return jsonify({"error": "budget_usd must be above 0 and at most %g" % BUDGET_MAX_USD}), 400
    con = None
    try:
        import sys as _sys; _sys.path.insert(0, str(SCRIPTS))
        from cost_tracker import ensure_usage_schema, set_budget, resume_budget, get_summary
        con = sqlite3.connect(db_path, timeout=30)
        ensure_usage_schema(con)
        before = dict(get_summary(con)["budget"])
        if new is None:
            resume_budget(con)
        else:
            set_budget(con, new)
        after = dict(get_summary(con)["budget"])
        _log_budget_change("resume" if new is None else "set", before, after)
        out = {"budget_usd": after["budget_usd"], "spent_usd": after["spent_usd"], "paused": after["paused"],
               "remaining_usd": round(after["budget_usd"] - after["spent_usd"], 6)}
        out["resumed" if new is None else "set"] = True
        if after["spent_usd"] >= after["budget_usd"]:
            out["warning"] = "the cap is at or below what is already spent, so paid steps stop at once"
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if con is not None:
            con.close()




# LIVE_BUDGET_2026_10_08 ------------------------------------------------------------------------
PROGRESS_PATH = ROOT / "data" / "translation_progress.json"
BUDGET_LOG_PATH = ROOT / "data" / "budget_changes.jsonl"
PROGRESS_STALE_S = 20 * 60
BUDGET_MAX_USD = 1000.0


def _translation_job_live() -> bool:
    with JOBS_LOCK:
        return any(j.ok is None and (j.kind.startswith("translate") or j.kind in ("pipeline", "advance_pipeline"))
                   for j in JOBS.values())


def _progress_truth(d):
    """translation_progress.json says 'running' until the run itself rewrites it. A run that dies
    with the dashboard or the computer never does, so the Live tab kept showing 'Calling API' (Ganita,
    from 2026-10-07 14:18 UTC to the next morning, with no job running). With no translation-family
    job unfinished here and the file unchanged for PROGRESS_STALE_S, it is reported as 'interrupted'.
    A recent file is left alone: a run started from a terminal writes it too."""
    if not isinstance(d, dict) or d.get("status") not in ("running", "paused") or _translation_job_live():
        return d
    import datetime as _dt
    try:
        ts = _dt.datetime.fromisoformat(str(d.get("updated_at") or "").replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_dt.timezone.utc)
        age = (_dt.datetime.now(_dt.timezone.utc) - ts).total_seconds()
    except ValueError:
        age = None
    if age is not None and age < PROGRESS_STALE_S:
        return d
    if age is None:
        ago = "at an unknown time"
    elif age >= 3600:
        ago = "%.0f h ago" % (age / 3600)
    else:
        ago = "%.0f min ago" % (age / 60)
    out = dict(d)
    out["status"] = "interrupted"
    out["stale_since"] = d.get("updated_at")
    out["message"] = ("No translation is running. This run stopped at p%s.%s with %s of %s verses done and last "
                      "wrote its progress %s: the dashboard or the computer was closed, or the process was "
                      "stopped, while it ran. Start Translate for this text again; verses already translated "
                      "are kept and skipped." % (d.get("current_page"), d.get("current_idx"),
                                                 d.get("verses_done", 0), d.get("verses_total", 0), ago))
    return out


def _log_budget_change(action, before, after):
    try:
        BUDGET_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BUDGET_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action,
                                "cap_before": before.get("budget_usd"), "cap_after": after.get("budget_usd"),
                                "spent_usd": after.get("spent_usd"), "paused_after": after.get("paused"),
                                "from": request.remote_addr}) + "\n")
    except Exception:
        pass


@app.get("/api/progress")
def api_progress():
    """Return live translation progress from data/translation_progress.json."""
    prog_path = PROGRESS_PATH   # LIVE_BUDGET_2026_10_08
    try:
        if prog_path.exists():
            return jsonify(_progress_truth(json.loads(prog_path.read_text(encoding="utf-8"))))
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
    # Pass the page list as a MANIFEST FILE, never as N arguments. Windows caps a
    # command line at ~32,767 chars; 1,064 Rgveda pages is ~80,000, so the job died
    # in 0.0s with "[WinError 206] The filename or extension is too long" and the UI
    # showed a red 0/1064 with no cause. Books under ~430 pages happened to fit,
    # which made the failure look arbitrary. (2026-08-29)
    man_dir = pathlib.Path("data") / "manifests"
    man_dir.mkdir(parents=True, exist_ok=True)
    manifest = man_dir / f"ocr_{doc}.txt"
    manifest.write_text("\n".join(str(p.resolve()) for p in sorted(missing)) + "\n",
                        encoding="utf-8")
    cmd = py(batch_script,
             "--pdfs-from", str(manifest.resolve()),
             "--outdir",    str(raw.resolve()),
             "--dpi",       dpi,
             "--max-dpi",   "600",
             "--lang-tries", *lang_tries)
    jid = launch("ocr", doc, cmd)
    return jsonify({"job": jid, "pages": len(missing), "manifest": str(manifest)})


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
    # Phase L1 (2026-08-29): classification is now an automatic pipeline stage,
    # not something to remember. A freshly ingested book arrives already sorted
    # into mula / frontmatter / noise, so the counters, the Library and the
    # translator all see real Sanskrit verses from the first moment. Chained via
    # `then=` so it runs only on a successful ingest and takes the write lock
    # itself rather than holding it through the ingest.
    def _classify_after(job, _doc=doc, _db=db):
        launch("classify", _doc,
               py(script("classify_doc.py"), "--doc", _doc, "--db", _db, "--apply"))
    return jsonify({"job": launch("ingest", doc, cmd, then=_classify_after)})


# REPAIR_PATH_2026_10_10 ---------------------------------------------------------------------
# The repair path, there and then. A translation that stops because of its scan (held by the
# OCR-debris guard, or most of what is left below the OCR quality bar) offers its next step where the
# stop is seen: in the Library, on /repair/<doc>, and from the dashboard's Log. Every step is a run of
# scripts/repair_text.py, whose last lines (JUDGED:, VERDICT:, NEXT:, ALSO:) are the advice; the page
# offers NEXT and ALSO as buttons. The register (data/source_verdicts.jsonl, beside the database) holds
# a text's state: set aside (a better scan is wanted), translate as is (the guard lets it through),
# complete (what is left is not to be translated), in repair (the site keeps its last version).
# REPAIR_HEAL_2026_10_11: those states, the debris judged, "Translate it now" after a repair, the texts
# with no English offered their translation, and the Source desk (scripts/source_desk.py): a better
# edition found on archive.org, the local wisdomlib archive and the e-text sites, previewed in the page.
_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore", "as_is", "accept", "hold", "release",
                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed
                 "withdraw", "path_all",                    # PATH_2026_10_12: off the site; the path of every text
                 "redeem_all")                              # REDEEM_2026_10_14: what of the translation is kept
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness
                  "withdrawn")                                                          # PATH_2026_10_12
SOURCES_DIR = ROOT / "sources"                       # ETEXT_WITNESS_2026_10_11: what source_desk.py and etext_witness.py fetch
WITNESS_DIR = ROOT / "data" / "raw_witness"          # the witnesses' pages, witness.json and align.json
WITNESSES_LOG = ROOT / "data" / "witnesses.jsonl"
SOURCE_DESK_DIR = ROOT / "data" / "source_desk"

_REPAIR_CSS = r"""/* REPAIR_PATH_2026_10_10, REPAIR_HEAL_2026_10_11 */
.repairbar{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;align-items:center}
.tr-rest.rp{flex:0 0 auto}
.tr-rest.rpnext{border-color:var(--gold);color:var(--gold)}
.tr-rest.rpalso{border-color:var(--border);color:var(--cream)}
.rplink{font-family:'Inter',sans-serif;font-size:10.5px;color:var(--muted);text-decoration:none}
.rplink:hover{color:var(--gold)}
.rpout{flex-basis:100%;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:var(--cream);opacity:.85}
.rpout:empty{display:none}
.rpjudge{flex-basis:100%;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;padding:4px 7px;border-radius:6px;border:1px solid var(--border)}
.rpjudge:empty{display:none}
.rpjudge[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.rpjudge[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.rpjudge[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.cardnote.aside{color:#d98a8a;border-left-color:#7a3a3a}
.cardnote.state{color:#a9c7e8;border-left-color:#3a5a7a}
.cardnote.repaired{color:#9fd8b5;border-left-color:#2f6b4a}
.rpintro{color:var(--muted);font-family:'Inter',sans-serif;font-size:12px;margin:-4px 0 12px}
.card-wrap.waiting .card{cursor:default}"""

_REPAIR_JS = r"""/* REPAIR_PATH_2026_10_10, REPAIR_HEAL_2026_10_11: the repair path, there and then. Each step is a run of
   repair_text.py (or source_desk.py, or a translation); its last lines (JUDGED:, VERDICT:, NEXT:, ALSO:) say
   what it found, and the next steps are offered as buttons. */
var _RP_DOING = {assess: 'assessing...', repair: 'repairing the scan...', use: 're-ingesting the repaired text...',
                 set_aside: 'setting it aside...', restore: 'restoring...', as_is: 'noting: translate as is...',
                 accept: 'noting: complete...', hold: 'holding it from the site...', release: 'publishing...',
                 find: 'looking for a better edition...', fetch: 'fetching...', translate: 'translating...',
                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...',
                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...',   /* REINGEST_2026_10_12 */
                 withdraw: 'withdrawing it from the site...', path_all: 'charting the path of every text (a few minutes)...',   /* PATH_2026_10_12 */
                 redeem_all: 'counting what of the translation is kept (free, a minute)...'};   /* REDEEM_2026_10_14 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
  return String(s || '').split(_RP_NL).map(function(l){ return l.split(_RP_CR).join(''); })
    .filter(function(l){ return l.trim(); });
}
function _rpVerdict(out){
  var v = '', n = '', j = '', also = [], done = [];
  _rpLines(out).forEach(function(l){
    if (l.indexOf('VERDICT: ') === 0){ v = l.slice(9); also = []; }
    if (l.indexOf('NEXT:') === 0) n = l.slice(5).trim();
    if (l.indexOf('ALSO:') === 0) also.push(l.slice(5).trim());
    if (l.indexOf('JUDGED: ') === 0) j = l.slice(8);
    var m = l.match(/Done[.] ([0-9]+)[/]([0-9]+) translated [|] ([0-9]+) quality-skipped/);
    if (m) done.push(m[1] + ' of ' + m[2] + ' translated' + (+m[3] ? ', ' + m[3] + ' below the OCR bar' : ''));
  });
  return {verdict: v, next: n, also: also, judged: j, done: done};
}
function _rpQuoted(n){ var m = String(n || '').match(/"([^"]*)"/); return m ? m[1] : ''; }
function _rpNext(next){
  var n = String(next || ''), m;
  if (n.indexOf('reingest_pages.py') >= 0){   /* REINGEST_2026_10_12: only the pages that changed */
    m = n.match(/--replace ([0-9]+)/);
    var pg = n.match(/--pages ([0-9,-]+)/);
    if (n.indexOf('--apply') < 0) return {step: 'reingest_plan', pages: pg ? pg[1] : '', label: 'Plan: only the changed pages (free)'};
    return {step: 'reingest', pages: pg ? pg[1] : '', replace: m ? +m[1] : null,
            label: (m && +m[1]) ? 'Re-ingest the changed pages (removes ' + m[1] + ' English)' : 'Re-ingest the changed pages'};
  }
  if (n.indexOf('etext_witness.py') >= 0){   /* ETEXT_WITNESS_2026_10_11 */
    if (n.indexOf('--ingest') >= 0){
      m = n.match(/--witness ([A-Za-z0-9_-]+)/);
      return m ? {step: 'witness', ingest: m[1], label: 'Ingest the witness as its own text'} : null;
    }
    m = n.match(/--file "([^"]+)"/);
    if (!m || n.indexOf('--page') >= 0) return null;
    var fname = m[1].split(_RP_BS).pop().split('/').pop();
    return n.indexOf('--write') >= 0 ? {step: 'witness', write: 1, file: fname, label: 'Make it a witness (its pages; not the database)'}
                                     : {step: 'witness', file: fname, label: 'Read it as a witness (free)'};
  }
  if (n.indexOf('--use-repaired') >= 0){
    m = n.match(/--replace ([0-9]+)/);
    return {step: 'use', replace: m ? +m[1] : null,
            label: m ? 'Use the repaired text (replaces ' + m[1] + ' English)' : 'Use the repaired text'};
  }
  if (n.indexOf('--as-is') >= 0) return {step: 'as_is', reason: _rpQuoted(n), label: 'Translate as is'};
  if (n.indexOf('--accept') >= 0) return {step: 'accept', reason: _rpQuoted(n), label: 'Accept as complete'};
  if (n.indexOf('--set-aside') >= 0) return {step: 'set_aside', label: 'Set aside: a better scan is wanted'};
  if (n.indexOf('--withdraw') >= 0) return {step: 'withdraw', reason: _rpQuoted(n), label: 'Withdraw it from the site'};   /* PATH_2026_10_12 */
  if (n.indexOf('--restore') >= 0) return {step: 'restore', label: 'Restore'};
  if (n.indexOf('--release') >= 0) return {step: 'release', label: 'Publish it to the site'};
  if (n.indexOf('--find-source') >= 0) return {step: 'find', label: 'Find a better source'};
  if (n.indexOf('--repair') >= 0){
    m = n.match(/--max-usd ([0-9.]+)/);
    var usd = m ? +m[1] : 1;
    return {step: 'repair', max_usd: usd, label: 'Repair the scan (at most $' + usd.toFixed(2) + ')'};
  }
  if (n.indexOf('Finish EN') >= 0) return {step: 'translate', label: 'Translate it now: English, then Hindi'};
  return null;
}
function _rpBox(doc){ return document.getElementById('rp-' + doc); }
function _rpSay(doc, text){
  var b = _rpBox(doc), o = b ? b.querySelector('.rpout') : null;
  if (o) o.textContent = text;
}
function _rpJudge(doc, text){
  if (!text) return;
  var el = document.getElementById('rpjudge-' + doc), b = _rpBox(doc);
  if (!el && b){ el = document.createElement('div'); el.className = 'rpjudge'; b.insertBefore(el, b.querySelector('.rpout')); }
  if (!el) return;
  el.textContent = 'The debris, judged: ' + text;
  var lv = text.split(':')[0].trim();
  if (lv === 'cosmetic' || lv === 'moderate' || lv === 'material') el.setAttribute('data-level', lv);
}
function _rpOffer(doc, next, also){
  var box = _rpBox(doc); if (!box) return;
  Array.prototype.slice.call(box.querySelectorAll('.rpnext')).forEach(function(x){ x.parentNode.removeChild(x); });
  var list = [_rpNext(next)].concat((also || []).map(_rpNext)), seen = {};
  list.forEach(function(s, i){
    if (!s || seen[s.step]) return;
    seen[s.step] = 1;
    var b = document.createElement('button');
    b.className = 'tr-rest rp rpnext' + (i ? ' rpalso' : ''); b.textContent = s.label;
    b.title = i ? (also[i - 1] || '') : next;
    b.onclick = function(){ repairStep(doc, s.step, b, s); };
    box.insertBefore(b, box.querySelector('.rpnext') ? box.querySelector('.rpnext').nextSibling : box.firstChild);
  });
}
async function repairStep(doc, step, btn, opt){
  opt = opt || {};
  if (step === 'library'){ location.href = '/library'; return; }
  var body = {doc: doc, step: step}, url = '/api/repair';
  if (step === 'translate'){
    if (!confirm('Translate ' + doc + ' now: English, then Hindi (one job, after the running translation). Passages '
                 + 'whose text did not change come from the cache at no cost. Go?')) return;
    url = '/api/translate'; body = {doc: doc, lang: 'both', limit: 0};
  }
  if (step === 'repair'){
    body.max_usd = opt.max_usd || 1;
    if (body.max_usd > 5){
      _rpSay(doc, 'The estimate is above the $5.00 one press may spend. Run it by hand: python scripts' + _RP_BS
             + 'repair_text.py --doc ' + doc + ' --repair --max-usd ' + body.max_usd.toFixed(2));
      return;
    }
    if (!confirm('Repair the scan of ' + doc + ': vision OCR on its pages, at most $' + body.max_usd.toFixed(2)
                 + ' (it stops before spending more). The database is not touched. Go?')) return;
  }
  if (step === 'use'){
    if (!confirm(opt.replace
        ? ('Use the repaired text of ' + doc + '. Its passages are replaced: ' + opt.replace + ' English translations, and the '
           + 'Hindi, vectors and pictures that point at the old passages, go with them. A backup is made first, and the '
           + 'site keeps its last version until you publish the new one. Go?')
        : ('Use the repaired text of ' + doc + '. Nothing translated is lost; a backup is made first. Go?'))) return;
    if (opt.replace != null) body.replace = opt.replace;   /* REINGEST_2026_10_12: --replace 0 (pictures) was never sent */
  }
  if (step === 'reingest_plan' || step === 'reingest'){   /* REINGEST_2026_10_12 */
    if (opt.pages) body.pages = opt.pages;
    if (step === 'reingest'){
      if (!confirm('Re-ingest the pages of ' + doc + ' that differ from its repaired text. A backup first; on those pages a '
                   + 'passage whose text is unchanged keeps its translations, the others are replaced'
                   + (opt.replace ? ' (' + opt.replace + ' English translations go)' : '') + '; the other pages are not '
                   + 'touched. Go?')) return;
      if (opt.replace != null) body.replace = opt.replace;
    }
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold' || step === 'withdraw'){   /* PATH_2026_10_12: withdraw */
    var ask = {set_aside: 'Set ' + doc + ' aside: why? Its files are kept; the Library stops offering its translation until '
                          + 'it is restored.',
               as_is: 'Translate ' + doc + ' as is: the debris guard will let it through. Why?',
               accept: 'Accept ' + doc + ' as complete: what is left is not to be translated. Why?',
               hold: 'Hold ' + doc + ' from the site: the site keeps its last version until you publish. Why?',
               withdraw: 'Withdraw ' + doc + ' from the site: at the next mirror run the site retires its passages, English '
                         + 'and Hindi (Restore brings them back); they are kept here, out of Ask the Corpus. Why?'}[step];
    var dflt = opt.reason || {set_aside: 'needs a better scan', as_is: 'debris judged cosmetic',
                              accept: 'what is left is not Sanskrit', hold: 're-translating after the repair',
                              withdraw: 'its text is damaged: a better source is wanted'}[step];
    var why = prompt(ask, dflt);
    if (why === null) return;
    body.reason = why || dflt;
  }
  if (step === 'release'){
    if (!confirm('Publish ' + doc + ': the next mirror run (every two hours) sends it to the site as it is now. Go?')) return;
  }
  if (step === 'find'){
    var ai = document.getElementById('srcai-' + doc);
    body.ai = !!(ai && ai.checked);
    if (body.ai && !confirm('Let the AI judge the editions it finds: one call, about $0.002. Go?')) return;
  }
  if (step === 'fetch'){
    body.identifier = opt.identifier; body.kind = opt.kind || 'pdf';
    if (!confirm('Download ' + (body.kind === 'pdf' ? 'the PDF (' + (opt.mb || '?') + ' MB)' : 'the OCR text') + ' of '
                 + opt.identifier + ' from archive.org into sources' + _RP_BS + doc + '? Nothing goes into the inbox: '
                 + 'import it as a witness once you have looked at it.')) return;
  }
  if (step === 'witness'){   /* ETEXT_WITNESS_2026_10_11 */
    if (opt.file) body.file = opt.file;
    if (opt.url) body.url = opt.url;
    if (opt.write){
      body.write = 1;
      if (!confirm('Make the witness of ' + doc + ': its pages go to data' + _RP_BS + 'raw_witness, a line to data' + _RP_BS
                   + 'witnesses.jsonl, and the register keeps it off the site until you adopt it. The database is not '
                   + 'touched. Go?')) return;
    }
    if (opt.ingest){
      body.ingest = opt.ingest;
      if (!confirm('Ingest ' + opt.ingest + ' as its own text: a backup first, then its passages go into the database '
                   + '(after the running translation). The scan is not touched, and the site does not have it until you '
                   + 'adopt it. Go?')) return;
    }
  }
  var orig = btn ? btn.textContent : '';
  if (btn){ btn.disabled = true; btn.textContent = 'starting...'; }
  try{
    var r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if (!d.job){
      _toast('Could not start: ' + (d.error || 'unknown'));
      if (btn){ btn.textContent = orig; btn.disabled = false; }
      return;
    }
    _rpSay(doc, _RP_DOING[step] || 'running...');
    _watchRepair(d.job, doc, step, btn, orig, 0);
  }catch(e){ _toast('Request failed: ' + e); if (btn){ btn.textContent = orig; btn.disabled = false; } }
}
async function _watchRepair(id, doc, step, btn, orig, n){
  try{
    var j = await (await fetch('/api/job/' + encodeURIComponent(id))).json();
    if (j.error){
      _rpSay(doc, 'The dashboard no longer knows this run (restarted?). Its outcome is in the Dashboard History.');
      if (btn){ btn.textContent = orig; btn.disabled = false; }
      return;
    }
    var lines = _rpLines(j.out), pre = document.getElementById('rplog-' + doc);
    if (pre) pre.textContent = lines.slice(-40).join(_RP_NL);
    if (j.state === 'done'){
      if (btn){ btn.textContent = step === 'assess' ? 'Assess again' : orig; btn.disabled = false; }
      var all = (j.out || '') + _RP_NL + (j.err || ''), v = _rpVerdict(all);
      var text = v.verdict;
      if (!text && step === 'translate'){
        text = /TRANSLATE_DEBRIS_GUARD|allow-debris/.test(all) ? 'held by the debris guard: assess it again'
             : (v.done.length ? v.done.join('; ') : (j.ok ? 'done' : 'it did not finish'));
      }
      text = text || (j.ok ? 'done' : 'it did not finish: the Dashboard History has its last lines');
      _rpSay(doc, text); _rpJudge(doc, v.judged); _rpOffer(doc, v.next, v.also);
      _toast(doc + ': ' + text);
      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|withdraw|as_is|accept|hold|release|translate|judge_all|benchmark_all|path_all|redeem_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
    }
    _rpSay(doc, (j.state === 'queued' ? 'queued: after the running database writer' : (_RP_DOING[step] || 'running...'))
                + (lines.length ? '  ' + lines[lines.length - 1] : ''));
  }catch(e){ if (n > 400){ if (btn){ btn.textContent = orig; btn.disabled = false; } return; } }
  setTimeout(function(){ _watchRepair(id, doc, step, btn, orig, n + 1); }, n < 45 ? 2000 : 10000);
}
function _rpEsc(s){ var d = document.createElement('div'); d.textContent = String(s == null ? '' : s); return d.innerHTML; }
async function _rpSources(doc){
  var list = document.getElementById('srclist-' + doc);
  if (!list) return;
  var d;
  try { d = await (await fetch('/api/repair/sources?doc=' + encodeURIComponent(doc))).json(); } catch (e) { return; }
  if (!d || d.missing){ list.innerHTML = '<p class="srcnone">No search yet. Press Find a better source.</p>' + _rpWitness(doc, d || {}) + _rpBench(doc, d || {}); list._data = d || {}; return; }
  var h = '<div class="srclinks">Search by hand: ' + (d.links || []).map(function(l){
    return '<a href="' + _rpEsc(l.url) + '" target="_blank" rel="noopener">' + _rpEsc(l.name) + '</a>'; }).join(' &middot; ')
    + '</div>';
  (d.wisdomlib_local || []).slice(0, 3).forEach(function(b){
    h += '<div class="srccard wl"><b>wisdomlib (local archive)</b>: <a href="' + _rpEsc(b.url) + '" target="_blank" rel="noopener">'
       + _rpEsc(b.book) + '</a>, ' + b.pages + ' pages archived</div>';
  });
  (d.candidates || []).slice(0, 12).forEach(function(c, i){
    var meta = [c.creator, c.publisher, c.year, c.language, c.pages ? c.pages + ' pages' : ''].filter(function(x){ return x; })
      .map(_rpEsc).join(' &middot; ');
    h += '<div class="srccard' + (c.current_scan ? ' cur' : '') + '"><div class="srchead"><span class="srcscore">' + Math.round(c.score)
       + '</span><a href="' + _rpEsc(c.details_url) + '" target="_blank" rel="noopener">' + _rpEsc(c.title || c.identifier) + '</a>'
       + (c.current_scan ? ' <span class="srctag">the scan you have</span>' : '') + '</div>'
       + '<div class="srcmeta">' + meta + '</div><div class="srcwhy">' + _rpEsc((c.why || []).join('; '))
       + (c.ai && c.ai.why ? ' &mdash; AI: ' + _rpEsc(c.ai.why) : '') + '</div><div class="srcacts">'
       + '<button class="tr-rest rp" data-i="' + i + '" onclick="_rpPreview(&#39;' + doc + '&#39;,this.dataset.i)">Preview here</button>'
       + (c.pdf_url && !c.current_scan ? '<button class="tr-rest rp" data-i="' + i + '" onclick="_rpFetch(&#39;' + doc
          + '&#39;,this.dataset.i,&#39;pdf&#39;,this)">Fetch the PDF' + (c.pdf_mb ? ' (' + c.pdf_mb + ' MB)' : '') + '</button>' : '')
       + (c.txt_url && c.purity != null && c.purity >= 0.85 && !c.current_scan ? '<button class="tr-rest rp" data-i="' + i
          + '" onclick="_rpFetch(&#39;' + doc + '&#39;,this.dataset.i,&#39;text&#39;,this)">Fetch the OCR text ('
          + Math.round(100 * c.purity) + '% Devanagari)</button>' : '')
       + '</div></div>';
  });
  if (!(d.candidates || []).length) h += '<p class="srcnone">archive.org offered nothing' + ((d.errors || []).length ? ' (' + _rpEsc(d.errors[0]) + ')' : '')
    + '. Try the e-text sites above.</p>';
  h += '<p class="srcnone">Searched ' + _rpEsc(d.at || '') + ' as: ' + _rpEsc((d.words || []).join(' ')) + '</p>';
  h += _rpWitness(doc, d) + _rpBench(doc, d);   // BENCHMARK_2026_10_11
  list.innerHTML = h; list._data = d;
}
function _rpWitness(doc, d){
  /* ETEXT_WITNESS_2026_10_11: the e-texts fetched for this text, its witnesses, and the pages they offer */
  var f = (d && d.fetched) || [], w = (d && d.witnesses) || [], h = '';
  if (f.length) h += '<div class="srcsub">Fetched into sources' + _RP_BS + _rpEsc(doc) + _RP_BS + '</div>';
  f.forEach(function(x){
    var act = (x.kind === 'text' && x.ok)
      ? '<button class="tr-rest rp" data-f="' + _rpEsc(x.name) + '" onclick="repairStep(&#39;' + doc
        + '&#39;,&#39;witness&#39;,this,{file:this.dataset.f})">Read it as a witness (free)</button>'
      : (x.kind === 'pdf' ? '<span class="srcwhy">A PDF: import it from the dashboard (Import path to inbox) as its own '
                            + 'text, and OCR it with vision.</span>' : '');
    h += '<div class="srccard"><div class="srchead"><b>' + _rpEsc(x.name) + '</b><span class="srcmeta">'
       + Math.max(1, Math.round((x.bytes || 0) / 1024)) + ' KB' + (x.url ? ' &middot; <a href="' + _rpEsc(x.url)
       + '" target="_blank" rel="noopener">its source</a>' : '') + '</span></div><div class="srcacts">' + act + '</div></div>';
  });
  w.forEach(function(x){
    var offers = (x.offers || []).filter(function(o){ return o.text; });
    h += '<div class="srccard wit"><div class="srchead"><b>Witness</b><span>' + _rpEsc(x.witness) + '</span>'
       + (x.state ? '<span class="srctag">' + _rpEsc(x.state) + '</span>' : '') + '</div>'
       + '<div class="srcmeta">' + _rpEsc(x.site || '') + ' &middot; ' + (x.verses || 0) + ' verses in ' + (x.pages || 0) + ' pages'
       + (x.coverage != null ? ' &middot; it reads ' + Math.round(100 * x.coverage) + '% of the scan&#39;s readable pages, in order '
          + Math.round(100 * (x.order || 0)) + '%' : '')
       + (x.ingested != null ? ' &middot; ingested: ' + x.ingested + ' passages' : '') + '</div>'
       + '<div class="srcwhy">' + _rpEsc(x.opinion || '') + '</div>'
       + '<div class="repairbar wbar" id="rp-' + _rpEsc(x.witness) + '">'
       + (x.ingested == null
          ? '<button class="tr-rest rp" data-w="' + _rpEsc(x.witness) + '" onclick="repairStep(&#39;' + doc
            + '&#39;,&#39;witness&#39;,this,{ingest:this.dataset.w})">Ingest it as its own text</button>'
          : '<button class="tr-rest rp" data-w="' + _rpEsc(x.witness) + '" onclick="repairStep(this.dataset.w,&#39;translate&#39;,this)">'
            + 'Translate it: English, then Hindi</button><button class="tr-rest rp" data-w="' + _rpEsc(x.witness)
            + '" onclick="repairStep(this.dataset.w,&#39;release&#39;,this)">Adopt it: publish it to the site</button>')
       + '<div class="rpout"></div></div>';
    if (offers.length){
      h += '<div class="srcsub">The pages the scan cannot read, as this witness reads them (' + offers.length + ')</div>';
      offers.slice(0, 40).forEach(function(o){
        h += '<details class="srcoffer"><summary>page ' + o.page + (o.refs ? ' &middot; ' + _rpEsc(o.refs) : '')
           + ' &middot; ' + _rpEsc(o.why) + '</summary><pre class="srcpre">' + _rpEsc(o.text) + '</pre></details>';
      });
    }
    h += '</div>';
  });
  return h;
}
function _rpBench(doc, d){
  /* BENCHMARK_2026_10_11: the readings of the text compared (benchmark_sources.py), and the opinion */
  var b = d && d.benchmark;
  if (!b || !(b.readings || []).length)
    return '<div class="srcsub">Benchmark</div><p class="srcnone">Not benchmarked yet: press Benchmark the readings (free).</p>';
  var f = function(v, k){ return v == null ? '-' : (+v).toFixed(k == null ? 2 : k); };
  var h = '<div class="srcsub">Benchmark, ' + _rpEsc(String(b.at || '').replace('T', ' ').slice(0, 16))
        + (b.reference ? ', against ' + _rpEsc(b.reference) : '') + '</div><div class="benchwrap"><table class="bench"><thead><tr>'
        + '<th>Reading</th><th>Pages</th><th>Letters</th><th>Misread</th><th>Pages hit</th><th>Level</th><th>Noise</th>'
        + '<th>Plausible</th><th>F1 with ours</th>'   /* QUALITY_2026_10_11: noise in the Devanagari, plausibility */
        + '<th>F1 with the critical text</th></tr></thead><tbody>';
  (b.readings || []).forEach(function(x){
    h += '<tr><td>' + _rpEsc(x.label) + '</td><td>' + x.pages + '</td><td>' + x.letters + '</td><td>' + f(x.misread_letters_pct)
       + '%</td><td>' + f(x.pages_misread_pct, 0) + '%</td><td><span class="lv" data-level="' + _rpEsc(x.level || '') + '">'
       + _rpEsc(x.level || '-') + '</span></td><td>' + (x.noise_pct == null ? '-' : f(x.noise_pct, 1) + '%') + '</td><td>'
       + (x.plausible_pct == null ? '-' : f(x.plausible_pct, 1) + '%') + '</td><td>' + f(x.f1_ours) + '</td><td>' + f(x.f1_ref) + '</td></tr>';
  });
  h += '</tbody></table></div>';
  (b.lines || []).forEach(function(l){ h += '<p class="benchline">' + _rpEsc(l) + '</p>'; });
  return h;
}
function _rpPreview(doc, i){
  var list = document.getElementById('srclist-' + doc), view = document.getElementById('srcview-' + doc);
  var c = list && list._data ? list._data.candidates[+i] : null;
  if (!c || !view) return;
  view.innerHTML = '<div class="srcviewbar"><b>' + _rpEsc(c.title || c.identifier) + '</b> <a href="' + _rpEsc(c.details_url)
    + '" target="_blank" rel="noopener">open on archive.org</a> <button class="tr-rest rp" onclick="this.parentNode.parentNode.innerHTML=&#39;&#39;">Close</button></div>'
    + '<iframe src="' + _rpEsc(c.embed_url) + '" loading="lazy" allowfullscreen></iframe>';
  view.scrollIntoView({behavior: 'smooth', block: 'start'});
}
function _rpFetch(doc, i, kind, btn){
  var list = document.getElementById('srclist-' + doc);
  var c = list && list._data ? list._data.candidates[+i] : null;
  if (c) repairStep(doc, 'fetch', btn, {identifier: c.identifier, kind: kind, mb: c.pdf_mb});
}"""


def _source_verdicts(folder=None) -> Dict[str, dict]:
    """The texts not in the ordinary state: data/source_verdicts.jsonl beside the database, written by
    repair_text.py; the latest record of a text wins. Never the database; a missing file is none."""
    p = pathlib.Path(folder if folder is not None else (ROOT / "data")) / "source_verdicts.jsonl"
    last: Dict[str, dict] = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[str(r["doc"])] = r
    except OSError:
        return {}
    return {d: r for d, r in last.items() if r.get("status") in _REPAIR_STATES}


def _repair_bar(code: str, mode="standard") -> str:
    """The repair bar under a card's notes. mode: standard | aside | repaired | in_repair (True means
    aside, as REPAIR_PATH called it)."""
    import html as _html
    mode = "aside" if mode is True else ("standard" if mode is False else mode)
    c = _html.escape(code, quote=True)
    b = lambda step, label, title: ('<button class="tr-rest rp" data-doc="%s" title="%s" onclick="repairStep(this.dataset.doc,'
                                    '&#39;%s&#39;,this)">%s</button>' % (c, title, step, label))
    if mode == "aside":
        btns = (b("restore", "Restore", "A better scan is in the inbox: offer this text again")
                + b("find", "Find a better source", "archive.org, the wisdomlib archive and the e-text sites"))
    elif mode == "repaired":
        btns = (b("translate", "&#9889; Translate it now: English, then Hindi", "One job; unchanged passages come from the cache")
                + b("assess", "Repair path: what now?", "Free: says what holds it, if anything"))
    elif mode == "in_repair":
        btns = (b("translate", "&#9889; Translate it now: English, then Hindi", "One job; unchanged passages come from the cache")
                + b("release", "Publish it to the site", "The next mirror run sends it to the site as it is now"))
    else:
        btns = (b("assess", "&#128295; Repair path: what now?", "Free: reads the database and the page files, judges the "
                  "debris, and says what the scan needs")
                + b("set_aside", "Set aside", "The scan cannot be repaired: set the text aside until a better scan is "
                    "found. Its files are kept."))
    return ('<div class="repairbar" id="rp-%s">%s<a class="rplink" href="/repair/%s" title="Its repair page: the steps, '
            'the debris judged, the Source desk, and the output of each run">details</a><div class="rpout"></div></div>'
            % (c, btns, c))


def _repair_html(code: str, acts_html: str, shown: list, rec, jd=None) -> str:   # JUDGE_DESK_2026_10_11: jd
    """The Library card's notes (as DESK_HEAL wrote them) and the repair bar under a note that the scan
    stopped the run. The text's state in the register changes what is shown."""
    import html as _html
    rec = rec or {}
    st = rec.get("status")
    at = _html.escape(str(rec.get("at") or "?")[:10])
    why = _html.escape(str(rec.get("reason") or ""))
    if st == "set_aside":
        return ('<div class="cardnote aside" title="data/source_verdicts.jsonl">Set aside on %s: %s. A better scan is '
                'wanted; its files are kept, and its translation is not offered until it is restored.</div>%s'
                % (at, why or "needs a better scan", _judged_note(jd, (), st) + _repair_bar(code, "aside")))
    if st == "complete":
        shown = [n for n in shown if n.get("kind") not in ("quality", "nothing")]
        acts_html += '<div class="cardnote state">Accepted as complete on %s: %s.</div>' % (at, why)
    elif st == "translate_as_is":
        shown = [n for n in shown if n.get("kind") != "held"]
        acts_html += ('<div class="cardnote state">To be translated as is (since %s): %s. The debris guard lets it '
                      'through.</div>' % (at, why))
    elif st == "witness":   # ETEXT_WITNESS_2026_10_11
        acts_html += ('<div class="cardnote state">A witness of %s (%s), made on %s: an e-text, local only. The site '
                      'does not have it until you adopt it (publish it), once it is translated.</div>'
                      % (_html.escape(str(rec.get("of") or "?")), _html.escape(str(rec.get("site") or "e-text")), at))
    elif st == "in_repair":
        acts_html += ('<div class="cardnote state">In repair since %s (%s): the site keeps its last version (%s English, '
                      '%s Hindi) until you publish this one.</div>'
                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))
    elif st == "withdrawn":   # PATH_2026_10_12
        acts_html += ('<div class="cardnote aside" title="data/source_verdicts.jsonl">Withdrawn from the site on %s: %s. The '
                      'site has retired its passages; they are kept here, out of Ask the Corpus, until a better source '
                      'replaces them (Restore sends them back).</div>' % (at, why))
    for n in shown:
        acts_html += ('<div class="cardnote%s" title="%s">%s</div>'
                      % (" repaired" if n.get("kind") == "repaired" else "",
                         _html.escape(n.get("detail") or ""), _html.escape(n.get("text") or "")))
    kinds = {n.get("kind") for n in shown}
    acts_html += _judged_note(jd, kinds, st)   # JUDGE_DESK_2026_10_11
    if st in ("in_repair", "witness"):   # ETEXT_WITNESS_2026_10_11: a witness too
        acts_html += _repair_bar(code, "in_repair")
    elif st == "withdrawn":   # PATH_2026_10_12: Restore, Find a better source
        acts_html += _repair_bar(code, "aside")
    elif "repaired" in kinds:
        acts_html += _repair_bar(code, "repaired")
    elif kinds & {"held", "quality", "nothing"}:
        acts_html += _repair_bar(code, "standard")
    return acts_html


def _repair_waiting(rows, cats, notes, aside, judged=None) -> str:   # JUDGE_DESK_2026_10_11: judged
    """The texts the Library does not list (no English yet) whose last run stopped because of the scan,
    that were repaired, or that are in the register: each with its notes, its translate buttons (unless
    set aside) and its repair path."""
    import html as _html
    listed = {d[0] for docs in cats.values() for d in docs}
    cards = ""
    rdm = _redeem()   # REDEEM_2026_10_14: a text paid for whose English a better reading replaced says so
    for code, title, _cat, total, en in rows:
        if code in listed or not (notes.get(code) or code in aside):
            continue
        rec = aside.get(code) or {}
        c = _html.escape(str(code), quote=True)
        _hold = _hold_reason(code, rec, rdm)   # HOLD_2026_10_14: no translate buttons while the scan or the source comes first
        acts = _hold_note(code, _hold, rec) if (rec.get("status") == "set_aside" or _hold) else (
            '<div class="cardacts"><button class="tr-rest" data-doc="%s" title="Translate its English" '
            'onclick="translateRest(this.dataset.doc,&#39;en&#39;,this)">&#9889; Finish EN</button>'
            '<button class="tr-rest hi" data-doc="%s" title="Translate its Hindi" '
            'onclick="translateRest(this.dataset.doc,&#39;hi&#39;,this)">&#2361;&#2367; Add Hindi</button></div>' % (c, c))
        inner = _repair_html(code, acts, list(notes.get(code, [])), aside.get(code), (judged or {}).get(code))
        if not inner:
            continue
        cards += ('<div class="card-wrap waiting"><div class="card"><div class="ttl">%s</div><div class="code">%s</div>'
                  '<div class="meta"><span class="badge en">EN %d/%d</span></div></div>%s%s</div>'
                  % (_html.escape(str(title)), _html.escape(str(code)), int(en or 0), int(total or 0),
                     _redeem_note(code, rdm), inner))   # REDEEM_2026_10_14
    if not cards:
        return ""
    return ('<h2 class="cat">Not yet readable</h2><p class="rpintro">No English yet. Each card says what held its last run '
            'and offers the next step: translate it when nothing holds it, repair the scan, or look for a better source.'
            '</p><div class="grid">%s</div>' % cards)


@app.route("/api/repair", methods=["GET", "POST"])
def api_repair():
    """POST {doc, step, ...}: one step of a text's repair path, as a run of repair_text.py (kind
    "repair"; "use" is kind "repair_use", under the translate lock) or, for "fetch", of source_desk.py.
    GET says the path is there (the dashboard page asks before it links to /repair/<doc>)."""
    if request.method == "GET":
        return jsonify({"ok": True, "mark": "REPAIR_PATH_2026_10_10", "heal": "REPAIR_HEAL_2026_10_11",
                        "steps": list(_REPAIR_STEPS), "max_usd": _REPAIR_MAX_USD})
    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step in ("judge_all", "benchmark_all", "path_all", "redeem_all") else _validate_doc(data.get("doc"))   # REDEEM_2026_10_14: redeem_all   # PATH_2026_10_12: path_all   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    if step not in _REPAIR_STEPS:
        return jsonify({"error": "unknown step %r (one of %s)" % (step, ", ".join(_REPAIR_STEPS))}), 400
    reason = " ".join(str(data.get("reason") or "").split())[:300]
    argv = [script("repair_text.py"), "--doc", doc, "--from-dashboard"]
    if step == "repair":
        try:
            usd = float(data.get("max_usd") or 1.0)
        except (TypeError, ValueError):
            return jsonify({"error": "max_usd must be a number"}), 400
        if usd > _REPAIR_MAX_USD:
            return jsonify({"error": "$%.2f is above the $%.2f one press may spend; run it by hand: python "
                                     "scripts\\repair_text.py --doc %s --repair --max-usd %.2f"
                                     % (usd, _REPAIR_MAX_USD, doc, usd)}), 400
        argv += ["--repair", "--max-usd", "%.2f" % max(0.05, usd)]
    elif step == "use":
        argv.append("--use-repaired")
        if data.get("replace") not in (None, ""):
            try:
                argv += ["--replace", str(int(data.get("replace")))]
            except (TypeError, ValueError):
                return jsonify({"error": "replace must be a whole number"}), 400
    elif step == "set_aside":
        argv += ["--set-aside", reason or "needs a better scan"]
    elif step == "as_is":
        argv += ["--as-is", reason or "debris judged cosmetic"]
    elif step == "accept":
        argv += ["--accept", reason or "what is left is not Sanskrit"]
    elif step == "hold":
        argv += ["--hold", reason or "re-translating after the repair"]
    elif step in ("restore", "release"):
        argv.append("--" + step)
    elif step == "find":
        argv.append("--find-source")
        if data.get("ai"):
            argv.append("--ai")
    elif step == "fetch":
        ident = str(data.get("identifier") or "")
        kind = str(data.get("kind") or "pdf")
        if not re.match(r"^[A-Za-z0-9._\-]{1,120}$", ident) or kind not in ("pdf", "text"):
            return jsonify({"error": "fetch needs an archive.org identifier and kind pdf or text"}), 400
        argv = [script("source_desk.py"), "--doc", doc, "--fetch", ident, "--kind", kind]
    elif step == "witness":   # ETEXT_WITNESS_2026_10_11: read, write or ingest an e-text witness
        argv = [script("etext_witness.py"), "--doc", doc, "--from-dashboard"]
        f, url, ing = str(data.get("file") or ""), str(data.get("url") or "").strip(), str(data.get("ingest") or "")
        if ing:
            if not re.match(r"^[A-Za-z0-9_\-]{1,200}$", ing) or not ing.startswith(doc + "__w_"):
                return jsonify({"error": "ingest needs a witness of this text (<doc>__w_<site>)"}), 400
            argv += ["--ingest", "--witness", ing]
        elif f:
            if not re.match(r"^[A-Za-z0-9._\- ()]{1,160}$", f) or f.startswith("."):
                return jsonify({"error": "file must be the name of a file in sources\\<doc>\\"}), 400
            argv += ["--file", str(SOURCES_DIR / doc / f)]
        elif url:
            if not re.match(r"^https?://[^\s\"'<>]{4,500}$", url):
                return jsonify({"error": "url must be an http(s) link"}), 400
            argv += ["--url", url]
        else:
            return jsonify({"error": "witness needs a file, a url, or a witness to ingest"}), 400
        if data.get("write") and not ing:
            argv.append("--write")
    elif step == "benchmark":   # BENCHMARK_2026_10_11: free and read-only
        argv = [script("benchmark_sources.py"), "--doc", doc, "--from-dashboard"]
    elif step == "benchmark_all":
        argv = [script("benchmark_sources.py"), "--all", "--from-dashboard"]
    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    elif step == "withdraw":   # PATH_2026_10_12: off the site (the mirror retires it there), out of Ask here
        argv += ["--withdraw", reason or "its text is damaged: a better source is wanted"]
    elif step == "path_all":   # PATH_2026_10_12: free and read-only
        argv = [script("text_path.py"), "--from-dashboard"]
    elif step == "redeem_all":   # REDEEM_2026_10_14: free and read-only
        argv = [script("redeem.py"), "--from-dashboard"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
        pages = str(data.get("pages") or "")
        if pages:
            if not re.match(r"^[0-9][0-9,\-]{0,199}$", pages):
                return jsonify({"error": "pages must be numbers and ranges: 2,20-21"}), 400
            argv += ["--pages", pages]
        if step == "reingest":
            argv.append("--apply")
            if data.get("replace") not in (None, ""):
                try:
                    argv += ["--replace", str(int(data.get("replace")))]
                except (TypeError, ValueError):
                    return jsonify({"error": "replace must be a whole number"}), 400
    kind = "repair_use" if step in ("use", "reingest") or (step == "witness" and data.get("ingest")) else "repair"   # ETEXT_WITNESS_2026_10_11; REINGEST_2026_10_12
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})


def _witness_info(doc: str) -> dict:
    """ETEXT_WITNESS_2026_10_11: the files fetched into sources/<doc>/ and the witnesses of the text (from
    data/witnesses.jsonl, their align.json and the register), for the repair page. Small files only."""
    import re as _re
    ok_name = _re.compile(r"^[A-Za-z0-9._\- ()]{1,160}$")
    ok_url = _re.compile(r"^https?://[^\s\"'<>]{4,500}$")
    fetched, wits = [], []
    try:
        for f in sorted((SOURCES_DIR / doc).iterdir()):
            if not f.is_file() or f.name.endswith((".json", ".part")):
                continue
            side = {}
            try:
                side = json.loads(f.with_name(f.name + ".json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            url = str(side.get("url") or side.get("details") or "")
            fetched.append({"name": f.name, "bytes": f.stat().st_size, "ok": bool(ok_name.match(f.name)) and not f.name.startswith("."),
                            "kind": "pdf" if f.suffix.lower() == ".pdf" else "text", "url": url if ok_url.match(url) else ""})
    except OSError:
        pass
    seen = {}
    try:
        for line in WITNESSES_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc") == doc and r.get("witness"):
                seen[r["witness"]] = dict(seen.get(r["witness"], {}), **r)
    except OSError:
        pass
    reg = {}
    try:
        for line in (WITNESSES_LOG.parent / "source_verdicts.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc") in seen:
                reg[r["doc"]] = r.get("status")
    except OSError:
        pass
    for w, r in sorted(seen.items(), key=lambda x: str(x[1].get("at") or "")):
        al = {}
        try:
            al = json.loads((WITNESS_DIR / w / "align.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        offers = [dict(o, text=str(o.get("text") or "")[:1500]) for o in (al.get("offers") or [])[:40] if isinstance(o, dict)]
        url = str(r.get("url") or "")
        wits.append({"witness": w, "site": r.get("site"), "verses": r.get("verses"), "pages": r.get("pages"),
                     "coverage": r.get("coverage"), "order": r.get("order"), "opinion": r.get("opinion"),
                     "ingested": r.get("ingested"), "at": r.get("at"), "url": url if ok_url.match(url) else "",
                     "state": {"witness": "local only", "released": "adopted"}.get(reg.get(w), reg.get(w) or ""),
                     "offers": offers})
    return {"fetched": fetched, "witnesses": wits}


# BENCHMARK_2026_10_11 -------------------------------------------------------------------------
# The readings of each text compared (scripts/benchmark_sources.py: Tesseract, vision, the repair, the
# database, the text before its repair, archive.org's OCR, the witnesses and the critical e-texts), and
# the effect of the debris on the translation, measured. Small files only (data/benchmarks/).
BENCH_DIR = ROOT / "data" / "benchmarks"


def _bench(doc: str):
    """The last benchmark of a text (data/benchmarks/<doc>.json), or None."""
    try:
        r = json.loads((BENCH_DIR / ("%s.json" % doc)).read_text(encoding="utf-8"))
        return r if isinstance(r, dict) else None
    except (OSError, ValueError):
        return None


@app.get("/benchmarks")
def benchmarks_page():
    """Every text benchmarked: misread letters in Tesseract, in ours (the repair, else the database) and in
    archive.org's OCR; the critical e-text's F1; the English before the repair and how much of it was made
    from damaged text; the English now; and the opinion. Reads small files only."""
    import html as _html
    e = _html.escape
    rows = []
    try:
        for p in sorted(BENCH_DIR.glob("*.json")):
            if p.name.startswith("_"):
                continue
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get("doc") and r.get("readings"):
                rows.append(r)
    except OSError:
        pass

    def red(r, label):
        return next((x for x in r.get("readings") or [] if x.get("label") == label), None)

    pct = lambda x: (("%.2f%%" % float(x.get("misread_letters_pct") or 0)) + (   # QUALITY_2026_10_11: and the noise
        " / %.1f%%" % float(x["noise_pct"]) if x.get("noise_pct") is not None else "")) if x else "-"
    trs, improved = "", 0
    for r in rows:
        te, ours = red(r, "tesseract"), (red(r, "consensus") or red(r, "database"))
        if te and ours and ours.get("label") == "consensus" and ours["misread_letters_pct"] < te["misread_letters_pct"]:
            improved += 1
        tr = r.get("translations") or {}
        b, n = tr.get("before") or {}, tr.get("now") or {}
        arch = [x for x in r.get("readings") or [] if x.get("kind") == "archive-ocr"]
        ref = ("%s: ours %s" % (r.get("reference"), "-" if not ours or ours.get("f1_ref") is None else "%.2f" % ours["f1_ref"])
               if r.get("reference") else "-")
        before = "-"
        if b.get("english"):
            before = "%s EN; %s%% of it from damaged text" % (b["english"], "?" if b.get("translated_misread_pct") is None
                                                               else "%.0f" % float(b["translated_misread_pct"]))
        trs += ('<tr><td><a href="/repair/%s">%s</a></td><td>%s</td><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td>'
                '<td>%s</td></tr>' % (e(r["doc"], quote=True), e(r["doc"]), pct(te), pct(ours),
                                      ('<br><span class="muted">%s</span>' % e(ours["label"])) if ours else "",
                                      e("; ".join("%s %s" % (x["label"], pct(x)) for x in arch)) or "-", e(ref), e(before),
                                      e(("%s of %s EN, %s HI" % (n.get("english", 0), n.get("passages", 0), n.get("hindi", 0)))
                                        + (("; judged %.2f of 5 on %d, %d%% a wrong meaning" % (   # REINGEST_2026_10_12
                                            n["reviews"]["fidelity"], n["reviews"]["n"],
                                            round(100.0 * n["reviews"]["serious"] / n["reviews"]["n"])))
                                           if (n.get("reviews") or {}).get("serious") is not None else ""))
                                      if n else "-"))
        if r.get("lines"):
            trs += '<tr><td colspan="7" class="muted" style="line-height:1.55">%s</td></tr>' % "<br>".join(
                e(x) for x in r["lines"])
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Each text\'s readings compared on the same pages: '
            'Tesseract, vision, the repair (ours), the text before its repair, archive.org\'s OCR and the critical '
            'e-texts, by the share of letters misread and, where a critical text is fetched, by how much of it each '
            'reading has. The translation: how much of the English made before the repair came from damaged text, '
            'and how much there is now. %d text(s) benchmarked; the repair cut the misreading in %d.</p>'
            '<div class="repairbar" id="rp-corpus" style="margin-top:10px"><button class="tr-rest rp" data-doc="corpus" '
            'onclick="repairStep(this.dataset.doc,&#39;benchmark_all&#39;,this)">Benchmark every text again (free, a minute '
            'or two)</button><div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>Tesseract '
            'misreads / noise</th><th>Ours misreads / noise</th><th>archive.org OCR</th><th>Critical e-text</th><th>English before the '
            'repair</th><th>Now</th></tr></thead><tbody>%s</tbody></table></div>%s</div>'
            % (len(rows), improved, trs, "" if rows else '<p class="srcnone">Nothing benchmarked yet. Press Benchmark '
                                                           'every text again.</p>'))
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Benchmarks</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.srcnone{color:var(--muted);font-size:12px;margin:10px 0}
""" + _REPAIR_CSS + _SOURCES_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><a href="/path">The path</a><h1>Benchmarks</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


PATH_FILE = ROOT / "data" / "text_path.json"   # PATH_2026_10_12: written by scripts/text_path.py


@app.get("/path")
def path_page():
    """PATH_2026_10_12: the path of every text (scripts/text_path.py): use the repair, retire, ingest, repair the scan,
    find a source, translate, translate again, judge a sample, in repair, done; each with its reason in numbers, its
    next command and its cost. Reads one small file."""
    import html as _html
    e = _html.escape
    try:
        res = json.loads(PATH_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        res = None
    money = lambda x: ("$%.2f" % x) if x >= 0.995 else ("$%.3f" % x)
    chips, groups = "", ""
    if res:
        tot = res.get("totals") or {}
        for key, label, desc in res.get("paths") or []:
            rows = [t for t in res.get("texts") or [] if t.get("path") == key and not t.get("retired")]
            if not rows:
                continue
            tt = tot.get(key) or {}
            hi, lo = tt.get("cost_hi") or 0, tt.get("cost_lo")
            side = []   # MIRROR_CAP_2026_10_12: the median text's price beside the corpus's
            if tt.get("cost") and lo is not None and lo < 0.95 * tt["cost"]:
                side.append("from %s at the median text's price" % money(lo))
            if tt.get("cost") and hi > 1.05 * tt["cost"]:
                side.append("up to %s at the dearest text's price" % money(hi))
            cost = ((" &middot; about %s now" % money(tt["cost"])) if tt.get("cost") else "") + (
                (" (%s)" % "; ".join(side)) if side else "") + (
                (" &middot; then %s to translate" % money(tt["then"])) if tt.get("then") else "")
            chips += '<a class="pchip" href="#p-%s">%s <b>%d</b></a>' % (e(key, quote=True), e(label), len(rows))
            trs = ""
            for t in rows:
                lines = "".join('<div class="pnext">NEXT %s</div>' % e(n) for n in t.get("next") or [])
                lines += "".join('<div class="palso">ALSO %s</div>' % e(n) for n in t.get("also") or [])
                link = ('<a href="/repair/%s">%s</a>' % (e(t["doc"], quote=True), e(t["doc"]))) if not t.get("new") else e(t["doc"])
                trs += '<tr><td class="pdoc">%s</td><td>%s%s</td><td class="pcost">%s</td></tr>' % (
                    link, e(t.get("why") or ""), lines, (money(t["cost"]) if t.get("cost") else "") + (
                        ("<br><span class=\"muted\">then %s</span>" % money(t["then"])) if t.get("then") else ""))
            groups += ('<h2 id="p-%s" class="ph">%s <span>%d</span></h2><p class="pdesc">%s%s</p><div class="srcwrap">'
                       '<table class="srct"><tbody>%s</tbody></table></div>' % (e(key, quote=True), e(label), len(rows),
                                                                              e(desc), cost, trs))
        pr = res.get("prices") or {}
        head = ('Charted %s: vision %s a page at the corpus price, its last 300 calls (%d text(s) priced from their own '
                'calls; the median %s, the dearest %s a page), translation %s a passage, measured in usage_log.'
                % (e(str(res.get("at", "?")).replace("T", " ")), "$%.4f" % (pr.get("vision_page") or 0),
                   len(pr.get("measured") or []),
                   ("$%.4f" % pr["vision_median"]) if pr.get("vision_median") else "-",   # MIRROR_CAP_2026_10_12
                   "$%.4f" % (pr.get("vision_dear") or 0), "$%.5f" % (pr.get("passage") or 0)))
    else:
        head = "Not charted yet: press Chart the path again, or run python scripts\\text_path.py (free, read-only)."
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Every text has one way forward: use the repair '
            'vision has made, retire a duplicate, ingest what is not in yet, repair the scan with vision, find a critical '
            'e-text or a better scan, translate a clean reading, translate again what the judge marks, judge a sample, '
            'or nothing. %s</p><div class="pchips">%s</div><div class="repairbar" id="rp-corpus" style="margin-top:10px">'
            '<button class="tr-rest rp" data-doc="corpus" onclick="repairStep(this.dataset.doc,&#39;path_all&#39;,this)">'
            'Chart the path again (free, read-only; a few minutes)</button><div class="rpout"></div></div>%s</div>'
            % (head, chips, groups))
    css = (".pchips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.pchip{border:1px solid var(--border);"
           "border-radius:7px;padding:4px 10px;font-size:12px;color:var(--cream);text-decoration:none}.pchip b{color:var(--gold)}"
           ".ph{font-size:15px;color:var(--gold);margin:22px 0 2px}.ph span{color:var(--muted);font-weight:400}"
           ".pdesc{color:var(--muted);font-size:12px;margin-bottom:6px}.pdoc{width:28%;word-break:break-all;font-weight:600}"
           ".pdoc a{color:var(--cream)}.pnext,.palso{font-family:ui-monospace,monospace;font-size:11px;margin-top:3px;"
           "word-break:break-all}.pnext{color:#9ec3ff}.palso{color:#d9a35b}.pcost{white-space:nowrap;text-align:right}"
           ".muted{color:var(--muted)}")
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>The path</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.srcnone{color:var(--muted);font-size:12px;margin:10px 0}
""" + _REPAIR_CSS + _SOURCES_CSS + css + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><a href="/benchmarks">Benchmarks</a><a href="/redeem">What is redeemed</a><h1>The path</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


REDEEM_FILE = ROOT / "data" / "redeem.json"   # REDEEM_2026_10_14: written by scripts/redeem.py
_REDEEM_CACHE = {"key": None, "res": None}
_REDEEM_CLS = {"redeemed": "r-ok", "mostly": "r-mid", "redo": "r-lo", "source": "r-lo", "replaced": "r-mid",
               "withdrawn": "r-off"}


def _redeem() -> dict:
    """REDEEM_2026_10_14: the last count of what of the translation is kept (data/redeem.json), read again only when
    the file changes; {} when there is none."""
    try:
        st = REDEEM_FILE.stat()
        key = (st.st_mtime, st.st_size)
    except OSError:
        return {}
    if _REDEEM_CACHE["key"] != key:
        try:
            _REDEEM_CACHE["res"] = json.loads(REDEEM_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _REDEEM_CACHE["res"] = None
        _REDEEM_CACHE["key"] = key
    return _REDEEM_CACHE["res"] or {}


def _redeem_note(code: str, res: dict) -> str:
    """The Library card's line: how much of this text's English is kept, and what the rest needs."""
    import html as _html
    for t in (res or {}).get("texts") or []:
        if t.get("doc") == code:
            c = t.get("classes") or {}
            tip = ("judged sound %s, vision %s, no debris seen %s, debris %s, judged wrong %s; translation spent %s, of "
                   "it %s on English that cannot be kept as it is (redeem.py, %s)"
                   % (c.get("judged_sound", 0), c.get("vision", 0), c.get("no_debris", 0), c.get("debris", 0),
                      c.get("judged_wrong", 0), "$%.3f" % (t.get("spent") or 0), "$%.3f" % (t.get("at_risk") or 0),
                      str(res.get("at") or "?")[:16].replace("T", " ")))
            return ('<a class="rdm %s" href="/redeem#r-%s" title="%s">%s</a>'
                    % (_REDEEM_CLS.get(t.get("verdict"), "r-mid"), _html.escape(t.get("verdict") or "", quote=True),
                       _html.escape(tip, quote=True), _html.escape(t.get("line") or "")))
    return ""


_REDEEM_CSS = (".rdm{display:block;margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;"
               "border-left:2px solid;padding:2px 0 2px 7px;text-decoration:none}.rdm:hover{text-decoration:underline}"
               ".rdm.r-ok{color:#7cc497;border-color:#2f6b45}.rdm.r-mid{color:#d9b36a;border-color:#6b5420}"
               ".rdm.r-lo{color:#e09a9a;border-color:#7a2f2f}.rdm.r-off{color:#8a8070;border-color:#3a352b}")


# SCHOLAR_2026_10_14 / HOLD_2026_10_14 -------------------------------------------------------------------------
_PATH_CACHE = {"key": None, "by": {}}
_HOLD_PATHS = {"repair": "repair its scan first", "source": "a better source first", "retire": "it is to be retired"}


def _path_texts() -> Dict[str, dict]:
    """HOLD_2026_10_14: the last chart of the path (data/text_path.json) as {doc: its row}, read again only when the
    file changes; {} when there is none."""
    try:
        st = PATH_FILE.stat()
        key = (str(PATH_FILE), st.st_mtime, st.st_size)
    except OSError:
        return {}
    if _PATH_CACHE["key"] != key:
        try:
            res = json.loads(PATH_FILE.read_text(encoding="utf-8"))
            _PATH_CACHE["by"] = {str(t.get("doc")): t for t in (res.get("texts") or []) if isinstance(t, dict)}
        except (OSError, ValueError, AttributeError):
            _PATH_CACHE["by"] = {}
        _PATH_CACHE["key"] = key
    return _PATH_CACHE["by"]


def _hold_reason(code: str, rec=None, rdm=None) -> str:
    """HOLD_2026_10_14: why the Library does not offer Finish EN and Add Hindi on this text now ('' when it does).
    The register first (withdrawn, set aside); then the path (repair the scan, a better source, retire); for a text
    the path has not charted, the count (redeem.py: to translate again after the repair, a source first). Translating
    now would pay for English made from the same misreading."""
    st = (rec or {}).get("status")
    if st == "withdrawn":
        return "withdrawn from the site: a better source first"
    if st == "set_aside":
        return "set aside: a better scan first"
    p = _path_texts().get(code)
    if p is not None:
        step = p.get("path")
        return ("%s (the path: %s)" % (_HOLD_PATHS[step], p.get("why") or step)) if step in _HOLD_PATHS else ""
    for t in (rdm or {}).get("texts") or []:
        if t.get("doc") == code:
            if t.get("verdict") == "redo":
                return "repair its scan first (less than half of its English can be kept)"
            if t.get("verdict") == "source":
                return "a better source first (its scan is not here)"
            return ""
    return ""


def _hold_note(code: str, reason: str, rec=None) -> str:
    """HOLD_2026_10_14: the card's line for a hold ('' for a text whose register state the card already explains)."""
    import html as _html
    if not reason or (rec or {}).get("status") in ("withdrawn", "set_aside"):
        return ""
    return ('<div class="cardnote state" title="HOLD_2026_10_14: data/text_path.json, data/redeem.json">Finish EN and Add '
            'Hindi are not offered now: %s. <a href="/path" style="color:inherit">The path</a> has the next step; chart '
            'it again there after a repair.</div>' % _html.escape(reason))


# LIBRARY_SCHOLAR_2026_10_16 -----------------------------------------------------------------------------------
# The scholarly English (scripts/scholar_translate.py, the table scholar_translations) on the Library's cards and in
# the reader, beside the working English (passages.translation, which the site shows). Read-only: the working English,
# the site and the scholarly rows are not changed.
_SCHOLAR_COVER = {"key": None, "at": 0.0, "res": {}}
_SCHOLAR_TTL = 120.0   # seconds: counted again at most this often, unless a row or a passage is added
_SCHOLAR_CSS = (".badge.sc{background:#2a1f3a;color:#c3a6e8}"
                ".schl{display:block;margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;"
                "color:#c3a6e8;border-left:2px solid #5a4380;padding:2px 0 2px 7px}.schl a{color:inherit}"
                ".schl b{color:var(--cream)}")


def _scholar_st():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import scholar_translate as _st
    return _st


def _scholar_cover(con) -> Dict[str, dict]:
    """LIBRARY_SCHOLAR_2026_10_16: {doc: its scholarly English}: "verses" (each verse's latest row, as /scholar/<doc>
    shows it, whose Sanskrit is unchanged), "passed", "flagged", "source_doubt", "accepted" and "rejected" (by a person),
    "stale" (the Sanskrit changed since), "engines" ({engine: verses}), "spent" ($ of all its rows), "last" (the last
    row's time). Counted again when a row or a passage is added, or after _SCHOLAR_TTL; {} when there is no such table
    or on any error (the Library is never stopped by it)."""
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scholar_translations'").fetchone():
            return {}
        key = tuple(con.execute("SELECT (SELECT MAX(id) FROM scholar_translations), (SELECT COUNT(*) FROM "
                                "scholar_translations), (SELECT MAX(id) FROM passages)").fetchone())
        now_ = time.time()
        if _SCHOLAR_COVER["key"] == key and now_ - _SCHOLAR_COVER["at"] < _SCHOLAR_TTL:
            return _SCHOLAR_COVER["res"]
        _st = _scholar_st()
        res: Dict[str, dict] = {}
        for doc, st, h, rv, eng, ptext in con.execute(
                "SELECT s.doc_code, s.status, s.src_hash, s.review_verdict, s.engine, p.text FROM scholar_translations s "
                "LEFT JOIN passages p ON p.id = s.passage_id WHERE s.id IN (SELECT MAX(id) FROM scholar_translations "
                "GROUP BY passage_id)"):
            c = res.setdefault(doc, {"verses": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "accepted": 0,
                                     "rejected": 0, "stale": 0, "engines": {}, "spent": 0.0, "last": ""})
            if ptext is None or _st.src_hash(ptext) != h:
                c["stale"] += 1
                continue
            c["verses"] += 1
            if st in ("passed", "flagged", "source_doubt"):
                c[st] += 1
            if rv == "accept":
                c["accepted"] += 1
            elif rv == "reject":
                c["rejected"] += 1
            c["engines"][eng or "?"] = c["engines"].get(eng or "?", 0) + 1
        for doc, spent, last in con.execute("SELECT doc_code, COALESCE(SUM(cost_usd), 0), MAX(created_at) FROM "
                                            "scholar_translations GROUP BY doc_code"):
            if doc in res:
                res[doc]["spent"] = float(spent or 0.0)
                res[doc]["last"] = str(last or "")
        _SCHOLAR_COVER.update(key=key, at=now_, res=res)
        return res
    except Exception:
        return {}


def _scholar_badge(code: str, sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the card's "SC n" ('' when none)."""
    c = (sc or {}).get(code)
    if not c or not c.get("verses"):
        return ""
    return ('<span class="badge sc" title="Verses in scholarly English (scholar_translate.py), beside the working '
            'English (EN)">SC {:,}</span>'.format(c["verses"]))


def _scholar_line(code: str, sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the card's line for its scholarly English, with the links to read it ('' when none)."""
    import html as _html
    from urllib.parse import quote
    c = (sc or {}).get(code)
    if not c or not (c.get("verses") or c.get("stale")):
        return ""
    n_ = lambda v: "{:,}".format(int(v or 0))
    top = sorted(c["engines"].items(), key=lambda kv: (-kv[1], kv[0]))
    eng = (top[0][0].split(":", 1)[-1] + ((" and %d other%s" % (len(top) - 1, "s" if len(top) > 2 else ""))
                                          if len(top) > 1 else "")) if top else "?"
    parts = ["%s passed" % n_(c["passed"]), "%s flagged" % n_(c["flagged"])]
    if c["source_doubt"]:
        parts.append("%s source doubts" % n_(c["source_doubt"]))
    if c["accepted"] or c["rejected"]:
        parts.append("%s accepted and %s rejected by a person" % (n_(c["accepted"]), n_(c["rejected"])))
    if c["stale"]:
        parts.append("%s stale (the Sanskrit changed)" % n_(c["stale"]))
    q = quote(code, safe="")
    tip = ("The scholarly English, verse by verse (scholar_translate.py): drafted with its context and glossary, read by "
           "a critic, revised, judged. It is kept beside the working English (EN, which the site shows) and is not on "
           "the site yet. $%.2f spent on all its rows; the last on %s." % (c["spent"], c["last"][:16].replace("T", " ")))
    return ('<div class="schl" title="%s">Scholarly English: <b>%s</b> verses by %s; %s. <a href="/scholar/%s">Verse by '
            'verse</a> &middot; <a href="/scholar/%s/prose">as prose</a></div>'
            % (_html.escape(tip, quote=True), n_(c["verses"]), _html.escape(eng), _html.escape(", ".join(parts)), q, q))


def _scholar_sum(sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the Library header's count of the verses in scholarly English ('' when none)."""
    n = sum(int(c.get("verses") or 0) for c in (sc or {}).values())
    if not n:
        return ""
    return (" &middot; <a href='/scholar' style='color:#c3a6e8;text-decoration:none' title='LIBRARY_SCHOLAR_2026_10_16: "
            "the scholarly English, text by text'>{:,} verses in scholarly English</a>".format(n))


def _scholar_rows(con, doc: str, type_clause: str = "", type_params=(), limit: int = 50, offset: int = 0) -> tuple:
    """LIBRARY_SCHOLAR_2026_10_16: ({(page_no, idx): its scholarly English}, the text's verses in scholarly English) for
    the passages one reader page lists (the filter, order, limit and offset of /api/passages): each passage's latest
    row, as /scholar/<doc> shows it, when its Sanskrit is unchanged, and the link to it there (that page shows 200 rows
    a page). ({}, 0) when there is none, or on any error."""
    try:
        n = int(((_scholar_cover(con).get(doc) or {}).get("verses")) or 0)
        if not n:
            return {}, 0
        listed = con.execute("SELECT p.id, p.page_no, p.idx, p.text FROM passages p JOIN docs d ON d.id=p.doc_id WHERE "
                             "d.code=?%s ORDER BY p.page_no, p.idx LIMIT ? OFFSET ?" % type_clause,
                             (doc, *type_params, limit, offset)).fetchall()
        if not listed:
            return {}, n
        from urllib.parse import quote
        _st = _scholar_st()
        order = [r[0] for r in con.execute(
            "SELECT s.passage_id FROM scholar_translations s LEFT JOIN passages p ON p.id = s.passage_id WHERE "
            "s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY "
            "passage_id) ORDER BY COALESCE(p.page_no, s.page_no), COALESCE(p.idx, s.idx), s.id", (doc, doc))]
        rank = {pid: k for k, pid in enumerate(order)}
        ids = [r[0] for r in listed]
        got = {}
        for pid, tr, st, h, eng, gref, ref, rv in con.execute(
                "SELECT passage_id, translation, status, src_hash, engine, group_ref, verse_ref, review_verdict FROM "
                "scholar_translations WHERE id IN (SELECT MAX(id) FROM scholar_translations WHERE passage_id IN (%s) "
                "GROUP BY passage_id)" % ",".join("?" * len(ids)), ids):
            got[pid] = (tr, st, h, eng, gref, ref, rv)
        out, q = {}, quote(doc, safe="")
        for pid, page, idx, text in listed:
            g = got.get(pid)
            if not g or not (g[0] or "").strip() or _st.src_hash(text) != g[2]:
                continue
            tr, st, _h, eng, gref, ref, rv = g
            anchor = str(gref).split("-", 1)[0] if gref else str(ref or "")
            out[(page, idx)] = {"translation": tr, "status": st or "", "engine": eng or "", "review": rv or "",
                                "sentence": gref or "", "ref": ref or "",
                                "href": "/scholar/%s?offset=%d#v-%s" % (q, (rank.get(pid, 0) // 200) * 200,
                                                                       quote(anchor, safe=".-_"))}
        return out, n
    except Exception:
        return {}, 0


def _with_scholar(d: dict, sch: dict) -> dict:
    """LIBRARY_SCHOLAR_2026_10_16: a reader passage with its scholarly English, when it has one."""
    s = (sch or {}).get((d.get("page_no"), d.get("idx")))
    if s:
        d["scholar"] = s
    return d


@app.get("/scholar")
def scholar_index_page():
    """SCHOLAR_2026_10_14: the scholarly English (scripts/scholar_translate.py), text by text. Reads the database
    read-only."""
    return _scholar_page(None)


@app.get("/scholar/<doc>")
def scholar_doc_page(doc):
    """SCHOLAR_2026_10_14: one text's scholarly English beside its Sanskrit and its working English, verse by verse."""
    doc = _validate_doc(doc)
    if not doc:
        return "invalid doc", 400
    return _scholar_page(doc)


@app.get("/scholar/<doc>/prose")
def scholar_prose_page(doc):
    """SCHOLAR_V2_2026_10_14: one text's scholarly English read as prose, chapter by chapter, its notes at each
    chapter's end. Reads the database read-only."""
    doc = _validate_doc(doc)
    if not doc:
        return "invalid doc", 400
    return _scholar_page(doc, prose=True)


def _scholar_page(doc, prose=False):
    import html as _html
    db_path = request.args.get("db", "data/context.db")
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import scholar_translate as _st
        con = sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            if doc and prose:   # SCHOLAR_V2_2026_10_14
                return _st.render_prose(con, doc, nav=True)
            if doc:
                try:
                    off = max(0, int(request.args.get("offset", 0) or 0))
                except ValueError:
                    off = 0
                return _st.render_doc(con, doc, offset=off, limit=200, nav=True)
            return _st.render_index(con, nav=True)
        finally:
            con.close()
    except Exception as e:
        return "<pre>Scholarly English: %s</pre>" % _html.escape("%s: %s" % (type(e).__name__, e)), 500


@app.get("/redeem")
def redeem_page():
    """REDEEM_2026_10_14: what of the translation already paid for is kept, and what is not, text by text
    (scripts/redeem.py). Reads one small file."""
    import html as _html
    e = _html.escape
    res = _redeem()
    money = lambda x: ("$%.2f" % x) if x >= 0.995 else ("$%.3f" % x)
    groups, chips = "", ""
    if res:
        t = res.get("totals") or {}
        for key, label, desc in res.get("verdicts") or []:
            rows = [x for x in res.get("texts") or [] if x.get("verdict") == key]
            if not rows:
                continue
            chips += '<a class="pchip %s" href="#r-%s">%s <b>%d</b></a>' % (_REDEEM_CLS.get(key, ""), e(key, quote=True),
                                                                          e(label), len(rows))
            trs = ""
            for x in rows:
                c = x.get("classes") or {}
                n_ = lambda v: "{:,}".format(int(v or 0))
                trs += ('<tr><td class="pdoc"><a href="/repair/%s">%s</a><div class="rdm %s" style="margin-top:3px">%s</div>'
                        '</td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                        '<td class="num">%d of %d</td><td class="num">%s</td><td class="num">%s</td></tr>'
                        % (e(x["doc"], quote=True), e(x["doc"]), _REDEEM_CLS.get(key, ""), e(x.get("line") or ""),
                           n_(x.get("english")), n_(x.get("keep")), n_(c.get("debris")), c.get("judged_wrong", 0),
                           x.get("judged", 0), money(x.get("spent") or 0), money(x.get("at_risk") or 0)))
            groups += ('<h2 id="r-%s" class="ph">%s <span>%d</span></h2><p class="pdesc">%s</p><div class="srcwrap">'
                       '<table class="srct"><thead><tr><th>Text</th><th>English</th><th>Kept</th><th>Debris</th>'
                       '<th>Judged wrong</th><th>Spent</th><th>At risk</th></tr></thead><tbody>%s</tbody></table></div>'
                       % (e(key, quote=True), e(label), len(rows), e(desc), trs))
        n_ = lambda v: "{:,}".format(int(v or 0))
        rep = t.get("spent_replaced") or 0.0
        head = ('Counted %s: <b>%s</b> English; <b>%s</b> kept (%.0f%%); %s made from misread Sanskrit; %s judged wrong. '
                'The translation cost %s (repriced at today\'s prices), %s of it on English that cannot be kept as it '
                'is%s; translating those again costs about %s. What lasts is the clean reading.'
                % (e(str(res.get("at", "?")).replace("T", " ")), n_(t.get("english")), n_(t.get("keep")),
                   (100.0 * t.get("keep", 0) / t["english"]) if t.get("english") else 0.0, n_(t.get("debris")),
                   n_(t.get("judged_wrong")), money(t.get("spent") or 0), money((t.get("at_risk") or 0) - rep),
                   (", %s on English a better reading replaced" % money(rep)) if rep else "",
                   money(t.get("redo_cost") or 0)))
    else:
        head = "Not counted yet: press Count again, or run python scripts\\redeem.py (free, read-only)."
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">What of the translation already paid for can be '
            'kept, and what cannot. %s</p><div class="pchips">%s</div><div class="repairbar" id="rp-corpus" '
            'style="margin-top:10px"><button class="tr-rest rp" data-doc="corpus" '
            'onclick="repairStep(this.dataset.doc,&#39;redeem_all&#39;,this)">Count again (free, a minute)</button>'
            '<div class="rpout"></div></div>%s</div>' % (head, chips, groups))
    css = (".pchips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.pchip{border:1px solid var(--border);"
           "border-radius:7px;padding:4px 10px;font-size:12px;color:var(--cream);text-decoration:none}.pchip b{color:var(--gold)}"
           ".pchip.r-ok{border-color:#2f6b45}.pchip.r-lo{border-color:#7a2f2f}.pchip.r-mid{border-color:#6b5420}"
           ".ph{font-size:15px;color:var(--gold);margin:22px 0 2px}.ph span{color:var(--muted);font-weight:400}"
           ".pdesc{color:var(--muted);font-size:12px;margin-bottom:6px}.pdoc{width:46%;word-break:break-word;font-weight:600}"
           ".pdoc a{color:var(--cream)}.num{white-space:nowrap;text-align:right}th{text-align:left;color:var(--muted);"
           "font-weight:600;font-size:11px}" + _REDEEM_CSS)
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>What is redeemed</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
""" + _REPAIR_CSS + _SOURCES_CSS + css + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/path">The path</a><a href="/sources">Sources &amp; repairs</a><h1>What is redeemed</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


@app.get("/api/repair/sources")
def api_repair_sources():
    """The Source desk's last search for a text (data/source_desk/<doc>.json), for the repair page."""
    doc = _validate_doc(request.args.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    p = SOURCE_DESK_DIR / ("%s.json" % doc)
    try:
        out = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out = {"doc": doc, "missing": True, "candidates": []}
    if isinstance(out, dict):   # ETEXT_WITNESS_2026_10_11
        out.update(_witness_info(doc))
        out["benchmark"] = _bench(doc)   # BENCHMARK_2026_10_11
    return jsonify(out)


_REPAIR_PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Repair path &mdash; __CODE__</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
main{max-width:960px;margin:0 auto;padding:22px 16px 60px}
.ttl{font-family:'EB Garamond',Georgia,serif;font-size:22px;word-break:break-word}
.code{color:var(--muted);font-size:12px;margin:2px 0 12px;word-break:break-all}
.facts{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.facts span{background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:3px 8px;font-size:12px}
ol.steps{margin:0 0 14px 20px;color:var(--muted);font-size:12.5px;line-height:1.65}
ol.steps b{color:var(--cream);font-weight:600}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:6px 10px;font-family:'Inter',sans-serif;font-size:12px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.cardnote{margin-top:8px;font-size:12px;line-height:1.45;color:#d9b36a;border-left:2px solid #6b5420;padding:2px 0 2px 8px}
__REPAIR_CSS__
.repairbar{margin-top:14px}
.rpout{font-size:13px;margin-top:8px}
.rpjudge{font-size:12.5px;margin-top:10px;padding:8px 10px}
pre.rplog{margin-top:12px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:11px;line-height:1.45;white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto;color:var(--muted)}
pre.rplog:empty{display:none}
.srcdesk{margin-top:26px;border-top:1px solid var(--border);padding-top:16px}
.srcdesk h2{font-size:14px;color:var(--gold);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
.srcintro,.srcnone{color:var(--muted);font-size:12px;line-height:1.5;margin:6px 0}
.srcbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
.srcai{font-size:11.5px;color:var(--muted)}
.srclinks{font-size:12px;color:var(--muted);margin:8px 0}
.srclinks a,.srccard a{color:var(--gold);text-decoration:none}
.srccard{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:9px 11px;margin:8px 0;font-size:12px}
.srccard.cur{opacity:.6}
.srchead{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:13px}
.srcscore{background:var(--card2);border:1px solid var(--border);border-radius:5px;padding:0 6px;font-size:11px;color:var(--cream)}
.srctag{font-size:10.5px;color:#d98a8a}
.srcmeta{color:var(--muted);margin-top:3px;word-break:break-word}
.srcwhy{color:var(--cream);opacity:.8;margin-top:3px;font-size:11.5px}
.srcacts{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.srcview iframe{width:100%;height:560px;border:1px solid var(--border);border-radius:8px;background:#fff;margin-top:8px}
.srcviewbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;margin-top:12px}
.srcviewbar a{color:var(--gold)}
.srcurl{flex:1 1 320px;min-width:0;background:var(--card);border:1px solid var(--border);color:var(--cream);border-radius:7px;padding:6px 9px;font-size:12px}
.srcsub{font-size:11px;color:var(--gold);letter-spacing:.5px;text-transform:uppercase;margin:14px 0 4px}
.srccard.wit{border-color:#3d5a3a}
.srcoffer{margin:4px 0;font-size:12px}
.srcoffer summary{cursor:pointer;color:var(--cream)}
.benchwrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin-top:4px}
table.bench{border-collapse:collapse;width:100%;font-size:11.5px;min-width:640px}
table.bench th,table.bench td{border-bottom:1px solid var(--border);padding:5px 8px;text-align:right;white-space:nowrap}
table.bench th:first-child,table.bench td:first-child{text-align:left}
table.bench th{color:var(--muted);font-weight:600;background:var(--card)}
.benchline{font-size:12.5px;line-height:1.5;margin:7px 0;color:var(--cream)}
.lv{display:inline-block;border-radius:5px;padding:0 6px;font-size:10.5px;border:1px solid var(--border)}
.lv[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.lv[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.lv[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.srcpre{white-space:pre-wrap;word-break:break-word;background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:8px;margin-top:4px;font-family:'EB Garamond',Georgia,serif;font-size:15px;line-height:1.5}
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><h1>Repair path</h1></header>
<main>
<div class="ttl">__TITLE__</div><div class="code">__CODE__</div>
<div class="facts"><span>__TOTAL__ passages</span><span>English __EN__</span><span>Hindi __HI__</span></div>
<ol class="steps">
<li><b>Assess</b>: free. It reads the database and the page files, judges the debris (what it is, and whether it touches the text), and says what the scan needs.</li>
<li><b>Repair the scan</b>: vision OCR on its pages, with a cap on the spend. The database is not touched.</li>
<li><b>Use the repaired text</b>: a backup first; then its passages are replaced by the repaired text, under the translate lock. The site keeps its last version until you publish the new one.</li>
<li><b>Re-ingest the changed pages</b> (REINGEST_2026_10_12): when the text has translations or pictures, only the pages that differ from the repaired text change; a passage whose text is unchanged keeps its translations. The plan is free.</li>
<li><b>Translate as is</b>, when the debris is cosmetic; <b>set aside</b> and <b>find a better source</b>, when the scan cannot be repaired.</li>
</ol>
__NOTES__
<div class="rpjudge" id="rpjudge-__CODE__"></div>
__BAR__
<pre class="rplog" id="rplog-__CODE__"></pre>
<section class="srcdesk" id="src-__CODE__">
<h2>Source desk</h2>
<p class="srcintro">A better edition: archive.org (previewed here), the local wisdomlib archive, and the e-text sites (GRETIL, sanskritdocuments.org), where a Unicode text needs no OCR at all. A fetched PDF goes to sources\__CODE__\, not to the inbox: import it as a second witness once you have looked at it.</p>
<div class="srcbar"><button class="tr-rest rp" data-doc="__CODE__" onclick="repairStep(this.dataset.doc,'find',this)">Find a better source</button>
<label class="srcai"><input type="checkbox" id="srcai-__CODE__"/> let the AI judge the editions (about $0.002)</label>
<button class="tr-rest rp" data-doc="__CODE__" onclick="repairStep(this.dataset.doc,'benchmark',this)">Benchmark the readings (free)</button></div>
<div class="srcbar"><input class="srcurl" id="srcurl-__CODE__" placeholder="Paste an e-text link (a .htm or .txt file on GRETIL, sanskritdocuments.org or archive.org)"/>
<button class="tr-rest rp" data-doc="__CODE__" onclick="var u=document.getElementById('srcurl-'+this.dataset.doc).value.trim(); if(u) repairStep(this.dataset.doc,'witness',this,{url:u});">Fetch it and read it as a witness</button></div>
<div class="srclist" id="srclist-__CODE__"></div>
<div class="srcview" id="srcview-__CODE__"></div>
</section>
</main>
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
__REPAIR_JS__
repairStep('__CODE__', 'assess', null);
_rpSources('__CODE__');
</script>
</body></html>"""


# JUDGE_DESK_2026_10_11 -----------------------------------------------------------------------
# The debris judged, shown where it is needed: on the Library's cards (from the last assessment, cached
# by repair_text.py in data/source_judged/<doc>.json) and on /sources, every text whose scan stops its
# translation in one place, with what it is, what is next, and the best edition the Source desk found.
_JUDGE_LEVELS = ("cosmetic", "moderate", "material")


def _judged(folder=None) -> Dict[str, dict]:
    """doc -> the last assessment repair_text.py cached (data/source_judged/<doc>.json, beside the
    database). Small files, read on each Library request; a missing folder is none."""
    d = pathlib.Path(folder if folder is not None else (ROOT / "data")) / "source_judged"
    out: Dict[str, dict] = {}
    try:
        for p in d.glob("*.json"):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get("doc"):
                out[str(r["doc"])] = r
    except OSError:
        return {}
    return out


def _judged_note(jd, kinds=(), st=None) -> str:
    """One line under a card: the debris judged, when the card says the scan stopped a run, the text has
    a state, or the debris is not cosmetic."""
    import html as _html
    if not jd or jd.get("level") not in _JUDGE_LEVELS or not jd.get("debris_pct"):
        return ""
    if not (set(kinds) & {"held", "quality", "nothing", "repaired"} or st or jd.get("level") != "cosmetic"):
        return ""
    bits = ["misread letters in %.0f%% of verses" % float(jd.get("misread_pct") or 0)]
    if jd.get("agree_pages"):
        bits.append("vision agreement %.2f" % float(jd.get("agree_median") or 0))
    if jd.get("furniture_pct"):
        bits.append("page furniture %.0f%%" % float(jd.get("furniture_pct") or 0))
    return ('<div class="cardnote judged" data-level="%s" title="%s">Debris judged %s (%s): %s.</div>'
            % (jd["level"], _html.escape(str(jd.get("judged") or "")), jd["level"].upper(),
               _html.escape(str(jd.get("at") or "?")[:10]), _html.escape("; ".join(bits))))


_SOURCES_CSS = r"""
.srcpage{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
.srcsum{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 16px}
.srcsum span{background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:4px 9px;font-size:12px}
.srcsum span[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.srcsum span[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.srcsum span[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.srcwrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px}
table.srct{width:100%;border-collapse:collapse;font-size:12px;min-width:860px}
table.srct th{text-align:left;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border);background:var(--card)}
table.srct td{padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top;line-height:1.45}
table.srct td a{color:var(--gold);text-decoration:none}
.lv{display:inline-block;border-radius:5px;padding:1px 7px;font-size:11px;border:1px solid var(--border)}
.lv[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.lv[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.lv[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.muted{color:var(--muted)}"""
_JUDGED_CSS = r"""
.cardnote.judged[data-level=material]{color:#e8a3a3;border-left-color:#7a3a3a}
.cardnote.judged[data-level=moderate]{color:#e6c27a;border-left-color:#6b5420}
.cardnote.judged[data-level=cosmetic]{color:#9fd8b5;border-left-color:#2f6b4a}"""


@app.get("/sources")
def sources_page():
    """Every text whose scan stops its translation, in one place: the debris judged (cached by
    repair_text.py), its state, what is next, and the best edition the Source desk found. Reads small
    files only (never the database); "Judge the texts again" runs repair_text.py --judge-all."""
    import html as _html
    db_path = request.args.get("db", "data/context.db")
    folder = pathlib.Path(db_path).parent
    jd = _judged(folder)
    reg = _source_verdicts(folder)
    rows = []
    for code in sorted(set(jd) | set(reg)):
        j, r = jd.get(code) or {}, reg.get(code) or {}
        keep = (r or j.get("held") or j.get("guard") or j.get("quality_stuck")
                or (j.get("level") in ("moderate", "material") and j.get("debris_pct")))
        if keep:
            rows.append((code, j, r))
    order = {"material": 0, "moderate": 1, "cosmetic": 2}
    rows.sort(key=lambda x: (0 if x[1].get("held") else 1, order.get(x[1].get("level"), 3), x[0]))
    counts = {}
    for _c, j, _r in rows:
        lv = j.get("level") if j.get("debris_pct") else None
        counts[lv] = counts.get(lv, 0) + 1
    last = max([str(j.get("at") or "") for j in jd.values()] or [""])
    e = _html.escape
    trs = ""
    for code, j, r in rows:
        c = e(code, quote=True)
        st = r.get("status") or j.get("state") or ""
        lv = j.get("level") if j.get("debris_pct") else ""
        judged = ""
        if lv:
            judged = ('<span class="lv" data-level="%s">%s</span><br><span class="muted">misread %.0f%% of verses%s</span>'
                      % (lv, lv, float(j.get("misread_pct") or 0),
                         ("; vision %.2f" % float(j.get("agree_median"))) if j.get("agree_pages") else ""))
        elif j:
            judged = '<span class="muted">no debris</span>'
        best = ""
        try:
            sd = json.loads((SOURCE_DESK_DIR / ("%s.json" % code)).read_text(encoding="utf-8"))
            b = next((x for x in sd.get("candidates") or [] if not x.get("current_scan")), None)
            if b:
                best = ('<a href="%s" target="_blank" rel="noopener">%s</a><br><span class="muted">score %.0f; %s</span>'
                        % (e(b.get("details_url") or "#"), e((b.get("title") or b.get("identifier") or "")[:80]),
                           float(b.get("score") or 0), e("; ".join((b.get("why") or [])[:2]))))
            else:
                best = '<span class="muted">searched: nothing better on archive.org</span>'
        except (OSError, ValueError):
            best = '<span class="muted">not searched</span>'
        nxt = str(j.get("next") or "")
        nxt_label = ""
        for key, label in (("--use-repaired", "use the repaired text"), ("--as-is", "translate as is"),
                           ("--accept", "accept as complete"), ("--set-aside", "set aside"), ("--restore", "restore"),
                           ("--release", "publish"), ("--find-source", "find a better source"), ("--repair", "repair the scan"),
                           ("Finish EN", "translate it")):
            if key in nxt:
                nxt_label = label
                break
        trs += ('<tr><td><a href="/repair/%s">%s</a><br><span class="muted">EN %s/%s &middot; HI %s</span></td>'
                '<td>%s</td><td>%s</td><td>%s%s</td><td>%s</td>'
                '<td><div class="repairbar" id="rp-%s"><button class="tr-rest rp" data-doc="%s" '
                'onclick="repairStep(this.dataset.doc,&#39;find&#39;,this)">Find a better source</button>'
                '<div class="rpout"></div></div></td></tr>'
                % (c, e(code), j.get("english", "?"), j.get("passages", "?"), j.get("hindi", "?"),
                   e(st.replace("_", " ")) or ('<span class="muted">held by the guard</span>' if j.get("held") else ""),
                   judged, ("<b>%s</b><br>" % e(nxt_label)) if nxt_label else "", e(str(j.get("verdict") or "")[:220]),
                   best, c, c))
    summary = "".join('<span data-level="%s">%d %s</span>' % (k or "none", v, k or "without debris")
                      for k, v in sorted(counts.items(), key=lambda x: order.get(x[0], 3)))
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Every text whose scan stops its translation: what '
            'its debris is and whether it touches the text, its state, what is next, and the best edition the Source desk '
            'found. Judged last: %s. Open a text for its repair path, the debris in full and the Source desk.</p>'
            '<div class="srcsum">%s</div>'
            '<div class="repairbar" id="rp-corpus"><button class="tr-rest rp" data-doc="corpus" onclick="repairStep('
            'this.dataset.doc,&#39;judge_all&#39;,this)">Judge the texts again (free, about a minute)</button>'
            '<div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>State</th>'
            '<th>Debris, judged</th><th>Next</th><th>Best edition found</th><th></th></tr></thead><tbody>%s</tbody>'
            '</table></div>%s</div>'
            % (e(last[:16].replace("T", " ")) or "never: press Judge the texts again", summary, trs,
               "" if rows else '<p class="srcnone">Nothing judged yet. Press Judge the texts again.</p>'))
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sources &amp; repairs</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.srcnone{color:var(--muted);font-size:12px;margin:10px 0}
""" + _REPAIR_CSS + _SOURCES_CSS + _JUDGED_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/benchmarks">Benchmarks</a><a href="/path">The path</a><h1>Sources &amp; repairs</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


@app.get("/repair/<doc>")
def repair_page(doc):
    """One text's repair path: what it holds, the steps, the debris judged, each run's output, and the
    Source desk. Opens with an assessment (free). Reads the database read-only."""
    import html as _html
    doc = _validate_doc(doc)
    if not doc:
        return "invalid doc", 400
    db_path = request.args.get("db", "data/context.db")
    title, total, en, hi = doc, 0, 0, 0
    try:
        con = sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            dcols = {r[1] for r in con.execute("PRAGMA table_info(docs)")}
            row = con.execute("SELECT id%s FROM docs WHERE code=?" % (", title" if "title" in dcols else ""),
                              (doc,)).fetchone()
            if row:
                if len(row) > 1 and row[1]:
                    title = row[1]
                total, en = con.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(translation,''))<>'' THEN 1 ELSE 0 END) "
                    "FROM passages WHERE doc_id=?", (row[0],)).fetchone()
                try:
                    hi = con.execute(
                        "SELECT COUNT(*) FROM translations_l10n l JOIN passages p ON p.id=l.passage_id "
                        "WHERE p.doc_id=? AND l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>''",
                        (row[0],)).fetchone()[0]
                except sqlite3.Error:
                    hi = 0
        finally:
            con.close()
    except Exception:
        pass
    rec = _source_verdicts(pathlib.Path(db_path).parent).get(doc)
    try:
        shown = _library_notes().get(doc, [])
    except Exception:
        shown = []
    st = (rec or {}).get("status")
    jd = _judged(pathlib.Path(db_path).parent).get(doc)   # JUDGE_DESK_2026_10_11
    if st == "set_aside":
        notes = _repair_html(doc, "", shown, rec, jd)
        bar = ""
    else:
        notes = _repair_html(doc, "", shown, rec, jd)
        bar = "" if 'class="repairbar"' in notes else _repair_bar(doc, "standard")
    page = (_REPAIR_PAGE.replace("__REPAIR_CSS__", _REPAIR_CSS + _JUDGED_CSS)
            .replace("__NOTES__", notes).replace("__BAR__", bar)
            .replace("__TITLE__", _html.escape(str(title))).replace("__TOTAL__", "{:,}".format(int(total or 0)))
            .replace("__EN__", "{:,}".format(int(en or 0))).replace("__HI__", "{:,}".format(int(hi or 0)))
            .replace("__CODE__", _html.escape(doc)))
    return page.replace("__REPAIR_JS__", _REPAIR_JS)


@app.post("/api/classify")
def api_classify():
    """Run the language/util classification stage for one doc on demand."""
    data = request.get_json(force=True) or {}
    doc  = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db = data.get("db") or "data/context.db"
    argv = [script("classify_doc.py"), "--doc", doc, "--db", db]
    if data.get("apply", True):
        argv.append("--apply")
    return jsonify({"job": launch("classify", doc, py(*argv))})

@app.post("/api/embeddings")
def api_embeddings():
    """Rebuild the semantic index from the UI. (PHASE_G_2026_09_06)

    This did not exist: the corpus could be QUERIED through /api/ask but its
    index could only be refreshed from a terminal, so the 'sanskritic brain'
    silently went stale after every ingest.
    """
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    doc  = data.get("doc")
    argv = [script("build_embeddings.py"), "--db", db]
    if doc:
        doc = _validate_doc(doc)
        if not doc:
            return jsonify({"error": "invalid doc"}), 400
        argv += ["--doc", doc]
    if data.get("refresh"):
        argv.append("--refresh")
    return jsonify({"job": launch("embeddings", doc or "(corpus)", py(*argv))})


@app.post("/api/entities")
def api_entities():
    """Extract named entities into the cross-linkage tables, from the UI."""
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    doc  = data.get("doc")
    argv = [script("extract_entities.py"), "--db", db]
    if doc:
        doc = _validate_doc(doc)
        if not doc:
            return jsonify({"error": "invalid doc"}), 400
        argv += ["--doc", doc]
    if data.get("retry_empty"):
        argv.append("--retry-empty")
    return jsonify({"job": launch("entities", doc or "(corpus)", py(*argv))})


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
    # TRANSLATION_FILTERS2_2026_09_27: optional page window, so a retry of the
    # verses a run already went past does not also start the untranslated rest.
    _win = []
    for _k, _flag in (("since_page", "--since-page"), ("until_page", "--until-page")):
        try:
            _v = int(data.get(_k) or 0)
        except (TypeError, ValueError):
            _v = 0
        if _v > 0:
            _win += [_flag, str(_v)]

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
             "--min-quality", min_quality) + _win
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
    return jsonify({"job": launch("export", doc, cmd, mode=mode), "mode": mode})


# ─────────────────────────────────────────────────────────────────────────
# BOOKSMITH_WIRING_2026_09_12
# Library selection -> Booksmith project -> PDF.
#
# Booksmith lives in its own tree with its own .venv (Python 3.13, native
# bits), so it cannot be imported into this process. Every step runs as a
# subprocess inside scripts/booksmith_build.py, launched through the same
# job runner as every other long task here, so it inherits the duplicate
# guard, the semaphore, /api/job/<id> and the history.
#
# 'booksmith' is not in the translate family, so launch() gives it the
# general semaphore - PDF builds do not write to context.db and must not
# serialise behind translation.
# ─────────────────────────────────────────────────────────────────────────
BOOKSMITH_ROOT = pathlib.Path(os.getenv(
    "BOOKSMITH_ROOT",
    r"D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith"))
BOOKSMITH_UI = os.getenv("BOOKSMITH_UI", "http://127.0.0.1:8765")
BOOKSMITH_MODES = ("tri", "en", "hi")
# LIBRARY_MODES_2026_09_13 - display order on a Library card, and what each
# edition is called there. tri comes first because every project created
# before 2026-09-13 is trilingual, so a text that has only ever had one
# build looks exactly as it did.
BOOKSMITH_MODES_ORDER = ("tri", "hi", "en")
BOOKSMITH_MODE_LABEL = {"tri": "Trilingual", "hi": "Hindi", "en": "English"}


# LIBRARY_MODES_2026_09_13
def _bs_mode_slug(doc: str, mode: str = "tri") -> str:
    """Must agree with slug_for(doc, mode) in booksmith_build.py, which since
    BOOKSMITH_MODES_2026_09_13 gives every language composition its own
    project - one project = one witness. tri keeps the bare slug so the
    projects created by hand on 2026-09-08 continue to resolve; en and hi are
    suffixed. The steps below are in the same order as there, and truncation
    happens before the suffix, so the two agree on over-long doc codes too.
    --verify checks that agreement against the real function."""
    s = (doc or "").strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    suffix = "" if mode == "tri" else ("-" + mode)
    return s[: 64 - len(suffix)] + suffix


def _bs_slug(doc: str) -> str:
    """The trilingual project id - the name every existing caller uses."""
    return _bs_mode_slug(doc, "tri")


# LIBRARY_MODES_2026_09_13
def _bs_pdf_path(doc: str, mode=None):
    """The PDF for a doc, preferring the full audit build over the sampled
    layout proof. With mode given, looks only in that edition's project;
    without, scans tri, hi, en in that order, so a text that has only ever
    had a trilingual build answers exactly as it did before today.
    Returns (path, kind) or (None, None) - arity deliberately unchanged."""
    modes = (mode,) if mode else BOOKSMITH_MODES_ORDER
    for m in modes:
        project = BOOKSMITH_ROOT / "projects" / _bs_mode_slug(doc, m)
        for name, kind in (("book.pdf", "book"), ("layout-proof.pdf", "proof")):
            p = project / "build" / name
            if p.exists():
                return p, kind
    return None, None


def _bs_sidecar(doc: str, mode: str = "tri"):
    """The last build's own account of itself, or None. Mode-aware since
    LIBRARY_MODES_2026_09_13; the bare name is the trilingual one.

    SIDECAR_TRUTH_2026_09_13 - the bare name was mode-blind until today, so a
    single-language run could land under it and still sits there:
    exports/booksmith/2015_405693_Shatpath-Brahmanam.json holds the Hindi
    build that crashed at 15:04:55, while the trilingual edition built
    cleanly at 17:37. Without this guard the TRILINGUAL card reports that
    failure, and quotes an encoding error that had nothing to do with it.

    Every sidecar records its own mode. Believe the file over its filename.
    A sidecar with no "mode" key predates the field and is accepted, because
    no edition other than trilingual existed when it was written."""
    name = ("%s.json" % doc) if mode == "tri" else ("%s__%s.json" % (doc, mode))
    p = ROOT / "exports" / "booksmith" / name
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    recorded = data.get("mode")
    if recorded is not None and recorded != mode:
        return None          # someone else's build, under this one's name
    return data


def _bs_variants(doc: str) -> list:
    """Every edition of this text that exists on disk. A project counts once
    it has a book.yaml; a download is offered once it also has a PDF. This is
    what lets one Library card carry a trilingual and a Hindi edition side by
    side instead of the second one being invisible."""
    out = []
    for m in BOOKSMITH_MODES_ORDER:
        slug = _bs_mode_slug(doc, m)
        project = BOOKSMITH_ROOT / "projects" / slug
        if not (project / "book.yaml").exists():
            continue
        v = {"mode": m, "slug": slug, "label": BOOKSMITH_MODE_LABEL[m],
             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}
        # TRANSLATION_FILTERS2_2026_09_27: say what the PDF is. booksmith_build
        # makes every project it creates an AUDIT proof ("not a textual
        # release"); only policy.output_mode 'reading' passes the reading gate.
        try:
            _om = re.search(r"^\s*output_mode:\s*([a-z_]+)",
                            (project / "book.yaml").read_text(encoding="utf-8", errors="replace"),
                            re.M)
            v["output_mode"] = _om.group(1) if _om else "reading"
        except OSError:
            v["output_mode"] = None
        pdf, kind = _bs_pdf_path(doc, m)
        if pdf:
            st = pdf.stat()
            v["pdf"] = {"kind": kind, "bytes": st.st_size,
                        "mtime": time.strftime("%Y-%m-%d %H:%M",
                                               time.localtime(st.st_mtime))}
        side = _bs_sidecar(doc, m)
        if side is not None:
            v["last"] = side
        out.append(v)
    return out


# LIBRARY_MODES_2026_09_13
def _bs_state_one(doc: str) -> dict:
    """One Library card's Booksmith state. variants[] is the new truth - one
    entry per edition that exists on disk. The flat project/ui/pdf/last keys
    are kept, pointing at the trilingual edition, so nothing that reads this
    endpoint has to change at the same moment."""
    slug = _bs_slug(doc)
    project = BOOKSMITH_ROOT / "projects" / slug
    state = {"doc": doc, "slug": slug, "variants": _bs_variants(doc),
             "project": project.exists() and (project / "book.yaml").exists(),
             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}
    side = _bs_sidecar(doc, "tri")
    if side is not None:
        state["last"] = side
    pdf, kind = _bs_pdf_path(doc)
    if pdf:
        st = pdf.stat()
        state["pdf"] = {"kind": kind, "bytes": st.st_size,
                        "mtime": time.strftime("%Y-%m-%d %H:%M",
                                               time.localtime(st.st_mtime))}
    for j in list(JOBS.values()):
        if j.kind == "booksmith" and j.doc == doc and j.ok is None:
            state["job"] = j.id
            break
    return state


@app.get("/api/booksmith/state")
def api_booksmith_state():
    raw = (request.args.get("docs") or "").strip()
    docs = [d for d in (x.strip() for x in raw.split(",")) if d]
    if not docs:
        return jsonify({"error": "docs is required"}), 400
    if len(docs) > 200:
        return jsonify({"error": "too many docs"}), 400
    return jsonify({"root": str(BOOKSMITH_ROOT),
                    "installed": (BOOKSMITH_ROOT / ".venv" / "Scripts" / "booksmith.exe").exists(),
                    "states": [_bs_state_one(d) for d in docs]})


@app.post("/api/booksmith/build")
def api_booksmith_build():
    data = request.get_json(force=True) or {}
    docs = data.get("docs") or []
    if not isinstance(docs, list) or not docs:
        return jsonify({"error": "docs must be a non-empty list"}), 400
    if len(docs) > 40:
        return jsonify({"error": "select 40 texts or fewer per run"}), 400
    mode = (data.get("mode") or "tri").strip()
    if mode not in BOOKSMITH_MODES:
        return jsonify({"error": f"mode must be one of {BOOKSMITH_MODES}"}), 400
    product = (data.get("product") or "audit").strip()
    if product not in ("audit", "proof"):
        return jsonify({"error": "product must be audit or proof"}), 400
    exe = BOOKSMITH_ROOT / ".venv" / "Scripts" / "booksmith.exe"
    if not exe.exists():
        return jsonify({"error": f"Booksmith is not installed at {BOOKSMITH_ROOT}. "
                                 f"Run Launch_Booksmith.bat there once."}), 409

    db = data.get("db") or "data/context.db"
    started, rejected = [], []
    for raw in docs:
        doc = _validate_doc(raw)
        if not doc:
            rejected.append({"doc": str(raw)[:80], "why": "invalid doc code"})
            continue
        cmd = py(script("booksmith_build.py"), "--db", db, "--doc", doc,
                 "--mode", mode, "--product", product,
                 "--booksmith-root", str(BOOKSMITH_ROOT))
        started.append({"doc": doc, "job": launch("booksmith", doc, cmd)})
    return jsonify({"started": started, "rejected": rejected,
                    "mode": mode, "product": product})


@app.get("/api/booksmith/pdf/<doc>")
def api_booksmith_pdf(doc):
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    # LIBRARY_MODES_2026_09_13 - ?mode=tri|en|hi picks the edition. Without
    # it the old behaviour stands: the first edition that has a PDF, tri
    # first. An unknown mode is a 400 rather than a quiet fall back to
    # trilingual - handing someone the wrong language is worse than an error.
    mode = (request.args.get("mode") or "").strip()
    if mode and mode not in BOOKSMITH_MODES:
        return jsonify({"error": f"mode must be one of {BOOKSMITH_MODES}"}), 400
    pdf, kind = _bs_pdf_path(doc, mode or None)
    if not pdf:
        return jsonify({"error": "no PDF built yet for this text"
                                 + (f" in mode {mode}" if mode else "")}), 404
    # Read and return rather than send_file, so no new Flask import is needed
    # and the download is named after the text instead of book.pdf every time.
    # LIBRARY_MODES_2026_09_13 - the language belongs in the filename, or a
    # folder of downloads becomes three files that cannot be told apart.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_",
                  f"{doc}_{mode or 'tri'}_{kind}") + ".pdf"
    resp = Response(pdf.read_bytes(), mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp


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
            ["verse_ref", "chapter", "text_type", "chandas", "iast", "quality_score",
             "translation_score", "translation_qa", "ocr_engine", "ocr_variants"]
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

        # Progress counts exclude non-verse rows (English front matter, noise) so the
        # header "194/664 translated" reflects real Sanskrit verses. The passage LIST
        # below still SHOWS those rows, labelled "Source is English" — mark, don't hide.
        stats_clause, stats_params = type_clause, list(type_params)
        if not text_type_filter and "text_type" in cols:
            stats_clause = " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
            stats_params = []
        total = con.execute(
            f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?{stats_clause}",
            (doc, *stats_params)
        ).fetchone()[0]
        translated = con.execute(
            f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id {join_l10n} "
            f"WHERE d.code=? AND TRIM(COALESCE({trans_col},''))<>''{stats_clause}",
            (*l10n_param, doc, *stats_params)
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
        sch, sch_n = (_scholar_rows(con, doc, type_clause, type_params, limit, offset) if lang == "en"
                      else ({}, 0))   # LIBRARY_SCHOLAR_2026_10_16: the scholarly English of these verses
        con.close()

        def row_to_dict(r):
            d = {"page_no": r[0], "idx": r[1], "text": r[2] or "", "translation": r[3] or ""}
            # LATENT BUG FIXED 2026-08-30: this used enumerate() over the FULL
            # column list while the SELECT above only emits columns that exist.
            # On any older DB missing one of them, every field after the gap was
            # read from the wrong offset - verse_ref showing a chandas, and so
            # on. Iterate over the PRESENT columns, in the same order the SELECT
            # built them, so the two can never drift apart.
            present = [c for c in ["verse_ref","chapter","text_type","chandas","iast",
                                   "quality_score","translation_score","translation_qa",
                                   "ocr_engine","ocr_variants"] if c in cols]
            for i, c in enumerate(present):
                if 4 + i < len(r):
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
            "scholar_count": sch_n,   # LIBRARY_SCHOLAR_2026_10_16
            "passages": [_with_scholar(row_to_dict(r), sch) for r in rows]
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
    import html as _html   # _html is imported locally in library(), not module-wide
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


# DESK_HEAL_2026_10_10 -------------------------------------------------------------------------
_HELD_RE = re.compile(r"TRANSLATE_DEBRIS_GUARD|allow-debris|ocr_consensus\.py --doc")
_DONE_RE = re.compile(r"Done\. (\d+)/(\d+) translated \| (\d+) quality-skipped")
_PIPE_TR_RE = re.compile(r"Translate\s+: (OK|FAIL)")    # pipeline_queue.py's summary line


def _library_notes() -> Dict[str, list]:
    """What the last translation run of each text and language said when it could not do the work:
    held by the OCR-debris guard (exit 3: Tesseract debris in the source while its page PDFs are in
    the inbox), nothing left to translate, or nearly all of what is left below the OCR quality bar.
    The Library shows it under the text's buttons, so that a press that cannot help says so first.
    From data/jobs.jsonl, newest first; never the database."""
    notes: Dict[str, list] = {}
    seen = set()
    try:
        recs = _load_job_history(limit=3000)
    except Exception:
        return notes
    held: Dict[tuple, dict] = {}
    for r in recs:
        kind = r.get("kind") or ""
        if kind == "repair_use":   # REPAIR_HEAL_2026_10_11: a repaired text that went in replaces the notes before it
            doc = r.get("doc") or ""
            langs = tuple(x for x in ("en", "hi") if (doc, x) not in seen)
            if r.get("ok") and langs:
                seen.update((doc, x) for x in langs)
                try:
                    at = time.strftime("%d %b %H:%M", time.localtime(float(r.get("end") or r.get("start") or 0)))
                except (TypeError, ValueError):
                    at = "?"
                notes.setdefault(doc, []).append({
                    "lang": "both" if len(langs) == 2 else langs[0], "kind": "repaired",
                    "detail": str(r.get("verdict") or r.get("out_tail") or "")[-600:],
                    "text": ("Repaired (%s): the vision-OCR text went in. Translate it now: English, then Hindi; "
                             "passages whose text did not change come from the cache at no cost." % at)})
            continue
        if kind not in ("translate", "translate_hi", "translate_both", "pipeline"):
            continue
        tail = "%s\n%s" % (r.get("out_tail") or "", r.get("err_preview") or "")
        if kind == "pipeline" and not (_PIPE_TR_RE.search(tail) or _HELD_RE.search(tail)):
            continue                        # a pipeline run that did not translate says nothing here
        doc = r.get("doc") or ""
        langs = ("en", "hi") if kind == "translate_both" else (("hi",) if kind == "translate_hi" else ("en",))
        langs = tuple(x for x in langs if (doc, x) not in seen)
        if not langs:
            continue
        seen.update((doc, x) for x in langs)
        lines = [ln.strip() for ln in tail.strip().splitlines() if ln.strip()]
        detail = " ".join(lines[-3:])[:600]
        try:
            at = time.strftime("%d %b %H:%M", time.localtime(float(r.get("end") or r.get("start") or 0)))
        except (TypeError, ValueError):
            at = "?"
        if r.get("ok") is False and (r.get("rc") == 3 or _HELD_RE.search(tail)):
            for x in langs:
                held[(doc, x)] = {"at": at, "detail": detail}
            continue
        for x in langs:
            name = "Hindi" if x == "hi" else "English"
            text = None
            if kind in ("translate_both", "pipeline"):
                pass                        # several runs in one tail: only a hold is read from it
            elif r.get("ok") and "[NOTHING]" in tail:
                text = ("%s: nothing left that can be translated (%s). What is left is illegible OCR: re-OCR it "
                        "rather than translate." % (name, at))
            elif r.get("ok"):
                m = _DONE_RE.search(tail)
                if m:
                    done, total, skipped = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    if total and skipped >= 0.8 * total:
                        text = ("%s: the last run (%s) translated %d of %d; %d are below the OCR quality bar and "
                                "were not sent. Re-OCR those pages first." % (name, at, done, total, skipped))
            if text:
                notes.setdefault(doc, []).append({"lang": x, "text": text, "detail": detail,   # REPAIR_PATH_2026_10_10: kind
                                                  "kind": "quality" if "quality bar" in text else "nothing"})
    for doc in sorted({d for d, _ in held}):
        langs = [x for x in ("en", "hi") if (doc, x) in held]
        h = held[(doc, langs[0])]
        what = "English and Hindi" if len(langs) == 2 else ("Hindi" if langs[0] == "hi" else "English")
        text = ("%s held (%s): the OCR of this text carries Tesseract debris (Latin letters inside the "
                "Devanagari) and its page PDFs are in the inbox, so the source is repaired first. Plan the "
                "repair, no spend: python scripts\\ocr_consensus.py --doc %s --threshold 101 "
                "--include-unassessed. To translate anyway, start the dashboard with SA_ALLOW_DEBRIS=1."
                % (what, h["at"], doc))
        notes.setdefault(doc, []).insert(0, {"lang": "both" if len(langs) == 2 else langs[0], "text": text,
                                             "detail": h["detail"], "kind": "held"})   # REPAIR_PATH_2026_10_10
    return notes


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
        # Exclude non-verse rows (English front matter, noise) from the coverage
        # denominator, so "EN 183/664" counts real Sanskrit verses only. The QA panel
        # already excludes them; this makes the Library agree (2026-08-28). Filter lives
        # in the LEFT JOIN's ON clause so docs with zero verses are still returned.
        _pcols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        _pfilter = (" AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
                    if "text_type" in _pcols else "")
        rows = con.execute(
            f"SELECT d.code, {title_expr}, COALESCE(d.category,'other'), "
            "COUNT(p.id), "
            "SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) "
            f"FROM docs d LEFT JOIN passages p ON p.doc_id=d.id{_pfilter} "
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
        sc = _scholar_cover(con)   # LIBRARY_SCHOLAR_2026_10_16: the scholarly English, per text
        con.close()
    except Exception as e:
        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500
    notes = _library_notes()   # DESK_HEAL_2026_10_10
    rdm = _redeem()   # REDEEM_2026_10_14: what of each text's English is kept
    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside
    judged = _judged(pathlib.Path(db_path).parent)   # JUDGE_DESK_2026_10_11: the last assessments

    cats = OrderedDict()
    total_docs = total_en = total_hi = 0
    for code, title, cat, total, en in rows:
        en = int(en or 0)
        if en == 0 and not (sc.get(code) or {}).get("verses"):   # LIBRARY_SCHOLAR_2026_10_16: or in scholarly English
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
            _hold = _hold_reason(code, aside.get(code), rdm) if (pct < 100 or h < en) else ''   # HOLD_2026_10_14
            if pct < 100 and not _hold:
                acts += (f'<button class="tr-rest" title="Translate the remaining English verses"'
                         f' onclick="translateRest(\'{code}\',\'en\',this)">&#9889; Finish EN</button>')
            if h < en and not _hold:
                acts += (f'<button class="tr-rest hi" title="Translate Hindi for verses that have English but no Hindi"'
                         f' onclick="translateRest(\'{code}\',\'hi\',this)">&#2361;&#2367; Add Hindi</button>')
            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
            acts_html += _hold_note(code, _hold, aside.get(code))   # HOLD_2026_10_14
            # DESK_HEAL_2026_10_10: what the last run said, when it could not do the work
            _shown = []
            for _n in notes.get(code, []):
                if ((_n["lang"] == "en" and pct >= 100) or (_n["lang"] == "hi" and h >= en)
                        or (_n["lang"] == "both" and pct >= 100 and h >= en)):
                    continue
                _shown.append(_n)
            # REPAIR_PATH_2026_10_10: the notes, and the repair path under them; a text set aside says why
            acts_html = _repair_html(code, acts_html, _shown, aside.get(code), judged.get(code))
            # Filled in by refreshBooksmith() once /api/booksmith/state answers.
            acts_html += f'<div class="bsacts" id="bs-{_html.escape(code)}"></div>'
            body += (
                f'<div class="card-wrap" data-doc="{_html.escape(code)}">'
                # BOOKSMITH_WIRING_2026_09_12 - the checkbox sits OUTSIDE the
                # <a>, or clicking it would navigate to the reader instead of
                # selecting the text.
                f'<label class="pick" title="Select this text for a PDF">'
                f'<input type="checkbox" class="pickbox" value="{_html.escape(code)}"/>'
                f'</label>'
                f'<a class="card" href="/reader/{code}">'
                f'<div class="ttl">{_html.escape(title)}</div>'
                f'<div class="code">{_html.escape(code)}</div>'
                f'<div class="bar"><i style="width:{pct}%"></i></div>'
                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{_scholar_badge(code, sc)}{hi_badge}{qa_badge}'
                f'<span class="pct">{pct}%</span></div></a>'
                f'{_scholar_line(code, sc)}{_redeem_note(code, rdm)}{acts_html}</div>'   # REDEEM_2026_10_14, LIBRARY_SCHOLAR_2026_10_16
            )
        body += '</div>'
    body += _repair_waiting(rows, cats, notes, aside, judged)   # REPAIR_PATH_2026_10_10: no English yet, held by its scan

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
.cardnote{{margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:#d9b36a;border-left:2px solid #6b5420;padding:2px 0 2px 7px;cursor:help}}
{_REPAIR_CSS}
{_JUDGED_CSS}
{_REDEEM_CSS}
{_SCHOLAR_CSS}
/* BOOKSMITH_WIRING_2026_09_12 */
.card-wrap{{position:relative}}
.pick{{position:absolute;top:8px;right:8px;z-index:3;cursor:pointer;padding:4px}}
.pickbox{{width:15px;height:15px;accent-color:var(--gold);cursor:pointer}}
.card-wrap.sel .card{{border-color:var(--gold);background:var(--card2)}}
.bsacts{{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}}
.bsacts a,.bsacts span{{font-family:'Inter',sans-serif;font-size:10px;font-weight:600;
  border-radius:7px;padding:4px 8px;text-decoration:none;border:1px solid var(--border)}}
.bsacts a.pdf{{color:var(--green);border-color:#23492f}}
.bsacts a.pdf:hover{{background:#12351f}}
.bsacts a.bsui{{color:var(--muted)}}
.bsacts a.bsui:hover{{color:var(--gold);border-color:var(--gold)}}
.bsacts span.warn{{color:#d98a8a;border-color:#3a1616}}
.bsacts span.busy{{color:var(--gold);border-color:#3a2f0f}}
#buildbar{{position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:40;
  display:none;align-items:center;gap:12px;background:var(--card2);
  border:1px solid var(--gold);border-radius:12px;padding:10px 16px;
  font-family:'Inter',sans-serif;font-size:12.5px;box-shadow:0 10px 30px #0009}}
#buildbar b{{color:var(--gold)}}
#buildbar select{{background:var(--card);color:var(--cream);border:1px solid var(--border);
  border-radius:7px;padding:5px 8px;font-family:'Inter',sans-serif;font-size:12px}}
#buildbar button{{background:var(--card);border:1px solid var(--border);color:var(--cream);
  border-radius:7px;padding:6px 12px;font-weight:600;cursor:pointer;font-size:12px}}
#buildbar button.go{{border-color:var(--gold);color:var(--gold)}}
#buildbar button:hover{{background:#000}}
#buildbar button:disabled{{opacity:.55;cursor:default}}
#buildbar .hint{{color:var(--muted);font-size:11px;max-width:300px}}
</style></head><body>
<header>
  <a class="back" href="/">&#8592; Dashboard</a>
  <h1>&#2384; Srangam Library</h1>
  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses{_scholar_sum(sc)}{(" &middot; <a href='/redeem' style='color:var(--green);text-decoration:none' title='REDEEM_2026_10_14: what of the English is kept, and what is not'>" + format((rdm.get("totals") or {}).get("keep", 0), ",") + " kept</a>") if rdm else ""}</span>
  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/path" title="PATH_2026_10_12: the way forward for every text: repair, find a source, retire, translate, judge" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#129517; The path</a>
  <a class="back" href="/redeem" title="REDEEM_2026_10_14: what of the translation already paid for is kept, and what is not" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878; What is redeemed</a>
  <a class="back" href="/scholar" title="SCHOLAR_2026_10_14: the scholarly English, verse by verse: drafted with its context and glossary, read by a critic, revised, judged" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128220; Scholarly English</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
</header>
<main>{body}</main>
<!-- BOOKSMITH_WIRING_2026_09_12 -->
<div id="buildbar">
  <span><b id="bbn">0</b> selected</span>
  <select id="bbmode" title="Which languages go into the witness Booksmith parses">
    <option value="tri">Sanskrit + IAST + English + Hindi</option>
    <option value="en">Sanskrit + IAST + English</option>
    <option value="hi">Sanskrit + IAST + Hindi</option>
  </select>
  <select id="bbproduct" title="Audit edition is the whole text and is never gated. Layout proof is eight representative units.">
    <option value="audit">Audit edition &mdash; whole text</option>
    <option value="proof">Layout proof &mdash; 8 units</option>
  </select>
  <button class="go" id="bbgo" onclick="buildSelected()">Build PDFs</button>
  <button onclick="clearSel()">Clear</button>
  <span class="hint">Every mode carries the Sanskrit source: Booksmith requires two to four reading languages, so a single-language witness is outside its model.</span>
</div>
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-family:'Inter',sans-serif;font-size:13px;display:none;z-index:50"></div>
<script>
function _toast(m){{var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){{t.style.display='none';}},4200);}}
async function translateRest(doc, lang, btn){{   // DESK_HEAL_2026_10_10: says what the run did, not only that it started
  btn.disabled=true; var orig=btn.textContent; btn.textContent='starting...';
  try{{
    var r=await fetch('/api/translate',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{doc:doc,lang:lang,limit:100000}})}});
    var d=await r.json();
    if(!d.job){{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; return; }}
    btn.textContent='queued...';
    _watchJob(d.job, doc, lang, btn, orig, 0);
  }}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}
}}
function _jobVerdict(j){{
  var out=(j.out||'')+' '+(j.err||'');
  if(j.ok===false && /allow-debris|ocr_consensus|TRANSLATE_DEBRIS_GUARD/.test(out)) return {{word:'held', text:'Held: the OCR of this text carries Tesseract debris and its page PDFs are in the inbox, so the source is repaired first (OCR consensus, no spend). Reload the Library: the note under the text has the command.'}};
  if(j.ok===false && /HOLD_2026_10_14/.test(out)) return {{word:'held', text:'Held: this text is withdrawn or set aside (data/source_verdicts.jsonl), so it is not translated further: a better source first. Nothing was spent.'}};
  if(j.ok===false && /KILLED/.test(out)) return {{word:'stopped', text:'Stopped by hand.'}};
  if(j.ok===false) return {{word:'failed', text:'It failed: the Dashboard History has the reason.'}};
  if(out.indexOf('[NOTHING]')>=0) return {{word:'nothing to do', text:'Nothing to translate: every verse has it already, or what is left is illegible OCR (re-OCR it rather than translate).'}};
  var m=out.match(/Done[.] ([0-9]+)[/]([0-9]+) translated [|] ([0-9]+) quality-skipped/);
  if(m) return {{word:'done: '+m[1]+' of '+m[2], text:m[1]+' of '+m[2]+' verses translated; '+m[3]+' below the OCR quality bar were not sent.'}};
  return {{word:'done', text:'Done.'}};
}}
async function _watchJob(id, doc, lang, btn, orig, n){{
  try{{
    var j=await (await fetch('/api/job/'+encodeURIComponent(id))).json();
    if(j.state==='done'){{
      var v=_jobVerdict(j); btn.textContent=v.word; btn.title=v.text; btn.disabled=false;
      _toast(doc+' ('+lang.toUpperCase()+'): '+v.text); return;
    }}
    btn.textContent = j.state==='queued' ? 'queued: after the running one' : 'translating...';
    if(n===45) _toast(doc+' ('+lang.toUpperCase()+') is still running: this button follows it; so does the Dashboard.');
  }}catch(e){{ if(n>400) {{ btn.textContent=orig; btn.disabled=false; return; }} }}
  setTimeout(function(){{ _watchJob(id, doc, lang, btn, orig, n+1); }}, n<45 ? 2000 : 10000);
}}
{_REPAIR_JS}

/* BOOKSMITH_WIRING_2026_09_12
   Selection, dispatch, and per-card state. The state endpoint is the single
   source of truth for what exists on disk; this script never infers that a
   PDF was produced from the fact that a job was started. */
var SEL = new Set();
function allDocs(){{
  return Array.from(document.querySelectorAll('.card-wrap[data-doc]'))
              .map(function(w){{ return w.getAttribute('data-doc'); }});
}}
function syncBar(){{
  var bar=document.getElementById('buildbar');
  document.getElementById('bbn').textContent=SEL.size;
  bar.style.display = SEL.size ? 'flex' : 'none';
}}
function clearSel(){{
  SEL.clear();
  document.querySelectorAll('.pickbox').forEach(function(b){{
    b.checked=false; b.closest('.card-wrap').classList.remove('sel');
  }});
  syncBar();
}}
document.addEventListener('change', function(e){{
  if(!e.target.classList.contains('pickbox')) return;
  var doc=e.target.value, wrap=e.target.closest('.card-wrap');
  if(e.target.checked){{ SEL.add(doc); wrap.classList.add('sel'); }}
  else {{ SEL.delete(doc); wrap.classList.remove('sel'); }}
  syncBar();
}});

function bsRender(s){{
  var el=document.getElementById('bs-'+s.doc);
  if(!el) return;
  var h='';
  if(s.job){{ h+='<span class="busy">building\u2026</span>'; }}
  // LIBRARY_MODES_2026_09_13 - one set of links per edition that exists,
  // instead of one link for whichever edition happened to build last. A
  // server from before this change sends no variants[]; render what it used
  // to rather than a blank card.
  var vs=(s.variants&&s.variants.length)?s.variants:null;
  if(!vs){{
    vs=[];
    if(s.pdf||s.project){{
      vs.push({{mode:'tri',label:'Trilingual',ui:s.ui,pdf:s.pdf,last:s.last}});
    }}
  }}
  var many=vs.length>1;
  vs.forEach(function(v){{
    if(v.pdf){{
      var kb=Math.round(v.pdf.bytes/1024);
      var what=(v.pdf.kind!=='book')?'layout proof':(v.output_mode==='audit'?'audit proof PDF':'PDF');
      h+='<a class="pdf" href="/api/booksmith/pdf/'+encodeURIComponent(s.doc)+
         '?mode='+encodeURIComponent(v.mode)+'" '+
         'title="'+v.label+' '+what+', '+kb+' KB, built '+v.pdf.mtime+'">'+
         '\u2b07 '+v.label+' '+what+'</a>';
    }}
    h+='<a class="bsui" target="_blank" rel="noopener" href="'+v.ui+'" '+
       'title="Open the '+v.label+' project in Booksmith to '+
       'review findings and build the reading edition">Booksmith \u2197'+
       (many?(' '+v.mode):'')+'</a>';
    if(v.last && v.last.blocked){{
      h+='<span class="warn" title="'+v.label+': '+
         (v.last.blockers||[]).join(' ').replace(/"/g,'')+'">'+
         (many?(v.label+' '):'')+'reading edition blocked</span>';
    }}
  }});
  el.innerHTML=h;
}}

var BS_TIMER=null;
async function refreshBooksmith(once){{
  var docs=allDocs();
  if(!docs.length) return;
  try{{
    var r=await fetch('/api/booksmith/state?docs='+encodeURIComponent(docs.join(',')));
    var d=await r.json();
    if(d.states) d.states.forEach(bsRender);
    var busy=(d.states||[]).some(function(s){{ return s.job; }});
    if(BS_TIMER) clearTimeout(BS_TIMER);
    if(busy && !once) BS_TIMER=setTimeout(refreshBooksmith,3000);
  }}catch(e){{ /* the dashboard may be restarting; the next tick retries */ }}
}}

async function buildSelected(){{
  if(!SEL.size) return;
  var go=document.getElementById('bbgo');
  var mode=document.getElementById('bbmode').value;
  var product=document.getElementById('bbproduct').value;
  go.disabled=true; var orig=go.textContent; go.textContent='starting\u2026';
  try{{
    var r=await fetch('/api/booksmith/build',{{method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{docs:Array.from(SEL),mode:mode,product:product}})}});
    var d=await r.json();
    if(d.error){{ _toast(d.error); }}
    else{{
      _toast('Queued '+d.started.length+' build(s). Export, ingest, audit, then PDF \u2014 watch the cards.');
      if(d.rejected && d.rejected.length) _toast(d.rejected.length+' rejected: '+d.rejected[0].why);
      clearSel();
      setTimeout(function(){{ refreshBooksmith(); }},800);
    }}
  }}catch(e){{ _toast('Request failed: '+e); }}
  go.textContent=orig; go.disabled=false;
}}
document.addEventListener('DOMContentLoaded',function(){{ refreshBooksmith(true); }});
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
.dev-text{{font-family:'Noto Serif Devanagari',serif;font-size:15px;line-height:2.0;color:var(--dev-col);white-space:pre-wrap}}\n.ocr-var{{border-bottom:1px dotted #c9a227;cursor:help;background:rgba(201,162,39,.10)}}\n.ocr-var:hover{{background:rgba(201,162,39,.28)}}\n.src-badge{{margin-top:6px;font-size:9px;color:#8a8a8a}}\n.src-badge.src-fallback{{color:#d08a3a}}\n.var-count{{color:#c9a227}}
/* ── English text ── */
.en-text{{font-size:15px;line-height:1.75;color:var(--en-col);font-style:italic}}
.en-text em{{font-style:normal;color:var(--cream)}}
/* Localized (e.g. Hindi) translation: Devanagari face, upright, not italic. */
.hi-text{{font-family:'Noto Serif Devanagari',serif;font-size:15px;line-height:1.9;color:var(--cream)}}
.en-pending{{color:var(--muted);font-style:italic;font-size:13px;font-family:'Inter',sans-serif}}
/* LIBRARY_SCHOLAR_2026_10_16: the scholarly English above the working English */
.col-label-sch{{color:#c3a6e8}}
.sch-text{{font-size:15px;line-height:1.75;color:var(--cream);margin-bottom:6px}}
.sch-text em{{font-style:italic;color:#e8dcc8}}
.sch-by{{font-family:'Inter',sans-serif;font-size:10px;color:var(--muted);margin-bottom:12px;padding-bottom:10px;border-bottom:1px dashed var(--border)}}
.sch-by a{{color:#c3a6e8}}
.sch-st{{border-radius:4px;padding:0 6px;font-size:9px;text-transform:none;letter-spacing:0;border:1px solid var(--border)}}
.sch-st.ok{{color:var(--green);border-color:#2f6b45}}
.sch-st.mid{{color:#d9b36a;border-color:#6b5420}}
.sch-st.lo{{color:#e09a9a;border-color:#7a2f2f}}
.sch-sent{{font-size:9px;color:var(--muted);text-transform:none;letter-spacing:0}}
.en-illegible{{color:#c06060;font-style:italic;font-size:12px;font-family:'Inter',sans-serif}}
.en-source{{color:#9a8f70;font-style:italic;font-size:12px;font-family:'Inter',sans-serif}}
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

// Coherent English SOURCE (book front-matter, title pages, editorial prefaces like the
// Ballantyne "ADVERTISEMENT"). This is NOT garbled OCR — it is legible English that
// simply needs no Sanskrit->English translation. Distinguished from illegible Sanskrit
// so it is labelled honestly instead of flagged for re-OCR (2026-08-28).
// ---- apparatus criticus -------------------------------------------------
// Vision is the source of record, but it is not always right: on this corpus
// Tesseract carried the correct reading roughly one time in nine (तरुण where
// vision wrote the non-word तरुश). merge_ocr_sources.py keeps the losing
// reading; this marks the word so a reader can see a machine made a choice.
function markVariants(text, rawVariants){{
  const safe = esc(text || '');
  if (!rawVariants) return safe;
  let vs;
  try {{ vs = JSON.parse(rawVariants); }} catch(e) {{ return safe; }}
  if (!Array.isArray(vs) || !vs.length) return safe;
  let out = safe;
  vs.slice(0, 40).forEach(function(d){{
    if (!d || !d.v || !d.t) return;
    const v = esc(d.v), t = esc(d.t);
    if (out.indexOf(v) < 0) return;
    out = out.split(v).join(
      '<span class="ocr-var" title="Tesseract read: ' + t +
      '  (similarity ' + (d.sim != null ? d.sim : '?') + ')">' + v + '</span>');
  }});
  return out;
}}

function engineBadge(p){{
  const e = p.ocr_engine || '';
  let vn = 0;
  try {{ const a = JSON.parse(p.ocr_variants || '[]'); vn = Array.isArray(a) ? a.length : 0; }} catch(_){{}}
  if (!e && !vn) return '';
  let cls = 'src-vision', label = 'vision OCR';
  if (e === 'tesseract-fallback') {{ cls = 'src-fallback'; label = 'Tesseract fallback \u2014 vision failed here'; }}
  else if (e && e.indexOf('gemini-vision') !== 0) {{ cls = 'src-other'; label = esc(e); }}
  return '<div class="src-badge ' + cls + '">' + label +
         (vn ? ' &middot; <span class="var-count">' + vn + ' engine disagreement' + (vn===1?'':'s') + '</span>' : '') +
         '</div>';
}}

// LIBRARY_SCHOLAR_2026_10_16: a verse's scholarly English (scholar_translate.py) above its working English, with its
// status and a link to its notes and checks on /scholar/<doc>. The working English below it is what the site shows.
function scholarHtml(p){{
  var s = p.scholar;
  if (!s || !s.translation) return '';
  var st = s.review === 'accept' ? 'accepted by a person' : (s.review === 'reject' ? 'rejected by a person'
           : String(s.status || '').replace('_', ' '));
  var cls = (s.review === 'accept' || (s.status === 'passed' && s.review !== 'reject')) ? 'ok'
            : ((s.status === 'source_doubt' || s.review === 'reject') ? 'lo' : 'mid');
  var eng = String(s.engine || '').split(':').pop();
  var txt = esc(s.translation).replace(/\\*([^*\\n]{{1,80}})\\*/g, '<em>$1</em>');
  return '<div class="col-label col-label-sch">&#128220; Scholarly English <span class="sch-st ' + cls + '">' + esc(st)
       + '</span>' + (s.sentence ? '<span class="sch-sent" title="one Sanskrit sentence over these verses">sentence '
       + esc(s.sentence) + '</span>' : '') + '</div><div class="sch-text">' + txt + '</div>'
       + '<div class="sch-by">' + esc(eng) + ' &middot; <a href="' + esc(s.href) + '" target="_blank">its notes and '
       + 'checks</a></div>';
}}

function looksEnglish(t){{
  if (!t) return false;
  var s = String(t);
  var lat = (s.match(/[A-Za-z]/g) || []).length;
  var dev = (s.match(/[ऀ-ॿ]/g) || []).length;
  var letters = lat + dev || 1;
  if (lat/letters < 0.85 || lat < 12) return false;   // Latin-dominant, enough text
  var lc = ' ' + s.toLowerCase().replace(/[^a-z]+/g,' ') + ' ';
  var words = [' the ',' of ',' and ',' to ',' in ',' is ',' was ',' this ',' that ',
               ' with ',' by ',' for ',' as ',' which ',' work ',' published ',' edited ',
               ' commentary ',' following ',' printed ',' society ',' college ',' preface ',
               ' aphorisms ',' oriental ',' collection '];
  var hits = 0; for (var i=0;i<words.length;i++){{ if (lc.indexOf(words[i])>=0) hits++; }}
  return hits >= 3;                                    // >=3 common English words = coherent English
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
    if (d.scholar_count) document.getElementById('progText').textContent += ' ' + String.fromCharCode(183) + ' '
        + d.scholar_count + ' in scholarly English';   // LIBRARY_SCHOLAR_2026_10_16

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
      const qual  = p.quality_score;      // SOURCE: OCR/Devanagari cleanliness
      const tqa   = p.translation_qa;     // TRANSLATION: structural QA of the rendering
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
        // Labelled "Source OCR", not bare "Quality": this measures the SANSKRIT SOURCE's
        // OCR cleanliness, NOT the translation. Conflating the two misleads the reader
        // (see /methodology). Translation QA is shown separately below (2026-08-28).
        metaHtml += '<div class="meta-item" title="Source OCR cleanliness: Devanagari density + verse punctuation. NOT a translation score — see Quality methodology.">'
                 + '<span class="meta-key">Source OCR ' + qPct + '%</span>' + qBar + '</div>';
      }}
      // Separate, explicitly-named TRANSLATION quality — shown only when a translation
      // exists, so the two axes are never confused with each other.
      if (hasTr && tqa !== null && tqa !== undefined){{
        var tPct = Math.round(tqa * 100);
        var tCol = quality_color(tqa);
        metaHtml += '<div class="meta-item" title="Structural QA of the translation (length band, residue, truncation). Structural soundness, not certified semantic fidelity — see Quality methodology.">'
                 + '<span class="meta-key">Translation QA ' + tPct + '%</span>'
                 + '<div class="quality-bar"><i style="width:'+tPct+'%;background:'+tCol+'"></i></div></div>';
      }}
      if (iast && iast.trim()){{
        metaHtml += '<div class="iast-text">' + esc(iast.substring(0,120)) + (iast.length>120?'&hellip;':'') + '</div>';
      }}
      metaHtml += '</div>';

      html += '<div class="verse-card">' +
        // Column 1: Sanskrit Devanagari
        '<div class="col-dev">' +
          '<div class="col-label col-label-dev">&#2344;&#2350;&#2307; Sanskrit</div>' +
          '<div class="dev-text">' + markVariants(p.text, p.ocr_variants) + '</div>' +
          engineBadge(p) +
        '</div>' +
        // Column 2: translation (English or localized, e.g. Hindi)
        '<div class="col-en">' +
          scholarHtml(p) +
          '<div class="col-label col-label-en">' + (LANG_LABELS[activeLang] || activeLang) + (p.scholar ? ' &middot; the working English' : '') + '</div>' +
          (hasTr
            ? '<div class="' + (activeLang === 'en' ? 'en-text' : 'hi-text') + '">' + esc(p.translation) + '</div>'
            : (looksEnglish(p.text)
                ? '<div class="en-source">&#128196; Source is English &mdash; no translation needed</div>'
                : looksIllegible(p.text)
                ? '<div class="en-illegible">&#9888; Source illegible &mdash; needs re-OCR, not translation</div>'
                : '<div class="en-pending">&#x231B; Not yet translated' + (p.scholar ? ' (the working English, which the site shows)' : '') + '</div>'
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

def _ask_withdrawn(con=None) -> set:
    """PATH_2026_10_12: the texts withdrawn from the site (repair_text.py --withdraw) are left out of Ask here too;
    the register beside the database asked (as the Library reads it), else data/."""
    try:
        folder = None
        if con is not None:
            f = (con.execute("PRAGMA database_list").fetchone() or (None, None, ""))[2]
            folder = pathlib.Path(f).parent if f else None
        return {d for d, r in _source_verdicts(folder).items() if r.get("status") == "withdrawn"}
    except Exception:
        return set()


def _ask_retrieve(con, q, k=12):
    m = _ask_fts_query(q)
    if not m:
        return []
    try:
        rows = con.execute(
            """SELECT d.code, p.verse_ref, p.page_no, p.idx, p.translation
               FROM passages_fts f
               JOIN passages p ON p.rowid = f.rowid
               JOIN docs d ON d.id = p.doc_id
               WHERE passages_fts MATCH ?
                 AND TRIM(COALESCE(p.translation,'')) <> ''
                 AND d.code NOT LIKE '%-RETIRED'
                 AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
               ORDER BY bm25(passages_fts) LIMIT ?""",
            (m, k),
        ).fetchall()
        wd = _ask_withdrawn(con)   # PATH_2026_10_12
        return [r for r in rows if r[0] not in wd]
    except sqlite3.OperationalError:
        return []


_ASK_VEC_CACHE = {}   # ASK_VECTOR_CACHE_2026_10_04: {key, ids, mat}
_ASK_QV = {}          # BRAIN_ITEMS_2026_10_07: question -> (model, normalised vector), briefly


def _ask_brain_items(con, q, data):
    """BRAIN_ITEMS_2026_10_07: approved stories, found episodes and approved images close to the
    question, from brain_items (scripts/brain_items.py). [] when there is no such index."""
    got = _ASK_QV.pop(q, None)
    if not got:
        return []
    try:
        import brain_items as _bi
        try:
            k = max(0, min(6, int(data.get("k_editorial", 3))))
        except (TypeError, ValueError):
            k = 3
        return _bi.retrieve(con, got[1], got[0], k=k, include_drafts=True if data.get("drafts") else None)
    except Exception as e:
        print(f"[ask] editorial items skipped: {type(e).__name__}: {e}")
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
        try:   # METER_GATES_2026_10_04: about $0.000001 a question, but recorded like any paid call
            from usage_meter import meter as _meter
            _dbf = (con.execute("PRAGMA database_list").fetchone() or (None, None, ""))[2]
            if _dbf:   # the file this question was asked of, never a default path
                _meter(kind="ask_embed", doc="", engine=model, in_chars=len(q), units=1, db=_dbf)
        except Exception:
            pass
        qv = np.asarray(res["embedding"] if isinstance(res, dict) else res.embedding,
                        dtype="float32")
    except Exception:
        return None                      # query-embed failed → FTS fallback
    n = float(np.linalg.norm(qv))
    if n > 0:
        qv = qv / n
    _ASK_QV[q] = (model, qv)   # BRAIN_ITEMS_2026_10_07: the same vector finds editorial items, no second call
    while len(_ASK_QV) > 64:
        _ASK_QV.pop(next(iter(_ASK_QV)))
    # ASK_VECTOR_CACHE_2026_10_04: read the matrix once; rebuild only when the index changes.
    _sig = con.execute("SELECT COUNT(*), MAX(updated_at) FROM passage_embeddings WHERE model=?",
                       (model,)).fetchone()
    _key = (model, dim, _sig[0], _sig[1])
    if _ASK_VEC_CACHE.get("key") != _key:
        ids, mats = [], []
        for pid, blob in con.execute(
                "SELECT passage_id, vec FROM passage_embeddings WHERE model=?", (model,)):
            v = np.frombuffer(blob, dtype="float32")
            if dim and v.shape[0] != dim:
                continue
            ids.append(pid); mats.append(v)
        if not ids:
            return None
        _ASK_VEC_CACHE.clear()
        _ASK_VEC_CACHE.update(key=_key, ids=ids, mat=np.vstack(mats))
    ids = _ASK_VEC_CACHE["ids"]
    sims = _ASK_VEC_CACHE["mat"] @ qv    # both L2-normalised → dot == cosine
    order = np.argsort(-sims)[: k * 3 + 64]   # over-fetch, then filter retired and noise (ASK_NOISE_2026_10_07)
    top_ids = [ids[j] for j in order]
    ph = ",".join("?" * len(top_ids))
    got = {r[0]: r for r in con.execute(
        f"""SELECT p.id, d.code, p.verse_ref, p.page_no, p.idx, p.translation
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE p.id IN ({ph}) AND d.code NOT LIKE '%-RETIRED'
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
              AND TRIM(COALESCE(p.translation,'')) <> ''""", top_ids)}
    out, wd = [], _ask_withdrawn(con)   # PATH_2026_10_12: withdrawn texts left out
    for pid in top_ids:
        r = got.get(pid)
        if r and r[1] not in wd:
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
    # BRAIN_ITEMS_2026_10_07
    " Items labelled EDITORIAL (a retelling, an episode pointer or an illustration) were made from this corpus "
    "by the project; they are not scripture. Ground every claim in the passages, and cite an editorial item only "
    "for what it adds, such as where an episode is told or that a retelling or picture of it exists."
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
    extra = []   # BRAIN_ITEMS_2026_10_07
    try:
        rows = _ask_semantic_retrieve(con, q, k)   # meaning-based if embeddings built
        if rows:
            mode = "semantic"
            extra = _ask_brain_items(con, q, data)
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
    for j, it in enumerate(extra, len(sources) + 1):   # BRAIN_ITEMS_2026_10_07
        sources.append({"n": j, "tag": it["tag"], "doc": it["doc"], "verse_ref": None, "page_no": it["page"],
                        "idx": it["idx"], "english": it["text"][:600], "kind": it["kind"], "link": it["link"],
                        "label": it["label"]})
        ctx.append(f"[{j}] [{it['tag']}] ({it['label']}) {it['text'][:700]}")
    user_msg = "PASSAGES:\n" + "\n".join(ctx) + f"\n\nQUESTION: {q}\n\nAnswer, citing [tags]:"
    # METER_GATES_2026_10_04: Ask is a paid call like any other. It asks the budget first and is metered.
    try:
        from usage_meter import budget_ok as _bok
        if not _bok(db):
            return jsonify({"error": "The spend cap is reached, so Ask is paused. The passages below were "
                                     "found without a paid call. Raise the cap with python scripts\\set_budget.py.",
                            "sources": sources, "mode": mode}), 402
    except Exception:
        pass
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
        _t0 = time.time()
        resp = genai.GenerativeModel(**kwargs).generate_content(user_msg)
        try:   # METER_GATES_2026_10_04
            from usage_meter import meter as _meter
            try:
                _out = len(getattr(resp, "text", "") or "")
            except Exception:
                _out = 0
            _meter(kind="ask", doc="", engine=engine, resp=resp, in_chars=len(user_msg) + len(_ASK_SYSTEM),
                   out_chars=_out, units=1, duration_s=time.time() - _t0, db=db)
        except Exception:
            pass
        answer = (getattr(resp, "text", "") or "").strip() or \
                 "(The model returned no text — try rephrasing or a smaller k.)"
    except Exception as e:
        return jsonify({"error": f"LLM error: {e}", "sources": sources}), 500
    return jsonify({"answer": answer, "sources": sources, "engine": engine,
                    "k": k, "mode": mode, "editorial": len(extra)})   # BRAIN_ITEMS_2026_10_07


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
    # FILTERS3_2026_09_27: say how old the snapshot is, and refresh it when
    # asked or when it is older than max_age_s (default 600) - but only a
    # Datasette THIS dashboard started; one left by an earlier dashboard
    # process is reported, never killed from here.
    _snap = ROOT / "query_snapshot.db"
    _age = (time.time() - _snap.stat().st_mtime) if _snap.exists() else None
    if _port_serving("127.0.0.1", port):
        _p = _DATASETTE.get("proc")
        _owned = _p is not None and _p.poll() is None
        try:
            _max = float(data.get("max_age_s", 600))
        except (TypeError, ValueError):
            _max = 600.0
        _want = bool(data.get("refresh")) or (_age is not None and _age > _max)
        if not (_want and _owned):
            return jsonify({"url": url, "status": "already-running",
                            "snapshot_age_s": int(_age) if _age is not None else None,
                            "owned": _owned, "stale": bool(_want and not _owned)})
        _p.terminate()
        try:
            _p.wait(timeout=10)
        except Exception:
            _p.kill()
        for _i in range(20):
            if not _port_serving("127.0.0.1", port):
                break
            time.sleep(0.5)
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

# IMAGES_UI_2026_10_03: the Images tab (/images) - see scripts/images_web.py.
# Guarded: if the module is missing or broken the dashboard still starts.
try:
    import images_web as _images_web
    _images_web.register(app, launch=launch, root=ROOT, py=py, script=script)
except Exception as _images_err:
    print(f"[images] Images tab not loaded: {type(_images_err).__name__}: {_images_err}")

# SHELF_2026_10_04: the Shelf (/shelf) - see scripts/library_web.py. Guarded like the Images tab.
try:
    import library_web as _library_web
    _library_web.register(app, root=ROOT, bs_pdf=_bs_pdf_path, bs_modes=BOOKSMITH_MODES)
except Exception as _shelf_err:
    print(f"[shelf] Shelf not loaded: {type(_shelf_err).__name__}: {_shelf_err}")

# STORIES_UI_2026_10_05: the Stories page (/stories) - see scripts/stories_web.py. Guarded like the Shelf.
try:
    import stories_web as _stories_web
    _stories_web.register(app, launch=launch, root=ROOT, py=py, script=script)
except Exception as _stories_err:
    print(f"[stories] Stories page not loaded: {type(_stories_err).__name__}: {_stories_err}")

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

    # SINGLE_INSTANCE_2026_09_27. JOBS live in this process's memory, so a second
    # dashboard beside a running one splits the queue and the translate lock in
    # two (2026-09-27: pid 21432 started at 15:05 beside pid 41088). Refuse.
    import socket as _si_socket
    _si_host = "127.0.0.1" if args.host in ("", "0.0.0.0", "::") else args.host
    try:
        with _si_socket.create_connection((_si_host, args.port), timeout=1.5):
            print(f"[REFUSED] something already answers on {_si_host}:{args.port} - "
                  "not starting a second dashboard (RUNBOOK 3h). Use "
                  "scripts\\restart_dashboard.ps1 to replace it.")
            sys.exit(3)
    except OSError:
        pass
    # DASH_HIDDEN_2026_10_08. scripts\restart_dashboard.ps1 now runs this server with no window
    # and its output in a log file. The page polls several times a second, so the launcher asks
    # (SA_QUIET_REQUESTS=1) for the per-request lines to be left out. Errors still reach the log.
    if os.environ.get("SA_QUIET_REQUESTS") == "1":
        import logging as _dh_logging
        _dh_logging.getLogger("werkzeug").setLevel(_dh_logging.WARNING)
        print("[log] request lines left out (SA_QUIET_REQUESTS=1); errors are still written")
    app.run(host=args.host, port=args.port, debug=False)
