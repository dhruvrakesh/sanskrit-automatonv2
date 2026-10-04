# -*- coding: ascii -*-
"""METER_GATES_2026_10_04 + DIAG_ORPHANS_2026_10_04. No network: the Gemini client is stubbed.
Fails before patch_meter_gates_2026_10_04.py, passes after (diag_orphans.py is a new file)."""
import importlib, io, os, sqlite3, subprocess, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DIM = 8


class _Usage:
    prompt_token_count = 1000
    candidates_token_count = 200
    thoughts_token_count = 300


class _Resp:
    text = "An answer [D p1.1]."
    usage_metadata = _Usage()


def _stub_genai(calls):
    g = types.ModuleType("google.generativeai")
    g.configure = lambda **kw: None
    g.GenerationConfig = lambda **kw: kw

    def embed_content(model, content, task_type=None):
        calls.append(("embed", task_type))
        return {"embedding": [1.0] + [0.0] * (DIM - 1)}
    g.embed_content = embed_content

    class GenerativeModel:
        def __init__(self, **kw):
            pass

        def generate_content(self, *a, **kw):
            calls.append(("generate",))
            return _Resp()
    g.GenerativeModel = GenerativeModel
    sys.modules["google.generativeai"] = g
    if "google" not in sys.modules:
        sys.modules["google"] = types.ModuleType("google")
    sys.modules["google"].generativeai = g


class Base(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('D')")
        con.execute("INSERT INTO docs(code) VALUES('D_v2')")
        for i in range(1, 4):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) "
                        "VALUES(1,1,?,?,?, 'mula')", (i, "sa %d" % i, "The king %d." % i))
        for i in range(1, 6):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) "
                        "VALUES(2,1,?,?,?, 'mula')", (i, "sa %d" % i, "The king %d." % i))
        con.commit(); con.close()
        self._saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
        self._google_attr = getattr(sys.modules.get("google"), "generativeai", None) if sys.modules.get("google") else None
        self._key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        self.calls = []
        _stub_genai(self.calls)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        if self._saved.get("google") is not None and self._google_attr is not None:
            self._saved["google"].generativeai = self._google_attr
        if self._key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self._key
        self.tmp.cleanup()

    def sql(self, q, *a):
        con = sqlite3.connect(self.db)
        try:
            r = con.execute(q, a).fetchall(); con.commit(); return r
        finally:
            con.close()

    def budget(self, cap, spent=0.0, paused=0):
        import cost_tracker
        con = sqlite3.connect(self.db); cost_tracker.ensure_usage_schema(con)
        con.execute("INSERT OR REPLACE INTO budget_state(id, budget_usd, spent_usd, paused) VALUES(1,?,?,?)",
                    (cap, spent, paused))
        con.commit(); con.close()


class CorpusStatusCosts(Base):
    def test_vision_and_translation_are_measured_at_todays_prices(self):
        import cost_tracker, corpus_status
        importlib.reload(corpus_status)
        con = sqlite3.connect(self.db); cost_tracker.ensure_usage_schema(con)
        for _ in range(10):   # 2,000 in + 400 out tokens a page at (0.30, 2.50) = $0.0016 a page
            cost_tracker.log_api_call(con, kind="ocr_vision", doc="D", engine="gemini-vision:gemini-2.5-flash",
                                      in_tokens=2000, out_tokens=400, passages=1)
        for _ in range(3):    # 250 passages of provider-metered translation: 1M in + 100k out = $0.55
            cost_tracker.log_api_call(con, kind="translation", doc="D", engine="gemini:gemini-2.5-flash",
                                      in_tokens=1_000_000 / 3, out_tokens=100_000 / 3, passages=250 // 3 + 1)
        con.commit()
        cpp = corpus_status.translation_cost_per_passage(con); con.close()
        self.assertAlmostEqual(cpp, 0.55 / 252, places=6)
        self.assertIn("provider tokens", corpus_status.CPP_SOURCE["source"])
        self.assertAlmostEqual(corpus_status.vision_cost_per_page(self.db), 0.0016, places=6)
        cmds, est = corpus_status.consensus_cmds("D", {"pages_inbox": 100, "pages_vision": 0, "pages_refused": 0})
        self.assertAlmostEqual(est, 0.16, places=6)
        self.assertIn("--max-usd 0.19", cmds[1])          # 0.16 x 1.15 + 0.01, so ocr_consensus will not refuse

    def test_fallback_is_the_repriced_figure(self):
        import corpus_status
        importlib.reload(corpus_status)
        self.assertIsNone(corpus_status.vision_cost_per_page(self.db))
        _, est = corpus_status.consensus_cmds("D", {"pages_inbox": 10, "pages_vision": 0, "pages_refused": 0})
        self.assertAlmostEqual(est, 0.054, places=6)


class ImageEstimate(unittest.TestCase):
    def test_estimate_follows_size(self):
        import images
        tmp = tempfile.TemporaryDirectory()
        try:
            db = str(Path(tmp.name) / "i.db")
            import db_utils
            con = sqlite3.connect(db); db_utils.ensure_schema(con); images.ensure_schema(con)
            con.execute("INSERT INTO docs(code) VALUES('D')")
            con.execute("INSERT INTO doc_images(doc_id, kind, status, brief, title, anchor_page, anchor_idx) "
                        "VALUES(1, 'generated', 'brief-approved', 'a scene', 't', 1, 1)")
            con.commit(); con.close()
            out = {}
            for size in ("", "2K", "4K"):
                env = dict(os.environ, SA_IMAGE_SIZE=size, GEMINI_API_KEY="")
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / "images.py"), "--db", db,
                                    "--root", str(Path(tmp.name) / "img"), "generate", "--doc", "D"],
                                   capture_output=True, text=True, env=env, cwd=str(ROOT))
                out[size] = r.stdout + r.stderr
            self.assertIn("~$0.091 each", out[""], out[""])
            self.assertIn("~$0.125 each", out["2K"], out["2K"])
            self.assertIn("~$0.175 each", out["4K"], out["4K"])
        finally:
            tmp.cleanup()


