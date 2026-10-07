# -*- coding: ascii -*-
"""BRAIN_ITEMS_2026_10_07: scripts/brain_items.py (new) and patch_brain_items_2026_10_07.py
(Ask uses the editorial index; ask.html links; maintenance step b2). No network: the
embedder and the Gemini client are fakes."""
import importlib, json, shutil, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_vignettes_2026_10_05 import _db   # noqa: E402

MODEL = "models/gemini-embedding-001"
DIM = 8


def vec_for(text):
    """A deterministic unit vector: words hash into 8 buckets."""
    v = np.zeros(DIM, dtype="float32")
    for w in str(text).lower().split():
        v[sum(map(ord, w)) % DIM] += 1.0
    n = np.linalg.norm(v)
    return (v / n) if n else v


class FakeEmbed:
    def __init__(self):
        self.calls = 0

    def __call__(self, texts):
        self.calls += 1
        return [vec_for(t).tolist() for t in texts]


def _fixture(d):
    import stories, images
    db = _db(d)
    con = sqlite3.connect(db); stories.ensure_schema(con); images.ensure_schema(con)
    con.execute("CREATE TABLE IF NOT EXISTS passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, "
                "vec BLOB, updated_at TEXT)")
    for pid, en in con.execute("SELECT id, translation FROM passages").fetchall():
        con.execute("INSERT INTO passage_embeddings VALUES(?,?,?,?,?)", (pid, MODEL, DIM, vec_for(en).tobytes(), "x"))
    con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,caption_en,context_note,anchor_page,anchor_idx,path)
                   VALUES(1,'generated','approved','Birds','The fledglings under the bell','11.6','11','6','a.png')""")
    con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,caption_en,anchor_page,anchor_idx)
                   VALUES(1,'generated','brief','Only an idea','never drawn',11,7)""")
    con.execute("""INSERT INTO doc_stories(doc_id,image_id,status,title,story_en,from_page,from_idx,to_page,to_idx)
                   VALUES(1,1,'approved','Samika finds the fledglings','The sage Samika found the young birds [11.5].',
                          11,4,11,8)""")
    con.execute("""INSERT INTO doc_stories(doc_id,status,title,story_en,from_page,from_idx,to_page,to_idx)
                   VALUES(1,'draft','A draft retelling','The eggs fell on the battlefield [11.4].',11,4,11,5)""")
    con.execute("""INSERT INTO doc_stories(doc_id,status,title,why,from_page,from_idx,to_page,to_idx)
                   VALUES(1,'candidate','The battle where the eggs fell','eggs survive the battle',11,4,11,6)""")
    con.execute("""INSERT INTO doc_stories(doc_id,status,title,story_en,from_page,from_idx,to_page,to_idx)
                   VALUES(1,'retired','Gone','gone [11.4].',11,4,11,5)""")
    con.commit(); con.close()
    return db


class Index(unittest.TestCase):
    def setUp(self):
        import brain_items
        importlib.reload(brain_items)
        self.bi = brain_items
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        self.con = sqlite3.connect(self.db)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_collect_kinds_and_exclusions(self):
        items = {(i["kind"], i["ref_id"]): i for i in self.bi.collect(self.con)}
        self.assertEqual(sorted(items), [("episode", 3), ("image", 1), ("story", 1), ("story", 2)])
        self.assertEqual(items[("story", 1)]["link"], "/stories?doc=M#s1")
        self.assertIn("passages 11.4-11.8", items[("story", 1)]["text"])
        self.assertEqual(items[("image", 1)]["link"], "/api/images/file/1")

    def test_sync_is_incremental_and_follows_status(self):
        emb = FakeEmbed()
        p = self.bi.sync(self.con, self.db, embed=emb)
        self.assertEqual((p["model"], p["embedded"], emb.calls), (MODEL, 4, 1))
        p = self.bi.sync(self.con, self.db, embed=emb)
        self.assertEqual((p["embedded"], emb.calls), (0, 1), "nothing new: no call")
        self.con.execute("UPDATE doc_stories SET status='approved' WHERE id=2"); self.con.commit()
        self.bi.sync(self.con, self.db, embed=emb)
        self.assertEqual(emb.calls, 1, "a status change alone is not re-embedded")
        self.assertEqual(self.con.execute("SELECT status FROM brain_items WHERE kind='story' AND ref_id=2").fetchone()[0],
                         "approved")
        self.con.execute("UPDATE doc_stories SET story_en='changed text [11.4].' WHERE id=2"); self.con.commit()
        self.assertEqual(self.bi.sync(self.con, self.db, embed=emb)["embedded"], 1)
        self.con.execute("UPDATE doc_stories SET status='retired' WHERE id=2"); self.con.commit()
        p = self.bi.sync(self.con, self.db, embed=emb)
        self.assertEqual(p["drop"], 1)
        self.assertIsNone(self.con.execute("SELECT 1 FROM brain_items WHERE kind='story' AND ref_id=2").fetchone())
        c = sqlite3.connect(self.db)
        self.assertGreaterEqual(c.execute("SELECT COUNT(*) FROM usage_log WHERE kind='embedding'").fetchone()[0], 2)
        c.close()

    def test_plan_makes_no_write(self):
        p = self.bi.plan(self.con)
        self.assertEqual((p["items"], p["add"], p["indexed"]), (4, 4, 0))
        self.assertNotIn("brain_items", {r[0] for r in self.con.execute("SELECT name FROM sqlite_master")})

    def test_retrieve_drafts_and_floor(self):
        self.bi.sync(self.con, self.db, embed=FakeEmbed())
        q = vec_for("A draft retelling. Retelling of M, passages 11.4-11.5. The eggs fell on the battlefield [11.4].")
        got = self.bi.retrieve(self.con, q, MODEL, k=5, min_sim=0.0)
        self.assertNotIn(("story", 2), [(g["kind"], g["id"]) for g in got], "drafts stay out by default")
        got = self.bi.retrieve(self.con, q, MODEL, k=5, include_drafts=True, min_sim=0.0)
        self.assertEqual((got[0]["kind"], got[0]["id"]), ("story", 2))
        self.assertIn("unreviewed draft", got[0]["label"])
        self.assertEqual(self.bi.retrieve(self.con, q, MODEL, k=5, min_sim=1.01), [])
        self.assertEqual(self.bi.retrieve(self.con, q, "other-model", k=5, min_sim=0.0), [])

    def test_no_passage_index_means_no_call(self):
        self.con.execute("DELETE FROM passage_embeddings"); self.con.commit()
        with self.assertRaises(SystemExit):
            self.bi.sync(self.con, self.db, embed=FakeEmbed())


