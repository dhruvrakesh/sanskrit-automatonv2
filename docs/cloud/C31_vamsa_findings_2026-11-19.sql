-- ============================================================
-- C31 - our findings on the vamsa page (C31_VAMSA_FINDINGS_2026_11_19; the automaton's VAMSA_FINDINGS_SITE_2026_11_19,
-- Srangam's VAMSA_FINDINGS_SITE_2026_11_19)
-- docs/ASKS_2026-10-22.md section 38. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 (read-only, before), then the
-- change (one paste, one transaction), then A1 and A3 (read-only, after); A2 after
-- `python scripts\index_sync.py --dynasty-works every --apply`. Export each result.
--
-- Why. Asked on 18 and 19 Nov: "the geneaologies work should carry tool tips and reference to dikshitar, raychaudhary,
-- bc law and any analyses built from iterative , statistical analysis of their works". On 19 Nov the desk's R1
-- (vamsa_findings.py) read the ten dynasties with the three scholars' notes (49 findings proposed, $0.24); each was read
-- against its verses and a person approved 20 and dropped 29. This puts the approved ones beside their dynasty on the
-- vamsa page, each in our own words, each citation resolved for a reader: a generation, a verse, a second name a text
-- states, Dikshitar's person, Raychaudhuri's claim (public domain; the claims the site carries already, C23's rule) and
-- B. C. Law's page only (his book is in copyright: his words never leave the desk).
--
-- What it changes (nothing else is touched; no row of any table):
--   corpus.index_vamsas.findings         (new column, default []) the approved findings of the dynasty;
--   public.corpus_index_ingest           a door in front of C29's: 'vamsas' here with the findings, every other table
--                                        to C29's own (kept as corpus.corpus_index_ingest_c29, its grants with it);
--   public.corpus_index_manifest         C29's (kept as corpus.corpus_index_manifest_c29), and
--                                        {"features": {"vamsa_findings": true}} (the desk sends the findings only then);
--   public.corpus_reader_index_vamsa_findings()   (new) for signed-in readers (corpus._reader_gate): the dynasties that
--                                        have approved findings, with them.
-- public.corpus_reader_index_vamsas(text) and the other tables are not changed.
--
-- Needs C29. Re-running it changes nothing.
-- Rollback (one paste, between a begin and a commit of its own):
--   DROP FUNCTION IF EXISTS public.corpus_reader_index_vamsa_findings();
--   DROP FUNCTION IF EXISTS public.corpus_index_ingest(text, jsonb);
--   ALTER FUNCTION corpus.corpus_index_ingest_c29(text, jsonb) SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_ingest_c29(text, jsonb) RENAME TO corpus_index_ingest;
--   DROP FUNCTION IF EXISTS public.corpus_index_manifest();
--   ALTER FUNCTION corpus.corpus_index_manifest_c29() SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_manifest_c29() RENAME TO corpus_index_manifest;
--   ALTER TABLE corpus.index_vamsas DROP COLUMN IF EXISTS findings;
-- ============================================================

-- B1 (before): C29 is there, C31 not yet. Expected: true, true, false, false, false.
SELECT to_regclass('corpus.index_vamsas') IS NOT NULL AS c29,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'vamsas')::boolean, false) AS c29_manifest,
       EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'corpus' AND table_name = 'index_vamsas' AND column_name = 'findings') AS c31_column,
       to_regprocedure('corpus.corpus_index_ingest_c29(text, jsonb)') IS NOT NULL AS c31_door,
       to_regprocedure('public.corpus_reader_index_vamsa_findings()') IS NOT NULL AS c31_reader;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.index_vamsas') IS NULL OR to_regprocedure('corpus.corpus_index_ingest_c28(text, jsonb)') IS NULL THEN
    RAISE EXCEPTION 'C31: C29 comes first. Nothing was changed.';
  END IF;
END $$;

ALTER TABLE corpus.index_vamsas ADD COLUMN IF NOT EXISTS findings JSONB NOT NULL DEFAULT '[]'::jsonb;
COMMENT ON COLUMN corpus.index_vamsas.findings IS
  'C31_VAMSA_FINDINGS_2026_11_19: the findings a person approved (R1), in our own words; citations: gen, verse, second, index, ray (claim), law (page only)';

