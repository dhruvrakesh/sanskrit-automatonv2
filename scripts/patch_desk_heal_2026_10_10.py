#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_desk_heal_2026_10_10.py  (2026-10-10)  DESK_HEAL_2026_10_10

What was seen on the desk on 2026-10-10 (docs/DESK_HEAL_2026-10-10.md):

  1. "The translator is not working." It was working: translations of 10 Oct 09:39 ran and ended ok.
     Three things made it look broken.
     a. The Srangam Hub called the dashboard "down (ReadTimeout)". It asked /api/status, the
        dashboard's heaviest read (7.2 s measured: 68 texts, 2,166 inbox pages, 10,903 page files),
        every 5 s with a 2.5 s limit, and the dashboard page itself asked it every 5 s while a job
        ran. The calls overlapped and each slowed the next. /api/status is now worked out once at a
        time, shared by every caller that arrives meanwhile, and kept 10 s (a job that ends clears
        it). /api/health is new: what is running, from memory, in milliseconds, for the hub and the
        scripts. The page no longer starts a status read while one is under way.
     b. "Add Hindi" in the Library for Karan Aagama said "starting..." then "queued", and the run
        ended at once (0.5 s, exit 3): translate_passages.py holds a text whose Tesseract OCR carries
        debris (Latin letters inside the Devanagari) while its page PDFs are in the inbox, so the source
        can be repaired first (TRANSLATE_DEBRIS_GUARD_2026_10_04), and says so. The Library never
        showed it, and History showed it as "fail". The Library now follows the run it
        started and says what it did (held, nothing to do, N of M translated, failed); under each
        text it shows what the last run said when it could not do the work (held; nothing left;
        nearly all left below the OCR quality bar). History shows "held" and "nothing" apart from
        "fail", and a row opens to the run's last lines.
     c. The Usage tab showed "Total API calls: undefined", "Total output chars: 0" and no table: it
        read the old cache's answer, not cost_tracker's (by_engine is an object). It now shows the
        calls, characters and cost by engine, and the last paid calls.
  2. The Queue tab offered "-- select doc --" with nothing in it while the document list had not
     loaded. It now also takes the texts from the last status, and opens on the text being translated.
     History and Usage said "Click Reload" when opened; they now load when opened.
  3. The brain stopped growing. The SanskritMaintenance task (QA, the passage vectors, the editorial
     index, names) skips while the dashboard has any job, and one OCR of 1,983 pages (Yoga Vasistha,
     running since 9 Oct) held every run since 9 Oct 15:00. An OCR job writes page files only, never
     the database, so maintenance now runs beside it; between its steps it looks again and leaves the
     rest for the next tick when a database writer has started (the OCR's own ingest and translation
     stage, or a run started by hand). scripts/maintenance_runner.ps1.

  scripts/dashboard.py, scripts/dashboard_static.html, scripts/maintenance_runner.ps1
  The page and the maintenance task take effect at once (the page on its next load). dashboard.py
  takes effect when the dashboard is restarted: only when it is idle (restart_dashboard.ps1 refuses
  otherwise).

Anchored, all-or-nothing, marker-idempotent per file; keeps line endings; the .py is compiled before
it replaces the original; backups .bak_deskheal_<date>.
  python scripts\\patch_desk_heal_2026_10_10.py --check
  python scripts\\patch_desk_heal_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "DESK_HEAL_2026_10_10"

# ---- scripts/dashboard.py -------------------------------------------------------------------

OLD_STATUS = '''@app.get("/api/status")
def api_status():
    inbox   = pathlib.Path(request.args.get("inbox")   or "inbox")
    raw     = pathlib.Path(request.args.get("raw")     or "data/raw")
    dbp     = pathlib.Path(request.args.get("db")      or "data/context.db")
    exports = pathlib.Path(request.args.get("exports") or "exports")
    return jsonify(build_status(inbox, raw, dbp, exports))
'''

