# -*- coding: ascii -*-
"""CORNER_C13_2026_10_10 against a real PostgreSQL: docs/cloud/C13 (the Corner's researchers see the
work in progress; the offering so far). Applies the Supabase stand-ins and every file the live database
has, in its order (C4, C4b, C5, C5b, C6, C7a, C7, C8, C9 twice, C10a, C10b, C11, C12), then C13 twice.
Then reads as the roles do: anon, a signed-in reader who is not invited, a researcher, an admin, the
super admin. Also: C13 refuses a function changed since, changing nothing, and its rollback works.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corner_drafts_pg_2026_10_10
"""
import json, os, re, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C13 = CLOUD / "C13_corner_drafts_offering_2026-10-10.sql"
C13_CHECKS = CLOUD / "C13_checks_2026-10-10.sql"
BEFORE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", REPO / "tests" / "supabase_stubs_rbac_2026_10_08.sql",
          CLOUD / "C4_corpus_mirror_2026-10-08.sql", CLOUD / "C4b_mirror_digests_2026-10-08.sql",
          CLOUD / "C5_corpus_reader_2026-10-08.sql", CLOUD / "C5b_corpus_reader_outline_2026-10-08.sql",
          CLOUD / "C6_corpus_library_2026-10-08.sql", CLOUD / "C7a_rbac_roles_2026-10-08.sql"]
AFTER = [CLOUD / "C7_rbac_researchers_2026-10-08.sql", CLOUD / "C8_corpus_media_2026-10-09.sql",
         CLOUD / "C9_researchers_corner_2026-10-09.sql", CLOUD / "C9_researchers_corner_2026-10-09.sql",
         CLOUD / "C10a_corner_state_2026-10-09.sql", CLOUD / "C10b_corner_kinds_2026-10-09.sql",
         CLOUD / "C11_learn_2026-10-09.sql", CLOUD / "C12_corner_mail_2026-10-09.sql", C13, C13]
SUPER = "11111111-1111-1111-1111-111111111111"
ADMIN = "44444444-4444-4444-4444-444444444444"
RES = "55555555-5555-5555-5555-555555555555"
READER = "33333333-3333-3333-3333-333333333333"
SHA = lambda c: c * 64
FIVE = ["corpus_reader_stories", "corpus_reader_media", "corpus_reader_novels", "corpus_reader_novel",
        "corpus_reader_media_file"]
MARK = "CORNER_C13_2026_10_10"


