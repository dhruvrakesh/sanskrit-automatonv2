# -*- coding: ascii -*-
"""ORNAMENT_2026_10_16: a printed ornament ("<decorative line>", a vision OCR's line of its own) is not OCR debris:
scholar_translate.readiness sends such a verse, redeem.classify counts its English as made from a clean reading. The
marker inside a line of text, and any other Latin word, is debris as before. In-memory databases and temp files only;
nothing is called."""
import shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import redeem as RD                             # noqa: E402

ST = base.ST
MARK = b"ORNAMENT_2026_10_16"
APPLIED = hasattr(ST, "ORNAMENT") and hasattr(RD, "ORNAMENT")
ORN = "<decorative line>"


@unittest.skipUnless(APPLIED, "ORNAMENT_2026_10_16 is not applied here")
class TheOrnament(unittest.TestCase):
    def test_readiness(self):
        v = base.V9
        self.assertIsNone(ST.readiness(v, "mula", 0.9))
        self.assertIsNone(ST.readiness(ORN + "\n" + v, "mula", 0.9), "the Markandeya Purana 1.4")
        self.assertIsNone(ST.readiness(v + "\n  " + ORN + " \n" + v, "mula", 0.9), "between two lines")
        self.assertIsNone(ST.readiness(ORN.upper() + "\r\n" + v, "mula", 0.9))
        self.assertTrue(ST.readiness(ORN + " " + v, "mula", 0.9).startswith("OCR debris"), "inside a line of text")
        self.assertTrue(ST.readiness(ORN + "\n" + v + " eGangotri", "mula", 0.9).startswith("OCR debris"))
        self.assertEqual(ST.readiness(ORN, "mula", 0.9), "fewer than 8 Devanagari signs")

    def test_redeem(self):
        con = sqlite3.connect(":memory:")
        con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT); CREATE TABLE passages(id INTEGER PRIMARY "
                          "KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT, text_type TEXT);"
                          "INSERT INTO docs VALUES (1, 'Orn');")
        rows = [(ORN + "\n" + base.V9, "A verse. //"), (base.V9 + " xyz", "A verse. //"), (ORN + " " + base.V9, "x //"),
                (base.V7, "Clean. //")]
        for k, (t, e) in enumerate(rows, 1):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type) VALUES (1,1,?,?,?,'mula')",
                        (k, t, e))
        r = RD.classify(con)["Orn"]
        self.assertEqual((r["no_debris"], r["debris"], r["en"]), (2, 2, 4))


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "redeem.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_ornament_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_ornament_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_scholarref_*"))   # SCHOLAR_REF_2026_10_18 came after (scholar_translate.py)
                self.assertEqual((t / "scripts" / f).read_bytes(), (later[0] if later else SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "redeem.py"
            p.write_bytes(p.read_bytes().replace(b'bool(JUNK.search(text or ""))', b'bool(JUNK.search(text))'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("redeem.py: anchor 2 found 0 times (want 1): this is not the file released", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / "scripts" / f).read_bytes(), "all or nothing")
            (t / "scripts" / "scholar_translate.py").write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry CLASSIFY_HINDI_2026_10_16", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_ornament_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(MARK, b)
        if APPLIED:
            for f in ("scholar_translate.py", "redeem.py"):
                b = (SCRIPTS / f).read_bytes()
                self.assertTrue(all(x < 128 for x in b), f); self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