-- C29's ingest and manifest kept as they are, under corpus (their grants go with them), the first time only
DO $$
BEGIN
  IF to_regprocedure('corpus.corpus_index_ingest_c29(text, jsonb)') IS NULL THEN
    ALTER FUNCTION public.corpus_index_ingest(text, jsonb) RENAME TO corpus_index_ingest_c29;
    ALTER FUNCTION public.corpus_index_ingest_c29(text, jsonb) SET SCHEMA corpus;
  END IF;
  IF to_regprocedure('corpus.corpus_index_manifest_c29()') IS NULL THEN
    ALTER FUNCTION public.corpus_index_manifest() RENAME TO corpus_index_manifest_c29;
    ALTER FUNCTION public.corpus_index_manifest_c29() SET SCHEMA corpus;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_ingest(p_table text, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0;
BEGIN
  IF p_table IS DISTINCT FROM 'vamsas' THEN
    RETURN corpus.corpus_index_ingest_c29(p_table, p_rows);   -- every other table as C29 (and C28) take it
  END IF;
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_index_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_index_ingest: at most 2000 rows a call'; END IF;
  INSERT INTO corpus.index_vamsas AS t (key, vamsa, ord, anchor, father, title, works, counts, rows, names, aligned_at,
                                        findings, row_hash)
  SELECT x.key, coalesce(x.vamsa, ''), coalesce(x.ord, 99), coalesce(x.anchor, ''), coalesce(x.father, ''),
         coalesce(x.title, ''), coalesce(x.works, '[]'::jsonb), coalesce(x.counts, '{}'::jsonb),
         coalesce(x.rows, '[]'::jsonb), coalesce(x.names, '[]'::jsonb), coalesce(x.aligned_at, ''),
         CASE WHEN jsonb_typeof(x.findings) = 'array' THEN x.findings ELSE '[]'::jsonb END, x.row_hash
  FROM jsonb_to_recordset(p_rows) AS x(key text, vamsa text, ord integer, anchor text, father text, title text,
                                        works jsonb, counts jsonb, rows jsonb, names jsonb, aligned_at text,
                                        findings jsonb, row_hash text)
  ON CONFLICT (key) DO UPDATE SET vamsa = excluded.vamsa, ord = excluded.ord, anchor = excluded.anchor,
    father = excluded.father, title = excluded.title, works = excluded.works, counts = excluded.counts,
    rows = excluded.rows, names = excluded.names, aligned_at = excluded.aligned_at, findings = excluded.findings,
    row_hash = excluded.row_hash, synced_at = now()
  WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  GET DIAGNOSTICS n_changed = ROW_COUNT;
  RETURN jsonb_build_object('rows', n_in, 'changed', n_changed);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r jsonb := corpus.corpus_index_manifest_c29();
BEGIN
  -- C31_VAMSA_FINDINGS_2026_11_19: what this site takes beyond C29 (index_sync.py asks before it sends the findings)
  RETURN r || jsonb_build_object('features', coalesce(r -> 'features', '{}'::jsonb)
                                             || jsonb_build_object('vamsa_findings', true));
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_vamsa_findings()
RETURNS TABLE (key text, vamsa text, ord integer, title text, findings jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C31_VAMSA_FINDINGS_2026_11_19
  RETURN QUERY
  SELECT v.key, v.vamsa, v.ord, v.title, v.findings
  FROM corpus.index_vamsas v
  WHERE jsonb_typeof(v.findings) = 'array' AND jsonb_array_length(v.findings) > 0
  ORDER BY v.vamsa DESC, v.ord, v.key;
END $$;

COMMENT ON FUNCTION public.corpus_reader_index_vamsa_findings() IS
  'C31_VAMSA_FINDINGS_2026_11_19: our findings a person approved, by dynasty, with their citations (signed-in readers only).';

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_index_manifest()', 'public.corpus_index_ingest(text, jsonb)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f); END IF;
  END LOOP;
  FOREACH f IN ARRAY ARRAY['corpus.corpus_index_manifest_c29()', 'corpus.corpus_index_ingest_c29(text, jsonb)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  f := 'public.corpus_reader_index_vamsa_findings()';
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

COMMIT;

-- A1 (after the change): the column, the door, the reader, the manifest's features. Expected: true, true, true, true,
-- true, 10, 0 (the findings come with the next send).
SELECT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'corpus' AND table_name = 'index_vamsas' AND column_name = 'findings') AS column_there,
       to_regprocedure('corpus.corpus_index_ingest_c29(text, jsonb)') IS NOT NULL AS c29_ingest_kept,
       to_regprocedure('public.corpus_reader_index_vamsa_findings()') IS NOT NULL AS reader_there,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'vamsa_findings')::boolean, false) AS manifest_says_findings,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'vamsas')::boolean, false) AS vamsas_still,
       (public.corpus_index_manifest() -> 'vamsas' ->> 'n')::int AS vamsa_rows_now,
       (SELECT count(*) FROM corpus.index_vamsas WHERE jsonb_array_length(findings) > 0) AS dynasties_with_findings;

-- A2 (after python scripts\index_sync.py --dynasty-works every --apply): the approved findings by dynasty, and that no
-- citation of B. C. Law carries more than his page. Expected (19 Nov): solar 4, lunar 1, haihaya 4, kroshtu 3,
-- turvasu 1, druhyu 2, puru 2, kuru 2, magadha 1 (20 in all; yadu none); law_with_words 0 on every row.
SELECT v.vamsa, v.key, jsonb_array_length(v.findings) AS findings,
       (SELECT string_agg(DISTINCT f ->> 'kind', ', ') FROM jsonb_array_elements(v.findings) f) AS kinds,
       (SELECT count(*) FROM jsonb_array_elements(v.findings) f, jsonb_array_elements(f -> 'cites') c) AS citations,
       (SELECT count(*) FROM jsonb_array_elements(v.findings) f, jsonb_array_elements(f -> 'cites') c
        WHERE c ->> 't' = 'law' AND (SELECT count(*) FROM jsonb_object_keys(c)) > 2) AS law_with_words,
       v.synced_at
FROM corpus.index_vamsas v ORDER BY v.vamsa DESC, v.ord;

-- A3 (after): who may call what. Expected: false, true, false, false.
SELECT has_function_privilege('anon', 'public.corpus_reader_index_vamsa_findings()', 'EXECUTE') AS anon_reads,
       has_function_privilege('authenticated', 'public.corpus_reader_index_vamsa_findings()', 'EXECUTE') AS signed_in_reads,
       has_function_privilege('authenticated', 'public.corpus_index_ingest(text, jsonb)', 'EXECUTE') AS signed_in_writes,
       has_function_privilege('anon', 'public.corpus_index_manifest()', 'EXECUTE') AS anon_manifest;
