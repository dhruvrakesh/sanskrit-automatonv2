# -*- coding: ascii -*-
"""DOCS83_2026_10_22: the morning of 22 Oct recorded (the brain page's section 9, PLATFORM 86, RUNBOOK, ENTERPRISE_PATH
73, STATE 18), and two things DOCS81 and DOCS82 said corrected: no proxy is set on the PC, and GRETIL's Satapatha has
one danda a kandika in kandas 1 to 9; the patcher writes once, after DOCS82, all or nothing. Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs83_2026_10_22.py"
MARK = "DOCS83_2026_10_22"
BRAIN = ("DOCS82_2026_10_21\n- The dandas: the Satapatha is prose and its unit is the kandika; neither e-text prints dandas "
         "within one. Ours would\n  kandika under its own line (13.1.1.[1]); IAST without the Vedic accents and without "
         "dandas; the pluti written 3, the\n**Why the PC could not download:** x where curl.exe\nreaches GRETIL (HTTP 200): "
         "PowerShell goes through Windows' proxy settings and curl.exe does not. The RUNBOOK shows\nthe settings; the "
         "downloads use curl.exe.\n")
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS82_2026_10_21\n  (curl.exe; Invoke-WebRequest goes through Windows' proxy settings).\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS82_2026_10_21\n## Addendum (72)\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS82_2026_10_21\n## 85. x\n",
    "RUNBOOK.md": "DOCS82_2026_10_21\r\nline\r\n",
    "docs/BRAIN_PATH_2026-10-21.md": BRAIN,
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

    def test_it_writes_once_after_docs82(self):
        self.assertIn("CHECK OK: 5 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        bp = (self.t / "docs/BRAIN_PATH_2026-10-21.md").read_text(encoding="utf-8")
        self.assertNotIn("goes through Windows' proxy settings", bp)
        self.assertNotIn("neither e-text prints dandas", bp)
        self.assertNotIn("without dandas", bp)
        for s in ("the PC has none", "## 9. The Satapatha read in full", "its ch", "7,173 kandikas", "246",
                  "Samasrami", "25,335", "$0.00058"):
            self.assertIn(s, bp, s)
        st = (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8")
        self.assertNotIn("goes through Windows' proxy settings", st)
        self.assertIn("## 18. 22 Oct", st)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        self.assertIn(b"wipe_doc.py --doc 2015_405693_Shatpath-Brahmanam__w_gretil --dry-run", rb)
        self.assertIn(b"--slug gretil --category brahmana --per-page 10", rb)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("DOCS82_2026_10_21\nno such sentence\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("anchor 1 found 0 times", r.stdout)
        for f in BODY:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
