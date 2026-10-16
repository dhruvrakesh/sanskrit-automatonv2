#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_gold_desk_2026_10_16.py  (2026-10-16)  BENCH_GOLD_2026_10_16

BM2 (scripts/bench_gold.py, a person's blind reading of BM3's units, new in this release) on the dashboard.

scripts/dashboard.py (needs BENCH_DUEL_2026_10_16):
  - /benchmarks/bm2: the reading. A unit at a time in BM3's order (the units both judges have read first): the
    Sanskrit (Devanagari and IAST) with the verses around it, the four translations as Translation 1 to 4 in an order
    of their own; the best (or equal), any marked wrong in meaning, a note; then who made each, the scholarly arm's
    notes and what each judge chose. Keys 1 to 4, E, Enter. The reader's name is kept in this browser only;
  - /api/bm2/next (the next unit, no names) and /api/bm2/pick (the pick, stored in BM2's folder, person.jsonl;
    refused when the unit's English has changed since the page was made);
  - the Benchmarks page: BM2's section under BM3's (what each reader has read, the report as a button, a job of kind
    "bench2", and its numbers: each judge against the reader); /benchmarks/bm2/report (private, 127.0.0.1);
  - BM3's section: the check (BENCH_DUEL_NOTES_2026_10_16: the pilot's units again, the scholarly arm's notes
    withheld) once the pilot is read: what each judge has read of it, its run and its report as buttons (bench_duel.py
    --no-notes), its numbers beside the pilot's.
Free: nothing is called and nothing is paid.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_benchgold_<date>. No database change. Needs scripts/bench_gold.py and BENCH_DUEL_NOTES_2026_10_16 in
scripts/bench_duel.py (this release).
  python scripts\\patch_bench_gold_desk_2026_10_16.py --check
  python scripts\\patch_bench_gold_desk_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "BENCH_GOLD_2026_10_16"
