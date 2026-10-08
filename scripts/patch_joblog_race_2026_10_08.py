#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_joblog_race_2026_10_08.py  JOBLOG_RACE_2026_10_08

tests/test_export_mode_joblog.py::test_mode_persisted_only_when_set failed on Windows on
2026-10-08 with KeyError: the ocr job's end record was not in the job log yet. The test waits for
job.ok, but scripts/dashboard.py sets job.ok inside _run_job's try block and appends the record
in its finally block (job.end, then _persist_job), so a fixed 0.3 s sleep loses the race on a busy
machine (14 translation jobs were queued). The dashboard is right; the test is fixed to poll the
log for both records (up to 10 s). Test-only change: nothing the dashboard runs is touched.

Anchored, all-or-nothing, marker-idempotent; backup first; py_compile; atomic replace; line
endings kept.

  python scripts/patch_joblog_race_2026_10_08.py --check
  python scripts/patch_joblog_race_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "JOBLOG_RACE_2026_10_08"
TARGET = Path("tests/test_export_mode_joblog.py")

OLD = """        wait_done(self.d, e); wait_done(self.d, o)
        time.sleep(0.3)
        recs = [json.loads(l) for l in self.d.JOBS_LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        by_id = {r["id"]: r for r in recs}
"""

NEW = """        wait_done(self.d, e); wait_done(self.d, o)
        # JOBLOG_RACE_2026_10_08: job.ok is set before the end record is appended (finally: in
        # _run_job), so poll the log for both records; a fixed 0.3 s sleep lost the race on a
        # busy Windows machine (KeyError, 2026-10-08).
        by_id = {}
        t0 = time.time()
        while time.time() - t0 < 10:
            if self.d.JOBS_LOG_PATH.exists():
                recs = [json.loads(l) for l in self.d.JOBS_LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
                by_id = {r["id"]: r for r in recs}
                if e in by_id and o in by_id:
                    break
            time.sleep(0.05)
"""


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes()
    if MARK.encode() in raw:
        print("skip %s (already carries %s)" % (TARGET, MARK)); return 0
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if text.count(OLD) != 1:
        print("FAIL: anchor found %d times (expected 1); nothing written." % text.count(OLD)); return 2
    out = text.replace(OLD, NEW)
    data = (out.replace("\n", "\r\n") if crlf else out).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        probe = Path(td) / TARGET.name
        probe.write_bytes(data)
        try:
            py_compile.compile(str(probe), doraise=True)
        except py_compile.PyCompileError as e:
            print("FAIL: patched file does not compile: %s" % e); return 2
    if a.check:
        print("CHECK OK: 1 anchor in %s; it would be patched. Nothing written." % TARGET); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak_joblog_" + stamp))
    tmp = TARGET.with_name(TARGET.name + ".tmp_joblog"); tmp.write_bytes(data); os.replace(tmp, TARGET)
    print("patched %s" % TARGET)
    return 0


if __name__ == "__main__":
    sys.exit(main())
