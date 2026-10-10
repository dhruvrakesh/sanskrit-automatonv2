#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_live_log_2026_10_10.py  (2026-10-10)  LIVE_LOG_2026_10_10

What was seen at 16:24-16:31 on 2026-10-10 (docs/LIVE_LOG_2026-10-10.md):

  "Adding or queueing translation jobs from the Library or the dashboard does not queue jobs, and the
  console does not seem live." Every press made a job, and every job ran (data/jobs.jsonl):
    Ganita (both, and Hindi)          ran: 7 of 186 sent, 185 below the OCR quality bar
    Vasishtha Dhanur Veda (both)      ran: 1 of 1
    Hayashirsha, Natyasastra, Karan,  held by the OCR-debris guard (exit 3) in 0.2-0.3 s each, or as soon
    Tantric Texts (both languages)    as the translate lock was free
  Nothing said so, for four reasons:
    1. The dashboard runs a job with communicate(), so a job's output reached /api/job only when it
       ended: the Log was silent while a job ran.
    2. A job started outside the page (the Library, another tab, before the page loaded) got a badge
       but was never followed: no lines in the Log, no outcome, and its badge stayed "running".
    3. A job that started and ended between two looks (a hold takes 0.3 s) never appeared at all.
    4. The Log said only [OK] or [FAIL]: a hold read as a failure, and "nothing to do" as success.
  Also: the Log stopped showing new lines once a job had written 6,000 characters (it compared lengths
  of a 6,000-character window), and the Live tab showed "NaNm NaNs" (started_at carries +00:00 and the
  page appended "Z").

  scripts/dashboard.py (takes effect on a restart, when idle)
    _run_job reads the job's output line by line while it runs (two readers, as communicate() has), so
    /api/job shows the last 200 lines as they come. A job that is stopped by hand keeps its output.
  scripts/dashboard_static.html (takes effect on a reload)
    The Log follows every job, wherever it was started; writes each outcome as what it is ([HELD] with
    the OCR-consensus command, [NOTHING], [OK] N of M with what was below the OCR bar, [STOPPED],
    [FAIL]); catches runs that started and ended between looks from the job history; opens with the
    last five runs instead of "Awaiting jobs"; keeps showing new lines past 6,000 characters. The Live
    tab shows the time a run has taken.

Needs DESK_HEAL_2026_10_10. Anchored, all-or-nothing, marker-idempotent per file; keeps line endings;
the .py is compiled before it replaces the original; backups .bak_livelog_<date>.
  python scripts\\patch_live_log_2026_10_10.py --check
  python scripts\\patch_live_log_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "LIVE_LOG_2026_10_10"
NEEDS = "DESK_HEAL_2026_10_10"

# ---- scripts/dashboard.py -------------------------------------------------------------------

OLD_RUNJOB = '''def _run_job(job: Job):
    try:
        proc = subprocess.Popen(
            job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), env=_child_env()
        )
        job.proc = proc  # store so it can be killed
        out, err = proc.communicate()
        job.rc = proc.returncode          # (JOB_DIAG_2026_09_06)
        if job.killed:
            job.ok  = False
            job.err = "[KILLED by user]"
        else:
'''

