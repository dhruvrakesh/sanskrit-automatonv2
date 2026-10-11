#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_repair_heal_2026_10_11.py  (2026-10-11)  REPAIR_HEAL_2026_10_11

What was seen on 11 Oct, 18:45-18:57 (data/jobs.jsonl; docs/REPAIR_HEAL_2026-10-11.md):
  * Every "Repair the scan" refused in a second: ocr_consensus.py refuses while the dashboard runs a
    job for the text ("stop them first"), and the repair is itself that job. Tantric Texts (twice) and
    Ganita never reached vision; the Tantric Texts were then set aside.
  * Karan Aagama's repaired text went in (18:51; debris 32% -> 9%, vision 0% -> 87%, drift 183 of 183
    current). Its English and Hindi were replaced, as the confirmation said. Then the path stopped: the
    text, now with no English, was listed under "Waiting for a better source" with no way to translate
    it, beside a stale "held" note from 18:50, and the next step read "open the Library".
  * The Log did show the runs (checked in the browser); a repair's verdict was cut to "done" when the
    job record's 400-character tail lost its start, and the Live tab showed only translations.
  * The next mirror run would send Karan's new passages without their translations to the site.

  scripts/ocr_consensus.py: it looks past the dashboard jobs of the kinds named in
    SA_CONSENSUS_SELF_KIND (repair_text.py names its own: "repair").
  scripts/translate_passages.py: the debris guard lets a text through when the register says
    "translate as is" (repair_text.py --as-is, after the debris is judged cosmetic or moderate).
  scripts/corpus_sync.py: a text "in repair" (repair_text.py --hold, and --use-repaired when it replaced
    translations) is not compared or sent: the site keeps its last version until --release.
  scripts/dashboard.py (on a restart): the repair path's states (set aside, translate as is, complete,
    in repair), "Translate it now: English, then Hindi" after a repair, the Library's texts with no
    English offered their translation ("Not yet readable"), the debris judged on the repair page, the
    Source desk (scripts/source_desk.py: find, preview in the page, fetch a better edition);
    /api/jobs/running says each job's mode; a job record keeps its last VERDICT and NEXT in full.
  scripts/dashboard_static.html (on a reload): the Log reads a repair's verdict in full; the Live tab
    shows the jobs that are not translations, with their last lines.

Needs REPAIR_PATH_2026_10_10 (dashboard files) and scripts/repair_text.py, scripts/source_desk.py of
2026-10-11 beside it. Anchored (the REPAIR_PATH block of dashboard.py is replaced whole, guarded by its
md5), all-or-nothing, marker-idempotent per file; keeps line endings; every .py is compiled before it
replaces the original; backups .bak_repairheal_<date>.
  python scripts\\patch_repair_heal_2026_10_11.py --check
  python scripts\\patch_repair_heal_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REPAIR_HEAL_2026_10_11"
BLOCK_START = "# REPAIR_PATH_2026_10_10 ---------------------------------------------------------------------\n"
BLOCK_END = '@app.post("/api/classify")\ndef api_classify():'
OLD_BLOCK_MD5 = "6feb07ea78093137b7b63e3ca4e35683"     # the block as patch_repair_path_2026_10_10.py wrote it

# ---- scripts/dashboard.py -------------------------------------------------------------------
OLD_RUNNING = '''             "active": bool(j.active), "state": "running" if j.active else "queued"}
'''
NEW_RUNNING = '''             "active": bool(j.active), "state": "running" if j.active else "queued",
             "mode": j.mode or None}   # REPAIR_HEAL_2026_10_11: a vision repair and an assessment differ
'''
OLD_PERSIST = '''        if job.mode:  # EXPORT_MODE_JOBLOG_2026_09_30 - only when set; other records keep their shape
            record["mode"] = job.mode
'''
NEW_PERSIST = '''        if job.mode:  # EXPORT_MODE_JOBLOG_2026_09_30 - only when set; other records keep their shape
            record["mode"] = job.mode
        # REPAIR_HEAL_2026_10_11: a repair step's verdict in full (the 400-character tail can lose its start)
        _v = [ln.strip() for ln in (job.out or "").splitlines() if ln.startswith(("VERDICT: ", "NEXT: "))]
        if _v:
            for _ln in _v:
                record["verdict" if _ln.startswith("VERDICT: ") else "next"] = _ln.split(": ", 1)[1][:700]
'''
OLD_NOTES = '''    for r in recs:
        kind = r.get("kind") or ""
        if kind not in ("translate", "translate_hi", "translate_both", "pipeline"):
            continue
'''
NEW_NOTES = '''    for r in recs:
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
'''

