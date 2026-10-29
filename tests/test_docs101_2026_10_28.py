# -*- coding: ascii -*-
"""DOCS101_2026_10_28: the asks read again on 28 Oct, night. The patch adds the register's section 14, STATE section
36 and the RUNBOOK's commands once, and bounds test_docs100's reading of section 13 at section 14 (refusing before the day's files: peoples_index.py, the ASK_ROOM and CLAIMS_PART2
patchers, the PEOPLES page and the night's checks), replays on the copies from before it, and does nothing the second
time. The register's section records the missing ask (Raychaudhuri carried forward, the tribes) as begun, not done,
keeps B. C. Law private, prices what is left against the cap, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs101_2026_10_28.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
PEO = REPO / "docs" / "PEOPLES_2026-10-28.md"
SQL = REPO / "docs" / "cloud" / "CHECKS_night_2026-10-28.sql"
MARK = "DOCS101_2026_10_28"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "tests/test_docs100_2026_10_28.py")
REQUIRES = ("scripts/peoples_index.py", "scripts/patch_ask_room_2026_10_28.py", "scripts/patch_claims_part2_2026_10_28.py",
            "docs/PEOPLES_2026-10-28.md", "docs/cloud/CHECKS_night_2026-10-28.sql")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS102_...) in the file."""
    return any(int(n) > 101 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs101_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs101_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            self.assertIn("REFUSE", run("--check").stdout, "the day's files come first")
            for rel in REQUIRES:
                if not (REPO / rel).exists():
                    self.skipTest("%s is not here" % rel)
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes((REPO / rel).read_bytes())
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 14 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 14. 28 Oct, night"):]
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "missing from this register", "It is now begun, not done", "B. C. Law",
                  "private reading", "PEOPLES", "ASK_ROOM", "3,068 of 3,072", "$22.56", "law-tribes", "vamsa-skeleton",
                  "CHECKS_night_2026-10-28.sql", "refuses until its Hindi is made"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| (\(recalled )?28 Oct", ln)]
        self.assertEqual(len(rows), 8, "the asks of 28 Oct, night")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


@unittest.skipUnless(PEO.exists() and SQL.exists(), "the PEOPLES page or the night's checks are not here")
class ThePages(unittest.TestCase):
    def test_the_peoples_page(self):
        s = PEO.read_text(encoding="utf-8")
        self.assertTrue(s.isascii())
        for k in ("PEOPLES_2026_10_28", "289 peoples", "agree on the region of 47 and differ on 3",
                  "copyright in India to the end of 2029", "Not read", "the tool infers nothing"):
            self.assertIn(k, " ".join(s.split()), k)

    def test_the_checks_are_read_only(self):
        q = SQL.read_text(encoding="utf-8")
        self.assertTrue(q.isascii())
        self.assertIn(MARK, q)
        body = "\n".join(ln for ln in q.splitlines() if not ln.lstrip().startswith("--"))
        self.assertEqual(body.count("SELECT"), 4)
        self.assertIsNone(re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|TRUNCATE)\b", body, re.I))


if __name__ == "__main__":
    unittest.main()
