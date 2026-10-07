# -*- coding: ascii -*-
"""STORY_BOOKS_2026_10_07: stories.py illustrate / book / booksmith-source (patch_story_books),
the Stories page routes for pictures, books and the brain (stories_web.py), and
booksmith_build.py --source-html (patch_booksmith_stories). No network."""
import importlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_vignettes_2026_10_05 import _db, GOOD, stub   # noqa: E402

IDEA = {"anchor": "11.6", "title": "The sage finds the fledglings", "brief": "A sage bends over four fledglings "
        "beneath a fallen elephant bell on an empty battlefield at dusk.", "context_note": "[11.6]",
        "caption_en": "Samika finds the fledglings", "caption_hi": "\u0936\u092e\u0940\u0915"}


def _fixture(d):
    import stories, images
    from PIL import Image
    db = _db(d)
    con = sqlite3.connect(db); stories.ensure_schema(con); images.ensure_schema(con)
    png = Path(d) / "a.png"; Image.new("RGB", (60, 40), "white").save(png)
    v = json.dumps({"ok": True, "problems": [], "cited": ["11.4", "11.5"], "words": 150})
    con.execute("""INSERT INTO doc_images(doc_id,lineage_id,version,kind,status,title,anchor_page,anchor_idx,path)
                   VALUES(1,1,1,'generated','approved','Birds',11,6,?)""", (str(png),))
    for st, title, img in (("approved", "First approved", 1), ("draft", "A draft", None),
                           ("approved", "Second approved", None), ("candidate", "Found", None)):
        con.execute("""INSERT INTO doc_stories(doc_id,image_id,status,title,title_hi,story_en,story_hi,quote_sa,quote_ref,
                       notes,cites,verify,from_page,from_idx,to_page,to_idx) VALUES(1,?,?,?,?,?,?,?,?,?,?,?,11,4,11,8)""",
                    (img, st, title, "\u0939", GOOD["story_en"] if st != "candidate" else "",
                     "h [11.5]" if st != "candidate" else "", GOOD["quote_sa"], "11.5",
                     "11.6: a doubtful reading", json.dumps(["11.4", "11.5"]), v))
    con.commit(); con.close()
    return db


