# -*- coding: ascii -*-
"""DOCS89_2026_10_22: the last of 22 Oct recorded (DEBT section 10, STATE 24, RUNBOOK, PLATFORM 92, ENTERPRISE_PATH
79, ASKS 6); the patcher writes once, after DOCS88, all or nothing, and only where what it records
(docs/RELATIONS_AND_ASK_2026-10-22.md, RELATIONS_CENSUS) is; the page itself is ASCII and carries the keys the
addendum cites. Temp folders only, and the repository's own page read."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs89_2026_10_22.py"
PAGE = REPO / "docs" / "RELATIONS_AND_ASK_2026-10-22.md"
MARK = "DOCS89_2026_10_22"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt (DOCS85_2026_10_22)\n## 9. x (DOCS88_2026_10_22)\n",
    "docs/STATE_2026-10-18.md": "DOCS88_2026_10_22\n## 23. x\n",
    "RUNBOOK.md": "DOCS88_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS88_2026_10_22\n## 91. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS88_2026_10_22\n## Addendum (78)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS88_2026_10_22)\n## 5. x\n",
}
CODE = {
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS89_2026_10_22)\n",
    "scripts/relations_census.py": "# RELATIONS_CENSUS_2026_10_22\n",
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

    def test_it_writes_once_after_docs88(self):
        self.assertIn("CHECK OK: 6 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in list(DOCS):
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs89_" + __import__("datetime").date.today()
                                                   .strftime("%Y%m%d")).exists(), "backup first: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 10. Published", "8f503ad2", "c4849e8", "mode `readers`", "not a site text", "+298, -38",
                  "45,994 pairs", "4,983 in two passages", "Yajnavalkya in 33 passages", "no Ask on the site",
                  "no CI", "R1 and U1 first"):
            self.assertIn(x, d, x)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"patch_docs89_2026_10_22.py", b"relations_census.py --name Janaka", b"git -C"):
            self.assertIn(x, rb, x)
        self.assertIn(b"## 24. 22 Oct, last", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn(b"## 92. The names measured", (self.t / "docs/PLATFORM_2026-10-04.md").read_bytes())
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        self.assertIn("(79) (DOCS89_2026_10_22)", ep)
        self.assertIn("| ci-tests |", ep)
        self.assertIn("## 6. 22 Oct, last", (self.t / "docs/ASKS_2026-10-22.md").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOCS88_2026_10_22", r.stdout)
        for f in list(DOCS):
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(DOCS["docs/STATE_2026-10-18.md"].encode("utf-8"))
        (self.t / "scripts/relations_census.py").write_text("# not yet\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("RELATIONS_CENSUS_2026_10_22", r.stdout, "the docs wait for the tool they record")
        for f in DOCS:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)


class TheFiles(unittest.TestCase):
    def test_the_page(self):
        if not PAGE.exists():
            self.skipTest("docs/RELATIONS_AND_ASK_2026-10-22.md is not here")
        a = PAGE.read_text(encoding="ascii")
        self.assertIn(MARK, a)
        for key in ("relations-together", "relations-index", "ask-v2", "ask-site", "ask-ui", "names-ui",
                    "load-measure", "english-coverage"):
            self.assertIn("| %s |" % key, a, key)
        for x in ("26,848", "45,994", "It reads no Sanskrit", "No CI"):
            self.assertIn(x, a, x)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
