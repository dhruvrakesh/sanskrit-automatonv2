#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI app exposing:
- POST /api/analyze
- POST /api/entities
- POST /api/translate  (?explain=true)
- GET  /api/search?q=&limit=&offset=
- GET  /api/passage/{id}
- GET  /api/passage/{id}/variants
- GET  /                -> webui
Serves /compare.html (variants view)
"""
import os, json, subprocess, sys, sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Body, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ---- paths & env ----
APP_DIR = Path(__file__).resolve().parent.parent
STATIC = APP_DIR / "webui" / "static"

# load .env after APP_DIR is defined
try:
    from dotenv import load_dotenv
    load_dotenv(str(APP_DIR / ".env"))
except Exception:
    pass

DB_PATH = Path(os.environ.get("SA_DB_PATH", APP_DIR / "data" / "context.db"))

app = FastAPI(title="Sanskrit Automaton API")

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

def db_conn():
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail=f"DB not found: {DB_PATH}")
    return sqlite3.connect(str(DB_PATH))

# ---- UI pages ----
@app.get("/", response_class=HTMLResponse)
def home():
    index = STATIC / "index.html"
    return HTMLResponse(index.read_text("utf-8") if index.exists() else "<h1>Sanskrit Automaton</h1>")

@app.get("/compare.html")
def compare_html():
    page = STATIC / "compare.html"
    if not page.exists():
        raise HTTPException(404, "compare.html not found. Please add it under webui/static.")
    return FileResponse(str(page))

# ---- helpers ----
def run_script(script: str, text: str, args: List[str] = None) -> Dict[str, Any]:
    args = args or []
    script_path = APP_DIR / "scripts" / script
    cmd = [sys.executable, str(script_path)] + args + ["--json"]
    try:
        proc = subprocess.run(
            cmd, input=text.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))
        return json.loads(proc.stdout.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{script} failed: {e}")

# ---- original endpoints ----
@app.post("/api/analyze")
def api_analyze(payload: Dict[str, Any] = Body(...)):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    norm = run_script("normalize_text.py", text, [])
    sandhi = run_script("sandhi_split.py", text, [])
    morph = run_script("morph_parse.py", text, [])
    return {"normalized": norm, "sandhi": sandhi, "morph": morph}

@app.post("/api/entities")
def api_entities(payload: Dict[str, Any] = Body(...)):
    text = payload.get("text", "").strip()
    gaz = payload.get("gazetteer_path", "data/processed/gazetteer.jsonl")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    if not Path(gaz).exists():
        return {"entities": [], "note": f"Gazetteer not found at {gaz}. Run build_gazetteer.py first."}
    return run_script("ner_tag.py", text, ["--gaz", gaz])

@app.post("/api/translate")
def api_translate(payload: Dict[str, Any] = Body(...), explain: bool = Query(False)):
    import tempfile, os as _os
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    if explain:
        analysis = api_analyze({"text": text})
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
            json.dump(analysis, tf, ensure_ascii=False)
            ctx_path = tf.name
        try:
            out = run_script("infer_mt.py", text, ["--ctx-file", ctx_path])
        finally:
            try: _os.unlink(ctx_path)
            except OSError: pass
        out["evidence"] = out.get("evidence", {})
        out["evidence"]["analysis"] = analysis
        return out

    return run_script("infer_mt.py", text, [])

# ---- new: /api/search (fts or fallback like) ----
@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1), limit: int = 20, offset: int = 0, doc: Optional[str] = None):
    """Full-text search over passages (text + translation)."""
    with db_conn() as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        cols_p  = {r[1] for r in db.execute("PRAGMA table_info(passages)")}

        # Detect doc join mode
        if "doc_id" in cols_p and "docs" in tables:
            doc_join   = "LEFT JOIN docs d ON d.id=p.doc_id"
            doc_title  = "COALESCE(d.code,'(unknown)')"
            doc_filter = "AND d.code=?" if doc else ""
        elif "doc" in cols_p:
            doc_join   = ""
            doc_title  = "COALESCE(p.doc,'(unknown)')"
            doc_filter = "AND p.doc=?" if doc else ""
        else:
            doc_join, doc_title, doc_filter = "", "'(unknown)'", ""

        pg_col = next((c for c in ("page_no","pageno","page") if c in cols_p), "rowid")
        ix_col = "idx" if "idx" in cols_p else "rowid"
        tr_col = "translation" if "translation" in cols_p else ("en" if "en" in cols_p else "NULL")
        tx_col = "text" if "text" in cols_p else ("san" if "san" in cols_p else "NULL")

        has_fts = "passages_fts" in tables
        results = []
        try:
            if has_fts:
                fts_sql = f"""
                    SELECT p.id, {doc_title} AS title, p.{pg_col}, p.{ix_col}, p.{tx_col}, p.{tr_col}
                    FROM passages_fts f
                    JOIN passages p ON p.id=f.rowid
                    {doc_join}
                    WHERE passages_fts MATCH ? {doc_filter}
                    ORDER BY p.id LIMIT ? OFFSET ?
                """
                params = [q] + ([doc] if doc else []) + [limit, offset]
                rows = db.execute(fts_sql, params).fetchall()
            else:
                like = f"%{q}%"
                like_sql = f"""
                    SELECT p.id, {doc_title} AS title, p.{pg_col}, p.{ix_col}, p.{tx_col}, p.{tr_col}
                    FROM passages p {doc_join}
                    WHERE (p.{tx_col} LIKE ? OR p.{tr_col} LIKE ?) {doc_filter}
                    ORDER BY p.id LIMIT ? OFFSET ?
                """
                params = [like, like] + ([doc] if doc else []) + [limit, offset]
                rows = db.execute(like_sql, params).fetchall()
            results = [
                {"id": r[0], "doc": r[1], "page": r[2], "idx": r[3], "text": r[4] or "", "translation": r[5] or ""}
                for r in rows
            ]
        except Exception as e:
            return {"results": [], "error": str(e), "limit": limit, "offset": offset}
    return {"results": results, "limit": limit, "offset": offset}

# ---- new: /api/passage/{id} ----
@app.get("/api/passage/{pid}")
def api_get_passage(pid: int):
    """Fetch a single passage by its integer id."""
    with db_conn() as db:
        cols_p = {r[1] for r in db.execute("PRAGMA table_info(passages)")}
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        if "doc_id" in cols_p and "docs" in tables:
            doc_expr = "COALESCE(d.code,'(unknown)')"
            join_doc = "LEFT JOIN docs d ON d.id=p.doc_id"
        elif "doc" in cols_p:
            doc_expr = "p.doc"
            join_doc = ""
        else:
            doc_expr, join_doc = "'(unknown)'", ""

        pg_col = next((c for c in ("page_no","pageno","page") if c in cols_p), "rowid")
        ix_col = "idx" if "idx" in cols_p else "rowid"
        tr_col = "translation" if "translation" in cols_p else ("en" if "en" in cols_p else "NULL")
        tx_col = "text" if "text" in cols_p else ("san" if "san" in cols_p else "NULL")
        nm_col = "norm" if "norm" in cols_p else "NULL"

        sql = f"""
            SELECT p.id, {doc_expr} AS doc, p.{pg_col}, p.{ix_col}, p.{tx_col}, p.{nm_col}, p.{tr_col}
            FROM passages p {join_doc} WHERE p.id=?
        """
        r = db.execute(sql, (pid,)).fetchone()
        if not r:
            raise HTTPException(404, "passage not found")
        return {
            "id": r[0], "doc": r[1], "page": r[2], "idx": r[3],
            "text": r[4] or "", "normalized": r[5] or "", "translation": r[6] or ""
        }

# ---- new: /api/passage/{id}/variants (pipeline + reference_translations) ----
@app.get("/api/passage/{pid}/variants")
def api_variants(pid: int):
    with db_conn() as db:
        r = db.execute("SELECT text, normalized, translation, engine, rationale FROM passages WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404, "passage not found")
        text, norm, transl, engine, rat = r

        # reference_translations table is optional
        has_ref = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reference_translations'"
        ).fetchone() is not None

        refs = {}
        if has_ref:
            rr = db.execute("SELECT bori, debroy, dutt, notes FROM reference_translations WHERE norm=?",
                            (norm or text,)).fetchone()
            if rr:
                refs = {"bori": rr[0] or "", "debroy": rr[1] or "", "dutt": rr[2] or "", "notes": rr[3] or ""}

        return {
            "text": text, "normalized": norm or text,
            "pipeline": {"translation": transl or "", "engine": engine or "", "rationale": rat or ""},
            "references": refs
        }
