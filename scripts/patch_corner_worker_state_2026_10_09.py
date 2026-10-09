#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_corner_worker_state_2026_10_09.py  CORNER_STATE_C10A_2026_10_09

Why: the site's Researchers' Corner is to show a live progress bar for each request the desk is
running ("Drawing page 3 of 12"), and editors are to see whether the mirror and the picture uploads
are in step. The database side is docs/cloud/C10a_corner_state_2026-10-09.sql; this is the desk's.

What changes in scripts/corner_worker.py (client 1.0 -> 1.1):
  1. While a request runs, the desk reports where it is: a 'running' report with
     {"progress": {"step": i, "of": n, "note": "..."}}, at most one every 5 seconds except the first
     and the last step. A progress report that fails is logged and never fails the request; after
     one fails, no more are sent for that request (the site may be unreachable).
  2. novel_draw counts the pages it will draw from context.db first (novel.py draw_pages' own rule:
     the pages asked for with no picture, or a stale one) and reads novel.py's output as it comes,
     still ONE call of novel.py draw --id K [--pages ...] --yes. With nothing to draw it says so and
     does not run novel.py.
  3. The heartbeat (corner.worker.info) gains "sync": the last run of the mirror and of the pictures,
     from the last line of data/corpus_sync_log.jsonl and data/corpus_media_log.jsonl.
Nothing else changes: the same request kinds, refusals, argument lists, ledger, lock, logs and exit
codes.

Apply docs/cloud/C10a_corner_state_2026-10-09.sql in the database FIRST: C9's corner_desk_report would
keep each progress report as the request's result.

Whole-file replace from docs/desk/CORNER_STATE_C10A_2026-10-09/corner_worker.py (md5 e80a5525...),
md5-guarded (the file must be the one released on 2026-10-09, md5 2abb74b4...; if it is already the
payload there is nothing to do). Backup .bak_state_<date>; LF only; py_compile before the atomic replace.

  python scripts/patch_corner_worker_state_2026_10_09.py --check
  python scripts/patch_corner_worker_state_2026_10_09.py
Then: python -m unittest tests.test_corner_worker_2026_10_09 tests.test_corner_worker_state_2026_10_09
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "CORNER_STATE_C10A_2026_10_09"
TARGET = Path("scripts/corner_worker.py")
PAYLOAD = Path("docs/desk/CORNER_STATE_C10A_2026-10-09/corner_worker.py")
WANT_MD5 = "2abb74b42611209b07de6797a60828b6"      # corner_worker.py 1.0, released 2026-10-09
PAYLOAD_MD5 = "e80a552537625743b853e6d7a5eb3d39"   # corner_worker.py 1.1


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes()
    have = hashlib.md5(raw).hexdigest()
    if have == PAYLOAD_MD5:
        print("Nothing to do: %s is already corner_worker.py 1.1 (%s)." % (TARGET, MARK)); return 0
    if have != WANT_MD5:
        print("REFUSE: %s has md5 %s, not the released %s (changed since). Nothing written." % (TARGET, have, WANT_MD5))
        return 1
    if b"\r\n" in raw:
        print("REFUSE: %s has CRLF line endings; expected LF. Nothing written." % TARGET); return 1
    if not PAYLOAD.exists():
        print("FAIL: the payload %s is missing. Nothing written." % PAYLOAD); return 2
    data = PAYLOAD.read_bytes()
    got = hashlib.md5(data).hexdigest()
    if got != PAYLOAD_MD5:
        print("REFUSE: the payload %s has md5 %s, not %s. Nothing written." % (PAYLOAD, got, PAYLOAD_MD5)); return 1
    if b"\r\n" in data:
        print("REFUSE: the payload has CRLF line endings; expected LF. Nothing written."); return 1
    try:
        data.decode("ascii")
    except UnicodeDecodeError:
        print("REFUSE: the payload is not ASCII. Nothing written."); return 1
    if MARK.encode() not in data:
        print("REFUSE: the payload does not carry %s. Nothing written." % MARK); return 1
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "corner_worker_probe.py"
        probe.write_bytes(data)
        try:
            py_compile.compile(str(probe), doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: the payload does not compile: %s. Nothing written." % e); return 1
    if a.check:
        print("CHECK OK: %s (1.0, md5 %s) would be replaced by the payload (1.1, md5 %s). Nothing written."
              % (TARGET, have, PAYLOAD_MD5)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    bak = TARGET.with_name(TARGET.name + ".bak_state_" + stamp)
    shutil.copy2(TARGET, bak)
    tmp = TARGET.with_name(TARGET.name + ".tmp_state")
    tmp.write_bytes(data)
    os.replace(tmp, TARGET)
    print("replaced %s (corner_worker.py 1.0 -> 1.1, md5 %s). Backup: %s" % (TARGET, PAYLOAD_MD5, bak.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
