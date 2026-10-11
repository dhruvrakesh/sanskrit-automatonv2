#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_repair_path_2026_10_10.py  (2026-10-10)  REPAIR_PATH_2026_10_10

Asked on 2026-10-10: "In case re-OCR is needed to start translation, rather than crashing, the
resolution path and action should be there and then; else we discard that PDF and look for a better
resolution. We need a clean corpus with the distillate of the best quality translations."

A translation stops for two reasons that are about the scan, not the translator:
  * held by the OCR-debris guard (translate_passages.py exits 3: the stored text is Tesseract debris
    and the page PDFs are in the inbox): Hayashirsha, Natyasastra, Karan Aagama, the Tantric Texts;
  * most of what is left is below the OCR quality bar (Ganita: 185 of 186).
Until now the run ended with a command to copy. Now the next step is a button, where the stop is seen.

  scripts/repair_text.py (new, delivered beside this patcher) is the one place the advice lives. Each
  step ends with two lines, VERDICT: and NEXT:, and the page offers NEXT as a button.

  scripts/dashboard.py (takes effect on a restart, when idle)
    POST /api/repair {doc, step}: assess (free) | repair (vision OCR, capped by max_usd, at most $5 a
      press) | use (re-ingest the repaired text: backup first; with replace=N when it replaces N English
      translations) | set_aside (reason) | restore. Each is a run of repair_text.py; "use" runs under
      the translate lock, as every database writer does. GET /api/repair says the path is there.
    GET /repair/<doc>: the text's repair page: what it holds, the steps, the output of each run.
    The Library: under a note that a run was held, or found nothing it could send, a bar: "Repair
      path: what now?" (assess), "Set aside", "details". A text set aside shows why, and Restore,
      instead of Finish EN and Add Hindi. Texts with no English yet that a run could not translate
      (Natyasastra) are listed at the end, "Waiting for a better source", with the same bar.
    The register of texts set aside is data/source_verdicts.jsonl (beside the database); the PDFs are
      never deleted.
  scripts/dashboard_static.html (takes effect on a reload)
    A [HELD] run, a run that left most of its text below the OCR bar, and a repair step's outcome
    ([REPAIR], with its verdict) are followed in the Log by a line that opens the text's repair page
    (once the dashboard is restarted; until then the line gives the command).

Needs DESK_HEAL_2026_10_10 and LIVE_LOG_2026_10_10 in both files. Anchored, all-or-nothing,
marker-idempotent per file; keeps line endings; the .py is compiled before it replaces the original;
backups .bak_repairpath_<date>.
  python scripts\\patch_repair_path_2026_10_10.py --check
  python scripts\\patch_repair_path_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REPAIR_PATH_2026_10_10"
NEEDS = ("DESK_HEAL_2026_10_10", "LIVE_LOG_2026_10_10")

# ---- scripts/dashboard.py -------------------------------------------------------------------

OLD_SEM = '''            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal", "classify",
                        "embeddings", "entities")):
        sem = _TRANSLATE_SEM
'''
NEW_SEM = '''            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal", "classify",
                        "embeddings", "entities",
                        "repair_use")):   # REPAIR_PATH_2026_10_10: re-ingesting a repaired text writes the DB
        sem = _TRANSLATE_SEM
'''

OLD_NOTE = '''                notes.setdefault(doc, []).append({"lang": x, "text": text, "detail": detail})
'''
NEW_NOTE = '''                notes.setdefault(doc, []).append({"lang": x, "text": text, "detail": detail,   # REPAIR_PATH_2026_10_10: kind
                                                  "kind": "quality" if "quality bar" in text else "nothing"})
'''

OLD_HELDNOTE = '''        notes.setdefault(doc, []).insert(0, {"lang": "both" if len(langs) == 2 else langs[0], "text": text,
                                             "detail": h["detail"]})
'''
NEW_HELDNOTE = '''        notes.setdefault(doc, []).insert(0, {"lang": "both" if len(langs) == 2 else langs[0], "text": text,
                                             "detail": h["detail"], "kind": "held"})   # REPAIR_PATH_2026_10_10
'''

