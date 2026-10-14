-- ============================================================
-- C15 checks (C15_READER_GUARD_2026_10_14). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) and keep it.
--
-- The order:  L1, L2 (what the meaning search could return now)  ->  P1  ->  C15 in one paste  ->  V1
--             ->  L1, L2 again after the mirror run that retires what it held (corpus_sync.py
--             --allow-mass-retire, the texts named; docs/PROVISIONAL_2026-10-14.md).
-- ============================================================


-- ---------------- WHAT THE SEARCH COULD RETURN ----------------

-- L1 live vectors whose passage is retired: Ask the corpus could answer with a retired passage's English
--    until C15 (or until the mirror retires the vector). Expect no rows once the held vectors are retired.
SELECT v.doc_code, count(*) AS live_vectors_on_retired_passages
FROM corpus.passage_vectors v
JOIN corpus.passages p ON p.doc_code = v.doc_code AND p.page_no = v.page_no AND p.idx = v.idx
WHERE v.retired_at IS NULL AND p.retired_at IS NOT NULL
GROUP BY v.doc_code
ORDER BY 2 DESC, 1;


-- L2 live vectors on a live passage with no English: a vector of the old English, at a key a re-ingest gave
--    to a new, untranslated passage. Expect no rows once the held vectors are retired.
SELECT v.doc_code, count(*) AS live_vectors_without_english
FROM corpus.passage_vectors v
JOIN corpus.passages p ON p.doc_code = v.doc_code AND p.page_no = v.page_no AND p.idx = v.idx
WHERE v.retired_at IS NULL AND p.retired_at IS NULL AND btrim(coalesce(p.translation, '')) = ''
GROUP BY v.doc_code
ORDER BY 2 DESC, 1;


-- ---------------- PREFLIGHT (before C15) ----------------

-- P1 the two functions are C5's. Expect 2 rows, each join_line 1, c15 false and is_c5 true:
--      corpus_reader_match(halfvec,integer,text[])           | 1 | false | true
--      corpus_reader_similar(text,integer,integer,integer)   | 1 | false | true
--    (c15 true: C15 has run, skip it. join_line 0 or is_c5 false: the function was changed since; C15
--    would stop and change nothing. Send me that row.)
SELECT p.oid::regprocedure AS fn,
       (length(p.prosrc) - length(replace(p.prosrc,
          'JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx', '')))
         / length('JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx')
         AS join_line,
       position('C15_READER_GUARD_2026_10_14' IN p.prosrc) > 0 AS c15,
       md5(p.prosrc) IN ('b4644a53040bf51047cd7331fdf2f245', '7454409020c0abfd5c7a33ae2118d46b',
                         'a100917dc7b45b37da6ef95b33caf1c8', '8b8417f0514bcd89c826a11a4c065c22') AS is_c5
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname IN ('corpus_reader_match', 'corpus_reader_similar')
ORDER BY p.oid::regprocedure::text;


-- ---------------- AFTER C15 ----------------

-- V1 both rewritten, as they were in every other way. Expect 2 rows, each c15 true, security_definer true,
--    config {search_path=""} and signed_in_may_call true.
SELECT p.oid::regprocedure AS fn,
       position('C15_READER_GUARD_2026_10_14' IN p.prosrc) > 0 AS c15,
       p.prosecdef AS security_definer, p.proconfig AS config,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS signed_in_may_call
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname IN ('corpus_reader_match', 'corpus_reader_similar')
ORDER BY p.oid::regprocedure::text;
