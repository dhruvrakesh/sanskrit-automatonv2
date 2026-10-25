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
        # EXPORT_EMPTY_2026_10_07: qualified. translations_l10n is joined to passages, which has the same
        # three columns; unqualified they were ambiguous and the Hindi line of the title page vanished.
        eng_col = "p.engine" if "engine" in _colnames(con, table) else "NULL"
        pv_col  = "p.mt_prompt_version" if "mt_prompt_version" in _colnames(con, table) else "NULL"
        qa_col  = "p.translation_qa" if "translation_qa" in _colnames(con, table) else "NULL"
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

def _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=None, keep_frontmatter=False):
    pg = _page_col(con); idx_sel, idx_order = _idx_expr(con)
    pcols = _colnames(con, "passages")
    vref = "p.verse_ref" if "verse_ref" in pcols else "NULL"
    chap = "p.chapter"   if "chapter"   in pcols else "NULL"
    iast = "p.iast"      if "iast"      in pcols else "NULL"
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {pg} BETWEEN ? AND ?"; prm = prm + (lo,hi)
    # EXPORT_TEXTTYPE_2026_09_13
    # Every other consumer of this table filters here and this one did not,
    # so AphorismsOfSandilya shipped a Harvard bookplate and an 1861 title
    # page as Sanskrit verse. The classifier had already marked them
    # frontmatter. Same predicate as db_utils, dashboard/library,
    # build_embeddings and the diag_* scripts - colophon is deliberately
    # kept, being apparatus rather than scaffolding.
    if "text_type" in pcols and not keep_frontmatter:
        where += " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
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
    """Apply to HTML-escaped translation text. The śloka/pāda markers may be
    followed by a NEWLINE (multi-śloka passages store "//\\nText"), so use
    whitespace-tolerant regexes rather than literal " // "."""
    s = re.sub(r"\s*//+\s*$", "", escaped)      # trailing "//"
    s = re.sub(r"\s*//+\s*", " — ", s)           # internal half-verse breaks (any whitespace)
    s = re.sub(r"\s+/\s+", " — ", s)             # single pāda slash (spaced; leaves and/or intact)
    s = re.sub(r"\s+", " ", s)                   # collapse newlines/runs to single spaces
    s = _EM_RE.sub(r"<em>\1</em>", s)            # *term* -> italics (Debroy convention)
    return s.strip()

def _extract_footnotes(text_escaped: str, counter: List[int], notes: List[Tuple[int,str]]):
    """text_escaped is HTML-escaped. Replace substantive [notes] with numbered
    <sup> markers; keep trivial single-word glosses inline as (parentheticals).

    Debroy reserves footnotes for editorial clarifications, not one-word
    synonyms. Observed noise (2026-08-02): single-word bracket-glosses like
    [lake], [current], [तीर्थ] were flooding the apparatus — those now render
    inline, and only multi-word notes become footnotes."""
    def repl(m):
        inner = m.group(1).strip()
        if inner.lower() in _SKIP_BRACKET:
            return m.group(0)  # keep [ILLEGIBLE]/[अस्पष्ट] literal
        if len(inner.split()) < 2:
            return f"({inner})"   # trivial gloss stays inline, not a footnote
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

def _display_title(title, doc):
    """EXPORT_EMPTY_2026_10_07: the dashboard and the pipeline pass '<doc code> - English Translation', so
    the title page showed the raw code (siddhanta_shiromani). The code is replaced by the curated title in
    configs/doc_titles.json, else by the code made readable. A title without the code is kept as given."""
    if not title or not doc or not title.startswith(doc):
        return title
    nice = None
    try:
        import collections_cfg as _cc
        nice = _cc.load_titles().get(doc)
    except Exception:
        nice = None
    return (nice or doc.replace("_", " ").title()) + title[len(doc):]

def _safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", s.strip()); s = re.sub(r"_+","_", s); return s.strip("._")

# --- scholarly render --------------------------------------------------------

_NUMERIC_CH_RE = re.compile(r"^[0-9]+([.\-–][0-9]+)*$")

def _section_key(rec):
    """Group by chapter ONLY when the chapter value is a clean numeric label.
    OCR-sourced docs sometimes carry a garbage chapter value (e.g. "पर्व"),
    which must never become an "Adhyāya <garbage>" heading — fall back to page
    grouping in that case (2026-08-02)."""
    ch = rec.get("chap")
    if ch not in (None, "", "None"):
        chs = str(ch).strip()
        if _NUMERIC_CH_RE.match(chs):
            return ("chapter", chs)
    return ("page", str(rec.get("page")))

