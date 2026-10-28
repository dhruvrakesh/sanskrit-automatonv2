# -*- coding: ascii -*-
"""DOCS98_2026_10_28: B2 and X1c recorded. The patch adds STATE section 33, the RUNBOOK's steps and README's line once
(refusing before the B2 index_sync.py, docs_map.py and docs/B2_AND_X1C_2026-10-28.md), replays on the copies from
before it to the files as they are, and does nothing the second time; the account names what it says it does (the
two decisions, the rights, the order of the pastes, the rollback) and never a placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs98_2026_10_28.py"
DOC = REPO / "docs" / "B2_AND_X1C_2026-10-28.md"
MARK = "DOCS98_2026_10_28"
FILES = ("docs/STATE_2026-10-18.md", "RUNBOOK.md", "README.md")
REQUIRES = ("docs/B2_AND_X1C_2026-10-28.md", "scripts/docs_map.py", "scripts/index_sync.py")


@unittest.skipUnless(PAT.exists(), "patch_docs98_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs98_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            self.assertIn("REFUSE", run("--check").stdout, "the B2 files come first")
            for rel in REQUIRES:
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes((REPO / rel).read_bytes())
            r = run("--check")
            self.assertIn("CHECK OK: 3 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                now = (REPO / rel).read_bytes()
                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_docs99_*"))   # DOCS99_2026_10_28 came after
                if later:
                    now = later[0].read_bytes()
                if MARK.encode() in now and b"DOCS99_2026_10_28" not in now:
                    self.assertEqual(got, now, rel)
            self.assertIn("Nothing to do", run().stdout)


@unittest.skipUnless(DOC.exists(), "the account is not here")
class TheAccount(unittest.TestCase):
    def test_says_what_it_does(self):
        s = DOC.read_text(encoding="utf-8")
        for k in ("B2_SITE_2026_10_28", "X1C_SITE_2026_10_28", MARK, "Hayasirsa", "Karanagama", "public domain",
                  "C23_index_claims_2026-10-28.sql", "C24_scholar_search_2026-10-28.sql", "## 9. Rollback",
                  "1,904 claims", "0 rows differ", "docs_map.py"):
            self.assertIn(k, s, k)
        self.assertIsNone(re.search(r"<[a-z_ ]+>", s.replace("<date>", "")), "no placeholder")


if __name__ == "__main__":
    unittest.main()
