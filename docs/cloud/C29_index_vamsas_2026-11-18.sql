-- ============================================================
-- C29 - the vamsas (C29_INDEX_VAMSAS_2026_11_18; the automaton's VAMSA_WAYIN_2026_11_18, Srangam's VAMSA_WAYIN_2026_11_18)
-- docs/ASKS_2026-10-22.md section 35. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 (read-only, before), then the
-- change (one paste, one transaction), then A1 and A3 (read-only, after); A2 after
-- `python scripts\index_sync.py --dynasty-works every --apply`. Export each result.
--
-- Why. Asked on 17 and 18 Nov: "have we made it easy for the user find geneaologies of kings via well known texts and
-- king / vansha names . surya and chandravanshas"; on 18 Nov, night, the way in by Suryavamsa and Candravamsa approved.
-- Measured that night: of the 500 lines on the site (corpus.index_dynasties) only 65 hold a founder of the solar or the
-- lunar line, since each line is one father's longest line in one work; the desk's G6c (vamsa_align.py) draws the same
-- dynasty across the works generation by generation from its founder (10 dynasties, 174 generations, 725 names of 17
-- works), and that is the way in. index_sync.py sends it here, each name tied to its line in corpus.index_dynasties
-- (622 of 725), each generation to Dikshitar's person in the Purana Index (134 of 174) and to Raychaudhuri's claims the
-- site carries already (C23's rule: the public-domain works only).
--
-- What it changes (nothing else is touched; no row of the other tables):
--   corpus.index_vamsas                  (new) one row a dynasty ("solar", "kuru"): its vamsa, founder, works, rows;
--   corpus._index_rel                    C28's, and 'vamsas';
--   public.corpus_index_ingest           a door in front of C28's: 'vamsas' here, every other table to C28's own
--                                        (kept as corpus.corpus_index_ingest_c28, its grants with it);
--   public.corpus_index_manifest         C28's (kept as corpus.corpus_index_manifest_c28), and 'vamsas' with
--                                        {"features": {"vamsas": true}};
--   public.corpus_reader_index_vamsas(p_key)   (new) for signed-in readers (corpus._reader_gate): every dynasty
--                                        without its generations (p_key NULL: the list, light), or one with them.
-- corpus.index_dynasties and public.corpus_reader_index_dynasties(p_work) are not changed.
--
-- Needs C28. Re-running it changes nothing.
-- Rollback (one paste, between a begin and a commit of its own):
--   DROP FUNCTION IF EXISTS public.corpus_reader_index_vamsas(text);
--   DROP FUNCTION IF EXISTS public.corpus_index_ingest(text, jsonb);
--   ALTER FUNCTION corpus.corpus_index_ingest_c28(text, jsonb) SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_ingest_c28(text, jsonb) RENAME TO corpus_index_ingest;
--   DROP FUNCTION IF EXISTS public.corpus_index_manifest();
--   ALTER FUNCTION corpus.corpus_index_manifest_c28() SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_manifest_c28() RENAME TO corpus_index_manifest;
--   DROP TABLE IF EXISTS corpus.index_vamsas;
--   then paste C28's corpus._index_rel.
-- ============================================================

-- B1 (before): C28 is there, C29 not yet. Expected: true, true, false, false.
SELECT to_regclass('corpus.index_dynasties') IS NOT NULL AS c28,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'dynasties')::boolean, false) AS c28_manifest,
       to_regclass('corpus.index_vamsas') IS NOT NULL AS c29,
       to_regprocedure('corpus.corpus_index_ingest_c28(text, jsonb)') IS NOT NULL AS c29_door;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.index_dynasties') IS NULL OR to_regprocedure('corpus.corpus_index_ingest_c26(text, jsonb)') IS NULL THEN
    RAISE EXCEPTION 'C29: C28 comes first. Nothing was changed.';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS corpus.index_vamsas (
    key         TEXT PRIMARY KEY,         -- the dynasty: solar, videha, lunar, yadu, haihaya, kroshtu, turvasu, druhyu, anu, puru, kuru, magadha
    vamsa       TEXT NOT NULL DEFAULT '', -- surya (the solar line and the Videhas) or candra (Pururavas's line and its branches)
    ord         INTEGER NOT NULL DEFAULT 99,  -- the order the desk lists the founders in (vamsa_align.ANCHORS)
    anchor      TEXT NOT NULL DEFAULT '', -- the founder (Iksvaku)
    father      TEXT NOT NULL DEFAULT '', -- his father (Manu)
    title       TEXT NOT NULL DEFAULT '', -- "the solar line (Aiksvakas) from Iksvaku"
    works       JSONB NOT NULL DEFAULT '[]'::jsonb,  -- the works that tell it, in the desk's order
    counts      JSONB NOT NULL DEFAULT '{}'::jsonb,  -- agree, most, differ, one, share_agree (G6c)
    rows        JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{gen, status, name, cells: {work: {name, ref, words, line}}, pui, canonical, ray_name_n, ray_n, ray}]
    names       JSONB NOT NULL DEFAULT '[]'::jsonb,  -- every name the works give it, for finding
    aligned_at  TEXT NOT NULL DEFAULT '', -- when the desk aligned it (vamsa_align.py)
    row_hash    TEXT NOT NULL,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corpus_index_vamsas_vamsa ON corpus.index_vamsas (vamsa, ord);

ALTER TABLE corpus.index_vamsas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON corpus.index_vamsas FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON corpus.index_vamsas FROM anon; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON corpus.index_vamsas FROM authenticated; END IF;
END $$;

CREATE OR REPLACE FUNCTION corpus._index_rel(p_table text) RETURNS regclass
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT CASE p_table
    WHEN 'texts' THEN 'corpus.index_texts'::regclass
    WHEN 'persons' THEN 'corpus.index_persons'::regclass
    WHEN 'steps' THEN 'corpus.index_steps'::regclass
    WHEN 'statements' THEN 'corpus.index_statements'::regclass
    WHEN 'lines' THEN 'corpus.index_lines'::regclass
    WHEN 'verses' THEN 'corpus.index_verses'::regclass
    WHEN 'meta' THEN 'corpus.index_meta'::regclass
    WHEN 'claims' THEN 'corpus.index_claims'::regclass   -- C23_INDEX_CLAIMS_2026_10_28
    WHEN 'dynasties' THEN 'corpus.index_dynasties'::regclass   -- C28_INDEX_DYNASTIES_2026_11_11
    WHEN 'vamsas' THEN 'corpus.index_vamsas'::regclass   -- C29_INDEX_VAMSAS_2026_11_18
  END
$$;

-- C28's ingest and manifest kept as they are, under corpus (their grants go with them), the first time only
DO $$
BEGIN
  IF to_regprocedure('corpus.corpus_index_ingest_c28(text, jsonb)') IS NULL THEN
    ALTER FUNCTION public.corpus_index_ingest(text, jsonb) RENAME TO corpus_index_ingest_c28;
    ALTER FUNCTION public.corpus_index_ingest_c28(text, jsonb) SET SCHEMA corpus;
  END IF;
  IF to_regprocedure('corpus.corpus_index_manifest_c28()') IS NULL THEN
    ALTER FUNCTION public.corpus_index_manifest() RENAME TO corpus_index_manifest_c28;
    ALTER FUNCTION public.corpus_index_manifest_c28() SET SCHEMA corpus;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_ingest(p_table text, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0;
BEGIN
  IF p_table IS DISTINCT FROM 'vamsas' THEN
    RETURN corpus.corpus_index_ingest_c28(p_table, p_rows);   -- every other table as C28 takes it
  END IF;
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_index_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_index_ingest: at most 2000 rows a call'; END IF;
  INSERT INTO corpus.index_vamsas AS t (key, vamsa, ord, anchor, father, title, works, counts, rows, names, aligned_at,
                                        row_hash)
  SELECT x.key, coalesce(x.vamsa, ''), coalesce(x.ord, 99), coalesce(x.anchor, ''), coalesce(x.father, ''),
         coalesce(x.title, ''), coalesce(x.works, '[]'::jsonb), coalesce(x.counts, '{}'::jsonb),
         coalesce(x.rows, '[]'::jsonb), coalesce(x.names, '[]'::jsonb), coalesce(x.aligned_at, ''), x.row_hash
  FROM jsonb_to_recordset(p_rows) AS x(key text, vamsa text, ord integer, anchor text, father text, title text,
                                        works jsonb, counts jsonb, rows jsonb, names jsonb, aligned_at text,
                                        row_hash text)
  ON CONFLICT (key) DO UPDATE SET vamsa = excluded.vamsa, ord = excluded.ord, anchor = excluded.anchor,
    father = excluded.father, title = excluded.title, works = excluded.works, counts = excluded.counts,
    rows = excluded.rows, names = excluded.names, aligned_at = excluded.aligned_at, row_hash = excluded.row_hash,
    synced_at = now()
  WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  GET DIAGNOSTICS n_changed = ROW_COUNT;
  RETURN jsonb_build_object('rows', n_in, 'changed', n_changed);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r jsonb := corpus.corpus_index_manifest_c28(); n bigint; d text;
BEGIN
  SELECT count(*), md5(coalesce(string_agg(key || ':' || row_hash, ',' ORDER BY key COLLATE "C"), ''))
    INTO n, d FROM corpus.index_vamsas;
  -- C29_INDEX_VAMSAS_2026_11_18: the table, and what this site takes beyond C28 (index_sync.py asks before it sends)
  RETURN r || jsonb_build_object('vamsas', jsonb_build_object('n', n, 'digest', d),
                                 'features', coalesce(r -> 'features', '{}'::jsonb)
                                             || jsonb_build_object('vamsas', true));
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_vamsas(p_key text DEFAULT NULL)
RETURNS TABLE (key text, vamsa text, ord integer, anchor text, father text, title text, works jsonb, counts jsonb,
               rows jsonb, names jsonb, aligned_at text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C29_INDEX_VAMSAS_2026_11_18
  RETURN QUERY
  SELECT v.key, v.vamsa, v.ord, v.anchor, v.father, v.title, v.works, v.counts,
         CASE WHEN p_key IS NULL THEN '[]'::jsonb ELSE v.rows END, v.names, v.aligned_at
  FROM corpus.index_vamsas v
  WHERE p_key IS NULL OR v.key = p_key
  ORDER BY v.vamsa DESC, v.ord, v.key;
END $$;

COMMENT ON FUNCTION public.corpus_reader_index_vamsas(text) IS
  'C29_INDEX_VAMSAS_2026_11_18: the dynasties across the works by vamsa (Suryavamsa, Candravamsa); the list without generations, or one dynasty with them (signed-in readers only).';

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
  FOREACH f IN ARRAY ARRAY['corpus.corpus_index_manifest_c28()', 'corpus.corpus_index_ingest_c28(text, jsonb)',
                           'corpus._index_rel(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  f := 'public.corpus_reader_index_vamsas(text)';
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

COMMIT;

-- A1 (after the change): the table, the door, the reader, the manifest's features. Expected: true, true, true, true,
-- true, 0 (517 rows of dynasties stay as they were).
SELECT to_regclass('corpus.index_vamsas') IS NOT NULL AS table_there,
       to_regprocedure('corpus.corpus_index_ingest_c28(text, jsonb)') IS NOT NULL AS c28_ingest_kept,
       to_regprocedure('public.corpus_reader_index_vamsas(text)') IS NOT NULL AS reader_there,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'vamsas')::boolean, false) AS manifest_says_vamsas,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'dynasties')::boolean, false) AS dynasties_still,
       (public.corpus_index_manifest() -> 'vamsas' ->> 'n')::int AS vamsa_rows_now,
       (public.corpus_index_manifest() -> 'dynasties' ->> 'n')::int AS dynasty_rows_now;