NEW_RUNJOB = '''LIVE_LINES = 200   # LIVE_LOG_2026_10_10: how many of a running job's last lines /api/job shows


def _pump(stream, chunks: list, job: Job, attr: str) -> None:
    """LIVE_LOG_2026_10_10: read one of a job's pipes line by line while it runs. Every line is kept for
    the end, as communicate() kept them, and the job's .out/.err show the last LIVE_LINES meanwhile, so
    /api/job and the page's Log follow the run instead of waiting for it to end."""
    try:
        for raw in iter(stream.readline, b""):
            chunks.append(raw)
            setattr(job, attr, b"".join(chunks[-LIVE_LINES:]).decode("utf-8", "replace"))
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _run_job(job: Job):
    try:
        proc = subprocess.Popen(
            job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), env=_child_env()
        )
        job.proc = proc  # store so it can be killed
        # LIVE_LOG_2026_10_10: two readers, as communicate() has, so neither pipe fills and blocks the job
        out_chunks: list = []
        err_chunks: list = []
        readers = [threading.Thread(target=_pump, args=(proc.stdout, out_chunks, job, "out"), daemon=True),
                   threading.Thread(target=_pump, args=(proc.stderr, err_chunks, job, "err"), daemon=True)]
        for t in readers:
            t.start()
        proc.wait()
        for t in readers:
            t.join(timeout=15)
        out, err = b"".join(out_chunks), b"".join(err_chunks)
        job.rc = proc.returncode          # (JOB_DIAG_2026_09_06)
        if job.killed:
            job.ok  = False
            job.out = (out or b"").decode("utf-8", "replace")   # LIVE_LOG_2026_10_10: what it did before
            job.err = "[KILLED by user]"
        else:
'''

# ---- scripts/dashboard_static.html ----------------------------------------------------------

OLD_CSS = '''.log-line-info{color:var(--gold)}
'''
NEW_CSS = '''.log-line-info{color:var(--gold)}
.log-line-held{color:var(--gold);font-weight:600}
.log-line-past{color:var(--muted)}
'''

OLD_POLLJOB = r'''      // Only show new output lines
      if (j.out && j.out.length > lastOutLen) {
        const newText = j.out.slice(lastOutLen);
        lastOutLen = j.out.length;
        newText.split('\n').filter(function(l) { return l.trim(); }).slice(-6)
          .forEach(function(l) { addLog('  ' + l); });
      }
      if (!j.running) {
        activeJobs[jid].done = true;
        activeJobs[jid].ok   = j.ok;
        addLog((j.ok ? '[OK] ' : '[FAIL] ') + label, j.ok ? 'log-line-ok' : 'log-line-err');
        if (j.err && !j.ok) addLog(j.err.slice(0, 400), 'log-line-err');
        toast(label + ': ' + (j.ok ? 'done' : 'FAILED'), j.ok ? 'ok' : 'fail');
'''
NEW_POLLJOB = r'''      // Only show new output lines. LIVE_LOG_2026_10_10: /api/job sends the last 6,000 characters, so
      // comparing lengths stopped once a job had written that much; the last line shown marks the place
      const lines = _outLines(j.out);
      _newLines(lastLine, lines).slice(-12).forEach(function(l) { addLog('  ' + l); });
      if (lines.length) lastLine = lines[lines.length - 1];
      if (!j.running) {
        activeJobs[jid].done = true;
        activeJobs[jid].ok   = j.ok;
        const v = jobVerdict(j.ok, (j.out || '') + '\n' + (j.err || ''));
        activeJobs[jid].verdict = v.word;
        _seenFinished.add(jid);
        addLog(v.tag + ' ' + label + ' - ' + v.text, v.cls);
        if (j.err && j.ok === false && v.word === 'failed') addLog(j.err.slice(0, 400), 'log-line-err');
        toast(label + ': ' + v.word, v.word === 'failed' || v.word === 'stopped' ? 'fail' : 'ok');
'''

OLD_POLLJOB_HEAD = '''  let lastOutLen = 0;
  let elapsed    = 0;
'''
NEW_POLLJOB_HEAD = '''  let lastLine   = '';   // LIVE_LOG_2026_10_10
  let elapsed    = 0;
'''

OLD_ADOPT = '''      d.running.forEach(function(sj) {
        const found = Object.values(activeJobs).find(function(j) { return j.doc === sj.doc && !j.done; });
        if (!found) {
          activeJobs[sj.id] = {label: sj.kind + ' ' + sj.doc, kind: sj.kind, doc: sj.doc, done: false, ok: null};
        }
      });
'''
NEW_ADOPT = '''      d.running.forEach(function(sj) {
        // LIVE_LOG_2026_10_10: a job started outside this page (the Library, another tab, before the page
        // loaded) is followed like one started here: its lines, its outcome, and its badge ends with it
        if (!activeJobs[sj.id]) {
          const label = sj.kind + ' ' + sj.doc;
          activeJobs[sj.id] = {label: label, kind: sj.kind, doc: sj.doc, done: false, ok: null, active: sj.active};
          addLog('> ' + label + ' (' + (sj.state || 'running') + '; started outside this page)', 'log-line-info');
          renderBadges();
          pollJob(sj.id, label);
        }
      });
'''