NEW_STATUS = '''# DESK_HEAL_2026_10_10 -------------------------------------------------------------------------
# /api/status is the dashboard's heaviest read: the inbox, data/raw and two queries per text (7.2 s
# on 2026-10-10 with 68 texts, 2,166 inbox pages and 10,903 page files). The page asked for it every
# 5 s while a job ran and the Srangam Hub every 5 s more, so the reads overlapped and each slowed the
# next ("Automaton down (ReadTimeout)" in the hub). It is now worked out once at a time, shared by
# every caller that arrives meanwhile, and kept STATUS_TTL_S seconds; a job that ends clears it.
STATUS_TTL_S = 10.0
_STATUS_LOCK = threading.Lock()
_STATUS_CACHE: dict = {}      # (inbox, raw, db, exports) -> (time, rows)
_STATUS_GEN = [0]             # bumped by _status_forget: a read that began before it is not kept
_STARTED_AT = time.time()


def _status_forget() -> None:
    _STATUS_GEN[0] += 1
    _STATUS_CACHE.clear()


def _status_cached(inbox, raw, dbp, exports):
    key = (str(inbox), str(raw), str(dbp), str(exports))
    hit = _STATUS_CACHE.get(key)
    if hit and time.time() - hit[0] < STATUS_TTL_S:
        return hit[1]
    with _STATUS_LOCK:        # one read at a time; a caller that waited finds the fresh answer here
        hit = _STATUS_CACHE.get(key)
        if hit and time.time() - hit[0] < STATUS_TTL_S:
            return hit[1]
        gen = _STATUS_GEN[0]
        rows = build_status(inbox, raw, dbp, exports)
        if gen == _STATUS_GEN[0]:   # nothing ended or was imported meanwhile
            _STATUS_CACHE[key] = (time.time(), rows)
        return rows


@app.get("/api/status")
def api_status():
    inbox   = pathlib.Path(request.args.get("inbox")   or "inbox")
    raw     = pathlib.Path(request.args.get("raw")     or "data/raw")
    dbp     = pathlib.Path(request.args.get("db")      or "data/context.db")
    exports = pathlib.Path(request.args.get("exports") or "exports")
    if request.args.get("fresh") == "1":
        _status_forget()
    return jsonify(_status_cached(inbox, raw, dbp, exports))


@app.get("/api/health")
def api_health():
    """DESK_HEAL_2026_10_10: is the dashboard up, and what is it doing - from memory only (no disk, no
    database), so it answers in milliseconds while jobs run. For the Srangam Hub and the scripts."""
    now = time.time()
    with JOBS_LOCK:
        running = [{"id": j.id, "kind": j.kind, "doc": j.doc, "state": "running" if j.active else "queued",
                    "elapsed_s": round(now - j.start, 1)} for j in JOBS.values() if j.ok is None]
    active = sum(1 for r in running if r["state"] == "running")
    return jsonify({"ok": True, "mark": "DESK_HEAL_2026_10_10", "pid": os.getpid(),
                    "up_s": round(now - _STARTED_AT, 1),
                    "jobs": {"count": len(running), "active": active, "queued": len(running) - active,
                             "running": running}})
'''

OLD_RUNJOB = '''        job.proc = None  # clear reference
        _persist_job(job)  # write to disk immediately
'''
NEW_RUNJOB = '''        job.proc = None  # clear reference
        _persist_job(job)  # write to disk immediately
        try:
            _status_forget()   # DESK_HEAL_2026_10_10: the counts changed
        except NameError:
            pass
'''

OLD_LIBRARY_DEF = '''@app.get("/library")
def library():
'''
NEW_LIBRARY_DEF = r'''# DESK_HEAL_2026_10_10 -------------------------------------------------------------------------
_HELD_RE = re.compile(r"TRANSLATE_DEBRIS_GUARD|allow-debris|ocr_consensus\.py --doc")
_DONE_RE = re.compile(r"Done\. (\d+)/(\d+) translated \| (\d+) quality-skipped")
_PIPE_TR_RE = re.compile(r"Translate\s+: (OK|FAIL)")    # pipeline_queue.py's summary line


def _library_notes() -> Dict[str, list]:
    """What the last translation run of each text and language said when it could not do the work:
    held by the OCR-debris guard (exit 3: Tesseract debris in the source while its page PDFs are in
    the inbox), nothing left to translate, or nearly all of what is left below the OCR quality bar.
    The Library shows it under the text's buttons, so that a press that cannot help says so first.
    From data/jobs.jsonl, newest first; never the database."""
    notes: Dict[str, list] = {}
    seen = set()
    try:
        recs = _load_job_history(limit=3000)
    except Exception:
        return notes
    held: Dict[tuple, dict] = {}
    for r in recs:
        kind = r.get("kind") or ""
        if kind not in ("translate", "translate_hi", "translate_both", "pipeline"):
            continue
        tail = "%s\n%s" % (r.get("out_tail") or "", r.get("err_preview") or "")
        if kind == "pipeline" and not (_PIPE_TR_RE.search(tail) or _HELD_RE.search(tail)):
            continue                        # a pipeline run that did not translate says nothing here
        doc = r.get("doc") or ""
        langs = ("en", "hi") if kind == "translate_both" else (("hi",) if kind == "translate_hi" else ("en",))
        langs = tuple(x for x in langs if (doc, x) not in seen)
        if not langs:
            continue
        seen.update((doc, x) for x in langs)
        lines = [ln.strip() for ln in tail.strip().splitlines() if ln.strip()]
        detail = " ".join(lines[-3:])[:600]
        try:
            at = time.strftime("%d %b %H:%M", time.localtime(float(r.get("end") or r.get("start") or 0)))
        except (TypeError, ValueError):
            at = "?"
        if r.get("ok") is False and (r.get("rc") == 3 or _HELD_RE.search(tail)):
            for x in langs:
                held[(doc, x)] = {"at": at, "detail": detail}
            continue
        for x in langs:
            name = "Hindi" if x == "hi" else "English"
            text = None
            if kind in ("translate_both", "pipeline"):
                pass                        # several runs in one tail: only a hold is read from it
            elif r.get("ok") and "[NOTHING]" in tail:
                text = ("%s: nothing left that can be translated (%s). What is left is illegible OCR: re-OCR it "
                        "rather than translate." % (name, at))
            elif r.get("ok"):
                m = _DONE_RE.search(tail)
                if m:
                    done, total, skipped = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    if total and skipped >= 0.8 * total:
                        text = ("%s: the last run (%s) translated %d of %d; %d are below the OCR quality bar and "
                                "were not sent. Re-OCR those pages first." % (name, at, done, total, skipped))
            if text:
                notes.setdefault(doc, []).append({"lang": x, "text": text, "detail": detail})
    for doc in sorted({d for d, _ in held}):
        langs = [x for x in ("en", "hi") if (doc, x) in held]
        h = held[(doc, langs[0])]
        what = "English and Hindi" if len(langs) == 2 else ("Hindi" if langs[0] == "hi" else "English")
        text = ("%s held (%s): the OCR of this text carries Tesseract debris (Latin letters inside the "
                "Devanagari) and its page PDFs are in the inbox, so the source is repaired first. Plan the "
                "repair, no spend: python scripts\\ocr_consensus.py --doc %s --threshold 101 "
                "--include-unassessed. To translate anyway, start the dashboard with SA_ALLOW_DEBRIS=1."
                % (what, h["at"], doc))
        notes.setdefault(doc, []).insert(0, {"lang": "both" if len(langs) == 2 else langs[0], "text": text,
                                             "detail": h["detail"]})
    return notes


@app.get("/library")
def library():
'''
OLD_LIBRARY_ERR = '''        con.close()
    except Exception as e:
        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500
'''
NEW_LIBRARY_ERR = '''        con.close()
    except Exception as e:
        return f"<pre>Library error: {_html.escape(str(e))}</pre>", 500
    notes = _library_notes()   # DESK_HEAL_2026_10_10
'''

