-- CLOUD_BRAIN_C0_PREFLIGHT_2026_10_07
-- READ-ONLY. Paste ONE numbered query at a time into the Lovable Cloud SQL editor and press Run
-- (the editor shows only the last result). Nothing here writes. Run after (or with) the earlier
-- audit D:\Sanksrit Automatons\_ops_2026-09-10\srangam_migration_audit_2026_10_04.sql (Q1-Q6).

-- P1. pgvector: installed version. halfvec and its HNSW index need 0.7.0 or later.
--     Expect one row; extversion >= 0.7.0. If it is older, C1 uses vector(768) instead of halfvec(768).
SELECT extname, extversion, extnamespace::regnamespace AS schema
FROM pg_extension WHERE extname IN ('vector', 'pg_cron', 'pg_net') ORDER BY extname;

-- P2. Does halfvec exist as a type here? (true/false; false means pgvector < 0.7.0)
SELECT to_regtype('halfvec') IS NOT NULL AS halfvec_available,
       to_regtype('vector')  IS NOT NULL AS vector_available;

-- P3. Nothing of C1 exists yet (all false before C1 is applied).
SELECT 'table srangam_passage_vectors' AS object, to_regclass('public.srangam_passage_vectors') IS NOT NULL AS present
UNION ALL SELECT 'table srangam_stories', to_regclass('public.srangam_stories') IS NOT NULL
UNION ALL SELECT 'function match_text_passages', EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'match_text_passages');

-- P4. What C1 builds on: texts, passages, published share, and the helper functions it reuses.
SELECT (SELECT count(*) FROM public.srangam_texts) AS texts,
       (SELECT count(*) FROM public.srangam_texts WHERE published) AS texts_published,
       (SELECT count(*) FROM public.srangam_text_passages) AS passages,
       EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'srangam_update_updated_at') AS fn_updated_at,
       EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'has_role') AS fn_has_role;

-- P5. Existing vector columns (the article metadata index uses vector(1536); C1 does not touch it).
SELECT c.table_name, c.column_name, format_type(a.atttypid, a.atttypmod) AS type
FROM information_schema.columns c
JOIN pg_attribute a ON a.attrelid = (c.table_schema || '.' || c.table_name)::regclass AND a.attname = c.column_name
WHERE c.table_schema = 'public' AND c.udt_name IN ('vector', 'halfvec') ORDER BY 1, 2;

-- P6. Database size now (Pro includes 8 GB).
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
