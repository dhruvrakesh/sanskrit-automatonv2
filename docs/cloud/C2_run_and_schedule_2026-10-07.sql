-- EMBED_PUBLISHED_C2_2026_10_07 - run, check and (optionally) schedule the C2 edge function
-- Order: C1 applied (docs/cloud/C1_corpus_brain_2026-10-07.sql, V1-V4) -> embed-published-passages
-- deployed (RUNBOOK, DOCS16) -> these blocks, ONE at a time, in the Lovable Cloud SQL editor.
-- The function is called the way the nightly jobs call theirs: public._cron_invoke_edge() reads
-- CRON_SECRET from vault and adds _cron:true, which _shared/auth-gate.ts requireAdminOrCron accepts.
-- Since S3 only postgres and service_role may call _cron_invoke_edge; the SQL editor runs as postgres.

-- R1. Dry run: nothing embedded, nothing written. Returns a request id.
SELECT public._cron_invoke_edge('embed-published-passages', '{"dry_run": true, "limit": 1000}'::jsonb) AS request_id;

-- R2. The answer (run about 10 seconds after R1 or R3). The newest row is the call just made.
--     Expect status_code 200 and a body with "pending_before":1655 (on 2026-10-07), "dry_run":true.
--     404: the function is not deployed yet.  401/403: the gate refused (CRON_SECRET).
--     500 "GEMINI_API_KEY is not set": add the secret in Lovable Cloud.  500 "srangam_passages_to_embed":
--     C1 is not applied.  502: a batch failed; the body says which and why; re-run R3 to resume.
SELECT id, status_code, timed_out, error_msg, left(content, 2000) AS body, created
FROM net._http_response ORDER BY id DESC LIMIT 3;

-- R3. Embed for real, 500 passages a call (about 30 seconds). Run R3 then R2 until the body shows
--     "pending_after_estimate":0. For 1,655 passages that is four calls; about $0.05 in all.
SELECT public._cron_invoke_edge('embed-published-passages', '{"limit": 500}'::jsonb) AS request_id;

-- R4. Count (read-only). Expect vectors = 1655, one model, dim 1536, and no pending rows.
SELECT count(*) AS vectors, count(DISTINCT model) AS models, min(dim) AS min_dim, max(dim) AS max_dim
FROM public.srangam_passage_vectors;
SELECT doc_code, count(*) AS rows_returned, max(total_pending) AS total_pending
FROM public.srangam_passages_to_embed(1000) GROUP BY doc_code;

-- R5. A real neighbourhood (read-only): passage 60.10 of the Markandeya Purana ("Alas! This is
--     Saivya ...") against everything published. Expect itself first (similarity 1.000), then
--     passages of the same episode (Hariscandra at the cremation ground).
SELECT m.doc_code, m.page_no, m.idx, round(m.similarity::numeric, 3) AS similarity, left(m.translation, 140) AS translation
FROM public.match_text_passages(
       (SELECT v.embedding FROM public.srangam_passage_vectors v
          JOIN public.srangam_text_passages p ON p.id = v.passage_id
          JOIN public.srangam_texts t ON t.id = p.text_id
         WHERE t.doc_code = 'markandeya_purana' AND p.page_no = 60 AND p.idx = 10), 6) AS m;

-- R6. Optional, once R4 shows nothing pending: keep it current every night at 04:15 UTC, after the
--     existing nightly jobs (03:00-04:00). Each run embeds only what is new or changed.
-- SELECT cron.schedule('srangam-embed-passages-nightly', '15 4 * * *',
--        $cron$ SELECT public._cron_invoke_edge('embed-published-passages', '{"limit": 500}'::jsonb); $cron$);
-- Undo: SELECT cron.unschedule('srangam-embed-passages-nightly');
