# -*- coding: ascii -*-
"""CREDITS_COST_2026_10_04. No network: the Gemini SDK is stubbed.
Fails before patch_credits_cost_2026_10_04.py, passes after."""
import importlib, os, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941"
MSG_402 = ('402 POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent: '
           'Your prepayment credits are depleted. Please go to AI Studio to manage your project and billing.')


def _stub_raising(calls, exc_text):
    g = types.ModuleType("google.generativeai")
    g.configure = lambda **kw: None
    g.GenerationConfig = lambda **kw: kw

    class GM:
        def __init__(self, **kw):
            pass

        def generate_content(self, *a, **kw):
            calls.append(1)
            raise Exception(exc_text)
    g.GenerativeModel = GM
    saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
    sys.modules["google.generativeai"] = g
    if sys.modules.get("google") is None:
        sys.modules["google"] = types.ModuleType("google")
    old = getattr(sys.modules["google"], "generativeai", None)
    sys.modules["google"].generativeai = g
    return saved, old


def _restore(saved, old):
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
    if saved.get("google") is not None and old is not None:
        saved["google"].generativeai = old


class Credits(unittest.TestCase):
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

    def test_detector(self):
        import infer_mt
        importlib.reload(infer_mt)
        self.assertTrue(infer_mt._credits_depleted(MSG_402))
        self.assertTrue(infer_mt._credits_depleted("HTTP 402: billing account has no credit"))
        self.assertFalse(infer_mt._credits_depleted("504 Deadline Exceeded on page 402"))
        self.assertFalse(infer_mt._credits_depleted("429 Resource has been exhausted (e.g. check quota)."))

    def test_402_aborts_the_run_after_one_call(self):
        calls = []
        saved, old = _stub_raising(calls, MSG_402)
        try:
            import infer_mt
            importlib.reload(infer_mt)
            infer_mt.SLEEP = 0
            con = sqlite3.connect(self.db)
            try:
                with self.assertRaises(infer_mt.QuotaExhausted) as cm:
                    infer_mt.translate_batch(con, [SA, SA + " 2", SA + " 3"], engine="gemini:gemini-2.5-flash",
                                             doc_code="D")
            finally:
                con.close()
            self.assertIsInstance(cm.exception, infer_mt.CreditsDepleted)
            self.assertEqual(len(calls), 1, "no retries and no further verses once the credit is gone")
        finally:
            _restore(saved, old)

    def test_fallback_model_exists(self):
        import infer_mt
        importlib.reload(infer_mt)
        if os.environ.get("MT_FALLBACK_MODEL") is None:
            self.assertEqual(infer_mt._FALLBACK_MODEL, "gemini-2.5-flash-lite")


class VisionMean(unittest.TestCase):
    def test_mean_not_median_and_fallback(self):
        import db_utils, cost_tracker, ocr_consensus as oc, corpus_status as cs
        importlib.reload(oc); importlib.reload(cs)
        with tempfile.TemporaryDirectory() as d:
            db = str(Path(d) / "t.db")
            con = sqlite3.connect(db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
            for out_tok in (400, 400, 400, 400, 4000):      # one expensive page, as in real data
                con.execute("INSERT INTO usage_log(kind, engine, in_tokens, out_tokens, cost_usd, passages, ok, token_source)"
                            " VALUES('ocr_vision','gemini-vision:gemini-2.5-flash',2000,?,0,1,1,'provider')", (out_tok,))
            con.commit(); con.close()
            cheap, dear = (2000 * 0.30 + 400 * 2.50) / 1e6, (2000 * 0.30 + 4000 * 2.50) / 1e6
            self.assertAlmostEqual(oc.measured_cost_per_page(db), (4 * cheap + dear) / 5, places=9)
        self.assertEqual(cs.VISION_COST_PER_PAGE, 0.0041)


class ShelfPage(unittest.TestCase):
    def test_badge_clearance_and_repeat_titles(self):
        s = (ROOT / "scripts" / "shelf_static.html").read_text(encoding="utf-8")
        self.assertTrue("CREDITS_COST_2026_10_04" in s, "CREDITS_COST_2026_10_04")
        self.assertTrue("padding:14px 10px 30px" in s, "padding:14px 10px 30px")
        self.assertTrue("dup[b.title] > 1" in s, "dup[b.title] > 1")


class BackupReads(unittest.TestCase):
    def test_backup_flag_leaves_no_sidecars(self):
        import db_utils, diag_orphans, io
        from contextlib import redirect_stdout
        importlib.reload(diag_orphans)
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "backup.db"
            con = sqlite3.connect(str(db)); db_utils.ensure_schema(con)
            con.execute("PRAGMA journal_mode=WAL"); con.commit(); con.close()
            for x in ("-wal", "-shm"):
                self.assertFalse(Path(str(db) + x).exists())
            with redirect_stdout(io.StringIO()):
                diag_orphans.run(str(db), immutable=True)
            for x in ("-wal", "-shm"):
                self.assertFalse(Path(str(db) + x).exists(), "an immutable read must not create " + x)


if __name__ == "__main__":
    unittest.main()
