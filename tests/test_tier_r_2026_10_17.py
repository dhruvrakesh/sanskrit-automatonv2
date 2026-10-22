# -*- coding: ascii -*-
"""TIER_R_2026_10_17: the working English by Sonnet in one pass from the desk (the rest, or every verse again with the
English before kept in the history), its price and the credit; /api/translate's retranslate; the scholarly English
begun at a verse (--from-ref); Sonnet among the main page's engines, and Translate All refusing Claude; the patcher.
Temp folders only; nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import translation_desk as TD               # noqa: E402

MARK = b"TIER_R_2026_10_17"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()


@unittest.skipUnless(MARK in (SCRIPTS / "translation_desk.py").read_bytes(), "not applied here")
class TheRules(unittest.TestCase):
    def test_begin_at_a_verse(self):
        argv, why = TD.scholar_argv("W", "plan", "", 40, from_ref="81.1")
        self.assertIsNone(why)
        self.assertEqual(argv[:6], ["--doc", "W", "--limit", "40", "--from-ref", "81.1"])
        self.assertEqual(argv[6:], list(TD.SCHOLAR_SOP))
        argv, why = TD.scholar_argv("W", "plan", "2", 40)
        self.assertNotIn("--from-ref", argv, "as before without it")
        for bad in ("81.x", "1; del", "81.1.1.1.1"):
            argv, why = TD.scholar_argv("W", "plan", "", 40, from_ref=bad)
            self.assertIsNone(argv)
            self.assertIn("begin at", why)
        self.assertEqual((TD.TIER_R_ENGINE, TD.TIER_R_PER_VERSE), ("anthropic:claude-sonnet-5-5", 0.0052))


@unittest.skipUnless(APPLIED, "TIER_R_2026_10_17 is not applied here")
class TheDesk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_bench_desk_2026_10_16 as T
        cls.d = T.load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        import test_scholar_2026_10_14 as base
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        self.chart = self.td / "text_path.json"
        self.chart.write_text(json.dumps({"at": "2026-10-17T10:00:00", "texts": [
            {"doc": "MBh01", "path": "done", "why": "translated", "next": [], "cost": 0.0}]}), encoding="utf-8")
        self.saved = (self.d.PATH_FILE, self.d.DESK_DB)
        self.d.PATH_FILE, self.d.DESK_DB = self.chart, str(self.db)
        self.d._DESK_CACHE.update(res=None)
        self.d._SCHOLAR_COVER.update(key=None, at=0.0, res={})

    def tearDown(self):
        self.d.PATH_FILE, self.d.DESK_DB = self.saved
        self.d._DESK_CACHE.update(res=None)
        self.tmp.cleanup()

    def launched(self, url, body):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j3")
        try:
            r = self.c.post(url, json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_the_tier_r_box(self):
        h = self.c.get("/desk/MBh01").get_data(as_text=True)
        self.assertIn("The working English by Sonnet in one pass (Tier R)", h)
        self.assertIn("deskTranslate('MBh01', this, 'anthropic:claude-sonnet-5-5', true)", h, "every verse again")
        self.assertIn("deskTranslate('MBh01', this, 'anthropic:claude-sonnet-5-5', false)", h, "the rest")
        self.assertIn("about $0.03 (the English before is kept in the history)", h)
        self.assertIn("async function deskTranslate(doc, btn, engine, again)", h)
        self.assertIn('id="dkfrom"', h)
        self.assertIn("from_ref: (document.getElementById('dkfrom') || {}).value || ''", h)

    def test_retranslate_and_the_engine(self):
        r, got = self.launched("/api/translate", {"doc": "MBh01", "lang": "en", "limit": 0,
                                                  "engine": "anthropic:claude-sonnet-5-5", "retranslate": True})
        self.assertEqual(r.status_code, 200)
        argv = got[0][2]
        self.assertIn("--retranslate", argv)
        self.assertEqual(argv[argv.index("--engine") + 1], "anthropic:claude-sonnet-5-5")
        r, got = self.launched("/api/translate", {"doc": "MBh01", "lang": "en", "limit": 0})
        self.assertNotIn("--retranslate", got[0][2], "as before")

    def test_the_scholarly_english_begins_at_a_verse(self):
        r, got = self.launched("/api/desk/scholar", {"doc": "MBh01", "step": "plan", "limit": 40, "from_ref": "1.1.7"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        argv = got[0][2]
        self.assertEqual(argv[argv.index("--from-ref") + 1], "1.1.7")
        r, got = self.launched("/api/desk/scholar", {"doc": "MBh01", "step": "plan", "limit": 40, "from_ref": "x;y"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(got, [])


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_engines(self):
        s = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertIn('<option value="anthropic:claude-sonnet-5-5" title="TIER_R_2026_10_17', s)
        self.assertIn("'<option value=\"anthropic:claude-sonnet-5-5\" title=\"Tier R: the Claude credit\">", s)
        self.assertIn("Translate All does not run Claude", s)
        self.assertIn('<option value="gemini:gemini-2.5-flash" selected>', s, "flash stays the default")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/translation_desk.py", "scripts/dashboard.py", "scripts/dashboard_static.html")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_tierr_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_tierr_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_tier_r_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after
                         or sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*")))   # UI_CLARITY_2026_10_22
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "translation_desk.py"
            p.write_bytes(p.read_bytes().replace(b"MAX_USD = 12.0 ", b"MAX_USD = 12.00 "))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("translation_desk.py: anchor 1 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_tier_r_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
