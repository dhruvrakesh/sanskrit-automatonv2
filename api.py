# api.py — run:  uvicorn api:app --reload --port 8000
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel

DATA_DIR = Path("data")
STATIC_DIR = Path("static")

app = FastAPI(title="Sanskrit Export API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR.mkdir(exist_ok=True, parents=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------- helpers ----------

def _db_path(db_file: str | None) -> Path:
    name = db_file or "context.db"
    p = DATA_DIR / name
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"DB not found: {p}")
    return p

def _tables(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def _cols(con: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    except sqlite3.OperationalError:
        return set()

def _page_col(con: sqlite3.Connection) -> str:
    c = _cols(con, "passages")
    if "page_no" in c: return "page_no"
    if "page" in c: return "page"
    raise HTTPException(status_code=500, detail="passages table needs a page_no or page column")

def _idx_expr(con: sqlite3.Connection) -> tuple[str,str]:
    # returns (select_expr, order_expr)
    c = _cols(con, "passages")
    if "idx" in c: return ("idx", "idx")
    # fallback: stable order by rowid, synthesize idx=0
    return ("0 AS idx", "rowid")

def _detect_mode(con: sqlite3.Connection) -> str:
    t = _tables(con)
    pc = _cols(con, "passages")
    # full relational
    if {"docs", "pages", "passages"}.issubset(t) and "page_id" in pc:
        return "new"
    # passages carries doc + page_no/page
    if "passages" in t and "doc" in pc and (("page_no" in pc) or ("page" in pc)):
        return "mid"
    # runs fallback (doc mapped to page ranges)
    if "runs" in t and "passages" in t and (("page_no" in pc) or ("page" in pc)):
        rc = _cols(con, "runs")
        if {"doc", "page_from", "page_to"}.issubset(rc):
            return "runs"
    # bare passages only
    if "passages" in t and (("page_no" in pc) or ("page" in pc)):
        return "compat"
    return "compat"

def _list_docs(con: sqlite3.Connection, mode: str) -> List[str]:
    try:
        if mode == "new":
            return [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code")]
        if mode == "mid":
            return [r[0] for r in con.execute("SELECT DISTINCT doc FROM passages ORDER BY doc")]
        if mode == "runs":
            return [r[0] for r in con.execute("SELECT DISTINCT doc FROM runs ORDER BY doc")]
        return []
    except Exception:
        return []

def _doc_ranges(con: sqlite3.Connection, mode: str) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    try:
        if mode == "new":
            q = """
            SELECT d.code, MIN(pg.page_no), MAX(pg.page_no)
            FROM pages pg JOIN docs d ON pg.doc_id=d.id
            GROUP BY d.code
            """
        elif mode == "mid":
            pg = _page_col(con)
            q = f"SELECT doc, MIN({pg}), MAX({pg}) FROM passages GROUP BY doc"
        elif mode == "runs":
            q = "SELECT doc, MIN(page_from), MAX(page_to) FROM runs GROUP BY doc"
        else:
            return out
        for code, lo, hi in con.execute(q):
            if lo is not None and hi is not None:
                out[str(code)] = [int(lo), int(hi)]
    except Exception:
        pass
    return out

def _runs_for_doc(con: sqlite3.Connection, doc: str) -> List[Tuple[int, int]]:
    return [(int(r[0]), int(r[1])) for r in con.execute(
        "SELECT page_from, page_to FROM runs WHERE doc=? ORDER BY page_from", (doc,)
    )]

def _fetch_passages(
    con: sqlite3.Connection,
    mode: str,
    doc: Optional[str],
    page_from: int,
    page_to: int,
) -> List[Tuple[int, int, str, str]]:
    if page_to < page_from:
        page_from, page_to = page_to, page_from

    if mode == "new":
        if not doc:
            raise HTTPException(status_code=400, detail="doc is required for this DB schema")
        q = """
        SELECT pg.page_no, pa.idx, IFNULL(pa.san,''), IFNULL(pa.en,'')
        FROM passages pa
        JOIN pages pg ON pa.page_id = pg.id
        JOIN docs d  ON pg.doc_id = d.id
        WHERE d.code = ? AND pg.page_no BETWEEN ? AND ?
        ORDER BY pg.page_no, pa.idx
        """
        return con.execute(q, (doc, page_from, page_to)).fetchall()

    if mode == "mid":
        if not doc:
            raise HTTPException(status_code=400, detail="doc is required for this DB schema")
        pg = _page_col(con)
        idx_sel, idx_order = _idx_expr(con)
        q = f"""
        SELECT {pg} AS page_no, {idx_sel}, IFNULL(san,''), IFNULL(en,'')
        FROM passages
        WHERE doc = ? AND {pg} BETWEEN ? AND ?
        ORDER BY {pg}, {idx_order}
        """
        return con.execute(q, (doc, page_from, page_to)).fetchall()

    if mode == "runs":
        pg = _page_col(con)
        idx_sel, idx_order = _idx_expr(con)
        rows: List[Tuple[int, int, str, str]] = []
        ranges = _runs_for_doc(con, doc) if doc else [(page_from, page_to)]
        if doc and not ranges:
            ranges = [(page_from, page_to)]
        for lo, hi in ranges:
            q = f"""
            SELECT {pg} AS page_no, {idx_sel}, IFNULL(san,''), IFNULL(en,'')
            FROM passages
            WHERE {pg} BETWEEN ? AND ?
            ORDER BY {pg}, {idx_order}
            """
            rows.extend(con.execute(q, (lo, hi)).fetchall())
        return rows

    # compat
    pg = _page_col(con)
    idx_sel, idx_order = _idx_expr(con)
    q = f"""
    SELECT {pg} AS page_no, {idx_sel}, IFNULL(san,''), IFNULL(en,'')
    FROM passages
    WHERE {pg} BETWEEN ? AND ?
    ORDER BY {pg}, {idx_order}
    """
    return con.execute(q, (page_from, page_to)).fetchall()

def _render_html(
    title: str,
    rows: List[Tuple[int, int, str, str]],
    include_san: bool,
    include_en: bool,
    side_by_side: bool,
    number_pages: bool,
) -> str:
    from html import escape
    pages: Dict[int, List[Tuple[int, int, str, str]]] = {}
    for pg, idx, san, en in rows:
        pages.setdefault(pg, []).append((pg, idx, san, en))

    css = """
    <style>
      @media print { .page { page-break-after: always; } }
      body { font-family: "Noto Serif", "Noto Serif Devanagari", "Noto Sans", serif; margin: 0; }
      .wrap { padding: 24px; max-width: 1100px; margin: 0 auto; }
      h1 { font-size: 20px; margin: 0 0 12px; font-weight: 600; }
      .page { margin: 24px 0; }
      .pg-head { color:#444; font-size: 12px; margin-bottom: 8px; }
      .rows { display: grid; grid-template-columns: 1fr; gap: 8px; }
      .row { display: grid; gap: 16px; }
      .san, .en { white-space: pre-wrap; line-height: 1.5; }
      .san { font-size: 18px; }
      .en { font-size: 16px; color:#111; }
      .two .row { grid-template-columns: 1fr 1fr; align-items: start; }
    </style>
    """
    body = [css, '<div class="wrap">', f"<h1>{escape(title)}</h1>"]
    for pg in sorted(pages):
        body.append('<div class="page">')
        if number_pages:
            body.append(f'<div class="pg-head">Page {pg}</div>')
        klass = "rows two" if (include_san and include_en and side_by_side) else "rows"
        body.append(f'<div class="{klass}">')
        for _, _, san, en in pages[pg]:
            san_html = escape(san or "")
            en_html = escape(en or "")
            if include_san and include_en and side_by_side:
                body.append(f'<div class="row"><div class="san">{san_html}</div><div class="en">{en_html}</div></div>')
            else:
                body.append('<div class="row">')
                if include_san: body.append(f'<div class="san">{san_html}</div>')
                if include_en: body.append(f'<div class="en">{en_html}</div>')
                body.append('</div>')
        body.append("</div></div>")
    body.append("</div>")
    return "<!doctype html><html><head><meta charset='utf-8'></head><body>" + "".join(body) + "</body></html>"


# ---------- API ----------

class DocsResp(BaseModel):
    db: str
    mode: str
    note: Optional[str] = None
    docs: List[str]
    ranges: Dict[str, List[int]] | None = None  # {doc:[min,max]}

@app.get("/api/meta/dbs")
def list_dbs():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    names = sorted([p.name for p in DATA_DIR.glob("*.db")])
    return {"dbs": names}

@app.get("/api/meta/docs", response_model=DocsResp)
def list_docs(db: str = Query(default="context.db")):
    p = _db_path(db)
    with sqlite3.connect(p) as con:
        mode = _detect_mode(con)
        docs = _list_docs(con, mode)
        ranges = _doc_ranges(con, mode) if docs else None
    note = None
    if mode == "compat":
        note = "Compat mode: DB lacks doc mapping; filtering is by page range only; 'doc' (if provided) is ignored."
    if mode == "runs":
        note = "Runs mode: using runs(doc, page_from, page_to) to map pages to docs."
    return DocsResp(db=p.name, mode=mode, note=note, docs=docs, ranges=ranges)

@app.get("/api/passages")
def get_passages(
    db: str = Query(default="context.db"),
    doc: Optional[str] = Query(default=None),
    page_from: int = Query(default=1, ge=1),
    page_to: int = Query(default=1, ge=1),
):
    p = _db_path(db)
    with sqlite3.connect(p) as con:
        mode = _detect_mode(con)
        rows = _fetch_passages(con, mode, doc, page_from, page_to)
    return [{"page_no": r[0], "idx": r[1], "san": r[2], "en": r[3]} for r in rows]

@app.get("/api/export/html", response_class=HTMLResponse)
def export_html(
    db: str = Query(default="context.db"),
    doc: Optional[str] = Query(default=None),
    page_from: int = Query(default=1, ge=1),
    page_to: int = Query(default=1, ge=1),
    title: str = Query(default="Export Sanskrit ↔ English"),
    include_san: bool = Query(default=True),
    include_en: bool = Query(default=True),
    side_by_side: bool = Query(default=True),
    number_pages: bool = Query(default=True),
):
    p = _db_path(db)
    with sqlite3.connect(p) as con:
        mode = _detect_mode(con)
        rows = _fetch_passages(con, mode, doc, page_from, page_to)
    html = _render_html(title, rows, include_san, include_en, side_by_side, number_pages)
    return HTMLResponse(content=html, media_type="text/html")

@app.get("/api/export/pdf")
def export_pdf(
    db: str = Query(default="context.db"),
    doc: Optional[str] = Query(default=None),
    page_from: int = Query(default=1, ge=1),
    page_to: int = Query(default=1, ge=1),
    title: str = Query(default="Export Sanskrit ↔ English"),
    include_san: bool = Query(default=True),
    include_en: bool = Query(default=True),
    side_by_side: bool = Query(default=True),
    number_pages: bool = Query(default=True),
):
    p = _db_path(db)
    with sqlite3.connect(p) as con:
        mode = _detect_mode(con)
        rows = _fetch_passages(con, mode, doc, page_from, page_to)
    html = _render_html(title, rows, include_san, include_en, side_by_side, number_pages)

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        raise HTTPException(status_code=501, detail="Playwright not installed. Use 'Print / Save PDF' in the UI or install Playwright.")

    out_pdf = Path("export.pdf")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pwt:
            browser = pwt.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=str(out_pdf), format="A4", margin={"top":"15mm","right":"12mm","bottom":"15mm","left":"12mm"})
            browser.close()
        return FileResponse(out_pdf, media_type="application/pdf", filename=out_pdf.name)
    finally:
        if out_pdf.exists():
            pass
