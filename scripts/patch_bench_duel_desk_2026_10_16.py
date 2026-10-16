#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_duel_desk_2026_10_16.py  (2026-10-16)  BENCH_DUEL_2026_10_16

BM3 (scripts/bench_duel.py, the blind side-by-side of BM1's English, new in this release) on the dashboard, wired as
BM1 is (BENCH_DESK_2026_10_16).

scripts/dashboard.py (needs BENCH_DESK_2026_10_16):
  - the Benchmarks page: BM3's section under BM1's: what each judge has read of the units, what it cost and what a
    reading costs, the caps, the next part (the pilot of 40 units, then 40 more) as a button, the last report's pairs
    with their intervals (each judge apart, and both where they agree), the report and the settling; a job of kind
    "bench3" (doc BM3); a paid press asks first and runs with --units N --with-reference --yes --max-usd (the estimate
    and a third more, at most $12.00 a press); the button is not offered when the spend cap cannot hold its Google
    part;
  - /api/bench: the steps duel, duel_report, duel_settle; /benchmarks/bm3/report serves the private report (on
    127.0.0.1 only);
  - the page's script: the output box of the section whose button was pressed (bm1 or bm3); the units sent.
scripts/dashboard_static.html (needs BENCH_DESK_2026_10_16): the Usage tab names kind bench_duel ("BM3: the
side-by-side").
docs/BENCH_MITRA_2026-10-16.md (needs BENCH_DESK_2026_10_16): the misalignment test, as the full run measured it.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_benchduel_<date>. No database change. Needs scripts/bench_duel.py (this release).
  python scripts\\patch_bench_duel_desk_2026_10_16.py --check
  python scripts\\patch_bench_duel_desk_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "BENCH_DUEL_2026_10_16"
NEEDS = {"scripts/dashboard.py": "BENCH_DESK_2026_10_16", "scripts/dashboard_static.html": "BENCH_DESK_2026_10_16",
         "docs/BENCH_MITRA_2026-10-16.md": "BENCH_DESK_2026_10_16"}
FILES = list(NEEDS)
TAG = "benchduel"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, r'''def _status_decorate(rows: list, dbp) -> list:
''', r'''# BENCH_DUEL_2026_10_16 -------------------------------------------------------------------------------------------
# BM3 (scripts/bench_duel.py), the blind side-by-side of BM1's English, on the Benchmarks page under BM1: what each
# judge has read, the price of the next part, the caps, the last report's pairs, and the steps as buttons (a job of
# kind "bench3", doc BM3); a paid one asks first and runs with --yes --max-usd (at most _BM1_MAX_USD a press), the
# published English among the translations (--with-reference). Its report is served here, on this computer only.
BM3_DIR = pathlib.Path(os.environ.get("SA_BENCH3_DIR") or (ROOT.parent / "benchmarks" / "bm3"))
_BM3_CACHE = {"at": 0.0, "res": None}
_BM3_STEP = 40          # the units a press reads (the pilot, then 40 more)


def _bm3_jobs() -> list:
    """BM3's jobs running or waiting (kind "bench3")."""
    with JOBS_LOCK:
        return [{"id": j.id, "mode": j.mode, "state": "running" if j.active else "queued",
                 "elapsed_s": round(time.time() - j.start, 1)} for j in JOBS.values() if j.kind == "bench3" and j.ok is None]


def _bm3_state(fresh: bool = False) -> dict:
    """BM3 as it stands (read only, bench_duel.state), with the next part's price; {"error"} when it cannot be read."""
    now_ = time.time()
    if not fresh and _BM3_CACHE["res"] is not None and now_ - _BM3_CACHE["at"] < 20:
        return dict(_BM3_CACHE["res"], running=_bm3_jobs())
    try:
        import bench_duel as bd
        res = bd.state(BM1_DIR, BM3_DIR, BM1_LEDGER, step=_BM3_STEP)
        res["next_plan"] = (res.get("plans") or {}).get("next") or {}
        if res.get("summary_mtime"):
            res["summary_at"] = time.strftime("%d %b, %H:%M", time.localtime(res["summary_mtime"]))
    except Exception as ex:   # the dashboard is never stopped by BM3
        res = {"error": "%s: %s" % (type(ex).__name__, str(ex)[:300])}
    _BM3_CACHE.update(at=now_, res=res)
    return dict(res, running=_bm3_jobs())


def _bm3_btn(label: str, step: str, usd: float = 0.0, units: int = 0, ask: str = "", nxt: bool = False) -> str:
    import html as _h
    return ('<button class="tr-rest rp%s" data-box="bm3" data-step="%s" data-usd="%s" data-units="%s" data-ask="%s" '
            'onclick="bm1Step(this)">%s</button>' % (" rpnext" if nxt else "", _h.escape(step, quote=True),
                                                     ("%.2f" % usd) if usd else "", str(units) if units else "",
                                                     _h.escape(ask, quote=True), _h.escape(label)))


_BM3_SHORT = {"gemini:gemini-2.5-pro": "gemini-2.5-pro", "anthropic:claude-opus-5-5": "Claude Opus 5.5"}


def _bm3_pair(d: dict, key: str = "share", ci: str = "ci") -> str:
    v, c = d.get(key), d.get(ci)
    if v is None:
        return "-"
    s = "%.2f" % float(v) + (" [%.2f, %.2f]" % (c[0], c[1]) if c else "")
    return ("<b>%s</b>" % s) if c and (c[0] > 0.5 or c[1] < 0.5) else s


def _bm3_html() -> str:
    """BM3's section of the Benchmarks page. Never raises."""
    import html as _h
    e = _h.escape
    try:
        s = _bm3_state(fresh=True)
    except Exception as ex:
        s = {"error": "%s: %s" % (type(ex).__name__, ex)}
    head = ('<div class="srcpage bm1 bm3" id="bm3"><h2 class="bmh">The blind side-by-side: BM3</h2>'
            '<p class="rpintro" style="margin:0 0 10px">BM1\'s three Englishes of each sentence, and the published '
            'English, side by side: who made each is not said, and the order is shuffled for each judge. Two judges, one '
            'of each family (gemini-2.5-pro and Claude Opus 5.5: scholar_duel.py\'s duel-v1, the Debroy register), give '
            'each translation fidelity, prose and notes and its errors, and rank them. A judge may favour its own '
            'family\'s English, so each is read apart, and where they agree is shown. The method: '
            'docs/BENCH_DUEL_2026-10-16.md.</p>')
    out_box = '<div class="rpout" id="bm3out"></div></div><pre class="bmlog" id="bm3log"></pre>'
    if s.get("error"):
        return head + '<p class="srcnone">BM3 could not be read: %s</p></div>' % e(s["error"])
    if not s.get("ready"):
        return head + '<p class="srcnone">BM3 waits for BM1: %s.</p></div>' % e(s.get("why") or "not ready")
    h = [head]
    run = s.get("running") or []
    if run:
        h.append('<p class="bmrun" id="bm3running" data-job="%s">Running: %s (%s, %d min). Its last lines are below; the '
                 'page shows the outcome when it ends.</p>' % (e(run[0]["id"], quote=True), e(run[0]["mode"] or "duel"),
                                                              e(run[0]["state"]), int(run[0]["elapsed_s"] // 60)))
    cp = s.get("caps") or {}
    total = int(s.get("units_total") or 0)
    rd = s.get("read") or {}
    sp = s.get("spend") or {}
    pr = s.get("prices") or {}
    h.append('<p class="bmcaps">Read so far: %s, of %d units; spent %s (Claude %s, Google %s). The Claude credit: '
             '<b>%s</b> left; the spend cap (Google): <b>%s</b> left of %s%s.</p>' % (
                 e(", ".join("%s %d" % (_BM3_SHORT.get(j, j), rd.get(j, 0)) for j in s.get("judges") or [])), total,
                 _bm1_usd((sp.get("claude") or 0) + (sp.get("google") or 0)), _bm1_usd(sp.get("claude")),
                 _bm1_usd(sp.get("google")), _bm1_usd(cp.get("credit_left")), _bm1_usd(cp.get("cap_left")),
                 _bm1_usd(cp.get("cap")), ", paused" if cp.get("paused") else ""))
    h.append('<p class="bmsmall">A reading costs about %s.</p>' % e("; ".join(
        "%s %s (%s)" % (_BM3_SHORT.get(j, j), _bm1_usd(v.get("each")), v.get("how") or "") for j, v in pr.items())))
    np_ = s.get("next_plan") or {}
    bar = ""
    if np_.get("calls"):
        first = not any(rd.values())
        what = ("the pilot: the first %d units" % np_["units"]) if first else ("the units up to %d" % np_["units"])
        g_left = float(cp.get("cap_left") or 0)
        fits = np_["max_usd"] <= _BM1_MAX_USD and np_["google"] <= g_left
        h.append('<p class="bmnextline"><b>Next:</b> %s, %d readings, about %s (Claude %s, Google %s).%s</p>' % (
            e(what), np_["calls"], _bm1_usd(np_["usd"]), _bm1_usd(np_["claude"]), _bm1_usd(np_["google"]),
            "" if fits else (" The spend cap has %s left: fewer units by hand (python scripts\\bench_duel.py --units N "
                             "--with-reference), or the cap raised (python scripts\\set_budget.py)." % _bm1_usd(g_left))))
        if not run and fits:
            bar += _bm3_btn("Read %s: about %s, at most %s" % (what, _bm1_usd(np_["usd"]), _bm1_usd(np_["max_usd"])),
                            "duel", np_["max_usd"], np_["units"],
                            "Let the two judges read %s (%d readings), the published English among the translations "
                            "(sent to both judges: a private evaluation). It spends at most %s (Claude about %s, Google "
                            "about %s) and stops before spending more. Go?" % (what, np_["calls"], _bm1_usd(np_["max_usd"]),
                                                                              _bm1_usd(np_["claude"]),
                                                                              _bm1_usd(np_["google"])), nxt=True)
    elif total:
        h.append('<p class="bmnextline"><b>Done:</b> both judges have read all %d units. Next: BM2, a person\'s blind '
                 'reading of the same units.</p>' % total)
    if not run:
        bar += _bm3_btn("Make the report again (free)", "duel_report", nxt=bool(s.get("stale")))
        bar += _bm3_btn("Settle the ledger (free)", "duel_settle")
    bar += ('<a class="rplink" href="/benchmarks/bm3/report" target="_blank">The full report (private: the dataset\'s '
            'text)</a>')
    h.append('<div class="repairbar">' + bar + out_box)
    sc = ((s.get("summary") or {}).get("scopes") or {})
    rows = ""
    for k in ("all", "core"):
        v = sc.get(k) or {}
        if not v.get("units"):
            continue
        for j, jn in (v.get("by_judge") or {}).items():
            if not jn.get("units"):
                continue
            ps = jn.get("pairs") or {}
            mm = jn.get("means") or {}
            rows += ('<tr><td>%s</td><td>%s</td><td class="n">%d</td>%s<td class="bmsmall">%s</td></tr>' % (
                e(v.get("name") or k), e(_BM3_SHORT.get(j, j)), jn["units"],
                "".join('<td class="n">%s</td>' % _bm3_pair(ps.get(p) or {}) for p in
                        ("scholar>flash", "scholar>sonnet1", "sonnet1>flash", "scholar>reference")),
                e("; ".join("%s %s, %s major/10" % (a, m.get("fidelity", "-"), m.get("major_per_10", "-"))
                            for a, m in mm.items()))))
        b = v.get("both") or {}
        if b.get("units"):
            ps = b.get("pairs") or {}
            rows += ('<tr><td>%s</td><td>both, where they agree</td><td class="n">%d</td>%s<td class="bmsmall">%s</td>'
                     '</tr>' % (e(v.get("name") or k), b["units"],
                                "".join('<td class="n">%s</td>' % _bm3_pair(ps.get(p) or {}, "consensus", "consensus_ci")
                                        for p in ("scholar>flash", "scholar>sonnet1", "sonnet1>flash",
                                                  "scholar>reference")),
                                e("; ".join("%s: alike %.0f%%%s" % (p, 100 * d.get("agree", 0), (
                                    ", split by family %d" % d["split_own_family"]) if "split_own_family" in d else "")
                                    for p, d in ps.items() if not p.endswith("reference")))))
    if rows:
        h.append('<h3 class="bmh3">The last report (%s)%s</h3>' % (e(s.get("summary_at") or ""), (
            ' <span class="bmwarn">a reading has been made since: make it again</span>') if s.get("stale") else ""))
        h.append('<table class="srct bmres"><thead><tr><th>Scope</th><th>Judge</th><th>Units</th><th>scholar above '
                 'flash</th><th>scholar above sonnet1</th><th>sonnet1 above flash</th><th>scholar above the published'
                 '</th><th>Fidelity; major errors per 10 verses</th></tr></thead><tbody>%s</tbody></table>' % rows)
        h.append('<p class="bmsmall">How to read it: a share above 0.50 means the first is ranked above the second '
                 '(a tie counts a half), weighted by verses; in bold when its 95% interval leaves out 0.50. gemini-2.5-pro '
                 'may favour the flash arm (its family), Claude Opus the Sonnet arms: "scholar above sonnet1" is the '
                 'cleanest reading by gemini-2.5-pro (neither is its family), and a pair the two judges order alike is '
                 'the firmest.</p>')
    h.append("</div>")
    return "".join(h)


def _bm3_post(data: dict, step: str):
    """BENCH_DUEL_2026_10_16: one step of scripts/bench_duel.py as a job of kind "bench3" (doc BM3)."""
    argv, mode = [script("bench_duel.py")], step
    if step == "duel":
        try:
            usd = float(data.get("max_usd"))
            units = int(data.get("units"))
        except (TypeError, ValueError):
            return jsonify({"error": "max_usd (a number) and units (a whole number) are needed"}), 400
        if not 0 < usd <= _BM1_MAX_USD:
            return jsonify({"error": "$%.2f is outside what one press may spend (up to $%.2f); run it by hand: python "
                                     "scripts\\bench_duel.py --units %d --with-reference --yes --max-usd %.2f"
                                     % (usd, _BM1_MAX_USD, units, usd)}), 400
        if not 0 < units <= 2000:
            return jsonify({"error": "units must be between 1 and 2000"}), 400
        argv += ["--units", str(units), "--with-reference", "--yes", "--max-usd", "%.2f" % usd]
        mode = "duel %d" % units
    else:
        argv.append("--report" if step == "duel_report" else "--settle")
    _BM3_CACHE.update(res=None)
    return jsonify({"job": launch("bench3", "BM3", py(*argv), mode=mode), "kind": "bench3", "step": step})


@app.get("/benchmarks/bm3/report")
def bm3_report():
    """BENCH_DUEL_2026_10_16: BM3's report (private: the dataset's text), from its folder, on this computer."""
    if not (BM3_DIR / "BM3_report.html").exists():
        return Response("BM3 has no report yet: press Make the report again on the Benchmarks page.", status=404,
                        mimetype="text/plain")
    r = send_from_directory(str(BM3_DIR), "BM3_report.html")
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Robots-Tag"] = "noindex"
    return r


def _status_decorate(rows: list, dbp) -> list:
''')

edit('scripts/dashboard.py', 2, r'''    step = str(data.get("step") or "")
    if step not in ("sample", "arm", "score", "report", "settle"):
''', r'''    step = str(data.get("step") or "")
    if step in ("duel", "duel_report", "duel_settle"):   # BENCH_DUEL_2026_10_16: BM3's steps
        return _bm3_post(data, step)
    if step not in ("sample", "arm", "score", "report", "settle"):
''')

edit('scripts/dashboard.py', 3, r'''<h1>Benchmarks</h1></header>
""" + _bm1_html() + body + """''', r'''<h1>Benchmarks</h1></header>
""" + _bm1_html() + _bm3_html() + body + """''')

edit('scripts/dashboard.py', 4, r'''function _bmOut(t){ var o = document.getElementById('bm1out'); if (o) o.textContent = t; }
''', r'''var _BM_BOX = 'bm1';   // BENCH_DUEL_2026_10_16: the section whose step runs (bm1, bm3)
function _bmOut(t){ var o = document.getElementById(_BM_BOX + 'out'); if (o) o.textContent = t; }
''')

edit('scripts/dashboard.py', 5, r'''  var usd = +(btn.getAttribute('data-usd') || 0), ask = btn.getAttribute('data-ask') || '';
''', r'''  var usd = +(btn.getAttribute('data-usd') || 0), ask = btn.getAttribute('data-ask') || '';
  _BM_BOX = btn.getAttribute('data-box') || 'bm1';   // BENCH_DUEL_2026_10_16
''')

edit('scripts/dashboard.py', 6, r'''  if (usd) body.max_usd = usd;
''', r'''  if (usd) body.max_usd = usd;
  if (btn.getAttribute('data-units')) body.units = +btn.getAttribute('data-units');   // BENCH_DUEL_2026_10_16
''')

edit('scripts/dashboard.py', 7, r'''    var pre = document.getElementById('bm1log');
''', r'''    var pre = document.getElementById(_BM_BOX + 'log');   // BENCH_DUEL_2026_10_16
''')

edit('scripts/dashboard.py', 8, r'''  if (r && r.getAttribute('data-job')){ _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
''', r'''  if (r && r.getAttribute('data-job')){ _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
(function(){   // BENCH_DUEL_2026_10_16: a BM3 run going on when the page opens
  var r = document.getElementById('bm3running');
  if (r && r.getAttribute('data-job')){ _BM_BOX = 'bm3'; _bmButtons(false); _bmWatch(r.getAttribute('data-job')); }
})();
''')

edit('scripts/dashboard.py', 9, r'''td.n{text-align:right;font-variant-numeric:tabular-nums}
''', r'''td.n{text-align:right;font-variant-numeric:tabular-nums}
@media (max-width:900px){.bm1{overflow-x:auto}}   /* BENCH_DUEL_2026_10_16: on a phone the section scrolls, its tables whole */
''')

edit('scripts/dashboard_static.html', 1, r'''bench_translation: 'BM1: one pass', bench_scholar: 'BM1: scholarly', bench_judge: 'BM1: the judge'};''', r'''bench_translation: 'BM1: one pass', bench_scholar: 'BM1: scholarly', bench_judge: 'BM1: the judge',
                  bench_duel: 'BM3: the side-by-side'};   // BENCH_DUEL_2026_10_16''')

edit('docs/BENCH_MITRA_2026-10-16.md', 1, r'''  ("aligned"). The judge, which reads the Sanskrit alone, is not touched by it.
''', r'''  ("aligned"). The judge, which reads the Sanskrit alone, is not touched by it.
  *Measured on the full run (BENCH_DUEL_2026_10_16):* the test marks none of the 200. The Satapatha's pairs drift
  rather than shift one for one: line 156's published English renders lines 155 and 156 together, and line 155's
  seems to close the sentence before; a neighbour's English, longer, does not fit better by 10 points (chrF weighs
  recall). So that text's chrF is lower for every arm alike, and the paired differences stand. Scored over each
  text's whole window (its lines joined, so that a boundary does not count), chrF orders the arms as before
  (docs/BM1_RESULTS_2026-10-16.md).
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
    bd = Path("scripts/bench_duel.py")
    if not bd.exists() or MARK.encode() not in bd.read_bytes():
        print("REFUSE: scripts/bench_duel.py (this release) is not there. Nothing written."); return 1
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
    print("  python -m unittest tests.test_bench_duel_desk_2026_10_16 tests.test_bench_duel_2026_10_16")
    print("  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
