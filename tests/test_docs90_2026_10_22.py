# -*- coding: ascii -*-
"""DOCS90_2026_10_22: the round of 22 Oct night recorded (DEBT section 11, STATE 25, RUNBOOK, PLATFORM 93,
ENTERPRISE_PATH 80, ASKS 7, RELATIONS_AND_ASK 5); the patcher writes once, after DOCS89, all or nothing, and only
where what it records (entity_links.py, the Ask page's patcher, the workflow) is. Temp folders only."""
import datetime, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs90_2026_10_22.py"
MARK = "DOCS90_2026_10_22"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt\n## 10. x (DOCS89_2026_10_22)\n",
    "docs/STATE_2026-10-18.md": "DOCS89_2026_10_22\n## 24. x\n",
    "RUNBOOK.md": "DOCS89_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS89_2026_10_22\n## 92. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS89_2026_10_22\n## Addendum (79)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS89_2026_10_22)\n## 6. x\n",
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS89_2026_10_22)\n## 4. x\n",
}
CODE = {
    "scripts/entity_links.py": "# ENTITY_LINKS_2026_10_22\n",
    "scripts/patch_ask_ui_2026_10_22.py": "# ASK_UI_2026_10_22\n",
    ".github/workflows/tests.yml": "# CI_TESTS_2026_10_22\n",
}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        for f, b in list(DOCS.items()) + list(CODE.items()):
            (self.t / f).parent.mkdir(parents=True, exist_ok=True)
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs89(self):
        self.assertIn("CHECK OK: 7 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stamp = datetime.date.today().strftime("%Y%m%d")
        for f in DOCS:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs90_" + stamp).exists(), "backup: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 11. The links stored", "cdba881c", "45,994 pairs", "235,002 near", "387 name two of our",
                  "78 are named together", "Devapi and Santanu", "1,280 citations", "Maharishi\n  University of Management",
                  "Nighantu (836", "9.57 and 4.95", "no Nighantu of Yaska", "777 pages, about $3.01", "about $3.81",
                  "$85.58 of $95", "backfill_missing.py", "CI and the vision pass (alerts"):
            self.assertIn(x, d, x)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"entity_links.py --apply", b"--claims data\\shelf\\claims.db", b"patch_ask_ui_2026_10_22.py --check",
                  b"--threshold 101 --include-unassessed", b"ocr_benchmark.py", b"DROP TABLE entity_links"):
            self.assertIn(x, rb, x)
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        for k in ("relations-together", "claims-check", "ask-ui", "ci-tests", "witness-vision-pairs", "nirukta-witness",
                  "nighantu-mend", "nirukta-source", "texts-to-seek", "broken-script"):
            self.assertIn("| %s |" % k, ep, k)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_before_docs89_or_without_the_code(self):
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(b"## 24. x\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSE", r.stdout)
        self.assertNotIn(MARK, (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8"), "all or nothing")
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(DOCS["docs/STATE_2026-10-18.md"].encode())
        (self.t / ".github/workflows/tests.yml").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("tests.yml does not carry", r.stdout)

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
