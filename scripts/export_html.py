#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML exporter for Sanskrit Automaton DBs (v4)
---------------------------------------------
- Honors --doc across schemas
- **Respects --en-col / --san-col even when only one is provided**
- Autodetects columns with name hints + content sampling
- **Excludes structural & JSON/NER-like columns** (ents/entities/gazetteer etc.)
- EN-only by default; optional Sanskrit & side-by-side
- Drops boilerplate; auto-fallback to keep all if nothing remains
- Batch mode (--all) & diagnostics (--debug)
"""
from __future__ import annotations
import argparse, html, os, re, sqlite3
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

# --- DB helpers --------------------------------------------------------------

def _tables(con: sqlite3.Connection) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def _cols(con: sqlite3.Connection, table: str):
    try:
        return list(con.execute(f"PRAGMA table_info({table})"))
    except sqlite3.OperationalError:
        return []

def _colnames(con: sqlite3.Connection, table: str) -> set:
    return {r[1] for r in _cols(con, table)}


def _page_col(con: sqlite3.Connection) -> str:
    pc = _colnames(con, "passages")
    for c in ("page_no","pageno","page","pg","pageNumber","page_num"):
        if c in pc: return c
    return "page_no" if "page_no" in pc else (next(iter(pc)) if pc else "rowid")


def _idx_expr(con: sqlite3.Connection) -> Tuple[str,str]:
    pc = _colnames(con, "passages")
    for c in ("idx","line_no","line","lineno","i"):
        if c in pc: return c,c
    return "rowid","rowid"

# --- doc-aware WHERE ---------------------------------------------------------

def _doc_where(con: sqlite3.Connection, doc: Optional[str]) -> Tuple[str,Tuple]:
    pc = _colnames(con, "passages"); t = _tables(con)
    if doc and "doc_id" in pc and "docs" in t:  return "JOIN docs d ON d.id=p.doc_id WHERE d.code=?", (doc,)
    if doc and "doc" in pc:                     return "WHERE p.doc=?", (doc,)
    if doc and "doc_code" in pc:                 return "WHERE p.doc_code=?", (doc,)
    return "WHERE 1=1", tuple()

def _and(where: str) -> str:  # help build WHERE ... AND ...
    return (where + " AND") if "WHERE" in where.upper() else (where + " WHERE")

# --- autodetect columns ------------------------------------------------------
_SAN_HINTS = {"san","sanskrit","sa","orig","text","ocr"}
_EN_HINTS  = {"en","english","eng","tr","translation","mt","mt_en","gpt","eng_text","translation_en","en_text"}
# exclude from candidate sets entirely
_STRUCT    = {"id","rowid","doc_id","doc","doc_code","hash","bbox","conf","lang","created_at","updated_at",
              # structural/order columns
              "idx","i","line","line_no","lineno","page","pageno","page_no","page_num","pageNumber"}
# strongly penalize as EN (NER/JSON-ish)
_JSONY_OR_NER_NAMES = {"ents","entities","gazetteer","ner","json","payload"}

_ASCII_RE  = re.compile(r"[A-Za-z]")
_DEV_RE    = re.compile(r"[\u0900-\u097F]")


def _to_str(x):
    if isinstance(x, str): return x
    if isinstance(x, bytes):
        try: return x.decode("utf-8", "ignore")
        except Exception: return x.decode(errors="ignore")
    return str(x)

def _ascii_ratio(s: object) -> float:
    s = _to_str(s);
    if not s: return 0.0
    a = sum(1 for ch in s if ord(ch) < 128); return a / max(1, len(s))

def _dev_ratio(s: object) -> float:
    s = _to_str(s);
    if not s: return 0.0
    d = len(_DEV_RE.findall(s)); return d / max(1, len(s))


def _sample_vals(con: sqlite3.Connection, doc: Optional[str], col: str, limit: int=300) -> List[str]:
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {col} IS NOT NULL AND {col}<>''"
    sql = f"SELECT CAST({col} AS TEXT) FROM passages p {where} LIMIT {limit}"
    return [r[0] for r in con.execute(sql, prm)]


def _detect_cols(con: sqlite3.Connection, doc: Optional[str], force_san: Optional[str], force_en: Optional[str], debug=False) -> Tuple[str,str]:
    pc = [c for c in _colnames(con, "passages") if c not in _STRUCT]

    # If caller forced one or both, honor it/them and only detect the missing one
    if force_san and force_en:
        if debug: print(f"[detect] forced san='{force_san}', en='{force_en}'")
        return force_san, force_en

    # scoring dicts
    s_san: Dict[str,float] = {}; s_en: Dict[str,float] = {}

    for c in pc:
        name = c.lower()
        vals = _sample_vals(con, doc, c, 150)
        if not vals:
            # name-only prior
            if name in _SAN_HINTS or any(h in name for h in _SAN_HINTS):
                s_san[c] = s_san.get(c, 0.0) + 0.5
            if name in _EN_HINTS or any(h in name for h in _EN_HINTS):
                s_en[c]  = s_en.get(c, 0.0) + 0.5
            # Penalize NER/JSON columns even with no samples
            if name in _JSONY_OR_NER_NAMES: s_en[c] = s_en.get(c,0.0) - 2.0
            continue

        dev = sum(_dev_ratio(v) for v in vals)/len(vals)
        asc = sum(_ascii_ratio(v) for v in vals)/len(vals)
        jsonish = sum(1 for v in vals if _to_str(v).lstrip().startswith(('{','[')) or '"engine"' in _to_str(v) or '"entities"' in _to_str(v)) / len(vals)
        san_hint = 0.5 if (name in _SAN_HINTS or any(h in name for h in _SAN_HINTS)) else 0.0
        en_hint  = 0.5 if (name in _EN_HINTS  or any(h in name for h in _EN_HINTS))  else 0.0
        ner_pen  = 1.5 if name in _JSONY_OR_NER_NAMES else 0.0

        s_san[c] = dev*1.2 + san_hint - asc*0.3
        s_en[c]  = asc*1.2 + en_hint - dev*0.3 - jsonish*2.0 - ner_pen

    # choose
    san_guess = max(s_san, key=s_san.get) if s_san else '""'
    en_guess  = max(s_en,  key=s_en.get)  if s_en  else '""'

    # if user forced one
    if force_en:
        en_guess = force_en
    if force_san:
        san_guess = force_san

    if san_guess == en_guess and len(s_en) > 1:
        for k,_ in sorted(s_en.items(), key=lambda x:x[1], reverse=True):
            if k != san_guess:
                en_guess = k; break

    if debug:
        print("[detect] san candidates:", sorted(s_san.items(), key=lambda x:x[1], reverse=True)[:5])
        print("[detect] en  candidates:", sorted(s_en.items(),  key=lambda x:x[1], reverse=True)[:5])
        print(f"[detect] chosen san='{san_guess}', en='{en_guess}'")

    return san_guess or '""', en_guess or '""'

# --- fetch -------------------------------------------------------------------

def _fetch(con: sqlite3.Connection, doc: Optional[str], lo: int, hi: int, san_col: str, en_col: str):
    pg = _page_col(con); idx_sel, idx_order = _idx_expr(con)
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {pg} BETWEEN ? AND ?"; prm = prm + (lo,hi)
    sql = f"""
    SELECT {pg} AS page_no, {idx_sel} AS idx,
           COALESCE({san_col},'') AS san,
           COALESCE({en_col},'') AS en
    FROM passages p
    {where}
    ORDER BY {pg}, {idx_order}
    """
    return list(con.execute(sql, prm).fetchall())


def _page_span(con: sqlite3.Connection, doc: str) -> Tuple[int,int]:
    pg = _page_col(con); where, prm = _doc_where(con, doc)
    row = con.execute(f"SELECT MIN({pg}), MAX({pg}) FROM passages p {where}", prm).fetchone()
    lo = int(row[0]) if row and row[0] is not None else 1
    hi = int(row[1]) if row and row[1] is not None else lo
    return lo,hi

# --- cleaning ----------------------------------------------------------------
_ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—\–\·\*\'\"`~^=]+$")
_MQQ_RE        = re.compile(r"^[\"']{1,4}$")
_JUNK_PHRASES  = tuple(s.lower() for s in [
    "i am not able to provide a translation",
    "i am not able to translate this snippet",
    "the translation is unclear",
    "does not form a coherent",
    "appears to be a mix of",
    "please provide a complete and coherent snippet",
    "not enough context to translate",
    "unable to translate",
    "garbled",
])

def _is_junk_en(s: str) -> bool:
    if not s: return True
    t = s.strip()
    if not t: return True
    if _ONLY_PUNCT_RE.match(t): return True
    if _MQQ_RE.match(t): return True
    return any(x in t.lower() for x in _JUNK_PHRASES)

# --- HTML --------------------------------------------------------------------
CSS = """
body { font-family: Georgia, 'Times New Roman', serif; margin: 2rem; color: #111; }
h1 { font-size: 2.2rem; margin-bottom: 1.0rem; }
h2 { font-size: 1.05rem; color: #666; margin-top: 1.4rem; margin-bottom: 0.6rem; }
.page { margin-bottom: 1.2rem; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; align-items: start; }
.col h3 { margin: 0 0 .5rem 0; font-size: 1rem; color: #333; }
.col p { margin: 0 0 .6rem 0; line-height: 1.6; }
.stacked p { margin: 0 0 .8rem 0; line-height: 1.65; }
.note { color: #888; font-style: italic; }
.small { font-size: .95rem; color: #333; }
hr { border: none; border-top: 1px solid #eee; margin: 1.0rem 0; }
"""

def _html(title: str, body_html: str) -> str:
    return f"""<!doctype html><html lang='en'><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
{body_html}
</body></html>"""

def _safe_filename(s: str) -> str:
    import re
    s = re.sub(r"[^\w\-]+", "_", s.strip()); s = re.sub(r"_+","_", s); return s.strip("._")

# --- export core -------------------------------------------------------------

def _group(rows: Sequence[Tuple[int,int,str,str]]):
    pages = defaultdict(list)
    for pg, _i, san, en in rows:
        pages[int(pg)].append((san or "", en or ""))
    return pages

def _render(title: str, pages, *, include_san=False, include_en=True, side_by_side=False, number_pages=True, drop_junk_en=True):
    out = []; kept = 0
    out.append(f"<h1>{html.escape(title)}</h1>")
    for pg in sorted(pages.keys()):
        san_lines = []; en_lines = []
        for san, en in pages[pg]:
            if include_san and san.strip(): san_lines.append(html.escape(san.strip()))
            if include_en and en is not None:
                if drop_junk_en and _is_junk_en(en):
                    continue
                t = en.strip()
                if t: en_lines.append(html.escape(t))
        if not (san_lines or en_lines):
            continue
        kept += len(en_lines)
        out.append("<div class='page'>")
        if number_pages: out.append(f"<h2>Page {pg}</h2>")
        if side_by_side and include_san and include_en:
            out.append("<div class='pair'>")
            out.append("<div class='col'><h3>Original</h3>" + "".join(f"<p>{t}</p>" for t in san_lines) + "</div>")
            out.append("<div class='col'><h3>English</h3>"  + "".join(f"<p>{t}</p>" for t in en_lines)  + "</div>")
            out.append("</div>")
        else:
            out.append("<div class='stacked'>")
            for t in en_lines: out.append(f"<p>{t}</p>")
            if include_san:
                if en_lines and san_lines: out.append("<hr/>")
                for t in san_lines: out.append(f"<p class='small'>{t}</p>")
            out.append("</div>")
        out.append("</div>")
    if kept == 0:
        out.append("<p class='note'>(No content matched your filters.)</p>")
    return "\n".join(out), kept

# --- CLI ---------------------------------------------------------------------

def _export_one(con: sqlite3.Connection, *, doc: Optional[str], lo: int, hi: int, title: Optional[str], dest: str, include_san: bool, include_en: bool, side_by_side: bool, number_pages: bool, drop_junk_en: bool, force_san: Optional[str], force_en: Optional[str], debug=False) -> str:
    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)
    rows = _fetch(con, doc, lo, hi, san_col, en_col); pages = _group(rows)
    if not title:
        title = (doc or "Export") + (" — English Translation" if include_en and not include_san else "")
    body, kept = _render(title, pages, include_san=include_san, include_en=include_en, side_by_side=side_by_side, number_pages=number_pages, drop_junk_en=drop_junk_en)
    if kept == 0 and include_en and not include_san and drop_junk_en:
        if debug: print("[export] 0 lines kept after cleaning; retrying with --keep-junk…")
        body, _ = _render(title, pages, include_san=include_san, include_en=include_en, side_by_side=side_by_side, number_pages=number_pages, drop_junk_en=False)
    os.makedirs(dest, exist_ok=True)
    out_path = os.path.join(dest, f"{_safe_filename(doc or 'export')}_{lo}-{hi}.html")
    with open(out_path, "w", encoding="utf-8") as f: f.write(_html(title, body))
    if debug: print(f"[export] wrote {out_path} | rows={len(rows)} | pages={len(pages)} | san='{san_col}' en='{en_col}'")
    return out_path


def _list_docs(con: sqlite3.Connection) -> List[str]:
    t = _tables(con)
    if "docs" in t and {"id","code"}.issubset(_colnames(con, "docs")):
        return [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code").fetchall()]
    pc = _colnames(con, "passages")
    if "doc" in pc:      return [r[0] for r in con.execute("SELECT DISTINCT doc FROM passages ORDER BY doc").fetchall()]
    if "doc_code" in pc: return [r[0] for r in con.execute("SELECT DISTINCT doc_code FROM passages ORDER BY doc_code").fetchall()]
    return []


def main():
    ap = argparse.ArgumentParser(description="Export clean HTML from Sanskrit Automaton DBs (v4)")
    ap.add_argument("--db", required=True)
    ap.add_argument("--doc")
    ap.add_argument("--from", dest="pg_from", type=int)
    ap.add_argument("--to",   dest="pg_to",   type=int)
    ap.add_argument("--out", default="exports")
    ap.add_argument("--title")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--side-by-side", action="store_true")
    ap.add_argument("--stacked", action="store_true")
    ap.add_argument("--no-pagenum", action="store_true")
    ap.add_argument("--no-sanskrit", action="store_true")
    ap.add_argument("--sanskrit", action="store_true")
    ap.add_argument("--keep-junk", action="store_true")
    ap.add_argument("--en-col")
    ap.add_argument("--san-col")
    ap.add_argument("--title-from-doc", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    include_san = bool(args.sanskrit and not args.no_sanskrit)
    include_en  = True
    side_by_side = bool(args.side_by_side and include_san)
    number_pages = not args.no_pagenum
    drop_junk_en = not args.keep_junk

    if not os.path.exists(args.db): raise SystemExit(f"DB not found: {args.db}")

    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        if args.all:
            docs = _list_docs(con)
            if not docs: raise SystemExit("Could not discover any docs in DB.")
            print(f"Found {len(docs)} docs. Exporting…")
            for code in docs:
                lo,hi = _page_span(con, code)
                title = (f"{code} — English Translation" if args.title_from_doc and (include_en and not include_san) else code)
                _export_one(con, doc=code, lo=lo, hi=hi, title=title or args.title, dest=args.out, include_san=include_san, include_en=include_en, side_by_side=side_by_side, number_pages=number_pages, drop_junk_en=drop_junk_en, force_san=args.san_col, force_en=args.en_col, debug=args.debug)
        else:
            if args.doc:
                lo,hi = (_page_span(con, args.doc) if (args.pg_from is None or args.pg_to is None) else (args.pg_from, args.pg_to))
            else:
                pg = _page_col(con); row = con.execute(f"SELECT MIN({pg}), MAX({pg}) FROM passages").fetchone()
                lo = int(row[0]) if row and row[0] is not None else 1
                hi = int(row[1]) if row and row[1] is not None else lo
            _export_one(con, doc=args.doc, lo=lo, hi=hi, title=args.title, dest=args.out, include_san=include_san, include_en=include_en, side_by_side=side_by_side, number_pages=number_pages, drop_junk_en=drop_junk_en, force_san=args.san_col, force_en=args.en_col, debug=args.debug)

if __name__ == "__main__":
    main()
