#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
Srangam Hub - unified local console (v2, HUB_V2_2026_10_10).

One localhost page for the whole corpus, end to end:
  * This PC makes it: the translation engine (the Sanskrit Automaton dashboard, :5057: OCR, ingest,
    translation, QA, exports), the database (data/context.db) and the Gemini brain (the passage
    vectors and the editorial index, kept current by the SanskritMaintenance task).
  * The cloud carries it: the mirror to Supabase (SanskritCorpusMirror, every 2 h), the pictures on
    Drive (after each mirror run), and the Researchers' Corner desk (SanskritCornerWorker, every
    10 min), with its email.
  * The site serves it: srangam.nartiang.org and its working corpus (Library, Stories, Names,
    Pictures, Graphic novels, the Corner, Learn) and the published texts.
plus the other local apps (Panchang :8501, Booksmith :8765) and the wisdomlib crawl actions.

PURELY ADDITIVE: lives in its own folder and changes nothing in the projects. It (a) health-checks
them, (b) launches them through their own launchers, (c) reads their logs and the database,
read-only, and (d) proxies a few read-only dashboard endpoints so the page needs no CORS changes.

HUB_V2_2026_10_10, what changed and why (2026-10-10):
  * The dashboard was reported "down (ReadTimeout)" while it ran. v1 asked /api/status, the
    dashboard's heaviest read (about 7 s with 68 texts and 2,166 inbox pages), every 5 s with a
    2.5 s limit, and the page asked /api/usage every 5 s on top: the hub itself slowed the
    dashboard down. v2 asks /api/health (or /api/jobs/running on an older dashboard), which answers
    in milliseconds, at most once every 8 s however many hub pages are open; a dashboard that holds
    its port but answers slowly is "busy", not "down".
  * Start launched run.bat: a visible window whose closing ends the dashboard and every run it
    started (the problem DASH_HIDDEN_2026_10_08 fixed). v2 starts it with
    scripts\\restart_dashboard.ps1: no window, logs in D:\\backups\\dashboard_logs.
  * context.db was counted every 30 s inside a request. v2 counts it in the background every 10 min
    (read-only) and the page reads the last count.
  * New: /api/online, what the mirror, the pictures, the Corner desk and the maintenance task last
    did (from their own log files) and when the scheduled tasks run next.

Safety properties (as v1):
  * Binds to 127.0.0.1 only. No remote access.
  * Launch actions are a fixed whitelist - no arbitrary command execution.
  * The automaton is NEVER started twice (in-memory JOBS dict): launch is refused while its port
    is held.
  * The proxy is GET-only and limited to a whitelist of read-only dashboard paths.
  * The database is opened read-only (mode=ro), never written.