NEEDS = {"scripts/dashboard.py": "BENCH_DUEL_2026_10_16"}
FILES = list(NEEDS)
TAG = "benchgold"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, r'''def _status_decorate(rows: list, dbp) -> list:
''', r'''# BENCH_GOLD_2026_10_16 -------------------------------------------------------------------------------------------
# BM2 (scripts/bench_gold.py), a person's blind reading of BM3's units: on the Benchmarks page under BM3, what each
# reader has read and the last report (each judge against the person); the reading itself at /benchmarks/bm2 (the
# Sanskrit, the four translations as Translation 1 to 4, a pick and marks; then who made each and what each judge
# chose). Free: nothing is called. The picks go to BM2's folder (person.jsonl), outside every repository.
BM2_DIR = pathlib.Path(os.environ.get("SA_BENCH2_DIR") or (ROOT.parent / "benchmarks" / "bm2"))
_BM2_CACHE = {"at": 0.0, "res": None}


def _bm2_jobs() -> list:
    with JOBS_LOCK:
        return [{"id": j.id, "mode": j.mode, "state": "running" if j.active else "queued",
                 "elapsed_s": round(time.time() - j.start, 1)} for j in JOBS.values() if j.kind == "bench2" and j.ok is None]


def _bm2_state(fresh: bool = False) -> dict:
    now_ = time.time()
    if not fresh and _BM2_CACHE["res"] is not None and now_ - _BM2_CACHE["at"] < 20:
        return dict(_BM2_CACHE["res"], running=_bm2_jobs())
    try:
        import bench_gold as bg
        res = bg.state(BM1_DIR, BM2_DIR, BM3_DIR)
        if res.get("summary_mtime"):
            res["summary_at"] = time.strftime("%d %b, %H:%M", time.localtime(res["summary_mtime"]))
    except Exception as ex:   # the dashboard is never stopped by BM2
        res = {"error": "%s: %s" % (type(ex).__name__, str(ex)[:300])}
    _BM2_CACHE.update(at=now_, res=res)
    return dict(res, running=_bm2_jobs())


def _bm2_html() -> str:
    """BM2's section of the Benchmarks page. Never raises."""
    import html as _h
    e = _h.escape
    try:
        s = _bm2_state(fresh=True)
    except Exception as ex:
        s = {"error": "%s: %s" % (type(ex).__name__, ex)}
    head = ('<div class="srcpage bm1 bm2" id="bm2"><h2 class="bmh">Your blind reading: BM2</h2>'
            '<p class="rpintro" style="margin:0 0 10px">The same units as BM3, in its order (the units both judges have '
            'read come first): the Sanskrit, and four translations as Translation 1 to 4 in an order of their own. Pick '
            'the best, mark any that is wrong in meaning; then the page says who made each and what each judge chose. '
            'Your picks are the gold the judges are measured against. Free: nothing is called. The method: '
            'docs/BENCH_GOLD_2026-10-16.md.</p>')
    out_box = '<div class="rpout" id="bm2out"></div></div><pre class="bmlog" id="bm2log"></pre>'
    if s.get("error"):
        return head + '<p class="srcnone">BM2 could not be read: %s</p></div>' % e(s["error"])
    if not s.get("ready"):
        return head + '<p class="srcnone">BM2 waits for BM1: %s.</p></div>' % e(s.get("why") or "not ready")
    h = [head]
    run = s.get("running") or []
    if run:
        h.append('<p class="bmrun" id="bm2running" data-job="%s">Running: the report (%s).</p>' % (
            e(run[0]["id"], quote=True), e(run[0]["state"])))
    rd = s.get("read") or {}
    h.append('<p class="bmcaps">%d units; both judges have read %d. Read so far: %s.</p>' % (
        int(s.get("units_total") or 0), int(s.get("judged_both") or 0),
        e(", ".join("%s %d" % kv for kv in sorted(rd.items())) or "nobody yet")))
    bar = ('<a class="tr-rest rp rpnext" style="text-decoration:none;display:inline-block" href="/benchmarks/bm2" '
           'target="_blank">Read blind &rarr;</a>')
    if not run:
        bar += ('<button class="tr-rest rp%s" data-box="bm2" data-step="gold_report" data-usd="" data-units="" '
                'data-ask="" onclick="bm1Step(this)">Make the report (free)</button>' % (" rpnext" if s.get("stale") else ""))
    bar += ('<a class="rplink" href="/benchmarks/bm2/report" target="_blank">The full report (private: the dataset\'s '
            'text and your notes)</a>')
    h.append('<div class="repairbar">' + bar + out_box)
    sc = ((s.get("summary") or {}).get("scopes") or {})
    rows = ""
    for k in ("all", "core"):
        v = sc.get(k) or {}
        for p, pn in (v.get("by_person") or {}).items():
            if not pn.get("units"):
                continue
            rows += '<tr><td>%s</td><td>%s</td><td class="n">%d</td><td class="bmsmall">%s</td><td class="bmsmall">%s</td></tr>' % (
                e(v.get("name") or k), e(p), pn["units"],
                e("; ".join("%s %.0f%%" % (a, 100 * x) for a, x in (pn.get("best") or {}).items())),
                e("; ".join("%s: same best %.2f (chance %.2f); caught %d of %d you marked wrong" % (
                    _BM3_SHORT.get(j, j), d["same_best"], d["chance"], d["judge_caught"], d["wrong_marked"])
                    for j, d in (pn.get("judges") or {}).items())))
    if rows:
        h.append('<h3 class="bmh3">The last report (%s)%s</h3>' % (e(s.get("summary_at") or ""), (
            ' <span class="bmwarn">a pick has been made since: make it again</span>') if s.get("stale") else ""))
        h.append('<table class="srct bmres"><thead><tr><th>Scope</th><th>Reader</th><th>Units</th><th>Your best</th>'
                 '<th>Each judge against you</th></tr></thead><tbody>%s</tbody></table>' % rows)
    h.append("</div>")
    return "".join(h)


def _bm2_post(data: dict, step: str):
    """BENCH_GOLD_2026_10_16: BM2's report as a job of kind "bench2" (doc BM2)."""
    _BM2_CACHE.update(res=None)
    return jsonify({"job": launch("bench2", "BM2", py(script("bench_gold.py"), "--report"), mode="report"),
                    "kind": "bench2", "step": step})


@app.get("/api/bm2/next")
def api_bm2_next():
    """BENCH_GOLD_2026_10_16: the next unit this reader has not read (no names, no notes), with the progress."""
    import bench_gold as bg
    by = (request.args.get("by") or "").strip()
    if not bg.BY_OK.match(by):
        return jsonify({"error": "say who is reading (letters, up to 40)"}), 400
    try:
        return jsonify(bg.next_for(BM1_DIR, BM2_DIR, by))
    except Exception as ex:
        return jsonify({"error": "%s: %s" % (type(ex).__name__, str(ex)[:300])}), 500


@app.post("/api/bm2/pick")
def api_bm2_pick():
    """BENCH_GOLD_2026_10_16: a reader's pick, stored; then who made each and what each judge chose."""
    import bench_gold as bg
    d = request.get_json(silent=True) or {}
    rev, why = bg.record(BM1_DIR, BM2_DIR, BM3_DIR, d.get("by"), str(d.get("key") or ""), str(d.get("unit") or ""),
                         str(d.get("token") or ""), d.get("best"), d.get("majors") or [], d.get("note") or "")
    if why:
        return jsonify({"error": why}), 400
    _BM2_CACHE.update(res=None)
    return jsonify({"ok": True, "reveal": rev})


@app.get("/benchmarks/bm2/report")
def bm2_report():
    """BENCH_GOLD_2026_10_16: BM2's report (private: the dataset's text and the reader's notes), on this computer."""
    if not (BM2_DIR / "BM2_report.html").exists():
        return Response("BM2 has no report yet: press Make the report on the Benchmarks page.", status=404,
                        mimetype="text/plain")
    r = send_from_directory(str(BM2_DIR), "BM2_report.html")
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Robots-Tag"] = "noindex"
    return r


_BM2_PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>BM2: your blind reading</title>
<style>/* BENCH_GOLD_2026_10_16 */
:root{--bg:#0f0d0a;--card:#1a1712;--card2:#221e17;--border:#3a3326;--gold:#c9952a;--cream:#eee4cf;--muted:#9a8f7a;--red:#e8a3a3;--green:#9fd8b5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--cream);font:15px/1.55 Georgia,'Noto Serif',serif}
header{display:flex;gap:14px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);flex-wrap:wrap}
header a{color:var(--gold);text-decoration:none;font-size:13px}
header h1{font-size:16px;margin:0;color:var(--gold);font-weight:600}
main{max-width:860px;margin:0 auto;padding:16px}
.who{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px;font-size:13px;color:var(--muted)}
input[type=text],textarea{background:var(--card2);color:var(--cream);border:1px solid var(--border);border-radius:6px;padding:6px 8px;font:inherit}
textarea{width:100%;min-height:56px;font-size:13px}
button{background:var(--card2);color:var(--cream);border:1px solid var(--gold);border-radius:6px;padding:7px 14px;font:inherit;font-size:13px;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
.prog{font-size:12px;color:var(--muted);margin:4px 0 12px}
.sa{font-family:'Noto Serif Devanagari','Noto Sans Devanagari',serif;font-size:20px;line-height:1.7;margin:6px 0}
.ia{font-style:italic;color:var(--muted);font-size:14px;margin-bottom:8px}
details{margin:6px 0;font-size:13px;color:var(--muted)}
details .sa{font-size:16px;color:var(--muted)}
.tr{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin:10px 0}
.tr.picked{border-color:var(--gold)}
.tr h3{margin:0 0 6px;font-size:13px;color:var(--gold);font-weight:600;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.tr h3 label{font-weight:400;color:var(--cream);cursor:pointer}
.tr p{margin:0;white-space:pre-wrap}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
.msg{font-size:13px;color:var(--red);margin:8px 0}
.rev{background:var(--card2);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin:12px 0;font-size:14px}
.rev b{color:var(--gold)}
.small{font-size:12px;color:var(--muted)}
.warn{font-size:12px;color:var(--muted);border-left:3px solid var(--gold);padding-left:8px;margin:0 0 12px}
</style></head><body>
<header><a href="/benchmarks">&larr; Benchmarks</a><h1>BM2: your blind reading</h1></header>
<main>
<p class="warn">Private evaluation: the Mitrasamgraha test set's Sanskrit and published English, on this computer only.
Who made each translation is not said until you have picked; the scholarly arm's notes are kept back too. Keys: 1 to 4
pick the best, E says they are equal, Enter saves.</p>
<div class="who">Reading as <input type="text" id="by" maxlength="40" placeholder="your name" autocomplete="off">
<button onclick="bm2Load()">Start</button></div>
<div id="bm2"></div>
</main>
<script>
var _B2 = {u: null, saved: false};
function _el(t, cls, txt){ var x = document.createElement(t); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; }
function _by(){ return (document.getElementById('by').value || '').trim(); }
(function(){ try { var b = localStorage.getItem('bm2by'); if (b){ document.getElementById('by').value = b; bm2Load(); } } catch(e){} })();
async function bm2Load(){
  var b = _by(), box = document.getElementById('bm2');
  if (!b){ box.textContent = 'Say who is reading first.'; return; }
  try { localStorage.setItem('bm2by', b); } catch(e){}
  box.textContent = 'Loading...';
  try{
    var r = await fetch('/api/bm2/next?by=' + encodeURIComponent(b));
    var d = await r.json();
    if (d.error){ box.textContent = d.error; return; }
    _render(d);
  }catch(e){ box.textContent = 'The dashboard did not answer: ' + e; }
}
function _sa(list, parent){
  list.forEach(function(v){ parent.appendChild(_el('div', 'sa', v.dev)); parent.appendChild(_el('div', 'ia', v.iast)); });
}
function _render(d){
  var box = document.getElementById('bm2'); box.textContent = '';
  box.appendChild(_el('div', 'prog', 'You have read ' + d.read + ' of ' + d.total + ' units.'));
  if (d.done){ box.appendChild(_el('p', null, 'You have read them all. Make the report on the Benchmarks page.')); return; }
  var u = d.unit; _B2.u = u; _B2.saved = false;
  box.appendChild(_el('h2', null, u.title + ', ' + u.unit + (u.n > 1 ? ' (one sentence over ' + u.n + ' verses)' : '')));
  if (u.before && u.before.length){ var b = _el('details'); b.appendChild(_el('summary', null, 'The verses before')); _sa(u.before, b); box.appendChild(b); }
  var v = _el('div'); _sa(u.verses, v); box.appendChild(v);
  if (u.after && u.after.length){ var a = _el('details'); a.appendChild(_el('summary', null, 'The verses after')); _sa(u.after, a); box.appendChild(a); }
  u.translations.forEach(function(t){
    var c = _el('div', 'tr'); c.id = 'tr' + t.n;
    var h = _el('h3', null, 'Translation ' + t.n);
    var l1 = _el('label'); var r1 = _el('input'); r1.type = 'radio'; r1.name = 'best'; r1.value = String(t.n);
    r1.onchange = _mark; l1.appendChild(r1); l1.appendChild(document.createTextNode(' the best'));
    var l2 = _el('label'); var c2 = _el('input'); c2.type = 'checkbox'; c2.name = 'wrong'; c2.value = String(t.n);
    l2.appendChild(c2); l2.appendChild(document.createTextNode(' wrong in meaning'));
    h.appendChild(l1); h.appendChild(l2); c.appendChild(h); c.appendChild(_el('p', null, t.text)); box.appendChild(c);
  });
  var row = _el('div', 'row');
  var le = _el('label'); var re = _el('input'); re.type = 'radio'; re.name = 'best'; re.value = 'equal'; re.onchange = _mark;
  le.appendChild(re); le.appendChild(document.createTextNode(' they are equally good')); row.appendChild(le); box.appendChild(row);
  var n = _el('textarea'); n.id = 'note'; n.maxLength = 1000; n.placeholder = 'a note (optional): what is wrong, what is right'; box.appendChild(n);
  var r2 = _el('div', 'row'); var s = _el('button', null, 'Save and show who made each'); s.id = 'save'; s.onclick = bm2Save; r2.appendChild(s); box.appendChild(r2);
  box.appendChild(_el('div', 'msg')).id = 'msg';
  window.scrollTo(0, 0);
}
function _mark(){
  var all = document.querySelectorAll('.tr'); for (var i = 0; i < all.length; i++) all[i].classList.remove('picked');
  var p = document.querySelector('input[name=best]:checked'); if (p && p.value !== 'equal'){ var c = document.getElementById('tr' + p.value); if (c) c.classList.add('picked'); }
}
async function bm2Save(){
  var p = document.querySelector('input[name=best]:checked'), m = document.getElementById('msg');
  if (!p){ m.textContent = 'Pick the best, or say they are equal.'; return; }
  var wr = Array.prototype.map.call(document.querySelectorAll('input[name=wrong]:checked'), function(x){ return +x.value; });
  var body = {by: _by(), key: _B2.u.key, unit: _B2.u.unit, token: _B2.u.token, best: p.value === 'equal' ? 'equal' : +p.value,
              majors: wr, note: document.getElementById('note').value};
  document.getElementById('save').disabled = true;
  try{
    var r = await fetch('/api/bm2/pick', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if (d.error){ m.textContent = d.error; document.getElementById('save').disabled = false; return; }
    _B2.saved = true; _reveal(d.reveal);
  }catch(e){ m.textContent = 'The dashboard did not answer: ' + e; document.getElementById('save').disabled = false; }
}
function _reveal(v){
  Array.prototype.forEach.call(document.querySelectorAll('#bm2 input, #bm2 textarea'), function(x){ x.disabled = true; });
  var box = _el('div', 'rev');
  box.appendChild(_el('div', null, 'Saved. Who made each:'));
  v.who.forEach(function(w){ var d = _el('div'); d.appendChild(_el('b', null, w.n + ': ')); d.appendChild(document.createTextNode(w.name)); box.appendChild(d); });
  if (v.scholar_notes && v.scholar_notes.length){
    box.appendChild(_el('div', 'small', 'The notes of Translation ' + v.scholar_n + ' (the scholarly pipeline):'));
    v.scholar_notes.forEach(function(x){ box.appendChild(_el('div', 'small', (x.anchor ? x.anchor + ': ' : '') + x.note)); });
  }
  var js = Object.keys(v.judges || {});
  if (js.length){
    js.forEach(function(j){ var x = v.judges[j]; box.appendChild(_el('div', 'small', j + ' chose ' + (x.best === 'equal' ? 'none (equal)' : 'Translation ' + x.best_n) + (x.majors && x.majors.length ? '; a major error in ' + x.majors.join(', ') : ''))); });
  } else { box.appendChild(_el('div', 'small', 'The judges of BM3 have not read this unit yet.')); }
  var nb = _el('button', null, 'Next unit'); nb.onclick = bm2Load; var r = _el('div', 'row'); r.appendChild(nb); box.appendChild(r);
  document.getElementById('bm2').appendChild(box); nb.focus();
}
document.addEventListener('keydown', function(ev){
  if (!_B2.u || _B2.saved) { if (_B2.saved && ev.key === 'Enter' && ev.target.tagName !== 'TEXTAREA'){ ev.preventDefault(); bm2Load(); } return; }
  var t = ev.target.tagName; if (t === 'TEXTAREA' || t === 'INPUT' && ev.target.type === 'text') return;
  if (/^[1-9]$/.test(ev.key)){ var x = document.querySelector('input[name=best][value="' + ev.key + '"]'); if (x){ x.checked = true; _mark(); } }
  else if (ev.key === 'e' || ev.key === 'E'){ var q = document.querySelector('input[name=best][value=equal]'); if (q){ q.checked = true; _mark(); } }
  else if (ev.key === 'Enter'){ ev.preventDefault(); bm2Save(); }
});
</script></body></html>"""


@app.get("/benchmarks/bm2")
def bm2_page():
    """BENCH_GOLD_2026_10_16: the blind reading (its units come from /api/bm2/next)."""
    r = Response(_BM2_PAGE, mimetype="text/html")
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Robots-Tag"] = "noindex"
    return r


def _bm3_check_state() -> dict:
    """BENCH_GOLD_2026_10_16: BM3's check (BENCH_DUEL_NOTES_2026_10_16): the pilot's units again, the scholarly arm's
    notes withheld. What each judge has read of it, and its last report. Read only; {} when it cannot be read."""
    try:
        import bench_duel as bd
        sample, items = bd.load(BM1_DIR)
        if not sample:
            return {}
        ix = bd.index_of(bd.readings(BM3_DIR))
        judges = list(bd.SD.JUDGES)
        done, todo, n = {j: 0 for j in judges}, {j: 0 for j in judges}, 0
        for ti, ui in bd.order_of(items)[:_BM3_STEP]:
            it = items[ti]
            m = it["units"][ui]
            t = bd.texts_of(it, m, True)
            if t is None:
                continue
            n += 1
            sh = json.dumps(bd.shas({a: {"text": v["text"], "notes": []} for a, v in t.items()}), sort_keys=True)
            for j in judges:
                if (it["f"]["key"], bd.bm.unit_name(m), j, sh) in ix:
                    done[j] += 1
                else:
                    todo[j] += 1
        res = {"units": n, "done": done, "todo": todo}
        p = BM3_DIR / "BM3_nonotes_summary.json"
        if p.exists():
            res["summary"] = json.loads(p.read_text(encoding="utf-8"))
            res["summary_at"] = time.strftime("%d %b, %H:%M", time.localtime(p.stat().st_mtime))
        return res
    except Exception as ex:
        return {"error": "%s: %s" % (type(ex).__name__, str(ex)[:200])}


def _bm3_check_html(s: dict) -> str:
    """BENCH_GOLD_2026_10_16: the check's lines in BM3's section, once the pilot is read. Never raises."""
    import html as _h
    e = _h.escape
    try:
        rd = s.get("read") or {}
        if not rd or min(rd.values()) < _BM3_STEP:
            return ""
        c = _bm3_check_state()
        if not c or c.get("error"):
            return ('<p class="bmsmall">The check (the notes withheld) could not be read: %s</p>' % e(c.get("error") or "")
                    if c else "")
        pr = s.get("prices") or {}
        cp = s.get("caps") or {}
        each = lambda j: float((pr.get(j) or {}).get("each") or 0.05)
        cl = sum(n * each(j) for j, n in c["todo"].items() if j.startswith("anthropic:"))
        gg = sum(n * each(j) for j, n in c["todo"].items() if not j.startswith("anthropic:"))
        mx = max(0.25, round((cl + gg) * 1.3 + 0.05, 2))
        h = ['<h3 class="bmh3">The check: the scholarly arm\'s notes withheld</h3><p class="bmsmall">Only the scholarly '
             'arm has notes, so its notes name it, and a judge may rank an annotated translation higher for them. The '
             'check reads the pilot\'s %d units again without them. Read: %s.</p>' % (
                 c["units"], e(", ".join("%s %d of %d" % (_BM3_SHORT.get(j, j), d, c["units"]) for j, d in c["done"].items())))]
        bar = ""
        if any(c["todo"].values()) and not (s.get("running") or []):
            if mx <= _BM1_MAX_USD and gg <= float(cp.get("cap_left") or 0):
                bar += ('<button class="tr-rest rp rpnext" data-box="bm3" data-step="duel" data-units="%d" data-nonotes="1" '
                        'data-usd="%.2f" data-ask="%s" onclick="bm1Step(this)">%s</button>' % (
                            _BM3_STEP, mx, e("Let the two judges read the pilot's %d units again with the scholarly arm's "
                                             "notes withheld (%d readings). It spends at most %s (Claude about %s, Google "
                                             "about %s) and stops before spending more. Go?" % (
                                                 c["units"], sum(c["todo"].values()), _bm1_usd(mx), _bm1_usd(cl),
                                                 _bm1_usd(gg)), quote=True),
                            e("Run the check: about %s, at most %s" % (_bm1_usd(cl + gg), _bm1_usd(mx)))))
            else:
                h.append('<p class="bmsmall">The check needs about %s (Google %s): the spend cap has %s left.</p>' % (
                    _bm1_usd(cl + gg), _bm1_usd(gg), _bm1_usd(cp.get("cap_left"))))
        if not (s.get("running") or []) and any(c["done"].values()):
            bar += ('<button class="tr-rest rp" data-box="bm3" data-step="duel_report" data-nonotes="1" data-usd="" '
                    'data-units="" data-ask="" onclick="bm1Step(this)">Make the check\'s report (free)</button>')
        if bar:
            h.append('<div class="repairbar" style="margin-top:6px">' + bar + '</div>')
        sm = (c.get("summary") or {}).get("scopes", {}).get("all") or {}
        with_ = ((s.get("summary") or {}).get("scopes") or {}).get("all") or {}
        rows = ""
        for j, jn in (sm.get("by_judge") or {}).items():
            w = ((with_.get("by_judge") or {}).get(j) or {}).get("pairs") or {}
            rows += '<tr><td>%s</td><td class="n">%d</td>%s</tr>' % (e(_BM3_SHORT.get(j, j)), jn.get("units", 0), "".join(
                '<td class="n">%s <span class="bmsmall">(with the notes %s)</span></td>' % (
                    _bm3_pair((jn.get("pairs") or {}).get(p) or {}), ("%.2f" % w[p]["share"]) if p in w else "-")
                for p in ("scholar>flash", "scholar>sonnet1", "sonnet1>flash")))
        if rows:
            h.append('<table class="srct bmres"><thead><tr><th>Judge (%s)</th><th>Units</th><th>scholar above flash</th>'
                     '<th>scholar above sonnet1</th><th>sonnet1 above flash</th></tr></thead><tbody>%s</tbody></table>' % (
                         e(c.get("summary_at") or ""), rows))
        return "".join(h)
    except Exception as ex:
        return '<p class="bmsmall">The check could not be shown: %s</p>' % e(str(ex)[:200])


def _status_decorate(rows: list, dbp) -> list:
''')

