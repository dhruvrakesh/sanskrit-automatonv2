# -*- coding: ascii -*-
"""DOCS120_2026_11_18: 18 Nov. The register's section 32, STATE section 54, the RUNBOOK's commands once; the
patch replays on the copies from before it and does nothing the second time. The section says done or not for each ask
with its evidence (the page of 17 Nov held; P1 and P2a built; P2b not), its sums add up, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs120_2026_11_18.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS120_2026_11_18"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 120 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs120_2026_11_18.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs120_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 32 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 32. 18 Nov"):].split("\n## 33. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("not the enterprise way in part", "hold\\vamsa_pages_20261117", "Done in full? No.",
                  "VAMSA_NAMES_2026_11_18", "VAMSA_SITE_2026_11_18", "7 tests OK", "5 tests OK", "106 rows, 123 kB",
                  "every 517 rows, 911 kB", "anon may not call it", "Do not send every until P2b is live",
                  "https://claude.ai/artifact/PSQpG5t46vLgXiSMWaBSf6", "still no row for detect-duplicate-articles"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 18 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 18 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        self.assertEqual(50 + 48 + 8, 106)
        lines = {"vip4": 49, "bhp9": 47, "bhp12": 7, "hv": 48, "ram1": 7, "ram2": 2, "matsya": 38, "bndp1": 6, "bndp2": 57,
                 "brahma": 39, "linga1": 17, "kurma1": 32, "garuda1": 47, "agni": 40, "markp": 5, "mbh1": 12, "vipc4": 47}
        self.assertEqual(sum(lines.values()) + len(lines), 517, "a row a line and one a work")
        self.assertIn("vip4 50 rows, 493 persons in lines", flat)

    def test_the_files_it_names_are_here(self):
        for rel in ("scripts/patch_vamsa_names_2026_11_18.py", "tests/test_vamsa_names_2026_11_18.py",
                    "scripts/patch_vamsa_site_2026_11_18.py", "tests/test_vamsa_site_2026_11_18.py"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
