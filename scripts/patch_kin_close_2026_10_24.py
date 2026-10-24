#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
KIN_CLOSE_2026_10_24: scripts/kin_index.py closes its store (data/shelf/kin.db) when a run ends.

The fault: on the PC, tests.test_kin_index_2026_10_23 ended "FAILED (errors=2)". Its two tests that read (--yes) left
kin.db open after main() returned, and Windows will not delete an open file, so the temp folder's cleanup raised. Linux
deletes open files, which is why the cloud and the VM passed. Measured here: after main() returned, two handles to
kin.db were still open in each of those two tests.

The fix: open_store() remembers each store it opens; main() runs the work (now run()) and closes every store in a
finally, whatever it returned or raised. Nothing else changes: the same arguments, the same output, the same files.

Run from the repo root:  python scripts\\patch_kin_close_2026_10_24.py --check   then without --check.
Backup: scripts\\kin_index.py.bak_kin_close_ and the date. Test: tests\\test_kin_close_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'KIN_CLOSE_2026_10_24'
TAG = 'kin_close'
FILES = ['scripts/kin_index.py']
NEEDS = {'scripts/kin_index.py': 'RELATIONS_INDEX_2026_10_23'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/kin_index.py', 1, '\n\ndef open_store(path: str):\n    Path(path).parent.mkdir(parents=True, exist_ok=True)\n    con = sqlite3.connect(path, timeout=60)\n    con.executescript(SCHEMA)\n    return con\n',
     '\n\n_STORES = []   # KIN_CLOSE_2026_10_24: every store this run opened; main() closes them all when the run ends\n\n\ndef open_store(path: str):\n    Path(path).parent.mkdir(parents=True, exist_ok=True)\n    con = sqlite3.connect(path, timeout=60)\n    con.executescript(SCHEMA)\n    _STORES.append(con)\n    return con\n')

edit('scripts/kin_index.py', 2, '\ndef main(argv=None, caller=None) -> int:\n    ap = argparse.ArgumentParser(description="the indexes\' kinships read and checked (%s)" % MARK)\n    ap.add_argument("--db", default="")',
     '\ndef main(argv=None, caller=None) -> int:\n    """KIN_CLOSE_2026_10_24: the run is run(); the stores it opened are closed here, whatever it returned or raised.\n    Windows will not delete, replace or back up a file that is still open, and the tests call main() in-process."""\n    try:\n        return run(argv, caller)\n    finally:\n        while _STORES:\n            try:\n                _STORES.pop().close()\n            except sqlite3.Error:\n                pass\n\n\ndef run(argv=None, caller=None) -> int:\n    ap = argparse.ArgumentParser(description="the indexes\' kinships read and checked (%s)" % MARK)\n    ap.add_argument("--db", default="")')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
