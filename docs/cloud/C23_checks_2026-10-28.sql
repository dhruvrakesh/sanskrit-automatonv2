-- ============================================================
-- C23 and C24 checks (C23_INDEX_CLAIMS_2026_10_28, C24_SCHOLAR_SEARCH_2026_10_28): read-only, ONE query per paste
-- in the Lovable Cloud SQL editor. The editor is not a signed-in reader, so the reader functions refuse it (as they
-- should); these read the tables and the catalogue. P1 before C23; V1, V2 and V3 right after C23 and C24; E1, E2 and
-- E3 after the PC's python scripts\index_sync.py --apply (once corpus-index is deployed again); S1 any time after C24.
-- ============================================================

-- P1 (before): C21 and C22 are there, C23 and C24 not yet. Want: c21_there, c22_there true; c23_there, c24_there
-- false; reader_mode readers.
SELECT to_regclass('corpus.index_statements') IS NOT NULL AS c21_there,
       to_regprocedure('public.corpus_reader_scholar_docs()') IS NOT NULL AS c22_there,
       to_regclass('corpus.index_claims') IS NOT NULL AS c23_there,
       to_regprocedure('public.corpus_reader_scholar_search(text, integer, text)') IS NOT NULL AS c24_there,
       (SELECT mode FROM corpus.reader_access) AS reader_mode;

-- V1 (after C23 and C24): the public functions. The four service ones (corpus_index_*): service_role only. The six
-- readers (corpus_reader_index_* and corpus_reader_scholar_search): authenticated true, anon false. All SECURITY
-- DEFINER with search_path "". Ten rows.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_role,
       p.prosecdef AS definer, p.proconfig
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
WHERE p.proname LIKE 'corpus_index_%' OR p.proname LIKE 'corpus_reader_index_%'
   OR p.proname = 'corpus_reader_scholar_search'
ORDER BY p.proname LIKE 'corpus_reader_%', p.proname;

-- V2 (after C23): the corpus helpers no one but the definers may call (anon and authenticated false), and the
-- manifest names the claims (claims_listed true).
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       p.proconfig,
       (SELECT pg_get_functiondef(m.oid) LIKE '%''claims''%' FROM pg_proc m
          JOIN pg_namespace mn ON mn.oid = m.pronamespace AND mn.nspname = 'public'
         WHERE m.proname = 'corpus_index_manifest') AS claims_listed
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'corpus'
WHERE p.proname IN ('_index_claim', '_index_statement', '_index_step', '_index_rel', '_scholar_fts')
ORDER BY p.proname;

-- V3 (after C23 and C24): eight index_ tables (index_claims new), row level security on, no grant to anon or
-- authenticated; the two new columns; the new search index. claims 0 until the first --apply after the deploy.
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS authenticated_select,
       (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM corpus.%I', c.relname), false, true, '')))[1]::text::bigint AS rows,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
       (SELECT string_agg(a.attname || ' ' || format_type(a.atttypid, a.atttypmod), ', ')
          FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname IN ('scholars', 'scholar') AND NOT a.attisdropped)
         AS new_columns,
       (SELECT to_regclass('corpus.corpus_translations_scholar_fts') IS NOT NULL) AS scholar_search_index
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'corpus'
WHERE c.relkind = 'r' AND c.relname LIKE 'index\_%'
ORDER BY c.relname;

-- E1 (after --apply): the claims. On the 28 Oct desk: one work (phai1923), 1904 claims (exact 1675, close 229),
-- 894 with the subject tied to one name of ours, 613 with the object tied; 953 citing a text; statements with a
-- scholar's view 253 (agrees 184, differs 68, reversed 1: inm 160, vei 53, pui 40); steps 62 (agrees 51, differs 11).
SELECT w.code AS work, w.show, left(w.rights, 60) AS rights,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code) AS claims,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code AND c.quote_check = 'exact') AS exact,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code AND c.quote_check = 'close') AS close,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code AND c.subject_canonical IS NOT NULL) AS subject_tied,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code AND c.object_canonical IS NOT NULL) AS object_tied,
       (SELECT count(*) FROM corpus.index_claims c WHERE c.work = w.code AND jsonb_array_length(c.cites) > 0) AS citing,
       (SELECT string_agg(v || '=' || n, ', ' ORDER BY v) FROM (
          SELECT x ->> 'verdict' AS v, count(*) AS n FROM corpus.index_statements s, jsonb_array_elements(s.scholars) x
          WHERE x ->> 'work' = w.code GROUP BY 1) q) AS statements_by_verdict,
       (SELECT string_agg(source || '=' || n, ', ' ORDER BY source) FROM (
          SELECT s.source, count(*) AS n FROM corpus.index_statements s
          WHERE jsonb_array_length(s.scholars) > 0 GROUP BY 1) q) AS statements_by_index,
       (SELECT string_agg(scholar || '=' || n, ', ' ORDER BY scholar) FROM (
          SELECT s.scholar, count(*) AS n FROM corpus.index_steps s WHERE s.scholar <> '' GROUP BY 1) q) AS steps_by_verdict
FROM corpus.index_texts w
WHERE w.kind = 'work'
ORDER BY w.code;

-- E2 (after --apply): every claim key a statement points at is there (missing 0), and ten of the views beside the
-- book's words, as /corpus/genealogies shows them.
SELECT (SELECT count(*) FROM corpus.index_statements s, jsonb_array_elements(s.scholars) x,
               jsonb_array_elements_text(x -> 'claims') k
        WHERE NOT EXISTS (SELECT 1 FROM corpus.index_claims c WHERE c.key = k)) AS missing_claims,
       s.source, s.subject, s.relation, s.object, x ->> 'verdict' AS verdict, x ->> 'note' AS note,
       c.key AS claim, c.printed, left(c.quote, 120) AS quote
FROM corpus.index_statements s
CROSS JOIN LATERAL jsonb_array_elements(s.scholars) x
LEFT JOIN corpus.index_claims c ON c.key = x -> 'claims' ->> 0
ORDER BY x ->> 'verdict' DESC, s.source, s.subject
LIMIT 10;

-- E3 (after --apply): the names the book speaks of most, as the "In our corpus" panel counts them.
SELECT name, count(*) AS claims, count(DISTINCT work) AS works
FROM (SELECT work, subject_canonical AS name FROM corpus.index_claims WHERE subject_canonical IS NOT NULL
      UNION ALL
      SELECT work, object_canonical FROM corpus.index_claims WHERE object_canonical IS NOT NULL) q
GROUP BY name
ORDER BY count(*) DESC, name
LIMIT 15;

-- S1 (after C24): the scholarly English that the new search reads, text by text, and how many verses a sample
-- search finds there (the same match the reader function makes; the editor cannot call the function itself).
SELECT t.doc_code, d.title, d.retired_at IS NULL AS live_text,
       count(*) AS scholarly_verses,
       count(*) FILTER (WHERE corpus._scholar_fts(t.translation) @@
                              (websearch_to_tsquery('pg_catalog.english', 'king') ||
                               websearch_to_tsquery('pg_catalog.simple', 'king'))) AS with_king
FROM corpus.translations t
LEFT JOIN corpus.docs d ON d.doc_code = t.doc_code
WHERE t.lang = 'en-x-scholar' AND t.retired_at IS NULL
GROUP BY t.doc_code, d.title, d.retired_at
ORDER BY t.doc_code;
