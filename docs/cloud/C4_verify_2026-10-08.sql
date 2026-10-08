-- ============================================================
-- C4 checks after a sync (read-only). CORPUS_MIRROR_C4_2026_10_08
-- Run in the Lovable Cloud SQL editor, one query at a time (the editor shows the last result).
-- ============================================================

-- M1 per document: passages, English, Hindi, vectors, stories (compare with the dashboard's
--    corpus status; the sync's own "verify" line already compares every row's hash):
SELECT * FROM corpus.v_docs ORDER BY passages DESC;

-- M2 the last five runs (finished_at empty = still running, or stopped by --max-mb or an error):
-- SELECT run_id, started_at, finished_at, info->'summary' AS summary, info->>'client' AS client
-- FROM corpus.sync_runs ORDER BY started_at DESC LIMIT 5;

-- M3 totals and size on disk:
-- SELECT (SELECT count(*) FROM corpus.docs WHERE retired_at IS NULL) AS docs,
--        (SELECT count(*) FROM corpus.passages WHERE retired_at IS NULL) AS passages,
--        (SELECT count(*) FROM corpus.passages WHERE retired_at IS NULL AND btrim(coalesce(translation,'')) <> '') AS english,
--        (SELECT count(*) FROM corpus.translations WHERE retired_at IS NULL AND lang = 'hi') AS hindi,
--        (SELECT count(*) FROM corpus.entities WHERE retired_at IS NULL) AS entities,
--        (SELECT count(*) FROM corpus.mentions WHERE retired_at IS NULL) AS mentions,
--        (SELECT count(*) FROM corpus.passage_vectors WHERE retired_at IS NULL) AS vectors,
--        (SELECT count(*) FROM corpus.stories WHERE retired_at IS NULL) AS stories,
--        pg_size_pretty((SELECT sum(pg_total_relation_size(c.oid)) FROM pg_class c
--                        WHERE c.relnamespace = to_regnamespace('corpus') AND c.relkind = 'r')) AS mirror_size,
--        pg_size_pretty(pg_database_size(current_database())) AS database_size;

-- M4 THE VECTOR GATE (run after `corpus_sync.py --apply --tables vectors --doc markandeya_purana`):
--    the mirror's vectors are the local 3,072-dim ones cut to 1,536 and renormalised; the site's
--    are made in the cloud at 1,536 (C2). Same model, task and text, so they should agree.
--    Expect avg_cos >= 0.99 and min_cos >= 0.95; then send all vectors. If lower, stop and keep
--    vectors out of the mirror (--tables without vectors) - see docs/CORPUS_MIRROR_2026-10-08.md.
-- SELECT c.doc_code, count(*) AS pairs,
--        round(avg(1 - (c.embedding <=> v.embedding))::numeric, 4) AS avg_cos,
--        round(min(1 - (c.embedding <=> v.embedding))::numeric, 4) AS min_cos
-- FROM corpus.passage_vectors c
-- JOIN public.srangam_texts t ON t.doc_code = c.doc_code
-- JOIN public.srangam_text_passages p ON p.text_id = t.id AND p.page_no = c.page_no AND p.idx = c.idx
-- JOIN public.srangam_passage_vectors v ON v.passage_id = p.id
-- WHERE c.retired_at IS NULL
-- GROUP BY c.doc_code;

-- M5 word search over the whole corpus (English stemmed, IAST as written):
-- SELECT * FROM corpus.search('cremation ground', 20);

-- M6 meaning search with a stored passage as the question (its nearest neighbours anywhere):
-- SELECT m.doc_code, m.page_no, m.idx, round(m.similarity::numeric, 3) AS similarity, p.verse_ref,
--        left(p.translation, 160) AS translation
-- FROM corpus.passages qp
-- JOIN corpus.passage_vectors q USING (doc_code, page_no, idx)
-- CROSS JOIN LATERAL corpus.match_passages(q.embedding, 8) m
-- JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx
-- WHERE qp.doc_code = 'markandeya_purana' AND qp.verse_ref = '60.10' AND qp.retired_at IS NULL
-- ORDER BY m.similarity DESC;

-- M7 what is still untranslated, per document (the work queue, readable from anywhere):
-- SELECT doc_code, count(*) FILTER (WHERE btrim(coalesce(translation,'')) = '') AS no_english,
--        count(*) AS passages
-- FROM corpus.passages WHERE retired_at IS NULL AND coalesce(text_type, 'mula') NOT IN ('noise', 'frontmatter')
-- GROUP BY doc_code ORDER BY no_english DESC;
