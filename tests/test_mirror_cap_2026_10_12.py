# -*- coding: ascii -*-
"""MIRROR_CAP_2026_10_12: the mirror's retire of a withdrawn or retired text no longer times out (vectors 25 to a
call, a timed-out retire sent again in halves); --max-usd stops a vision run before a page would take it past (what
it has spent read from usage_log); the chart gives the median text's price beside the corpus's. Temp files only,
never data/context.db."""
import importlib.util, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_sync as cs                      # noqa: E402
import test_corpus_sync_2026_10_08 as base    # noqa: E402

TIMEOUT = ("corpus-ingest HTTP 422: {\"ok\":false,\"error\":\"corpus_retire: canceling statement due to statement "
           "timeout\"}")
ENG = "gemini-vision:gemini-2.5-flash"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class SlowRetire(base.FakeSink):
    """Times out retiring more than `limit` vectors in one call, as the HNSW index did on 12 Oct."""

    def __init__(self, server, limit=1, error=TIMEOUT):
        super().__init__(server)
        self.limit, self.error, self.sizes = limit, error, []

    def retire(self, table, group, keys, run_id):
        if table == "vectors":
            self.sizes.append(len(keys))
            if len(keys) > self.limit:
                raise cs.SinkError(self.error)
        return super().retire(table, group, keys, run_id)


class TheMirrorRetire(base.Base):
    def setUp(self):
        super().setUp()
        self.v = Path(self.tmp.name) / "verdicts.jsonl"
        self.old = os.environ.get("SA_SOURCE_VERDICTS")
        os.environ["SA_SOURCE_VERDICTS"] = str(self.v)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("SA_SOURCE_VERDICTS", None)
        else:
            os.environ["SA_SOURCE_VERDICTS"] = self.old
        super().tearDown()

    def withdraw(self, doc="AphorismsOfSandilya"):
        self.v.write_text(json.dumps({"doc": doc, "status": "withdrawn"}) + "\n", encoding="utf-8")

    def test_vectors_are_retired_25_to_a_call(self):
        self.assertEqual(cs.MAX_VEC_KEYS_PER_RETIRE, 25)
        self.assertEqual(self.sync()["stopped"], "done")
        self.withdraw()
        old = cs.MAX_VEC_KEYS_PER_RETIRE
        cs.MAX_VEC_KEYS_PER_RETIRE = 3
        try:
            sink = SlowRetire(self.server, limit=3)
            s = self.sync(sink=sink)
        finally:
            cs.MAX_VEC_KEYS_PER_RETIRE = old
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(sink.sizes, [3, 1])
        for t in ("passages", "translations", "vectors"):
            rows = self.server.t[t].get("AphorismsOfSandilya", {})
            self.assertTrue(rows and all(r["retired"] for r in rows.values()), t)
        self.assertTrue(all(not r["retired"] for r in self.server.t["passages"]["markandeya_purana"].values()))

    def test_a_timed_out_retire_is_sent_again_in_halves(self):
        self.sync()
        self.withdraw()
        notes = []
        sink = SlowRetire(self.server, limit=1)
        s = self.sync(sink=sink, progress=notes.append)
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(sink.sizes[0], 4)
        self.assertIn(1, sink.sizes)
        self.assertTrue(any("vectors AphorismsOfSandilya: the database timed out retiring 4 rows; sending them as 2 + 2"
                            in n for n in notes), notes)
        self.assertEqual(s["tables"]["vectors"]["retired"], 4)
        self.assertTrue(all(r["retired"] for r in self.server.t["vectors"]["AphorismsOfSandilya"].values()))
        again = self.sync(sink=SlowRetire(self.server, limit=1))
        self.assertEqual(again["stopped"], "done"); self.assertEqual(again["tables"]["vectors"]["retire"], 0)

    def test_another_error_and_a_one_key_timeout_stop_the_run(self):
        self.sync()
        self.withdraw()
        s = self.sync(sink=SlowRetire(self.server, limit=1, error="corpus-ingest HTTP 401: bad signature"))
        self.assertEqual(s["stopped"], "error"); self.assertIn("bad signature", s["error"])
        s = self.sync(sink=SlowRetire(self.server, limit=0))
        self.assertEqual(s["stopped"], "error"); self.assertIn("statement timeout", s["error"])


