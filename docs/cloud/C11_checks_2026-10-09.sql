-- ============================================================
-- C11 checks (LEARN_T1_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\learn_2026-10-09\ and keep it.
--
-- The order:  P1-P2  ->  C11 in one paste  ->  V1-V3  ->  D1-D2 whenever you want to see how the
--             team is getting on.
-- ============================================================


-- ---------------- PREFLIGHT (before C11) ----------------

-- P1 what C11 needs (C9, the Researchers' Corner). Expect true | true | true | true | true | true.
SELECT to_regclass('corner.requests') IS NOT NULL AS c9_requests,
       to_regclass('corner.collections') IS NOT NULL AS c9_collections,
       to_regclass('corner.collection_items') IS NOT NULL AS c9_items,
       to_regprocedure('corner._can_request()') IS NOT NULL AS c9_can_request,
       to_regprocedure('corpus._is_editor()') IS NOT NULL AS c8_editor,
       to_regprocedure('corpus._reader_gate()') IS NOT NULL AS c5_gate;

-- P2 nothing of C11 yet. Expect true (if false, C11 has run: re-running it is harmless, it keeps
--    everyone's progress and refreshes the catalogue).
SELECT to_regnamespace('learn') IS NULL AS no_learn_yet;


-- ---------------- AFTER C11 ----------------

-- V1 the two tables: RLS on, closed to anon and authenticated. Expect 2 rows (marks, quests):
--    rls true, the rest false.
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select,
       has_table_privilege('authenticated', c.oid, 'INSERT') AS auth_insert
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'learn' AND c.relkind = 'r'
ORDER BY 1;

-- V2 who may call what. Expect 10 rows: the 4 public.learn_* with security_definer true,
--    anon false, authenticated true; the 6 learn._* helpers false | false | false.
SELECT n.nspname AS schema, p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       p.prosecdef AS security_definer,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'learn' OR (n.nspname = 'public' AND p.proname LIKE 'learn\_%')
ORDER BY 1 DESC, 2;

-- V3 the quest catalogue. Expect find 6 quests 60 XP (self) | read 4, 40 (self) |
--    ask 6, 120 (auto) | make 4, 120 (3 auto, make_print self) | edit 3, 60 (auto, editors only);
--    and the last row: 23 quests, 400 XP (a researcher has 20 and 340).
SELECT x.track, x.quests, x.xp, x.keys
FROM (
  SELECT q.track, count(*) AS quests, sum(q.xp) AS xp,
         string_agg(q.key || ' ' || q.mode || ' ' || q.xp || CASE WHEN q.editors_only THEN ' editors' ELSE '' END,
                    ', ' ORDER BY q.sort) AS keys,
         min(q.sort) AS o
  FROM learn.quests q GROUP BY q.track
  UNION ALL
  SELECT '(all)', count(*), sum(q.xp), 'researchers: ' || count(*) FILTER (WHERE NOT q.editors_only) || ' quests, '
         || sum(q.xp) FILTER (WHERE NOT q.editors_only) || ' XP', 2147483647
  FROM learn.quests q
) x
ORDER BY x.o;


-- ---------------- ONCE PEOPLE USE IT ----------------

-- D1 "I did this" marks per quest (auto quests are never marked: they show 0).
SELECT q.track, q.key, q.mode, count(m.user_id) AS marked, min(m.done_at) AS first, max(m.done_at) AS last
FROM learn.quests q LEFT JOIN learn.marks m ON m.quest = q.key
GROUP BY q.track, q.key, q.mode, q.sort
ORDER BY q.sort;

-- D2 the team's progress: what learn_team() shows an editor, read here without signing in (the
--    members from public.user_roles and auth.users, each person's numbers from the same helpers).
WITH m AS (
  SELECT r.user_id AS uid, array_agg(r.role::text ORDER BY r.role::text) AS roles
  FROM public.user_roles r
  GROUP BY r.user_id
  HAVING bool_or(r.role::text IN ('researcher', 'admin', 'super_admin'))
)
SELECT u.email, m.roles, s.xp, s.level, s.next_level, s.badges, s.quests_done, s.quests_total,
       learn._last_activity(m.uid) AS last_activity
FROM m
LEFT JOIN auth.users u ON u.id = m.uid
CROSS JOIN LATERAL learn._summary(m.uid, 'admin' = ANY (m.roles) OR 'super_admin' = ANY (m.roles)) s
ORDER BY s.xp DESC, u.email NULLS LAST;
