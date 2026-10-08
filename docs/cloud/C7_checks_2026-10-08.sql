-- ============================================================
-- C7 checks (RBAC_RESEARCHERS_2026_10_08). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) and keep it: the P results are the "before" record and the exact rollback source.
--
-- The order:  P1-P7  ->  C7a alone  ->  V0  ->  C7 in one paste  ->  V1-V7.
-- ============================================================


-- ---------------- PREFLIGHT (before C7a) ----------------

-- P1 the roles type. Expect {admin,moderator,user}. If it already shows super_admin and
--    researcher, C7a has run: skip it.
SELECT enum_range(NULL::public.app_role);

-- P2 the super admin's account. Expect exactly 1 row with email_confirmed_at set.
SELECT id, email, email_confirmed_at FROM auth.users WHERE lower(email) = 'dhruv.rakesh@gmail.com';

-- P3 who holds a role now. Expect dhruv.rakesh@gmail.com | admin (and anyone else you know of).
SELECT u.email, r.role, r.created_at FROM public.user_roles r JOIN auth.users u ON u.id = r.user_id ORDER BY 1, 2;

-- P4 the policies on user_roles, with their expressions (the rollback source).
--    Expect "Admins can view all roles" (SELECT) and "Only admins can manage roles" (ALL).
SELECT policyname, cmd, roles, qual, with_check FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'user_roles' ORDER BY policyname;

-- P5 the table's owner and the editor's role. Expect postgres | postgres (C7 changes the policy and
--    adds the audit trigger only when they match; otherwise it skips both with a NOTICE).
SELECT pg_get_userbyid(c.relowner) AS owner, current_user FROM pg_class c WHERE c.oid = 'public.user_roles'::regclass;

-- P6 the reader gate as it is now (the rollback source for C7 section 5).
SELECT pg_get_functiondef('public.corpus_reader_allowed()'::regprocedure);

-- P7 the access mode, the old reader list, and no rbac schema yet.
--    Expect signed_in | <n> | true.
SELECT (SELECT mode FROM corpus.reader_access) AS mode,
       (SELECT count(*) FROM corpus.readers) AS on_reader_list,
       to_regnamespace('rbac') IS NULL AS no_rbac_yet;


-- ---------------- AFTER C7a (a separate run) ----------------

-- V0 expect {admin,moderator,user,super_admin,researcher}.
SELECT enum_range(NULL::public.app_role);


-- ---------------- AFTER C7 ----------------

-- V1 the roles. Expect dhruv.rakesh@gmail.com with admin AND super_admin.
SELECT u.email, r.role, r.created_at, r.notes FROM public.user_roles r JOIN auth.users u ON u.id = r.user_id ORDER BY 1, 2;

-- V2 the policies. Expect "Admins can view all roles" (SELECT) and "Only super admins can manage roles" (ALL).
SELECT policyname, cmd, qual FROM pg_policies WHERE schemaname = 'public' AND tablename = 'user_roles' ORDER BY policyname;

-- V3 who may call the new functions. Expect 12 rows; anon true ONLY for research_invite_peek;
--    authenticated true on all 12.
SELECT p.oid::regprocedure AS fn, has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname IN ('my_roles', 'is_super_admin', 'research_invite_create',
  'research_invites_list', 'research_invite_revoke', 'research_invite_peek', 'research_invite_accept',
  'rbac_members_list', 'researcher_remove', 'rbac_audit_list', 'corpus_access_mode', 'corpus_access_mode_set')
ORDER BY 1;

-- V4 the rbac schema is closed. Expect 4 rows, every privilege false.
SELECT r.rolname, t.tbl,
       has_table_privilege(r.rolname, t.tbl, 'SELECT') AS can_select,
       has_table_privilege(r.rolname, t.tbl, 'INSERT') AS can_insert
FROM (VALUES ('anon'), ('authenticated')) AS r(rolname)
CROSS JOIN (VALUES ('rbac.invites'), ('rbac.audit')) AS t(tbl) ORDER BY 1, 2;

-- V5 the audit trigger. Expect one row: rbac_log_role_change.
SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.user_roles'::regclass AND NOT tgisinternal;

-- V6 the audit log so far. Expect role_granted | dhruv.rakesh@gmail.com | {"role": "super_admin"} (no actor:
--    it came from the editor).
SELECT at, actor, action, target_email, detail FROM rbac.audit ORDER BY id;

-- V7 the mode is unchanged (C7 does not change it). Expect signed_in.
SELECT mode, updated_at FROM corpus.reader_access;


-- ---------------- LATER, ONLY AFTER THE FIRST RESEARCHER HAS ACCEPTED ----------------
-- Close the corpus to plain sign-ups (the same switch is on /admin/researchers, and is audited there;
-- this editor route is not audited):
-- UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();
-- Reopen:
-- UPDATE corpus.reader_access SET mode = 'signed_in', updated_at = now();
