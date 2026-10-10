# -*- coding: ascii -*-
"""CORNER_MAIL_C12_2026_10_09 against a real PostgreSQL: docs/cloud/C12 (email from the Researchers'
Corner). The harness of tests/test_corner_state_pg_2026_10_09.py, with its BEFORE and AFTER lists (the
Supabase stand-ins, C4, C4b, C5, C7a, C7, C8, C9 twice, C10a twice), then C12 twice. The site asks, the
editors decide and the desk reports as the roles do (anon, a reader, two researchers, an admin, the
super admin, the desk as service_role); the corner-mail edge function's side (claim and done) runs as
service_role. The last four classes run every C9 test and every C10a test again with C12 on top, with
mail off and with mail on.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corner_mail_pg_2026_10_09
"""
import json, os, re, sys, time, unittest, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
import test_corner_pg_2026_10_09 as c9  # noqa: E402  (its Corner class runs again below, with C12)
import test_corner_state_pg_2026_10_09 as c10a  # noqa: E402  (its harness, and its CornerState class)

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C9F = CLOUD / "C9_researchers_corner_2026-10-09.sql"
C10A = c10a.C10A
C12 = CLOUD / "C12_corner_mail_2026-10-09.sql"
C12_CHECKS = CLOUD / "C12_checks_2026-10-09.sql"
BEFORE = list(c10a.BEFORE)
AFTER = list(c10a.AFTER) + [C12, C12]
SUPER, ADMIN, RES, RES2, READER = c10a.SUPER, c10a.ADMIN, c10a.RES, c10a.RES2, c10a.READER
NOMAIL = "77777777-7777-7777-7777-777777777777"      # an account with no email address
GHOST = "88888888-8888-8888-8888-888888888888"       # not an account at all
SITE = "https://srangam.nartiang.org"
FOOT = ("You get this because you use the Researchers' Corner on Srangam. To stop these emails: "
        + SITE + "/corpus/corner?tab=settings")
FROM = "Srangam desk <desk@nartiang.org>"
DEFAULTS = [("daily_cap_usd", "2.00"), ("researchers_need_approval", "true"), ("max_pending_per_person", "20"),
            ("mail_enabled", "false"), ("mail_from", FROM), ("mail_reply_to", ""), ("site_url", SITE)]
REPORT = c10a.REPORT
CLAIM = "SELECT * FROM public.corner_mail_claim(%s)"
DONE = "SELECT public.corner_mail_done(%s::bigint, %s::boolean, %s::text, %s::text)"
INVITE = "SELECT public.corner_mail_invite(%s::uuid, %s::text)"
PREFS = "SELECT * FROM public.corner_mail_prefs()"
PREFS_SET = "SELECT public.corner_mail_prefs_set(%s::boolean, %s::boolean)"
STATE = "SELECT * FROM public.corner_mail_state()"
SET = "SELECT public.corner_settings_set(%s, %s)"
SITE_FUNCS = {
    "corner_mail_prefs": "SELECT * FROM public.corner_mail_prefs()",
    "corner_mail_prefs_set": "SELECT public.corner_mail_prefs_set(true, true)",
    "corner_mail_state": "SELECT * FROM public.corner_mail_state()",
    "corner_mail_invite": "SELECT public.corner_mail_invite('00000000-0000-0000-0000-000000000000', 'x')",
    "corner_settings_set": "SELECT public.corner_settings_set('mail_enabled', 'true')",
}
EDGE_FUNCS = {
    "corner_mail_claim": "SELECT * FROM public.corner_mail_claim(1)",
    "corner_mail_done": "SELECT public.corner_mail_done(1, true, NULL, NULL)",
}


def refuse_live():
    if "supabase" in DSN or "pooler" in DSN:
        raise unittest.SkipTest("refusing to run against a Supabase host")


def reset_settings(pg, mail_on=False):
    for k, v in DEFAULTS:
        if k == "mail_enabled":
            v = "true" if mail_on else "false"
        pg.execute("INSERT INTO corner.settings (key, value) VALUES (%s, %s) "
                   "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = NULL", (k, v))


def watch_notices(cls):
    cls.notices = []
    cls.pg.add_notice_handler(lambda d, n=cls.notices: n.append((d.severity_nonlocalized or d.severity or "",
                                                                 d.message_primary or "")))


def c12_warnings(notices):
    return [m for s, m in notices if s == "WARNING" and m.startswith("C12 mail")]