class Commands(unittest.TestCase):
    def setUp(self):
        import stories
        importlib.reload(stories)
        self.s = stories
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        self.con = sqlite3.connect(self.db)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_illustrate_stores_a_linked_idea(self):
        calls = []
        iid = self.s.illustrate(self.con, 4, self.db, http=stub(IDEA, calls))
        r = self.con.execute("SELECT status, kind, anchor_page, anchor_idx, lineage_id, title FROM doc_images WHERE id=?",
                             (iid,)).fetchone()
        self.assertEqual(r, ("brief", "generated", 11, 6, iid, IDEA["title"]))
        self.assertEqual(self.con.execute("SELECT image_id FROM doc_stories WHERE id=4").fetchone()[0], iid)
        with self.assertRaises(SystemExit):
            self.s.illustrate(self.con, 4, self.db, http=stub(IDEA, calls))   # one live picture per story
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM usage_log WHERE kind='image_brief'").fetchone()[0], 1)

    def test_illustrate_reads_notes_and_snaps_a_bad_anchor(self):
        calls = []
        bad = dict(IDEA, anchor="99.1")
        iid = self.s.illustrate(self.con, 2, self.db, http=stub(bad, calls))
        prompt = calls[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("EDITORIAL NOTES", prompt); self.assertIn("doubtful reading", prompt)
        pg, ix = self.con.execute("SELECT anchor_page, anchor_idx FROM doc_images WHERE id=?", (iid,)).fetchone()
        self.assertTrue((11, 4) <= (pg, ix) <= (11, 8))

    def test_book_order_audience_and_proof(self):
        out = Path(self.tmp.name) / "b.html"
        path, n = self.s.book(self.con, [3, 2, 1, 4], "T", out, "general")
        h = out.read_text(encoding="utf-8")
        self.assertEqual(n, 2, "approved only")
        self.assertLess(h.index("Second approved"), h.index("First approved"), "the order given")
        self.assertIn("<sup class='cite'>", h); self.assertIn("Editorial notes", h); self.assertIn("data:image/jpeg", h)
        self.s.book(self.con, [1], "T", out, "young")
        h = out.read_text(encoding="utf-8")
        self.assertNotIn("<sup class='cite'>", h); self.assertNotIn("Editorial notes", h)
        self.assertNotIn("[11.4]", h.split("Where these stories come from")[0])
        self.s.book(self.con, [1], "T", out, "scholar", hindi=False)
        h = out.read_text(encoding="utf-8")
        self.assertIn("Sanskrit (as printed)", h); self.assertNotIn("class='hi'", h)
        _p, n = self.s.book(self.con, [2], "T", out, "general", proof=True)
        self.assertEqual(n, 1); self.assertIn("PROOF", out.read_text(encoding="utf-8"))

    def test_booksmith_source_parses_as_booksmith_reads_it(self):
        out = Path(self.tmp.name) / "w.html"
        _p, n = self.s.booksmith_source(self.con, [1, 2, 3], "T", out)
        self.assertEqual(n, 2)
        try:
            from nartiang_booksmith.parser import parse_html
        except ImportError:
            h = out.read_text(encoding="utf-8")
            self.assertEqual(h.count("<section class='chapter'"), 2); self.assertEqual(h.count("class='vref'"), 2)
            return
        doc = parse_html(out)
        self.assertEqual((doc.leaves, len(doc.units), doc.parser_mode), (2, 2, "leaf"))
        u = doc.units[0]
        self.assertIn("1. First approved", u.supplied_reference)
        self.assertTrue(u.text["english"].startswith("The eggs fell"))
        self.assertTrue(any("Editorial note" in x for x in u.notes))

    def test_cli_book_and_dry_run_illustrate(self):
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "stories.py"), "--db", self.db, *a],
                                        capture_output=True, text=True, encoding="utf-8", timeout=60,
                                        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        r = run("illustrate", "--id", "4")
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("Dry run", r.stdout)
        out = Path(self.tmp.name) / "c.html"
        r = run("book", "--ids", "3,1", "--title", "Tales", "--audience", "young", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("2 stories, audience young", r.stdout)
        r = run("book", "--ids", "2", "--title", "Tales", "--out", str(out))
        self.assertEqual(r.returncode, 1, "a draft alone makes no book without --proof")


class Page(unittest.TestCase):
    def setUp(self):
        import stories, stories_web
        importlib.reload(stories); importlib.reload(stories_web)
        self.tmp = Path(tempfile.mkdtemp(prefix="stbk_"))
        (self.tmp / "scripts").mkdir(); (self.tmp / "exports").mkdir()
        shutil.copy2(ROOT / "scripts" / "stories_static.html", self.tmp / "scripts" / "stories_static.html")
        self.db = _fixture(str(self.tmp))
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

    def test_page_has_the_new_controls(self):
        r = self.c.get("/stories"); h = r.data.decode("utf-8"); r.close()
        for k in ("Propose image", "Draw it", "Make a book", "Booksmith edition", "Update brain", "/api/stories/books/stories"):
            self.assertIn(k, h)

    def test_illustrate_route(self):
        self.post("/api/stories/4/illustrate", {})
        self.assertEqual(self.jobs[-1][2][-4:], ["illustrate", "--id", "4", "--yes"])
        self.assertEqual(self.post("/api/stories/1/illustrate", {}).status_code, 400, "already has a picture")

    def test_redraw_shows_newest_version_and_approve_relinks(self):
        import images
        con = sqlite3.connect(self.db)
        new = images.new_version(con, 1)
        con.execute("UPDATE doc_images SET status='draft', path=(SELECT path FROM doc_images WHERE id=1) WHERE id=?", (new,))
        con.commit(); con.close()
        row = [x for x in self.c.get("/api/stories/list?doc=M").get_json() if x["id"] == 1][0]
        self.assertEqual((row["image"]["id"], row["image"]["status"]), (new, "draft"))
        self.assertEqual(self.post("/api/stories/3/image", {"action": "approve", "image": new}).status_code, 400)
        self.assertEqual(self.post("/api/stories/1/image", {"action": "approve", "image": new}).status_code, 200)
        con = sqlite3.connect(self.db)
        self.assertEqual(con.execute("SELECT image_id FROM doc_stories WHERE id=1").fetchone()[0], new)
        self.assertEqual(con.execute("SELECT status FROM doc_images WHERE id=1").fetchone()[0], "retired",
                         "one approved version per lineage")
        con.close()

    def test_book_routes(self):
        rows = self.c.get("/api/stories/books/stories?docs=M").get_json()
        self.assertEqual([(r["id"], r["status"], r["image_ok"]) for r in rows],
                         [(1, "approved", True), (2, "draft", False), (3, "approved", False)])
        self.post("/api/stories/book", {"ids": [3, 1], "title": "Tales of M", "audience": "young", "hindi": False})
        argv = self.jobs[-1][2]
        self.assertEqual(argv[argv.index("book"):], ["book", "--ids", "3,1", "--title", "Tales of M", "--audience",
                                                     "young", "--no-hindi"])
        self.assertEqual(self.post("/api/stories/book", {"ids": []}).status_code, 400)
        (self.tmp / "exports" / "book_tales-of-m_20261007.html").write_text("x", encoding="utf-8")
        self.assertEqual(self.post("/api/stories/pdf", {"name": "book_tales-of-m_20261007.html"}).status_code, 200)
        files = self.c.get("/api/stories/books/files").get_json()
        self.assertEqual(files[0]["name"], "book_tales-of-m_20261007.html")

    def test_booksmith_route_writes_the_witness_and_passes_plates(self):
        r = self.post("/api/stories/booksmith", {"ids": [1, 2, 3], "title": "Tales of M"}).get_json()
        self.assertEqual((r["label"], r["stories"], r["plates"]), ("stories-tales-of-m", 2, 1))
        kind, label, argv, mode = self.jobs[-1]
        self.assertEqual((kind, label, mode), ("booksmith", "stories-tales-of-m", "story"))
        self.assertEqual(argv[argv.index("--mode") + 1], "story")
        self.assertEqual(argv[argv.index("--plate-ids") + 1], "1")
        self.assertTrue(Path(argv[argv.index("--source-html") + 1]).is_file())
        self.assertEqual(self.post("/api/stories/booksmith", {"ids": [2]}).status_code, 400, "drafts only")
        self.assertEqual(self.c.get("/api/stories/booksmith/file?label=../x").status_code, 400)

    def test_brain_status(self):
        b = self.c.get("/api/stories/brain").get_json()
        self.assertTrue(b["available"])
        self.assertEqual((b["indexed"], b["model"]), (0, None))
        self.post("/api/stories/brain/refresh", {})
        self.assertEqual(self.jobs[-1][0], "brain")
        self.assertEqual(self.jobs[-1][2][1], "scripts/brain_items.py")


@unittest.skipUnless(os.environ.get("BOOKSMITH_TEST_ROOT"), "set BOOKSMITH_TEST_ROOT to a Booksmith with a .venv")
class BooksmithBuild(unittest.TestCase):
    """End to end through a real Booksmith: init, ingest, audit, build, with one plate."""
    def test_build(self):
        import stories
        with tempfile.TemporaryDirectory() as d:
            db = _fixture(d)
            con = sqlite3.connect(db)
            w = Path(d) / "w.html"
            stories.booksmith_source(con, [1, 3], "Tales", w)
            con.close()
            label = "stories-test-%d" % os.getpid()
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "booksmith_build.py"), "--db", db, "--doc", label,
                                "--mode", "story", "--source-html", str(w), "--title", "Tales", "--plate-ids", "1",
                                "--exports", str(Path(d) / "exports"), "--booksmith-root", os.environ["BOOKSMITH_TEST_ROOT"]],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            side = json.loads((Path(d) / "exports" / "booksmith" / ("%s__story.json" % label)).read_text())
            self.assertTrue(side["ok"]); self.assertEqual(side["pdf_kind"], "book.pdf")
            self.assertEqual(len(side["plates"]["plates"]), 1)
            shutil.rmtree(Path(os.environ["BOOKSMITH_TEST_ROOT"]) / "projects" / (label + "-story"), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
