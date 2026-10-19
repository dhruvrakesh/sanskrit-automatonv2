# -*- coding: ascii -*-
"""DOCS77_2026_10_19: the morning of 19 Oct recorded (PLATFORM 80, RUNBOOK, ENTERPRISE_PATH 67, STATE 12) with
docs/LEAK_GUARD_2026-10-19.md; the patcher appends once, after DOCS76, all or nothing. Temp folders only."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs77_2026_10_19.py"
MARK = "DOCS77_2026_10_19"
FILES = ("docs/PLATFORM_2026-10-04.md", "RUNBOOK.md", "docs/ENTERPRISE_PATH_2026-10-04.md", "docs/STATE_2026-10-18.md")


class TheDocs(unittest.TestCase):
    def test_it_appends_once_after_docs76(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "docs").mkdir()
            for f in FILES:
                (t / f).write_text("# %s\n\nDOCS76_2026_10_18\n" % f, encoding="utf-8")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in FILES:
                self.assertIn(MARK, (t / f).read_text(encoding="utf-8"), f)
            self.assertIn("## 12. The morning of 19 Oct", (t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
            self.assertIn("Nothing to do", subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True,
                                                          text=True).stdout)
            (t / "RUNBOOK.md").write_text("# no docs76 yet\n", encoding="utf-8")
            for f in FILES[2:]:
                (t / f).write_text("DOCS76_2026_10_18\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn(MARK, (t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"), "all or nothing")

    def test_ascii_and_the_page(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        page = REPO / "docs" / "LEAK_GUARD_2026-10-19.md"
        if page.exists():
            self.assertIn("LEAK_GUARD_2026_10_19", page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
