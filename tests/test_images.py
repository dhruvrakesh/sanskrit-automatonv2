# -*- coding: ascii -*-
"""IMAGE_LIBRARY_2026_10_03. python -m unittest tests.test_images -v
Throwaway SQLite + temp folder; the HTTP layer is faked. No API, no network."""
import base64, importlib.util, io, json, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("images_under_test", str(REPO / "scripts" / "images.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


def png_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (64, 48), "white").save(b, format="PNG"); return b.getvalue()


class FakeHTTP:
    def __init__(self): self.calls = 0

    def __call__(self, url, body=None, timeout=180):
        self.calls += 1
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png",
                "data": base64.b64encode(png_bytes()).decode()}}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 1290}}


class Images(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "c.db"
        self.con = sqlite3.connect(self.db)
        self.con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                               "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT,"
                               " verse_ref TEXT, translation TEXT, text_type TEXT);"
                               "INSERT INTO docs VALUES(1,'X');")
        for i in range(1, 6):
            self.con.execute("INSERT INTO passages VALUES(?,1,?,?,NULL,?,'mula')", (i, 10, i, "The wrestler stands. %d" % i))
        self.con.commit()
        self.m.ensure_schema(self.con)
        self.m.ensure_schema(self.con)   # idempotent

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_briefs_snap_to_real_anchors_and_respect_the_cap(self):
        text, valid = self.m.gather_text(self.con, "X")
        self.assertIn("[p10.3]", text)
        items = [{"page": 10, "idx": 3, "title": "A", "brief": "a wrestler"},
                 {"page": 10, "idx": 99, "title": "B", "brief": "snaps to idx 5"},
                 {"page": 77, "idx": 1, "title": "C", "brief": "no such page - dropped"},
                 {"page": 10, "idx": 1, "title": "D", "brief": ""}]
        ids = self.m.store_briefs(self.con, "X", items, valid, 3, "m")
        rows = self.con.execute("SELECT anchor_page, anchor_idx, status, lineage_id=id FROM doc_images").fetchall()
        self.assertEqual(rows, [(10, 3, "brief", 1), (10, 5, "brief", 1)])
        self.assertEqual(len(ids), 2)

    def test_generate_once_cache_approve_and_versioning(self):
        _, valid = self.m.gather_text(self.con, "X")
        [i1] = self.m.store_briefs(self.con, "X", [{"page": 10, "idx": 2, "title": "A", "brief": "a wrestler"}], valid, 6, "m")
        self.m.set_status(self.con, i1, "brief-approved")
        http = FakeHTTP(); root = Path(self.tmp.name) / "images"
        self.m.generate_one(self.con, self.m.get(self.con, i1), "gemini-3.1-flash-image", root, "X", str(self.db), http=http)
        r1 = self.m.get(self.con, i1)
        self.assertEqual((r1["status"], http.calls), ("draft", 1))
        self.assertTrue(Path(r1["path"]).exists()); self.assertEqual((r1["width"], r1["height"]), (64, 48))
        self.assertIn("generated, not a historical source", r1["provenance"])
        self.m.approve(self.con, i1)
        # same brief again (a new version) -> cached file, no second API call
        i2 = self.m.new_version(self.con, i1)
        self.m.generate_one(self.con, self.m.get(self.con, i2), "gemini-3.1-flash-image", root, "X", str(self.db), http=http)
        self.assertEqual(http.calls, 1, "identical brief is never generated twice")
        self.m.approve(self.con, i2)
        self.assertEqual(self.m.get(self.con, i1)["status"], "retired", "one approved version per lineage")
        self.assertEqual(self.m.get(self.con, i2)["version"], 2)
        man = self.m.manifest(self.con, "X")
        self.assertEqual([x["id"] for x in man], [i2])
        self.assertIn("generated, not a historical source", man[0]["caption_en"])

    def test_approve_requires_a_draft_image(self):
        _, valid = self.m.gather_text(self.con, "X")
        [i1] = self.m.store_briefs(self.con, "X", [{"page": 10, "idx": 1, "title": "A", "brief": "x"}], valid, 6, "m")
        with self.assertRaises(SystemExit):
            self.m.approve(self.con, i1)

    def test_image_call_without_image_raises(self):
        with self.assertRaises(RuntimeError):
            self.m.call_image("m", "p", http=lambda u, b=None, timeout=0: {"candidates": [{"finishReason": "SAFETY"}]})

    def test_prompt_hash_depends_on_model_and_brief(self):
        h = self.m.prompt_hash
        self.assertEqual(h("m", "a"), h("m", "a"))
        self.assertNotEqual(h("m", "a"), h("m", "b")); self.assertNotEqual(h("m", "a"), h("n", "a"))

    def test_dedupe_keeps_first_per_anchor_and_store_skips_same_idea(self):
        _, valid = self.m.gather_text(self.con, "X")
        a = [{"page": 10, "idx": 2, "title": "Arena", "brief": "x"}, {"page": 10, "idx": 3, "title": "Pillar", "brief": "y"}]
        first = self.m.store_briefs(self.con, "X", a, valid, 6, "m")
        again = self.m.store_briefs(self.con, "X", a, valid, 6, "m")
        self.assertEqual(again, [], "the same idea at the same verse is not stored twice")
        b = self.m.store_briefs(self.con, "X", [{"page": 10, "idx": 2, "title": "Arena (Rangabhumi)", "brief": "z"}], valid, 6, "m")
        self.assertEqual(self.m.open_briefs(self.con, "X"), 3)
        res = self.m.dedupe(self.con, "X", apply=True)
        self.assertEqual([(r[0], r[1]) for r in res], [(b[0], first[0])])
        self.assertEqual(self.m.get(self.con, b[0])["status"], "retired")
        self.assertEqual(self.m.open_briefs(self.con, "X"), 2)


if __name__ == "__main__":
    unittest.main()
