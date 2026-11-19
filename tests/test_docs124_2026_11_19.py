# -*- coding: ascii -*-
"""DOCS124_2026_11_19: 19 Nov. The register's section 36, STATE section 58, the RUNBOOK's order once and ARCHITECTURE.md's
road with step 7 (R1); the patch replays on the copies from before it and does nothing the second time. The section
with its evidence and its sums, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs124_2026_11_19.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS124_2026_11_19"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "ARCHITECTURE.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 124 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs124_2026_11_19.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs124_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 36 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 36. 19 Nov"):].split("\n## 37. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "31da6d5", "cc32c10", "CorpusVamsas-BYYDBSh0.js", "corpus-index does not take them yet",
                  "$70.22 left", "1 admin, 1 super admin, 3 researchers", "spatial_ref_sys", "Fix all",
                  "VAMSA_FINDINGS_2026_11_19", "about $0.67 in all", "226 pages", "C30"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 19 Nov \|", ln)]
        self.assertEqual(len(rows), 11, "the asks of 19 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        self.assertAlmostEqual(173.93 - 103.71, 70.22, places=2)
        self.assertAlmostEqual(68.16 + 19.90 + 11.19 + 4.45, 103.70, places=2)
        self.assertEqual(1 + 1 + 3, 5)

    def test_the_road_and_the_files(self):
        a = (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
        road = a[a.index("## The genealogies' road"):]
        for k in ("Only the first step spends", "| 7. Our findings (R1) |", "scripts\\vamsa_findings.py",
                  "exports\\vamsa_findings.md (the review page, not in git)", "the approved findings on the vamsa page (C30"):
            self.assertIn(k, road, k)
        self.assertNotIn("our findings on a dynasty (R1, with B. C. Law)", road)
        run = (REPO / "RUNBOOK.md").read_text(encoding="utf-8")
        sec = run[run.index("## 19 Nov: the vamsas sent"):]
        self.assertIsNone(re.search(r"kuru:N\b|<[a-z]+>", sec), "no placeholder in the commands")
        for rel in ("scripts/vamsa_findings.py", "tests/test_vamsa_findings_2026_11_19.py"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