# ---- scripts/dashboard_static.html ----------------------------------------------------------
OLD_LOGFIN = r'''  const v = jobVerdict(r.ok, String(r.out_tail || '') + '\n' + String(r.err_preview || ''));
'''
NEW_LOGFIN = r'''  const v = jobVerdict(r.ok, String(r.out_tail || '') + '\n' + String(r.err_preview || '')
                            + (r.verdict ? '\nVERDICT: ' + r.verdict : ''));   // REPAIR_HEAL_2026_10_11: in full
'''
OLD_POLLPROG = r'''async function pollProgress() {
  try {
    const r = await fetch('/api/progress');
    if (!r.ok) return;
    renderProgress(await r.json());
  } catch(e) {}
}
'''
NEW_POLLPROG = r'''async function pollProgress() {
  try {
    const r = await fetch('/api/progress');
    if (!r.ok) return;
    renderProgress(await r.json());
  } catch(e) {}
  _liveOthers();   // REPAIR_HEAL_2026_10_11
}

// REPAIR_HEAL_2026_10_11: the Live tab also shows the jobs that are not translations (a repair, an OCR, an
// ingest), with their last lines, so a press in the Library or on a repair page is seen running here.
let _liveOthersTick = 0;
async function _liveOthers() {
  if ((_liveOthersTick++) % 2) return;            // every other poll: about every 4 s
  const host = document.getElementById('progressContent');
  if (!host || !host.parentNode) return;
  let box = document.getElementById('liveOthers');
  if (!box) { box = document.createElement('div'); box.id = 'liveOthers'; host.parentNode.insertBefore(box, host); }
  try {
    const d = await (await fetch('/api/jobs/running')).json();
    const jobs = (d.running || []).filter(function(j) { return !/^translate/.test(j.kind || ''); }).slice(0, 3);
    if (!jobs.length) { box.innerHTML = ''; return; }
    const parts = await Promise.all(jobs.map(async function(j) {
      let tail = [];
      try { const x = await (await fetch('/api/job/' + j.id)).json(); tail = _outLines(x.out).slice(-3); } catch (e) {}
      const t = Math.round(j.elapsed_s || 0);
      return '<div style="border:1px solid var(--border-v);border-radius:6px;padding:7px 9px;margin-bottom:8px">'
        + '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:10px">'
        + '<span class="' + (j.state === 'queued' ? 'pstat-idle' : 'pstat-run') + '">'
        + (j.state === 'queued' ? '&#9203; queued' : '&#9654; running') + '</span>'
        + '<b>' + esc((j.kind || '') + (j.mode ? ' (' + j.mode + ')' : '')) + '</b>'
        + '<span style="color:var(--muted);font-family:JetBrains Mono,monospace;overflow:hidden;text-overflow:ellipsis;'
        + 'white-space:nowrap;max-width:160px">' + esc(j.doc || '') + '</span>'
        + '<span style="color:var(--muted)">' + (t < 60 ? t + 's' : Math.floor(t / 60) + 'm ' + (t % 60) + 's') + '</span></div>'
        + (tail.length ? '<div style="margin-top:4px;font-family:JetBrains Mono,monospace;font-size:9.5px;color:var(--muted);'
           + 'white-space:pre-wrap;word-break:break-word">' + esc(tail.join('\n')) + '</div>' : '')
        + '</div>';
    }));
    box.innerHTML = '<div style="font-size:9px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:4px">'
      + 'Running now</div>' + parts.join('');
  } catch (e) {}
}
'''

# ---- scripts/ocr_consensus.py ---------------------------------------------------------------
OLD_CONS = '''        return [j for j in data.get("running", []) if j.get("doc") == doc]
'''
NEW_CONS = '''        # REPAIR_HEAL_2026_10_11: repair_text.py runs this as the dashboard's own job (kind "repair"); it names
        # its kind here, so the job that asked for the repair is not taken for one in its way
        skip = {k.strip() for k in os.environ.get("SA_CONSENSUS_SELF_KIND", "").split(",") if k.strip()}
        return [j for j in data.get("running", []) if j.get("doc") == doc and j.get("kind") not in skip]
'''

