#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_translation_desk_2026_10_17.py  (2026-10-17)  TRANSLATION_DESK_2026_10_17

Asked on 17 Oct: the dashboard's translation offers no path to the scholarly English, nor a page for the texts well
translated or on the way to it. scripts/translation_desk.py (new, this release) holds the rules; this patch wires them.

scripts/dashboard.py (needs BENCH_GOLD_2026_10_16):
  - /desk: every text by its stage (the scholarly edition, ready to translate, translated: to judge, done, the reading
    first, not charted), from the path chart (data/text_path.json), the register and the scholarly English, with its
    one next step; the caps; Chart the path again (free);
  - /desk/<doc>: a text's whole state; the working English's button where it is ready; the scholarly English's steps:
    Plan them (the dry run of scholar_translate.py with the standard flags of 15 Oct, free), Run (the plan's own
    --max-usd, at most $12.00 a press, it asks first), Status, Report, Triage (free); not offered for a text withdrawn
    or set aside, or whose path says the reading comes first; --held-ok for a text in repair;
  - /api/desk/scholar: those steps as jobs of kind "scholar", doc "scholar:<doc>";
  - the guard: /api/translate and /api/pipeline/translate-doc answer 409 with the path's reason and next step for a
    text whose path says the reading comes first (repair the scan, use the repair, ingest, find a source, retire, or a
    re-ingest of changed pages first), unless {"force": true}; the Library's button asks and goes on;
  - /api/status: each row with "path" (its path, the next step, the chart's date, held or not);
  - the Library's header: a link to the desk.
scripts/dashboard_static.html (needs BENCH_DUEL_2026_10_16):
  - a Desk link in the header; on each row a chip of its path ("the reading first: repair the scan", linked to its page
    on the desk); the Translate and Start buttons ask before going on with a guarded text; Translate ALL leaves the
    guarded texts and says which.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_transdesk_<date>. No database change. Needs scripts/translation_desk.py (this release).
  python scripts\\patch_translation_desk_2026_10_17.py --check
  python scripts\\patch_translation_desk_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "TRANSLATION_DESK_2026_10_17"
NEEDS = {"scripts/dashboard.py": "BENCH_GOLD_2026_10_16", "scripts/dashboard_static.html": "BENCH_DUEL_2026_10_16"}
FILES = list(NEEDS)
TAG = "transdesk"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, r'''def _status_decorate(rows: list, dbp) -> list:
''', r'''# TRANSLATION_DESK_2026_10_17 -------------------------------------------------------------------------------------
# The translation desk (scripts/translation_desk.py holds its rules): /desk, every text by its stage (the scholarly
# edition, ready to translate, translated, done, the reading first), from the path chart, the register and the
# scholarly English; /desk/<doc>, a text's whole state and its steps, the scholarly English among them (plan it free,
# then run it, capped; report; triage); the guard on the working translation (_desk_guard) a text whose path says the
# reading comes first. Read only, but for the jobs its buttons start.
DESK_DB = str(ROOT / "data" / "context.db")   # the register beside it: data/source_verdicts.jsonl
_DESK_CACHE = {"at": 0.0, "res": None}


def _desk_titles() -> dict:
    try:
        return dict((json.loads((ROOT / "configs" / "doc_titles.json").read_text(encoding="utf-8")) or {}).get("titles")
                    or {})
    except (OSError, ValueError, AttributeError):
        return {}


def _desk_counts(con) -> dict:
    """{doc: {"mula", "en"}}: the verse passages of each text and those with working English."""
    tt = ("COALESCE(p.text_type, 'mula')" if "text_type" in {r_[1] for r_ in con.execute("PRAGMA table_info(passages)")}
          else "'mula'")
    out = {}
    for doc, n, en in con.execute("SELECT d.code, COUNT(*), SUM(CASE WHEN TRIM(COALESCE(p.translation, '')) <> '' THEN 1 "
                                  "ELSE 0 END) FROM passages p JOIN docs d ON d.id = p.doc_id WHERE %s = 'mula' "
                                  "GROUP BY d.code" % tt):
        out[doc] = {"mula": int(n or 0), "en": int(en or 0)}
    return out


def _desk_state(fresh: bool = False) -> dict:
    """{"chart_at", "age", "rows": [...], "caps", "running"}: every text with its stage. Cached 30 s; never raises."""
    now_ = time.time()
    if not fresh and _DESK_CACHE["res"] is not None and now_ - _DESK_CACHE["at"] < 30:
        return _DESK_CACHE["res"]
    import translation_desk as td
    res = {"rows": [], "chart_at": "", "age": None, "caps": {}, "error": None}
    try:
        chart = td.load_path(PATH_FILE)
        res["chart_at"], res["age"] = chart["at"], td.chart_age_days(chart["at"])
        reg = _source_verdicts(pathlib.Path(DESK_DB).parent)
        cover, counts = {}, {}
        dbp = pathlib.Path(DESK_DB)
        if dbp.exists():
            con = sqlite3.connect(dbp.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
            try:
                cover = _scholar_cover(con)
                counts = _desk_counts(con)
                try:
                    import claude_engine as _ce
                    c = _ce.credit(con)
                    res["caps"]["credit_left"] = max(0.0, float(c["left"]))
                    res["caps"]["credit_expires"] = c.get("expires")
                except Exception:
                    pass
                try:
                    b = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
                    if b:
                        res["caps"]["cap_left"] = max(0.0, float(b[0] or 0) - float(b[1] or 0))
                        res["caps"]["paused"] = bool(b[2])
                except sqlite3.Error:
                    pass
            finally:
                con.close()
        titles = _desk_titles()
        docs = set(chart["texts"]) | set(cover) | set(counts)
        for doc in sorted(docs):
            if doc.endswith("-RETIRED"):
                continue
            prow = chart["texts"].get(doc)
            cv = cover.get(doc) or {}
            rg = reg.get(doc) or {}
            n = counts.get(doc) or {}
            st = td.stage_of(prow, cv, rg)
            res["rows"].append({
                "doc": doc, "title": titles.get(doc) or doc, "stage": st, "path": (prow or {}).get("path"),
                "why": (prow or {}).get("why") or "", "next_path": list((prow or {}).get("next") or []),
                "cost": float((prow or {}).get("cost") or 0.0), "held": rg.get("status"), "held_reason": rg.get("reason"),
                "mula": int(n.get("mula") or 0), "en": int(n.get("en") or 0),
                "scholar": {k: cv.get(k, 0) for k in ("verses", "passed", "flagged", "source_doubt", "accepted",
                                                      "rejected", "stale")},
                "engines": dict(cv.get("engines") or {}), "spent": float(cv.get("spent") or 0.0),
                "next": td.next_step(st, prow, cv, int(n.get("mula") or 0)),
                "guard": td.guard(prow, rg, chart["at"])})
    except Exception as ex:   # the dashboard is never stopped by the desk
        res["error"] = "%s: %s" % (type(ex).__name__, str(ex)[:300])
    _DESK_CACHE.update(at=now_, res=res)
    return res


def _desk_guard(doc: str):
    """TRANSLATION_DESK_2026_10_17: why a working translation of doc is held now (its path says the reading comes
    first), or None. Never raises: on any error nothing is held."""
    try:
        import translation_desk as td
        chart = td.load_path(PATH_FILE)
        return td.guard(chart["texts"].get(doc), _source_verdicts(pathlib.Path(DESK_DB).parent).get(doc), chart["at"])
    except Exception:
        return None


def _desk_jobs(doc: str = None) -> list:
    """The desk's scholarly jobs running or waiting (kind "scholar", doc "scholar:<doc>")."""
    with JOBS_LOCK:
        return [{"id": j.id, "doc": j.doc, "mode": j.mode, "state": "running" if j.active else "queued",
                 "elapsed_s": round(time.time() - j.start, 1)} for j in JOBS.values()
                if j.kind == "scholar" and j.ok is None and (doc is None or j.doc == "scholar:" + doc)]


_DESK_CSS = """<style>/* TRANSLATION_DESK_2026_10_17 */
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#8a7d66;--red:#e8a3a3;--green:#9fd8b5;--amber:#e6c27a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--cream);font:14px/1.5 'Inter',system-ui,sans-serif}
header{background:var(--card);border-bottom:1px solid var(--border);padding:12px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}header a:hover{color:var(--gold)}
header h1{font-size:17px;color:var(--gold);margin:0;font-weight:700}
main{max-width:1180px;margin:0 auto;padding:16px}
.intro{color:var(--muted);font-size:12.5px;margin:0 0 10px;max-width:980px}
.caps{font-size:12.5px;margin:6px 0 14px}
h2{font-size:14px;color:var(--gold);margin:22px 0 6px;font-weight:600}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:760px}
th{text-align:left;color:var(--muted);font-weight:600;font-size:11.5px;padding:6px 8px;border-bottom:1px solid var(--border);background:var(--card)}
td{padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top;font-size:12.5px}
a{color:var(--gold)}td a{color:var(--gold);text-decoration:none}
.chip{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10.5px;margin:0 4px 2px 0}
.c-edition{background:rgba(201,149,42,.18);color:var(--gold)}.c-ready{background:rgba(120,200,160,.15);color:var(--green)}
.c-source{background:rgba(220,90,90,.15);color:var(--red)}.c-judged{background:rgba(120,160,200,.15);color:#a9c7e8}
.c-done{background:rgba(160,160,160,.15);color:#cfc6b4}.c-uncharted{background:rgba(160,160,160,.1);color:var(--muted)}
.small{font-size:11.5px;color:var(--muted)}
.btn{background:var(--card2);border:1px solid var(--border);color:var(--cream);border-radius:7px;padding:6px 11px;font:inherit;font-size:12px;font-weight:600;cursor:pointer}
.btn:hover{border-color:var(--gold);color:var(--gold)}.btn.go{border-color:var(--gold);color:var(--gold)}.btn:disabled{opacity:.5;cursor:default}
.box{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin:12px 0}
.box h3{margin:0 0 6px;font-size:13px;color:var(--gold)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
input[type=text],input[type=number]{background:var(--card2);color:var(--cream);border:1px solid var(--border);border-radius:6px;padding:5px 7px;font:inherit;font-size:12.5px;width:110px}
pre{white-space:pre-wrap;font-size:11px;line-height:1.4;background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:8px;max-height:300px;overflow:auto;display:none}
.out{font-size:12.5px;margin:6px 0;color:var(--amber)}
.warn{color:var(--amber)}
</style>"""


def _desk_head(title: str) -> str:
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            'initial-scale=1"><title>%s</title>%s</head><body><header><a href="/">&larr; Dashboard</a><a href="/desk">'
            'The desk</a><a href="/library">Library</a><a href="/scholar">Scholarly English</a><a href="/path">The path</a>'
            '<a href="/sources">Sources &amp; repairs</a><a href="/benchmarks">Benchmarks</a><h1>%s</h1></header><main>'
            % (title, _DESK_CSS, title))


def _desk_caps_line(caps: dict) -> str:
    if not caps:
        return ""
    return ('<p class="caps">The Claude credit: <b>%s</b> left%s. The spend cap (Google): <b>%s</b> left%s.</p>' % (
        _bm1_usd(caps.get("credit_left")), (" (it expires %s)" % caps["credit_expires"]) if caps.get("credit_expires")
        else "", _bm1_usd(caps.get("cap_left")), ", paused" if caps.get("paused") else ""))


def _desk_chart_line(s: dict) -> str:
    import html as _h
    age = s.get("age")
    when = ("charted %s (%s)" % (_h.escape(str(s.get("chart_at") or "")[:16].replace("T", " ")),
                                 "today" if age is not None and age < 1 else "%d days ago" % int(age or 0))
            if s.get("chart_at") else "not charted yet")
    return ('<p class="caps">The path of every text: %s%s. <button class="btn" onclick="deskChart(this)">Chart the path '
            'again (free)</button> <span class="small" id="chartout"></span></p>' % (
                when, '; <span class="warn">old: chart it again</span>' if age is not None and age >= 3 else ""))


_DESK_JS = r"""<script>/* TRANSLATION_DESK_2026_10_17 */
var _DK_NL = String.fromCharCode(10);
async function deskChart(btn){
  btn.disabled = true; var o = document.getElementById('chartout'); o.textContent = 'charting...';
  try{
    var r = await fetch('/api/repair', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({step: 'path_all'})});
    var d = await r.json();
    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); btn.disabled = false; return; }
    _dkWatch(d.job, function(j){ o.textContent = j.ok ? 'charted: the page reads it again' : 'it did not finish (the History has why)'; if (j.ok) setTimeout(function(){ location.reload(); }, 1500); }, null);
  }catch(e){ o.textContent = 'Request failed: ' + e; btn.disabled = false; }
}
async function _dkWatch(id, done, pre){
  try{
    var j = await (await fetch('/api/job/' + encodeURIComponent(id))).json();
    if (j.error){ done({ok: false, out: '', err: j.error}); return; }
    if (pre){ var ls = String(j.out || '').split(_DK_NL).filter(function(l){ return l.trim(); }); pre.style.display = 'block'; pre.textContent = ls.slice(-22).join(_DK_NL); pre.scrollTop = pre.scrollHeight; }
    if (j.state === 'done'){ done(j); return; }
    setTimeout(function(){ _dkWatch(id, done, pre); }, 2500);
  }catch(e){ setTimeout(function(){ _dkWatch(id, done, pre); }, 5000); }
}
function _dkLine(out, tag){
  var v = ''; String(out || '').split(_DK_NL).forEach(function(l){ if (l.indexOf(tag) === 0) v = l.slice(tag.length); }); return v;
}
async function deskStep(doc, step, btn){
  var o = document.getElementById('dkout'), pre = document.getElementById('dklog');
  var pages = (document.getElementById('dkpages') || {}).value || '', limit = +((document.getElementById('dklimit') || {}).value || 40);
  var body = {doc: doc, step: step, pages: pages, limit: limit};
  if (step === 'run'){
    var cap = +(btn.getAttribute('data-cap') || 0);
    if (!confirm('Run the scholarly English of ' + doc + (pages ? ', pages ' + pages : '') + ', ' + limit + ' verse(s): Claude Sonnet 5.5 drafts and criticises, Claude Opus 5.5 audits one sentence in ten, judge-v1 reads each. It spends at most $' + cap.toFixed(2) + ' (the Claude credit, the judge on the spend cap) and stops before spending more. Go?')) return;
    body.max_usd = cap;
  }
  var all = document.querySelectorAll('.dkbtn'); for (var i = 0; i < all.length; i++) all[i].disabled = true;
  o.textContent = 'starting...';
  try{
    var r = await fetch('/api/desk/scholar', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); for (var k = 0; k < all.length; k++) all[k].disabled = false; return; }
    o.textContent = (step === 'plan' ? 'planning (free)' : step === 'run' ? 'running' : step) + '...';
    _dkWatch(d.job, function(j){
      var out = String(j.out || '') + _DK_NL + String(j.err || '');
      var v = _dkLine(out, 'VERDICT: '), n = _dkLine(out, 'NEXT: '), rf = _dkLine(out, 'REFUSE: ');
      o.textContent = (rf ? 'Refused: ' + rf + '. ' : '') + (v || (j.ok ? 'done' : 'it did not finish: the History has its last lines'));
      for (var k2 = 0; k2 < all.length; k2++) all[k2].disabled = false;
      var rb = document.getElementById('dkrun');
      if (step === 'plan' && rb){
        var m = n.match(/--max-usd ([0-9.]+)/);
        if (m && n.indexOf('--yes') >= 0){
          var cap = +m[1];
          rb.setAttribute('data-cap', String(cap));
          rb.textContent = 'Run these verses: at most $' + cap.toFixed(2);
          rb.style.display = cap <= 12 ? 'inline-block' : 'none';
          if (cap > 12) o.textContent += '  Above the $12.00 one press may spend: plan fewer verses, or run by hand: ' + n;
        } else { rb.style.display = 'none'; }
      }
      if (step === 'run' && j.ok) setTimeout(function(){ location.reload(); }, 4000);
    }, pre);
  }catch(e){ o.textContent = 'Request failed: ' + e; for (var k3 = 0; k3 < all.length; k3++) all[k3].disabled = false; }
}
async function deskTranslate(doc, btn){
  if (!confirm('The working English of ' + doc + ': one pass, gemini-2.5-flash, the verses not yet translated. Go?')) return;
  btn.disabled = true;
  var r = await fetch('/api/translate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({doc: doc, lang: 'en', limit: 0})});
  var d = await r.json();
  document.getElementById('dkout').textContent = d.job ? 'Started: the main dashboard\'s job log follows it.' : ('Could not start: ' + (d.error || 'unknown'));
}
(function(){ var r = document.getElementById('dkrunning'); if (r && r.getAttribute('data-job')){ _dkWatch(r.getAttribute('data-job'), function(){ location.reload(); }, document.getElementById('dklog')); } })();
</script>"""


def _desk_sc_cell(r: dict) -> str:
    s = r["scholar"]
    if not s.get("verses"):
        return '<span class="small">-</span>'
    return ('%d of %d <span class="small">(%d passed, %d flagged, %d doubts%s)</span>' % (
        s["verses"], max(r["mula"], s["verses"]), s.get("passed", 0), s.get("flagged", 0), s.get("source_doubt", 0),
        (", %d stale" % s["stale"]) if s.get("stale") else ""))


@app.get("/desk")
def desk_page():
    """TRANSLATION_DESK_2026_10_17: every text by its stage, with its one next step."""
    import html as _h
    import translation_desk as td
    e = _h.escape
    s = _desk_state(fresh=request.args.get("fresh") == "1")
    h = [_desk_head("The translation desk"),
         '<p class="intro">Every text by its stage, from the path of every text (/path), the register (withdrawn, set '
         'aside, in repair) and the scholarly English. The working English is the draft every text gets (one pass, '
         'gemini-2.5-flash); the scholarly English is the edition (Claude Sonnet 5.5 drafts and criticises, with notes; '
         'Opus audits one sentence in ten; judge-v1 reads each), begun from a text\'s own page here. What the benchmarks '
         'found and the standard way: docs/SOP_TRANSLATION_2026-10-17.md.</p>',
         _desk_caps_line(s.get("caps") or {}), _desk_chart_line(s)]
    if s.get("error"):
        h.append('<p class="warn">The desk could not read everything: %s</p>' % e(s["error"]))
    rows = s.get("rows") or []
    for key, label in td.STAGES:
        rs = [r for r in rows if r["stage"] == key]
        if not rs:
            continue
        rs.sort(key=lambda r: (-r["scholar"].get("verses", 0), -r["mula"]))
        body = "".join(
            '<tr><td><a href="/desk/%s">%s</a>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="small">%s</td></tr>' % (
                e(r["doc"], quote=True), e(r["title"]),
                ('<br><span class="small">%s</span>' % e(r["doc"])) if r["title"] != r["doc"] else "",
                ('<span class="chip c-%s">%s</span>' % (key, e(td.PATH_LABEL.get(r["path"] or "", r["path"] or "uncharted"))))
                + (('<span class="chip c-source">%s</span>' % e(r["held"].replace("_", " "))) if r.get("held") in td.HOLDS
                   or (r.get("held") == "in_repair" and r.get("path") != "in_repair") else ""),
                ("%d of %d" % (r["en"], r["mula"])) if r["mula"] else "-", _desk_sc_cell(r), e(r["next"]))
            for r in rs)
        h.append('<h2>%s (%d)</h2><div class="scroll"><table><colgroup><col style="width:24%%"><col style="width:15%%">'
                 '<col style="width:13%%"><col style="width:20%%"><col style="width:28%%"></colgroup><thead><tr><th>Text</th>'
                 '<th>Path</th><th>Working English (verses)</th><th>Scholarly English</th><th>Next</th></tr></thead><tbody>%s'
                 '</tbody></table></div>' % (
                     e(label), len(rs), body))
    h.append("</main>" + _DESK_JS + "</body></html>")
    return Response("".join(h), mimetype="text/html")


@app.get("/desk/<doc>")
def desk_text(doc):
    """TRANSLATION_DESK_2026_10_17: one text's whole state and its steps."""
    import html as _h
    import translation_desk as td
    e = _h.escape
    d = _validate_doc(doc)
    s = _desk_state(fresh=True)
    r = next((x for x in s.get("rows") or [] if x["doc"] == d), None) if d else None
    if r is None:
        return Response(_desk_head("The translation desk") + '<p>No such text here: %s. <a href="/desk">The desk</a></p>'
                        '</main></body></html>' % e(str(doc)), status=404, mimetype="text/html")
    sc = r["scholar"]
    held = r.get("held")
    h = [_desk_head(e(r["title"])), _desk_caps_line(s.get("caps") or {})]
    h.append('<div class="box"><h3>Where it stands</h3><p><span class="chip c-%s">%s</span>%s %s</p><p class="small">The path%s: '
             '%s. %s</p><p>Next: %s</p></div>' % (
                 e(r["stage"]), e(dict(td.STAGES).get(r["stage"], r["stage"])),
                 ('<span class="chip c-source">%s: %s</span>' % (e(held.replace("_", " ")), e(r.get("held_reason") or "")))
                 if held in td.HOLDS or held == "in_repair" else "", e(r["doc"]),
                 (" (charted %s)" % e(str(s.get("chart_at") or "")[:10])) if s.get("chart_at") else "",
                 e(td.PATH_LABEL.get(r["path"] or "", r["path"] or "not charted")), e(r["why"]), e(r["next"])))
    if r["path"] and r["next_path"]:
        h.append('<p class="small">The path\'s steps: %s. <a href="/repair/%s">The repair page</a> &middot; '
                 '<a href="/path">The path</a></p>' % (e(" | ".join(r["next_path"])), e(r["doc"], quote=True)))
    h.append('<div class="box"><h3>The working English (the draft, one pass)</h3><p>%s of %d verses. %s</p>%s</div>' % (
        r["en"], r["mula"], ('<span class="warn">Held: %s</span>' % e(r["guard"]["say"])) if r.get("guard") else "",
        ('<div class="row"><button class="btn dkbtn" onclick="deskTranslate(\'%s\', this)">Translate the rest '
         '(working English)</button> <span class="small">the path\'s estimate, English and Hindi: about $%.2f</span> '
         '<a href="/library">or from the Library</a></div>' % (e(r["doc"], quote=True), r["cost"])) if r["stage"] in ("ready", "edition") and r["en"] < r["mula"]
        and not r.get("guard") and r.get("held") not in td.HOLDS else ""))
    run = _desk_jobs(r["doc"])
    sc_line = ("%d of %d verses: %d passed, %d flagged (a person reads them), %d source doubts; %d accepted, %d rejected "
               "by a person%s; spent %s; by %s" % (
                   sc.get("verses", 0), max(r["mula"], sc.get("verses", 0)), sc.get("passed", 0), sc.get("flagged", 0),
                   sc.get("source_doubt", 0), sc.get("accepted", 0), sc.get("rejected", 0),
                   ("; %d stale (the Sanskrit changed)" % sc["stale"]) if sc.get("stale") else "", _bm1_usd(r["spent"]),
                   ", ".join("%s %d" % kv for kv in r["engines"].items()) or "-")) if sc.get("verses") else "Not begun."
    blocked = None
    if held in td.HOLDS:
        blocked = "it is %s (the register): a better source first" % held.replace("_", " ")
    elif r["stage"] == "source":
        blocked = "its path says the reading comes first (%s): the English would be made from a reading to be replaced" % (
            td.PATH_LABEL.get(r["path"] or "", r["path"]))
    held_ok = held == "in_repair"
    ctl = ""
    if r.get("guard") and r["stage"] == "edition":
        ctl += ('<p class="warn">Its path says the reading comes first (%s): the verses of the pages that change go '
                'stale, not wrong; the path\'s step first is the safer way.</p>' % e(r["guard"]["label"]))
    if run:
        ctl += ('<p class="warn" id="dkrunning" data-job="%s">Running: %s (%s, %d min). Its last lines are below.</p>' % (
            e(run[0]["id"], quote=True), e(run[0]["mode"] or ""), e(run[0]["state"]), int(run[0]["elapsed_s"] // 60)))
    elif blocked:
        ctl += '<p class="warn">Not offered: %s.</p>' % e(blocked)
    else:
        ctl += ('<div class="row">Pages <input type="text" id="dkpages" placeholder="all" title="a page, a range or a list: '
                '2, or 1-3,5"> Verses <input type="number" id="dklimit" value="%d" min="1" max="%d"> '
                '<button class="btn go dkbtn" onclick="deskStep(\'%s\', \'plan\', this)">Plan them (free)</button> '
                '<button class="btn go dkbtn" id="dkrun" style="display:none" data-cap="0" onclick="deskStep(\'%s\', \'run\', '
                'this)">Run</button></div>%s' % (
                    td.STEP_VERSES, td.MAX_VERSES, e(r["doc"], quote=True), e(r["doc"], quote=True),
                    '<p class="small">In repair: run with --held-ok, as on 15 Oct (nothing is written to the site or to '
                    'its passages; a row goes stale, not wrong, if the reading changes).</p>' if held_ok else ""))
    ctl += ('<div class="row"><button class="btn dkbtn" onclick="deskStep(\'%s\', \'status\', this)">Status (free)</button>'
            '<button class="btn dkbtn" onclick="deskStep(\'%s\', \'report\', this)">Report (free)</button>'
            '<button class="btn dkbtn" onclick="deskStep(\'%s\', \'triage\', this)">Triage what is not passed (free)</button>'
            ' <a href="/scholar/%s">Verse by verse</a> &middot; <a href="/scholar/%s/prose">As prose</a> &middot; '
            '<a href="/reader/%s">The reader</a></div><div class="out" id="dkout"></div><pre id="dklog"></pre>' % (
                e(r["doc"], quote=True), e(r["doc"], quote=True), e(r["doc"], quote=True), e(r["doc"], quote=True),
                e(r["doc"], quote=True), e(r["doc"], quote=True)))
    h.append('<div class="box"><h3>The scholarly English (the edition)</h3><p>%s</p>%s<p class="small">The standard flags '
             '(15 Oct; BM1 and BM3 measured them): %s. A plan is the dry run: what it would send, what it leaves out, '
             'and its price; nothing is called. The run asks first and stops at its cap.</p></div>' % (
                 e(sc_line), ctl, e(" ".join(td.SCHOLAR_SOP))))
    h.append("</main>" + _DESK_JS + "</body></html>")
    return Response("".join(h), mimetype="text/html")


@app.post("/api/desk/scholar")
def api_desk_scholar():
    """TRANSLATION_DESK_2026_10_17: a step of the scholarly English (scholar_translate.py) as a job of kind "scholar",
    doc "scholar:<doc>" (so that the script's own check of the dashboard's jobs on the text does not see itself):
    plan (the dry run, free), run (--yes --max-usd, at most translation_desk.MAX_USD a press), report, triage, status."""
    import translation_desk as td
    data = request.get_json(silent=True) or {}
    doc = _validate_doc(data.get("doc"))
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
    step = str(data.get("step") or "")
    reg = _source_verdicts(pathlib.Path(DESK_DB).parent).get(doc) or {}
    if step in ("plan", "run"):
        if reg.get("status") in td.HOLDS:
            return jsonify({"error": "%s is %s (the register): a better source first" % (doc, reg["status"])}), 409
        chart = td.load_path(PATH_FILE)
        prow = chart["texts"].get(doc)
        cover = {}
        try:
            con = sqlite3.connect(pathlib.Path(DESK_DB).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
            try:
                cover = _scholar_cover(con).get(doc) or {}
            finally:
                con.close()
        except Exception:
            cover = {}
        if td.stage_of(prow, cover, reg) == "source":
            return jsonify({"error": "its path says the reading comes first (%s): %s" % (
                td.PATH_LABEL.get((prow or {}).get("path") or "", ""), td.guard(prow, reg, chart["at"])["say"]
                if td.guard(prow, reg, chart["at"]) else "")}), 409
    argv, why = td.scholar_argv(doc, step, data.get("pages") or "", data.get("limit") or td.STEP_VERSES,
                                data.get("max_usd") or 0, reg.get("status") == "in_repair")
    if why:
        return jsonify({"error": why}), 400
    _DESK_CACHE.update(res=None)
    argv = ["--db", str(DESK_DB)] + argv   # the database the desk reads
    return jsonify({"job": launch("scholar", "scholar:" + doc, py(script("scholar_translate.py"), *argv), mode=step),
                    "kind": "scholar", "step": step})


def _status_decorate(rows: list, dbp) -> list:
''')

