-- C20 checks (NAME_LINKS_C20_2026_10_23): read-only, one query per paste in the Lovable Cloud SQL editor.

-- N1. The view's size (expect about 45,000 pairs; about 4,800 in two passages or more).
SELECT count(*) AS pairs, count(*) FILTER (WHERE passages >= 2) AS in_2_passages,
       count(*) FILTER (WHERE texts >= 2) AS in_2_texts FROM corpus.name_links;

-- N2. Janaka's neighbours as the name page will list them (expect Yajnavalkya 33, Videha 29 first).
SELECT CASE WHEN name_a = 'Janaka' THEN name_b ELSE name_a END AS named_with, passages, texts, first_doc, first_page
FROM corpus.name_links WHERE 'Janaka' IN (name_a, name_b) ORDER BY passages DESC LIMIT 12;

-- N3. Who may call the reader function (expect anon false, authenticated true).
SELECT p.oid::regprocedure, has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p WHERE p.proname = 'corpus_reader_name_links';

-- N4. The nightly job (expect one row, 40 4 * * *).
SELECT jobid, jobname, schedule, active FROM cron.job WHERE jobname = 'srangam-corpus-name-links';

-- N5. Its last runs (after a night).
SELECT d.status, d.start_time, d.end_time, left(d.return_message, 120) AS message
FROM cron.job_run_details d JOIN cron.job j ON j.jobid = d.jobid
WHERE j.jobname = 'srangam-corpus-name-links' ORDER BY d.start_time DESC LIMIT 5;
