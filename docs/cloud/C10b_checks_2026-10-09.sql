-- ============================================================
-- C10b checks (CORNER_C10B_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\corner_2026-10-09\ and keep it.
--
-- The order:  (worker 1.2 on the desk: scripts/patch_corner_worker_c10_2026_10_09.py)  ->  P1  ->
--             C10b in one paste  ->  V1-V3  ->  D1 whenever you want to see what was asked of the
--             new kinds and what the desk did. C12 (mail) is independent: its checks are its own.
-- ============================================================


-- ---------------- PREFLIGHT (before C10b) ----------------

-- P1 C9 and C10a are there and C10b is not yet. Expect true | true | true | true | false | false
--    (has_story_edit or has_ideas true: C10b has run, skip it; an error "relation corner.kinds does
--    not exist": C9 is not there, stop).
SELECT to_regclass('corner.kinds') IS NOT NULL AS c9_kinds,
       to_regprocedure('corner._clean(text, text, jsonb)') IS NOT NULL AS c9_clean,
       to_regprocedure('public.corner_request_create(text, text, jsonb, text)') IS NOT NULL AS c9_create,
       to_regprocedure('public.corner_request_track(bigint[])') IS NOT NULL AS c10a_track,
       EXISTS (SELECT 1 FROM corner.kinds k WHERE k.kind = 'story_edit') AS has_story_edit,
       to_regprocedure('public.corner_ideas(text)') IS NOT NULL AS has_ideas;


-- ---------------- AFTER C10b ----------------

-- V1 the kinds: C9's 16 and the 8 new, in the site's order. Expect 24 rows, all enabled true
--    (est_usd as set when each kind was added, unless someone changed one since):
--      kind                 cost_bearing editor_only est_usd unit    sort
--      story_range          true         false       0.0100  request 10
--      story_write          true         false       0.0100  request 20
--      story_edit           false        false       0.0000  request 25    new
--      story_verify         false        false       0.0000  request 26    new
--      story_mine           true         false       0.0100  chunk   30
--      picture_passage      true         false       0.1000  request 40
--      picture_ideas        true         false       0.0200  request 42    new
--      picture_cover        true         false       0.0100  request 44    new
--      picture_draw         true         false       0.1000  request 46    new
--      story_illustrate     true         false       0.1100  request 50
--      picture_redraw       true         false       0.1000  request 60
--      picture_edit         false        false       0.0000  request 65    new
--      novel_plan           true         false       0.0200  request 70
--      novel_cast           true         false       0.4000  request 80
--      novel_draw           true         false       0.1000  page    90
--      story_approve        false        true        0.0000  request 110
--      story_retire         false        true        0.0000  request 120
--      picture_approve      false        true        0.0000  request 130
--      picture_retire       false        true        0.0000  request 140
--      picture_restore      false        true        0.0000  request 145   new
--      novel_page_approve   false        true        0.0000  request 150
--      novel_page_edit      false        false       0.0000  request 155   new
--      novel_approve        false        true        0.0000  request 160
--      novel_retire         false        true        0.0000  request 170
--    In all: 12 paid, 8 for editors only, 4 free for researchers too.
SELECT k.kind, k.label, k.cost_bearing, k.editor_only, k.est_usd, k.unit, k.sort, k.enabled
FROM corner.kinds k
ORDER BY k.sort, k.kind;

-- V2 who may call the two new functions. Expect 2 rows, both security_definer true, config
--    {search_path=""}, anon false, authenticated true (service as Supabase's defaults give it; the
--    functions refuse anyone who is not signed in):
--      corner_ideas             p_doc text | TABLE(image_id integer, kind text, title text, brief text,
--                                            at text, request_id bigint, asked_at timestamp with time
--                                            zone, drawn boolean, draw_request_id bigint, draw_status text)
--      corner_retired_pictures  p_doc text | TABLE(image_id integer, kind text, title text, caption_en
--                                            text, retired_at timestamp with time zone, has_file boolean)
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args, pg_get_function_result(p.oid) AS returns,
       p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname IN ('corner_ideas', 'corner_retired_pictures')
ORDER BY p.proname;

-- V3 the two helpers C10b replaced: still the owner's only, and C10b's (not C9's again). Expect 2 rows:
--      corner._clean(text,text,jsonb)     | false | {search_path=""} | false | false | false | true
--      corner._estimate(text,text,jsonb)  | false | {search_path=""} | false | false | false | true
--    (c10b false: a re-run of C9 put C9's back; paste C10b again).
SELECT p.oid::regprocedure AS fn, p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('public', p.oid, 'EXECUTE') AS public,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       position('CORNER_C10B_2026_10_09' IN p.prosrc) > 0 AS c10b
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'corner' AND p.proname IN ('_clean', '_estimate')
ORDER BY p.proname;


-- ---------------- ONCE THE NEW KINDS ARE IN USE ----------------

-- D1 the requests of the new kinds (and the novels' "draw again"), open or done, newest first: who
--    asked, what, and what the desk said. No rows until someone asks for one of them.
SELECT r.id, r.requested_at, u.email AS asked_by, r.kind, r.doc_code, r.params, r.status, r.est_usd, r.cost_usd,
       r.finished_at, r.message, r.result
FROM corner.requests r LEFT JOIN auth.users u ON u.id = r.requested_by
WHERE (r.kind IN ('story_edit', 'story_verify', 'picture_ideas', 'picture_cover', 'picture_draw', 'picture_edit',
                  'picture_restore', 'novel_page_edit')
       OR (r.kind IN ('novel_cast', 'novel_draw') AND r.params ->> 'redo' = 'true'))
  AND r.status IN ('pending', 'approved', 'claimed', 'running', 'done')
ORDER BY r.id DESC
LIMIT 50;
