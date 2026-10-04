# -*- coding: ascii -*-
"""IMAGE_QUALITY_2026_10_04 + COVERS_2026_10_04. HTTP is faked; no network.
Fails before patch_images_quality_2026_10_04.py, passes after."""
import base64, importlib, io, json, os, re, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _png(w, h):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (w, h), (200, 180, 140)).save(b, "PNG"); return b.getvalue()


class Quality(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.db = str(self.t / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('Book')")
        for i in range(1, 4):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,?,1,?,?, 'mula')",
                        (i, "\u0927\u0930\u094d\u092e \u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 %d" % i,
                         "The king %d stood in the field." % i))
        con.commit(); con.close()
        for k in ("SA_IMAGE_ASPECT", "SA_IMAGE_SIZE", "SA_IMAGE_STYLE", "SA_IMAGE_CONFIG_FIELD"):
            os.environ.pop(k, None)
        import images
        self.lib = importlib.reload(images)
        c = self.lib._connect(self.db); self.lib.ensure_schema(c); c.close()

    def tearDown(self):
        for k in ("SA_IMAGE_ASPECT", "SA_IMAGE_SIZE", "SA_IMAGE_STYLE", "SA_IMAGE_CONFIG_FIELD"):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def _fake_http(self, w, h, sent):
        def http(url, body=None, timeout=180):
            sent.append(body)
            return {"candidates": [{"content": {"parts": [{"inlineData": {
                "mimeType": "image/png", "data": base64.b64encode(_png(w, h)).decode()}}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 1120}}
        return http

    def test_default_request_and_hash_unchanged(self):
        sent = []
        self.lib.call_image("m", "p", http=self._fake_http(10, 10, sent))
        self.assertEqual(sent[0]["generationConfig"], {"responseModalities": ["IMAGE"]})
        import hashlib
        old = hashlib.sha256(("m" + "\x00" + self.lib.prompt_for("b")).encode("utf-8")).hexdigest()
        self.assertEqual(self.lib.prompt_hash("m", "b"), old)
        self.assertNotEqual(self.lib.prompt_hash("m", "b", "3:4", "2K"), old)

    def test_aspect_and_size_are_sent_and_checked(self):
        sent = []
        self.lib.call_image("m", "p", http=self._fake_http(10, 10, sent), aspect="3:4", size="2K")
        self.assertEqual(sent[0]["generationConfig"]["imageConfig"], {"aspectRatio": "3:4", "imageSize": "2K"})
        self.lib.IMAGE_CONFIG_FIELD = "responseFormat"
        sent2 = []
        self.lib.call_image("m", "p", http=self._fake_http(10, 10, sent2), aspect="3:4")
        self.assertEqual(sent2[0]["generationConfig"]["responseFormat"], {"image": {"aspectRatio": "3:4"}})

    def test_cover_written_by_a_person_then_drawn_portrait(self):
        con = self.lib._connect(self.db)
        argv0 = sys.argv
        sys.argv = ["images.py", "--db", self.db, "cover", "--doc", "Book", "--brief", "A lone banyan at dawn."]
        try:
            self.assertEqual(self.lib.main(), 0)
            sys.argv = ["images.py", "--db", self.db, "cover", "--doc", "Book", "--brief", "Another."]
            self.assertEqual(self.lib.main(), 1, "a second open cover needs --more")
        finally:
            sys.argv = argv0
        row = con.execute("SELECT id, kind, status, anchor_page FROM doc_images").fetchone()
        self.assertEqual(row[1:], ("cover", "brief", 0))
        con.execute("UPDATE doc_images SET status='brief-approved' WHERE id=?", (row[0],)); con.commit()
        sent = []
        r = self.lib.get(con, row[0])
        self.lib.generate_one(con, r, "m", self.t / "img", "Book", self.db, http=self._fake_http(1024, 1536, sent))
        gc = sent[0]["generationConfig"]
        self.assertEqual(gc["imageConfig"]["aspectRatio"], "2:3")
        self.assertIn("upper third", sent[0]["contents"][0]["parts"][0]["text"])
        con.close()

    def test_ratio_warning(self):
        con = self.lib._connect(self.db)
        cur = con.execute("INSERT INTO doc_images(doc_id, kind, status, brief, anchor_page, anchor_idx, version)"
                          " VALUES(1,'generated','brief-approved','b',1,1,1)")
        con.execute("UPDATE doc_images SET lineage_id=id"); con.commit()
        self.lib.IMAGE_ASPECT = "3:4"
        buf = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf):
            self.lib.generate_one(con, self.lib.get(con, cur.lastrowid), "m", self.t / "img", "Book", self.db,
                                  http=self._fake_http(1408, 768, []))
        self.assertIn("ignored the image config", buf.getvalue())
        con.close()

    def test_style_preset(self):
        os.environ["SA_IMAGE_STYLE"] = "pahari"
        lib = importlib.reload(self.lib)
        self.assertIn("Pahari", lib.prompt_for("x"))
        self.assertIn("iconography", lib.BRIEF_SYSTEM)

    def test_export_puts_the_cover_on_the_title_page_only(self):
        con = self.lib._connect(self.db)
        p = self.t / "c.png"; p.write_bytes(_png(40, 60))
        q = self.t / "f.png"; q.write_bytes(_png(60, 40))
        con.execute("INSERT INTO doc_images(doc_id, kind, status, title, anchor_page, anchor_idx, path, version)"
                    " VALUES(1,'cover','approved','Cover',0,0,?,1)", (str(p),))
        con.execute("INSERT INTO doc_images(doc_id, kind, status, title, anchor_page, anchor_idx, path, version)"
                    " VALUES(1,'generated','approved','Field',2,1,?,1)", (str(q),))
        con.commit(); con.close()
        out = self.t / "exp"
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_html.py"), "--db", self.db, "--doc", "Book",
                            "--out", str(out), "--images", "approved", "--debug"],
                           capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        html = next(out.glob("*_img.html")).read_text(encoding="utf-8")
        tp = html.index("<div class='titlepage'>")
        self.assertTrue(tp < html.index("id='cover-") < html.index("<h1>"))
        self.assertEqual(html.count("<figure class='plate'"), 1)      # the verse figure only
        self.assertIn("images: 1 approved, 1 placed", r.stdout)

    def test_web_cover_endpoint_and_page_button(self):
        from flask import Flask
        import images_web
        importlib.reload(images_web)
        launched = []
        app = Flask("t")
        images_web.register(app, launch=lambda kind, doc, argv, then=None, mode="": launched.append((kind, argv, mode)) or "j1",
                            root=self.t, py=lambda *a: list(a), script=lambda n: n, db=self.db)
        c = app.test_client()
        r = c.post("/api/images/cover", json={"doc": "Book", "brief": "A banyan."})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        kind, argv, mode = launched[0]
        self.assertEqual((kind, mode), ("images_brief", "cover"))
        self.assertIn("--brief", argv)
        page = (ROOT / "scripts" / "images_static.html").read_text(encoding="utf-8")
        self.assertIn("btnCover", page)


if __name__ == "__main__":
    unittest.main()