OLD_ACTS = '''            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
'''
NEW_ACTS = '''            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
            # DESK_HEAL_2026_10_10: what the last run said, when it could not do the work
            for _n in notes.get(code, []):
                if ((_n["lang"] == "en" and pct >= 100) or (_n["lang"] == "hi" and h >= en)
                        or (_n["lang"] == "both" and pct >= 100 and h >= en)):
                    continue
                acts_html += (f'<div class="cardnote" title="{_html.escape(_n["detail"])}">'
                              f'{_html.escape(_n["text"])}</div>')
'''

OLD_CSS = '''.tr-rest:disabled{{opacity:.6;cursor:default}}
'''
NEW_CSS = '''.tr-rest:disabled{{opacity:.6;cursor:default}}
.cardnote{{margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;color:#d9b36a;border-left:2px solid #6b5420;padding:2px 0 2px 7px;cursor:help}}
'''

OLD_TRANSLATE_REST = ("async function translateRest(doc, lang, btn){{\n"
    "  btn.disabled=true; var orig=btn.textContent; btn.textContent='starting\u2026';\n"
    "  try{{\n"
    "    var r=await fetch('/api/translate',{{method:'POST',headers:{{'Content-Type':'application/json'}},\n"
    "      body:JSON.stringify({{doc:doc,lang:lang,limit:100000}})}});\n"
    "    var d=await r.json();\n"
    "    if(d.job){{ _toast('Translating '+(lang==='both'?'EN+\u0939\u093f':lang.toUpperCase())+' for '+doc+' \u2014 watch the Dashboard for progress.'); btn.textContent='queued \u2713'; }}\n"
    "    else{{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; }}\n"
    "  }}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}\n"
    "}}\n")

NEW_TRANSLATE_REST = r'''async function translateRest(doc, lang, btn){{   // DESK_HEAL_2026_10_10: says what the run did, not only that it started
  btn.disabled=true; var orig=btn.textContent; btn.textContent='starting...';
  try{{
    var r=await fetch('/api/translate',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{doc:doc,lang:lang,limit:100000}})}});
    var d=await r.json();
    if(!d.job){{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; return; }}
    btn.textContent='queued...';
    _watchJob(d.job, doc, lang, btn, orig, 0);
  }}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}
}}
function _jobVerdict(j){{
  var out=(j.out||'')+' '+(j.err||'');
  if(j.ok===false && /allow-debris|ocr_consensus|TRANSLATE_DEBRIS_GUARD/.test(out)) return {{word:'held', text:'Held: the OCR of this text carries Tesseract debris and its page PDFs are in the inbox, so the source is repaired first (OCR consensus, no spend). Reload the Library: the note under the text has the command.'}};
  if(j.ok===false && /KILLED/.test(out)) return {{word:'stopped', text:'Stopped by hand.'}};
  if(j.ok===false) return {{word:'failed', text:'It failed: the Dashboard History has the reason.'}};
  if(out.indexOf('[NOTHING]')>=0) return {{word:'nothing to do', text:'Nothing to translate: every verse has it already, or what is left is illegible OCR (re-OCR it rather than translate).'}};
  var m=out.match(/Done[.] ([0-9]+)[/]([0-9]+) translated [|] ([0-9]+) quality-skipped/);
  if(m) return {{word:'done: '+m[1]+' of '+m[2], text:m[1]+' of '+m[2]+' verses translated; '+m[3]+' below the OCR quality bar were not sent.'}};
  return {{word:'done', text:'Done.'}};
}}
async function _watchJob(id, doc, lang, btn, orig, n){{
  try{{
    var j=await (await fetch('/api/job/'+encodeURIComponent(id))).json();
    if(j.state==='done'){{
      var v=_jobVerdict(j); btn.textContent=v.word; btn.title=v.text; btn.disabled=false;
      _toast(doc+' ('+lang.toUpperCase()+'): '+v.text); return;
    }}
    btn.textContent = j.state==='queued' ? 'queued: after the running one' : 'translating...';
    if(n===45) _toast(doc+' ('+lang.toUpperCase()+') is still running: this button follows it; so does the Dashboard.');
  }}catch(e){{ if(n>400) {{ btn.textContent=orig; btn.disabled=false; return; }} }}
  setTimeout(function(){{ _watchJob(id, doc, lang, btn, orig, n+1); }}, n<45 ? 2000 : 10000);
}}
'''