Run:   python hub.py        (needs: pip install flask requests)
Open:  http://127.0.0.1:5050
"""

import concurrent.futures
import datetime
import json
import os as _os
import pathlib
import re
import sqlite3
import subprocess
import threading
import time

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

HUB_MARK = "HUB_V2_2026_10_10"

# ---------------------------------------------------------------------------
# Configuration - monorepo-relative paths with a legacy fallback
# ---------------------------------------------------------------------------
# In the sanskrit-symphony monorepo the projects are siblings under one root. This hub lives in
# <root>/hub, so ROOT = HERE.parent and every sibling is addressed relatively. Transition-safe: a
# sibling that is not there falls back to its original absolute path. SYMPHONY_<NAME> overrides both.
HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent


def _resolve_path(name: str, rel: str, legacy: str) -> pathlib.Path:
    env = _os.environ.get(f"SYMPHONY_{name.upper()}")
    if env:
        return pathlib.Path(env)
    candidate = ROOT / rel
    if candidate.exists():
        return candidate
    return pathlib.Path(legacy)


PATHS = {
    "automaton": _resolve_path("automaton", "automaton",
                               r"D:\Sanksrit Automatons\sanskrit-automatonv2"),
    "panchang":  _resolve_path("panchang", "panchang", r"D:\panchang"),
    "wisdomlib": _resolve_path("wisdomlib", "wisdomlib", r"D:\wisdomlib"),
    # BOOKSMITH_PANE_2026_09_08 - lives outside the monorepo today.
    "booksmith": _resolve_path(
        "booksmith", "booksmith",
        r"D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith"),
    # HUB_V2_2026_10_10: where the desk's tasks write their logs
    "backups":   _resolve_path("backups", "backups", r"D:\backups"),
}
WISDOM_ARCHIVE = PATHS["wisdomlib"] / "wisdomlib_archive"
DATA = PATHS["automaton"] / "data"
URLS = {
    "automaton": "http://127.0.0.1:5057",
    "panchang":  "http://127.0.0.1:8501",
    "booksmith": "http://127.0.0.1:8765",   # BOOKSMITH_PANE_2026_09_08
    "srangam":   "https://srangam.nartiang.org",
    "srangam_sitemap": "https://xjaizfjcpkjcqbyobcsh.supabase.co/functions/v1/generate-sitemap",
}

HUB_PORT = 5050
AUTOMATON_PORT = 5057

# Fixed action whitelist: key -> (cwd, argv, long_running)
ACTIONS = {
    # HUB_V2_2026_10_10: the dashboard's own detached launcher (no window, logs to files)
    "start-automaton": (PATHS["automaton"],
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                         str(PATHS["automaton"] / "scripts" / "restart_dashboard.ps1")], False),
    "start-panchang":  (PATHS["panchang"],  ["cmd", "/c", "run.bat"], True),
    "start-booksmith": (PATHS["booksmith"], ["cmd", "/c", "run.bat"], True),
    "crawl-burst":     (PATHS["wisdomlib"], ["python", "scraper.py"], True),
    "reprioritize-dry":(PATHS["wisdomlib"], ["python", "reprioritize_crawl.py", "--dry-run"], False),
    "reprioritize":    (PATHS["wisdomlib"], ["python", "reprioritize_crawl.py"], False),
    "adapter-dry":     (PATHS["automaton"], ["python", r"scripts\wisdomlib_to_jsonl.py",
                                             "--archive", str(WISDOM_ARCHIVE),
                                             "--dry-run"], False),
    "adapter-run":     (PATHS["automaton"], ["python", r"scripts\wisdomlib_to_jsonl.py",
                                             "--archive", str(WISDOM_ARCHIVE)], False),
}

# The one-click "morning run": reprioritize (apply) -> crawl burst (500 pages) -> adapter (write JSONL)
MORNING_RUN = [
    ("reprioritize", PATHS["wisdomlib"], ["python", "reprioritize_crawl.py"]),
    ("crawl burst",  PATHS["wisdomlib"], ["python", "scraper.py"]),
    ("adapter",      PATHS["automaton"], ["python", r"scripts\wisdomlib_to_jsonl.py",
                                          "--archive", str(WISDOM_ARCHIVE)]),
]

# Read-only dashboard paths the proxy may forward. api/status (heavy) is not among them any more.
PROXY_ALLOW = {"api/health", "api/budget", "api/jobs/running", "api/progress", "api/jobs/history", "api/corpus",
               "api/usage"}

# The scheduled tasks of the desk (Windows Task Scheduler)
TASKS = ("SanskritCorpusMirror", "SanskritCornerWorker", "SanskritMaintenance", "SanskritDBBackup")

SERVICES_TTL_S = 8          # one round of health checks serves every hub page for this long
DB_EVERY_S = 10 * 60        # the database is counted this often, in the background
TASKS_EVERY_S = 5 * 60      # the task scheduler is asked this often

app = Flask(__name__)

# job registry: name -> {proc, started, lines[], done, rc}
JOBS = {}
JOBS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    """HUB_SINGLE_2026_09_27: a busy dashboard can miss an HTTP check but still owns its port; a TCP
    connect tells the two apart."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check(url: str, timeout: float = 2.5):
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        return {"up": r.status_code < 500, "code": r.status_code,
                "ms": int((time.time() - t0) * 1000)}
    except requests.RequestException as e:
        return {"up": False, "error": type(e).__name__, "ms": int((time.time() - t0) * 1000)}