OLD_LIBNOTES = '''    notes = _library_notes()   # DESK_HEAL_2026_10_10
'''
NEW_LIBNOTES = '''    notes = _library_notes()   # DESK_HEAL_2026_10_10
    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside
'''

OLD_RENDER = '''            # DESK_HEAL_2026_10_10: what the last run said, when it could not do the work
            for _n in notes.get(code, []):
                if ((_n["lang"] == "en" and pct >= 100) or (_n["lang"] == "hi" and h >= en)
                        or (_n["lang"] == "both" and pct >= 100 and h >= en)):
                    continue
                acts_html += (f'<div class="cardnote" title="{_html.escape(_n["detail"])}">'
                              f'{_html.escape(_n["text"])}</div>')
'''
NEW_RENDER = '''            # DESK_HEAL_2026_10_10: what the last run said, when it could not do the work
            _shown = []
            for _n in notes.get(code, []):
                if ((_n["lang"] == "en" and pct >= 100) or (_n["lang"] == "hi" and h >= en)
                        or (_n["lang"] == "both" and pct >= 100 and h >= en)):
                    continue
                _shown.append(_n)
            # REPAIR_PATH_2026_10_10: the notes, and the repair path under them; a text set aside says why
            acts_html = _repair_html(code, acts_html, _shown, aside.get(code))
'''

OLD_WAITING = r'''        body += '</div>'

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Srangam &mdash; Corpus Library</title>
'''
NEW_WAITING = r'''        body += '</div>'
    body += _repair_waiting(rows, cats, notes, aside)   # REPAIR_PATH_2026_10_10: no English yet, held by its scan

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Srangam &mdash; Corpus Library</title>
'''

OLD_LIBCSS = '''.cardnote{{margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:#d9b36a;border-left:2px solid #6b5420;padding:2px 0 2px 7px;cursor:help}}
'''
NEW_LIBCSS = '''.cardnote{{margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:#d9b36a;border-left:2px solid #6b5420;padding:2px 0 2px 7px;cursor:help}}
{_REPAIR_CSS}
'''

OLD_LIBJS = '''  setTimeout(function(){{ _watchJob(id, doc, lang, btn, orig, n+1); }}, n<45 ? 2000 : 10000);
}}
'''
NEW_LIBJS = '''  setTimeout(function(){{ _watchJob(id, doc, lang, btn, orig, n+1); }}, n<45 ? 2000 : 10000);
}}
{_REPAIR_JS}
'''