# ---- scripts/translate_passages.py ----------------------------------------------------------
OLD_GUARD = '''def _debris_guard(con, doc, debris_max, inbox=None):
    """A refusal message when the doc's stored text is repairable Tesseract debris, else None."""
    import re as _re
'''
NEW_GUARD = '''def _source_state(doc):
    """REPAIR_HEAL_2026_10_11: the text's latest record in data/source_verdicts.jsonl (repair_text.py's
    register), or None. SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (Path(__file__).resolve().parent.parent / "data" / "source_verdicts.jsonl"))
    last = None
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc") == doc:
                    last = r
    except OSError:
        return None
    return last


def _debris_guard(con, doc, debris_max, inbox=None):
    """A refusal message when the doc's stored text is repairable Tesseract debris, else None."""
    _st = _source_state(doc)   # REPAIR_HEAL_2026_10_11: "translate as is" was decided for this text
    if _st and _st.get("status") == "translate_as_is":
        print("debris guard: %s is to be translated as is (data/source_verdicts.jsonl, %s: %s)"
              % (doc, str(_st.get("at") or "?")[:16], _st.get("reason") or ""))
        return None
    import re as _re
'''

# ---- scripts/corpus_sync.py -----------------------------------------------------------------
OLD_SYNC = '''                for n_doc, doc in enumerate(sel_docs, 1):
                    groups = build_doc_groups(self.con, doc, set(per_doc), ent_ok)
'''
NEW_SYNC = '''                in_repair = _in_repair_docs()   # REPAIR_HEAL_2026_10_11
                for n_doc, doc in enumerate(sel_docs, 1):
                    if doc[1] in in_repair:
                        self.held.append("%s: in repair (data/source_verdicts.jsonl): not compared or sent; the site "
                                         "keeps its last version until repair_text.py --release" % doc[1])
                        continue
                    groups = build_doc_groups(self.con, doc, set(per_doc), ent_ok)
'''
OLD_LIVE = '''def live_docs(con, include_retired: bool = False):
'''
NEW_LIVE = '''def _in_repair_docs() -> set:
    """REPAIR_HEAL_2026_10_11: the texts whose latest record in data/source_verdicts.jsonl (repair_text.py's
    register) is "in_repair": their passages were replaced and are being translated again, so the site
    keeps its last version of them. SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "in_repair"}


def live_docs(con, include_retired: bool = False):
'''

