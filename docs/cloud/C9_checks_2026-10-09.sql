-- ============================================================
-- C9 checks (CORNER_C9_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\corner_2026-10-09\ and keep it.
--
-- The order:  P1-P2  ->  C9 in one paste  ->  V1-V4  ->  (deploy corpus-desk, register the desk task,
--             first request)  ->  D1-D6 whenever you want to see what the Corner has done.
-- ============================================================


-- ---------------- PREFLIGHT (before C9) ----------------

-- P1 what C9 needs. Expect true | true | true | true.
SELECT to_regclass('corpus.media') IS NOT NULL AS c8_media,
       to_regprocedure('corpus._is_editor()') IS NOT NULL AS c8_editor,
       to_regprocedure('public.my_roles()') IS NOT NULL AS c7_roles,
       'researcher' = ANY (enum_range(NULL::public.app_role)::text[]) AS c7a_researcher;

-- P2 nothing of C9 yet. Expect true (if false, C9 has run: skip it).
SELECT to_regnamespace('corner') IS NULL AS no_corner_yet;


-- ---------------- AFTER C9 ----------------

-- V1 the seven tables: RLS on, closed to anon and authenticated. Expect 7 rows: rls true, the rest false.
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select,
       has_table_privilege('authenticated', c.oid, 'INSERT') AS auth_insert
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'corner' AND c.relkind = 'r'
ORDER BY 1;

-- V2 who may call what. Expect 16 rows, all security_definer true, anon false everywhere;
--    authenticated true for the 12 corner_* of the site, service true for the 4 corner_desk_*.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args, p.prosecdef AS security_definer,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname LIKE 'corner\_%'
ORDER BY (p.proname LIKE 'corner\_desk\_%'), p.proname;

-- V3 the request kinds and the settings. Expect 16 kinds (9 paid, 7 editors' decisions) and
--    daily_cap_usd 2.00 | researchers_need_approval true | max_pending_per_person 20.
SELECT 'kind' AS what, kind AS key, label AS value, est_usd::text AS est, cost_bearing::text AS paid,
       editor_only::text AS editors_only
FROM corner.kinds
UNION ALL
SELECT 'setting', key, value, NULL, NULL, NULL FROM corner.settings
ORDER BY 1, 2;

-- V4 the desk's view of the empty queue. Expect scheme corner.1, 0 | 0 | 0, last_seen null.
SELECT public.corner_desk_state();


-- ---------------- ONCE THE CORNER IS IN USE ----------------

-- D1 requests by status.
SELECT status, count(*), round(sum(est_usd), 2) AS est_usd, round(sum(cost_usd), 4) AS cost_usd
FROM corner.requests GROUP BY 1 ORDER BY 1;

-- D2 the last 30 requests: who asked, what, and what the desk said.
SELECT r.id, r.requested_at, u.email AS asked_by, r.kind, r.doc_code, r.params, r.status, r.est_usd, r.cost_usd,
       r.message, r.result
FROM corner.requests r LEFT JOIN auth.users u ON u.id = r.requested_by
ORDER BY r.id DESC LIMIT 30;

-- D3 when the desk last came for work, and what it said about itself (its spend cap and spend).
SELECT last_seen, now() - last_seen AS ago, info FROM corner.worker;

-- D4 today (India time): committed against the cap.
SELECT corner._today() AS today, corner._committed_today() AS committed_usd,
       (SELECT value FROM corner.settings WHERE key = 'daily_cap_usd') AS cap_usd;

-- D5 the anthologies.
SELECT c.id, c.title, c.status, c.audience, u.email AS made_by, c.updated_at, c.published_at,
       (SELECT count(*) FROM corner.collection_items i WHERE i.collection_id = c.id) AS stories
FROM corner.collections c LEFT JOIN auth.users u ON u.id = c.created_by
ORDER BY c.id;

-- D6 the last 50 events.
SELECT e.at, u.email AS actor, e.action, e.request_id, e.collection_id, e.detail
FROM corner.events e LEFT JOIN auth.users u ON u.id = e.actor
ORDER BY e.id DESC LIMIT 50;
