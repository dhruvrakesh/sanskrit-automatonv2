-- SRANGAM_HEAL_S1_2026_10_07
-- Paste ONE numbered block at a time into the Lovable Cloud SQL editor and press Run (the editor shows
-- only the last result). H1, H2 and H4 only read. H3 is the one write: an additive view, verbatim from
-- the repository's own migration supabase/migrations/20260910120000_cross_reference_stats_view.sql
-- (QUERY_CEILING_2026_09_10), which your audit of 2026-10-07 13:19 (Q2) shows was never applied.
-- src/pages/ResearchNetwork.tsx line 148 reads this view; without it the query errors and the page's
-- totals are blank (the code returns null on error). Do NOT insert a row into
-- supabase_migrations.schema_migrations by hand (B1 precedent, docs/CURRENT_STATUS.md 2026-09-08).
--
-- What the audit's Q1 really showed (my expectation "exactly 1 row" was wrong): 55 of the 57 versions
-- listed as "in repo, not recorded" are recorded within 6 seconds of their file name (Lovable records
-- the apply time, the file carries its own timestamp) - the same migrations, not missing ones. The real
-- differences are three: 20260201064547 recorded with no file in the repo (H1 shows what it did),
-- 20260718120000 (B1, applied through the editor on 2026-09-08, verified in Q2), and 20260910120000
-- (this view, never applied).

-- H1. What is the recorded migration that has no file? (read-only)
SELECT version, name, created_by, cardinality(statements) AS n_statements,
       left(statements[1], 600) AS first_statement
FROM supabase_migrations.schema_migrations WHERE version = '20260201064547';

-- H2. Pre-flight for H3 (read-only). Expect: server_version_num >= 150000 (security_invoker views need
--     PostgreSQL 15), 4 columns present, rls_on true, the view absent.
SELECT current_setting('server_version_num')::int AS server_version_num,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'srangam_cross_references'
           AND column_name IN ('reference_type', 'strength', 'source_article_id', 'target_article_id')) AS columns_present,
       (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.srangam_cross_references'::regclass) AS rls_on,
       to_regclass('public.srangam_cross_reference_stats') IS NOT NULL AS view_exists,
       (SELECT count(*) FROM public.srangam_cross_references) AS rows_now;

-- H3. Apply the view (additive; reversible with: DROP VIEW public.srangam_cross_reference_stats;)
create or replace view public.srangam_cross_reference_stats
with (security_invoker = on) as
select
  count(*)::bigint                              as total,
  count(distinct reference_type)::int           as distinct_types,
  round(avg(strength)::numeric, 2)              as avg_strength,
  min(strength)                                 as min_strength,
  max(strength)                                 as max_strength,
  count(*) filter (where strength is null)::int as null_strength,
  count(distinct source_article_id)::int        as source_articles,
  count(distinct target_article_id)::int        as target_articles
from public.srangam_cross_references;

comment on view public.srangam_cross_reference_stats is
  'QUERY_CEILING_2026_09_10. Exact aggregates for /research-network. Replaces '
  'client-side arithmetic over a PostgREST-capped fetch, which reported 1000 '
  'connections, 2 reference types and a mean over an arbitrary thousand rows.';

grant select on public.srangam_cross_reference_stats to anon, authenticated;

-- H4. Verify (read-only). Expect one row; total equals H2 rows_now; then run block_BE_reader.ps1 -Verify,
--     whose STEP 3 asks the same view as an anonymous visitor.
SELECT * FROM public.srangam_cross_reference_stats;