edit('scripts/dashboard.py', 2, r'''    if not reg and not sc:
        return rows
    out = []
    for r in rows:
        x = dict(r)
''', r'''    try:   # TRANSLATION_DESK_2026_10_17: the path of each text, on its row
        import translation_desk as _td
        _chart = _td.load_path(PATH_FILE)
    except Exception:
        _td, _chart = None, {"at": "", "texts": {}}
    if not reg and not sc and not _chart["texts"]:
        return rows
    out = []
    for r in rows:
        x = dict(r)
        _p = _chart["texts"].get(r.get("doc"))
        if _p and _td is not None:   # TRANSLATION_DESK_2026_10_17
            x["path"] = {"path": _p.get("path"), "label": _td.PATH_LABEL.get(_p.get("path"), _p.get("path")),
                         "next": str((list(_p.get("next") or []) or [""])[0])[:300], "at": _chart["at"][:10],
                         "held": bool(_td.guard(_p, reg.get(r.get("doc")), _chart["at"]))}
''')

edit('scripts/dashboard.py', 3, r'''    db      = data.get("db")      or "data/context.db"
    engine  = data.get("engine")  or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    # A blank/0 limit means''', r'''    if not data.get("force"):   # TRANSLATION_DESK_2026_10_17: a text whose path says the reading comes first
        _g = _desk_guard(doc)
        if _g:
            return jsonify(dict(_g, error=_g["say"], needs_force=True)), 409
    db      = data.get("db")      or "data/context.db"
    engine  = data.get("engine")  or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    # A blank/0 limit means''')

