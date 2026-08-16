#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML exporter for Sanskrit Automaton DBs (v5 — scholarly edition)
-----------------------------------------------------------------
v5 (2026-08-02) rebuilds the output as a readable scholarly edition:
  * Title page with provenance (source, engine, prompt version, date, counts)
  * Table of contents linking to each chapter / adhyāya
  * Chapter/adhyāya grouping with headings (falls back to page grouping)
  * Per-verse blocks with the verse reference shown (e.g. 1.1.3)
  * Footnotes: the model's [bracketed] editorial clarifications become numbered
    footnotes at the end of each chapter (parenthetical epithet-glosses stay inline)
  * Optional IAST transliteration line under the Sanskrit
  * Multi-language: --hindi / --hindi-only / --lang <code>, side-by-side or stacked
  * Print-friendly, Devanagari-aware typography

Backward-compatible CLI: existing --doc/--all/--no-sanskrit/--side-by-side/etc.
still work; English-only export is unchanged in content.
"""
from __future__ import annotations
import argparse, html, os, re, sqlite3
from collections import defaultdict, OrderedDict
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

def _doc_where(con: sqlite3.Connection, doc: Optional[str]) -> Tuple[str,Tuple]:
    pc = _colnames(con, "passages"); t = _tables(con)
    if doc and "doc_id" in pc and "docs" in t:  return "JOIN docs d ON d.id=p.doc_id WHERE d.code=?", (doc,)
    if doc and "doc" in pc:                     return "WHERE p.doc=?", (doc,)
    if doc and "doc_code" in pc:                 return "WHERE p.doc_code=?", (doc,)
    return "WHERE 1=1", tuple()

def _and(where: str) -> str:
    return (where + " AND") if "WHERE" in where.upper() else (where + " WHERE")

def _has_l10n(con: sqlite3.Connection, lang: str) -> bool:
    if "translations_l10n" not in _tables(con):
        return False
    try:
        return bool(con.execute(
            "SELECT 1 FROM translations_l10n WHERE lang=? AND "
            "TRIM(COALESCE(translation,''))<>'' LIMIT 1", (lang,)).fetchone())
    except sqlite3.OperationalError:
        return False

# --- autodetect columns (unchanged from v4) ----------------------------------
_SAN_HINTS = {"san","sanskrit","sa","orig","text","ocr"}
_EN_HINTS  = {"en","english","eng","tr","translation","mt","mt_en","gpt","eng_text","translation_en","en_text"}
_STRUCT    = {"id","rowid","doc_id","doc","doc_code","hash","bbox","conf","lang","source","engine","meta_json","created_at","updated_at",
              "idx","i","line","line_no","lineno","page","pageno","page_no","page_num","pageNumber"}
_JSONY_OR_NER_NAMES = {"ents","entities","gazetteer","ner","json","payload"}
_ASCII_RE  = re.compile(r"[A-Za-z]")
_DEV_RE    = re.compile(r"[ऀ-ॿ]")

def _to_str(x):
    if isinstance(x, str): return x
    if isinstance(x, bytes):
        try: return x.decode("utf-8", "ignore")
        except Exception: return x.decode(errors="ignore")
    return str(x)

def _ascii_ratio(s: object) -> float:
    s = _to_str(s)
    if not s: return 0.0
    a = sum(1 for ch in s if ord(ch) < 128); return a / max(1, len(s))

def _dev_ratio(s: object) -> float:
    s = _to_str(s)
    if not s: return 0.0
    d = len(_DEV_RE.findall(s)); return d / max(1, len(s))

def _sample_vals(con, doc, col, limit=300):
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {col} IS NOT NULL AND {col}<>''"
    sql = f"SELECT CAST({col} AS TEXT) FROM passages p {where} LIMIT {limit}"
    return [r[0] for r in con.execute(sql, prm)]

def _detect_cols(con, doc, force_san, force_en, debug=False):
    pc = [c for c in _colnames(con, "passages") if c not in _STRUCT]
    if force_san and force_en:
        return force_san, force_en
    s_san: Dict[str,float] = {}; s_en: Dict[str,float] = {}
    for c in pc:
        name = c.lower()
        vals = _sample_vals(con, doc, c, 150)
        if not vals:
            if name in _SAN_HINTS or any(h in name for h in _SAN_HINTS): s_san[c] = s_san.get(c,0.0)+0.5
            if name in _EN_HINTS or any(h in name for h in _EN_HINTS):   s_en[c]  = s_en.get(c,0.0)+0.5
            if name in _JSONY_OR_NER_NAMES: s_en[c] = s_en.get(c,0.0)-2.0
            continue
        dev = sum(_dev_ratio(v) for v in vals)/len(vals)
        asc = sum(_ascii_ratio(v) for v in vals)/len(vals)
        jsonish = sum(1 for v in vals if _to_str(v).lstrip().startswith(('{','[')) or '"engine"' in _to_str(v) or '"entities"' in _to_str(v)) / len(vals)
        san_hint = 0.5 if (name in _SAN_HINTS or any(h in name for h in _SAN_HINTS)) else 0.0
        en_hint  = 0.5 if (name in _EN_HINTS  or any(h in name for h in _EN_HINTS))  else 0.0
        ner_pen  = 1.5 if name in _JSONY_OR_NER_NAMES else 0.0
        s_san[c] = dev*1.2 + san_hint - asc*0.3
        s_en[c]  = asc*1.2 + en_hint - dev*0.3 - jsonish*2.0 - ner_pen
    san_guess = max(s_san, key=s_san.get) if s_san else '""'
    en_guess  = max(s_en,  key=s_en.get)  if s_en  else '""'
    if not force_san and "text" in pc:        san_guess = "text"
    if not force_en and "translation" in pc:  en_guess = "translation"
    if force_en:  en_guess = force_en
    if force_san: san_guess = force_san
    if san_guess == en_guess and len(s_en) > 1:
        for k,_ in sorted(s_en.items(), key=lambda x:x[1], reverse=True):
            if k != san_guess: en_guess = k; break
    if debug:
        print(f"[detect] chosen san='{san_guess}', en='{en_guess}'")
    return san_guess or '""', en_guess or '""'

# --- provenance --------------------------------------------------------------

def _provenance(con, doc, hi_lang):
    """Collect edition metadata for the title page. Degrades gracefully."""
    prov = {"doc": doc, "category": None, "source": None,
            "en": {}, "loc": {}}
    dt = _tables(con)
    if "docs" in dt:
        dc = _colnames(con, "docs")
        sel = ["category" if "category" in dc else "NULL",
               "src_path" if "src_path" in dc else "NULL"]
        try:
            r = con.execute(f"SELECT {sel[0]}, {sel[1]} FROM docs WHERE code=?", (doc,)).fetchone()
            if r: prov["category"], prov["source"] = r[0], r[1]
        except sqlite3.OperationalError:
            pass
    pc = _colnames(con, "passages")
    def _agg(where, params, table="passages", tjoin=""):
        eng_col = "engine" if "engine" in _colnames(con, table) else "NULL"
        pv_col  = "mt_prompt_version" if "mt_prompt_version" in _colnames(con, table) else "NULL"
        qa_col  = "translation_qa" if "translation_qa" in _colnames(con, table) else "NULL"
        try:
            row = con.execute(
                f"""SELECT COUNT(*), GROUP_CONCAT(DISTINCT {eng_col}),
                           GROUP_CONCAT(DISTINCT {pv_col}), ROUND(AVG({qa_col}),3)
                    FROM {table} p {tjoin} {where}""", params).fetchone()
            return {"count": row[0] or 0, "engine": row[1], "prompt": row[2], "qa": row[3]}
        except sqlite3.OperationalError:
            return {}
    if "doc_id" in pc and "docs" in dt:
        prov["en"] = _agg("JOIN docs d ON d.id=p.doc_id WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''", (doc,))
        if hi_lang and "translations_l10n" in dt:
            prov["loc"] = _agg(
                "JOIN passages pp ON pp.id=p.passage_id JOIN docs d ON d.id=pp.doc_id "
                "WHERE d.code=? AND p.lang=? AND TRIM(COALESCE(p.translation,''))<>''",
                (doc, hi_lang), table="translations_l10n", tjoin="")
    return prov

# --- fetch (with verse_ref, chapter, iast) -----------------------------------

def _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=None):
    pg = _page_col(con); idx_sel, idx_order = _idx_expr(con)
    pcols = _colnames(con, "passages")
    vref = "p.verse_ref" if "verse_ref" in pcols else "NULL"
    chap = "p.chapter"   if "chapter"   in pcols else "NULL"
    iast = "p.iast"      if "iast"      in pcols else "NULL"
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {pg} BETWEEN ? AND ?"; prm = prm + (lo,hi)
    def _q(c):
        return f"p.{c}" if re.fullmatch(r"\w+", c or "") else (c or "''")
    if hi_lang:
        sql = f"""
        SELECT {pg} AS page_no, {idx_sel} AS idx, {vref} AS vref, {chap} AS chap,
               COALESCE({_q(san_col)},'') AS san, COALESCE({iast},'') AS iast,
               COALESCE({_q(en_col)},'') AS en, COALESCE(l.translation,'') AS loc
        FROM passages p
        LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = ?
        {where} ORDER BY {pg}, {idx_order}"""
        rows = con.execute(sql, (hi_lang,) + prm).fetchall()
    else:
        sql = f"""
        SELECT {pg} AS page_no, {idx_sel} AS idx, {vref} AS vref, {chap} AS chap,
               COALESCE({san_col},'') AS san, COALESCE({iast},'') AS iast,
               COALESCE({en_col},'') AS en, '' AS loc
        FROM passages p {where} ORDER BY {pg}, {idx_order}"""
        rows = con.execute(sql, prm).fetchall()
    out = []
    for r in rows:
        out.append({"page": int(r[0]) if r[0] is not None else 0, "idx": r[1],
                    "vref": r[2], "chap": r[3], "san": r[4] or "", "iast": r[5] or "",
                    "en": r[6] or "", "loc": r[7] or ""})
    return out

def _page_span(con, doc):
    pg = _page_col(con); where, prm = _doc_where(con, doc)
    row = con.execute(f"SELECT MIN({pg}), MAX({pg}) FROM passages p {where}", prm).fetchone()
    lo = int(row[0]) if row and row[0] is not None else 1
    hi = int(row[1]) if row and row[1] is not None else lo
    return lo,hi

# --- cleaning ----------------------------------------------------------------
_ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—\–\·\*\'\"`~^=]+$")
_MQQ_RE        = re.compile(r"^[\"']{1,4}$")
_JUNK_PHRASES  = tuple(s.lower() for s in [
    "i am not able to provide a translation","i am not able to translate this snippet",
    "the translation is unclear","does not form a coherent","appears to be a mix of",
    "please provide a complete and coherent snippet","not enough context to translate",
    "unable to translate","garbled",
])
def _is_junk_en(s: str) -> bool:
    if not s: return True
    t = s.strip()
    if not t: return True
    if _ONLY_PUNCT_RE.match(t): return True
    if _MQQ_RE.match(t): return True
    return any(x in t.lower() for x in _JUNK_PHRASES)

# --- footnote extraction -----------------------------------------------------
# The model's editorial clarifications look like "[i.e., Yudhiṣṭhira]" or
# "[referring to the Pāṇḍavas]". Turn each into a numbered footnote; leave
# parenthetical epithet-glosses "Dhanañjaya (Winner of Wealth)" inline.
_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
_SKIP_BRACKET = {"illegible", "अस्पष्ट"}

# Debroy-style inline formatting (2026-08-02): the model marks untranslated
# technical terms with markdown *asterisks* (e.g. *parva*, *nirveda*) — render
# them as italics, exactly as Debroy italicizes such terms, instead of showing
# raw asterisks. And drop the śloka-end "//" / pāda "/" structural markers,
# which are not printed in a reading edition.
_EM_RE = re.compile(r"\*(?!\s)([^*\n]+?)(?<!\s)\*")
_VERSE_END_RE = re.compile(r"\s*//+\s*$")

def _inline_format(escaped: str) -> str:
    """Apply to HTML-escaped translation text. Order matters: strip verse
    markers, then italicize *terms* (footnote [brackets] are handled separately)."""
    s = _VERSE_END_RE.sub("", escaped)          # trailing "//"
    s = s.replace(" // ", " — ").replace(" / ", " — ")  # internal half-verse breaks (rare post-v2)
    s = _EM_RE.sub(r"<em>\1</em>", s)            # *term* -> italics
    return s.strip()

def _extract_footnotes(text_escaped: str, counter: List[int], notes: List[Tuple[int,str]]):
    """text_escaped is HTML-escaped. Replace [notes] with <sup> markers and
    append (n, note) to notes. Returns the rewritten HTML."""
    def repl(m):
        inner = m.group(1).strip()
        if inner.lower() in _SKIP_BRACKET:
            return m.group(0)  # keep [ILLEGIBLE]/[अस्पष्ट] literal
        counter[0] += 1
        n = counter[0]
        notes.append((n, inner))
        return f"<sup class='fn-ref' id='fnr-{n}'><a href='#fn-{n}'>{n}</a></sup>"
    return _BRACKET_RE.sub(repl, text_escaped)

# --- HTML / CSS --------------------------------------------------------------
CSS = """
:root { --ink:#1a1a1a; --muted:#6b6b6b; --rule:#e2e0da; --accent:#7a5c2e; --hi-ink:#1a1a2e; }
* { box-sizing: border-box; }
body { font-family: 'Iowan Old Style','Palatino Linotype',Georgia,serif; color: var(--ink);
       max-width: 820px; margin: 0 auto; padding: 2.5rem 1.5rem 6rem; line-height: 1.7;
       background: #fcfbf8; }
.titlepage { text-align: center; padding: 2rem 0 1rem; border-bottom: 2px solid var(--rule); margin-bottom: 1.5rem; }
.titlepage h1 { font-size: 2.4rem; margin: 0 0 .4rem; letter-spacing: .01em; }
.titlepage .subtitle { color: var(--muted); font-size: 1.05rem; font-style: italic; }
.prov { font-size: .82rem; color: var(--muted); margin-top: 1.2rem; line-height: 1.9; }
.prov b { color: var(--ink); font-weight: 600; }
.methodology { font-size: .86rem; color: var(--muted); background: #f4f1ea;
       border-left: 3px solid var(--accent); padding: .7rem 1rem; margin: 1.2rem 0; text-align: left; border-radius: 0 4px 4px 0; }
.toc { margin: 1.5rem 0 2.5rem; padding: 1rem 1.25rem; background: #f7f5ef; border: 1px solid var(--rule); border-radius: 6px; }
.toc h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 0 0 .6rem; }
.toc ol { margin: 0; padding-left: 1.4rem; columns: 2; column-gap: 2rem; }
.toc a { color: var(--accent); text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.chapter { margin: 2.5rem 0; }
.chapter > h2 { font-size: 1.5rem; border-bottom: 1px solid var(--rule); padding-bottom: .3rem;
       color: var(--accent); scroll-margin-top: 1rem; }
.verse { margin: 0 0 1.25rem; padding-left: 3.2rem; position: relative; }
.vref { position: absolute; left: 0; top: .15rem; font-size: .72rem; color: var(--muted);
       font-family: 'JetBrains Mono',ui-monospace,monospace; width: 2.9rem; text-align: right; }
.verse .en { margin: 0 0 .3rem; }
.verse .hi { margin: .2rem 0; font-family: 'Noto Sans Devanagari','Nirmala UI','Mangal',serif;
       line-height: 1.95; color: var(--hi-ink); }
.verse .sa { margin: .25rem 0 0; font-size: .95rem; color: #333;
       font-family: 'Noto Serif Devanagari','Nirmala UI','Mangal',serif; }
.verse .iast { font-size: .8rem; color: var(--muted); font-style: italic; margin: .1rem 0 0; }
.pair { display: grid; gap: 1.25rem; align-items: start; }
.pair.cols-2 { grid-template-columns: 1fr 1fr; }
.pair.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
.pair .col h4 { margin: 0 0 .4rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
.footnotes { margin-top: 1.5rem; padding-top: .8rem; border-top: 1px solid var(--rule); font-size: .82rem; color: #444; }
.footnotes ol { margin: 0; padding-left: 1.4rem; }
.footnotes li { margin-bottom: .3rem; }
.fn-ref { font-size: .68em; line-height: 0; }
.fn-ref a { text-decoration: none; color: var(--accent); }
.note { color: #999; font-style: italic; }
@media (max-width: 800px) { .pair.cols-2, .pair.cols-3 { grid-template-columns: 1fr; }
       .toc ol { columns: 1; } body { padding: 1.5rem 1rem 4rem; } }
@media print { body { background: #fff; max-width: none; } .toc { break-inside: avoid; }
       .chapter { break-inside: avoid-page; } a { color: inherit; text-decoration: none; } }
"""

def _html(title: str, body_html: str, lang_attr="en") -> str:
    return f"""<!doctype html><html lang='{lang_attr}'><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
{body_html}
</body></html>"""

def _safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", s.strip()); s = re.sub(r"_+","_", s); return s.strip("._")

# --- scholarly render --------------------------------------------------------

def _section_key(rec):
    """Group by chapter when present, else by page."""
    ch = rec.get("chap")
    if ch not in (None, "", "None"):
        return ("chapter", str(ch))
    return ("page", str(rec.get("page")))

def _render(doc, recs, prov, *, include_san, include_en, include_hi, hi_label,
            side_by_side, number_pages, drop_junk_en, want_toc=True, want_footnotes=True,
            title=None):
    # Group into ordered sections.
    sections = OrderedDict()
    for r in recs:
        sections.setdefault(_section_key(r), []).append(r)

    out = []
    # ── Title page ──
    disp_title = title or (doc or "Export").replace("_", " ").title()
    langs = []
    if include_en: langs.append("English")
    if include_hi: langs.append(hi_label)
    if include_san and not (include_en or include_hi): langs.append("Sanskrit")
    subtitle = " / ".join(langs) + (" edition" if langs else "")
    out.append("<div class='titlepage'>")
    out.append(f"<h1>{html.escape(disp_title)}</h1>")
    if subtitle.strip(): out.append(f"<div class='subtitle'>{html.escape(subtitle)}</div>")
    pv = []
    if prov.get("source"):   pv.append(f"<b>Source:</b> {html.escape(str(prov['source']))}")
    if prov.get("category"): pv.append(f"<b>Category:</b> {html.escape(str(prov['category']))}")
    en, loc = prov.get("en") or {}, prov.get("loc") or {}
    if include_en and en.get("count"):
        pv.append(f"<b>English:</b> {en['count']} verses"
                  + (f", engine {html.escape(str(en.get('engine')))}" if en.get('engine') else "")
                  + (f", prompt {html.escape(str(en.get('prompt')))}" if en.get('prompt') else "")
                  + (f", mean QA {en.get('qa')}" if en.get('qa') is not None else ""))
    if include_hi and loc.get("count"):
        pv.append(f"<b>{html.escape(hi_label)}:</b> {loc['count']} verses"
                  + (f", engine {html.escape(str(loc.get('engine')))}" if loc.get('engine') else "")
                  + (f", prompt {html.escape(str(loc.get('prompt')))}" if loc.get('prompt') else "")
                  + (f", mean QA {loc.get('qa')}" if loc.get('qa') is not None else ""))
    if pv:
        out.append("<div class='prov'>" + "<br/>".join(pv) + "</div>")
    out.append("<div class='methodology'>Machine translation produced by the Sanskrit "
               "Automaton pipeline (context-aware, verse-by-verse) in the tradition of "
               "Bibek Debroy's critical-edition renderings. Italicized words are "
               "untranslated Sanskrit technical terms; bracketed clarifications appear "
               "as numbered footnotes. Verse references follow the source numbering "
               "(e.g. 1.1.0 is the benedictory maṅgala verse; star-passages excluded by "
               "the critical edition are omitted). A scholar's reading edition, not a "
               "substitute for the critical text.</div>")
    out.append("</div>")

    # ── TOC ──
    sec_meta = []
    for i, (key, _rows) in enumerate(sections.items(), 1):
        kind, val = key
        label = (f"Adhyāya {val}" if kind == "chapter" else f"Page {val}")
        sec_meta.append((f"sec-{i}", label))
    if want_toc and len(sec_meta) > 1:
        out.append("<nav class='toc'><h2>Contents</h2><ol>")
        for sid, label in sec_meta:
            out.append(f"<li><a href='#{sid}'>{html.escape(label)}</a></li>")
        out.append("</ol></nav>")

    kept = 0
    # ── Sections ──
    for i, (key, rows) in enumerate(sections.items(), 1):
        kind, val = key
        sid, label = sec_meta[i-1]
        out.append(f"<section class='chapter' id='{sid}'>")
        out.append(f"<h2>{html.escape(label)}</h2>")
        fn_counter = [0]; fn_notes: List[Tuple[int,str]] = []
        for r in rows:
            san = (r["san"] or "").strip()
            iast = (r["iast"] or "").strip()
            en  = (r["en"] or "").strip()
            loc = (r["loc"] or "").strip()
            if include_en and drop_junk_en and _is_junk_en(en): en = ""
            has_any = (include_san and san) or (include_en and en) or (include_hi and loc)
            if not has_any: continue
            vref = r.get("vref")
            vlabel = html.escape(str(vref)) if vref not in (None,"","None") else ""
            def _en_html():
                base = _inline_format(html.escape(en))
                return _extract_footnotes(base, fn_counter, fn_notes) if want_footnotes else base
            def _hi_html():
                return _inline_format(html.escape(loc))
            if side_by_side:
                cols = []
                if include_san and san: cols.append(("Sanskrit",
                    f"<p class='sa'>{html.escape(san)}</p>" + (f"<p class='iast'>{html.escape(iast)}</p>" if iast else "")))
                if include_en and en:
                    cols.append(("English", f"<p class='en'>{_en_html()}</p>"))
                if include_hi and loc: cols.append((hi_label, f"<p class='hi'>{_hi_html()}</p>"))
                if not cols: continue
                out.append(f"<div class='verse'>")
                if vlabel: out.append(f"<span class='vref'>{vlabel}</span>")
                out.append(f"<div class='pair cols-{len(cols)}'>")
                for lab, cell in cols:
                    out.append(f"<div class='col'><h4>{html.escape(lab)}</h4>{cell}</div>")
                out.append("</div></div>")
            else:
                out.append("<div class='verse'>")
                if vlabel: out.append(f"<span class='vref'>{vlabel}</span>")
                if include_en and en:
                    out.append(f"<p class='en'>{_en_html()}</p>")
                if include_hi and loc:
                    out.append(f"<p class='hi'>{_hi_html()}</p>")
                if include_san and san:
                    out.append(f"<p class='sa'>{html.escape(san)}</p>")
                    if iast: out.append(f"<p class='iast'>{html.escape(iast)}</p>")
                out.append("</div>")
            kept += 1
        # footnotes for this section
        if want_footnotes and fn_notes:
            out.append("<div class='footnotes'><ol>")
            for n, note in fn_notes:
                out.append(f"<li id='fn-{n}'>{html.escape(note)} "
                           f"<a href='#fnr-{n}' class='fn-ref'>&#8617;</a></li>")
            out.append("</ol></div>")
        out.append("</section>")
    if kept == 0:
        out.append("<p class='note'>(No content matched your filters.)</p>")
    return "\n".join(out), kept

# --- export core -------------------------------------------------------------

def _export_one(con, *, doc, lo, hi, title, dest, include_san, include_en,
                side_by_side, number_pages, drop_junk_en, force_san, force_en,
                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False):
    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)
    include_hi = bool(hi_lang)
    recs = _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=hi_lang)
    prov = _provenance(con, doc, hi_lang)
    body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,
                         include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,
                         number_pages=number_pages, drop_junk_en=drop_junk_en,
                         want_toc=want_toc, want_footnotes=want_footnotes, title=title)
    if kept == 0 and include_en and not include_san and drop_junk_en:
        body, _ = _render(doc, recs, prov, include_san=include_san, include_en=include_en,
                          include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,
                          number_pages=number_pages, drop_junk_en=False,
                          want_toc=want_toc, want_footnotes=want_footnotes, title=title)
    os.makedirs(dest, exist_ok=True)
    suffix = f"_{hi_lang}" if (include_hi and not include_en) else ("_tri" if include_hi else "")
    out_path = os.path.join(dest, f"{_safe_filename(doc or 'export')}_{lo}-{hi}{suffix}.html")
    lang_attr = hi_lang if (include_hi and not include_en) else "en"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_html(title or (doc or "Export"), body, lang_attr=lang_attr))
    if debug: print(f"[export] wrote {out_path} | recs={len(recs)} | san='{san_col}' en='{en_col}' hi='{hi_lang}'")
    return out_path

def _list_docs(con):
    t = _tables(con)
    if "docs" in t and {"id","code"}.issubset(_colnames(con, "docs")):
        return [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code").fetchall()]
    pc = _colnames(con, "passages")
    if "doc" in pc:      return [r[0] for r in con.execute("SELECT DISTINCT doc FROM passages ORDER BY doc").fetchall()]
    if "doc_code" in pc: return [r[0] for r in con.execute("SELECT DISTINCT doc_code FROM passages ORDER BY doc_code").fetchall()]
    return []

def main():
    ap = argparse.ArgumentParser(description="Export scholarly HTML from Sanskrit Automaton DBs (v5)")
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
    ap.add_argument("--hindi", action="store_true", help="Include the Hindi column.")
    ap.add_argument("--hindi-only", action="store_true", help="Export Hindi only.")
    ap.add_argument("--lang", default=None, help="Localized language code (default 'hi').")
    ap.add_argument("--no-toc", action="store_true", help="Omit the table of contents.")
    ap.add_argument("--no-footnotes", action="store_true", help="Keep [bracketed] notes inline.")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    hi_lang = None; hi_label = "Hindi"
    if args.hindi or args.hindi_only:
        hi_lang = (args.lang or "hi").strip()
        hi_label = "हिन्दी" if hi_lang == "hi" else hi_lang
    include_san = bool(args.sanskrit and not args.no_sanskrit)
    include_en  = not args.hindi_only
    side_by_side = bool(args.side_by_side and (include_san or (hi_lang and include_en)))
    number_pages = not args.no_pagenum
    drop_junk_en = not args.keep_junk
    want_toc = not args.no_toc
    want_footnotes = not args.no_footnotes

    if not os.path.exists(args.db): raise SystemExit(f"DB not found: {args.db}")
    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        if args.all:
            docs = _list_docs(con)
            if not docs: raise SystemExit("Could not discover any docs in DB.")
            print(f"Found {len(docs)} docs. Exporting…")
            for code in docs:
                lo,hi = _page_span(con, code)
                _export_one(con, doc=code, lo=lo, hi=hi, title=args.title, dest=args.out,
                            include_san=include_san, include_en=include_en, side_by_side=side_by_side,
                            number_pages=number_pages, drop_junk_en=drop_junk_en,
                            force_san=args.san_col, force_en=args.en_col, hi_lang=hi_lang,
                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug)
        else:
            if args.doc:
                lo,hi = (_page_span(con, args.doc) if (args.pg_from is None or args.pg_to is None) else (args.pg_from, args.pg_to))
            else:
                pg = _page_col(con); row = con.execute(f"SELECT MIN({pg}), MAX({pg}) FROM passages").fetchone()
                lo = int(row[0]) if row and row[0] is not None else 1
                hi = int(row[1]) if row and row[1] is not None else lo
            _export_one(con, doc=args.doc, lo=lo, hi=hi, title=args.title, dest=args.out,
                        include_san=include_san, include_en=include_en, side_by_side=side_by_side,
                        number_pages=number_pages, drop_junk_en=drop_junk_en,
                        force_san=args.san_col, force_en=args.en_col, hi_lang=hi_lang,
                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug)

if __name__ == "__main__":
    main()