NEW_BLOCK = r'''# REPAIR_PATH_2026_10_10 ---------------------------------------------------------------------
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
                 "find", "fetch")
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair")
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
                 find: 'looking for a better edition...', fetch: 'fetching...', translate: 'translating...'};
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
  if (n.indexOf('--use-repaired') >= 0){
    m = n.match(/--replace ([0-9]+)/);
    return {step: 'use', replace: m ? +m[1] : null,
            label: m ? 'Use the repaired text (replaces ' + m[1] + ' English)' : 'Use the repaired text'};
  }
  if (n.indexOf('--as-is') >= 0) return {step: 'as_is', reason: _rpQuoted(n), label: 'Translate as is'};
  if (n.indexOf('--accept') >= 0) return {step: 'accept', reason: _rpQuoted(n), label: 'Accept as complete'};
  if (n.indexOf('--set-aside') >= 0) return {step: 'set_aside', label: 'Set aside: a better scan is wanted'};
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
    if (opt.replace) body.replace = opt.replace;
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold'){
    var ask = {set_aside: 'Set ' + doc + ' aside: why? Its files are kept; the Library stops offering its translation until '
                          + 'it is restored.',
               as_is: 'Translate ' + doc + ' as is: the debris guard will let it through. Why?',
               accept: 'Accept ' + doc + ' as complete: what is left is not to be translated. Why?',
               hold: 'Hold ' + doc + ' from the site: the site keeps its last version until you publish. Why?'}[step];
    var dflt = opt.reason || {set_aside: 'needs a better scan', as_is: 'debris judged cosmetic',
                              accept: 'what is left is not Sanskrit', hold: 're-translating after the repair'}[step];
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
      if ((step === 'find' || step === 'fetch') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|as_is|accept|hold|release|translate)$/.test(step))
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
  if (!d || d.missing){ list.innerHTML = '<p class="srcnone">No search yet. Press Find a better source.</p>'; return; }
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
  list.innerHTML = h; list._data = d;
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


def _repair_html(code: str, acts_html: str, shown: list, rec) -> str:
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
                % (at, why or "needs a better scan", _repair_bar(code, "aside")))
    if st == "complete":
        shown = [n for n in shown if n.get("kind") not in ("quality", "nothing")]
        acts_html += '<div class="cardnote state">Accepted as complete on %s: %s.</div>' % (at, why)
    elif st == "translate_as_is":
        shown = [n for n in shown if n.get("kind") != "held"]
        acts_html += ('<div class="cardnote state">To be translated as is (since %s): %s. The debris guard lets it '
                      'through.</div>' % (at, why))
    elif st == "in_repair":
        acts_html += ('<div class="cardnote state">In repair since %s (%s): the site keeps its last version (%s English, '
                      '%s Hindi) until you publish this one.</div>'
                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))
    for n in shown:
        acts_html += ('<div class="cardnote%s" title="%s">%s</div>'
                      % (" repaired" if n.get("kind") == "repaired" else "",
                         _html.escape(n.get("detail") or ""), _html.escape(n.get("text") or "")))
    kinds = {n.get("kind") for n in shown}
    if st == "in_repair":
        acts_html += _repair_bar(code, "in_repair")
    elif "repaired" in kinds:
        acts_html += _repair_bar(code, "repaired")
    elif kinds & {"held", "quality", "nothing"}:
        acts_html += _repair_bar(code, "standard")
    return acts_html


def _repair_waiting(rows, cats, notes, aside) -> str:
    """The texts the Library does not list (no English yet) whose last run stopped because of the scan,
    that were repaired, or that are in the register: each with its notes, its translate buttons (unless
    set aside) and its repair path."""
    import html as _html
    listed = {d[0] for docs in cats.values() for d in docs}
    cards = ""
    for code, title, _cat, total, en in rows:
        if code in listed or not (notes.get(code) or code in aside):
            continue
        rec = aside.get(code) or {}
        c = _html.escape(str(code), quote=True)
        acts = "" if rec.get("status") == "set_aside" else (
            '<div class="cardacts"><button class="tr-rest" data-doc="%s" title="Translate its English" '
            'onclick="translateRest(this.dataset.doc,&#39;en&#39;,this)">&#9889; Finish EN</button>'
            '<button class="tr-rest hi" data-doc="%s" title="Translate its Hindi" '
            'onclick="translateRest(this.dataset.doc,&#39;hi&#39;,this)">&#2361;&#2367; Add Hindi</button></div>' % (c, c))
        inner = _repair_html(code, acts, list(notes.get(code, [])), aside.get(code))
        if not inner:
            continue
        cards += ('<div class="card-wrap waiting"><div class="card"><div class="ttl">%s</div><div class="code">%s</div>'
                  '<div class="meta"><span class="badge en">EN %d/%d</span></div></div>%s</div>'
                  % (_html.escape(str(title)), _html.escape(str(code)), int(en or 0), int(total or 0), inner))
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
    doc = _validate_doc(data.get("doc"))
    step = str(data.get("step") or "assess")
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
    kind = "repair_use" if step == "use" else "repair"
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})


@app.get("/api/repair/sources")
def api_repair_sources():
    """The Source desk's last search for a text (data/source_desk/<doc>.json), for the repair page."""
    doc = _validate_doc(request.args.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    p = SOURCE_DESK_DIR / ("%s.json" % doc)
    try:
        return jsonify(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return jsonify({"doc": doc, "missing": True, "candidates": []})


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
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><h1>Repair path</h1></header>
<main>
<div class="ttl">__TITLE__</div><div class="code">__CODE__</div>
<div class="facts"><span>__TOTAL__ passages</span><span>English __EN__</span><span>Hindi __HI__</span></div>
<ol class="steps">
<li><b>Assess</b>: free. It reads the database and the page files, judges the debris (what it is, and whether it touches the text), and says what the scan needs.</li>
<li><b>Repair the scan</b>: vision OCR on its pages, with a cap on the spend. The database is not touched.</li>
<li><b>Use the repaired text</b>: a backup first; then its passages are replaced by the repaired text, under the translate lock. The site keeps its last version until you publish the new one.</li>
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
<label class="srcai"><input type="checkbox" id="srcai-__CODE__"/> let the AI judge the editions (about $0.002)</label></div>
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
    if st == "set_aside":
        notes = _repair_html(doc, "", shown, rec)
        bar = ""
    else:
        notes = _repair_html(doc, "", shown, rec)
        bar = "" if 'class="repairbar"' in notes else _repair_bar(doc, "standard")
    page = (_REPAIR_PAGE.replace("__REPAIR_CSS__", _REPAIR_CSS)
            .replace("__NOTES__", notes).replace("__BAR__", bar)
            .replace("__TITLE__", _html.escape(str(title))).replace("__TOTAL__", "{:,}".format(int(total or 0)))
            .replace("__EN__", "{:,}".format(int(en or 0))).replace("__HI__", "{:,}".format(int(hi or 0)))
            .replace("__CODE__", _html.escape(doc)))
    return page.replace("__REPAIR_JS__", _REPAIR_JS)


'''

