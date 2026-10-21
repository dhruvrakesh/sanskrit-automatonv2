# -*- coding: ascii -*-
"""DOCS81_2026_10_21: the rest of the night of 21 Oct recorded (PLATFORM 84, RUNBOOK, ENTERPRISE_PATH 71, STATE 16, the
brain page's section 7) and the brain page's table corrected (the site's live passages, not all of ours); the patcher
writes once, after DOCS80, all or nothing; the checks it names are read-only. Temp folders only."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs81_2026_10_21.py"
SQL = REPO / "docs" / "cloud" / "CHECKS_brain_counts_2026-10-21.sql"
MARK = "DOCS81_2026_10_21"
BRAIN = ("DOCS80_2026_10_21\n| Passages | 174,019 | mirrored (row hashes, digests) | the reader (C5, C17) |\n"
         "| Scholarly English | `scholar_translations` 5,569 rows | mirrored as `en-x-scholar` rows | the reader |\n"
         "| Names | `entity_mentions` 41,059 | `corpus.entities`, `corpus.mentions` | the chips |\n"
         "| Meaning | `passage_embeddings` 26,345 | `corpus.passage_vectors` | search |\n"
         "| The shelf, step 2 | data/shelf/claims.db: 1,703 claims of 83 pages (1,963 of 95 once `--reparse` is run) | not "
         "mirrored | no |\n"
         "input by John Robert Gardner (GRETIL's general\n  terms apply). Ours is book 14 only.\n")
BODY = {
    "docs/STATE_2026-10-18.md": "DOCS80_2026_10_21\n## 15. x\n",
    "docs/ENTERPRISE_PATH_2026-10-04.md": "DOCS80_2026_10_21\n## Addendum (70)\n",
    "docs/PLATFORM_2026-10-04.md": "DOCS80_2026_10_21\n## 83. x\n",
    "RUNBOOK.md": "DOCS80_2026_10_21\r\nline\r\n",
    "docs/BRAIN_PATH_2026-10-21.md": BRAIN,
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

    def test_it_writes_once_after_docs80(self):
        self.assertIn("CHECK OK: 5 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in BODY:
            self.assertIn(MARK, (self.t / f).read_text(encoding="utf-8"), f)
        bp = (self.t / "docs/BRAIN_PATH_2026-10-21.md").read_text(encoding="utf-8")
        self.assertNotIn("| 174,019 | mirrored", bp)
        self.assertIn("99,966 live", bp)
        self.assertIn("`corpus.mentions` 40,054", bp)
        self.assertIn("rows, 1,671 live", bp)
        self.assertIn("Part I complete, 2,010 claims of 99 pages", bp)
        self.assertIn("John Robert Gardner", bp, "the DOCS80 test still finds its credit")
        self.assertIn("H. S. Ananthanarayana", bp)
        self.assertIn("## 7. B1 done", bp)
        rb = (self.t / "RUNBOOK.md").read_bytes()
        self.assertNotIn(b"\n", rb.replace(b"\r\n", b""), "the RUNBOOK keeps its CRLF")
        self.assertIn(b'$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"', rb)
        self.assertIn(b"python scripts\\scholar_claims.py --link", rb)
        self.assertIn("## 16. 21 Oct, late night", (self.t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
        self.assertIn("## 84. The claims tied", (self.t / "docs/PLATFORM_2026-10-04.md").read_text(encoding="utf-8"))
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_all_or_nothing(self):
        (self.t / "docs/BRAIN_PATH_2026-10-21.md").write_text("DOCS80_2026_10_21\nno table here\n", encoding="utf-8")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("anchor 1 found 0 times", r.stdout)
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
        self.assertEqual(body.count(";"), 4, "four blocks, B1 to B4")


if __name__ == "__main__":
    unittest.main()
