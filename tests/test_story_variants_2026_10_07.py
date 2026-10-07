# -*- coding: ascii -*-
"""STORY_VARIANTS_2026_10_07: versions of an approved story for children 8-12 and readers 13-16
(stories.py retell / variant, the book's young and teen layouts, the Stories page routes).
No network: the REST client is stubbed."""
import importlib, json, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_vignettes_2026_10_05 import GOOD, stub   # noqa: E402
from test_story_books_2026_10_07 import _fixture   # noqa: E402

YOUNG = {"title": "The sage and the baby birds", "title_hi": "t",
         "story_en": ("The eggs fell on the battlefield and lay under the bell of an elephant [11.4]. "
                      "Samika, a self-controlled forest sage, came to that place [11.5]. "
                      "He heard the young birds calling and saw them on the ground [11.6, 11.7]. "
                      "The revered sage was filled with wonder and spoke to his disciples [11.8]. ") * 3,
         "story_hi": "h [11.5]", "notes": "left out the battle"}


class Variants(unittest.TestCase):
    def setUp(self):
        import stories
        importlib.reload(stories)
        self.s = stories
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        self.con = sqlite3.connect(self.db)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_retell_needs_an_approved_story_and_checks_like_a_story(self):
        with self.assertRaises(SystemExit):
            self.s.retell(self.con, 2, "young", self.db, http=stub(YOUNG, []))   # #2 is a draft
        calls = []
        v = self.s.retell(self.con, 1, "young", self.db, http=stub(YOUNG, calls))
        self.assertTrue(v["ok"], v["problems"])
        self.assertIn("children aged 8 to 12", calls[0]["systemInstruction"]["parts"][0]["text"])
        self.assertIn("APPROVED RETELLING", calls[0]["contents"][0]["parts"][0]["text"])
        row = self.s._variant_row(self.con, 1, "young")
        self.assertEqual((row["status"], row["title"]), ("draft", YOUNG["title"]))
        bad = dict(YOUNG, story_en=YOUNG["story_en"] + " Then Mrnjiga carried them to Lanka.")
        self.assertFalse(self.s.retell(self.con, 1, "young", self.db, http=stub(bad, []))["ok"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM doc_story_variants").fetchone()[0], 1, "one live row")

    def test_book_uses_the_approved_version_only(self):
        self.s.retell(self.con, 1, "young", self.db, http=stub(YOUNG, []))
        out = Path(self.tmp.name) / "b.html"
        self.s.book(self.con, [1], "T", out, "young")
        self.assertNotIn("baby birds", out.read_text(encoding="utf-8"), "a draft version is not used")
        self.con.execute("UPDATE doc_story_variants SET status='approved'"); self.con.commit()
        self.s.book(self.con, [1], "T", out, "young")
        h = out.read_text(encoding="utf-8")
        self.assertIn("The sage and the baby birds", h); self.assertIn("forest sage", h)
        self.assertNotIn("elephant [11.4]", h, "young readers: no citation marks in the text")
        self.s.book(self.con, [1], "T", out, "general")
        self.assertNotIn("baby birds", out.read_text(encoding="utf-8"), "general readers get the story")
        self.s.book(self.con, [1], "T", out, "teen")
        h = out.read_text(encoding="utf-8")
        self.assertNotIn("baby birds", h, "no approved teen version: the story is used")
        self.assertNotIn("Editorial notes", h)

    def test_cli_variant_approve_refuses_a_failed_check(self):
        import subprocess, os
        bad = dict(YOUNG, story_en="Too short [11.4].")
        self.s.retell(self.con, 1, "teen", self.db, http=stub(bad, []))
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "stories.py"), "--db", self.db, *a],
                                        capture_output=True, text=True, encoding="utf-8", timeout=60,
                                        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(run("variant", "--id", "1", "--audience", "teen", "--action", "approve").returncode, 1)
        self.assertEqual(run("variant", "--id", "1", "--audience", "teen", "--action", "force").returncode, 0)
        self.assertEqual(run("retell", "--id", "1", "--audience", "young").returncode, 0, "a dry run")


class Page(unittest.TestCase):
    def setUp(self):
        import stories, stories_web
        importlib.reload(stories); importlib.reload(stories_web)
        self.s = stories
        self.tmp = Path(tempfile.mkdtemp(prefix="stvar_"))
        (self.tmp / "scripts").mkdir(); (self.tmp / "exports").mkdir()
        shutil.copy2(ROOT / "scripts" / "stories_static.html", self.tmp / "scripts" / "stories_static.html")
        self.db = _fixture(str(self.tmp))
        con = sqlite3.connect(self.db); stories.retell(con, 1, "young", self.db, http=stub(YOUNG, [])); con.close()
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
        return self.c.post(url, json=body)

    def test_list_carries_versions_and_routes_work(self):
        row = [x for x in self.c.get("/api/stories/list?doc=M").get_json() if x["id"] == 1][0]
        self.assertEqual(row["variants"]["young"]["status"], "draft")
        self.assertTrue(row["variants"]["young"]["verify"]["ok"])
        self.post("/api/stories/1/retell", {"audience": "teen"})
        self.assertEqual(self.jobs[-1][2][-5:], ["--id", "1", "--audience", "teen", "--yes"])
        self.assertEqual(self.post("/api/stories/2/retell", {"audience": "teen"}).status_code, 400, "draft story")
        self.assertEqual(self.post("/api/stories/1/retell", {"audience": "baby"}).status_code, 400)
        r = self.post("/api/stories/1/variant", {"audience": "young", "action": "edit",
                                                 "story_en": YOUNG["story_en"] + " Then Mrnjiga came [11.8]."}).get_json()
        self.assertFalse(r["verify"]["ok"])
        self.assertEqual(self.post("/api/stories/1/variant", {"audience": "young", "action": "approve"}).status_code, 409)
        self.assertEqual(self.post("/api/stories/1/variant", {"audience": "young", "action": "force"}).status_code, 200)
        self.assertEqual(self.post("/api/stories/1/variant", {"audience": "teen", "action": "approve"}).status_code, 404)
        h = self.c.get("/stories"); t = h.data.decode("utf-8"); h.close()
        self.assertIn("For younger readers", t); self.assertIn("Graphic novels", t)


if __name__ == "__main__":
    unittest.main()
