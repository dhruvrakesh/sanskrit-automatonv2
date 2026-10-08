-- ============================================================
-- C7 - roles for Srangam: one super admin, invited researchers (RBAC_RESEARCHERS_2026_10_08)
-- STEP 3 of 4. The order (docs/cloud/C7_checks_2026-10-08.sql, one query per paste):
--   1. Preflight P1-P7.  2. C7a ALONE, then V0 as a separate run.  3. THIS FILE, whole, in one
--   paste.  4. Verify V1-V7.
-- This file is one transaction: if any statement fails, nothing in it is kept. It refuses to run
-- (and changes nothing) until C7a's two values are committed, and until C5 is in place.
--
-- The roles (public.app_role, rows in public.user_roles, checked by public.has_role):
--   super_admin  dhruv.rakesh@gmail.com (granted below). Invites researchers, removes them, sets
--                who may read the working corpus, and is the only role that may write
--                public.user_roles from the site. Keeps the 'admin' row too, so every existing
--                admin policy (role = 'admin') still lets this account through.
--   admin        unchanged: the admin pages, drafts and candidates among the stories.
--   researcher   NEW. An invited fellow researcher. Reads the working corpus (/corpus, Stories,
--                Names, search) in mode 'signed_in' and in mode 'readers'; not in mode 'admins'.
--                Sees approved stories, like every reader.
--   moderator, user  unchanged (unused).
--
-- Invitations (schema rbac, not exposed through the API; RLS on, no policies, nothing granted):
--   - The super admin makes one at /admin/researchers: an email, an optional note, 1-90 days.
--   - The function returns a link token ONCE. The table keeps only its SHA-256, so a database
--     reader cannot rebuild a link. Making a new invitation for the same email voids the old one.
--   - The researcher opens /invite/<token>, signs in or creates an account WITH THAT EMAIL, and
--     accepts. Acceptance needs the account's email to match the invitation and to be confirmed;
--     it then adds the role 'researcher'. A link works once, for one email, until it expires.
--   - Every invitation, acceptance, revocation, mode change and role change is written to
--     rbac.audit. Role changes are caught by a trigger on public.user_roles, so a change made in
--     this SQL editor is recorded as well (with no actor).
--
-- The reader gate: public.corpus_reader_allowed() (from C5) is replaced with the same rule plus
-- two clauses: a super_admin may always read, and in mode 'readers' a researcher may read (as a
-- user on corpus.readers already could). The mode itself is NOT changed here: it stays what it is
-- (signed_in) until the super admin sets it on /admin/researchers or runs step C below.
--
-- The one tightening: the policy "Only admins can manage roles" on public.user_roles (FOR ALL)
-- becomes "Only super admins can manage roles". "Admins can view all roles" (SELECT) stays. No
-- site code writes user_roles; the SQL editor is not affected by policies. Skipped with a NOTICE
-- if the editor's role does not own public.user_roles (then nothing about the policy changes).
--
-- Functions (SECURITY DEFINER, search_path ''): for signed-in callers, each checks the caller
-- again; peek is the only one an anonymous visitor may call.
--   my_roles()                                   the caller's own roles, text[] (no one else's)
--   is_super_admin()                             boolean
--   research_invite_create(p_email, p_note, p_days)  super admin: (invite_id, email, token, expires_at, reissued)
--   research_invites_list(k)                     super admin: the invitations, newest first, with status
--   research_invite_revoke(p_id)                 super admin: void a pending invitation
--   research_invite_peek(p_token)                anyone: status, masked email, expiry, is it for the caller
--   research_invite_accept(p_token)              signed in: 'accepted' | 'already_accepted' | 'used' |
--                                                'revoked' | 'expired' | 'wrong_email' | 'unconfirmed' | 'invalid'
--   rbac_members_list()                          super admin: everyone with a role or on corpus.readers
--   researcher_remove(p_user)                    super admin: take the role 'researcher' away
--   rbac_audit_list(k)                           super admin: the audit log, newest first
--   corpus_access_mode()                         super admin: corpus.reader_access.mode
--   corpus_access_mode_set(p_mode)               super admin: 'signed_in' | 'readers' | 'admins'
--
-- Needs C5 (corpus.reader_access, corpus.readers, corpus_reader_allowed) and C7a.
-- All-or-nothing: one transaction. Re-running it changes nothing (IF NOT EXISTS, OR REPLACE,
-- ON CONFLICT DO NOTHING).
--
-- Rollback (in this order, one paste):
--   DROP POLICY IF EXISTS "Only super admins can manage roles" ON public.user_roles;
--   DROP POLICY IF EXISTS "Only admins can manage roles" ON public.user_roles;
--   CREATE POLICY "Only admins can manage roles" ON public.user_roles FOR ALL TO authenticated
--     USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));
--   DROP FUNCTION IF EXISTS public.my_roles(), public.is_super_admin(),
--     public.research_invite_create(text, text, integer), public.research_invites_list(integer),
--     public.research_invite_revoke(uuid), public.research_invite_peek(text),
--     public.research_invite_accept(text), public.rbac_members_list(), public.researcher_remove(uuid),
--     public.rbac_audit_list(integer), public.corpus_access_mode(), public.corpus_access_mode_set(text);
--   DROP SCHEMA rbac CASCADE;              -- the invitations, the audit log, the trigger
--   DELETE FROM public.user_roles WHERE role IN ('super_admin', 'researcher');
--   then re-run the CREATE OR REPLACE FUNCTION public.corpus_reader_allowed() block of C5.
--
-- Tested 2026-10-08 on PostgreSQL 16 with stand-ins for auth.users, auth.uid() and has_role()
-- (tests/test_rbac_researchers_pg_2026_10_08.py).
-- ============================================================