def rollback_sql() -> str:
    """The rollback written in C13's header, without its comment marks."""
    text = C13.read_text(encoding="utf-8")
    block = text.split("-- Rollback", 1)[1].split("-- ====", 1)[0]
    lines = block.splitlines()[1:]
    return "\n".join(l[5:] if l.startswith("--   ") else "" for l in lines)


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Drafts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        x = cls.pg.execute
        for f in BEFORE:
            x(f.read_text(encoding="utf-8"))
        x("INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'dhruv.rakesh@gmail.com', now()), "
          "(%s, 'admin@example.org', now()), (%s, 'kanika@example.org', now()), "
          "(%s, 'reader@example.org', now()) ON CONFLICT DO NOTHING", (SUPER, ADMIN, RES, READER))
        for f in AFTER:
            x(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        x = self.pg.execute
        x("TRUNCATE corner.requests, corner.collections, corner.collection_items, corner.events RESTART IDENTITY CASCADE")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("DELETE FROM public.user_roles WHERE user_id IN (%s, %s)", (ADMIN, RES))
        x("INSERT INTO public.user_roles (user_id, role) VALUES (%s, 'admin'), (%s, 'researcher')", (ADMIN, RES))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('nil', 'Nilamata', 'x'), ('mal', 'Mallapurana', 'x'), "
          "('old', 'Gone', 'x')")
        x("UPDATE corpus.docs SET retired_at = now() WHERE doc_code = 'old'")
        rows = [("nil", 25, i, "translation %d" % i) for i in range(1, 5)] + [("nil", 26, 1, "")] + \
               [("mal", 1, 1, "t"), ("mal", 1, 2, "  "), ("old", 1, 1, "t")]
        for doc, pg, ix, tr in rows:
            x("INSERT INTO corpus.passages (doc_code, page_no, idx, translation, row_hash) VALUES (%s, %s, %s, %s, 'x')",
              (doc, pg, ix, tr))
        for sid, st in ((34, "approved"), (35, "draft"), (36, "candidate"), (37, "retired"), (38, "rejected")):
            x("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, row_hash) "
              "VALUES ('nil', %s, %s, %s, %s, 'x')", (sid, st, "Story %d" % sid, "Text of %d" % sid))
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, row_hash, retired_at) "
          "VALUES ('nil', 39, 'approved', 'Retired row', 'x', now())")
        with self.pg.transaction():
            x("SET LOCAL ROLE service_role")
            x("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps([
                {"media_key": "img:3", "doc_code": "nil", "kind": "generated", "status": "draft", "story_id": 35,
                 "sha256": SHA("a"), "row_hash": "h3"},
                {"media_key": "img:4", "doc_code": "nil", "kind": "generated", "status": "approved", "story_id": 34,
                 "sha256": SHA("b"), "row_hash": "h4"}]),))
            x("SELECT public.corpus_novels_upsert(%s::jsonb)", (json.dumps([
                {"novel_id": 1, "doc_code": "nil", "story_id": 34, "status": "drawing", "pages": 8, "row_hash": "n1"},
                {"novel_id": 2, "doc_code": "nil", "story_id": 34, "status": "approved", "pages": 8, "row_hash": "n2"}]),))
        for c in "ab":
            x("INSERT INTO corpus.media_files (sha256, rendition, file_id, mime, bytes, file_sha256) "
              "VALUES (%s, 'thumb', %s, 'image/jpeg', 10, %s)", (SHA(c), "drive-file-" + c, SHA(c)))
        x("INSERT INTO corner.collections (title, status, created_by) VALUES ('A', 'published', %s), ('B', 'draft', %s)",
          (RES, RES))
        x("INSERT INTO corner.requests (kind, doc_code, requested_by, status, finished_at) VALUES "
          "('story_mine', 'nil', %s, 'done', now() - interval '1 day'), ('story_mine', 'nil', %s, 'done', now() - interval '9 days'), "
          "('story_mine', 'mal', %s, 'failed', now())", (RES, RES, RES))

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

    def seen(self, uid, role="authenticated"):
        """What each of the five functions shows this person."""
        st = self.call("SELECT story_id, status FROM public.corpus_reader_stories('nil') ORDER BY story_id", uid=uid, role=role)
        md = self.call("SELECT media_key, status FROM public.corpus_reader_media('nil') ORDER BY media_key", uid=uid, role=role)
        nv = self.call("SELECT novel_id, status FROM public.corpus_reader_novels('nil') ORDER BY novel_id", uid=uid, role=role)
        one = self.call("SELECT novel_id FROM public.corpus_reader_novel(1)", uid=uid, role=role)
        fa = self.call("SELECT file_id FROM public.corpus_reader_media_file(%s, 'thumb')", (SHA("a"),), uid=uid, role=role)
        fb = self.call("SELECT file_id FROM public.corpus_reader_media_file(%s, 'thumb')", (SHA("b"),), uid=uid, role=role)
        return st, md, nv, one, fa, fb

    def fn_defs(self):
        return {r[0]: r[1] for r in self.pg.execute(
            "SELECT p.proname, p.prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname = ANY(%s)", (FIVE,)).fetchall()}

    # ---- the rewrite

    def test_the_five_functions_carry_the_helper_and_keep_their_grants(self):
        defs = self.fn_defs()
        self.assertEqual(sorted(defs), sorted(FIVE))
        for name, src in defs.items():
            with self.subTest(fn=name):
                self.assertEqual(src.count(MARK), 1)
                self.assertEqual(src.count("corpus._sees_drafts()"), 1)
                self.assertNotIn("corpus._is_editor()", src)
                self.assertNotIn("'admin'::public.app_role", src)
        rows = self.pg.execute(
            "SELECT p.proname, p.prosecdef, p.proconfig, has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE') FROM pg_proc p JOIN pg_namespace n "
            "ON n.oid = p.pronamespace WHERE n.nspname = 'public' AND p.proname = ANY(%s) ORDER BY 1",
            (FIVE + ["corner_offering"],)).fetchall()
        for name, secdef, config, anon, auth in rows:
            with self.subTest(fn=name):
                self.assertEqual((secdef, config, anon, auth), (True, ['search_path=""'], False, True))
        helper = self.pg.execute(
            "SELECT p.prosecdef, has_function_privilege('authenticated', p.oid, 'EXECUTE'), "
            "has_function_privilege('anon', p.oid, 'EXECUTE') FROM pg_proc p WHERE p.oid = 'corpus._sees_drafts()'::regprocedure"
        ).fetchall()
        self.assertEqual(helper, [(False, False, False)])

    # ---- who sees what

    def test_researchers_and_editors_see_the_work_in_progress_readers_do_not(self):
        work = ([(34, "approved"), (35, "draft"), (36, "candidate")], [("img:3", "draft"), ("img:4", "approved")],
                [(1, "drawing"), (2, "approved")], [(1,)], [("drive-file-a",)], [("drive-file-b",)])
        approved = ([(34, "approved")], [("img:4", "approved")], [(2, "approved")], [], [], [("drive-file-b",)])
        self.assertEqual(self.seen(RES), work)
        self.assertEqual(self.seen(ADMIN), work)
        self.assertEqual(self.seen(SUPER), work)
        self.assertEqual(self.seen(READER), approved)
        for r in self.seen(None, role="anon"):
            self.assertIn("permission denied", r)
        # the reader list: a researcher reads by her role, a listed reader still sees approved work only
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'readers'")
        self.assertEqual(self.seen(RES), work)
        self.assertIn("signed-in readers only", self.seen(READER)[0])
        self.pg.execute("INSERT INTO corpus.readers (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (READER,))
        try:
            self.assertEqual(self.seen(READER), approved)
        finally:
            self.pg.execute("DELETE FROM corpus.readers WHERE user_id = %s", (READER,))
        # a researcher whose role is taken away is a reader again
        self.pg.execute("DELETE FROM public.user_roles WHERE user_id = %s", (RES,))
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        self.assertEqual(self.seen(RES), approved)

    def test_the_corner_lists_a_proposed_episode_to_write_for_a_researcher(self):
        # the request the Corner offers her now is the one the database always accepted from her
        r = self.call("SELECT request_status FROM public.corner_request_create('story_write', 'nil', '{\"story_id\": 36}'::jsonb)")
        self.assertEqual(r, [("pending",)])
        r = self.call("SELECT request_status FROM public.corner_request_create('story_illustrate', 'nil', '{\"story_id\": 35}'::jsonb)")
        self.assertIn("already has a picture", str(r))   # img:3 is the draft's picture, which she now sees too
        # she sees draft 35 now, but an anthology of hers still holds approved stories only (C9), which is why
        # the site's anthology editor offers her approved stories alone
        r = self.call("SELECT * FROM public.corner_collection_save(NULL, 'Mine', NULL, NULL, 'general', "
                      "'[{\"doc_code\": \"nil\", \"story_id\": 35}]'::jsonb)")
        self.assertIn("is not an approved story", str(r))
        r = self.call("SELECT collection_status FROM public.corner_collection_save(NULL, 'Mine', NULL, NULL, 'general', "
                      "'[{\"doc_code\": \"nil\", \"story_id\": 34}]'::jsonb)")
        self.assertEqual(r, [("draft",)])

    # ---- the offering

    def test_the_offering_so_far(self):
        want = [(2, 5, 1, 1, 1, 1, 1, 1, 1, 2, 1)]
        got = self.call("SELECT * FROM public.corner_offering()")
        self.assertEqual(got, want)
        self.assertEqual(self.call("SELECT * FROM public.corner_offering()", uid=SUPER), want)
        self.assertIn("open to invited researchers", str(self.call("SELECT * FROM public.corner_offering()", uid=READER)))
        self.assertIn("permission denied", str(self.call("SELECT * FROM public.corner_offering()", role="anon", uid=None)))
        # D1 of the checks gives the same numbers
        checks = C13_CHECKS.read_text(encoding="utf-8")
        d1 = checks.split("-- D1", 1)[1].split("\n-- D2", 1)[0].split("\n", 1)[1]
        d1 = "\n".join(l for l in d1.splitlines() if not l.startswith("--"))
        self.assertEqual(self.pg.execute(d1).fetchall(), want)

    # ---- the checks' queries run

    def test_the_checks_run(self):
        checks = C13_CHECKS.read_text(encoding="utf-8")
        queries = [q for q in re.split(r"\n(?=-- [PVD]\d )", checks) if re.match(r"-- [PVD]\d ", q)]
        self.assertEqual([q[3:5] for q in queries], ["P1", "V1", "V2", "V3", "D1", "D2"])
        out = {}
        for q in queries:
            body = "\n".join(l for l in q.splitlines() if not l.startswith("--"))
            out[q[3:5]] = self.pg.execute(body).fetchall()
        self.assertEqual([(str(r[0]), r[1], r[2]) for r in out["P1"]], [
            ("corpus_reader_media(text,integer,integer,integer)", 0, True),
            ("corpus_reader_media_file(text,text)", 0, True),
            ("corpus_reader_novel(integer)", 0, True),
            ("corpus_reader_novels(text)", 0, True),
            ("corpus_reader_stories(text,boolean)", 0, True)])
        self.assertTrue(all(r[1] and not r[2] and r[3] and r[5] is False and r[6] is True for r in out["V1"]))
        self.assertEqual(len(out["V1"]), 5)
        self.assertEqual([(str(a), b, d, e, f) for a, b, c, d, e, f in out["V2"]],
                         [("corner_offering()", True, False, False, True), ("corpus._sees_drafts()", False, False, False, False)])
        self.assertEqual([(r[0], r[2], r[3]) for r in out["V3"]], [("kanika@example.org", "signed_in", True)])
        self.assertEqual([r[0] for r in out["D2"]], ["mail_enabled", "mail_from", "mail_reply_to", "site_url"])

    # ---- a changed function, a re-run, the rollback

    def test_rerun_refusal_and_rollback(self):
        before = self.fn_defs()
        self.pg.execute(C13.read_text(encoding="utf-8"))           # a third run changes nothing
        self.assertEqual(self.fn_defs(), before)
        self.pg.execute(rollback_sql())                             # the header's rollback
        back = self.fn_defs()
        for name, src in back.items():
            with self.subTest(fn=name):
                self.assertNotIn(MARK, src)
                self.assertEqual(src.count("corpus._is_editor()") + src.count("'admin'::public.app_role"), 1)
        self.assertIsNone(self.pg.execute("SELECT to_regprocedure('public.corner_offering()')").fetchone()[0])
        self.assertIsNone(self.pg.execute("SELECT to_regprocedure('corpus._sees_drafts()')").fetchone()[0])
        self.assertEqual(self.seen(RES)[0], [(34, "approved")])   # approved only again, as before C13
        # a function changed since: C13 stops and changes nothing at all
        novel = self.pg.execute("SELECT pg_get_functiondef('public.corpus_reader_novel(integer)'::regprocedure)").fetchone()[0]
        self.pg.execute(novel.replace("editor := corpus._is_editor();",
                                      "editor := corpus._is_editor(); editor := corpus._is_editor();"))
        import psycopg
        with self.assertRaises(psycopg.Error) as e:
            self.pg.execute(C13.read_text(encoding="utf-8"))
        self.assertIn("is not the function C6/C8 made", str(e.exception))
        self.pg.execute("ROLLBACK")
        self.assertEqual({k: v for k, v in self.fn_defs().items() if k != "corpus_reader_novel"},
                         {k: v for k, v in back.items() if k != "corpus_reader_novel"})
        self.assertIsNone(self.pg.execute("SELECT to_regprocedure('corpus._sees_drafts()')").fetchone()[0])
        # put it right, and C13 goes in again
        self.pg.execute(novel)
        self.pg.execute(C13.read_text(encoding="utf-8"))
        self.assertEqual(self.fn_defs(), before)
        self.assertEqual(self.seen(RES)[0], [(34, "approved"), (35, "draft"), (36, "candidate")])


if __name__ == "__main__":
    unittest.main()
