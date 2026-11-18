# -*- coding: ascii -*-
"""DOCS121_2026_11_18: 18 Nov, evening. The register's section 33, STATE section 55, the RUNBOOK's commands once; the
patch replays on the copies from before it and does nothing the second time. The section says done or not for each ask
with its evidence (P2b and the task's last step built), its sums add up, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs121_2026_11_18.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS121_2026_11_18"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 121 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs121_2026_11_18.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs121_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 33 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 33. 18 Nov"):].split("\n## 34. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "ded5ed51", "DYNASTIES_WORKS_2026-11-18", "patch_index_task_every_2026_11_18.py",
                  "6 tests OK", "3 tests OK", "$70.22 left", "loadDynasties(work)", "invariant 70",
                  "Apply only after Publish", "dynasties 517 (0.9 MB), 5,565,024 bytes", "not this project's",
                  "still no row for detect-duplicate-articles"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 18 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 18 Nov, evening")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        self.assertEqual(round(173.93 - 103.71, 2), 70.22)
        self.assertEqual(round(68.1638 - 49.3047, 2), 18.86)
        self.assertEqual(round(70.22 / (18.86 / 5)), 19)
        self.assertIn("about 19 hours", flat)

    def test_the_files_it_names_are_here(self):
        for rel in ("scripts/patch_srangam_dynasties_works_2026_11_18.py", "tests/test_srangam_dynasties_works_2026_11_18.py",
                    "scripts/patch_index_task_every_2026_11_18.py", "tests/test_index_task_every_2026_11_18.py",
                    "docs/srangam/DYNASTIES_WORKS_2026-11-18/src/pages/corpus/CorpusDynasties.tsx"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