def automaton_health(timeout: float = 4.0) -> dict:
    """HUB_V2_2026_10_10: up (answers), busy (holds its port, answers slowly) or down (no port).
    Asks /api/health (DESK_HEAL_2026_10_10), or /api/jobs/running on an older dashboard: both answer
    from memory, without touching the disk or the database."""
    t0 = time.time()
    for path in ("/api/health", "/api/jobs/running"):
        try:
            r = requests.get(URLS["automaton"] + path, timeout=timeout)
        except requests.RequestException as e:
            if _port_open("127.0.0.1", AUTOMATON_PORT):
                return {"up": True, "state": "busy", "error": type(e).__name__,
                        "ms": int((time.time() - t0) * 1000)}
            return {"up": False, "state": "down", "error": type(e).__name__,
                    "ms": int((time.time() - t0) * 1000)}
        if r.status_code == 404 and path == "/api/health":
            continue                      # a dashboard from before DESK_HEAL_2026_10_10
        out = {"up": r.status_code < 500, "state": "up" if r.status_code < 500 else "error",
               "code": r.status_code, "ms": int((time.time() - t0) * 1000)}
        try:
            j = r.json()
        except ValueError:
            return out
        jobs = j.get("jobs") if isinstance(j.get("jobs"), dict) else j   # /api/health nests them
        out["jobs"] = {"count": jobs.get("count", 0), "active": jobs.get("active", 0),
                       "queued": jobs.get("queued", 0), "running": (jobs.get("running") or [])[:8]}
        out["mark"] = j.get("mark")
        return out
    return {"up": False, "state": "down", "ms": int((time.time() - t0) * 1000)}


_SERVICES = {"at": 0.0, "data": None}
_SERVICES_LOCK = threading.Lock()


def services_snapshot() -> dict:
    """One round of checks, run side by side, shared by every caller for SERVICES_TTL_S."""
    with _SERVICES_LOCK:
        if _SERVICES["data"] is not None and time.time() - _SERVICES["at"] < SERVICES_TTL_S:
            return _SERVICES["data"]

        def panchang():
            p = check(URLS["panchang"] + "/_stcore/health")
            return p if p["up"] else check(URLS["panchang"] + "/healthz")   # older Streamlit builds

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            fa = ex.submit(automaton_health)
            fp = ex.submit(panchang)
            fs = ex.submit(check, URLS["srangam"], 6.0)
            fb = ex.submit(check, URLS["booksmith"])           # BOOKSMITH_PANE_2026_09_08
            data = {"automaton": fa.result(), "panchang": fp.result(), "srangam": fs.result(),
                    "booksmith": fb.result(), "paths_ok": {k: p.exists() for k, p in PATHS.items()},
                    "mark": HUB_MARK}
        _SERVICES.update(at=time.time(), data=data)
        return data