edit('scripts/dashboard.py', 4, r'''    engine      = data.get("engine")      or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    context     = str(data.get("context", 5))
''', r'''    if not data.get("force"):   # TRANSLATION_DESK_2026_10_17: a text whose path says the reading comes first
        _g = _desk_guard(doc)
        if _g:
            return jsonify(dict(_g, error=_g["say"], needs_force=True)), 409
    engine      = data.get("engine")      or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
    context     = str(data.get("context", 5))
''')

edit('scripts/dashboard.py', 5, r'''    var d=await r.json();
    if(!d.job){{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; return; }}
    btn.textContent='queued...';''', r'''    var d=await r.json();
    if(r.status===409 && d.needs_force && confirm(d.say+'\\n\\nTranslate it anyway?')){{   // TRANSLATION_DESK_2026_10_17
      r=await fetch('/api/translate',{{method:'POST',headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{doc:doc,lang:lang,limit:100000,force:true}})}});
      d=await r.json();
    }}
    if(!d.job){{ _toast('Could not start: '+(d.error||'unknown')); btn.textContent=orig; btn.disabled=false; return; }}
    btn.textContent='queued...';''')

edit('scripts/dashboard.py', 6, r'''  <a class="back" href="/scholar" title="SCHOLAR_2026_10_14: the scholarly English, verse by verse: drafted with its context and glossary, read by a critic, revised, judged" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128220; Scholarly English</a>
''', r'''  <a class="back" href="/scholar" title="SCHOLAR_2026_10_14: the scholarly English, verse by verse: drafted with its context and glossary, read by a critic, revised, judged" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128220; Scholarly English</a>
  <a class="back" href="/desk" title="TRANSLATION_DESK_2026_10_17: every text by its stage, and the scholarly English begun from its page" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128221; The desk</a>
''')