def _render(doc, recs, prov, *, include_san, include_en, include_hi, hi_label,
            side_by_side, number_pages, drop_junk_en, want_toc=True, want_footnotes=True,
            title=None, figures=None, prose=False):   # EXPORT_IMAGES_2026_10_04: figures; PROSE_EDITION_2026_10_25: prose
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
    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        subtitle = "The scholarly English" + (", with the Sanskrit" if include_san else "") + (
            " and the working " + hi_label if include_hi else "")
        if prose:   # PROSE_EDITION_2026_10_25
            subtitle = "The scholarly English, read as prose"
    out.append("<div class='titlepage'>")
    out.append(f"<h1>{html.escape(disp_title)}</h1>")
    if subtitle.strip(): out.append(f"<div class='subtitle'>{html.escape(subtitle)}</div>")
    pv = []
    if prov.get("source"):   pv.append(f"<b>Source:</b> {html.escape(str(prov['source']))}")
    if prov.get("category"): pv.append(f"<b>Category:</b> {html.escape(str(prov['category']))}")
    en, loc = prov.get("en") or {}, prov.get("loc") or {}
    if include_en and en.get("count"):
        pv.append(("<b>Working English:</b> " if prov.get("scholar") is not None else "<b>English:</b> ")   # SCHOLAR_EDITION_2026_10_17
                  + f"{en['count']} verses"
                  + (f", engine {html.escape(str(en.get('engine')))}" if en.get('engine') else "")
                  + (f", prompt {html.escape(str(en.get('prompt')))}" if en.get('prompt') else "")
                  + (f", mean QA {en.get('qa')}" if en.get('qa') is not None else ""))
    if include_hi and loc.get("count"):
        pv.append(f"<b>{html.escape(hi_label)}:</b> {loc['count']} verses"
                  + (f", engine {html.escape(str(loc.get('engine')))}" if loc.get('engine') else "")
                  + (f", prompt {html.escape(str(loc.get('prompt')))}" if loc.get('prompt') else "")
                  + (f", mean QA {loc.get('qa')}" if loc.get('qa') is not None else ""))
    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        pv.append(_sch_prov(prov["scholar"]))
    if pv:
        out.append("<div class='prov'>" + "<br/>".join(pv) + "</div>")
    _meth_at = len(out)   # SCHOLAR_EDITION_2026_10_17: the methodology's place, for the scholarly edition's own
    out.append("<div class='methodology'>Machine translation produced by the Sanskrit "
               "Automaton pipeline (context-aware, verse-by-verse) in the tradition of "
               "Bibek Debroy's critical-edition renderings. Italicized words are "
               "untranslated Sanskrit technical terms; bracketed clarifications appear "
               "as numbered footnotes. Verse references follow the source numbering "
               "(e.g. 1.1.0 is the benedictory maṅgala verse; star-passages excluded by "
               "the critical edition are omitted). A scholar's reading edition, not a "
               "substitute for the critical text.</div>")
    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        out[_meth_at] = _sch_meth(prov["scholar"])
    out.append("</div>")

    # EXPORT_EMPTY_2026_10_07: a section whose rows all have nothing to show in the chosen languages
    # used to keep its heading and its line in the contents (an untranslated text exported as 180
    # empty "Page N" headings). It is left out, unless an approved picture is anchored on its pages.
    def _shows(r):
        en_ = (r["en"] or "").strip()
        if include_en and drop_junk_en and _is_junk_en(en_):
            en_ = ""
        return bool((include_san and (r["san"] or "").strip()) or (include_en and en_)
                    or (include_hi and (r["loc"] or "").strip()))
    _fig_pages = {k[0] for k in (figures or {})}
    sections = OrderedDict((k, v) for k, v in sections.items()
                           if any(_shows(r) for r in v) or any(r["page"] in _fig_pages for r in v))

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
        paras, cur_p = [], []   # PROSE_EDITION_2026_10_25
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
                if r.get("sch") is not None:   # SCHOLAR_EDITION_2026_10_17
                    return _sch_en_html(en, r["sch"], fn_counter, fn_notes, want_footnotes)
                base = _inline_format(html.escape(en))
                return _extract_footnotes(base, fn_counter, fn_notes) if want_footnotes else base
            def _hi_html():
                base = _inline_format(html.escape(loc))
                # Hindi bracket-notes get footnoted too (36 such rows in MBh01);
                # they share the section's footnote numbering with English.
                return _extract_footnotes(base, fn_counter, fn_notes) if want_footnotes else base
            if prose:   # PROSE_EDITION_2026_10_25: the verses run on as a book's paragraphs, a speaker opening one
                sch_ = r.get("sch")
                if not (include_en and en) or (sch_ or {}).get("with"):
                    continue
                num = str(vref).split(".")[-1] if vlabel else ""   # a line without a reference has no number
                if sch_ is not None and sch_.get("range"):
                    num = str(sch_["range"]).split(".")[-1]
                    sch_ = dict(sch_, range="")
                body_ = (_sch_en_html(en, sch_, fn_counter, fn_notes, want_footnotes) if sch_ is not None
                         else _inline_format(html.escape(en)))
                if cur_p and (_PROSE_SPEECH.match(en) or len(cur_p) >= 8):
                    paras.append(cur_p)
                    cur_p = []
                cur_p.append(("<span class='vr'>%s</span>" % html.escape(num) if num else "") + body_)
                kept += 1
                continue
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
            if figures:   # EXPORT_IMAGES_2026_10_04: right after the anchored verse
                for _fg in figures.pop(_fig_key(r["page"], r["idx"]), []):
                    out.append(_figure_html(_fg, include_en, include_hi))
        if figures:   # anchors whose verse was filtered out: end of the section holding the page
            _pages = {_fig_key(x["page"], 0)[0] for x in rows}
            for _k in sorted((k for k in list(figures) if k[0] in _pages), key=str):
                for _fg in figures.pop(_k):
                    _fg["_late"] = True
                    out.append(_figure_html(_fg, include_en, include_hi))
        if prose:   # PROSE_EDITION_2026_10_25
            if cur_p:
                paras.append(cur_p)
            out.extend("<p class='prose'>%s</p>" % " ".join(p_) for p_ in paras)
        # footnotes for this section
        if want_footnotes and fn_notes:
            out.append("<div class='footnotes'><ol>")
            for n, note in fn_notes:
                out.append(f"<li id='fn-{n}'>{_note_html(note)} "   # EDITION_REFS_2026_10_18: *terms* in italics
                           f"<a href='#fnr-{n}' class='fn-ref'>&#8617;</a></li>")
            out.append("</ol></div>")
        out.append("</section>")
    if kept == 0:   # EXPORT_EMPTY_2026_10_07: say what is missing
        want = [x for x, on in (("English", include_en), (hi_label, include_hi), ("Sanskrit", include_san)) if on]
        out.append("<p class='note'>Nothing to show yet: no passage in this range has %s text%s.</p>"
                   % (html.escape(" or ".join(want) or "any"),
                      "" if include_san else " (an export with --sanskrit shows the Sanskrit)"))
    return "\n".join(out), kept