OLD_ENDPOINT = '''@app.post("/api/classify")
def api_classify():
'''
NEW_ENDPOINT = r'''# REPAIR_PATH_2026_10_10 ---------------------------------------------------------------------
# The repair path, there and then. A translation that stops because of its scan (held by the
# OCR-debris guard, or most of what is left below the OCR quality bar) offers its next step where the
# stop is seen: in the Library, on /repair/<doc>, and from the dashboard's Log. Every step is a run of
# scripts/repair_text.py, whose last two lines (VERDICT:, NEXT:) are the advice; the page offers NEXT
# as a button. A text that cannot be repaired is set aside (data/source_verdicts.jsonl, beside the
# database): its files are kept, and a better scan is looked for.
_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore")
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand

_REPAIR_CSS = r"""/* REPAIR_PATH_2026_10_10 */
.repairbar{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;align-items:center}
.tr-rest.rp{flex:0 0 auto}
.tr-rest.rpnext{border-color:var(--gold);color:var(--gold)}
.rplink{font-family:'Inter',sans-serif;font-size:10.5px;color:var(--muted);text-decoration:none}
.rplink:hover{color:var(--gold)}
.rpout{flex-basis:100%;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:var(--cream);opacity:.85}
.rpout:empty{display:none}
.cardnote.aside{color:#d98a8a;border-left-color:#7a3a3a}
.rpintro{color:var(--muted);font-family:'Inter',sans-serif;font-size:12px;margin:-4px 0 12px}
.card-wrap.waiting .card{cursor:default}"""

_REPAIR_JS = r"""/* REPAIR_PATH_2026_10_10: the repair path, there and then. Each step is a run of repair_text.py; its
   last two lines (VERDICT:, NEXT:) say what it found, and the next step is offered as a button. */
var _RP_DOING = {assess: 'assessing...', repair: 'repairing the scan...', use: 're-ingesting the repaired text...',
                 set_aside: 'setting it aside...', restore: 'restoring...'};
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13);
function _rpLines(s){
  return String(s || '').split(_RP_NL).map(function(l){ return l.split(_RP_CR).join(''); })
    .filter(function(l){ return l.trim(); });
}
function _rpVerdict(out){
  var v = '', n = '';
  _rpLines(out).forEach(function(l){
    if (l.indexOf('VERDICT: ') === 0) v = l.slice(9);
    if (l.indexOf('NEXT:') === 0) n = l.slice(5).trim();
  });
  return {verdict: v, next: n};
}
function _rpNext(next){
  var n = String(next || ''), m;
  if (n.indexOf('--use-repaired') >= 0){
    m = n.match(/--replace ([0-9]+)/);
    return {step: 'use', replace: m ? +m[1] : null,
            label: m ? 'Use the repaired text (replaces ' + m[1] + ' English)' : 'Use the repaired text'};
  }
  if (n.indexOf('--set-aside') >= 0) return {step: 'set_aside', label: 'Set aside: a better scan is wanted'};
  if (n.indexOf('--restore') >= 0) return {step: 'restore', label: 'Restore'};
  if (n.indexOf('--repair') >= 0){
    m = n.match(/--max-usd ([0-9.]+)/);
    var usd = m ? +m[1] : 1;
    return {step: 'repair', max_usd: usd, label: 'Repair the scan (at most $' + usd.toFixed(2) + ')'};
  }
  if (n.indexOf('Finish EN') >= 0) return {step: 'library', label: 'Translate it: open the Library'};
  return null;
}
function _rpBox(doc){ return document.getElementById('rp-' + doc); }
function _rpSay(doc, text){
  var b = _rpBox(doc), o = b ? b.querySelector('.rpout') : null;
  if (o) o.textContent = text;
}
function _rpOffer(doc, next){
  var box = _rpBox(doc); if (!box) return;
  var old = box.querySelector('.rpnext'); if (old) old.parentNode.removeChild(old);
  var s = _rpNext(next); if (!s) return;
  var b = document.createElement('button');
  b.className = 'tr-rest rp rpnext'; b.textContent = s.label; b.title = next;
  b.onclick = function(){ repairStep(doc, s.step, b, s); };
  box.insertBefore(b, box.firstChild);
}
async function repairStep(doc, step, btn, opt){
  opt = opt || {};
  if (step === 'library'){ location.href = '/library'; return; }
  var body = {doc: doc, step: step};
  if (step === 'repair'){
    body.max_usd = opt.max_usd || 1;
    if (body.max_usd > 5){
      _rpSay(doc, 'The estimate is above the $5.00 one press may spend. Run it by hand: python scripts' + String.fromCharCode(92)
             + 'repair_text.py --doc ' + doc + ' --repair --max-usd ' + body.max_usd.toFixed(2));
      return;
    }
    if (!confirm('Repair the scan of ' + doc + ': vision OCR on its pages, at most $' + body.max_usd.toFixed(2)
                 + ' (it stops before spending more). The database is not touched. Go?')) return;
  }
  if (step === 'use'){
    if (!confirm(opt.replace
        ? ('Use the repaired text of ' + doc + '. Its passages are replaced: ' + opt.replace + ' English translations, and the '
           + 'Hindi, vectors and pictures that point at the old passages, go with them. A backup is made first; translating '
           + 'again costs nothing where a passage did not change. Go?')
        : ('Use the repaired text of ' + doc + '. Nothing translated is lost; a backup is made first. Go?'))) return;
    if (opt.replace) body.replace = opt.replace;
  }
  if (step === 'set_aside'){
    var why = prompt('Set ' + doc + ' aside: why? Its files are kept; the Library stops offering its translation until '
                     + 'it is restored.', 'needs a better scan');
    if (why === null) return;
    body.reason = why || 'needs a better scan';
  }
  var orig = btn ? btn.textContent : '';
  if (btn){ btn.disabled = true; btn.textContent = 'starting...'; }
  try{
    var r = await fetch('/api/repair', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                        body: JSON.stringify(body)});
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
      var v = _rpVerdict((j.out || '') + _RP_NL + (j.err || ''));
      var text = v.verdict || (j.ok ? 'done' : 'it did not finish: the Dashboard History has its last lines');
      _rpSay(doc, text); _rpOffer(doc, v.next);
      _toast(doc + ': ' + text);
      if (j.ok && !pre && (step === 'set_aside' || step === 'restore' || step === 'use'))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
    }
    _rpSay(doc, (j.state === 'queued' ? 'queued: after the running database writer' : (_RP_DOING[step] || 'running...'))
                + (lines.length ? '  ' + lines[lines.length - 1] : ''));
  }catch(e){ if (n > 400){ if (btn){ btn.textContent = orig; btn.disabled = false; } return; } }
  setTimeout(function(){ _watchRepair(id, doc, step, btn, orig, n + 1); }, n < 45 ? 2000 : 10000);
}"""


def _source_verdicts(folder=None) -> Dict[str, dict]:
    """The texts set aside: data/source_verdicts.jsonl beside the database, written by repair_text.py;
    the latest record of a text wins. Never the database; a missing file is no text set aside."""
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
    return {d: r for d, r in last.items() if r.get("status") == "set_aside"}


def _repair_bar(code: str, aside: bool) -> str:
    import html as _html
    c = _html.escape(code, quote=True)
    if aside:
        btns = ('<button class="tr-rest rp" data-doc="%s" title="A better scan is in the inbox: offer this text again"'
                ' onclick="repairStep(this.dataset.doc,&#39;restore&#39;,this)">Restore</button>' % c)
    else:
        btns = ('<button class="tr-rest rp" data-doc="%s" title="Free: reads the database and the page files, and says '
                'what the scan needs" onclick="repairStep(this.dataset.doc,&#39;assess&#39;,this)">&#128295; Repair path: '
                'what now?</button>'
                '<button class="tr-rest rp" data-doc="%s" title="The scan cannot be repaired: set the text aside until a '
                'better scan is found. Its files are kept." onclick="repairStep(this.dataset.doc,&#39;set_aside&#39;,this)">'
                'Set aside</button>' % (c, c))
    return ('<div class="repairbar" id="rp-%s">%s<a class="rplink" href="/repair/%s" title="Its repair page: the steps, '
            'and the output of each run">details</a><div class="rpout"></div></div>' % (c, btns, c))


def _repair_html(code: str, acts_html: str, shown: list, aside_rec) -> str:
    """The Library card's notes (as DESK_HEAL wrote them) and, under a note that the scan stopped the
    run, the repair bar. A text set aside shows why and Restore instead of its translate buttons."""
    import html as _html
    if aside_rec:
        return ('<div class="cardnote aside" title="data/source_verdicts.jsonl">Set aside on %s: %s. A better scan is '
                'wanted; its files are kept, and its translation is not offered until it is restored.</div>%s'
                % (_html.escape(str(aside_rec.get("at") or "?")[:10]),
                   _html.escape(str(aside_rec.get("reason") or "needs a better scan")), _repair_bar(code, True)))
    for n in shown:
        acts_html += ('<div class="cardnote" title="%s">%s</div>'
                      % (_html.escape(n.get("detail") or ""), _html.escape(n.get("text") or "")))
    if any(n.get("kind") in ("held", "quality", "nothing") for n in shown):
        acts_html += _repair_bar(code, False)
    return acts_html


def _repair_waiting(rows, cats, notes, aside) -> str:
    """The texts the Library does not list (no English yet) whose last run stopped because of the scan,
    or that are set aside: each with its notes and its repair path."""
    import html as _html
    listed = {d[0] for docs in cats.values() for d in docs}
    cards = ""
    for code, title, _cat, total, en in rows:
        if code in listed or not (notes.get(code) or code in aside):
            continue
        inner = _repair_html(code, "", list(notes.get(code, [])), aside.get(code))
        if not inner:
            continue
        cards += ('<div class="card-wrap waiting"><div class="card"><div class="ttl">%s</div><div class="code">%s</div>'
                  '<div class="meta"><span class="badge en">EN %d/%d</span></div></div>%s</div>'
                  % (_html.escape(str(title)), _html.escape(str(code)), int(en or 0), int(total or 0), inner))
    if not cards:
        return ""
    return ('<h2 class="cat">Waiting for a better source</h2><p class="rpintro">No English yet: the last run could not '
            'translate these because of their scan. Each offers its repair path.</p><div class="grid">%s</div>' % cards)


@app.route("/api/repair", methods=["GET", "POST"])
def api_repair():
    """POST {doc, step, max_usd?, replace?, reason?}: one step of a text's repair path, as a run of
    repair_text.py (kind "repair"; "use" is kind "repair_use", under the translate lock). GET says the
    path is there (the dashboard page asks before it links to /repair/<doc>)."""
    if request.method == "GET":
        return jsonify({"ok": True, "mark": "REPAIR_PATH_2026_10_10", "steps": list(_REPAIR_STEPS),
                        "max_usd": _REPAIR_MAX_USD})
    data = request.get_json(silent=True) or {}
    doc = _validate_doc(data.get("doc"))
    step = str(data.get("step") or "assess")
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    if step not in _REPAIR_STEPS:
        return jsonify({"error": "unknown step %r (one of %s)" % (step, ", ".join(_REPAIR_STEPS))}), 400
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
        argv += ["--set-aside", " ".join(str(data.get("reason") or "").split())[:300] or "needs a better scan"]
    elif step == "restore":
        argv.append("--restore")
    kind = "repair_use" if step == "use" else "repair"
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})


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
main{max-width:860px;margin:0 auto;padding:22px 16px 60px}
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
pre.rplog{margin-top:12px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:11px;line-height:1.45;white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto;color:var(--muted)}
pre.rplog:empty{display:none}
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><h1>Repair path</h1></header>
<main>
<div class="ttl">__TITLE__</div><div class="code">__CODE__</div>
<div class="facts"><span>__TOTAL__ passages</span><span>English __EN__</span><span>Hindi __HI__</span></div>
<ol class="steps">
<li><b>Assess</b>: free. It reads the database and the page files, and says what the scan needs.</li>
<li><b>Repair the scan</b>: vision OCR on its pages, with a cap on the spend. The database is not touched.</li>
<li><b>Use the repaired text</b>: a backup first; then its passages are replaced by the repaired text, under the translate lock.</li>
<li><b>Set aside</b>: when the scan cannot be repaired. Its files are kept, and a better scan is looked for.</li>
</ol>
__NOTES__
__BAR__
<pre class="rplog" id="rplog-__CODE__"></pre>
</main>
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
__REPAIR_JS__
repairStep('__CODE__', 'assess', null);
</script>
</body></html>"""


@app.get("/repair/<doc>")
def repair_page(doc):
    """One text's repair path: what it holds, the steps, and each run's output. Opens with an
    assessment (free). Reads the database read-only."""
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
    aside = _source_verdicts(pathlib.Path(db_path).parent).get(doc)
    try:
        shown = _library_notes().get(doc, [])
    except Exception:
        shown = []
    notes = "".join('<div class="cardnote" title="%s">%s</div>' % (_html.escape(n.get("detail") or ""),
                                                                    _html.escape(n.get("text") or "")) for n in shown)
    if aside:
        notes += ('<div class="cardnote aside">Set aside on %s: %s. A better scan is wanted; its files are kept.</div>'
                  % (_html.escape(str(aside.get("at") or "?")[:10]), _html.escape(str(aside.get("reason") or ""))))
    page = (_REPAIR_PAGE.replace("__REPAIR_CSS__", _REPAIR_CSS)
            .replace("__NOTES__", notes).replace("__BAR__", _repair_bar(doc, bool(aside)))
            .replace("__TITLE__", _html.escape(str(title))).replace("__TOTAL__", "{:,}".format(int(total or 0)))
            .replace("__EN__", "{:,}".format(int(en or 0))).replace("__HI__", "{:,}".format(int(hi or 0)))
            .replace("__CODE__", _html.escape(doc)))
    return page.replace("__REPAIR_JS__", _REPAIR_JS)


@app.post("/api/classify")
def api_classify():
'''