OLD_IMPORT = '''    _invalidate_corpus_cache()
    return results
'''
NEW_IMPORT = '''    _invalidate_corpus_cache()
    try:
        _status_forget()   # DESK_HEAL_2026_10_10: a copied page shows on the next status read
    except NameError:
        pass
    return results
'''

# ---- scripts/dashboard_static.html ----------------------------------------------------------

OLD_USAGE = r'''async function loadUsage() {
  const el = document.getElementById('usageBody');
  el.innerHTML = '<span style="color:var(--muted)">Loading&hellip;</span>';
  try {
    const r = await fetch('/api/usage');
    const d = await r.json();
    if (d.error) { el.innerHTML = '<span style="color:var(--muted)">' + esc(d.error) + '</span>'; return; }
    let html = budgetHtml(d.budget) + '<div style="margin-bottom:8px">' +
      '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">Translation Cache</div>' +
      '<div>Total API calls: <b>' + d.total_calls + '</b></div>' +
      '<div>Total output chars: <b>' + (d.total_out_chars||0).toLocaleString() + '</b></div>' +
      '<div style="margin-top:4px;color:var(--gold)">Est. cost: <b>$' + (d.budget && d.budget.spent_usd != null ? d.budget.spent_usd : d.cost_estimate_usd) + '</b></div>' +
      '<div style="color:var(--muted);font-size:9px;margin-top:2px">' + esc(d.note||'') + '</div></div>';
    if (d.by_engine && d.by_engine.length) {
      html += '<table style="width:100%;border-collapse:collapse"><tr style="color:var(--muted)"><th style="text-align:left">Engine</th><th>Calls</th><th>Chars</th><th>Cost</th></tr>';
      d.by_engine.forEach(function(e) {
        html += '<tr style="border-top:1px solid rgba(255,255,255,.05)">' +
          '<td style="color:var(--gold);padding:3px 0">' + esc(e.engine) + '</td>' +
          '<td style="text-align:center">' + e.calls + '</td>' +
          '<td style="text-align:center">' + (e.out_chars||0).toLocaleString() + '</td>' +
          '<td style="text-align:center">$' + e.cost_usd + '</td></tr>';
      });
      html += '</table>';
    }
    el.innerHTML = html;
  } catch(e) { el.innerHTML = '<span style="color:#f87171">Error: ' + esc(String(e)) + '</span>'; }
}
'''

