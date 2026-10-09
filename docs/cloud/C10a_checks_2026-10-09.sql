-- ============================================================
-- C10a checks (CORNER_STATE_C10A_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\corner_2026-10-09\ and keep it.
--
-- The order:  P1  ->  C10a in one paste  ->  V1-V2  ->  (worker 1.1 on the desk:
--             scripts/patch_corner_worker_state_2026_10_09.py)  ->  D1-D2 whenever you want to see
--             where the desk is with the open requests, and what it says of the mirror.
-- ============================================================


-- ---------------- PREFLIGHT (before C10a) ----------------

-- P1 C9 is there and C10a is not yet. Expect true | true | true | true | false
--    (if has_progress is true, C10a has run: skip it).
SELECT to_regclass('corner.requests') IS NOT NULL AS c9_requests,
       to_regprocedure('public.corner_desk_report(bigint, text, jsonb, text, numeric, text)') IS NOT NULL AS c9_report,
       to_regprocedure('corner._gate()') IS NOT NULL AS c9_gate,
       to_regprocedure('corner._bad(text)') IS NOT NULL AS c9_bad,
       EXISTS (SELECT 1 FROM pg_attribute a
               WHERE a.attrelid = to_regclass('corner.requests') AND a.attname = 'progress'
                 AND NOT a.attisdropped) AS has_progress;


-- ---------------- AFTER C10a ----------------

-- V1 the new column. Expect 1 row: progress | jsonb | true (its check: NULL or an object of at most
--    1000 characters).
SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS type,
       EXISTS (SELECT 1 FROM pg_constraint c
               WHERE c.conrelid = a.attrelid AND c.conname = 'requests_progress_check') AS has_check
FROM pg_attribute a
WHERE a.attrelid = 'corner.requests'::regclass AND a.attname = 'progress' AND NOT a.attisdropped;

-- V2 who may call the two functions. Expect 2 rows, both security_definer true, config
--    {search_path=""}, anon false:
--      corner_desk_report    returns boolean          | authenticated false | service true
--      corner_request_track  returns TABLE(id bigint, status text, decided_at ..., progress jsonb)
--                                                     | authenticated true  | (service as Supabase's
--                                                       defaults give it; the function refuses anyone
--                                                       who is not signed in)
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args, pg_get_function_result(p.oid) AS returns,
       p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname IN ('corner_desk_report', 'corner_request_track')
ORDER BY p.proname;


-- ---------------- ONCE THE DESK RUNS WORKER 1.1 ----------------

-- D1 the open requests and where the desk is with each: step of of, the desk's note, when it said
--    so. A request not taken yet has no progress.
SELECT r.id, r.kind, r.doc_code, r.status, r.claimed_at, r.started_at, now() - r.started_at AS running_for,
       (r.progress ->> 'step')::integer AS step, (r.progress ->> 'of')::integer AS "of",
       r.progress ->> 'note' AS note, r.progress ->> 'at' AS said_at
FROM corner.requests r
WHERE r.status IN ('pending', 'approved', 'claimed', 'running')
ORDER BY r.id;

-- D2 what the desk last said of the mirror and of the picture uploads (its heartbeat). Expect
--    client corner_worker.py 1.1; mirror_ok and media_ok true when the last runs went well.
SELECT w.last_seen, now() - w.last_seen AS ago, w.info ->> 'client' AS client,
       (w.info -> 'sync' -> 'mirror' ->> 'ok') AS mirror_ok, w.info -> 'sync' -> 'mirror' ->> 'at' AS mirror_at,
       w.info -> 'sync' -> 'mirror' ->> 'error' AS mirror_error,
       (w.info -> 'sync' -> 'media' ->> 'ok') AS media_ok, w.info -> 'sync' -> 'media' ->> 'at' AS media_at,
       w.info -> 'sync' -> 'media' ->> 'error' AS media_error, w.info -> 'sync' AS sync
FROM corner.worker w;