# ---- scripts/dashboard_static.html ----------------------------------------------------------

OLD_ADDLOG = r'''function addLog(line, cls) {
  logLines.push({line, cls: cls || ''});
'''
NEW_ADDLOG = r'''function addLog(line, cls, href) {
  logLines.push({line, cls: cls || '', href: href || ''});   // REPAIR_PATH_2026_10_10: a line may open a page
'''

OLD_RENDERLOG = r'''    return '<span' + (l.cls ? ' class="' + l.cls + '"' : '') + '>' + esc(l.line) + '</span>\n';
'''
NEW_RENDERLOG = r'''    return '<span' + (l.cls ? ' class="' + l.cls + '"' : '') + '>'
      + (l.href ? '<a class="log-act" href="' + esc(l.href) + '" target="_blank" rel="noopener">' + esc(l.line) + '</a>'
                : esc(l.line)) + '</span>\n';
'''

OLD_LOGCSS = r'''.log-line-past{color:var(--muted)}
'''
NEW_LOGCSS = r'''.log-line-past{color:var(--muted)}
.log-act{color:inherit;text-decoration:underline;cursor:pointer}  /* REPAIR_PATH_2026_10_10 */
'''

OLD_VERDICT_HEAD = r'''function jobVerdict(ok, out) {
  out = String(out || '');
'''
NEW_VERDICT_HEAD = r'''function jobVerdict(ok, out) {
  out = String(out || '');
  // REPAIR_PATH_2026_10_10: a step of a repair path says what it found on its VERDICT: line
  const rv = out.match(/(?:^|\n)VERDICT: [^\n]*/g);
  if (rv && !/KILLED/.test(out)) {
    return {word: ok === false ? 'repair: not done' : 'repair', tag: '[REPAIR]', cls: ok === false ? 'log-line-held' : 'log-line-ok',
            text: rv[rv.length - 1].replace(/^\n?VERDICT: /, '').replace(/\r$/, '')};
  }
'''

