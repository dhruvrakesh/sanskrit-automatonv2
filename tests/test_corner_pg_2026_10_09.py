# -*- coding: ascii -*-
"""CORNER_C9_2026_10_09 against a real PostgreSQL: docs/cloud/C9 (the Researchers' Corner). Applies the
Supabase stand-ins, C4, C4b, C5, C7a, C7, C8 and C9 (twice), then asks, decides, pulls and reports as the
roles do: anon, a signed-in reader, a researcher, an admin, the super admin and the desk (service_role).

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corner_pg_2026_10_09
"""
import json, os, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
BEFORE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", REPO / "tests" / "supabase_stubs_rbac_2026_10_08.sql",
          CLOUD / "C4_corpus_mirror_2026-10-08.sql", CLOUD / "C4b_mirror_digests_2026-10-08.sql",
          CLOUD / "C5_corpus_reader_2026-10-08.sql", CLOUD / "C7a_rbac_roles_2026-10-08.sql"]
AFTER = [CLOUD / "C7_rbac_researchers_2026-10-08.sql", CLOUD / "C8_corpus_media_2026-10-09.sql",
         CLOUD / "C9_researchers_corner_2026-10-09.sql", CLOUD / "C9_researchers_corner_2026-10-09.sql"]
SUPER = "11111111-1111-1111-1111-111111111111"
ADMIN = "44444444-4444-4444-4444-444444444444"
RES = "55555555-5555-5555-5555-555555555555"
RES2 = "66666666-6666-6666-6666-666666666666"
READER = "33333333-3333-3333-3333-333333333333"
SHA = lambda c: c * 64
SITE = ["SELECT * FROM public.corner_me()", "SELECT * FROM public.corner_kinds()",
        "SELECT * FROM public.corner_request_create('story_mine', 'nil', '{\"max\": 2}')",
        "SELECT * FROM public.corner_requests()", "SELECT * FROM public.corner_request_decide(1, true)",
        "SELECT * FROM public.corner_request_cancel(1)", "SELECT public.corner_settings_set('daily_cap_usd', '1')",
        "SELECT * FROM public.corner_collection_save(NULL, 't', NULL, NULL, 'general', '[]')",
        "SELECT * FROM public.corner_collections()", "SELECT * FROM public.corner_collection(1)",
        "SELECT * FROM public.corner_collection_publish(1, true)", "SELECT * FROM public.corner_collection_retire(1)"]
