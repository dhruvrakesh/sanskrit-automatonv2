#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_legacy_tests_2026_10_22.py  (2026-10-22)  LEGACY_TESTS_2026_10_22

Found by your run of the whole suite on 22 Oct (14:04), module by module:
  - tests/test_morph_parse.py, tests/test_normalize.py, tests/test_sandhi_split.py were pytest functions:
    `python -m unittest` collects none of them ("NO TESTS RAN"), so they had never run here; test_normalize's called
    normalize_text.py --json, a command line the module no longer has. Now unittest tests: morph_parse.py and
    sandhi_split.py --json in safe mode (sys.executable, the repo as cwd, a timeout), and normalize_text.py's
    functions as ingest_jsonl_fast.py and the heal and witness scripts call them (the dandas kept, a lone | a danda,
    invisible characters out, a verse ending at its double danda).
  - tests/test_docs76_2026_10_18.py (FAILED, failures=1 on the PC; skipped on copies without its backups): its replay
    compared the patch's result with the docs as they are, which DOCS77 to DOCS85 have written again since. Now the
    result must be the file as it is or a later patch's backup of it (the exact bytes the patch wrote).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_legacytests_<date>; py_compile first.
  python scripts\\patch_legacy_tests_2026_10_22.py --check
  python scripts\\patch_legacy_tests_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'LEGACY_TESTS_2026_10_22'
TAG = 'legacytests'
FILES = ['tests/test_morph_parse.py', 'tests/test_normalize.py', 'tests/test_sandhi_split.py', 'tests/test_docs76_2026_10_18.py']
NEEDS = {'tests/test_docs76_2026_10_18.py': 'DOCS76_2026_10_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('tests/test_morph_parse.py', 1, 'import subprocess, json\ndef test_morph():\n    p = subprocess.run(["python","scripts/morph_parse.py","--json"], input="\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947".encode("utf-8"), stdout=subprocess.PIPE)\n    out = json.loads(p.stdout.decode("utf-8"))\n    assert "engine" in out\n',
     '# -*- coding: ascii -*-\n"""LEGACY_TESTS_2026_10_22: scripts/morph_parse.py --json reads Devanagari on stdin and names the engine that parsed\nit (in safe mode, the default, the heuristic one: no network, no model). It was a pytest function, which\n`python -m unittest` never ran ("NO TESTS RAN" on the PC, 22 Oct)."""\nimport json, os, subprocess, sys, unittest\nfrom pathlib import Path\n\nREPO = Path(__file__).resolve().parent.parent\nWORD = "\\u0915\\u0941\\u0930\\u0941\\u0915\\u094d\\u0937\\u0947\\u0924\\u094d\\u0930\\u0947"\n\n\nclass TheMorph(unittest.TestCase):\n    def test_json_names_the_engine(self):\n        p = subprocess.run([sys.executable, str(REPO / "scripts" / "morph_parse.py"), "--json"], input=WORD.encode("utf-8"),\n                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO), timeout=120,\n                           env=dict(os.environ, SA_SAFE_MODE="1", PYTHONIOENCODING="utf-8"))\n        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))\n        out = json.loads(p.stdout.decode("utf-8"))\n        self.assertIn("engine", out)\n        self.assertEqual(out.get("tokens"), [WORD])\n\n\nif __name__ == "__main__":\n    unittest.main()\n')