NEW_USAGE = r'''async function loadUsage() {   // DESK_HEAL_2026_10_10: cost_tracker's summary as it is (by_engine is an object)
  const el = document.getElementById('usageBody');
  el.innerHTML = '<span style="color:var(--muted)">Loading&hellip;</span>';
  try {
    const r = await fetch('/api/usage');
    const d = await r.json();
    if (d.error) { el.innerHTML = '<span style="color:var(--muted)">' + esc(d.error) + '</span>'; return; }
    const eng = d.by_engine || {};
    const rows = Array.isArray(eng) ? eng.slice() : Object.keys(eng).map(function(k) { return Object.assign({engine: k}, eng[k]); });
    rows.sort(function(a, b) { return (+b.cost_usd || 0) - (+a.cost_usd || 0); });
    const sum = function(f) { return rows.reduce(function(a, e) { return a + (+e[f] || 0); }, 0); };
    const usd = function(v) { return '$' + (+v || 0).toFixed(2); };
    const spent = d.budget && d.budget.spent_usd != null ? d.budget.spent_usd : (d.cost_estimate_usd != null ? d.cost_estimate_usd : sum('cost_usd'));
    const calls = rows.length ? sum('calls') : (+d.total_calls || 0);
    let html = budgetHtml(d.budget) + '<div style="margin-bottom:8px">' +
      '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">What the paid steps used</div>' +
      '<div>API calls: <b>' + calls.toLocaleString() + '</b> &middot; passages: <b>' + sum('passages').toLocaleString() + '</b></div>' +
      '<div>Characters sent: <b>' + sum('in_chars').toLocaleString() + '</b> &middot; received: <b>' + (rows.length ? sum('out_chars') : (+d.total_out_chars || 0)).toLocaleString() + '</b></div>' +
      '<div style="margin-top:4px;color:var(--gold)">Spent, all time: <b>' + usd(spent) + '</b></div>' +
      '<div style="color:var(--muted);font-size:9px;margin-top:2px">' + esc(d.note || 'Translation, OCR, pictures, stories, names and the brain, as cost_tracker records them.') + '</div></div>';
    if (rows.length) {
      html += '<table style="width:100%;border-collapse:collapse"><tr style="color:var(--muted)"><th style="text-align:left">Engine</th><th>Calls</th><th>Chars out</th><th>Cost</th></tr>';
      rows.forEach(function(e) {
        html += '<tr style="border-top:1px solid rgba(255,255,255,.05)">' +
          '<td style="color:var(--gold);padding:3px 0;word-break:break-all">' + esc(e.engine) + '</td>' +
          '<td style="text-align:center">' + (+e.calls || 0).toLocaleString() + '</td>' +
          '<td style="text-align:center">' + (+e.out_chars || 0).toLocaleString() + '</td>' +
          '<td style="text-align:center">' + usd(e.cost_usd) + '</td></tr>';
      });
      html += '</table>';
    }
    if (d.recent && d.recent.length) {
      html += '<div style="color:var(--gold);font-weight:600;margin:10px 0 4px">Last paid calls</div>';
      d.recent.slice(0, 10).forEach(function(c) {
        const t = new Date(c.ts);
        const at = isNaN(t) ? String(c.ts || '') : t.toLocaleString('en-IN', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false});
        html += '<div style="display:flex;gap:6px;border-top:1px solid rgba(255,255,255,.04);padding:2px 0">' +
          '<span style="color:var(--muted);white-space:nowrap">' + esc(at) + '</span>' +
          '<span style="color:var(--gold)">' + esc(c.kind || '') + '</span>' +
          '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(c.doc || '') + '</span>' +
          '<span>' + (c.cost_usd ? '$' + (+c.cost_usd).toFixed(4) : '') + '</span>' +
          (c.ok === false ? '<span style="color:#f87171">&#x2717;</span>' : '') + '</div>';
      });
    }
    el.innerHTML = html;
  } catch(e) { el.innerHTML = '<span style="color:#f87171">Error: ' + esc(String(e)) + '</span>'; }
}
'''

OLD_HISTORY = r'''async function loadHistory() {
  const el = document.getElementById('historyBody');
  el.innerHTML = '<span style="color:var(--muted)">Loading&hellip;</span>';
  try {
    const r = await fetch('/api/jobs/history?limit=100');
    const rows = await r.json();
    if (!rows.length) { el.innerHTML = '<span style="color:var(--muted)">No job history yet.</span>'; return; }
    let html = '<table style="width:100%;border-collapse:collapse">' +
      '<tr style="color:var(--muted);border-bottom:1px solid var(--border)"><th style="text-align:left;padding:2px 4px">Kind</th><th style="text-align:left;padding:2px 4px">Doc</th><th style="padding:2px 4px">Status</th><th style="padding:2px 4px">Duration</th><th style="padding:2px 4px">When</th></tr>';
    rows.forEach(function(j) {
      const when = j.start ? new Date(j.start * 1000).toLocaleString('en-IN', {hour12:false,month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
      const dur  = j.duration_s ? (j.duration_s >= 60 ? Math.round(j.duration_s/60) + 'm' : j.duration_s + 's') : '';
      const ok   = j.ok === true ? '<span style="color:#4ade80">&#x2713; ok</span>' : j.ok === false ? '<span style="color:#f87171">&#x2717; fail</span>' : '<span style="color:var(--muted)">?</span>';
      html += '<tr style="border-bottom:1px solid rgba(255,255,255,.04)">' +
        '<td style="padding:3px 4px;color:var(--gold)">' + esc(j.kind||'') + '</td>' +
        '<td style="padding:3px 4px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(j.doc||'') + '</td>' +
        '<td style="padding:3px 4px;text-align:center">' + ok + '</td>' +
        '<td style="padding:3px 4px;text-align:center;color:var(--muted)">' + dur + '</td>' +
        '<td style="padding:3px 4px;color:var(--muted)">' + when + '</td></tr>';
    });
    html += '</table>';
    el.innerHTML = html;
  } catch(e) { el.innerHTML = '<span style="color:#f87171">Error: ' + esc(String(e)) + '</span>'; }
}
'''

