# -*- coding: ascii -*-
"""IMAGES_UI_2026_10_03. python -m unittest tests.test_images_web -v
A fresh Flask app with the Images routes, a throwaway DB and a fake launch().
No dashboard, no port, no API, no network."""
import importlib.util, io, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(REPO / "scripts" / (name + ".py")))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


class ImagesWeb(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.db = t / "c.db"
        c = sqlite3.connect(self.db)
        c.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                        "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, verse_ref TEXT,"
                        " text TEXT, translation TEXT, text_type TEXT);"
                        "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
                        "INSERT INTO docs VALUES(1,'X');"
                        "INSERT INTO passages VALUES(1,1,10,1,NULL,'sa text','The wrestler stands.','mula');"
                        "INSERT INTO translations_l10n VALUES(1,'hi','hindi');")
        c.commit(); c.close()
        self.lib = load("images"); self.web = load("images_web")
        con = self.lib._connect(str(self.db)); self.lib.ensure_schema(con)
        ids = self.lib.store_briefs(con, "X", [{"page": 10, "idx": 1, "title": "A", "brief": "b"},
                                                {"page": 10, "idx": 1, "title": "Another", "brief": "b2"}], {(10, 1)}, 6, "m")
        self.ids = ids
        # an image file for a third row, to test thumbnails
        from PIL import Image
        img = t / "data" / "images" / "X"; img.mkdir(parents=True)
        Image.new("RGB", (1200, 900), "white").save(img / "99_v1.png")
        con.execute("INSERT INTO doc_images(id, doc_id, lineage_id, version, kind, status, title, anchor_page, anchor_idx, path)"
                    " VALUES(99,1,99,1,'generated','draft','D',10,1,?)", ("data/images/X/99_v1.png",))
        con.commit(); con.close()
        self.launched = []
        def fake_launch(kind, doc, argv, then=None, mode=""):
            self.launched.append((kind, doc, argv, mode)); return "job-%d" % len(self.launched)
        app = Flask("t")
        self.web.register(app, launch=fake_launch, root=t, py=lambda *a: ["py", *a], script=lambda n: n, db=str(self.db))
        app.view_functions["images_page"] = lambda: "page"
        self.c = app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_edit_actions(self):
        rows = self.c.get("/api/images/list?doc=X").get_json()
        self.assertEqual(len(rows), 3)
        self.assertTrue([r for r in rows if r["id"] == 99][0]["has_image"])
        r = self.c.post("/api/images/%d/edit" % self.ids[0], json={"caption_hi": "\u092e\u0932\u094d\u0932", "anchor": "10.1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.post("/api/images/%d/action" % self.ids[0], json={"action": "approve-brief"}).get_json()["status"], "brief-approved")
        self.assertEqual(self.c.post("/api/images/%d/action" % self.ids[0], json={"action": "approve"}).status_code, 400,
                         "an idea without an image cannot be approved as an image")
        self.assertEqual(self.c.post("/api/images/99/action", json={"action": "approve"}).get_json()["status"], "approved")
        self.assertEqual(self.c.post("/api/images/%d/edit" % self.ids[0], json={"anchor": "abc"}).status_code, 400)

    def test_dedupe_passage_and_jobs(self):
        self.assertEqual(self.c.post("/api/images/dedupe", json={"doc": "X"}).get_json()["retired"], [self.ids[1]])
        p = self.c.get("/api/images/passage?doc=X&page=10&idx=1").get_json()
        self.assertEqual((p["en"], p["hi"]), ("The wrestler stands.", "hindi"))
        self.c.post("/api/images/generate", json={"doc": "X", "id": self.ids[0]})
        self.c.post("/api/images/brief", json={"doc": "X", "max": 50})
        kinds = [(k, m) for k, _, _, m in self.launched]
        self.assertEqual(kinds, [("images_gen", "id%d" % self.ids[0]), ("images_brief", "all")])
        self.assertIn("12", self.launched[1][2], "max is capped at HARD_CAP")
        self.assertEqual(self.c.post("/api/images/brief", json={"doc": "../etc"}).status_code, 400)

    def test_thumbnail_is_small_and_cached(self):
        r = self.c.get("/api/images/thumb/99")
        self.assertEqual(r.status_code, 200)
        from PIL import Image
        self.assertEqual(Image.open(io.BytesIO(r.data)).size[0], 360)
        self.assertTrue((Path(self.tmp.name) / "data/images/X/_thumbs/99_v1.jpg").exists())
        self.assertEqual(self.c.get("/api/images/thumb/%d" % self.ids[0]).status_code, 404)

    def test_docs_listing(self):
        d = self.c.get("/api/images/docs").get_json()
        self.assertEqual(d[0]["doc"], "X"); self.assertEqual(sum(d[0]["images"].values()), 3)

    def test_patch_anchors_exist_in_the_real_files(self):
        src = (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        html = (REPO / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        if "IMAGES_UI_2026_10_03" in src:
            self.assertIn("_images_web.register(app", src)
        else:
            self.assertEqual(src.replace("\r\n", "\n").count('\nif __name__ == "__main__":\n'), 1)
            self.assertEqual(html.replace("\r\n", "\n").count('    <div class="top-bar-spacer"></div>\n'), 1)


if __name__ == "__main__":
    unittest.main()