# --- EXPORT_IMAGES_2026_10_04: approved images as figures (opt-in) -----------
_FIG_LABEL_EN = "Illustration - generated, not a historical source."
_FIG_LABEL_HI = "\u091a\u093f\u0924\u094d\u0930\u0923 - \u0915\u0943\u0924\u094d\u0930\u093f\u092e \u0930\u0942\u092a \u0938\u0947 \u0928\u093f\u0930\u094d\u092e\u093f\u0924, \u0910\u0924\u093f\u0939\u093e\u0938\u093f\u0915 \u0938\u094d\u0930\u094b\u0924 \u0928\u0939\u0940\u0902\u0964"
_FIG_CSS = (
    "figure.plate { margin: 1.6rem auto 2rem; max-width: 36rem; text-align: center; break-inside: avoid; }"
    "figure.plate img { max-width: 100%; max-height: 70vh; border: 1px solid var(--rule); border-radius: 3px; }"
    "figure.plate figcaption { font-size: .84rem; color: var(--muted); margin-top: .5rem; line-height: 1.6; text-align: left; }"
    "figure.plate figcaption b { color: var(--ink); }"
    "figure.plate .plate-hi { font-family: 'Noto Sans Devanagari','Nirmala UI','Mangal',serif; }"
    "figure.plate .plate-note { display: block; margin-top: .3rem; }"
    "figure.plate .plate-label { display: block; margin-top: .3rem; font-style: italic; font-size: .76rem; }"
    "@media print { figure.plate { break-inside: avoid; page-break-inside: avoid; }"
    " figure.plate img { max-height: 150mm; } }"
)


def _fig_key(page, idx):
    try:
        return (int(page), int(idx))
    except (TypeError, ValueError):
        return (page, idx)


def _fig_embed(path: str):
    """data: URI for the image file, or None when it cannot be read."""
    import base64, io
    try:
        raw = open(path, "rb").read()
    except OSError:
        return None
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            im.thumbnail((1400, 1400))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=84, optimize=True)
            raw, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        ext = os.path.splitext(path)[1].lower()
        mime = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


def _load_figures(con, doc, root=None):
    """{(page, idx): [figure dict, ...]} for the doc's APPROVED images. Empty when
    the doc_images table does not exist yet (no image library) or nothing is approved."""
    if not doc or "doc_images" not in _tables(con):
        return {}
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = con.execute(
        """SELECT i.id, i.version, i.kind, i.title, i.caption_en, i.caption_hi, i.context_note,
                  i.path, i.anchor_page, i.anchor_idx
           FROM doc_images i JOIN docs d ON d.id = i.doc_id
           WHERE d.code = ? AND i.status = 'approved' AND i.path IS NOT NULL
             AND COALESCE(i.kind, '') <> 'cover'   -- COVERS_2026_10_04: the cover goes on the title page
           ORDER BY i.anchor_page, i.anchor_idx, i.id""", (doc,)).fetchall()
    out = {}
    for (iid, ver, kind, title, cen, chi, note, path, pg, ix) in rows:
        full = path if os.path.isabs(path) else os.path.join(root, path)
        uri = _fig_embed(full)
        if not uri:
            print("[export] image #%s skipped: file not found (%s)" % (iid, full))
            continue
        out.setdefault(_fig_key(pg, ix), []).append(
            {"id": iid, "version": ver, "kind": kind or "", "title": title or "", "caption_en": cen or "",
             "caption_hi": chi or "", "note": note or "", "uri": uri, "page": pg, "idx": ix})
    _attach_stories(con, out)   # VIGNETTES_2026_10_05
    return out


