# -*- coding: ascii -*-
"""DOCS127_2026_11_20: 20 Nov, morning. The register's section 39, STATE section 61 and the RUNBOOK's order once;
the patch replays on the copies from before it and does nothing the second time. The section with its evidence and its
sums, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs127_2026_11_20.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS127_2026_11_20"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 127 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs127_2026_11_20.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs127_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 39 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 39. 20 Nov"):].split("\n## 40. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "sent 9 row(s) (9 changed)", "law_with_words 0 on every row", "d6da526", "808246d",
                  "$12.13 for 7,937 verses", "$161.36 of $162", "[BUDGET] Set to $167.00", "ENTITY_ALLOWANCE_2026_11_20",
                  "C30b_admin_status_static_2026-11-20.sql", "never \"Try to fix\" or \"Fix all\"",
                  "kept in memory", "pinned to the generations"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 20 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 20 Nov, morning")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        self.assertAlmostEqual(1.99 + 7.25 + 2.89, 12.13, places=2)          # entities, 17 to 19 Nov
        self.assertAlmostEqual(0.14 + 0.103, 0.24, places=2)                 # OCR
        self.assertAlmostEqual(0.07 + 0.05, 0.12, places=2)                  # embeddings
        self.assertEqual(4 + 1 + 0 + 4 + 3 + 1 + 2 + 2 + 2 + 1, 20)          # the findings on the site
        self.assertEqual(28 + 6 + 0 + 28 + 23 + 7 + 9 + 11 + 12 + 7, 131)    # their citations
        self.assertAlmostEqual(38.56 + 11.41, 49.97, places=2)               # the translations of 17 and 18 Nov

    def test_the_files(self):
        for rel in ("docs/cloud/C30b_admin_status_static_2026-11-20.sql", "scripts/patch_entity_allowance_2026_11_20.py",
                    "tests/test_entity_allowance_2026_11_20.py"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
