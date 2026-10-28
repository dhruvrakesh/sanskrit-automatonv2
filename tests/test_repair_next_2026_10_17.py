# -*- coding: ascii -*-
"""REPAIR_NEXT_2026_10_17: repair_text.py's advice when the debris guard lets a text through but its reading is
Tesseract's, its debris judged moderate or material and its scan is here: the path's next step (the pages vision has
not read, at the price measured on the text; then the re-ingest of the changed pages; then the translation), not
"translate it". The cases it leaves as they were; the patcher. Nothing is called; no database."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import repair_text as RT                    # noqa: E402

MARK = b"REPAIR_NEXT_2026_10_17"
APPLIED = MARK in (SCRIPTS / "repair_text.py").read_bytes()
DOC = "SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press"


def sp4214(**kw):
    """The assessment of 17 Oct, 14:36 (the Patala Khanda after its vision run stopped at its cap)."""
    r = {"doc": DOC, "passages": 21128, "english": 2, "hindi": 0, "vectors": 2, "pictures": 0, "stories": 0,
         "debris_pct": 15.7, "vision_pct": 0.0, "below_quality": 636, "pdfs": 364, "raw_pages": 364, "vision_pages": 218,
         "merged_pages": 361, "queued": 360, "merged_complete": False, "held": False, "guard": False,
         "untranslated": 21126, "quality_stuck": False, "state": None, "cost_per_page": 0.0087, "vision_gave_up": 0,
         "consensus": {"at": "2026-10-17T14:36:52", "current": 158, "stale": 203, "missing-in-db": 0},
         "nothing_to_lose": False,
         "judged": {"level": "material", "verses": 40, "misread_pct": 11.4, "misread_letters_pct": 1.56,
                    "furniture_pct": 0.0, "notes_pct": 2.9, "numbering_pct": 0.5, "misread_top": ["ae", "Ul"]}}
    r.update(kw)
    return r


@unittest.skipUnless(APPLIED, "REPAIR_NEXT_2026_10_17 is not applied here")
class TheAdvice(unittest.TestCase):
    def test_the_patala_khanda(self):
        v, n, also = RT.advise(sp4214(), DOC)
        self.assertTrue(v.startswith("nothing holds it: 21128 passages, 2 with English"), v)
        self.assertIn("but its reading is Tesseract's and its debris material: repair first", v)
        self.assertIn("vision has read 218 of its 364 pages, 146 to go, about $1.27 at $0.0087 a page", v)
        self.assertEqual(n, "python scripts\\repair_text.py --doc %s --repair --max-usd 1.60   (the pages vision has not "
                            "read; it stops before spending more)" % DOC)
        self.assertTrue(also[0].startswith("python scripts\\reingest_pages.py --doc %s" % DOC), also)
        self.assertIn("the 203 page(s) of the repair that differ from the database can go in now", also[0])
        self.assertTrue(also[-1].startswith("then: translate it"), also)

    def test_failed_twice_and_all_read(self):
        v, n, also = RT.advise(sp4214(vision_gave_up=6), DOC)
        self.assertIn("(6 left to Tesseract: vision failed on them twice), 140 to go", v)
        v, n, also = RT.advise(sp4214(vision_pages=364), DOC)
        self.assertIn("but 203 page(s) of its repair differ from the database: they go in first", v)
        self.assertTrue(n.startswith("python scripts\\reingest_pages.py --doc %s" % DOC), n)
        self.assertTrue(also[0].startswith("then: translate it"))

    def test_the_cases_left_as_they_were(self):
        tr = "translate it: Finish EN and Add Hindi in the Library (unchanged passages come from the cache at no cost)"
        for kw in ({"judged": dict(sp4214()["judged"], level="cosmetic")}, {"vision_pct": 97.8}, {"pdfs": 0},
                   {"pdfs": 100}, {"vision_pages": 364, "consensus": {"stale": 0}}):
            v, n, also = RT.advise(sp4214(**kw), DOC)
            self.assertEqual((n, also), (tr, []), kw)
            self.assertNotIn("repair first", v)


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("repair_text.py.bak_repairnext_*"))
        if not baks:
            self.skipTest("no .bak_repairnext_ copy here")
        pat = [sys.executable, str(SCRIPTS / "patch_repair_next_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo's root\n", encoding="ascii")
            shutil.copy2(baks[0], t / "scripts" / "repair_text.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("repair_text.py.bak_repairpartial_*"))   # REPAIR_PARTIAL_2026_10_28 came after
            self.assertEqual((t / "scripts" / "repair_text.py").read_bytes(),
                             (later[0] if later else SCRIPTS / "repair_text.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], t / "scripts" / "repair_text.py")
            p = t / "scripts" / "repair_text.py"
            p.write_bytes(p.read_bytes().replace(b"def advise(r: dict, doc: str):", b"def advise(r, doc):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("repair_text.py: anchor 1 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, p.read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_repair_next_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
