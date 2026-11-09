# -*- coding: ascii -*-
"""DOCS103_2026_11_09: the cards live and measured again; the Claude credit's first runs. The patch adds the register's
section 16, STATE section 38, the page's section 7 and the RUNBOOK's commands once, replays on the copies from before
it, and does nothing the second time. The register's section says done or not for each ask, gives the measurement
before and after, the credit's runs as measured, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs103_2026_11_09.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
PAGE = REPO / "docs" / "LOAD_AND_STORIES_2026-11-09.md"
MARK = "DOCS103_2026_11_09"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "docs/LOAD_AND_STORIES_2026-11-09.md")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS104_...) in the file."""
    return any(int(n) > 103 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs103_2026_11_09.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs103_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 4 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                now = (REPO / rel).read_bytes()
                if MARK.encode() in now and not newer(now):
                    self.assertEqual(got, now, rel)
            self.assertIn("Nothing to do", run().stdout)


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 16 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 16. 9 Nov, later"):].split("\n## 17. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "3,091 KB to 778 KB", "2,504 to 1,072 ms", "$0.024 a story",
                  "$0.0055 a passage", "git push", "about $142"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 9 Nov, later", ln)]
        self.assertEqual(len(rows), 5, "the asks of 9 Nov, later")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_page(self):
        s = " ".join(PAGE.read_text(encoding="utf-8").split())
        self.assertIn("## 7. After Publish", s)
        self.assertIn("| / transferred | 3,091 KB | 778 KB |", s)
        self.assertTrue(PAGE.read_bytes().isascii())


if __name__ == "__main__":
    unittest.main()
