#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_live_budget_2026_10_08.py  (2026-10-08)  LIVE_BUDGET_2026_10_08

Two things seen on the dashboard on 2026-10-08:

  1. "The translation seems stuck." It was not running at all. /api/jobs/running answered 0 jobs;
     data/translation_progress.json had last been written at 2026-10-07 14:18:05 UTC (Ganita,
     p221.2, 242 of 830 verses, "translating..."), and the job had no end record in data/jobs.jsonl:
     it died with the dashboard (the computer or the console was closed that evening). The run never
     rewrote the file, so the Live tab kept showing "running ... Calling API" for 17 hours.
     /api/progress now reports such a file as status "interrupted", with what was done and how to
     continue, when no translation-family job is unfinished here and the file has not changed for 20
     minutes (a recent file is left alone, since a run started from a terminal writes it too). The
     Live tab shows it as "stopped" with that message instead of "Calling API".

  2. "We should be able to modify the allowed budget from the front end." /api/budget could already
     set the cap, but no page called it. The Usage tab now shows the spend cap (spent, cap, left,
     paused), a field to set a new cap and Resume when it is paused. The endpoint checks the value
     (a number above 0, at most $1000), always closes its connection, warns when the cap is at or
     below what is spent, and appends every change to data/budget_changes.jsonl (git-ignored).

  scripts/dashboard.py, scripts/dashboard_static.html, .gitignore
  The dashboard must be restarted to load it (only when idle; it is idle now).

Anchored, all-or-nothing, marker-idempotent; keeps line endings; .py compiled before it replaces
the original; backups .bak_livebudget_<date>.
  python scripts\\patch_live_budget_2026_10_08.py --check
  python scripts\\patch_live_budget_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "LIVE_BUDGET_2026_10_08"

PY_HELPERS = '''
# LIVE_BUDGET_2026_10_08 ------------------------------------------------------------------------
PROGRESS_PATH = ROOT / "data" / "translation_progress.json"
BUDGET_LOG_PATH = ROOT / "data" / "budget_changes.jsonl"
PROGRESS_STALE_S = 20 * 60
BUDGET_MAX_USD = 1000.0


def _translation_job_live() -> bool:
    with JOBS_LOCK:
        return any(j.ok is None and (j.kind.startswith("translate") or j.kind in ("pipeline", "advance_pipeline"))
                   for j in JOBS.values())


def _progress_truth(d):
    """translation_progress.json says 'running' until the run itself rewrites it. A run that dies
    with the dashboard or the computer never does, so the Live tab kept showing 'Calling API' (Ganita,
    from 2026-10-07 14:18 UTC to the next morning, with no job running). With no translation-family
    job unfinished here and the file unchanged for PROGRESS_STALE_S, it is reported as 'interrupted'.
    A recent file is left alone: a run started from a terminal writes it too."""
    if not isinstance(d, dict) or d.get("status") not in ("running", "paused") or _translation_job_live():
        return d
    import datetime as _dt
    try:
        ts = _dt.datetime.fromisoformat(str(d.get("updated_at") or "").replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_dt.timezone.utc)
        age = (_dt.datetime.now(_dt.timezone.utc) - ts).total_seconds()
    except ValueError:
        age = None
    if age is not None and age < PROGRESS_STALE_S:
        return d
    if age is None:
        ago = "at an unknown time"
    elif age >= 3600:
        ago = "%.0f h ago" % (age / 3600)
    else:
        ago = "%.0f min ago" % (age / 60)
    out = dict(d)
    out["status"] = "interrupted"
    out["stale_since"] = d.get("updated_at")
    out["message"] = ("No translation is running. This run stopped at p%s.%s with %s of %s verses done and last "
                      "wrote its progress %s: the dashboard or the computer was closed, or the process was "
                      "stopped, while it ran. Start Translate for this text again; verses already translated "
                      "are kept and skipped." % (d.get("current_page"), d.get("current_idx"),
                                                 d.get("verses_done", 0), d.get("verses_total", 0), ago))
    return out


def _log_budget_change(action, before, after):
    try:
        BUDGET_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BUDGET_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action,
                                "cap_before": before.get("budget_usd"), "cap_after": after.get("budget_usd"),
                                "spent_usd": after.get("spent_usd"), "paused_after": after.get("paused"),
                                "from": request.remote_addr}) + "\\n")
    except Exception:
        pass


'''

