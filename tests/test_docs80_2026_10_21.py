# -*- coding: ascii -*-
"""DOCS80_2026_10_21: the night of 21 Oct recorded (PLATFORM 83, RUNBOOK, ENTERPRISE_PATH 70, STATE 15) and the figure
of the verses of numbers corrected ($2.10 by the run's own count) where DOCS79 gave $2.01; the patcher writes once, after
DOCS79, all or nothing; the page docs/BRAIN_PATH_2026-10-21.md names its markers. Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs80_2026_10_21.py"
MARK = "DOCS80_2026_10_21"
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS79_2026_10_21\n  (17:48 IST: 15 passed, 3 flagged, $2.01; data/scholar/x.jsonl).\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS79_2026_10_21\n| S2 | x | Done: 15 passed, 3 flagged, $2.01. Addendum 68 had said |\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS79_2026_10_21\n- 18 verses: 15 passed, 3 flagged, $2.01.\n",
    "RUNBOOK.md": "DOCS79_2026_10_21\r\nline\r\n",
    "docs/CLAIMS_AND_REFS_2026-10-21.md": "a (18 verses, 15 passed, 3\nflagged, $2.01); its rows still carry b\nthe Gemini run "
                                          "was the one made: 18 verses, 15 passed, 3\nflagged, $2.01.\n",
}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "docs").mkdir()
        for f, b in BODY.items():
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self):
        return subprocess.run([sys.executable, str(PAT)], cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs79(self):
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            t = (self.t / f).read_text(encoding="utf-8")
            self.assertIn(MARK, t, f)
            if f != "RUNBOOK.md":
                self.assertNotIn("$2.01;", t.replace("sum to $2.01", ""), f)
                self.assertIn("$2.10", t, f)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        self.assertIn(b'$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"', rb)
        self.assertIn("## 15. 21 Oct, night", (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
        self.assertIn("## 83. The claims audited", (self.t / "docs/PLATFORM_2026-10-04.md").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/PLATFORM_2026-10-04.md").write_text("DOCS79_2026_10_21\nno figure here\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("anchor 1 found 0 times", r.stdout)
        self.assertNotIn(MARK, (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"), "all or nothing")

    def test_ascii_and_the_page(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        page = REPO / "docs" / "BRAIN_PATH_2026-10-21.md"
        if page.exists():
            t = page.read_text(encoding="utf-8")
            for m in ("CLAIMS_FIX_2026_10_21", "DOCS80_2026_10_21", "Copyright Act, 1957", "John Robert Gardner"):
                self.assertIn(m, t)


if __name__ == "__main__":
    unittest.main()
