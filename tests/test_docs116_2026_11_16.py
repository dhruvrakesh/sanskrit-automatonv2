# -*- coding: ascii -*-
"""DOCS116_2026_11_16: is it done? The register's section 29, STATE section 51, the RUNBOOK's commands once; the patch
replays on the copies from before it and does nothing the second time. The section says done or not for each ask with
its evidence, its sums add up, no placeholder. docs\\cloud\\SITE_SCHEMA_2026-11-17.md (I2) traces every table and
function of the site's schema corpus to a docs\\cloud file that makes it, and those files are here."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs116_2026_11_16.py"
REG = REPO / "docs" / "ASKS_2026-10-22.md"
SCHEMA = REPO / "docs" / "cloud" / "SITE_SCHEMA_2026-11-17.md"
MARK = "DOCS116_2026_11_16"
FILES = ("docs/ASKS_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md")


def newer(b: bytes) -> bool:
    return any(int(n) > 116 for n in re.findall(rb"\bDOCS(\d+)_20\d\d_\d\d_\d\d", b))


@unittest.skipUnless(PAT.exists(), "patch_docs116_2026_11_16.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_docs116_*"))
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


@unittest.skipUnless(REG.exists() and MARK.encode() in REG.read_bytes(), "the register's section 29 is not here")
class TheRegister(unittest.TestCase):
    def section(self):
        s = REG.read_text(encoding="utf-8")
        return s[s.index("## 29. 17 Nov"):].split("\n## 30. ", 1)[0]

    def test_says_done_or_not(self):
        sec = self.section()
        flat = " ".join(sec.split())
        for k in ("Done in full? No.", "12d9d0c", "Arjuna son_of Pandu", "begotten_by Sakra", "91 of 248 parts",
                  "3,392 of 9,029 verses", "WinError 10054", "dynasties 106", "SITE_SCHEMA_2026-11-17.md",
                  "148.0 GB", "70 SQL files", "$48.04 spent, $125.89 left"):
            self.assertIn(k, flat, k)
        rows = [ln for ln in sec.splitlines() if re.match(r"^\| 17 Nov \|", ln)]
        self.assertEqual(len(rows), 11, "the asks of 17 Nov")
        self.assertIsNone(re.search(r"<[A-Za-z_ ]+>", sec), "no placeholder")
        self.assertTrue(sec.isascii())

    def test_the_sums(self):
        flat = " ".join(self.section().split())
        parts = {"hv": 28, "ram1": 12, "ram2": 1, "matsya": 23, "bndp1": 11, "bndp2": 14, "mbh1": 2}
        self.assertEqual(sum(parts.values()), 91)
        allp = {"hv": 28, "ram1": 12, "ram2": 1, "matsya": 23, "bndp1": 11, "bndp2": 45, "brahma": 21, "linga1": 15,
                "kurma1": 16, "garuda1": 14, "agni": 9, "markp": 4, "mbh1": 16, "vipc4": 33}
        self.assertEqual(sum(allp.values()), 248)
        self.assertEqual(248 - 91, 157)
        self.assertEqual(9029 - 3392, 5637)
        self.assertEqual(round(5637 * 2.90 / 3392, 2), 4.82)
        self.assertIn("157 parts, 5,637 verses, about $4.82", flat)
        small = [4, 50, 40, 30, 30, 15, 15, 16, 12, 15, 12, 12, 7, 6, 5, 3]
        self.assertEqual((len(small), sum(small)), (16, 272))
        self.assertIn("the 16 small texts 272", flat)


@unittest.skipUnless(SCHEMA.exists(), "SITE_SCHEMA_2026-11-17.md is not here")
class TheSchema(unittest.TestCase):
    def test_every_table_and_function_has_its_file(self):
        s = SCHEMA.read_text(encoding="ascii")
        tables = re.findall(r"^\| ([a-z_]+) \| (C[^|]*\.sql)[^|]* \|", s, re.M)
        funcs = re.findall(r"^\| (corpus_[a-z_]+) \| [^|]* \| (C[^|]*) \|", s, re.M)
        self.assertEqual(len(tables), 26)
        self.assertEqual(len(funcs), 48)
        cloud = REPO / "docs" / "cloud"
        for name, made in tables + funcs:
            for f in made.split(", "):
                self.assertTrue((cloud / f.strip()).exists(), (name, f))
        self.assertIn("index_dynasties | C28_index_dynasties_2026-11-11.sql", s)
        self.assertIn("pg_get_function_identity_arguments", s)


if __name__ == "__main__":
    unittest.main()