BEGIN;

-- 0. Preconditions: C7a ran, C5 ran.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                 JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE n.nspname = 'public' AND t.typname = 'app_role' AND e.enumlabel = 'super_admin')
     OR NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'app_role' AND e.enumlabel = 'researcher') THEN
    RAISE EXCEPTION 'C7: run C7a first, on its own (app_role has no super_admin or researcher yet).';
  END IF;
  IF to_regclass('corpus.reader_access') IS NULL OR to_regclass('corpus.readers') IS NULL THEN
    RAISE EXCEPTION 'C7: needs C5 (corpus.reader_access and corpus.readers are missing).';
  END IF;
END $$;

-- 1. The private schema: invitations and the audit log.
CREATE SCHEMA IF NOT EXISTS rbac;
COMMENT ON SCHEMA rbac IS 'Srangam RBAC: research invitations and the role audit log (RBAC_RESEARCHERS_2026_10_08). Not exposed; read through public functions.';

CREATE TABLE IF NOT EXISTS rbac.invites (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        TEXT NOT NULL CHECK (email = lower(btrim(email)) AND length(email) <= 254),
    role         public.app_role NOT NULL DEFAULT 'researcher' CHECK (role = 'researcher'),
    token_hash   TEXT NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    note         TEXT CHECK (note IS NULL OR length(note) <= 500),
    invited_by   UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    accepted_at  TIMESTAMPTZ,
    accepted_by  UUID,
    revoked_at   TIMESTAMPTZ,
    revoked_by   UUID
);
-- At most one open invitation per email (a new one voids the old one first).
CREATE UNIQUE INDEX IF NOT EXISTS rbac_invites_one_open ON rbac.invites (email)
    WHERE accepted_at IS NULL AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS rbac_invites_created ON rbac.invites (created_at DESC);

CREATE TABLE IF NOT EXISTS rbac.audit (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor         UUID,
    action        TEXT NOT NULL,
    target_user   UUID,
    target_email  TEXT,
    detail        JSONB
);
CREATE INDEX IF NOT EXISTS rbac_audit_at ON rbac.audit (at DESC);

DO $$
DECLARE t text;
BEGIN
  REVOKE ALL ON SCHEMA rbac FROM PUBLIC;
  FOREACH t IN ARRAY ARRAY['invites', 'audit'] LOOP
    EXECUTE format('ALTER TABLE rbac.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON rbac.%I FROM PUBLIC', t);
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON SCHEMA rbac FROM anon;
    REVOKE ALL ON rbac.invites, rbac.audit FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON SCHEMA rbac FROM authenticated;
    REVOKE ALL ON rbac.invites, rbac.audit FROM authenticated;
  END IF;
END $$;