EDITS = {
    "scripts/dashboard.py": [
        ("/api/jobs/running says the mode", OLD_RUNNING, NEW_RUNNING),
        ("a job record keeps its verdict", OLD_PERSIST, NEW_PERSIST),
        ("a repaired text replaces the notes before it", OLD_NOTES, NEW_NOTES),
    ],
    "scripts/dashboard_static.html": [
        ("the Log reads a verdict in full", OLD_LOGFIN, NEW_LOGFIN),
        ("the Live tab shows the other jobs", OLD_POLLPROG, NEW_POLLPROG),
    ],
    "scripts/ocr_consensus.py": [("look past the asking job", OLD_CONS, NEW_CONS)],
    "scripts/translate_passages.py": [("translate as is", OLD_GUARD, NEW_GUARD)],
    "scripts/corpus_sync.py": [("the register is read", OLD_LIVE, NEW_LIVE),
                               ("a text in repair is not sent", OLD_SYNC, NEW_SYNC)],
}
NEEDS = {"scripts/dashboard.py": "REPAIR_PATH_2026_10_10", "scripts/dashboard_static.html": "REPAIR_PATH_2026_10_10"}


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def swap_block(src: str, problems: list) -> str:
    a = src.find(BLOCK_START)
    b = src.find(BLOCK_END)
    if a < 0 or b < 0 or b < a or src.count(BLOCK_START) != 1:
        problems.append("scripts/dashboard.py: the REPAIR_PATH block was not found once"); return src
    old = src[a:b]
    md5 = hashlib.md5(old.encode("utf-8")).hexdigest()
    if md5 != OLD_BLOCK_MD5:
        problems.append("scripts/dashboard.py: the REPAIR_PATH block is not the one released (md5 %s, want %s); "
                        "nothing is replaced" % (md5, OLD_BLOCK_MD5)); return src
    return src[:a] + NEW_BLOCK + src[b:]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    for need, mark in (("scripts/repair_text.py", MARK), ("scripts/source_desk.py", "SOURCE_DESK_2026_10_11")):
        if not Path(need).exists() or mark.encode() not in Path(need).read_bytes():
            print("REFUSE: %s of 2026-10-11 is not there (it comes with this patcher). Nothing written." % need); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if rel in NEEDS and NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply scripts\\patch_repair_path_2026_10_10.py first" % (rel, NEEDS[rel]))
            continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        if rel == "scripts/dashboard.py":
            out = swap_block(out, problems)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    gi = Path(".gitignore")   # SOURCE_DESK_2026_10_11: fetched editions are large and can be fetched again
    if gi.exists():
        gsrc, gnl = load(gi)
        if "SOURCE_DESK_2026_10_11" not in gsrc:
            add = ("\n# SOURCE_DESK_2026_10_11: editions fetched by scripts/source_desk.py are large and can be fetched\n"
                   "# again (each has its provenance beside it); the search results are regenerated on every search\n"
                   "sources/\ndata/source_desk/\n")
            todo.append((gi, (gsrc.rstrip("\n") + "\n" + add).replace("\n", gnl).encode("utf-8")))
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
        shutil.copy2(p, p.with_name(p.name + ".bak_repairheal_" + stamp))
        t = p.with_name(p.name + ".tmp_repairheal"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Now: ocr_consensus.py, translate_passages.py and corpus_sync.py take it on their next run. Reload the")
    print("dashboard page (Ctrl+F5). dashboard.py takes it when restarted, only when idle: scripts\\restart_dashboard.ps1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
