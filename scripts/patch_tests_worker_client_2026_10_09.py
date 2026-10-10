#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_tests_worker_client_2026_10_09.py  (2026-10-09)  WORKER_TEST_CLIENT_2026_10_09

tests/test_corner_worker_state_2026_10_09.py (released with STATE_LEARN, ffdacb5f) checks the worker's
version as the literal text "corner_worker.py 1.1" in two places. Desk worker 1.2 (CORNER_C10_2026_10_09)
is a later version of the same worker, so those two checks now compare with the worker's own CLIENT
(cw.CLIENT) instead. Nothing else in the test changes.
md5-guarded (line endings ignored), backup .bak_wclient_<date>, line endings kept, re-running changes
nothing.

  python scripts/patch_tests_worker_client_2026_10_09.py --check
  python scripts/patch_tests_worker_client_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "WORKER_TEST_CLIENT_2026_10_09"
REL = Path("tests/test_corner_worker_state_2026_10_09.py")
WANT_LF_MD5 = "765901a73ed39af5440543f18fe5cdcd"
EDITS = [
    ('        self.assertEqual(info["client"], "corner_worker.py 1.1")\n',
     '        self.assertEqual(info["client"], cw.CLIENT)   # WORKER_TEST_CLIENT_2026_10_09\n'),
    ('info[0]["sync"]["media"]["files_on_drive"]), ("corner_worker.py 1.1", True, 9, 10))\n',
     'info[0]["sync"]["media"]["files_on_drive"]), (cw.CLIENT, True, 9, 10))   # WORKER_TEST_CLIENT_2026_10_09\n'),
]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not REL.exists():
        print("FAIL: %s not found. Run from the automaton repo root." % REL); return 2
    raw = REL.read_bytes()
    if MARK.encode() in raw:
        print("Nothing to do: %s already carries %s." % (REL, MARK)); return 0
    text = raw.replace(b"\r\n", b"\n")
    if hashlib.md5(text).hexdigest() != WANT_LF_MD5:
        print("REFUSE: %s is not the released version (md5 %s); nothing written." % (REL, hashlib.md5(text).hexdigest()))
        return 1
    s = text.decode("utf-8")
    for old, new in EDITS:
        if s.count(old) != 1:
            print("REFUSE: an anchor is found %d times in %s; nothing written." % (s.count(old), REL)); return 1
        s = s.replace(old, new)
    out = s.encode("utf-8")
    if raw.count(b"\r\n") > raw.count(b"\n") // 2:
        out = out.replace(b"\n", b"\r\n")
    if args.check:
        print("CHECK OK: %s: 2 version checks would compare with cw.CLIENT. Nothing written." % REL); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(REL, REL.with_name(REL.name + ".bak_wclient_" + stamp))
    t = REL.with_name(REL.name + ".tmp_wclient"); t.write_bytes(out); os.replace(t, REL)
    print("patched %s (2 version checks now compare with cw.CLIENT)" % REL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