def body(*lines):
    return "\n".join(lines)


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Mail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        refuse_live()
        cls.pg = psycopg.connect(DSN, autocommit=True)
        watch_notices(cls)
        x = cls.pg.execute
        for f in BEFORE:
            x(f.read_text(encoding="utf-8"))
        x("INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'dhruv.rakesh@gmail.com', now()), "
          "(%s, 'admin@example.org', now()), (%s, 'kanika@example.org', now()), (%s, 'r2@example.org', now()), "
          "(%s, 'reader@example.org', now()), (%s, NULL, NULL) ON CONFLICT DO NOTHING",
          (SUPER, ADMIN, RES, RES2, READER, NOMAIL))
        for f in AFTER:
            x(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        x = self.pg.execute
        x("TRUNCATE corner.outbox, corner.mail_prefs, corner.requests, corner.collections, corner.collection_items, "
          "corner.events RESTART IDENTITY")
        reset_settings(self.pg, mail_on=False)
        x("UPDATE corner.worker SET last_seen = NULL, info = NULL")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("DELETE FROM rbac.invites")
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
        del self.notices[:]

    # ---- helpers (those of tests/test_corner_pg_2026_10_09.py, and the mail's own)

    def call(self, sql, args=(), role="authenticated", uid=RES, timeout=None):
        with self.pg.transaction(force_rollback=False):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            if timeout:
                self.pg.execute("SET LOCAL statement_timeout = '%s'" % timeout)
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def ask(self, kind, doc, params, uid=RES, note=None):
        r = self.call("SELECT * FROM public.corner_request_create(%s, %s, %s::jsonb, %s)",
                      (kind, doc, json.dumps(params), note), uid=uid)
        self.assertIsInstance(r, list, r)
        return r[0][0]

    def desk(self, sql, args=()):
        return self.call(sql, args, role="service_role", uid=None)

    def mail_on(self, on=True):
        self.pg.execute("UPDATE corner.settings SET value = %s WHERE key = 'mail_enabled'", ("true" if on else "false",))

    def status(self, rid):
        return self.pg.execute("SELECT status FROM corner.requests WHERE id = %s", (rid,)).fetchone()[0]

    def decide(self, rid, ok, note=None, uid=ADMIN):
        r = self.call("SELECT * FROM public.corner_request_decide(%s, %s, %s)", (rid, ok, note), uid=uid)
        self.assertIsInstance(r, list, r)
        return r[0][0]

    def take(self, rid):
        got = self.desk("SELECT public.corner_desk_pull(20, 'desk-pc')")[0][0]
        self.assertIn(rid, [g["id"] for g in got])

    def report(self, rid, status, result=None, message=None, cost=None):
        r = self.desk(REPORT, (rid, status, None if result is None else json.dumps(result), message, cost, None))
        self.assertIsInstance(r, list, r)
        return r[0][0]

    def outbox(self, rid=None):
        """(kind, user_id, request_id) of the queued emails, in order; of one request if rid is given."""
        return [(k, u, r) for k, u, r in self.pg.execute(
            "SELECT kind, user_id::text, request_id FROM corner.outbox WHERE %s::bigint IS NULL OR request_id = %s "
            "ORDER BY id", (rid, rid)).fetchall()]

    def mail(self, kind, rid, uid):
        """The subject and the body of one queued email."""
        return self.pg.execute("SELECT subject, body FROM corner.outbox WHERE kind = %s AND request_id = %s "
                               "AND user_id = %s", (kind, rid, uid)).fetchone()

    def put(self, kind="request_done", user_id=RES, to_email=None, request_id=None, invite_id=None, subject="s",
            text="b", **cols):
        names = ["kind", "user_id", "to_email", "request_id", "invite_id", "subject", "body"] + sorted(cols)
        vals = [kind, user_id, to_email, request_id, invite_id, subject, text] + [cols[k] for k in sorted(cols)]
        return self.pg.execute("INSERT INTO corner.outbox (%s) VALUES (%s) RETURNING id"
                               % (", ".join(names), ", ".join(["%s"] * len(names))), vals).fetchone()[0]

    def orow(self, oid):
        return self.pg.execute("SELECT attempts, claimed_at, sent_at, failed_at, last_error, provider_id, body "
                               "FROM corner.outbox WHERE id = %s", (oid,)).fetchone()

    def claim(self, n=10):
        r = self.desk(CLAIM, (n,))
        self.assertIsInstance(r, list, r)
        return r

    def done(self, oid, ok, provider=None, error=None):
        r = self.desk(DONE, (oid, ok, provider, error))
        self.assertIsInstance(r, list, r)
        return r[0][0]

    def invite(self, email="new@example.org", note="Welcome to the corpus.", days=14):
        r = self.call("SELECT invite_id, token, expires_at FROM public.research_invite_create(%s, %s, %s)",
                      (email, note, days), uid=SUPER)
        self.assertIsInstance(r, list, r)
        return str(r[0][0]), r[0][1]

    def warnings(self):
        return c12_warnings(self.notices)

    # ---- the shape, and who may call what

    def test_the_tables_the_indexes_and_the_trigger(self):
        t = self.pg.execute(
            "SELECT c.relname, c.relrowsecurity, has_table_privilege('anon', c.oid, 'SELECT'), "
            "has_table_privilege('authenticated', c.oid, 'SELECT'), has_table_privilege('authenticated', c.oid, 'INSERT'), "
            "has_table_privilege('service_role', c.oid, 'SELECT') FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'corner' AND c.relname IN ('mail_prefs', 'outbox') ORDER BY 1").fetchall()
        self.assertEqual(t, [("mail_prefs", True, False, False, False, False), ("outbox", True, False, False, False, False)])
        cols = lambda rel: self.pg.execute(
            "SELECT attname, format_type(atttypid, atttypmod), attnotnull FROM pg_attribute WHERE attrelid = %s::regclass "
            "AND attnum > 0 AND NOT attisdropped ORDER BY attnum", (rel,)).fetchall()
        self.assertEqual(cols("corner.mail_prefs"), [
            ("user_id", "uuid", True), ("on_my_requests", "boolean", True), ("on_queue", "boolean", True),
            ("updated_at", "timestamp with time zone", True)])
        self.assertEqual(cols("corner.outbox"), [
            ("id", "bigint", True), ("kind", "text", True), ("user_id", "uuid", False), ("to_email", "text", False),
            ("request_id", "bigint", False), ("invite_id", "uuid", False), ("subject", "text", True),
            ("body", "text", True), ("created_at", "timestamp with time zone", True),
            ("claimed_at", "timestamp with time zone", False), ("sent_at", "timestamp with time zone", False),
            ("failed_at", "timestamp with time zone", False), ("attempts", "integer", True), ("last_error", "text", False),
            ("provider_id", "text", False)])
        idx = dict(self.pg.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'corner' "
                                   "AND tablename = 'outbox'").fetchall())
        self.assertEqual(sorted(idx), ["corner_outbox_one_open_invite", "corner_outbox_one_per_request",
                                       "corner_outbox_waiting", "outbox_pkey"])
        self.assertIn("UNIQUE INDEX corner_outbox_one_per_request ON corner.outbox USING btree (kind, request_id, user_id) "
                      "WHERE (request_id IS NOT NULL)", idx["corner_outbox_one_per_request"])
        self.assertIn("(sent_at, failed_at, created_at)", idx["corner_outbox_waiting"])
        fk = self.pg.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'corner.outbox'::regclass "
                             "AND contype = 'f'").fetchall()
        self.assertEqual(fk, [("FOREIGN KEY (request_id) REFERENCES corner.requests(id) ON DELETE CASCADE",)])
        bad = {"kind": "('nope', %s, NULL, 's', 'b')", "to_email": "('invite', NULL, repeat('a', 255), 's', 'b')",
               "subject": "('invite', %s, NULL, repeat('s', 301), 'b')", "body": "('invite', %s, NULL, 's', repeat('b', 6001))",
               "nobody": "('invite', NULL, NULL, 's', 'b')", "no body": "('invite', %s, NULL, 's', NULL)"}
        for what, vals in bad.items():
            with self.subTest(what=what):
                with self.assertRaises(Exception):
                    with self.pg.transaction():
                        self.pg.execute("INSERT INTO corner.outbox (kind, user_id, to_email, subject, body) VALUES "
                                        + vals, (RES,) * vals.count("%s"))
        ok = self.put("invite", None, "x@example.org", subject="s" * 300, text="b" * 6000)
        self.assertEqual(self.orow(ok)[0], 0)
        trg = self.pg.execute("SELECT tgname, tgenabled, pg_get_triggerdef(oid) FROM pg_trigger "
                              "WHERE tgrelid = 'corner.requests'::regclass AND NOT tgisinternal").fetchall()
        self.assertEqual(trg, [("corner_requests_mail", "O", "CREATE TRIGGER corner_requests_mail AFTER INSERT OR UPDATE "
                                "OF status ON corner.requests FOR EACH ROW EXECUTE FUNCTION corner._mail_on_request()")])
        fns = self.pg.execute(
            "SELECT n.nspname || '.' || p.proname, pg_get_function_identity_arguments(p.oid), pg_get_function_result(p.oid), "
            "p.prosecdef, p.provolatile, p.proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE (n.nspname = 'corner' AND p.proname LIKE '\\_mail\\_%%') OR (n.nspname = 'public' AND "
            "(p.proname LIKE 'corner\\_mail\\_%%' OR p.proname = 'corner_settings_set')) ORDER BY 1").fetchall()
        sp = ['search_path=""']
        self.assertEqual(fns, [
            ("corner._mail_on_request", "", "trigger", True, "v", sp),
            ("corner._mail_text", "p text, p_max integer", "text", False, "i", sp),
            ("corner._mail_usd", "p numeric", "text", False, "s", sp),
            ("public.corner_mail_claim", "p_limit integer",
             "TABLE(id bigint, to_email text, mail_from text, reply_to text, subject text, body text)", True, "v", sp),
            ("public.corner_mail_done", "p_id bigint, p_ok boolean, p_provider_id text, p_error text", "boolean", True, "v", sp),
            ("public.corner_mail_invite", "p_invite uuid, p_token text", "text", True, "v", sp),
            ("public.corner_mail_prefs", "",
             "TABLE(on_my_requests boolean, on_queue boolean, mail_enabled boolean, is_editor boolean, mail_from text)",
             True, "s", sp),
            ("public.corner_mail_prefs_set", "p_on_my_requests boolean, p_on_queue boolean", "boolean", True, "v", sp),
            ("public.corner_mail_state", "",
             "TABLE(mail_enabled boolean, waiting bigint, sent_today bigint, failed_7d bigint, "
             "last_sent_at timestamp with time zone, last_error text)", True, "s", sp),
            ("public.corner_settings_set", "p_key text, p_value text", "text", True, "v", sp)])

    def test_the_settings_and_their_key_check(self):
        rows = self.pg.execute("SELECT key, value FROM corner.settings ORDER BY key").fetchall()
        self.assertEqual(rows, sorted(DEFAULTS))
        chk = self.pg.execute("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                              "WHERE conrelid = 'corner.settings'::regclass AND contype = 'c'").fetchall()
        self.assertEqual(chk, [("settings_key_check", "CHECK ((key = ANY (ARRAY['daily_cap_usd'::text, "
                                "'researchers_need_approval'::text, 'max_pending_per_person'::text, 'mail_enabled'::text, "
                                "'mail_from'::text, 'mail_reply_to'::text, 'site_url'::text])))")])
        with self.assertRaises(Exception):
            with self.pg.transaction():
                self.pg.execute("INSERT INTO corner.settings (key, value) VALUES ('nope', 'x')")
        # the shipped values: mail off
        self.assertEqual(self.call(PREFS, uid=SUPER), [(True, True, False, True, FROM)])

    def test_grants(self):
        priv = dict((r[0], r[1:]) for r in self.pg.execute(
            "SELECT p.proname, has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE'), has_function_privilege('service_role', p.oid, 'EXECUTE') "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE (n.nspname = 'public' AND "
            "(p.proname LIKE 'corner\\_mail\\_%%' OR p.proname = 'corner_settings_set')) "
            "OR (n.nspname = 'corner' AND p.proname LIKE '\\_mail\\_%%')").fetchall())
        for f in EDGE_FUNCS:
            self.assertEqual(priv[f], (False, False, True), f)
        for f in SITE_FUNCS:
            self.assertEqual(priv[f][:2], (False, True), f)
        for f in ("_mail_on_request", "_mail_text", "_mail_usd"):
            self.assertEqual(priv[f], (False, False, False), f)
        for name, sql in list(SITE_FUNCS.items()) + list(EDGE_FUNCS.items()):
            with self.subTest(anon=name):
                self.assertIn("permission denied", str(self.call(sql, role="anon", uid=None)))
        for name, sql in EDGE_FUNCS.items():
            for uid in (RES, ADMIN, SUPER):
                with self.subTest(edge=name, uid=uid):
                    self.assertIn("permission denied", str(self.call(sql, uid=uid)))
        for sql in ("SELECT * FROM corner.outbox", "SELECT * FROM corner.mail_prefs",
                    "SELECT corner._mail_text('x', 1)", "SELECT corner._mail_usd(1)"):
            for role, uid in (("authenticated", SUPER), ("service_role", None)):
                with self.subTest(sql=sql, role=role):
                    self.assertIn("permission denied", str(self.call(sql, role=role, uid=uid)))
        self.assertEqual(self.claim(1), [])                                       # the edge function: mail is off
        self.assertEqual(self.done(1, True), False)

    def test_needs_c9_c10a_and_c7(self):
        import psycopg
        text = C12.read_text(encoding="utf-8")
        pre = text[text.index("DO $$\nBEGIN\n  IF to_regclass('corner.settings')"):]
        pre = pre[:pre.index("END $$;") + len("END $$;")]
        for hide, want in (("ALTER SCHEMA corner RENAME TO corner_hidden_c12", "C12: needs C9"),
                           ("ALTER FUNCTION public.corner_request_track(bigint[]) RENAME TO corner_request_track_hidden",
                            "C12: run C10a first"),
                           ("ALTER SCHEMA rbac RENAME TO rbac_hidden_c12", "C12: needs C7")):
            with self.subTest(want=want):
                with self.pg.transaction(force_rollback=True):
                    self.pg.execute(hide)
                    with self.assertRaises(psycopg.errors.RaiseException) as e:
                        with self.pg.transaction():
                            self.pg.execute(pre)
                    self.assertIn(want, str(e.exception))
        self.assertIsNotNone(self.pg.execute("SELECT to_regclass('corner.outbox')").fetchone()[0])

    def test_a_rerun_keeps_everything_and_follows_a_rerun_of_c9(self):
        self.mail_on()
        self.call(SET, ("mail_from", "The editors <editors@nartiang.org>"), uid=SUPER)
        self.call(PREFS_SET, (False, True))
        rid = self.ask("story_mine", "nil", {"max": 2})
        before = self.pg.execute("SELECT id, kind, user_id, subject, body FROM corner.outbox ORDER BY id").fetchall()
        self.assertEqual(len(before), 2)
        self.pg.execute(C12.read_text(encoding="utf-8"))
        self.assertEqual(self.pg.execute("SELECT id, kind, user_id, subject, body FROM corner.outbox ORDER BY id").fetchall(),
                         before)
        self.assertEqual(self.call(PREFS), [(False, True, True, False, None)])
        self.assertEqual(self.call(PREFS, uid=SUPER)[0][4], "The editors <editors@nartiang.org>")
        self.assertEqual(self.pg.execute("SELECT count(*) FROM pg_trigger WHERE tgname = 'corner_requests_mail'").fetchone()[0], 1)
        # a re-run of C9 puts C9's corner_settings_set back; C10a and C12 again restore theirs
        self.pg.execute(C9F.read_text(encoding="utf-8"))
        self.assertIn("no such setting", str(self.call(SET, ("site_url", SITE), uid=SUPER)))
        self.assertEqual(self.pg.execute("SELECT value FROM corner.settings WHERE key = 'mail_enabled'").fetchone()[0], "true")
        self.pg.execute(C10A.read_text(encoding="utf-8"))
        self.pg.execute(C12.read_text(encoding="utf-8"))
        self.assertEqual(self.call(SET, ("site_url", SITE), uid=SUPER), [(SITE,)])
        self.decide(rid, False, "no")
        self.assertEqual([k for k, _u, _r in self.outbox()], ["request_pending"] * 2)   # RES turned on_my_requests off
        self.assertEqual(self.warnings(), [])

    # ---- what is queued

    def test_nothing_is_queued_while_mail_is_off(self):
        a = self.ask("story_mine", "nil", {"max": 2})                            # pending
        b = self.ask("story_mine", "nil", {"max": 3})
        c = self.ask("story_approve", "nil", {"story_id": 35}, uid=ADMIN)         # an editor's, approved
        self.decide(a, False, "no")
        self.decide(b, True)
        self.take(b)
        self.report(b, "done", {"count": 1}, "1 episode proposed", 0.01)
        self.report(c, "failed", None, "the story changed")
        self.assertEqual(self.outbox(), [])
        oid = self.put()
        self.assertEqual(self.claim(5), [])                                       # mail off: nothing taken
        self.assertEqual(self.orow(oid)[:4], (0, None, None, None))
        self.assertEqual(self.call(PREFS)[0][2], False)
        iid, tok = self.invite()
        self.assertIn("Email is off; the super admin turns it on in Corner -> Settings",
                      str(self.call(INVITE, (iid, tok), uid=SUPER)))
        self.assertEqual(self.warnings(), [])

    def test_a_waiting_request_mails_each_editor_but_the_one_who_asked(self):
        self.mail_on()
        r1 = self.ask("story_mine", "nil", {"max": 2})
        self.assertEqual(self.status(r1), "pending")
        self.assertEqual(sorted(self.outbox()), sorted([("request_pending", ADMIN, r1), ("request_pending", SUPER, r1)]))
        subject, text = self.mail("request_pending", r1, ADMIN)
        self.assertEqual(subject, "Srangam: request #1 waits for approval - Find episodes in a text")
        self.assertEqual(text, body(
            "Request #1 waits for an editor's approval.", "",
            "Who asked: kanika@example.org", "What was asked: Find episodes in a text", "Text: Nilamata",
            "Estimate: $0.01", "",
            "To approve or reject it: " + SITE + "/corpus/corner?tab=queue", "", FOOT))
        self.assertEqual(self.mail("request_pending", r1, SUPER), (subject, text))
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.outbox WHERE to_email IS NULL AND attempts = 0 "
                                         "AND claimed_at IS NULL AND sent_at IS NULL AND failed_at IS NULL").fetchone()[0], 2)
        # the one who asked is left out, even an editor (an editor's own request never waits from the
        # site; here one is put in by hand)
        r2 = self.pg.execute("INSERT INTO corner.requests (kind, doc_code, params, requested_by, status, est_usd) "
                             "VALUES ('story_mine', 'mal', '{\"max\": 1}', %s, 'pending', 0.01) RETURNING id",
                             (ADMIN,)).fetchone()[0]
        self.assertEqual(self.outbox(r2), [("request_pending", SUPER, r2)])
        self.assertIn("Who asked: admin@example.org", self.mail("request_pending", r2, SUPER)[1])
        self.assertIn("Text: Mallapurana", self.mail("request_pending", r2, SUPER)[1])
        # an account with no email address (or none at all) still reaches the editors
        for who in (NOMAIL, GHOST):
            r = self.pg.execute("INSERT INTO corner.requests (kind, doc_code, params, requested_by, status, est_usd) "
                                "VALUES ('story_mine', 'mal', jsonb_build_object('who', %s::text), %s, 'pending', 0.01) "
                                "RETURNING id", (who, who)).fetchone()[0]
            self.assertEqual(len(self.outbox(r)), 2)
            self.assertIn("Who asked: an account with no email address", self.mail("request_pending", r, ADMIN)[1])
        # on_queue off for the super admin: only the admin hears of the next one; then neither
        self.assertEqual(self.call(PREFS_SET, (None, False), uid=SUPER), [(True,)])
        r3 = self.ask("story_mine", "nil", {"max": 3})
        self.assertEqual(self.outbox(r3), [("request_pending", ADMIN, r3)])
        self.call(PREFS_SET, (True, False), uid=ADMIN)
        r4 = self.ask("story_mine", "nil", {"max": 4})
        self.assertEqual(self.outbox(r4), [])
        self.call(PREFS_SET, (True, True), uid=ADMIN)
        self.call(PREFS_SET, (True, False), uid=RES)                             # a researcher's on_queue: unused
        r5 = self.ask("story_mine", "nil", {"max": 5}, uid=RES2)
        self.assertEqual(self.outbox(r5), [("request_pending", ADMIN, r5)])
        # nothing waits, nothing is sent: an editor's request, approved at once; a researcher's when
        # researchers need no approval; approving a waiting one
        r6 = self.ask("story_mine", "nil", {"max": 6}, uid=ADMIN)
        self.assertEqual((self.status(r6), self.outbox(r6)), ("approved", []))
        self.call(SET, ("researchers_need_approval", "false"), uid=SUPER)
        r7 = self.ask("story_mine", "nil", {"max": 7})
        self.assertEqual((self.status(r7), self.outbox(r7)), ("approved", []))
        n = len(self.outbox())
        self.decide(r3, True)
        self.assertEqual(len(self.outbox()), n)
        self.assertEqual(self.warnings(), [])

    def test_done_failed_and_rejected_mail_the_one_who_asked(self):
        self.mail_on()
        a = self.ask("story_range", "nil", {"from": "25.2", "to": "25.9", "title": "Vitasta flows"})
        self.decide(a, True)
        self.take(a)
        self.report(a, "running", None, "The desk is working on it.")
        self.report(a, "running", {"progress": {"step": 1, "of": 2, "note": "Writing"}}, "Writing")
        self.assertEqual([k for k, _u, _r in self.outbox(a)], ["request_pending", "request_pending"])   # running: no email
        self.report(a, "done", {"story_id": 40}, "Story #40 written.", 0.0071)
        self.assertEqual(self.outbox(a)[2:], [("request_done", RES, a)])
        subject, text = self.mail("request_done", a, RES)
        self.assertEqual(subject, "Srangam: request #1 is done - A story from passages you choose")
        self.assertEqual(text, body(
            "Your request #1 is done.", "",
            "What was asked: A story from passages you choose", "Text: Nilamata",
            "The desk says: Story #40 written.", "Cost: $0.0071", "",
            "See it in the Corner: " + SITE + "/corpus/corner?tab=mine", "", FOOT))
        # an editor's decision carried out: no email; the same failing: an email
        b = self.ask("story_approve", "nil", {"story_id": 35}, uid=ADMIN)
        c = self.ask("story_retire", "nil", {"story_id": 36}, uid=ADMIN)
        self.take(b)
        self.report(b, "done", {"story_id": 35, "status": "approved"}, "Story #35 approved.", 0)
        self.assertEqual(self.outbox(b), [])
        self.report(c, "failed", None, "Story #36 changed on the desk.\nNothing was done.")
        self.assertEqual(self.outbox(c), [("request_failed", ADMIN, c)])
        subject, text = self.mail("request_failed", c, ADMIN)
        self.assertEqual(subject, "Srangam: request #%d failed - Retire a story" % c)
        self.assertEqual(text, body(
            "Your request #%d could not be done." % c, "",
            "What was asked: Retire a story", "Text: Nilamata",
            "The desk says: Story #36 changed on the desk. Nothing was done.", "",
            "See it in the Corner: " + SITE + "/corpus/corner?tab=mine", "", FOOT))
        # a researcher's paid request failing, with a long message (cut to 600) and a cost
        d = self.ask("story_mine", "nil", {"max": 2})
        self.decide(d, True)
        self.take(d)
        self.report(d, "failed", None, "x" * 2000, 0.004)
        text = self.mail("request_failed", d, RES)[1]
        self.assertIn("\nThe desk says: " + "x" * 600 + "\nCost: $0.004\n", text)
        # rejected, with the editor's note and without one
        e = self.ask("story_mine", "nil", {"max": 3})
        f = self.ask("story_mine", "nil", {"max": 4})
        self.decide(e, False, "Not this text, please.")
        self.decide(f, False)
        subject, text = self.mail("request_rejected", e, RES)
        self.assertEqual(subject, "Srangam: request #%d was not approved - Find episodes in a text" % e)
        self.assertEqual(text, body(
            "An editor did not approve your request #%d." % e, "",
            "What was asked: Find episodes in a text", "Text: Nilamata",
            "The editor's note: Not this text, please.", "",
            "See it in the Corner: " + SITE + "/corpus/corner?tab=mine", "", FOOT))
        self.assertNotIn("note", self.mail("request_rejected", f, RES)[1])
        # withdrawn: no email; taken and never finished, put back: no email; failed after three: an email
        g = self.ask("story_mine", "nil", {"max": 5})
        self.call("SELECT * FROM public.corner_request_cancel(%s)", (g,))
        self.assertEqual([k for k, _u, _r in self.outbox(g)], ["request_pending", "request_pending"])
        h = self.ask("story_mine", "mal", {"max": 2}, uid=RES2)
        self.decide(h, True)
        self.take(h)
        self.pg.execute("UPDATE corner.requests SET claimed_at = now() - interval '4 hours' WHERE id = %s", (h,))
        self.take(h)                                                              # back to approved, taken again
        self.assertEqual([k for k, _u, _r in self.outbox(h)], ["request_pending", "request_pending"])
        self.pg.execute("UPDATE corner.requests SET claimed_at = now() - interval '4 hours', attempts = 3 WHERE id = %s", (h,))
        self.desk("SELECT public.corner_desk_pull(20, 'desk-pc')")
        self.assertEqual(self.status(h), "failed")
        self.assertEqual(self.outbox(h)[2:], [("request_failed", RES2, h)])
        self.assertIn("The desk says: The desk did not finish it in three attempts.", self.mail("request_failed", h, RES2)[1])
        self.assertIn("Text: Mallapurana", self.mail("request_failed", h, RES2)[1])
        # one email of a kind per request and person, whatever happens to the request afterwards
        self.pg.execute("UPDATE corner.requests SET status = 'running' WHERE id = %s", (a,))
        self.pg.execute("UPDATE corner.requests SET status = 'done' WHERE id = %s", (a,))
        self.assertEqual([k for k, _u, _r in self.outbox(a)].count("request_done"), 1)
        self.assertEqual(self.warnings(), [])
        for (txt,) in self.pg.execute("SELECT subject || body FROM corner.outbox").fetchall():
            txt.encode("ascii")
            self.assertNotIn("Text of", txt)                                      # no story text

    def test_turning_my_emails_off(self):
        self.mail_on()
        self.assertEqual(self.call(PREFS_SET, (False, None)), [(True,)])
        a = self.ask("story_mine", "nil", {"max": 2})
        b = self.ask("story_mine", "nil", {"max": 3})
        self.assertEqual(len(self.outbox(a)), 2)                                  # the editors still hear of it
        self.decide(a, True)
        self.decide(b, False, "no")
        self.take(a)
        self.report(a, "done", {"count": 0}, "nothing found", 0.01)
        self.assertEqual([k for k, _u, _r in self.outbox()], ["request_pending"] * 4)
        for uid in (ADMIN, SUPER):
            self.call(PREFS_SET, (None, False), uid=uid)
        c = self.ask("story_mine", "nil", {"max": 4})
        self.assertEqual(self.outbox(c), [])
        self.call(PREFS_SET, (True, None))
        self.decide(c, False, "again no")
        self.assertEqual(self.outbox(c), [("request_rejected", RES, c)])
        self.assertEqual(self.warnings(), [])

    def test_the_trigger_never_breaks_a_request(self):
        self.mail_on()
        self.pg.execute("DELETE FROM corner.settings WHERE key = 'site_url'")    # composing fails: no link
        r = self.call("SELECT * FROM public.corner_request_create('story_mine', 'nil', '{\"max\": 2}', NULL)")
        self.assertEqual((r[0][0], r[0][1]), (1, "pending"))
        self.assertEqual(self.status(1), "pending")
        self.assertEqual(self.outbox(), [])
        w = self.warnings()
        self.assertEqual(len(w), 1)
        self.assertIn("C12 mail: request #1 is kept, but its email was not queued: the setting site_url is missing", w[0])
        self.assertEqual(self.decide(1, False, "no"), "rejected")
        self.assertEqual((self.status(1), self.outbox()), ("rejected", []))
        self.pg.execute("INSERT INTO corner.settings (key, value) VALUES ('site_url', 'http://insecure.example.org')")
        a = self.ask("story_approve", "nil", {"story_id": 35}, uid=ADMIN)
        self.take(a)
        self.assertEqual(self.report(a, "failed", None, "no"), True)
        self.assertEqual((self.status(a), self.outbox()), ("failed", []))
        self.assertEqual(len(self.warnings()), 3)
        self.pg.execute("UPDATE corner.settings SET value = %s WHERE key = 'site_url'", (SITE,))
        # the queue itself refuses the row: the request still goes through
        self.pg.execute("ALTER TABLE corner.outbox ADD CONSTRAINT c12_test_block CHECK (false) NOT VALID")
        try:
            b = self.ask("story_mine", "nil", {"max": 3})
            self.assertEqual((self.status(b), self.outbox()), ("pending", []))
            self.assertIn("c12_test_block", self.warnings()[-1])
            self.assertEqual(self.decide(b, True), "approved")
        finally:
            self.pg.execute("ALTER TABLE corner.outbox DROP CONSTRAINT c12_test_block")
        c = self.ask("story_mine", "nil", {"max": 4})                             # all well again
        self.assertEqual(len(self.outbox(c)), 2)
        self.assertEqual(len(self.warnings()), 4)

    # ---- the corner-mail edge function's side

    def test_claim(self):
        self.mail_on()
        for k in (2, 3, 4):
            self.ask("story_mine", "nil", {"max": k})
        ids = [r[0] for r in self.pg.execute("SELECT id FROM corner.outbox ORDER BY created_at, id").fetchall()]
        self.assertEqual(len(ids), 6)
        got = self.claim(2)
        self.assertEqual([g[0] for g in got], ids[:2])                            # oldest first
        addr = {ADMIN: "admin@example.org", SUPER: "dhruv.rakesh@gmail.com"}
        for oid, to, frm, reply, subject, text in got:
            uid, s, b = self.pg.execute("SELECT user_id::text, subject, body FROM corner.outbox WHERE id = %s",
                                        (oid,)).fetchone()
            self.assertEqual((to, frm, reply, subject, text), (addr[uid], FROM, None, s, b))   # from auth.users
            att, claimed = self.orow(oid)[:2]
            self.assertEqual(att, 1)
            self.assertIsNotNone(claimed)
        self.assertEqual(self.orow(ids[2])[:2], (0, None))
        self.assertEqual([g[0] for g in self.claim(0)], ids[2:3])                 # at least one
        self.assertEqual([g[0] for g in self.claim(-5)], ids[3:4])
        self.assertEqual([g[0] for g in self.claim(None)], ids[4:5])
        self.assertEqual([g[0] for g in self.claim(100)], ids[5:])
        self.assertEqual(self.claim(10), [])                                      # each taken once
        # taken ten minutes ago and not answered: taken again
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '9 minutes' WHERE id = %s", (ids[0],))
        self.assertEqual(self.claim(10), [])
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '11 minutes' WHERE id = %s", (ids[0],))
        self.assertEqual([g[0] for g in self.claim(10)], [ids[0]])
        self.assertEqual(self.orow(ids[0])[0], 2)
        # at most 20 at a time; a reply-to once it is set; an address given wins over the account's
        self.pg.execute("INSERT INTO corner.outbox (kind, user_id, subject, body) "
                        "SELECT 'request_done', %s, 's' || g, 'b' FROM generate_series(1, 25) g", (RES,))
        self.call(SET, ("mail_reply_to", "editors@nartiang.org"), uid=SUPER)
        got = self.claim(100)
        self.assertEqual(len(got), 20)
        self.assertEqual({(g[1], g[3]) for g in got}, {("kanika@example.org", "editors@nartiang.org")})
        self.assertEqual(len(self.claim(100)), 5)
        other = self.put(user_id=RES, to_email="other@example.org")
        self.assertEqual([(g[0], g[1]) for g in self.claim(5)], [(other, "other@example.org")])
        # no address: given up, not returned
        lost = [self.put(user_id=NOMAIL), self.put(user_id=GHOST), self.put(user_id=None, to_email="   ")]
        keep = self.put(user_id=RES2)
        self.assertEqual([(g[0], g[1]) for g in self.claim(10)], [(keep, "r2@example.org")])
        for oid in lost:
            att, claimed, sent, failed, err = self.orow(oid)[:5]
            self.assertEqual((att, claimed, sent, err), (0, None, None, "no address"))
            self.assertIsNotNone(failed)
        # mail off: nothing is taken, even what could be taken again
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '1 hour' WHERE id = %s", (keep,))
        self.mail_on(False)
        self.assertEqual(self.claim(10), [])
        self.assertEqual(self.orow(keep)[0], 1)
        self.assertEqual(self.warnings(), [])

    def test_claim_skips_what_another_claim_holds(self):
        import psycopg
        self.mail_on()
        a, b = self.put(), self.put(user_id=RES2)
        other = psycopg.connect(DSN)
        try:
            other.execute("SELECT id FROM corner.outbox WHERE id = %s FOR UPDATE", (a,))
            t0 = time.time()
            got = self.call(CLAIM, (10,), role="service_role", uid=None, timeout="3s")
            self.assertIsInstance(got, list, got)                                 # did not wait for the lock
            self.assertEqual([g[0] for g in got], [b])
            self.assertLess(time.time() - t0, 2.5)
        finally:
            other.rollback()
            other.close()
        self.assertEqual([g[0] for g in self.claim(10)], [a])

    def test_done(self):
        self.mail_on()
        r = self.ask("story_mine", "nil", {"max": 2})
        o1, o2 = [g[0] for g in self.claim(2)]
        self.assertEqual(self.done(o1, True, "re_" + "p" * 300, None), True)
        att, claimed, sent, failed, err, prov, text = self.orow(o1)
        self.assertEqual((att, claimed, failed, err, prov), (1, None, None, None, "re_" + "p" * 197))
        self.assertIsNotNone(sent)
        self.assertIn("Request #%d waits" % r, text)                             # a request's body is kept
        self.assertEqual(self.done(o1, True, "again", None), False)               # sent already
        self.assertEqual(self.done(o1, False, None, "late"), False)
        self.assertEqual(self.done(9999, True, None, None), False)
        # not sent: kept for the next round, given up after the fifth attempt
        for n in range(1, 6):
            if n > 1:
                self.assertEqual([g[0] for g in self.claim(5)], [o2])
            self.assertEqual(self.done(o2, False, None, "HTTP 422 %d " % n + "e" * 1000), True)
            att, claimed, sent, failed, err = self.orow(o2)[:5]
            self.assertEqual((att, claimed, sent, len(err)), (n, None, None, 500))
            self.assertTrue(err.startswith("HTTP 422 %d " % n))
            self.assertEqual(failed is not None, n == 5)
        self.assertEqual(self.claim(5), [])
        o3 = self.put()
        self.assertEqual([g[0] for g in self.claim(1)], [o3])
        self.assertEqual(self.done(o3, False, None, ""), True)
        self.assertEqual(self.orow(o3)[4], "not sent")
        # taken five times and never answered (the function died): given up on the next claim
        o4 = self.put(attempts=5, claimed_at=None)
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '11 minutes' WHERE id = %s", (o4,))
        o5 = self.put(attempts=5)
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '1 minute' WHERE id = %s", (o5,))
        self.assertEqual([g[0] for g in self.claim(5)], [o3])
        self.assertEqual(self.orow(o4)[4], "not confirmed in 5 attempts")
        self.assertIsNotNone(self.orow(o4)[3])
        self.assertIsNone(self.orow(o5)[3])                                       # still in its ten minutes
        # what the editors see
        st = self.call(STATE, uid=ADMIN)
        self.assertEqual(st[0][:4], (True, 2, 1, 2))                             # o3 and o5 wait; o1 sent; o2, o4 given up
        self.assertIsNotNone(st[0][4])
        self.assertEqual(st[0][5], "not confirmed in 5 attempts")              # the newest error of what is not sent
        self.assertEqual(self.warnings(), [])

    def test_state_is_for_editors(self):
        self.assertEqual(self.call(STATE, uid=ADMIN), [(False, 0, 0, 0, None, None)])
        self.assertEqual(self.call(STATE, uid=SUPER), [(False, 0, 0, 0, None, None)])
        self.assertIn("Only an editor", str(self.call(STATE)))
        self.assertIn("open to invited researchers", str(self.call(STATE, uid=READER)))
        self.assertIn("signed-in readers only", str(self.call(STATE, uid=None)))
        self.assertIn("permission denied", str(self.call(STATE, role="anon", uid=None)))
        self.mail_on()
        self.put()
        oid = self.put(user_id=RES2)
        self.pg.execute("UPDATE corner.outbox SET sent_at = now() - interval '2 days', last_error = 'old' WHERE id = %s", (oid,))
        mail_on, waiting, today, failed, last, err = self.call(STATE, uid=ADMIN)[0]
        self.assertEqual((mail_on, waiting, today, failed, err), (True, 1, 0, 0, None))   # an error since sent: not shown
        self.assertIsNotNone(last)

    # ---- the site's side

    def test_prefs(self):
        for sql in (PREFS, "SELECT public.corner_mail_prefs_set(false, false)"):
            with self.subTest(sql=sql):
                self.assertIn("permission denied", str(self.call(sql, role="anon", uid=None)))
                self.assertIn("signed-in readers only", str(self.call(sql, uid=None)))
                self.assertIn("open to invited researchers", str(self.call(sql, uid=READER)))
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.mail_prefs").fetchone()[0], 0)
        self.assertEqual(self.call(PREFS), [(True, True, False, False, None)])
        self.assertEqual(self.call(PREFS, uid=ADMIN), [(True, True, False, True, None)])
        self.assertEqual(self.call(PREFS, uid=SUPER), [(True, True, False, True, FROM)])   # the From: the super admin's
        self.assertEqual(self.call(PREFS_SET, (False, None)), [(True,)])
        self.assertEqual(self.call(PREFS), [(False, True, False, False, None)])
        self.assertEqual(self.call(PREFS_SET, (None, False)), [(True,)])
        self.assertEqual(self.call(PREFS), [(False, False, False, False, None)])   # on_queue stored, unused
        self.assertEqual(self.call(PREFS_SET, (None, None)), [(True,)])
        self.assertEqual(self.call(PREFS), [(False, False, False, False, None)])
        self.assertEqual(self.call(PREFS_SET, (True, True)), [(True,)])
        self.assertEqual(self.call(PREFS_SET, (None, False), uid=RES2), [(True,)])
        rows = self.pg.execute("SELECT user_id::text, on_my_requests, on_queue FROM corner.mail_prefs ORDER BY 1").fetchall()
        self.assertEqual(rows, [(RES, True, True), (RES2, True, False)])
        self.mail_on()
        self.assertEqual(self.call(PREFS)[0][2], True)
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")       # the corpus closed to researchers
        self.assertIn("ERROR", str(self.call(PREFS)))
        self.assertEqual(self.call(PREFS, uid=ADMIN)[0][3], True)

    def test_invite(self):
        iid, tok = self.invite()
        self.assertIn("Email is off", str(self.call(INVITE, (iid, tok), uid=SUPER)))
        self.mail_on()
        for uid in (ADMIN, RES, None):
            with self.subTest(uid=uid):
                self.assertIn("Only the super admin sends invitations", str(self.call(INVITE, (iid, tok), uid=uid)))
        self.assertIn("permission denied", str(self.call(INVITE, (iid, tok), role="anon", uid=None)))
        iid2, tok2 = self.invite("second@example.org", None)
        for bad_id, bad_tok in ((iid, "f" * 64), (iid, "xyz"), (iid, None), (iid, tok.upper()), (str(uuid.uuid4()), tok),
                                (iid, tok2), (iid2, tok), (None, tok)):
            with self.subTest(invite=bad_id, token=bad_tok):
                self.assertIn("not a pending invitation", str(self.call(INVITE, (bad_id, bad_tok), uid=SUPER)))
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.outbox").fetchone()[0], 0)
        self.assertEqual(self.call(INVITE, (iid, tok), uid=SUPER), [("queued",)])
        rows = self.pg.execute("SELECT kind, user_id, to_email, request_id, invite_id::text, subject, body, attempts "
                               "FROM corner.outbox").fetchall()
        until = self.pg.execute("SELECT to_char(expires_at AT TIME ZONE 'Asia/Kolkata', 'FMDD FMMonth YYYY, HH24:MI') "
                                "FROM rbac.invites WHERE id = %s", (iid,)).fetchone()[0]
        self.assertEqual(rows, [("invite", None, "new@example.org", None, iid,
                                 "An invitation to the Srangam working corpus", body(
            "You are invited to work with the Srangam working corpus as a researcher.", "",
            "To accept, open this link and sign in (or create an account) with this email address, new@example.org:",
            SITE + "/invite/" + tok, "",
            "The link works once, until " + until + " India time.", "",
            "A note with the invitation:", "Welcome to the corpus.", "",
            "If you did not expect this email, you can ignore it."), 0)])
        # asked again: still one open email for it, its body replaced and its attempts counted afresh
        self.assertEqual([g[0] for g in self.claim(1)], [1])
        self.done(1, False, None, "HTTP 500")
        self.assertEqual(self.call(INVITE, (iid, tok), uid=SUPER), [("queued",)])
        self.assertEqual(self.pg.execute("SELECT id, attempts, last_error FROM corner.outbox").fetchall(), [(1, 0, None)])
        self.assertEqual(self.call(INVITE, (iid2, tok2), uid=SUPER), [("queued",)])
        b2 = self.pg.execute("SELECT body FROM corner.outbox WHERE invite_id = %s", (iid2,)).fetchone()[0]
        self.assertNotIn("A note", b2)
        self.assertIn(" India time.\n\nIf you did not expect", b2)
        got = self.claim(5)
        self.assertEqual([(g[0], g[1], g[2], g[4]) for g in got],
                         [(1, "new@example.org", FROM, "An invitation to the Srangam working corpus"),
                          (3, "second@example.org", FROM, "An invitation to the Srangam working corpus")])
        self.assertIn(SITE + "/invite/" + tok, got[0][5])
        self.assertEqual(self.done(1, True, "re_1", None), True)
        self.assertEqual(self.orow(1)[6], "(sent; the link is not kept)")
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.outbox WHERE body LIKE %s",
                                         ("%" + tok + "%",)).fetchone()[0], 0)
        self.assertEqual(self.call(INVITE, (iid, tok), uid=SUPER), [("queued",)])   # sent once: a new email
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corner.outbox WHERE invite_id = %s", (iid,)).fetchone()[0], 2)
        ev = self.pg.execute("SELECT actor::text, detail FROM corner.events WHERE action = 'mail_invite' ORDER BY id").fetchall()
        self.assertEqual(ev[0], (SUPER, {"invite": iid}))
        # an invitation that is no longer pending: refused, and its open email is given up, not sent
        self.assertEqual(self.call("SELECT public.research_invite_revoke(%s)", (iid2,), uid=SUPER), [(True,)])
        self.assertIn("not a pending invitation", str(self.call(INVITE, (iid2, tok2), uid=SUPER)))
        self.pg.execute("UPDATE corner.outbox SET claimed_at = now() - interval '11 minutes' WHERE id = 3")
        self.assertEqual([g[0] for g in self.claim(5)], [4])                      # the new one for iid
        att, claimed, sent, failed, err, prov, text = self.orow(3)
        self.assertEqual((sent, err, text), (None, "the invitation is no longer pending", "(not sent; the link is not kept)"))
        self.assertIsNotNone(failed)
        self.pg.execute("UPDATE rbac.invites SET expires_at = now() - interval '1 minute' WHERE id = %s", (iid,))
        self.assertIn("not a pending invitation", str(self.call(INVITE, (iid, tok), uid=SUPER)))
        self.pg.execute("UPDATE rbac.invites SET expires_at = now() + interval '1 day', accepted_at = now() WHERE id = %s",
                        (iid,))
        self.assertIn("not a pending invitation", str(self.call(INVITE, (iid, tok), uid=SUPER)))
        # given up after five attempts: the link is not kept either
        iid3, tok3 = self.invite("third@example.org", None)
        self.call(INVITE, (iid3, tok3), uid=SUPER)
        o = self.pg.execute("SELECT id FROM corner.outbox WHERE invite_id = %s", (iid3,)).fetchone()[0]
        self.pg.execute("UPDATE corner.outbox SET attempts = 4 WHERE id = %s", (o,))
        self.assertEqual([g[0] for g in self.claim(5)], [o])
        self.done(o, False, None, "HTTP 403")
        self.assertEqual(self.orow(o)[6], "(not sent; the link is not kept)")
        self.pg.execute("UPDATE corner.settings SET value = '' WHERE key = 'site_url'")
        iid4, tok4 = self.invite("fourth@example.org", None)
        self.assertIn("site_url: not set", str(self.call(INVITE, (iid4, tok4), uid=SUPER)))

    def test_settings_set(self):
        self.assertIn("Only the super admin changes", str(self.call(SET, ("mail_enabled", "true"), uid=ADMIN)))
        self.assertIn("Only the super admin changes", str(self.call(SET, ("mail_enabled", "true"))))
        self.assertIn("open to invited researchers", str(self.call(SET, ("mail_enabled", "true"), uid=READER)))
        good = [("mail_enabled", "true"), ("mail_enabled", "false"), ("mail_from", FROM),
                ("mail_from", "The Srangam editors <editors@mail.nartiang.org>"), ("mail_from", "x" * 60 + " <a@b.co>"),
                ("mail_reply_to", "dhruv.rakesh@gmail.com"), ("mail_reply_to", ""),
                ("site_url", "https://localhost:8443"), ("site_url", SITE)]
        bad = [("mail_enabled", v, "mail_enabled: true or false") for v in ("yes", "TRUE", "", " true", None)] + \
              [("mail_from", v, "mail_from: a name and an address") for v in (
                  "desk@nartiang.org", "<desk@nartiang.org>", " <desk@nartiang.org>", "Desk desk@nartiang.org",
                  "D<e>sk <desk@nartiang.org>", "Desk\n <desk@nartiang.org>", "Desk\t<desk@nartiang.org>",
                  "x" * 61 + " <a@b.co>", "Desk <desk@nartiang>", "Desk <desk@nartiang.org> ", "Desk <a@b@c.org>", None)] + \
              [("mail_reply_to", v, "mail_reply_to: empty, or one address") for v in (
                  FROM, "desk", " desk@nartiang.org", "a@b", "a" * 250 + "@b.org", None)] + \
              [("site_url", v, "site_url: https:// and the site's host") for v in (
                  "http://srangam.nartiang.org", SITE + "/", "https://Srangam.nartiang.org", SITE + "/corpus",
                  SITE + ":x", "https://", "", None, "https://srangam.nartiang.org?x=1")]
        for key, value in good:
            with self.subTest(key=key, value=value):
                self.assertEqual(self.call(SET, (key, value), uid=SUPER), [(value,)])
                self.assertEqual(self.pg.execute("SELECT value, updated_by::text FROM corner.settings WHERE key = %s",
                                                 (key,)).fetchone(), (value, SUPER))
        before = self.pg.execute("SELECT key, value FROM corner.settings ORDER BY key").fetchall()
        for key, value, want in bad:
            with self.subTest(key=key, value=value):
                self.assertIn(want, str(self.call(SET, (key, value), uid=SUPER)))
        self.assertEqual(self.pg.execute("SELECT key, value FROM corner.settings ORDER BY key").fetchall(), before)
        n = self.pg.execute("SELECT count(*) FROM corner.events WHERE action = 'setting'").fetchone()[0]
        self.assertEqual(n, len(good))
        self.pg.execute("DELETE FROM corner.settings WHERE key = 'site_url'")    # a mail key that went missing comes back
        self.assertEqual(self.call(SET, ("site_url", SITE), uid=SUPER), [(SITE,)])
        self.assertEqual(self.pg.execute("SELECT value FROM corner.settings WHERE key = 'site_url'").fetchone()[0], SITE)

    def test_the_old_settings_behave_exactly_as_in_c9(self):
        """C9's own corner_settings_set (from the C9 file, renamed) and C12's, side by side."""
        text = C9F.read_text(encoding="utf-8")
        src = text[text.index("CREATE OR REPLACE FUNCTION public.corner_settings_set("):]
        src = src[:src.index("END $$;") + len("END $$;")]
        self.pg.execute(src.replace("public.corner_settings_set(", "public.corner_settings_set_c9(", 1))
        self.pg.execute("GRANT EXECUTE ON FUNCTION public.corner_settings_set_c9(text, text) TO authenticated")
        try:
            cases = [(k, v) for k in ("daily_cap_usd",) for v in ("1.00", "0", "50", "50.01", "99", "1.234", "abc", "",
                                                                  " 1", "1.5", None)] + \
                    [("researchers_need_approval", v) for v in ("true", "false", "True", "", None)] + \
                    [("max_pending_per_person", v) for v in ("1", "200", "0", "201", "abc", "05", None)] + \
                    [(k, "x") for k in ("nope", "", None)]
            for key, value in cases:
                for uid in (SUPER, ADMIN, RES):
                    with self.subTest(key=key, value=value, uid=uid):
                        out = []
                        for fn in ("corner_settings_set", "corner_settings_set_c9"):
                            reset_settings(self.pg)
                            self.pg.execute("DELETE FROM corner.events")
                            r = self.call("SELECT public.%s(%%s, %%s)" % fn, (key, value), uid=uid)
                            out.append((r, self.pg.execute("SELECT key, value, updated_by FROM corner.settings "
                                                           "ORDER BY key").fetchall(),
                                        self.pg.execute("SELECT action, detail FROM corner.events").fetchall()))
                        self.assertEqual(out[0], out[1])
        finally:
            self.pg.execute("DROP FUNCTION public.corner_settings_set_c9(text, text)")

    # ---- the files

    def test_the_files(self):
        for f in (C12, C12_CHECKS, Path(__file__)):
            with self.subTest(f=f.name):
                f.read_bytes().decode("ascii")
        sql = C12.read_text(encoding="ascii")
        self.assertIn("CORNER_MAIL_C12_2026_10_09", sql)
        self.assertIn("RESEND_API_KEY", sql)
        self.assertIn("\nBEGIN;\n", sql)
        self.assertIn("\nCOMMIT;\n", sql)
        self.assertNotIn("RESEND_API_KEY", re.sub(r"(?m)^--.*$", "", sql))     # only named in the header
        checks = C12_CHECKS.read_text(encoding="ascii")
        queries = [q.strip() for q in re.sub(r"(?m)^\s*--.*$", "", checks).split(";") if q.strip()]
        self.assertEqual(len(queries), 6)                                         # P1, V1, V2, V3, D1, D2
        self.mail_on()
        self.ask("story_mine", "nil", {"max": 2})
        out = []
        for q in queries:
            with self.pg.transaction(force_rollback=True):
                self.pg.execute("SET TRANSACTION READ ONLY")
                cur = self.pg.execute(q)
                out.append(([d.name for d in cur.description], cur.fetchall()))
        p1, v1, v2, v3, d1, d2 = out
        self.assertEqual(p1[1], [(True, True, True, True, True, "settings_key_check", False)])
        self.assertEqual([r[:2] for r in v1[1]], [("mail_prefs", True), ("outbox", True)])
        self.assertTrue(all(not any(r[2:]) for r in v1[1]))
        self.assertEqual(len(v2[1]), 10)
        self.assertTrue(all(r[5] is False for r in v2[1]))                       # anon: nothing
        self.assertEqual([r[:3] for r in v3[1] if r[0] == "trigger"], [("trigger", "corner_requests_mail", "O")])
        self.assertIn(("setting", "mail_enabled", "true"), [r[:3] for r in v3[1]])
        self.assertEqual(d1[1], [("request_pending", 2, 0, 0, None)])
        self.assertEqual(d2[0], ["id", "kind", "request_id", "created_at", "sent_at", "failed_at", "attempts", "last_error"])
        for cols, _rows in (d1, d2):
            self.assertFalse({"to_email", "body", "subject", "user_id"} & set(cols))