def _attach_stories(con, figs):
    """VIGNETTES_2026_10_05: an APPROVED story (scripts/stories.py) linked to an image placed
    here is printed under that image. No doc_stories table, or no approved story: no change."""
    if not figs or "doc_stories" not in _tables(con):
        return
    ids = [fg["id"] for v in figs.values() for fg in v]
    got = {}
    for iid, en, hi, q, qr in con.execute(
            "SELECT image_id, story_en, story_hi, quote_sa, quote_ref FROM doc_stories "
            "WHERE status = 'approved' AND image_id IN (%s) ORDER BY approved_at" % ",".join("?" * len(ids)), ids):
        got[iid] = {"en": en or "", "hi": hi or "", "q": q or "", "qr": qr or ""}
    for v in figs.values():
        for fg in v:
            if fg["id"] in got:
                fg["story"] = got[fg["id"]]


def _story_html(st, include_en, include_hi):
    """VIGNETTES_2026_10_05: the retelling under a plate, citations as superscripts."""
    if not st:
        return ""
    import re as _re
    def _cite(t):
        return _re.sub(r"\[([^\]]*\d+\.\d+[^\]]*)\]", r"<sup class='cite'>[\1]</sup>", html.escape(t))
    parts = []
    if st.get("q"):
        parts.append("<div class='plate-story-sa'>%s <span class='plate-label'>[%s]</span></div>"
                     % (html.escape(st["q"]), html.escape(st.get("qr") or "")))
    if include_en and st.get("en"):
        parts.append("<div>%s</div>" % _cite(st["en"]))
    if include_hi and st.get("hi"):
        parts.append("<div class='plate-hi'>%s</div>" % _cite(st["hi"]))
    if not parts:
        return ""
    return ("<div class='plate-story' style='text-align:left;font-size:.92em;max-width:40rem;margin:.6rem auto'>%s"
            "<div class='plate-label'>Retold from the passages cited; drafted by a model, approved by an editor."
            "</div></div>" % "".join(parts))


def _fig_copy(figs):
    return {k: list(v) for k, v in (figs or {}).items()}


def _figure_html(fg, include_en, include_hi):
    cap = []
    if fg["title"]:
        cap.append("<b>%s</b>" % html.escape(fg["title"]))
    if include_en and fg["caption_en"]:
        cap.append(html.escape(fg["caption_en"]))
    if include_hi and fg["caption_hi"]:
        cap.append("<span class='plate-hi'>%s</span>" % html.escape(fg["caption_hi"]))
    if not include_en and not (include_hi and fg["caption_hi"]) and fg["caption_en"]:
        cap.append(html.escape(fg["caption_en"]))
    if include_en and fg["note"]:
        cap.append("<span class='plate-note'>%s</span>" % html.escape(fg["note"]))
    if fg["kind"] == "generated":
        lab = _FIG_LABEL_EN if include_en or not include_hi else _FIG_LABEL_HI
        if include_en and include_hi:
            lab = _FIG_LABEL_EN + " / " + _FIG_LABEL_HI
        cap.append("<span class='plate-label'>%s</span>" % html.escape(lab))
    elif fg["kind"] == "edition-plate":
        cap.append("<span class='plate-label'>Plate from the source edition.</span>")
    alt = html.escape(fg["title"] or "illustration", quote=True)
    _st = _story_html(fg.get("story"), include_en, include_hi)   # VIGNETTES_2026_10_05
    return ("<figure class='plate' id='img-%s' data-kind='%s'><img src='%s' alt='%s'/>"
            "<figcaption>%s</figcaption>%s</figure>"
            % (fg["id"], html.escape(fg["kind"], quote=True), fg["uri"], alt, " ".join(cap), _st))


def _load_cover(con, doc, root=None):
    """COVERS_2026_10_04: the newest APPROVED cover (kind='cover') as a figure for the title page, or ''."""
    if not doc or "doc_images" not in _tables(con):
        return ""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = con.execute("""SELECT i.id, i.title, i.path FROM doc_images i JOIN docs d ON d.id = i.doc_id
                       WHERE d.code = ? AND i.status = 'approved' AND i.kind = 'cover' AND i.path IS NOT NULL
                       ORDER BY i.approved_at DESC, i.id DESC LIMIT 1""", (doc,)).fetchone()
    if not r:
        return ""
    full = r[2] if os.path.isabs(r[2]) else os.path.join(root, r[2])
    uri = _fig_embed(full)
    if not uri:
        return ""
    return ("<figure class='plate cover' id='cover-%s' style='max-width:24rem'><img src='%s' alt='%s'/>"
            "<figcaption><span class='plate-label'>%s</span></figcaption></figure>"
            % (r[0], uri, html.escape(r[1] or "cover", quote=True), html.escape(_FIG_LABEL_EN)))


def _with_fig_css(doc_html, on):
    return doc_html.replace("</style>", _FIG_CSS + "</style>", 1) if on else doc_html


# --- EDITION_REFS_2026_10_18: an e-text's own references for its chapters and its sentences ----------
_REF2_RE = re.compile(r"^\D*?(\d+)\.(\d+)$")
_ITI = "\u0907\u0924\u093f"