OLD_VERDICT_HELD = r'''    return {word: 'held', tag: '[HELD]', cls: 'log-line-held',
'''
NEW_VERDICT_HELD = r'''    return {word: 'held', tag: '[HELD]', cls: 'log-line-held', doc: m ? m[1] : '',
'''

OLD_VERDICT_DONE = r'''    const sent = done.reduce(function(a, m) { return a + (+m[1]); }, 0);
    return {word: sent ? 'done' : 'nothing sent', tag: sent ? '[OK]' : '[NOTHING]', cls: sent ? 'log-line-ok' : 'log-line-info',
'''
NEW_VERDICT_DONE = r'''    const sent = done.reduce(function(a, m) { return a + (+m[1]); }, 0);
    const tot = done.reduce(function(a, m) { return a + (+m[2]); }, 0);    // REPAIR_PATH_2026_10_10
    const skip = done.reduce(function(a, m) { return a + (+m[3]); }, 0);
    return {stuck: tot > 0 && skip >= 0.8 * tot,
            word: sent ? 'done' : 'nothing sent', tag: sent ? '[OK]' : '[NOTHING]', cls: sent ? 'log-line-ok' : 'log-line-info',
'''

OLD_POLL_OUTCOME = r'''        addLog(v.tag + ' ' + label + ' - ' + v.text, v.cls);
'''
NEW_POLL_OUTCOME = r'''        addLog(v.tag + ' ' + label + ' - ' + v.text, v.cls);
        _repairHint(v, activeJobs[jid].doc || v.doc, false);   // REPAIR_PATH_2026_10_10
'''

