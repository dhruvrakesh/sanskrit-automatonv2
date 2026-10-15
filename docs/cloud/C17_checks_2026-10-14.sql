-- ============================================================
-- C17 checks (C17_READER_SOURCES_2026_10_14). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) and keep it.
--
-- The order:  E1 (what the site holds now)  ->  P1  ->  C17 in one paste  ->  V1, V2
-- ============================================================


-- ---------------- WHAT THE SITE HOLDS ----------------

-- E1 where the live passages' Sanskrit comes from, text by text, with their quality. After the 14 Oct
--    mirror run MBh01 should read: gretil-bori-etext | 6957 (7197 once its prose is in) | 0.980 | 0.
--    A text whose engine is empty went in before the engine was recorded.
SELECT p.doc_code, coalesce(p.ocr_engine, '(not recorded)') AS ocr_engine, count(*) AS passages,
       round(avg(p.quality_score)::numeric, 3) AS mean_quality,
       count(*) FILTER (WHERE p.quality_score > 0 AND p.quality_score < 0.5) AS marked_hard_to_read
FROM corpus.passages p
WHERE p.retired_at IS NULL
GROUP BY 1, 2
ORDER BY 1, 3 DESC;


-- ---------------- PREFLIGHT (before C17) ----------------

-- P1 the reader's gate is there and the new function is not yet. Expect: gate true, sources false.
--    (sources true: C17 has run; pasting it again changes nothing.)
SELECT to_regprocedure('corpus._reader_gate()') IS NOT NULL AS gate,
       to_regprocedure('public.corpus_reader_sources(text)') IS NOT NULL AS sources;


-- ---------------- AFTER C17 ----------------

-- V1 who may call it. Expect one row: anon false, authenticated true, definer true, search_path {search_path=""}.
SELECT p.oid::regprocedure AS fn,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       p.prosecdef AS definer, p.proconfig AS search_path
FROM pg_proc p
WHERE p.proname = 'corpus_reader_sources';


-- V2 the editor is not a signed-in reader, so this is refused there, by design:
--    expect "The working corpus is open to signed-in readers only." The reader (signed in) gets the rows.
SELECT * FROM public.corpus_reader_sources('MBh01');