def _last_jsonl(path: pathlib.Path, n: int = 30) -> list:
    """The last n JSON lines of a log, newest last; reads only the file's tail."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 400 * 1024))
            tail = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    out = []
    for line in tail[-n:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _mirror_state() -> dict:
    rows = _last_jsonl(DATA / "corpus_sync_log.jsonl")
    if not rows:
        return {"error": "no corpus_sync_log.jsonl yet"}
    def brief(r):
        v = r.get("verified") or {}
        return {"ts": r.get("ts"), "stopped": r.get("stopped"), "error": r.get("error"),
                "seconds": r.get("seconds"), "client": r.get("client"),
                "equal": v.get("groups_equal"), "different": v.get("groups_different"),
                "verify_error": v.get("error"),     # the rows went in; the final check could not run
                "changed": sum(int((t or {}).get("changed") or 0) for t in (r.get("tables") or {}).values())}
    ok = [r for r in rows if r.get("stopped") == "done"]
    return {"last": brief(rows[-1]), "last_ok": brief(ok[-1]) if ok else None}


def _media_state() -> dict:
    rows = _last_jsonl(DATA / "corpus_media_log.jsonl")
    if not rows:
        return {"error": "no corpus_media_log.jsonl yet"}
    def brief(r):
        f = dict(r.get("files") or {}) if isinstance(r.get("files"), dict) else None
        if f is not None and f.get("on_drive") is not None:
            # on_drive counts what was there before the run; add what it uploaded or found there
            # (as corner_worker.media_state does)
            f["on_drive_after"] = int(f.get("on_drive") or 0) + int(f.get("uploaded") or 0) + int(f.get("skipped") or 0)
        return {"ts": r.get("ts"), "stopped": r.get("stopped"), "error": r.get("error"),
                "files": f, "here": r.get("here")}
    ok = [r for r in rows if r.get("stopped") == "done"]
    return {"last": brief(rows[-1]), "last_ok": brief(ok[-1]) if ok else None}


def _corner_state() -> dict:
    rows = _last_jsonl(DATA / "corner_worker_log.jsonl", n=200)
    if not rows:
        return {"error": "no corner_worker_log.jsonl yet"}
    last = rows[-1]
    day = time.strftime("%Y-%m-%d", time.gmtime())
    today = [r for r in rows if str(r.get("ts") or "").startswith(day)]
    return {"last": {k: last.get(k) for k in ("ts", "stopped", "error", "taken", "done", "failed", "queued",
                                               "mail", "seconds", "client")},
            "today": {"rounds": len(today), "done": sum(int(r.get("done") or 0) for r in today),
                      "failed": sum(int(r.get("failed") or 0) for r in today)}}


_MAINT_RE = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] (.*)$")


def _maintenance_state() -> dict:
    log = PATHS["backups"] / "maintenance_log.txt"
    if not log.exists():
        return {"error": "no maintenance_log.txt yet"}
    try:
        with open(log, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 200 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError as e:
        return {"error": type(e).__name__}
    last_tick = last_done = last_skip = open_start = None
    skips_since = 0
    for line in lines:
        m = _MAINT_RE.match(line.strip())
        if not m:
            continue
        at, msg = m.group(1), m.group(2)
        if msg.startswith("TICK"):
            last_tick = at
        elif msg.startswith("START"):
            open_start = at                 # cleared by the DONE, FAIL or SKIP that ends the run
        elif msg.startswith("DONE"):
            last_done, skips_since, open_start = {"at": at, "text": msg}, 0, None
        elif msg.startswith("SKIP") or msg.startswith("FAIL"):
            last_skip, skips_since, open_start = {"at": at, "text": msg}, skips_since + 1, None
    # a START with nothing after it is a run in progress, or one the task's 1 h limit stopped (it
    # cannot log that): the page tells them apart by its age
    return {"last_tick": last_tick, "last_done": last_done, "last_skip": last_skip,
            "skips_since_done": skips_since, "unfinished_start": open_start}


# ---- the database, counted in the background ------------------------------------------------

_DB = {"at": None, "data": None, "running": False}
_DB_LOCK = threading.Lock()

_DB_QUERIES = {
    "texts": "SELECT COUNT(*) FROM docs WHERE code NOT LIKE '%-RETIRED'",
    # as the dashboard's Library counts them: running heads and front matter are not verses
    "verses": ("SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) "
               "FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code NOT LIKE '%-RETIRED' "
               "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"),
    "passages": ("SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(translation,''))<>'' THEN 1 ELSE 0 END) "
                 "FROM passages"),
    "hindi": "SELECT COUNT(*) FROM translations_l10n WHERE lang='hi' AND TRIM(COALESCE(translation,''))<>''",
    "vectors": "SELECT COUNT(*) FROM passage_embeddings",
    # as build_embeddings.py picks them: English verses with no vector, or one older than the translation
    "to_embed": ("SELECT COUNT(*) FROM passages p JOIN docs d ON d.id = p.doc_id "
                 "WHERE TRIM(COALESCE(p.translation,'')) <> '' "
                 "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') AND d.code NOT LIKE '%-RETIRED' "
                 "AND NOT EXISTS (SELECT 1 FROM passage_embeddings e WHERE e.passage_id = p.id "
                 "AND NOT (p.translated_at IS NOT NULL AND e.updated_at IS NOT NULL "
                 "AND julianday(p.translated_at) > julianday(e.updated_at)))"),
    "brain_items": "SELECT COUNT(*) FROM brain_items",
    "names": "SELECT COUNT(*) FROM entities",
    "mentions": "SELECT COUNT(*) FROM entity_mentions",
    "stories": "SELECT COALESCE(status,'?'), COUNT(*) FROM doc_stories GROUP BY 1",
    "pictures": "SELECT COALESCE(status,'?'), COUNT(*) FROM doc_images GROUP BY 1",
    "novels": "SELECT COALESCE(status,'?'), COUNT(*) FROM doc_novels GROUP BY 1",
}


def _count_db() -> dict:
    db = DATA / "context.db"
    if not db.exists():
        return {"error": "context.db not found"}
    out, errors = {}, {}
    t0 = time.time()
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error as e:
        return {"error": str(e)}
    try:
        for key, sql in _DB_QUERIES.items():
            try:
                rows = con.execute(sql).fetchall()
            except sqlite3.Error as e:          # a table this database does not have (yet)
                errors[key] = str(e)
                continue
            if key in ("stories", "pictures", "novels"):
                out[key] = {str(s): int(n) for s, n in rows}
            elif key in ("verses", "passages"):
                out[key] = {"all": int(rows[0][0] or 0), "english": int(rows[0][1] or 0)}
            else:
                out[key] = int(rows[0][0] or 0)
    finally:
        con.close()
    out["seconds"] = round(time.time() - t0, 1)
    if errors:
        out["missing"] = errors
    return out


def _db_refresh():
    try:
        data = _count_db()
    except Exception as e:                      # never let the thread die
        data = {"error": "%s: %s" % (type(e).__name__, e)}
    with _DB_LOCK:
        _DB.update(at=time.time(), data=data, running=False)


def db_snapshot(start: bool = True) -> dict:
    """The last count and its time; starts a new count in the background when it is old."""
    with _DB_LOCK:
        stale = _DB["at"] is None or time.time() - _DB["at"] > DB_EVERY_S
        if start and stale and not _DB["running"]:
            _DB["running"] = True
            threading.Thread(target=_db_refresh, daemon=True).start()
        return {"at": _DB["at"], "counting": _DB["running"], **(_DB["data"] or {})}


# ---- the scheduled tasks, asked in the background --------------------------------------------

_TASKS = {"at": None, "data": None, "running": False}
_TASKS_LOCK = threading.Lock()

_TASKS_PS = (
    "$o = foreach ($n in @(%s)) { try { $i = Get-ScheduledTaskInfo -TaskName $n -ErrorAction Stop; "
    "[pscustomobject]@{name=$n; last=$(if ($i.LastRunTime) { $i.LastRunTime.ToString('o') } else { $null }); "
    "next=$(if ($i.NextRunTime) { $i.NextRunTime.ToString('o') } else { $null }); result=$i.LastTaskResult} } "
    "catch { [pscustomobject]@{name=$n; error='not found'} } }; $o | ConvertTo-Json -Compress"
) % ", ".join("'%s'" % t for t in TASKS)


def _tasks_refresh():
    data = {}
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", _TASKS_PS], capture_output=True,
                           text=True, timeout=25,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        rows = json.loads(r.stdout or "[]")
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            data[row.get("name")] = {k: row.get(k) for k in ("last", "next", "result", "error")}
    except Exception as e:                      # never let the thread die with running=True
        data = {"error": type(e).__name__}
    with _TASKS_LOCK:
        _TASKS.update(at=time.time(), data=data, running=False)


def tasks_snapshot() -> dict:
    with _TASKS_LOCK:
        stale = _TASKS["at"] is None or time.time() - _TASKS["at"] > TASKS_EVERY_S
        if stale and not _TASKS["running"]:
            _TASKS["running"] = True
            threading.Thread(target=_tasks_refresh, daemon=True).start()
        return _TASKS["data"] or {}


def sequence_thread(name: str, steps):
    """Run steps in order, all output into one job buffer; stop on first failure."""
    rc = 0
    for label, cwd, argv in steps:
        with JOBS_LOCK:
            JOBS[name]["lines"].append(f"-- {label} --")
        try:
            proc = subprocess.Popen(
                argv, cwd=str(cwd),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace")
        except OSError as e:
            with JOBS_LOCK:
                JOBS[name]["lines"].append(f"x launch failed: {e}")
                JOBS[name]["done"], JOBS[name]["rc"] = True, 1
            return
        for line in iter(proc.stdout.readline, ""):
            with JOBS_LOCK:
                buf = JOBS[name]["lines"]
                buf.append(line.rstrip()[:400])
                if len(buf) > 400:
                    del buf[:200]
        proc.wait()
        rc = proc.returncode
        with JOBS_LOCK:
            JOBS[name]["lines"].append(f"-- {label} finished (rc={rc}) --")
        if rc != 0:
            break
    with JOBS_LOCK:
        JOBS[name]["done"], JOBS[name]["rc"] = True, rc


def reader_thread(name: str, proc: subprocess.Popen):
    # HUB_POLL_2026_09_27: a launcher can hand the hub's stdout pipe to the service it starts, so the
    # pipe stays open for the service's whole life and the loop below never ends. Mark the job done
    # when the launcher process itself exits.
    def _waiter():
        rc = proc.wait()
        with JOBS_LOCK:
            JOBS[name]["done"] = True
            JOBS[name]["rc"] = rc
        with _SERVICES_LOCK:
            _SERVICES["at"] = 0.0           # HUB_V2: what was started shows on the next look
    threading.Thread(target=_waiter, daemon=True).start()
    for line in iter(proc.stdout.readline, ""):
        with JOBS_LOCK:
            buf = JOBS[name]["lines"]
            buf.append(line.rstrip()[:400])
            if len(buf) > 200:
                del buf[:100]
    proc.wait()
    with JOBS_LOCK:
        JOBS[name]["done"] = True
        JOBS[name]["rc"] = proc.returncode


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(HERE, "hub.html")


@app.get("/api/services")
def services():
    return jsonify(services_snapshot())


@app.get("/api/online")
def online():
    """HUB_V2_2026_10_10: what the desk did last, from its own logs, and the database's last count."""
    return jsonify({
        "mark": HUB_MARK,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "db": db_snapshot(),
        "mirror": _mirror_state(),
        "media": _media_state(),
        "corner": _corner_state(),
        "maintenance": _maintenance_state(),
        "tasks": tasks_snapshot(),
    })