OLD_LOGFINISHED = r'''  addLog(v.tag + ' ' + at + ' ' + (r.kind || '') + ' ' + (r.doc || '') + ' - ' + v.text, past ? 'log-line-past' : v.cls);
  return v;
}
'''
NEW_LOGFINISHED = r'''  addLog(v.tag + ' ' + at + ' ' + (r.kind || '') + ' ' + (r.doc || '') + ' - ' + v.text, past ? 'log-line-past' : v.cls);
  _repairHint(v, r.doc || v.doc, past);   // REPAIR_PATH_2026_10_10
  return v;
}
'''

OLD_SEEN = r'''const _seenFinished = new Set();
let _historySeeded = false;
'''
NEW_SEEN = r'''// REPAIR_PATH_2026_10_10: a run that stops because of its scan points at its repair path, there and then:
// a line that opens /repair/<doc> (assess, repair the scan, use it, or set it aside). Until the dashboard
// is restarted with the path, the line gives the command instead.
let _repairReady = false;
const _repairProbe = fetch('/api/repair').then(function(r) { return r.ok ? r.json() : null; })
  .then(function(d) { _repairReady = !!(d && d.mark); }).catch(function() {});
function _repairHint(v, doc, past) {
  if (!doc || !(v.word === 'held' || v.stuck || (v.tag === '[REPAIR]' && !past))) return;
  const cls = past ? 'log-line-past' : 'log-line-held';
  if (_repairReady) {
    addLog('  -> ' + doc + ': its repair path, there and then (assess, repair the scan, use it, or set it aside)', cls,
           '/repair/' + encodeURIComponent(doc));
  } else {
    addLog('  -> its repair path: python scripts\\repair_text.py --doc ' + doc + '   (buttons come with the dashboard restart)', cls);
  }
}
const _seenFinished = new Set();
let _historySeeded = false;
'''

