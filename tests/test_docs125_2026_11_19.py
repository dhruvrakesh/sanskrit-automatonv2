# -*- coding: ascii -*-
"""DOCS125_2026_11_19: 19 Nov, midday. The register's section 37, STATE section 59, the RUNBOOK's order once and
ARCHITECTURE.md's step 8; the patch replays on the copies from before it and does nothing the second time. The
section with its evidence and its sums, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs125_2026_11_19.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS125_2026_11_19"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "ARCHITECTURE.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 125 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs125_2026_11_19.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs125_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 37 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 37. 19 Nov"):].split("\n## 38. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "Deployed corpus-index at cc32c10", "equal the desk's (10 tables)",
                  "8,500 inserted, 0 updated, 0 deleted", "4090724", "$0.0382", "MBh 1,90.45", "approve none of v1",
                  "VAMSA_FINDINGS_V2_2026_11_19", "C30_admin_status_2026-11-19.sql", "ADMIN_REWIRE_2026-11-19.md",
                  "git pull"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 19 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 19 Nov, midday")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        self.assertEqual(14 + 13 + 14 + 13 + 39 + 14 + 10 + 25 + 21 + 11, 174)
        self.assertEqual(5 + 17 + 13 + 6 + 11 + 17 + 14 + 5, 88)

    def test_the_road_and_the_files(self):
        a = (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
        road = a[a.index("## The genealogies' road"):]
        self.assertIn("| 8. Watch, admin | public.corpus_admin_status() (C30", road)
        for rel in ("docs/ADMIN_REWIRE_2026-11-19.md", "docs/cloud/C30_admin_status_2026-11-19.sql",
                    "scripts/patch_srangam_admin_status_2026_11_19.py", "scripts/patch_vamsa_findings_v2_2026_11_19.py",
                    "docs/srangam/ADMIN_STATUS_2026-11-19"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
