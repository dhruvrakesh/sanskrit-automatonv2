# -*- coding: ascii -*-
"""DOCS91_2026_10_23: 23 Oct recorded (DEBT section 12, STATE 26, RUNBOOK, PLATFORM 94, ENTERPRISE_PATH 81, ASKS 8,
RELATIONS_AND_ASK 6); the patcher writes once, after DOCS90, all or nothing, and only where what it records is. Temp
folders only."""
import datetime, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs91_2026_10_23.py"
MARK = "DOCS91_2026_10_23"
DOCS = {
    "docs/DEBT_2026-10-22.md": "# debt\n## 11. x (DOCS90_2026_10_22)\n",
    "docs/STATE_2026-10-18.md": "DOCS90_2026_10_22\n## 25. x\n",
    "RUNBOOK.md": "DOCS90_2026_10_22\r\nline\r\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS90_2026_10_22\n## 93. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS90_2026_10_22\n## Addendum (80)\n",
    "docs/ASKS_2026-10-22.md": "# asks (DOCS90_2026_10_22)\n## 7. x\n",
    "docs/RELATIONS_AND_ASK_2026-10-22.md": "# page (DOCS90_2026_10_22)\n## 5. x\n",
}
CODE = {
    "scripts/kin_index.py": "# RELATIONS_INDEX_2026_10_23\n",
    "scripts/health_watch.py": "# HEALTH_2026_10_23\n",
    "scripts/patch_ask_prof_2026_10_23.py": "# ASK_PROF_2026_10_23\n",
    "scripts/patch_links_sched_2026_10_23.py": "# ENTITY_LINKS_SCHED_2026_10_23\n",
    "scripts/patch_health_2026_10_23.py": "# HEALTH_2026_10_23\n",
    "scripts/patch_srangam_name_links_2026_10_23.py": "# NAME_LINKS_SITE_2026_10_23\n",
    "docs/cloud/C19_health_mail_2026-10-23.sql": "-- HEALTH_MAIL_C19_2026_10_23\n",
    "docs/cloud/C20_name_links_2026-10-23.sql": "-- NAME_LINKS_C20_2026_10_23\n",
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

    def test_it_writes_once_after_docs90(self):
        self.assertIn("CHECK OK: 7 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stamp = datetime.date.today().strftime("%Y%m%d")
        for f in DOCS:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
            self.assertTrue((self.t / f).with_name(Path(f).name + ".bak_docs91_" + stamp).exists(), "backup: " + f)
        d = (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8")
        for x in ("## 12. 23 Oct", "553b2160", "45,183 pairs", "context_pre_links_20261023_053008.db", "Narasimha 2.56",
                  "3.85 own misreadings", "Yajnavalkya (no vision page", "Maharishi University of Management",
                  "until 1 January 2029", "CC BY-NC-SA 3.0 notice", "Purana Index 7,075", "never to speak as any real",
                  "150 GB"):
            self.assertIn(x, d, x)
        self.assertNotIn("\\\\", d, "single backslashes in the paths")
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        for x in (b"kin_index.py --yes", b"C19_health_mail_2026-10-23.sql", b"C20_name_links_2026-10-23.sql",
                  b"patch_srangam_name_links_2026_10_23.py", b"--doc nirukta__w_gretil", b"--limit 20",
                  b"--doc Daivat-Sanhita --withdraw", b"smriti_06yagyavalkya_smriti"):
            self.assertIn(x, rb, x)
        ep = (self.t / "docs/ENTERPRISE_PATH_2026-10-04.md").read_text(encoding="utf-8")
        for k in ("relations-index", "ask-v2", "links-sched", "alerts", "names-ui", "nirukta-source", "h2",
                  "daivat-rights", "ask-site", "claims-mirror"):
            self.assertIn("| %s |" % k, ep, k)
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_without_what_it_records(self):
        (self.t / "scripts/kin_index.py").unlink()
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("kin_index.py does not carry", r.stdout)
        self.assertNotIn(MARK, (self.t / "docs/DEBT_2026-10-22.md").read_text(encoding="utf-8"))

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
