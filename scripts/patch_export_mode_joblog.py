#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_export_mode_joblog.py  (2026-09-30)  EXPORT_MODE_JOBLOG_2026_09_30

Follow-up to EXPORT_MODE_VISIBLE_2026_09_30 (UI). Two server-side gaps found
while diagnosing the 2026-09-30 "trilingual export is broken" report:

1. data/jobs.jsonl did not record WHICH edition an export produced. The record
   for the 20:16 Shatpath job says kind=export, rc 0, and nothing else; the
   edition could only be inferred from the output file name (_hi).
2. The duplicate guard in launch() keys on (kind, doc). A trilingual export
   started while a Hindi export of the same doc was still running was silently
   answered with the Hindi job's id. Rare (exports take 0.2-0.8 s) but real.

WHAT THIS CHANGES (scripts/dashboard.py, additive)
  * Job gains `mode: str = ""`.
  * launch(..., mode="") stores it; the duplicate guard also compares mode.
    Every existing caller passes no mode, so for them the guard is unchanged.
  * /api/export passes mode=mode.
  * _persist_job writes "mode" ONLY when set, so every other record in
    jobs.jsonl keeps its exact shape.
  * /api/job/<id> returns "mode".
Unchanged: export_html.py, the request contract, file names, semaphores.

REQUIRES A DASHBOARD RESTART. RUNBOOK rule: never restart while jobs are
queued - the queue lives in memory. Apply, then restart only when the header
reads "idle".

Run from the repo root:
  python scripts/patch_export_mode_joblog.py --check
  python scripts/patch_export_mode_joblog.py
Test:  python -m unittest tests.test_export_mode_joblog -v  (fails before, passes after)
"""
from __future__ import annotations
import argparse
import datetime
import os
import py_compile
import shutil
import sys
from pathlib import Path

MARK = "EXPORT_MODE_JOBLOG_2026_09_30"
DASH = Path("scripts/dashboard.py")

EDITS = [
    ("Job.mode field",
     "                           # ACTUALLY executing (vs. still queued behind the lock).\n",
     "                           # ACTUALLY executing (vs. still queued behind the lock).\n"
     "    mode: str = \"\"         # EXPORT_MODE_JOBLOG_2026_09_30: edition (en/hi/tri) for exports; \"\" otherwise.\n"),
    ("persist mode",
     "            \"out_tail\": (job.out or \"\")[-400:],\n        }\n",
     "            \"out_tail\": (job.out or \"\")[-400:],\n        }\n"
     "        if job.mode:  # EXPORT_MODE_JOBLOG_2026_09_30 - only when set; other records keep their shape\n"
     "            record[\"mode\"] = job.mode\n"),
    ("launch signature",
     "def launch(kind: str, doc: str, argv: List[str], then=None) -> str:\n",
     "def launch(kind: str, doc: str, argv: List[str], then=None, mode: str = \"\") -> str:\n"),
    ("duplicate guard",
     "            if j.ok is None and j.kind == kind and j.doc == doc:\n",
     "            # EXPORT_MODE_JOBLOG_2026_09_30: mode is part of the identity, so a\n"
     "            # trilingual export is not swallowed by a running Hindi one.\n"
     "            if j.ok is None and j.kind == kind and j.doc == doc and j.mode == mode:\n"),
    ("Job construction",
     "    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv)\n",
     "    job = Job(id=str(uuid.uuid4()), kind=kind, doc=doc, cmd=argv, mode=mode)\n"),
    ("api_export launch",
     "    return jsonify({\"job\": launch(\"export\", doc, cmd), \"mode\": mode})\n",
     "    return jsonify({\"job\": launch(\"export\", doc, cmd, mode=mode), \"mode\": mode})\n"),
    ("api_job mode",
     "        \"running\": job.ok is None, \"killed\": job.killed,\n",
     "        \"running\": job.ok is None, \"killed\": job.killed, \"mode\": job.mode or None,\n"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not DASH.exists():
        print("FAIL: %s not found. Run from the repo root." % DASH)
        return 2
    raw = DASH.read_bytes()
    crlf = raw.count(b"\r\n")
    newline = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    problems = []
    for label, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            problems.append("%s: matched %d times, expected exactly 1" % (label, n))
        else:
            src = src.replace(old, new)
    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1
    if args.check:
        print("CHECK OK: all %d anchors match exactly once. Nothing written." % len(EDITS))
        return 0
    tmp = DASH.with_name(DASH.name + ".tmp_expjob")
    tmp.write_bytes(src.replace("\n", newline).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink()
        print("REFUSING TO WRITE: patched file does not compile:\n%s" % e)
        return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    bak = DASH.with_name(DASH.name + ".bak_expjob_" + stamp)
    shutil.copy2(DASH, bak)
    os.replace(tmp, DASH)
    print("PATCHED %s (backup %s)." % (DASH, bak))
    print("Restart the dashboard ONLY when the header reads 'idle' (RUNBOOK section 1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
