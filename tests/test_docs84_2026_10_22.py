# -*- coding: ascii -*-
"""DOCS84_2026_10_22: the letter fidelity of 22 Oct recorded (the brain page's section 10, PLATFORM 87, RUNBOOK,
ENTERPRISE_PATH 74, STATE 19) and QUALITY_METHODOLOGY's known blind spot measured for vision OCR; the patcher writes
once, after DOCS83, all or nothing, and needs docs/FIDELITY_2026-10-22.md. Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs84_2026_10_22.py"
MARK = "DOCS84_2026_10_22"
QM = ('## 1. Source quality\r\n(GRETIL / sanskritdocuments / wisdomlib). Treat a high source score on a pre-1900 scan as\r\n'
      '"probably readable", and confirm by eye or by the translation\'s own QA.\r\n\r\n---\r\n'
      '*Last reviewed 2026-08-28. Formulas are authoritative to `scripts/text_filters.py`; if the\r\n')
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS83_2026_10_22\n## 18. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS83_2026_10_22\n## Addendum (73)\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS83_2026_10_22\n## 86. x\n",
    "RUNBOOK.md": "DOCS83_2026_10_22\r\nline\r\n",
    "docs/BRAIN_PATH_2026-10-21.md": "DOCS83_2026_10_22\n## 9. x\n",
    "QUALITY_METHODOLOGY.md": QM,
    "docs/FIDELITY_2026-10-22.md": "# fidelity\n",
    ".gitignore": "data/raw_witness/\ndata/source_judged/\n",
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

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs83(self):
        self.assertIn("CHECK OK: 7 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            if f != "docs/FIDELITY_2026-10-22.md":
                self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        bp = (self.t / "docs/BRAIN_PATH_2026-10-21.md").read_text(encoding="utf-8")
        for s in ("## 10. How faithfully", "3.58", "3.62", "49 to 55", "$4.12", "Nirukta"):
            self.assertIn(s, bp, s)
        qm = (self.t / "QUALITY_METHODOLOGY.md").read_bytes()
        self.assertNotIn(b"\n", qm.replace(b"\r\n", b""), "QUALITY_METHODOLOGY keeps its CRLF")
        self.assertIn(b"Measured letter by letter (2026-10-22", qm)
        self.assertIn(b"*Last reviewed 2026-08-28; the letter fidelity in section 1 on 2026-10-22", qm)
        self.assertLess(qm.index(b"Measured letter by letter"), qm.index(b"---"))
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        self.assertIn(b"source_fidelity.py --ref db:markandeya_purana__w_gretil", rb)
        self.assertIn(b"archive_dli_2015_405693_djvu.txt", rb)
        self.assertIn(b"## 19. 22 Oct", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn("\ndata/source_fidelity/\n", (self.t / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "QUALITY_METHODOLOGY.md").write_text("no blind spot here\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSE: QUALITY_METHODOLOGY.md", r.stdout)
        for f in BODY:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "QUALITY_METHODOLOGY.md").write_bytes(QM.encode("utf-8"))
        (self.t / "docs/FIDELITY_2026-10-22.md").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 2)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
