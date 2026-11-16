# -*- coding: ascii -*-
"""DOCS114_2026_11_15: the genealogies' texts taught to the reader (VAMSA_G6A), the cut measured, the release and the
Ganita verified, the commands of a trial reading. The patch adds the register's section 27, STATE section 49 and the
RUNBOOK's commands once, replays on the copies from before it, and does nothing the second time. The register's section
says done or not for each ask, with what was measured, and has no placeholder; the RUNBOOK's commands are whole."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs114_2026_11_15.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS114_2026_11_15"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 114 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs114_2026_11_15.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs114_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 27 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 27. 15 Nov, evening"):].split("\n## 28. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("VAMSA_G6A_2026_11_15", "Done in full? Yes for G6a", "9,029 verses in 154 chapters", "b391f48",
                  "971 passages mended in place", "ap_273.001cd inside chapter 274", "about $8.26",
                  "nothing of G6 reaches the site", "Not verified: no verse of these works has been read by Claude yet",
                  "hv 816, ram1 299, ram2 31, matsya 1,024, bndp1 503, bndp2 2,080, brahma 937, linga1 649, kurma1 552, "
                  "garuda1 456, agni 290, markp 134, mbh1 629, vipc4 629"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 15 Nov \|", ln)]
        self.assertEqual(len(rows), 7, "the asks of 15 Nov, evening")
        nums = [int(x.replace(",", "")) for x in re.findall(r"(?:hv|ram1|ram2|matsya|bndp1|bndp2|brahma|linga1|kurma1|"
                                                            r"garuda1|agni|markp|mbh1|vipc4) ([\d,]+)[,.]", flat)][:14]
        self.assertEqual(sum(nums), 9029, "the works' verses add up")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_runbook_commands_are_whole(self):
        r = (REPO / "RUNBOOK.md").read_text(encoding="utf-8")
        sec = " ".join(r[r.index("## 15 Nov, evening: the genealogies' texts"):].split("\n## ", 1)[0].split())
        for k in ("python scripts\\patch_vamsa_g6a_2026_11_15.py --check", "python scripts\\vamsa_read.py --work g6 --verses",
                  "python scripts\\vamsa_read.py --work hv --chapters 9-10 --yes --max-usd 0.50",
                  "python scripts\\vamsa_read.py --work mbh1 --chapters 90 --yes --max-usd 0.50",
                  "python scripts\\vamsa_read.py --work hv --report", "COMMIT_MSG_vamsag6a_20261115.txt"):
            self.assertIn(k, sec, k)
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")


if __name__ == "__main__":
    unittest.main()