OLD_ELAPSED = '''  let elapsed = '';
  if (d.started_at) {
    const s = Math.round((Date.now() - new Date(d.started_at + 'Z').getTime()) / 1000);
    elapsed = s < 60 ? s + 's' : Math.floor(s/60) + 'm ' + (s%60) + 's';
  }
'''
NEW_ELAPSED = '''  let elapsed = '';   // LIVE_LOG_2026_10_10: started_at carries its offset (+00:00); a finished run shows its time
  if (d.started_at) {
    const t0 = _isoMs(d.started_at);
    const t1 = (isDone || isPause) && d.updated_at ? _isoMs(d.updated_at) : Date.now();
    const s = Math.max(0, Math.round((t1 - t0) / 1000));
    if (!isNaN(s)) elapsed = (s < 60 ? s + 's' : s < 3600 ? Math.floor(s/60) + 'm ' + (s%60) + 's'
                              : Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm') + (isDone ? ' taken' : '');
  }
'''

OLD_INIT = '''setInterval(pollProgress, 2000);
pollRunningJobs();
pollProgress();
'''
NEW_INIT = r'''setInterval(pollProgress, 2000);
pollRunningJobs();
pollProgress();

// LIVE_LOG_2026_10_10 ---------------------------------------------------------------------------
// The Log tells what each run did. A hold by the OCR-debris guard is not a failure, and "nothing to do"
// is not a translation. Runs that start and end between two looks (a hold takes 0.3 s) are caught from
// the job history, so a press in the Library shows here too.
function _isoMs(x) {
  x = String(x || '');
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(x) ? x : x + 'Z').getTime();
}
function _outLines(out) {
  return String(out || '').split('\n').map(function(l) { return l.replace(/\r$/, ''); })
    .filter(function(l) { return l.trim(); });
}
function _newLines(prev, lines) {
  if (!prev) return lines.slice(-6);
  const i = lines.lastIndexOf(prev);
  return i < 0 ? lines.slice(-6) : lines.slice(i + 1);
}
function jobVerdict(ok, out) {
  out = String(out || '');
  if (ok === false && /TRANSLATE_DEBRIS_GUARD|allow-debris/.test(out)) {
    const m = out.match(/ocr_consensus\.py --doc (\S+)/);
    return {word: 'held', tag: '[HELD]', cls: 'log-line-held',
            text: 'held by the OCR-debris guard: its scan carries Tesseract debris, so the source is repaired first'
                  + (m ? '. Plan the repair, no spend: python scripts\\ocr_consensus.py --doc ' + m[1]
                         + ' --threshold 101 --include-unassessed' : '')};
  }
  if (ok === false && /KILLED/.test(out)) return {word: 'stopped', tag: '[STOPPED]', cls: 'log-line-err', text: 'stopped by hand'};
  if (ok === false) return {word: 'failed', tag: '[FAIL]', cls: 'log-line-err', text: 'failed: History has its last lines'};
  const done = Array.from(out.matchAll(/Done\. (\d+)\/(\d+) translated \| (\d+) quality-skipped/g));
  if (done.length) {
    const sent = done.reduce(function(a, m) { return a + (+m[1]); }, 0);
    return {word: sent ? 'done' : 'nothing sent', tag: sent ? '[OK]' : '[NOTHING]', cls: sent ? 'log-line-ok' : 'log-line-info',
            text: done.map(function(m) { return m[1] + ' of ' + m[2] + ' translated' + (+m[3] ? ', ' + m[3] + ' below the OCR quality bar' : ''); }).join('; ')};
  }
  if (/\[NOTHING\]/.test(out)) return {word: 'nothing to do', tag: '[NOTHING]', cls: 'log-line-info',
                                       text: 'nothing to translate: every verse has it, or what is left is illegible OCR'};
  return {word: 'done', tag: '[OK]', cls: 'log-line-ok', text: 'done'};
}
const _seenFinished = new Set();
let _historySeeded = false;
function _logFinished(r, past) {
  const v = jobVerdict(r.ok, String(r.out_tail || '') + '\n' + String(r.err_preview || ''));
  const at = r.end ? new Date(r.end * 1000).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit', hour12: false}) : '';
  addLog(v.tag + ' ' + at + ' ' + (r.kind || '') + ' ' + (r.doc || '') + ' - ' + v.text, past ? 'log-line-past' : v.cls);
  return v;
}
async function watchFinished() {
  if (document.hidden && _historySeeded) return;
  try {
    const rows = await (await fetch('/api/jobs/history?limit=15')).json();
    if (!Array.isArray(rows)) return;
    if (!_historySeeded) {
      _historySeeded = true;
      rows.forEach(function(r) { _seenFinished.add(r.id); });
      const last = rows.slice(0, 5).reverse();
      if (last.length) {
        addLog('-- the last ' + last.length + ' runs, from the job history --', 'log-line-past');
        last.forEach(function(r) { _logFinished(r, true); });
      }
      return;
    }
    rows.slice().reverse().forEach(function(r) {
      if (_seenFinished.has(r.id)) return;
      const a = activeJobs[r.id];
      if (a && !a.done) return;                 // pollJob follows it and writes its outcome
      _seenFinished.add(r.id);
      if (a && a.done) return;                  // written already
      const v = _logFinished(r, false);
      activeJobs[r.id] = {label: (r.kind || '') + ' ' + (r.doc || ''), kind: r.kind, doc: r.doc, done: true, ok: r.ok, verdict: v.word};
      toast((r.kind || '') + ' ' + (r.doc || '') + ': ' + v.word, v.word === 'failed' ? 'fail' : 'ok');
      renderBadges();
    });
  } catch (e) {}
}
watchFinished();
setInterval(watchFinished, 8000);
'''

