# -*- coding: ascii -*-
"""CORNER_C10_2026_10_09: scripts/corner_worker.py 1.2 (the Corner level with the desk: the eight kinds of
C10b, "redo" for the novels' cast and pages, and the mail flush of E1). The small context.db, the fake site
queue and the fake scripts are those of tests/test_corner_worker_2026_10_09.py, with the fake clock and the
progress desk of tests/test_corner_worker_state_2026_10_09.py; the fake scripts here also store ideas for
pictures (images.py brief) and for a cover (images.py cover) as images.py does. The edits run in-process:
no script is run for them. A fake urlopen stands in for corpus-desk and corner-mail and checks each call's
signature as the functions do. The last class runs rounds against PostgreSQL with C9, C10a and C10b
applied by the harness of tests/test_corner_kinds_pg_2026_10_09.py (CORPUS_TEST_DSN, a throwaway database).
  python -m unittest tests.test_corner_worker_c10_2026_10_09 -v
"""
import gzip, hashlib, hmac, io, json, os, re, sqlite3, sys, unittest, urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import corner_worker as cw                            # noqa: E402
import corpus_media as cm                             # noqa: E402
import corpus_sync as cs                              # noqa: E402
import test_corner_worker_2026_10_09 as base          # noqa: E402
import test_corner_worker_state_2026_10_09 as state   # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
DOC = base.DOC
SECRET = "test-secret-of-forty-characters-0123456"
NEW = ["story_edit", "story_verify", "picture_ideas", "picture_cover", "picture_draw", "picture_edit",
       "picture_restore", "novel_page_edit"]
HI = "\u0935\u093f\u0924\u0938\u094d\u0924\u093e"                    # Devanagari: the river's name
# A story that passes stories.verify over passages 25.1-25.6 (152 words, every sentence cited, no names,
# its quotation 's' found in passage 25.3).
GOOD = " ".join(["the river ran from the lake down to the sea and the people of the valley watched it go [25.3]."] * 8)
ARGV_WORDS = {"scripts/stories.py", "scripts/images.py", "scripts/novel.py", "scripts/corpus_sync.py",
              "scripts/corpus_media.py", "--db", "write", "mine", "illustrate", "approve", "retire", "approve-brief",
              "generate", "regenerate", "brief", "cover", "plan", "cast", "draw", "approve-page", "--id", "--doc",
              "--max", "--yes", "--more", "--redo", "--pages", "--story", "--audience", "--force", "--page", "--apply",
              "--if-configured", "--tables", "docs,stories", "young", "teen", "general", DOC}
C9_KINDS = ["story_range", "story_write", "story_mine", "picture_passage", "story_illustrate", "picture_redraw",
            "novel_plan", "novel_cast", "novel_draw", "story_approve", "story_retire", "picture_approve",
            "picture_retire", "novel_page_approve", "novel_approve", "novel_retire"]
NUMBERS_RE = re.compile(r"^\d+(-\d+)?(,\d+(-\d+)?)*$")


class C10Scripts(state.TimedScripts):
    """The fake scripts, each taking 10 s of the fake clock, and images.py brief and cover as they store their
    ideas (status brief, lineage_id = id): `ideas` rows for brief (images.py stores at most --max; this fake
    stores what it is told, to test the worker's own cap), `covers` rows for cover."""

    def __init__(self, db, clock):
        super().__init__(db, clock)
        self.ideas, self.covers, self.timeouts = 3, 1, []

    def __call__(self, args, timeout, on_line=None):
        self.timeouts.append((args[3] if len(args) > 3 else args[0], timeout))
        return super().__call__(args, timeout, on_line=on_line)

    def idea(self, con, did, kind, title, brief, page, idx, status="brief"):
        cur = con.execute("INSERT INTO doc_images(doc_id, kind, status, title, brief, anchor_page, anchor_idx) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?)", (did, kind, status, title, brief, page, idx))
        con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (cur.lastrowid,))
        return cur.lastrowid

    def apply(self, con, name, a):
        cmd = a[0]
        arg = lambda k: a[a.index(k) + 1]
        if name == "images.py" and cmd in ("brief", "cover"):
            did = con.execute("SELECT id FROM docs WHERE code=?", (arg("--doc"),)).fetchone()[0]
            if cmd == "brief":
                for k in range(1, self.ideas + 1):
                    self.idea(con, did, "generated", "Idea %d" % k, ("Brief %d: " % k) + "x" * 400, 25, k)
                self.idea(con, did, "cover", "A cover made meanwhile", "not an idea of this run", 0, 0)
                self.idea(con, did, "generated", "Retired at once", "not an idea of this run", 25, 9, "retired")
                self.idea(con, 2, "generated", "Another text", "not an idea of this text", 1, 1)
                self.cost(con, arg("--doc"), 0.004)
                return "stored %d brief(s)" % self.ideas
            for k in range(self.covers):
                self.idea(con, did, "cover", "Cover", "The lake under a calm sky, a lotus on the water", 0, 0)
            self.cost(con, arg("--doc"), 0.002)
            return "stored cover idea"
        return super().apply(con, name, a)


class Base(base.Base):
    """The 1.1 tests' context.db, and: story 35 with a quotation (its check can pass), story 37 retired,
    pictures 4 (approved), 5 (retired, drawn, its file here), 6 (retired idea), 7 (an idea), 8 (another
    text's), and novel 1 with a plan of 8 pages, pages 1 and 2 drawn."""

    def setUp(self):
        super().setUp()
        self.clock = state.Clock()
        for name, fn in (("clock", self.clock.now), ("sleep", self.clock.sleep)):
            p = mock.patch.object(cw.Progress, name, staticmethod(fn))
            p.start()
            self.addCleanup(p.stop)
        self.p5 = self.tmp / "5_v1.jpg"
        self.p5.write_bytes(b"\xff\xd8 not really a jpeg")
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_stories SET quote_sa='s', quote_ref='25.3' WHERE id=35")
        con.execute("INSERT INTO doc_stories(id, doc_id, status, title, from_page, from_idx, to_page, to_idx, story_en) "
                    "VALUES (37, 1, 'retired', 'Gone', 25, 1, 25, 2, 'T')")
        con.execute("UPDATE doc_stories SET approved_at='2026-10-08T10:00:00' WHERE id=34")
        con.execute("INSERT INTO doc_images(id, doc_id, lineage_id, version, status, title, path, retired_at) VALUES "
                    "(4, 1, 4, 1, 'approved', 'Approved', 'p4', NULL), (5, 1, 5, 1, 'retired', 'Old river', ?, "
                    "'2026-10-08T09:00:00'), (6, 1, 6, 1, 'retired', 'Old idea', NULL, '2026-10-08T09:00:00')",
                    (str(self.p5),))
        con.execute("INSERT INTO doc_images(id, doc_id, lineage_id, version, kind, status, title, brief, anchor_page, "
                    "anchor_idx) VALUES (7, 1, 7, 1, 'generated', 'brief', 'An idea', 'The lake at dawn, a heron', 25, 3), "
                    "(8, 2, 8, 1, 'generated', 'brief', 'Elsewhere', 'Elsewhere', 1, 1)")
        con.commit()
        con.close()
        self.plan_novel()
        self.scripts = C10Scripts(self.db, self.clock)
        self.said = []
        self.worker = cw.Worker(self.db, runner=self.scripts, ledger=self.tmp / "made.jsonl", say=self.said.append)

    def plan_novel(self, drawn=(1, 2), pages=8, status="drawing"):
        imgs = {str(n): {"path": "p%d" % n, "status": "draft"} for n in drawn}
        plan = {"title": "T", "cast": [], "pages": [{"n": n, "scene": "Scene %d by the lake" % n,
                                                     "caption": "Caption %d [25.%d]." % (n, n), "caption_hi": "",
                                                     "speech": [], "cites": ["25.%d" % n]} for n in range(1, pages + 1)]}
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_novels SET plan=?, page_images=?, status=? WHERE id=1",
                    (json.dumps(plan), json.dumps(imgs), status))
        con.commit()
        con.close()

    def do(self, *reqs, limit=30, desk_class=state.ProgressDesk):
        desk = desk_class([dict({"est_usd": 0.01, "attempts": 1}, **r) for r in reqs])
        return desk, cw.run_once(desk, self.worker, limit, progress=True)

    def one(self, kind, params, rid=1, **kw):
        desk, s = self.do({"id": rid, "kind": kind, "doc_code": DOC, "params": params}, **kw)
        return desk, desk.final(rid)

    def story_row(self, sid):
        con = sqlite3.connect(self.db)
        try:
            con.row_factory = sqlite3.Row
            return dict(con.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone())
        finally:
            con.close()

    def image_row(self, iid):
        con = sqlite3.connect(self.db)
        try:
            con.row_factory = sqlite3.Row
            return dict(con.execute("SELECT * FROM doc_images WHERE id=?", (iid,)).fetchone())
        finally:
            con.close()

    def novel_full(self):
        import novel as nv
        con = sqlite3.connect(self.db)
        try:
            return nv.get(con, 1)
        finally:
            con.close()

    def scripts_run(self):
        """The scripts run, but for the sending on (corpus_sync.py, corpus_media.py)."""
        return [c for c in self.scripts.calls if "corpus_" not in c[0]]

    def sent_on(self):
        return [c[0] for c in self.scripts.calls if "corpus_" in c[0]]


