# -*- coding: ascii -*-
"""DOCS105_2026_11_11: the desk said what was so a fortnight before; the credit's line; spatial_ref_sys. The patch adds
the register's section 18, STATE section 40 and the RUNBOOK's commands once, replays on the copies from before it, and
does nothing the second time. The register's section says done or not for each ask of 11 Nov, with what was measured,
and has no placeholder; C27 is ASCII, read-only but for its one REVOKE, and drops nothing."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs105_2026_11_11.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
C27 = REPO / "docs" / "cloud" / "C27_spatial_ref_sys_2026-11-11.sql"
MARK = "DOCS105_2026_11_11"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS106_...) in the file."""
    return any(int(n) > 105 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs105_2026_11_11.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs105_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 18 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 18. 11 Nov"):].split("\n## 19. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("written last on 28 Oct (17:48, 88 texts)", "507 pages current, 0 stale, 0 missing",
                  "page 422 Tesseract's", "--doc X --write", "Chart this text again (free)", "expires 2026-11-11",
                  "benchmark_sources.py --doc gandharva_veda_natya_shastra", "7,010 rows", "3,409 claims", "C27", "G5a",
                  "kin-long"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 11 Nov \|", ln)]
        self.assertEqual(len(rows), 7, "the asks of 11 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_files_it_names_are_here(self):
        for rel in ("scripts/patch_desk_fresh_2026_11_11.py", "scripts/text_path.py", "scripts/benchmark_sources.py",
                    "docs/cloud/C27_spatial_ref_sys_2026-11-11.sql"):
            self.assertTrue((REPO / rel).exists(), rel)


@unittest.skipUnless(C27.exists(), "C27 is not here")
class TheSQL(unittest.TestCase):
    def test_c27_reads_and_revokes_only(self):
        b = C27.read_bytes()
        self.assertTrue(b.isascii())
        code = "\n".join(ln for ln in b.decode("ascii").splitlines() if not ln.lstrip().startswith("--"))
        self.assertEqual(re.findall(r"(?im)^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|TRUNCATE|REVOKE)\b", code),
                         ["REVOKE"])
        self.assertIn("ON public.spatial_ref_sys FROM anon, authenticated;", code)
        self.assertIn("Do NOT run DROP EXTENSION postgis CASCADE", b.decode("ascii"))


if __name__ == "__main__":
    unittest.main()
