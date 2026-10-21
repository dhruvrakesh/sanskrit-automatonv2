# -*- coding: ascii -*-
"""DOCS82_2026_10_21: the counts explained and the Satapatha's sources recorded (the brain page's section 8, PLATFORM
85, RUNBOOK, ENTERPRISE_PATH 72, STATE 17); the patcher writes once, after DOCS81, all or nothing; the checks it names
are read-only. Temp folders only."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs82_2026_10_21.py"
SQL = REPO / "docs" / "cloud" / "CHECKS_held_2026-10-21.sql"
MARK = "DOCS82_2026_10_21"
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS81_2026_10_21\n## 16. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS81_2026_10_21\n## Addendum (71)\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS81_2026_10_21\n## 84. x\n",
    "RUNBOOK.md": "DOCS81_2026_10_21\r\nline\r\n",
    "docs/BRAIN_PATH_2026-10-21.md": "DOCS81_2026_10_21\n## 7. B1 done\n",
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

    def test_it_writes_once_after_docs81(self):
        self.assertIn("CHECK OK: 5 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        bp = (self.t / "docs/BRAIN_PATH_2026-10-21.md").read_text(encoding="utf-8")
        for s in ("## 8. The counts explained", "1,531 there", "That is the 175", "Satyavrata", "ETEXT_PROSE_2026_10_21",
                  "public domain only when viewed in the US", "curl.exe does not"):
            self.assertIn(s, bp)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        self.assertIn(b'$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"', rb)
        self.assertIn(b"sources\\satapatha_gretil", rb)
        self.assertIn("## 85. The counts explained", (self.t / "docs/PLATFORM_2026-10-04.md").read_text(encoding="utf-8"))
        self.assertIn("## 17. 21 Oct", (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/STATE_2026-10-18.md").write_text("no marker here\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("has no DOCS81_2026_10_21 section", r.stdout)
        for f in BODY:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "all or nothing: " + f)

    def test_ascii_and_the_checks(self):
        for f in (PAT, Path(__file__), SQL):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        body = re.sub(r"--[^\n]*", "", SQL.read_text(encoding="ascii")).upper()
        for w in ("INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE", "GRANT", "TRUNCATE"):
            self.assertNotRegex(body, r"\b%s\b" % w, "read-only: " + w)
        self.assertEqual(body.count(";"), 3, "three blocks, H1 to H3")


if __name__ == "__main__":
    unittest.main()
