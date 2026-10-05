# -*- coding: ascii -*-
"""VIGNETTES_2026_10_05: stories.py (new) and the export hook (patch_vignettes_2026_10_05.py).
No network: the REST client is stubbed."""
import importlib, json, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SA1 = "\u0936\u092e\u0940\u0915\u094b \u0928\u093e\u092e \u0938\u0902\u092f\u092e\u0940 \u0964"   # shamiko nama samyami
EN = {
    (11, 4): "The eggs fell on the battlefield and lay under the elephant's bell.",
    (11, 5): "Samika by name, a self-controlled ascetic, arrived at that place.",
    (11, 6): "There he heard the young birds calling out.",
    (11, 7): "He saw them on the ground.",
    (11, 8): "The revered sage Samika was filled with wonder and spoke to his disciples.",
}


def _db(d):
    import db_utils, cost_tracker, images
    db = str(Path(d) / "t.db")
    con = sqlite3.connect(db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con); images.ensure_schema(con)
    con.execute("UPDATE budget_state SET budget_usd=100, spent_usd=0, paused=0 WHERE id=1")
    con.execute("INSERT INTO docs(code) VALUES('M')")
    for (p, i), en in EN.items():
        con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,?,?,?,?,'mula')",
                    (p, i, SA1 if (p, i) == (11, 5) else "\u0915\u0916\u0917 %d" % i, en))
    con.commit(); con.close()
    return db


GOOD = {"title": "Samika finds the fledglings", "title_hi": "t",
        "story_en": ("The eggs fell on the battlefield and lay under the bell of an elephant [11.4]. "
                     "A self-controlled ascetic named Samika came to that place [11.5]. "
                     "He heard the young birds calling and saw them on the ground [11.6, 11.7]. "
                     "Filled with wonder, the revered sage spoke to his disciples about what he had found there "
                     "on the field of the great battle, where the young birds had survived [11.8]. ") * 3,
        "story_hi": "x [11.5]", "quote_sa": SA1.replace(" \u0964", ""), "quote_ref": "11.5", "notes": "",
        "cites": ["11.4", "11.5"]}


def stub(payload, calls):
    def http(url, body=None, timeout=180):
        calls.append(body)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
                "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 300, "thoughtsTokenCount": 100}}
    return http


class Vignettes(unittest.TestCase):
    def setUp(self):
        import stories
        importlib.reload(stories)
        self.s = stories
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _db(self.tmp.name)
        self.con = sqlite3.connect(self.db); stories.ensure_schema(self.con)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def given(self):
        return self.s.passages(self.con, "M")

    def test_verify_accepts_a_faithful_story(self):
        v = self.s.verify(GOOD, self.given())
        self.assertTrue(v["ok"], v["problems"])

    def test_verify_catches_invention(self):
        bad = dict(GOOD)
        bad["story_en"] = GOOD["story_en"] + " Then the sage Mrnjiga flew to Lanka with them. "
        bad["quote_sa"], bad["quote_ref"] = "\u0905\u0917\u0928\u093f", "11.5"
        v = self.s.verify(bad, self.given())
        self.assertFalse(v["ok"])
        txt = " ".join(v["problems"])
        self.assertIn("without a citation", txt)
        self.assertIn("not found verbatim", txt)
        self.assertIn("Mrnjiga", txt)
        out = dict(GOOD); out["story_en"] = GOOD["story_en"].replace("[11.8]", "[99.1]")
        self.assertIn("outside", " ".join(self.s.verify(out, self.given())["problems"]))

    def test_mine_keeps_only_valid_ranges_and_meters(self):
        calls = []
        eps = {"episodes": [{"title": "The sage finds the birds", "from": "11.4", "to": "11.8", "why": "w"},
                            {"title": "Invented range", "from": "50.1", "to": "51.2", "why": "w"}]}
        made = self.s.mine(self.con, "M", 1, self.db, max_n=5, chunk=150, yes=True, http=stub(eps, calls))
        self.assertEqual(len(made), 1)
        self.assertEqual(len(calls), 1)
        c = sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM usage_log WHERE kind='story_mine'").fetchone()[0], 1)
        c.close()

    def test_write_verify_approve_and_anthology(self):
        calls = []
        sid = self.con.execute("""INSERT INTO doc_stories(doc_id,status,title,from_page,from_idx,to_page,to_idx)
                                  VALUES(1,'candidate','t',11,4,11,8)""").lastrowid
        self.con.commit()
        v = self.s.write_story(self.con, sid, "M", self.db, http=stub(GOOD, calls))
        self.assertTrue(v["ok"], v["problems"])
        self.assertIn("SA: ", calls[0]["contents"][0]["parts"][0]["text"], "the Sanskrit is given to the model")
        self.con.execute("UPDATE doc_stories SET status='approved' WHERE id=?", (sid,)); self.con.commit()
        out, n = self.s.anthology(self.con, ["M"], "Test", Path(self.tmp.name) / "a.html")
        h = out.read_text(encoding="utf-8")
        self.assertEqual(n, 1)
        self.assertIn("<sup class='cite'>[11.5]</sup>", h)
        self.assertIn("Sources", h)
        self.assertIn(self.s.MARK, h)

    def test_story_for_image_and_cover_refusal(self):
        self.con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,anchor_page,anchor_idx)
                            VALUES(1,'generated','draft','Birds',11,6)""")
        self.con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,anchor_page,anchor_idx)
                            VALUES(1,'cover','approved','Cover',0,0)""")
        self.con.commit()
        sid = self.s.story_for_image(self.con, 1, before=2, after=2)
        r = self.con.execute("SELECT image_id, from_page, from_idx, to_page, to_idx FROM doc_stories WHERE id=?",
                             (sid,)).fetchone()
        self.assertEqual(r, (1, 11, 4, 11, 8))
        self.assertEqual(self.s.story_for_image(self.con, 1), sid, "one story per image")
        with self.assertRaises(SystemExit):
            self.s.story_for_image(self.con, 2)


class ExportHook(unittest.TestCase):
    def test_approved_story_prints_under_its_image(self):
        import export_html as ex, stories
        importlib.reload(ex)
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            db = _db(d)
            png = Path(d) / "a.png"; Image.new("RGB", (40, 30), "white").save(png)
            con = sqlite3.connect(db); stories.ensure_schema(con)
            con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,anchor_page,anchor_idx,path)
                           VALUES(1,'generated','approved','Birds',11,6,?)""", (str(png),))
            con.execute("""INSERT INTO doc_stories(doc_id,image_id,status,story_en,story_hi,quote_sa,quote_ref)
                           VALUES(1,1,'approved','The sage came [11.5].','h [11.5]','q','11.5')""")
            con.commit()
            figs = ex._load_figures(con, "M", root=d)
            fg = figs[(11, 6)][0]
            h = ex._figure_html(fg, True, True)
            self.assertIn("The sage came", h)
            self.assertIn("<sup class='cite'>[11.5]</sup>", h)
            con.execute("UPDATE doc_stories SET status='draft'"); con.commit()
            self.assertNotIn("The sage came", ex._figure_html(ex._load_figures(con, "M", root=d)[(11, 6)][0], True, True))
            con.close()


if __name__ == "__main__":
    unittest.main()
