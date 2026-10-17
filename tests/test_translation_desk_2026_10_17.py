# -*- coding: ascii -*-
"""TRANSLATION_DESK_2026_10_17: the translation desk. Its rules (scripts/translation_desk.py: the stage of a text, the
guard on a working translation whose path says the reading comes first, the scholarly English's arguments with the
standard flags, the cap a plan proposes); the dashboard's /desk and /desk/<doc>; /api/desk/scholar (jobs of kind
scholar, doc scholar:<doc>); the guard on /api/translate and /api/pipeline/translate-doc (409, then force); the path
on each row of /api/status; the main page's buttons; the patcher. Temp folders only; nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import translation_desk as TD               # noqa: E402

MARK = b"TRANSLATION_DESK_2026_10_17"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()
NOW = "2026-10-17T09:00:00"


def chart_rows():
    return [
        {"doc": "MBh01", "path": "translate", "why": "no debris found", "next": ["translate it: Finish EN and Add Hindi"],
         "cost": 3.77},
        {"doc": "ReadyText", "path": "translate", "why": "a clean reading", "next": ["translate it: Finish EN"], "cost": 0.5},
        {"doc": "RepairText", "path": "repair", "why": "Tesseract's text: debris moderate (1.56% of letters misread)",
         "next": ["python scripts\\repair_text.py --doc RepairText --repair --max-usd 1.90"], "cost": 1.5},
        {"doc": "ChangedText", "path": "translate", "why": "the repair differs on 7 pages",
         "next": ["python scripts\\reingest_pages.py --doc ChangedText   (first: the 7 changed page(s))"], "cost": 2.0},
        {"doc": "HeldText", "path": "source", "why": "damaged", "next": ["find a source"], "cost": 0},
        {"doc": "RepairedText", "path": "in_repair", "why": "repaired", "next": ["translate it: Finish EN"], "cost": 1.0},
        {"doc": "JudgeText", "path": "judge", "why": "translated, never judged", "next": ["python scripts\\judge_sample.py"]},
        {"doc": "DoneText", "path": "done", "why": "", "next": []}]


class TheRules(unittest.TestCase):
    def test_the_stages(self):
        rows = {r["doc"]: r for r in chart_rows()}
        self.assertEqual(TD.stage_of(rows["ReadyText"]), "ready")
        self.assertEqual(TD.stage_of(rows["RepairText"]), "source")
        self.assertEqual(TD.stage_of(rows["ChangedText"]), "source", "a re-ingest first")
        self.assertEqual(TD.stage_of(rows["RepairedText"]), "ready", "in repair, its translation next")
        self.assertEqual(TD.stage_of(rows["JudgeText"]), "judged")
        self.assertEqual(TD.stage_of(rows["DoneText"]), "done")
        self.assertEqual(TD.stage_of(None), "uncharted")
        self.assertEqual(TD.stage_of(rows["RepairText"], {"verses": 3}), "edition", "the scholarly English begun")
        self.assertEqual(TD.stage_of(rows["ReadyText"], {}, {"status": "withdrawn"}), "source")

    def test_the_guard(self):
        rows = {r["doc"]: r for r in chart_rows()}
        now = time.mktime(time.strptime(NOW, "%Y-%m-%dT%H:%M:%S"))
        g = TD.guard(rows["RepairText"], None, "2026-10-14T22:18:42", now)
        self.assertEqual((g["path"], g["label"]), ("repair", "repair the scan"))
        self.assertIn("Next: python scripts\\repair_text.py --doc RepairText --repair --max-usd 1.90", g["say"])
        self.assertIn("(the chart of 2026-10-14)", g["say"], "two days old: not yet old")
        g = TD.guard(rows["RepairText"], None, "2026-10-01T10:00:00", now)
        self.assertIn("(the chart of 2026-10-01, 15 days old: chart it again, free)", g["say"])
        self.assertIsNotNone(TD.guard(rows["ChangedText"], None, ""))
        for d in ("ReadyText", "RepairedText", "JudgeText", "DoneText"):
            self.assertIsNone(TD.guard(rows[d], None, ""), d)
        self.assertIsNone(TD.guard(None), "uncharted: the chart has nothing to say")
        self.assertIsNone(TD.guard(rows["RepairText"], {"status": "withdrawn"}), "translate_passages.py holds it itself")

    def test_the_scholarly_arguments(self):
        argv, why = TD.scholar_argv("MBh01", "plan")
        self.assertIsNone(why)
        self.assertEqual(argv, ["--doc", "MBh01", "--limit", "40"] + list(TD.SCHOLAR_SOP))
        argv, _w = TD.scholar_argv("MBh01", "run", "1-3,5", 24, 2.5, held_ok=True)
        self.assertEqual(argv[-5:], ["--no-compare", "--held-ok", "--yes", "--max-usd", "2.50"])
        self.assertIn("--pages", argv)
        for bad, why in (({"step": "drop"}, "unknown step"), ({"step": "plan", "pages": "1;rm"}, "pages:"),
                         ({"step": "plan", "limit": 401}, "1 to 400"), ({"step": "run", "max_usd": 13}, "outside what"),
                         ({"step": "run", "max_usd": 0}, "outside what")):
            argv, w = TD.scholar_argv("MBh01", bad["step"], bad.get("pages", ""), bad.get("limit", 40),
                                      bad.get("max_usd", 0))
            self.assertIsNone(argv)
            self.assertIn(why, w)
        self.assertEqual(TD.scholar_argv("MBh01", "triage")[0], ["--doc", "MBh01", "--triage", "--engine",
                                                                 TD.SCHOLAR_ENGINE])
        self.assertEqual(TD.SCHOLAR_SOP, ("--engine", "anthropic:claude-sonnet-5-5", "--compare-engine",
                                          "anthropic:claude-opus-5-5", "--audit-every", "10", "--no-compare"))
        try:
            import bench_mitra
            self.assertEqual(tuple(bench_mitra.SCHOLAR_FLAGS), TD.SCHOLAR_SOP, "the flags BM1 and BM3 measured")
        except ImportError:
            pass

    def test_the_plans_cap(self):
        out = ("VERDICT: 40 verse(s) ready, about $1.71; 3 left out\n"
               "NEXT: python scripts\\scholar_translate.py --doc MBh01 --limit 40 --yes --max-usd 2.14\n")
        self.assertEqual(TD.cap_of(out), 2.14)
        self.assertIsNone(TD.cap_of("NEXT: python scripts\\scholar_translate.py --doc MBh01 --report"))
        self.assertIsNone(TD.cap_of(""))

    def test_the_chart_is_read_again_only_when_it_changes(self):
        tmp = Path(tempfile.mkdtemp(prefix="td_chart_"))
        try:
            p = tmp / "text_path.json"
            p.write_text(json.dumps({"at": "2026-10-14T22:18:42", "texts": chart_rows()}), encoding="utf-8")
            a = TD.load_path(p)
            self.assertIs(TD.load_path(p), a)
            self.assertEqual(a["at"], "2026-10-14T22:18:42")
            self.assertEqual(len(a["texts"]), 8)
            time.sleep(0.05)
            p.write_text(json.dumps({"at": "2026-10-17T09:00:00", "texts": chart_rows()[:2]}), encoding="utf-8")
            b = TD.load_path(p)
            self.assertEqual((b["at"], len(b["texts"])), ("2026-10-17T09:00:00", 2))
            p.unlink()
            self.assertEqual(TD.load_path(p), {"at": "", "texts": {}})
            p.write_text("not json", encoding="utf-8")
            self.assertEqual(TD.load_path(p), {"at": "", "texts": {}})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(APPLIED, "TRANSLATION_DESK_2026_10_17 is not applied here")
class TheDesk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_bench_desk_2026_10_16 as T
        cls.d = T.load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()
        cls.node = staticmethod(T.node)

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        import test_scholar_2026_10_14 as base
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        (self.td / "fx").mkdir()
        db = base.fixture(self.td / "fx", register=[
            {"doc": "HeldText", "status": "withdrawn", "at": "2026-10-16T13:28:00", "reason": "a better source first"},
            {"doc": "RepairedText", "status": "in_repair", "at": "2026-10-11", "reason": "re-translating"}])
        ST = base.ST
        con = sqlite3.connect(db)
        ST.ensure_schema(con)
        for code in ("ReadyText", "RepairText", "ChangedText", "HeldText", "RepairedText", "JudgeText", "DoneText"):
            con.execute("INSERT INTO docs(code, category) VALUES (?, 'x')", (code,))
            did = con.execute("SELECT id FROM docs WHERE code = ?", (code,)).fetchone()[0]
            for k in range(1, 4):
                con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type) VALUES (?,?,?,?,?,?)",
                            (did, 1, k, "\u0927\u0930\u094d\u092e %s %d" % (code, k), "E //" if code == "JudgeText" else "",
                             "mula"))
        allp = ST.load_text(con, "MBh01")
        for x, st in ((allp[0], "passed"), (allp[1], "flagged")):
            ST.store(con, {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"],
                           "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]), "translation": "S //", "notes": "[]",
                           "critique": "[]", "status": st, "engine": "anthropic:claude-sonnet-5-5", "judge_engine": ST.JUDGE,
                           "cost_usd": 0.04, "created_at": "2026-10-16T12:00:00+00:00"})
        con.commit()
        con.close()
        self.db = db
        self.chart = self.td / "text_path.json"
        self.chart.write_text(json.dumps({"mark": "PATH_2026_10_12", "at": "2026-10-01T10:00:00", "texts": chart_rows()}),
                              encoding="utf-8")
        self.saved = (self.d.PATH_FILE, self.d.DESK_DB)
        self.d.PATH_FILE, self.d.DESK_DB = self.chart, str(db)
        self.d._DESK_CACHE.update(res=None)
        self.d._SCHOLAR_COVER.update(key=None, at=0.0, res={})

    def tearDown(self):
        self.d.PATH_FILE, self.d.DESK_DB = self.saved
        self.d._DESK_CACHE.update(res=None)
        self.tmp.cleanup()

    def launched(self, url, body):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j9")
        try:
            r = self.c.post(url, json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_the_desk(self):
        r = self.c.get("/desk")
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        for s in ("The scholarly edition (1)", "Ready to translate (2)", "Translated: to judge (1)", "Done (1)",
                  "The reading first (3)", 'href="/desk/MBh01"', "Mah\u0101bh\u0101rata, Book I",
                  "2 of 6 <span class=\"small\">(1 passed, 1 flagged, 0 doubts)</span>",
                  "the scholarly English: plan the next 4 verses (free), then run them", "Chart the path again (free)",
                  "charted 2026-10-01 10:00", "old: chart it again", "withdrawn"):
            self.assertIn(s, h)
        if self.node():
            p = self.td / "desk.js"
            p.write_text(re.findall(r"<script>(.*?)</script>", h, re.S)[0], encoding="utf-8")
            res = subprocess.run([self.node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_a_texts_page(self):
        h = self.c.get("/desk/MBh01").get_data(as_text=True)
        self.assertIn("Plan them (free)", h)
        self.assertIn("deskStep('MBh01', 'plan', this)", h)
        self.assertIn("2 of 6 verses: 1 passed, 1 flagged", h)
        self.assertIn(" ".join(TD.SCHOLAR_SOP), h)
        h = self.c.get("/desk/RepairText").get_data(as_text=True)
        self.assertIn("Not offered: its path says the reading comes first (repair the scan)", h)
        self.assertNotIn("Plan them (free)", h)
        self.assertIn('href="/repair/RepairText"', h)
        h = self.c.get("/desk/HeldText").get_data(as_text=True)
        self.assertIn("Not offered: it is withdrawn (the register): a better source first", h)
        h = self.c.get("/desk/RepairedText").get_data(as_text=True)
        self.assertIn("In repair: run with --held-ok", h)
        h = self.c.get("/desk/ReadyText").get_data(as_text=True)
        self.assertIn("deskTranslate('ReadyText', this)", h)
        self.assertEqual(self.c.get("/desk/Nothing").status_code, 404)

    def test_the_scholarly_steps(self):
        r, got = self.launched("/api/desk/scholar", {"doc": "MBh01", "step": "plan", "limit": 40})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("scholar", "scholar:MBh01", "plan"))
        self.assertTrue(str(argv[-14]).endswith("scholar_translate.py"), argv)
        self.assertEqual(argv[-13:], ["--db", str(self.db), "--doc", "MBh01", "--limit", "40"] + list(TD.SCHOLAR_SOP))
        r, got = self.launched("/api/desk/scholar", {"doc": "MBh01", "step": "run", "limit": 40, "max_usd": 2.14})
        self.assertEqual(got[0][2][-3:], ["--yes", "--max-usd", "2.14"])
        r, got = self.launched("/api/desk/scholar", {"doc": "RepairedText", "step": "plan", "limit": 3})
        self.assertIn("--held-ok", got[0][2])
        for body, code, why in (({"doc": "MBh01", "step": "run", "max_usd": 13}, 400, "outside what"),
                                ({"doc": "HeldText", "step": "plan"}, 409, "withdrawn"),
                                ({"doc": "RepairText", "step": "plan"}, 409, "the reading comes first"),
                                ({"doc": "MBh01", "step": "drop"}, 400, "unknown step"),
                                ({"doc": "../x", "step": "plan"}, 400, "invalid")):
            r, got = self.launched("/api/desk/scholar", body)
            self.assertEqual(r.status_code, code, body)
            self.assertIn(why, r.get_json()["error"])
            self.assertEqual(got, [])
        r, got = self.launched("/api/desk/scholar", {"doc": "HeldText", "step": "report"})
        self.assertEqual(got[0][2][-1], "--report", "the free steps stay open")

    def test_the_guard(self):
        for url in ("/api/translate", "/api/pipeline/translate-doc"):
            r, got = self.launched(url, {"doc": "RepairText", "lang": "en"})
            self.assertEqual(r.status_code, 409, url)
            j = r.get_json()
            self.assertTrue(j["needs_force"])
            self.assertEqual(j["path"], "repair")
            self.assertIn("repair_text.py --doc RepairText --repair", j["say"])
            self.assertEqual(got, [])
            r, got = self.launched(url, {"doc": "RepairText", "lang": "en", "force": True})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(got), 1)
            r, got = self.launched(url, {"doc": "ReadyText", "lang": "en"})
            self.assertEqual((r.status_code, len(got)), (200, 1))
        self.d.PATH_FILE = self.td / "none.json"
        r, got = self.launched("/api/translate", {"doc": "RepairText", "lang": "en"})
        self.assertEqual((r.status_code, len(got)), (200, 1), "no chart: nothing is held")

    def test_the_rows_carry_their_path(self):
        rows = self.d._status_decorate([{"doc": "RepairText"}, {"doc": "ReadyText"}, {"doc": "Other"}], self.db)
        self.assertEqual(rows[0]["path"]["path"], "repair")
        self.assertTrue(rows[0]["path"]["held"])
        self.assertEqual(rows[0]["path"]["at"], "2026-10-01")
        self.assertFalse(rows[1]["path"]["held"])
        self.assertNotIn("path", rows[2])


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_main_page(self):
        h = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        for s in ('href="/desk" target="_blank"', "var p = r.path;", "the reading first: ",
                  "if (r.status === 409 && j.needs_force)", "async function startDoc(doc, opts)",
                  "await startDoc(docs[i], {bulk: true}) === 'held'", "force: true"):
            self.assertIn(s, h)
        import test_bench_desk_2026_10_16 as T
        if T.node():
            with tempfile.TemporaryDirectory() as td:
                for k, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
                    p = Path(td) / ("s%d.js" % k)
                    p.write_text(js, encoding="utf-8")
                    r = subprocess.run([T.node(), "--check", str(p)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/dashboard_static.html")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_transdesk_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the files")
        pat = [sys.executable, str(SCRIPTS / "patch_translation_desk_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in self.FILES:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("scripts/translation_desk.py (this release) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "translation_desk.py", t / "scripts" / "translation_desk.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "dashboard_static.html"
            p.write_bytes(p.read_bytes().replace(b"async function startDoc(doc) {", b"async function startDoc(d) {"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard_static.html: anchor 4 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "translation_desk.py", SCRIPTS / "patch_translation_desk_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