class TheRunCap(unittest.TestCase):
    def setUp(self):
        self.oc = load("ocr_consensus_mirrorcap", SCRIPTS / "ocr_consensus.py")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.db = str(self.t / "c.db")
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE usage_log(id INTEGER PRIMARY KEY, kind TEXT, doc TEXT, engine TEXT, in_tokens REAL, "
                    "out_tokens REAL, passages INTEGER, token_source TEXT)")
        con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, passages, token_source) VALUES "
                    "('ocr_vision', 'N', ?, 1000, 4000, 1, 'provider')", (ENG,))   # before the run: not counted
        con.commit(); con.close()
        import cost_tracker
        pin, pout = cost_tracker._get_pricing(ENG)
        self.page = (1000 * pin + 4000 * pout) / 1e6
        self.v = self.t / "vision"; self.v.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def bill(self, doc="N", n=1):
        con = sqlite3.connect(self.db)
        for _ in range(n):
            con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, passages, token_source) VALUES "
                        "('ocr_vision', ?, ?, 1000, 4000, 1, 'provider')", (doc, ENG))
        con.commit(); con.close()

    def test_what_the_run_has_spent(self):
        mark = self.oc.usage_mark(self.db)
        self.assertEqual(mark, 1)
        self.assertEqual(self.oc.spent_since(self.db, "N", mark), 0.0)
        self.bill(n=3); self.bill(doc="Other")
        self.assertAlmostEqual(self.oc.spent_since(self.db, "N", mark), 3 * self.page)
        self.assertEqual(self.oc.usage_mark(str(self.t / "none.db")), 0)
        self.assertEqual(self.oc.spent_since(str(self.t / "none.db"), "N", 0), 0.0)

    def test_the_run_stops_before_a_page_would_pass_the_cap(self):
        mark = self.oc.usage_mark(self.db)
        cap = self.oc.run_cap(self.db, "N", 3.5 * self.page, self.page, mark)
        calls = []

        def runner(argv):
            out = Path(argv[argv.index("--out") + 1])
            calls.append(out.stem)
            self.bill()
            if out.stem != "N_0002":
                out.write_text(json.dumps({"text": "\u0915\u0916\u0917"}) + "\n", encoding="utf-8")
            return 0
        led = {}
        todo = [str(self.t / ("N_%04d.pdf" % i)) for i in range(1, 9)]
        ok, fails, stopped = self.oc.run_vision(todo, self.v, "N", led, budget=lambda: True, runner=runner, cap=cap)
        self.assertEqual(len(calls), 3, "3 pages fit under 3.5 pages' worth; the fourth would pass it")
        self.assertEqual((ok, fails), (2, 1)); self.assertEqual(led["N_0002"]["fails"], 1, "a failure under the cap is a failure")
        self.assertIn("this run's --max-usd $", stopped); self.assertIn("is reached", stopped)
        ok, fails, stopped = self.oc.run_vision(todo[:1], self.v, "N", {}, runner=runner, cap=None)
        self.assertEqual((ok, stopped), (1, ""), "no cap: as before")

    def test_main_and_the_redo_round_use_it(self):
        s = (SCRIPTS / "ocr_consensus.py").read_text(encoding="utf-8")
        self.assertIn("_cap = run_cap(args.db, doc, args.max_usd, cpp, _mark)", s)
        self.assertIn("run_vision(todo, vdir, doc, led, args.model, _budget, cap=_cap)", s)
        self.assertIn("STOPPING the redo round", s)


