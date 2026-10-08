# -*- coding: ascii -*-
"""RBAC_RESEARCHERS_2026_10_08 against a real PostgreSQL: docs/cloud/C7a and C7 (the super admin,
research invitations, the audit log, the reader gate with researchers, the user_roles policy).
Applies the Supabase stand-ins, C4, C4b, C5, C7a, then C7 once WITHOUT the super admin's account
(it must change nothing), then C7 twice with it, and calls the functions as anon, as signed-in
users, as an admin and as the super admin.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_rbac_researchers_pg_2026_10_08
"""
import os, re, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
BASE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", REPO / "tests" / "supabase_stubs_rbac_2026_10_08.sql",
        CLOUD / "C4_corpus_mirror_2026-10-08.sql", CLOUD / "C4b_mirror_digests_2026-10-08.sql",
        CLOUD / "C5_corpus_reader_2026-10-08.sql", CLOUD / "C7a_rbac_roles_2026-10-08.sql"]
C7 = CLOUD / "C7_rbac_researchers_2026-10-08.sql"
SUPER = "aaaaaaaa-0000-0000-0000-000000000001"
ADMIN = "aaaaaaaa-0000-0000-0000-000000000002"
SCHOLAR = "aaaaaaaa-0000-0000-0000-000000000003"
LATE = "aaaaaaaa-0000-0000-0000-000000000004"
OTHER = "aaaaaaaa-0000-0000-0000-000000000005"
LISTED = "aaaaaaaa-0000-0000-0000-000000000006"
NEW_FUNCS = ["my_roles", "is_super_admin", "research_invite_create", "research_invites_list",
             "research_invite_revoke", "research_invite_peek", "research_invite_accept", "rbac_members_list",
             "researcher_remove", "rbac_audit_list", "corpus_access_mode", "corpus_access_mode_set"]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Rbac(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        x = cls.pg.execute
        x("DROP SCHEMA IF EXISTS rbac CASCADE")
        for f in NEW_FUNCS:
            x("DO $$ DECLARE p regprocedure; BEGIN FOR p IN SELECT oid::regprocedure FROM pg_proc "
              "WHERE proname = '%s' AND pronamespace = 'public'::regnamespace LOOP "
              "EXECUTE 'DROP FUNCTION ' || p; END LOOP; END $$" % f)
        for f in BASE:
            x(f.read_text(encoding="utf-8"))
        x("TRUNCATE public.user_roles, auth.users, corpus.readers")
        x("DROP POLICY IF EXISTS \"Only super admins can manage roles\" ON public.user_roles")
        # The super admin's account is not there yet: C7 must refuse and leave everything as it was.
        cls.first_error = None
        try:
            x(C7.read_text(encoding="utf-8"))
        except Exception as e:
            cls.first_error = str(e)
            x("ROLLBACK")
        cls.after_refusal = x(
            "SELECT to_regnamespace('rbac') IS NULL, to_regprocedure('public.my_roles()') IS NULL, "
            "(SELECT count(*) FROM pg_policies WHERE tablename = 'user_roles' "
            " AND policyname = 'Only admins can manage roles')").fetchone()
        users = [(SUPER, "Dhruv.Rakesh@gmail.com", True), (ADMIN, "editor@srangam.test", True),
                 (SCHOLAR, "scholar@uni.test", True), (LATE, "late@uni.test", False),
                 (OTHER, "someone@else.test", True), (LISTED, "listed@uni.test", True)]
        with cls.pg.cursor() as c:
            c.executemany("INSERT INTO auth.users (id, email, email_confirmed_at) VALUES "
                          "(%s, %s, CASE WHEN %s THEN now() END)", users)
        x("INSERT INTO public.user_roles (user_id, role) VALUES (%s, 'admin'), (%s, 'admin')", (SUPER, ADMIN))
        x("INSERT INTO corpus.readers (user_id, note) VALUES (%s, 'old list')", (LISTED,))
        x(C7.read_text(encoding="utf-8"))
        x(C7.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        x = self.pg.execute
        x("DELETE FROM rbac.invites")
        x("DELETE FROM public.user_roles WHERE role = 'researcher'")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")

    def call(self, sql, args=(), role="authenticated", uid=SUPER):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def commit_call(self, sql, args=(), uid=SUPER):
        """Like call, but keeps what the function wrote."""
        with self.pg.transaction():
            self.pg.execute("SET LOCAL ROLE authenticated")
            self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            return self.pg.execute(sql, args).fetchall()

    def invite(self, email, days=14, note=None):
        r = self.commit_call("SELECT invite_id, email, token, expires_at, reissued "
                             "FROM public.research_invite_create(%s, %s, %s)", (email, note, days))
        return r[0]

    # ---- applying it

    def test_refuses_without_the_super_admins_account_and_changes_nothing(self):
        self.assertIn("no account with the email dhruv.rakesh@gmail.com", self.first_error or "")
        self.assertEqual(self.after_refusal, (True, True, 1))

    def test_super_admin_granted_once_admin_kept_audit_and_policy(self):
        rows = self.pg.execute("SELECT role::text FROM public.user_roles WHERE user_id = %s ORDER BY 1",
                               (SUPER,)).fetchall()
        self.assertEqual([r[0] for r in rows], ["admin", "super_admin"])
        pol = dict(self.pg.execute("SELECT policyname, cmd FROM pg_policies WHERE tablename = 'user_roles'").fetchall())
        self.assertEqual(pol, {"Admins can view all roles": "SELECT", "Only super admins can manage roles": "ALL"})
        a = self.pg.execute("SELECT actor, action, target_email, detail->>'role' FROM rbac.audit "
                            "WHERE action = 'role_granted' AND target_user = %s", (SUPER,)).fetchall()
        self.assertEqual(a, [(None, "role_granted", "Dhruv.Rakesh@gmail.com", "super_admin")])

    def test_my_roles_and_is_super_admin(self):
        self.assertEqual(self.call("SELECT public.my_roles()"), [(["admin", "super_admin"],)])
        self.assertEqual(self.call("SELECT public.my_roles()", uid=OTHER), [([],)])
        self.assertEqual(self.call("SELECT public.is_super_admin()"), [(True,)])
        self.assertEqual(self.call("SELECT public.is_super_admin()", uid=ADMIN), [(False,)])
        self.assertIn("permission denied", self.call("SELECT public.my_roles()", role="anon", uid=None))

    def test_grants(self):
        r = self.pg.execute(
            "SELECT p.proname, has_function_privilege('anon', p.oid, 'EXECUTE'), "
            "has_function_privilege('authenticated', p.oid, 'EXECUTE') FROM pg_proc p "
            "WHERE p.pronamespace = 'public'::regnamespace AND p.proname = ANY(%s)", (NEW_FUNCS,)).fetchall()
        self.assertEqual(len(r), 12)
        for name, anon, auth in r:
            self.assertTrue(auth, name)
            self.assertEqual(anon, name == "research_invite_peek", name)
        r = self.pg.execute("SELECT p.proname, has_function_privilege('authenticated', p.oid, 'EXECUTE') "
                            "FROM pg_proc p WHERE p.pronamespace = 'rbac'::regnamespace").fetchall()
        self.assertEqual(len(r), 5)
        self.assertFalse(any(x[1] for x in r))
        self.assertIn("permission denied", self.call("SELECT * FROM rbac.invites"))
        self.assertIn("permission denied", self.call("SELECT * FROM rbac.audit", role="anon", uid=None))

    # ---- invitations

    def test_only_the_super_admin_invites_lists_revokes_and_sees_members(self):
        for uid in (ADMIN, OTHER, None):
            for sql in ("SELECT * FROM public.research_invite_create('x@y.test')",
                        "SELECT * FROM public.research_invites_list()", "SELECT public.research_invite_revoke(gen_random_uuid())",
                        "SELECT * FROM public.rbac_members_list()", "SELECT public.researcher_remove(gen_random_uuid())",
                        "SELECT * FROM public.rbac_audit_list()", "SELECT public.corpus_access_mode()",
                        "SELECT public.corpus_access_mode_set('readers')"):
                with self.subTest(uid=uid, sql=sql):
                    self.assertIn("Only the super admin may do this", self.call(sql, uid=uid))
        self.assertIn("permission denied",
                      self.call("SELECT * FROM public.research_invite_create('x@y.test')", role="anon", uid=None))

    def test_create_returns_a_token_once_and_stores_only_its_hash(self):
        iid, email, token, exp, reissued = self.invite("  Scholar@Uni.TEST ", days=7, note="Nirukta")
        self.assertEqual(email, "scholar@uni.test")
        self.assertRegex(token, r"^[0-9a-f]{64}$")
        self.assertFalse(reissued)
        row = self.pg.execute("SELECT token_hash, note, invited_by::text, expires_at - created_at FROM rbac.invites "
                              "WHERE id = %s", (iid,)).fetchone()
        self.assertNotEqual(row[0], token)
        self.assertEqual(row[0], self.pg.execute("SELECT encode(sha256(%s::bytea), 'hex')", (token,)).fetchone()[0])
        self.assertEqual(row[1:3], ("Nirukta", SUPER))
        self.assertEqual(row[3].days, 7)
        t2 = self.invite("scholar@uni.test")
        self.assertNotEqual(t2[2], token)
        self.assertTrue(t2[4])                                       # re-issued: the old link is void
        self.assertEqual(self.call("SELECT status FROM public.research_invite_peek(%s)", (token,), role="anon", uid=None),
                         [("revoked",)])
        acts = [r[0] for r in self.pg.execute("SELECT action FROM rbac.audit WHERE target_email = 'scholar@uni.test' "
                                              "ORDER BY id").fetchall()]
        self.assertEqual(acts[-2:], ["invite_created", "invite_reissued"])

    def test_create_validates(self):
        for args, msg in [(("not-an-email",), "not an email address"), (("a@b.test", None, 0), "1 to 90 days"),
                          (("a@b.test", None, 91), "1 to 90 days"), (("a@b.test", "x" * 501), "at most 500"),
                          (("a b@c.test",), "not an email address")]:
            with self.subTest(args=args):
                sql = "SELECT * FROM public.research_invite_create(%s" + ", %s" * (len(args) - 1) + ")"
                self.assertIn(msg, self.call(sql, args))
        tok = self.invite("scholar@uni.test")[2]
        self.assertEqual(self.commit_call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR), [("accepted",)])
        self.assertIn("already a researcher", self.call("SELECT * FROM public.research_invite_create('scholar@uni.test')"))

    def test_peek_for_anyone_masks_the_email(self):
        tok = self.invite("scholar@uni.test")[2]
        r = self.call("SELECT status, email_hint, role, for_you FROM public.research_invite_peek(%s)", (tok,),
                      role="anon", uid=None)
        self.assertEqual(r, [("pending", "s***@uni.test", "researcher", None)])
        self.assertEqual(self.call("SELECT for_you FROM public.research_invite_peek(%s)", (tok,), uid=SCHOLAR), [(True,)])
        self.assertEqual(self.call("SELECT for_you FROM public.research_invite_peek(%s)", (tok,), uid=OTHER), [(False,)])
        for bad in ("", "abc", tok.upper(), "0" * 64, None):
            with self.subTest(bad=bad):
                self.assertEqual(self.call("SELECT status, email_hint FROM public.research_invite_peek(%s)", (bad,),
                                           role="anon", uid=None), [("invalid", None)])

    def test_accept_needs_the_invited_confirmed_email_and_works_once(self):
        tok = self.invite("scholar@uni.test")[2]
        self.assertIn("Sign in to accept", self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=None))
        self.assertIn("permission denied", self.call("SELECT public.research_invite_accept(%s)", (tok,), role="anon", uid=None))
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=OTHER), [("wrong_email",)])
        self.assertEqual(self.call("SELECT public.research_invite_accept('nope')", uid=SCHOLAR), [("invalid",)])
        self.assertEqual(self.commit_call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR), [("accepted",)])
        self.assertEqual(self.call("SELECT public.my_roles()", uid=SCHOLAR), [(["researcher"],)])
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR), [("already_accepted",)])
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=OTHER), [("used",)])
        self.assertEqual(self.call("SELECT status FROM public.research_invite_peek(%s)", (tok,), role="anon", uid=None),
                         [("accepted",)])
        r = self.pg.execute("SELECT created_by::text, notes FROM public.user_roles WHERE user_id = %s AND role = 'researcher'",
                            (SCHOLAR,)).fetchone()
        self.assertEqual(r[0], SUPER); self.assertTrue(r[1].startswith("research invitation "))
        acts = [x[0] for x in self.pg.execute("SELECT action FROM rbac.audit WHERE target_user = %s ORDER BY id",
                                               (SCHOLAR,)).fetchall()]
        self.assertEqual(acts[-2:], ["role_granted", "invite_accepted"])
        late = self.invite("late@uni.test")[2]
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (late,), uid=LATE), [("unconfirmed",)])

    def test_expired_and_revoked(self):
        iid, _, tok, _, _ = self.invite("scholar@uni.test")
        self.pg.execute("UPDATE rbac.invites SET expires_at = now() - interval '1 minute' WHERE id = %s", (iid,))
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR), [("expired",)])
        self.assertEqual(self.call("SELECT status FROM public.research_invites_list()"), [("expired",)])
        iid, _, tok, _, _ = self.invite("scholar@uni.test")
        self.assertEqual(self.commit_call("SELECT public.research_invite_revoke(%s)", (iid,)), [(True,)])
        self.assertEqual(self.call("SELECT public.research_invite_revoke(%s)", (iid,)), [(False,)])
        self.assertEqual(self.call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR), [("revoked",)])
        r = self.call("SELECT email, status, invited_by_email, accepted_by_email FROM public.research_invites_list()")
        self.assertEqual([x[1] for x in r], ["revoked", "revoked"])  # re-issuing voided the expired one
        self.assertEqual(r[0][2], "Dhruv.Rakesh@gmail.com")

    # ---- the reader gate

    def test_reader_gate_by_mode(self):
        tok = self.invite("scholar@uni.test")[2]
        self.commit_call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR)
        allowed = lambda uid: self.call("SELECT public.corpus_reader_allowed()", uid=uid)[0][0]
        want = {"signed_in": {SUPER: True, ADMIN: True, SCHOLAR: True, LISTED: True, OTHER: True},
                "readers": {SUPER: True, ADMIN: True, SCHOLAR: True, LISTED: True, OTHER: False},
                "admins": {SUPER: True, ADMIN: True, SCHOLAR: False, LISTED: False, OTHER: False}}
        for mode, who in want.items():
            self.pg.execute("UPDATE corpus.reader_access SET mode = %s", (mode,))
            for uid, ok in who.items():
                with self.subTest(mode=mode, uid=uid):
                    self.assertEqual(allowed(uid), ok)
        self.assertEqual(self.call("SELECT public.corpus_reader_allowed()", uid=None), [(False,)])
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'readers'")
        self.assertIsInstance(self.call("SELECT * FROM public.corpus_reader_docs()", uid=SCHOLAR), list)
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corpus_reader_docs()", uid=OTHER))

    def test_access_mode_set_by_the_super_admin_and_audited(self):
        self.assertEqual(self.call("SELECT public.corpus_access_mode()"), [("signed_in",)])
        self.assertIn("signed_in, readers or admins", self.call("SELECT public.corpus_access_mode_set('everyone')"))
        self.assertEqual(self.commit_call("SELECT public.corpus_access_mode_set('readers')"), [("readers",)])
        self.assertEqual(self.pg.execute("SELECT mode FROM corpus.reader_access").fetchone()[0], "readers")
        a = self.pg.execute("SELECT actor::text, detail FROM rbac.audit WHERE action = 'access_mode' "
                            "ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(a, (SUPER, {"from": "signed_in", "to": "readers"}))

    # ---- people and roles

    def test_members_remove_and_audit_list(self):
        tok = self.invite("scholar@uni.test")[2]
        self.commit_call("SELECT public.research_invite_accept(%s)", (tok,), uid=SCHOLAR)
        r = self.call("SELECT email, roles, on_reader_list, invited_by_email FROM public.rbac_members_list()")
        self.assertEqual(r[0][:2], ("Dhruv.Rakesh@gmail.com", ["admin", "super_admin"]))
        self.assertEqual(r[1][:2], ("editor@srangam.test", ["admin"]))
        self.assertEqual(r[2], ("scholar@uni.test", ["researcher"], False, "Dhruv.Rakesh@gmail.com"))
        self.assertEqual(r[3], ("listed@uni.test", [], True, None))
        self.assertEqual(self.commit_call("SELECT public.researcher_remove(%s)", (SCHOLAR,)), [(True,)])
        self.assertEqual(self.call("SELECT public.researcher_remove(%s)", (SCHOLAR,)), [(False,)])
        self.assertEqual(self.call("SELECT public.my_roles()", uid=SCHOLAR), [([],)])
        a = self.call("SELECT actor_email, action, target_email, detail FROM public.rbac_audit_list(1)")
        self.assertEqual(a, [("Dhruv.Rakesh@gmail.com", "role_revoked", "scholar@uni.test", {"role": "researcher"})])
        self.assertEqual(len(self.call("SELECT * FROM public.rbac_audit_list(0)")), 1)    # k is at least 1

    def test_user_roles_writable_from_the_site_by_the_super_admin_only(self):
        ins = "INSERT INTO public.user_roles (user_id, role) VALUES ('%s', 'researcher') RETURNING role::text" % OTHER
        self.assertIn("row-level security", self.call(ins, uid=ADMIN))
        self.assertIn("row-level security", self.call(ins, uid=OTHER))
        self.assertEqual(self.call(ins, uid=SUPER), [("researcher",)])
        self.assertEqual(len(self.call("SELECT * FROM public.user_roles", uid=ADMIN)), 3)   # admins still see all three
        self.assertEqual(self.call("SELECT * FROM public.user_roles", uid=OTHER), [])


if __name__ == "__main__":
    unittest.main()
