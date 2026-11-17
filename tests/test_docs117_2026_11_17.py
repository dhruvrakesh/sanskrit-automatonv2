# -*- coding: ascii -*-
"""DOCS117_2026_11_17: 17 Nov, night. The register's section 30, STATE section 52, the RUNBOOK's commands once; the
patch replays on the copies from before it and does nothing the second time. The section says done or not for each ask
with its evidence (G6c and I1 built, G6d not), its sums add up, no placeholder; the files it names are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs117_2026_11_17.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS117_2026_11_17"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 117 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs117_2026_11_17.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs117_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 30 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 30. 17 Nov"):].split("\n## 31. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "VAMSA_ALIGN_2026_11_17", "AI_GATEWAY_OFF_2026-11-17", "17 tests OK",
                  "6 tests OK", "Not built (designed below)", "aiExtractCitations", "invariant 69", "$93.80 left",
                  "de1e346", "154 of 248 parts", "Not run here: npm run typecheck, vitest, build"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 17 Nov \|", ln)]
        self.assertEqual(len(rows), 12, "the asks of 17 Nov, night")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        gens = {"solar": 14, "lunar": 5, "yadu": 13, "haihaya": 12, "kroshtu": 6, "turvasu": 10, "druhyu": 10,
                "puru": 29, "kuru": 21, "magadha": 11}
        self.assertEqual((len(gens), sum(gens.values())), (10, 131))
        self.assertEqual(55 + 15 + 47 + 14, 131)
        self.assertIn("10 dynasties in two works or more; of their 131 generations 55 agree, 15 most, 47 differ, 14 in"
                      " one work only", flat)
        read = {"hv": 28, "ram1": 12, "ram2": 1, "matsya": 23, "bndp1": 11, "bndp2": 45, "brahma": 21, "linga1": 11,
                "mbh1": 2}
        left = {"linga1": 4, "kurma1": 16, "garuda1": 14, "agni": 9, "markp": 4, "mbh1": 14, "vipc4": 33}
        self.assertEqual(sum(read.values()), 154)
        self.assertEqual(sum(left.values()), 94)
        self.assertEqual(154 + 94, 248)
        self.assertIn("vipc4 33 parts (94)", flat)

    def test_the_files_it_names_are_here(self):
        for rel in ("scripts/vamsa_align.py", "tests/test_vamsa_align_2026_11_17.py",
                    "scripts/patch_srangam_ai_gateway_off_2026_11_17.py",
                    "tests/test_srangam_ai_gateway_off_2026_11_17.py",
                    "docs/srangam/AI_GATEWAY_OFF_2026-11-17/supabase/functions/detect-duplicate-articles/index.ts",
                    "docs/srangam/AI_GATEWAY_OFF_2026-11-17/supabase/functions/suggest-tag-categories/index.ts",
                    "docs/srangam/AI_GATEWAY_OFF_2026-11-17/src/__tests__/ai-gateway-off.test.ts",
                    "docs/srangam/AI_GATEWAY_OFF_2026-11-17/_append/RELIABILITY_AUDIT.phaseAS.md"):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
