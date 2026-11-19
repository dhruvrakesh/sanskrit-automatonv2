# -*- coding: ascii -*-
"""DOCS123_2026_11_18: 18 Nov, late night. The register's section 35, STATE section 57, the RUNBOOK's order once and
ARCHITECTURE.md's road with the vamsas; the patch replays on the copies from before it and does nothing the second time.
The section with its evidence, the credit's plan and its sums, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs123_2026_11_18.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS123_2026_11_18"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "ARCHITECTURE.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 123 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs123_2026_11_18.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs123_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 35 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 35. 18 Nov"):].split("\n## 36. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "97b9fa21", "CorpusDynasties-D2CZ5603.js", "17 works, 517 rows",
                  "corpus.readers 0 rows", "/admin/researchers", "28 calls, all gemini-2.5-flash", "only 65 hold a founder",
                  "VAMSA_WAYIN_2026_11_18", "C29_index_vamsas_2026-11-18.sql", "134 of 174 generations",
                  "in copyright (to the end of 2029)", "PGlite (PostgreSQL 17.5)", "$70.22 left", "claude_engine.py --credit"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 18 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 18 Nov, late night")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        self.assertEqual(500 - 65, 435)
        self.assertEqual(40 + 119, 159)
        self.assertEqual(1004 - 177, 827)
        lo, hi = 1 + 38 + 11, 3 + 38 + 21
        self.assertTrue(70.22 - hi >= 8 and 70.22 - lo <= 20.5, (70.22 - hi, 70.22 - lo))

    def test_the_road_and_the_files(self):
        a = (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
        road = a[a.index("## The genealogies' road"):]
        for k in ("6. Show, site, by vamsa", "public.corpus_reader_index_vamsas(p_key)", "corpus.index_vamsas, C29",
                  "aligned.json is written by vamsa_align.py", "B. C. Law's book (in copyright) never"):
            self.assertIn(k, road, k)
        self.assertNotIn("a dynasty and vamsa on each line", road)
        for rel in ("docs/cloud/C29_index_vamsas_2026-11-18.sql", "scripts/patch_vamsa_wayin_2026_11_18.py",
                    "scripts/patch_srangam_vamsa_wayin_2026_11_18.py", "docs/srangam/VAMSA_WAYIN_2026-11-18"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
