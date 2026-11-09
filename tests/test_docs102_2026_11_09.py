# -*- coding: ascii -*-
"""DOCS102_2026_11_09: the asks of 9 Nov recorded. The patch adds the register's section 15, STATE section 37 and the
RUNBOOK's commands once (refusing before the day's files: the STORY_QUALITY and LOAD_CARDS patchers, the page and
C25), replays on the copies from before it, and does nothing the second time. The register's section says done or not
for each ask, names the credit's grants and the load measured, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs102_2026_11_09.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
PAGE = REPO / "docs" / "LOAD_AND_STORIES_2026-11-09.md"
MARK = "DOCS102_2026_11_09"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")
REQUIRES = ("scripts/patch_story_quality_2026_11_09.py", "scripts/patch_srangam_load_cards_2026_11_09.py",
            "docs/LOAD_AND_STORIES_2026-11-09.md", "docs/cloud/C25_article_cards_2026-11-09.sql")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS103_...) in the file."""
    return any(int(n) > 102 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs102_2026_11_09.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs102_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            self.assertIn("REFUSE", run("--check").stdout, "the day's files come first")
            for rel in REQUIRES:
                if not (REPO / rel).exists():
                    self.skipTest("%s is not here" % rel)
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
                if MARK.encode() in now and not newer(now):
                    self.assertEqual(got, now, rel)
            self.assertIn("Nothing to do", run().stdout)


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 15 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 15. 9 Nov"):]
        sec = sec.split("\n## 16. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "STORY_QUALITY", "LOAD_CARDS", "3,091 KB", "2,329 KB", "$10.57 to 11 Nov",
                  "$200 to 11 Dec", "6,062 claims", "374 groups equal", "dashboard-job"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 9 Nov", ln)]
        self.assertEqual(len(rows), 7, "the asks of 9 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


@unittest.skipUnless(PAGE.exists(), "the page is not here")
class ThePage(unittest.TestCase):
    def test_the_page(self):
        s = " ".join(PAGE.read_text(encoding="utf-8").split())
        self.assertTrue(PAGE.read_bytes().isascii())
        for k in (MARK, "LOAD_CARDS_2026_11_09", "STORY_QUALITY_2026_11_09", "written by Claude",
                  "SA_CLAUDE_CREDIT_USD=200", "SA_CLAUDE_CREDIT_EXPIRES=2026-12-11", "MT_ENGINE stays gemini",
                  "nothing is published until a person approves it"):
            self.assertIn(k, s, k)


if __name__ == "__main__":
    unittest.main()
