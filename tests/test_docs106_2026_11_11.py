# -*- coding: ascii -*-
"""DOCS106_2026_11_11: the tests apart from this PC; G5a; our findings may be published. The patch adds the register's
section 19, STATE section 41 and the RUNBOOK's commands once, replays on the copies from before it, and does nothing the
second time. The register's section says done or not for each ask, with what was measured; the findings' page writes
the rule (Law's book private, our cited findings publishable after a person's reading) and is ASCII; C27 says its REVOKE
cannot work and adds S3, read-only."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs106_2026_11_11.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
PAGE = REPO / "docs" / "PEOPLES_FINDINGS_2026-11-11.md"
C27 = REPO / "docs" / "cloud" / "C27_spatial_ref_sys_2026-11-11.sql"
MARK = "DOCS106_2026_11_11"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 106 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs106_2026_11_11.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs106_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 19 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 19. 11 Nov, later"):].split("\n## 20. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("ANTHROPIC_API_KEY2", "$200 from 9 Nov until 11 Dec", "16:17 (89 texts)", "4,422 passages",
                  "235 modules, 1,752 tests", "supabase_admin", "Never DROP EXTENSION postgis CASCADE",
                  "PEOPLES_FINDINGS_2026-11-11.md", "eight words", "2,349 verses", "about $1.82"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 11 Nov \|", ln)]
        self.assertEqual(len(rows), 7, "the asks of 11 Nov, later")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


class ThePages(unittest.TestCase):
    @unittest.skipUnless(PAGE.exists(), "the findings' page is not here")
    def test_the_findings_rule(self):
        b = PAGE.read_bytes()
        self.assertTrue(b.isascii())
        s = " ".join(b.decode("ascii").split())
        for k in ("to the end of 2029", "public domain in India since 2018", "once a person has read and approved it",
                  "no run of eight words", "R1: planned, priced, not built", "CC BY-NC-SA 4.0", "VAMSA_READ_2026_11_11"):
            self.assertIn(k, s, k)

    @unittest.skipUnless(C27.exists(), "C27 is not here")
    def test_c27_says_the_revoke_cannot_work(self):
        s = C27.read_text(encoding="ascii")
        self.assertIn("did nothing and needs no undo", s)
        self.assertIn("S3 (read-only", s)
        code = "\n".join(ln for ln in s.splitlines() if not ln.lstrip().startswith("--"))
        self.assertEqual(re.findall(r"(?im)^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|TRUNCATE|REVOKE)\b", code),
                         ["REVOKE"])


if __name__ == "__main__":
    unittest.main()
