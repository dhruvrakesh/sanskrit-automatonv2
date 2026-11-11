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
-- S2 takes the writes away from anon and authenticated (they keep SELECT: the catalogue is public knowledge). Nothing
-- is dropped and no row is touched. Undo (one paste):
--   GRANT INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.spatial_ref_sys TO anon, authenticated;
-- If S1 after S2 still says anon_insert true, the table's owner (not the editor's role) made those grants and only it
-- can take them back: then the finding is to be marked accepted in Lovable's security view, with this file's reason.
-- Do NOT run DROP EXTENSION postgis CASCADE: it would drop every column of ours that S1 lists as a geometry.
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