-- A2 (after python scripts\index_sync.py --dynasty-works every --apply): the dynasties by vamsa. Expected (18 Nov):
-- surya 1 (solar: 7 works, 14 generations); candra 9 (lunar 13, yadu 14, haihaya 13, kroshtu 39, turvasu 14, druhyu 10,
-- puru 25, kuru 21, magadha 11 generations).
SELECT vamsa, key, anchor, jsonb_array_length(works) AS works, jsonb_array_length(rows) AS generations,
       (SELECT count(*) FROM jsonb_array_elements(rows) g WHERE g ? 'pui') AS with_dikshitar,
       (SELECT count(*) FROM jsonb_array_elements(rows) g WHERE g ? 'ray_name_n') AS with_raychaudhuri,
       pg_column_size(rows) AS bytes, synced_at
FROM corpus.index_vamsas ORDER BY vamsa DESC, ord;

-- A3 (after): who may call what. Expected: false, true, false, false.
SELECT has_function_privilege('anon', 'public.corpus_reader_index_vamsas(text)', 'EXECUTE') AS anon_reads,
       has_function_privilege('authenticated', 'public.corpus_reader_index_vamsas(text)', 'EXECUTE') AS signed_in_reads,
       has_function_privilege('authenticated', 'public.corpus_index_ingest(text, jsonb)', 'EXECUTE') AS signed_in_writes,
       has_function_privilege('anon', 'public.corpus_index_manifest()', 'EXECUTE') AS anon_manifest;