class Wiring(unittest.TestCase):
    def test_files_carry_the_change(self):
        d = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("_ASK_QV[q] = (model, qv)", d)
        self.assertIn("extra = _ask_brain_items(con, q, data)", d)
        self.assertIn("Items labelled EDITORIAL", d)
        a = (ROOT / "scripts" / "ask.html").read_text(encoding="utf-8")
        self.assertIn("s.link ? esc(s.link)", a)
        m = (ROOT / "scripts" / "maintenance_runner.ps1").read_bytes()
        self.assertIn(b"scripts\\brain_items.py --db data\\context.db", m)
        self.assertTrue(all(b < 128 for b in m), "the runner must stay ASCII (PowerShell 5.1)")
        self.assertLess(m.index(b"STEP b embeddings"), m.index(b"brain_items.py"))
        self.assertLess(m.index(b"brain_items.py"), m.index(b"extract_entities.py"))


class AskEndToEnd(unittest.TestCase):
    """POST /api/ask with a fake Gemini client: editorial items follow the passages, labelled."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        import brain_items
        con = sqlite3.connect(self.db); brain_items.sync(con, self.db, embed=FakeEmbed()); con.close()
        self.sent = []
        g = types.ModuleType("google.generativeai")
        g.configure = lambda **k: None
        g.embed_content = lambda model, content, task_type=None: {"embedding": vec_for(content).tolist()}
        g.GenerationConfig = lambda **k: k
        outer = self

        class _M:
            def __init__(self, **k):
                self.k = k

            def generate_content(self, msg):
                outer.sent.append(msg)
                return types.SimpleNamespace(text="Answer [M p11.5].", usage_metadata=None)
        g.GenerativeModel = _M
        pkg = types.ModuleType("google"); pkg.generativeai = g
        self._saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai")}
        sys.modules["google"], sys.modules["google.generativeai"] = pkg, g
        import os
        self._key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test"
        import dashboard
        self.dash = dashboard
        dashboard._ASK_VEC_CACHE.clear()

    def tearDown(self):
        import os
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

    def test_editorial_items_after_passages(self):
        c = self.dash.app.test_client()
        q = "Samika finds the fledglings. Retelling of M, passages 11.4-11.8. The sage Samika found the young birds [11.5]."
        r = c.post("/api/ask", json={"q": q, "db": self.db, "k": 3}).get_json()
        self.assertEqual(r["mode"], "semantic", r)
        self.assertGreaterEqual(r["editorial"], 1)
        kinds = [s.get("kind") for s in r["sources"]]
        self.assertEqual(kinds[:3], [None, None, None], "passages first, unchanged")
        ed = [s for s in r["sources"] if s.get("kind")]
        self.assertTrue(all(s["link"] and s["label"].startswith("EDITORIAL") for s in ed))
        self.assertIn("(EDITORIAL retelling)", self.sent[-1])
        self.assertNotIn("A draft retelling", self.sent[-1], "drafts are not given to Ask by default")


if __name__ == "__main__":
    unittest.main()