NEW_HISTORY = r'''// DESK_HEAL_2026_10_10: a run held on purpose, or one with nothing to do, is not a failure; a row opens
// to the run's last lines
function histStatus(j) {
  const out = String(j.out_tail || '') + '\n' + String(j.err_preview || '');
  if (j.ok === true && /\[NOTHING\]/.test(out)) return '<span style="color:var(--muted)" title="Nothing was left to do">&#x2713; nothing</span>';
  if (j.ok === true) return '<span style="color:#4ade80">&#x2713; ok</span>';
  if (j.ok === false && (j.rc === 3 || /allow-debris|ocr_consensus/.test(out))) return '<span style="color:var(--gold)" title="Held on purpose: open the row for why">&#x23F8; held</span>';
  if (j.ok === false && /KILLED/.test(out)) return '<span style="color:var(--muted)">&#x25A0; stopped</span>';
  if (j.ok === false) return '<span style="color:#f87171">&#x2717; fail</span>';
  return '<span style="color:var(--muted)">?</span>';
}
function histToggle(i) {
  const r = document.getElementById('hist-d-' + i);
  if (r) r.style.display = r.style.display === 'none' ? '' : 'none';
}
async function loadHistory() {
  const el = document.getElementById('historyBody');
  el.innerHTML = '<span style="color:var(--muted)">Loading&hellip;</span>';
  try {
    const r = await fetch('/api/jobs/history?limit=100');
    const rows = await r.json();
    if (!rows.length) { el.innerHTML = '<span style="color:var(--muted)">No job history yet.</span>'; return; }
    let html = '<table style="width:100%;border-collapse:collapse">' +
      '<tr style="color:var(--muted);border-bottom:1px solid var(--border)"><th style="text-align:left;padding:2px 4px">Kind</th><th style="text-align:left;padding:2px 4px">Doc</th><th style="padding:2px 4px">Status</th><th style="padding:2px 4px">Duration</th><th style="padding:2px 4px">When</th></tr>';
    rows.forEach(function(j, i) {
      const when = j.start ? new Date(j.start * 1000).toLocaleString('en-IN', {hour12:false,month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
      const dur  = j.duration_s ? (j.duration_s >= 60 ? Math.round(j.duration_s/60) + 'm' : j.duration_s + 's') : '';
      const last = String((j.out_tail || '') + '\n' + (j.err_preview || '')).trim().split(/\r?\n/).filter(function(x) { return x.trim(); }).slice(-6).join('\n');
      html += '<tr style="border-bottom:1px solid rgba(255,255,255,.04);cursor:pointer" title="Open: the run\'s last lines" onclick="histToggle(' + i + ')">' +
        '<td style="padding:3px 4px;color:var(--gold)">' + esc(j.kind||'') + '</td>' +
        '<td style="padding:3px 4px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(j.doc||'') + '</td>' +
        '<td style="padding:3px 4px;text-align:center">' + histStatus(j) + '</td>' +
        '<td style="padding:3px 4px;text-align:center;color:var(--muted)">' + dur + '</td>' +
        '<td style="padding:3px 4px;color:var(--muted)">' + when + '</td></tr>' +
        '<tr id="hist-d-' + i + '" style="display:none"><td colspan="5" style="padding:4px 6px 8px;color:var(--muted);white-space:pre-wrap;word-break:break-word;font-family:JetBrains Mono,monospace;font-size:9px">' +
        esc(j.doc || '') + '\n' + esc(last || '(no output kept)') + '</td></tr>';
    });
    html += '</table>';
    el.innerHTML = html;
  } catch(e) { el.innerHTML = '<span style="color:#f87171">Error: ' + esc(String(e)) + '</span>'; }
}
'''

OLD_REFRESH = r'''async function refresh() {
  try {
    const r = await fetch('/api/status?inbox=' + encodeURIComponent(cfg.inbox) +
      '&raw=' + encodeURIComponent(cfg.raw) +
      '&db=' + encodeURIComponent(cfg.db) +
      '&exports=' + encodeURIComponent(cfg.exports));
    renderPipeline(await r.json());
  } catch(e) { toast('Refresh failed: ' + e, 'fail'); }
}
'''

NEW_REFRESH = r'''// DESK_HEAL_2026_10_10: never two status reads at once. A call that comes while one runs is kept and
// run once after it (the dashboard keeps the answer 10 s, so that is cheap); refresh(true), the
// Refresh button and an import, asks the dashboard to work it out again.
let _refreshing = false, _refreshAgain = false, _refreshFresh = false;
async function refresh(force) {
  if (force === true) _refreshFresh = true;
  if (_refreshing) { _refreshAgain = true; return; }
  _refreshing = true;
  const fresh = _refreshFresh; _refreshFresh = false;
  try {
    const r = await fetch('/api/status?inbox=' + encodeURIComponent(cfg.inbox) +
      '&raw=' + encodeURIComponent(cfg.raw) +
      '&db=' + encodeURIComponent(cfg.db) +
      '&exports=' + encodeURIComponent(cfg.exports) + (fresh ? '&fresh=1' : ''));
    renderPipeline(await r.json());
  } catch(e) { toast('Refresh failed: ' + e, 'fail'); }
  finally {
    _refreshing = false;
    if (_refreshAgain) { _refreshAgain = false; refresh(); }
  }
}
'''

