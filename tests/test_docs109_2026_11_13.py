# -*- coding: ascii -*-
"""DOCS109_2026_11_13: the page's first verses (BANNER_HEAD), Mallapurana's edition (DESK_SCHOLAR_NEXT), the
correction on corpus-index. The patch adds the register's section 22, STATE section 44 and the RUNBOOK's commands
once, replays on the copies from before it, and does nothing the second
time. The register's section says done or not for each ask, with what was measured, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs109_2026_11_13.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS109_2026_11_13"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 109 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs109_2026_11_13.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs109_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 22 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 22. 13 Nov"):].split("\n## 23. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("/desk/Mallapurana", "DESK_SCHOLAR_NEXT_2026_11_13", "BANNER_HEAD_2026_11_13", "1,924 passages of 21 texts",
                  "1,745 of them untranslated", "Publish does not deploy an edge function", "$0.026 to $0.045",
                  "No, not yet", "6d8aad4", "A3 false, true, false, false"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 13 Nov \|", ln)]
        self.assertEqual(len(rows), 8, "the asks of 13 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


if __name__ == "__main__":
    unittest.main()
