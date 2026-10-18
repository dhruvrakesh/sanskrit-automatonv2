-- ============================================================
-- C18 checks (C18_READER_SCHOLAR_2026_10_18). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) and keep it.
--
-- The order:  E1 (what the site holds now)  ->  P1  ->  C18 in one paste  ->  V1, V2
--             then, after the mirror has run with SCHOLAR_MIRROR_2026_10_18:  E1 again, E2
-- ============================================================


-- ---------------- WHAT THE SITE HOLDS ----------------

-- E1 the scholarly English on the site, text by text. Before the mirror runs with SCHOLAR_MIRROR_2026_10_18: no rows.
--    After it: MBh01 and the Tantrabhidhana first (they are live); markandeya_purana__w_gretil once it is adopted
--    (repair_text.py --release). en-x-scholar is the verses with an English; en-x-scholar-meta is one more for each
--    verse of a sentence given with the verse before it.
SELECT t.doc_code, t.lang, count(*) AS rows, max(t.synced_at) AS last_synced
FROM corpus.translations t
WHERE t.retired_at IS NULL AND t.lang LIKE 'en-x-scholar%'
GROUP BY 1, 2
ORDER BY 1, 2;


-- E2 a sample, as the reader will show it (the editor reads the tables as their owner).
SELECT s.doc_code, s.page_no, s.idx, left(s.translation, 90) AS english, s.translation_score AS fidelity,
       s.translation_qa AS fluency, m.translation::jsonb ->> 'status' AS status, m.translation::jsonb ->> 'flag' AS flag,
       jsonb_array_length(coalesce(m.translation::jsonb -> 'notes', '[]'::jsonb)) AS notes
FROM corpus.translations s
JOIN corpus.translations m ON m.doc_code = s.doc_code AND m.page_no = s.page_no AND m.idx = s.idx
 AND m.lang = 'en-x-scholar-meta' AND m.retired_at IS NULL
WHERE s.lang = 'en-x-scholar' AND s.retired_at IS NULL
ORDER BY s.doc_code, s.page_no, s.idx
LIMIT 12;


-- ---------------- PREFLIGHT (before C18) ----------------

-- P1 the reader's gate is there and the new functions are not yet. Expect: gate true, scholar false, count false.
--    (true, true: C18 has run; pasting it again changes nothing.)
SELECT to_regprocedure('corpus._reader_gate()') IS NOT NULL AS gate,
       to_regprocedure('public.corpus_reader_scholar(text, integer, integer)') IS NOT NULL AS scholar,
       to_regprocedure('public.corpus_reader_scholar_count(text)') IS NOT NULL AS count;


-- ---------------- AFTER C18 ----------------

-- V1 who may call them. Expect two rows: anon false, authenticated true, definer true, search_path {search_path=""}.
SELECT p.oid::regprocedure AS fn,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       p.prosecdef AS definer, p.proconfig AS search_path
FROM pg_proc p
WHERE p.proname IN ('corpus_reader_scholar', 'corpus_reader_scholar_count')
ORDER BY 1;


-- V2 the editor is not a signed-in reader, so this is refused there, by design:
--    expect "The working corpus is open to signed-in readers only." The reader (signed in) gets the rows.
SELECT * FROM public.corpus_reader_scholar('MBh01', 0, 50);
