-- ============================================================
-- C21 checks (C21_INDEX_SITE_2026_10_25): read-only, ONE query per paste in the Lovable Cloud SQL editor.
-- The editor is not a signed-in reader, so the reader functions refuse it (as they should); these read the tables
-- and the catalogue. P1 before C21; V1 and V2 right after it; E1, E2 and E3 after the PC's first
-- python scripts\index_sync.py --apply.
-- ============================================================

-- P1 (before): C5's gate is there (C21 needs it) and C21 not yet.
SELECT to_regprocedure('corpus._reader_gate()') IS NOT NULL AS c5_gate_there,
       to_regclass('corpus.index_persons') IS NOT NULL AS c21_there,
       to_regprocedure('public.corpus_reader_index_tree(text, integer, integer, integer)') IS NOT NULL AS tree_there,
       (SELECT mode FROM corpus.reader_access) AS reader_mode;

-- V1 (after C21): nine functions. The four service ones: service_role only (anon and authenticated false).
-- The five readers: authenticated true, anon false. All SECURITY DEFINER with search_path ''.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_role,
       p.prosecdef AS definer, p.proconfig
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
WHERE p.proname LIKE 'corpus_index_%' OR p.proname LIKE 'corpus_reader_index_%'
ORDER BY p.proname LIKE 'corpus_reader_%', p.proname;

-- V2 (after C21): seven tables, row level security on, no grant to anon or authenticated, and their rows
-- (all 0 until the first --apply).
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS authenticated_select,
       (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM corpus.%I', c.relname), false, true, '')))[1]::text::bigint AS rows,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'corpus'
WHERE c.relkind = 'r' AND c.relname LIKE 'index\_%'
ORDER BY c.relname;

-- E1 (after the first --apply): index by index, what /corpus/genealogies lists. On the 25 Oct desk:
--   inm 3773 persons with a line, 1010 tied to our names, 2909 steps, 0 cited both, 8495 statements, longest 24
--   pui 10147, 2625, 7779, 3580, 12130, 38
--   vei 275, 54, 173, 0, 1396, (no line of six)
-- and the run: 53,628 rows in all (texts 11, persons 14979, steps 10861, statements 22021, lines 53, verses 5702).
SELECT p.source,
       count(*) FILTER (WHERE p.has_line) AS persons_with_a_line,
       count(*) FILTER (WHERE p.canonical IS NOT NULL) AS tied_to_our_names,
       (SELECT count(*) FROM corpus.index_steps s WHERE s.source = p.source) AS steps,
       (SELECT count(*) FROM corpus.index_steps s WHERE s.source = p.source AND s.cited = 'both') AS steps_cited_both,
       (SELECT count(*) FROM corpus.index_statements s WHERE s.source = p.source) AS statements,
       (SELECT max(l.length) FROM corpus.index_lines l WHERE l.source = p.source) AS longest_line,
       (SELECT m.value ->> 'mark' FROM corpus.index_meta m WHERE m.key = 'run') AS mark,
       (SELECT m.synced_at FROM corpus.index_meta m WHERE m.key = 'run') AS synced_at
FROM corpus.index_persons p
GROUP BY p.source
ORDER BY p.source;

-- E2 (after --apply): the longest line of the Purana Index, and how many of its steps rest on a verse that
-- names both persons (the site draws this line on /corpus/genealogies).
SELECT l.source, l.rank, l.length, l.both_steps, l.heads[1] AS eldest, l.heads[array_length(l.heads, 1)] AS youngest,
       array_to_string(l.heads[1:8], ' > ') AS first_eight
FROM corpus.index_lines l
WHERE l.source = 'pui'
ORDER BY l.rank
LIMIT 5;

-- E3 (after --apply): the Mahabharata e-text's words never on the site (both counts 0), and the texts whose
-- verses may be shown (show true: GRETIL, CC BY-NC-SA 4.0; mbh false: references and counts only).
SELECT (SELECT count(*) FROM corpus.index_verses v WHERE v.text = 'mbh') AS mbh_verses,
       (SELECT count(*) FROM corpus.index_steps s WHERE EXISTS (SELECT 1 FROM unnest(s.verse_keys) k
                                                               WHERE k LIKE 'mbh|%')) AS steps_pointing_at_mbh_words,
       (SELECT string_agg(t.code || '=' || t.show, ', ' ORDER BY t.code) FROM corpus.index_texts t
        WHERE t.kind = 'text') AS texts_show;
