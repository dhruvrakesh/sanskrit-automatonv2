#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_cost_truth_2026_10_15.py  (2026-10-15)  COST_TRUTH_2026_10_15

What a call costs, metered as Google bills it; a job stopped while queued does not start; the scholarly English is not
held up by a job that only adds working English.

Found on 15 Oct in usage_log (scholar-v2's run of 14 Oct, 21:13): five drafts came back empty, cut off at the token
limit by gemini-2.5-pro's thinking (8,192 tokens), and each was metered as its input alone (out_tokens 0, $0.0038
to $0.0052). Their retries were metered for their visible output only (1,235 tokens for 3,931 characters). The SDK on
this PC does not name thoughts_token_count, so usage_meter.usage_from_response() and infer_mt._usage_add() never saw
the thinking, which Google bills as output (gemini-2.5-pro $10, gemini-2.5-flash $2.50 a million tokens). The spend
recorded, and so the spend cap and the scholarly English's price, leave the thinking out.

This patch:
  usage_meter.py, infer_mt.py: the output billed is total_token_count - prompt_token_count when that is more than the
    candidates and the thoughts named (total = prompt + candidates + thoughts on every SDK). source_desk.py meters
    through usage_from_response (it read the candidates only).
  scholar_translate.py:
    the price counts only rows metered so (created from METERED_SINCE, 2026-10-15); before 10 of them, the prior,
    which now assumes 3,000 output tokens a call with the thinking (it said 1,500);
    a job that only adds working English (translate, translate_both, translate_one) does not stop a run, as a Hindi
    job did not: it never changes the Sanskrit a row is made from. A job that changes the Sanskrit still does.
  dashboard.py: a job stopped while it waits for its lock no longer starts when its turn comes (it used to run in
    full and be called killed afterwards); /api/job/<id>/kill says "queued": true for such a job.
Nothing in the database is changed. The rows already in usage_log stay as they were metered.

Needs SCHOLAR_V21_2026_10_14 (scholar_translate.py) and SCHOLAR_V2_2026_10_14 (dashboard.py).
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and encodings; each .py is compiled before it
replaces the original; backups .bak_costtruth_<date>.
  python scripts\\patch_cost_truth_2026_10_15.py --check
  python scripts\\patch_cost_truth_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "COST_TRUTH_2026_10_15"
NEEDS = {"scripts/usage_meter.py": "def usage_from_response", "scripts/infer_mt.py": "def _usage_add",
         "scripts/source_desk.py": "SOURCE_DESK_2026_10_11", "scripts/scholar_translate.py": "SCHOLAR_V21_2026_10_14",
         "scripts/dashboard.py": "SCHOLAR_V2_2026_10_14"}
FILES = list(NEEDS)

E = []   # (file, number, old, new)
def edit(f, n, old, new):
    E.append((f, n, old, new))


UM = 'scripts/usage_meter.py'
edit(UM, 1,
     r'''        think = getattr(um, "thoughts_token_count", None) or 0
        if pin is None and out is None:
            return None, None
        return float(pin or 0), float((out or 0) + (think or 0))
''',
     r'''        think = getattr(um, "thoughts_token_count", None) or 0
        if pin is None and out is None:
            return None, None
        billed = float((out or 0) + (think or 0))
        # COST_TRUTH_2026_10_15: an SDK that does not name thoughts_token_count still counts the thinking in
        # total_token_count (prompt + candidates + thoughts), and Google bills it as output. Without this a
        # gemini-2.5 call was metered for its input and its visible output only.
        total = getattr(um, "total_token_count", None)
        if total and pin is not None and float(total) - float(pin) > billed:
            billed = float(total) - float(pin)
        return float(pin or 0), billed
''')

IM = 'scripts/infer_mt.py'
edit(IM, 1,
     r'''        think = getattr(um, "thoughts_token_count", None) or 0
        if pin is None and out is None:
            return
        _USAGE["in"] += float(pin or 0)
        _USAGE["out"] += float((out or 0) + think)
''',
     r'''        think = getattr(um, "thoughts_token_count", None) or 0
        if pin is None and out is None:
            return
        billed = float((out or 0) + think)
        total = getattr(um, "total_token_count", None)   # COST_TRUTH_2026_10_15: the thinking, where it is not named
        if total and pin is not None and float(total) - float(pin) > billed:
            billed = float(total) - float(pin)
        _USAGE["in"] += float(pin or 0)
        _USAGE["out"] += billed
''')

SD = 'scripts/source_desk.py'
edit(SD, 1,
     r'''            u = getattr(resp, "usage_metadata", None)
            cost_tracker.log_api_call(con, kind="source_desk", doc=doc, engine="gemini:gemini-2.5-flash",
                                      in_chars=len(prompt), out_chars=len(text), duration_s=time.time() - t0,
                                      passages=0, ok=bool(by),
                                      in_tokens=getattr(u, "prompt_token_count", None) if u else None,
                                      out_tokens=getattr(u, "candidates_token_count", None) if u else None)
''',
     r'''            try:   # COST_TRUTH_2026_10_15: the thinking too, as the meter reads it
                from usage_meter import usage_from_response
                _in, _out = usage_from_response(resp)
            except Exception:
                _in = _out = None
            cost_tracker.log_api_call(con, kind="source_desk", doc=doc, engine="gemini:gemini-2.5-flash",
                                      in_chars=len(prompt), out_chars=len(text), duration_s=time.time() - t0,
                                      passages=0, ok=bool(by), in_tokens=_in, out_tokens=_out)
''')

