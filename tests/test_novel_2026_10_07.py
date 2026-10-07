# -*- coding: ascii -*-
"""NOVEL_2026_10_07: scripts/novel.py (new) - a cited page plan, cast sheets, pages drawn with the
sheets as reference images, approval, the book - and the Stories page routes. No network."""
import base64, importlib, io, json, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_vignettes_2026_10_05 import stub   # noqa: E402
from test_story_books_2026_10_07 import _fixture   # noqa: E402

CAPS = ["The eggs fell on the battlefield and lay under the bell of an elephant [11.4].",
        "A self-controlled ascetic named Samika came to that place [11.5].",
        "He heard the young birds calling out [11.6].",
        "He saw them on the ground [11.7].",
        "The revered sage was filled with wonder [11.8].",
        "The sage spoke to his disciples [11.8].",
        "The disciples listened to the sage [11.8].",
        "Samika looked at the young birds again [11.7]."]


def plan_payload(n=8, extra=""):
    return {"title": "The fledglings", "title_hi": "t",
            "cast": [{"name": "Samika", "look": "an old sage in bark garments, white beard"}],
            "pages": [{"n": k + 1, "scene": "scene %d: the sage and the birds at dusk" % (k + 1),
                       "caption": CAPS[k % len(CAPS)] + extra, "caption_hi": "h [11.5]",
                       "speech": [], "cites": ["11.5"]} for k in range(n)]}


def png_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (30, 40), "white").save(b, "PNG"); return b.getvalue()


def image_stub(calls):
    data = base64.b64encode(png_bytes()).decode("ascii")

    def http(url, body=None, timeout=180):
        calls.append(body)
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": data}}]}}],
                "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 1290}}
    return http


class Novel(unittest.TestCase):
    def setUp(self):
        import stories, novel
        importlib.reload(stories); importlib.reload(novel)
        self.nv = novel
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        self.con = sqlite3.connect(self.db)
        self.root = Path(self.tmp.name) / "imgs"

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_plan_is_checked_and_stored(self):
        calls = []
        nid = self.nv.plan(self.con, 1, self.db, pages=8, audience="young", http=stub(plan_payload(), calls))
        n = self.nv.get(self.con, nid)
        self.assertEqual((n["status"], n["pages"], n["audience"]), ("plan", 8, "young"))
        self.assertTrue(n["verify"]["ok"], n["verify"]["problems"])
        self.assertIn("children aged 8 to 12", calls[0]["systemInstruction"]["parts"][0]["text"])
        with self.assertRaises(SystemExit):
            self.nv.plan(self.con, 2, self.db, http=stub(plan_payload(), []))   # a draft story
        bad = plan_payload(8, " Then Mrnjiga flew to Lanka.")
        n2 = self.nv.get(self.con, self.nv.plan(self.con, 1, self.db, pages=8, http=stub(bad, [])))
        txt = " ".join(n2["verify"]["problems"])
        self.assertIn("without a citation", txt); self.assertIn("Mrnjiga", txt)
        n3 = self.nv.get(self.con, self.nv.plan(self.con, 1, self.db, pages=12, http=stub(plan_payload(5), [])))
        self.assertIn("5 pages", " ".join(n3["verify"]["problems"]))

    def test_cast_then_pages_use_the_sheets_as_references(self):
        nid = self.nv.plan(self.con, 1, self.db, pages=8, http=stub(plan_payload(), []))
        calls = []
        self.assertEqual(self.nv.draw_cast(self.con, nid, self.db, http=image_stub(calls), root=self.root), [1])
        self.assertEqual(len(calls[0]["contents"][0]["parts"]), 1, "a cast sheet has no reference")
        made = self.nv.draw_pages(self.con, nid, self.db, which=[1, 2], http=image_stub(calls), root=self.root)
        self.assertEqual(made, [1, 2])
        parts = calls[-1]["contents"][0]["parts"]
        self.assertIn("inlineData", parts[0]); self.assertIn("Samika", parts[1]["text"])
        self.assertIn("No letters", parts[-1]["text"])
        n = self.nv.get(self.con, nid)
        self.assertEqual(n["status"], "drawing")
        self.assertTrue(Path(n["page_images"]["1"]["path"]).is_file())
        self.assertEqual(self.nv.draw_pages(self.con, nid, self.db, which=[1], http=image_stub(calls), root=self.root), [],
                         "a drawn page is not drawn again without redo")
        c = sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM usage_log WHERE kind='image'").fetchone()[0], 3)
        c.close()

    def test_edit_marks_stale_and_approval_rules(self):
        nid = self.nv.plan(self.con, 1, self.db, pages=8, http=stub(plan_payload(), []))
        self.nv.draw_pages(self.con, nid, self.db, http=image_stub([]), root=self.root)
        for k in range(1, 9):
            self.nv.approve_page(self.con, nid, k)
        self.nv.edit_page(self.con, nid, 3, {"scene": "a different moment"})
        n = self.nv.get(self.con, nid)
        self.assertEqual(n["page_images"]["3"]["status"], "stale")
        with self.assertRaises(SystemExit):
            self.nv.approve(self.con, nid)
        self.nv.draw_pages(self.con, nid, self.db, http=image_stub([]), root=self.root)   # redraws the stale page only
        self.nv.approve_page(self.con, nid, 3)
        self.nv.approve(self.con, nid)
        self.assertEqual(self.nv.get(self.con, nid)["status"], "approved")
        v = self.nv.edit_page(self.con, nid, 2, {"caption": "Samika said nothing to anyone there."})
        self.assertFalse(v["ok"]); self.assertEqual(self.nv.get(self.con, nid)["status"], "plan")

    def test_build(self):
        nid = self.nv.plan(self.con, 1, self.db, pages=8, audience="young", http=stub(plan_payload(), []))
        self.nv.draw_pages(self.con, nid, self.db, which=[1], http=image_stub([]), root=self.root)
        out = Path(self.tmp.name) / "n.html"
        self.nv.build(self.con, nid, out)
        h = out.read_text(encoding="utf-8")
        self.assertIn("PROOF", h); self.assertIn("data:image/jpeg", h); self.assertIn("picture to come", h)
        self.assertNotIn("<sup class='cite'>", h, "young readers: no citation marks")
        self.assertIn("Where this story comes from", h)


