# -*- coding: ascii -*-
"""DOCS99_2026_10_28: the corpus read again and the open texts weighed, recorded. The patch adds STATE section 34,
the RUNBOOK's steps and README's line once (refusing before the account, mend_marks.py and the day's three patchers),
replays on the copies from before it to the files as they are, and does nothing the second time; the account names
what it says it does (parity, the Hayasirsa, the Karanagama, the open texts, the four mends, the costs, the rollback)
and never a placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs99_2026_10_28.py"
DOC = REPO / "docs" / "REPAIR_AND_SOURCES_2026-10-28.md"
MARK = "DOCS99_2026_10_28"
FILES = ("docs/STATE_2026-10-18.md", "RUNBOOK.md", "README.md", "tests/test_docs98_2026_10_28.py")
REQUIRES = ("docs/REPAIR_AND_SOURCES_2026-10-28.md", "scripts/mend_marks.py", "scripts/patch_repair_partial_2026_10_28.py",
            "scripts/patch_rights_frontmatter_2026_10_28.py", "scripts/patch_vedic_lla_2026_10_28.py")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS100_...) in the file."""
    return any(int(n) > 99 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs99_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs99_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            self.assertIn("REFUSE", run("--check").stdout, "the account and the day's files come first")
            for rel in REQUIRES:
                if not (REPO / rel).exists():
                    self.skipTest("%s is not here" % rel)
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes((REPO / rel).read_bytes())
            r = run("--check")
            self.assertIn("CHECK OK: 4 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                now = (REPO / rel).read_bytes()
                if MARK.encode() in now and not newer(now):   # a later record changes the file again: not compared
                    self.assertEqual(got, now, rel)
            self.assertIn("Nothing to do", run().stdout)


@unittest.skipUnless(DOC.exists(), "the account is not here")
class TheAccount(unittest.TestCase):
    def test_says_what_it_does(self):
        s = " ".join(DOC.read_text(encoding="utf-8").split())
        for k in (MARK, "REPAIR_PARTIAL_2026_10_28", "RIGHTS_FRONTMATTER_2026_10_28", "INLINE_MARKS_2026_10_28",
                  "VEDIC_LLA_2026_10_28", "368 groups equal", "Hayasirsa", "Karanagama", "854 numbers",
                  "667 scholarly rows", "41 respelled", "Muktabodha", "CC BY-NC-SA 4.0", "## 10. Rollback",
                  "mend_marks.py --doc HAYASHIRSHA_PANCARATRA --apply", "docs_map.py --write"):
            self.assertIn(k, s, k)
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", s), "no placeholder")


if __name__ == "__main__":
    unittest.main()
