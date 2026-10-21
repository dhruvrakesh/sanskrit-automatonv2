# -*- coding: ascii -*-
"""ETEXT_ORTHO_2026_10_21: etext_witness.to_deva() reads a GRETIL e-text's conventions as meant (H the visarga, +a an
a merged into the vowel before it, written with the avagraha; the pada labels and the sigla as written; the note
"checked" dropped); ortho=False reads as before; GRETIL's English header is dropped; leftover_latin() does not count
what is kept in Latin letters; the patcher applies once, from the copy it found. Samples are made up for the test."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "ETEXT_ORTHO_2026_10_21"
APPLIED = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes()

try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False


@unittest.skipUnless(APPLIED and HAVE_IT, "ETEXT_ORTHO_2026_10_21 or indic_transliteration is not here")
class TheReading(unittest.TestCase):
    def setUp(self):
        import etext_witness as EW
        self.EW = EW

    def test_the_visarga_and_the_avagraha(self):
        d = lambda s: self.EW.to_deva(s, "iast")
        self.assertEqual(d("1.01a: namaH \u015biv\u0101ya/ 1.01b: devo +api gataH//"),
                         "1.01a: \u0928\u092e\u0903 \u0936\u093f\u0935\u093e\u092f\u0964 1.01b: "
                         "\u0926\u0947\u0935\u094b\u093d\u092a\u093f \u0917\u0924\u0903\u0965")
        self.assertEqual(d("r\u0101maH/(B r\u0101mo) v\u0101 +atra//"),
                         "\u0930\u093e\u092e\u0903\u0964(B \u0930\u093e\u092e\u094b) \u0935\u093e\u093d\u0924\u094d\u0930\u0965")
        self.assertEqual(d("(\u1e0d devaH)"), "(D \u0926\u0947\u0935\u0903)", "the dotted D is the siglum D")
        self.assertEqual(d("(C +asti)"), "(C \u093d\u0938\u094d\u0924\u093f)", "after a siglum the space stays")
        self.assertEqual(d("1.30a: kham/(123) checked"), "1.30a: \u0916\u092e\u094d\u0964(\u0967\u0968\u0969)",
                         "the inputter's note is not the text")

    def test_before_the_patch(self):
        self.assertEqual(self.EW.to_deva("namaH", "iast", ortho=False), "\u0928\u092e\u0939\u094d")
        self.assertEqual(self.EW.to_deva("nama\u1e25", "iast"), "\u0928\u092e\u0903", "an e-text with the dot is as before")
        self.assertEqual(self.EW.to_deva("namaH", "hk"), "\u0928\u092e\u0903", "Harvard-Kyoto is not touched")

    def test_the_header_and_the_latin_left(self):
        txt = ("S\u016bryasiddh\u0101nta\n\nHeader\nData entry: X Y\nPublisher: G\u00f6ttingen Register of Electronic "
               "Texts in Indian Languages (GRETIL)\nSource:\nText\n\n1.01a: namaH \u015biv\u0101ya/ 1.01b: devo +api gataH//\n")
        self.assertEqual(self.EW.gretil_header(txt.split("\n")), {3, 4, 5, 6, 7})
        self.assertEqual(self.EW.gretil_header(txt.replace("GRETIL", "a library").split("\n")), set(), "it must name GRETIL")
        p = self.EW.parse(txt, "iast")
        self.assertEqual([v["text"] for v in p["verses"]][-1], "1.01a: \u0928\u092e\u0903 \u0936\u093f\u0935\u093e\u092f\u0964 "
                         "1.01b: \u0926\u0947\u0935\u094b\u093d\u092a\u093f \u0917\u0924\u0903\u0965")
        self.assertFalse(any("Source" in v["text"] or "\u0938\u094b\u0909" in v["text"] for v in p["verses"]))
        self.assertEqual(self.EW.leftover_latin([{"text": "1.01a: \u0928\u092e\u0903"}, {"text": "(B \u0930\u093e\u092e\u094b)"},
                                                 {"text": "abc \u0928\u092e\u0903"}]), 1 / 3.0)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "tests/test_etext_page_2026_10_18.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextortho_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextortho_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_etext_ortho_2026_10_21.py")]
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
            p = t / "scripts" / "etext_witness.py"
            p.write_bytes(p.read_bytes().replace(b"    if scheme == \"iast\":\n        s = s.lower()\n",
                                                 b"    if scheme == 'iast':\n        s = s.lower()\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 2 found 0 times", r.stdout)
            self.assertNotIn(MARK.encode(), (t / "tests" / "test_etext_page_2026_10_18.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_etext_ortho_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
