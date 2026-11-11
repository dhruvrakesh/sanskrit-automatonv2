# -*- coding: ascii -*-
"""DOCS107_2026_11_11: the dynasties read and mended; is it done in full, on the desk, on the site, on a schedule? The
patch adds the register's section 20, STATE section 42 and the RUNBOOK's commands once, replays on the copies from
before it, and does nothing the second time. The register's section says "Done in full? No.", each ask done or not with
what was measured, the four tasks of this PC and the site's pg_cron jobs, and has no placeholder."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs107_2026_11_11.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
MARK = "DOCS107_2026_11_11"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 107 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs107_2026_11_11.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs107_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 20 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 20. 11 Nov, evening"):].split("\n## 21. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("**Done in full? No.**", "1,975 statements, 1,449 verified (73%), $2.00", "2,098 statements, 1,767 verified",
                  "Marici to Trnabindu (27)", "misreads 0.10%", "$13.77", "$173.93", "restart_dashboard.ps1",
                  "srangam_inscriptions.coordinates", "SanskritDBBackup", "SanskritCornerWorker", "PATH_SCHED_2026_11_11",
                  "by invitation", "G5b", "G5c"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 11 Nov \|", ln)]
        self.assertEqual(len(rows), 7, "the asks of 11 Nov, evening")
        self.assertIsNone(re.search(r"<(?!work>)[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())


if __name__ == "__main__":
    unittest.main()
