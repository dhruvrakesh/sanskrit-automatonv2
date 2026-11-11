# -*- coding: ascii -*-
"""DOCS104_2026_11_10: the genealogies mended and explained; B. C. Law made ready. The patch adds the register's
section 17, STATE section 39, the RUNBOOK's commands and the docs map's theme once, replays on the copies from before
it, and does nothing the second time. The register's section says done or not for each ask, with the numbers measured
on the real data, and has no placeholder; the page docs/GENEALOGY_2026-11-10.md is ASCII and says what it cannot do."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs104_2026_11_10.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
PAGE = REPO / "docs" / "GENEALOGY_2026-11-10.md"
MARK = "DOCS104_2026_11_10"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "scripts/docs_map.py")


def newer(b: bytes) -> bool:
    """A DOCS marker after this one (DOCS105_...) in the file."""
    return any(int(n) > 104 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs104_2026_11_10.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs104_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 17 is not here")
class TheRegister(unittest.TestCase):
    def test_says_done_or_not(self):
        s = REG.read_text(encoding="utf-8")
        sec = s[s.index("## 17. 10 Nov"):].split("\n## 18. ", 1)[0]
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "5,602 entries", "through Pandu, not Indra", "kin-long", "G5a", "$36.61",
                  "--reparse", "about $2.34", "private"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 10 Nov \|", ln)]
        self.assertEqual(len(rows), 8, "the asks of 10 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_page(self):
        b = PAGE.read_bytes()
        self.assertTrue(b.isascii())
        s = " ".join(b.decode("ascii").split())
        for k in ("## 6. B. C. Law", "What these rules cannot mend", "5,602 name a person", "G5a", "kin-long",
                  "C26_INDEX_ALIASES_2026_11_10", "In_copyright"):
            self.assertIn(k, s, k)

    def test_the_map_files_the_page(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import importlib
        dm = importlib.import_module("docs_map")
        self.assertEqual(dm.theme_of("GENEALOGY_2026-11-10.md"), "Names, relations and genealogies")
        self.assertEqual(dm.theme_of("PEOPLES_2026-10-28.md"), "Names, relations and genealogies")


if __name__ == "__main__":
    unittest.main()
