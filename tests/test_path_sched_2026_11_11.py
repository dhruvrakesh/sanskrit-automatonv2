# -*- coding: ascii -*-
"""PATH_SCHED_2026_11_11: the path of every text charted again by the maintenance task (step f of
scripts/maintenance_runner.ps1, after the repair's round) when data/text_path.json is 20 hours old or more; free, the
database read only; a failure logged and skipped. The patcher applies once, all or nothing."""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
RUNNER = S / "maintenance_runner.ps1"
PAT = S / "patch_path_sched_2026_11_11.py"
MARK = "PATH_SCHED_2026_11_11"


@unittest.skipUnless(MARK.encode() in RUNNER.read_bytes(), "PATH_SCHED_2026_11_11 is not applied here")
class TheStep(unittest.TestCase):
    def test_after_the_repair_before_done(self):
        r = RUNNER.read_text(encoding="ascii")
        self.assertLess(r.index("STEP e repair"), r.index("STEP f path"))
        self.assertLess(r.index("STEP f path"), r.index("DONE maintenance"))
        f = r[r.index("# f) PATH_SCHED_2026_11_11"):r.index("DONE maintenance")]
        self.assertIn("TotalHours -ge 20", f)
        self.assertIn("scripts\\text_path.py 2>&1", f)
        self.assertIn("STEP f path SKIPPED", f, "a failure is logged and skipped")
        self.assertNotIn("--write", f, "the whole chart, not one text")

    def test_ascii(self):
        for p in (RUNNER, PAT, Path(__file__)):
            if p.exists():
                self.assertTrue(p.read_bytes().isascii(), p.name)


@unittest.skipUnless(PAT.exists(), "the patcher is not here")
class ThePatcher(unittest.TestCase):
    def test_applies_once(self):
        bak = sorted(S.glob("maintenance_runner.ps1.bak_pathsched_*"))
        if not bak:
            self.skipTest("no pre-patch copy beside the file")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(bak[0], t / "scripts" / "maintenance_runner.ps1")
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(MARK.encode(), (t / "scripts" / "maintenance_runner.ps1").read_bytes())
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
