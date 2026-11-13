# -*- coding: ascii -*-
"""DOCS110_2026_11_13: the best reading for each text (SOURCE_PICK), the Surya and the Ganita. The patch adds the
register's section 23, STATE section 45 and the RUNBOOK's commands once, replays on the copies from before it, and does nothing the second
time. The register's section says done or not for each ask, with what was measured, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs110_2026_11_13.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS110_2026_11_13"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 110 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs110_2026_11_13.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs110_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 23 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 23. 13 Nov, evening"):].split("\n## 24. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("SOURCE_PICK_2026_11_13", "415 passed, 94 flagged, 1 source doubt", "Bhaskara's Bijaganita",
                  "vision has read 112 of its 339 pages", "114 rows", "499 of 501", "text_path.pycls",
                  "$0.036 a verse", "A person confirms"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 13 Nov \|", ln)]
        self.assertEqual(len(rows), 8, "the asks of 13 Nov, evening")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


if __name__ == "__main__":
    unittest.main()
