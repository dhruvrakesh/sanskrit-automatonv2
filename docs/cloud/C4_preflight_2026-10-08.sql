-- ============================================================
-- C4 pre-flight (read-only). CORPUS_MIRROR_C4_2026_10_08
-- Run in the Lovable Cloud SQL editor BEFORE C4_corpus_mirror_2026-10-08.sql.
-- Changes nothing. Run P1 and P2 one at a time (the editor shows only the last result).
-- ============================================================

-- P1 (one row per item). Expect: vector 0.8.0 in public, schema corpus absent (false),
--    service_role present (true). Note "database size" before the mirror: C4 adds roughly
--    300-450 MB when the whole corpus is in (docs/CORPUS_MIRROR_2026-10-08.md, "Size").
SELECT 'postgres version' AS item, current_setting('server_version') AS value
UNION ALL SELECT 'database size', pg_size_pretty(pg_database_size(current_database()))
UNION ALL SELECT 'vector extension',
       (SELECT e.extversion || ' in ' || n.nspname FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace WHERE e.extname = 'vector')
UNION ALL SELECT 'schema corpus exists', (to_regnamespace('corpus') IS NOT NULL)::text
UNION ALL SELECT 'function corpus_ingest exists',
       EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'corpus_ingest')::text
UNION ALL SELECT 'role service_role exists', EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role')::text
UNION ALL SELECT 'srangam_text_passages rows', (SELECT count(*)::text FROM public.srangam_text_passages)
UNION ALL SELECT 'srangam_passage_vectors rows', (SELECT count(*)::text FROM public.srangam_passage_vectors);

-- P2 (the ten largest tables today, to see where the space goes):
-- SELECT n.nspname || '.' || c.relname AS relation,
--        pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
--        pg_total_relation_size(c.oid) AS bytes
-- FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
-- WHERE c.relkind IN ('r', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
-- ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 10;
