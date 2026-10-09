-- ============================================================
-- C8 checks (CORPUS_MEDIA_C8_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\media_2026-10-09\ and keep it.
--
-- The order:  P1-P3  ->  C8 in one paste  ->  V1-V3  ->  (deploy corpus-media, first desk push)
--             ->  D1-D5.
-- ============================================================


-- ---------------- PREFLIGHT (before C8) ----------------

-- P1 what C8 needs. Expect true | true | true (C4, C5, C7a are in).
SELECT to_regclass('corpus.docs') IS NOT NULL AS c4_docs,
       to_regprocedure('corpus._reader_gate()') IS NOT NULL AS c5_gate,
       'super_admin' = ANY (enum_range(NULL::public.app_role)::text[]) AS c7a_super_admin;

-- P2 nothing of C8 yet. Expect true | true | true | true (if all false, C8 has run: skip it).
SELECT to_regclass('corpus.media') IS NULL AS no_media, to_regclass('corpus.media_files') IS NULL AS no_files,
       to_regclass('corpus.novels') IS NULL AS no_novels, to_regclass('corpus.media_config') IS NULL AS no_config;

-- P3 the texts in the mirror (a picture can travel only for a text that is here). Expect your
--    live documents, e.g. 65, including Mallapurana and nilamata_seg.
SELECT count(*) AS docs_in_mirror,
       bool_or(doc_code = 'Mallapurana') AS mallapurana, bool_or(doc_code = 'nilamata_seg') AS nilamata
FROM corpus.docs WHERE retired_at IS NULL;


-- ---------------- AFTER C8 ----------------

-- V1 the four tables: RLS on, and closed to anon and authenticated. Expect 4 rows:
--    rls true, every other column false.
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select,
       has_table_privilege('authenticated', c.oid, 'INSERT') AS auth_insert
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'corpus' AND c.relname IN ('media', 'media_files', 'novels', 'media_config')
ORDER BY 1;

-- V2 who may call what. Expect 12 rows: the 4 corpus_reader_* with authenticated true, anon false,
--    service false-or-true; the 8 corpus_media_* / corpus_novels_* with service true and
--    authenticated false, anon false. All security_definer true.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args, p.prosecdef AS security_definer,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND (p.proname LIKE 'corpus_reader_media%' OR p.proname IN
      ('corpus_reader_novels', 'corpus_reader_novel', 'corpus_media_state', 'corpus_media_upsert',
       'corpus_novels_upsert', 'corpus_media_retire', 'corpus_media_file_get', 'corpus_media_file_put',
       'corpus_media_config_get', 'corpus_media_config_set'))
ORDER BY 1;

-- V3 the desk's view of the empty store. Expect scheme media.1, your docs, {} {} [] and null.
SELECT public.corpus_media_state();


-- ---------------- AFTER THE FIRST DESK PUSH (python scripts\corpus_media.py --apply) ----------------

-- D1 what is on the site. Expect, as of 2026-10-09: generated approved 17, generated draft 12,
--    cover approved 1, cover draft 1, novel_page draft 20, novel_cast draft 6 (57 in all), and
--    the novels 2 | drawing.
SELECT 'media' AS what, kind, status, count(*) FROM corpus.media WHERE retired_at IS NULL GROUP BY 2, 3
UNION ALL
SELECT 'novels', 'novel', status, count(*) FROM corpus.novels WHERE retired_at IS NULL GROUP BY 3
ORDER BY 1, 2, 3;

-- D2 every picture has both renditions on Drive. Expect 0 rows.
SELECT m.media_key, m.sha256,
       EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'thumb') AS thumb,
       EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'display') AS display
FROM corpus.media m
WHERE m.retired_at IS NULL
  AND NOT (EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'thumb')
       AND EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'display'));

-- D3 the space used on Drive. Expect about 114 files and 14 MB for 57 pictures.
SELECT rendition, count(*) AS files, round(sum(bytes) / 1048576.0, 1) AS mb, max(uploaded_at) AS last_upload
FROM corpus.media_files GROUP BY 1 ORDER BY 1;

-- D4 the Drive folder the pictures went to (created by corpus-media on its first upload, in the
--    Srangam Shared Drive, named "Srangam corpus media"). Expect one row with a Drive id.
SELECT key, value, updated_at FROM corpus.media_config;

-- D5 files on Drive that no live picture uses any more (retired, or replaced by a new version).
--    Nothing is deleted automatically; this is the list to tidy by hand once in a while.
SELECT f.sha256, f.rendition, f.file_id, f.bytes, f.uploaded_at
FROM corpus.media_files f
WHERE NOT EXISTS (SELECT 1 FROM corpus.media m WHERE m.sha256 = f.sha256 AND m.retired_at IS NULL)
ORDER BY f.uploaded_at;