OLD_REFRESH_BTN = '''    <button class="btn-refresh" onclick="refresh()">&#x27F3; Refresh</button>
'''
NEW_REFRESH_BTN = '''    <button class="btn-refresh" onclick="refresh(true)">&#x27F3; Refresh</button>
'''
OLD_IMPORT_REFRESH_1 = '''    setTimeout(function(){ refresh(); if (jumpDoc) setTimeout(function(){ flashDoc(jumpDoc); }, 900); }, 1500);
'''
NEW_IMPORT_REFRESH_1 = '''    setTimeout(function(){ refresh(true); if (jumpDoc) setTimeout(function(){ flashDoc(jumpDoc); }, 900); }, 1500);
'''
OLD_IMPORT_REFRESH_2 = '''    setTimeout(function(){ refresh(); if (jumpDoc) setTimeout(function(){ flashDoc(jumpDoc); }, 900); }, 1200);
'''
NEW_IMPORT_REFRESH_2 = '''    setTimeout(function(){ refresh(true); if (jumpDoc) setTimeout(function(){ flashDoc(jumpDoc); }, 900); }, 1200);
'''

OLD_TABS = r'''  if (name === 'queue') populateQueueDocSelect();
  if (name === 'qa') loadQa();
}
'''
NEW_TABS = r'''  if (name === 'queue') populateQueueDocSelect();
  if (name === 'qa') loadQa();
  if (name === 'history') loadHistory();   // DESK_HEAL_2026_10_10: a tab shows its content when opened
  if (name === 'usage') loadUsage();
}
'''

OLD_EMPTY = '''    <div id="pipelineWrap">
      <div class="empty-state">
        <div class="e-icon">&#x1F4C2;</div>
        <h3>No documents in inbox</h3>
        <p>Use the corpus browser on the left to select scriptures from the D: drive and import them.</p>
'''
NEW_EMPTY = '''    <div id="pipelineWrap">
      <div class="empty-state">
        <div class="e-icon">&#x1F4C2;</div>
        <h3>Loading the documents&hellip;</h3>
        <p>The list takes a few seconds while jobs run. <!-- DESK_HEAL_2026_10_10 --></p>
'''

OLD_QUEUE = r'''function populateQueueDocSelect() {
  const sel = document.getElementById('queueDocSelect');
  if (sel.options.length > 1) return; // already populated
  // Pull from pipeline table rows
  document.querySelectorAll('.pipeline-table tr[data-doc]').forEach(function(tr) {
    const doc = tr.getAttribute('data-doc');
    if (doc) {
      const opt = document.createElement('option');
      opt.value = doc;
      opt.textContent = doc;
      sel.appendChild(opt);
    }
  });
  // Also try from corpusData
  if (window.corpusData) {
    const existing = new Set(Array.from(sel.options).map(function(o){ return o.value; }));
    (window.corpusData.docs || []).forEach(function(d) {
      if (d.code && !existing.has(d.code)) {
        const opt = document.createElement('option');
        opt.value = d.code; opt.textContent = d.code;
        sel.appendChild(opt);
      }
    });
  }
}
'''

NEW_QUEUE = r'''function populateQueueDocSelect() {   // DESK_HEAL_2026_10_10: also from the last status; opens on the text being translated
  const sel = document.getElementById('queueDocSelect');
  const have = new Set(Array.from(sel.options).map(function(o) { return o.value; }));
  const add = function(doc) {
    if (!doc || have.has(doc)) return;
    const opt = document.createElement('option');
    opt.value = doc; opt.textContent = doc;
    sel.appendChild(opt); have.add(doc);
  };
  document.querySelectorAll('.pipeline-table tr[data-doc]').forEach(function(tr) { add(tr.getAttribute('data-doc')); });
  (window._lastPipeRows || []).forEach(function(r) { add(r && r.doc); });
  if (window.corpusData) (window.corpusData.docs || []).forEach(function(d) { add(d && d.code); });
  if (sel.value) return;
  fetch('/api/jobs/running').then(function(r) { return r.json(); }).then(function(d) {
    const t = (d.running || []).find(function(j) { return /^translate|pipeline/.test(j.kind || '') && j.state === 'running'; });
    if (t && !sel.value && have.has(t.doc)) { sel.value = t.doc; loadQueue(); }
  }).catch(function() {});
}
'''

# ---- scripts/maintenance_runner.ps1 ---------------------------------------------------------

OLD_GUARD = '''    $busy = [int]$r.count
    if ($busy -gt 0) { Log "SKIP: dashboard busy ($busy job(s) running/queued)"; exit 0 }
    Log "dashboard idle (0 jobs) - ok to maintain"
'''
NEW_GUARD = '''    $busy = [int]$r.count
    # DESK_HEAL_2026_10_10: an OCR job writes page files only, never the database, so it does not hold
    # maintenance. One OCR of 1,983 pages (Yoga Vasistha) held every run from 2026-10-09 15:00: no new
    # vectors, QA or names for a day.
    $writers = @(@($r.running) | Where-Object { $_.kind -ne "ocr" })
    if ($writers.Count -gt 0) { Log "SKIP: dashboard busy ($busy job(s) running/queued)"; exit 0 }
    if ($busy -gt 0) { Log "dashboard runs $busy OCR job(s) only (page files, not the database) - ok to maintain" }
    else { Log "dashboard idle (0 jobs) - ok to maintain" }
'''

