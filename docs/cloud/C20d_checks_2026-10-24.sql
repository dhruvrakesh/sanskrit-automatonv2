-- ============================================================
-- C20d checks (NAME_LINKS_FAST_2026_10_24). Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL editor; export
-- each result (Export CSV). The order: C20d -> F1 -> C20b -> F1, F2 -> C20_checks_2026-10-24.sql V2, V3, V4, V5.
-- ============================================================


-- F1 the view is the fast one, and whether it is filled. After C20d: fast_query true, filled false. After C20b:
--    filled true.
SELECT position('WITH ORDINALITY' IN pg_get_viewdef('corpus.name_links'::regclass)) > 0 AS fast_query,
       (SELECT c.relispopulated FROM pg_class c WHERE c.oid = 'corpus.name_links'::regclass) AS filled;


-- F2 the nightly job with its own limit (expect one row: 40 4 * * *, the command beginning
--    SET statement_timeout = '5min', active true; the same jobid as before, 10 on 24 Oct).
SELECT jobid, jobname, schedule, command, active FROM cron.job WHERE jobname = 'srangam-corpus-name-links';