DESK = ["SELECT public.corner_desk_pull(1, 'w')", "SELECT public.corner_desk_report(1, 'done', NULL, NULL, NULL, NULL)",
        "SELECT public.corner_desk_heartbeat('{}')", "SELECT public.corner_desk_state()"]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Corner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        x = cls.pg.execute
        for f in BEFORE:
            x(f.read_text(encoding="utf-8"))
        x("INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'dhruv.rakesh@gmail.com', now()), "
          "(%s, 'admin@example.org', now()), (%s, 'kanika@example.org', now()), (%s, 'r2@example.org', now()), "
          "(%s, 'reader@example.org', now()) ON CONFLICT DO NOTHING", (SUPER, ADMIN, RES, RES2, READER))
        for f in AFTER:
            x(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        x = self.pg.execute
        x("TRUNCATE corner.requests, corner.collections, corner.collection_items, corner.events RESTART IDENTITY")
        x("UPDATE corner.settings SET value = CASE key WHEN 'daily_cap_usd' THEN '2.00' "
          "WHEN 'researchers_need_approval' THEN 'true' ELSE '20' END")
        x("UPDATE corner.worker SET last_seen = NULL, info = NULL")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("DELETE FROM public.user_roles WHERE user_id IN (%s, %s, %s)", (ADMIN, RES, RES2))
        x("INSERT INTO public.user_roles (user_id, role) VALUES (%s, 'admin'), (%s, 'researcher'), (%s, 'researcher')",
          (ADMIN, RES, RES2))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('nil', 'Nilamata', 'x'), ('mal', 'Mallapurana', 'x')")
        rows = [("nil", 25, i, "translation %d" % i, "mula") for i in range(1, 15)] + \
               [("nil", 25, 15, "running head", "noise"), ("nil", 26, 1, "", "mula"), ("mal", 1, 1, "t", "mula")]
        for doc, pg, ix, tr, tt in rows:
            x("INSERT INTO corpus.passages (doc_code, page_no, idx, translation, text_type, row_hash) "
              "VALUES (%s, %s, %s, %s, %s, 'x')", (doc, pg, ix, tr, tt))
        for sid, st in ((34, "approved"), (35, "draft"), (36, "candidate"), (37, "retired")):
            x("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, row_hash) "
              "VALUES ('nil', %s, %s, %s, %s, 'x')", (sid, st, "Story %d" % sid, "Text of %d" % sid))
        with self.pg.transaction():
            self.pg.execute("SET LOCAL ROLE service_role")
            self.pg.execute("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps([
                {"media_key": "img:3", "doc_code": "nil", "kind": "generated", "status": "draft", "story_id": 35,
                 "sha256": SHA("a"), "row_hash": "h3"},
                {"media_key": "img:4", "doc_code": "nil", "kind": "generated", "status": "approved", "story_id": 34,
                 "sha256": SHA("b"), "row_hash": "h4"}]),))
            self.pg.execute("SELECT public.corpus_novels_upsert(%s::jsonb)", (json.dumps([
                {"novel_id": 1, "doc_code": "nil", "story_id": 34, "status": "drawing", "pages": 8, "row_hash": "n1"}]),))

    # ---- helpers

    def call(self, sql, args=(), role="authenticated", uid=RES):
        with self.pg.transaction(force_rollback=False):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def ask(self, kind, doc, params, uid=RES, note=None):
        return self.call("SELECT * FROM public.corner_request_create(%s, %s, %s::jsonb, %s)",
                         (kind, doc, json.dumps(params), note), uid=uid)

    def desk(self, sql, args=()):
        return self.call(sql, args, role="service_role", uid=None)

    def status(self, rid):
        return self.pg.execute("SELECT status FROM corner.requests WHERE id = %s", (rid,)).fetchone()[0]

    # ---- who may call what

    def test_grants(self):
        for sql in SITE + DESK:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
        for sql in DESK:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql))
        self.assertIn("permission denied", self.call("SELECT * FROM corner.requests"))
        me = self.call("SELECT can_request, is_editor, is_super_admin FROM public.corner_me()", uid=READER)
        self.assertEqual(me, [(False, False, False)])                           # a reader sees the Corner's state
        self.assertIn("open to invited researchers", self.ask("story_mine", "nil", {"max": 2}, uid=READER)[0:120])
        self.assertEqual(self.call("SELECT can_request, is_editor FROM public.corner_me()", uid=RES), [(True, False)])
        self.assertEqual(self.call("SELECT is_editor, is_super_admin FROM public.corner_me()", uid=SUPER), [(True, True)])
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corner_me()", uid=None))

    # ---- asking

    def test_a_researcher_asks_and_it_waits_for_an_editor(self):
        r = self.ask("story_range", "nil", {"from": "25.2", "to": " 25.9", "title": "Vitasta flows", "why": "x"})
        self.assertEqual([(a, b, float(c), d) for a, b, c, d in r], [(1, "pending", 0.01, "Waiting for an editor's approval.")])
        self.assertEqual(self.pg.execute("SELECT params FROM corner.requests").fetchone()[0],
                         {"from": "25.2", "to": "25.9", "title": "Vitasta flows", "why": "x"})
        again = self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows", "why": "x"})
        self.assertEqual(again[0][0], 1)                                       # the same open request, not a second
        self.assertIn("already open", again[0][3])
        bad = {
            ("story_range", json.dumps({"from": "25.9", "to": "25.2", "title": "abc"})): "from must come before to",
            ("story_range", json.dumps({"from": "25.15", "to": "25.15", "title": "abc"})): "translated passages",
            ("story_range", json.dumps({"from": "26.1", "to": "26.1", "title": "abc"})): "translated passages",
            ("story_range", json.dumps({"from": "x", "to": "25.2", "title": "abc"})): "passage references",
            ("story_range", json.dumps({"from": "25.1", "to": "25.2", "title": "a"})): "title: 3 to 200",
            ("story_mine", json.dumps({"max": 40})): "max: a whole number from 1 to 12",
            ("picture_passage", json.dumps({"at": "25.3", "title": "abc", "brief": "short"})): "brief",
            ("story_write", json.dumps({"story_id": 34})): "only a proposed episode or a draft",
            ("story_write", json.dumps({"story_id": 37})): "a story of this text",
            ("novel_plan", json.dumps({"story_id": 35})): "from an approved story",
            ("novel_draw", json.dumps({"novel_id": 1, "pages": "1-30"})): "pages: such as",
            ("picture_redraw", json.dumps({"image_id": 99})): "a picture of this text",
            ("story_illustrate", json.dumps({"story_id": 34})): "already has a picture",
        }
        for (kind, params), want in bad.items():
            with self.subTest(kind=kind, params=params):
                self.assertIn(want, str(self.ask(kind, "nil", json.loads(params))))
        self.assertIn("a text of the working corpus", str(self.ask("story_mine", "nope", {"max": 2})))
        self.assertIn("Only an editor", str(self.ask("story_approve", "nil", {"story_id": 35})))
        self.assertIn("not something the desk", str(self.ask("delete_all", "nil", {})))

    def test_estimates(self):
        cases = [("story_mine", {"max": 3}, 0.01), ("picture_passage", {"at": "25.3", "title": "abc",
                  "brief": "Show the river goddess flowing to the sea"}, 0.10),
                 ("novel_draw", {"novel_id": 1, "pages": "1-4"}, 0.40), ("novel_draw", {"novel_id": 1}, 0.80),
                 ("novel_cast", {"novel_id": 1}, 0.40), ("novel_plan", {"story_id": 34, "pages": 10}, 0.02)]
        for kind, params, est in cases:
            with self.subTest(kind=kind, params=params):
                r = self.ask(kind, "nil", params)
                self.assertEqual((r[0][1], float(r[0][2])), ("pending", est))

    def test_editors_ask_within_the_daily_cap_and_the_super_admin_sets_it(self):
        r = self.ask("novel_draw", "nil", {"novel_id": 1}, uid=ADMIN)               # $0.80, approved at once
        self.assertEqual(r[0][1], "approved")
        self.assertEqual(self.ask("story_approve", "nil", {"story_id": 35}, uid=ADMIN)[0][1], "approved")
        self.assertIn("only a draft story", str(self.ask("story_approve", "nil", {"story_id": 34}, uid=ADMIN)))
        self.assertIn("Only the super admin", str(self.call("SELECT public.corner_settings_set('daily_cap_usd', '1.00')",
                                                            uid=ADMIN)))
        self.assertEqual(self.call("SELECT public.corner_settings_set('daily_cap_usd', '1.00')", uid=SUPER), [("1.00",)])
        self.assertIn("0 to 50", str(self.call("SELECT public.corner_settings_set('daily_cap_usd', '99')", uid=SUPER)))
        over = self.ask("novel_draw", "nil", {"novel_id": 1, "pages": "1-4"}, uid=ADMIN)   # 0.80 + 0.40 > 1.00
        self.assertIn("Today's cap for the Corner is $1.00", str(over))
        me = self.call("SELECT daily_cap_usd, committed_today, queued FROM public.corner_me()", uid=ADMIN)
        self.assertEqual([(float(a), float(b), c) for a, b, c in me], [(1.0, 0.8, 2)])
        self.call("SELECT public.corner_settings_set('researchers_need_approval', 'false')", uid=SUPER)
        self.assertEqual(self.ask("story_mine", "nil", {"max": 2})[0][1], "approved")

    def test_deciding_cancelling_and_listing(self):
        a = self.ask("story_mine", "nil", {"max": 2})[0][0]
        b = self.ask("story_mine", "mal", {"max": 2})[0][0]
        c = self.ask("story_mine", "nil", {"max": 3}, uid=RES2)[0][0]
        self.assertIn("Only an editor", str(self.call("SELECT * FROM public.corner_request_decide(%s, true)", (a,))))
        self.assertEqual(self.call("SELECT * FROM public.corner_request_decide(%s, true, 'go')", (a,), uid=ADMIN),
                         [("approved", "Approved; the desk takes it on its next round.")])
        self.assertEqual(self.call("SELECT * FROM public.corner_request_decide(%s, false, 'not now')", (b,), uid=ADMIN)[0][0],
                         "rejected")
        self.assertIn("not waiting", str(self.call("SELECT * FROM public.corner_request_decide(%s, true)", (a,), uid=ADMIN)))
        self.assertIn("no such request of yours", str(self.call("SELECT * FROM public.corner_request_cancel(%s)", (c,))))
        self.assertEqual(self.call("SELECT * FROM public.corner_request_cancel(%s)", (c,), uid=RES2)[0][0], "cancelled")
        mine = self.call("SELECT id, status, mine, requester FROM public.corner_requests('mine')")
        self.assertEqual(mine, [(b, "rejected", True, None), (a, "approved", True, None)])
        self.assertIn("Only an editor", str(self.call("SELECT * FROM public.corner_requests('all')")))
        q = self.call("SELECT id, requester FROM public.corner_requests('all')", uid=ADMIN)
        self.assertEqual(sorted(q), [(a, "kanika@example.org"), (b, "kanika@example.org"), (c, "r2@example.org")])
        self.ask("story_mine", "mal", {"max": 4})
        self.assertEqual([r[0] for r in self.call("SELECT id FROM public.corner_requests('queue')", uid=ADMIN)], [4])

    def test_the_desk_pulls_reports_and_the_asker_sees_the_draft(self):
        a = self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows"})[0][0]
        b = self.ask("picture_passage", "nil", {"at": "25.3", "title": "The river",
                                                "brief": "Show the river goddess flowing to the sea"}, uid=ADMIN)[0][0]
        self.call("SELECT * FROM public.corner_request_decide(%s, true)", (a,), uid=ADMIN)
        got = self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")[0][0]
        self.assertEqual([g["id"] for g in got], [b, a])                       # in the order they were approved
        self.assertEqual(got[1]["params"]["from"], "25.2")
        self.assertEqual(self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")[0][0], [])   # claimed once
        self.assertEqual(self.desk("SELECT public.corner_desk_report(%s, 'running', NULL, 'writing', NULL, NULL)", (a,)),
                         [(True,)])
        self.pg.execute("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, verify, row_hash) "
                        "VALUES ('nil', 40, 'draft', 'Vitasta flows', 'The river ran.', '{\"ok\": true}', 'x')")
        self.assertEqual(self.desk("SELECT public.corner_desk_report(%s, 'done', %s::jsonb, 'story #40 written', 0.0071, "
                                   "'log')", (a, json.dumps({"story_id": 40}))), [(True,)])
        self.assertEqual(self.desk("SELECT public.corner_desk_report(%s, 'done', NULL, NULL, NULL, NULL)", (a,)),
                         [(False,)])                                           # finished requests stay finished
        row = self.call("SELECT status, cost_usd, preview ->> 'story_en', preview ->> 'status' FROM public.corner_requests('mine')")
        self.assertEqual([(s, float(c), e, p) for s, c, e, p in row], [("done", 0.0071, "The river ran.", "draft")])
        # a request the desk took and never finished goes back, three times at most
        self.pg.execute("UPDATE corner.requests SET claimed_at = now() - interval '4 hours' WHERE id = %s", (b,))
        self.assertEqual([g["id"] for g in self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")[0][0]], [b])
        self.pg.execute("UPDATE corner.requests SET claimed_at = now() - interval '4 hours', attempts = 3 WHERE id = %s", (b,))
        self.assertEqual(self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")[0][0], [])
        self.assertEqual(self.status(b), "failed")
        hb = self.desk("SELECT public.corner_desk_heartbeat(%s::jsonb)", (json.dumps({"version": "1.0", "budget_left": 3.2}),))
        self.assertEqual(hb[0][0]["scheme"], "corner.1")
        self.assertEqual(self.call("SELECT worker_info ->> 'version' FROM public.corner_me()", uid=ADMIN), [("1.0",)])
        self.assertEqual(self.call("SELECT worker_info FROM public.corner_me()"), [(None,)])   # editors only

    def test_anthologies(self):
        self.assertIn("is not an approved story", str(self.call(
            "SELECT * FROM public.corner_collection_save(NULL, 'Rivers', NULL, NULL, 'general', %s::jsonb)",
            (json.dumps([{"doc_code": "nil", "story_id": 35}]),))))
        cid = self.call("SELECT * FROM public.corner_collection_save(NULL, 'Rivers', NULL, 'Of rivers.', 'general', %s::jsonb)",
                        (json.dumps([{"doc_code": "nil", "story_id": 34}, {"doc_code": "nil", "story_id": 34}]),))[0][0]
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.collection_items").fetchone()[0], 1)
        self.assertEqual(self.call("SELECT id, status, mine FROM public.corner_collections('mine')"), [(cid, "draft", True)])
        self.assertEqual(self.call("SELECT id FROM public.corner_collections()", uid=READER), [])      # a draft is private
        self.assertEqual(self.call("SELECT id FROM public.corner_collections()", uid=RES2), [])
        self.assertEqual(self.call("SELECT id FROM public.corner_collections()", uid=ADMIN), [(cid,)])
        # an editor may put a draft story in; publishing then waits for its approval
        self.call("SELECT * FROM public.corner_collection_save(%s, 'Rivers', NULL, 'Of rivers.', 'general', %s::jsonb)",
                  (cid, json.dumps([{"doc_code": "nil", "story_id": 34}, {"doc_code": "nil", "story_id": 35}])), uid=ADMIN)
        self.assertIn("Only an editor", str(self.call("SELECT * FROM public.corner_collection_publish(%s, true)", (cid,))))
        self.assertIn("1 of its 2 stories are not approved",
                      str(self.call("SELECT * FROM public.corner_collection_publish(%s, true)", (cid,), uid=ADMIN)))
        self.pg.execute("UPDATE corpus.stories SET status = 'approved' WHERE story_id = 35")
        self.assertEqual(self.call("SELECT * FROM public.corner_collection_publish(%s, true)", (cid,), uid=ADMIN)[0][0],
                         "published")
        self.pg.execute("UPDATE corpus.stories SET status = 'draft' WHERE story_id = 35")   # sent back on the desk
        seen = self.call("SELECT status, can_edit, jsonb_array_length(items), items -> 0 -> 'picture' ->> 'media_key' "
                         "FROM public.corner_collection(%s)", (cid,), uid=READER)
        self.assertEqual(seen, [("published", False, 1, "img:4")])             # readers: approved stories and pictures
        ed = self.call("SELECT jsonb_array_length(items), items -> 1 -> 'picture' ->> 'media_key' "
                       "FROM public.corner_collection(%s)", (cid,), uid=ADMIN)
        self.assertEqual(ed, [(2, "img:3")])                                   # editors: drafts too
        self.assertEqual(self.call("SELECT id, cover_sha FROM public.corner_collections('published')", uid=READER),
                         [(cid, SHA("b"))])
        self.assertIn("changed by an editor", str(self.call(
            "SELECT * FROM public.corner_collection_save(%s, 'Mine now', NULL, NULL, 'general', '[]')", (cid,))))
        self.assertIn("approved stories only", str(self.call(
            "SELECT * FROM public.corner_collection_save(%s, 'Rivers', NULL, NULL, 'general', %s::jsonb)",
            (cid, json.dumps([{"doc_code": "nil", "story_id": 35}])), uid=ADMIN)))
        self.assertIn("retired by an editor", str(self.call("SELECT * FROM public.corner_collection_retire(%s)", (cid,))))
        self.assertEqual(self.call("SELECT * FROM public.corner_collection_retire(%s)", (cid,), uid=ADMIN)[0][0], "retired")
        self.assertEqual(self.call("SELECT id FROM public.corner_collections()", uid=READER), [])


if __name__ == "__main__":
    unittest.main()
