# -*- coding: ascii -*-
"""STORIES_UI_2026_10_05: the Stories page (stories_web.py, new) and patch_stories_ui_2026_10_05.py
(dashboard wiring, verify sentence split, prompt rule 6). No network, no real jobs: launch is stubbed."""
import importlib, json, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_vignettes_2026_10_05 import _db, GOOD, SA1   # noqa: E402


class VerifySplit(unittest.TestCase):
    """Fails before the patch: 'Later' / 'Go' were reported as unknown names."""
    def setUp(self):
        import stories
        importlib.reload(stories)
        self.s = stories
        self.tmp = tempfile.TemporaryDirectory()
        self.con = sqlite3.connect(_db(self.tmp.name))

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def names(self, en):
        st = dict(GOOD); st["story_en"] = GOOD["story_en"] + en
        probs = self.s.verify(st, self.s.passages(self.con, "M"))["problems"]
        return " ".join(p for p in probs if p.startswith("names"))

    def test_citation_after_full_stop(self):
        self.assertEqual(self.names(" He saw the birds. [11.6] Later, the sage spoke to his disciples [11.8]."), "")
        self.assertEqual(self.names(" The eggs fell. [11.4] Simultaneously, the birds called out [11.6]."), "")

    def test_speech_and_colon_openers(self):
        self.assertEqual(self.names(' The sage said to his disciples: "Look at the young birds" [11.8].'), "")

    def test_invented_names_still_caught(self):
        self.assertIn("Mrnjiga", self.names(" Then the sage Mrnjiga flew away with them [11.8]."))
        self.assertIn("M\u1e5b\u00f1jig\u0101", self.names(" [11.6] M\u1e5b\u00f1jig\u0101 flew away with them [11.8]."))

    def test_uncited_sentence_after_citation_still_caught(self):
        st = dict(GOOD); st["story_en"] = GOOD["story_en"] + " He saw them. [11.7] Then he walked home through the forest."
        self.assertIn("without a citation", " ".join(self.s.verify(st, self.s.passages(self.con, "M"))["problems"]))

    def test_prompt_rule_6(self):
        self.assertIn("(6)", self.s.STORY_SYSTEM)
        self.assertIn("notes", self.s.STORY_SYSTEM.split("(6)")[1])


