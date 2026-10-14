#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_redeem_2026_10_14.py  (2026-10-14)  REDEEM_2026_10_14

Asked on 14 Oct: "substantial time and money and energy have gone into translating all these texts. What can be
redeemed and what cannot should be clearly marked." scripts/redeem.py (new, read-only) counts it, text by text and
passage by passage; scripts/retranslate_marked.py (new, T2) translates again what the judge marks, with the stronger
engine, and judges it again. This patch wires them in:
  dashboard.py (on a restart): each Library card says how much of its English is kept, in green, amber or red, and
    what the rest needs (a text not yet readable whose paid-for English a better reading replaced says that); the
    header counts the English kept; /redeem, the ledger text by text, with "Count again"; a link to it from the
    Library and /path.
  text_path.py: a text the judge marks (10% or more of its sample) has retranslate_marked.py as its NEXT, and the
    judge_sample.py line to judge more.
  .gitignore: data/redeem.json and data/retranslate/ stay local.

Needs PATH_2026_10_12 (dashboard.py), READ_IN_2026_10_13 (text_path.py), scripts/redeem.py and
scripts/retranslate_marked.py. Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and
encodings; each .py is compiled before it replaces the original; backups .bak_redeem_<date>.
  python scripts\\patch_redeem_2026_10_14.py --check
  python scripts\\patch_redeem_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REDEEM_2026_10_14"
NEEDS = {"scripts/dashboard.py": "PATH_2026_10_12", "scripts/text_path.py": "READ_IN_2026_10_13"}
FILES = list(NEEDS)
GITIGNORE_BLOCK = ("# REDEEM_2026_10_14: what of the translation is kept (scripts/redeem.py) and the T2 logs stay local\n"
                   "data/redeem.json\ndata/retranslate/\n")

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1,
     r'''                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed
                 "withdraw", "path_all")                    # PATH_2026_10_12: off the site; the path of every text
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness
''',
     r'''                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed
                 "withdraw", "path_all",                    # PATH_2026_10_12: off the site; the path of every text
                 "redeem_all")                              # REDEEM_2026_10_14: what of the translation is kept
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness
''')
edit('scripts/dashboard.py', 2,
     r'''                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...',   /* REINGEST_2026_10_12 */
                 withdraw: 'withdrawing it from the site...', path_all: 'charting the path of every text (a few minutes)...'};   /* PATH_2026_10_12 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''',
     r'''                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...',   /* REINGEST_2026_10_12 */
                 withdraw: 'withdrawing it from the site...', path_all: 'charting the path of every text (a few minutes)...',   /* PATH_2026_10_12 */
                 redeem_all: 'counting what of the translation is kept (free, a minute)...'};   /* REDEEM_2026_10_14 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''')