class RetireDelta(Base):
    def test_preexisting_orphans_are_not_this_retirements_fault(self):
        self.sql("CREATE TABLE IF NOT EXISTS entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, "
                 "passage_id INTEGER, surface TEXT, created_at TEXT)")
        self.sql("CREATE TABLE IF NOT EXISTS passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, "
                 "vec BLOB, updated_at TEXT)")
        self.sql("INSERT INTO entity_mentions(entity_id, passage_id) VALUES(1, 99999)")   # already orphaned
        self.sql("INSERT INTO entity_mentions(entity_id, passage_id) VALUES(1, 1)")       # D's own, deleted with it
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "retire_doc.py"), "--db", self.db,
                            "--doc", "D", "--supersedes", "D_v2", "--yes"], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("orphaned mentions corpus-wide : 1  (before: 1)", r.stdout)
        self.assertIn("Pre-existing orphans", r.stdout)
        self.assertNotIn("NEW ORPHANS", r.stdout)
        self.assertEqual(self.sql("SELECT code FROM docs WHERE id=1")[0][0], "D-RETIRED")


class DiagOrphans(Base):
    def test_blocks_neighbours_and_reuse_warning(self):
        import diag_orphans
        self.sql("CREATE TABLE IF NOT EXISTS entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, "
                 "passage_id INTEGER, surface TEXT, created_at TEXT)")
        self.sql("DELETE FROM passages WHERE doc_id=1 AND idx=2")   # a hole at id 2
        for pid in (2, 200, 201):                                   # 200, 201 are above max id 8
            self.sql("INSERT INTO entity_mentions(entity_id, passage_id) VALUES(1, ?)", pid)
        buf = io.StringIO()
        with redirect_stdout(buf):
            res = diag_orphans.run(self.db, out=print)
        t = res["tables"]["entity_mentions"]
        self.assertEqual((t["orphans"], t["above_max"]), (3, 2))
        self.assertEqual([b[:2] for b in t["blocks"]], [(2, 2), (200, 201)])
        txt = buf.getvalue()
        self.assertIn("below: D (passage 1)", txt)
        if res["autoincrement"]:      # db_utils.BASE_SCHEMA declares AUTOINCREMENT
            self.assertIn("AUTOINCREMENT prevents reuse", txt)
        else:
            self.assertIn("Clean before ingesting", txt)
        con = sqlite3.connect(self.db)    # never wrote
        self.assertEqual(con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0], 3); con.close()


class AskIsMeteredAndGated(Base):
    def setUp(self):
        super().setUp()
        import numpy as np
        self.sql("CREATE TABLE IF NOT EXISTS passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, "
                 "vec BLOB, updated_at TEXT)")
        v = np.asarray([1.0] + [0.0] * (DIM - 1), dtype="float32").tobytes()
        for pid in (1, 2, 3):
            self.sql("INSERT INTO passage_embeddings VALUES(?, 'models/text-embedding-004', ?, ?, '2026-10-02')",
                     pid, DIM, v)
        import dashboard
        dashboard._ASK_VEC_CACHE.clear()
        self.c = dashboard.app.test_client()

    def test_metered(self):
        self.budget(25.0)
        r = self.c.post("/api/ask", json={"q": "king", "db": self.db, "k": 3})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        rows = dict((k, (s, i, o)) for k, s, i, o in self.sql(
            "SELECT kind, token_source, in_tokens, out_tokens FROM usage_log"))
        self.assertEqual(rows["ask"], ("provider", 1000.0, 500.0))   # thinking tokens counted as output
        self.assertIn("ask_embed", rows)

    def test_gated(self):
        self.budget(1.0, spent=2.0, paused=1)
        r = self.c.post("/api/ask", json={"q": "king", "db": self.db, "k": 3})
        self.assertEqual(r.status_code, 402)
        self.assertTrue(r.get_json()["sources"], "retrieval still answers, without the paid call")
        self.assertNotIn(("generate",), self.calls)


class EntitiesGated(Base):
    def test_stops_before_the_first_batch(self):
        import usage_meter, extract_entities
        importlib.reload(extract_entities)
        saved = usage_meter.budget_ok
        usage_meter.budget_ok = lambda *_a, **_k: False

        def boom(*a, **k):
            raise AssertionError("a paid batch ran with the cap reached")
        extract_entities._extract_chunk = boom
        argv0 = sys.argv
        sys.argv = ["extract_entities.py", "--db", self.db, "--sleep", "0"]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                extract_entities.main()
        finally:
            sys.argv = argv0
            usage_meter.budget_ok = saved
            importlib.reload(extract_entities)
        self.assertIn("spend cap is reached", buf.getvalue())


class StaticScan(unittest.TestCase):
    def test_every_paid_call_site_meters_and_asks(self):
        import spend_audit
        rows = {n: (m, g) for n, m, g in spend_audit.static_check(ROOT / "scripts")}
        for name in ("dashboard.py", "extract_entities.py", "judge_sample.py", "ab_source_quality.py"):
            if name in rows:
                self.assertEqual(rows[name], (True, True), name)


if __name__ == "__main__":
    unittest.main()
