-- ============================================================
-- C27 - Lovable's security finding on public.spatial_ref_sys (C27_SPATIAL_REF_SYS_2026_11_11)
-- docs/ASKS_2026-10-22.md section 18. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: S1 (read-only), then S2 (one
-- paste), then S1 again. Export each result.
--
-- What it is. spatial_ref_sys is PostGIS's own table: the catalogue of coordinate systems (EPSG codes), made by
-- CREATE EXTENSION postgis in the schema the extension was put in. It holds no data of ours. Lovable flags it because
-- it sits in public with row level security off, so the site's API (anon, authenticated) can reach it; what matters is
-- whether they may WRITE it (a changed coordinate system breaks every geometry that uses it).
--
-- S1 says: the extensions and their schemas; the table's owner, RLS and rows; what anon and authenticated may do on
-- it; any geometry or geography column of ours (does the site use PostGIS at all); the public tables without RLS (so
-- the other findings of the same kind show here too).
--
-- S2 was meant to take the writes away from anon and authenticated. It cannot (S1's export of 11 Nov, 17:24, says
-- anon_insert true): supabase_admin owns the table and made those grants, and a role can revoke only its own grants.
-- Postgres then prints "no privileges could be revoked", which the SQL editor does not show. Supabase's own pages say
-- so: "Security Advisor flags spatial_ref_sys and other PostGIS objects in the public schema" and "Revoking privileges
-- on Storage, pg_cron, Vault, and extension objects has no effect" (supabase.com/kb/troubleshooting, 4 Nov 2026). S2
-- did nothing and needs no undo.
--
-- What S1 said (11 Nov): postgis 3.3.7 in public (pg_net and vector in public too); spatial_ref_sys owned by
-- supabase_admin, RLS off, anon and authenticated may insert and update; geo_columns 2 (two columns of ours are
-- PostGIS types); spatial_ref_sys the only public table without RLS.
--
-- Supabase's way out is to move PostGIS into the schema "extensions" (never exposed to the API). With columns of ours
-- of PostGIS types, only Supabase Support can move it without dropping them (here: through Lovable's support, as we
-- reach the database only through Lovable Cloud). Dropping and re-creating it ourselves deletes those columns and their
-- data. Until then: mark the finding accepted in Lovable's security view, with this reason, and run S3 now and then:
-- it says which two columns use PostGIS and whether anyone has written spatial_ref_sys through the API ("inserted"
-- counts PostGIS's own several thousand rows when the statistics were never reset; "updated" or "deleted" above 0
-- is someone's write, and so is srs_4326_and_3857 below 2).
-- Do NOT run DROP EXTENSION postgis CASCADE: it would drop every column of ours that S3 lists.
-- ============================================================

-- ---------- S1 (read-only; before and after S2) ----------
SELECT
  (SELECT string_agg(e.extname || ' ' || e.extversion || ' in ' || n.nspname, '; ' ORDER BY e.extname)
     FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace)                         AS extensions,
  (SELECT pg_get_userbyid(c.relowner) FROM pg_class c
     WHERE c.oid = to_regclass('public.spatial_ref_sys'))                                         AS srs_owner,
  (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = to_regclass('public.spatial_ref_sys'))   AS srs_rls,
  (SELECT c.reltuples::bigint FROM pg_class c WHERE c.oid = to_regclass('public.spatial_ref_sys')) AS srs_rows_about,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'SELECT')                                 AS anon_select,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'INSERT')                                 AS anon_insert,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'UPDATE')                                 AS anon_update,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'DELETE')                                 AS anon_delete,
  has_table_privilege('authenticated', 'public.spatial_ref_sys', 'INSERT')                        AS auth_insert,
  has_table_privilege('authenticated', 'public.spatial_ref_sys', 'UPDATE')                        AS auth_update,
  (SELECT count(*) FROM information_schema.columns
     WHERE udt_name IN ('geometry', 'geography', 'raster')
       AND table_schema NOT IN ('pg_catalog', 'information_schema'))                              AS geo_columns,
  (SELECT string_agg(DISTINCT table_schema || '.' || table_name, ', ') FROM information_schema.columns
     WHERE udt_name IN ('geometry', 'geography', 'raster')
       AND table_schema NOT IN ('pg_catalog', 'information_schema'))                              AS geo_tables,
  (SELECT string_agg(c.relname, ', ' ORDER BY c.relname) FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity)             AS public_tables_without_rls;

-- ---------- S2 (the change: one paste) ----------
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.spatial_ref_sys FROM anon, authenticated;

-- ---------- S3 (read-only: which columns use PostGIS; was spatial_ref_sys written through the API) ----------
SELECT
  (SELECT string_agg(table_schema || '.' || table_name || '.' || column_name || ' ' || udt_name, '; '
                     ORDER BY table_schema, table_name, column_name)
     FROM information_schema.columns
     WHERE udt_name IN ('geometry', 'geography', 'raster')
       AND table_schema NOT IN ('pg_catalog', 'information_schema'))                            AS geo_columns,
  (SELECT n_tup_ins || ' inserted, ' || n_tup_upd || ' updated, ' || n_tup_del || ' deleted'
     FROM pg_stat_all_tables WHERE relid = to_regclass('public.spatial_ref_sys'))               AS srs_writes_since_stats_reset,
  (SELECT count(*) FROM public.spatial_ref_sys)                                                  AS srs_rows,
  (SELECT count(*) FROM public.spatial_ref_sys WHERE srid IN (4326, 3857))                       AS srs_4326_and_3857,
  (SELECT extversion FROM pg_extension WHERE extname = 'postgis')                                AS postgis_version;