@app.get("/api/sitemap-stats")
def sitemap_stats():
    """Live-site pulse: how many URLs the DB-driven sitemap currently exposes."""
    try:
        r = requests.get(URLS["srangam_sitemap"], timeout=10)
        n = r.text.count("<loc>")
        arts = r.text.count("/articles/")
        return jsonify({"ok": r.status_code == 200, "urls": n, "article_urls": arts})
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": type(e).__name__})


@app.get("/api/corpus-stats")
def corpus_stats():
    """Local pipeline pulse (as v1, for the crawl row): the database's last count (HUB_V2: from the
    background count, never a query in the request) + crawl_state.json progress."""
    snap = db_snapshot()
    if snap.get("error"):
        out = {"db": {"error": snap["error"]}}
    elif snap.get("at") is None:
        out = {"db": {"error": "counting the database..."}}
    else:
        p = snap.get("passages") or {}
        out = {"db": {"docs": snap.get("texts"), "passages": p.get("all", 0), "translated": p.get("english", 0),
                      "by_lang": {"hi": snap.get("hindi", 0)}}}
    state = PATHS["wisdomlib"] / "wisdomlib_archive" / "crawl_state.json"
    if state.exists():
        try:
            s = json.loads(state.read_text(encoding="utf-8"))
            out["crawl"] = {"visited": len(s.get("visited", [])),
                            "queued": len(s.get("queue", [])),
                            "pages_crawled": s.get("pages_crawled", 0)}
        except (json.JSONDecodeError, OSError) as e:
            out["crawl"] = {"error": type(e).__name__}
    else:
        out["crawl"] = {"error": "crawl_state.json not found"}
    return jsonify(out)


