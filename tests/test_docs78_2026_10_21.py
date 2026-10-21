# -*- coding: ascii -*-
"""DOCS78_2026_10_21: 21 Oct recorded (PLATFORM 81, RUNBOOK, ENTERPRISE_PATH 68, STATE 13), docs/LEAK_GUARD_2026-10-19.md
corrected (a Gemini run has no Claude judge), data/shelf/ kept out of git; the patcher writes once, after DOCS77, all
or nothing. Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs78_2026_10_21.py"
MARK = "DOCS78_2026_10_21"
FILES = ("docs/PLATFORM_2026-10-04.md", "RUNBOOK.md", "docs/ENTERPRISE_PATH_2026-10-04.md", "docs/STATE_2026-10-18.md")
LEAK = ("LEAK_GUARD_2026_10_19\n**The money.** ... about $1.45 on\n"
        "Gemini 2.5 Pro (judged by Claude Haiku, so that no family judges its own). The Ganita's scholarly English (about 1,800\n"
        "verses) costs\n\n1. The Surya's last 88 verses: Gemini 2.5 Pro with a Claude Haiku judge now (about $1.45 Google), or "
        "Sonnet when there\n   is credit again (about $4.45).\n2. next\n")


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "docs").mkdir()
        for f in FILES:
            (self.t / f).write_text("# %s\n\nDOCS77_2026_10_19\n" % f, encoding="utf-8")
        (self.t / "docs" / "LEAK_GUARD_2026-10-19.md").write_text(LEAK, encoding="utf-8")
        (self.t / ".gitignore").write_text("data/heal/\n", encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self):
        return subprocess.run([sys.executable, str(PAT)], cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs77(self):
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in FILES:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        self.assertIn("## 13. 21 Oct", (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
        leak = (self.t / "docs" / "LEAK_GUARD_2026-10-19.md").read_text(encoding="utf-8")
        self.assertNotIn("Claude Haiku", leak)
        self.assertIn("refuses a Claude judge for a Gemini run", leak)
        self.assertIn("data/shelf/", (self.t / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "RUNBOOK.md").write_text("# no docs77 yet\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertNotIn(MARK, (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"), "all or nothing")
        self.assertNotIn("data/shelf/", (self.t / ".gitignore").read_text(encoding="utf-8"))

    def test_ascii_and_the_page(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        page = REPO / "docs" / "SHELF_AND_SURYA_2026-10-21.md"
        if page.exists():
            t = page.read_text(encoding="utf-8")
            for m in ("ETEXT_ORTHO_2026_10_21", "WITNESS_MEND_2026_10_21", "NUMERAL_VERSE_2026_10_21", "SHELF_2026_10_21"):
                self.assertIn(m, t)


if __name__ == "__main__":
    unittest.main()
