# -*- coding: ascii -*-
"""DOCS79_2026_10_21: the evening of 21 Oct recorded (PLATFORM 82, RUNBOOK, ENTERPRISE_PATH 69, STATE 14); the patcher
writes once, after DOCS78, all or nothing; the page names its markers and owns the estimate of the verses of numbers.
Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs79_2026_10_21.py"
MARK = "DOCS79_2026_10_21"
FILES = ("docs/PLATFORM_2026-10-04.md", "RUNBOOK.md", "docs/ENTERPRISE_PATH_2026-10-04.md", "docs/STATE_2026-10-18.md")


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "docs").mkdir()
        for f in FILES:
            (self.t / f).write_text("# %s\n\nDOCS78_2026_10_21\n" % f, encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self):
        return subprocess.run([sys.executable, str(PAT)], cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs78(self):
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in FILES:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        self.assertIn("## 14. 21 Oct, evening", (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
        self.assertIn("## 82. The Surya's references", (self.t / "docs/PLATFORM_2026-10-04.md").read_text(encoding="utf-8"))
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        self.assertIn('Addendum 68 had said "about $0.30 of Google\'s cap": wrong', ep)
        self.assertIn("15 passed, 3 flagged, $2.01", ep)
        rb = (self.t / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn('$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"', rb)
        self.assertIn("When the Gemini run of the verses of numbers has finished", rb)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "RUNBOOK.md").write_text("# no docs78 yet\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertNotIn(MARK, (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"), "all or nothing")

    def test_ascii_and_the_page(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        page = REPO / "docs" / "CLAIMS_AND_REFS_2026-10-21.md"
        if page.exists():
            t = page.read_text(encoding="utf-8")
            for m in ("ETEXT_REFS_2026_10_21", "CLAIMS_2026_10_21", "ETEXT_NOISE_2026_10_21", "DOCS79_2026_10_21",
                      "75e8d7bd429f9396997cc9e1c2e9f4bd", "That was wrong"):
                self.assertIn(m, t)


if __name__ == "__main__":
    unittest.main()
