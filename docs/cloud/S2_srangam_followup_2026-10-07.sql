-- SRANGAM_FOLLOWUP_S2_2026_10_07   (all read-only; paste ONE numbered block at a time, the editor shows
-- only the last result; Export CSV each and keep them)
--
-- What S1 showed (2026-10-07 14:39-14:40):
--   H1  20260201064547 (created_by apikey@lovable.dev, 1 statement, no name) is
--       "Phase 1.3: Batch increment function for cultural terms": CREATE OR REPLACE FUNCTION
--       increment_term_usage_counts(term_names text[]) ... SECURITY DEFINER SET search_path = 'public',
--       then a GRANT EXECUTE (cut at 600 characters). The repo has no file for it, but
--       supabase/migrations/20260517042601_210c7ad5-...sql line 83 (recorded as 20260517042600) revokes
--       EXECUTE on it from PUBLIC, anon and authenticated (RELIABILITY_AUDIT N.7). No edge function in
--       supabase/functions calls it (searched 2026-10-07). G1-G2 confirm the live state.
--   H2  PostgreSQL 170006, 4 columns, RLS on, 1,561 rows, view absent. H3 created the view.
--   H4  as the editor's role: total 1,561, 2 types, avg strength 6.71 (4-10, none null), 48 source and
--       48 target articles.
--   block_BE_reader -Verify, as an anonymous visitor: total 1,392. That is RLS doing its job: the view
--       is security_invoker, and the policy "Public read cross references between published articles"
--       (migration 20260607043411) shows a reference only when BOTH articles are published. G3-G4 show
--       the 169 hidden rows by article status.

-- G1. The whole recorded statement of 20260201064547 (to keep a copy in docs; do NOT add it to
--     supabase/migrations or insert anything into schema_migrations).
SELECT version, created_by, length(statements[1]) AS chars, statements[1] AS full_statement
FROM supabase_migrations.schema_migrations WHERE version = '20260201064547';

-- G2. Who can run increment_term_usage_counts now. Expect anon false, authenticated false,
--     service_role true; security_definer true; search_path pinned.
SELECT p.oid::regprocedure AS function, p.prosecdef AS security_definer, p.proconfig AS settings, p.proacl AS acl,
       has_function_privilege('anon',          p.oid, 'EXECUTE') AS anon_can_execute,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated_can_execute,
       has_function_privilege('service_role',  p.oid, 'EXECUTE') AS service_role_can_execute
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'increment_term_usage_counts';

-- G3. The read policies on srangam_cross_references as they are live.
SELECT policyname, cmd, roles, qual
FROM pg_policies WHERE schemaname = 'public' AND tablename = 'srangam_cross_references'
ORDER BY policyname;

-- G4. The 1,561 references by whether each end is a published article. Expect the (true, true) row to be
--     1,392 (what the public sees); the others are the 169 the public cannot see.
SELECT coalesce(sa.status, '(no article)') AS source_status,
       coalesce(ta.status, '(no article)') AS target_status,
       count(*) AS refs
FROM public.srangam_cross_references r
LEFT JOIN public.srangam_articles sa ON sa.id = r.source_article_id
LEFT JOIN public.srangam_articles ta ON ta.id = r.target_article_id
GROUP BY 1, 2 ORDER BY refs DESC;

-- G5. Every SECURITY DEFINER function in public that anon can still execute (the N.7 lockdown kept
--     has_role and the two search functions on purpose). Anything else listed here is worth a look.
SELECT p.oid::regprocedure AS function, p.proconfig AS settings
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.prosecdef AND has_function_privilege('anon', p.oid, 'EXECUTE')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')   -- not extension-owned
ORDER BY 1;
