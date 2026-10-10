-- ============================================================
-- C12 - email from the Researchers' Corner (CORNER_MAIL_C12_2026_10_09)
-- docs/RESEARCHERS_CORNER_2026-10-09.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C12_checks_2026-10-09.sql, one query per paste.
--
-- The order: after C10a (it refuses to run without it); independent of C10b (either may come first).
-- Mail stays OFF until the super admin turns it on (Corner -> Settings, which calls
-- corner_settings_set('mail_enabled', 'true')). While it is off nothing is queued and nothing is sent.
-- The database never sends anything and never holds a key: the corner-mail edge function claims the
-- queued emails as service_role and sends them through Resend. Its RESEND_API_KEY secret lives only in
-- Lovable Secrets and is read only by that edge function.
--
-- What it adds:
--   corner.settings      four keys more (the key CHECK settings_key_check is widened): mail_enabled
--                        'false', mail_from 'Srangam desk <desk@nartiang.org>', mail_reply_to '' (none),
--                        site_url 'https://srangam.nartiang.org' (the links in the emails).
--   corner.mail_prefs    each person's choice: email me when my requests finish (on_my_requests),
--                        and, for editors, when a researcher's request waits (on_queue). No row: both on.
--   corner.outbox        the emails waiting, sent or given up: to whom (an account, or an address for an
--                        invitation), the subject and the plain-text body, attempts and the last error.
--                        An invitation's body (it holds the link) is wiped once it is sent or given up.
--   the trigger corner_requests_mail on corner.requests (corner._mail_on_request()): with mail on,
--                        - a request that waits for an editor: one email to each editor (admin or super
--                          admin) but the one who asked, unless they turned on_queue off;
--                        - a paid request done, or any request failed: one email to the one who asked;
--                        - a waiting request rejected: one email to the one who asked (with the note);
--                        both unless they turned on_my_requests off. Short English plain text: what was
--                        asked, the text's title, the desk's message, the cost, the link to the Corner,
--                        and the line that says how to stop these emails. No story text.
--                        It never raises: a mail problem is a WARNING, and the request goes through.
--   public.corner_mail_prefs(), corner_mail_prefs_set(boolean, boolean)   the person's own choice
--   public.corner_mail_state()                     editors: is mail on, waiting, sent today, failed
--   public.corner_mail_invite(uuid, text)          the super admin: send an invitation's link by email
--   public.corner_mail_claim(integer), corner_mail_done(bigint, boolean, text, text)   service_role only:
--                        the corner-mail edge function takes up to 20 emails, then says how each went.
-- What it changes (CREATE OR REPLACE, the same signature and grants):
--   public.corner_settings_set  as in C9 for daily_cap_usd, researchers_need_approval and
--                        max_pending_per_person; it also takes the four mail keys, checked.
--
-- Needs C7 (rbac.invites), C9 and C10a. Re-running it changes nothing (the settings, the choices and
-- the queue are kept). A re-run of C9 puts C9's corner_settings_set back: run this file again after
-- any re-run of C9.
-- Rollback (one paste; the settings rows and the wider key CHECK can stay):
--   BEGIN;
--   DROP TRIGGER IF EXISTS corner_requests_mail ON corner.requests;
--   DROP FUNCTION IF EXISTS corner._mail_on_request(), corner._mail_text(text, integer),
--     corner._mail_usd(numeric), public.corner_mail_prefs(), public.corner_mail_prefs_set(boolean, boolean),
--     public.corner_mail_state(), public.corner_mail_invite(uuid, text), public.corner_mail_claim(integer),
--     public.corner_mail_done(bigint, boolean, text, text);
--   DROP TABLE IF EXISTS corner.outbox, corner.mail_prefs;
--   CREATE OR REPLACE FUNCTION public.corner_settings_set(p_key text, p_value text)
--   RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
--   BEGIN
--     PERFORM corner._gate();
--     IF NOT corner._is_super() THEN
--       RAISE EXCEPTION 'Only the super admin changes the Corner''s settings.' USING ERRCODE = '42501';
--     END IF;
--     IF p_key = 'daily_cap_usd' THEN
--       IF p_value !~ '^[0-9]{1,2}(\.[0-9]{1,2})?$' OR p_value::numeric > 50 THEN
--         PERFORM corner._bad('daily_cap_usd: 0 to 50 dollars');
--       END IF;
--     ELSIF p_key = 'researchers_need_approval' THEN
--       IF p_value NOT IN ('true', 'false') THEN PERFORM corner._bad('researchers_need_approval: true or false'); END IF;
--     ELSIF p_key = 'max_pending_per_person' THEN
--       IF p_value !~ '^[0-9]{1,3}$' OR p_value::integer < 1 OR p_value::integer > 200 THEN
--         PERFORM corner._bad('max_pending_per_person: 1 to 200');
--       END IF;
--     ELSE
--       PERFORM corner._bad('no such setting');
--     END IF;
--     UPDATE corner.settings s SET value = p_value, updated_at = now(), updated_by = auth.uid() WHERE s.key = p_key;
--     PERFORM corner._log('setting', NULL, NULL, jsonb_build_object('key', p_key, 'value', p_value));
--     RETURN p_value;
--   END $$;
--   COMMIT;
--   NOTIFY pgrst, 'reload schema';
-- (Before a rollback, remove the corner-mail edge function, or it answers with errors.)
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins (tests/test_corner_mail_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corner.settings') IS NULL OR to_regclass('corner.requests') IS NULL
     OR to_regclass('corner.kinds') IS NULL OR to_regclass('corner.events') IS NULL
     OR to_regprocedure('public.corner_settings_set(text, text)') IS NULL
     OR to_regprocedure('corner._gate()') IS NULL OR to_regprocedure('corner._editor_gate()') IS NULL
     OR to_regprocedure('corner._is_super()') IS NULL OR to_regprocedure('corner._setting(text)') IS NULL
     OR to_regprocedure('corner._bad(text)') IS NULL OR to_regprocedure('corner._today()') IS NULL
     OR to_regprocedure('corner._log(text, bigint, bigint, jsonb)') IS NULL
     OR to_regprocedure('corpus._is_editor()') IS NULL THEN
    RAISE EXCEPTION 'C12: needs C9 (corner.settings, corner.requests, corner_settings_set or the corner helpers are missing).';
  END IF;
  IF to_regprocedure('public.corner_request_track(bigint[])') IS NULL THEN
    RAISE EXCEPTION 'C12: run C10a first (public.corner_request_track is missing).';
  END IF;
  IF to_regclass('rbac.invites') IS NULL OR to_regprocedure('rbac._token_hash(text)') IS NULL
     OR to_regclass('auth.users') IS NULL THEN
    RAISE EXCEPTION 'C12: needs C7 (rbac.invites, rbac._token_hash or auth.users is missing).';
  END IF;
END $$;

-- 1. The settings: the key CHECK of C9 (settings_key_check, made by C9's inline CHECK on the column)
--    is widened to the four mail keys. A CHECK on the key that does not allow them is dropped (by its
--    real name), and settings_key_check is added again; one that allows them already is kept.
DO $$
DECLARE c record;
BEGIN
  FOR c IN
    SELECT x.conname, pg_get_constraintdef(x.oid) AS def
    FROM pg_constraint x
    WHERE x.conrelid = 'corner.settings'::regclass AND x.contype = 'c'
      AND x.conkey = ARRAY[(SELECT a.attnum FROM pg_attribute a
                            WHERE a.attrelid = 'corner.settings'::regclass AND a.attname = 'key')]
  LOOP
    IF NOT (c.def LIKE '%''mail_enabled''%' AND c.def LIKE '%''mail_from''%'
            AND c.def LIKE '%''mail_reply_to''%' AND c.def LIKE '%''site_url''%') THEN
      EXECUTE format('ALTER TABLE corner.settings DROP CONSTRAINT %I', c.conname);
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint x
                 WHERE x.conrelid = 'corner.settings'::regclass AND x.conname = 'settings_key_check') THEN
    ALTER TABLE corner.settings ADD CONSTRAINT settings_key_check CHECK (key IN (
      'daily_cap_usd', 'researchers_need_approval', 'max_pending_per_person',
      'mail_enabled', 'mail_from', 'mail_reply_to', 'site_url'));
  END IF;
END $$;
INSERT INTO corner.settings (key, value) VALUES
  ('mail_enabled', 'false'), ('mail_from', 'Srangam desk <desk@nartiang.org>'), ('mail_reply_to', ''),
  ('site_url', 'https://srangam.nartiang.org')
ON CONFLICT (key) DO NOTHING;

-- 2. Tables (closed: RLS on, no grant to anyone).
CREATE TABLE IF NOT EXISTS corner.mail_prefs (
    user_id         UUID PRIMARY KEY,
    on_my_requests  BOOLEAN NOT NULL DEFAULT true,
    on_queue        BOOLEAN NOT NULL DEFAULT true,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corner.outbox (
    id           BIGSERIAL PRIMARY KEY,
    kind         TEXT NOT NULL CHECK (kind IN ('request_done', 'request_failed', 'request_rejected',
                                               'request_pending', 'invite')),
    user_id      UUID,
    to_email     TEXT CHECK (to_email IS NULL OR length(to_email) <= 254),
    request_id   BIGINT REFERENCES corner.requests(id) ON DELETE CASCADE,
    invite_id    UUID,
    subject      TEXT NOT NULL CHECK (length(subject) <= 300),
    body         TEXT NOT NULL CHECK (length(body) <= 6000),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_at   TIMESTAMPTZ,
    sent_at      TIMESTAMPTZ,
    failed_at    TIMESTAMPTZ,
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    provider_id  TEXT,
    CHECK (user_id IS NOT NULL OR to_email IS NOT NULL)
);
-- One email of a kind per request and person; at most one open (unsent, not given up) per invitation.
CREATE UNIQUE INDEX IF NOT EXISTS corner_outbox_one_per_request ON corner.outbox (kind, request_id, user_id)
  WHERE request_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS corner_outbox_one_open_invite ON corner.outbox (invite_id)
  WHERE invite_id IS NOT NULL AND sent_at IS NULL AND failed_at IS NULL;
CREATE INDEX IF NOT EXISTS corner_outbox_waiting ON corner.outbox (sent_at, failed_at, created_at);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['mail_prefs', 'outbox'] LOOP
    EXECUTE format('ALTER TABLE corner.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corner.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corner.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corner.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- 3. Helpers (the owner's only) and the trigger.
-- One line of an email: control characters become spaces, cut to p_max characters; NULL when empty.
CREATE OR REPLACE FUNCTION corner._mail_text(p text, p_max integer)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT nullif(btrim(regexp_replace(left(p, p_max), '[[:cntrl:]]+', ' ', 'g')), '')
$$;

-- 0.01 -> $0.01, 0.0071 -> $0.0071, 0.4 -> $0.40; NULL stays NULL.
CREATE OR REPLACE FUNCTION corner._mail_usd(p numeric)
RETURNS text LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT CASE WHEN p IS NOT NULL THEN '$' || to_char(p, 'FM99990.0099') END
$$;

CREATE OR REPLACE FUNCTION corner._mail_on_request()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_kind text; v_label text; v_paid boolean; v_site text; v_title text; v_link text;
  v_subject text; v_body text;
BEGIN
  BEGIN
    IF TG_OP = 'INSERT' THEN
      IF NEW.status = 'pending' THEN v_kind := 'request_pending'; END IF;
    ELSIF TG_OP = 'UPDATE' THEN
      IF NEW.status IS DISTINCT FROM OLD.status THEN
        IF NEW.status IN ('done', 'failed') THEN
          v_kind := 'request_' || NEW.status;
        ELSIF NEW.status = 'rejected' AND OLD.status = 'pending' THEN
          v_kind := 'request_rejected';
        END IF;
      END IF;
    END IF;
    IF v_kind IS NULL OR coalesce(corner._setting('mail_enabled'), 'false') <> 'true' THEN
      RETURN NULL;
    END IF;
    SELECT k.label, k.cost_bearing INTO v_label, v_paid FROM corner.kinds k WHERE k.kind = NEW.kind;
    IF v_kind = 'request_done' AND NOT coalesce(v_paid, false) THEN
      RETURN NULL;                     -- an editor's decision carried out: no email
    END IF;
    v_site := corner._setting('site_url');
    IF v_site IS NULL OR v_site !~ '^https://' THEN
      RAISE EXCEPTION 'the setting site_url is missing or not https';
    END IF;
    v_label := coalesce(corner._mail_text(v_label, 200), NEW.kind);
    v_title := coalesce(corner._mail_text((SELECT d.title FROM corpus.docs d WHERE d.doc_code = NEW.doc_code), 200),
                        NEW.doc_code, '-');
    v_link := v_site || '/corpus/corner?tab=' || CASE WHEN v_kind = 'request_pending' THEN 'queue' ELSE 'mine' END;
    v_subject := left('Srangam: request #' || NEW.id || CASE v_kind
                        WHEN 'request_done' THEN ' is done - '
                        WHEN 'request_failed' THEN ' failed - '
                        WHEN 'request_rejected' THEN ' was not approved - '
                        ELSE ' waits for approval - ' END || v_label, 300);
    -- concat_ws leaves out the lines that are NULL (a message, a cost or a note the request does not have).
    v_body := concat_ws(E'\n',
      CASE v_kind WHEN 'request_done' THEN 'Your request #' || NEW.id || ' is done.'
                  WHEN 'request_failed' THEN 'Your request #' || NEW.id || ' could not be done.'
                  WHEN 'request_rejected' THEN 'An editor did not approve your request #' || NEW.id || '.'
                  ELSE 'Request #' || NEW.id || ' waits for an editor''s approval.' END,
      '',
      CASE WHEN v_kind = 'request_pending' THEN 'Who asked: ' || coalesce(
        (SELECT corner._mail_text(u.email::text, 254) FROM auth.users u WHERE u.id = NEW.requested_by),
        'an account with no email address') END,
      'What was asked: ' || v_label,
      'Text: ' || v_title,
      CASE WHEN v_kind = 'request_pending' THEN 'Estimate: ' || corner._mail_usd(NEW.est_usd) END,
      CASE WHEN v_kind IN ('request_done', 'request_failed') THEN 'The desk says: ' || corner._mail_text(NEW.message, 600) END,
      CASE WHEN v_kind IN ('request_done', 'request_failed') THEN 'Cost: ' || corner._mail_usd(NEW.cost_usd) END,
      CASE WHEN v_kind = 'request_rejected' THEN 'The editor''s note: ' || corner._mail_text(NEW.decision_note, 600) END,
      '',
      CASE WHEN v_kind = 'request_pending' THEN 'To approve or reject it: ' ELSE 'See it in the Corner: ' END || v_link,
      '',
      'You get this because you use the Researchers'' Corner on Srangam. To stop these emails: '
        || v_site || '/corpus/corner?tab=settings');
    IF v_kind = 'request_pending' THEN
      INSERT INTO corner.outbox (kind, user_id, request_id, subject, body)
      SELECT v_kind, e.uid, NEW.id, v_subject, v_body
      FROM (SELECT DISTINCT r.user_id AS uid FROM public.user_roles r
            WHERE r.role IN ('admin'::public.app_role, 'super_admin'::public.app_role)) e
      WHERE e.uid IS NOT NULL AND e.uid IS DISTINCT FROM NEW.requested_by
        AND coalesce((SELECT p.on_queue FROM corner.mail_prefs p WHERE p.user_id = e.uid), true)
      ON CONFLICT (kind, request_id, user_id) WHERE request_id IS NOT NULL DO NOTHING;
    ELSIF coalesce((SELECT p.on_my_requests FROM corner.mail_prefs p WHERE p.user_id = NEW.requested_by), true) THEN
      INSERT INTO corner.outbox (kind, user_id, request_id, subject, body)
      VALUES (v_kind, NEW.requested_by, NEW.id, v_subject, v_body)
      ON CONFLICT (kind, request_id, user_id) WHERE request_id IS NOT NULL DO NOTHING;
    END IF;
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'C12 mail: request #% is kept, but its email was not queued: % (%)', NEW.id, SQLERRM, SQLSTATE;
  END;
  RETURN NULL;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid = 'corner.requests'::regclass
                 AND t.tgname = 'corner_requests_mail' AND NOT t.tgisinternal) THEN
    CREATE TRIGGER corner_requests_mail AFTER INSERT OR UPDATE OF status ON corner.requests
      FOR EACH ROW EXECUTE FUNCTION corner._mail_on_request();
  END IF;
END $$;

-- 4. The site's functions.
CREATE OR REPLACE FUNCTION public.corner_mail_prefs()
RETURNS TABLE (on_my_requests boolean, on_queue boolean, mail_enabled boolean, is_editor boolean, mail_from text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corner._gate();
  RETURN QUERY
  SELECT coalesce(p.on_my_requests, true), coalesce(p.on_queue, true),
         coalesce(corner._setting('mail_enabled'), 'false') = 'true', corpus._is_editor(),
         CASE WHEN corner._is_super() THEN corner._setting('mail_from') END
  FROM (SELECT auth.uid() AS uid) me
  LEFT JOIN corner.mail_prefs p ON p.user_id = me.uid;
END $$;

-- The caller's own choice; a NULL leaves that choice as it was. on_queue is kept for anyone, and
-- used only while they are an editor.
CREATE OR REPLACE FUNCTION public.corner_mail_prefs_set(p_on_my_requests boolean, p_on_queue boolean)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corner._gate();
  INSERT INTO corner.mail_prefs AS p (user_id, on_my_requests, on_queue, updated_at)
  VALUES (auth.uid(), coalesce(p_on_my_requests, true), coalesce(p_on_queue, true), now())
  ON CONFLICT (user_id) DO UPDATE SET on_my_requests = coalesce(p_on_my_requests, p.on_my_requests),
         on_queue = coalesce(p_on_queue, p.on_queue), updated_at = now();
  RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.corner_mail_state()
RETURNS TABLE (mail_enabled boolean, waiting bigint, sent_today bigint, failed_7d bigint, last_sent_at timestamptz,
               last_error text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corner._editor_gate();
  RETURN QUERY
  SELECT coalesce(corner._setting('mail_enabled'), 'false') = 'true',
         (SELECT count(*) FROM corner.outbox o WHERE o.sent_at IS NULL AND o.failed_at IS NULL),
         (SELECT count(*) FROM corner.outbox o
           WHERE o.sent_at IS NOT NULL AND (o.sent_at AT TIME ZONE 'Asia/Kolkata')::date = corner._today()),
         (SELECT count(*) FROM corner.outbox o
           WHERE o.sent_at IS NULL AND o.failed_at > now() - interval '7 days'),
         (SELECT max(o.sent_at) FROM corner.outbox o),
         (SELECT left(o.last_error, 300) FROM corner.outbox o
           WHERE o.last_error IS NOT NULL AND o.sent_at IS NULL ORDER BY o.id DESC LIMIT 1);
END $$;

-- The super admin sends a pending invitation's link (the token is known only right after
-- research_invite_create). Asking again for the same invitation replaces its open email.
CREATE OR REPLACE FUNCTION public.corner_mail_invite(p_invite uuid, p_token text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE i rbac.invites%ROWTYPE; v_site text; v_body text;
BEGIN
  IF NOT corner._is_super() THEN
    RAISE EXCEPTION 'Only the super admin sends invitations.' USING ERRCODE = '42501';
  END IF;
  IF coalesce(corner._setting('mail_enabled'), 'false') <> 'true' THEN
    PERFORM corner._bad('Email is off; the super admin turns it on in Corner -> Settings');
  END IF;
  IF p_invite IS NULL OR p_token IS NULL OR p_token !~ '^[0-9a-f]{64}$' THEN
    PERFORM corner._bad('not a pending invitation');
  END IF;
  SELECT * INTO i FROM rbac.invites x WHERE x.id = p_invite;
  IF NOT FOUND OR i.token_hash IS DISTINCT FROM rbac._token_hash(p_token) OR i.accepted_at IS NOT NULL
     OR i.revoked_at IS NOT NULL OR i.expires_at <= now() THEN
    PERFORM corner._bad('not a pending invitation');
  END IF;
  v_site := corner._setting('site_url');
  IF v_site IS NULL OR v_site !~ '^https://' THEN
    PERFORM corner._bad('site_url: not set; the super admin sets it in Corner -> Settings');
  END IF;
  v_body := concat_ws(E'\n',
    'You are invited to work with the Srangam working corpus as a researcher.',
    '',
    'To accept, open this link and sign in (or create an account) with this email address, ' || i.email || ':',
    v_site || '/invite/' || p_token,
    '',
    'The link works once, until ' || to_char(i.expires_at AT TIME ZONE 'Asia/Kolkata', 'FMDD FMMonth YYYY, HH24:MI')
      || ' India time.',
    CASE WHEN i.note IS NOT NULL THEN E'\nA note with the invitation:\n' || left(i.note, 500) END,
    '',
    'If you did not expect this email, you can ignore it.');
  INSERT INTO corner.outbox (kind, to_email, invite_id, subject, body)
  VALUES ('invite', i.email, i.id, 'An invitation to the Srangam working corpus', v_body)
  ON CONFLICT (invite_id) WHERE invite_id IS NOT NULL AND sent_at IS NULL AND failed_at IS NULL
  DO UPDATE SET to_email = EXCLUDED.to_email, subject = EXCLUDED.subject, body = EXCLUDED.body,
                attempts = 0, last_error = NULL;
  PERFORM corner._log('mail_invite', NULL, NULL, jsonb_build_object('invite', i.id));
  RETURN 'queued';
END $$;

-- 5. The corner-mail edge function's side (service_role only).
-- Up to 20 emails, oldest first, each taken for 10 minutes and at most 5 times. An email with no
-- address, or an invitation that is no longer pending, is given up here and not returned.
CREATE OR REPLACE FUNCTION public.corner_mail_claim(p_limit integer)
RETURNS TABLE (id bigint, to_email text, mail_from text, reply_to text, subject text, body text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE v_from text; v_reply text;
BEGIN
  IF coalesce(corner._setting('mail_enabled'), 'false') <> 'true' THEN
    RETURN;
  END IF;
  v_from := corner._setting('mail_from');
  v_reply := nullif(btrim(coalesce(corner._setting('mail_reply_to'), '')), '');
  -- Taken five times and never confirmed (the function died before it answered): given up.
  UPDATE corner.outbox o
     SET failed_at = now(), claimed_at = NULL, last_error = coalesce(o.last_error, 'not confirmed in 5 attempts'),
         body = CASE WHEN o.kind = 'invite' THEN '(not sent; the link is not kept)' ELSE o.body END
   WHERE o.sent_at IS NULL AND o.failed_at IS NULL AND o.attempts >= 5
     AND (o.claimed_at IS NULL OR o.claimed_at < now() - interval '10 minutes');
  RETURN QUERY
  WITH c AS (
    SELECT o.id AS oid,
           coalesce(nullif(btrim(o.to_email), ''),
                    (SELECT nullif(btrim(u.email::text), '') FROM auth.users u WHERE u.id = o.user_id)) AS addr,
           (o.kind = 'invite' AND NOT EXISTS (
              SELECT 1 FROM rbac.invites i WHERE i.id = o.invite_id AND i.accepted_at IS NULL
                AND i.revoked_at IS NULL AND i.expires_at > now())) AS stale
    FROM corner.outbox o
    WHERE o.sent_at IS NULL AND o.failed_at IS NULL AND o.attempts < 5
      AND (o.claimed_at IS NULL OR o.claimed_at < now() - interval '10 minutes')
    ORDER BY o.created_at, o.id
    LIMIT least(greatest(p_limit, 1), 20)
    FOR UPDATE OF o SKIP LOCKED
  ), u AS (
    UPDATE corner.outbox o
       SET claimed_at = CASE WHEN c.addr IS NULL OR c.stale THEN NULL ELSE now() END,
           attempts = o.attempts + CASE WHEN c.addr IS NULL OR c.stale THEN 0 ELSE 1 END,
           failed_at = CASE WHEN c.addr IS NULL OR c.stale THEN now() END,
           last_error = CASE WHEN c.addr IS NULL THEN 'no address'
                             WHEN c.stale THEN 'the invitation is no longer pending' ELSE o.last_error END,
           body = CASE WHEN c.stale THEN '(not sent; the link is not kept)' ELSE o.body END
      FROM c
     WHERE o.id = c.oid
    RETURNING o.id AS oid, c.addr AS addr, c.stale AS stale, o.subject AS subj, o.body AS bod, o.created_at AS cat
  )
  SELECT u.oid, u.addr, v_from, v_reply, u.subj, u.bod
  FROM u
  WHERE u.addr IS NOT NULL AND NOT u.stale
  ORDER BY u.cat, u.oid;
END $$;

-- How one email went. Sent: kept as sent (an invitation's body, which holds the link, is wiped).
-- Not sent: the error is kept and the email is taken again later; after its fifth attempt it is
-- given up. False for an email that does not exist or was sent already.
CREATE OR REPLACE FUNCTION public.corner_mail_done(p_id bigint, p_ok boolean, p_provider_id text, p_error text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE o corner.outbox;
BEGIN
  SELECT * INTO o FROM corner.outbox x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR o.sent_at IS NOT NULL THEN
    RETURN false;
  END IF;
  IF coalesce(p_ok, false) THEN
    UPDATE corner.outbox x SET sent_at = now(), provider_id = left(p_provider_id, 200), claimed_at = NULL,
           body = CASE WHEN x.kind = 'invite' THEN '(sent; the link is not kept)' ELSE x.body END
    WHERE x.id = p_id;
  ELSE
    UPDATE corner.outbox x SET last_error = coalesce(nullif(left(p_error, 500), ''), 'not sent'), claimed_at = NULL,
           failed_at = CASE WHEN x.attempts >= 5 THEN coalesce(x.failed_at, now()) ELSE x.failed_at END,
           body = CASE WHEN x.kind = 'invite' AND x.attempts >= 5 THEN '(not sent; the link is not kept)' ELSE x.body END
    WHERE x.id = p_id;
  END IF;
  RETURN true;
END $$;

-- 6. The settings: C9's three keys exactly as in C9, and the four mail keys.
CREATE OR REPLACE FUNCTION public.corner_settings_set(p_key text, p_value text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corner._gate();
  IF NOT corner._is_super() THEN
    RAISE EXCEPTION 'Only the super admin changes the Corner''s settings.' USING ERRCODE = '42501';
  END IF;
  IF p_key = 'daily_cap_usd' THEN
    IF p_value !~ '^[0-9]{1,2}(\.[0-9]{1,2})?$' OR p_value::numeric > 50 THEN
      PERFORM corner._bad('daily_cap_usd: 0 to 50 dollars');
    END IF;
  ELSIF p_key = 'researchers_need_approval' THEN
    IF p_value NOT IN ('true', 'false') THEN PERFORM corner._bad('researchers_need_approval: true or false'); END IF;
  ELSIF p_key = 'max_pending_per_person' THEN
    IF p_value !~ '^[0-9]{1,3}$' OR p_value::integer < 1 OR p_value::integer > 200 THEN
      PERFORM corner._bad('max_pending_per_person: 1 to 200');
    END IF;
  ELSIF p_key = 'mail_enabled' THEN
    IF p_value IS NULL OR p_value NOT IN ('true', 'false') THEN PERFORM corner._bad('mail_enabled: true or false'); END IF;
  ELSIF p_key = 'mail_from' THEN
    IF p_value IS NULL OR length(p_value) > 320 OR p_value ~ '[[:cntrl:]]'
       OR p_value !~ '^[^<>@]{1,60} <[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}>$' THEN
      PERFORM corner._bad('mail_from: a name and an address, such as Srangam desk <desk@nartiang.org>');
    END IF;
  ELSIF p_key = 'mail_reply_to' THEN
    IF p_value IS NULL OR (p_value <> '' AND (length(p_value) > 254
       OR p_value !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')) THEN
      PERFORM corner._bad('mail_reply_to: empty, or one address such as desk@nartiang.org');
    END IF;
  ELSIF p_key = 'site_url' THEN
    IF p_value IS NULL OR length(p_value) > 200 OR p_value !~ '^https://[a-z0-9.-]+(:[0-9]+)?$' THEN
      PERFORM corner._bad('site_url: https:// and the site''s host, with no path, such as https://srangam.nartiang.org');
    END IF;
  ELSE
    PERFORM corner._bad('no such setting');
  END IF;
  IF p_key IN ('mail_enabled', 'mail_from', 'mail_reply_to', 'site_url') THEN
    INSERT INTO corner.settings AS s (key, value, updated_at, updated_by) VALUES (p_key, p_value, now(), auth.uid())
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(), updated_by = auth.uid();
  ELSE
    UPDATE corner.settings s SET value = p_value, updated_at = now(), updated_by = auth.uid() WHERE s.key = p_key;
  END IF;
  PERFORM corner._log('setting', NULL, NULL, jsonb_build_object('key', p_key, 'value', p_value));
  RETURN p_value;
END $$;

-- 7. Who may call what: the site's four for signed-in people (each checks the caller again), claim
--    and done for the edge function only, the helpers and the trigger function for nobody.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'corner._mail_text(text, integer)', 'corner._mail_usd(numeric)', 'corner._mail_on_request()',
      'public.corner_mail_prefs()', 'public.corner_mail_prefs_set(boolean, boolean)', 'public.corner_mail_state()',
      'public.corner_mail_invite(uuid, text)', 'public.corner_mail_claim(integer)',
      'public.corner_mail_done(bigint, boolean, text, text)', 'public.corner_settings_set(text, text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corner_mail_prefs(), public.corner_mail_prefs_set(boolean, boolean),
      public.corner_mail_state(), public.corner_mail_invite(uuid, text),
      public.corner_settings_set(text, text) TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.corner_mail_claim(integer),
      public.corner_mail_done(bigint, boolean, text, text) TO service_role;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
