#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_desk_2026_10_16.py  (2026-10-16)  BENCH_DESK_2026_10_16

Asked on 16 Oct: "UI/UX on the dashboard needs to reflect the latest state, and intuitive wiring". What the dashboard
did not show: BM1 at all (its spend appeared as bench_translation BM1:Rgveda among the last calls, nothing more); the
Claude credit (the Usage tab's "Spent, all time" was the spend cap's Google count, beside an engine table holding
Claude's $112); a text's register state (withdrawn, set aside, in repair) and its scholarly English, on the main
table's rows.

scripts/dashboard.py (needs CLASSIFY_HINDI_2026_10_16):
  - the Benchmarks page opens with BM1 (scripts/bench_mitra.py): what each arm has made per text, what the judge has
    read, what each arm cost and costs a verse, the caps, the last report's numbers with their intervals (marked stale
    when a step has run since; "scored on n of 8 texts" when partial), and the steps as buttons: a job of kind
    "bench" (doc BM1), its last lines shown while it runs; a paid one asks first and runs with --yes --max-usd (the
    estimate and a third more, at most $12.00 a press). /api/bench (GET the state, POST a step);
    /benchmarks/bm1/report serves the private report, on this computer only (127.0.0.1);
  - /api/status: each row with "held" (the register's state of its text) and "scholar" (its scholarly English);
  - /api/usage: "credit" (the Claude credit), "kinds_since" (the steps since the credit began, by kind and bill;
    BM1's kinds bench_* apart), "bm1" (its line).
scripts/dashboard_static.html (needs REPAIR_HEAL_2026_10_11):
  - a Benchmarks link in the header; on each row a chip for the register's state and one for the scholarly English
    (a link to /scholar/<doc>); the Usage tab: the spend cap (Google) and the Claude credit side by side, Google and
    Claude apart in the totals and the engine table, the steps since the credit began by name, the last calls with
    their step and engine, BM1's line with a link.
scripts/bench_mitra.py (needs BENCH_MITRA_2026_10_16):
  - prices(mcon, out): an arm that has made 10 verses or more is priced by its own spend (gemini-2.5-flash cost $0.005
    a BM1 verse, twice the corpus's, so the flash arm stopped at --max-usd 0.75 before its last two texts);
  - the report's NEXT line is PowerShell's (Start-Process), not cmd's (start "").
docs/BENCH_MITRA_2026-10-16.md: the same correction in its commands.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_benchdesk_<date>. No database change.
  python scripts\\patch_bench_desk_2026_10_16.py --check
  python scripts\\patch_bench_desk_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "BENCH_DESK_2026_10_16"
NEEDS = {"scripts/dashboard.py": "CLASSIFY_HINDI_2026_10_16", "scripts/dashboard_static.html": "REPAIR_HEAL_2026_10_11",
         "scripts/bench_mitra.py": "BENCH_MITRA_2026_10_16", "docs/BENCH_MITRA_2026-10-16.md": "BENCH_MITRA_2026_10_16"}
FILES = list(NEEDS)
TAG = "benchdesk"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, r'''    return jsonify(_status_cached(inbox, raw, dbp, exports))
''', r'''    return jsonify(_status_decorate(_status_cached(inbox, raw, dbp, exports), dbp))   # BENCH_DESK_2026_10_16: the register, the scholarly English
''')

edit('scripts/dashboard.py', 2, r'''                return jsonify(get_summary(con))
''', r'''                return jsonify(_usage_more(con, get_summary(con)))   # BENCH_DESK_2026_10_16: the Claude credit, the steps, BM1
''')

edit('scripts/dashboard.py', 3, r'''BENCH_DIR = ROOT / "data" / "benchmarks"


def _bench(doc: str):''', r'''BENCH_DIR = ROOT / "data" / "benchmarks"


# BENCH_DESK_2026_10_16 -------------------------------------------------------------------------------------------
# What the dashboard shows of the state of things, wired to what can be done about it:
#   - BM1 (scripts/bench_mitra.py, our English against published translations) at the head of the Benchmarks page:
#     what each arm has made, what the judge has read, what it cost, the last report's numbers (marked stale when a
#     step has run since), the caps, and the next step as a button: a job of kind "bench", a paid one asks first and
#     is capped (--max-usd, at most _BM1_MAX_USD a press). Its report is served here, on this computer only.
#   - each row of the dashboard's table says what the register holds of its text (withdrawn, set aside, in repair)
#     and how much of it has scholarly English (a link to /scholar/<doc>);
#   - the Usage tab: the Claude credit beside the spend cap, the steps since the credit began by name (BM1's apart),
#     and BM1's line.
BM1_DIR = pathlib.Path(os.environ.get("SA_BENCH_DIR") or (ROOT.parent / "benchmarks" / "bm1"))
BM1_LEDGER = "data/context.db"   # the real ledger: the caps, and the prices measured
_BM1_MAX_USD = 12.0     # the most one press may spend; above it, run bench_mitra.py by hand
_BM1_CACHE = {"at": 0.0, "res": None}
_BM1_ARMS = ("flash", "sonnet1", "scholar")
_BM1_BILL = {"flash": "the spend cap (Google)", "sonnet1": "the Claude credit",
             "scholar": "the Claude credit (its judge on the spend cap)", "score": "the spend cap (Google)"}


def _bm1_jobs() -> list:
    """BM1's jobs running or waiting (kind "bench")."""
    with JOBS_LOCK:
        return [{"id": j.id, "mode": j.mode, "state": "running" if j.active else "queued",
                 "elapsed_s": round(time.time() - j.start, 1)} for j in JOBS.values() if j.kind == "bench" and j.ok is None]


def _bm1_state(fresh: bool = False, db: str = None) -> dict:
    """BM1 as it stands (read-only): the sample, each arm's verses per text with its price, the judge's reading, the
    spend per arm, the last report's numbers, the caps, and the next step with its price. {"error"} when it cannot be
    read; {"made": False} before its sample is made."""
    now_ = time.time()
    if not fresh and _BM1_CACHE["res"] is not None and now_ - _BM1_CACHE["at"] < 20:
        return dict(_BM1_CACHE["res"], running=_bm1_jobs())
    res = {"dir": str(BM1_DIR), "made": False, "mark": "BENCH_DESK_2026_10_16"}
    db = db or BM1_LEDGER
    try:
        import bench_mitra as bm
        sample = bm.load_sample(BM1_DIR)
        if sample:
            specs = list(bm.FILES)
            res["made"] = True
            res["texts"] = [{"key": f["key"], "title": f["title"], "verses": len(bm.window(sample, f["key"]))}
                            for f in specs]
            p, caps = dict(bm.PRIOR, judge=bm.ST.JUDGE_COST_NOW, how={}), None
            if pathlib.Path(db).exists():
                mcon = bm.open_ro(db)
                try:
                    p = bm.prices(mcon, BM1_DIR)
                    caps = bm.caps(mcon)
                finally:
                    mcon.close()
            res["prices"] = {k: v for k, v in p.items() if k != "how"}
            res["caps"] = caps
            arms = {}
            for arm in bm.ARMS:
                todo = bm.todo_of(BM1_DIR, sample, specs, arm)
                left = sum(todo.values())
                c_, g_ = bm.split_cost(arm, left, p)
                arms[arm] = {"label": bm.ARM[arm]["label"], "todo": todo, "left": left, "usd": round(c_ + g_, 4),
                             "max_usd": max(0.25, round((c_ + g_) * 1.3 + 0.05, 2)), "bill": _BM1_BILL[arm],
                             "how": (p.get("how") or {}).get(arm, "")}
            res["arms"] = arms
            miss = bm.missing_arms(BM1_DIR, sample, specs)
            res["missing"] = [list(m) for m in miss]
            res["judged"] = len(bm.judged(BM1_DIR))
            res["to_judge"] = None if miss else len(bm.judge_tasks(BM1_DIR, sample, specs, True))
            res["spend"] = {a: {"claude": round(v["claude"], 4), "google": round(v["google"], 4)}
                            for a, v in bm.spend(BM1_DIR).items()}
            sp_path, jl, summ = BM1_DIR / "spend.jsonl", BM1_DIR / "judge.jsonl", BM1_DIR / "BM1_summary.json"
            last = max([x.stat().st_mtime for x in (sp_path, jl) if x.exists()] or [0.0])
            if summ.exists():
                try:
                    res["summary"] = json.loads(summ.read_text(encoding="utf-8"))
                    res["summary_at"] = time.strftime("%d %b, %H:%M", time.localtime(summ.stat().st_mtime))
                    res["stale"] = summ.stat().st_mtime < last
                except (OSError, ValueError):
                    pass
            nxt = None
            for arm in bm.ARMS:
                if arms[arm]["left"]:
                    nxt = {"step": "arm", "arm": arm, "usd": arms[arm]["usd"], "max_usd": arms[arm]["max_usd"],
                           "bill": arms[arm]["bill"],
                           "label": "Run %s on the %d verse(s) it has not made" % (arm, arms[arm]["left"])}
                    break
            if nxt is None and res["to_judge"]:
                est = res["to_judge"] * float(p.get("judge") or bm.ST.JUDGE_COST_NOW)
                nxt = {"step": "score", "usd": round(est, 4), "max_usd": max(0.25, round(est * 1.3 + 0.05, 2)),
                       "bill": _BM1_BILL["score"],
                       "label": "Judge the %d English not yet read (the arms' and the published)" % res["to_judge"]}
            if nxt is None and (not summ.exists() or res.get("stale")):
                nxt = {"step": "report", "usd": 0.0, "max_usd": 0.0, "bill": "free", "label": "Make the report again (free)"}
            res["next"] = nxt
    except Exception as ex:   # the dashboard is never stopped by BM1
        res["error"] = "%s: %s" % (type(ex).__name__, str(ex)[:300])
    _BM1_CACHE.update(at=now_, res=res)
    return dict(res, running=_bm1_jobs())


def _bm1_line(s: dict) -> dict:
    """BM1 in one line, for the Usage tab."""
    if not s.get("made"):
        return {"made": False, "error": s.get("error")}
    total = sum(int(t.get("verses") or 0) for t in s.get("texts") or [])
    arms = s.get("arms") or {}
    sp = s.get("spend") or {}
    cl = sum(float(v.get("claude") or 0) for v in sp.values())
    gg = sum(float(v.get("google") or 0) for v in sp.values())
    judge = ("the judge waits for every arm" if s.get("missing") else
             ("the judge has %d English to read" % s["to_judge"]) if s.get("to_judge") else "the judge has read them all")
    return {"made": True, "next": (s.get("next") or {}).get("label") or "",
            "line": "%s of %d verses made; %s; $%.2f spent (Claude $%.2f, Google $%.2f)" % (
                ", ".join("%s %d" % (a, total - int(v.get("left") or 0)) for a, v in arms.items()), total, judge,
                cl + gg, cl, gg)}


def _bm1_usd(x) -> str:
    x = float(x or 0.0)
    return ("$%.2f" % x) if (x >= 0.995 or x == 0) else ("$%.3f" % x)


def _bm1_btn(label: str, step: str, arm: str = "", usd: float = 0.0, ask: str = "", nxt: bool = False) -> str:
    import html as _h
    return ('<button class="tr-rest rp%s" data-step="%s" data-arm="%s" data-usd="%s" data-ask="%s" '
            'onclick="bm1Step(this)">%s</button>' % (" rpnext" if nxt else "", _h.escape(step, quote=True),
                                                     _h.escape(arm, quote=True), ("%.2f" % usd) if usd else "",
                                                     _h.escape(ask, quote=True), _h.escape(label)))


def _bm1_ci(d: dict, key: str) -> str:
    """A difference and its interval, in bold when the interval leaves out nought."""
    v, ci = d.get(key), d.get(key + "_ci")
    if v is None:
        return "-"
    s = "%+.2f" % float(v) + (" [%+.2f, %+.2f]" % (ci[0], ci[1]) if ci else "")
    return ("<b>%s</b>" % s) if ci and (ci[0] > 0 or ci[1] < 0) else s


def _bm1_row(name: str, v: dict, arms: list) -> str:
    import html as _h
    e = _h.escape
    ch = "".join('<td class="n" title="folded: %s">%s</td>' % (e(str((v.get("chrf_folded") or {}).get(a, "-"))),
                                                              e(str((v.get("chrf") or {}).get(a, "-")))) for a in arms)
    jd = v.get("judge") or {}
    js = "".join('<td class="n">%s</td>' % (("%.2f / %.2f &middot; %.0f%%" % (jd[a]["fidelity"], jd[a]["fluency"],
                                                                         jd[a]["pass"])) if a in jd else "-")
                 for a in list(arms) + ["reference"])
    df = v.get("diff") or {}
    ds = "<br>".join("%s: chrF %s%s" % (e(k.replace("-", " - ")), _bm1_ci(d, "chrf"),
                                        ("; fidelity %s" % _bm1_ci(d, "fidelity")) if d.get("fidelity") is not None else "")
                     for k, d in df.items())
    return ('<tr><td>%s%s</td><td class="n">%s (%s)</td>%s%s<td class="bmsmall">%s</td></tr>'
            % (e(name), ('<br><span class="bmsmall">%d unit(s) whose published English seems a neighbour\'s</span>'
                          % v["misaligned"]) if v.get("misaligned") else "", v.get("units", 0), v.get("verses", 0), ch, js,
               ds or "-"))


def _bm1_html() -> str:
    """BM1's section of the Benchmarks page. Never raises."""
    import html as _h
    e = _h.escape
    try:
        s = _bm1_state(fresh=True)
    except Exception as ex:
        s = {"error": "%s: %s" % (type(ex).__name__, ex)}
    head = (_BM1_CSS + '<div class="srcpage bm1" id="bm1"><h2 class="bmh">Translation benchmark: BM1</h2>'
            '<p class="rpintro" style="margin:0 0 10px">Our three ways of making English (gemini-2.5-flash in one pass, as '
            'the working English is made; Claude Sonnet 5.5 in one pass; the scholarly pipeline), on the same 200 verses of '
            'eight Hindu texts, scored against the published English of the Mitrasamgraha test set (chrF) and by our judge '
            'on the Sanskrit alone (judge-v1, unchanged). Private evaluation: the dataset\'s text stays in <code>%s</code>, '
            'outside the repository, and never reaches the site. The method: docs/BENCH_MITRA_2026-10-16.md.</p>'
            % e(s.get("dir") or str(BM1_DIR)))
    out_box = '<div class="rpout" id="bm1out"></div></div><pre class="bmlog" id="bm1log"></pre>'
    if s.get("error"):
        return head + '<p class="srcnone">BM1 could not be read: %s</p></div>' % e(s["error"])
    if not s.get("made"):
        return (head + '<div class="repairbar">' + _bm1_btn("Make the sample (free)", "sample", nxt=True) + out_box
                + '</div>')
    texts, arms, nxt = s.get("texts") or [], s.get("arms") or {}, s.get("next") or {}
    run = s.get("running") or []
    h = [head]
    if run:
        h.append('<p class="bmrun" id="bm1running" data-job="%s">Running: %s (%s, %d min). Its last lines are below; the '
                 'page shows the outcome when it ends.</p>' % (e(run[0]["id"], quote=True), e(run[0]["mode"] or "bench"),
                                                              e(run[0]["state"]), int(run[0]["elapsed_s"] // 60)))
    cp = s.get("caps") or {}
    if cp:
        h.append('<p class="bmcaps">The Claude credit: <b>%s</b> left of %s (it expires %s). The spend cap (Google): '
                 '<b>%s</b> left of %s%s.</p>' % (_bm1_usd(cp.get("credit_left")), _bm1_usd(cp.get("credit_cap")),
                                                  e(str(cp.get("credit_expires") or "")), _bm1_usd(cp.get("cap_left")),
                                                  _bm1_usd(cp.get("cap")), ", paused" if cp.get("paused") else ""))
    if nxt:
        h.append('<p class="bmnextline"><b>Next:</b> %s%s.</p>' % (e(nxt["label"]), (", about %s on %s" % (
            _bm1_usd(nxt["usd"]), e(nxt["bill"]))) if nxt.get("usd") else ""))
    elif not run:
        h.append('<p class="bmnextline"><b>Done:</b> every arm has its English, the judge has read it, and the report is '
                 'up to date. Next come BM3 (the blind side-by-side) and BM2 (a person\'s gold set).</p>')
    th = "".join("<th>%s</th>" % e(a) for a in arms)
    rows = ""
    for t in texts:
        cells = ""
        for a in arms:
            n = int(t["verses"])
            done = n - int((arms[a].get("todo") or {}).get(t["key"], 0))
            cells += ('<td class="bmok">%d/%d &#10003;</td>' % (done, n)) if done >= n else ('<td class="bmtodo">%d/%d</td>'
                                                                                              % (done, n))
        rows += "<tr><td>%s</td>%s</tr>" % (e(t["title"]), cells)
    sp = s.get("spend") or {}

    def spent(a):
        v = sp.get(a) or {}
        parts = [("%s Claude" % _bm1_usd(v["claude"])) if v.get("claude") else "",
                 ("%s Google" % _bm1_usd(v["google"])) if v.get("google") else ""]
        return " + ".join(x for x in parts if x) or "-"
    rows += '<tr class="bmfoot"><td>Spent</td>%s</tr>' % "".join("<td>%s</td>" % e(spent(a)) for a in arms)
    rows += '<tr class="bmfoot"><td>A verse</td>%s</tr>' % "".join(
        '<td title="%s">%s</td>' % (e(arms[a].get("how") or "", quote=True), _bm1_usd((s.get("prices") or {}).get(a)))
        for a in arms)
    h.append('<table class="srct bmgrid"><thead><tr><th>Text</th>%s</tr></thead><tbody>%s</tbody></table>' % (th, rows))
    jline = ("The judge waits until every arm has its English (%s): the scholarly arm's sentences decide the units "
             "every arm is judged on." % e(", ".join("%s on %s" % (m[0], m[1]) for m in (s.get("missing") or [])[:6]))
             if s.get("missing") else ("The judge: %d read, %d to read." % (s.get("judged") or 0, s.get("to_judge") or 0)))
    h.append('<p class="bmcaps">%s</p>' % jline)
    bar = ""
    if not run:
        for a, v in arms.items():
            if v["left"]:
                bar += _bm1_btn("Run %s: %d verse(s), about %s, at most %s" % (a, v["left"], _bm1_usd(v["usd"]),
                                                                            _bm1_usd(v["max_usd"])),
                                "arm", a, v["max_usd"],
                                "Run %s on the %d verse(s) it has not made: it spends at most %s, on %s, and stops before "
                                "spending more. Go?" % (a, v["left"], _bm1_usd(v["max_usd"]), v["bill"]),
                                nxt=(nxt.get("step") == "arm" and nxt.get("arm") == a))
        if not s.get("missing") and s.get("to_judge"):
            sn = nxt if nxt.get("step") == "score" else {}
            est = s["to_judge"] * float((s.get("prices") or {}).get("judge") or 0.0027)
            mx = sn.get("max_usd") or max(0.25, round(est * 1.3 + 0.05, 2))
            bar += _bm1_btn("Judge them: %d English, about %s, at most %s" % (s["to_judge"], _bm1_usd(est), _bm1_usd(mx)),
                            "score", "", mx, "Let judge-v1 read the %d English not yet read (and the published English, "
                            "as a calibration): it spends at most %s, on the spend cap (Google), and stops before "
                            "spending more. Go?" % (s["to_judge"], _bm1_usd(mx)), nxt=bool(sn))
        bar += _bm1_btn("Make the report again (free)", "report", nxt=(nxt.get("step") == "report"))
        bar += _bm1_btn("Settle the ledger (free)", "settle")
    bar += ('<a class="rplink" href="/benchmarks/bm1/report" target="_blank">The full report (private: the dataset\'s '
            'text)</a>')
    h.append('<div class="repairbar">' + bar + out_box)
    summ = s.get("summary") or {}
    sc = summ.get("scopes") or {}
    if sc.get("all", {}).get("units"):
        al = sc["all"]
        aa = [a for a in _BM1_ARMS if a in (al.get("chrf") or {})]
        scored = [t for t in texts if (sc.get(t["key"]) or {}).get("units")]
        note = []
        if len(scored) < len(texts):
            note.append("scored on %d of the %d texts" % (len(scored), len(texts)))
        if not al.get("judge"):
            note.append("the judge has not read them yet: chrF only")
        if s.get("stale"):
            note.append("a step has run since this report: make it again")
        hd = ("<th>Scope</th><th>Units (verses)</th>" + "".join("<th>chrF %s</th>" % e(a) for a in aa)
              + "".join("<th>judge %s</th>" % e(a) for a in aa + ["reference"]) + "<th>Differences [95%]</th>")
        body = "".join(_bm1_row((sc.get(k) or {}).get("name") or k, sc[k], aa) for k in ("all", "core", "aligned")
                       if (sc.get(k) or {}).get("units"))
        per = "".join(_bm1_row(t["title"], sc[t["key"]], aa) for t in scored)
        h.append('<h3 class="bmh3">The last report (%s)%s</h3>' % (e(s.get("summary_at") or ""), (
            ' <span class="bmwarn">%s</span>' % e("; ".join(note))) if note else ""))
        h.append('<table class="srct bmres"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (hd, body))
        if per:
            h.append('<details><summary class="bmsmall">Text by text</summary><table class="srct bmres"><thead><tr>%s</tr>'
                     '</thead><tbody>%s</tbody></table></details>' % (hd, per))
        h.append('<p class="bmsmall">How to read it: chrF is how close an English is to the published 19th-century '
                 'English (higher is closer), not how faithful it is; the scholarly register (modern prose, names in IAST, '
                 'notes apart) is further from it by design. The judge reads the Sanskrit alone: fidelity / fluency, 1 to '
                 '5, and the share of verses with both 4 or more. A difference is in bold when its 95% interval leaves out '
                 'nought.</p>')
    h.append("</div>")
    return "".join(h)


_BM1_CSS = """<style>/* BENCH_DESK_2026_10_16 */
.bm1{margin-bottom:22px;border-bottom:1px solid var(--border);padding-bottom:16px}
.bmh{font-size:15px;color:var(--gold);margin:0 0 6px;font-weight:700}
.bmh3{font-size:13px;color:var(--gold);margin:14px 0 6px;font-weight:600}
.bmcaps,.bmnextline,.bmrun{font-size:12px;margin:6px 0;color:var(--cream)}
.bmrun{color:#e6c27a}
.bmgrid td,.bmgrid th,.bmres td,.bmres th{font-size:11.5px;padding:4px 8px}
.bmok{color:#9fd8b5}.bmtodo{color:#e6c27a}
.bmfoot td{color:var(--muted);font-size:11px}
.bmsmall{font-size:11px;color:var(--muted)}
.bmwarn{font-size:11px;color:#e6c27a;font-weight:400}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.bmlog{display:none;white-space:pre-wrap;font-size:10.5px;line-height:1.4;background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:8px;margin-top:8px;max-height:260px;overflow:auto;color:var(--cream)}
</style>"""

_BM1_JS = r"""
/* BENCH_DESK_2026_10_16: BM1's steps from the page. Each is a run of scripts/bench_mitra.py (a job of kind "bench");
   a paid one asks first and is capped. Its last lines are shown while it runs; its VERDICT and NEXT when it ends. */
var _BM_NL = String.fromCharCode(10);
function _bmOut(t){ var o = document.getElementById('bm1out'); if (o) o.textContent = t; }
function _bmButtons(on){
  var all = document.querySelectorAll('.bm1 button.tr-rest');
  for (var i = 0; i < all.length; i++) all[i].disabled = !on;
}
async function bm1Step(btn){
  var step = btn.getAttribute('data-step'), arm = btn.getAttribute('data-arm') || '';
  var usd = +(btn.getAttribute('data-usd') || 0), ask = btn.getAttribute('data-ask') || '';
  if (ask && !confirm(ask)) return;
  var body = {step: step};
  if (arm) body.arm = arm;
  if (usd) body.max_usd = usd;
  _bmButtons(false); _bmOut('starting...');
  try{
    var r = await fetch('/api/bench', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if (!d.job){ _bmOut('Could not start: ' + (d.error || 'unknown')); _bmButtons(true); return; }
    _bmWatch(d.job);
  }catch(e){ _bmOut('Request failed: ' + e); _bmButtons(true); }
}
async function _bmWatch(id){
  try{
    var j = await (await fetch('/api/job/' + encodeURIComponent(id))).json();
    if (j.error){ _bmOut('The dashboard no longer knows this run (restarted?): its outcome is in the History.'); _bmButtons(true); return; }
    var lines = String(j.out || '').split(_BM_NL).filter(function(l){ return l.trim(); });
    var pre = document.getElementById('bm1log');
    if (pre){ pre.style.display = 'block'; pre.textContent = lines.slice(-16).join(_BM_NL); pre.scrollTop = pre.scrollHeight; }
    if (j.state === 'done'){
      var v = '', n = '';
      (String(j.out || '') + _BM_NL + String(j.err || '')).split(_BM_NL).forEach(function(l){
        if (l.indexOf('VERDICT: ') === 0) v = l.slice(9);
        if (l.indexOf('NEXT: ') === 0) n = l.slice(6);
      });
      _bmOut((v || (j.ok ? 'done' : 'it did not finish: the History has its last lines')) + (n ? '   Next: ' + n : '')
             + '   (the page shows the new state in a moment)');
      setTimeout(function(){ location.reload(); }, 4000);
      return;
    }
    _bmOut((j.state === 'queued' ? 'waiting for its turn' : 'running') + '... ' + Math.round(Date.now() / 1000 - (+j.start || 0)) + ' s');
    setTimeout(function(){ _bmWatch(id); }, 2500);
  }catch(e){ setTimeout(function(){ _bmWatch(id); }, 5000); }
}
(function(){
  var r = document.getElementById('bm1running');
  if (r && r.getAttribute('data-job')){ _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
"""


def _status_decorate(rows: list, dbp) -> list:
    """BENCH_DESK_2026_10_16: each row of /api/status with what the register holds of its text ("held": withdrawn,
    set aside, in repair ...) and its scholarly English ("scholar": verses, passed, flagged ...). The rows as they were
    on any error; nothing is written."""
    try:
        reg = _source_verdicts(pathlib.Path(dbp).parent)
    except Exception:
        reg = {}
    sc = {}
    try:
        con = sqlite3.connect(pathlib.Path(dbp).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            sc = _scholar_cover(con)
        finally:
            con.close()
    except Exception:
        sc = {}
    if not reg and not sc:
        return rows
    out = []
    for r in rows:
        x = dict(r)
        g = reg.get(r.get("doc"))
        if g:
            x["held"] = {"status": g.get("status"), "at": str(g.get("at") or "")[:10], "reason": str(g.get("reason") or "")[:200]}
        c = sc.get(r.get("doc"))
        if c and c.get("verses"):
            x["scholar"] = {k: c.get(k, 0) for k in ("verses", "passed", "flagged", "source_doubt", "accepted", "rejected",
                                                      "stale", "set_aside")}
        out.append(x)
    return out


def _usage_more(con, d: dict) -> dict:
    """BENCH_DESK_2026_10_16: /api/usage with the Claude credit (claude_engine.credit), the steps since it began by
    kind and bill (BM1's kinds bench_* apart), and BM1's line. What was there is left as it was."""
    try:
        import claude_engine as _ce
        c = _ce.credit(con)
        d["credit"] = {"cap": c["cap"], "spent": round(c["spent"], 4), "left": round(max(0.0, c["left"]), 4),
                       "since": c["since"], "expires": c["expires"], "expired": c["expired"], "calls": c["calls"]}
    except Exception as ex:
        d["credit"] = {"error": str(ex)[:200]}
    try:
        since = (d.get("credit") or {}).get("since") or "2026-10-15"
        rows = con.execute("SELECT kind, CASE WHEN engine LIKE 'anthropic:%' THEN 'claude' ELSE 'google' END, COUNT(*), "
                           "COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE ts >= ? GROUP BY 1, 2 ORDER BY 4 DESC",
                           (since,)).fetchall()
        d["kinds_since"] = {"since": since, "rows": [{"kind": k, "bill": b, "calls": n, "cost_usd": round(float(s_), 4)}
                                                     for k, b, n, s_ in rows]}
    except sqlite3.Error:
        pass
    try:
        d["bm1"] = _bm1_line(_bm1_state())
    except Exception:
        pass
    return d


@app.route("/api/bench", methods=["GET", "POST"])
def api_bench():
    """BENCH_DESK_2026_10_16. GET: BM1's state (?fresh=1 reads it again). POST {step: sample | arm | score | report |
    settle, arm, max_usd}: one step of scripts/bench_mitra.py as a job of kind "bench" (doc "BM1"); arm and score are
    paid, need max_usd, at most _BM1_MAX_USD a press, and run with --yes; score reads the published English too."""
    if request.method == "GET":
        return jsonify(_bm1_state(fresh=request.args.get("fresh") == "1"))
    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "")
    if step not in ("sample", "arm", "score", "report", "settle"):
        return jsonify({"error": "unknown step %r (one of sample, arm, score, report, settle)" % step}), 400
    argv, mode = [script("bench_mitra.py")], step
    if step in ("arm", "score"):
        try:
            usd = float(data.get("max_usd"))
        except (TypeError, ValueError):
            return jsonify({"error": "max_usd must be a number"}), 400
        arm = str(data.get("arm") or "")
        if step == "arm" and arm not in _BM1_ARMS:
            return jsonify({"error": "arm must be one of %s" % ", ".join(_BM1_ARMS)}), 400
        if not 0 < usd <= _BM1_MAX_USD:
            return jsonify({"error": "$%.2f is outside what one press may spend (up to $%.2f); run it by hand: python "
                                     "scripts\\bench_mitra.py %s --yes --max-usd %.2f"
                                     % (usd, _BM1_MAX_USD, ("--arm " + arm) if step == "arm" else "--score --judge-reference",
                                        usd)}), 400
        if step == "arm":
            argv += ["--arm", arm, "--yes", "--max-usd", "%.2f" % usd]
            mode = "arm " + arm
        else:
            argv += ["--score", "--judge-reference", "--yes", "--max-usd", "%.2f" % usd]
    else:
        argv.append("--" + step)
    _BM1_CACHE.update(res=None)
    return jsonify({"job": launch("bench", "BM1", py(*argv), mode=mode), "kind": "bench", "step": step})


@app.get("/benchmarks/bm1/report")
def bm1_report():
    """BENCH_DESK_2026_10_16: BM1's report (private: the dataset's text), from the bench folder, on this computer."""
    if not (BM1_DIR / "BM1_report.html").exists():
        return Response("BM1 has no report yet: press Make the report again on the Benchmarks page.", status=404,
                        mimetype="text/plain")
    r = send_from_directory(str(BM1_DIR), "BM1_report.html")
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Robots-Tag"] = "noindex"
    return r


def _bench(doc: str):''')

edit('scripts/dashboard.py', 4, r'''<h1>Benchmarks</h1></header>
""" + body + """''', r'''<h1>Benchmarks</h1></header>
""" + _bm1_html() + body + """''')

edit('scripts/dashboard.py', 5, r'''""" + _REPAIR_JS + """
</script>
</body></html>""")


PATH_FILE = ROOT / "data" / "text_path.json"''', r'''""" + _REPAIR_JS + _BM1_JS + """
</script>
</body></html>""")


PATH_FILE = ROOT / "data" / "text_path.json"''')

edit('scripts/dashboard_static.html', 1, r'''    <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>
''', r'''    <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>
    <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>
''')

edit('scripts/dashboard_static.html', 2, r'''    const docCell =
      '<div class="doc-name">' + esc(r.doc) + '</div>' + ocrLine + compLine +
''', r'''    const docCell =
      '<div class="doc-name">' + esc(r.doc) + '</div>' + ocrLine + compLine + docStateHtml(r) +   // BENCH_DESK_2026_10_16
''')

edit('scripts/dashboard_static.html', 3, r'''function renderPipeline(rows) {
''', r'''// BENCH_DESK_2026_10_16: what the register and the scholarly English say of a text, on its row
var HELD_LABEL = {withdrawn: 'withdrawn from the site', in_repair: 'held from the site (in repair)',
                  set_aside: 'set aside: a better scan', translate_as_is: 'translated as is', complete: 'complete',
                  witness: 'a witness (local only)'};
function docStateHtml(r) {
  var h = '', g = r.held, s = r.scholar;
  if (g && g.status) {
    var bad = g.status === 'withdrawn' || g.status === 'set_aside' || g.status === 'in_repair';
    h += '<span title="' + esc((g.reason || '') + (g.at ? ' (' + g.at + ')' : '')) + '" style="display:inline-block;margin:3px 4px 0 0;'
      + 'padding:1px 6px;border-radius:3px;font-size:9.5px;' + (bad ? 'background:rgba(220,90,90,.15);color:#e8a3a3'
      : 'background:rgba(120,160,200,.15);color:#a9c7e8') + '">' + esc(HELD_LABEL[g.status] || g.status)
      + (g.at ? ' &middot; ' + esc(String(g.at).slice(5)) : '') + '</span>';
  }
  if (s && s.verses) {
    var t = s.verses + ' verses in scholarly English: ' + (s.passed || 0) + ' passed, ' + (s.flagged || 0) + ' flagged, '
      + (s.source_doubt || 0) + ' source doubts' + (s.stale ? ', ' + s.stale + ' stale' : '') + (s.set_aside ? ', ' + s.set_aside
      + ' set aside (not verse)' : '') + '. Open its pages.';
    h += '<a href="/scholar/' + encodeURIComponent(r.doc) + '" target="_blank" title="' + esc(t) + '" style="display:inline-block;'
      + 'margin:3px 4px 0 0;padding:1px 6px;border-radius:3px;font-size:9.5px;background:rgba(201,149,42,.15);color:var(--gold);'
      + 'text-decoration:none">SC ' + s.verses + ' &middot; ' + (s.passed || 0) + ' passed' + (s.flagged ? ' &middot; ' + s.flagged
      + ' flagged' : '') + '</a>';
  }
  return h ? '<div style="line-height:1.2">' + h + '</div>' : '';
}

function renderPipeline(rows) {
''')

edit('scripts/dashboard_static.html', 4, r'''    + '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">Spend cap'
''', r'''    + '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">The spend cap (Google)'
''')

edit('scripts/dashboard_static.html', 5, r'''Every paid step (translation, OCR, pictures, stories, novels) stops at the cap.''', r'''Every Gemini step (translation, OCR, pictures, stories, novels, the judge) stops at the cap; a Claude step stops at the credit below.''')

edit('scripts/dashboard_static.html', 6, r'''async function loadUsage() {   // DESK_HEAL_2026_10_10: cost_tracker's summary as it is (by_engine is an object)
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
''', r'''// BENCH_DESK_2026_10_16: the Claude credit beside the spend cap; the steps by their names; BM1's line
function creditHtml(c) {
  if (!c) return '';
  if (c.cap == null) return c.error ? '<div style="margin-bottom:10px;color:var(--muted)">The Claude credit could not be read: ' + esc(c.error) + '</div>' : '';
  const spent = +c.spent || 0, cap = +c.cap || 0, left = Math.max(0, cap - spent);
  const pct = cap > 0 ? Math.min(100, Math.round(100 * spent / cap)) : 100;
  const col = c.expired || left <= 0 ? 'var(--red)' : pct >= 90 ? 'var(--gold)' : 'var(--green)';
  return '<div style="margin-bottom:10px;padding:8px;border:1px solid var(--border-v);border-radius:6px">'
    + '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">The Claude credit'
    + (c.expired ? ' <span style="color:var(--red)">&middot; expired</span>' : '') + '</div>'
    + '<div>Spent <b>$' + spent.toFixed(2) + '</b> of <b>$' + cap.toFixed(2) + '</b> since ' + esc(c.since || '') + ' &middot; left <b style="color:' + col + '">$'
    + left.toFixed(2) + '</b></div>'
    + '<div style="height:5px;background:var(--bg4);border-radius:999px;overflow:hidden;margin-top:4px">'
    + '<div style="height:100%;width:' + pct + '%;background:' + col + '"></div></div>'
    + '<div style="font-size:9px;color:var(--muted);margin-top:3px">Sonnet, Opus and Haiku calls (' + (+c.calls || 0).toLocaleString()
    + '); it expires on ' + esc(c.expires || '') + '. Every Claude step stops at it. Its size is SA_CLAUDE_CREDIT_USD in .env.</div></div>';
}
var KIND_LABEL = {translation: 'working English', translate_hi: 'Hindi', scholar: 'scholarly English', judge: 'the judge',
                  entities: 'names (entities)', ocr_vision: 'vision OCR', ocr: 'OCR', embedding: 'vectors', probe: 'probes',
                  ask: 'Ask the Corpus', image: 'pictures', story: 'stories',
                  bench_translation: 'BM1: one pass', bench_scholar: 'BM1: scholarly', bench_judge: 'BM1: the judge'};
function kindLabel(k) { return KIND_LABEL[k] || k || ''; }
function engineShort(e) { return String(e || '').replace(/^anthropic:claude-/, '').replace(/^gemini(-vision|-image)?:gemini-/, 'gemini ').replace(/^models\//, ''); }
function bm1UsageHtml(b) {
  if (!b || !b.made) return '';
  return '<div style="margin-bottom:10px;padding:8px;border:1px solid var(--border-v);border-radius:6px">'
    + '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">BM1, the benchmark</div>'
    + '<div>' + esc(b.line || '') + '</div>'
    + (b.next ? '<div style="margin-top:2px">Next: ' + esc(b.next) + '</div>' : '')
    + '<a href="/benchmarks#bm1" target="_blank" style="color:var(--gold);font-size:10px">Open it on the Benchmarks page &rarr;</a></div>';
}

async function loadUsage() {   // DESK_HEAL_2026_10_10: cost_tracker's summary as it is (by_engine is an object); BENCH_DESK_2026_10_16: the two bills
  const el = document.getElementById('usageBody');
  el.innerHTML = '<span style="color:var(--muted)">Loading&hellip;</span>';
  try {
    const r = await fetch('/api/usage');
    const d = await r.json();
    if (d.error) { el.innerHTML = '<span style="color:var(--muted)">' + esc(d.error) + '</span>'; return; }
    const eng = d.by_engine || {};
    const rows = Array.isArray(eng) ? eng.slice() : Object.keys(eng).map(function(k) { return Object.assign({engine: k}, eng[k]); });
    rows.sort(function(a, b) { return (+b.cost_usd || 0) - (+a.cost_usd || 0); });
    const sum = function(f, xs) { return (xs || rows).reduce(function(a, e) { return a + (+e[f] || 0); }, 0); };
    const usd = function(v) { return '$' + (+v || 0).toFixed(2); };
    const isClaude = function(e) { return String(e.engine || '').indexOf('anthropic:') === 0; };
    const calls = rows.length ? sum('calls') : (+d.total_calls || 0);
    const google = rows.filter(function(e) { return !isClaude(e); }), claude = rows.filter(isClaude);
    let html = budgetHtml(d.budget) + creditHtml(d.credit) + bm1UsageHtml(d.bm1) + '<div style="margin-bottom:8px">' +
      '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">What the paid steps used, all time</div>' +
      '<div>API calls: <b>' + calls.toLocaleString() + '</b> &middot; passages: <b>' + sum('passages').toLocaleString() + '</b></div>' +
      '<div>Characters sent: <b>' + sum('in_chars').toLocaleString() + '</b> &middot; received: <b>' + (rows.length ? sum('out_chars') : (+d.total_out_chars || 0)).toLocaleString() + '</b></div>' +
      '<div style="margin-top:4px;color:var(--gold)">Google: <b>' + usd(sum('cost_usd', google)) + '</b> &middot; Claude: <b>' + usd(sum('cost_usd', claude)) + '</b></div>' +
      '<div style="color:var(--muted);font-size:9px;margin-top:2px">' + esc(d.note || 'As the meters record each call: Google against the spend cap, Claude against its credit (the cap above counts only what it has counted since it was set).') + '</div></div>';
    if (rows.length) {
      html += '<table style="width:100%;border-collapse:collapse"><tr style="color:var(--muted)"><th style="text-align:left">Engine</th><th>Bill</th><th>Calls</th><th>Chars out</th><th>Cost</th></tr>';
      rows.forEach(function(e) {
        html += '<tr style="border-top:1px solid rgba(255,255,255,.05)">' +
          '<td style="color:var(--gold);padding:3px 0;word-break:break-all">' + esc(e.engine) + '</td>' +
          '<td style="text-align:center;color:var(--muted)">' + (isClaude(e) ? 'Claude' : 'Google') + '</td>' +
          '<td style="text-align:center">' + (+e.calls || 0).toLocaleString() + '</td>' +
          '<td style="text-align:center">' + (+e.out_chars || 0).toLocaleString() + '</td>' +
          '<td style="text-align:center">' + usd(e.cost_usd) + '</td></tr>';
      });
      html += '</table>';
    }
    const ks = d.kinds_since && d.kinds_since.rows ? d.kinds_since.rows : [];
    if (ks.length) {
      html += '<div style="color:var(--gold);font-weight:600;margin:10px 0 4px">Since ' + esc(d.kinds_since.since) + ', by step</div>' +
        '<table style="width:100%;border-collapse:collapse"><tr style="color:var(--muted)"><th style="text-align:left">Step</th><th>Bill</th><th>Calls</th><th>Cost</th></tr>';
      ks.forEach(function(k) {
        const bench = String(k.kind || '').indexOf('bench_') === 0;
        html += '<tr style="border-top:1px solid rgba(255,255,255,.05)">' +
          '<td style="padding:3px 0;color:' + (bench ? '#a9c7e8' : 'var(--gold)') + '">' + esc(kindLabel(k.kind)) + '</td>' +
          '<td style="text-align:center;color:var(--muted)">' + (k.bill === 'claude' ? 'Claude' : 'Google') + '</td>' +
          '<td style="text-align:center">' + (+k.calls || 0).toLocaleString() + '</td>' +
          '<td style="text-align:center">' + usd(k.cost_usd) + '</td></tr>';
      });
      html += '</table>';
    }
    if (d.recent && d.recent.length) {
      html += '<div style="color:var(--gold);font-weight:600;margin:10px 0 4px">Last paid calls</div>';
      d.recent.slice(0, 10).forEach(function(c) {
        const t = new Date(c.ts);
        const at = isNaN(t) ? String(c.ts || '') : t.toLocaleString('en-IN', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false});
        const bench = String(c.kind || '').indexOf('bench_') === 0;
        html += '<div style="display:flex;gap:6px;border-top:1px solid rgba(255,255,255,.04);padding:2px 0">' +
          '<span style="color:var(--muted);white-space:nowrap">' + esc(at) + '</span>' +
          '<span style="color:' + (bench ? '#a9c7e8' : 'var(--gold)') + '" title="' + esc(c.kind || '') + '">' + esc(kindLabel(c.kind)) + '</span>' +
          '<span style="color:var(--muted);white-space:nowrap">' + esc(engineShort(c.engine)) + '</span>' +
          '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(c.doc || '') + '</span>' +
          '<span>' + (c.cost_usd ? '$' + (+c.cost_usd).toFixed(4) : '') + '</span>' +
          (c.ok === false ? '<span style="color:#f87171">&#x2717;</span>' : '') + '</div>';
      });
    }
    el.innerHTML = html;
  } catch(e) { el.innerHTML = '<span style="color:#f87171">Error: ' + esc(String(e)) + '</span>'; }
}
''')

edit('scripts/bench_mitra.py', 1, r'''def prices(mcon) -> dict:
    """$ a verse for each arm and $ a judge call, measured in data/context.db where there are enough rows."""
''', r'''def prices(mcon, out=None) -> dict:
    """$ a verse for each arm and $ a judge call, measured in data/context.db where there are enough rows.
    BENCH_DESK_2026_10_16: with out (the bench folder), an arm that has made 10 verses or more is priced by its own
    spend (spend.jsonl): on 16 Oct gemini-2.5-flash cost $0.005 a BM1 verse, twice the corpus's $0.00247, and the flash
    arm stopped at --max-usd before its last two texts."""
''')

edit('scripts/bench_mitra.py', 2, r'''    except sqlite3.Error:
        pass
    p["how"] = how
    return p
''', r'''    except sqlite3.Error:
        pass
    if out is not None:   # BENCH_DESK_2026_10_16: an arm's own price, once it has made 10 verses or more
        try:
            sample = load_sample(Path(out))
            sp = spend(Path(out))
            if sample:
                total = sum(1 for x in sample["lines"] if x["role"] == "window")
                for arm in ARMS:
                    v = sp.get(arm)
                    done = total - sum(todo_of(Path(out), sample, list(FILES), arm).values())
                    if v and done >= 10 and (v["claude"] + v["google"]) > 0:
                        p[arm] = (v["claude"] + v["google"]) / done
                        how[arm] = "measured on BM1's own %d verses" % done
        except Exception:
            pass
    p["how"] = how
    return p
''')

edit('scripts/bench_mitra.py', 3, r'''    p = prices(mcon) if mcon else dict(PRIOR, judge=ST.JUDGE_COST_NOW, how={})
''', r'''    p = prices(mcon, out) if mcon else dict(PRIOR, judge=ST.JUDGE_COST_NOW, how={})   # BENCH_DESK_2026_10_16
''')

edit('scripts/bench_mitra.py', 4, r'''        p = prices(mcon)
        todo = todo_of(out, sample, specs, arm)
''', r'''        p = prices(mcon, out)   # BENCH_DESK_2026_10_16: an arm's own price once it has one
        todo = todo_of(out, sample, specs, arm)
''')

edit('scripts/bench_mitra.py', 5, r'''        print("NEXT: start \"\" \"%s\"" % hp)
''', r'''        print('NEXT: Start-Process "%s"   (BENCH_DESK_2026_10_16: or the Benchmarks page)' % hp)
''')

edit('docs/BENCH_MITRA_2026-10-16.md', 1, r'''start "" "D:\Sanksrit Automatons\benchmarks\bm1\BM1_report.html"
''', r'''Start-Process "D:\Sanksrit Automatons\benchmarks\bm1\BM1_report.html"   # BENCH_DESK_2026_10_16 (or the Benchmarks page)
''')

for _f, _n, _o, _new in E:
    assert all(ord(ch) < 128 for ch in _new), "edit %s %d is not ASCII" % (_f, _n)


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
    print("  python -m unittest tests.test_bench_desk_2026_10_16")
    print("  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
