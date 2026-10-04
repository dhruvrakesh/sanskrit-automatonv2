# -*- coding: ascii -*-
"""BRAIN_FRESH_2026_10_04 + ASK_VECTOR_CACHE_2026_10_04. No network: the Gemini client is stubbed.
Fails before patch_brain_2026_10_04.py, passes after."""
import importlib, io, os, sqlite3, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DIM = 8


def _stub_genai(calls):
    g = types.ModuleType("google.generativeai")
    g.configure = lambda **kw: None

    class M:  # one embedding model
        name = "models/text-embedding-004"
        supported_generation_methods = ["embedContent"]
    g.list_models = lambda: [M()]

    def embed_content(model, content, task_type=None):
        calls.append((task_type, content if isinstance(content, str) else len(content)))
        if isinstance(content, list):
            return {"embedding": [[1.0] + [0.0] * (DIM - 1) for _ in content]}
        return {"embedding": [1.0] + [0.0] * (DIM - 1)}
    g.embed_content = embed_content
    sys.modules["google.generativeai"] = g
    if "google" not in sys.modules:
        sys.modules["google"] = types.ModuleType("google")
    sys.modules["google"].generativeai = g
    return g


class Brain(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('D')")
        for i, ta in enumerate(["2026-10-01T00:00:00+00:00", "2026-10-03T10:00:00+00:00", None], 1):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,translated_at) "
                        "VALUES(1,1,?,?,?, 'mula', ?)", (i, "sa %d" % i, "The king %d." % i, ta))
        con.execute("CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, "
                    "vec BLOB, updated_at TEXT)")
        import numpy as np
        v = np.asarray([1.0] + [0.0] * (DIM - 1), dtype="float32").tobytes()
        for pid in (1, 2):   # both embedded on 10-02; passage 2 was re-translated on 10-04 -> stale
            con.execute("INSERT INTO passage_embeddings VALUES(?, 'models/text-embedding-004', ?, ?, "
                        "'2026-10-02T00:00:00+00:00')", (pid, DIM, v))
        con.commit(); con.close()
        self._saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
        self._google_attr = getattr(sys.modules.get("google"), "generativeai", None) if sys.modules.get("google") else None
        self._key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        self.calls = []
        _stub_genai(self.calls)

    def tearDown(self):
        # put the real client (or its absence) back, so later tests never see the stub
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

    def run_embed(self, *extra):
        be = importlib.import_module("build_embeddings")
        argv0 = sys.argv
        sys.argv = ["build_embeddings.py", "--db", self.db, "--sleep", "0"] + list(extra)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                be.main()
        finally:
            sys.argv = argv0
        return buf.getvalue()

    def test_plan_counts_missing_and_stale(self):
        out = self.run_embed("--plan")
        self.assertIn("2 to embed (1 missing, 1 stale", out)
        self.assertEqual(self.calls, [])

    def test_stale_vector_is_refreshed_and_no_stale_keeps_old_rule(self):
        self.assertIn("1 to embed (1 missing, 0 stale", self.run_embed("--plan", "--no-stale"))
        self.run_embed()
        con = sqlite3.connect(self.db)
        ts = dict(con.execute("SELECT passage_id, updated_at FROM passage_embeddings").fetchall()); con.close()
        self.assertEqual(sorted(ts), [1, 2, 3])
        self.assertEqual(ts[1], "2026-10-02T00:00:00+00:00")            # untouched
        self.assertGreater(ts[2], "2026-10-03T10:00:00+00:00")          # refreshed
        self.assertIn("0 to embed", self.run_embed("--plan"))           # converged

    def test_ask_reads_the_matrix_once(self):
        import dashboard
        con = sqlite3.connect(self.db)
        seen = []
        con.set_trace_callback(lambda s: seen.append(s))
        r1 = dashboard._ask_semantic_retrieve(con, "king", 2)
        r2 = dashboard._ask_semantic_retrieve(con, "king", 2)
        blob_reads = [s for s in seen if "SELECT passage_id, vec FROM passage_embeddings" in s]
        self.assertTrue(r1 and r2)
        self.assertEqual(len(blob_reads), 1, "second question must reuse the cached matrix")
        con.execute("UPDATE passage_embeddings SET updated_at='2026-10-05T00:00:00+00:00' WHERE passage_id=1")
        dashboard._ask_semantic_retrieve(con, "king", 2)
        blob_reads = [s for s in seen if "SELECT passage_id, vec FROM passage_embeddings" in s]
        self.assertEqual(len(blob_reads), 2, "a changed index is re-read")
        con.close()


if __name__ == "__main__":
    unittest.main()