class _TruncateTheOutboxToo(object):
    """The old classes' setUp truncates corner.requests, which corner.outbox (C12) references: the
    outbox and the choices go in the same TRUNCATE. Everything else reaches the connection as it is."""

    def __init__(self, pg):
        self._pg = pg

    def execute(self, sql, *args, **kw):
        if isinstance(sql, str) and sql.startswith("TRUNCATE corner.requests"):
            sql = "TRUNCATE corner.outbox, corner.mail_prefs, " + sql[len("TRUNCATE "):]
        return self._pg.execute(sql, *args, **kw)

    def __getattr__(self, name):
        return getattr(self._pg, name)


class _OnTopOfC12(object):
    MAIL_ON = False

    @classmethod
    def apply_c12(cls):
        cls.pg.execute(C10A.read_text(encoding="utf-8"))                         # C12 comes after C10a
        cls.pg.execute(C12.read_text(encoding="utf-8"))
        cls.pg.execute(C12.read_text(encoding="utf-8"))
        assert cls.pg.execute("SELECT count(*) FROM pg_trigger WHERE tgname = 'corner_requests_mail'").fetchone()[0] == 1
        assert cls.pg.execute("SELECT to_regprocedure('public.corner_mail_claim(integer)')").fetchone()[0]
        watch_notices(cls)
        cls.queued = 0

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.MAIL_ON and cls.queued == 0:
                raise AssertionError("mail was on, yet the old tests queued no email: the trigger did not run")
            if not cls.MAIL_ON and cls.queued:
                raise AssertionError("mail was off, yet %d emails were queued" % cls.queued)
        finally:
            super().tearDownClass()

    def setUp(self):
        self.pg = _TruncateTheOutboxToo(type(self).pg)
        try:
            super().setUp()
        finally:
            del self.pg
        reset_settings(self.pg, self.MAIL_ON)       # the old setUp gives every key it does not know '20'
        del self.notices[:]

    def tearDown(self):
        type(self).queued += self.pg.execute("SELECT count(*) FROM corner.outbox").fetchone()[0]
        self.assertEqual(c12_warnings(self.notices), [])                        # the trigger composed every email
        super().tearDown()


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C9WithC12(_OnTopOfC12, c9.Corner):
    """Every test of tests/test_corner_pg_2026_10_09.py again, with C10a and C12 on top of C9; mail off."""

    @classmethod
    def setUpClass(cls):
        refuse_live()
        super().setUpClass()
        cls.apply_c12()


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C9WithC12MailOn(C9WithC12):
    """The same, with mail on: the trigger queues emails all along, and no request notices."""
    MAIL_ON = True


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C10aWithC12(_OnTopOfC12, c10a.CornerState):
    """Every test of tests/test_corner_state_pg_2026_10_09.py's CornerState again, with C12 on top; mail off."""

    @classmethod
    def setUpClass(cls):
        refuse_live()
        super().setUpClass()
        cls.apply_c12()


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class C10aWithC12MailOn(C10aWithC12):
    """The same, with mail on."""
    MAIL_ON = True


if __name__ == "__main__":
    unittest.main()
