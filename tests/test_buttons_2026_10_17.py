# -*- coding: ascii -*-
"""BUTTONS_2026_10_17: the main page's buttons. Translate All OCR'd retired (/api/pipeline/advance answers 410 and
starts nothing; the button is a link to the desk); Ingest and Full ask first for a text with English (409, the reason
and the safe way; force goes on); Full asks the path's question too; Ingest All leaves the texts with English and
names them; the patcher. Temp folders only; nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MARK = b"BUTTONS_2026_10_17"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()


@unittest.skipUnless(APPLIED, "BUTTONS_2026_10_17 is not applied here")
class TheRoutes(unittest.TestCase):
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
        self.db = base.fixture(self.td)   # MBh01: 4 passages with English
        con = sqlite3.connect(str(self.db))
        con.execute("INSERT INTO docs(code, category) VALUES ('Fresh', 'x')")
        did = con.execute("SELECT id FROM docs WHERE code = 'Fresh'").fetchone()[0]
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type) VALUES (?, 1, 1, 'x', '', 'mula')",
                    (did,))
        con.commit()
        con.close()
        self.chart = self.td / "text_path.json"
        self.chart.write_text(json.dumps({"at": "2026-10-17T10:00:00", "texts": [
            {"doc": "Fresh", "path": "repair", "why": "Tesseract's text: debris material", "next": [
                "python scripts\\repair_text.py --doc Fresh --repair --max-usd 1.00"], "cost": 0.5}]}), encoding="utf-8")
        self.saved = (self.d.PATH_FILE, self.d.DESK_DB)
        self.d.PATH_FILE, self.d.DESK_DB = self.chart, str(self.db)

    def tearDown(self):
        self.d.PATH_FILE, self.d.DESK_DB = self.saved
        self.tmp.cleanup()

    def launched(self, url, body):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j7")
        try:
            r = self.c.post(url, json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_translate_all_ocrd_is_retired(self):
        r, got = self.launched("/api/pipeline/advance", {})
        self.assertEqual(r.status_code, 410)
        j = r.get_json()
        self.assertTrue(j["retired"])
        self.assertEqual(j["desk"], "/desk")
        self.assertIn("re-ingested 22 texts", j["error"])
        self.assertEqual(got, [], "nothing started")

    def test_ingest_asks_for_a_text_with_english(self):
        r, got = self.launched("/api/ingest", {"doc": "MBh01", "db": str(self.db)})
        self.assertEqual(r.status_code, 409)
        j = r.get_json()
        self.assertTrue(j["needs_force"])
        self.assertEqual(j["english"], 4)
        self.assertIn("reingest_pages.py --doc MBh01", j["say"])
        self.assertEqual(got, [])
        r, got = self.launched("/api/ingest", {"doc": "MBh01", "db": str(self.db), "force": True})
        self.assertEqual((r.status_code, got[0][0]), (200, "ingest"))
        r, got = self.launched("/api/ingest", {"doc": "Fresh", "db": str(self.db)})
        self.assertEqual((r.status_code, got[0][0]), (200, "ingest"), "no English: as before")
        r, got = self.launched("/api/ingest", {"doc": "NotHere", "db": str(self.db)})
        self.assertEqual(r.status_code, 200, "a new text: as before")

    def test_full_asks_both_questions(self):
        r, got = self.launched("/api/queue/run", {"doc": "MBh01", "db": str(self.db)})
        self.assertEqual(r.status_code, 409)
        self.assertIn("English", r.get_json()["say"])
        self.assertEqual(got, [])
        r, got = self.launched("/api/queue/run", {"doc": "Fresh", "db": str(self.db)})
        self.assertEqual(r.status_code, 409)
        j = r.get_json()
        self.assertIn("Its path says the reading comes first: repair the scan", j["say"])
        self.assertEqual(j["label"], "repair the scan")
        r, got = self.launched("/api/queue/run", {"doc": "Fresh", "db": str(self.db), "force": True})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(got, "force goes on")
        r, got = self.launched("/api/queue/run", {"doc": "MBh01", "db": str(self.db), "skip_ingest": True})
        self.assertEqual(r.status_code, 200, "no ingest, no path held: as before")


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_buttons(self):
        s = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertIn('<a class="btn-batch" id="advanceBtn" href="/desk"', s)
        self.assertNotIn('onclick="advancePipeline()"', s)
        self.assertIn("async function doAction(act, doc, opts) {", s)
        self.assertIn("Ingest it again anyway?", s)
        self.assertIn("Run the full pipeline anyway?", s)
        self.assertIn("await doAction('ingest', _bs[_k].dataset.doc, {bulk: true}) === 'held'", s)
        self.assertIn("body: JSON.stringify({doc, db: cfg.db, raw: cfg.raw, force: true})", s)

    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_script_parses(self):
        import test_bench_desk_2026_10_16 as T
        node = T.node()
        if not node:
            self.skipTest("node is not installed")
        s = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            for k, js in enumerate(re.findall(r"<script>(.*?)</script>", s, re.S)):
                p = Path(td) / ("s%d.js" % k)
                p.write_text(js, encoding="utf-8")
                r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/dashboard_static.html")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_buttons_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_buttons_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_buttons_2026_10_17.py")]
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
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_goldfair_*"))   # BENCH_GOLD_FAIR_2026_10_17 came after
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "dashboard_static.html"
            p.write_bytes(p.read_bytes().replace(b"async function doAction(act, doc) {", b"async function doAction(a, d) {"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard_static.html: anchor 2 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_buttons_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
