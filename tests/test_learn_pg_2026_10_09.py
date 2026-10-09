# -*- coding: ascii -*-
"""LEARN_T1_2026_10_09 against a real PostgreSQL: docs/cloud/C11 (Learn: quests, XP, levels and badges).
Applies the Supabase stand-ins, C4, C4b, C5, C7a, C7, C8, C9 (twice) and C11 (twice), then marks quests,
asks the desk and makes anthologies as the roles do: anon, a signed-in reader, a researcher, an admin and
the super admin. The harness is the one of tests/test_corner_pg_2026_10_09.py.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_learn_pg_2026_10_09
"""
import json, os, unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
BEFORE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", REPO / "tests" / "supabase_stubs_rbac_2026_10_08.sql",
          CLOUD / "C4_corpus_mirror_2026-10-08.sql", CLOUD / "C4b_mirror_digests_2026-10-08.sql",
          CLOUD / "C5_corpus_reader_2026-10-08.sql", CLOUD / "C7a_rbac_roles_2026-10-08.sql"]
AFTER = [CLOUD / "C7_rbac_researchers_2026-10-08.sql", CLOUD / "C8_corpus_media_2026-10-09.sql",
         CLOUD / "C9_researchers_corner_2026-10-09.sql", CLOUD / "C9_researchers_corner_2026-10-09.sql",
         CLOUD / "C11_learn_2026-10-09.sql", CLOUD / "C11_learn_2026-10-09.sql"]
SUPER = "11111111-1111-1111-1111-111111111111"
ADMIN = "44444444-4444-4444-4444-444444444444"
RES = "55555555-5555-5555-5555-555555555555"
RES2 = "66666666-6666-6666-6666-666666666666"
READER = "33333333-3333-3333-3333-333333333333"
UTC = lambda *a: datetime(*a, tzinfo=timezone.utc)
SITE = ["SELECT * FROM public.learn_me()", "SELECT * FROM public.learn_summary()",
        "SELECT public.learn_mark('find_library')", "SELECT * FROM public.learn_team()"]
