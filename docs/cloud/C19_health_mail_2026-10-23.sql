-- ============================================================
-- C19 - the desk's health by email (HEALTH_MAIL_C19_2026_10_23)
-- docs/RELATIONS_AND_ASK_2026-10-22.md (alerts). Paste this whole file once in the Lovable Cloud SQL editor (one
-- transaction). Read-only checks: docs/cloud/C19_checks_2026-10-23.sql, one query per paste.
--
-- The desk (scripts/corner_worker.py, every 10 minutes) sends its heartbeat; since HEALTH_2026_10_23 the heartbeat's
-- info carries "health" (scripts/health_watch.py: the maintenance task, the mirror, the daily backup, the disk, the
-- spend, the links), beside "sync" (the mirror's and the pictures' last run). This file reads them as the heartbeat
-- lands and, with the Corner's mail on (C12), queues an email to each super admin:
--   - when the desk says warn or fail, or its mirror's last run is not ok;
--   - the same report again only after 12 hours; a changed report at once;
--   - once, when all is well again.
-- The email is sent as every Corner email is: by the desk's next round (corner-mail). A desk that does not come by
-- at all therefore mails nothing; its last visit is in the Corner (corner_me) and in check H4.
--
-- What it adds:
--   corner.outbox             the kind 'health' (the kind CHECK is widened)
--   corner.health_state       one row: the last status and problems the desk reported, when they were last mailed
--   corner._health_on_heartbeat()   the trigger's function; it never raises: a problem is a WARNING, the
--                             heartbeat goes through
--   the trigger corner_worker_health   AFTER UPDATE OF info ON corner.worker
-- Needs C9, C10a and C12. Re-running it changes nothing (the state is kept).
-- Rollback (one paste; the wider kind CHECK can stay):
--   BEGIN;
--   DROP TRIGGER IF EXISTS corner_worker_health ON corner.worker;
--   DROP FUNCTION IF EXISTS corner._health_on_heartbeat();
--   DROP TABLE IF EXISTS corner.health_state;
--   COMMIT;
-- ============================================================
BEGIN;

DO $$
BEGIN
  IF to_regclass('corner.outbox') IS NULL OR to_regclass('corner.worker') IS NULL
     OR to_regprocedure('corner._mail_text(text,integer)') IS NULL OR to_regprocedure('corner._setting(text)') IS NULL
     OR to_regclass('public.user_roles') IS NULL THEN
    RAISE EXCEPTION 'C19 needs C9, C10a and C12 applied first';
  END IF;
END $$;

-- 1. The outbox takes 'health'.
DO $$
DECLARE c record;
BEGIN
  FOR c IN SELECT con.conname, pg_get_constraintdef(con.oid) AS def FROM pg_constraint con
           WHERE con.conrelid = 'corner.outbox'::regclass AND con.contype = 'c' LOOP
    IF c.def LIKE '%request_done%' AND c.def LIKE '%invite%' AND c.def NOT LIKE '%health%' THEN
      EXECUTE format('ALTER TABLE corner.outbox DROP CONSTRAINT %I', c.conname);
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conrelid = 'corner.outbox'::regclass AND con.contype = 'c'
                 AND pg_get_constraintdef(con.oid) LIKE '%health%') THEN
    ALTER TABLE corner.outbox ADD CONSTRAINT outbox_kind_check CHECK (kind IN ('request_done', 'request_failed',
      'request_rejected', 'request_pending', 'invite', 'health'));
  END IF;
END $$;

-- 2. The state: one row.
CREATE TABLE IF NOT EXISTS corner.health_state (
    id         INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    status     TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'warn', 'fail')),
    problems   TEXT NOT NULL DEFAULT '',
    mailed_at  TIMESTAMPTZ,
    seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO corner.health_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
ALTER TABLE corner.health_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON corner.health_state FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON corner.health_state FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON corner.health_state FROM authenticated'; END IF;
END $$;

-- 3. The trigger.
CREATE OR REPLACE FUNCTION corner._health_on_heartbeat()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_h jsonb; v_m jsonb; v_status text; v_probs text[]; v_text text; v_last corner.health_state%ROWTYPE;
  v_site text; v_subject text; v_body text;