edit('tests/test_normalize.py', 1, 'import subprocess, json, sys, os, pathlib\n\ndef run(cmd, text):\n    p = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE)\n    return json.loads(p.stdout.decode("utf-8"))\n\ndef test_normalize_basic():\n    out = run(["python","scripts/normalize_text.py","--json"], "\u0930\u093e\u092e\u0903\u0964")\n    assert "normalized" in out\n    assert "transliterated" in out\n',
     '# -*- coding: ascii -*-\n"""LEGACY_TESTS_2026_10_22: scripts/normalize_text.py, which ingest_jsonl_fast.py and the heal and witness scripts call:\nthe dandas are kept (spaced, never made full stops), a lone | is a danda, invisible characters go, quotes and dashes\nare plain, a verse ends at its double danda. The pytest function before ran normalize_text.py --json, a command line\nthe module no longer has; `python -m unittest` never ran it."""\nimport sys, unittest\nfrom pathlib import Path\n\nREPO = Path(__file__).resolve().parent.parent\nsys.path.insert(0, str(REPO / "scripts"))\nimport normalize_text as nt  # noqa: E402\n\nD, DD = "\\u0964", "\\u0965"\nRAMAH, SITA = "\\u0930\\u093e\\u092e\\u0903", "\\u0938\\u0940\\u0924\\u093e"\n\n\nclass TheSanskrit(unittest.TestCase):\n    def test_the_dandas_are_kept(self):\n        self.assertEqual(nt.normalize_sanskrit(RAMAH + D), RAMAH + " " + D)\n        self.assertEqual(nt.normalize_sanskrit(RAMAH + " | " + SITA), RAMAH + " " + D + " " + SITA, "a lone | is a danda")\n        self.assertEqual(nt.count_dandas(RAMAH + " " + D + " " + SITA + " " + DD), (1, 1))\n\n    def test_invisible_and_typographic(self):\n        self.assertEqual(nt.normalize_sanskrit("a\\u200bb\\u00a0 c"), "ab c")\n        self.assertEqual(nt.normalize_english("a\\u2014b  \\u201cc\\u201d"), \'a-b "c"\')\n\n    def test_verses_end_at_the_double_danda(self):\n        self.assertEqual(nt.split_on_double_danda("\\u0915 " + DD + " \\u0916 " + DD + " \\u0917"),\n                         ["\\u0915 " + DD, "\\u0916 " + DD, "\\u0917"])\n        self.assertEqual(nt.frac_devanagari("\\u0915a"), 0.5)\n\n\nif __name__ == "__main__":\n    unittest.main()\n')

edit('tests/test_sandhi_split.py', 1, 'import subprocess, json\ndef test_sandhi():\n    p = subprocess.run(["python","scripts/sandhi_split.py","--json"], input="\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947".encode("utf-8"), stdout=subprocess.PIPE)\n    out = json.loads(p.stdout.decode("utf-8"))\n    assert "splits" in out\n',
     '# -*- coding: ascii -*-\n"""LEGACY_TESTS_2026_10_22: scripts/sandhi_split.py --json reads Devanagari on stdin and gives its splits (in safe\nmode, the default: deterministic, never a crash). It was a pytest function, which `python -m unittest` never ran."""\nimport json, os, subprocess, sys, unittest\nfrom pathlib import Path\n\nREPO = Path(__file__).resolve().parent.parent\nWORD = "\\u0927\\u0930\\u094d\\u092e\\u0915\\u094d\\u0937\\u0947\\u0924\\u094d\\u0930\\u0947"\n\n\nclass TheSplit(unittest.TestCase):\n    def test_json_gives_the_splits(self):\n        p = subprocess.run([sys.executable, str(REPO / "scripts" / "sandhi_split.py"), "--json"], input=WORD.encode("utf-8"),\n                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO), timeout=120,\n                           env=dict(os.environ, SA_SAFE_MODE="1", PYTHONIOENCODING="utf-8"))\n        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))\n        out = json.loads(p.stdout.decode("utf-8"))\n        self.assertIn("splits", out)\n        self.assertTrue(out["splits"] and all(isinstance(s, list) for s in out["splits"]))\n\n\nif __name__ == "__main__":\n    unittest.main()\n')

edit('tests/test_docs76_2026_10_18.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in FILES:',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in FILES:   # LEGACY_TESTS_2026_10_22: DOCS77 to DOCS85 wrote these files again since: the patch\'s\n                got = (t / f).read_bytes()   # result is the file as it is, or a later patch\'s backup of it\n                later = [x.read_bytes() for x in sorted((REPO / f).parent.glob(Path(f).name + ".bak_*"))\n                         if ".bak_docs76_" not in x.name]\n                self.assertTrue(got == (REPO / f).read_bytes() or got in later, f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in FILES:')


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