OLD_BUDGET = '''@app.post("/api/budget")
def api_budget_set():
    """Set/resume budget. Body: {budget_usd: 15.0} or {resume: true}."""
    db_path = request.args.get("db", "data/context.db")
    data = request.get_json(force=True) or {}
    try:
        import sys as _sys; _sys.path.insert(0, str(SCRIPTS))
        from cost_tracker import ensure_usage_schema, set_budget, resume_budget
        con = sqlite3.connect(db_path)
        ensure_usage_schema(con)
        if data.get("resume"):
            resume_budget(con)
            return jsonify({"resumed": True})
        if "budget_usd" in data:
            set_budget(con, float(data["budget_usd"]))
            return jsonify({"budget_usd": float(data["budget_usd"]), "set": True})
        con.close()
        return jsonify({"error": "specify budget_usd or resume:true"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

NEW_BUDGET = '''@app.post("/api/budget")
def api_budget_set():
    """Set the cap or resume. Body: {budget_usd: 30} or {resume: true}. LIVE_BUDGET_2026_10_08: the
    value is checked (a number above 0, at most BUDGET_MAX_USD), the connection is always closed,
    the answer carries the new state, and every change is appended to data/budget_changes.jsonl."""
    db_path = request.args.get("db", "data/context.db")
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("resume") and "budget_usd" not in data:
        return jsonify({"error": "specify budget_usd or resume:true"}), 400
    new = None
    if "budget_usd" in data:
        try:
            new = float(data["budget_usd"])
        except (TypeError, ValueError):
            return jsonify({"error": "budget_usd must be a number"}), 400
        if new != new or new <= 0 or new > BUDGET_MAX_USD:   # NaN, zero, negative, or absurd
            return jsonify({"error": "budget_usd must be above 0 and at most %g" % BUDGET_MAX_USD}), 400
    con = None
    try:
        import sys as _sys; _sys.path.insert(0, str(SCRIPTS))
        from cost_tracker import ensure_usage_schema, set_budget, resume_budget, get_summary
        con = sqlite3.connect(db_path, timeout=30)
        ensure_usage_schema(con)
        before = dict(get_summary(con)["budget"])
        if new is None:
            resume_budget(con)
        else:
            set_budget(con, new)
        after = dict(get_summary(con)["budget"])
        _log_budget_change("resume" if new is None else "set", before, after)
        out = {"budget_usd": after["budget_usd"], "spent_usd": after["spent_usd"], "paused": after["paused"],
               "remaining_usd": round(after["budget_usd"] - after["spent_usd"], 6)}
        out["resumed" if new is None else "set"] = True
        if after["spent_usd"] >= after["budget_usd"]:
            out["warning"] = "the cap is at or below what is already spent, so paid steps stop at once"
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if con is not None:
            con.close()