ST = 'scripts/scholar_translate.py'
edit(ST, 1,
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14, SCHOLAR_V21_2026_10_14
''',
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14, SCHOLAR_V21_2026_10_14,
COST_TRUTH_2026_10_15
''')

edit(ST, 2,
     r'''  - the pages order the rows by their passage's place now (a re-ingest moves it), and a sentence whose passage is not
    its segments joined is shown whole after its verse range, the segments under the fold.
''',
     r'''  - the pages order the rows by their passage's place now (a re-ingest moves it), and a sentence whose passage is not
    its segments joined is shown whole after its verse range, the segments under the fold.

COST_TRUTH_2026_10_15: the meter now counts gemini-2.5-pro's thinking (billed as output; the SDK here does not name
it, and the 14 Oct runs were metered for their visible output only). The price counts only rows metered so (from
METERED_SINCE); before 10 of them, the prior of 3,000 output tokens a call. A job that only adds working English does
not stop a run.
''')

edit(ST, 3,
     r'''OUT_TOKENS_PRIOR = 1500      # a pro call's output with its thinking, before 10 verses are measured
''',
     r'''OUT_TOKENS_PRIOR = 3000      # a pro call's output with its thinking, before 10 verses are measured (COST_TRUTH_2026_10_15:
                             # was 1500; on 14 Oct a group's draft spent 8,192 thinking tokens and was cut off)
METERED_SINCE = "2026-10-15"   # COST_TRUTH_2026_10_15: rows made before it were metered without the thinking
''')

edit(ST, 4,
     r'''QUIET_KINDS = ("translate_hi", "ocr", "judge", "judge_all", "benchmark", "benchmark_all", "redeem_all", "path_all",
               "export", "pdf", "booksmith")
''',
     r'''QUIET_KINDS = ("translate_hi", "ocr", "judge", "judge_all", "benchmark", "benchmark_all", "redeem_all", "path_all",
               "export", "pdf", "booksmith",
               "translate", "translate_both", "translate_one")   # COST_TRUTH_2026_10_15: they add working English
''')

edit(ST, 5,
     r'''            q = ("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE engine = ? AND "
                 "cost_usd > 0 AND prompt_version LIKE ?")
            n, avg, mx = con.execute(q, (a.engine, PROMPT_VERSION + "+%")).fetchone()
            fam = PROMPT_VERSION.split(".")[0]   # SCHOLAR_V21_2026_10_14: scholar-v2.1 is priced by scholar-v2's rows
            nf, avgf, mxf = (con.execute(q, (a.engine, fam + "+%")).fetchone() if fam != PROMPT_VERSION
                             else (0, None, None))
''',
     r'''            q = ("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE engine = ? AND "
                 "cost_usd > 0 AND prompt_version LIKE ? AND created_at >= ?")   # COST_TRUTH_2026_10_15
            n, avg, mx = con.execute(q, (a.engine, PROMPT_VERSION + "+%", METERED_SINCE)).fetchone()
            fam = PROMPT_VERSION.split(".")[0]   # SCHOLAR_V21_2026_10_14: scholar-v2.1 is priced by scholar-v2's rows
            nf, avgf, mxf = (con.execute(q, (a.engine, fam + "+%", METERED_SINCE)).fetchone() if fam != PROMPT_VERSION
                             else (0, None, None))
''')

edit(ST, 6,
     r'''                n1, avg1, mx1 = con.execute(q, (a.engine, "scholar-v1+%")).fetchone()
''',
     r'''                n1, avg1, mx1 = con.execute(q, (a.engine, "scholar-v1+%", METERED_SINCE)).fetchone()
''')

DB = 'scripts/dashboard.py'
edit(DB, 1,
     r'''def _run_job(job: Job):
    try:
        proc = subprocess.Popen(
''',
     r'''def _run_job(job: Job):
    if job.killed:   # COST_TRUTH_2026_10_15: stopped while it waited for its lock: it never starts
        job.ok, job.out, job.err = False, "", "[KILLED by user] while queued: it never started"
        job.end = time.time()
        _persist_job(job)
        try:
            _status_forget()
        except NameError:
            pass
        return
    try:
        proc = subprocess.Popen(
''')

edit(DB, 2,
     r'''    job.killed = True
    killed = _kill_proc(job.proc)
    return jsonify({"killed": killed, "jid": jid, "doc": job.doc, "kind": job.kind})
''',
     r'''    job.killed = True
    killed = _kill_proc(job.proc)
    return jsonify({"killed": killed, "jid": jid, "doc": job.doc, "kind": job.kind,
                    "queued": not job.active})   # COST_TRUTH_2026_10_15: a queued job will not start
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


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
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, cfile=tmp + "c", doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            for t_ in (tmp, tmp + "c"):
                if os.path.exists(t_):
                    os.unlink(t_)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_costtruth_" + stamp))
        t = p.with_name(p.name + ".tmp_costtruth"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The meter counts the thinking from the next call of a new process; the")
    print("running dashboard and its jobs keep the old code until they end (restart only when idle).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
