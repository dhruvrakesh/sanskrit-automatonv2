-- ============================================================
-- C13 checks (CORNER_C13_2026_10_10). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\corner_2026-10-10\ and keep it.
--
-- The order:  P1  ->  C13 in one paste  ->  V1-V3  ->  D1 whenever you want the numbers the Corner's
--             strip shows. The site (CORNER_UX_U1_2026_10_10) works before C13 and after it.
-- ============================================================


-- ---------------- PREFLIGHT (before C13) ----------------

-- P1 the five reader functions are C6's and C8's, and C13 is not there yet. Expect 5 rows, each
--    old_line 1 and c13 false, and helper false on every row:
--      corpus_reader_media(text,integer,integer,integer) | 1 | false | false
--      corpus_reader_media_file(text,text)               | 1 | false | false
--      corpus_reader_novel(integer)                      | 1 | false | false
--      corpus_reader_novels(text)                        | 1 | false | false
--      corpus_reader_stories(text,boolean)               | 1 | false | false
--    (c13 true on every row: C13 has run, skip it. Fewer than 5 rows: C6 or C8 is missing, stop.
--    old_line 0 or 2 with c13 false: the function was changed since; C13 would stop and change
--    nothing. Send me that row.)
SELECT p.oid::regprocedure AS fn,
       (length(p.prosrc) - length(replace(p.prosrc,
          CASE WHEN p.proname = 'corpus_reader_stories'
               THEN 'admin := coalesce(public.has_role(auth.uid(), ''admin''::public.app_role), false);'
               ELSE 'editor := corpus._is_editor();' END, '')))
         / length(CASE WHEN p.proname = 'corpus_reader_stories'
               THEN 'admin := coalesce(public.has_role(auth.uid(), ''admin''::public.app_role), false);'
               ELSE 'editor := corpus._is_editor();' END) AS old_line,
       position('CORNER_C13_2026_10_10' IN p.prosrc) > 0 AS c13,
       to_regprocedure('corpus._sees_drafts()') IS NOT NULL AS helper
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('corpus_reader_stories', 'corpus_reader_media', 'corpus_reader_novels', 'corpus_reader_novel',
                    'corpus_reader_media_file')
ORDER BY p.oid::regprocedure::text;


-- ---------------- AFTER C13 ----------------

-- V1 the five reader functions see drafts through the helper, and kept who may call them. Expect 5 rows,
--    each: c13 true | old_line false | security_definer true | config search_path="" | anon false |
--    authenticated true. (The editor may print config as ["search_path=\"\""]: the same thing.)
SELECT p.oid::regprocedure AS fn,
       position('CORNER_C13_2026_10_10' IN p.prosrc) > 0 AS c13,
       (position('corpus._is_editor()' IN p.prosrc) > 0
        OR position('''admin''::public.app_role' IN p.prosrc) > 0) AS old_line,
       p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('corpus_reader_stories', 'corpus_reader_media', 'corpus_reader_novels', 'corpus_reader_novel',
                    'corpus_reader_media_file')
ORDER BY p.oid::regprocedure::text;

-- V2 the two new functions. Expect 2 rows (columns: security_definer, config, public, anon, authenticated):
--      corner_offering()      | true  | search_path="" | false | false | true
--      corpus._sees_drafts()  | false | search_path="" | false | false | false
SELECT p.oid::regprocedure AS fn, p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('public', p.oid, 'EXECUTE') AS public,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE (n.nspname = 'corpus' AND p.proname = '_sees_drafts') OR (n.nspname = 'public' AND p.proname = 'corner_offering')
ORDER BY p.oid::regprocedure::text;

-- V3 who now sees the work in progress besides the editors: the invited researchers. Expect one row
--    per researcher (Kanika, Parth), each with reader_mode signed_in (or readers) and sees_drafts true.
--    (reader_mode admins: only admins read the corpus at all, researchers included out; sees_drafts false.)
SELECT u.email, r.role::text AS role, a.mode AS reader_mode, a.mode IN ('signed_in', 'readers') AS sees_drafts
FROM public.user_roles r
JOIN auth.users u ON u.id = r.user_id
CROSS JOIN LATERAL (SELECT coalesce((SELECT x.mode FROM corpus.reader_access x WHERE x.id), 'admins') AS mode) a
WHERE r.role::text = 'researcher'
ORDER BY u.email;


-- ---------------- ANY TIME ----------------

-- D1 the numbers of the Corner's strip ("the offering so far"), straight from the tables (the SQL
--    editor is not signed in, so corner_offering() itself refuses it; the site calls it).
WITH live AS (SELECT d.doc_code FROM corpus.docs d WHERE d.retired_at IS NULL),
en AS (SELECT p.doc_code, count(*) AS n FROM corpus.passages p JOIN live l USING (doc_code)
       WHERE p.retired_at IS NULL AND btrim(coalesce(p.translation, '')) <> '' GROUP BY p.doc_code),
st AS (SELECT s.doc_code, s.status FROM corpus.stories s JOIN live l USING (doc_code)
       WHERE s.retired_at IS NULL AND coalesce(s.status, '') NOT IN ('retired', 'rejected'))
SELECT (SELECT count(*) FROM en) AS texts,
       (SELECT coalesce(sum(n), 0) FROM en) AS passages_en,
       (SELECT count(*) FROM st WHERE status = 'approved') AS stories_approved,
       (SELECT count(*) FROM st WHERE status = 'draft') AS stories_draft,
       (SELECT count(*) FROM st WHERE status = 'candidate') AS stories_proposed,
       (SELECT count(*) FROM corpus.media m JOIN live l USING (doc_code)
          WHERE m.retired_at IS NULL AND m.novel_id IS NULL AND m.status = 'approved') AS pictures,
       (SELECT count(*) FROM corpus.novels v JOIN live l USING (doc_code)
          WHERE v.retired_at IS NULL AND v.status = 'approved') AS novels,
       (SELECT count(*) FROM corner.collections c WHERE c.status = 'published') AS anthologies,
       (SELECT count(*) FROM en WHERE NOT EXISTS (SELECT 1 FROM st WHERE st.doc_code = en.doc_code)) AS untold,
       (SELECT count(*) FROM corner.requests r WHERE r.status = 'done') AS done_all,
       (SELECT count(*) FROM corner.requests r WHERE r.status = 'done' AND r.finished_at > now() - interval '7 days') AS done_7d;

-- D2 the Corner's email settings as saved (Reply-to is not shown back on the site). Expect
--    mail_enabled true, mail_from Srangam desk <desk@nartiang.org>, mail_reply_to an inbox that
--    receives mail (empty means none), site_url https://srangam.nartiang.org.
SELECT s.key, s.value, s.updated_at
FROM corner.settings s
WHERE s.key IN ('mail_enabled', 'mail_from', 'mail_reply_to', 'site_url')
ORDER BY s.key;
