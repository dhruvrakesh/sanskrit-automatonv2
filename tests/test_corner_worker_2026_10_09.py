# -*- coding: ascii -*-
"""CORNER_C9_2026_10_09: scripts/corner_worker.py (the desk carries out the Corner's approved requests).

A small context.db, a fake site queue and a fake runner that does to the database what the desk's
scripts would do, so every request kind is carried out end to end without a paid call. The last
class runs against PostgreSQL with C9 (CORPUS_TEST_DSN, a throwaway database).
  python -m unittest tests.test_corner_worker_2026_10_09 -v
"""
import json, os, shutil, sqlite3, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import corner_worker as cw  # noqa: E402
import cost_tracker  # noqa: E402
import images as im  # noqa: E402
import novel as nv  # noqa: E402
import stories as st  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
DOC = "nilamata_seg"


class FakeDesk:
    name = "fake"

    def __init__(self, requests):
        self.queue = list(requests)
        self.reports = []
        self.beats = []

    def heartbeat(self, info):
        self.beats.append(info)
        return {"scheme": "corner.1", "queued": len(self.queue)}

    def pull(self, limit, worker):
        out, self.queue = self.queue[:limit], self.queue[limit:]
        return out

    def report(self, rid, status, result=None, message=None, cost=None, log=None):
        self.reports.append({"id": rid, "status": status, "result": result, "message": message, "cost": cost, "log": log})
        return True

    def final(self, rid):
        return [r for r in self.reports if r["id"] == rid][-1]


