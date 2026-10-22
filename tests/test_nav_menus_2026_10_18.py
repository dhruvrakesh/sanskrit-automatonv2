# -*- coding: ascii -*-
"""NAV_MENUS_2026_10_18: the main page's top bar in six menus (Texts, Translate, Check, Make, Ask, Site), every page of
the dashboard reachable from it (Scholarly English, Path, Redeem, BM2 and Methodology had no link), the links that were
there kept as they were, Srangam's editions and corpus, the Corner and the Hub; no script block added; the patcher.
Reads scripts/dashboard_static.html only."""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
PAGE = SCRIPTS / "dashboard_static.html"
MARK = b"NAV_MENUS_2026_10_18"
APPLIED = MARK in PAGE.read_bytes()

PAGES = ["/stories", "/shelf", "/images", "/translate", "/library", "/sources", "/benchmarks", "/benchmarks/bm2", "/desk",
         "/ask", "/scholar", "/path", "/redeem", "/methodology"]
SITE = ["https://srangam.nartiang.org/editions", "https://srangam.nartiang.org/corpus",
        "https://srangam.nartiang.org/corpus/corner", "http://127.0.0.1:5050/"]


def top_bar(h: str) -> str:
    i = h.index('<header class="top-bar">')
    return h[i:h.index("</header>", i)]


@unittest.skipUnless(APPLIED, "NAV_MENUS_2026_10_18 is not applied here")
class TheMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = PAGE.read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.bar = top_bar(cls.h)

    def test_six_menus_and_every_page(self):
        self.assertEqual(self.bar.count('<nav class="topnav"'), 1)
        menus = re.findall(r'<details class="tn"[^>]*><summary>([^<]+)</summary>', self.bar)
        self.assertEqual([m.split(";")[-1].strip() for m in menus], ["Texts", "Translate", "Check", "Make", "Ask", "Site"])
        for href in PAGES + SITE:
            self.assertIn('href="%s"' % href, self.bar, href)
        self.assertIn('onclick="openDatabase(this)"', self.bar)
        self.assertIn('onclick="refresh(true)"', self.bar, "Refresh stays")
        self.assertEqual(self.bar.count('<div class="tn-pop">'), 6)
        self.assertEqual(self.bar.count("</details>"), 6)

    def test_the_links_that_were_there_are_kept(self):
        for s in ('title="Stories: cited retellings', 'title="Shelf: every text by collection', 'title="Image library',
                  'title="JUDGE_DESK_2026_10_11', 'title="BENCH_DESK_2026_10_16', 'title="TRANSLATION_DESK_2026_10_17',
                  'title="Ask questions answered from the corpus', 'title="Translate any Sanskrit'):
            self.assertIn(s, self.bar, s)
        self.assertIn('<select id="engineSelect" class="engine-select">', self.bar)
        self.assertIn('<option value="gemini:gemini-2.5-flash" selected>', self.bar, "flash stays the default")
        self.assertIn('<div class="status-dot" title="Server running"></div>', self.bar)
        self.assertEqual(self.h.count('    <div class="top-bar-spacer"></div>\n'), 1)

    def test_one_menu_at_a_time_without_a_script_block(self):
        self.assertEqual(self.bar.count("ontoggle="), 6)
        self.assertEqual(self.bar.count('onmouseleave="'), 6)   # UI_CLARITY_2026_10_22: closed a moment after it is left
        self.assertNotIn("<script", self.bar)
        self.assertEqual(self.h.count("<script"), 1, "the page's one script block, as before")
        self.assertIn(".tn-pop>a,.tn-pop>button{display:block!important", self.h)
        self.assertTrue(all(ord(c) < 128 for c in self.bar), "the bar is ASCII (entities for the signs)")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard_static.html", "tests/test_tier_r_2026_10_17.py", "tests/test_stories_ui_2026_10_05.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_navmenus_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_nav_menus_2026_10_18.py")]
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
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*"))   # UI_CLARITY_2026_10_22 came after
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            g = t / "scripts" / "dashboard_static.html"
            g.write_bytes(g.read_bytes().replace(b'<a href="/images" ', b'<a href="/images2" '))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard_static.html: anchor 2 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, (t / "tests" / "test_tier_r_2026_10_17.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_nav_menus_2026_10_18.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)


if __name__ == "__main__":
    unittest.main()