def _ref_chapters(recs):
    """EDITION_REFS_2026_10_18: in an e-text whose verses carry their own two-part references (GRETIL's 81.1), the
    chapter is the reference's, not the file's headings (the GRETIL Markandeya's speaker lines carried "77" within
    adhyaya 81). A passage without a reference goes with the next verse that has one (a heading, a speaker's line), a
    colophon (iti ...) with the one before. Only when half or more of the passages that show Sanskrit have such a reference; three-part
    references (MBh 1.1.8) and texts without references are left as they were."""
    chs = []
    for r in recs:
        m = _REF2_RE.match(str(r.get("vref") or "").strip())
        chs.append(m.group(1) if m else None)
    shown = [c for r, c in zip(recs, chs) if (r.get("san") or "").strip()]
    if not shown or sum(1 for c in shown if c) < 0.5 * len(shown):
        return recs
    after, nxt = [None] * len(recs), None
    for i in range(len(recs) - 1, -1, -1):
        if chs[i]:
            nxt = chs[i]
        after[i] = nxt
    prev = None
    for i, r in enumerate(recs):
        if chs[i]:
            prev = r["chap"] = chs[i]
            continue
        san = (r.get("san") or "").strip()
        if prev and (san.startswith(_ITI) or after[i] is None):
            r["chap"] = prev
        elif after[i]:
            r["chap"] = after[i]
    return recs


def _own_range(u, pref):
    """EDITION_REFS_2026_10_18: a sentence's range from its verses' own references, so that one begun by a speaker's line
    (no reference of its own) is not labelled by that line's page.idx ("628.1-18"); ST._range when none has one."""
    import scholar_translate as ST
    refs = [pref.get(r.get("passage_id")) for r in u]
    refs = [x for x in refs if x]
    if not refs:
        return ST._range(u)
    a_, b_ = refs[0], refs[-1]
    return a_ if a_ == b_ else "%s\u2013%s" % (a_, b_.split(".")[-1])


# --- SCHOLAR_EDITION_2026_10_17: the scholarly English as an edition ----------
# Asked on 17 Oct for "authoritative and scholarly books from our corpus in our good html format like ganita
# yuktibhasa": this exporter's edition (the Sanskrit, its IAST, the English, the notes at each chapter's end), with
# the scholarly English (scripts/scholar_translate.py) in place of the working English. Per verse: its latest row
# (as /scholar/<doc>/prose reads it), kept only while the Sanskrit it was made from is the Sanskrit here (its
# src_hash); a sentence made over several verses stands once, after its verse range, the verses after it saying so;
# its notes become the chapter's numbered notes, its doubts about the reading too. A verse a person rejected, or with
# no current scholarly English, shows the working English, marked as such. A verse flagged by the judge or doubted
# for its reading, and not yet accepted by a person, carries a dagger. Read only: nothing is written but the file.

_SCH_CSS = (".sch-flag { color: #a0522d; font-size: .8em; margin-left: .15em; cursor: help; }"
            ".sch-rng { font-size: .72rem; color: var(--muted); font-family: 'JetBrains Mono',ui-monospace,monospace; "
            "margin-right: .35em; }"
            ".sch-wk { color: #555; }"
            ".sch-wk::before { content: 'working English, a draft: '; font-size: .72rem; color: var(--muted); "
            "font-style: italic; }"
            ".sch-with { color: var(--muted); font-style: italic; font-size: .85rem; }")


# PROSE_EDITION_2026_10_25: the scholarly edition read as prose (--scholar --prose), as the desk's /scholar/<doc>/prose
# reads it: no Sanskrit, the verse numbers small, a sentence over verses whole, a paragraph where a speaker begins (or
# after eight verses), the chapter's notes at its end; the chapters, the notes, the daggers and the title page are the
# edition's own.
_PROSE_CSS = ("p.prose { text-align: justify; line-height: 1.9; margin: 0 0 1.1rem; }"
              "p.prose .vr { font-size: .62rem; color: var(--muted); vertical-align: super; margin: 0 .2em 0 .15em; "
              "font-family: 'JetBrains Mono',ui-monospace,monospace; }")
_PROSE_SPEECH = re.compile(r"^[A-Z][^.:;]{0,60} said:")   # scholar_translate.py _SPEECH


def _sch_meth(stats: dict) -> str:
    """The title page's methodology, for the scholarly edition."""
    return ("<div class='methodology'>The scholarly English of the Sanskrit Automaton (scholar_translate.py): each "
            "verse translated afresh from the Sanskrit given here, in the register of an unabridged translation made "
            "from a critical edition, with the verses around it and a glossary kept across the text; at most three "
            "notes a verse, at the end of each chapter, with the translator's doubts about the reading. A critic "
            "reads each draft, which is revised where it finds a fault; a judge reads every verse; the models are "
            "named above. A verse marked &#8224; was flagged by the judge or doubted for its reading and has not yet "
            "been read by a person. Square brackets hold a word the Sanskrit implies; italics, an untranslated term. "
            "A verse with no current scholarly English shows the working English (one pass), marked as a draft. A "
            "machine translation, to be read beside the Sanskrit and checked by a person: not a substitute for the "
            "critical text.</div>")