edit('scripts/dashboard.py', 3,
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|withdraw|as_is|accept|hold|release|translate|judge_all|benchmark_all|path_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''',
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|withdraw|as_is|accept|hold|release|translate|judge_all|benchmark_all|path_all|redeem_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''')
edit('scripts/dashboard.py', 4,
     r'''    listed = {d[0] for docs in cats.values() for d in docs}
    cards = ""
    for code, title, _cat, total, en in rows:
        if code in listed or not (notes.get(code) or code in aside):
''',
     r'''    listed = {d[0] for docs in cats.values() for d in docs}
    cards = ""
    rdm = _redeem()   # REDEEM_2026_10_14: a text paid for whose English a better reading replaced says so
    for code, title, _cat, total, en in rows:
        if code in listed or not (notes.get(code) or code in aside):
''')
edit('scripts/dashboard.py', 5,
     r'''            continue
        cards += ('<div class="card-wrap waiting"><div class="card"><div class="ttl">%s</div><div class="code">%s</div>'
                  '<div class="meta"><span class="badge en">EN %d/%d</span></div></div>%s</div>'
                  % (_html.escape(str(title)), _html.escape(str(code)), int(en or 0), int(total or 0), inner))
    if not cards:
        return ""
''',
     r'''            continue
        cards += ('<div class="card-wrap waiting"><div class="card"><div class="ttl">%s</div><div class="code">%s</div>'
                  '<div class="meta"><span class="badge en">EN %d/%d</span></div></div>%s%s</div>'
                  % (_html.escape(str(title)), _html.escape(str(code)), int(en or 0), int(total or 0),
                     _redeem_note(code, rdm), inner))   # REDEEM_2026_10_14
    if not cards:
        return ""
''')
edit('scripts/dashboard.py', 6,
     r'''    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step in ("judge_all", "benchmark_all", "path_all") else _validate_doc(data.get("doc"))   # PATH_2026_10_12: path_all   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
''',
     r'''    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step in ("judge_all", "benchmark_all", "path_all", "redeem_all") else _validate_doc(data.get("doc"))   # REDEEM_2026_10_14: redeem_all   # PATH_2026_10_12: path_all   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
''')
edit('scripts/dashboard.py', 7,
     r'''    elif step == "path_all":   # PATH_2026_10_12: free and read-only
        argv = [script("text_path.py"), "--from-dashboard"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
''',
     r'''    elif step == "path_all":   # PATH_2026_10_12: free and read-only
        argv = [script("text_path.py"), "--from-dashboard"]
    elif step == "redeem_all":   # REDEEM_2026_10_14: free and read-only
        argv = [script("redeem.py"), "--from-dashboard"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
''')
edit('scripts/dashboard.py', 8,
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + css + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><a href="/benchmarks">Benchmarks</a><h1>The path</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
''',
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + css + """
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
''')
edit('scripts/dashboard.py', 9,
     r'''        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500
    notes = _library_notes()   # DESK_HEAL_2026_10_10
    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside
    judged = _judged(pathlib.Path(db_path).parent)   # JUDGE_DESK_2026_10_11: the last assessments
''',
     r'''        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500
    notes = _library_notes()   # DESK_HEAL_2026_10_10
    rdm = _redeem()   # REDEEM_2026_10_14: what of each text's English is kept
    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside
    judged = _judged(pathlib.Path(db_path).parent)   # JUDGE_DESK_2026_10_11: the last assessments
''')
edit('scripts/dashboard.py', 10,
     r'''                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{hi_badge}{qa_badge}'
                f'<span class="pct">{pct}%</span></div></a>'
                f'{acts_html}</div>'
            )
        body += '</div>'
''',
     r'''                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{hi_badge}{qa_badge}'
                f'<span class="pct">{pct}%</span></div></a>'
                f'{_redeem_note(code, rdm)}{acts_html}</div>'   # REDEEM_2026_10_14
            )
        body += '</div>'
''')
edit('scripts/dashboard.py', 11,
     r'''{_REPAIR_CSS}
{_JUDGED_CSS}
/* BOOKSMITH_WIRING_2026_09_12 */
.card-wrap{{position:relative}}
''',
     r'''{_REPAIR_CSS}
{_JUDGED_CSS}
{_REDEEM_CSS}
/* BOOKSMITH_WIRING_2026_09_12 */
.card-wrap{{position:relative}}
''')
edit('scripts/dashboard.py', 12,
     r'''  <a class="back" href="/">&#8592; Dashboard</a>
  <h1>&#2384; Srangam Library</h1>
  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses</span>
  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/path" title="PATH_2026_10_12: the way forward for every text: repair, find a source, retire, translate, judge" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#129517; The path</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
''',
     r'''  <a class="back" href="/">&#8592; Dashboard</a>
  <h1>&#2384; Srangam Library</h1>
  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses{(" &middot; <a href='/redeem' style='color:var(--green);text-decoration:none' title='REDEEM_2026_10_14: what of the English is kept, and what is not'>" + format((rdm.get("totals") or {}).get("keep", 0), ",") + " kept</a>") if rdm else ""}</span>
  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/path" title="PATH_2026_10_12: the way forward for every text: repair, find a source, retire, translate, judge" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#129517; The path</a>
  <a class="back" href="/redeem" title="REDEEM_2026_10_14: what of the translation already paid for is kept, and what is not" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878; What is redeemed</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
''')
edit('scripts/text_path.py', 13,
     r'''DUP_SHARE = 0.5         # share of letter 4-grams two readings share: the same work
JUDGE_SAMPLE = 40
WITHDRAW_MISREAD = 5.0  # % of letters misread (or a judged sample 25% wrong): withdrawing it from the site is offered
EN_PER_PASSAGE = 0.00063   # measured on 12 Oct (gemini-2.5-flash, the last 2,258 calls); usage_log decides
''',
     r'''DUP_SHARE = 0.5         # share of letter 4-grams two readings share: the same work
JUDGE_SAMPLE = 40
T2_PER_PASSAGE = 0.0017  # REDEEM_2026_10_14: a marked passage translated again (pro), judged again, its Hindi again
WITHDRAW_MISREAD = 5.0  # % of letters misread (or a judged sample 25% wrong): withdrawing it from the site is offered
EN_PER_PASSAGE = 0.00063   # measured on 12 Oct (gemini-2.5-flash, the last 2,258 calls); usage_log decides
''')
edit('scripts/text_path.py', 14,
     r'''        o.update(path="retranslate", why=("the judge read %d passages: fidelity %.2f of 5, a wrong meaning in %d (%.0f%%)"
                                          % (rv["n"], rv["fidelity"], rv["serious"], serious)),
                 next=["python scripts\\judge_review.py --doc %s   (read what it marks)" % doc],
                 also=["T2 (next): translate the marked passages again with the stronger engine, then judge them again"])
        return o
    o.update(path="done", why="translated (English %d of %d, Hindi %d); %s; the judge: fidelity %.2f, a wrong meaning in "
''',
     r'''        o.update(path="retranslate", why=("the judge read %d passages: fidelity %.2f of 5, a wrong meaning in %d (%.0f%%)"
                                          % (rv["n"], rv["fidelity"], rv["serious"], serious)),
                 next=["python scripts\\judge_review.py --doc %s   (read what it marks)" % doc,
                       "python scripts\\retranslate_marked.py --doc %s   (T2: the marked passages again with the stronger "
                       "engine, then judged again; the dry run, free)" % doc],   # REDEEM_2026_10_14
                 also=["the judge read %d of %d English: judge more to find the rest: python scripts\\judge_sample.py --doc %s "
                       "--sample-pct %d --limit 40   (the dry run, free)"
                       % (rv["n"], en, doc, max(1, min(100, int(math.ceil(100.0 * 2 * JUDGE_SAMPLE / max(1, en))))))],
                 cost=rv["serious"] * T2_PER_PASSAGE)
        return o
    o.update(path="done", why="translated (English %d of %d, Hindi %d); %s; the judge: fidelity %.2f, a wrong meaning in "
''')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for tool, mark in (("scripts/redeem.py", MARK), ("scripts/retranslate_marked.py", "T2_2026_10_14")):
        if not Path(tool).exists() or mark.encode() not in Path(tool).read_bytes():
            problems.append("%s (%s) is not there: copy it in first" % (tool, mark))
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            todo.append((p, out.replace("\n", nl).encode("utf-8")))
    gi = Path(".gitignore")
    if gi.exists():
        gsrc, gnl = load(gi)
        if MARK not in gsrc:
            todo.append((gi, (gsrc.rstrip("\n") + "\n" + GITIGNORE_BLOCK).replace("\n", gnl).encode("utf-8")))
        else:
            print("skip .gitignore (already carries %s)" % MARK)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        if p.suffix != ".py":
            continue
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_redeem_" + stamp))
        t = p.with_name(p.name + ".tmp_redeem"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. What of the translation is kept, free and read-only:")
    print("  python scripts\\redeem.py --html exports\\redeem.html")
    print("dashboard.py shows it on the Library and /redeem when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