class Routes(unittest.TestCase):
    def setUp(self):
        import stories, stories_web, novel
        importlib.reload(stories); importlib.reload(novel); importlib.reload(stories_web)
        self.tmp = Path(tempfile.mkdtemp(prefix="nv_"))
        (self.tmp / "scripts").mkdir(); (self.tmp / "exports").mkdir()
        shutil.copy2(ROOT / "scripts" / "stories_static.html", self.tmp / "scripts" / "stories_static.html")
        self.db = _fixture(str(self.tmp))
        con = sqlite3.connect(self.db)
        self.nid = novel.plan(con, 1, self.db, pages=8, http=stub(plan_payload(), []))
        novel.draw_pages(con, self.nid, self.db, which=[1], http=image_stub([]), root=self.tmp / "imgs")
        con.close()
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

    def test_routes(self):
        r = self.c.get("/api/novels?doc=M").get_json()
        self.assertEqual([x["id"] for x in r["novels"]], [self.nid])
        self.assertEqual([x["id"] for x in r["stories"]], [1, 3])
        self.assertGreater(r["novels"][0]["cost_per_image"], 0)
        self.c.post("/api/novels/plan", json={"story": 1, "pages": 40, "audience": "teen"})
        self.assertEqual(self.jobs[-1][2][-7:], ["--story", "1", "--pages", "16", "--audience", "teen", "--yes"])
        self.assertEqual(self.c.post("/api/novels/plan", json={"story": 2}).status_code, 400, "draft story")
        self.c.post("/api/novels/%d/draw" % self.nid, json={"pages": [3, "x"], "redo": True})
        kind, _doc, argv, _m = self.jobs[-1]
        self.assertEqual(kind, "images_gen")
        self.assertIn("--redo", argv); self.assertEqual(argv[argv.index("--pages") + 1], "3")
        self.c.post("/api/novels/%d/cast" % self.nid, json={})
        self.assertEqual(self.jobs[-1][0], "images_gen")
        r = self.c.get("/api/novels/%d/img?kind=page&n=1" % self.nid)
        self.assertEqual((r.status_code, r.mimetype), (200, "image/jpeg")); r.close()
        self.assertEqual(self.c.get("/api/novels/%d/img?kind=page&n=5" % self.nid).status_code, 404)
        r = self.c.post("/api/novels/%d/page" % self.nid, json={"action": "edit", "page": 1, "caption": "The sage walked home through the forest."}).get_json()
        self.assertFalse(r["verify"]["ok"])
        self.assertEqual(self.c.post("/api/novels/%d/action" % self.nid, json={"action": "approve"}).status_code, 400)
        self.c.post("/api/novels/%d/build" % self.nid, json={})
        self.assertEqual(self.jobs[-1][2][1:3], ["scripts/novel.py", "--db"])
        (self.tmp / "exports" / "novel_the-fledglings_20261007.html").write_text("x", encoding="utf-8")
        self.assertEqual(self.c.post("/api/stories/pdf", json={"name": "novel_the-fledglings_20261007.html"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
