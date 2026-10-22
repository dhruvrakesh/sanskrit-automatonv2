# -*- coding: ascii -*-
"""UI_CLARITY_2026_10_22: the top bar's menus stay open on the way to them (a bridge over the 6px gap; closed 450 ms
after the pointer leaves, kept open when it comes back); the Library card says what EN counts (the working English) and
what SC counts (the scholarly English), and where each goes; a text in repair says why its English was cleared and how
it is published; the Source desk says that "% Devanagari" is an OCR text's script, not its fidelity; the patcher. Reads
the files only."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
PAGE = SCRIPTS / "dashboard_static.html"
DASH = SCRIPTS / "dashboard.py"
PAT = SCRIPTS / "patch_ui_clarity_2026_10_22.py"
MARK = "UI_CLARITY_2026_10_22"
APPLIED = MARK.encode() in PAGE.read_bytes() and MARK.encode() in DASH.read_bytes()
CLOSE = ('onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);'
         'd._tnT=setTimeout(function(){d.open=false},450)"')


def top_bar(h: str) -> str:
    i = h.index('<header class="top-bar">')
    return h[i:h.index("</header>", i)]


@unittest.skipUnless(APPLIED, "UI_CLARITY_2026_10_22 is not applied here")
class TheMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = PAGE.read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.bar = top_bar(cls.h)

    def test_a_bridge_and_a_delayed_close(self):
        self.assertEqual(self.bar.count(CLOSE), 6)
        self.assertNotIn('onmouseleave="this.open=false"', self.bar)
        self.assertIn('.tn-pop::before{content:"";position:absolute;left:-8px;right:-8px;top:-12px;height:12px}', self.h)
        self.assertIn(".tn-pop{position:absolute;top:calc(100% + 6px)", self.h, "the list where it was")

    def test_no_script_block_added(self):
        self.assertNotIn("<script", self.bar)
        self.assertEqual(self.h.count("<script"), 1)
        self.assertEqual(self.bar.count("ontoggle="), 6, "one menu open at a time, as before")


@unittest.skipUnless(APPLIED, "UI_CLARITY_2026_10_22 is not applied here")
class TheWords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = DASH.read_text(encoding="utf-8")

    def test_the_two_englishes(self):
        self.assertIn('<span class="badge en" title="The working English (Gemini): what the reader shows first', self.d)
        self.assertIn("SC beside it is the scholarly ", self.d)
        self.assertIn(">EN {en}/{total}</span>", self.d, "the count as it was")
        self.assertNotIn("is not on the site yet", self.d)
        self.assertNotIn("(EN, which the site shows) and is not on", self.d)
        self.assertGreaterEqual(self.d.count("not while the text is held in repair or"), 2)

    def test_a_text_in_repair_says_why_and_how(self):
        self.assertIn("The repair replaced its Sanskrit, so the English and the ", self.d)
        self.assertIn("Publishing waits for the ", self.d)
        self.assertIn("repair_text.py --release --force", self.d)
        self.assertIn("the site keeps its last version (%s English, ", self.d, "as test_repair_heal reads it")

    def test_script_is_not_fidelity(self):
        self.assertIn('"% Devanagari" is the script of an OCR text, not its fidelity', self.d)
        self.assertIn('title="The share of its letters that are Devanagari: its script, not its fidelity', self.d)
        self.assertIn("Fetch the OCR text (", self.d, "the button as it was")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard_static.html", "scripts/dashboard.py", "tests/test_nav_menus_2026_10_18.py",
             "tests/test_tier_r_2026_10_17.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_uiclarity_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("CHECK OK: 4 file(s)", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            g = t / "scripts" / "dashboard.py"
            g.write_bytes(g.read_bytes().replace(b"Verses in scholarly English (scholar_translate.py)", b"Verses"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSE: scripts/dashboard.py: anchor", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK.encode(), (t / f).read_bytes(), "all or nothing: " + f)


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
