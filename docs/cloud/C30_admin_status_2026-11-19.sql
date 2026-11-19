-- ============================================================
-- C30 - the desk and the site, for the super admin (C30_ADMIN_STATUS_2026_11_19; Srangam's ADMIN_STATUS_2026_11_19)
-- docs/ASKS_2026-10-22.md section 37. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 (read-only, before), then
-- the change (one paste, one transaction), then A1 and A2 (read-only, after). Export each result.
--
-- Why. Asked on 19 Nov: "alot of the admin dashboard and landing pages need to be reimagined and rewired to reflect
-- present state of local and online deployment and linkages". Read that day: the admin pages read the articles' tables
-- (srangam_articles, tags, cross-references, bibliography, pins); none shows what the desk on the PC sends to the site,
-- when it last did, whether its worker is alive, who may read the working corpus, or which AI keys the site's
-- functions used. All of it is in this database already. One read-only function gathers it, for the super admin:
--   public.corpus_admin_status()   (new) one row, { result }: as_of; mirror (the live and retired texts, the passages
--                                  and translations about, the last text synced, the mirror's last run); index (each
--                                  corpus.index_* table: rows, last changed) and index_run (the desk's run row);
--                                  desk (the worker's last heartbeat, the Corner's queue); access (the readers' mode
--                                  and since, the readers listed, the roles); ai_7d (srangam_ai_usage of the last 7
--                                  days by provider, model and outcome) and ai_functions_7d (by function).
-- Nothing else is changed: no table, no other function, no grant of anything else.
-- Needs C7 (rbac), C9 (the Corner), C29 (the vamsas). Re-running it changes nothing.
-- Rollback (one paste): DROP FUNCTION IF EXISTS public.corpus_admin_status();
-- ============================================================

-- B1 (before): what it reads is there, it is not. Expected: true, true, true, true, true, true, false.
SELECT to_regprocedure('rbac._require_super()') IS NOT NULL AS rbac,
       to_regclass('corpus.sync_runs') IS NOT NULL AS mirror_runs,
       to_regclass('corpus.index_vamsas') IS NOT NULL AS c29,
       to_regclass('corner.worker') IS NOT NULL AS desk_worker,
       to_regclass('corpus.reader_access') IS NOT NULL AS access,
       to_regclass('public.srangam_ai_usage') IS NOT NULL AS ai_ledger,
       to_regprocedure('public.corpus_admin_status()') IS NOT NULL AS c30;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regprocedure('rbac._require_super()') IS NULL OR to_regclass('corpus.index_vamsas') IS NULL
     OR to_regclass('corner.worker') IS NULL OR to_regclass('corpus.sync_runs') IS NULL THEN
    RAISE EXCEPTION 'C30: C7, C9 and C29 come first. Nothing was changed.';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_admin_status()
RETURNS TABLE (result jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  r jsonb := jsonb_build_object('as_of', now(), 'scheme', 'admin-status.1');
  idx jsonb := '{}'::jsonb;
  t text; rel regclass; n bigint; changed timestamptz;
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
  FOREACH t IN ARRAY ARRAY['texts', 'persons', 'steps', 'statements', 'claims', 'lines', 'verses', 'dynasties',
                           'vamsas', 'meta'] LOOP
    rel := corpus._index_rel(t);
    IF rel IS NOT NULL THEN
      EXECUTE format('SELECT count(*), max(synced_at) FROM %s', rel) INTO n, changed;
      idx := idx || jsonb_build_object(t, jsonb_build_object('rows', n, 'last_changed', changed));
    END IF;
  END LOOP;
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
  'C30_ADMIN_STATUS_2026_11_19: the desk and the site at a glance (the mirror, the indexes, the desk worker, who may read, the AI calls); read-only; the super admin only.';

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

-- A1 (after): the function, who may call it. Expected: true, false, true. (Signed-in callers who are not the super
-- admin are refused inside it: "Only the super admin may do this.")
SELECT to_regprocedure('public.corpus_admin_status()') IS NOT NULL AS c30,
       has_function_privilege('anon', 'public.corpus_admin_status()', 'EXECUTE') AS anon_calls,
       has_function_privilege('authenticated', 'public.corpus_admin_status()', 'EXECUTE') AS signed_in_calls;

-- A2 (after): what it would say, read here directly (the SQL editor is not the super admin, so the function itself
-- refuses it; these are the same numbers). Expected (19 Nov): 10 index tables, vamsas 10, dynasties 517.
SELECT (SELECT count(*) FROM corpus.docs WHERE retired_at IS NULL) AS live_texts,
       (SELECT max(started_at) FROM corpus.sync_runs) AS mirror_last_run,
       (SELECT last_seen FROM corner.worker WHERE id = 1) AS desk_last_seen,
       (SELECT count(*) FROM corpus.index_vamsas) AS vamsas,
       (SELECT count(*) FROM corpus.index_dynasties) AS dynasty_rows,
       (SELECT max(synced_at) FROM corpus.index_dynasties) AS dynasties_last_changed,
       (SELECT mode FROM corpus.reader_access WHERE id) AS reader_mode;
