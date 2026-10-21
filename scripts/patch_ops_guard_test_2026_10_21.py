#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ops_guard_test_2026_10_21.py  (2026-10-21)  OPS_GUARD_TEST_2026_10_21

Found on 21 Oct running the whole suite: tests/test_ops_guard.py's test_no_direct_generate_calls_left has failed since
SPEND_TRUTH_2026_10_04. It asserts that "resp = gm.generate_content(" is nowhere in scripts/infer_mt.py, to know that
every Gemini call goes through _gen(); SPEND_TRUTH made _gen() itself write "resp = gm.generate_content(...)" (to count
the tokens), so the test reads _gen's own two calls as calls that bypass it. The code is right; the test is not.

tests/test_ops_guard.py (needs MT_TIMEOUT): the test now asserts what it means: every "gm.generate_content(" in
infer_mt.py is inside _gen(). Nothing else changes.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_opsguardtest_<date>. No database change; nothing is called.
  python scripts\\patch_ops_guard_test_2026_10_21.py --check
  python scripts\\patch_ops_guard_test_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'OPS_GUARD_TEST_2026_10_21'
NEEDS = {'tests/test_ops_guard.py': 'MT_TIMEOUT'}
FILES = list(NEEDS)
TAG = 'opsguardtest'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('tests/test_ops_guard.py', 1, r'''    def test_no_direct_generate_calls_left(self):
        src = (REPO / "scripts" / "infer_mt.py").read_text(encoding="utf-8")
        self.assertNotIn("resp = gm.generate_content(", src)   # every call goes through _gen
''', r'''    def test_no_direct_generate_calls_left(self):
        src = (REPO / "scripts" / "infer_mt.py").read_text(encoding="utf-8")
        # OPS_GUARD_TEST_2026_10_21: every call goes through _gen, whose own calls (SPEND_TRUTH_2026_10_04 writes them
        # "resp = gm.generate_content(...)" to count the tokens) are the only ones
        parts = src.split("def _gen(gm, msg):", 1)
        self.assertEqual(len(parts), 2, "_gen() is not in infer_mt.py")
        gen = parts[1].split("\ndef ", 1)[0]
        self.assertGreater(gen.count("gm.generate_content("), 0)
        self.assertEqual(src.count("gm.generate_content("), gen.count("gm.generate_content("))
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


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
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
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
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
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
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("DONE: %s; backups .bak_%s_%s" % (MARK, TAG, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
