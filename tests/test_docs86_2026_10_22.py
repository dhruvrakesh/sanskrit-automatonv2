# -*- coding: ascii -*-
"""DOCS86_2026_10_22: the afternoon's run recorded (DEBT section 7, STATE 21, RUNBOOK, PLATFORM 89, ENTERPRISE_PATH
76); the patcher writes once, after DOCS85, all or nothing, and needs docs/cloud/CHECKS_followup_2026-10-22.sql,
whose blocks only read. Temp folders only."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs86_2026_10_22.py"
CHECKS = REPO / "docs" / "cloud" / "CHECKS_followup_2026-10-22.sql"
MARK = "DOCS86_2026_10_22"
BODY = {
    "docs/DEBT_2026-10-22.md": "# debt (DOCS85_2026_10_22)\n## 6. x\n",
    "docs/STATE_2026-10-18.md": "DOCS85_2026_10_22\n## 20. x\n",
    "RUNBOOK.md": "DOCS85_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS85_2026_10_22\n## 88. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS85_2026_10_22\n## Addendum (75)\n",
    "docs/cloud/CHECKS_followup_2026-10-22.sql": "-- checks\n",
}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "docs" / "cloud").mkdir(parents=True)
        for f, b in BODY.items():
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs85(self):
        self.assertIn("CHECK OK: 5 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in list(BODY)[:5]:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for s in ("## 7. After the release", "33b50ae5", "16.5%", "4,676", "11.27", "NO TESTS RAN", "403"):
            self.assertIn(s, d, s)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for s in (b"patch_witness_fix_2026_10_22.py", b"patch_legacy_tests_2026_10_22.py", b'"(?m)^FAILED.*$"',
                  b"the preview first", b"CHECKS_followup_2026-10-22.sql"):
            self.assertIn(s, rb, s)
        self.assertIn(b"## 21. 22 Oct", (self.t / "docs/STATE_2026-10-18.md").read_bytes())
        self.assertIn(b"## 89. After the release", (self.t / "docs/PLATFORM_2026-10-04.md").read_bytes())
        self.assertIn(b"(76) (DOCS86_2026_10_22)", (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_bytes())
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOCS85_2026_10_22", r.stdout)
        for f in list(BODY)[:5]:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)
        (self.t / "docs/STATE_2026-10-18.md").write_bytes(BODY["docs/STATE_2026-10-18.md"].encode("utf-8"))
        (self.t / "docs/cloud/CHECKS_followup_2026-10-22.sql").unlink()
        self.assertEqual(self.run_pat().returncode, 2)


class TheChecks(unittest.TestCase):
    def test_they_only_read(self):
        if not CHECKS.exists():
            self.skipTest("the checks are not here")
        q = CHECKS.read_text(encoding="utf-8")
        body = "\n".join(l for l in q.splitlines() if not l.lstrip().startswith("--"))
        self.assertGreaterEqual(body.upper().count("SELECT"), 3)
        for w in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"):
            self.assertIsNone(re.search(r"\b%s\b" % w, body, re.I), w)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__), CHECKS):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
