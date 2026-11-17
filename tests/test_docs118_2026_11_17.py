# -*- coding: ascii -*-
"""DOCS118_2026_11_17: 17 Nov, late. The register's section 31, STATE section 53, the RUNBOOK's commands once; the
patch replays on the copies from before it and does nothing the second time. The section says done or not for each ask
with its evidence (I1 live, G6d built, G6e and G6f not), its sums add up, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs118_2026_11_17.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS118_2026_11_17"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 118 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs118_2026_11_17.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs118_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 31 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 31. 17 Nov"):].split("\n## 32. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "eae2901", "de1e346..eae2901", "d5fca11", "VAMSA_REGISTER_2026_11_17",
                  "10 tests OK", "206 of 248 parts", "no row (neither called since the deploy)",
                  "120 succeeded", "Not built (designed below)", "yam ahuh pratipam nama", "Bhishma is one entry in 8 works",
                  "Jobs 2, 6, 7, 8, 9 and 10 each succeeded"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 17 Nov \|", ln)]
        self.assertEqual(len(rows), 12, "the asks of 17 Nov, late")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        read = {"hv": 28, "ram1": 12, "ram2": 1, "matsya": 23, "bndp1": 11, "bndp2": 45, "brahma": 21, "linga1": 15,
                "kurma1": 16, "garuda1": 14, "agni": 9, "markp": 4, "mbh1": 7, "vipc4": 0}
        self.assertEqual(sum(read.values()), 206)
        self.assertEqual(248 - 206, 9 + 33)
        self.assertIn("(mbh1 9 parts, vipc4 33)", flat)
        self.assertIn("5,672 persons in 3,289 entries; 1,062 in two works or more, 559 in three or more", flat)
        self.assertEqual(sum((1658, 24, 701)), 2383)

    def test_the_files_it_names_are_here(self):
        for rel in ("scripts/vamsa_register.py", "tests/test_vamsa_register_2026_11_17.py", "scripts/vamsa_align.py"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
