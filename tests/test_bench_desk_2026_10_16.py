# -*- coding: ascii -*-
"""BENCH_DESK_2026_10_16: the dashboard shows the state of things, wired to what can be done about it. BM1 on the
Benchmarks page (what each arm has made, the judge, the spend, the report, the next step as a capped button, the
private report served here); each row of /api/status with its register state and its scholarly English; /api/usage
with the Claude credit, the steps by kind, BM1's line; bench_mitra's arms priced by their own spend; the report's NEXT
in PowerShell. A made-up dataset and temp folders; the scripts and the judge are stand-ins; nothing is called."""
import importlib.util, json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_mitra as B                       # noqa: E402
import test_bench_mitra_2026_10_16 as TB      # noqa: E402

MARK = b"BENCH_DESK_2026_10_16"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()
KEYS = TB.KEYS


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_benchdesk", str(SCRIPTS / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def node():
    return shutil.which("node")


@unittest.skipUnless(APPLIED and TB.HAVE_TR, "BENCH_DESK_2026_10_16 is not applied here, or no transliterator")
class TheDesk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = TB.dataset(self.td)
        self.main = TB.ledger(self.td)
        self.out = self.td / "bm1"
        self.args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.out), "--files", ",".join(KEYS)]
        self.saved = (B.FILES, B.arm_cmd, B.ST.Gemini, self.d.BM1_DIR, self.d.BM1_LEDGER)
        B.FILES = tuple(f for f in B.FILES if f["key"] in KEYS)   # the made-up dataset has two texts
        self.d.BM1_DIR, self.d.BM1_LEDGER = self.out, str(self.main)
        self.d._BM1_CACHE.update(res=None)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        B.ST.Gemini = TB.FakeGemini

    def tearDown(self):
        B.FILES, B.arm_cmd, B.ST.Gemini, self.d.BM1_DIR, self.d.BM1_LEDGER = self.saved
        self.d._BM1_CACHE.update(res=None)
        self.tmp.cleanup()

    def page(self):
        r = self.c.get("/benchmarks")
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def post(self, body):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j1")
        try:
            r = self.c.post("/api/bench", json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_before_the_sample(self):
        s = self.c.get("/api/bench?fresh=1").get_json()
        self.assertFalse(s["made"])
        h = self.page()
        self.assertIn("Translation benchmark: BM1", h)
        self.assertIn('data-step="sample"', h)
        self.assertIn("Make the sample (free)", h)

    def test_the_state_the_page_and_the_steps(self):
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        s = self.c.get("/api/bench?fresh=1").get_json()
        self.assertTrue(s["made"])
        self.assertEqual([t["verses"] for t in s["texts"]], [25, 25])
        self.assertEqual({a: v["left"] for a, v in s["arms"].items()}, {"flash": 50, "sonnet1": 50, "scholar": 50})
        self.assertEqual(s["next"]["step"], "arm"); self.assertEqual(s["next"]["arm"], "flash")
        self.assertEqual(len(s["missing"]), 6); self.assertIsNone(s["to_judge"])
        h = self.page()
        self.assertIn('data-step="arm" data-arm="flash"', h)
        self.assertIn("Run flash on the 50 verse(s) it has not made: it spends at most", h)
        self.assertIn("The judge waits until every arm has its English", h)
        self.assertIn("The Claude credit: <b>$79.63</b> left", h)
        for arm in B.ARMS:
            self.assertEqual(B.main(self.args + ["--arm", arm, "--yes"]), 0)
        s = self.c.get("/api/bench?fresh=1").get_json()
        self.assertEqual({a: v["left"] for a, v in s["arms"].items()}, {"flash": 0, "sonnet1": 0, "scholar": 0})
        self.assertEqual(s["missing"], []); self.assertEqual(s["to_judge"], 2 * 24 * 4)
        self.assertEqual(s["next"]["step"], "score")
        self.assertAlmostEqual(s["prices"]["flash"], 0.002, places=6, msg="the arm's own price")
        self.assertAlmostEqual(s["spend"]["sonnet1"]["claude"], 0.5, places=4)
        h = self.page()
        self.assertIn('data-step="score"', h); self.assertIn("Judge them: 192 English", h)
        self.assertIn("25/25 &#10003;", h)
        self.assertNotIn("The last report", h, "no report yet")
        self.assertEqual(B.main(self.args + ["--score", "--judge-reference", "--yes"]), 0)
        self.assertEqual(B.main(self.args + ["--report"]), 0)
        s = self.c.get("/api/bench?fresh=1").get_json()
        self.assertIsNone(s["next"]); self.assertFalse(s["stale"])
        h = self.page()
        self.assertIn("The last report (", h); self.assertIn("<b>Done:</b>", h)
        self.assertIn("scholar - flash: chrF", h); self.assertIn("<b>+2.00 [+2.00, +2.00]</b>", h)
        self.assertNotIn("PUBLISHED", h, "the page holds numbers, not the dataset's English")
        r = self.c.get("/benchmarks/bm1/report")
        self.assertEqual(r.status_code, 200); self.assertEqual(r.headers.get("Cache-Control"), "no-store")
        self.assertIn("Private evaluation.", r.get_data(as_text=True))
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.td / "b.js"; p.write_text(js, encoding="utf-8")
            res = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_the_posts(self):
        r, got = self.post({"step": "arm", "arm": "flash", "max_usd": 0.4})
        self.assertEqual(r.status_code, 200)
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("bench", "BM1", "arm flash"))
        self.assertTrue(str(argv[-6]).endswith("bench_mitra.py"))
        self.assertEqual(argv[-5:], ["--arm", "flash", "--yes", "--max-usd", "0.40"])
        r, got = self.post({"step": "score", "max_usd": 2.75})
        self.assertEqual(got[0][2][-5:], ["--score", "--judge-reference", "--yes", "--max-usd", "2.75"])
        for body in ({"step": "report"}, {"step": "settle"}, {"step": "sample"}):
            r, got = self.post(body)
            self.assertEqual(got[0][2][-1], "--" + body["step"])
        for body, why in (({"step": "arm", "arm": "gpt", "max_usd": 1}, "arm must be one of"),
                          ({"step": "arm", "arm": "scholar", "max_usd": 13}, "run it by hand"),
                          ({"step": "score"}, "max_usd must be a number"),
                          ({"step": "arm", "arm": "flash", "max_usd": 0}, "outside what one press may spend"),
                          ({"step": "drop"}, "unknown step")):
            r, got = self.post(body)
            self.assertEqual(r.status_code, 400, body); self.assertIn(why, r.get_json()["error"]); self.assertEqual(got, [])
        self.assertEqual(self.c.get("/benchmarks/bm1/report").status_code, 404)

    def test_the_usage(self):
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        self.assertEqual(B.main(self.args + ["--arm", "flash", "--yes"]), 0)
        con = sqlite3.connect(self.main)
        con.execute("CREATE TABLE IF NOT EXISTS mt_cache(id INTEGER PRIMARY KEY)")   # as data/context.db has it
        con.commit(); con.close()
        j = self.c.get("/api/usage?db=%s" % self.main).get_json()
        self.assertEqual((j["credit"]["cap"], round(j["credit"]["spent"], 2), j["credit"]["since"]), (190.0, 110.37, "2026-10-15"))
        kinds = {(k["kind"], k["bill"]): k for k in j["kinds_since"]["rows"]}
        self.assertEqual(kinds[("bench_translation", "google")]["calls"], 50)
        self.assertEqual(kinds[("scholar", "claude")]["calls"], 1)
        self.assertTrue(j["bm1"]["made"])
        self.assertIn("flash 50, sonnet1 0, scholar 0 of 50 verses made; the judge waits for every arm", j["bm1"]["line"])
        self.assertIn("budget", j); self.assertIn("by_engine", j)

    def test_the_rows_of_the_table(self):
        import test_scholar_2026_10_14 as base
        (self.td / "fx").mkdir()
        db = base.fixture(self.td / "fx")
        ST = base.ST
        con = sqlite3.connect(db)
        ST.ensure_schema(con)
        allp = ST.load_text(con, "MBh01")
        for x, st in ((allp[0], "passed"), (allp[1], "flagged")):
            ST.store(con, {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"],
                           "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]), "translation": "S //", "notes": "[]",
                           "critique": "[]", "status": st, "engine": "anthropic:claude-sonnet-5-5", "judge_engine": ST.JUDGE,
                           "cost_usd": 0.04, "created_at": "2026-10-16T12:00:00+00:00"})
        con.commit(); con.close()
        (Path(db).parent / "source_verdicts.jsonl").write_text(json.dumps(
            {"doc": "MBh01", "status": "withdrawn", "at": "2026-10-16T13:28:00", "reason": "a better source first"}) + "\n",
            encoding="utf-8")
        self.d._SCHOLAR_COVER.update(key=None, at=0.0, res={})
        rows = self.d._status_decorate([{"doc": "MBh01", "total_lines": 9}, {"doc": "Other"}], db)
        self.assertEqual(rows[0]["held"], {"status": "withdrawn", "at": "2026-10-16", "reason": "a better source first"})
        self.assertEqual((rows[0]["scholar"]["verses"], rows[0]["scholar"]["passed"], rows[0]["scholar"]["flagged"]), (2, 1, 1))
        self.assertEqual(rows[0]["total_lines"], 9)
        self.assertEqual(rows[1], {"doc": "Other"})
        self.assertEqual(self.d._status_decorate([{"doc": "X"}], self.td / "none" / "c.db"), [{"doc": "X"}], "no database")


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_dashboard_page(self):
        h = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        for s in ('href="/benchmarks"', "function docStateHtml(r)", "compLine + docStateHtml(r)", "function creditHtml(c)",
                  "budgetHtml(d.budget) + creditHtml(d.credit) + bm1UsageHtml(d.bm1)", "Object.keys(eng)",
                  "function kindLabel(k)", "bench_translation: 'BM1: one pass'", "The spend cap (Google)",
                  "a Claude step stops at the credit below", "d.kinds_since.rows"):
            self.assertIn(s, h)
        self.assertNotIn("d.by_engine.length", h)
        if node():
            with tempfile.TemporaryDirectory() as td:
                for k, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
                    p = Path(td) / ("s%d.js" % k); p.write_text(js, encoding="utf-8")
                    r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipUnless(TB.HAVE_TR, "no transliterator")
class TheHarness(unittest.TestCase):
    def test_the_report_says_powershell(self):
        b = (SCRIPTS / "bench_mitra.py").read_text(encoding="ascii")
        if "BENCH_DESK_2026_10_16" not in b:
            self.skipTest("not applied here")
        self.assertIn("NEXT: Start-Process", b); self.assertNotIn('NEXT: start \\"\\"', b)
        self.assertIn("def prices(mcon, out=None) -> dict:", b)
        self.assertIn('Start-Process "D:', (REPO / "docs" / "BENCH_MITRA_2026-10-16.md").read_text(encoding="utf-8"))


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/dashboard_static.html", "scripts/bench_mitra.py", "docs/BENCH_MITRA_2026-10-16.md")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_benchdesk_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the files")
        pat = [sys.executable, str(SCRIPTS / "patch_bench_desk_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in self.FILES:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
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
            p = t / "scripts" / "dashboard_static.html"
            p.write_bytes(p.read_bytes().replace(b"function renderPipeline(rows) {", b"function renderPipeline(rs) {"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard_static.html: anchor 3 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_bench_desk_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
