# -*- coding: ascii -*-
"""DOCS88_2026_10_22: the night of 22 Oct recorded (DEBT section 9, STATE 23, RUNBOOK, PLATFORM 91, ENTERPRISE_PATH
78); the patcher writes once, after DOCS87, all or nothing, and only where what it records (docs/ASKS_2026-10-22.md,
OCR_BENCHMARK, DOC_REGISTER, GRETIL_NEXT) is; the register itself is ASCII and carries the keys the addendum cites.
Temp folders only, and the repository's own docs/ASKS_2026-10-22.md read."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs88_2026_10_22.py"
ASKS = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS88_2026_10_22"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt (DOCS85_2026_10_22)\n## 8. x (DOCS87_2026_10_22)\n",
    "docs/STATE_2026-10-18.md": "DOCS87_2026_10_22\n## 22. x\n",
    "RUNBOOK.md": "DOCS87_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS87_2026_10_22\n## 90. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS87_2026_10_22\n## Addendum (77)\n",
}
CODE = {
    "docs/ASKS_2026-10-22.md": "# asks (DOCS88_2026_10_22)\n",
    "scripts/ocr_benchmark.py": "# OCR_BENCHMARK_2026_10_22\n",
    "scripts/doc_register.py": "# DOC_REGISTER_2026_10_22\n",
    "scripts/gretil_library.py": "# GRETIL_LIBRARY_2026_10_22 GRETIL_NEXT_2026_10_22\n",
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

    def test_it_writes_once_after_docs87(self):
        self.assertIn("CHECK OK: 5 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in list(DOCS):
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs88_" + __import__("datetime").date.today()
                                                   .strftime("%Y%m%d")).exists(), "backup first: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 9. What GRETIL taught us", "b0ba93c3", "c4849e8", "| Narasimha Purana | 83.22% | 3,555 of 3,582 | 27 |",
                  "vision 4.33", "Tesseract 12.02", "archive.org 25.20", "Is it a learning system?", "about $4.80",
                  "Parasara 363 of 941", "not by\n  setting its verses into our scan", "63 labels", "decided on 18 Oct (L1)",
                  "MEMBER --doc DOC", "2,031 with English"):
            self.assertIn(x, d, x)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"patch_gretil_next_2026_10_22.py", b"patch_docs88_2026_10_22.py", b"scripts\\ocr_benchmark.py",
                  b"doc_register.py --open --before", b"Lovable Publish first"):
            self.assertIn(x, rb, x)
        self.assertIn(b"## 23. 22 Oct, night", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn(b"## 91. The benchmark; the register", (self.t / "docs/PLATFORM_2026-10-04.md").read_bytes())
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        self.assertIn("(78) (DOCS88_2026_10_22)", ep)
        self.assertIn("| T10 | test_mbh_prose: 3 errors on the PC alone | Closed:", ep)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOCS87_2026_10_22", r.stdout)
        for f in list(DOCS):
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(DOCS["docs/STATE_2026-10-18.md"].encode("utf-8"))
        (self.t / "scripts/gretil_library.py").write_text("# GRETIL_LIBRARY_2026_10_22\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("GRETIL_NEXT_2026_10_22", r.stdout, "the docs wait for the patch they record")
        for f in DOCS:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)


class TheFiles(unittest.TestCase):
    def test_the_register(self):
        if not ASKS.exists():
            self.skipTest("docs/ASKS_2026-10-22.md is not here")
        a = ASKS.read_text(encoding="ascii")
        self.assertIn(MARK, a)
        for key in ("nirukta-text", "witness-adopt", "witness-vision-pairs", "srangam-seo-publish", "docs-coherence",
                    "witness-check", "edge-functions-review", "gretil-legacy-terms"):
            self.assertIn("| %s |" % key, a, key)
        self.assertIn("decided 18 Oct (L1", a)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