class FakeScripts:
    """What the desk's scripts do to context.db, without any model call."""

    def __init__(self, db):
        self.db, self.calls, self.rc_for, self.out_for = db, [], {}, {}

    def __call__(self, args, timeout):
        self.calls.append(list(args))
        assert all(isinstance(a, str) for a in args) and args[0].startswith("scripts/")
        name, rest = args[0].split("/")[1], args[3:]
        key = " ".join([name] + rest[:1])
        if key in self.rc_for:
            return self.rc_for[key], self.out_for.get(key, "FAIL: no")
        con = sqlite3.connect(self.db)
        try:
            out = self.apply(con, name, rest)
            con.commit()
        finally:
            con.close()
        return 0, out

    def cost(self, con, doc, usd):
        con.execute("INSERT INTO usage_log(kind, doc, engine, cost_usd, ts) VALUES('x', ?, 'gemini', ?, ?)",
                    (doc, usd, time.strftime("%Y-%m-%dT%H:%M:%S.500Z", time.gmtime())))

    def apply(self, con, name, a):
        cmd = a[0]
        arg = lambda k: a[a.index(k) + 1]
        if name == "stories.py" and cmd == "write":
            con.execute("UPDATE doc_stories SET status='draft', story_en='Told.', verify=?, provenance=? WHERE id=?",
                        (json.dumps({"ok": True, "problems": []}), json.dumps({"given": []}), int(arg("--id"))))
            self.cost(con, DOC, 0.007)
            return "story written"
        if name == "stories.py" and cmd == "mine":
            for t in ("Ep one", "Ep two"):
                con.execute("INSERT INTO doc_stories(doc_id, status, title, from_page, from_idx, to_page, to_idx) "
                            "VALUES(1, 'candidate', ?, 25, 1, 25, 3)", (t,))
            return "2 candidates"
        if name == "stories.py" and cmd == "illustrate":
            sid = int(arg("--id"))
            cur = con.execute("INSERT INTO doc_images(doc_id, status, title, brief, anchor_page, anchor_idx) "
                              "VALUES(1, 'brief', 'Idea', 'A brief long enough', 25, 3)")
            con.execute("UPDATE doc_stories SET image_id=? WHERE id=?", (cur.lastrowid, sid))
            return "idea stored"
        if name == "stories.py" and cmd in ("approve", "retire"):
            con.execute("UPDATE doc_stories SET status=? WHERE id=?",
                        ("approved" if cmd == "approve" else "retired", int(arg("--id"))))
            return "ok"
        if name == "images.py" and cmd == "approve-brief":
            con.execute("UPDATE doc_images SET status='brief-approved' WHERE id=?", (int(a[1]),))
            return "ok"
        if name == "images.py" and cmd == "generate":
            con.execute("UPDATE doc_images SET status='draft', path='data/images/x.jpg' WHERE id=?", (int(arg("--id")),))
            self.cost(con, arg("--doc"), 0.091)
            return "drawn"
        if name == "images.py" and cmd == "regenerate":
            old = con.execute("SELECT lineage_id, version FROM doc_images WHERE id=?", (int(a[1]),)).fetchone()
            con.execute("INSERT INTO doc_images(doc_id, lineage_id, version, status, path) VALUES(1, ?, ?, 'draft', 'p')",
                        (old[0], old[1] + 1))
            return "redrawn"
        if name == "images.py" and cmd in ("approve", "retire"):
            con.execute("UPDATE doc_images SET status=? WHERE id=?", ("approved" if cmd == "approve" else "retired", int(a[1])))
            return "ok"
        if name == "novel.py" and cmd == "plan":
            con.execute("INSERT INTO doc_novels(story_id, doc_id, status, pages) VALUES(?, 1, 'plan', ?)",
                        (int(arg("--story")), int(arg("--pages"))))
            return "planned"
        if name == "novel.py":
            return "ok"
        if name in ("corpus_sync.py", "corpus_media.py"):
            return "sent"
        raise AssertionError("unexpected script %s %s" % (name, a))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cwtest_"))
        self.db = str(self.tmp / "context.db")
        con = sqlite3.connect(self.db)
        con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT, src_path TEXT, glossary TEXT, "
                          "created_at TEXT);"
                          "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, "
                          "text TEXT, iast TEXT, translation TEXT, text_type TEXT);")
        con.executescript(st.SCHEMA + im.SCHEMA + nv.SCHEMA)
        cost_tracker.ensure_usage_schema(con)
        con.execute("UPDATE budget_state SET budget_usd=10, spent_usd=1, paused=0")
        con.execute("INSERT INTO docs(id, code) VALUES (1, ?), (2, 'other')", (DOC,))
        for i in range(1, 15):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type) VALUES (1, 25, ?, 's', ?, 'mula')",
                        (i, "translation %d" % i))
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type) VALUES (1, 25, 15, 's', 'x', 'noise')")
        con.execute("INSERT INTO doc_stories(id, doc_id, status, title, from_page, from_idx, to_page, to_idx, story_en) "
                    "VALUES (34, 1, 'approved', 'Lake', 25, 1, 25, 6, 'Told'), (35, 1, 'draft', 'Draft', 25, 2, 25, 4, 'T'), "
                    "(36, 1, 'candidate', 'Cand', 25, 1, 25, 2, NULL), (40, 2, 'draft', 'Elsewhere', 1, 1, 1, 2, 'T')")
        con.execute("INSERT INTO doc_images(id, doc_id, lineage_id, version, status, title, path) "
                    "VALUES (3, 1, 3, 1, 'draft', 'Pic', 'p3')")
        con.execute("INSERT INTO doc_novels(id, story_id, doc_id, status, pages) VALUES (1, 34, 1, 'drawing', 8)")
        con.commit()
        con.close()
        self.scripts = FakeScripts(self.db)
        self.worker = cw.Worker(self.db, runner=self.scripts, ledger=self.tmp / "made.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def do(self, *reqs, limit=10):
        desk = FakeDesk([dict({"est_usd": 0.01, "attempts": 1}, **r) for r in reqs])
        s = cw.run_once(desk, self.worker, limit)
        return desk, s

    def q(self, sql, *a):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(sql, a).fetchall()
        finally:
            con.close()


class Kinds(Base):
    def test_story_from_passages_once_even_when_retried(self):
        req = {"id": 7, "kind": "story_range", "doc_code": DOC,
               "params": {"from": "25.2", "to": "25.9", "title": "Vitasta flows", "why": "asked"}}
        desk, s = self.do(req)
        r = desk.final(7)
        self.assertEqual(r["status"], "done", r)
        sid = r["result"]["story_id"]
        self.assertEqual(self.q("SELECT status, title, from_page, from_idx, to_idx FROM doc_stories WHERE id=?", sid),
                         [("draft", "Vitasta flows", 25, 2, 9)])
        self.assertEqual(r["result"]["check_ok"], True)
        self.assertAlmostEqual(r["cost"], 0.007, places=4)                     # measured on the desk's ledger
        self.assertIn(["scripts/stories.py", "--db", self.db, "write", "--id", str(sid), "--yes"], self.scripts.calls)
        self.assertIn(["scripts/corpus_sync.py", "--db", self.db, "--apply", "--if-configured", "--doc", DOC,
                       "--tables", "docs,stories"], self.scripts.calls)          # sent on at once
        self.assertEqual([x["status"] for x in desk.reports], ["running", "done"])
        n = self.q("SELECT count(*) FROM doc_stories")[0][0]
        self.do(req)                                                           # the site gave it again (a retry)
        self.assertEqual(self.q("SELECT count(*) FROM doc_stories")[0][0], n)  # the same candidate, not a second

    def test_bad_requests_fail_with_a_reason_and_nothing_is_run(self):
        cases = [
            ({"kind": "story_range", "doc_code": DOC, "params": {"from": "25.15", "to": "25.15", "title": "abc"}}, "translated passages"),
            ({"kind": "story_range", "doc_code": "gone", "params": {"from": "25.1", "to": "25.2", "title": "abc"}}, "not a live text"),
            ({"kind": "story_write", "doc_code": DOC, "params": {"story_id": 40}}, "not a story of"),
            ({"kind": "story_write", "doc_code": DOC, "params": {"story_id": 34}}, "only a proposed episode"),
            ({"kind": "novel_plan", "doc_code": DOC, "params": {"story_id": 35, "pages": 10, "audience": "general"}}, "approved story"),
            ({"kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "1;rm -rf"}}, "pages: such as"),
            ({"kind": "picture_redraw", "doc_code": DOC, "params": {"image_id": "3 --yes"}}, "not a whole number"),
            ({"kind": "format_disk", "doc_code": DOC, "params": {}}, "does not know"),
        ]
        for i, (req, want) in enumerate(cases, 1):
            with self.subTest(req=req):
                desk, s = self.do(dict(req, id=i))
                self.assertEqual(desk.final(i)["status"], "failed")
                self.assertIn(want, desk.final(i)["message"])
        self.assertEqual([c for c in self.scripts.calls if "corpus" not in c[0]], [])

    def test_a_picture_for_a_passage_from_the_persons_own_brief(self):
        desk, s = self.do({"id": 9, "kind": "picture_passage", "doc_code": DOC, "params": {
            "at": "25.3", "title": "The river", "brief": "Show the river goddess flowing to the sea", "caption_en": "Vitasta"}})
        r = desk.final(9)
        self.assertEqual(r["status"], "done", r)
        iid = r["result"]["image_id"]
        row = self.q("SELECT status, anchor_page, anchor_idx, title, brief, caption_en, provenance FROM doc_images WHERE id=?", iid)[0]
        self.assertEqual(row[:6], ("draft", 25, 3, "The river", "Show the river goddess flowing to the sea", "Vitasta"))
        self.assertEqual(json.loads(row[6])["corner_request"], 9)
        self.assertIn(["scripts/images.py", "--db", self.db, "approve-brief", str(iid)], self.scripts.calls)
        self.assertIn(["scripts/images.py", "--db", self.db, "generate", "--doc", DOC, "--id", str(iid), "--yes"],
                      self.scripts.calls)
        self.assertIn(["scripts/corpus_media.py", "--db", self.db, "--apply", "--if-configured", "--doc", DOC],
                      self.scripts.calls)
        self.assertAlmostEqual(r["cost"], 0.091, places=3)
        flat = " ".join(" ".join(c) for c in self.scripts.calls)
        self.assertNotIn("river goddess", flat)                               # free text never on a command line

    def test_illustrate_redraw_mine_and_the_novel(self):
        desk, s = self.do({"id": 1, "kind": "story_illustrate", "doc_code": DOC, "params": {"story_id": 34}},
                          {"id": 2, "kind": "picture_redraw", "doc_code": DOC, "params": {"image_id": 3}},
                          {"id": 3, "kind": "story_mine", "doc_code": DOC, "params": {"max": 2}},
                          {"id": 4, "kind": "novel_plan", "doc_code": DOC, "params": {"story_id": 34, "pages": 10, "audience": "young"}},
                          {"id": 5, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "1-4"}},
                          {"id": 6, "kind": "novel_cast", "doc_code": DOC, "params": {"novel_id": 1}})
        for i in range(1, 7):
            self.assertEqual(desk.final(i)["status"], "done", desk.final(i))
        self.assertEqual(desk.final(1)["result"]["story_id"], 34)
        self.assertEqual(desk.final(2)["result"]["replaces"], 3)
        self.assertEqual(desk.final(3)["result"]["count"], 2)
        self.assertEqual(self.q("SELECT pages FROM doc_novels WHERE id=?", desk.final(4)["result"]["novel_id"]), [(10,)])
        self.assertIn(["scripts/novel.py", "--db", self.db, "plan", "--story", "34", "--pages", "10", "--audience", "young",
                       "--yes"], self.scripts.calls)
        self.assertIn(["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--pages", "1-4", "--yes"], self.scripts.calls)

    def test_editors_decisions(self):
        desk, s = self.do({"id": 1, "kind": "story_approve", "doc_code": DOC, "params": {"story_id": 35, "force": True}},
                          {"id": 2, "kind": "picture_approve", "doc_code": DOC, "params": {"image_id": 3}},
                          {"id": 3, "kind": "novel_page_approve", "doc_code": DOC, "params": {"novel_id": 1, "page": 2}},
                          {"id": 4, "kind": "story_retire", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertEqual([desk.final(i)["status"] for i in range(1, 5)], ["done"] * 4)
        self.assertIn(["scripts/stories.py", "--db", self.db, "approve", "--id", "35", "--force"], self.scripts.calls)
        self.assertEqual(self.q("SELECT status FROM doc_stories WHERE id IN (35, 36) ORDER BY id"), [("approved",), ("retired",)])

    def test_the_spend_cap_and_a_script_that_fails(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE budget_state SET paused=1")
        con.commit()
        con.close()
        desk, s = self.do({"id": 1, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}},
                          {"id": 2, "kind": "story_retire", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertIn("spend cap", desk.final(1)["message"])                  # paid: refused before any call
        self.assertEqual(desk.final(2)["status"], "done")                      # a decision costs nothing
        con = sqlite3.connect(self.db)
        con.execute("UPDATE budget_state SET paused=0")
        con.execute("UPDATE doc_stories SET status='draft' WHERE id=36")
        con.commit()
        con.close()
        self.scripts.rc_for["stories.py write"] = 0
        self.scripts.out_for["stories.py write"] = "Stopping: the spend cap is reached."
        desk, s = self.do({"id": 3, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertIn("spend cap is reached", desk.final(3)["message"])
        self.scripts.rc_for["stories.py write"] = 1
        self.scripts.out_for["stories.py write"] = "FAIL: story #36: no translated passages in its range."
        desk, s = self.do({"id": 4, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertEqual(desk.final(4)["status"], "failed")
        self.assertIn("no translated passages", desk.final(4)["message"])

    def test_a_bug_never_leaves_a_request_running(self):
        def boom(*a, **k):
            raise ZeroDivisionError("oops")
        self.worker.k_story_retire = boom
        desk, s = self.do({"id": 1, "kind": "story_retire", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertEqual(desk.final(1)["status"], "failed")
        self.assertIn("oops", desk.final(1)["message"])

    def test_one_run_at_a_time_and_secrets_are_not_logged(self):
        lock = self.tmp / "l.lock"
        with cw.Lock(lock) as a:
            self.assertTrue(a.held)
            with cw.Lock(lock) as b:
                self.assertFalse(b.held)
        self.assertFalse(lock.exists())
        self.assertNotIn("AIzaSyA", cw.tail("key AIzaSyA1234567890abcdefghijklmnop end"))

    def test_hello_and_unconfigured(self):
        from unittest import mock
        import corpus_sync as cs
        with mock.patch.object(cs, "load_config", lambda: {"secret": "", "url": "", "anon": "", "dsn": ""}):
            self.assertEqual(cw.main(["--apply", "--if-configured"]), 0)
        self.assertTrue(cw.not_ready(cw.SinkError("corpus-desk HTTP 404: x", 404)))
        self.assertTrue(cw.not_ready(cw.SinkError("corpus-desk HTTP 422: corner_desk_state: Could not find the function", 422)))


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class PgEndToEnd(Base):
    """C9's own queue: an editor's request is pulled, carried out, and reported back."""

    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        if cls.pg.execute("SELECT to_regclass('corner.requests')").fetchone()[0] is None:
            raise unittest.SkipTest("C9 is not applied in this test database (run tests.test_corner_pg_2026_10_09 first)")

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def test_pull_do_report(self):
        x = self.pg.execute
        x("TRUNCATE corner.requests, corner.events RESTART IDENTITY")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES (%s, 'Nilamata', 'x')", (DOC,))
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, row_hash) VALUES (%s, 36, 'candidate', 'C', 'x')", (DOC,))
        with self.pg.transaction():
            x("SET LOCAL ROLE authenticated")
            x("SELECT set_config('request.jwt.claim.sub', '44444444-4444-4444-4444-444444444444', true)")
            rid = x("SELECT request_id FROM public.corner_request_create('story_write', %s, '{\"story_id\": 36}', NULL)",
                    (DOC,)).fetchone()[0]
        desk = cw.PgDesk(DSN)
        try:
            s = cw.run_once(desk, self.worker, 3, "test-desk")
        finally:
            desk.con.close()
        self.assertEqual((s["taken"], s["done"]), (1, 1), s)
        row = x("SELECT status, result ->> 'story_id', worker, cost_usd FROM corner.requests WHERE id = %s", (rid,)).fetchone()
        self.assertEqual((row[0], row[1], row[2]), ("done", "36", "test-desk"))
        self.assertAlmostEqual(float(row[3]), 0.007, places=4)
        self.assertIsNotNone(x("SELECT last_seen FROM corner.worker").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
