# -*- coding: ascii -*-
"""DOCS87_2026_10_22: the evening of 22 Oct recorded (DEBT section 8, STATE 22, RUNBOOK, PLATFORM 90, ENTERPRISE_PATH
77) and data/gretil/ in .gitignore; the patcher writes once, after DOCS86, all or nothing, and only where the code it
records (GRETIL_LIBRARY, TEST_ENV, ETEXT_ANALYSIS) is. Temp folders only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs87_2026_10_22.py"
MARK = "DOCS87_2026_10_22"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt (DOCS85_2026_10_22)\n## 7. x (DOCS86_2026_10_22)\n",
    "docs/STATE_2026-10-18.md": "DOCS86_2026_10_22\n## 21. x\n",
    "RUNBOOK.md": "DOCS86_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS86_2026_10_22\n## 89. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS86_2026_10_22\n## Addendum (76)\n",
}
CODE = {
    ".gitignore": "sources/\n# FIDELITY_2026_10_22 (DOCS84_2026_10_22): reports\ndata/source_fidelity/\n",
    "scripts/gretil_library.py": "# GRETIL_LIBRARY_2026_10_22\n",
    "scripts/run_tests.ps1": "# TEST_ENV_2026_10_22\n",
    "tests/test_repo_hygiene_2026_10_15.py": "# TEST_ENV_2026_10_22\n",
    "scripts/etext_witness.py": "# ETEXT_ANALYSIS_2026_10_22\n",
}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        for d in ("docs", "scripts", "tests"):
            (self.t / d).mkdir()
        for f, b in list(DOCS.items()) + list(CODE.items()):
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs86(self):
        self.assertIn("CHECK OK: 6 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in list(DOCS) + [".gitignore"]:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs87_" + __import__("datetime").date.today()
                                                   .strftime("%Y%m%d")).exists(), "backup first: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for s in ("## 8. GRETIL's library", "ef43359b", "75.33%", "70.74%", "cp1252", "run_tests.ps1",
                  "295,862,698", "CC BY-NC-SA 4.0", "387", "REFERENCE PURPOSES ONLY", "380 not", "332",
                  "Vettam Mani", "a part or a parallel", "5,748 verses (3,058)", "Siddheswar Jena", "Phase AN",
                  "curl.exe", "403"):
            self.assertIn(s, d, s)
        gi = (self.t / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/source_fidelity/\n# GRETIL_LIBRARY_2026_10_22 (DOCS87_2026_10_22)", gi)
        self.assertTrue(gi.endswith("\ndata/gretil/\n"))
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for s in (b"patch_test_env_2026_10_22.py", b"patch_etext_analysis_2026_10_22.py", b"scripts\\run_tests.ps1",
                  b"Move-Item inbox\\1_sanskr.zip sources\\gretil\\", b"--extract 1_sanskr/tei/transformations/html/"
                  b"sa_manusmRti.htm --doc", b"--witness smriti_14manu_smriti_seg__w_gretil",
                  b"curl.exe -s https://srangam.nartiang.org/ | Out-String", b"not `-A`"):
            self.assertIn(s, rb, s)
        self.assertNotIn(b"Invoke-WebRequest https", rb)
        self.assertIn(b"## 22. 22 Oct, evening", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn(b"## 90. GRETIL's library", (self.t / "docs/PLATFORM_2026-10-04.md").read_bytes())
        self.assertIn(b"(77) (DOCS87_2026_10_22)", (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_bytes())
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOCS86_2026_10_22", r.stdout)
        for f in list(DOCS) + [".gitignore"]:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(DOCS["docs/STATE_2026-10-18.md"].encode("utf-8"))
        (self.t / "scripts/etext_witness.py").write_text("# not yet\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("ETEXT_ANALYSIS_2026_10_22", r.stdout, "the docs wait for the code they record")
        (self.t / "scripts/etext_witness.py").write_bytes(CODE["scripts/etext_witness.py"].encode("utf-8"))
        (self.t / ".gitignore").write_text("data/x/\n", encoding="utf-8")
        self.assertEqual(self.run_pat().returncode, 1)
        for f in DOCS:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
