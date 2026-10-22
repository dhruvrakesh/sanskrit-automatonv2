# -*- coding: ascii -*-
"""DOCS85_2026_10_22: the debt of 22 Oct recorded (the brain page's section 11, PLATFORM 88, RUNBOOK, ENTERPRISE_PATH
75, STATE 20) and FIDELITY's section 6 corrected (the Surya's "about $0.02" was the price of 12 Oct, not today's
fallback); the patcher writes once, after DOCS84, all or nothing, and needs docs/DEBT_2026-10-22.md; the register and
the read-only checks come with it. Temp folders only."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs85_2026_10_22.py"
DEBT = REPO / "docs" / "DEBT_2026-10-22.md"
CHECKS = REPO / "docs" / "cloud" / "CHECKS_debt_2026-10-22.sql"
MARK = "DOCS85_2026_10_22"
FID = ("# fidelity\n\n## 6. Limits\n\n"
       "- The meter's vision price in October is $0.0032 a page (2,987 calls, $9.57). `repair_text.py` prices a repair at the\n"
       "  text's own measured rate, and at a fallback of $0.0004 a page where the text has none (the Surya's \"about $0.02\" for\n"
       "  55 pages): an eighth of October's price. Read such an estimate as about $0.18.\n\n## 7. The path\n")
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS84_2026_10_22\n## 19. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS84_2026_10_22\n## Addendum (74)\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS84_2026_10_22\n## 87. x\n",
    "RUNBOOK.md": "DOCS84_2026_10_22\r\nline\r\n",
    "docs/BRAIN_PATH_2026-10-21.md": "DOCS84_2026_10_22\n## 10. x\n",
    "docs/FIDELITY_2026-10-22.md": FID,
    "docs/DEBT_2026-10-22.md": "# debt\n",
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

    def test_it_writes_once_after_docs84(self):
        self.assertIn("CHECK OK: 6 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            if f != "docs/DEBT_2026-10-22.md":
                self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        bp = (self.t / "docs/BRAIN_PATH_2026-10-21.md").read_text(encoding="utf-8")
        for s in ("## 11. The debt collected", "The intake rule (proposed", "pages:<dir>/<doc>", "0.25 and 0.40"):
            self.assertIn(s, bp, s)
        fid = (self.t / "docs/FIDELITY_2026-10-22.md").read_text(encoding="utf-8")
        self.assertIn("before REINGEST_2026_10_12 priced repairs from the meter", fid)
        self.assertNotIn("an eighth of October's price", fid)
        self.assertLess(fid.index("before REINGEST"), fid.index("## 7. The path"), "in section 6, where it was")
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for s in (b"patch_engines_2026_10_22.py", b"nirukta__w_gretil --dry-run", b"pages:data/raw_vision_pro/",
                  b"CHECKS_debt_2026-10-22.sql", b"pgvector/pgvector:pg16"):
            self.assertIn(s, rb, s)
        self.assertIn(b"## 20. 22 Oct", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn(b"(75) (DOCS85_2026_10_22)", (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_bytes())
        self.assertIn(b"## 88. The debt", (self.t / "docs/PLATFORM_2026-10-04.md").read_bytes())
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/FIDELITY_2026-10-22.md").write_text("# fidelity\n\n## 6. Limits\n\nchanged\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSE: docs", r.stdout)
        for f in BODY:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "docs/FIDELITY_2026-10-22.md").write_bytes(FID.encode("utf-8"))
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOCS84_2026_10_22", r.stdout)
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(BODY["docs/STATE_2026-10-18.md"].encode("utf-8"))
        (self.t / "docs/DEBT_2026-10-22.md").unlink()
        self.assertEqual(self.run_pat().returncode, 2)


class TheRegister(unittest.TestCase):
    def test_it_is_here_and_says_what_it_rests_on(self):
        if not DEBT.exists():
            self.skipTest("the register is not here")
        d = DEBT.read_text(encoding="utf-8")
        for s in ("## 1. Resolved in this release", "## 3. Yours to decide", "UI_CLARITY_2026_10_22",
                  "ENGINES_2026_10_22", "ETEXT_DOTS_2026_10_22", "PG_TESTS_2026_10_22", "1,298 tests", "283 tests",
                  "## 6. Not reviewed this round"):
            self.assertIn(s, d, s)

    def test_the_checks_only_read(self):
        if not CHECKS.exists():
            self.skipTest("the checks are not here")
        q = CHECKS.read_text(encoding="utf-8")
        body = "\n".join(l for l in q.splitlines() if not l.lstrip().startswith("--"))
        self.assertEqual(body.upper().count("SELECT") >= 4, True)
        for w in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"):
            self.assertIsNone(re.search(r"\b%s\b" % w, body, re.I), w)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__), DEBT, CHECKS):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
