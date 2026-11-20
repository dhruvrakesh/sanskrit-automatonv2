-- ============================================================
-- C30b - the admin's status without a command built at run time (C30B_ADMIN_STATUS_STATIC_2026_11_20)
-- docs/ASKS_2026-10-22.md section 39. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 (read-only, before), then
-- the change (one paste, one transaction), then A1 (read-only, after). Export each result.
--
-- Why. Lovable's security scan of 19 Nov, 17:34, marked C30 "Critical": "Stored data decides which commands
-- corpus_admin_status runs. The function corpus_admin_status runs database commands it assembles from stored rows, and
-- whoever signs up can call it." Read against C30: the table names came from a fixed list in the function (through
-- corpus._index_rel), not from stored rows, and the function's first statement refuses everyone but the super admin
-- (rbac._require_super(), tested: SQLSTATE 42501). So no one could steer it; but a command assembled at run time
-- (EXECUTE format) is the pattern the scan looks for, and it is not needed: this reads each of the ten index tables by
-- name. The answer is the same (scheme admin-status.2: the same fields); the grants are the same.
--
-- What it changes: public.corpus_admin_status() only (CREATE OR REPLACE). Nothing else.
-- Needs C30. Re-running it changes nothing.
-- Rollback (one paste): the change of docs/cloud/C30_admin_status_2026-11-19.sql again.
-- ============================================================

-- B1 (before): C30 is there and builds its commands at run time. Expected: true, true, true.
SELECT to_regprocedure('public.corpus_admin_status()') IS NOT NULL AS c30,
       (SELECT position('EXECUTE format' IN p.prosrc) > 0 FROM pg_catalog.pg_proc p
        WHERE p.oid = to_regprocedure('public.corpus_admin_status()')) AS builds_commands,
       has_function_privilege('authenticated', 'public.corpus_admin_status()', 'EXECUTE') AS signed_in_calls;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regprocedure('public.corpus_admin_status()') IS NULL OR to_regclass('corpus.index_vamsas') IS NULL THEN
    RAISE EXCEPTION 'C30b: C30 comes first. Nothing was changed.';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_admin_status()
RETURNS TABLE (result jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  r jsonb := jsonb_build_object('as_of', now(), 'scheme', 'admin-status.2');
  idx jsonb;
BEGIN
  PERFORM rbac._require_super();   -- C30_ADMIN_STATUS_2026_11_19: the super admin only
  r := r || jsonb_build_object('mirror', jsonb_build_object(
    'texts', (SELECT count(*) FROM corpus.docs d WHERE d.retired_at IS NULL),
    'retired', (SELECT count(*) FROM corpus.docs d WHERE d.retired_at IS NOT NULL),
    'last_text_synced', (SELECT max(d.synced_at) FROM corpus.docs d),
    'passages_about', (SELECT greatest(c.reltuples, 0)::bigint FROM pg_catalog.pg_class c
                       WHERE c.oid = to_regclass('corpus.passages')),
    'translations_about', (SELECT greatest(c.reltuples, 0)::bigint FROM pg_catalog.pg_class c
                           WHERE c.oid = to_regclass('corpus.translations')),
    'last_run', (SELECT jsonb_build_object('started_at', s.started_at, 'finished_at', s.finished_at)
                 FROM corpus.sync_runs s ORDER BY s.started_at DESC LIMIT 1)));
  -- C30B_ADMIN_STATUS_STATIC_2026_11_20: each index table read by name, no command built at run time
  idx := jsonb_build_object(
    'texts', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_texts x),
    'persons', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_persons x),
    'steps', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_steps x),
    'statements', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_statements x),
    'claims', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_claims x),
    'lines', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_lines x),
    'verses', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_verses x),
    'dynasties', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_dynasties x),
    'vamsas', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_vamsas x),
    'meta', (SELECT jsonb_build_object('rows', count(*), 'last_changed', max(x.synced_at)) FROM corpus.index_meta x));
  r := r || jsonb_build_object('index', idx,
                               'index_run', (SELECT m.value FROM corpus.index_meta m WHERE m.key = 'run'));
  r := r || jsonb_build_object('desk', jsonb_build_object(
    'last_seen', (SELECT w.last_seen FROM corner.worker w WHERE w.id = 1),
    'queued', (SELECT count(*) FROM corner.requests q WHERE q.status = 'approved'),
    'running', (SELECT count(*) FROM corner.requests q WHERE q.status IN ('claimed', 'running')),
    'pending', (SELECT count(*) FROM corner.requests q WHERE q.status = 'pending')));
  r := r || jsonb_build_object('access', jsonb_build_object(
    'mode', coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins'),
    'since', (SELECT a.updated_at FROM corpus.reader_access a WHERE a.id),
    'readers_listed', (SELECT count(*) FROM corpus.readers),
    'roles', coalesce((SELECT jsonb_object_agg(x.role, x.n) FROM (
        SELECT ur.role::text AS role, count(*) AS n FROM public.user_roles ur GROUP BY ur.role::text) x), '{}'::jsonb)));
  IF to_regclass('public.srangam_ai_usage') IS NOT NULL THEN
    r := r || jsonb_build_object(
      'ai_7d', coalesce((SELECT jsonb_agg(jsonb_build_object('provider', x.provider, 'model', x.model, 'ok', x.ok,
                                                             'calls', x.calls, 'last_call', x.last_call)
                                          ORDER BY x.calls DESC, x.provider, x.model)
                         FROM (SELECT u.provider, u.model, u.ok, count(*) AS calls, max(u.created_at) AS last_call
                               FROM public.srangam_ai_usage u WHERE u.created_at > now() - interval '7 days'
                               GROUP BY u.provider, u.model, u.ok) x), '[]'::jsonb),
      'ai_functions_7d', coalesce((SELECT jsonb_object_agg(x.function_name, x.calls)
                                   FROM (SELECT u.function_name, count(*) AS calls FROM public.srangam_ai_usage u
                                         WHERE u.created_at > now() - interval '7 days' GROUP BY u.function_name) x),
                                  '{}'::jsonb));
  END IF;
  RETURN QUERY SELECT r;
END $$;

COMMENT ON FUNCTION public.corpus_admin_status() IS
  'C30_ADMIN_STATUS_2026_11_19, C30B_ADMIN_STATUS_STATIC_2026_11_20: the desk and the site at a glance (the mirror, the indexes, the desk worker, who may read, the AI calls); read-only; the super admin only.';

DO $$
DECLARE f text := 'public.corpus_admin_status()';
BEGIN
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

DO $$
DECLARE f text := 'public.corpus_admin_status()';
BEGIN
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

COMMIT;

-- A1 (after): the same function, no command built at run time, the super admin's check first, the same grants.
-- Expected: true, false, true, false, true.
SELECT to_regprocedure('public.corpus_admin_status()') IS NOT NULL AS c30,
       (SELECT position('EXECUTE' IN p.prosrc) > 0 FROM pg_catalog.pg_proc p
        WHERE p.oid = to_regprocedure('public.corpus_admin_status()')) AS builds_commands,
       (SELECT position('PERFORM rbac._require_super();' IN p.prosrc) BETWEEN 1 AND 400 FROM pg_catalog.pg_proc p
        WHERE p.oid = to_regprocedure('public.corpus_admin_status()')) AS super_admin_first,
       has_function_privilege('anon', 'public.corpus_admin_status()', 'EXECUTE') AS anon_calls,
       has_function_privilege('authenticated', 'public.corpus_admin_status()', 'EXECUTE') AS signed_in_calls;
