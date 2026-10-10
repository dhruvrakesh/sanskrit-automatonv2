# -*- coding: ascii -*-
"""CORNER_C10B_2026_10_09 against a real PostgreSQL: docs/cloud/C10b (eight new kinds of request, "redo" for
the novels' cast and pages, the ideas for pictures and the retired pictures). The harness of
tests/test_corner_state_pg_2026_10_09.py: the Supabase stand-ins, C4, C4b, C5, C7a, C7, C8, C9 (twice), C10a
(twice) and C10b (twice); then corner._clean is asked about every new kind as a researcher, an admin and the
super admin (as the owner: it is nobody else's), C9's kinds are cleaned by C10b and by C9's own corner._clean
side by side, the new kinds are asked for through corner_request_create, the desk takes them as
service_role, and the two new site functions are called as anon, a reader, researchers and editors. The last
two classes run every C9 test and every C10a test again with C10b applied on top.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corner_kinds_pg_2026_10_09
"""
import json, os, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
import test_corner_pg_2026_10_09 as c9  # noqa: E402  (its Corner class runs again below, with C10b)
import test_corner_state_pg_2026_10_09 as c10a  # noqa: E402  (its CornerState class runs again below)

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C9F = CLOUD / "C9_researchers_corner_2026-10-09.sql"
C10A = CLOUD / "C10a_corner_state_2026-10-09.sql"
C10B = CLOUD / "C10b_corner_kinds_2026-10-09.sql"
BEFORE = list(c10a.BEFORE)
AFTER = list(c10a.AFTER) + [C10B, C10B]
SUPER, ADMIN, RES, RES2, READER = c10a.SUPER, c10a.ADMIN, c10a.RES, c10a.RES2, c10a.READER
SHA = lambda c: c * 64
NEW = ["story_edit", "story_verify", "picture_ideas", "picture_cover", "picture_draw", "picture_edit",
       "picture_restore", "novel_page_edit"]
IDEAS = "SELECT * FROM public.corner_ideas(%s)"
RETIRED = "SELECT * FROM public.corner_retired_pictures(%s)"
BODY = "The river ran down from the lake to the sea. "
HI = "\u0935\u093f\u0924\u0938\u094d\u0924\u093e"          # Devanagari: the river's name


def idea(iid, kind="generated", at="25.3"):
    return {"image_id": iid, "kind": kind, "title": "Idea %d" % iid, "brief": "Brief of idea %d" % iid, "at": at}