class Version(unittest.TestCase):
    def test_the_version_the_marker_and_the_tables(self):
        self.assertEqual((cw.CLIENT_VERSION, cw.CLIENT), ("1.2", "corner_worker.py 1.2"))
        src = Path(cw.__file__).read_bytes()
        self.assertIn(b"CORNER_C10_2026_10_09", src)
        src.decode("ascii")                                                   # ASCII only
        self.assertNotIn(b"\r\n", src)
        self.assertEqual(cw.heartbeat_info(None)["client"], "corner_worker.py 1.2")
        for kind in NEW:
            self.assertTrue(callable(getattr(cw.Worker, "k_" + kind, None)), kind)
        self.assertTrue({"picture_ideas", "picture_cover", "picture_draw"} <= cw.PAID)
        self.assertFalse({"story_edit", "story_verify", "picture_edit", "picture_restore", "novel_page_edit"} & cw.PAID)
        self.assertEqual({k: cw.TIMEOUT_S[k] for k in ("picture_ideas", "picture_cover", "picture_draw")},
                         {"picture_ideas": 600, "picture_cover": 300, "picture_draw": 900})
        self.assertEqual((cw.MARK, cw.STATE_MARK, cw.SCHEME), ("CORNER_C9_2026_10_09", "CORNER_STATE_C10A_2026_10_09",
                                                              "corner.1"))


class StoryKinds(Base):
    def test_story_edit_of_a_draft_in_process(self):
        before = self.story_row(35)
        desk, r = self.one("story_edit", {"story_id": 35, "fields": {"story_en": GOOD, "title": "  The river runs  ",
                                                                     "title_hi": HI}, "editor": False})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"story_id": 35, "status": "draft", "check_ok": True, "problems": [],
                                       "changed": ["story_en", "title", "title_hi"]})
        self.assertEqual(r["message"], "Story #35 changed (story_en, title, title_hi).")
        row = self.story_row(35)
        self.assertEqual((row["title"], row["title_hi"], row["story_en"], row["status"]),
                         ("The river runs", HI, GOOD, "draft"))
        v = json.loads(row["verify"])
        self.assertEqual((v["ok"], v["cited"]), (True, ["25.3"]))
        self.assertEqual(json.loads(row["cites"]), ["25.3"])                    # cites = verify's cited, as the page
        self.assertIsNone(row["approved_at"])
        self.assertNotEqual(row["updated_at"], before["updated_at"])
        self.assertEqual(self.scripts_run(), [])                               # in-process: no script for the edit
        self.assertEqual(self.scripts.calls, [["scripts/corpus_sync.py", "--db", self.db, "--apply", "--if-configured",
                                               "--doc", DOC, "--tables", "docs,stories"]])   # sent on at once
        self.assertEqual(desk.progress(1), [(1, 2, "Changing story #35"), (2, 2, "Sending it to the site")])
        self.assertEqual(r["cost"], 0.0)                                       # free

    def test_story_edit_a_proposed_episode_and_an_approved_story(self):
        desk, r = self.one("story_edit", {"story_id": 36, "fields": {"title": "A better title", "title_hi": None},
                                          "editor": False})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual((r["result"]["status"], r["result"]["changed"]), ("candidate", ["title", "title_hi"]))
        self.assertIn("a proposed episode still", r["message"])
        row = self.story_row(36)
        self.assertEqual((row["title"], row["title_hi"], row["status"]), ("A better title", None, "candidate"))
        desk, r = self.one("story_edit", {"story_id": 34, "fields": {"story_hi": "\u0915\u0925\u093e [25.3]"},
                                          "editor": True}, rid=2)
        self.assertEqual(r["status"], "done", r)
        row = self.story_row(34)
        self.assertEqual((row["status"], row["approved_at"], row["story_hi"]), ("draft", None, "\u0915\u0925\u093e [25.3]"))
        self.assertIn("a draft again, for an editor to approve", r["message"])

    def test_story_edit_refusals_change_nothing(self):
        snap = {sid: self.story_row(sid) for sid in (34, 35, 36, 37)}
        cases = [
            ({"story_id": 34, "fields": {"title": "Not mine to change"}, "editor": False},
             "story #34 was approved since; only an editor changes it now"),
            ({"story_id": 34, "fields": {"title": "Not mine to change"}, "editor": "true"},
             "only an editor changes it now"),                                 # only a JSON true is an editor
            ({"story_id": 36, "fields": {"story_en": GOOD}, "editor": True}, "a proposed episode: only its title"),
            ({"story_id": 36, "fields": {"title": "Two", "story_hi": "x"}, "editor": True}, "only its title"),
            ({"story_id": 37, "fields": {"title": "Back again"}, "editor": True}, "story #37 is retired"),
            ({"story_id": 40, "fields": {"title": "Elsewhere"}, "editor": True}, "not a story of"),
            ({"story_id": 35, "fields": {"notes": "a note"}}, "fields: notes is not changed here"),
            ({"story_id": 35, "fields": {}}, "fields: nothing to change"),
            ({"story_id": 35}, "fields: nothing to change"),
            ({"story_id": 35, "fields": {"title": "ab"}}, "title: 3 to 300 characters"),
            ({"story_id": 35, "fields": {"title": None}}, "title: 3 to 300 characters"),
            ({"story_id": 35, "fields": {"story_en": "too short"}}, "story_en: 20 to 6000 characters"),
            ({"story_id": 35, "fields": {"title": 12345}}, "fields: title must be text"),
            ({"story_id": "35; rm", "fields": {"title": "abc"}}, "not a whole number"),
        ]
        for i, (params, want) in enumerate(cases, 1):
            with self.subTest(params=params):
                desk, r = self.one("story_edit", params, rid=i)
                self.assertEqual(r["status"], "failed", r)
                self.assertIn(want, r["message"])
                self.assertEqual(desk.progress(i), [])                         # refused before any step
        self.assertEqual({sid: self.story_row(sid) for sid in (34, 35, 36, 37)}, snap)
        self.assertEqual(self.scripts.calls, [])

    def test_story_edit_cuts_to_the_pages_limits(self):
        desk, r = self.one("story_edit", {"story_id": 35, "fields": {"title": "t" * 400, "story_hi": "h" * 9000},
                                          "editor": False})
        self.assertEqual(r["status"], "done", r)
        row = self.story_row(35)
        self.assertEqual((len(row["title"]), len(row["story_hi"])), (300, 8000))   # stories_web.LIMITS

    def test_story_verify(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_stories SET story_en=?, verify=NULL, updated_at='x' WHERE id IN (34, 35)", (GOOD,))
        con.commit()
        con.close()
        desk, r = self.one("story_verify", {"story_id": 35})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"story_id": 35, "status": "draft", "title": "Draft", "check_ok": True, "problems": []})
        self.assertEqual(r["message"], "Story #35 checked: no problems.")
        row = self.story_row(35)
        self.assertEqual((json.loads(row["verify"])["ok"], row["status"]), (True, "draft"))
        self.assertNotEqual(row["updated_at"], "x")
        self.assertEqual(desk.progress(1), [(1, 2, "Checking story #35 against its passages"),
                                            (2, 2, "Sending it to the site")])
        desk, r = self.one("story_verify", {"story_id": 34}, rid=2)             # approved: checked, still approved
        self.assertEqual((r["status"], r["result"]["status"], r["result"]["check_ok"]), ("done", "approved", False))
        self.assertIn("1 problem(s)", r["message"])                            # 34 has no quotation
        self.assertEqual(self.story_row(34)["approved_at"], "2026-10-08T10:00:00")
        for rid, sid, want in ((3, 36, "story #36 is candidate; only a written story is checked"),
                               (4, 37, "story #37 is retired"), (5, 40, "not a story of")):
            desk, r = self.one("story_verify", {"story_id": sid}, rid=rid)
            self.assertEqual(r["status"], "failed")
            self.assertIn(want, r["message"])
        self.assertEqual(self.scripts_run(), [])


