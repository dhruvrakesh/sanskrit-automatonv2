#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_job_diagnostics.py - make a failed job say why it failed. (2026-09-06)

THE EVIDENCE
------------
data/jobs.jsonl, 2026-09-06 10:18 UTC:

  {"kind": "entities", "doc": "2015_405693_Shatpath-Brahmanam",
   "duration_s": 32.9, "ok": false, "out_lines": 0, "err_preview": ""}

Thirty-three seconds of work, a non-zero exit, and NOT ONE CHARACTER of
explanation. extract_entities.py prints on every batch and calls
sys.exit("...") with a message on both of its early exits, so it is not a
silent program. The output was produced and then thrown away.

WHY
---
dashboard.py line 435:

    def py(*args): return [sys.executable, *args]

No `-u`. CPython block-buffers stdout at 8 KB whenever it is a pipe rather
than a console, and _run_job pipes both streams. Anything the child printed is
sitting in that buffer, and it is flushed only on a clean exit. Die any other
way - killed, crashed, interpreter aborted - and the whole buffer evaporates.

The same buffering is half of the restart problem in RUNBOOK 9d: a child whose
reader has gone away fills the ~64 KB pipe and blocks forever on write.
Unbuffered output does not prevent that, but it does mean everything up to the
block was already delivered instead of lost.

WHAT THIS CHANGES  (two edits, both additive)
  1. py() launches children with -u. One flag. Every line a job prints is
     delivered when it is printed, so a job that dies mid-run still leaves
     its trail.
  2. _persist_job() records the return CODE and a tail of stdout, not just a
     stderr preview. "ok: false" with no rc tells you nothing; rc=1 versus
     rc=2 (argparse) versus rc=-9 (killed) tells you where to look.

Not changed here: _run_job still has no creationflags and no Job Object, so a
dashboard restart still orphans its children. That is a real fix with real
risk and it does not belong in the same patch as a logging change - see
RUNBOOK 9d for the procedure that avoids it in the meantime.

  python scripts\\patch_job_diagnostics.py            # dry run
  python scripts\\patch_job_diagnostics.py --apply

SAFE TO APPLY WHILE THE DASHBOARD IS RUNNING: Python already holds its own
copy of dashboard.py in memory. The change takes effect at the NEXT restart,
whenever that happens to be - it does not disturb a running job.
"""
from __future__ import annotations
import argparse, io, os, py_compile, shutil, sys, time

MARKER = "JOB_DIAG_2026_09_06"
PY = os.path.join("scripts", "dashboard.py")

EDITS = [
    ('''def py(*args: str) -> List[str]:
    return [sys.executable, *args]''',
     '''def py(*args: str) -> List[str]:
    # -u is load-bearing. (JOB_DIAG_2026_09_06)
    # _run_job pipes stdout and stderr, and CPython block-buffers stdout at 8 KB
    # when it is a pipe. A job that does not exit cleanly therefore loses
    # EVERYTHING it printed - which is how the entities job on 2026-09-06 came to
    # be recorded as ok:false, out_lines:0, err_preview:"" after 32.9 seconds of
    # work. Unbuffered, each line is delivered as it is printed.
    return [sys.executable, "-u", *args]'''),

    # 2. a field to hold the return code. _run_job clears job.proc in its
    #    `finally` BEFORE calling _persist_job, so the code has to be copied off
    #    the Popen while it is still there.
    ('''    proc: Optional[object] = field(default=None, repr=False)  # subprocess.Popen, not serialized
    killed: bool = False''',
     '''    proc: Optional[object] = field(default=None, repr=False)  # subprocess.Popen, not serialized
    rc: Optional[int] = None   # child exit code, copied off proc before it is
                               # cleared. (JOB_DIAG_2026_09_06)
    killed: bool = False'''),

    # 3. capture it in every branch, including the killed one.
    ('''        if job.killed:
            job.ok  = False
            job.err = "[KILLED by user]"
        else:
            job.ok  = proc.returncode == 0''',
     '''        job.rc = proc.returncode          # (JOB_DIAG_2026_09_06)
        if job.killed:
            job.ok  = False
            job.err = "[KILLED by user]"
        else:
            job.ok  = proc.returncode == 0'''),

    # 4. and write it down.
    ('''            "out_lines": len((job.out or "").splitlines()),
            "err_preview": (job.err or "")[:300],''',
     '''            "out_lines": len((job.out or "").splitlines()),
            "err_preview": (job.err or "")[:300],
            # (JOB_DIAG_2026_09_06) "ok: false" on its own is not a diagnosis.
            # rc separates a crash (1) from bad arguments (2) from a kill, and
            # out_tail is usually the last thing the job managed to say.
            "rc": job.rc,
            "out_tail": (job.out or "")[-400:],''')
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(PY):
        sys.exit(f"not found: {PY} - run from the repo root")
    s = io.open(PY, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return

    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAll anchors OK. Re-run with --apply."); return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"dashboard.py.preJobDiag.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(PY, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        io.open(PY, "w", encoding="utf-8", newline="\n").write(s)
        py_compile.compile(PY, doraise=True)
    except Exception as exc:
        shutil.copy2(b, PY)
        sys.exit(f"FAILED ({exc}) - restored from backup.")
    print("\nApplied and compiles. Takes effect at the NEXT dashboard restart.")
    print("Do NOT restart to pick it up while a translate job is running -")
    print("see RUNBOOK 9d. It will be there whenever you do restart.")


if __name__ == "__main__":
    main()