FIND = ["find_library", "find_passage", "find_views", "find_search", "find_meaning", "find_names"]
READ = ["read_story", "read_picture", "read_novel", "read_texts"]
ASK = ["ask_any", "ask_story", "ask_done", "ask_write", "ask_picture", "ask_novel"]
MAKE = ["make_anthology", "make_three", "make_published", "make_print"]
EDIT = ["edit_decide", "edit_approve", "edit_publish"]
CATALOGUE = (
    [(k, "find", 10, "self", False) for k in FIND] + [(k, "read", 10, "self", False) for k in READ]
    + [(k, "ask", 20, "auto", False) for k in ASK]
    + [("make_anthology", "make", 30, "auto", False), ("make_three", "make", 30, "auto", False),
       ("make_published", "make", 50, "auto", False), ("make_print", "make", 10, "self", False)]
    + [(k, "edit", 20, "auto", True) for k in EDIT])


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Learn(unittest.TestCase):
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
        x("TRUNCATE learn.marks")
        x("TRUNCATE corner.requests, corner.collections, corner.collection_items, corner.events RESTART IDENTITY")
        x("UPDATE corner.settings SET value = CASE key WHEN 'daily_cap_usd' THEN '2.00' "
          "WHEN 'researchers_need_approval' THEN 'true' ELSE '20' END")
        x("UPDATE corner.worker SET last_seen = NULL, info = NULL")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("DELETE FROM public.user_roles WHERE user_id IN (%s, %s, %s, %s)", (ADMIN, RES, RES2, READER))
        x("INSERT INTO public.user_roles (user_id, role) VALUES (%s, 'admin'), (%s, 'researcher'), (%s, 'researcher')",
          (ADMIN, RES, RES2))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('nil', 'Nilamata', 'x'), ('mal', 'Mallapurana', 'x')")
        rows = [("nil", 25, i, "translation %d" % i, "mula") for i in range(1, 15)] + [("mal", 1, 1, "t", "mula")]
        for doc, pg, ix, tr, tt in rows:
            x("INSERT INTO corpus.passages (doc_code, page_no, idx, translation, text_type, row_hash) "
              "VALUES (%s, %s, %s, %s, %s, 'x')", (doc, pg, ix, tr, tt))
        for sid, st in ((34, "approved"), (35, "draft"), (36, "candidate"), (38, "approved"), (39, "approved")):
            x("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, row_hash) "
              "VALUES ('nil', %s, %s, %s, %s, 'x')", (sid, st, "Story %d" % sid, "Text of %d" % sid))

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

    def mark(self, quest, uid=RES):
        return self.call("SELECT public.learn_mark(%s)", (quest,), uid=uid)

    def done(self, uid=RES):
        """{quest: done_at} of the quests done, from learn_me()."""
        rows = self.call("SELECT quest, done, done_at FROM public.learn_me()", uid=uid)
        self.assertIsInstance(rows, list, rows)
        return {q: at for q, d, at in rows if d}

    def summary(self, uid=RES):
        rows = self.call("SELECT * FROM public.learn_summary()", uid=uid)
        self.assertIsInstance(rows, list, rows)
        self.assertEqual(len(rows), 1)
        return rows[0]

    def save(self, title, stories, cid=None, uid=RES):
        items = json.dumps([{"doc_code": "nil", "story_id": s} for s in stories])
        return self.call("SELECT * FROM public.corner_collection_save(%s, %s, NULL, NULL, 'general', %s::jsonb)",
                         (cid, title, items), uid=uid)

    # ---- who may call what

    def test_grants(self):
        for sql in SITE:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
        for sql in ["SELECT * FROM learn.quests", "SELECT * FROM learn.marks",
                    "INSERT INTO learn.marks (user_id, quest) VALUES ('%s', 'find_library')" % RES,
                    "SELECT * FROM learn._progress('%s', true)" % RES, "SELECT learn._auto_done('ask_any', '%s')" % RES]:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql))
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
        closed = self.pg.execute(
            "SELECT c.relname, c.relrowsecurity, has_table_privilege('anon', c.oid, 'SELECT'), "
            "has_table_privilege('authenticated', c.oid, 'SELECT'), has_table_privilege('authenticated', c.oid, 'INSERT') "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'learn' AND c.relkind = 'r' "
            "ORDER BY 1").fetchall()
        self.assertEqual(closed, [("marks", True, False, False, False), ("quests", True, False, False, False)])
        fns = self.pg.execute(
            "SELECT n.nspname || '.' || p.proname, p.prosecdef, has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE') FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'learn' OR (n.nspname = 'public' AND p.proname LIKE 'learn\\_%') ORDER BY 1").fetchall()
        self.assertEqual(fns, [
            ("learn._auto_done", False, False, False), ("learn._gate", False, False, False),
            ("learn._last_activity", False, False, False), ("learn._levels", False, False, False),
            ("learn._progress", False, False, False), ("learn._summary", False, False, False),
            ("public.learn_mark", True, False, True), ("public.learn_me", True, False, True),
            ("public.learn_summary", True, False, True), ("public.learn_team", True, False, True)])
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.learn_me()", uid=None))

    def test_a_plain_reader_is_refused(self):
        for sql in SITE:
            with self.subTest(sql=sql):
                self.assertIn("Learn is open to invited researchers and editors", str(self.call(sql, uid=READER)))
        self.assertEqual(self.pg.execute("SELECT count(*) FROM learn.marks").fetchone()[0], 0)
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")      # not a reader at all
        self.assertIn("signed-in readers only", str(self.call("SELECT * FROM public.learn_me()")))

    # ---- the catalogue

    def test_a_researcher_has_20_quests_and_an_editor_23(self):
        rows = self.call("SELECT quest, track, xp, mode, editors_only, done, done_at FROM public.learn_me()")
        self.assertEqual([r[:5] for r in rows], CATALOGUE[:20])
        self.assertEqual({r[1] for r in rows}, {"find", "read", "ask", "make"})
        self.assertTrue(all(r[5] is False and r[6] is None for r in rows))
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                rows = self.call("SELECT quest, track, xp, mode, editors_only FROM public.learn_me()", uid=uid)
                self.assertEqual(rows, CATALOGUE)
        self.assertEqual(self.pg.execute("SELECT count(*), sum(xp) FROM learn.quests").fetchone(), (23, 400))
        self.assertEqual(self.summary()[6:], (0, 20))
        self.assertEqual(self.summary(ADMIN)[6:], (0, 23))

    def test_rerun_keeps_progress_and_refreshes_the_catalogue(self):
        self.assertEqual(self.mark("find_library"), [(True,)])
        self.pg.execute("UPDATE learn.quests SET xp = 99, sort = 1 WHERE key = 'find_library'")
        self.pg.execute((CLOUD / "C11_learn_2026-10-09.sql").read_text(encoding="utf-8"))
        self.assertEqual(self.pg.execute("SELECT xp, sort FROM learn.quests WHERE key = 'find_library'").fetchone(), (10, 110))
        self.assertIn("find_library", self.done())

    # ---- self quests

    def test_self_marking(self):
        self.assertEqual(self.mark("find_library"), [(True,)])
        first = self.done()["find_library"]
        self.assertIsNotNone(first)
        self.assertEqual(self.mark("find_library"), [(False,)])               # idempotent: the first time is kept
        self.assertEqual(self.mark(" find_library "), [(False,)])
        self.assertEqual(self.done()["find_library"], first)
        self.assertEqual(self.pg.execute("SELECT count(*) FROM learn.marks").fetchone()[0], 1)
        self.assertIn("checked for you from the Researchers' Corner", str(self.mark("ask_any")))
        self.assertIn("checked for you", str(self.mark("make_three")))
        self.assertIn("No such quest: nope.", str(self.mark("nope")))
        self.assertIn("No such quest: (none named).", str(self.mark(None)))
        self.assertIn("No such quest: (none named).", str(self.mark("  ")))
        self.assertIn("No such quest: edit_decide.", str(self.mark("edit_decide")))     # not a researcher's quest
        self.assertIn("checked for you", str(self.mark("edit_decide", uid=ADMIN)))       # an editor's, but auto
        self.assertEqual(self.mark("make_print", uid=ADMIN), [(True,)])
        self.assertEqual(set(self.done()), {"find_library"})                  # each person's own
        self.assertEqual(set(self.done(ADMIN)), {"make_print"})
        self.assertEqual(self.done(RES2), {})
        self.assertEqual(self.pg.execute("SELECT count(*) FROM learn.marks").fetchone()[0], 2)

    # ---- auto quests, checked live from the Corner

    def test_auto_quests_turn_done_from_the_corner(self):
        self.assertEqual(self.done(), {})
        a = self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows"})[0][0]
        got = self.done()
        self.assertEqual(set(got), {"ask_any", "ask_story"})
        at = self.pg.execute("SELECT requested_at FROM corner.requests WHERE id = %s", (a,)).fetchone()[0]
        self.assertEqual(got["ask_any"], at)
        self.ask("story_write", "nil", {"story_id": 36})
        self.ask("picture_passage", "nil", {"at": "25.3", "title": "The river",
                                            "brief": "Show the river goddess flowing to the sea"})
        self.assertEqual(set(self.done()), {"ask_any", "ask_story", "ask_write", "ask_picture"})
        n = self.ask("novel_plan", "nil", {"story_id": 34, "pages": 10})[0][0]
        self.call("SELECT * FROM public.corner_request_cancel(%s)", (n,))          # withdrawn: still asked
        self.assertIn("ask_novel", self.done())
        self.assertEqual(self.done(RES2), {})                                   # someone else's requests
        # an editor approves; the desk takes it and finishes it
        self.assertNotIn("edit_decide", self.done(ADMIN))
        self.call("SELECT * FROM public.corner_request_decide(%s, true)", (a,), uid=ADMIN)
        self.assertIn("edit_decide", self.done(ADMIN))
        self.assertNotIn("ask_done", self.done())
        self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")
        self.desk("SELECT public.corner_desk_report(%s, 'done', '{\"story_id\": 40}'::jsonb, 'written', 0.007, NULL)", (a,))
        got = self.done()
        fin = self.pg.execute("SELECT finished_at FROM corner.requests WHERE id = %s", (a,)).fetchone()[0]
        self.assertEqual(got["ask_done"], fin)
        self.assertEqual(set(got), set(ASK))
        # an editor's own request, approved at once, is not a decision on someone else's
        self.ask("story_mine", "nil", {"max": 2}, uid=SUPER)
        self.assertNotIn("edit_decide", self.done(SUPER))
        self.assertIn("ask_any", self.done(SUPER))
        self.ask("story_approve", "nil", {"story_id": 35}, uid=SUPER)
        self.assertIn("edit_approve", self.done(SUPER))
        self.assertNotIn("edit_approve", self.done(ADMIN))
        # a decision still counts when the researcher withdraws the approved request afterwards
        b = self.ask("story_mine", "mal", {"max": 3})[0][0]
        self.call("SELECT * FROM public.corner_request_decide(%s, false, 'not now')", (b,), uid=SUPER)
        self.assertIn("edit_decide", self.done(SUPER))
        c = self.ask("story_mine", "mal", {"max": 4}, uid=RES2)[0][0]
        self.call("SELECT * FROM public.corner_request_decide(%s, true)", (c,), uid=SUPER)
        self.assertEqual(self.call("SELECT request_status FROM public.corner_request_cancel(%s)", (c,), uid=RES2),
                         [("cancelled",)])
        self.pg.execute("DELETE FROM corner.requests WHERE id = %s", (b,))
        self.assertIn("edit_decide", self.done(SUPER))

    def test_auto_quests_for_anthologies(self):
        cid = self.save("Rivers", [34])[0][0]
        self.assertEqual(set(self.done()), {"make_anthology"})
        self.save("Rivers", [34, 38, 39], cid=cid)
        got = self.done()
        self.assertEqual(set(got), {"make_anthology", "make_three"})
        saved = self.pg.execute("SELECT min(at) FROM corner.events WHERE collection_id = %s AND action = 'collection_saved'",
                                (cid,)).fetchone()[0]
        self.assertEqual(got["make_three"], saved)                             # when it first held three
        self.save("Rivers", [34, 38, 39], cid=cid)
        self.assertEqual(self.done()["make_three"], saved)
        self.save("Rivers", [34], cid=cid)                                     # live: fewer than three now
        self.assertNotIn("make_three", self.done())
        self.save("Rivers", [34, 38, 39], cid=cid)
        self.assertEqual(self.done()["make_three"], saved)
        self.assertEqual(self.done(RES2), {})
        self.assertIn("Only an editor", str(self.call("SELECT * FROM public.corner_collection_publish(%s, true)", (cid,))))
        self.call("SELECT * FROM public.corner_collection_publish(%s, true)", (cid,), uid=ADMIN)
        pub = self.pg.execute("SELECT published_at FROM corner.collections WHERE id = %s", (cid,)).fetchone()[0]
        self.assertEqual(self.done()["make_published"], pub)
        self.assertEqual(self.done(ADMIN)["edit_publish"], pub)
        self.assertNotIn("make_published", self.done(ADMIN))                   # not the editor's own anthology
        self.call("SELECT * FROM public.corner_collection_publish(%s, false)", (cid,), uid=ADMIN)
        self.assertIn("make_published", self.done())                           # it was published once
        # rows put in directly (as the desk's own history would be): a collection of three, made by RES2
        self.pg.execute("INSERT INTO corner.collections (id, title, created_by, created_at, updated_at) "
                        "VALUES (50, 'Direct', %s, '2026-10-01T10:00:00Z', '2026-10-02T10:00:00Z')", (RES2,))
        self.pg.execute("INSERT INTO corner.collection_items (collection_id, pos, doc_code, story_id) "
                        "VALUES (50, 1, 'nil', 34), (50, 2, 'nil', 38), (50, 3, 'nil', 39)")
        got = self.done(RES2)
        self.assertEqual(set(got), {"make_anthology", "make_three"})
        self.assertEqual(got["make_three"], UTC(2026, 10, 2, 10))   # no event: when last saved
        self.assertEqual(got["make_anthology"], UTC(2026, 10, 1, 10))

    # ---- XP, levels and badges

    def test_summary_xp_levels_and_badges(self):
        self.assertEqual(self.summary(), (0, "Reader", 0, "Explorer", 50, [], 0, 20))
        for k in FIND[:5]:
            self.mark(k)
        self.assertEqual(self.summary(), (50, "Explorer", 1, "Storyteller", 120, [], 5, 20))   # exactly 50
        self.mark("find_names")
        self.assertEqual(self.summary(), (60, "Explorer", 1, "Storyteller", 120, ["find"], 6, 20))
        for k in READ:
            self.mark(k)
        self.mark("make_print")
        self.assertEqual(self.summary(), (110, "Explorer", 1, "Storyteller", 120, ["find", "read"], 11, 20))
        self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows"})
        self.assertEqual(self.summary(), (150, "Storyteller", 2, "Curator", 200, ["find", "read"], 13, 20))
        # the rest of the ask and make tracks, as rows put in directly
        x = self.pg.execute
        for kind, st in (("story_write", "pending"), ("picture_passage", "rejected"), ("novel_plan", "done")):
            x("INSERT INTO corner.requests (kind, doc_code, requested_by, status) VALUES (%s, 'nil', %s, %s)", (kind, RES, st))
        self.assertEqual(self.summary(), (230, "Curator", 3, "Keeper", 280, ["find", "read", "ask"], 17, 20))
        x("INSERT INTO corner.collections (id, title, created_by, status, published_by, published_at) "
          "VALUES (60, 'Mine', %s, 'published', %s, now())", (RES, ADMIN))
        self.assertEqual(self.summary(), (310, "Keeper", 4, None, None, ["find", "read", "ask"], 19, 20))
        x("INSERT INTO corner.collection_items (collection_id, pos, doc_code, story_id) "
          "VALUES (60, 1, 'nil', 34), (60, 2, 'nil', 38), (60, 3, 'nil', 39)")
        self.assertEqual(self.summary(), (340, "Keeper", 4, None, None, ["find", "read", "ask", "make"], 20, 20))
        # an editor: the edit track counts, and its badge
        self.assertEqual(self.summary(ADMIN), (20, "Reader", 0, "Explorer", 50, [], 1, 23))   # published 60
        self.assertEqual(set(self.done(ADMIN)), {"edit_publish"})
        x("UPDATE corner.requests SET decided_by = %s, decided_at = now() WHERE status = 'rejected'", (ADMIN,))
        self.ask("story_approve", "nil", {"story_id": 35}, uid=ADMIN)
        s = self.summary(ADMIN)
        self.assertEqual(s, (80, "Explorer", 1, "Storyteller", 120, ["edit"], 4, 23))    # 3 x 20 + ask_any 20

    # ---- the team

    def test_the_team_is_for_editors(self):
        self.assertIn("Only an editor", str(self.call("SELECT * FROM public.learn_team()")))
        self.assertIn("Learn is open to invited researchers", str(self.call("SELECT * FROM public.learn_team()", uid=READER)))
        for k in FIND:
            self.mark(k)
        self.mark("read_story", uid=RES2)
        self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows"})
        self.pg.execute("UPDATE learn.marks SET done_at = '2026-10-01T09:00:00Z' WHERE user_id = %s", (RES2,))
        self.call("SELECT * FROM public.corner_request_decide(1, true)", uid=ADMIN)
        team = self.call("SELECT user_id::text, email, roles, xp, level, quests_done, last_activity FROM public.learn_team()",
                         uid=ADMIN)
        self.assertEqual([t[:6] for t in team], [
            (RES, "kanika@example.org", ["researcher"], 100, "Explorer", 8),
            (ADMIN, "admin@example.org", ["admin"], 20, "Reader", 1),
            (RES2, "r2@example.org", ["researcher"], 10, "Reader", 1),
            (SUPER, "dhruv.rakesh@gmail.com", ["admin", "super_admin"], 0, "Reader", 0)])
        last = {t[0]: t[6] for t in team}
        req = self.pg.execute("SELECT requested_at, decided_at FROM corner.requests WHERE id = 1").fetchone()
        mk = self.pg.execute("SELECT max(done_at) FROM learn.marks WHERE user_id = %s", (RES,)).fetchone()[0]
        self.assertEqual(last[RES], max(req[0], mk))
        self.assertEqual(last[ADMIN], req[1])                                  # its decision
        self.assertEqual(last[RES2], UTC(2026, 10, 1, 9))
        self.assertIsNone(last[SUPER])
        self.assertNotIn(READER, last)                                         # no role: not a member
        self.assertEqual(len(self.call("SELECT * FROM public.learn_team()", uid=SUPER)), 4)
        # the team view agrees with each member's own summary
        for uid in (RES, RES2, ADMIN):
            with self.subTest(uid=uid):
                s = self.summary(uid)
                row = [t for t in team if t[0] == uid][0]
                self.assertEqual((row[3], row[4], row[5]), (s[0], s[1], s[6]))


if __name__ == "__main__":
    unittest.main()
