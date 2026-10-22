# -*- coding: ascii -*-
"""LEGACY_TESTS_2026_10_22: the three pytest-style test files are unittest modules now (each collects tests), and
test_docs76's replay accepts a later patch's backup; the patcher applies once, from the copies it found. Reads the
files only."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_legacy_tests_2026_10_22.py"
MARK = "LEGACY_TESTS_2026_10_22"
FILES = ("tests/test_morph_parse.py", "tests/test_normalize.py", "tests/test_sandhi_split.py",
         "tests/test_docs76_2026_10_18.py")
APPLIED = all(MARK.encode() in (REPO / f).read_bytes() for f in FILES)


@unittest.skipUnless(APPLIED, "LEGACY_TESTS_2026_10_22 is not applied here")
class TheModules(unittest.TestCase):
    def test_each_collects_tests(self):
        loader = unittest.TestLoader()
        for f in FILES[:3]:
            n = loader.loadTestsFromName("tests." + Path(f).stem).countTestCases()
            self.assertGreater(n, 0, f)

    def test_no_pytest_function_is_left(self):
        for f in FILES[:3]:
            src = (REPO / f).read_text(encoding="ascii")
            self.assertNotIn("\ndef test_", src, f)
            self.assertIn("sys.executable" if "subprocess" in src else "import normalize_text", src, f)


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_legacytests_*")) for f in FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_legacytests_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "tests").mkdir()
            for f in FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