edit('scripts/dashboard_static.html', 1, r'''    <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>
''', r'''    <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>
    <a class="btn-refresh" href="/desk" target="_blank" style="text-decoration:none;margin-right:6px" title="TRANSLATION_DESK_2026_10_17: every text by its stage (the scholarly edition, ready to translate, translated, the reading first), and the scholarly English begun from its page">&#128221; Desk</a>
''')

edit('scripts/dashboard_static.html', 2, r'''  return h ? '<div style="line-height:1.2">' + h + '</div>' : '';
}

function renderPipeline(rows) {''', r'''  var p = r.path;   // TRANSLATION_DESK_2026_10_17: the path of the text, linked to its page on the desk
  if (p && p.path) {
    h += '<a href="/desk/' + encodeURIComponent(r.doc) + '" target="_blank" title="' + esc('The path (' + (p.at || '') + '): '
      + (p.label || p.path) + '. Next: ' + (p.next || '-')) + '" style="display:inline-block;margin:3px 4px 0 0;padding:1px 6px;'
      + 'border-radius:3px;font-size:9.5px;text-decoration:none;' + (p.held ? 'background:rgba(220,90,90,.15);color:#e8a3a3'
      : 'background:rgba(120,200,160,.12);color:#9fd8b5') + '">' + (p.held ? 'the reading first: ' : 'path: ')
      + esc(p.label || p.path) + '</a>';
  }
  return h ? '<div style="line-height:1.2">' + h + '</div>' : '';
}

function renderPipeline(rows) {''')