def _sch_prov(stats: dict) -> str:
    """The title page's line on the scholarly English."""
    if not stats.get("verses"):
        return ("<b>Scholarly English:</b> none current for this text%s; every verse shows the working English."
                % ((" (%d rejected by a person)" % stats["rejected"]) if stats.get("rejected") else " yet"))
    eng = ", ".join("%s (%d)" % (html.escape(str(k)), v) for k, v in sorted(stats["engines"].items(), key=lambda kv: -kv[1]))
    jud = ", ".join(html.escape(str(k)) for k in sorted(stats["judges"]))
    pv = ", ".join(html.escape(str(k)) for k in sorted(stats["prompts"]))
    return ("<b>Scholarly English:</b> %d of %d verses (passed %d, flagged %d, doubted for the reading %d; accepted by a "
            "person %d, rejected %d%s); made by %s; judged by %s; prompt %s.%s"
            % (stats["verses"], stats["shown"], stats["passed"], stats["flagged"], stats["doubt"], stats["accepted"],
               stats["rejected"], ("; %d left out, their Sanskrit changed since" % stats["stale"]) if stats["stale"] else "",
               eng or "-", jud or "-", pv or "-",
               (" The working English stands for %d other verse(s), marked." % stats["working"]) if stats["working"] else ""))


def _scholar_recs(con, doc, recs):
    """(recs, stats): each record's English replaced by its scholarly English where there is a current one."""
    import scholar_translate as ST
    stats = {"verses": 0, "shown": len(recs), "passed": 0, "flagged": 0, "doubt": 0, "accepted": 0, "rejected": 0,
             "stale": 0, "working": 0, "engines": {}, "judges": set(), "prompts": set()}
    if not doc or "scholar_translations" not in _tables(con):
        for r in recs:
            r["sch"] = {"working": True}
        stats["working"] = len(recs)
        return recs, stats
    ptext, pkey = {}, {}
    pref = {}   # EDITION_REFS_2026_10_18: each passage's own reference
    if "verse_ref" in _colnames(con, "passages"):
        for pid_, vr_ in con.execute("SELECT p.id, p.verse_ref FROM passages p JOIN docs d ON d.id = p.doc_id "
                                     "WHERE d.code = ?", (doc,)):
            if vr_ not in (None, ""):
                pref[pid_] = str(vr_).strip()
    for pid, pg, ix, tx in con.execute("SELECT p.id, p.page_no, p.idx, p.text FROM passages p JOIN docs d ON d.id = p.doc_id "
                                       "WHERE d.code = ?", (doc,)):
        ptext[pid] = tx
        try:
            pkey[(int(pg), int(ix))] = pid
        except (TypeError, ValueError):
            pkey[(pg, ix)] = pid
    cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM "
                      "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY page_no, idx, id", (doc, doc))
    names = [d_[0] for d_ in cur.description]
    rows = [dict(zip(names, tuple(x))) for x in cur.fetchall()]
    live = []
    for r in rows:
        t = ptext.get(r.get("passage_id"))
        if t is not None and ST.src_hash(t) == r.get("src_hash"):
            live.append(r)
        else:
            stats["stale"] += 1
    by_pid = {}
    for u in ST._units(live):
        r0 = u[0]
        notes = [n for n in ST._loads(r0.get("notes"), []) if isinstance(n, dict)]
        doubt = str(r0.get("doubts") or "").strip()
        flag = r0.get("status") in ("flagged", "source_doubt") and r0.get("review_verdict") != "accept"
        inline = ST._inline(u)
        rng = _own_range(u, pref) if len(u) > 1 else ""   # EDITION_REFS_2026_10_18
        for k, r in enumerate(u):
            meta = {"status": r0.get("status"), "flag": flag, "rejected": r0.get("review_verdict") == "reject",
                    "accepted": r.get("review_verdict") == "accept", "engine": str(r.get("engine") or "?"),
                    "judge": str(r.get("judge_engine") or ""), "prompt": str(r.get("prompt_version") or "")}
            if inline:
                meta.update(text=r.get("translation") or "", notes=notes if k == 0 else [], doubts=doubt if k == 0 else "")
            elif k == 0:
                meta.update(text=r0.get("group_translation") or r0.get("translation") or "", notes=notes, doubts=doubt,
                            range=rng)
            else:
                meta.update({"with": rng})
            by_pid[r["passage_id"]] = meta
    for rec in recs:
        try:
            pid = pkey.get((int(rec["page"]), int(rec["idx"])))
        except (TypeError, ValueError):
            pid = pkey.get((rec["page"], rec["idx"]))
        s = by_pid.get(pid)
        if s is not None and s.get("rejected"):
            stats["rejected"] += 1
            s = None
        if s is None or (not s.get("with") and not (s.get("text") or "").strip()):
            rec["sch"] = {"working": True}
            if (rec.get("en") or "").strip():
                stats["working"] += 1
            continue
        rec["sch"] = s
        rec["en"] = ("with " + s["with"]) if s.get("with") else re.sub(r"\s*//\s*", " ", s["text"]).strip()
        stats["verses"] += 1
        stats["passed"] += 1 if s["status"] == "passed" else 0
        stats["flagged"] += 1 if s["status"] == "flagged" else 0
        stats["doubt"] += 1 if s["status"] == "source_doubt" else 0
        stats["accepted"] += 1 if s["accepted"] else 0
        stats["engines"][s["engine"]] = stats["engines"].get(s["engine"], 0) + 1
        if s["judge"]:
            stats["judges"].add(s["judge"])
        if s["prompt"]:
            stats["prompts"].add(s["prompt"])
    return recs, stats