edit('scripts/dashboard.py', 2, r'''    if step in ("duel", "duel_report", "duel_settle"):   # BENCH_DUEL_2026_10_16: BM3's steps
''', r'''    if step == "gold_report":   # BENCH_GOLD_2026_10_16: BM2's report
        return _bm2_post(data, step)
    if step in ("duel", "duel_report", "duel_settle"):   # BENCH_DUEL_2026_10_16: BM3's steps
''')

edit('scripts/dashboard.py', 3, r'''<h1>Benchmarks</h1></header>
""" + _bm1_html() + _bm3_html() + body + """''', r'''<h1>Benchmarks</h1></header>
""" + _bm1_html() + _bm3_html() + _bm2_html() + body + """''')

edit('scripts/dashboard.py', 4, r'''  if (r && r.getAttribute('data-job')){ _BM_BOX = 'bm3'; _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
''', r'''  if (r && r.getAttribute('data-job')){ _BM_BOX = 'bm3'; _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
(function(){   // BENCH_GOLD_2026_10_16: BM2's report being made when the page opens
  var r = document.getElementById('bm2running');
  if (r && r.getAttribute('data-job')){ _BM_BOX = 'bm2'; _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
''')

edit('scripts/dashboard.py', 5, r'''    else:
        argv.append("--report" if step == "duel_report" else "--settle")
''', r'''    else:
        argv.append("--report" if step == "duel_report" else "--settle")
        if step == "duel_report" and data.get("no_notes"):   # BENCH_GOLD_2026_10_16: the check's report
            argv.append("--no-notes")
            mode = "duel_report no notes"
''')

