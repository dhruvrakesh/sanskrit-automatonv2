-- ============================================================
-- C10a - the Corner's state: where the desk is with a request (CORNER_STATE_C10A_2026_10_09)
-- docs/RESEARCHERS_CORNER_2026-10-09.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C10a_checks_2026-10-09.sql, one query per paste.
--
-- What it adds:
--   corner.requests.progress  where the desk is with a request it is running, as the desk last said:
--                             {"step": 3, "of": 12, "note": "Drawing page 3 of 12", "at": "<when>"}.
--                             NULL until the desk says; an object of at most 1000 characters.
--   public.corner_request_track(bigint[])  the state of up to 100 requests at once, for the site's
--                             progress bars: a researcher sees their own requests, an editor any.
-- What it changes (CREATE OR REPLACE; the same signature, the same grants: the desk only):
--   public.corner_desk_report
--     - a 'running' report whose result is an object with the key progress stores that progress,
--       made safe (step 0 to of, of 1 to 1000, note cut to 200 characters, at = the database's
--       now()), and leaves the request's result as it was;
--     - started_at is set once, at the desk's first report (C9 set it again at every 'running' report);
--     - an event is written when the status changes, and for every done or failed report; not one
--       for each progress report.
--     Everything else is as in C9: done and failed set finished_at, the result, the cost and the log
--     tail; they keep the last progress.
-- The desk's worker 1.1 (scripts/corner_worker.py, CORNER_STATE_C10A_2026_10_09) sends the progress,
-- and its heartbeat (corner.worker.info, shown to editors by corner_me()) gains "sync": the state of
-- the mirror and of the picture uploads. Apply this file BEFORE the desk gets worker 1.1: C9's
-- corner_desk_report would keep each progress report as the request's result.
--
-- Needs C9. Purely additive but for corner_desk_report. Re-running it changes nothing. A re-run of C9
-- puts C9's corner_desk_report back: run this file again after any re-run of C9.
-- Rollback (one paste; C9's own corner_desk_report again, then the rest):
--   BEGIN;
--   CREATE OR REPLACE FUNCTION public.corner_desk_report(p_id bigint, p_status text, p_result jsonb, p_message text,
--                                                       p_cost numeric, p_log text)
--   RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
--   DECLARE r corner.requests;
--   BEGIN
--     IF p_status NOT IN ('running', 'done', 'failed') THEN
--       RAISE EXCEPTION 'p_status: running, done or failed' USING ERRCODE = '22023';
--     END IF;
--     SELECT * INTO r FROM corner.requests x WHERE x.id = p_id FOR UPDATE;
--     IF NOT FOUND OR r.status NOT IN ('claimed', 'running') THEN
--       RETURN false;
--     END IF;
--     UPDATE corner.requests x SET
--         status = p_status,
--         started_at = CASE WHEN p_status = 'running' THEN now() ELSE coalesce(x.started_at, now()) END,
--         finished_at = CASE WHEN p_status IN ('done', 'failed') THEN now() END,
--         result = CASE WHEN p_result IS NOT NULL AND jsonb_typeof(p_result) = 'object' AND length(p_result::text) <= 20000
--                       THEN p_result ELSE x.result END,
--         message = coalesce(left(p_message, 2000), x.message),
--         cost_usd = CASE WHEN p_cost IS NOT NULL AND p_cost >= 0 AND p_cost < 100 THEN p_cost ELSE x.cost_usd END,
--         log_tail = coalesce(left(p_log, 8000), x.log_tail)
--     WHERE x.id = p_id;
--     INSERT INTO corner.events (request_id, action, detail)
--     VALUES (p_id, 'desk_' || p_status, jsonb_build_object('cost', p_cost, 'message', left(p_message, 300)));
--     UPDATE corner.worker w SET last_seen = now() WHERE w.id = 1;
--     RETURN true;
--   END $$;
--   DROP FUNCTION IF EXISTS public.corner_request_track(bigint[]);
--   ALTER TABLE corner.requests DROP COLUMN IF EXISTS progress;
--   COMMIT;
--   NOTIFY pgrst, 'reload schema';
-- (Before a rollback, put the desk back on worker 1.0: scripts/corner_worker.py.bak_state_<date>.)
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins (tests/test_corner_state_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corner.requests') IS NULL OR to_regclass('corner.events') IS NULL
     OR to_regclass('corner.worker') IS NULL
     OR to_regprocedure('public.corner_desk_report(bigint, text, jsonb, text, numeric, text)') IS NULL
     OR to_regprocedure('corner._gate()') IS NULL OR to_regprocedure('corner._bad(text)') IS NULL
     OR to_regprocedure('corpus._is_editor()') IS NULL THEN
    RAISE EXCEPTION 'C10a: needs C9 (corner.requests, corner_desk_report, corner._gate or corner._bad is missing).';
  END IF;
END $$;

-- 1. Where the desk is with a request (the table stays closed: no grant to anyone).
ALTER TABLE corner.requests ADD COLUMN IF NOT EXISTS progress JSONB
  CONSTRAINT requests_progress_check
  CHECK (progress IS NULL OR (jsonb_typeof(progress) = 'object' AND length(progress::text) <= 1000));

-- 2. The desk's report, as in C9 but for the progress, started_at and the events.
CREATE OR REPLACE FUNCTION public.corner_desk_report(p_id bigint, p_status text, p_result jsonb, p_message text,
                                                    p_cost numeric, p_log text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r corner.requests; tick boolean; pr jsonb; v_of integer; v_step integer; v_note text; prog jsonb;
BEGIN
  IF p_status NOT IN ('running', 'done', 'failed') THEN
    RAISE EXCEPTION 'p_status: running, done or failed' USING ERRCODE = '22023';
  END IF;
  SELECT * INTO r FROM corner.requests x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR r.status NOT IN ('claimed', 'running') THEN
    RETURN false;
  END IF;
  -- A progress report: 'running' with {"progress": {"step": i, "of": n, "note": "..."}}. It moves the
  -- bar and leaves the result alone. A progress that is not an object is not stored.
  tick := p_status = 'running' AND p_result IS NOT NULL AND jsonb_typeof(p_result) = 'object' AND p_result ? 'progress';
  IF tick AND jsonb_typeof(p_result -> 'progress') = 'object' THEN
    pr := p_result -> 'progress';
    v_of := CASE WHEN jsonb_typeof(pr -> 'of') = 'number'
                   THEN trunc(least(greatest((pr ->> 'of')::numeric, 1), 1000))::integer
                 WHEN (pr ->> 'of') ~ '^\s*-?[0-9]{1,9}\s*$'
                   THEN least(greatest(btrim(pr ->> 'of')::integer, 1), 1000)
                 ELSE 1 END;
    v_step := CASE WHEN jsonb_typeof(pr -> 'step') = 'number'
                     THEN trunc(least(greatest((pr ->> 'step')::numeric, 0), v_of))::integer
                   WHEN (pr ->> 'step') ~ '^\s*-?[0-9]{1,9}\s*$'
                     THEN least(greatest(btrim(pr ->> 'step')::integer, 0), v_of)
                   ELSE 0 END;
    v_note := left(regexp_replace(coalesce(pr ->> 'note', ''), '[[:cntrl:]]', ' ', 'g'), 200);
    prog := jsonb_build_object('step', v_step, 'of', v_of, 'note', v_note, 'at', now()::text);
  END IF;
  UPDATE corner.requests x SET
      status = p_status,
      started_at = coalesce(x.started_at, now()),
      finished_at = CASE WHEN p_status IN ('done', 'failed') THEN now() END,
      result = CASE WHEN tick THEN x.result
                    WHEN p_result IS NOT NULL AND jsonb_typeof(p_result) = 'object' AND length(p_result::text) <= 20000
                    THEN p_result ELSE x.result END,
      progress = coalesce(prog, x.progress),
      message = coalesce(left(p_message, 2000), x.message),
      cost_usd = CASE WHEN p_cost IS NOT NULL AND p_cost >= 0 AND p_cost < 100 THEN p_cost ELSE x.cost_usd END,
      log_tail = coalesce(left(p_log, 8000), x.log_tail)
  WHERE x.id = p_id;
  IF r.status IS DISTINCT FROM p_status OR p_status IN ('done', 'failed') THEN
    INSERT INTO corner.events (request_id, action, detail)
    VALUES (p_id, 'desk_' || p_status, jsonb_build_object('cost', p_cost, 'message', left(p_message, 300)));
  END IF;
  UPDATE corner.worker w SET last_seen = now() WHERE w.id = 1;
  RETURN true;
END $$;

-- 3. The state of up to 100 requests at once, for the site's progress bars.
CREATE OR REPLACE FUNCTION public.corner_request_track(p_ids bigint[])
RETURNS TABLE (id bigint, status text, decided_at timestamptz, claimed_at timestamptz, started_at timestamptz,
               finished_at timestamptz, attempts integer, progress jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corner._gate();
  IF p_ids IS NULL OR cardinality(p_ids) = 0 THEN
    RETURN;
  END IF;
  IF cardinality(p_ids) > 100 THEN
    PERFORM corner._bad('at most 100 requests at a time');
  END IF;
  editor := corpus._is_editor();
  RETURN QUERY
  SELECT r.id, r.status, r.decided_at, r.claimed_at, r.started_at, r.finished_at, r.attempts, r.progress
  FROM corner.requests r
  WHERE r.id = ANY (p_ids) AND (r.requested_by = auth.uid() OR editor)
  ORDER BY r.id;
END $$;

-- 4. Who may call what: track for the site's signed-in people (its gate decides who), report for
--    the desk only, as in C9.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corner_request_track(bigint[])',
                           'public.corner_desk_report(bigint, text, jsonb, text, numeric, text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corner_request_track(bigint[]) TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.corner_desk_report(bigint, text, jsonb, text, numeric, text) TO service_role;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
