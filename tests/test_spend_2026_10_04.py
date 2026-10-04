# -*- coding: ascii -*-
"""SPEND_TRUTH_2026_10_04 + SPEND_AUDIT_2026_10_04. No network: the Gemini SDK is stubbed.
Fails before patch_spend_2026_10_04.py, passes after."""
import importlib, io, json, os, sqlite3, subprocess, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"


class _UM:
    def __init__(self, i, o, t):
        self.prompt_token_count, self.candidates_token_count, self.thoughts_token_count = i, o, t


class _Resp:
    def __init__(self, text, finish, um):
        self.text = text
        self.candidates = [types.SimpleNamespace(finish_reason=finish)]
        self.usage_metadata = um


def _stub_sdk(script):
    """script: list of (text, finish) returned by successive generate_content calls."""
    g = types.ModuleType("google.generativeai")
    g.configure = lambda **kw: None
    g.GenerationConfig = lambda **kw: kw
    calls = iter(script)

    class GM:
        def __init__(self, **kw):
            pass

        def generate_content(self, msg, request_options=None):
            text, finish = next(calls)
            return _Resp(text, finish, _UM(100, 40, 60))
    g.GenerativeModel = GM
    saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
    sys.modules["google.generativeai"] = g
    if sys.modules.get("google") is None:
        sys.modules["google"] = types.ModuleType("google")
    old_attr = getattr(sys.modules["google"], "generativeai", None)
    sys.modules["google"].generativeai = g
    return saved, old_attr


def _restore(saved, old_attr):
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
    if saved.get("google") is not None and old_attr is not None:
        saved["google"].generativeai = old_attr


class Spend(unittest.TestCase):
    def setUp(self):
        import db_utils, cost_tracker
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
        con.execute("UPDATE budget_state SET budget_usd=100, spent_usd=0, paused=0 WHERE id=1")
        con.commit(); con.close()
        self._key = os.environ.get("GEMINI_API_KEY"); os.environ["GEMINI_API_KEY"] = "k"

    def tearDown(self):
        if self._key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self._key
        self.tmp.cleanup()

    def test_prices(self):
        import cost_tracker
        importlib.reload(cost_tracker)
        self.assertEqual(cost_tracker._get_pricing("gemini:gemini-2.5-flash"), (0.30, 2.50))
        self.assertEqual(cost_tracker._get_pricing("gemini-vision:gemini-2.5-flash"), (0.30, 2.50))
        self.assertEqual(cost_tracker._get_pricing("some-new-engine"), (0.30, 2.50))

    def test_translation_is_metered_from_provider_tokens_including_the_ladder(self):
        # first call truncates (MAX_TOKENS=2); the ladder's first rung succeeds -> 2 calls
        saved, old = _stub_sdk([("partial", 2), ("The full verse.", 1)])
        try:
            import infer_mt
            importlib.reload(infer_mt)
            infer_mt.SLEEP = 0
            con = sqlite3.connect(self.db)
            out = infer_mt.translate_batch(con, [SA], engine="gemini:gemini-2.5-flash", doc_code="D")
            con.close()
        finally:
            _restore(saved, old)
        self.assertEqual(out, ["The full verse."])
        con = sqlite3.connect(self.db)
        r = con.execute("SELECT token_source, in_tokens, out_tokens, cost_usd FROM usage_log "
                        "WHERE kind='translation'").fetchall()
        con.close()
        self.assertEqual(len(r), 1)
        src, tin, tout, cost = r[0]
        self.assertEqual(src, "provider")
        self.assertEqual((tin, tout), (200.0, 200.0))          # 2 calls x (100 in, 40 out + 60 thinking)
        self.assertAlmostEqual(cost, (200 * 0.30 + 200 * 2.50) / 1e6, places=9)

    def test_consensus_uses_measured_cost_and_skips_given_up_pages(self):
        import ocr_consensus as oc
        importlib.reload(oc)
        con = sqlite3.connect(self.db)
        for _ in range(9):
            con.execute("INSERT INTO usage_log(kind, engine, in_tokens, out_tokens, cost_usd, passages, ok, token_source)"
                        " VALUES('ocr_vision','gemini-vision:gemini-2.5-flash',1000,800,0,1,1,'provider')")
        con.commit(); con.close()
        cpp = oc.measured_cost_per_page(self.db)
        self.assertAlmostEqual(cpp, (1000 * 0.30 + 800 * 2.50) / 1e6, places=9)
        self.assertEqual(oc.measured_cost_per_page(str(Path(self.tmp.name) / "none.db")), 0.0015)
        vdir = Path(self.tmp.name) / "v"; vdir.mkdir()
        (vdir / "B_0001.jsonl").write_text(json.dumps({"text": "", "meta": {"finish": "STOP", "retries": 2}}) + "\n")
        (vdir / "B_0002.jsonl").write_text(json.dumps({"text": "", "meta": {"finish": "STOP", "retries": 0}}) + "\n")
        todo, done = oc.plan_vision(["inbox/B_0001.pdf", "inbox/B_0002.pdf"], vdir)
        self.assertEqual([Path(x).stem for x in todo], ["B_0002"])
        todo, _ = oc.plan_vision(["inbox/B_0001.pdf"], vdir, retry_refused=True)
        self.assertEqual(len(todo), 1)

    def test_embeddings_respect_the_budget(self):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO docs(code) VALUES('D')")
        con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,1,1,?,'x','mula')", (SA,))
        con.execute("UPDATE budget_state SET paused=1 WHERE id=1"); con.commit(); con.close()
        g = types.ModuleType("google.generativeai")
        g.configure = lambda **kw: None

        class M:
            name = "models/gemini-embedding-001"; supported_generation_methods = ["embedContent"]
        g.list_models = lambda: [M()]
        g.embed_content = lambda **kw: self.fail("must not embed when the budget is paused")
        saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
        sys.modules["google.generativeai"] = g
        if sys.modules.get("google") is None:
            sys.modules["google"] = types.ModuleType("google")
        old = getattr(sys.modules["google"], "generativeai", None); sys.modules["google"].generativeai = g
        try:
            be = importlib.import_module("build_embeddings")
            argv0 = sys.argv; sys.argv = ["build_embeddings.py", "--db", self.db, "--sleep", "0"]
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    be.main()
            finally:
                sys.argv = argv0
        finally:
            _restore(saved, old)
        self.assertIn("Refusing: the spend cap is reached", buf.getvalue())

    def test_audit_runs_read_only(self):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO usage_log(kind, engine, in_tokens, out_tokens, cost_usd, passages, ok, token_source)"
                    " VALUES('translation','gemini:gemini-2.5-flash',1000,1000,0.00075,1,1,'estimated')")
        con.commit(); con.close()
        before = Path(self.db).stat().st_mtime_ns
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "spend_audit.py"), "--db", self.db],
                           capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("0.0028", p.stdout)                      # 1000*0.30 + 1000*2.50 per 1M
        self.assertIn("metered from characters", p.stdout)
        self.assertEqual(Path(self.db).stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
