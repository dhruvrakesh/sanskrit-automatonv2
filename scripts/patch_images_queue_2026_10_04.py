#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_images_queue_2026_10_04.py  (2026-10-04)  IMAGES_QUEUE_2026_10_04

What was measured (data/jobs.jsonl, 2026-10-03/04): all 12 image jobs ended ok=True,
including ones that overlapped (Karan #25 ran 07:04:22-07:05:27 while #27 and #34
started and finished). Nothing was stopped. What the page did wrong:
  * it had ONE toast; each new request overwrote the message of the one before, so a
    running job looked as if it had been replaced;
  * jobs ran up to 3 at a time (they fell into the dashboard's general semaphore),
    so a "generate all" and a "generate #5" could draw the same idea twice;
  * the dashboard collects a job's output only when it ends, so there was nothing to
    show while "Propose ideas" (one model call, 30-40 s) was running.

This patch:
  scripts/images.py      --progress FILE (global, optional): writes a small JSON
                         {phase, step, total, current, started, updated} as it works.
                         Without the flag nothing changes.
  scripts/images_web.py  passes --progress per job; GET /api/images/jobs?doc= lists
                         every image job (queued with its place in line, running with
                         progress, finished in the last 15 minutes with its last lines);
                         registers ONE semaphore for images_brief + images_gen in the
                         dashboard's _KIND_SEM, so image jobs run one at a time, in order.
  scripts/images_static.html  replaced by images_static_2026_10_04.html: a job tray
                         (queued / running with a progress bar / done / failed, Cancel,
                         Dismiss) that survives a reload; card buttons show "In the queue".
                         The page works on the old dashboard too (it then tracks only the
                         jobs started on that page).

Takes effect: the HTML at once (it is read per request); images.py at the next job;
images_web.py (the endpoint and the queue) at the next dashboard restart, done only when
the header reads idle (RUNBOOK 1 / 9d).

  python scripts/patch_images_queue_2026_10_04.py --check
  python scripts/patch_images_queue_2026_10_04.py
Test: python -m unittest tests.test_images_queue_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "IMAGES_QUEUE_2026_10_04"
IMG = Path("scripts/images.py")
WEB = Path("scripts/images_web.py")
HTML = Path("scripts/images_static.html")
NEW_HTML = Path("scripts/images_static_2026_10_04.html")

IMG_HELPER = '''
def _progress(path, **kw):
    """IMAGES_QUEUE_2026_10_04: merge kw into a small JSON progress file (atomic). No-op without a path."""
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        d = {}
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                d = {}
        d.update(kw)
        d["updated"] = time.time()
        t = p.with_name(p.name + ".tmp")
        t.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(t, p)
    except Exception:
        pass


def main() -> int:
'''

IMG_EDITS = [
    ("helper", "\ndef main() -> int:\n", IMG_HELPER, 1),
    ("arg", '    ap.add_argument("--root", default="data/images")\n',
     '    ap.add_argument("--root", default="data/images")\n'
     '    ap.add_argument("--progress", default=None,\n'
     '                    help="IMAGES_QUEUE_2026_10_04: write job progress JSON here (used by the Images page)")\n', 1),
    ("brief start",
     "            t0 = time.time()\n            items, resp = call_text_json(args.model, BRIEF_SYSTEM, user)\n",
     "            t0 = time.time()\n"
     "            _progress(args.progress, phase=\"asking %s for up to %d ideas (one call, usually 30-60 s)\" % (args.model, n),\n"
     "                      step=0, total=1, started=t0)\n"
     "            items, resp = call_text_json(args.model, BRIEF_SYSTEM, user)\n", 1),
    ("brief end",
     '            print("stored %d brief(s): %s" % (len(ids), ids))\n',
     '            print("stored %d brief(s): %s" % (len(ids), ids))\n'
     '            _progress(args.progress, phase="stored %d idea(s)" % len(ids), step=1, total=1, done=True)\n', 1),
    ("generate loop",
     '            bad = 0\n            for t in todo:\n                try:\n'
     '                    generate_one(con, t, args.model, root, code, args.db)\n'
     '                except Exception as ex:\n'
     '                    bad += 1; print("  #%d: FAILED %s" % (t["id"], ex))\n'
     '            return 1 if bad else 0\n',
     '            bad = 0\n'
     '            _progress(args.progress, phase="drawing", step=0, total=len(todo), started=time.time())\n'
     '            for _i, t in enumerate(todo):\n'
     '                _progress(args.progress, phase="drawing", step=_i, total=len(todo),\n'
     '                          current="#%d %s" % (t["id"], (t["title"] or "")[:60]))\n'
     '                try:\n'
     '                    generate_one(con, t, args.model, root, code, args.db)\n'
     '                except Exception as ex:\n'
     '                    bad += 1; print("  #%d: FAILED %s" % (t["id"], ex))\n'
     '            _progress(args.progress, phase=("finished" if not bad else "%d failed" % bad), step=len(todo),\n'
     '                      total=len(todo), current="", done=True)\n'
     '            return 1 if bad else 0\n', 1),
]

WEB_JOB_OLD = '''    def _job(kind, doc, argv, mode="all"):
        # mode is part of the dashboard's duplicate-job identity: generating image 3
        # must not be swallowed by a running generation of image 5.
        try:
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv), mode=mode)
        except TypeError:   # a dashboard without EXPORT_MODE_JOBLOG (no mode argument)
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv))
        return jsonify({"job": jid})
'''
WEB_JOB_NEW = '''    # IMAGES_QUEUE_2026_10_04 ------------------------------------------------------
    # The dashboard's own job table, read through launch's module globals (dashboard.py
    # runs as __main__). Missing on an unusual host: the page then tracks its own jobs.
    _g = getattr(launch, "__globals__", {}) or {}
    _JOBS, _JOBS_LOCK = _g.get("JOBS"), _g.get("JOBS_LOCK")
    _KINDS = ("images_brief", "images_gen")
    _ks = _g.get("_KIND_SEM")
    if isinstance(_ks, dict) and not any(k in _ks for k in _KINDS):
        import threading as _threading
        _img_sem = _threading.Semaphore(1)     # one image job at a time, in the order asked
        for _k in _KINDS:
            _ks[_k] = _img_sem
    prog_dir = root / "data" / "images" / "_progress"

    def _pfile(kind, doc, mode):
        return prog_dir / ("%s__%s__%s.json" % (kind, doc, mode or "all"))

    def _snapshot():
        if _JOBS is None or _JOBS_LOCK is None:
            return None
        with _JOBS_LOCK:
            return [j for j in _JOBS.values() if j.kind in _KINDS]

    def _job(kind, doc, argv, mode="all"):
        # mode is part of the dashboard's duplicate-job identity: generating image 3
        # must not be swallowed by a running generation of image 5.
        pf = _pfile(kind, doc, mode)
        snap = _snapshot() or []
        if not any(j.ok is None and j.doc == doc and j.kind == kind and (j.mode or "") == mode for j in snap):
            try:
                pf.unlink()          # a fresh request starts with a fresh progress file
            except OSError:
                pass
        argv = ["--progress", str(pf)] + list(argv)
        try:
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv), mode=mode)
        except TypeError:   # a dashboard without EXPORT_MODE_JOBLOG (no mode argument)
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv))
        return jsonify({"job": jid})

    @app.get("/api/images/jobs")
    def images_jobs():
        doc = request.args.get("doc", "")
        snap = _snapshot()
        if snap is None:
            return jsonify({"jobs": [], "available": False})
        now = time.time()
        waiting = sorted((j for j in snap if j.ok is None and not getattr(j, "active", False)),
                         key=lambda j: j.start)
        out = []
        for j in snap:
            if doc and j.doc != doc:
                continue
            if j.ok is not None and (not j.end or now - j.end > 900):
                continue
            if j.ok is None:
                state = "running" if getattr(j, "active", False) else "queued"
            else:
                state = "done" if j.ok else ("killed" if getattr(j, "killed", False) else "failed")
            prog = None
            try:
                pf = _pfile(j.kind, j.doc, j.mode)
                if pf.exists():
                    prog = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                prog = None
            tail = ""
            if state not in ("queued", "running"):
                tail = "\\n".join((j.out or "").strip().splitlines()[-4:])
                if state != "done" and j.err:
                    tail += "\\n" + "\\n".join(j.err.strip().splitlines()[-3:])
            out.append({"id": j.id, "kind": j.kind, "doc": j.doc, "mode": j.mode or "", "state": state,
                        "start": j.start, "end": j.end, "progress": prog, "tail": tail.strip(),
                        "position": (waiting.index(j) + 1) if state == "queued" else None})
        out.sort(key=lambda x: -(x["start"] or 0))
        return jsonify({"jobs": out, "available": True, "queued_total": len(waiting)})
'''

WEB_EDITS = [("job + endpoint", WEB_JOB_OLD, WEB_JOB_NEW, 1)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def apply(src, edits):
    probs = []
    for label, old, new, n in edits:
        c = src.count(old)
        if c != n:
            probs.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    return src, probs


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (IMG, WEB, HTML, NEW_HTML):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    i_src, i_nl = load(IMG); w_src, w_nl = load(WEB); h_src = HTML.read_text(encoding="utf-8")
    marks = (MARK in i_src, MARK in w_src, MARK in h_src)
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand."); return 1
    i_new, p1 = apply(i_src, IMG_EDITS)
    w_new, p2 = apply(w_src, WEB_EDITS)
    if "IMAGES_UI_2026_10_03" not in h_src:
        p2.append("images_static.html is not the IMAGES_UI_2026_10_03 page - inspect by hand")
    if MARK not in NEW_HTML.read_text(encoding="utf-8"):
        p2.append("%s does not carry %s" % (NEW_HTML, MARK))
    if p1 or p2:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in p1 + p2]; return 1
    if args.check:
        print("CHECK OK: %d + %d anchored edits and the new page. Nothing written." % (len(IMG_EDITS), len(WEB_EDITS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in ((IMG, i_new, i_nl), (WEB, w_new, w_nl)):
        t = p.with_name(p.name + ".tmp_iq")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for p in (IMG, WEB, HTML):
        shutil.copy2(p, p.with_name(p.name + ".bak_iq_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
    th = HTML.with_name(HTML.name + ".tmp_iq")
    shutil.copyfile(NEW_HTML, th)
    os.replace(th, HTML)
    print("PATCHED images.py, images_web.py; installed the new images_static.html (backups *.bak_iq_%s)." % stamp)
    print("The page changes now; the queue and /api/images/jobs need one dashboard restart while idle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
