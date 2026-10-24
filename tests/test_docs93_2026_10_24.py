# -*- coding: ascii -*-
"""DOCS93_2026_10_24: the evening of 24 Oct recorded (DEBT section 14, STATE 28 with a line under its title, RUNBOOK,
PLATFORM 96, ENTERPRISE_PATH 83, ASKS 10, RELATIONS_AND_ASK 8); the patcher writes once, after DOCS92, all or nothing,
and only where what it records is. Temp folders only."""
import datetime, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs93_2026_10_24.py"
MARK = "DOCS93_2026_10_24"
TITLE = "# The state of the project, all repos and how they join (18 Oct 2026)\n"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt\n## 13. x (DOCS92_2026_10_24)\n",
    "docs/STATE_2026-10-18.md": TITLE + "\nMarker: x\n## 27. x (DOCS92_2026_10_24)\n",
    "RUNBOOK.md": "DOCS92_2026_10_24\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS92_2026_10_24\n## 95. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS92_2026_10_24\n## Addendum (82)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS92_2026_10_24)\n## 9. x\n",
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS92_2026_10_24)\n## 7. x\n",
}
CODE = {
    "scripts/patch_kin_lines_2026_10_24.py": "# KIN_LINES_2026_10_24\n",
    "tests/test_kin_lines_2026_10_24.py": "# KIN_LINES_2026_10_24\n",
    "scripts/patch_name_links_fast_2026_10_24.py": "# NAME_LINKS_FAST_2026_10_24\n",
    "docs/cloud/C20d_name_links_fast_2026-10-24.sql": "-- NAME_LINKS_FAST_2026_10_24\n",
    "docs/cloud/C20d_checks_2026-10-24.sql": "-- NAME_LINKS_FAST_2026_10_24\n",
    "tests/test_name_links_fast_pg_2026_10_24.py": "# NAME_LINKS_FAST_2026_10_24\n",
    "scripts/patch_ask_homonym_2026_10_24.py": "# ASK_HOMONYM_2026_10_24\n",
    "tests/test_ask_homonym_2026_10_24.py": "# ASK_HOMONYM_2026_10_24\n",
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

    def test_it_writes_once_after_docs92(self):
        self.assertIn("CHECK OK: 7 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stamp = datetime.date.today().strftime("%Y%m%d")
        for f in DOCS:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs93_" + stamp).exists(), "backup: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 14. 24 Oct, evening", "58cddb1c", "1,430 tests", "03:02:17 UTC", "ONE row", "58,913 pairs",
                  "5-minute limit", "913 calls", "$4.67", "15,409 kept", "2,243",
                  "40 steps from Narayana", "29\n  lines", "Indra (I) > Arjuna (III)", "381 (10%)",
                  "$0.2021", "about $12.2", "$6.52", "$0.0085"):
            self.assertIn(x, d, x)
        self.assertNotIn("\\\\", d, "single backslashes in the paths")
        s = (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8")
        self.assertTrue(s.startswith(TITLE + "\n> **Read first:** the newest state is the LAST section"), s[:300])
        self.assertEqual(s.count("Read first"), 1)
        self.assertIn("## 28. 24 Oct, evening", s)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"patch_kin_lines_2026_10_24.py --check", b"patch_name_links_fast_2026_10_24.py",
                  b"patch_ask_homonym_2026_10_24.py", b"C20d_name_links_fast_2026-10-24.sql", b"C20d_checks_2026-10-24.sql",
                  b"kin_index.py --yes --per-source 0 --max-usd 2.00", b"--doc nirukta__w_gretil --sample-pct 10",
                  b"restart_dashboard.ps1 -Status"):
            self.assertIn(x, rb, x)
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        for k in ("names-ui", "relations-lines", "ask-homonym", "relations-index", "nirukta-judge", "yajur-shukla",
                  "vamsa-corpus", "relations-names", "h2", "ask-site", "claims-mirror", "hygiene"):
            self.assertIn("| %s |" % k, ep, k)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_without_what_it_records(self):
        (self.t / "docs/cloud/C20d_name_links_fast_2026-10-24.sql").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("C20d_name_links_fast_2026-10-24.sql does not carry", r.stdout)
        self.assertNotIn(MARK, (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8"))

    def test_refuses_before_docs92_all_or_nothing(self):
        (self.t / "docs/ASKS_2026-10-22.md").write_bytes(b"# asks\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("has no DOCS92_2026_10_24", r.stdout)
        for f in DOCS:
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "nothing written: " + f)

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