BEGIN
  BEGIN
    v_h := CASE WHEN jsonb_typeof(NEW.info -> 'health') = 'object' THEN NEW.info -> 'health' ELSE '{}'::jsonb END;
    v_status := CASE WHEN v_h ->> 'status' IN ('ok', 'warn', 'fail') THEN v_h ->> 'status' ELSE 'ok' END;
    v_probs := ARRAY(SELECT corner._mail_text(x, 160)
                     FROM jsonb_array_elements_text(CASE WHEN jsonb_typeof(v_h -> 'problems') = 'array'
                                                         THEN v_h -> 'problems' ELSE '[]'::jsonb END) AS t(x)
                     WHERE corner._mail_text(x, 160) IS NOT NULL LIMIT 8);
    v_m := NEW.info -> 'sync' -> 'mirror';
    IF jsonb_typeof(v_m) = 'object' AND v_m ->> 'ok' = 'false'
       AND NOT EXISTS (SELECT 1 FROM unnest(v_probs) AS p WHERE p LIKE 'mirror:%') THEN
      v_probs := v_probs || corner._mail_text('mirror: the last run stopped ' || coalesce(v_m ->> 'stopped', '?')
                 || coalesce(', ' || (v_m ->> 'different') || ' groups different', '')
                 || coalesce(' (' || (v_m ->> 'error') || ')', ''), 200);
      IF v_status = 'ok' THEN v_status := 'warn'; END IF;
    END IF;
    v_text := coalesce(array_to_string(v_probs, '; '), '');
    SELECT * INTO v_last FROM corner.health_state WHERE id = 1 FOR UPDATE;
    IF NOT FOUND THEN
      INSERT INTO corner.health_state (id) VALUES (1) RETURNING * INTO v_last;
    END IF;
    IF coalesce(corner._setting('mail_enabled'), 'false') = 'true'
       AND ((v_status <> 'ok' AND (v_status <> v_last.status OR v_text <> v_last.problems
                                   OR v_last.mailed_at IS NULL OR v_last.mailed_at < now() - interval '12 hours'))
            OR (v_status = 'ok' AND v_last.status <> 'ok')) THEN
      v_site := coalesce(corner._setting('site_url'), '');
      v_subject := left(CASE WHEN v_status = 'ok' THEN 'Srangam desk: all well again'
                             ELSE 'Srangam desk: ' || upper(v_status) || ' - ' || coalesce(v_probs[1], 'see the Corner')
                        END, 300);
      v_body := concat_ws(E'\n',
        CASE WHEN v_status = 'ok' THEN 'The desk reports that all is well again. Before, it reported: '
                                       || coalesce(nullif(v_last.problems, ''), v_last.status) || '.'
             ELSE 'The desk reports ' || upper(v_status) || ':' END,
        CASE WHEN v_status <> 'ok' THEN array_to_string(ARRAY(SELECT '- ' || p FROM unnest(v_probs) AS p), E'\n') END,
        '',
        'Reported at: ' || coalesce(corner._mail_text(v_h ->> 'at', 40), to_char(now(), 'YYYY-MM-DD HH24:MI') || ' UTC'),
        CASE WHEN v_site ~ '^https://' THEN 'The Corner: ' || v_site || '/corpus/corner' END,
        'On the desk: python scripts\health_watch.py',
        '',
        'You get this because you are the super admin of Srangam. The desk sends it again only when its report '
          || 'changes, or after 12 hours, and once when all is well again.');
      INSERT INTO corner.outbox (kind, user_id, subject, body)
      SELECT 'health', r.uid, v_subject, left(v_body, 6000)
      FROM (SELECT DISTINCT ur.user_id AS uid FROM public.user_roles ur
            WHERE ur.role = 'super_admin'::public.app_role) r
      WHERE r.uid IS NOT NULL;
      UPDATE corner.health_state SET mailed_at = now() WHERE id = 1;
    END IF;
    UPDATE corner.health_state SET status = v_status, problems = v_text, seen_at = now() WHERE id = 1;
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'C19 health: the heartbeat is kept, but its health was not read: % (%)', SQLERRM, SQLSTATE;
  END;
  RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION corner._health_on_heartbeat() FROM PUBLIC;

DROP TRIGGER IF EXISTS corner_worker_health ON corner.worker;
CREATE TRIGGER corner_worker_health AFTER UPDATE OF info ON corner.worker
  FOR EACH ROW WHEN (NEW.info IS DISTINCT FROM OLD.info) EXECUTE FUNCTION corner._health_on_heartbeat();

COMMIT;
