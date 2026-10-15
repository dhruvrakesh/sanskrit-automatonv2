#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_run_fix_2026_10_15.py  (2026-10-15)  RUN_FIX_2026_10_15

After the canary of 15 Oct, 16:27 IST (the Hayasirsa 17.1-19.11 and 20.5-21.4 on claude-sonnet-5-5: 25 passed, 5
flagged, 1 source doubt; the Karanagama stopped). Follows AUDIT_2026_10_15 (eb7dc3d).

scripts/scholar_translate.py:
  - a critic whose answer cannot be read: 3 of 29 critiques came back not as JSON, and 20.6 and 20.8 were flagged for
    that alone. Now:
      parse_json reads the first whole JSON object of an answer, whatever follows it, before the old greedy match;
      a Claude critic (as a draft already) is asked once more when its answer is not JSON;
      an answer still not JSON is kept in unparsed_<doc>.jsonl beside the run's log (data/scholar: its kind, how it
      ended, its length, its first and last 300 characters), and the row's doubts say so (the verse is flagged, as
      before, unless the audit reads it);
  - a dashboard pipeline job (pipeline_queue.py: OCR, ingest, translate, export) that has begun its translate stage
    changes no Sanskrit any more, only the working English and then the HTML: it no longer stops a run (the
    Karanagama's canary stopped on one at 16:27). Its output says so: the stage header "Translate <doc>" or "Export
    <doc>" (/api/job/<id>, read-only). A queued pipeline, one still at its OCR or ingest, or a dashboard that does not
    say, stops the run as before.

Needs AUDIT_2026_10_15. Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic
replace; backup .bak_runfix_<date>.
  python scripts\\patch_run_fix_2026_10_15.py --check
  python scripts\\patch_run_fix_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "RUN_FIX_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "AUDIT_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15,
AUDIT_2026_10_15
''', r'''CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15,
AUDIT_2026_10_15, RUN_FIX_2026_10_15
''')

edit(ST, 2, r'''sentence in N; its reading decides the status (a person reads what it flags). --status: what a text has, per engine
(free, read-only).
''', r'''sentence in N; its reading decides the status (a person reads what it flags). --status: what a text has, per engine
(free, read-only).

RUN_FIX_2026_10_15: an answer's first whole JSON object is read whatever follows it; a Claude critic not answering in
JSON is asked once more, and an answer still unread is kept (data/scholar/unparsed_<doc>.jsonl); a dashboard pipeline
past its ingest (translating or exporting) does not stop a run.
''')

edit(ST, 3, r'''    try:
        d = json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except ValueError:
            return None
    return d if isinstance(d, dict) else None
''', r'''    try:
        d = json.loads(s)
    except ValueError:
        d = first_object(s)   # RUN_FIX_2026_10_15: the first whole object, whatever follows it
        if d is None:
            m = re.search(r"\{.*\}", s, re.S)
            if not m:
                return None
            try:
                d = json.loads(m.group(0))
            except ValueError:
                return None
    return d if isinstance(d, dict) else None


def first_object(s: str, tries: int = 20):
    """RUN_FIX_2026_10_15: the first JSON object that decodes whole from a "{" of s (at most tries of them); None."""
    dec = json.JSONDecoder()
    i = s.find("{")
    while i >= 0 and tries > 0:
        try:
            d, _end = dec.raw_decode(s[i:])
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
        i = s.find("{", i + 1)
        tries -= 1
    return None
''')

edit(ST, 4, r'''        if d is None and kind == "draft" and stop != "refusal":
            txt, stop, more = self._once(kind, msg, 2 * CLAUDE_MAX_TOKENS)
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": stop, "chars": len(txt or ""), "json": d is not None}
        return d, cost
''', r'''        if d is None and kind in ("draft", "critic") and stop != "refusal":   # RUN_FIX_2026_10_15: a critic too
            txt, stop, more = self._once(kind, msg, 2 * CLAUDE_MAX_TOKENS)
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": stop, "chars": len(txt or ""), "json": d is not None}
        self.kept = keep_unparsed(self.a, self.meta, kind, stop, txt, self.client.model) if d is None else None
        return d, cost
''')

edit(ST, 5, r'''class CreditGate:
''', r'''def keep_unparsed(a, meta: dict, kind: str, stop, txt, engine):
    """RUN_FIX_2026_10_15: an answer that is not JSON, kept so that it can be read (unparsed_<doc>.jsonl in --log-dir,
    data/scholar by default): its kind, how it ended, its length, its first and last 300 characters. The file, or None
    (no log folder, or it could not be written). Never raises."""
    d = getattr(a, "log_dir", None)
    if not d:
        return None
    try:
        p = Path(d) / ("unparsed_%s.jsonl" % _safe(meta.get("doc") or "x"))
        p.parent.mkdir(parents=True, exist_ok=True)
        t = str(txt or "")
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "doc": meta.get("doc"), "kind": kind, "engine": engine, "stop": str(stop),
                                "chars": len(t), "head": t[:300], "tail": t[-300:], "mark": "RUN_FIX_2026_10_15"},
                               ensure_ascii=False) + "\n")
        return p
    except Exception:
        return None


class CreditGate:
''')

edit(ST, 6, r'''    return [j for j in jobs if j.get("doc") == doc and j.get("kind") not in QUIET_KINDS]
''', r'''    return [j for j in jobs if j.get("doc") == doc and j.get("kind") not in QUIET_KINDS
            and not (j.get("kind") == "pipeline" and pipeline_past_ingest(j, doc))]   # RUN_FIX_2026_10_15


def job_out(jid) -> str:
    """RUN_FIX_2026_10_15: a dashboard job's output, as /api/job/<id> gives it (read-only); "" when it does not answer."""
    try:
        import urllib.request
        import repair_text as rt
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(rt.DASHBOARD + "/api/job/%s" % jid, timeout=6) as f:
            return str(json.loads(f.read().decode("utf-8")).get("out") or "")
    except Exception:
        return ""


def pipeline_past_ingest(j: dict, doc: str) -> bool:
    """RUN_FIX_2026_10_15: a running pipeline job (pipeline_queue.py) whose output has reached its translate or export
    stage, after its OCR and ingest: it changes no Sanskrit any more. False when it is queued, earlier, or unknown."""
    if j.get("state") != "running" or not j.get("id"):
        return False
    out = job_out(j["id"])
    return ("  Translate %s" % doc) in out or ("  Export %s" % doc) in out
''')

edit(ST, 7, r'''        if accepted(cr) or revisions >= a.rounds or cr is None:
            break
''', r'''        if cr is None:   # RUN_FIX_2026_10_15: say so; the status is flagged, unless the audit reads it
            kept = getattr(asker, "kept", None)
            note = "; ".join(s_ for s_ in (note, "the critic's answer could not be read" + (
                " (it is kept in %s beside the run's log)" % kept.name if kept else "")) if s_)
        if accepted(cr) or revisions >= a.rounds or cr is None:
            break
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


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
    if not Path("scripts/scholar_translate.py").exists():
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
        if not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_runfix_" + stamp))
        t = p.with_name(p.name + ".tmp_runfix"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_run_fix_2026_10_15 tests.test_audit_2026_10_15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