class TheMedianPrice(unittest.TestCase):
    TP = None

    @classmethod
    def setUpClass(cls):
        cls.TP = load("text_path_mirrorcap", SCRIPTS / "text_path.py")

    def test_the_median_of_the_texts_measured(self):
        import cost_tracker
        pin, pout = cost_tracker._get_pricing(ENG)
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con = sqlite3.connect(str(db))
            con.execute("CREATE TABLE usage_log(id INTEGER PRIMARY KEY, kind TEXT, doc TEXT, engine TEXT, in_tokens REAL, "
                        "out_tokens REAL, passages INTEGER, token_source TEXT, cost_usd REAL)")
            for doc, tout in (("A", 1000), ("B", 2000), ("C", 9000)):
                for _ in range(25):
                    con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, passages, token_source) "
                                "VALUES('ocr_vision', ?, ?, 1000, ?, 1, 'provider')", (doc, ENG, tout))
            con.commit(); con.close()
            pr = self.TP.prices(str(db), {"A", "B", "C"})
            two = self.TP.prices(str(db), {"A", "B"})
        self.assertAlmostEqual(pr["vision_median"], round((1000 * pin + 2000 * pout) / 1e6, 5), places=5)
        self.assertIsNone(two["vision_median"], "fewer than 3 texts measured: no median")

    def test_the_estimate_beside_the_corpus_price(self):
        pr = {"vision_page": 0.0100, "vision_dear": 0.0111, "vision_median": 0.0024, "measured": ["N"], "passage": 0.00045,
              "passage_from": "usage_log"}
        f = {"doc": "P", "state": None, "passages": 1000, "english": 0, "hindi": 0, "below_quality": 0, "vision_pct": 0.0,
             "level": "moderate", "misread_letters_pct": 1.56, "pdfs": 364, "raw_pages": 364, "vision_pages": 0,
             "merged_pages": 0, "merged_complete": False, "cost_per_page": 0.0100, "db_pages": 364, "reviews": None,
             "vectors": 0, "price_from": "the corpus"}
        o = self.TP.decide(f, pr)
        self.assertEqual(o["path"], "repair")
        self.assertTrue(o["next"][0].startswith("python scripts\\repair_text.py --doc P --repair --max-usd 4.60"), o["next"][0])
        self.assertIn("; about $0.874 at the median text's $0.0024; it stops at the cap", o["next"][0])
        self.assertAlmostEqual(o["cost"], 3.64); self.assertAlmostEqual(o["cost_lo"], 364 * 0.0024)
        self.assertEqual(self.TP.money_line({"cost": 37.83, "cost_hi": 41.12, "cost_lo": 9.1, "then": 49.79}),
                         "about $37.83 now (from $9.10 at the median text's price; up to $41.12 at the dearest text's "
                         "price); then about $49.79 to translate")
        o = self.TP.decide(dict(f, cost_per_page=0.0111, price_from="this text"), pr)
        self.assertAlmostEqual(o["cost_lo"], o["cost"], msg="measured on this text: one price")


class TheDashboard(unittest.TestCase):
    def test_the_path_page_shows_the_median(self):
        d = load("dashboard_mirrorcap", SCRIPTS / "dashboard.py")
        res = {"mark": "PATH_2026_10_12", "at": "2026-10-12T13:37:02", "paths": [["repair", "Repair the scan", "x"]],
               "prices": {"vision_page": 0.01002, "vision_dear": 0.01109, "vision_median": 0.00237, "measured": ["N"] * 10,
                          "passage": 0.000449},
               "totals": {"repair": {"texts": 1, "cost": 37.83, "cost_hi": 41.12, "cost_lo": 9.1, "then": 49.79}},
               "texts": [{"doc": "N", "path": "repair", "why": "w", "next": [], "also": [], "cost": 37.83, "then": 49.79}]}
        with tempfile.TemporaryDirectory() as td:
            old = d.PATH_FILE
            d.PATH_FILE = Path(td) / "p.json"
            d.PATH_FILE.write_text(json.dumps(res), encoding="utf-8")
            try:
                h = d.app.test_client().get("/path").get_data(as_text=True)
            finally:
                d.PATH_FILE = old
        self.assertIn("about $37.83 now (from $9.10 at the median text's price; up to $41.12 at the dearest text's price)", h)
        self.assertIn("its last 300 calls (10 text(s) priced from their own calls; the median $0.0024, the dearest $0.0111", h)


class ThePatcher(unittest.TestCase):
    FILES = ("corpus_sync.py", "ocr_consensus.py", "text_path.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_mirrorcap_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            pat = [sys.executable, str(SCRIPTS / "patch_mirror_cap_2026_10_12.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_readin_*"))   # READ_IN_2026_10_13 came after
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b'hi = tt.get("cost_hi") or 0', b'hi = 0'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"MIRROR_CAP_2026_10_12", (t / "scripts" / "corpus_sync.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "patch_mirror_cap_2026_10_12.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"MIRROR_CAP_2026_10_12", b)


if __name__ == "__main__":
    unittest.main()