-- 2. Helpers (the owner's only).
CREATE OR REPLACE FUNCTION rbac._token_hash(p_token text)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT encode(sha256(convert_to(p_token, 'UTF8')), 'hex')
$$;

CREATE OR REPLACE FUNCTION rbac._mask_email(p_email text)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT CASE WHEN p_email IS NULL OR position('@' in p_email) < 2 THEN NULL
              ELSE left(p_email, 1) || '***' || substr(p_email, position('@' in p_email)) END
$$;

CREATE OR REPLACE FUNCTION rbac._status(p_accepted timestamptz, p_revoked timestamptz, p_expires timestamptz)
RETURNS text LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT CASE WHEN p_accepted IS NOT NULL THEN 'accepted'
              WHEN p_revoked IS NOT NULL THEN 'revoked'
              WHEN p_expires <= now() THEN 'expired'
              ELSE 'pending' END
$$;

CREATE OR REPLACE FUNCTION rbac._require_super()
RETURNS uuid LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE v uuid := auth.uid();
BEGIN
  IF v IS NULL OR NOT coalesce(public.has_role(v, 'super_admin'::public.app_role), false) THEN
    RAISE EXCEPTION 'Only the super admin may do this.' USING ERRCODE = '42501';
  END IF;
  RETURN v;
END $$;

-- Every change to public.user_roles, from the site or from this editor.
CREATE OR REPLACE FUNCTION rbac._log_role_change()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO rbac.audit (actor, action, target_user, target_email, detail)
    VALUES (auth.uid(), 'role_granted', NEW.user_id,
            (SELECT u.email::text FROM auth.users u WHERE u.id = NEW.user_id),
            jsonb_build_object('role', NEW.role::text));
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO rbac.audit (actor, action, target_user, target_email, detail)
    VALUES (auth.uid(), 'role_revoked', OLD.user_id,
            (SELECT u.email::text FROM auth.users u WHERE u.id = OLD.user_id),
            jsonb_build_object('role', OLD.role::text));
    RETURN OLD;
  END IF;
  IF NEW.role IS DISTINCT FROM OLD.role OR NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    INSERT INTO rbac.audit (actor, action, target_user, target_email, detail)
    VALUES (auth.uid(), 'role_changed', NEW.user_id,
            (SELECT u.email::text FROM auth.users u WHERE u.id = NEW.user_id),
            jsonb_build_object('from', OLD.role::text, 'to', NEW.role::text, 'from_user', OLD.user_id));
  END IF;
  RETURN NEW;
END $$;

-- 3. Who may write roles from the site, and the role audit trigger. Both need the editor's role
--    to own public.user_roles; otherwise both are skipped with a NOTICE (nothing else depends on them).
DO $$
DECLARE owner_ok boolean;
BEGIN
  SELECT pg_has_role(current_user, c.relowner, 'USAGE') INTO owner_ok
  FROM pg_class c WHERE c.oid = 'public.user_roles'::regclass;
  IF NOT coalesce(owner_ok, false) THEN
    RAISE NOTICE 'C7: % does not own public.user_roles: the policy and the audit trigger were left as they are.', current_user;
    RETURN;
  END IF;
  EXECUTE 'DROP POLICY IF EXISTS "Only admins can manage roles" ON public.user_roles';
  EXECUTE 'DROP POLICY IF EXISTS "Only super admins can manage roles" ON public.user_roles';
  EXECUTE $p$CREATE POLICY "Only super admins can manage roles" ON public.user_roles
             FOR ALL TO authenticated
             USING (public.has_role(auth.uid(), 'super_admin'::public.app_role))
             WITH CHECK (public.has_role(auth.uid(), 'super_admin'::public.app_role))$p$;
  EXECUTE 'DROP TRIGGER IF EXISTS rbac_log_role_change ON public.user_roles';
  EXECUTE 'CREATE TRIGGER rbac_log_role_change AFTER INSERT OR UPDATE OR DELETE ON public.user_roles
           FOR EACH ROW EXECUTE FUNCTION rbac._log_role_change()';
END $$;

-- 4. The super admin (after the trigger, so the grant is in the audit log). Fails the whole file
--    if the account does not exist yet.
DO $$
DECLARE v uuid;
BEGIN
  SELECT u.id INTO v FROM auth.users u WHERE lower(u.email) = 'dhruv.rakesh@gmail.com';
  IF v IS NULL THEN
    RAISE EXCEPTION 'C7: no account with the email dhruv.rakesh@gmail.com in auth.users. Nothing was changed.';
  END IF;
  INSERT INTO public.user_roles (user_id, role, notes)
  VALUES (v, 'admin'::public.app_role, 'RBAC_RESEARCHERS_2026_10_08')
  ON CONFLICT (user_id, role) DO NOTHING;
  INSERT INTO public.user_roles (user_id, role, notes)
  VALUES (v, 'super_admin'::public.app_role, 'RBAC_RESEARCHERS_2026_10_08: the super admin')
  ON CONFLICT (user_id, role) DO NOTHING;
END $$;

-- 5. The reader gate: C5's rule, plus the super admin always, plus researchers in mode 'readers'.
CREATE OR REPLACE FUNCTION public.corpus_reader_allowed()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    coalesce(public.has_role(auth.uid(), 'admin'::public.app_role), false)
    OR coalesce(public.has_role(auth.uid(), 'super_admin'::public.app_role), false)
    OR coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins') = 'signed_in'
    OR (coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins') = 'readers'
        AND (EXISTS (SELECT 1 FROM corpus.readers r WHERE r.user_id = auth.uid())
             OR coalesce(public.has_role(auth.uid(), 'researcher'::public.app_role), false))))
