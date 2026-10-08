-- ============================================================
-- OPS health (OPS_HEALTH_2026_10_08). Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL
-- editor; Export CSV each result. Nothing here writes, calls a function that writes, or costs.
--
-- What keeps what current:
--   - The mirror (schema corpus): the Windows task SanskritCorpusMirror on the PC, every 2 hours,
--     runs scripts/corpus_sync.py (log: D:\backups\corpus_mirror_log.txt). Not pg_cron.
--   - Its vectors (corpus.passage_vectors): made on the PC by SanskritMaintenance (every 3 hours,
--     only when the dashboard is idle, scripts/build_embeddings.py), then carried by the mirror.
--   - Vectors for PUBLISHED texts (srangam_passage_vectors, for /texts): pg_cron job
--     'srangam-embed-passages-nightly' (04:15 UTC) calls embed-published-passages (C2).
--   - The other nightly jobs: docs/CRON_OPS_PLAYBOOK.md (Srangam repo).
-- pg_net keeps HTTP responses for about 6 hours, so H1's http_status is NULL for a run older than
-- that. The proof of the nightly embed is then H3 and H4 (the artifact), as the playbook says.
-- ============================================================


-- H1 every srangam pg_cron job with its last run (the playbook's audit query).
--    Expect active jobs 1, 2, 6, 7, 8 and 9 (srangam-embed-passages-nightly), cron_status succeeded.
WITH last_run AS (
  SELECT DISTINCT ON (jobid) jobid, status, return_message, start_time, end_time
  FROM cron.job_run_details ORDER BY jobid, start_time DESC
)
SELECT j.jobid, j.jobname, j.schedule, j.active, r.status AS cron_status, r.start_time AS cron_start,
       (SELECT status_code FROM net._http_response
        WHERE created BETWEEN r.start_time AND r.start_time + interval '5 min'
        ORDER BY created DESC LIMIT 1) AS http_status
FROM cron.job j LEFT JOIN last_run r USING (jobid)
WHERE j.jobname LIKE 'srangam-%' ORDER BY j.jobid;

-- H2 the nightly embed job's last 7 runs. Expect one a day at 04:15 UTC, all succeeded.
SELECT d.start_time, d.end_time, d.status, left(d.return_message, 120) AS message
FROM cron.job_run_details d JOIN cron.job j ON j.jobid = d.jobid
WHERE j.jobname = 'srangam-embed-passages-nightly'
ORDER BY d.start_time DESC LIMIT 7;

-- H3 published texts: passages on the site against vectors. Expect passages = vectors for each,
--    and passage_count = passages (after the withheld verses: 1,219 and 446).
SELECT t.doc_code, t.passage_count, count(DISTINCT p.id) AS passages, count(DISTINCT v.passage_id) AS vectors
FROM public.srangam_texts t
LEFT JOIN public.srangam_text_passages p ON p.text_id = t.id
LEFT JOIN public.srangam_passage_vectors v ON v.passage_id = p.id
WHERE t.published
GROUP BY t.doc_code, t.passage_count ORDER BY t.doc_code;

-- H4 what the nightly embed would take next. Expect no rows (nothing pending).
SELECT doc_code, count(*) AS rows_returned, max(total_pending) AS total_pending
FROM public.srangam_passages_to_embed(1000) GROUP BY doc_code;

-- H5 the mirror's last 6 runs (the PC's two-hourly task). Expect a run every ~2 hours, each with
--    finished_at set; summary.stopped = done.
SELECT started_at, finished_at, info->'summary'->>'stopped' AS stopped,
       info->'summary'->>'bytes' AS bytes, info->>'client' AS client
FROM corpus.sync_runs ORDER BY started_at DESC LIMIT 6;

-- H6 the mirror's totals. Expect docs 63+, passages ~75.7k, english ~21.9k, vectors ~21.9k
--    (one vector per translated passage), and vectors >= english - a few.
SELECT count(*) AS docs, sum(passages) AS passages, sum(english) AS english, sum(hindi) AS hindi,
       sum(vectors) AS vectors, sum(stories) AS stories, max(synced_at) AS last_synced
FROM corpus.v_docs;

-- H7 texts whose English has no vector in the mirror yet (expect none, or only texts translated
--    since the last maintenance run).
SELECT doc_code, english, vectors, english - vectors AS missing
FROM corpus.v_docs WHERE english > vectors ORDER BY missing DESC LIMIT 20;

-- H8 the mirror's digests agree with its index (C4b K1). Expect indexed = digested in all 8.
SELECT t, (SELECT count(*) FROM corpus.row_index WHERE tbl = t) AS indexed,
       (SELECT sum(n) FROM corpus.group_digest WHERE tbl = t) AS digested
FROM unnest(ARRAY['docs','entities','passages','translations','mentions','stories','stages','vectors']) t;

-- H9 the database's size (the plan allows for 300-400 MB with the mirror).
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
