# -*- coding: ascii -*-
"""DOCS100_2026_10_28: the week's asks verified. The patch adds the register's section 13, STATE section 35 and the
RUNBOOK's commands once (refusing before the tags script, RIGHTS_NOISE's patcher and the rights checks), replays on
the copies from before it, and does nothing the second time; the register's section says done or not for each ask,
names what is left with its state, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs100_2026_10_28.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS100_2026_10_28"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")
REQUIRES = ("scripts/tags_2026_10_28.ps1", "scripts/patch_rights_noise_2026_10_28.py",
            "docs/cloud/CHECKS_rights_2026-10-28.sql")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS101_...) in the file."""
    return any(int(n) > 100 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs100_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs100_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 13 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 13. 25 to 28 Oct"):]
        sec = sec.split("\n## 14. ", 1)[0]   # DOCS101_2026_10_28: section 13 only (section 14 has its own asks)
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "9 are done and 6 are partly done", "load-ux", "hayasirsa-apparatus",
                  "karanagama-matter", "thinking-ab", "proxy-limit", "1,904 claims", "141 passages",
                  "the tags"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| (25|28) Oct", ln)]
        self.assertEqual(len(rows), 15, "the asks of 25 to 28 Oct")
        done = sum(1 for ln in rows if ln.rstrip().endswith("| Done |") or "| Done;" in ln or "| Done with" in ln)
        self.assertEqual(done, 9)
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")


if __name__ == "__main__":
    unittest.main()
