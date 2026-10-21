# -*- coding: ascii -*-
"""NUMERAL_VERSE_2026_10_21: in a typed edition (an e-text, GRETIL, BORI) the numbers in brackets after a verse's
word-numerals are the editor's values, not an index: readiness() sends such a verse; a scan's reading is judged as
before, and an index stays an index; the patcher applies once, from the copy it found. Made-up samples."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "NUMERAL_VERSE_2026_10_21"
APPLIED = MARK.encode() in (SCRIPTS / "scholar_translate.py").read_bytes()

# "1.40a: kha-veda-yama (240), rasa-agni (36) ... //" in Devanagari, with the values in brackets as the e-text gives them
VERSE = ("1.40a: \u0916\u0935\u0947\u0926\u092f\u092e\u093e\u0903 \u0938\u0942\u0930\u094d\u092f\u0938\u094d\u092f "
         "(\u0968\u096a\u0966, \u0969\u096c) 1.40b: \u0930\u0938\u093e\u0917\u094d\u0928\u092f\u0903 "
         "\u0915\u0941\u091c\u0938\u094d\u092f \u0924\u0941 (\u096b\u096d\u096e, \u096e\u096f\u096f, \u0967\u0968) "
         "\u091a\u0928\u094d\u0926\u094d\u0930\u0938\u094d\u092f \u0965")
INDEX = ("\u0905\u0917\u094d\u0928\u093f\u0903 \u0967\u0968, \u0969\u096a, \u096b\u096c "
         "\u0907\u0928\u094d\u0926\u094d\u0930\u0903 \u096d\u096e, \u096f\u0967 \u0935\u093e\u092f\u0941\u0903 \u0968\u0969, \u096a\u096b")


@unittest.skipUnless(APPLIED, "NUMERAL_VERSE_2026_10_21 is not here")
class TheGuard(unittest.TestCase):
    def setUp(self):
        import scholar_translate as ST
        self.ST = ST

    def test_a_typed_editions_values_are_not_an_index(self):
        ST = self.ST
        self.assertTrue(ST.is_index(VERSE), "a scan's reading: as before")
        self.assertFalse(ST.is_index(VERSE, typed=True))
        self.assertIsNone(ST.readiness(VERSE, "mula", 0.95, 0.35, engine="etext:etext"))
        self.assertIsNone(ST.readiness(VERSE, "mula", 0.95, 0.35, engine="gretil"))
        self.assertIn("numbers among the words", ST.readiness(VERSE, "mula", 0.95, 0.35) or "")
        self.assertIn("numbers among the words", ST.readiness(VERSE, "mula", 0.95, 0.35, engine="tesseract") or "")
        self.assertTrue(ST.is_index(INDEX, typed=True), "an index without brackets stays an index")
        self.assertTrue(ST.typed_engine("etext:etext") and ST.typed_engine("bori") and not ST.typed_engine(None))

    def test_choose_sends_it(self):
        ST = self.ST
        class A:   # what choose() reads of the arguments
            pages = None; only_page = None; only_idx = None; from_ref = None; only_ids = None; skip_ids = None
            min_quality = 0.35; redo = False; limit = 10
        x = {"id": 1, "page": 3, "idx": 2, "text": VERSE, "type": "mula", "quality": 0.95, "engine": "etext:etext",
             "ref": None}
        picked, left, _done = ST.choose(A(), [x], {})
        self.assertEqual((picked, left), ([0], []))
        x["engine"] = "tesseract"
        picked, left, _done = ST.choose(A(), [x], {})
        self.assertEqual(picked, [])
        self.assertIn("numbers among the words", left[0][1])


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/scholar_translate.py", "tests/test_scholar_ref_2026_10_18.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_numeral_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_numeral_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_numeral_verse_2026_10_21.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "scholar_translate.py"
            p.write_bytes(p.read_bytes().replace(b"    if is_index(t):\n", b"    if is_index(t) is True:\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 4 found 0 times", r.stdout)
            self.assertNotIn(MARK.encode(), (t / "tests" / "test_scholar_ref_2026_10_18.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_numeral_verse_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
