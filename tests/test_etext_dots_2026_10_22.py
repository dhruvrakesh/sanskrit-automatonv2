# -*- coding: ascii -*-
"""ETEXT_DOTS_2026_10_22: etext_witness.to_deva() reads a line whose words are joined by full stops (GRETIL's Nirukta)
as written: a full stop between two words a space, two or more a danda, one at the line's end nothing, `` and ''
quotation marks, a reference, a siglum and an English note in brackets in Latin; every other line as before (a full
stop the danda, the Mahabharata's '' two avagrahas); ortho=False as before; the patcher applies once, from the copy it
found, all or nothing. Samples are short lines of the e-texts' own kinds; no file of the repo is written."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
PAT = SCRIPTS / "patch_etext_dots_2026_10_22.py"
MARK = "ETEXT_DOTS_2026_10_22"
APPLIED = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes()

try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False

DANDA = "\u0964"
SAMAMNAYA = "sam\u0101mn\u0101ya\u1e25.sam\u0101mn\u0101ta\u1e25.sa.vy\u0101khy\u0101tavya\u1e25"


@unittest.skipUnless(APPLIED and HAVE_IT, "ETEXT_DOTS_2026_10_22 or indic_transliteration is not here")
class TheDottedLine(unittest.TestCase):
    def setUp(self):
        import etext_witness as EW
        self.d = lambda s, o=True: EW.to_deva(s, "iast", ortho=o)

    def test_a_full_stop_between_words_is_a_space(self):
        self.assertEqual(self.d(SAMAMNAYA),
                         "\u0938\u092e\u093e\u092e\u094d\u0928\u093e\u092f\u0903 \u0938\u092e\u093e\u092e\u094d\u0928"
                         "\u093e\u0924\u0903 \u0938 \u0935\u094d\u092f\u093e\u0916\u094d\u092f\u093e\u0924\u0935"
                         "\u094d\u092f\u0903")
        self.assertEqual(self.d("1,1: yad.v\u0101"), "\u0967,\u0967: \u092f\u0926\u094d \u0935\u093e",
                         "the label's space is not the words' spacing")

    def test_a_final_h_is_the_visarga(self):
        self.assertEqual(self.d("\u012bro.n\u0101ma.kara\u1e47ah,.u\u015b\u012bram"),
                         "\u0908\u0930\u094b \u0928\u093e\u092e \u0915\u0930\u0923\u0903, \u0909\u0936\u0940"
                         "\u0930\u092e\u094d")
        self.assertEqual(self.d("mahat.bh\u0101va.pradh\u0101nam"),
                         "\u092e\u0939\u0924\u094d \u092d\u093e\u0935 \u092a\u094d\u0930\u0927\u093e\u0928"
                         "\u092e\u094d", "an h inside a word, or after a consonant, as before")

    def test_two_stops_a_danda_and_the_last_nothing(self):
        self.assertEqual(self.d("su.\u1e5btas..bh\u0101\u1e63\u0101.iti."),
                         "\u0938\u0941 \u090b\u0924\u0938\u094d \u0964 \u092d\u093e\u0937\u093e \u0907\u0924\u093f")

    def test_quotes_references_sigla_and_notes(self):
        self.assertEqual(self.d("``.agnir.iva.''.(\u1e5bV.X,84,2;.106,3).iti"),
                         "\u201c\u0905\u0917\u094d\u0928\u093f\u0930\u094d \u0907\u0935\u201d (\u1e5bV X,84,2; 106,3) "
                         "\u0907\u0924\u093f")
        self.assertEqual(self.d("v\u0101.(ca.Bh).aneka.parvasu"),
                         "\u0935\u093e (\u091a Bh) \u0905\u0928\u0947\u0915 \u092a\u0930\u094d\u0935\u0938\u0941",
                         "the reading in Devanagari, its siglum in Latin")
        self.assertEqual(self.d("tad.y\u0101ny.[et\u0101ni.Bh].catv\u0101ri"),
                         "\u0924\u0926\u094d \u092f\u093e\u0928\u094d\u092f\u094d [\u090f\u0924\u093e\u0928\u093f Bh] "
                         "\u091a\u0924\u094d\u0935\u093e\u0930\u093f")
        self.assertEqual(self.d("eka.upasarg\u0101d.[i.e.,.from.su].dad\u0101ti"),
                         "\u090f\u0915 \u0909\u092a\u0938\u0930\u094d\u0917\u093e\u0926\u094d [i.e., from su] "
                         "\u0926\u0926\u093e\u0924\u093f")

    def test_every_other_line_as_before(self):
        self.assertEqual(self.d("garte ''rt\u0101\u1e43s tr\u0101\u1e47am icchata\u1e25"),
                         "\u0917\u0930\u094d\u0924\u0947 \u093d\u093d\u0930\u094d\u0924\u093e\u0902\u0938\u094d "
                         "\u0924\u094d\u0930\u093e\u0923\u092e\u094d \u0907\u091a\u094d\u091b\u0924\u0903",
                         "the Mahabharata's '' is two avagrahas")
        self.assertEqual(self.d("gatv\u0101. puna\u1e25"), "\u0917\u0924\u094d\u0935\u093e\u0964 \u092a\u0941\u0928\u0903")
        self.assertEqual(self.d("so'pi gacchati /"), "\u0938\u094b\u093d\u092a\u093f \u0917\u091a\u094d\u091b\u0924\u093f \u0964")
        self.assertEqual(self.d("1.01a: namaH \u015biv\u0101ya/"), "1.01a: \u0928\u092e\u0903 \u0936\u093f\u0935\u093e\u092f\u0964",
                         "the Surya's labels and visarga as ETEXT_ORTHO reads them")

    def test_ortho_false_reads_as_before(self):
        self.assertEqual(self.d("sam\u0101mn\u0101ya\u1e25.sam\u0101mn\u0101ta\u1e25", False),
                         "\u0938\u092e\u093e\u092e\u094d\u0928\u093e\u092f\u0903\u0964\u0938\u092e\u093e\u092e\u094d"
                         "\u0928\u093e\u0924\u0903")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "tests/test_etext_prose2_2026_10_22.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextdots_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextdots_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("CHECK OK: 2 file(s)", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            g = t / "scripts" / "etext_witness.py"
            g.write_bytes(g.read_bytes().replace(b"            s, kept = gretil_marks(s)\n", b"            s, kept = x(s)\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSE: scripts/etext_witness.py: anchor", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK.encode(), (t / f).read_bytes(), "all or nothing: " + f)

    def test_it_needs_etext_prose2(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "etext_witness.py").write_text("# an older etext_witness.py\n", encoding="ascii")
            (t / "tests" / "test_etext_prose2_2026_10_22.py").write_text("# ETEXT_PROSE2_2026_10_22\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("ETEXT_PROSE2_2026_10_22", r.stdout)
            self.assertIn("Nothing written", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
