# -*- coding: ascii -*-
"""ASK_NOISE_2026_10_07: Ask leaves out passages tagged noise/frontmatter (running heads), in
keyword and in semantic retrieval. Fake Gemini client; no network."""
import os, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_brain_items_2026_10_07 import vec_for, MODEL, DIM   # noqa: E402

HEAD_EN = "Markandeya Purana"


def _db(d, vectors=True):
    import db_utils, cost_tracker
    db = str(Path(d) / "t.db")
    con = sqlite3.connect(db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
    con.execute("UPDATE budget_state SET budget_usd=100, spent_usd=0, paused=0 WHERE id=1")
    con.execute("INSERT INTO docs(code) VALUES('markandeya_purana')")
    rows = [(6, 1, "head", HEAD_EN, "noise")] + [(p, 1, "head", HEAD_EN, "noise") for p in range(8, 30, 2)] + [
        (11, 5, "verse", "The sage Markandeya Purana teacher Samika came to that place", "mula"),
        (11, 6, "verse", "Markandeya Purana tells how the young birds called out", "mula")]
    for pg, ix, t, en, tt in rows:
        pid = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,?,?,?,?,?)",
                          (pg, ix, t, en, tt)).lastrowid
        con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)", (pid, t, "", en))
    if vectors:
        con.execute("CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB, "
                    "updated_at TEXT)")
        for pid, en in con.execute("SELECT id, translation FROM passages").fetchall():
            con.execute("INSERT INTO passage_embeddings VALUES(?,?,?,?,?)", (pid, MODEL, DIM, vec_for(en).tobytes(), "x"))
    con.commit(); con.close()
    return db


class AskSkipsNoise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        g = types.ModuleType("google.generativeai")
        g.configure = lambda **k: None
        g.embed_content = lambda model, content, task_type=None: {"embedding": vec_for(content).tolist()}
        g.GenerationConfig = lambda **k: k

        class _M:
            def __init__(self, **k):
                pass

            def generate_content(self, msg):
                return types.SimpleNamespace(text="ok", usage_metadata=None)
        g.GenerativeModel = _M
        pkg = types.ModuleType("google"); pkg.generativeai = g
        self._saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
        sys.modules["google"], sys.modules["google.generativeai"] = pkg, g
        self._key = os.environ.get("GEMINI_API_KEY"); os.environ["GEMINI_API_KEY"] = "test"
        import dashboard
        self.dash = dashboard
        dashboard._ASK_VEC_CACHE.clear()

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        if self._key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self._key
        self.tmp.cleanup()

    def ask(self, db, k=3):
        r = self.dash.app.test_client().post("/api/ask", json={"q": HEAD_EN, "db": db, "k": k}).get_json()
        return r["mode"], [(s["page_no"], s["idx"]) for s in r["sources"] if not s.get("kind")]

    def test_semantic_skips_heads_and_still_finds_verses(self):
        mode, got = self.ask(_db(self.tmp.name))
        self.assertEqual(mode, "semantic")
        self.assertEqual(sorted(got), [(11, 5), (11, 6)], "the 12 identical heads must not crowd out the verses")

    def test_keyword_skips_heads(self):
        mode, got = self.ask(_db(self.tmp.name, vectors=False))
        self.assertEqual(mode, "keyword")
        self.assertEqual(sorted(got), [(11, 5), (11, 6)])


if __name__ == "__main__":
    unittest.main()