class PictureKinds(Base):
    def test_picture_ideas(self):
        self.scripts.ideas = 14                                                # more than a result lists
        desk, r = self.one("picture_ideas", {"max": 12})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(self.scripts_run(), [["scripts/images.py", "--db", self.db, "brief", "--doc", DOC, "--max", "12",
                                               "--more", "--yes"]])
        self.assertEqual(self.sent_on(), [])                                   # ideas are not sent on: touched set()
        res = r["result"]
        self.assertEqual(sorted(res), ["count", "ideas"])
        self.assertEqual(res["count"], 14)
        self.assertEqual(len(res["ideas"]), 12)
        first = res["ideas"][0]
        self.assertEqual(sorted(first), ["at", "brief", "image_id", "kind", "title"])
        self.assertEqual((first["kind"], first["title"], first["at"], len(first["brief"])), ("generated", "Idea 1", "25.1", 300))
        self.assertTrue(first["brief"].startswith("Brief 1: xxx"))
        self.assertTrue(all(isinstance(i["image_id"], int) and i["image_id"] > 8 for i in res["ideas"]))
        self.assertEqual([i["at"] for i in res["ideas"]][:3], ["25.1", "25.2", "25.3"])
        titles = {i["title"] for i in res["ideas"]}
        self.assertFalse(titles & {"A cover made meanwhile", "Retired at once", "Another text", "An idea"})
        self.assertEqual(r["message"], "14 idea(s) for pictures; ask for any of them to be drawn.")
        self.assertAlmostEqual(r["cost"], 0.004, places=4)                    # paid: measured on the ledger
        self.assertEqual(desk.progress(1), [(1, 2, "Reading the text for up to 12 ideas for pictures"),
                                            (2, 2, "14 ideas for pictures")])
        self.assertIn(("brief", 600), self.scripts.timeouts)
        self.assertLess(len(json.dumps(res)), 20000)                          # corner_desk_report keeps <= 20000

    def test_picture_ideas_max_and_none_found(self):
        desk, r = self.one("picture_ideas", {})
        self.assertEqual(r["status"], "done", r)
        self.assertIn("--max", self.scripts.calls[0])
        self.assertEqual(self.scripts.calls[0][self.scripts.calls[0].index("--max") + 1], "6")   # the default
        self.assertEqual(r["result"]["count"], 3)
        self.scripts.calls.clear()
        for rid, params, want in ((2, {"max": 13}, "max: at most 12"), (3, {"max": "3 --yes"}, "not a whole number"),
                                  (4, {"max": 0}, "not a whole number")):
            desk, r = self.one("picture_ideas", params, rid=rid)
            self.assertEqual(r["status"], "failed")
            self.assertIn(want, r["message"])
        self.assertEqual(self.scripts.calls, [])
        self.scripts.ideas = 0
        desk, r = self.one("picture_ideas", {"max": 2}, rid=5)
        self.assertEqual((r["status"], r["result"]), ("done", {"ideas": [], "count": 0}))
        self.assertIn("No new idea for a picture", r["message"])
        desk = state.ProgressDesk([{"id": 7, "kind": "picture_ideas", "doc_code": "gone", "params": {"max": 2}}])
        cw.run_once(desk, self.worker, 3)
        self.assertIn("not a live text", desk.final(7)["message"])

    def test_picture_cover(self):
        desk, r = self.one("picture_cover", {})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(self.scripts_run(), [["scripts/images.py", "--db", self.db, "cover", "--doc", DOC, "--more", "--yes"]])
        self.assertEqual(self.sent_on(), [])
        iid = self.q("SELECT max(id) FROM doc_images WHERE kind='cover'")[0][0]
        self.assertEqual(r["result"], {"ideas": [{"image_id": iid, "kind": "cover", "title": "Cover",
                                                  "brief": "The lake under a calm sky, a lotus on the water", "at": None}],
                                       "count": 1})
        self.assertEqual(r["message"], "An idea for a cover (#%d); ask for it to be drawn." % iid)
        self.assertIn(("cover", 300), self.scripts.timeouts)
        self.assertAlmostEqual(r["cost"], 0.002, places=4)
        self.scripts.covers = 0
        desk, r = self.one("picture_cover", {}, rid=2)
        self.assertEqual((r["status"], r["message"]), ("failed", "no idea for a cover was stored"))
        self.scripts.rc_for["images.py cover"] = 1
        self.scripts.out_for["images.py cover"] = "FAIL: the model returned no usable cover idea."
        desk, r = self.one("picture_cover", {}, rid=3)
        self.assertIn("no usable cover idea", r["message"])

    def test_picture_draw_an_idea(self):
        desk, r = self.one("picture_draw", {"image_id": 7})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"image_id": 7, "status": "draft"})
        self.assertEqual(r["message"], "Picture #7 drawn; an editor approves it.")
        self.assertEqual(self.scripts_run(), [["scripts/images.py", "--db", self.db, "approve-brief", "7"],
                                              ["scripts/images.py", "--db", self.db, "generate", "--doc", DOC, "--id", "7",
                                               "--yes"]])
        self.assertEqual(self.sent_on(), ["scripts/corpus_media.py"])          # touched media
        self.assertEqual(desk.progress(1), [(1, 3, "The idea is approved"), (2, 3, "Drawing the picture"),
                                            (3, 3, "Sending it to Drive")])
        self.assertIn(("generate", 900), self.scripts.timeouts)
        self.assertAlmostEqual(r["cost"], 0.091, places=3)

    def test_picture_draw_of_an_idea_drawn_already_or_retired(self):
        desk, r = self.one("picture_draw", {"image_id": 3})                    # drawn (a draft): nothing to do
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"image_id": 3, "status": "draft", "already": True})
        self.assertEqual(r["message"], "Idea #3 is drawn already (it is draft); nothing was drawn.")
        self.assertEqual(self.scripts.calls, [])                               # not drawn, not even sent on
        self.assertEqual(r["cost"], 0.0)
        self.assertEqual(desk.progress(1), [(2, 2, "Nothing to draw: picture #3 is drawn already")])
        desk, r = self.one("picture_draw", {"image_id": 4}, rid=2)
        self.assertEqual(r["result"], {"image_id": 4, "status": "approved", "already": True})
        for rid, iid, want in ((3, 5, "picture #5 is retired"), (4, 6, "picture #6 is retired"),
                               (5, 8, "picture #8 is not a picture of"), (6, 99, "picture #99 is not a picture of")):
            desk, r = self.one("picture_draw", {"image_id": iid}, rid=rid)
            self.assertEqual(r["status"], "failed")
            self.assertIn(want, r["message"])
        self.assertEqual(self.scripts.calls, [])

    def test_picture_edit(self):
        desk, r = self.one("picture_edit", {"image_id": 3, "fields": {"title": "The river at dawn", "caption_en": "Vitasta",
                                                                      "caption_hi": HI, "context_note": None},
                                            "editor": False})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"image_id": 3, "status": "draft",
                                       "changed": ["caption_en", "caption_hi", "context_note", "title"]})
        row = self.image_row(3)
        self.assertEqual((row["title"], row["caption_en"], row["caption_hi"], row["context_note"], row["status"],
                          row["path"]), ("The river at dawn", "Vitasta", HI, None, "draft", "p3"))
        self.assertIsNotNone(row["updated_at"])
        self.assertEqual(self.scripts.calls, [["scripts/corpus_media.py", "--db", self.db, "--apply", "--if-configured",
                                               "--doc", DOC]])                 # in-process, then sent on
        desk, r = self.one("picture_edit", {"image_id": 4, "fields": {"license": "CC BY 4.0", "caption_en": "x"},
                                            "editor": True}, rid=2)
        self.assertEqual(r["status"], "done", r)
        row = self.image_row(4)
        self.assertEqual((row["license"], row["caption_en"], row["status"], row["approved_at"]), ("CC BY 4.0", "x", "approved", None))
        desk, r = self.one("picture_edit", {"image_id": 7, "fields": {"title": "An idea, renamed"}}, rid=3)
        self.assertEqual((r["status"], self.image_row(7)["status"]), ("done", "brief"))   # an idea's words too

    def test_picture_edit_refusals(self):
        snap = {i: self.image_row(i) for i in (3, 4, 5)}
        cases = [
            ({"image_id": 4, "fields": {"caption_en": "Mine now"}, "editor": False},
             "picture #4 was approved since; only an editor changes it now"),
            ({"image_id": 3, "fields": {"license": "CC0"}, "editor": False}, "only an editor changes a picture's licence"),
            ({"image_id": 5, "fields": {"title": "Back"}, "editor": True}, "picture #5 is retired"),
            ({"image_id": 8, "fields": {"title": "Elsewhere"}, "editor": True}, "not a picture of"),
            ({"image_id": 3, "fields": {"brief": "draw it otherwise"}, "editor": True}, "fields: brief is not changed here"),
            ({"image_id": 3, "fields": {"title": "ab"}}, "title: 3 to 200 characters"),
            ({"image_id": 3, "fields": {"anchor_page": 7}}, "is not changed here"),
        ]
        for i, (params, want) in enumerate(cases, 1):
            with self.subTest(params=params):
                desk, r = self.one("picture_edit", params, rid=i)
                self.assertEqual(r["status"], "failed", r)
                self.assertIn(want, r["message"])
        self.assertEqual({i: self.image_row(i) for i in (3, 4, 5)}, snap)
        self.assertEqual(self.scripts.calls, [])

    def test_picture_restore_clears_retired_at_so_the_mirror_shows_it_again(self):
        def mirrored():
            con = cs.open_ro(self.db)
            try:
                pictures, _novels, _notes, _stats = cm.collect(con, cs.live_docs(con), root=self.tmp)
            finally:
                con.close()
            return set(pictures)
        self.assertNotIn("img:5", mirrored())
        desk, r = self.one("picture_restore", {"image_id": 5})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(r["result"], {"image_id": 5, "status": "draft"})
        row = self.image_row(5)
        self.assertEqual((row["status"], row["retired_at"]), ("draft", None))
        self.assertIn("img:5", mirrored())                                     # corpus_media.py sends it again
        self.assertEqual(self.sent_on(), ["scripts/corpus_media.py"])
        self.assertEqual(self.scripts_run(), [])
        desk, r = self.one("picture_restore", {"image_id": 6}, rid=2)          # an idea: back to brief
        self.assertEqual((r["status"], r["result"]), ("done", {"image_id": 6, "status": "brief"}))
        self.assertEqual((self.image_row(6)["status"], self.image_row(6)["retired_at"]), ("brief", None))
        self.assertIn("reaches the site once drawn", r["message"])
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_images SET retired_at='2026-10-01T00:00:00' WHERE id=4")   # odd: approved, retired_at set
        con.commit()
        con.close()
        desk, r = self.one("picture_restore", {"image_id": 4}, rid=3)
        self.assertEqual((r["status"], r["result"]["status"], self.image_row(4)["retired_at"]), ("done", "approved", None))
        for rid, iid, want in ((4, 3, "picture #3 is not retired (it is draft)"), (5, 8, "not a picture of")):
            desk, r = self.one("picture_restore", {"image_id": iid}, rid=rid)
            self.assertEqual(r["status"], "failed")
            self.assertIn(want, r["message"])