def c9_function(name):
    """C9's own text of corner.<name>, from CREATE to its END $$;."""
    text = C9F.read_text(encoding="utf-8")
    start = text.index("CREATE OR REPLACE FUNCTION corner.%s(" % name)
    return text[start:text.index("END $$;", start) + len("END $$;")]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class CornerKinds(unittest.TestCase):
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
          "(%s, 'admin@example.org', now()), (%s, 'kanika@example.org', now()), (%s, 'r2@example.org', now()), "
          "(%s, 'reader@example.org', now()) ON CONFLICT DO NOTHING", (SUPER, ADMIN, RES, RES2, READER))
        for f in AFTER:
            x(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        c9.Corner.setUp(self)        # C9's texts, passages, stories 34-37, pictures img:3 and img:4, novel 1
        x = self.pg.execute
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, story_en, row_hash) VALUES "
          "('nil', 38, 'rejected', 'Story 38', 'Text of 38', 'x'), ('nil', 39, NULL, 'Story 39', 'Text of 39', 'x'), "
          "('mal', 50, 'draft', 'Story 50', 'Text of 50', 'x')")
        self.media("img:5", "nil", retired=120, sha="c", title="Old river", caption="The old river")
        self.media("img:8", "nil", status="approved", retired=60, sha="d", title="Old lake", caption="The old lake")
        self.media("img:6", "mal", retired=30, sha="e")
        self.media("img:7", "mal", sha="f")
        self.media("novel:1:page:1", "nil", retired=10, sha="1", kind="novel_page")
        for sha, rendition in (("c", "display"), ("c", "thumb"), ("d", "thumb")):
            x("INSERT INTO corpus.media_files (sha256, rendition, file_id, mime, bytes, file_sha256) "
              "VALUES (%s, %s, 'drive-file-0123456789', 'image/jpeg', 100, %s)", (SHA(sha), rendition, SHA(sha)))
        for nid, doc, st, pages, retired in ((2, "nil", "approved", 12, False), (3, "nil", "plan", None, False),
                                             (4, "nil", "drawing", 8, True), (5, "mal", "drawing", 8, False),
                                             (6, "nil", "drawing", 20, False)):
            x("INSERT INTO corpus.novels (novel_id, doc_code, story_id, status, pages, row_hash, retired_at) "
              "VALUES (%s, %s, 34, %s, %s, 'x', CASE WHEN %s THEN now() END)", (nid, doc, st, pages, retired))

    # ---- helpers (those of tests/test_corner_pg_2026_10_09.py, and four for C10b)

    call = c9.Corner.call
    ask = c9.Corner.ask
    desk = c9.Corner.desk
    status = c9.Corner.status

    def media(self, key, doc, status="draft", retired=None, sha="c", title=None, caption=None, kind="generated"):
        """A picture in the mirror; retired: so many minutes ago."""
        self.pg.execute(
            "INSERT INTO corpus.media (media_key, doc_code, kind, status, title, caption_en, sha256, row_hash, novel_id, "
            "retired_at) VALUES (%s, %s, %s, %s, %s, %s, %s, 'x', %s, now() - %s::integer * interval '1 minute')",
            (key, doc, kind, status, title, caption, SHA(sha), 1 if key.startswith("novel:") else None, retired))

    def clean(self, kind, params, uid=RES, doc="nil"):
        """corner._clean as its owner, for the asker uid: the cleaned params, or 'ERROR: <message>'."""
        p = params if isinstance(params, str) or params is None else json.dumps(params)
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid or "",))
            try:
                with self.pg.transaction():
                    return self.pg.execute("SELECT corner._clean(%s, %s, %s::jsonb)", (kind, doc, p)).fetchone()[0]
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def estimate(self, kind, params, doc="nil"):
        return float(self.pg.execute("SELECT corner._estimate(%s, %s, %s::jsonb)",
                                     (kind, doc, json.dumps(params))).fetchone()[0])

    def done(self, kind, doc, ideas, status="done", uid=RES, ago=60, result=None):
        """A request the desk has finished (or not), ago minutes ago, with these ideas: its id."""
        res = result if result is not None else {"ideas": ideas, "count": len(ideas)}
        return self.pg.execute(
            "INSERT INTO corner.requests (kind, doc_code, params, requested_by, requested_at, status, est_usd, "
            "decided_by, decided_at, finished_at, result) VALUES (%s, %s, %s::jsonb, %s, "
            "now() - %s::integer * interval '1 minute', %s, 0, %s, now(), now(), %s::jsonb) RETURNING id",
            (kind, doc, json.dumps({"max": 6} if kind == "picture_ideas" else {}), uid, ago, status, uid,
             json.dumps(res))).fetchone()[0]

    def draw_request(self, iid, status, ago, doc="nil"):
        return self.pg.execute(
            "INSERT INTO corner.requests (kind, doc_code, params, requested_by, requested_at, status, est_usd) "
            "VALUES ('picture_draw', %s, %s::jsonb, %s, now() - %s::integer * interval '1 minute', %s, 0.1) RETURNING id",
            (doc, json.dumps({"image_id": iid}), RES, ago, status)).fetchone()[0]

    # ---- the shape, the grants, the guard, the rollback

    def test_the_kinds(self):
        rows = self.pg.execute("SELECT kind, label, cost_bearing, editor_only, est_usd::text, unit, sort, enabled "
                               "FROM corner.kinds WHERE kind = ANY (%s) ORDER BY sort", (NEW,)).fetchall()
        self.assertEqual(rows, [
            ("story_edit", "Edit a story", False, False, "0.0000", "request", 25, True),
            ("story_verify", "Check a story against its citations", False, False, "0.0000", "request", 26, True),
            ("picture_ideas", "Ideas for pictures in a text", True, False, "0.0200", "request", 42, True),
            ("picture_cover", "An idea for a cover", True, False, "0.0100", "request", 44, True),
            ("picture_draw", "Draw an idea", True, False, "0.1000", "request", 46, True),
            ("picture_edit", "Edit a picture's words", False, False, "0.0000", "request", 65, True),
            ("picture_restore", "Restore a retired picture", False, True, "0.0000", "request", 145, True),
            ("novel_page_edit", "Edit a graphic novel's page", False, False, "0.0000", "request", 155, True)])
        n, paid, editors = self.pg.execute("SELECT count(*), count(*) FILTER (WHERE cost_bearing), "
                                           "count(*) FILTER (WHERE editor_only) FROM corner.kinds").fetchone()
        self.assertEqual((n, paid, editors), (24, 12, 8))
        self.assertEqual([r[0] for r in self.call("SELECT kind FROM public.corner_kinds()", uid=READER)][:5],
                         ["story_range", "story_write", "story_edit", "story_verify", "story_mine"])
        self.pg.execute("UPDATE corner.kinds SET est_usd = 0.15, label = 'x', sort = 1, editor_only = true "
                        "WHERE kind = 'picture_draw'")
        try:
            self.pg.execute(C10B.read_text(encoding="utf-8"))                     # a re-run: the estimate is kept
            self.assertEqual(self.pg.execute("SELECT est_usd::text, label, sort, editor_only FROM corner.kinds "
                                             "WHERE kind = 'picture_draw'").fetchone(), ("0.1500", "Draw an idea", 46, False))
        finally:
            self.pg.execute("UPDATE corner.kinds SET est_usd = 0.1 WHERE kind = 'picture_draw'")
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.kinds").fetchone()[0], 24)

    def test_functions_and_grants(self):
        fns = self.pg.execute(
            "SELECT p.proname, pg_get_function_identity_arguments(p.oid), pg_get_function_result(p.oid), p.prosecdef, "
            "p.provolatile, p.proconfig, has_function_privilege('public', p.oid, 'EXECUTE'), "
            "has_function_privilege('anon', p.oid, 'EXECUTE'), has_function_privilege('authenticated', p.oid, 'EXECUTE') "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname IN ('corner_ideas', 'corner_retired_pictures') ORDER BY 1").fetchall()
        self.assertEqual(fns, [
            ("corner_ideas", "p_doc text",
             "TABLE(image_id integer, kind text, title text, brief text, at text, request_id bigint, "
             "asked_at timestamp with time zone, drawn boolean, draw_request_id bigint, draw_status text)",
             True, "s", ['search_path=""'], False, False, True),
            ("corner_retired_pictures", "p_doc text",
             "TABLE(image_id integer, kind text, title text, caption_en text, retired_at timestamp with time zone, "
             "has_file boolean)", True, "s", ['search_path=""'], False, False, True)])
        helpers = self.pg.execute(
            "SELECT p.oid::regprocedure::text, p.prosecdef, p.provolatile, p.proconfig, "
            "has_function_privilege('public', p.oid, 'EXECUTE'), has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE'), has_function_privilege('service_role', p.oid, 'EXECUTE'), "
            "position('CORNER_C10B_2026_10_09' IN p.prosrc) > 0 "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'corner' AND p.proname IN ('_clean', '_estimate') ORDER BY 1").fetchall()
        self.assertEqual(helpers, [
            ("corner._clean(text,text,jsonb)", False, "s", ['search_path=""'], False, False, False, False, True),
            ("corner._estimate(text,text,jsonb)", False, "s", ['search_path=""'], False, False, False, False, True)])
        for sql in ("SELECT corner._clean('picture_cover', 'nil', '{}')",
                    "SELECT corner._estimate('picture_draw', 'nil', '{}')"):
            with self.subTest(sql=sql):
                self.assertIn("permission denied", str(self.call(sql)))
                self.assertIn("permission denied", str(self.call(sql, uid=SUPER)))
        for sql in (IDEAS, RETIRED):
            with self.subTest(sql=sql):
                self.assertIn("permission denied", str(self.call(sql, ("nil",), role="anon", uid=None)))
                self.assertIn("permission denied", str(self.call(sql, ("nil",), role="service_role", uid=None)))
                self.assertIn("signed-in readers only", str(self.call(sql, ("nil",), uid=None)))
                self.assertIn("open to invited researchers", str(self.call(sql, ("nil",), uid=READER)))

    def test_needs_c9(self):
        import psycopg
        text = C10B.read_text(encoding="utf-8")
        pre = text[text.index("DO $$\nBEGIN\n  IF to_regclass('corner.kinds')"):]
        pre = pre[:pre.index("END $$;") + len("END $$;")]
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("ALTER SCHEMA corner RENAME TO corner_hidden_c10b")
            with self.assertRaises(psycopg.errors.RaiseException) as e:
                with self.pg.transaction():
                    self.pg.execute(pre)
            self.assertIn("C10b: needs C9", str(e.exception))
        self.pg.execute(pre)                                                    # with C9 there: nothing to say
        self.assertIsNotNone(self.pg.execute("SELECT to_regclass('corner.kinds')").fetchone()[0])

    def test_the_file(self):
        raw = C10B.read_bytes()
        self.assertTrue(all(b < 128 for b in raw))                               # ASCII only
        text = raw.decode("ascii")
        self.assertIn("CORNER_C10B_2026_10_09", text[:200])
        self.assertNotIn("\r", text)
        body = text[text.index("\nBEGIN;\n"):]
        self.assertEqual(body.count("\nBEGIN;\n"), 1)
        self.assertEqual(body.count("\nCOMMIT;\n"), 1)
        for line in body.splitlines():                                          # no SELECT outside a function
            self.assertFalse(line.startswith("SELECT"), line)

    def test_the_rollback_block(self):
        head = C10B.read_text(encoding="utf-8")
        head = head[:head.index("\nBEGIN;\n")].split("\n")
        i, j = head.index("--   BEGIN;"), head.index("--   NOTIFY pgrst, 'reload schema';")
        lines = []
        for line in head[i + 1:j]:
            self.assertTrue(line == "--" or line.startswith("--   "), line)
            lines.append(line[5:] if line.startswith("--   ") else "")
        self.assertEqual(lines[-1], "COMMIT;")
        sql = "\n".join(lines[:-1])
        c9_clean, c9_est = c9_function("_clean"), c9_function("_estimate")
        self.assertIn(c9_clean, sql)                                            # C9's text, as C9 has it
        self.assertIn(c9_est, sql)
        src = lambda f: self.pg.execute("SELECT prosrc FROM pg_proc WHERE oid = %s::regprocedure", (f,)).fetchone()[0]
        body = lambda t: t[t.index("$$") + 2:t.rindex("$$")]
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("INSERT INTO corner.requests (kind, doc_code, params, requested_by, status) "
                            "VALUES ('story_edit', 'nil', '{}', %s, 'done')", (RES,))
            self.pg.execute(sql)
            self.assertEqual(src("corner._clean(text, text, jsonb)"), body(c9_clean))
            self.assertEqual(src("corner._estimate(text, text, jsonb)"), body(c9_est))
            self.assertEqual(self.pg.execute("SELECT to_regprocedure('public.corner_ideas(text)'), "
                                             "to_regprocedure('public.corner_retired_pictures(text)')").fetchone(),
                             (None, None))
            kinds = [r[0] for r in self.pg.execute("SELECT kind FROM corner.kinds WHERE kind = ANY (%s)", (NEW,))]
            self.assertEqual(kinds, ["story_edit"])                             # a request uses it: it stays
            self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.kinds").fetchone()[0], 17)
            self.assertEqual(self.clean("novel_cast", {"novel_id": 1}), {"novel_id": 1})   # C9's again
            self.assertIn("unknown kind", self.clean("story_edit", {"story_id": 35, "title": "abc"}))
            self.assertEqual(self.pg.execute("SELECT has_function_privilege('authenticated', "
                                             "'corner._clean(text, text, jsonb)', 'EXECUTE')").fetchone()[0], False)
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.kinds").fetchone()[0], 24)   # all back
        self.assertEqual(self.clean("novel_cast", {"novel_id": 1}), {"novel_id": 1, "redo": False})

    # ---- C9's kinds: cleaned and priced exactly as C9 did (but for "redo")

    def test_c9_kinds_are_cleaned_as_c9_did(self):
        import psycopg
        cases = [
            ("story_range", {"from": "25.2", "to": " 25.9", "title": "Vitasta flows", "why": "x"}),
            ("story_range", {"from": "25.2", "to": "25.9", "title": " Vitasta ", "why": ""}),
            ("story_range", {"from": "25.9", "to": "25.2", "title": "abc"}),
            ("story_range", {"from": "25.15", "to": "25.15", "title": "abc"}),
            ("story_range", {"from": "26.1", "to": "26.1", "title": "abc"}),
            ("story_range", {"from": "x", "to": "25.2", "title": "abc"}),
            ("story_range", {"from": "25.1", "to": "25.2", "title": "a"}),
            ("story_range", {"from": "25.1", "to": "25.2", "title": "abc", "why": "w" * 1001}),
            ("story_mine", {"max": 3}), ("story_mine", {"max": "12"}), ("story_mine", {"max": 40}),
            ("story_mine", {}), ("story_mine", {"max": 2.5}),
            ("picture_passage", {"at": "25.3", "title": "The river", "brief": "Show the river goddess flowing",
                                 "caption_en": " c "}),
            ("picture_passage", {"at": "25.3", "title": "abc", "brief": "short"}),
            ("picture_passage", {"at": "26.1", "title": "abc", "brief": "b" * 30}),
            ("story_write", {"story_id": 36}), ("story_write", {"story_id": 35}), ("story_write", {"story_id": 34}),
            ("story_write", {"story_id": 37}), ("story_write", {"story_id": 38}), ("story_write", {"story_id": 39}),
            ("story_write", {"story_id": "x"}), ("story_write", {"story_id": 50}),
            ("story_illustrate", {"story_id": 34}), ("story_illustrate", {"story_id": 36}),
            ("novel_plan", {"story_id": 34, "pages": 10, "audience": "young"}), ("novel_plan", {"story_id": 34}),
            ("novel_plan", {"story_id": 35}), ("novel_plan", {"story_id": 34, "audience": "old"}),
            ("novel_plan", {"story_id": 34, "pages": 20}),
            ("story_approve", {"story_id": 35, "force": True}), ("story_approve", {"story_id": 35}),
            ("story_approve", {"story_id": 34}), ("story_retire", {"story_id": 34}), ("story_retire", {"story_id": 39}),
            ("picture_redraw", {"image_id": 3}), ("picture_redraw", {"image_id": 99}), ("picture_redraw", {"image_id": 5}),
            ("picture_approve", {"image_id": 3}), ("picture_approve", {"image_id": 4}),
            ("picture_retire", {"image_id": 4}), ("picture_retire", {"image_id": 7}),
            ("novel_cast", {"novel_id": 1}), ("novel_cast", {"novel_id": 99}), ("novel_cast", {"novel_id": 4}),
            ("novel_cast", {"novel_id": 5}), ("novel_draw", {"novel_id": 1}), ("novel_draw", {"novel_id": 6}),
            ("novel_draw", {"novel_id": 1, "pages": "1-3"}), ("novel_draw", {"novel_id": 1, "pages": "1,3,5-7"}),
            ("novel_draw", {"novel_id": 1, "pages": "1-30"}), ("novel_draw", {"novel_id": 1, "pages": ""}),
            ("novel_draw", {"novel_id": 1, "pages": "3-1"}),
            ("novel_page_approve", {"novel_id": 1, "page": 3}), ("novel_page_approve", {"novel_id": 1, "page": 17}),
            ("novel_approve", {"novel_id": 2, "force": "1"}), ("novel_approve", {"novel_id": 1}),
            ("novel_retire", {"novel_id": 1}), ("novel_retire", {"novel_id": 5}),
            ("delete_all", {}), ("story_mine", "[1]"), ("story_mine", "null"), ("story_mine", None),
        ]
        cases = [(k, p, "nil") for k, p in cases] + [("story_mine", {"max": 2}, "nope"), ("story_mine", {"max": 2}, None),
                                                    ("story_write", {"story_id": 50}, "mal"), ("novel_cast", {"novel_id": 5}, "mal")]
        cases += [(k, {}, "nil") for k in NEW]
        q = "SELECT %s(%%s, %%s, %%s::jsonb)"
        with self.pg.transaction(force_rollback=True):
            self.pg.execute(c9_function("_clean").replace("corner._clean(p_kind", "corner._clean_c9(p_kind", 1))
            self.pg.execute(c9_function("_estimate").replace("corner._estimate(p_kind", "corner._estimate_c9(p_kind", 1))
            seen = {"ok": 0, "err": 0}
            for uid in (RES, ADMIN):
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
                for kind, params, doc in cases:
                    p = params if isinstance(params, str) or params is None else json.dumps(params)
                    got = []
                    for fn in ("corner._clean_c9", "corner._clean"):
                        try:
                            with self.pg.transaction():
                                got.append(self.pg.execute(q % fn, (kind, doc, p)).fetchone()[0])
                        except psycopg.Error as e:
                            got.append(("ERROR", e.sqlstate, str(e).splitlines()[0]))
                    old, new = got
                    with self.subTest(uid=uid, kind=kind, params=params, doc=doc):
                        if kind in NEW:
                            self.assertEqual(old, ("ERROR", "22023", "unknown kind"))
                            continue
                        if isinstance(old, dict) and kind in ("novel_cast", "novel_draw"):
                            old = dict(old, redo=False)
                        self.assertEqual(new, old)
                        seen["ok" if isinstance(old, dict) else "err"] += 1
                        if isinstance(old, dict):
                            e9, e10 = [self.pg.execute(q % fn, (kind, doc, json.dumps(v))).fetchone()[0]
                                       for fn, v in (("corner._estimate_c9", got[0]), ("corner._estimate", new))]
                            self.assertEqual(e10, e9)
            self.assertGreater(seen["ok"], 40)
            self.assertGreater(seen["err"], 50)

    # ---- the new kinds, one by one

    def test_story_edit(self):
        self.assertEqual(self.clean("story_edit", {"story_id": 35, "title": "  The Vitasta flows  ", "status": "approved"}),
                         {"story_id": 35, "fields": {"title": "The Vitasta flows"}, "editor": False})
        self.assertEqual(self.clean("story_edit", {"story_id": 35, "story_en": " " + BODY, "story_hi": "  ", "title_hi": None}),
                         {"story_id": 35, "fields": {"story_en": BODY.strip(), "story_hi": None}, "editor": False})
        self.assertEqual(self.clean("story_edit", {"story_id": 39, "title": "abc", "title_hi": HI, "story_en": BODY,
                                                   "story_hi": HI * 5}),
                         {"story_id": 39, "fields": {"title": "abc", "title_hi": HI, "story_en": BODY.strip(),
                                                     "story_hi": HI * 5}, "editor": False})
        # a proposed episode: its title only, whoever asks
        self.assertEqual(self.clean("story_edit", {"story_id": 36, "title": "abc", "title_hi": HI, "story_en": None}),
                         {"story_id": 36, "fields": {"title": "abc", "title_hi": HI}, "editor": False})
        for uid in (RES, ADMIN, SUPER):
            for extra in ({"story_en": BODY}, {"story_hi": ""}):
                with self.subTest(uid=uid, extra=extra):
                    self.assertIn("a proposed episode: only its title; ask for it to be written first",
                                  self.clean("story_edit", dict({"story_id": 36, "title": "abc"}, **extra), uid=uid))
        # an approved story: an editor's
        self.assertIn("only an editor changes an approved story", self.clean("story_edit", {"story_id": 34, "title": "abc"}))
        self.assertIn("only an editor changes an approved story",
                      self.clean("story_edit", {"story_id": 34, "title": "abc"}, uid=RES2))
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                self.assertEqual(self.clean("story_edit", {"story_id": 34, "title": "abc", "story_en": BODY}, uid=uid),
                                 {"story_id": 34, "fields": {"title": "abc", "story_en": BODY.strip()}, "editor": True})
        self.assertEqual(self.clean("story_edit", {"story_id": 35, "title": "abc"}, uid=ADMIN)["editor"], True)
        # not a story of this text
        for sid in (37, 38, 50, 99):
            with self.subTest(sid=sid):
                self.assertIn("story_id: a story of this text", self.clean("story_edit", {"story_id": sid, "title": "abc"},
                                                                           uid=ADMIN))
        self.assertEqual(self.clean("story_edit", {"story_id": 50, "title": "abc"}, doc="mal")["story_id"], 50)
        self.assertIn("story_id: a whole number from 1 to 2000000000", self.clean("story_edit", {"story_id": "x", "title": "abc"}))
        self.assertIn("doc: a text of the working corpus", self.clean("story_edit", {"story_id": 35, "title": "abc"}, doc="nope"))
        # nothing to change
        for p in ({"story_id": 35}, {"story_id": 35, "title": None}, {"story_id": 35, "why": "x", "fields": {"title": "abc"}}):
            with self.subTest(p=p):
                self.assertIn("nothing to change", self.clean("story_edit", p))
        # the bounds of every field
        for key, value, ok in (("title", "ab", False), ("title", "t" * 3, True), ("title", "t" * 300, True),
                               ("title", "t" * 301, False), ("title_hi", "", True), ("title_hi", "t" * 300, True),
                               ("title_hi", "t" * 301, False), ("story_en", "s" * 19, False), ("story_en", "s" * 20, True),
                               ("story_en", "s" * 6000, True), ("story_en", "s" * 6001, False), ("story_en", "", False),
                               ("story_hi", "s" * 8000, True), ("story_hi", "s" * 8001, False)):
            with self.subTest(key=key, n=len(value)):
                got = self.clean("story_edit", {"story_id": 35, key: value})
                if ok:
                    self.assertEqual(got["fields"], {key: value or None})
                else:
                    lo, hi = {"title": (3, 300), "title_hi": (0, 300), "story_en": (20, 6000), "story_hi": (0, 8000)}[key]
                    self.assertIn("%s: %d to %d characters" % (key, lo, hi), got)

    def test_story_verify(self):
        for sid, uid in ((35, RES), (34, RES), (34, ADMIN), (35, SUPER)):
            with self.subTest(sid=sid, uid=uid):
                self.assertEqual(self.clean("story_verify", {"story_id": sid, "title": "ignored"}, uid=uid), {"story_id": sid})
        for sid in (36, 39):
            with self.subTest(sid=sid):
                self.assertIn("only a written story is checked", self.clean("story_verify", {"story_id": sid}, uid=ADMIN))
        for sid in (37, 38, 50, 99):
            with self.subTest(sid=sid):
                self.assertIn("story_id: a story of this text", self.clean("story_verify", {"story_id": sid}))
        self.assertEqual(self.estimate("story_verify", {"story_id": 35}), 0.0)

    def test_picture_ideas_and_cover(self):
        for p, want in (({}, 6), ({"max": None}, 6), ({"max": 1}, 1), ({"max": "12"}, 12), ({"max": 12}, 12),
                        ({"max": " 3 "}, 3)):
            with self.subTest(p=p):
                self.assertEqual(self.clean("picture_ideas", p), {"max": want})
        for bad in (0, 13, "x", "", -1, 2.5, [3]):
            with self.subTest(bad=bad):
                self.assertIn("max: a whole number from 1 to 12", self.clean("picture_ideas", {"max": bad}))
        self.assertEqual(self.clean("picture_cover", {}), {})
        self.assertEqual(self.clean("picture_cover", {"max": 3, "brief": "anything"}, uid=ADMIN), {})
        self.assertIn("doc: a text of the working corpus", self.clean("picture_cover", {}, doc="nope"))
        self.assertIn("params: a JSON object", self.clean("picture_cover", "[]"))
        self.assertEqual(self.estimate("picture_ideas", {"max": 6}), 0.02)
        self.assertEqual(self.estimate("picture_cover", {}), 0.01)

    def test_picture_draw(self):
        self.done("picture_ideas", "nil", [idea(21), idea(22), idea(26)])
        self.done("picture_cover", "nil", [idea(23, kind="cover", at=None)], uid=ADMIN)
        self.done("picture_ideas", "nil", [idea(24)], status="failed")
        self.done("picture_ideas", "nil", [idea(28)], status="running")
        self.done("picture_ideas", "mal", [idea(25)])
        self.done("picture_passage", "nil", None, result={"ideas": [idea(29)]})   # not an ideas request
        self.done("picture_ideas", "nil", None, result={"ideas": [{"image_id": "30"}]})   # a string is not the number
        self.media("img:22", "mal", sha="9")                                    # drawn (the key is the desk's own)
        self.media("img:26", "nil", sha="8", retired=5)                         # drawn and retired since
        for iid, uid in ((21, RES), (21, ADMIN), (23, RES2), (26, RES), ("21", RES), (" 23 ", SUPER)):
            with self.subTest(iid=iid, uid=uid):
                self.assertEqual(self.clean("picture_draw", {"image_id": iid}, uid=uid), {"image_id": int(iid)})
        for iid in (24, 28, 25, 29, 30, 99):
            with self.subTest(iid=iid):
                self.assertIn("image_id: an idea the desk proposed for this text",
                              self.clean("picture_draw", {"image_id": iid}, uid=ADMIN))
        self.assertEqual(self.clean("picture_draw", {"image_id": 25}, doc="mal"), {"image_id": 25})
        self.assertIn("this idea is drawn already", self.clean("picture_draw", {"image_id": 22}, uid=SUPER))
        for bad in ("x", 0, None):
            with self.subTest(bad=bad):
                self.assertIn("image_id: a whole number from 1 to 2000000000", self.clean("picture_draw", {"image_id": bad}))
        self.assertEqual(self.estimate("picture_draw", {"image_id": 21}), 0.10)

    def test_picture_edit(self):
        self.assertEqual(self.clean("picture_edit", {"image_id": 3, "caption_en": "  A river  ", "caption_hi": "",
                                                     "title": None, "status": "approved"}),
                         {"image_id": 3, "fields": {"caption_en": "A river", "caption_hi": None}, "editor": False})
        every = {"title": "The river", "caption_en": "c" * 500, "caption_hi": HI, "context_note": "n" * 1000}
        self.assertEqual(self.clean("picture_edit", dict(every, image_id=3)),
                         {"image_id": 3, "fields": every, "editor": False})
        # the licence: an editor's
        self.assertIn("only an editor changes a picture's licence",
                      self.clean("picture_edit", {"image_id": 3, "caption_en": "c", "license": "CC BY-SA 4.0"}))
        self.assertIn("only an editor changes a picture's licence", self.clean("picture_edit", {"image_id": 3, "license": ""}))
        self.assertEqual(self.clean("picture_edit", {"image_id": 3, "caption_en": "c", "license": None})["fields"],
                         {"caption_en": "c"})
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                self.assertEqual(self.clean("picture_edit", {"image_id": 3, "license": " CC BY-SA 4.0 "}, uid=uid),
                                 {"image_id": 3, "fields": {"license": "CC BY-SA 4.0"}, "editor": True})
        # an approved picture: an editor's
        for uid in (RES, RES2):
            with self.subTest(uid=uid):
                self.assertIn("only an editor changes an approved picture",
                              self.clean("picture_edit", {"image_id": 4, "caption_en": "c"}, uid=uid))
        self.assertEqual(self.clean("picture_edit", {"image_id": 4, "caption_en": "c", "license": "PD"}, uid=ADMIN),
                         {"image_id": 4, "fields": {"caption_en": "c", "license": "PD"}, "editor": True})
        self.assertEqual(self.clean("picture_edit", {"image_id": 4, "title": "abc"}, uid=SUPER)["editor"], True)
        # not a picture of this text (retired, another text's, none)
        for iid in (5, 7, 99):
            with self.subTest(iid=iid):
                self.assertIn("image_id: a picture of this text", self.clean("picture_edit", {"image_id": iid, "title": "abc"},
                                                                             uid=ADMIN))
        self.assertEqual(self.clean("picture_edit", {"image_id": 7, "title": "abc"}, doc="mal")["image_id"], 7)
        for p in ({"image_id": 3}, {"image_id": 3, "caption_en": None, "status": "approved"}):
            with self.subTest(p=p):
                self.assertIn("nothing to change", self.clean("picture_edit", p))
        for key, value in (("title", "ab"), ("title", "t" * 201), ("caption_en", "c" * 501), ("caption_hi", "c" * 501),
                           ("context_note", "n" * 1001), ("license", "l" * 201)):
            with self.subTest(key=key, n=len(value)):
                lo, hi = {"title": (3, 200), "caption_en": (0, 500), "caption_hi": (0, 500), "context_note": (0, 1000),
                          "license": (0, 200)}[key]
                self.assertIn("%s: %d to %d characters" % (key, lo, hi),
                              self.clean("picture_edit", {"image_id": 3, key: value}, uid=ADMIN))
        self.assertEqual(self.estimate("picture_edit", {"image_id": 3}), 0.0)

    def test_picture_restore(self):
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                self.assertEqual(self.clean("picture_restore", {"image_id": 5, "title": "x"}, uid=uid), {"image_id": 5})
                self.assertEqual(self.clean("picture_restore", {"image_id": 8}, uid=uid), {"image_id": 8})
        for iid in (3, 4, 6, 99):                                               # not retired, or another text's
            with self.subTest(iid=iid):
                self.assertIn("image_id: a retired picture of this text",
                              self.clean("picture_restore", {"image_id": iid}, uid=ADMIN))
        self.assertEqual(self.clean("picture_restore", {"image_id": 6}, uid=ADMIN, doc="mal"), {"image_id": 6})
        self.assertIn("image_id: a whole number", self.clean("picture_restore", {"image_id": "img:5"}, uid=ADMIN))
        self.assertIn("Only an editor (an admin or the super admin) may ask for this.",
                      str(self.ask("picture_restore", "nil", {"image_id": 5})))
        r = self.ask("picture_restore", "nil", {"image_id": 5}, uid=ADMIN)
        self.assertEqual([(b, float(c)) for _a, b, c, _d in r], [("approved", 0.0)])

    def test_novel_page_edit(self):
        self.assertEqual(self.clean("novel_page_edit", {"novel_id": 1, "page": 3, "scene": "  Nila rises from the lake  "}),
                         {"novel_id": 1, "page": 3, "fields": {"scene": "Nila rises from the lake"}, "editor": False})
        self.assertEqual(self.clean("novel_page_edit", {"novel_id": 1, "page": "8", "caption": "", "caption_hi": HI,
                                                        "scene": None}),
                         {"novel_id": 1, "page": 8, "fields": {"caption": None, "caption_hi": HI}, "editor": False})
        for page in (0, 9, -1, "x", None, 2.5):
            with self.subTest(page=page):
                self.assertIn("page: a whole number from 1 to 8",
                              self.clean("novel_page_edit", {"novel_id": 1, "page": page, "caption": "c"}))
        self.assertIn("page: a whole number from 1 to 8", self.clean("novel_page_edit", {"novel_id": 1, "caption": "c"}))
        self.assertEqual(self.clean("novel_page_edit", {"novel_id": 6, "page": 16, "caption": "c"})["page"], 16)
        self.assertIn("page: a whole number from 1 to 16", self.clean("novel_page_edit", {"novel_id": 6, "page": 17, "caption": "c"}))
        self.assertEqual(self.clean("novel_page_edit", {"novel_id": 2, "page": 12, "caption": "c"}, uid=ADMIN)["page"], 12)
        # an approved novel: an editor's
        self.assertIn("only an editor changes an approved graphic novel",
                      self.clean("novel_page_edit", {"novel_id": 2, "page": 1, "caption": "c"}))
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                self.assertEqual(self.clean("novel_page_edit", {"novel_id": 2, "page": 1, "scene": "s" * 2000}, uid=uid),
                                 {"novel_id": 2, "page": 1, "fields": {"scene": "s" * 2000}, "editor": True})
        self.assertIn("this graphic novel has no pages yet", self.clean("novel_page_edit", {"novel_id": 3, "page": 1, "caption": "c"}))
        for nid in (4, 5, 99):                                                  # retired, another text's, none
            with self.subTest(nid=nid):
                self.assertIn("novel_id: a graphic novel of this text",
                              self.clean("novel_page_edit", {"novel_id": nid, "page": 1, "caption": "c"}, uid=ADMIN))
        self.assertEqual(self.clean("novel_page_edit", {"novel_id": 5, "page": 1, "caption": "c"}, doc="mal")["novel_id"], 5)
        self.assertIn("nothing to change", self.clean("novel_page_edit", {"novel_id": 1, "page": 1, "plan": {}}))
        for key, value in (("scene", "s" * 9), ("scene", "s" * 2001), ("scene", ""), ("caption", "c" * 2001),
                           ("caption_hi", "c" * 2001)):
            with self.subTest(key=key, n=len(value)):
                lo = 10 if key == "scene" else 0
                self.assertIn("%s: %d to 2000 characters" % (key, lo),
                              self.clean("novel_page_edit", {"novel_id": 1, "page": 1, key: value}))
        self.assertEqual(self.estimate("novel_page_edit", {"novel_id": 1}), 0.0)

    def test_redo_for_the_novels(self):
        for value, want in ((True, True), ("true", True), ("1", True), (1, True), (False, False), ("false", False),
                            ("yes", False), ("TRUE", False), (None, False), (0, False)):
            with self.subTest(redo=value):
                self.assertEqual(self.clean("novel_cast", {"novel_id": 1, "redo": value}), {"novel_id": 1, "redo": want})
                self.assertEqual(self.clean("novel_draw", {"novel_id": 1, "redo": value}),
                                 {"novel_id": 1, "pages": "", "redo": want})
        self.assertEqual(self.clean("novel_cast", {"novel_id": 1}), {"novel_id": 1, "redo": False})
        self.assertEqual(self.clean("novel_draw", {"novel_id": 1, "pages": "1-3", "redo": True}),
                         {"novel_id": 1, "pages": "1-3", "redo": True})
        self.assertIn("pages: such as", self.clean("novel_draw", {"novel_id": 1, "pages": "1-30", "redo": True}))
        self.assertIn("novel_id: a graphic novel of this text", self.clean("novel_cast", {"novel_id": 4, "redo": True}))
        for kind, extra in (("novel_page_approve", {"page": 2}), ("novel_approve", {}), ("novel_retire", {})):
            with self.subTest(kind=kind):
                self.assertNotIn("redo", self.clean(kind, dict({"novel_id": 1, "redo": True}, **extra), uid=ADMIN))
        # the estimates: every page of the novel when no pages are given, with redo or without
        for params, est in (({"novel_id": 1, "pages": "", "redo": True}, 0.80), ({"novel_id": 1, "pages": "", "redo": False}, 0.80),
                            ({"novel_id": 6, "pages": "", "redo": True}, 2.00), ({"novel_id": 1, "pages": "1-3", "redo": True}, 0.30),
                            ({"novel_id": 1, "pages": "1,3,5-7", "redo": False}, 0.50)):
            with self.subTest(params=params):
                self.assertEqual(self.estimate("novel_draw", params), est)
        self.assertEqual(self.estimate("novel_cast", {"novel_id": 1, "redo": True}), 0.40)
        # asked for: a redo is a request of its own; the desk is told
        a = self.ask("novel_draw", "nil", {"novel_id": 1}, uid=ADMIN)[0]
        b = self.ask("novel_draw", "nil", {"novel_id": 1, "redo": True}, uid=ADMIN)[0]
        c = self.ask("novel_draw", "nil", {"novel_id": 1, "redo": "1", "pages": None}, uid=ADMIN)[0]
        self.assertEqual([(r[0], r[1], float(r[2])) for r in (a, b)], [(1, "approved", 0.8), (2, "approved", 0.8)])
        self.assertEqual(c[0], 2)
        self.assertIn("already open", c[3])
        r = self.ask("novel_cast", "nil", {"novel_id": 1, "redo": True})[0]
        self.assertEqual((r[1], float(r[2])), ("pending", 0.4))
        got = self.desk("SELECT public.corner_desk_pull(5, 'desk-pc')")[0][0]
        self.assertEqual([g["params"] for g in got], [{"novel_id": 1, "pages": "", "redo": False},
                                                      {"novel_id": 1, "pages": "", "redo": True}])

    # ---- asking for them

    def test_asking_for_the_new_kinds(self):
        # free kinds: approved at once, a researcher's too, at no cost
        r = self.ask("story_edit", "nil", {"story_id": 35, "title": "  The Vitasta flows  "}, note="a better title")
        self.assertEqual([(a, b, float(c), d) for a, b, c, d in r],
                         [(1, "approved", 0.0, "Approved; the desk takes it on its next round.")])
        row = self.pg.execute("SELECT params, decided_by::text, note FROM corner.requests WHERE id = 1").fetchone()
        self.assertEqual(row, ({"story_id": 35, "fields": {"title": "The Vitasta flows"}, "editor": False}, RES,
                               "a better title"))
        again = self.ask("story_edit", "nil", {"story_id": 35, "title": "The Vitasta flows"})[0]
        self.assertEqual(again[0], 1)
        self.assertIn("already open", again[3])
        for kind, params in (("story_verify", {"story_id": 34}), ("picture_edit", {"image_id": 3, "caption_en": "c"}),
                             ("novel_page_edit", {"novel_id": 1, "page": 2, "caption": "c"})):
            with self.subTest(kind=kind):
                self.assertEqual([(b, float(c)) for _a, b, c, _d in self.ask(kind, "nil", params)], [("approved", 0.0)])
        self.assertIn("only an editor changes an approved story", str(self.ask("story_edit", "nil", {"story_id": 34, "title": "abc"})))
        self.assertIn("open to invited researchers", str(self.ask("story_edit", "nil", {"story_id": 35, "title": "abc"}, uid=READER)))
        # paid kinds: a researcher's wait for an editor
        r = self.ask("picture_ideas", "nil", {"max": 4})[0]
        self.assertEqual((r[1], float(r[2]), r[3]), ("pending", 0.02, "Waiting for an editor's approval."))
        r = self.ask("picture_cover", "nil", {})[0]
        self.assertEqual((r[1], float(r[2])), ("pending", 0.01))
        # an editor's: approved at once, within the daily cap
        ideas = self.ask("picture_ideas", "nil", {}, uid=ADMIN)[0]
        self.assertEqual((ideas[1], float(ideas[2])), ("approved", 0.02))
        self.assertEqual(self.pg.execute("SELECT params FROM corner.requests WHERE id = %s", (ideas[0],)).fetchone()[0],
                         {"max": 6})
        # the desk takes the approved ones, and finds two ideas
        got = self.desk("SELECT public.corner_desk_pull(20, 'desk-pc')")[0][0]
        self.assertEqual(sorted(g["kind"] for g in got),
                         ["novel_page_edit", "picture_edit", "picture_ideas", "story_edit", "story_verify"])
        self.assertEqual(self.desk(c10a.REPORT, (ideas[0], "done", json.dumps({"ideas": [idea(31), idea(32, at="25.4")],
                                                                                "count": 2}),
                                                 "2 idea(s) for pictures; ask for any of them to be drawn.", 0.004, None)),
                         [(True,)])
        self.assertIn("an idea the desk proposed", str(self.ask("picture_draw", "nil", {"image_id": 33})))
        draw = self.ask("picture_draw", "nil", {"image_id": 31})[0]             # a researcher's: paid, it waits
        self.assertEqual((draw[1], float(draw[2])), ("pending", 0.1))
        seen = self.call(IDEAS, ("nil",), uid=RES2)
        self.assertEqual([(r[0], r[5], r[7], r[8], r[9]) for r in seen],
                         [(31, ideas[0], False, draw[0], "pending"), (32, ideas[0], False, None, None)])
        self.assertEqual(self.call("SELECT * FROM public.corner_request_decide(%s, true)", (draw[0],), uid=ADMIN)[0][0],
                         "approved")
        self.media("img:31", "nil", sha="7")                                    # drawn; the mirror has it
        self.assertIn("this idea is drawn already", str(self.ask("picture_draw", "nil", {"image_id": 31}, uid=ADMIN)))
        self.assertEqual([(r[0], r[7], r[9]) for r in self.call(IDEAS, ("nil",))], [(31, True, "approved"), (32, False, None)])
        # the cap counts the new paid kinds as any other
        self.call("SELECT public.corner_settings_set('daily_cap_usd', '0.15')", uid=SUPER)
        self.assertIn("Today's cap for the Corner is $0.15", str(self.ask("picture_draw", "nil", {"image_id": 32}, uid=ADMIN)))
        self.call("SELECT public.corner_settings_set('daily_cap_usd', '2.00')", uid=SUPER)
        self.assertEqual(self.ask("picture_draw", "nil", {"image_id": 32}, uid=ADMIN)[0][1], "approved")
        # researchers' paid requests need no editor when the super admin says so
        self.call("SELECT public.corner_settings_set('researchers_need_approval', 'false')", uid=SUPER)
        self.assertEqual(self.ask("picture_cover", "mal", {})[0][1], "approved")
        listed = self.call("SELECT kind, label, status FROM public.corner_requests('mine') WHERE kind = 'picture_cover'")
        self.assertEqual(listed, [("picture_cover", "An idea for a cover", "approved"),
                                  ("picture_cover", "An idea for a cover", "pending")])

    # ---- the two new site functions

    def test_corner_ideas(self):
        a = self.done("picture_ideas", "nil", [idea(21), idea(22, at="25.4")], uid=RES, ago=120)
        b = self.done("picture_cover", "nil", [idea(23, kind="cover", at=None)], uid=ADMIN, ago=60)
        self.done("picture_ideas", "nil", [idea(24)], status="failed", ago=30)
        self.done("picture_ideas", "nil", [idea(28)], status="running", ago=30)
        self.done("picture_ideas", "mal", [idea(25)], ago=30)
        self.done("picture_ideas", "nil", None, result={"ideas": {"image_id": 26}}, ago=180)       # not a list
        self.done("picture_ideas", "nil", None, result={"count": 0}, ago=190)
        self.done("story_mine", "nil", None, result={"ideas": [idea(29)]}, ago=30)                 # not an ideas request
        f = self.done("picture_ideas", "nil", None, ago=240,
                      result={"ideas": ["x", 7, None, [1], {"image_id": "abc"}, {"title": "no id"}, {"image_id": 1.5},
                                         {"image_id": "41"}, {"image_id": 27, "title": "t" * 400, "brief": "b" * 2500,
                                                              "kind": None}]})
        self.media("img:22", "nil", sha="9")                                    # drawn
        self.media("img:27", "nil", sha="8", retired=5)                         # drawn, then retired
        self.draw_request(21, "cancelled", 50)
        d2 = self.draw_request(21, "pending", 40)
        self.draw_request(21, "approved", 1, doc="mal")                         # another text's: not this one
        d3 = self.draw_request(22, "done", 20)
        for uid in (RES, RES2, ADMIN, SUPER):
            with self.subTest(uid=uid):
                rows = self.call(IDEAS, ("nil",), uid=uid)
                self.assertEqual([r[:6] + r[7:] for r in rows], [
                    (23, "cover", "Idea 23", "Brief of idea 23", None, b, False, None, None),
                    (21, "generated", "Idea 21", "Brief of idea 21", "25.3", a, False, d2, "pending"),
                    (22, "generated", "Idea 22", "Brief of idea 22", "25.4", a, True, d3, "done"),
                    (27, None, "t" * 300, "b" * 2000, None, f, False, None, None)])
        asked = dict(self.pg.execute("SELECT id, requested_at FROM corner.requests").fetchall())
        self.assertEqual([r[6] for r in self.call(IDEAS, ("nil",))], [asked[b], asked[a], asked[a], asked[f]])
        self.assertEqual([r[0] for r in self.call(IDEAS, ("mal",))], [25])
        self.assertEqual(self.call(IDEAS, (None,)), [])
        self.assertEqual(self.call(IDEAS, ("nope",)), [])
        # an idea in two results: the newer one's
        g = self.done("picture_ideas", "nil", [idea(22, at="25.9"), idea(40)], ago=10)
        self.assertEqual([(r[0], r[4], r[5]) for r in self.call(IDEAS, ("nil",))],
                         [(22, "25.9", g), (40, "25.3", g), (23, None, b), (21, "25.3", a), (27, None, f)])
        # at most 200
        self.done("picture_ideas", "nil", [idea(1000 + i) for i in range(250)], ago=1)
        rows = self.call(IDEAS, ("nil",))
        self.assertEqual(len(rows), 200)
        self.assertEqual((rows[0][0], rows[-1][0]), (1000, 1199))

    def test_corner_retired_pictures(self):
        for uid in (ADMIN, SUPER):
            with self.subTest(uid=uid):
                rows = self.call(RETIRED, ("nil",), uid=uid)
                self.assertEqual([r[:4] + r[5:] for r in rows], [(8, "generated", "Old lake", "The old lake", False),
                                                                 (5, "generated", "Old river", "The old river", True)])
                self.assertTrue(rows[0][4] > rows[1][4])                         # newest first
        self.assertEqual([r[0] for r in self.call(RETIRED, ("mal",), uid=ADMIN)], [6])
        self.assertEqual(self.call(RETIRED, (None,), uid=ADMIN), [])
        for uid in (RES, RES2):
            with self.subTest(uid=uid):
                self.assertIn("Only an editor (an admin or the super admin) may do this.", str(self.call(RETIRED, ("nil",), uid=uid)))
        self.assertIn("open to invited researchers", str(self.call(RETIRED, ("nil",), uid=READER)))
        self.assertIn("signed-in readers only", str(self.call(RETIRED, ("nil",), uid=None)))
        self.assertIn("permission denied", str(self.call(RETIRED, ("nil",), role="anon", uid=None)))
        self.pg.execute("UPDATE corpus.media SET retired_at = NULL WHERE media_key = 'img:8'")   # restored on the desk
        self.assertEqual([r[0] for r in self.call(RETIRED, ("nil",), uid=ADMIN)], [5])
        for i in range(205):
            self.media("img:%d" % (2000 + i), "nil", retired=1000 - i, sha="5")
        rows = self.call(RETIRED, ("nil",), uid=ADMIN)
        self.assertEqual((len(rows), rows[0][0], rows[1][0], rows[-1][0]), (200, 5, 2204, 2006))   # img:5: 2 hours ago


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C9WithC10b(c9.Corner):
    """Every test of tests/test_corner_pg_2026_10_09.py again, with C10a and C10b on top of C9."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pg.execute(C10A.read_text(encoding="utf-8"))
        cls.pg.execute(C10B.read_text(encoding="utf-8"))
        assert cls.pg.execute("SELECT to_regprocedure('public.corner_ideas(text)')").fetchone()[0]
        assert cls.pg.execute("SELECT position('CORNER_C10B_2026_10_09' IN prosrc) > 0 FROM pg_proc "
                              "WHERE oid = 'corner._clean(text, text, jsonb)'::regprocedure").fetchone()[0]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C10aWithC10b(c10a.CornerState):
    """Every test of tests/test_corner_state_pg_2026_10_09.py again, with C10b on top of C10a."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pg.execute(C10B.read_text(encoding="utf-8"))
        assert cls.pg.execute("SELECT to_regprocedure('public.corner_retired_pictures(text)')").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
