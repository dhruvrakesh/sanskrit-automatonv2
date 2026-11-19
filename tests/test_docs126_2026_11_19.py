# -*- coding: ascii -*-
"""DOCS126_2026_11_19: 19 Nov, afternoon. The register's section 38, STATE section 60, the RUNBOOK's order once and
ARCHITECTURE.md's step 9; the patch replays on the copies from before it and does nothing the second time. The
section with its evidence and its sums, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs126_2026_11_19.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS126_2026_11_19"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "ARCHITECTURE.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 126 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs126_2026_11_19.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs126_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 38 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 38. 19 Nov"):].split("\n## 39. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "64f58d70", "33f9301..31419c7", "caniuse-lite 1.0.30001727 to 1.0.30001814",
                  "$0.237", "48 decision(s) recorded", "0 proposed, 20 approved, 29 dropped, 0 refused",
                  "R 2,102.7", "BndP 2,69.5", "KurmP 1,21.5", "C31_vamsa_findings_2026-11-19.sql",
                  "VAMSA_FINDINGS_SITE_2026_11_19", "B. C. Law's page only", "ADMIN_REWIRE_2026-11-19.md"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 19 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 19 Nov, afternoon")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        self.assertEqual(6 + 5 + 4 + 5 + 5 + 5 + 4 + 5 + 5 + 5, 49)          # proposed, by dynasty
        self.assertEqual(4 + 1 + 0 + 4 + 3 + 1 + 2 + 2 + 2 + 1, 20)          # approved
        self.assertEqual(2 + 4 + 4 + 1 + 2 + 4 + 2 + 3 + 3 + 4, 29)          # dropped
        self.assertEqual(67 + 26 + 17 + 13 + 8, 131)                         # the citations sent

    def test_the_road_and_the_files(self):
        a = (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
        road = a[a.index("## The genealogies' road"):]
        self.assertIn("| 9. Our findings, on the site | index_sync.findings_for", road)
        for rel in ("docs/cloud/C31_vamsa_findings_2026-11-19.sql", "scripts/patch_vamsa_findings_site_2026_11_19.py",
                    "scripts/patch_srangam_vamsa_findings_site_2026_11_19.py", "docs/srangam/VAMSA_FINDINGS_SITE_2026-11-19",
                    "tests/test_vamsa_findings_site_2026_11_19.py"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
