# -*- coding: ascii -*-
"""DOCS115_2026_11_16: the trial read, what failed on 15 Nov, Sonnet's next work, the desk and the site rationalised.
The patch adds the register's section 28, STATE section 50 and the RUNBOOK's commands once, replays on the copies from
before it, and does nothing the second time. The register's section says done or not for each ask, with what was
measured; its sums add up; the RUNBOOK's commands are whole; no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs115_2026_11_16.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS115_2026_11_16"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 115 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs115_2026_11_16.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs115_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 28 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 28. 16 Nov"):].split("\n## 29. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "VAMSA_G6B_READY_2026_11_16", "CLAUDE_KEY_FRESH_2026_11_16", "952 empty answers",
                  "401 invalid x-api-key", "nothing billed", "175 statements (151 verified", "181 (173, 7, 1, 0)",
                  "108 statements become verified", "$128.92", "11 Dec", "UGG6uRRMsfqBSk1pCgLQo2",
                  "detect-duplicate-articles", "suggest-tag-categories", "process 40108"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 16 Nov \|", ln)]
        self.assertEqual(len(rows), 9, "the asks of 16 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        self.assertEqual(88, 30 + 57 + 1)
        self.assertIn("G5a 88: vip4 30, bhp9 57, bhp12 1; hv 14; mbh1 6", flat)
        self.assertEqual(88 + 14 + 6, 108)
        lo = 0.34 + 9 + 6 + 6 + 3 + 38
        hi = 0.34 + 15 + 20 + 6 + 8 + 38
        self.assertEqual((round(lo), round(hi)), (62, 87))
        self.assertIn("In all about $62 to $87; $42 to $67 would be left", flat)
        self.assertEqual((round(128.92 - hi), round(128.92 - lo)), (42, 67))
        self.assertEqual(1004 - 177, 827)
        self.assertEqual(2315 - 1352, 963)

    def test_the_runbook_commands_are_whole(self):
        r = (REPO / "RUNBOOK.md").read_text(encoding="utf-8")
        sec = " ".join(r[r.index("## 16 Nov: the Claude key read fresh"):].split("\n## ", 1)[0].split())
        for k in ("python scripts\\patch_claude_key_fresh_2026_11_16.py --check", "restart_dashboard.ps1 -Status",
                  "python scripts\\claude_engine.py --probe", "python scripts\\vamsa_read.py --work g6 --reparse",
                  "python scripts\\vamsa_read.py --work hv --chapters 9-10 --yes --max-usd 0.50",
                  "python scripts\\vamsa_read.py --work g6 --yes --max-usd 15", "COMMIT_MSG_g6bready_20261116.txt",
                  "Get-Process -Id 40108"):
            self.assertIn(k, sec, k)
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")


if __name__ == "__main__":
    unittest.main()