@app.get("/proxy/automaton/<path:sub>")
def proxy(sub):
    if sub not in PROXY_ALLOW:
        return jsonify({"error": "path not whitelisted"}), 403
    try:
        r = requests.get(f"{URLS['automaton']}/{sub}", params=request.args, timeout=10)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "application/json"))
    except requests.RequestException as e:
        return jsonify({"error": type(e).__name__}), 502


@app.post("/api/run/<action>")
def run_action(action):
    # Sequenced one-click pipeline pass
    if action == "morning-run":
        with JOBS_LOCK:
            j = JOBS.get(action)
            if j and not j["done"]:
                return jsonify({"error": "morning run already in progress"}), 409
            for step_action in ("crawl-burst", "reprioritize", "adapter-run"):
                sj = JOBS.get(step_action)
                if sj and not sj["done"]:
                    return jsonify({"error": f"{step_action} already running"}), 409
            JOBS[action] = {"proc": None, "started": time.time(),
                            "lines": [], "done": False, "rc": None}
        threading.Thread(target=sequence_thread, args=(action, MORNING_RUN),
                         daemon=True).start()
        return jsonify({"ok": True, "action": action, "long_running": True})

    if action not in ACTIONS:
        return jsonify({"error": "unknown action"}), 404
    cwd, argv, long_running = ACTIONS[action]
    if not cwd.exists():
        return jsonify({"error": f"folder not found: {cwd}"}), 500

    # Guard: never double-start a service that is already up. HUB_V2: a running dashboard is not an
    # error, so the page shows it as information ("already running").
    if action == "start-automaton" and (_port_open("127.0.0.1", AUTOMATON_PORT)
                                        or automaton_health()["up"]):
        return jsonify({"error": "the dashboard is already running (it is never started twice)",
                        "already": True}), 409
    if action == "start-panchang" and (check(URLS["panchang"] + "/_stcore/health")["up"]
                                       or check(URLS["panchang"] + "/healthz")["up"]):
        return jsonify({"error": "panchang is already running", "already": True}), 409
    if action == "start-booksmith" and check(URLS["booksmith"])["up"]:
        return jsonify({"error": "booksmith is already running", "already": True}), 409
    with JOBS_LOCK:
        j = JOBS.get(action)
        if j and not j["done"]:
            return jsonify({"error": "action already in progress"}), 409

    try:
        proc = subprocess.Popen(
            argv, cwd=str(cwd), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    with JOBS_LOCK:
        JOBS[action] = {"proc": proc, "started": time.time(),
                        "lines": [], "done": False, "rc": None}
    threading.Thread(target=reader_thread, args=(action, proc), daemon=True).start()
    with _SERVICES_LOCK:
        _SERVICES["at"] = 0.0                       # the next look is a fresh one
    return jsonify({"ok": True, "action": action, "long_running": long_running})


@app.get("/api/job/<action>")
def job_status(action):
    with JOBS_LOCK:
        j = JOBS.get(action)
        if not j:
            return jsonify({"exists": False})
        return jsonify({
            "exists": True, "done": j["done"], "rc": j["rc"],
            "elapsed_s": int(time.time() - j["started"]),
            "tail": j["lines"][-30:],
        })


if __name__ == "__main__":
    print(f"Srangam Hub ({HUB_MARK}) -> http://127.0.0.1:{HUB_PORT}")
    db_snapshot()          # the first count starts now, in the background
    app.run(host="127.0.0.1", port=HUB_PORT, debug=False, threaded=True)