edit('scripts/dashboard_static.html', 3, r'''    const r = await fetch('/api/translate', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, engine: eng, limit, lang})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, 'Translate ' + doc + (lang!=='en'?' ['+lang+']':''), 'translate', doc); toast('Translation started (' + eng + ', ' + lang + ')'); }
''', r'''    let r = await fetch('/api/translate', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, engine: eng, limit, lang})});
    let j = await r.json();
    if (r.status === 409 && j.needs_force) {   // TRANSLATION_DESK_2026_10_17: the path says the reading comes first
      if (!confirm(j.say + '\n\nTranslate it anyway?')) { toast('Held: ' + doc + ' (' + (j.label || 'the reading first') + '): the desk has its steps', 'fail'); return; }
      r = await fetch('/api/translate', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({doc, db: cfg.db, engine: eng, limit, lang, force: true})});
      j = await r.json();
    }
    if (j.job) { trackJob(j.job, 'Translate ' + doc + (lang!=='en'?' ['+lang+']':''), 'translate', doc); toast('Translation started (' + eng + ', ' + lang + ')'); }
    else if (j.error) toast(j.error, 'fail');
''')

edit('scripts/dashboard_static.html', 4, r'''async function startDoc(doc) {
  const eng = getEngine(doc);
  const lang = getLang();
  try {
    const r = await fetch('/api/pipeline/translate-doc', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({doc: doc, engine: eng, context: 5, sleep: 0.8, db: cfg.db, lang: lang})
    });
    const d = await r.json();
    if (d.error) { toast('Error: ' + d.error, 'fail'); return; }
''', r'''async function startDoc(doc, opts) {   // TRANSLATION_DESK_2026_10_17: opts.bulk holds a guarded text quietly
  const eng = getEngine(doc);
  const lang = getLang();
  try {
    const r = await fetch('/api/pipeline/translate-doc', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({doc: doc, engine: eng, context: 5, sleep: 0.8, db: cfg.db, lang: lang})
    });
    let d = await r.json();
    if (r.status === 409 && d.needs_force) {   // TRANSLATION_DESK_2026_10_17: the path says the reading comes first
      if ((opts || {}).bulk || !confirm(d.say + '\n\nTranslate it anyway?')) { if (!(opts || {}).bulk) toast('Held: ' + doc + ' (' + (d.label || 'the reading first') + '): the desk has its steps', 'fail'); return 'held'; }
      const r2 = await fetch('/api/pipeline/translate-doc', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({doc: doc, engine: eng, context: 5, sleep: 0.8, db: cfg.db, lang: lang, force: true})});
      d = await r2.json();
    }
    if (d.error) { toast('Error: ' + d.error, 'fail'); return; }
''')

edit('scripts/dashboard_static.html', 5, r'''    for (var i = 0; i < docs.length; i++) { await startDoc(docs[i]); }
''', r'''    var _held = [];   // TRANSLATION_DESK_2026_10_17: the texts whose path says the reading comes first are left
    for (var i = 0; i < docs.length; i++) { if (await startDoc(docs[i], {bulk: true}) === 'held') _held.push(docs[i]); }
    if (_held.length) toast(_held.length + ' text(s) left: their path says the reading comes first (the desk has their steps): ' + _held.slice(0, 6).join(', ') + (_held.length > 6 ? ' ...' : ''), 'fail');
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    td = Path("scripts/translation_desk.py")
    if not td.exists() or MARK.encode() not in td.read_bytes():
        print("REFUSE: scripts/translation_desk.py (this release) is not there. Nothing written."); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_translation_desk_2026_10_17")
    print("  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
