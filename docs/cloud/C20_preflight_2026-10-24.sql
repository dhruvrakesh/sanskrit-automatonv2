-- ============================================================
-- C20 preflight (NAME_LINKS_C20_SPLIT_2026_10_24). Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL editor;
-- export each result (Export CSV) and keep it.
--
-- Why: on 24 Oct the one-paste C20 (C20_name_links_2026-10-23.sql) ended "Query failed - Server error" with no
-- detail, and the transaction rolled back (corpus.name_links does not exist). The same file runs clean on
-- PostgreSQL 16 with pg_cron 1.6 as a role that is not a superuser, so the fault is the site's, not the SQL's:
-- most likely the editor gave up while the view was being filled. C20 is now three short pastes (C20a the
-- definitions, filled with nothing; C20b the fill; C20c the nightly job), and these four queries say first what the
-- site holds and how long the fill takes there.
--
-- The order:  P1, P2, P3, P4  ->  C20a (one paste)  ->  C20b (one statement)  ->  C20c (one statement)
--             ->  C20_checks_2026-10-24.sql V1-V6
-- ============================================================


-- P1 who the editor is, its time limit, and what the view will read. Expect: role postgres; live_mentions in the
--    tens or hundreds of thousands; name_links null (C20 rolled back); gate true; ordinal true.
SELECT current_user AS role, current_setting('statement_timeout') AS statement_timeout,
       (SELECT count(*) FROM corpus.mentions WHERE retired_at IS NULL) AS live_mentions,
       (SELECT count(*) FROM corpus.passages WHERE retired_at IS NULL) AS live_passages,
       to_regclass('corpus.name_links') AS name_links_now,
       to_regprocedure('corpus._reader_gate()') IS NOT NULL AS gate,
       to_regprocedure('corpus._ordinal(text,integer,integer)') IS NOT NULL AS ordinal;


-- P2 pg_cron, and whether this role may schedule. Expect: true, true, true. (A false in the last two: C20c will be
--    refused; C20a and C20b still work, and the refresh can be run by hand.)
SELECT to_regnamespace('cron') IS NOT NULL AS cron_here,
       CASE WHEN to_regnamespace('cron') IS NOT NULL THEN has_schema_privilege('cron', 'USAGE') END AS cron_usage,
       CASE WHEN to_regprocedure('cron.schedule(text,text,text)') IS NOT NULL
            THEN has_function_privilege('cron.schedule(text,text,text)', 'EXECUTE') END AS can_schedule;


-- P3 the jobs already scheduled, and whose they are (expect the nightly jobs of 03:00-04:15; no
--    srangam-corpus-name-links yet).
SELECT jobid, jobname, schedule, active, username FROM cron.job ORDER BY jobname;


-- P4 (NAME_LINKS_FAST_2026_10_24: the fast query; the first one ended "Server error" here on 24 Oct)
--    how long the fill takes on the site: the view's own query, counted, nothing kept. Read the last two lines
--    (Planning Time, Execution Time). Under about 20 seconds: go on to C20a. Longer, or "Server error" here too:
--    stop and send the CSV (the fill then needs to be made in parts).
EXPLAIN (ANALYZE, SUMMARY) SELECT count(*) FROM (
WITH named AS (
  SELECT m.doc_code, m.page_no, m.idx, m.canonical
  FROM corpus.mentions m
  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL
  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE '%-RETIRED'
), few AS (
  SELECT n.doc_code, n.page_no, n.idx, array_agg(n.canonical ORDER BY n.canonical) AS names
  FROM named n
  GROUP BY n.doc_code, n.page_no, n.idx
  HAVING count(*) BETWEEN 2 AND 12
), live AS (
  SELECT f.doc_code, f.page_no, f.idx, f.names FROM few f
  WHERE EXISTS (SELECT 1 FROM corpus.passages p WHERE p.doc_code = f.doc_code AND p.page_no = f.page_no
                AND p.idx = f.idx AND p.retired_at IS NULL)
), pairs AS (
  SELECT x.a AS name_a, y.b AS name_b, l.doc_code, l.page_no, l.idx
  FROM live l
  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS x(a, i)
  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS y(b, j)
  WHERE x.i < y.j
)
SELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,
       (array_agg(doc_code ORDER BY doc_code, page_no, idx))[1] AS first_doc,
       (array_agg(page_no ORDER BY doc_code, page_no, idx))[1] AS first_page,
       (array_agg(idx ORDER BY doc_code, page_no, idx))[1] AS first_idx
FROM pairs
GROUP BY name_a, name_b) z;
