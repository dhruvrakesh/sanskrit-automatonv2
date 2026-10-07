-- SRANGAM_LOCKDOWN_S3_2026_10_07
-- Paste ONE numbered block at a time into the Lovable Cloud SQL editor. L1 and L3-L5 only read.
-- L2 is the one write: it removes EXECUTE from roles that were never meant to have it. It creates,
-- drops and changes nothing else. Undo is in L6 (commented out).
--
-- WHY (S2 G5, 2026-10-07 15:06): an anonymous visitor can execute four SECURITY DEFINER functions that
-- the repo's own migrations meant to keep private:
--   _cron_invoke_edge(text, jsonb)   reads CRON_SECRET from vault and POSTs to any edge function with
--       the x-cron-secret header (and a 120 s timeout). Created 20260531075801 with
--       "REVOKE ALL ... FROM PUBLIC, anon, authenticated; GRANT EXECUTE ... TO postgres, service_role";
--       recreated by 20260531083133 / ...083825 / ...084140 / 20260602113931 with only
--       "REVOKE ALL ... FROM PUBLIC". Supabase's default privileges grant EXECUTE on new functions to
--       anon and authenticated by name, so revoking from PUBLIC alone leaves both able to call it
--       through /rest/v1/rpc. Callers in the repo: the SECURITY DEFINER enqueuers (run as their owner)
--       and pg_cron (runs as postgres). No call from src/ or supabase/functions.
--   reconcile_stuck_admin_jobs()     marks running admin jobs failed after 5 minutes without a
--       heartbeat. 20260528160242: "REVOKE ALL ... FROM PUBLIC; GRANT EXECUTE ... TO service_role".
--       Called by pg_cron job 1 (srangam-admin-jobs-watchdog, every 5 minutes, as postgres).
--   get_corpus_correlations(int,int) and get_corpus_correlations_v2(int,int,numeric x5): read
--       correlations across ALL articles, drafts included (SECURITY DEFINER bypasses RLS). Their
--       migrations grant authenticated + service_role only; comment: "admin-only at UI layer".
--       Callers: src/pages/admin/CorpusCorrelations.tsx (signed in) and edge function correlate-corpus
--       (service role). Authenticated stays as designed; only anon is removed.
-- Kept public on purpose (RELIABILITY_AUDIT N.7): has_role, srangam_search_articles_fulltext,
-- srangam_search_articles_semantic.

-- L1. Before (read-only). Expect anon_can_execute = true on all four rows.
SELECT p.oid::regprocedure AS function,
       has_function_privilege('anon',          p.oid, 'EXECUTE') AS anon_can_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated_can_execute,
       has_function_privilege('service_role',  p.oid, 'EXECUTE') AS service_role_can_execute,
       pg_get_userbyid(p.proowner) AS owner, p.proacl AS acl
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('_cron_invoke_edge', 'reconcile_stuck_admin_jobs', 'get_corpus_correlations',
                    'get_corpus_correlations_v2')
ORDER BY 1;

-- L2. Apply (one transaction; all or nothing).
BEGIN;
REVOKE EXECUTE ON FUNCTION public._cron_invoke_edge(text, jsonb)          FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public._cron_invoke_edge(text, jsonb)          TO postgres, service_role;
REVOKE EXECUTE ON FUNCTION public.reconcile_stuck_admin_jobs()            FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.reconcile_stuck_admin_jobs()            TO postgres, service_role;
REVOKE EXECUTE ON FUNCTION public.get_corpus_correlations(integer, integer) FROM PUBLIC, anon;
REVOKE EXECUTE ON FUNCTION public.get_corpus_correlations_v2(integer, integer, numeric, numeric, numeric, numeric, numeric)
       FROM PUBLIC, anon;
COMMIT;

-- L3. After (read-only). Expect: anon false on all four; authenticated false on the first two and true
--     on the two correlation functions; service_role true on all four.
SELECT p.oid::regprocedure AS function,
       has_function_privilege('anon',          p.oid, 'EXECUTE') AS anon_can_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated_can_execute,
       has_function_privilege('service_role',  p.oid, 'EXECUTE') AS service_role_can_execute
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('_cron_invoke_edge', 'reconcile_stuck_admin_jobs', 'get_corpus_correlations',
                    'get_corpus_correlations_v2')
ORDER BY 1;

-- L4. The G5 check again (read-only). Expect exactly: has_role, srangam_search_articles_fulltext,
--     srangam_search_articles_semantic. Keep this query; re-run it after any Lovable change that adds
--     a function, because the default privileges will grant anon EXECUTE again on anything new.
SELECT p.oid::regprocedure AS function, p.proconfig AS settings
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.prosecdef AND has_function_privilege('anon', p.oid, 'EXECUTE')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
ORDER BY 1;

-- L5. Scheduled jobs still succeed (read-only). Run 10 minutes after L2: the watchdog (job 1) runs
--     every 5 minutes; the nightly jobs (2, 6, 7, 8) run 03:00-04:00 UTC, so look again tomorrow.
SELECT j.jobid, j.jobname, d.status, d.return_message, d.start_time
FROM cron.job_run_details d JOIN cron.job j ON j.jobid = d.jobid
WHERE d.start_time > now() - interval '30 minutes' OR (j.jobid <> 1 AND d.start_time > now() - interval '1 day')
ORDER BY d.start_time DESC LIMIT 20;

-- L6. Undo (only if L5 shows a job failing with "permission denied for function ..."):
-- BEGIN;
-- GRANT EXECUTE ON FUNCTION public._cron_invoke_edge(text, jsonb) TO authenticated;
-- GRANT EXECUTE ON FUNCTION public.reconcile_stuck_admin_jobs() TO authenticated;
-- COMMIT;
-- (anon is not given back: nothing in the repo calls these as an anonymous visitor.)
