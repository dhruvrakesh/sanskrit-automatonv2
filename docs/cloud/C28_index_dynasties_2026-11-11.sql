-- ============================================================
-- C28 - the dynasties (C28_INDEX_DYNASTIES_2026_11_11; the automaton's VAMSA_JOIN_2026_11_11, Srangam's DYNASTIES_2026_11_11)
-- docs/ASKS_2026-10-22.md section 21. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 (read-only, before), then the
-- change (one paste, one transaction), then A1 and A3 (read-only, after); A2 after `python scripts\index_sync.py --apply`.
-- Export each result.
--
-- Why. Asked on 10 and 11 Nov: the dynasties, the vamshas, "an API call thing". The genealogy pages draw the indexes'
-- lines (what Sorensen and Dikshitar say of a person). The desk now reads the Puranas' own genealogical books verse by
-- verse (scripts/vamsa_read.py: the Visnupurana's book 4, the Bhagavatapurana's books 9 and 12.1, GRETIL's text) and
-- joins each line's persons to the Purana Index's (scripts/vamsa_join.py): 111 lines of three persons or more, each step
-- with its verse, the Sanskrit words that say it and what the index says of it (on 11 Nov: 990 steps agree with the
-- index, 55 differ, 408 are persons the index has not). index_sync.py sends them here; the Dynasties page reads them.
--
-- What it changes (nothing else is touched; no row of the other tables):
--   corpus.index_dynasties              (new) one row a line ("vip4:1"), one a work ("vip4:0": its counts);
--   corpus._index_rel                   C23's, and 'dynasties';
--   public.corpus_index_ingest          a door in front of C26's: 'dynasties' here, every other table to C26's own
--                                       (kept as corpus.corpus_index_ingest_c26, its grants with it);
--   public.corpus_index_manifest        C26's (kept as corpus.corpus_index_manifest_c26), and 'dynasties' with
--                                       {"features": {"dynasties": true}};
--   public.corpus_reader_index_dynasties(p_work)   (new) the lines, for signed-in readers (corpus._reader_gate).
--
-- Needs C21, C23 and C26. Re-running it changes nothing.
-- Rollback (one paste, between a begin and a commit of its own):
--   DROP FUNCTION IF EXISTS public.corpus_reader_index_dynasties(text);
--   DROP FUNCTION IF EXISTS public.corpus_index_ingest(text, jsonb);
--   ALTER FUNCTION corpus.corpus_index_ingest_c26(text, jsonb) SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_ingest_c26(text, jsonb) RENAME TO corpus_index_ingest;
--   DROP FUNCTION IF EXISTS public.corpus_index_manifest();
--   ALTER FUNCTION corpus.corpus_index_manifest_c26() SET SCHEMA public;
--   ALTER FUNCTION public.corpus_index_manifest_c26() RENAME TO corpus_index_manifest;
--   DROP TABLE IF EXISTS corpus.index_dynasties;
--   then paste C23's corpus._index_rel.
-- ============================================================

-- B1 (before): C21, C23 and C26 are there, C28 not yet. Expected: true, true, true, false.
SELECT to_regclass('corpus.index_persons') IS NOT NULL AS c21,
       to_regclass('corpus.index_claims') IS NOT NULL AS c23,
       EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'corpus' AND table_name = 'index_persons'
               AND column_name = 'same_as') AS c26,
       to_regclass('corpus.index_dynasties') IS NOT NULL AS c28;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.index_persons') IS NULL OR to_regclass('corpus.index_claims') IS NULL
     OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'corpus'
                    AND table_name = 'index_persons' AND column_name = 'same_as') THEN
    RAISE EXCEPTION 'C28: C21, C23 and C26 come first. Nothing was changed.';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS corpus.index_dynasties (
    key        TEXT PRIMARY KEY,         -- work:n (n 0: the work's counts)
    work       TEXT NOT NULL,            -- vip4, bhp9, bhp12
    n          INTEGER NOT NULL,         -- the line's rank in its work, longest first; 0 the work's row
    title      TEXT NOT NULL DEFAULT '',
    text_code  TEXT NOT NULL DEFAULT '', -- the code of the verses' text (vi, bh), as corpus.index_texts
    label      TEXT NOT NULL DEFAULT '', -- the line's name when the text names it ("the Yadavas, after Yadu")
    length     INTEGER NOT NULL DEFAULT 0,
    steps      JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{name, father, ref, words, person, index_head, how, index, joined, page}]
    counts     JSONB NOT NULL DEFAULT '{}'::jsonb,   -- the work's row: persons, found, joined, agrees, differs, new, absent
    source     TEXT NOT NULL DEFAULT '', -- the text's file and its credit (GRETIL, CC BY-NC-SA 4.0)
    row_hash   TEXT NOT NULL,
    synced_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corpus_index_dynasties_work ON corpus.index_dynasties (work, n);

ALTER TABLE corpus.index_dynasties ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON corpus.index_dynasties FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON corpus.index_dynasties FROM anon; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON corpus.index_dynasties FROM authenticated; END IF;
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
  END
$$;

-- C26's ingest and manifest kept as they are, under corpus (their grants go with them), the first time only
DO $$
BEGIN
  IF to_regprocedure('corpus.corpus_index_ingest_c26(text, jsonb)') IS NULL THEN
    ALTER FUNCTION public.corpus_index_ingest(text, jsonb) RENAME TO corpus_index_ingest_c26;
    ALTER FUNCTION public.corpus_index_ingest_c26(text, jsonb) SET SCHEMA corpus;
  END IF;
  IF to_regprocedure('corpus.corpus_index_manifest_c26()') IS NULL THEN
    ALTER FUNCTION public.corpus_index_manifest() RENAME TO corpus_index_manifest_c26;
    ALTER FUNCTION public.corpus_index_manifest_c26() SET SCHEMA corpus;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_ingest(p_table text, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0;
BEGIN
  IF p_table IS DISTINCT FROM 'dynasties' THEN
    RETURN corpus.corpus_index_ingest_c26(p_table, p_rows);   -- every other table as C26 takes it
  END IF;
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_index_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_index_ingest: at most 2000 rows a call'; END IF;
  INSERT INTO corpus.index_dynasties AS t (key, work, n, title, text_code, label, length, steps, counts, source, row_hash)
  SELECT x.key, x.work, x.n, coalesce(x.title, ''), coalesce(x.text_code, ''), coalesce(x.label, ''),
         coalesce(x.length, 0), coalesce(x.steps, '[]'::jsonb), coalesce(x.counts, '{}'::jsonb), coalesce(x.source, ''),
         x.row_hash
  FROM jsonb_to_recordset(p_rows) AS x(key text, work text, n integer, title text, text_code text, label text,
                                        length integer, steps jsonb, counts jsonb, source text, row_hash text)
  ON CONFLICT (key) DO UPDATE SET work = excluded.work, n = excluded.n, title = excluded.title,
    text_code = excluded.text_code, label = excluded.label, length = excluded.length, steps = excluded.steps,
    counts = excluded.counts, source = excluded.source, row_hash = excluded.row_hash, synced_at = now()
  WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  GET DIAGNOSTICS n_changed = ROW_COUNT;
  RETURN jsonb_build_object('rows', n_in, 'changed', n_changed);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r jsonb := corpus.corpus_index_manifest_c26(); n bigint; d text;
BEGIN
  SELECT count(*), md5(coalesce(string_agg(key || ':' || row_hash, ',' ORDER BY key COLLATE "C"), ''))
    INTO n, d FROM corpus.index_dynasties;
  -- C28_INDEX_DYNASTIES_2026_11_11: the table, and what this site takes beyond C26 (index_sync.py asks before it sends)
  RETURN r || jsonb_build_object('dynasties', jsonb_build_object('n', n, 'digest', d),
                                 'features', coalesce(r -> 'features', '{}'::jsonb)
                                             || jsonb_build_object('dynasties', true));
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_dynasties(p_work text DEFAULT NULL)
RETURNS TABLE (key text, work text, n integer, title text, text_code text, label text, length integer, steps jsonb,
               counts jsonb, source text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C28_INDEX_DYNASTIES_2026_11_11
  RETURN QUERY
  SELECT d.key, d.work, d.n, d.title, d.text_code, d.label, d.length, d.steps, d.counts, d.source
  FROM corpus.index_dynasties d
  WHERE p_work IS NULL OR d.work = p_work
  ORDER BY d.work, d.n;
END $$;

COMMENT ON FUNCTION public.corpus_reader_index_dynasties(text) IS
  'C28_INDEX_DYNASTIES_2026_11_11: the Puranas'' own lines, read verse by verse and joined to the Purana Index (signed-in readers only).';

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
  FOREACH f IN ARRAY ARRAY['corpus.corpus_index_manifest_c26()', 'corpus.corpus_index_ingest_c26(text, jsonb)',
                           'corpus._index_rel(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  f := 'public.corpus_reader_index_dynasties(text)';
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

COMMIT;

-- A1 (after the change): the table, the door, the reader, the manifest's feature. Expected: true, true, true, true, 0.
SELECT to_regclass('corpus.index_dynasties') IS NOT NULL AS table_there,
       to_regprocedure('corpus.corpus_index_ingest_c26(text, jsonb)') IS NOT NULL AS c26_ingest_kept,
       to_regprocedure('public.corpus_reader_index_dynasties(text)') IS NOT NULL AS reader_there,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'dynasties')::boolean, false) AS manifest_says_dynasties,
       (public.corpus_index_manifest() -> 'dynasties' ->> 'n')::int AS rows_now;

-- A2 (after python scripts\index_sync.py --apply): the lines by work. Expected (11 Nov): vip4 54 lines, bhp9 50,
-- bhp12 7 (the work's row apart), the longest 29, 27 and 10.
SELECT work, count(*) FILTER (WHERE n > 0) AS lines, max(length) AS longest,
       max(counts ->> 'agrees') FILTER (WHERE n = 0) AS steps_agree,
       max(counts ->> 'absent') FILTER (WHERE n = 0) AS persons_not_in_the_index
FROM corpus.index_dynasties GROUP BY work ORDER BY work;

-- A3 (after): who may call what. Expected: false, true, false, false.
SELECT has_function_privilege('anon', 'public.corpus_reader_index_dynasties(text)', 'EXECUTE') AS anon_reads,
       has_function_privilege('authenticated', 'public.corpus_reader_index_dynasties(text)', 'EXECUTE') AS signed_in_reads,
       has_function_privilege('authenticated', 'public.corpus_index_ingest(text, jsonb)', 'EXECUTE') AS signed_in_writes,
       has_function_privilege('anon', 'public.corpus_index_manifest()', 'EXECUTE') AS anon_manifest;
