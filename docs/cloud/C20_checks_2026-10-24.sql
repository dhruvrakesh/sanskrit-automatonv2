-- ============================================================
-- C20 checks (NAME_LINKS_C20_SPLIT_2026_10_24). Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL editor;
-- export each result (Export CSV) and keep it. They replace C20_checks_2026-10-23.sql.
-- The order: C20_preflight P1-P4 -> C20a -> V1 -> C20b -> V1, V2, V3, V4 -> C20c -> V5; after a night, V6.
-- ============================================================


-- V1 the definitions, and whether the view is filled. After C20a: view corpus.name_links, filled false, refresh true,
--    reader true. After C20b: filled true.
SELECT to_regclass('corpus.name_links') AS view,
       (SELECT c.relispopulated FROM pg_class c WHERE c.oid = to_regclass('corpus.name_links')) AS filled,
       to_regprocedure('corpus._refresh_name_links()') IS NOT NULL AS refresh,
       to_regprocedure('public.corpus_reader_name_links(text,integer)') IS NOT NULL AS reader;


-- V2 the view's size (expect about 45,000 pairs; about 4,800 in two passages or more; about 1,500 in two texts or
--    more: on 23 Oct the site's own count was 45,183, 4,822 and 1,516).
SELECT count(*) AS pairs, count(*) FILTER (WHERE passages >= 2) AS in_2_passages,
       count(*) FILTER (WHERE texts >= 2) AS in_2_texts, count(*) FILTER (WHERE texts >= 5) AS in_5_texts
FROM corpus.name_links;


-- V3 Janaka's neighbours as the name page will list them (Yajnavalkya and Videha first).
SELECT CASE WHEN name_a = 'Janaka' THEN name_b ELSE name_a END AS named_with, passages, texts, first_doc, first_page
FROM corpus.name_links WHERE 'Janaka' IN (name_a, name_b) ORDER BY passages DESC LIMIT 12;


-- V4 who may call what (expect the reader: anon false, authenticated true; the refresh: false, false).
SELECT p.oid::regprocedure AS function, has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p WHERE p.proname IN ('corpus_reader_name_links', '_refresh_name_links') ORDER BY 1;


-- V5 the nightly job (expect one row: 40 4 * * *, active true).
SELECT jobid, jobname, schedule, active, username FROM cron.job WHERE jobname = 'srangam-corpus-name-links';


-- V6 its last runs (after a night: status succeeded).
SELECT d.status, d.start_time, d.end_time, left(d.return_message, 120) AS message
FROM cron.job_run_details d JOIN cron.job j ON j.jobid = d.jobid
WHERE j.jobname = 'srangam-corpus-name-links' ORDER BY d.start_time DESC LIMIT 5;
