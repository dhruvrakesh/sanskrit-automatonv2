# -*- coding: ascii -*-
"""DOCS92_2026_10_24: 24 Oct recorded (DEBT section 13, STATE 27, RUNBOOK, PLATFORM 95, ENTERPRISE_PATH 82, ASKS 9,
RELATIONS_AND_ASK 7) and the 23 Oct C20 files marked superseded at their top; the patcher writes once, after DOCS91,
all or nothing, and only where what it records is. Temp folders only."""
import datetime, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs92_2026_10_24.py"
MARK = "DOCS92_2026_10_24"
SPLIT = "NAME_LINKS_C20_SPLIT_2026_10_24"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt\n## 12. x (DOCS91_2026_10_23)\n",
    "docs/STATE_2026-10-18.md": "DOCS91_2026_10_23\n## 26. x\n",
    "RUNBOOK.md": "DOCS91_2026_10_23\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS91_2026_10_23\n## 94. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS91_2026_10_23\n## Addendum (81)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS91_2026_10_23)\n## 8. x\n",
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS91_2026_10_23)\n## 6. x\n",
}
SQL = {
    "docs/cloud/C20_name_links_2026-10-23.sql": "-- ====\r\n-- C20 (NAME_LINKS_C20_2026_10_23)\r\nBEGIN;\r\n",
    "docs/cloud/C20_checks_2026-10-23.sql": "-- C20 checks (NAME_LINKS_C20_2026_10_23): read-only\n",
}
CODE = {
    "scripts/patch_kin_close_2026_10_24.py": "# KIN_CLOSE_2026_10_24\n",
    "tests/test_kin_close_2026_10_24.py": "# KIN_CLOSE_2026_10_24\n",
    "docs/cloud/C20_preflight_2026-10-24.sql": "-- %s\n" % SPLIT,
    "docs/cloud/C20a_name_links_view_2026-10-24.sql": "-- %s\n" % SPLIT,
    "docs/cloud/C20b_name_links_fill_2026-10-24.sql": "-- %s\n" % SPLIT,
    "docs/cloud/C20c_name_links_nightly_2026-10-24.sql": "-- %s\n" % SPLIT,
    "docs/cloud/C20_checks_2026-10-24.sql": "-- %s\n" % SPLIT,
    "tests/test_name_links_pg_2026_10_24.py": "# %s\n" % SPLIT,
}


class TheDocs(unittest.TestCase):
    def setUp(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        for f, b in list(DOCS.items()) + list(SQL.items()) + list(CODE.items()):
            (self.t / f).parent.mkdir(parents=True, exist_ok=True)
            (self.t / f).write_bytes(b.encode("utf-8"))

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_it_writes_once_after_docs91(self):
        self.assertIn("CHECK OK: 9 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stamp = datetime.date.today().strftime("%Y%m%d")
        for f in list(DOCS) + list(SQL):
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs92_" + stamp).exists(), "backup: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 13. 24 Oct", "541f2e64", "$98.44 spent of $110.00", "470 relations, $0.164", "Kept after the checks",
                  "358 are names our texts'", "$5.51 for 647 calls", "length ratio", "errors=2", "two handles",
                  "Server error", "WITH NO DATA", "316,127 pairs", "before 1 January 2029", "DaivatSanhita_201702.pdf", "341cf7f"):
            self.assertIn(x, d, x)
        self.assertNotIn("\\\\", d, "single backslashes in the paths")
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"patch_kin_close_2026_10_24.py --check", b"C20_preflight_2026-10-24.sql", b"C20a_name_links_view",
                  b"C20b_name_links_fill", b"C20c_name_links_nightly", b"never paste it",
                  b"kin_index.py --yes --per-source 0 --max-usd 4.50", b"--doc nirukta__w_gretil --sample-pct 10",
                  b"yajur_veda_shukla_yajur_veda --release"):
            self.assertIn(x, rb, x)
        old = (self.t / "docs/cloud/C20_name_links_2026-10-23.sql").read_bytes()
        self.assertTrue(old.startswith(b"-- SUPERSEDED 2026-10-24 (DOCS92_2026_10_24)"), "the note on top")
        self.assertNotIn(b"\n", old.replace(b"\r\n", b""), "its line endings kept")
        self.assertIn(b"BEGIN;", old, "the rest as it was")
        ck = (self.t / "docs/cloud/C20_checks_2026-10-23.sql").read_text(encoding="ascii")
        self.assertTrue(ck.startswith("-- SUPERSEDED 2026-10-24 (DOCS92_2026_10_24): use C20_checks_2026-10-24.sql."))
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        for k in ("relations-index", "relations-names", "names-ui", "alerts", "kin-close", "nirukta-witness",
                  "yajur-shukla", "daivat-rights"):
            self.assertIn("| %s |" % k, ep, k)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_without_what_it_records(self):
        (self.t / "docs/cloud/C20a_name_links_view_2026-10-24.sql").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("C20a_name_links_view_2026-10-24.sql does not carry", r.stdout)
        self.assertNotIn(MARK, (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8"))

    def test_refuses_before_docs91_all_or_nothing(self):
        (self.t / "docs/ASKS_2026-10-22.md").write_bytes(b"# asks\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("has no DOCS91_2026_10_23", r.stdout)
        for f in list(DOCS) + list(SQL):
            self.assertNotIn(MARK, (self.t / f).read_text(encoding="utf-8"), "nothing written: " + f)

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
