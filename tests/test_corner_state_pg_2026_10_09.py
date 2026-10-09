# -*- coding: ascii -*-
"""CORNER_STATE_C10A_2026_10_09 against a real PostgreSQL: docs/cloud/C10a (where the desk is with a
request). The harness of tests/test_corner_pg_2026_10_09.py: the Supabase stand-ins, C4, C4b, C5, C7a,
C7, C8, C9 (twice) and C10a (twice); then the desk reports progress as service_role, and the site
tracks requests as anon, a reader, two researchers, an admin and the super admin. The last class runs
every C9 test again with C10a applied on top.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corner_state_pg_2026_10_09
"""
import json, os, sys, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
import test_corner_pg_2026_10_09 as c9  # noqa: E402  (its Corner class runs again below, with C10a)

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C10A = CLOUD / "C10a_corner_state_2026-10-09.sql"
BEFORE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", REPO / "tests" / "supabase_stubs_rbac_2026_10_08.sql",
          CLOUD / "C4_corpus_mirror_2026-10-08.sql", CLOUD / "C4b_mirror_digests_2026-10-08.sql",
          CLOUD / "C5_corpus_reader_2026-10-08.sql", CLOUD / "C7a_rbac_roles_2026-10-08.sql"]
AFTER = [CLOUD / "C7_rbac_researchers_2026-10-08.sql", CLOUD / "C8_corpus_media_2026-10-09.sql",
         CLOUD / "C9_researchers_corner_2026-10-09.sql", CLOUD / "C9_researchers_corner_2026-10-09.sql",
         C10A, C10A]
