# -*- coding: ascii -*-
"""SHELF_2026_10_04 + COLLECTIONS_2026_10_04 - the Shelf page and its collections."""
import json, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class Shelf(unittest.TestCase):
    def setUp(self):
        import db_utils, images
        self.tmp = Path(tempfile.mkdtemp(prefix="shelf_"))
        (self.tmp / "configs").mkdir(); (self.tmp / "exports").mkdir(); (self.tmp / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts" / "shelf_static.html", self.tmp / "scripts" / "shelf_static.html")
        self.db = self.tmp / "t.db"
        con = sqlite3.connect(str(self.db)); db_utils.ensure_schema(con); images.ensure_schema(con)
        con.execute("CREATE TABLE IF NOT EXISTS doc_stage(doc_code TEXT, stage TEXT, status TEXT, updated_at TEXT)")
        for code, cat in (("harita_tritiya_sthanam", "ayurveda"), ("harita_prathama_sthanam", "ayurveda"),
                          ("smriti_14manu_smriti", "smriti"), ("smriti_14manu_smriti_seg", "smriti"),
                          ("Mallapurana", "purana"), ("upapurana_kapila_purana", "upapurana"), ("oddity", None)):
            con.execute("INSERT INTO docs(code, category) VALUES(?,?)", (code, cat))
        con.execute("INSERT INTO doc_stage VALUES('smriti_14manu_smriti','retired','done','x')")
        did = con.execute("SELECT id FROM docs WHERE code='Mallapurana'").fetchone()[0]
        for i in range(4):
            cur = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(?,?,1,'x',?, 'mula')",
                              (did, i + 1, "en" if i < 3 else ""))
            if i < 2:
                con.execute("INSERT INTO translations_l10n(passage_id, lang, translation) VALUES(?, 'hi', 'h')", (cur.lastrowid,))
        con.execute("INSERT INTO doc_images(doc_id, kind, status, path, anchor_page, anchor_idx) VALUES(?, 'cover', 'approved', 'c.png', 0, 0)", (did,))
        con.execute("INSERT INTO doc_images(doc_id, kind, status, path, anchor_page, anchor_idx) VALUES(?, 'generated', 'approved', 'g.png', 1, 1)", (did,))
        con.commit(); con.close()
        for n in ("Mallapurana_1-137_tri.html", "Mallapurana_1-137_tri_img.pdf", "Mallapurana_notes.txt",
                  "smriti_14manu_smriti_seg_1-208.html"):
            (self.tmp / "exports" / n).write_text("x", encoding="utf-8")
        (self.tmp / "configs" / "doc_titles.json").write_text(json.dumps({"titles": {"Mallapurana": "Mallapur\u0101\u1e47a"}}),
                                                             encoding="utf-8")
        from flask import Flask
        import importlib, library_web
        importlib.reload(library_web)
        self.lw = library_web
        app = Flask("t")
        library_web.register(app, root=self.tmp, db=str(self.db),
                             bs_pdf=lambda code, mode: ((Path("x.pdf"), "book") if (code, mode) == ("Mallapurana", "hi") else (None, None)),
                             bs_modes=("tri", "hi"))
        self.c = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def books(self):
        d = self.c.get("/api/shelf?fresh=1").get_json()
        return d, {b["code"]: (c["key"], b) for c in d["collections"] for b in c["books"]}

    def test_shelves_series_and_metrics(self):
        d, by = self.books()
        self.assertFalse(d["from_file"])
        self.assertNotIn("smriti_14manu_smriti", by, "retired texts are not shelved")
        self.assertEqual(by["harita_prathama_sthanam"][0], "ayurveda")
        ay = [b["code"] for c in d["collections"] if c["key"] == "ayurveda" for b in c["books"]]
        self.assertEqual(ay, ["harita_prathama_sthanam", "harita_tritiya_sthanam"], "series order, not alphabetical")
        self.assertEqual(by["upapurana_kapila_purana"][0], "upapurana")
        self.assertEqual(by["oddity"][0], "other")
        _, m = by["Mallapurana"]
        self.assertEqual((m["passages"], m["en"], m["hi"], m["images_approved"]), (4, 3, 2, 1))
        self.assertTrue(m["cover_id"])
        self.assertTrue(m["title_confirmed"])
        self.assertEqual(sorted(e["name"] for e in m["editions"]), ["Mallapurana_1-137_tri.html", "Mallapurana_1-137_tri_img.pdf"])
        self.assertEqual(m["booksmith"], [{"mode": "hi", "kind": "book"}])
        _, seg = by["smriti_14manu_smriti_seg"]
        self.assertEqual([e["name"] for e in seg["editions"]], ["smriti_14manu_smriti_seg_1-208.html"])

    def test_title_and_move_write_config_files_with_backups(self):
        r = self.c.post("/api/shelf/title", json={"code": "oddity", "title": "An Odd Text", "title_sa": "\u0935\u093f\u091a\u093f\u0924\u094d\u0930"})
        self.assertEqual(r.status_code, 200)
        t = json.loads((self.tmp / "configs" / "doc_titles.json").read_text(encoding="utf-8"))
        self.assertEqual(t["titles"]["oddity"], "An Odd Text")
        self.assertTrue(list((self.tmp / "configs").glob("doc_titles.json.bak_*")))
        r = self.c.post("/api/shelf/move", json={"code": "oddity", "key": "bhakti"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        d, by = self.books()
        self.assertTrue(d["from_file"])
        self.assertEqual(by["oddity"][0], "bhakti")
        self.assertEqual(by["oddity"][1]["title"], "An Odd Text")
        self.assertEqual(self.c.post("/api/shelf/move", json={"code": "oddity", "key": "nope"}).status_code, 400)

    def test_file_route_is_confined_to_exports(self):
        r = self.c.get("/api/shelf/file?name=Mallapurana_1-137_tri.html"); self.assertEqual(r.status_code, 200); r.close()
        self.assertEqual(self.c.get("/api/shelf/file?name=..%2Fconfigs%2Fdoc_titles.json").status_code, 404)
        self.assertEqual(self.c.get("/api/shelf/file?name=Mallapurana_notes.txt").status_code, 404)

    def test_page(self):
        r = self.c.get("/shelf"); self.assertIn(b"SHELF_2026_10_04", r.data); r.close()


if __name__ == "__main__":
    unittest.main()