class NovelKinds(Base):
    def test_novel_page_edit_marks_a_drawn_page_stale_when_its_scene_changes(self):
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 2, "fields": {"scene": "The sage on the shore at dawn",
                                                                                 "caption": None}, "editor": False})
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(sorted(r["result"]), ["check_ok", "novel_id", "page", "stale"])
        self.assertEqual((r["result"]["novel_id"], r["result"]["page"], r["result"]["stale"]), (1, 2, True))
        self.assertIsInstance(r["result"]["check_ok"], bool)
        self.assertIn("its picture no longer matches the scene", r["message"])
        n = self.novel_full()
        p2 = n["plan"]["pages"][1]
        self.assertEqual((p2["scene"], p2["caption"]), ("The sage on the shore at dawn", ""))
        self.assertEqual(n["page_images"]["2"]["status"], "stale")
        self.assertEqual(n["page_images"]["1"]["status"], "draft")
        self.assertEqual(n["verify"]["ok"], r["result"]["check_ok"])            # novel.edit_page's own check
        self.assertEqual(self.scripts.calls, [["scripts/corpus_media.py", "--db", self.db, "--apply", "--if-configured",
                                               "--doc", DOC]])
        self.assertEqual(desk.progress(1), [(1, 2, "Changing page 2 of graphic novel #1"), (2, 2, "Sending it to the site")])
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(self.worker.pages_to_draw(con, 1, "1-3"), ([2, 3], 3))   # the stale page is drawn again
        finally:
            con.close()
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 3, "fields": {"scene": "A new scene for page three"}},
                           rid=2)
        self.assertEqual(r["result"]["stale"], False)                         # no picture yet: nothing stale
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 1, "fields": {"caption_hi": HI + " [25.1]"}}, rid=3)
        self.assertEqual(r["result"]["stale"], False)                         # the scene is the same
        self.assertEqual(self.novel_full()["page_images"]["1"]["status"], "draft")
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 1, "fields": {"scene": "Scene 1 by the lake"}}, rid=4)
        self.assertEqual(r["result"]["stale"], False)                         # given, but not changed

    def test_novel_page_edit_refusals_and_an_approved_novel(self):
        self.plan_novel(status="approved")
        before = self.novel_full()
        cases = [
            ({"novel_id": 1, "page": 2, "fields": {"caption": "Mine"}, "editor": False},
             "graphic novel #1 was approved since; only an editor changes it now"),
            ({"novel_id": 1, "page": 9, "fields": {"caption": "x"}, "editor": True}, "graphic novel #1 has no page 9"),
            ({"novel_id": 1, "page": 2, "fields": {"scene": "short"}, "editor": True}, "scene: 10 to 2000 characters"),
            ({"novel_id": 1, "page": 2, "fields": {"speech": "x"}, "editor": True}, "fields: speech is not changed here"),
            ({"novel_id": 2, "page": 2, "fields": {"caption": "x"}, "editor": True}, "not a novel of"),
        ]
        for i, (params, want) in enumerate(cases, 1):
            with self.subTest(params=params):
                desk, r = self.one("novel_page_edit", params, rid=i)
                self.assertEqual(r["status"], "failed", r)
                self.assertIn(want, r["message"])
        self.assertEqual(self.novel_full(), before)
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 2, "fields": {"caption": "Caption [25.2]."},
                                               "editor": True}, rid=9)
        self.assertEqual(r["status"], "done", r)
        n = self.novel_full()
        self.assertEqual((n["status"], n["approved_at"], n["plan"]["pages"][1]["caption"]), ("plan", None, "Caption [25.2]."))
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_novels SET status='retired' WHERE id=1")
        con.commit()
        con.close()
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 2, "fields": {"caption": "x"}, "editor": True}, rid=10)
        self.assertIn("graphic novel #1 is retired", r["message"])
        self.assertEqual(self.scripts_run(), [])

    def test_a_page_edit_that_novel_py_refuses(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_novels SET story_id=999 WHERE id=1")           # its story is gone from the desk
        con.commit()
        con.close()
        desk, r = self.one("novel_page_edit", {"novel_id": 1, "page": 2, "fields": {"caption": "x"}, "editor": True})
        self.assertEqual(r["status"], "failed", r)
        self.assertEqual(r["message"], "story #999 not found.")                 # novel.edit_page's SystemExit, as a refusal

    def test_redo_for_the_cast_and_the_pages(self):
        desk, s = self.do({"id": 1, "kind": "novel_cast", "doc_code": DOC, "params": {"novel_id": 1, "redo": True}},
                          {"id": 2, "kind": "novel_cast", "doc_code": DOC, "params": {"novel_id": 1, "redo": False}},
                          {"id": 3, "kind": "novel_cast", "doc_code": DOC, "params": {"novel_id": 1, "redo": "true"}})
        casts = [c for c in self.scripts.calls if c[0] == "scripts/novel.py"]
        self.assertEqual(casts, [["scripts/novel.py", "--db", self.db, "cast", "--id", "1", "--redo", "--yes"],
                                 ["scripts/novel.py", "--db", self.db, "cast", "--id", "1", "--yes"],
                                 ["scripts/novel.py", "--db", self.db, "cast", "--id", "1", "--yes"]])   # only a JSON true
        self.assertEqual((desk.final(1)["result"], desk.final(1)["message"]),
                         ({"novel_id": 1, "redo": True}, "The cast of graphic novel #1 is drawn again."))
        self.assertEqual(desk.final(2)["result"], {"novel_id": 1})
        self.assertEqual(desk.progress(1)[0], (1, 2, "Drawing the cast again"))
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(self.worker.pages_to_draw(con, 1, "", redo=True), ([1, 2, 3, 4, 5, 6, 7, 8], 8))
            self.assertEqual(self.worker.pages_to_draw(con, 1, "2-3,7", redo=True), ([2, 3, 7], 3))
            self.assertEqual(self.worker.pages_to_draw(con, 1, "1-2", redo=True), ([1, 2], 2))   # drawn: again
            self.assertEqual(self.worker.pages_to_draw(con, 1, "1-2"), ([], 2))                  # without redo: none
            self.assertEqual(self.worker.pages_to_draw(con, 1, "13-16", redo=True), ([], 0))
        finally:
            con.close()
        self.scripts.calls.clear()
        self.scripts.pages = [1, 2]
        desk, r = self.one("novel_draw", {"novel_id": 1, "pages": "1-2", "redo": True}, rid=4)
        self.assertEqual(r["status"], "done", r)
        self.assertEqual([c for c in self.scripts.calls if c[0] == "scripts/novel.py"],
                         [["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--pages", "1-2", "--redo", "--yes"]])
        self.assertEqual(desk.progress(4), [(1, 4, "2 pages to draw"), (2, 4, "Drawing page 1 of 2"),
                                            (3, 4, "Drawing page 2 of 2"), (4, 4, "Sending it to Drive")])
        self.assertEqual(r["result"], {"novel_id": 1, "pages": "1-2", "redo": True})
        self.assertEqual(r["message"], "Pages of graphic novel #1 drawn again; an editor approves them page by page.")
        desk, r = self.one("novel_draw", {"novel_id": 1, "pages": "1-2", "redo": False}, rid=5)
        self.assertEqual((r["message"], r["result"]), ("Nothing to draw for graphic novel #1: every page asked for has a picture.",
                                                       {"novel_id": 1, "pages": "1-2"}))   # 1.1's rule without redo
        self.scripts.calls.clear()
        self.scripts.pages = list(range(1, 9))
        desk, r = self.one("novel_draw", {"novel_id": 1, "pages": "", "redo": True}, rid=6)
        self.assertEqual([c for c in self.scripts.calls if c[0] == "scripts/novel.py"],
                         [["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--redo", "--yes"]])
        self.assertEqual(desk.progress(6)[0], (1, 10, "8 pages to draw"))     # every page, drawn or not
        self.assertEqual(r["result"], {"novel_id": 1, "pages": "all", "redo": True})
        desk, r = self.one("novel_draw", {"novel_id": 1, "pages": "13-16", "redo": True}, rid=7)
        self.assertEqual(r["message"], "Nothing to draw for graphic novel #1: its plan has no page 13-16.")


class Argv(Base):
    def test_no_free_text_reaches_a_command_line_for_any_kind(self):
        z = "zebra"
        reqs = [
            ("story_edit", {"story_id": 35, "fields": {"title": z + " title", "story_en": GOOD + " " + z}, "editor": False,
                            "note": z}),
            ("story_edit", {"story_id": 36, "fields": {"title": z + " cand", "title_hi": z}, "editor": False}),
            ("story_verify", {"story_id": 34, "note": z}),
            ("picture_edit", {"image_id": 3, "fields": {"caption_en": z, "context_note": z, "title": z + " pic"},
                              "editor": False}),
            ("picture_restore", {"image_id": 5, "note": z}),
            ("novel_page_edit", {"novel_id": 1, "page": 2, "fields": {"scene": z + " scene by the lake", "caption": z},
                                 "editor": False}),
            ("picture_ideas", {"max": 3, "note": z}),
            ("picture_cover", {"note": z, "brief": z + " my own cover idea"}),
            ("picture_draw", {"image_id": 7, "note": z}),
            ("story_range", {"from": "25.2", "to": "25.9", "title": z + " range", "why": z}),
            ("story_write", {"story_id": 36, "note": z}),
            ("story_mine", {"max": 2, "note": z}),
            ("picture_passage", {"at": "25.3", "title": z + " picture", "brief": z + " a brief long enough to draw",
                                 "caption_en": z}),
            ("story_illustrate", {"story_id": 34, "note": z}),
            ("picture_redraw", {"image_id": 3, "note": z}),
            ("novel_plan", {"story_id": 34, "pages": 10, "audience": "young", "note": z}),
            ("novel_cast", {"novel_id": 1, "redo": True, "note": z}),
            ("novel_draw", {"novel_id": 1, "pages": "1-4", "redo": True, "note": z}),
            ("story_approve", {"story_id": 35, "force": True, "note": z}),
            ("picture_approve", {"image_id": 3, "note": z}),
            ("novel_page_approve", {"novel_id": 1, "page": 2, "note": z}),
            ("novel_approve", {"novel_id": 1, "force": True, "note": z}),
            ("picture_retire", {"image_id": 4, "note": z}),
            ("story_retire", {"story_id": 36, "note": z}),
            ("novel_retire", {"novel_id": 1, "note": z}),
        ]
        desk, s = self.do(*[{"id": i, "kind": k, "doc_code": DOC, "params": p} for i, (k, p) in enumerate(reqs, 1)])
        every = {n[2:] for n in dir(cw.Worker) if n.startswith("k_")}
        self.assertEqual(every, set(C9_KINDS) | set(NEW))
        self.assertEqual({k for k, _p in reqs}, every)                         # every kind the desk knows
        for i, (k, _p) in enumerate(reqs, 1):
            self.assertEqual(desk.final(i)["status"], "done", (k, desk.final(i)))
        self.assertGreater(len(self.scripts.calls), 20)
        for call in self.scripts.calls:
            for tok in call:
                self.assertTrue(tok == self.db or tok in ARGV_WORDS or NUMBERS_RE.match(tok), (tok, call))
        self.assertNotIn(z, json.dumps(self.scripts.calls))
        self.assertEqual(self.story_row(35)["title"], z + " title")             # the words went in as data
        self.assertEqual(self.image_row(3)["caption_en"], z)


class Budget(Base):
    def test_the_paid_kinds_wait_for_the_cap_and_the_free_ones_do_not(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE budget_state SET paused=1")
        con.commit()
        con.close()
        desk, s = self.do({"id": 1, "kind": "picture_ideas", "doc_code": DOC, "params": {"max": 3}},
                          {"id": 2, "kind": "picture_cover", "doc_code": DOC, "params": {}},
                          {"id": 3, "kind": "picture_draw", "doc_code": DOC, "params": {"image_id": 7}},
                          {"id": 4, "kind": "story_edit", "doc_code": DOC, "params": {"story_id": 35, "fields": {"title": "Free"}}},
                          {"id": 5, "kind": "picture_restore", "doc_code": DOC, "params": {"image_id": 5}})
        for i in (1, 2, 3):
            self.assertEqual(desk.final(i)["status"], "failed")
            self.assertIn("spend cap", desk.final(i)["message"])
        self.assertEqual([desk.final(i)["status"] for i in (4, 5)], ["done", "done"])
        self.assertEqual(self.scripts_run(), [])
        con = sqlite3.connect(self.db)
        con.execute("UPDATE budget_state SET paused=0")
        con.commit()
        con.close()
        self.scripts.rc_for["images.py brief"] = 1
        self.scripts.out_for["images.py brief"] = "Refusing: the spend cap is reached."
        desk, r = self.one("picture_ideas", {"max": 3}, rid=6)
        self.assertIn("the desk's spend cap is reached", r["message"])


# --------------------------------------------------------------------------- the mail flush

class Answer(io.BytesIO):
    """What urlopen gives back (a context manager with read())."""


class FakeHttp:
    """corpus-desk and corner-mail behind urlopen. Each call is checked as both functions check it: the
    signature over the body as sent, x-corpus-ts within 5 minutes, gzip; then answered."""

    def __init__(self, todo=(), mail=None):
        self.todo, self.mail, self.calls = list(todo), mail, []

    def __call__(self, req, timeout=None):
        h = {k.lower(): v for k, v in req.header_items()}
        assert req.get_method() == "POST"
        assert h["x-corpus-sig"] == hmac.new(SECRET.encode(), h["x-corpus-ts"].encode() + b"." + req.data,
                                             hashlib.sha256).hexdigest()
        assert abs(int(h["x-corpus-ts"]) - int(__import__("time").time())) < 300
        assert (h["x-corpus-encoding"], h["apikey"], h["authorization"]) == ("gzip", "anon-key", "Bearer anon-key")
        fn = req.full_url.rsplit("/", 1)[1]
        assert req.full_url == "https://proj.example.org/functions/v1/" + fn, req.full_url
        payload = json.loads(gzip.decompress(req.data).decode("utf-8"))
        self.calls.append((fn, payload, timeout))
        if fn == "corner-mail":
            return self.mail(req, payload)
        a = payload["action"]
        if a == "heartbeat":
            return Answer(json.dumps({"ok": True, "result": {"scheme": "corner.1", "queued": len(self.todo)}}).encode())
        if a == "pull":
            out, self.todo = self.todo, []
            return Answer(json.dumps({"ok": True, "result": out}).encode())
        return Answer(json.dumps({"ok": True, "result": True}).encode())


def http_error(req, code, body):
    return urllib.error.HTTPError(req.full_url, code, "error", {}, io.BytesIO(body.encode()))


class MailDesk(state.ProgressDesk):
    """The fake site queue with a mail function: what it answers, or raises."""
    answer = {"configured": True, "claimed": 2, "sent": 2, "failed": 0}
    error = None

    def __init__(self, requests):
        super().__init__(requests)
        self.events = []

    def report(self, rid, status, result=None, message=None, cost=None, log=None):
        self.events.append(("report", rid, status))
        return super().report(rid, status, result, message, cost, log)

    def mail(self, limit=10):
        self.events.append(("mail", limit))
        if self.error is not None:
            raise self.error
        return self.answer


class Mail(Base):
    def edge(self):
        return cw.EdgeDesk("https://proj.example.org/", "anon-key", SECRET)

    def test_the_signature_is_corpus_desks(self):
        self.assertEqual(cs.sign("test-secret-for-golden", "1760000000", b'{"action":"hello"}'),
                         "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16")   # lib_test.ts's golden

    def test_edge_mail_signs_and_posts_to_corner_mail(self):
        http = FakeHttp(mail=lambda req, payload: Answer(json.dumps(
            {"ok": True, "result": {"configured": True, "claimed": 3, "sent": 2, "failed": 1}}).encode()))
        edge = self.edge()
        with mock.patch.object(cw.urllib.request, "urlopen", http):
            self.assertEqual(edge.mail(), {"configured": True, "claimed": 3, "sent": 2, "failed": 1})
            self.assertEqual(edge.mail(4), {"configured": True, "claimed": 3, "sent": 2, "failed": 1})
            self.assertEqual(edge.heartbeat({"client": "x"}), {"scheme": "corner.1", "queued": 0})   # the same signing
        self.assertEqual(http.calls, [("corner-mail", {"action": "flush", "limit": 10}, cw.MAIL_TIMEOUT_S),
                                      ("corner-mail", {"action": "flush", "limit": 4}, cw.MAIL_TIMEOUT_S),
                                      ("corpus-desk", {"action": "heartbeat", "info": {"client": "x"}}, 60)])
        self.assertEqual(edge.mail_url, "https://proj.example.org/functions/v1/corner-mail")
        self.assertEqual(edge.url, "https://proj.example.org/functions/v1/corpus-desk")

    def test_edge_mail_errors_are_corner_mails_and_tried_once(self):
        tries = []

        def down(req, payload):
            tries.append(1)
            raise http_error(req, 503, '{"ok": false, "error": "boot error"}')
        edge = self.edge()
        with mock.patch.object(cw.urllib.request, "urlopen", FakeHttp(mail=down)), \
                mock.patch.object(cw.time, "sleep", lambda s: self.fail("a mail flush is not retried")):
            with self.assertRaises(cw.SinkError) as cm_:
                edge.mail()
        self.assertEqual((str(cm_.exception), cm_.exception.status, len(tries)),
                         ('corner-mail HTTP 503: {"ok": false, "error": "boot error"}', 503, 1))
        with mock.patch.object(cw.urllib.request, "urlopen", FakeHttp(mail=lambda req, p: Answer(
                b'{"ok": false, "error": "limit: a number from 1 to 20"}'))):
            with self.assertRaises(cw.SinkError) as cm_:
                edge.mail()
        self.assertEqual(str(cm_.exception), "corner-mail: limit: a number from 1 to 20")

    def test_a_round_through_edge_desk_where_corner_mail_is_not_deployed(self):
        def missing(req, payload):
            raise http_error(req, 404, '{"code":"NOT_FOUND","message":"Requested function was not found"}')
        http = FakeHttp(todo=[{"id": 11, "kind": "story_verify", "doc_code": DOC, "params": {"story_id": 35},
                               "est_usd": 0, "attempts": 1}], mail=missing)
        with mock.patch.object(cw.urllib.request, "urlopen", http):
            s = cw.run_once(self.edge(), self.worker, 3)
        self.assertEqual((s["taken"], s["done"], s["failed"], s["stopped"]), (1, 1, 0, "done"), s)
        self.assertEqual(s["mail"], {"error": "corner-mail is not deployed"})
        self.assertEqual([(c[0], c[1]["action"], c[1].get("status")) for c in http.calls],
                         [("corpus-desk", "heartbeat", None), ("corpus-desk", "pull", None),
                          ("corpus-desk", "report", "running"), ("corpus-desk", "report", "done"),
                          ("corner-mail", "flush", None)])                     # once, after the requests
        self.assertIn("mail: corner-mail is not deployed", self.said)

    def test_the_mail_flush_comes_once_a_round_after_the_requests(self):
        desk = MailDesk([{"id": 1, "kind": "story_verify", "doc_code": DOC, "params": {"story_id": 35}},
                         {"id": 2, "kind": "picture_edit", "doc_code": DOC, "params": {"image_id": 3, "fields": {"title": "New"}}}])
        s = cw.run_once(desk, self.worker, 5, progress=True)
        self.assertEqual(s["mail"], {"configured": True, "claimed": 2, "sent": 2, "failed": 0})
        self.assertEqual(desk.events[-1], ("mail", 10))
        self.assertEqual([e for e in desk.events if e[0] == "mail"], [("mail", 10)])
        self.assertEqual([e for e in desk.events if e[0] == "report" and e[2] in ("done", "failed")],
                         [("report", 1, "done"), ("report", 2, "done")])
        self.assertIn("mail: 2 claimed, 2 sent, 0 failed", self.said)
        desk = MailDesk([])
        s = cw.run_once(desk, self.worker, 5)                                   # nothing to do: the mail still goes
        self.assertEqual((s["taken"], desk.events), (0, [("mail", 10)]))
        MailDesk.answer, desk = {"configured": False}, MailDesk([])
        try:
            self.assertEqual(cw.run_once(desk, self.worker, 5)["mail"], {"configured": False})
        finally:
            MailDesk.answer = {"configured": True, "claimed": 2, "sent": 2, "failed": 0}

    def test_a_mail_problem_never_fails_the_round(self):
        cases = [
            (cw.SinkError("corner-mail HTTP 404: {}", 404), "corner-mail is not deployed"),
            (cw.SinkError('corner-mail HTTP 404: {"message":"Requested function was not found"}'), "corner-mail is not deployed"),
            (cw.SinkError("corner-mail HTTP 422: corner_mail_claim: Could not find the function "
                          "public.corner_mail_claim(p_limit) in the schema cache", 422), "C12 is not applied in the database yet"),
            (cw.SinkError("corner-mail unreachable: <urlopen error timed out>"), "corner-mail unreachable: <urlopen error timed out>"),
            (cw.SinkError("corner-mail HTTP 500: key AIzaSyA1234567890abcdefghijklmnop", 500), "corner-mail HTTP 500: key [redacted]"),
            (ValueError("x" * 500), "x" * 300),
            (ZeroDivisionError(), "ZeroDivisionError"),
        ]
        for i, (err, want) in enumerate(cases, 1):
            with self.subTest(err=err):
                desk = MailDesk([{"id": i, "kind": "story_verify", "doc_code": DOC, "params": {"story_id": 35}}])
                desk.error = err
                s = cw.run_once(desk, self.worker, 5)
                self.assertEqual((s["done"], s["failed"], s["stopped"], desk.final(i)["status"]), (1, 0, "done", "done"))
                self.assertEqual(s["mail"], {"error": want})

    def test_pg_desk_mail_and_a_desk_without_mail(self):
        pg = object.__new__(cw.PgDesk)                                          # no database needed for this
        self.assertEqual((pg.mail(), pg.mail(3)), ({"configured": False}, {"configured": False}))
        desk = state.ProgressDesk([])                                           # the 1.1 tests' fake: no mail
        self.assertIsNone(cw.run_once(desk, self.worker, 3)["mail"])
        self.assertIsNone(cw.flush_mail(desk))

    def test_the_summary_line_and_the_log_carry_the_mail(self):
        log = self.tmp / "log.jsonl"
        cw.log_run({"taken": 0, "mail": {"error": "corner-mail is not deployed"}}, log)
        rec = json.loads(log.read_text(encoding="utf-8"))
        self.assertEqual((rec["mail"], rec["client"]), ({"error": "corner-mail is not deployed"}, "corner_worker.py 1.2"))


# --------------------------------------------------------------------------- against PostgreSQL

@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class PgRound(Base):
    """Worker 1.2 against C9 + C10a + C10b: the new kinds are asked for through corner_request_create (by a
    researcher and an admin), pulled, carried out on the desk's context.db and reported back; a picture_draw
    can then be asked for the ideas the desk proposed."""

    @classmethod
    def setUpClass(cls):
        import psycopg
        import test_corner_kinds_pg_2026_10_09 as c10b
        if "supabase" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.k = c10b
        cls.pg = psycopg.connect(DSN, autocommit=True)
        x = cls.pg.execute
        for f in c10b.BEFORE:
            x(f.read_text(encoding="utf-8"))
        x("INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'dhruv.rakesh@gmail.com', now()), "
          "(%s, 'admin@example.org', now()), (%s, 'kanika@example.org', now()), (%s, 'r2@example.org', now()), "
          "(%s, 'reader@example.org', now()) ON CONFLICT DO NOTHING",
          (c10b.SUPER, c10b.ADMIN, c10b.RES, c10b.RES2, c10b.READER))
        for f in c10b.AFTER:                                                    # C9, C10a and C10b, each twice
            x(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        super().setUp()
        k, x = self.k, self.pg.execute
        x("TRUNCATE corner.requests, corner.collections, corner.collection_items, corner.events RESTART IDENTITY")
        x("UPDATE corner.settings SET value = CASE key WHEN 'daily_cap_usd' THEN '2.00' "
          "WHEN 'researchers_need_approval' THEN 'true' ELSE '20' END")
        x("UPDATE corner.worker SET last_seen = NULL, info = NULL")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("DELETE FROM public.user_roles WHERE user_id IN (%s, %s, %s)", (k.ADMIN, k.RES, k.RES2))
        x("INSERT INTO public.user_roles (user_id, role) VALUES (%s, 'admin'), (%s, 'researcher'), (%s, 'researcher')",
          (k.ADMIN, k.RES, k.RES2))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES (%s, 'Nilamata', 'x')", (DOC,))
        for sid, st_ in ((34, "approved"), (35, "draft"), (36, "candidate")):
            x("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, row_hash) "
              "VALUES (%s, %s, %s, %s, 'Text', 'x')", (DOC, sid, st_, "Story %d" % sid))
        for key, status, retired in (("img:3", "draft", False), ("img:5", "draft", True)):
            x("INSERT INTO corpus.media (media_key, doc_code, kind, status, title, sha256, row_hash, retired_at) "
              "VALUES (%s, %s, 'generated', %s, 'Pic', %s, 'x', CASE WHEN %s THEN now() END)",
              (key, DOC, status, "a" * 64, retired))
        x("INSERT INTO corpus.novels (novel_id, doc_code, story_id, status, pages, row_hash) "
          "VALUES (1, %s, 34, 'drawing', 8, 'x')", (DOC,))

    def call(self, sql, args=(), uid=None):
        with self.pg.transaction():
            self.pg.execute("SET LOCAL ROLE authenticated")
            self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid or self.k.RES,))
            return self.pg.execute(sql, args).fetchall()

    def ask(self, kind, params, uid=None):
        rows = self.call("SELECT request_id, request_status FROM public.corner_request_create(%s, %s, %s::jsonb, NULL)",
                         (kind, DOC, json.dumps(params)), uid)
        return rows[0]

    def round(self):
        desk = cw.PgDesk(DSN)
        try:
            return cw.run_once(desk, self.worker, 20, "test-desk", progress=True)
        finally:
            desk.con.close()

    def req(self, rid):
        return self.pg.execute("SELECT status, params, result, message FROM corner.requests WHERE id = %s", (rid,)).fetchone()

    def test_the_new_kinds_end_to_end(self):
        k = self.k
        asked = {
            "edit35": self.ask("story_edit", {"story_id": 35, "story_en": GOOD, "title_hi": HI}),            # researcher
            "edit34": self.ask("story_edit", {"story_id": 34, "title": "The lake, again"}, k.ADMIN),          # editor
            "verify34": self.ask("story_verify", {"story_id": 34}),
            "ideas": self.ask("picture_ideas", {"max": 3}, k.ADMIN),
            "cover": self.ask("picture_cover", {}, k.ADMIN),
            "pedit": self.ask("picture_edit", {"image_id": 3, "caption_en": "The river at dawn", "caption_hi": HI}),
            "restore": self.ask("picture_restore", {"image_id": 5}, k.ADMIN),
            "page": self.ask("novel_page_edit", {"novel_id": 1, "page": 2, "scene": "The sage on the shore at dawn"}),
            "cast": self.ask("novel_cast", {"novel_id": 1, "redo": True}, k.ADMIN),
            "draw": self.ask("novel_draw", {"novel_id": 1, "pages": "1-2", "redo": True}, k.ADMIN),
        }
        self.assertEqual({n: a[1] for n, a in asked.items()}, {n: "approved" for n in asked})
        rid = {n: a[0] for n, a in asked.items()}
        self.assertEqual(self.req(rid["edit35"])[1], {"story_id": 35, "fields": {"story_en": GOOD, "title_hi": HI},
                                                      "editor": False})
        self.assertEqual(self.req(rid["edit34"])[1]["editor"], True)
        self.scripts.pages = [1, 2]
        s = self.round()
        self.assertEqual((s["taken"], s["done"], s["failed"]), (10, 10, 0), s)
        self.assertEqual(s["mail"], {"configured": False})
        st35 = self.req(rid["edit35"])
        self.assertEqual((st35[0], st35[2]), ("done", {"story_id": 35, "status": "draft", "check_ok": True, "problems": [],
                                                       "changed": ["story_en", "title_hi"]}))
        self.assertEqual((self.story_row(35)["story_en"], self.story_row(35)["title_hi"]), (GOOD, HI))
        self.assertEqual((self.story_row(34)["title"], self.story_row(34)["status"]), ("The lake, again", "draft"))
        self.assertEqual(self.req(rid["verify34"])[2]["story_id"], 34)
        ideas = self.req(rid["ideas"])[2]
        self.assertEqual((ideas["count"], [i["at"] for i in ideas["ideas"]]), (3, ["25.1", "25.2", "25.3"]))
        cover = self.req(rid["cover"])[2]
        self.assertEqual((cover["count"], cover["ideas"][0]["kind"], cover["ideas"][0]["at"]), (1, "cover", None))
        self.assertEqual((self.image_row(3)["caption_en"], self.image_row(3)["caption_hi"]), ("The river at dawn", HI))
        self.assertEqual((self.image_row(5)["status"], self.image_row(5)["retired_at"]), ("draft", None))
        self.assertEqual(self.req(rid["page"])[2], {"novel_id": 1, "page": 2, "check_ok": self.novel_full()["verify"]["ok"],
                                                    "stale": True})
        self.assertIn(["scripts/novel.py", "--db", self.db, "cast", "--id", "1", "--redo", "--yes"], self.scripts.calls)
        self.assertIn(["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--pages", "1-2", "--redo", "--yes"],
                      self.scripts.calls)
        self.assertEqual(self.req(rid["draw"])[2], {"novel_id": 1, "pages": "1-2", "redo": True})
        prog = self.pg.execute("SELECT progress FROM corner.requests WHERE id = %s", (rid["draw"],)).fetchone()[0]
        self.assertEqual((prog["step"], prog["of"], prog["note"]), (4, 4, "Sending it to Drive"))
        info = self.pg.execute("SELECT info FROM corner.worker").fetchone()[0]
        self.assertEqual(info["client"], "corner_worker.py 1.2")

        # round 2: an idea the desk proposed is drawn (a researcher's paid request, approved by an editor), and
        # an edit the mirror allowed is refused by the desk, where the story was approved since
        iid = ideas["ideas"][0]["image_id"]
        d, d_status = self.ask("picture_draw", {"image_id": iid})
        self.assertEqual(d_status, "pending")
        self.assertEqual(self.call("SELECT request_status FROM public.corner_request_decide(%s, true)", (d,), k.ADMIN),
                         [("approved",)])
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_stories SET status='approved' WHERE id=35")
        con.commit()
        con.close()
        e, _ = self.ask("story_edit", {"story_id": 35, "title": "Mine to change?"})    # the mirror says draft
        s = self.round()
        self.assertEqual((s["taken"], s["done"], s["failed"]), (2, 1, 1), s)
        self.assertEqual(self.req(d)[:1] + (self.req(d)[2],), ("done", {"image_id": iid, "status": "draft"}))
        self.assertEqual(self.image_row(iid)["status"], "draft")
        refused = self.req(e)
        self.assertEqual((refused[0], refused[3]), ("failed", "story #35 was approved since; only an editor changes it now"))
        self.assertEqual(self.story_row(35)["title"], "Draft")
        shown = self.call("SELECT image_id, kind, at, drawn, draw_request_id, draw_status FROM public.corner_ideas(%s) "
                          "ORDER BY image_id", (DOC,))
        self.assertEqual(len(shown), 4)
        self.assertIn((iid, "generated", "25.1", False, d, "done"), shown)   # drawn on the desk, not yet mirrored
        self.pg.execute("INSERT INTO corpus.media (media_key, doc_code, kind, status, title, sha256, row_hash) "
                        "VALUES (%s, %s, 'generated', 'draft', 'Drawn', %s, 'x')", ("img:%d" % iid, DOC, "b" * 64))
        with self.assertRaisesRegex(Exception, "this idea is drawn already"):   # once mirrored, corner._clean says so
            self.ask("picture_draw", {"image_id": iid})


if __name__ == "__main__":
    unittest.main()