SUPER = "11111111-1111-1111-1111-111111111111"
ADMIN = "44444444-4444-4444-4444-444444444444"
RES = "55555555-5555-5555-5555-555555555555"
RES2 = "66666666-6666-6666-6666-666666666666"
READER = "33333333-3333-3333-3333-333333333333"
SHA = lambda c: c * 64
REPORT = "SELECT public.corner_desk_report(%s::bigint, %s::text, %s::jsonb, %s::text, %s::numeric, %s::text)"
TRACK = "SELECT * FROM public.corner_request_track(%s::bigint[])"


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class CornerState(unittest.TestCase):
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

    # ---- helpers (those of tests/test_corner_pg_2026_10_09.py, and three for the desk's reports)

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

    def taken(self, n=1):
        """n editor's requests (approved at once), pulled by the desk: their ids."""
        ids = [self.ask("story_mine", "nil", {"max": k}, uid=ADMIN)[0][0] for k in range(1, n + 1)]
        got = self.desk("SELECT public.corner_desk_pull(20, 'desk-pc')")[0][0]
        self.assertEqual(sorted(g["id"] for g in got), sorted(ids))
        return ids

    def report(self, rid, status, result=None, message=None, cost=None, log=None):
        r = self.desk(REPORT, (rid, status, None if result is None else json.dumps(result), message, cost, log))
        self.assertIsInstance(r, list, r)
        return r[0][0]

    def row(self, rid):
        return self.pg.execute("SELECT status, started_at, finished_at, result, progress, message, cost_usd, log_tail "
                               "FROM corner.requests WHERE id = %s", (rid,)).fetchone()

    def events(self, rid):
        return [r[0] for r in self.pg.execute("SELECT action FROM corner.events WHERE request_id = %s AND action LIKE 'desk%%' "
                                              "ORDER BY id", (rid,)).fetchall()]

    # ---- the shape and who may call what

    def test_the_column_and_the_two_functions(self):
        col = self.pg.execute("SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid = "
                              "'corner.requests'::regclass AND attname = 'progress' AND NOT attisdropped").fetchall()
        self.assertEqual(col, [("jsonb",)])
        for bad in ("'[1]'", "'\"x\"'", "jsonb_build_object('note', repeat('n', 1000))"):
            with self.subTest(bad=bad):
                with self.assertRaises(Exception):
                    with self.pg.transaction():
                        self.pg.execute("INSERT INTO corner.requests (kind, doc_code, requested_by, status, progress) "
                                        "VALUES ('story_mine', 'nil', %%s, 'approved', %s)" % bad, (RES,))
        fns = self.pg.execute(
            "SELECT p.proname, pg_get_function_identity_arguments(p.oid), pg_get_function_result(p.oid), p.prosecdef, "
            "p.provolatile, p.proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname IN ('corner_desk_report', 'corner_request_track') ORDER BY 1").fetchall()
        self.assertEqual(fns, [
            ("corner_desk_report", "p_id bigint, p_status text, p_result jsonb, p_message text, p_cost numeric, p_log text",
             "boolean", True, "v", ['search_path=""']),
            ("corner_request_track", "p_ids bigint[]",
             "TABLE(id bigint, status text, decided_at timestamp with time zone, claimed_at timestamp with time zone, "
             "started_at timestamp with time zone, finished_at timestamp with time zone, attempts integer, progress jsonb)",
             True, "s", ['search_path=""'])])

    def test_grants(self):
        priv = self.pg.execute(
            "SELECT p.proname, has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE'), has_function_privilege('service_role', p.oid, 'EXECUTE') "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname IN ('corner_desk_report', 'corner_request_track') ORDER BY 1").fetchall()
        self.assertEqual(priv[0], ("corner_desk_report", False, False, True))
        self.assertEqual(priv[1][:3], ("corner_request_track", False, True))
        rid = self.taken()[0]
        for role, uid in (("anon", None), ("authenticated", RES), ("authenticated", ADMIN)):
            with self.subTest(role=role, uid=uid):
                self.assertIn("permission denied", str(self.call(REPORT, (rid, "running", None, "x", None, None),
                                                                 role=role, uid=uid)))
        self.assertIn("permission denied", str(self.call(TRACK, ([rid],), role="anon", uid=None)))
        self.assertIn("signed-in readers only", str(self.call(TRACK, ([rid],), uid=None)))
        self.assertIn("open to invited researchers", str(self.call(TRACK, ([rid],), uid=READER)))
        self.assertIn("permission denied", str(self.call("SELECT progress FROM corner.requests")))   # still closed
        self.assertEqual(self.report(rid, "running", None, "go"), True)

    def test_needs_c9(self):
        import psycopg
        text = C10A.read_text(encoding="utf-8")
        pre = text[text.index("DO $$\nBEGIN\n  IF to_regclass('corner.requests')"):]
        pre = pre[:pre.index("END $$;") + len("END $$;")]
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("ALTER SCHEMA corner RENAME TO corner_hidden_c10a")
            with self.assertRaises(psycopg.errors.RaiseException) as e:
                with self.pg.transaction():
                    self.pg.execute(pre)
            self.assertIn("C10a: needs C9", str(e.exception))
        self.assertIsNotNone(self.pg.execute("SELECT to_regclass('corner.requests')").fetchone()[0])

    # ---- the desk's reports

    def test_progress_is_stored_made_safe_and_kept(self):
        rid = self.taken()[0]
        self.assertEqual(self.report(rid, "running", None, "The desk is working on it."), True)
        cases = [
            ({"step": 3, "of": 12, "note": "Drawing page 3 of 12"}, (3, 12, "Drawing page 3 of 12")),
            ({"step": 15, "of": 12}, (12, 12, "")),
            ({"step": -2, "of": 0}, (0, 1, "")),
            ({"step": 2.7, "of": 5000, "note": 7}, (2, 1000, "7")),
            ({"step": " 4", "of": "9 "}, (4, 9, "")),
            ({"step": "x", "of": [1]}, (0, 1, "")),
            ({"step": 1e30, "of": 1e30}, (1000, 1000, "")),
            ({"of": 3, "note": "n" * 300}, (0, 3, "n" * 200)),
            ({"step": 1, "of": 2, "note": "a\nb\tc"}, (1, 2, "a b c")),
            ({"step": 1, "of": 2, "note": '"' * 200}, (1, 2, '"' * 200)),
        ]
        for prog, want in cases:
            with self.subTest(prog=prog):
                self.assertEqual(self.report(rid, "running", {"progress": prog}, "tick"), True)
                p = self.row(rid)[4]
                self.assertEqual((p["step"], p["of"], p["note"]), want)
                self.assertEqual(sorted(p), ["at", "note", "of", "step"])
        fresh = self.pg.execute("SELECT abs(extract(epoch FROM now() - (progress ->> 'at')::timestamptz)) < 60 "
                                "FROM corner.requests WHERE id = %s", (rid,)).fetchone()[0]
        self.assertTrue(fresh)                                                  # at: the database's now()
        self.report(rid, "running", {"progress": {"step": 2, "of": 3, "note": "Writing the story"}}, "Writing the story")
        self.assertEqual(self.report(rid, "running", {"progress": 5}, "odd"), True)   # not an object: not stored
        st, _a, _b, result, p, msg = self.row(rid)[:6]
        self.assertEqual((st, result, p["step"], p["note"], msg), ("running", None, 2, "Writing the story", "odd"))
        self.pg.execute(C10A.read_text(encoding="utf-8"))                       # a re-run keeps what is there
        self.assertEqual(self.row(rid)[4]["note"], "Writing the story")
        self.assertEqual(self.report(rid, "done", {"candidates": [41], "count": 1}, "1 episode proposed", 0.01, "log"), True)
        st, _a, fin, result, p, msg, cost, log = self.row(rid)
        self.assertEqual((st, result, p["step"], p["of"], msg, float(cost), log),
                         ("done", {"candidates": [41], "count": 1}, 2, 3, "1 episode proposed", 0.01, "log"))
        self.assertIsNotNone(fin)                                               # done keeps the last progress
        self.assertEqual(self.report(rid, "running", {"progress": {"step": 3, "of": 3}}, "late"), False)   # finished stays finished
        self.assertEqual(self.row(rid)[4]["step"], 2)

    def test_started_at_is_set_once(self):
        a, b = self.taken(2)
        self.report(a, "running", None, "The desk is working on it.")
        t1 = self.row(a)[1]
        self.assertIsNotNone(t1)
        time.sleep(0.05)
        self.report(a, "running", None, "still")
        self.report(a, "running", {"progress": {"step": 1, "of": 2, "note": "Writing"}}, "Writing")
        self.assertEqual(self.row(a)[1], t1)                                    # C9 set it again here
        time.sleep(0.05)
        self.report(a, "done", {"story_id": 40}, "ok", 0.007, None)
        st, started, fin = self.row(a)[:3]
        self.assertEqual((st, started), ("done", t1))
        self.assertGreater(fin, t1)
        self.report(b, "failed", None, "the desk could not do it")             # never reported running
        st, started, fin = self.row(b)[:3]
        self.assertEqual(st, "failed")
        self.assertIsNotNone(started)
        self.assertIsNotNone(fin)

    def test_an_event_per_change_not_per_progress_report(self):
        a, b = self.taken(2)
        self.report(a, "running", None, "The desk is working on it.")
        for i in range(1, 6):
            self.report(a, "running", {"progress": {"step": i, "of": 6, "note": "step %d" % i}}, "step %d" % i)
        self.report(a, "running", None, "still working")                       # no change: no event
        self.assertEqual(self.events(a), ["desk_running"])
        self.report(a, "running", {"progress": {"step": 6, "of": 6, "note": "Sending it to the site"}}, "Sending")
        self.report(a, "done", {"count": 0}, "nothing found", 0, None)
        self.assertEqual(self.events(a), ["desk_running", "desk_done"])
        self.report(b, "running", {"progress": {"step": 1, "of": 2, "note": "first"}}, "first")   # claimed -> running
        self.report(b, "failed", None, "no")
        self.assertEqual(self.events(b), ["desk_running", "desk_failed"])
        detail = self.pg.execute("SELECT detail FROM corner.events WHERE request_id = %s AND action = 'desk_done'",
                                 (a,)).fetchone()[0]
        self.assertEqual(detail, {"cost": 0, "message": "nothing found"})
        self.assertIsNotNone(self.pg.execute("SELECT last_seen FROM corner.worker").fetchone()[0])

    def test_a_running_report_without_progress_is_as_before(self):
        rid = self.taken()[0]
        self.report(rid, "running", None, "The desk is working on it.")
        self.assertEqual(self.row(rid)[3:6], (None, None, "The desk is working on it."))
        self.report(rid, "running", {"partial": 1}, None, 0.5, "half way")     # a result object is kept, as in C9
        st, _a, fin, result, p, msg, cost, log = self.row(rid)
        self.assertEqual((st, fin, result, p, msg, float(cost), log),
                         ("running", None, {"partial": 1}, None, "The desk is working on it.", 0.5, "half way"))
        self.assertIn("running, done or failed", str(self.desk(REPORT, (rid, "cancelled", None, None, None, None))))
        self.assertEqual(self.report(999, "running", None, "x"), False)        # no such request

    def test_the_result_waits_for_done(self):
        rid = self.taken()[0]
        self.report(rid, "running", None, "The desk is working on it.")
        self.report(rid, "running", {"progress": {"step": 1, "of": 3, "note": "Passages chosen"}, "story_id": 99}, "x")
        self.assertIsNone(self.row(rid)[3])                                    # a progress report is not a result
        self.report(rid, "running", {"partial": True}, None)
        self.report(rid, "running", {"progress": {"step": 2, "of": 3, "note": "Writing the story"}}, "Writing the story")
        self.assertEqual(self.row(rid)[3], {"partial": True})
        self.report(rid, "done", {"story_id": 40, "status": "draft"}, "Story #40 written.", 0.007, "story written")
        st, _a, _f, result, p = self.row(rid)[:5]
        self.assertEqual((st, result, p["step"]), ("done", {"story_id": 40, "status": "draft"}, 2))
        self.assertEqual(self.call("SELECT result ->> 'story_id' FROM public.corner_requests('all')", uid=ADMIN),
                         [("40",)])

    # ---- tracking from the site

    def test_track(self):
        a = self.ask("story_mine", "nil", {"max": 1})[0][0]                       # RES, waits for an editor
        b = self.ask("story_mine", "nil", {"max": 2})[0][0]                       # RES
        c = self.ask("story_mine", "nil", {"max": 3}, uid=RES2)[0][0]             # RES2
        d = self.ask("story_mine", "mal", {"max": 4}, uid=ADMIN)[0][0]            # the admin's, approved
        self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")
        self.report(d, "running", None, "The desk is working on it.")
        self.report(d, "running", {"progress": {"step": 1, "of": 2, "note": "Reading 1 translated passages"}}, "x")
        ids = [a, b, c, d, 999]
        self.assertEqual([r[0] for r in self.call(TRACK, (ids,))], [a, b])               # a researcher: their own
        self.assertEqual([r[0] for r in self.call(TRACK, (ids,), uid=RES2)], [c])
        self.assertEqual([r[0] for r in self.call(TRACK, (ids,), uid=ADMIN)], [a, b, c, d])   # an editor: any
        self.assertEqual([r[0] for r in self.call(TRACK, (ids,), uid=SUPER)], [a, b, c, d])
        row = self.call(TRACK, ([d],), uid=ADMIN)[0]
        self.assertEqual((row[0], row[1], row[6], row[7]["step"], row[7]["of"], row[7]["note"]),
                         (d, "running", 1, 1, 2, "Reading 1 translated passages"))
        self.assertTrue(all(v is not None for v in row[2:5]))                   # decided, claimed, started
        self.assertIsNone(row[5])                                               # not finished
        pend = self.call(TRACK, ([a],))[0]
        self.assertEqual((pend[1], pend[2], pend[3], pend[4], pend[6], pend[7]), ("pending", None, None, None, 0, None))
        self.assertEqual(self.call(TRACK, (None,)), [])
        self.assertEqual(self.call(TRACK, ([],)), [])
        self.assertEqual([r[0] for r in self.call(TRACK, (list(range(1, 101)),), uid=ADMIN)], [a, b, c, d])
        self.assertIn("at most 100 requests at a time", str(self.call(TRACK, (list(range(1, 102)),), uid=ADMIN)))
        self.assertIn("open to invited researchers", str(self.call(TRACK, ([a],), uid=READER)))
        self.assertIn("permission denied", str(self.call(TRACK, ([a],), role="anon", uid=None)))


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C9WithC10a(c9.Corner):
    """Every test of tests/test_corner_pg_2026_10_09.py again, with C10a on top of C9."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pg.execute(C10A.read_text(encoding="utf-8"))
        assert cls.pg.execute("SELECT to_regprocedure('public.corner_request_track(bigint[])')").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