def _note_html(note):
    # EDITION_REFS_2026_10_18: a chapter's note as printed: escaped, a *term* in italics as in the English
    return _EM_RE.sub(r"<em>\1</em>", html.escape(note))


def _note_at(s, raw_a):
    # EDITION_REFS_2026_10_18: (position, form) of a note's anchor in a verse's English as printed (escaped, *terms* in
    # italics), or (-1, '')
    if not raw_a:
        return -1, ""
    for a in (html.escape(raw_a), _inline_format(html.escape(raw_a)), html.escape(raw_a.replace("*", ""))):
        if a:
            p = s.find(a)
            if p >= 0:
                return p, a
    return -1, ""


def _sch_en_html(en, sch, counter, notes_out, want_footnotes=True):
    """The scholarly English of a verse: italics for *terms*, each note's number after its anchor's first appearance,
    the dagger of a verse not yet read by a person; the working English marked as a draft."""
    if sch.get("working"):
        base = _inline_format(html.escape(en))
        base = _extract_footnotes(base, counter, notes_out) if want_footnotes else base
        return "<span class='sch-wk'>%s</span>" % base
    if sch.get("with"):
        return "<span class='sch-with'>Its English is given with %s, above.</span>" % html.escape(sch["with"])
    s = _inline_format(html.escape(en))
    if want_footnotes:
        # EDITION_REFS_2026_10_18: the notes numbered in the order their anchors are read (they came in the order the
        # translator listed them: 1, 4, 3, 2 in the Devimahatmya's first sentence), an italic *term* found as printed;
        # a note whose anchor is not found comes last
        placed = []
        for j, n in enumerate(sch.get("notes") or []):
            pos, a = _note_at(s, str(n.get("anchor") or "").strip())
            placed.append((pos if pos >= 0 else len(s) + 1 + j, j, n, pos, a))
        placed.sort(key=lambda t: (t[0], t[1]))
        marks = []
        for _o, _j, n, pos, a in placed:
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "%s: %s" % (str(n.get("anchor") or "").strip(), str(n.get("note") or "").strip())))
            marks.append((pos + len(a) if pos >= 0 else -1, "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>"
                          % (k, k, k)))
        for i_, (p_, m_) in sorted(enumerate(marks), key=lambda t: (-t[1][0], -t[0])):
            if p_ >= 0:
                s = s[:p_] + m_ + s[p_:]
        s += "".join(m_ for p_, m_ in marks if p_ < 0)
        if sch.get("doubts"):
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "The reading: " + sch["doubts"]))
            s += "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>" % (k, k, k)
    if sch.get("range"):
        s = "<span class='sch-rng'>%s</span>%s" % (html.escape(sch["range"]), s)
    if sch.get("flag"):
        s += ("<span class='sch-flag' title='%s: not yet read by a person'>&#8224;</span>"
              % html.escape(str(sch.get("status") or "flagged").replace("_", " "), quote=True))
    return s


# --- export core -------------------------------------------------------------

