# -*- coding: ascii -*-
"""DOCS94_2026_10_24: the night of 24 Oct recorded (DEBT section 15, STATE 29, RUNBOOK, PLATFORM 97, ENTERPRISE_PATH 84,
ASKS 11, RELATIONS_AND_ASK 9) and the Relations page added to README.md's web UI after its /ask entry; the patcher
writes once, after DOCS93, all or nothing, and only where what it records is. Temp folders only."""
import datetime, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs94_2026_10_24.py"
MARK = "DOCS94_2026_10_24"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt\n## 14. x (DOCS93_2026_10_24)\n",
    "docs/STATE_2026-10-18.md": "# state\n## 28. x (DOCS93_2026_10_24)\n",
    "RUNBOOK.md": "DOCS93_2026_10_24\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS93_2026_10_24\n## 96. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS93_2026_10_24\n## Addendum (83)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS93_2026_10_24)\n## 10. x\n",
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS93_2026_10_24)\n## 8. x\n",
}
README = ("## The web UI\r\n\r\n- **/ask** - Ask the Corpus: falls back to keyword search when\r\n"
          "  the embedding index isn't built.\r\n- **Database** - Datasette.\r\n")
CODE = {f: "# %s\n" % m for f, m in {
    "scripts/relations_view.py": "RELATIONS_UI_2026_10_24", "scripts/relations.html": "RELATIONS_UI_2026_10_24",
    "scripts/patch_relations_ui_2026_10_24.py": "RELATIONS_UI_2026_10_24",
    "tests/test_relations_ui_2026_10_24.py": "RELATIONS_UI_2026_10_24",
    "scripts/patch_maint_guard_2026_10_24.py": "MAINT_GUARD_2026_10_24",
    "tests/test_maint_guard_2026_10_24.py": "MAINT_GUARD_2026_10_24",
    "scripts/patch_kin_also_2026_10_24.py": "KIN_ALSO_2026_10_24",
    "tests/test_kin_also_2026_10_24.py": "KIN_ALSO_2026_10_24"}.items()}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        for f, b in list(DOCS.items()) + list(CODE.items()) + [("README.md", README)]:
            (self.t / f).parent.mkdir(parents=True, exist_ok=True)
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs93(self):
        self.assertIn("CHECK OK: 8 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stamp = datetime.date.today().strftime("%Y%m%d")
        for f in list(DOCS) + ["README.md"]:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs94_" + stamp).exists(), "backup: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 15. 24 Oct, night", '{"ms":3104,"pairs":45183,"was_filled":false}', "4,822", "1,516", "86 in five",
                  "Yajnavalkya 33", "9a840934", "$115.00", "1,016 of 2,941", "$0.00114", "every 3 hours",
                  "at 15:00 the runner wrote", "http://127.0.0.1:5057/relations", "12\n  persons", "epithets",
                  "phase U3"):
            self.assertIn(x, d, x)
        self.assertNotIn("\\\\", d, "single backslashes in the paths")
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"patch_relations_ui_2026_10_24.py --check", b"patch_maint_guard_2026_10_24.py",
                  b"patch_kin_also_2026_10_24.py", b"http://127.0.0.1:5057/relations", b"Publish Srangam"):
            self.assertIn(x, rb, x)
        rd = (self.t / "README.md").read_bytes()
        self.assertNotIn(b"\n", rd.replace(b"\r\n", b""), "README keeps its CRLF")
        s = rd.decode("utf-8")
        self.assertLess(s.index("the embedding index isn't built."), s.index("- **/relations**"))
        self.assertLess(s.index("- **/relations**"), s.index("- **Database**"))
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        for k in ("names-ui", "relations-ui-local", "relations-ui-site (U3)", "maint-guard", "kin-also", "relations-index"):
            self.assertIn("| %s |" % k, ep, k)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_without_what_it_records(self):
        (self.t / "scripts/relations_view.py").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("relations_view.py does not carry", r.stdout)
        self.assertNotIn(MARK, (self.t / "README.md").read_text(encoding="utf-8"))

    def test_refuses_before_docs93_all_or_nothing(self):
        (self.t / "docs/ASKS_2026-10-22.md").write_bytes(b"# asks\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        for f in list(DOCS) + ["README.md"]:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "nothing written: " + f)

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