edit('scripts/dashboard.py', 6, r'''        argv += ["--units", str(units), "--with-reference", "--yes", "--max-usd", "%.2f" % usd]
        mode = "duel %d" % units
''', r'''        argv += ["--units", str(units), "--with-reference", "--yes", "--max-usd", "%.2f" % usd]
        mode = "duel %d" % units
        if data.get("no_notes"):   # BENCH_GOLD_2026_10_16: BM3's check, the scholarly arm's notes withheld
            argv.append("--no-notes")
            mode += " no notes"
''')

edit('scripts/dashboard.py', 7, r'''the firmest.</p>')
    h.append("</div>")
''', r'''the firmest.</p>')
    h.append(_bm3_check_html(s))   # BENCH_GOLD_2026_10_16: the check, the notes withheld
    h.append("</div>")
''')

edit('scripts/dashboard.py', 8, r'''  if (btn.getAttribute('data-units')) body.units = +btn.getAttribute('data-units');   // BENCH_DUEL_2026_10_16
''', r'''  if (btn.getAttribute('data-units')) body.units = +btn.getAttribute('data-units');   // BENCH_DUEL_2026_10_16
  if (btn.getAttribute('data-nonotes')) body.no_notes = true;   // BENCH_GOLD_2026_10_16: BM3's check
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
    bg = Path("scripts/bench_gold.py")
    if not bg.exists() or MARK.encode() not in bg.read_bytes() or not Path("scripts/bench_duel.py").exists() or b"BENCH_DUEL_NOTES_2026_10_16" not in Path("scripts/bench_duel.py").read_bytes():
        print("REFUSE: scripts/bench_gold.py, or BENCH_DUEL_NOTES_2026_10_16 in scripts/bench_duel.py (this release), is not there. Nothing written."); return 1
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
    print("  python -m unittest tests.test_bench_gold_desk_2026_10_16 tests.test_bench_gold_2026_10_16")
    print("  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
