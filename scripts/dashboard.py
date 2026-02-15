#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple inbox dashboard (Flask) for Sanskrit Automaton

- Shows per-doc progress: PDFs, JSONL, ingested pages, total lines, translated lines, exports
- Never dies on a single bad doc/file (errors are logged & surfaced)
- Launch OCR / Ingest / Translate / Export as background jobs (threaded)
- Windows-safe subprocess calls (no shell=True, proper argv lists)

Run:
  python scripts/dashboard.py --inbox inbox --raw data/raw --db data/context.db --exports exports --host 127.0.0.1 --port 5057
"""
from __future__ import annotations
import os, sys, re, json, time, threading, uuid, pathlib, subprocess, sqlite3, traceback
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from flask import Flask, jsonify, request, send_from_directory

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

app = Flask("dashboard")

# ---------------- Job runner ----------------

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

JOBS: Dict[str, Job] = {}
JOBS_LOCK = threading.Lock()

def _run_job(job: Job):
    try:
        proc = subprocess.Popen(job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT))
        out, err = proc.communicate()
        job.ok = (proc.returncode == 0)
        job.out = (out or b"").decode("utf-8", "replace")
        job.err = (err or b"").decode("utf-8", "replace")
    except Exception as e:
        job.ok = False
        job.err = f"{type(e).__name__}: {e}\n" + traceback.format_exc()
    finally:
        job.end = time.time()

def launch(kind: str, doc: str, argv: List[str]) -> str:
    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv)
    with JOBS_LOCK:
        JOBS[job.id] = job
    t = threading.Thread(target=_run_job, args=(job,), daemon=True)
    t.start()
    return job.id

# -------------- utils ----------------

PDF_RE = re.compile(r"^([A-Za-z0-9_]+)_(\d{4})\.pdf$", re.IGNORECASE)
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
    """Return a dict with keys:
       {'pg_col','idx_col','doc_mode'} 
       doc_mode ∈ {'join_docs', 'passages_doc', 'passages_doc_code'}
    """
    pc = _cols(con, "passages")
    pg_col = "page_no" if "page_no" in pc else ( "pageno" if "pageno" in pc else ( "page" if "page" in pc else "rowid"))
    idx_col = "idx" if "idx" in pc else "rowid"
    tset = _tables(con)
    if "docs" in tset and {"id","code"}.issubset(_cols(con, "docs")) and "doc_id" in pc:
        doc_mode = "join_docs"
    elif "doc" in pc:
        doc_mode = "passages_doc"
    elif "doc_code" in pc:
        doc_mode = "passages_doc_code"
    else:
        doc_mode = "unknown"
    return {"pg_col":pg_col, "idx_col":idx_col, "doc_mode":doc_mode}

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
        return 0, 0
    pages = int(con.execute(sql,(doc,)).fetchone()[0] or 0)

    # total lines & translated lines
    if dm == "join_docs":
        sql_tot = "SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?"
        sql_tr  = "SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''"
    elif dm == "passages_doc":
        sql_tot = "SELECT COUNT(*) FROM passages WHERE doc=?"
        sql_tr  = "SELECT COUNT(*) FROM passages WHERE doc=? AND TRIM(COALESCE(translation,''))<>''"
    else:
        sql_tot = "SELECT COUNT(*) FROM passages WHERE doc_code=?"
        sql_tr  = "SELECT COUNT(*) FROM passages WHERE doc_code=? AND TRIM(COALESCE(translation,''))<>''"
    total = int(con.execute(sql_tot,(doc,)).fetchone()[0] or 0)
    trans = int(con.execute(sql_tr,(doc,)).fetchone()[0] or 0)
    return pages, total, trans

def count_exports(exports_dir: pathlib.Path, doc: str) -> int:
    if not exports_dir.exists(): return 0
    pref = f"{doc}_"
    return sum(1 for p in exports_dir.iterdir() if p.suffix.lower()==".html" and p.name.startswith(pref))

# -------------- API ----------------

def build_status(inbox: pathlib.Path, raw: pathlib.Path, dbp: pathlib.Path, exports: pathlib.Path):
    # never raise – return empty list on failure and log
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
                    "doc": doc,
                    "pdf_count": len(pdf_pages),
                    "jsonl_count": len(jsonl_pages),
                    "ingested_pages": int(ing_pages),
                    "total_lines": int(total_lines),
                    "translated_lines": int(trans_lines),
                    "exports": count_exports(exports, doc),
                })
        return rows
    except Exception as e:
        traceback.print_exc()
        return []

@app.get("/")
def index():
    return send_from_directory(str(SCRIPTS), "dashboard_static.html")

@app.get("/api/status")
def api_status():
    inbox = pathlib.Path(request.args.get("inbox") or "inbox")
    raw = pathlib.Path(request.args.get("raw") or "data/raw")
    dbp = pathlib.Path(request.args.get("db") or "data/context.db")
    exports = pathlib.Path(request.args.get("exports") or "exports")
    return jsonify(build_status(inbox, raw, dbp, exports))

@app.get("/api/job/<jid>")
def api_job(jid):
    with JOBS_LOCK:
        job = JOBS.get(jid)
    if not job:
        return jsonify({"error":"unknown job"}), 404
    return jsonify({
        "id": job.id, "kind": job.kind, "doc": job.doc,
        "ok": job.ok, "start": job.start, "end": job.end,
        "out": job.out[-4000:], "err": job.err[-4000:],  # tail
        "running": job.ok is None
    })

# -------- action endpoints (background) --------

# Doc codes must be safe for paths and CLI (no path traversal, no shell metachars)
DOC_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

def _validate_doc(doc) -> Optional[str]:
    if not doc or not isinstance(doc, str):
        return None
    return doc if DOC_RE.match(doc) else None

def py(*args: str) -> List[str]:
    return [sys.executable, *args]

def script(name: str) -> str:
    return str(SCRIPTS / name)

@app.post("/api/ocr")
def api_ocr():
    data = request.get_json(force=True) or {}
    doc   = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    dpi   = str(data.get("dpi") or 400)
    langs = str(data.get("langs") or "san+hin+eng")

    # find missing PDFs → OCR each (creates data/raw/<doc>_<pg>.jsonl)
    inbox = pathlib.Path(data.get("inbox") or "inbox")
    raw   = pathlib.Path(data.get("raw") or "data/raw")
    missing: List[pathlib.Path] = []
    for p in inbox.glob(f"{doc}_*.pdf"):
        m = PDF_RE.match(p.name); 
        if not m: continue
        pg = m.group(2)
        j1 = raw / f"{doc}_{pg}.jsonl"
        j2 = raw / f"{doc}_{pg}_norm.jsonl"
        if not j1.exists() and not j2.exists():
            missing.append(p)
    if not missing:
        return jsonify({"message":"Nothing to OCR"}), 200

    # Create one big job that loops inside a Python runner
    runner = [
        sys.executable, "-u", "-c",
        (
            "import sys,subprocess,pathlib,os;"
            f"pdfs={json.dumps([str(p) for p in missing])};"
            f"outdir={json.dumps(str(raw))};"
            f"dpi={json.dumps(dpi)};langs={json.dumps(langs)};"
            "root=str(pathlib.Path(sys.argv[0]).resolve().parents[2]);"
            "scr=str(pathlib.Path(root)/'scripts'/'ocr_pdf.py');"
            "ok=0;"
            "import shutil;"
            "for i,p in enumerate(pdfs,1):\n"
            "  cmd=[sys.executable,scr,'--pdf',p,'--out',str(pathlib.Path(outdir)/ (pathlib.Path(p).stem+'.jsonl')),'--dpi',dpi,'--langs',langs];\n"
            "  pr=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);\n"
            "  sys.stdout.write(f'[{i}/{len(pdfs)}] {pathlib.Path(p).name} -> {pr.returncode}\\n'); sys.stdout.flush();\n"
            "  ok+= (pr.returncode==0)\n"
            "print(f'Done: {ok}/{len(pdfs)} ok');"
        )
    ]
    jid = launch("ocr", doc, runner)
    return jsonify({"job": jid})

@app.post("/api/ingest")
def api_ingest():
    data = request.get_json(force=True) or {}
    doc  = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db   = data.get("db") or "data/context.db"
    raw  = data.get("raw") or "data/raw"
    glob = str(pathlib.Path(raw) / f"{doc}_*.jsonl")
    cmd = py(script("ingest_jsonl_fast.py"),
             "--doc", doc, "--glob", glob, "--db", db)
    jid = launch("ingest", doc, cmd)
    return jsonify({"job": jid})

@app.post("/api/translate")
def api_translate():
    data = request.get_json(force=True) or {}
    doc = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db  = data.get("db") or "data/context.db"
    engine = data.get("engine") or "openai:gpt-4o-mini"
    limit  = str(data.get("limit") or 50)
    sleep  = str(data.get("sleep") or 0.6)
    cmd = py(script("translate_passages.py"),
             "--db", db, "--doc", doc, "--engine", engine, "--sleep", sleep, "--limit", limit)
    jid = launch("translate", doc, cmd)
    return jsonify({"job": jid})

@app.post("/api/export")
def api_export():
    data = request.get_json(force=True) or {}
    doc = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    db  = data.get("db") or "data/context.db"
    out = data.get("out") or "exports"
    title = data.get("title") or f"{doc} — English Translation"
    cmd = py(script("export_html.py"),
             "--db", db, "--doc", doc, "--out", out, "--title", title, "--no-sanskrit")
    jid = launch("export", doc, cmd)
    return jsonify({"job": jid})

# -------------- static HTML (1 file) --------------

# Written next to this script so Flask can serve it easily
(SCRIPTS / "dashboard_static.html").write_text(r"""
<!doctype html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Inbox Dashboard</title>
<style>
  :root{--ink:#111;--mut:#6b7280;--bar:#e5e7eb;--ok:#6366f1}
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:24px}
  h1{font-size:28px;margin:0 0 16px 0}
  small{color:var(--mut)}
  table{width:100%;border-collapse:collapse;margin-top:12px}
  th,td{padding:10px;border-bottom:1px solid #f0f0f0;text-align:left;font-size:14px}
  .bar{height:8px;background:var(--bar);border-radius:999px;overflow:hidden}
  .bar>i{display:block;height:100%;background:var(--ok)}
  button{padding:6px 10px;border:1px solid #ddd;border-radius:7px;background:#fff;cursor:pointer}
  button:hover{background:#f9fafb}
  .row-actions button{margin-right:6px}
  #toast{position:fixed;right:14px;bottom:14px;background:#111;color:#fff;padding:10px 12px;border-radius:8px;opacity:.95;display:none}
</style>
</head><body>
<h1>Inbox Dashboard</h1>
<div id="meta" class="mut"></div>
<table id="grid"><thead><tr>
  <th>Doc</th><th>PDFs</th><th>JSONL</th><th>Ingested pages</th><th>Lines</th><th>Translated</th><th>Exports</th><th>Actions</th>
</tr></thead><tbody></tbody></table>
<div id="toast"></div>
<script>
const params = new URLSearchParams(window.location.search);
const cfg = {
  inbox:   params.get("inbox")   || "inbox",
  raw:     params.get("raw")     || "data/raw",
  db:      params.get("db")      || "data/context.db",
  exports: params.get("exports") || "exports",
}
document.getElementById("meta").textContent =
  `${cfg.inbox} | raw=${cfg.raw} | db=${cfg.db} | exports=${cfg.exports}`;

function pct(a,b){return b?Math.round(100*a/b):0;}
function bar(a,b){return `<div class="bar"><i style="width:${pct(a,b)}%"></i></div><small>${a}/${b} (${pct(a,b)}%)</small>`}
function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2000);}

async function refresh(){
  const r = await fetch(`/api/status?inbox=${encodeURIComponent(cfg.inbox)}&raw=${encodeURIComponent(cfg.raw)}&db=${encodeURIComponent(cfg.db)}&exports=${encodeURIComponent(cfg.exports)}`);
  const data = await r.json();
  const tb = document.querySelector("#grid tbody"); tb.innerHTML = "";
  for(const row of data){
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><b>${row.doc}</b></td>
      <td>${row.pdf_count}</td>
      <td>${bar(row.jsonl_count,row.pdf_count)}</td>
      <td>${bar(row.ingested_pages,row.pdf_count)}</td>
      <td>${row.total_lines}</td>
      <td>${bar(row.translated_lines,row.total_lines)}</td>
      <td>${row.exports}</td>
      <td class="row-actions">
        <button data-act="ocr" data-doc="${row.doc}">OCR</button>
        <button data-act="ingest" data-doc="${row.doc}">Ingest</button>
        <button data-act="translate" data-doc="${row.doc}">Translate (50)</button>
        <button data-act="export" data-doc="${row.doc}">Export</button>
      </td>`;
    tb.appendChild(tr);
  }
}

async function poll(jid,label){
  let tries=0;
  while(true){
    const r = await fetch(`/api/job/${jid}`);
    const j = await r.json();
    if(!j.running){ toast(`${label}: ${j.ok ? "done" : "failed"}`); console.log(j.out, j.err); refresh(); return; }
    await new Promise(r=>setTimeout(r, 1200));
    if(++tries%5===0) toast(`${label}: working…`);
  }
}

document.addEventListener("click", async ev=>{
  const b = ev.target.closest("button[data-act]");
  if(!b) return;
  const doc = b.dataset.doc;
  const act = b.dataset.act;

  if(act==="ocr"){
    const dpi = prompt("DPI?", "400") || "400";
    const langs = prompt("Tesseract langs? (e.g. san+hin+eng)", "san+hin+eng") || "san+hin+eng";
    const r = await fetch("/api/ocr",{method:"POST",headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, dpi, langs, inbox:cfg.inbox, raw:cfg.raw})});
    const j = await r.json(); if(j.job){ poll(j.job, `OCR ${doc}`); }
    else toast(j.message||"No work");
  }
  if(act==="ingest"){
    const r = await fetch("/api/ingest",{method:"POST",headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db:cfg.db, raw:cfg.raw})});
    const j = await r.json(); if(j.job) poll(j.job, `Ingest ${doc}`);
  }
  if(act==="translate"){
    const engine = prompt("Engine?", "openai:gpt-4o-mini") || "openai:gpt-4o-mini";
    const limit = prompt("Limit (rows)?", "50") || "50";
    const r = await fetch("/api/translate",{method:"POST",headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db:cfg.db, engine, limit})});
    const j = await r.json(); if(j.job) poll(j.job, `Translate ${doc}`);
  }
  if(act==="export"){
    const title = `${doc} — English Translation`;
    const r = await fetch("/api/export",{method:"POST",headers:{"Content-Type":"application/json"},
      body: JSON.stringify({doc, db:cfg.db, out:cfg.exports, title})});
    const j = await r.json(); if(j.job) poll(j.job, `Export ${doc}`);
  }
});

refresh();
setInterval(refresh, 10000);
</script>
</body></html>
""", encoding="utf-8")

# -------------- CLI --------------

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5057)
    args = ap.parse_args()
    print(f"Dashboard on http://{args.host}:{args.port}/")
    print("inbox=", pathlib.Path(args.inbox).resolve())
    print("raw=", pathlib.Path(args.raw).resolve())
    print("db=", pathlib.Path(args.db).resolve())
    print("exports=", pathlib.Path(args.exports).resolve())
    app.run(host=args.host, port=args.port, debug=False)