'''

JS_FUNCS = r'''// LIVE_BUDGET_2026_10_08: the spend cap, shown and set from the Usage tab
var BUDGET_MSG = '';
function budgetHtml(b) {
  if (!b || b.budget_usd == null) return '';
  const spent = Number(b.spent_usd || 0), cap = Number(b.budget_usd || 0), left = cap - spent;
  const pct = cap > 0 ? Math.min(100, Math.round(100 * spent / cap)) : 100;
  const col = b.paused || left <= 0 ? 'var(--red)' : pct >= 90 ? 'var(--gold)' : 'var(--green)';
  return '<div style="margin-bottom:10px;padding:8px;border:1px solid var(--border-v);border-radius:6px">'
    + '<div style="color:var(--gold);font-weight:600;margin-bottom:4px">Spend cap'
    + (b.paused ? ' <span style="color:var(--red)">&middot; paused</span>' : '') + '</div>'
    + '<div>Spent <b>$' + spent.toFixed(2) + '</b> of <b>$' + cap.toFixed(2) + '</b> &middot; left <b style="color:' + col + '">$'
    + left.toFixed(2) + '</b></div>'
    + '<div style="height:5px;background:var(--bg4);border-radius:999px;overflow:hidden;margin-top:4px">'
    + '<div style="height:100%;width:' + pct + '%;background:' + col + '"></div></div>'
    + '<div style="display:flex;gap:6px;margin-top:6px;align-items:center">'
    + '<label for="budgetCap" style="font-size:10px;color:var(--muted)">New cap $</label>'
    + '<input id="budgetCap" type="number" min="1" max="1000" step="1" value="' + Math.ceil(Math.max(cap, spent + 5)) + '"'
    + ' style="width:70px;background:var(--bg3);border:1px solid var(--border-v);color:var(--ink);border-radius:4px;padding:3px 6px;font-size:11px">'
    + '<button class="btn-batch" onclick="setBudget()">Set cap</button>'
    + (b.paused ? '<button class="btn-batch" onclick="resumeBudget()">Resume</button>' : '')
    + '</div><div id="budgetMsg" style="font-size:9px;color:var(--muted);margin-top:3px">'
    + esc(BUDGET_MSG || 'Every paid step (translation, OCR, pictures, stories, novels) stops at the cap.') + '</div></div>';
}
async function postBudget(body) {
  const msg = document.getElementById('budgetMsg');
  try {
    const r = await fetch('/api/budget', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const j = await r.json();
    if (j.error) { if (msg) msg.textContent = 'Not changed: ' + j.error; return; }
    BUDGET_MSG = (body.resume ? 'Resumed. ' : 'Saved. ') + 'Cap $' + Number(j.budget_usd).toFixed(2) + ', left $'
      + Number(j.remaining_usd).toFixed(2) + (j.warning ? ' - ' + j.warning : '') + '.';
    if (msg) msg.textContent = BUDGET_MSG;
    setTimeout(loadUsage, 800);
  } catch (e) { if (msg) msg.textContent = 'Not changed: ' + e; }
}
function setBudget() {
  const v = parseFloat((document.getElementById('budgetCap') || {}).value);
  if (!(v > 0) || v > 1000) {
    const msg = document.getElementById('budgetMsg');
    if (msg) msg.textContent = 'Enter a cap above $0 and at most $1000.';
    return;
  }
  postBudget({budget_usd: v});
}
function resumeBudget() { postBudget({resume: true}); }

'''

JS_INTERRUPTED = r'''  if (d.status === 'interrupted') {   // LIVE_BUDGET_2026_10_08: a run that died, not one that is calling the API
    el.innerHTML = '<div style="padding:12px;border:1px solid var(--red);border-radius:8px;background:#f8717112">'
      + '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap">'
      + '<span class="pstat-idle" style="color:var(--red)">&#9632; stopped</span>'
      + '<span style="font-size:10px;color:var(--muted);font-family:JetBrains Mono,monospace">' + esc(d.doc || '') + '</span>'
      + '<span style="font-size:10px;color:var(--muted)">' + (d.verses_done || 0) + '/' + (d.verses_total || 0) + ' verses</span></div>'
      + '<div style="font-size:11px;color:var(--ink);line-height:1.5">' + esc(d.message || 'This run is not running.') + '</div></div>';
    return;
  }
'''

EDITS = {
    "scripts/dashboard.py": [
        ("helpers", '@app.get("/api/progress")\n', PY_HELPERS + '@app.get("/api/progress")\n'),
        ("budget endpoint", OLD_BUDGET, NEW_BUDGET),
        ("progress path", '    prog_path = ROOT / "data" / "translation_progress.json"\n',
         '    prog_path = PROGRESS_PATH   # LIVE_BUDGET_2026_10_08\n'),
        ("progress truth", '            return jsonify(json.loads(prog_path.read_text(encoding="utf-8")))\n',
         '            return jsonify(_progress_truth(json.loads(prog_path.read_text(encoding="utf-8"))))\n'),
    ],
    "scripts/dashboard_static.html": [
        ("budget functions", "async function loadUsage() {\n", JS_FUNCS + "async function loadUsage() {\n"),
        ("budget block", "    let html = '<div style=\"margin-bottom:8px\">' +\n"
                         "      '<div style=\"color:var(--gold);font-weight:600;margin-bottom:4px\">Translation Cache</div>' +\n",
         "    let html = budgetHtml(d.budget) + '<div style=\"margin-bottom:8px\">' +\n"
         "      '<div style=\"color:var(--gold);font-weight:600;margin-bottom:4px\">Translation Cache</div>' +\n"),
        ("interrupted", "  const isRun = d.status === 'running';\n", JS_INTERRUPTED + "  const isRun = d.status === 'running';\n"),
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
        p = Path(rel); src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    gi = Path(".gitignore")
    if gi.exists():
        g, nl = load(gi)
        if "data/budget_changes.jsonl" not in g:
            todo.append((gi, (g.rstrip("\n") + "\n# " + MARK + ": the budget change log stays local\n"
                              "data/budget_changes.jsonl\n").replace("\n", nl).encode("utf-8")))
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
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_livebudget_" + stamp))
        t = p.with_name(p.name + ".tmp_livebudget"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Restart the dashboard (it is idle) to load it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
