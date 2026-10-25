-- ============================================================
-- C22 checks (C22_SCHOLAR_SITE_2026_10_25): read-only, ONE query per paste in the Lovable Cloud SQL editor.
-- The editor is not a signed-in reader, so the reader functions refuse it (as they should); these read the
-- tables the functions read. P1 and E1 before C22; V1, V2, V3, E2 and E3 after.
-- ============================================================

-- P1 (before): C18 is there and C22 not yet; the scholarly rows on the site.
SELECT to_regprocedure('public.corpus_reader_scholar_count(text)') IS NOT NULL AS c18_there,
       to_regprocedure('public.corpus_reader_scholar_docs()') IS NOT NULL AS c22_there,
       (SELECT count(*) FROM corpus.translations WHERE lang = 'en-x-scholar' AND retired_at IS NULL) AS scholar_rows,
       (SELECT count(*) FROM corpus.translations WHERE lang = 'en-x-scholar-meta' AND retired_at IS NULL) AS meta_rows,
       (SELECT count(*) FROM corpus.translations) AS all_translation_rows;

-- E1 (before or after): what the index page will list, text by text (live passages only).
SELECT t.doc_code,
       count(*) FILTER (WHERE t.lang = 'en-x-scholar' AND btrim(coalesce(t.translation, '')) <> '') AS verses,
       count(*) FILTER (WHERE t.lang = 'en-x-scholar-meta') AS meta_rows,
       count(*) FILTER (WHERE t.lang = 'en-x-scholar-meta' AND position('"flag":true' IN coalesce(t.translation, '')) > 0) AS flagged_meta,
       min(t.translated_at) AS first_made, max(t.translated_at) AS last_made
FROM corpus.translations t
JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx AND p.retired_at IS NULL
JOIN corpus.docs d ON d.doc_code = t.doc_code AND d.retired_at IS NULL
WHERE t.retired_at IS NULL AND t.lang IN ('en-x-scholar', 'en-x-scholar-meta')
GROUP BY t.doc_code
ORDER BY 2 DESC, 1;

-- V1 (after): the two functions, for signed-in readers only, SECURITY DEFINER, search_path ''.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       p.prosecdef AS definer, p.proconfig
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
WHERE p.proname IN ('corpus_reader_scholar_docs', 'corpus_reader_scholar_prose', 'corpus_reader_scholar',
                    'corpus_reader_scholar_count')
ORDER BY 1;

-- V2 (after): the partial index is there and valid, and how big it is.
SELECT c.relname, i.indisvalid, pg_size_pretty(pg_relation_size(c.oid)) AS size, pg_get_indexdef(c.oid) AS def
FROM pg_class c JOIN pg_index i ON i.indexrelid = c.oid
WHERE c.relname = 'corpus_translations_scholar';

-- V3 (after): how long the index page's question takes (read the last line, "Execution Time").
EXPLAIN (ANALYZE, BUFFERS)
SELECT t.doc_code, count(*), avg(t.translation_score)
FROM corpus.translations t
JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx AND p.retired_at IS NULL
WHERE t.lang = 'en-x-scholar' AND t.retired_at IS NULL
GROUP BY t.doc_code;

-- E2 (after): the first verses the prose page of the GRETIL Markandeya will read.
SELECT p.page_no, p.idx, p.verse_ref, p.chapter, left(s.translation, 90) AS english,
       left(m.translation, 90) AS meta
FROM corpus.translations m
JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx AND p.retired_at IS NULL
LEFT JOIN corpus.translations s ON s.doc_code = m.doc_code AND s.page_no = m.page_no AND s.idx = m.idx
     AND s.lang = 'en-x-scholar' AND s.retired_at IS NULL
WHERE m.doc_code = 'markandeya_purana__w_gretil' AND m.lang = 'en-x-scholar-meta' AND m.retired_at IS NULL
ORDER BY m.page_no, m.idx
LIMIT 12;

-- E3 (after): the shape of each text's references, which decides how the prose page makes its chapters
-- (two-part references 81.18 on half or more: by the reference; else by the chapter column; else by the page).
SELECT m.doc_code, count(*) AS rows,
       count(*) FILTER (WHERE p.verse_ref ~ '^\D*?\d+\.\d+$') AS two_part,
       count(*) FILTER (WHERE p.verse_ref ~ '^\D*?\d+\.\d+\.\d+$') AS three_part,
       count(*) FILTER (WHERE btrim(coalesce(p.chapter, '')) <> '') AS with_chapter,
       min(p.verse_ref) AS a_ref, max(p.verse_ref) AS another_ref
FROM corpus.translations m
JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx AND p.retired_at IS NULL
WHERE m.lang = 'en-x-scholar-meta' AND m.retired_at IS NULL
GROUP BY m.doc_code
ORDER BY 2 DESC;
