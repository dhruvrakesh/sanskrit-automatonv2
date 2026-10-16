# -*- coding: ascii -*-
"""READY_PRICE_2026_10_16: a vision OCR's footnote mark (<sup>6</sup>) is not OCR debris (scholar_translate.readiness);
the price of a passage of working English is measured on the rows since the thinking is counted (redeem.spend_by_doc).
Temp files and an in-memory database only; nothing is called."""
import shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import redeem as RD                             # noqa: E402

ST = base.ST
MARK = b"READY_PRICE_2026_10_16"
APPLIED = hasattr(ST, "SUP_TAG")


@unittest.skipUnless(APPLIED, "READY_PRICE_2026_10_16 is not applied here")
class TheFootnoteMarks(unittest.TestCase):
    def test_a_mark_is_not_debris(self):
        v = base.V6
        self.assertIsNone(ST.readiness(v, "mula", 0.9))
        self.assertIsNone(ST.readiness(v + "<sup>6</sup>", "mula", 0.9), "the edition's footnote number")
        self.assertIsNone(ST.readiness(v.replace(" ", "<SUP>7</SUP> ", 1), "mula", 0.9))
        self.assertTrue(ST.readiness(v + " This verse is omitted in B,C.", "mula", 0.9).startswith("OCR debris"),
                        "the apparatus is still left out")
        self.assertTrue(ST.readiness(v + "<sup>6</sup> eGangotri", "mula", 0.9).startswith("OCR debris"))
        self.assertEqual(ST.readiness("<sup>6</sup>", "mula", 0.9), "fewer than 8 Devanagari signs")


class ThePrice(unittest.TestCase):
    def con(self, rows):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE usage_log(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, doc TEXT, engine TEXT, "
                    "in_tokens INT, out_tokens INT, cost_usd REAL, passages INT)")
        con.executemany("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd, passages) VALUES (?,?,?,?,?,?)", rows)
        return con

    @unittest.skipUnless(hasattr(RD, "METERED_SINCE"), "READY_PRICE_2026_10_16 is not applied here")
    def test_measured_since_the_thinking_is_counted(self):
        F, P, C = "gemini:gemini-2.5-flash", "gemini:gemini-2.5-pro", "anthropic:claude-haiku-5-5"
        old = [("2026-10-13T10:00:00Z", "translation", "A", F, 0.5, 1000), ("2026-10-13T10:00:00Z", "translation", "A",
                                                                            P, 0.1, 100)]
        new = [("2026-10-15T10:00:00Z", "translation", "B", F, 0.3705, 150),
               ("2026-10-15T11:00:00Z", "translation", "B", P, 0.12, 60),
               ("2026-10-16T10:00:00Z", "translation", "C", C, 5.0, 500),          # a Claude engine prices neither
               ("2026-10-15T10:00:00Z", "judge", "B", F, 9.0, 900)]                 # not a translation
        by, f, p = RD.spend_by_doc(self.con(old + new))
        self.assertEqual((f, p), (0.00247, 0.002))
        self.assertAlmostEqual(by["C"], 5.0, msg="its spend is still the text's")
        by, f, p = RD.spend_by_doc(self.con(old + [("2026-10-15T10:00:00Z", "translation", "B", F, 0.1235, 50)]))
        self.assertEqual(f, round((0.5 + 0.1235) / 1050, 6), "too few since: all the rows, as before")
        self.assertEqual(p, round(0.1 / 100, 6))
        self.assertEqual(RD.spend_by_doc(self.con(old))[1:], (0.0005, 0.001), "no rows since: as before")

    def test_without_a_ledger(self):
        con = sqlite3.connect(":memory:")
        self.assertEqual(RD.spend_by_doc(con), ({}, RD.FLASH_DEFAULT, RD.PRO_DEFAULT))


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "redeem.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_readyprice_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_ready_price_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / "scripts" / f).read_bytes(), (SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "redeem.py"
            p.write_bytes(p.read_bytes().replace(b"def spend_by_doc(con) -> tuple:", b"def spend_by_doc(con):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("redeem.py: anchor 2 found 0 times (want 1): this is not the file released", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / "scripts" / f).read_bytes(), "all or nothing")
            (t / "scripts" / "scholar_translate.py").write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry TRIAGE_2026_10_16", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_ready_price_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(MARK, b)
        if APPLIED:
            for f in ("scholar_translate.py", "redeem.py"):
                b = (SCRIPTS / f).read_bytes()
                self.assertTrue(all(x < 128 for x in b), f); self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