OLD_SEED = r'''      _historySeeded = true;
'''
NEW_SEED = r'''      _historySeeded = true;
      await _repairProbe;   // REPAIR_PATH_2026_10_10: know whether /repair/<doc> answers before linking to it
'''

EDITS = {
    "scripts/dashboard.py": [
        ("the re-ingest takes the translate lock", OLD_SEM, NEW_SEM),
        ("a note says what kind it is", OLD_NOTE, NEW_NOTE),
        ("a hold says it is one", OLD_HELDNOTE, NEW_HELDNOTE),
        ("the Library reads the texts set aside", OLD_LIBNOTES, NEW_LIBNOTES),
        ("the Library card's notes and repair bar", OLD_RENDER, NEW_RENDER),
        ("texts waiting for a better source", OLD_WAITING, NEW_WAITING),
        ("Library css", OLD_LIBCSS, NEW_LIBCSS),
        ("Library script", OLD_LIBJS, NEW_LIBJS),
        ("/api/repair and /repair/<doc>", OLD_ENDPOINT, NEW_ENDPOINT),
    ],
    "scripts/dashboard_static.html": [
        ("a Log line may open a page", OLD_ADDLOG, NEW_ADDLOG),
        ("render it as a link", OLD_RENDERLOG, NEW_RENDERLOG),
        ("log link css", OLD_LOGCSS, NEW_LOGCSS),
        ("a repair step's verdict", OLD_VERDICT_HEAD, NEW_VERDICT_HEAD),
        ("a hold names its text", OLD_VERDICT_HELD, NEW_VERDICT_HELD),
        ("most of it below the OCR bar", OLD_VERDICT_DONE, NEW_VERDICT_DONE),
        ("pollJob points at the path", OLD_POLL_OUTCOME, NEW_POLL_OUTCOME),
        ("the history points at the path", OLD_LOGFINISHED, NEW_LOGFINISHED),
        ("the hint and the probe", OLD_SEEN, NEW_SEEN),
        ("the seed waits for the probe", OLD_SEED, NEW_SEED),
    ],
}


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    if not Path("scripts/repair_text.py").exists():
        print("REFUSE: scripts\\repair_text.py is not there (it comes with this patcher). Nothing written."); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        missing = [m for m in NEEDS if m not in src]
        if missing:
            problems.append("%s does not carry %s: apply those patches first" % (rel, ", ".join(missing))); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        if p.suffix == ".py":
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
        shutil.copy2(p, p.with_name(p.name + ".bak_repairpath_" + stamp))
        t = p.with_name(p.name + ".tmp_repairpath"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Reload the dashboard page (Ctrl+F5): a held run in the Log points at its repair path. dashboard.py takes")
    print("/api/repair, /repair/<doc> and the Library's repair bar when it is restarted, only when idle:")
    print("scripts\\restart_dashboard.ps1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
