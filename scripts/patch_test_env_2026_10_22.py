#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_test_env_2026_10_22.py  (2026-10-22)  TEST_ENV_2026_10_22

Found by your run of the whole suite on 22 Oct (16:50): nine modules failed on the PC and passed on the copies.
  - Eight (test_mbh_prose, test_bench_duel, test_bench_duel_notes, test_bench_gold, test_bench_gold_fair,
    test_bench_mitra, test_ocr_consensus, and test_docs76's patcher run) failed with UnicodeEncodeError 'charmap':
    Python on Windows writes to a pipe in the console's code page (cp1252), and the loop piped each module's output
    (2>&1 | Out-String). Reproduced on a copy with PYTHONIOENCODING=cp1252: the same eight, the same counts. The
    dashboard runs its jobs with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (dashboard.py); scripts\run_tests.ps1, which
    comes with this release, runs the tests so, for its own window only.
  - test_repo_hygiene_2026_10_15 compared its patcher's result with .gitignore as it is, which DOCS78 and DOCS84 have
    written again since (it skipped on copies without .bak_hygiene_). Now the result must be the file as it is or a
    later patch's backup of it.
This patcher edits tests/test_repo_hygiene_2026_10_15.py (needs REPO_HYGIENE_2026_10_15). Anchored, all or nothing,
marker-idempotent; keeps line endings; backup .bak_testenv_<date>; py_compile first.
  python scripts\\patch_test_env_2026_10_22.py --check
  python scripts\\patch_test_env_2026_10_22.py
  powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'TEST_ENV_2026_10_22'
TAG = 'testenv'
FILES = ['tests/test_repo_hygiene_2026_10_15.py']
NEEDS = {'tests/test_repo_hygiene_2026_10_15.py': 'REPO_HYGIENE_2026_10_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('tests/test_repo_hygiene_2026_10_15.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            self.assertEqual((t / ".gitignore").read_bytes(), GI.read_bytes())\n            self.assertEqual((t / "scripts" / "release.ps1").read_bytes(), PS.read_bytes())\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[".gitignore"][0], t / ".gitignore")',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel, cur in ((".gitignore", GI), ("scripts/release.ps1", PS)):   # TEST_ENV_2026_10_22: DOCS78 and\n                got = (t / rel).read_bytes()                              # DOCS84 wrote .gitignore again since\n                later = [x.read_bytes() for x in sorted(cur.parent.glob(cur.name + ".bak_*"))\n                         if ".bak_hygiene_" not in x.name]\n                self.assertTrue(got == cur.read_bytes() or got in later, rel)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[".gitignore"][0], t / ".gitignore")')


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
