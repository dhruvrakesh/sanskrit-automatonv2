# -*- coding: ascii -*-
"""DOCS122_2026_11_18: 18 Nov, night. The register's section 34, STATE section 56, the RUNBOOK's commands once and
ARCHITECTURE.md's road; the patch replays on the copies from before it and does nothing the second time. The section
with its evidence (P2b and the task's last step built), its sums add up, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs122_2026_11_18.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS122_2026_11_18"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "ARCHITECTURE.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 122 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs122_2026_11_18.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs122_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 34 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 34. 18 Nov"):].split("\n## 35. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "d7c6eda9", "72e109b", "sent 412 row(s) (412 changed), deleted 0",
                  "17 works, 517 rows", "mode readers, since 2026-10-09", "CorpusDynasties-D2CZ5603.js", "srangam_ai_usage",
                  "still no row for detect-duplicate-articles", "The genealogies' road"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 18 Nov \|", ln)]
        self.assertEqual(len(rows), 10, "the asks of 18 Nov, night")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        rows = {"agni": 41, "bhp12": 8, "bhp9": 48, "bndp1": 7, "bndp2": 58, "brahma": 40, "garuda1": 48, "hv": 49,
                "kurma1": 33, "linga1": 18, "markp": 6, "matsya": 39, "mbh1": 13, "ram1": 8, "ram2": 3, "vip4": 50,
                "vipc4": 48}
        self.assertEqual((len(rows), sum(rows.values())), (17, 517))
        self.assertEqual(517 - 106, 411)

    def test_the_road(self):
        a = (REPO / "ARCHITECTURE.md").read_text(encoding="utf-8")
        if MARK not in a:
            self.skipTest("the patch is not applied here")
        road = a[a.index("## The genealogies' road"):]
        for k in ("scripts\\vamsa_read.py", "scripts\\vamsa_align.py", "scripts\\vamsa_register.py",
                  "scripts\\vamsa_join.py", "scripts\\index_sync.py --dynasty-works every", "corpus_mirror_task.ps1",
                  "corpus.index_dynasties", "corpus_reader_allowed()", "Only the first step spends"):
            self.assertIn(k, road, k)


if __name__ == "__main__":
    unittest.main()
