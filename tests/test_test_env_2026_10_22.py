# -*- coding: ascii -*-
"""TEST_ENV_2026_10_22: scripts/run_tests.ps1 runs each test module with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8, as
the dashboard runs its jobs, and reports each failing module's verdict; test_repo_hygiene's replay accepts a later
patch's backup of .gitignore; the patcher applies once, from the copy it found. Reads the files only."""
import os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PS = REPO / "scripts" / "run_tests.ps1"
DASH = REPO / "scripts" / "dashboard.py"
T = REPO / "tests" / "test_repo_hygiene_2026_10_15.py"
PAT = REPO / "scripts" / "patch_test_env_2026_10_22.py"
MARK = "TEST_ENV_2026_10_22"
APPLIED = MARK.encode() in T.read_bytes()


class TheRunner(unittest.TestCase):
    def setUp(self):
        if not PS.exists():
            self.skipTest("run_tests.ps1 is not here")

    def test_it_runs_as_the_dashboard_runs_jobs(self):
        s = PS.read_text(encoding="ascii")
        self.assertTrue(all(x < 128 for x in PS.read_bytes()), "PowerShell 5.1: ASCII")
        for line in ('$env:PYTHONUTF8 = "1"', '$env:PYTHONIOENCODING = "utf-8"', '$env:PYTHONDONTWRITEBYTECODE = "1"',
                     '-m unittest $m 2>&1', '"(?m)^FAILED \\([^)]*\\)"', '"NO TESTS RAN"', "exit 1", MARK):
            self.assertIn(line, s, line)
        self.assertNotIn("[Environment]::SetEnvironmentVariable", s, "nothing set for the machine or the account")
        d = DASH.read_text(encoding="utf-8")
        self.assertIn('env["PYTHONUTF8"] = "1"', d, "the dashboard's own way, which this follows")

    def test_a_cp1252_pipe_is_why(self):
        r = subprocess.run([sys.executable, "-c", "print('\\u0101')"], capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0"))
        self.assertNotEqual(r.returncode, 0, "a cp1252 pipe cannot print IAST")
        r = subprocess.run([sys.executable, "-c", "print('\\u0101')"], capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.decode("utf-8").strip(), "\u0101")


@unittest.skipUnless(APPLIED, "TEST_ENV_2026_10_22 is not applied here")
class TheHygieneReplay(unittest.TestCase):
    def test_a_later_backup_is_accepted(self):
        s = T.read_text(encoding="ascii")
        self.assertIn('if ".bak_hygiene_" not in x.name]', s)
        self.assertIn("got == cur.read_bytes() or got in later", s)

    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(T.parent.glob(T.name + ".bak_testenv_*"))
        if not baks:
            self.skipTest("no .bak_testenv_ copy here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "tests").mkdir()
            shutil.copy2(baks[0], t / "tests" / T.name)
            pat = [sys.executable, str(PAT)]
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((t / "tests" / T.name).read_bytes(), T.read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