$$;

-- 6. The site's functions.
CREATE OR REPLACE FUNCTION public.my_roles()
RETURNS text[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT coalesce(array_agg(r.role::text ORDER BY r.role::text), ARRAY[]::text[])
  FROM public.user_roles r WHERE r.user_id = auth.uid()
$$;

CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL
     AND coalesce(public.has_role(auth.uid(), 'super_admin'::public.app_role), false)
$$;

CREATE OR REPLACE FUNCTION public.research_invite_create(p_email text, p_note text DEFAULT NULL,
                                                         p_days integer DEFAULT 14)
RETURNS TABLE (invite_id uuid, email text, token text, expires_at timestamptz, reissued boolean)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE
  v_actor uuid := rbac._require_super();
  v_email text := lower(btrim(coalesce(p_email, '')));
  v_note  text := nullif(btrim(coalesce(p_note, '')), '');
  v_days  integer := coalesce(p_days, 14);
  v_token text;
  v_id    uuid;
  v_exp   timestamptz;
  v_prev  integer;
BEGIN
  IF length(v_email) > 254 OR v_email !~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' THEN
    RAISE EXCEPTION 'That is not an email address.' USING ERRCODE = '22023';
  END IF;
  IF v_days < 1 OR v_days > 90 THEN
    RAISE EXCEPTION 'An invitation lasts 1 to 90 days.' USING ERRCODE = '22023';
  END IF;
  IF v_note IS NOT NULL AND length(v_note) > 500 THEN
    RAISE EXCEPTION 'The note is at most 500 characters.' USING ERRCODE = '22023';
  END IF;
  IF EXISTS (SELECT 1 FROM auth.users u JOIN public.user_roles r ON r.user_id = u.id
             WHERE lower(u.email) = v_email AND r.role = 'researcher'::public.app_role) THEN
    RAISE EXCEPTION '% is already a researcher.', v_email USING ERRCODE = '23505';
  END IF;
  UPDATE rbac.invites i SET revoked_at = now(), revoked_by = v_actor
  WHERE i.email = v_email AND i.accepted_at IS NULL AND i.revoked_at IS NULL;
  GET DIAGNOSTICS v_prev = ROW_COUNT;
  v_token := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
  v_exp := now() + make_interval(days => v_days);
  INSERT INTO rbac.invites (email, role, token_hash, note, invited_by, expires_at)
  VALUES (v_email, 'researcher'::public.app_role, rbac._token_hash(v_token), v_note, v_actor, v_exp)
  RETURNING id INTO v_id;
  INSERT INTO rbac.audit (actor, action, target_email, detail)
  VALUES (v_actor, CASE WHEN v_prev > 0 THEN 'invite_reissued' ELSE 'invite_created' END, v_email,
          jsonb_build_object('invite', v_id, 'days', v_days, 'voided', v_prev));
  RETURN QUERY SELECT v_id, v_email, v_token, v_exp, v_prev > 0;
END $$;

CREATE OR REPLACE FUNCTION public.research_invites_list(k integer DEFAULT 200)
RETURNS TABLE (id uuid, email text, note text, status text, created_at timestamptz,
               expires_at timestamptz, accepted_at timestamptz, revoked_at timestamptz,
               invited_by_email text, accepted_by_email text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM rbac._require_super();
  RETURN QUERY
  SELECT i.id, i.email, i.note, rbac._status(i.accepted_at, i.revoked_at, i.expires_at),
         i.created_at, i.expires_at, i.accepted_at, i.revoked_at,
         (SELECT u.email::text FROM auth.users u WHERE u.id = i.invited_by),
         (SELECT u.email::text FROM auth.users u WHERE u.id = i.accepted_by)
  FROM rbac.invites i
  ORDER BY i.created_at DESC
  LIMIT least(greatest(coalesce(k, 200), 1), 1000);
END $$;

CREATE OR REPLACE FUNCTION public.research_invite_revoke(p_id uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_actor uuid := rbac._require_super(); v_email text;
BEGIN
  UPDATE rbac.invites i SET revoked_at = now(), revoked_by = v_actor
  WHERE i.id = p_id AND i.accepted_at IS NULL AND i.revoked_at IS NULL
  RETURNING i.email INTO v_email;
  IF v_email IS NULL THEN
    RETURN false;
  END IF;
  INSERT INTO rbac.audit (actor, action, target_email, detail)
  VALUES (v_actor, 'invite_revoked', v_email, jsonb_build_object('invite', p_id));
  RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.research_invite_peek(p_token text)
RETURNS TABLE (status text, email_hint text, expires_at timestamptz, role text, for_you boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE i rbac.invites%ROWTYPE;
BEGIN
  IF p_token IS NULL OR p_token !~ '^[0-9a-f]{64}$' THEN
    RETURN QUERY SELECT 'invalid'::text, NULL::text, NULL::timestamptz, NULL::text, NULL::boolean;
    RETURN;
  END IF;
  SELECT * INTO i FROM rbac.invites x WHERE x.token_hash = rbac._token_hash(p_token);
  IF NOT FOUND THEN
    RETURN QUERY SELECT 'invalid'::text, NULL::text, NULL::timestamptz, NULL::text, NULL::boolean;
    RETURN;
  END IF;
  RETURN QUERY SELECT rbac._status(i.accepted_at, i.revoked_at, i.expires_at), rbac._mask_email(i.email),
    i.expires_at, i.role::text,
    CASE WHEN auth.uid() IS NULL THEN NULL
         ELSE EXISTS (SELECT 1 FROM auth.users u WHERE u.id = auth.uid() AND lower(u.email) = i.email) END;
END $$;

CREATE OR REPLACE FUNCTION public.research_invite_accept(p_token text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_uid uuid := auth.uid();
  i rbac.invites%ROWTYPE;
  v_email text;
  v_confirmed timestamptz;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'Sign in to accept an invitation.' USING ERRCODE = '42501';
  END IF;
  IF p_token IS NULL OR p_token !~ '^[0-9a-f]{64}$' THEN
    RETURN 'invalid';
  END IF;
  SELECT * INTO i FROM rbac.invites x WHERE x.token_hash = rbac._token_hash(p_token) FOR UPDATE;
  IF NOT FOUND THEN
    RETURN 'invalid';
  END IF;
  IF i.accepted_at IS NOT NULL THEN
    RETURN CASE WHEN i.accepted_by = v_uid THEN 'already_accepted' ELSE 'used' END;
  END IF;
  IF i.revoked_at IS NOT NULL THEN
    RETURN 'revoked';
  END IF;
  IF i.expires_at <= now() THEN
    RETURN 'expired';
  END IF;
  SELECT lower(u.email), u.email_confirmed_at INTO v_email, v_confirmed FROM auth.users u WHERE u.id = v_uid;
  IF v_email IS DISTINCT FROM i.email THEN
    RETURN 'wrong_email';
  END IF;
  IF v_confirmed IS NULL THEN
    RETURN 'unconfirmed';
  END IF;
  INSERT INTO public.user_roles (user_id, role, created_by, notes)
  VALUES (v_uid, i.role, i.invited_by, 'research invitation ' || i.id::text)
  ON CONFLICT (user_id, role) DO NOTHING;
  UPDATE rbac.invites x SET accepted_at = now(), accepted_by = v_uid WHERE x.id = i.id;
  INSERT INTO rbac.audit (actor, action, target_user, target_email, detail)
  VALUES (v_uid, 'invite_accepted', v_uid, i.email, jsonb_build_object('invite', i.id));
  RETURN 'accepted';
END $$;

CREATE OR REPLACE FUNCTION public.rbac_members_list()
RETURNS TABLE (user_id uuid, email text, roles text[], since timestamptz, last_sign_in_at timestamptz,
               on_reader_list boolean, invited_by_email text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM rbac._require_super();
  RETURN QUERY
  WITH m AS (
    SELECT r.user_id AS uid FROM public.user_roles r
    UNION
    SELECT cr.user_id FROM corpus.readers cr
  ), x AS (
    SELECT m.uid, u.email::text AS email,
           coalesce((SELECT array_agg(r.role::text ORDER BY r.role::text) FROM public.user_roles r
                     WHERE r.user_id = m.uid), ARRAY[]::text[]) AS roles,
           (SELECT min(r.created_at) FROM public.user_roles r WHERE r.user_id = m.uid) AS since,
           u.last_sign_in_at,
           EXISTS (SELECT 1 FROM corpus.readers cr WHERE cr.user_id = m.uid) AS listed,
           (SELECT iu.email::text FROM rbac.invites i JOIN auth.users iu ON iu.id = i.invited_by
            WHERE i.accepted_by = m.uid ORDER BY i.accepted_at DESC LIMIT 1) AS inviter
    FROM m LEFT JOIN auth.users u ON u.id = m.uid
  )
  SELECT x.uid, x.email, x.roles, x.since, x.last_sign_in_at, x.listed, x.inviter
  FROM x
  ORDER BY ('super_admin' = ANY (x.roles)) DESC, ('admin' = ANY (x.roles)) DESC,
           ('researcher' = ANY (x.roles)) DESC, x.email NULLS LAST;
END $$;

CREATE OR REPLACE FUNCTION public.researcher_remove(p_user uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE n integer;
BEGIN
  PERFORM rbac._require_super();
  DELETE FROM public.user_roles r WHERE r.user_id = p_user AND r.role = 'researcher'::public.app_role;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n > 0;   -- the trigger writes the audit row
END $$;

CREATE OR REPLACE FUNCTION public.rbac_audit_list(k integer DEFAULT 100)
RETURNS TABLE (at timestamptz, actor_email text, action text, target_email text, detail jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM rbac._require_super();
  RETURN QUERY
  SELECT a.at, (SELECT u.email::text FROM auth.users u WHERE u.id = a.actor), a.action, a.target_email, a.detail
  FROM rbac.audit a
  ORDER BY a.at DESC, a.id DESC
  LIMIT least(greatest(coalesce(k, 100), 1), 1000);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_access_mode()
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM rbac._require_super();
  RETURN coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins');
END $$;

CREATE OR REPLACE FUNCTION public.corpus_access_mode_set(p_mode text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_actor uuid := rbac._require_super(); v_old text;
BEGIN
  IF p_mode IS NULL OR p_mode NOT IN ('signed_in', 'readers', 'admins') THEN
    RAISE EXCEPTION 'The mode is signed_in, readers or admins.' USING ERRCODE = '22023';
  END IF;
  SELECT a.mode INTO v_old FROM corpus.reader_access a WHERE a.id FOR UPDATE;
  INSERT INTO corpus.reader_access (id, mode, updated_at) VALUES (true, p_mode, now())
  ON CONFLICT (id) DO UPDATE SET mode = EXCLUDED.mode, updated_at = now();
  IF v_old IS DISTINCT FROM p_mode THEN
    INSERT INTO rbac.audit (actor, action, detail)
    VALUES (v_actor, 'access_mode', jsonb_build_object('from', v_old, 'to', p_mode));
  END IF;
  RETURN p_mode;
END $$;

-- 7. Who may call what. Helpers: the owner only. Site functions: signed-in callers. Peek: anyone.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['rbac._token_hash(text)', 'rbac._mask_email(text)',
      'rbac._status(timestamptz, timestamptz, timestamptz)', 'rbac._require_super()',
      'rbac._log_role_change()',
      'public.my_roles()', 'public.is_super_admin()',
      'public.research_invite_create(text, text, integer)', 'public.research_invites_list(integer)',
      'public.research_invite_revoke(uuid)', 'public.research_invite_peek(text)',
      'public.research_invite_accept(text)', 'public.rbac_members_list()',
      'public.researcher_remove(uuid)', 'public.rbac_audit_list(integer)',
      'public.corpus_access_mode()', 'public.corpus_access_mode_set(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.my_roles(), public.is_super_admin(),
      public.research_invite_create(text, text, integer), public.research_invites_list(integer),
      public.research_invite_revoke(uuid), public.research_invite_peek(text),
      public.research_invite_accept(text), public.rbac_members_list(),
      public.researcher_remove(uuid), public.rbac_audit_list(integer),
      public.corpus_access_mode(), public.corpus_access_mode_set(text) TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION public.research_invite_peek(text) TO anon;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';

-- ============================================================
-- Checks: docs/cloud/C7_checks_2026-10-08.sql, V1-V7, one query per paste.
-- Closing the corpus to plain sign-ups is a separate, later decision (the end of that file, or the
-- switch on /admin/researchers once the first researcher has accepted).
-- ============================================================