OLD_LOGFN = '''function Log($m) {
    Add-Content -Path $log -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m)
}
'''
NEW_LOGFN = OLD_LOGFN + '''
# DESK_HEAL_2026_10_10: the guard below lets maintenance run beside an OCR job. When that OCR ends the
# dashboard may start its ingest and translation stage, and a person may start a run meanwhile. So
# between the steps it looks again, and leaves the rest for the next tick when a database writer has
# started. (A writer that starts inside a step waits on SQLite's lock: WAL, busy_timeout 30-60 s.)
function Test-Writer($after) {
    try {
        $now = Invoke-RestMethod -Uri "http://127.0.0.1:5057/api/jobs/running" -TimeoutSec 6
    } catch {
        return $false
    }
    $w = @(@($now.running) | Where-Object { $_.kind -ne "ocr" })
    if ($w.Count -eq 0) { return $false }
    $what = (@($w | Select-Object -First 3 | ForEach-Object { [string]$_.kind + " " + [string]$_.doc }) -join ", ")
    Log ("SKIP rest after step " + $after + ": the dashboard started " + $what + " - the next tick goes on")
    return $true
}
'''

OLD_STEP_A = '''    Log ("STEP a qa_scan      {0:n0}s" -f ((Get-Date) - $ta).TotalSeconds)
'''
NEW_STEP_A = OLD_STEP_A + '''    if (Test-Writer "a") { exit 0 }   # DESK_HEAL_2026_10_10
'''
OLD_STEP_B = '''    Log ("STEP b embeddings   {0:n0}s" -f ((Get-Date) - $tb).TotalSeconds)
'''
NEW_STEP_B = OLD_STEP_B + '''    if (Test-Writer "b") { exit 0 }   # DESK_HEAL_2026_10_10
'''
OLD_STEP_B2 = '''        Log ("STEP b2 brain items SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $tb2).TotalSeconds, $_)
    }
'''
NEW_STEP_B2 = OLD_STEP_B2 + '''    if (Test-Writer "b2") { exit 0 }   # DESK_HEAL_2026_10_10
'''

EDITS = {
    "scripts/dashboard.py": [
        ("api_status", OLD_STATUS, NEW_STATUS),
        ("_run_job", OLD_RUNJOB, NEW_RUNJOB),
        ("_do_import", OLD_IMPORT, NEW_IMPORT),
        ("library notes", OLD_LIBRARY_DEF, NEW_LIBRARY_DEF),
        ("library error", OLD_LIBRARY_ERR, NEW_LIBRARY_ERR),
        ("library acts", OLD_ACTS, NEW_ACTS),
        ("library css", OLD_CSS, NEW_CSS),
        ("library translateRest", OLD_TRANSLATE_REST, NEW_TRANSLATE_REST),
    ],
    "scripts/dashboard_static.html": [
        ("usage", OLD_USAGE, NEW_USAGE),
        ("history", OLD_HISTORY, NEW_HISTORY),
        ("refresh", OLD_REFRESH, NEW_REFRESH),
        ("first empty state", OLD_EMPTY, NEW_EMPTY),
        ("queue select", OLD_QUEUE, NEW_QUEUE),
        ("tabs load on open", OLD_TABS, NEW_TABS),
        ("refresh button", OLD_REFRESH_BTN, NEW_REFRESH_BTN),
        ("refresh after import (1)", OLD_IMPORT_REFRESH_1, NEW_IMPORT_REFRESH_1),
        ("refresh after import (2)", OLD_IMPORT_REFRESH_2, NEW_IMPORT_REFRESH_2),
    ],
    "scripts/maintenance_runner.ps1": [
        ("idle guard", OLD_GUARD, NEW_GUARD),
        ("look again: function", OLD_LOGFN, NEW_LOGFN),
        ("look again after a", OLD_STEP_A, NEW_STEP_A),
        ("look again after b", OLD_STEP_B, NEW_STEP_B),
        ("look again after b2", OLD_STEP_B2, NEW_STEP_B2),
    ],
}


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        if rel.endswith(".ps1") and any(ord(ch) > 127 for ch in out):
            problems.append("%s would not be ASCII (Windows PowerShell 5.1 reads it in the system code page)" % rel)
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
        shutil.copy2(p, p.with_name(p.name + ".bak_deskheal_" + stamp))
        t = p.with_name(p.name + ".tmp_deskheal"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("The page takes it on its next load and the maintenance task at its next run. dashboard.py takes it")
    print("when the dashboard is restarted, only when idle: scripts\\restart_dashboard.ps1 (it refuses while jobs run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
