# -*- coding: ascii -*-
"""ETEXT_ANALYSIS_2026_10_22: etext_witness.html_to_text() leaves out GRETIL's analysis column (<p class="analysis">,
the verse again with its sandhi undone), so a verse is read once; an html file without one reads as before; the
patcher applies once, from the copies it found. Samples are made up for the test; no file of the repo is written."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
PAT = SCRIPTS / "patch_etext_analysis_2026_10_22.py"
MARK = "ETEXT_ANALYSIS_2026_10_22"
APPLIED = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes()

ROW = ('<div class="row"><div class="column"><p id="Manu_1.%d">\n manum ek\u0101gram \u0101s\u012bnam <br />\n'
       ' pratip\u016bjya yath\u0101ny\u0101yam //\n <span class="ref">Manu_1.%d</span></p></div>\n'
       '<div class="column"><p class="analysis">\n manum ek\u0101gram \u0101s\u012bnam\n pratip\u016bjya yath\u0101 '
       'ny\u0101yam //\n</p></div></div>\n')
PAGE = "<html><body><h2>Text</h2><div>" + "".join(ROW % (i, i) for i in range(1, 4)) + "</div></body></html>"


@unittest.skipUnless(APPLIED, "ETEXT_ANALYSIS_2026_10_22 is not here")
class TheAnalysis(unittest.TestCase):
    def setUp(self):
        import etext_witness as EW
        self.EW = EW

    def test_the_analysis_is_left_out(self):
        t = self.EW.html_to_text(PAGE)
        self.assertEqual(t.count("manum"), 3, "each verse once, not twice")
        self.assertNotIn("yath\u0101 ny\u0101yam", t, "the analysed form is not the text")
        self.assertEqual(t.count("Manu_1."), 3)

    def test_a_page_without_one_reads_as_before(self):
        plain = PAGE.replace(' class="analysis"', "")
        self.assertEqual(self.EW.html_to_text(plain).count("manum"), 6, "a paragraph that is not the analysis stays")
        other = '<p class="verse">rama</p><p class="analysis-note">x</p>'
        self.assertIn("x", self.EW.html_to_text(other), "only the analysis class itself")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "tests/test_witness_fix_2026_10_22.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextanalysis_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextanalysis_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:   # VEDIC_LLA_2026_10_28 came after: its backup of etext_witness.py is this patch's
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)


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