def _export_one(con, *, doc, lo, hi, title, dest, include_san, include_en,
                side_by_side, number_pages, drop_junk_en, force_san, force_en,
                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False,
                keep_frontmatter=False, images="none", scholar=False,
                prose=False):   # SCHOLAR_EDITION_2026_10_17: scholar; PROSE_EDITION_2026_10_25: prose
    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07
    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)
    figs = _load_figures(con, doc) if images == "approved" else {}   # EXPORT_IMAGES_2026_10_04
    cover = _load_cover(con, doc) if images == "approved" else ""   # COVERS_2026_10_04
    _fig_total = sum(len(v) for v in figs.values())
    include_hi = bool(hi_lang)
    recs = _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=hi_lang,
                  keep_frontmatter=keep_frontmatter)
    prov = _provenance(con, doc, hi_lang)
    if scholar:   # SCHOLAR_EDITION_2026_10_17: the scholarly English in place of the working English
        recs, prov["scholar"] = _scholar_recs(con, doc, recs)
        recs = _ref_chapters(recs)   # EDITION_REFS_2026_10_18: an e-text's chapters from its own references
    body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,
                         include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,
                         number_pages=number_pages, drop_junk_en=drop_junk_en,
                         want_toc=want_toc, want_footnotes=want_footnotes, title=title,
                         figures=_fig_copy(figs) if figs else None, prose=prose)
    if kept == 0 and include_en and not include_san and drop_junk_en:
        body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,
                          include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,
                          number_pages=number_pages, drop_junk_en=False,
                          want_toc=want_toc, want_footnotes=want_footnotes, title=title,
                         figures=_fig_copy(figs) if figs else None, prose=prose)
    os.makedirs(dest, exist_ok=True)
    suffix = f"_{hi_lang}" if (include_hi and not include_en) else ("_tri" if include_hi else "")
    if scholar:   # SCHOLAR_EDITION_2026_10_17: never overwrite the working edition
        suffix += "_scholar"
    if prose:   # PROSE_EDITION_2026_10_25: never overwrite the verse edition
        suffix += "_prose"
    if images == "approved":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition
        suffix += "_img"
    out_path = os.path.join(dest, f"{_safe_filename(doc or 'export')}_{lo}-{hi}{suffix}.html")
    lang_attr = hi_lang if (include_hi and not include_en) else "en"
    with open(out_path, "w", encoding="utf-8") as f:
        if cover:   # COVERS_2026_10_04
            body = body.replace("<div class='titlepage'>", "<div class='titlepage'>" + cover, 1)
        _doc_html = _with_fig_css(_html(title or (doc or "Export"), body, lang_attr=lang_attr), bool(figs) or bool(cover))
        if scholar:   # SCHOLAR_EDITION_2026_10_17
            _doc_html = _doc_html.replace("</style>", _SCH_CSS + "</style>", 1)
        if prose:   # PROSE_EDITION_2026_10_25
            _doc_html = _doc_html.replace("</style>", _PROSE_CSS + "</style>", 1)
        f.write(_doc_html)
    if images == "approved":   # EXPORT_IMAGES_2026_10_04
        _n_in = body.count("<figure class='plate'")
        print(f"[export] images: {_fig_total} approved, {_n_in} placed, "
              f"{_fig_total - _n_in} outside pages {lo}-{hi}")
    if debug: print(f"[export] wrote {out_path} | recs={len(recs)} | san='{san_col}' en='{en_col}' hi='{hi_lang}'")
    if kept == 0:   # EXPORT_EMPTY_2026_10_07
        print(f"[export] WARNING {doc}: pages {lo}-{hi} have nothing to show in the chosen languages "
              f"({len(recs)} passages read); {out_path} holds only the title page and a note.")
    else:
        print(f"[export] wrote {out_path}: {kept} passage(s)")
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
    ap.add_argument("--keep-frontmatter", action="store_true",
                    help="EXPORT_TEXTTYPE_2026_09_13: keep rows classified "
                         "noise/frontmatter. Off by default; every other script "
                         "in this pipeline excludes them. A filter you cannot "
                         "switch off is one you cannot debug.")
    ap.add_argument("--en-col")
    ap.add_argument("--san-col")
    ap.add_argument("--title-from-doc", action="store_true")
    ap.add_argument("--hindi", action="store_true", help="Include the Hindi column.")
    ap.add_argument("--hindi-only", action="store_true", help="Export Hindi only.")
    ap.add_argument("--lang", default=None, help="Localized language code (default 'hi').")
    ap.add_argument("--no-toc", action="store_true", help="Omit the table of contents.")
    ap.add_argument("--no-footnotes", action="store_true", help="Keep [bracketed] notes inline.")
    ap.add_argument("--images", choices=["none", "approved"], default="none",
                    help="EXPORT_IMAGES_2026_10_04: approved = place approved images from the "
                         "image library at their verses (file name gains _img).")
    ap.add_argument("--scholar", action="store_true",
                    help="SCHOLAR_EDITION_2026_10_17: the scholarly English (scholar_translate.py) with its notes in "
                         "place of the working English, which stands, marked, where there is none (file name "
                         "gains _scholar)")
    ap.add_argument("--prose", action="store_true",
                    help="PROSE_EDITION_2026_10_25: with --scholar, the scholarly English read as prose: no Sanskrit, "
                         "the verse numbers small, the notes at each chapter's end (file name gains _prose)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    if args.prose and not args.scholar:   # PROSE_EDITION_2026_10_25
        raise SystemExit("--prose reads the scholarly English: give --scholar too")

    hi_lang = None; hi_label = "Hindi"
    if args.hindi or args.hindi_only:
        hi_lang = (args.lang or "hi").strip()
        hi_label = "हिन्दी" if hi_lang == "hi" else hi_lang
    include_san = bool(args.sanskrit and not args.no_sanskrit) and not args.prose   # PROSE_EDITION_2026_10_25
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
                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                            keep_frontmatter=args.keep_frontmatter, images=args.images,
                            scholar=args.scholar, prose=args.prose)   # SCHOLAR_EDITION_2026_10_17; PROSE_EDITION_2026_10_25
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
                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                        keep_frontmatter=args.keep_frontmatter, images=args.images,
                        scholar=args.scholar, prose=args.prose)   # SCHOLAR_EDITION_2026_10_17; PROSE_EDITION_2026_10_25

if __name__ == "__main__":
    main()
# IMAGE_QUALITY_2026_10_04