class Wiring(unittest.TestCase):
    def test_dashboard_registers_stories_guarded(self):
        d = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        i = d.index("import stories_web as _stories_web")
        self.assertGreater(i, d.index("import library_web as _library_web"), "after the Shelf")
        self.assertLess(i, d.index('if __name__ == "__main__":'), "registered at import, before the CLI")
        self.assertEqual(d[:i].rstrip().splitlines()[-1].strip(), "try:")
        h = (ROOT / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertLess(h.index('href="/stories"'), h.index('href="/shelf"'))


class Page(unittest.TestCase):
    def setUp(self):
        import stories, stories_web
        importlib.reload(stories); importlib.reload(stories_web)
        self.s = stories
        self.tmp = Path(tempfile.mkdtemp(prefix="stui_"))
        (self.tmp / "scripts").mkdir(); (self.tmp / "exports").mkdir()
        shutil.copy2(ROOT / "scripts" / "stories_static.html", self.tmp / "scripts" / "stories_static.html")
        self.db = _db(str(self.tmp))
        con = sqlite3.connect(self.db); stories.ensure_schema(con)
        con.execute("""INSERT INTO doc_images(doc_id,kind,status,title,anchor_page,anchor_idx,path)
                       VALUES(1,'generated','approved','Birds',11,6,'x.png')""")
        good = dict(GOOD)
        v = stories.verify(good, stories.passages(con, "M"))
        assert v["ok"], v
        con.execute("""INSERT INTO doc_stories(doc_id,image_id,status,title,story_en,story_hi,quote_sa,quote_ref,
                       from_page,from_idx,to_page,to_idx,verify,cites) VALUES(1,1,'draft',?,?,?,?,?,11,4,11,8,?,?)""",
                    (good["title"], good["story_en"], good["story_hi"], good["quote_sa"], good["quote_ref"],
                     json.dumps(v), json.dumps(v["cited"])))
        con.execute("""INSERT INTO doc_stories(doc_id,status,title,from_page,from_idx,to_page,to_idx)
                       VALUES(1,'candidate','A found episode',11,5,11,7)""")
        con.commit(); con.close()
        self.jobs = []

        def launch(kind, doc, argv, then=None, mode=""):
            self.jobs.append((kind, doc, list(argv), mode)); return "job%d" % len(self.jobs)
        from flask import Flask
        app = Flask("t")
        stories_web.register(app, launch=launch, root=self.tmp, py=lambda *a: ["PY", *a],
                             script=lambda n: "scripts/" + n, db=self.db)
        self.c = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def post(self, url, body):
        return self.c.post(url, data=json.dumps(body), content_type="application/json")

    def test_page_docs_list_and_passages(self):
        r = self.c.get("/stories")
        self.assertEqual(r.status_code, 200); self.assertIn(b"/api/stories/list", r.data); r.close()
        d = self.c.get("/api/stories/docs").get_json()
        self.assertEqual(d[0]["doc"], "M"); self.assertEqual(d[0]["stories"], {"draft": 1, "candidate": 1})
        self.assertEqual(d[0]["images_drawn"], 1)
        rows = self.c.get("/api/stories/list?doc=M").get_json()
        self.assertEqual([x["status"] for x in rows], ["draft", "candidate"])
        self.assertTrue(rows[0]["verify"]["ok"]); self.assertEqual(rows[0]["range"], "11.4-11.8")
        self.assertEqual(rows[0]["image"]["id"], 1); self.assertNotIn("provenance", rows[0])
        p = self.c.get("/api/stories/1/passages").get_json()
        self.assertEqual([x["ref"] for x in p], ["11.4", "11.5", "11.6", "11.7", "11.8"])
        self.assertEqual(p[1]["sa"], SA1)
        self.assertEqual(self.c.get("/api/stories/list?doc=x;drop").status_code, 400)
        self.assertEqual(self.c.get("/api/stories/list?doc=Nope").status_code, 404)

    def test_edit_rechecks_and_needs_reapproval(self):
        self.assertEqual(self.post("/api/stories/1/action", {"action": "approve"}).status_code, 200)
        r = self.post("/api/stories/1/edit", {"story_en": GOOD["story_en"] + " Then Mrnjiga came [11.8].",
                                              "status": "approved", "id": 99}).get_json()
        self.assertFalse(r["verify"]["ok"])
        row = self.c.get("/api/stories/list?doc=M").get_json()[0]
        self.assertEqual((row["id"], row["status"], row["approved_at"]), (1, "draft", None),
                         "an edit returns an approved story to draft; status/id are not editable")
        self.assertEqual(self.post("/api/stories/1/action", {"action": "approve"}).status_code, 409)
        self.assertEqual(self.post("/api/stories/1/action", {"action": "approve", "force": True}).status_code, 200)
        self.assertEqual(self.post("/api/stories/2/action", {"action": "approve"}).status_code, 400, "candidate")
        self.assertEqual(self.post("/api/stories/1/edit", {}).status_code, 400)

    def test_unicode_edit_round_trip(self):
        hi = "\u0936\u092e\u0940\u0915 \u0928\u0947 \u092a\u0915\u094d\u0937\u093f\u092f\u094b\u0902 \u0915\u094b \u0926\u0947\u0916\u093e [11.6]"
        self.post("/api/stories/1/edit", {"story_hi": hi, "title": "\u015aam\u012bka and the birds"})
        row = self.c.get("/api/stories/list?doc=M").get_json()[0]
        self.assertEqual((row["story_hi"], row["title"]), (hi, "\u015aam\u012bka and the birds"))

    def test_retire_unretire_and_retired_is_read_only(self):
        self.post("/api/stories/1/action", {"action": "retire"})
        self.assertEqual(self.post("/api/stories/1/edit", {"title": "x"}).status_code, 400)
        self.post("/api/stories/1/action", {"action": "unretire"})
        self.post("/api/stories/2/action", {"action": "retire"}); self.post("/api/stories/2/action", {"action": "unretire"})
        st = {x["id"]: x["status"] for x in self.c.get("/api/stories/list?doc=M").get_json()}
        self.assertEqual(st, {1: "draft", 2: "candidate"})
        self.assertEqual(self.post("/api/stories/1/action", {"action": "drop"}).status_code, 400)
        self.assertEqual(self.post("/api/stories/9/action", {"action": "verify"}).status_code, 404)

    def test_jobs_argv(self):
        self.post("/api/stories/mine", {"doc": "M", "max": 500})
        self.post("/api/stories/write", {"doc": "M", "id": 2})
        self.post("/api/stories/write", {"doc": "M", "image": 1, "before": 3})
        self.post("/api/stories/write", {"doc": "M", "which": "images", "max": 4})
        self.post("/api/stories/anthology", {"docs": ["M", "bad;doc"], "title": "T"})
        self.assertEqual(self.post("/api/stories/write", {"doc": "M", "which": "all"}).status_code, 400)
        self.assertEqual(self.post("/api/stories/mine", {"doc": "../x"}).status_code, 400)
        tails = [(k, d, a[a.index("--db") + 2:], m) for k, d, a, m in self.jobs]
        self.assertEqual(tails, [
            ("stories", "M", ["mine", "--doc", "M", "--max", "40", "--yes"], "mine"),
            ("stories", "M", ["write", "--id", "2", "--yes"], "id-2"),
            ("stories", "M", ["write", "--image", "1", "--yes", "--before", "3", "--after", "6"], "image-1"),
            ("stories", "M", ["write", "--doc", "M", "--images", "--max", "4", "--yes"], "images"),
            ("stories", "M", ["anthology", "--docs", "M", "--title", "T"], "anthology")])
        self.assertEqual(self.jobs[0][2][:3], ["PY", "scripts/stories.py", "--db"])

    def test_pdf_only_for_an_existing_anthology(self):
        self.assertEqual(self.post("/api/stories/pdf", {"name": "anthology_20261005.html"}).status_code, 400)
        (self.tmp / "exports" / "anthology_20261005.html").write_text("x", encoding="utf-8")
        self.assertEqual(self.post("/api/stories/pdf", {"name": "../anthology_20261005.html"}).status_code, 400)
        self.assertEqual(self.post("/api/stories/pdf", {"name": "anthology_20261005.html"}).get_json()["job"], "job1")
        self.assertEqual(self.jobs[0][2][1], "scripts/export_pdf.py")

    def test_missing_database_is_never_created(self):
        import stories_web
        from flask import Flask
        app = Flask("t2"); gone = self.tmp / "nope" / "context.db"
        stories_web.register(app, launch=lambda *a, **k: "j", root=self.tmp, py=lambda *a: list(a),
                             script=lambda n: n, db=str(gone))
        r = app.test_client().get("/api/stories/docs")
        self.assertEqual(r.status_code, 500); self.assertIn("not found", r.get_json()["error"])
        self.assertFalse(gone.exists())


if __name__ == "__main__":
    unittest.main()