OLD_BADGE = '''    return '<span class="badge ' + (j.ok ? 'ok' : 'fail') + '"><span class="badge-dot"></span>' + esc(j.label) + '</span>';
'''
NEW_BADGE = '''    // LIVE_LOG_2026_10_10: a run held on purpose is not shown as a failure
    const held = j.verdict === 'held';
    return '<span class="badge ' + (held ? 'queued' : (j.ok ? 'ok' : 'fail')) + '"' + (j.verdict ? ' title="' + esc(j.verdict) + '"' : '')
      + '><span class="badge-dot"></span>' + esc(j.label) + (held ? ' (held)' : '') + '</span>';
'''

EDITS = {
    "scripts/dashboard.py": [
        ("_run_job reads while it runs", OLD_RUNJOB, NEW_RUNJOB),
    ],
    "scripts/dashboard_static.html": [
        ("log css", OLD_CSS, NEW_CSS),
        ("pollJob head", OLD_POLLJOB_HEAD, NEW_POLLJOB_HEAD),
        ("pollJob lines and outcome", OLD_POLLJOB, NEW_POLLJOB),
        ("follow jobs started elsewhere", OLD_ADOPT, NEW_ADOPT),
        ("held badge", OLD_BADGE, NEW_BADGE),
        ("live tab time", OLD_ELAPSED, NEW_ELAPSED),
        ("watch the history", OLD_INIT, NEW_INIT),
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
        if NEEDS not in src:
            problems.append("%s does not carry %s: run scripts\\patch_desk_heal_2026_10_10.py first" % (rel, NEEDS))
            continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_livelog_" + stamp))
        t = p.with_name(p.name + ".tmp_livelog"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Reload the dashboard page (Ctrl+F5): the Log follows every job now. dashboard.py takes it (output")
    print("while a job runs) when the dashboard is restarted, only when idle: scripts\\restart_dashboard.ps1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
