-- ============================================================
-- C4b - the mirror's digests without full scans (docs/CORPUS_MIRROR_2026-10-08.md, "C4b")
-- CORPUS_MIRROR_C4B_2026_10_08
--
-- Why: after all 21,931 vectors were in, the sync's last step failed with
--   corpus_manifest: canceling statement due to statement timeout
-- corpus_manifest() (C4) re-read every row of every mirror table (passages with their search
-- column, vectors at 3 KB each) and sorted all keys, on every call. Every later run would fail at
-- its first call, so the mirror would stop following the PC.
--
-- What changes:
--   1. corpus.row_index (table, group, key, row_hash) - one narrow row per live mirror row, and
--      corpus.group_digest (table, group, count, s1, s2) - running sums, kept current by
--      corpus_ingest() and corpus_retire() in the same statement as the change they record.
--   2. The digest is now order-free: count:sum1:sum2, where each row adds the two halves of
--      md5(key || ' ' || row_hash) as 64-bit numbers, modulo 2^64. A change subtracts the old
--      row's share and adds the new one, so no call ever needs to read a whole table again.
--      corpus_manifest() returns {"_scheme": "sum64.1", ...}; corpus_sync.py 4.2 checks it.
--   3. corpus_keys() reads row_index (an index range), not the wide tables.
--   4. Writers take one advisory lock, so two runs at once cannot double-count a change. Every row
--      of an ingested batch is recorded in the index (changed or not), so re-sending a row heals a
--      missing index entry, and a batch that names a key twice is refused.
--   5. corpus._rebuild_index(table) recomputes one table's index and digests from the rows
--      themselves (once now, and whenever a check says so).
-- Signatures, grants and the edge function are unchanged.
--
-- HOW TO APPLY (Lovable Cloud SQL editor):
--   A. Paste this whole file and run it once. It is safe to run again.
--   B. Then fill the index, ONE statement at a time (each reads one table once):
--        SELECT corpus._rebuild_index('docs');
--        SELECT corpus._rebuild_index('entities');
--        SELECT corpus._rebuild_index('passages');
--        SELECT corpus._rebuild_index('translations');
--        SELECT corpus._rebuild_index('mentions');
--        SELECT corpus._rebuild_index('stories');
--        SELECT corpus._rebuild_index('stages');
--        SELECT corpus._rebuild_index('vectors');
--      Each answers {"table": ..., "rows": N, "groups": G}.
--   C. Run the checks at the end (K1-K3).
-- Until B is done the manifest reports empty tables and a sync would re-send everything, so run B
-- before the next sync (the scheduled tick included).
--
-- Tested 2026-10-08 on PostgreSQL 16 + pgvector 0.8.0 on top of C4, with a full-size mirror
-- (75,720 passages, 22,040 vectors): see tests/test_corpus_sync_pg_2026_10_08.py.
-- Rollback: re-run C4_corpus_mirror_2026-10-08.sql (its functions replace these), then
--   DROP TABLE corpus.row_index, corpus.group_digest;
--   DROP FUNCTION corpus._h64(text, integer), corpus._index_apply(text, jsonb),
--                 corpus._index_remove(text, jsonb), corpus._rebuild_index(text), corpus._digest(bigint, numeric, numeric),
--                 corpus._batch_keys(text, jsonb);
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS corpus.row_index (
    tbl       TEXT NOT NULL,
    grp       TEXT NOT NULL,
    k         TEXT NOT NULL,
    row_hash  TEXT NOT NULL,
    PRIMARY KEY (tbl, grp, k)
);
CREATE TABLE IF NOT EXISTS corpus.group_digest (
    tbl  TEXT NOT NULL,
    grp  TEXT NOT NULL,
    n    BIGINT NOT NULL DEFAULT 0,
    s1   NUMERIC NOT NULL DEFAULT 0,
    s2   NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY (tbl, grp)
);
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['row_index', 'group_digest'] LOOP
    EXECUTE format('ALTER TABLE corpus.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corpus.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- Half `part` (0 or 1) of md5(t) as a signed 64-bit number. Sums are taken modulo 2^64, so the
-- sign does not matter: corpus_sync.py adds the same halves unsigned and gets the same digest.
CREATE OR REPLACE FUNCTION corpus._h64(t text, part integer)
RETURNS numeric LANGUAGE sql IMMUTABLE STRICT SET search_path = '' AS $$
  SELECT (('x' || substr(md5(t), part * 16 + 1, 16))::bit(64)::bigint)::numeric
$$;

CREATE OR REPLACE FUNCTION corpus._digest(n bigint, s1 numeric, s2 numeric)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT n::text || ':' ||
         mod(mod(s1, 18446744073709551616::numeric) + 18446744073709551616::numeric, 18446744073709551616::numeric)::text || ':' ||
         mod(mod(s2, 18446744073709551616::numeric) + 18446744073709551616::numeric, 18446744073709551616::numeric)::text
$$;

-- Record changed rows [[group, key, row_hash], ...] of one table: index upsert and digest delta in
-- one statement (every part of it sees the index as it was before the statement).
CREATE OR REPLACE FUNCTION corpus._index_apply(p_table text, p_changed jsonb)
RETURNS void LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
  IF p_changed IS NULL OR jsonb_array_length(p_changed) = 0 THEN RETURN; END IF;
  WITH c AS (
    SELECT x->>0 AS grp, x->>1 AS k, x->>2 AS h FROM jsonb_array_elements(p_changed) x),
  prev AS (
    SELECT ri.grp, ri.k, ri.row_hash AS h FROM corpus.row_index ri
    JOIN c ON ri.tbl = p_table AND ri.grp = c.grp AND ri.k = c.k),
  ins AS (
    INSERT INTO corpus.row_index AS ri (tbl, grp, k, row_hash)
    SELECT p_table, grp, k, h FROM c
    ON CONFLICT (tbl, grp, k) DO UPDATE SET row_hash = EXCLUDED.row_hash
      WHERE ri.row_hash IS DISTINCT FROM EXCLUDED.row_hash
    RETURNING 1),
  d AS (
    SELECT grp, sum(dn) AS dn, sum(a) AS a, sum(b) AS b FROM (
      SELECT grp, 1 AS dn, corpus._h64(k || ' ' || h, 0) AS a, corpus._h64(k || ' ' || h, 1) AS b FROM c
      UNION ALL
      SELECT grp, -1, -corpus._h64(k || ' ' || h, 0), -corpus._h64(k || ' ' || h, 1) FROM prev) z
    GROUP BY grp)
  INSERT INTO corpus.group_digest AS g (tbl, grp, n, s1, s2)
  SELECT p_table, grp, dn, a, b FROM d
  ON CONFLICT (tbl, grp) DO UPDATE SET n = g.n + EXCLUDED.n, s1 = g.s1 + EXCLUDED.s1, s2 = g.s2 + EXCLUDED.s2;
END $$;

-- Record retired rows [[group, key], ...]: drop them from the index and their share from the digest.
CREATE OR REPLACE FUNCTION corpus._index_remove(p_table text, p_removed jsonb)
RETURNS void LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
  IF p_removed IS NULL OR jsonb_array_length(p_removed) = 0 THEN RETURN; END IF;
  WITH c AS (
    SELECT x->>0 AS grp, x->>1 AS k FROM jsonb_array_elements(p_removed) x),
  del AS (
    DELETE FROM corpus.row_index ri USING c
    WHERE ri.tbl = p_table AND ri.grp = c.grp AND ri.k = c.k
    RETURNING ri.grp, ri.k, ri.row_hash),
  d AS (
    SELECT grp, count(*) AS dn, sum(corpus._h64(k || ' ' || row_hash, 0)) AS a,
           sum(corpus._h64(k || ' ' || row_hash, 1)) AS b
    FROM del GROUP BY grp)
  UPDATE corpus.group_digest g SET n = g.n - d.dn, s1 = g.s1 - d.a, s2 = g.s2 - d.b
  FROM d WHERE g.tbl = p_table AND g.grp = d.grp;
END $$;

-- Recompute one table's index and digests from its live rows (step B, and whenever K2 differs).
CREATE OR REPLACE FUNCTION corpus._rebuild_index(p_table text)
RETURNS jsonb LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE s record; n_rows bigint; n_groups bigint;
BEGIN
  SELECT * INTO s FROM corpus._spec(p_table);
  IF s.rel IS NULL THEN RAISE EXCEPTION 'corpus._rebuild_index: unknown table %', p_table; END IF;
  PERFORM pg_advisory_xact_lock(4242001);
  DELETE FROM corpus.row_index WHERE tbl = p_table;
  EXECUTE format('INSERT INTO corpus.row_index (tbl, grp, k, row_hash) '
                 'SELECT $1, %s, %s, row_hash FROM %s WHERE retired_at IS NULL', s.grp, s.k, s.rel)
  USING p_table;
  GET DIAGNOSTICS n_rows = ROW_COUNT;
  DELETE FROM corpus.group_digest WHERE tbl = p_table;
  INSERT INTO corpus.group_digest (tbl, grp, n, s1, s2)
  SELECT p_table, grp, count(*), sum(corpus._h64(k || ' ' || row_hash, 0)), sum(corpus._h64(k || ' ' || row_hash, 1))
  FROM corpus.row_index WHERE tbl = p_table GROUP BY grp;
  GET DIAGNOSTICS n_groups = ROW_COUNT;
  RETURN jsonb_build_object('table', p_table, 'rows', n_rows, 'groups', n_groups);
END $$;

-- The manifest from the running sums: a few hundred small rows, no table scan.
CREATE OR REPLACE FUNCTION public.corpus_manifest(p_tables text[] DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE t text; part jsonb; result jsonb := jsonb_build_object('_scheme', 'sum64.1');
BEGIN
  FOREACH t IN ARRAY coalesce(p_tables,
      ARRAY['docs','entities','passages','translations','mentions','stories','stages','vectors']) LOOP
    IF (SELECT rel FROM corpus._spec(t)) IS NULL THEN RAISE EXCEPTION 'corpus_manifest: unknown table %', t; END IF;
    SELECT coalesce(jsonb_object_agg(g.grp, jsonb_build_array(g.n, corpus._digest(g.n, g.s1, g.s2))), '{}'::jsonb)
      INTO part FROM corpus.group_digest g WHERE g.tbl = t AND g.n > 0;
    result := result || jsonb_build_object(t, part);
  END LOOP;
  RETURN result;
END $$;

-- {key: row_hash} of one table and group, from the narrow index.
CREATE OR REPLACE FUNCTION public.corpus_keys(p_table text, p_group text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb;
BEGIN
  IF (SELECT rel FROM corpus._spec(p_table)) IS NULL THEN RAISE EXCEPTION 'corpus_keys: unknown table %', p_table; END IF;
  SELECT coalesce(jsonb_object_agg(ri.k, ri.row_hash), '{}'::jsonb) INTO result
  FROM corpus.row_index ri WHERE ri.tbl = p_table AND ri.grp = p_group;
  RETURN result;
END $$;

-- The keys of a batch, [[group, key, row_hash], ...], built exactly as corpus._spec() builds them
-- from stored rows (integers through ::int, so 12 and 12.0 cannot differ).
CREATE OR REPLACE FUNCTION corpus._batch_keys(p_table text, p_rows jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT coalesce(jsonb_agg(jsonb_build_array(g, k, h)), '[]'::jsonb) FROM (
    SELECT CASE WHEN p_table IN ('docs', 'entities') THEN '*' ELSE e->>'doc_code' END AS g,
           CASE p_table
             WHEN 'docs'         THEN e->>'doc_code'
             WHEN 'entities'     THEN e->>'canonical'
             WHEN 'passages'     THEN ((e->>'page_no')::int)::text || '|' || ((e->>'idx')::int)::text
             WHEN 'vectors'      THEN ((e->>'page_no')::int)::text || '|' || ((e->>'idx')::int)::text
             WHEN 'translations' THEN ((e->>'page_no')::int)::text || '|' || ((e->>'idx')::int)::text || '|' || (e->>'lang')
             WHEN 'mentions'     THEN ((e->>'page_no')::int)::text || '|' || ((e->>'idx')::int)::text || '|' || (e->>'canonical')
             WHEN 'stories'      THEN ((e->>'story_id')::int)::text
             WHEN 'stages'       THEN e->>'stage'
           END AS k,
           e->>'row_hash' AS h
    FROM jsonb_array_elements(p_rows) e) z
$$;

-- Upsert as C4, and record the batch in the index and the digest (C4B).
CREATE OR REPLACE FUNCTION public.corpus_ingest(p_table text, p_rows jsonb, p_run uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0; ch jsonb;
BEGIN
  -- C4B: one writer at a time, so a digest never misses a concurrent change
  PERFORM pg_advisory_xact_lock(4242001);
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_ingest: % rows; at most 2000 per call', n_in; END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_rows) e
             WHERE jsonb_typeof(e) <> 'object' OR coalesce(e->>'row_hash', '') = '') THEN
    RAISE EXCEPTION 'corpus_ingest: every row needs a row_hash';
  END IF;
  -- C4B: the batch's keys as the index writes them; a batch must not name a key twice
  ch := corpus._batch_keys(p_table, p_rows);
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(ch) x WHERE x->>1 IS NULL OR x->>0 IS NULL) THEN
    RAISE EXCEPTION 'corpus_ingest: unknown table % or a row without its key', p_table;
  END IF;
  IF (SELECT count(DISTINCT (x->>0, x->>1)) FROM jsonb_array_elements(ch) x) <> n_in THEN
    RAISE EXCEPTION 'corpus_ingest: the batch names a key twice';
  END IF;

  IF p_table = 'docs' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, local_id integer, title text, category text, src_name text, glossary text,
        created_at_local text, row_hash text) ORDER BY x.doc_code),
    u AS (
      INSERT INTO corpus.docs AS t (doc_code, local_id, title, category, src_name, glossary,
                                    created_at_local, row_hash)
      SELECT doc_code, local_id, title, category, src_name, glossary, created_at_local, row_hash FROM r
      ON CONFLICT (doc_code) DO UPDATE SET
        local_id = EXCLUDED.local_id, title = EXCLUDED.title, category = EXCLUDED.category,
        src_name = EXCLUDED.src_name, glossary = EXCLUDED.glossary,
        created_at_local = EXCLUDED.created_at_local, row_hash = EXCLUDED.row_hash,
        synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'entities' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.canonical) x.* FROM jsonb_to_recordset(p_rows) AS x(
        canonical text, local_id integer, kind text, notes text, variants text[],
        created_at_local text, row_hash text) ORDER BY x.canonical),
    u AS (
      INSERT INTO corpus.entities AS t (canonical, local_id, kind, notes, variants, created_at_local, row_hash)
      SELECT canonical, local_id, kind, notes, variants, created_at_local, row_hash FROM r
      ON CONFLICT (canonical) DO UPDATE SET
        local_id = EXCLUDED.local_id, kind = EXCLUDED.kind, notes = EXCLUDED.notes,
        variants = EXCLUDED.variants, created_at_local = EXCLUDED.created_at_local,
        row_hash = EXCLUDED.row_hash, synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'passages' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.page_no, x.idx) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, page_no integer, idx integer, local_id bigint, text text, iast text,
        translation text, verse_ref text, chapter text, text_type text, chandas text, padas integer,
        quality_score double precision, translation_score double precision,
        translation_qa double precision, engine text, mt_prompt_version text, translated_at text,
        ocr_engine text, sandhi text, morph text, source text, row_hash text)
      ORDER BY x.doc_code, x.page_no, x.idx),
    u AS (
      INSERT INTO corpus.passages AS t (doc_code, page_no, idx, local_id, text, iast, translation,
        verse_ref, chapter, text_type, chandas, padas, quality_score, translation_score,
        translation_qa, engine, mt_prompt_version, translated_at, ocr_engine, sandhi, morph, source,
        row_hash)
      SELECT doc_code, page_no, idx, local_id, text, iast, translation, verse_ref, chapter,
        text_type, chandas, padas, quality_score, translation_score, translation_qa, engine,
        mt_prompt_version, translated_at, ocr_engine, sandhi, morph, source, row_hash FROM r
      ON CONFLICT (doc_code, page_no, idx) DO UPDATE SET
        local_id = EXCLUDED.local_id, text = EXCLUDED.text, iast = EXCLUDED.iast,
        translation = EXCLUDED.translation, verse_ref = EXCLUDED.verse_ref,
        chapter = EXCLUDED.chapter, text_type = EXCLUDED.text_type, chandas = EXCLUDED.chandas,
        padas = EXCLUDED.padas, quality_score = EXCLUDED.quality_score,
        translation_score = EXCLUDED.translation_score, translation_qa = EXCLUDED.translation_qa,
        engine = EXCLUDED.engine, mt_prompt_version = EXCLUDED.mt_prompt_version,
        translated_at = EXCLUDED.translated_at, ocr_engine = EXCLUDED.ocr_engine,
        sandhi = EXCLUDED.sandhi, morph = EXCLUDED.morph, source = EXCLUDED.source,
        row_hash = EXCLUDED.row_hash, synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'translations' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.page_no, x.idx, x.lang) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, page_no integer, idx integer, lang text, translation text, engine text,
        mt_prompt_version text, translation_score double precision, translation_qa double precision,
        translated_at text, row_hash text)
      ORDER BY x.doc_code, x.page_no, x.idx, x.lang),
    u AS (
      INSERT INTO corpus.translations AS t (doc_code, page_no, idx, lang, translation, engine,
        mt_prompt_version, translation_score, translation_qa, translated_at, row_hash)
      SELECT doc_code, page_no, idx, lang, translation, engine, mt_prompt_version,
        translation_score, translation_qa, translated_at, row_hash FROM r
      ON CONFLICT (doc_code, page_no, idx, lang) DO UPDATE SET
        translation = EXCLUDED.translation, engine = EXCLUDED.engine,
        mt_prompt_version = EXCLUDED.mt_prompt_version,
        translation_score = EXCLUDED.translation_score, translation_qa = EXCLUDED.translation_qa,
        translated_at = EXCLUDED.translated_at, row_hash = EXCLUDED.row_hash,
        synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'mentions' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.page_no, x.idx, x.canonical) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, page_no integer, idx integer, canonical text, surface text, row_hash text)
      ORDER BY x.doc_code, x.page_no, x.idx, x.canonical),
    u AS (
      INSERT INTO corpus.mentions AS t (doc_code, page_no, idx, canonical, surface, row_hash)
      SELECT doc_code, page_no, idx, canonical, surface, row_hash FROM r
      ON CONFLICT (doc_code, page_no, idx, canonical) DO UPDATE SET
        surface = EXCLUDED.surface, row_hash = EXCLUDED.row_hash, synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'stories' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.story_id) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, story_id integer, image_id integer, status text, title text, title_hi text,
        why text, from_page integer, from_idx integer, to_page integer, to_idx integer,
        story_en text, story_hi text, quote_sa text, quote_ref text, notes text, cites text,
        verify text, model text, provenance text, created_at_local text, updated_at_local text,
        approved_at_local text, row_hash text)
      ORDER BY x.doc_code, x.story_id),
    u AS (
      INSERT INTO corpus.stories AS t (doc_code, story_id, image_id, status, title, title_hi, why,
        from_page, from_idx, to_page, to_idx, story_en, story_hi, quote_sa, quote_ref, notes, cites,
        verify, model, provenance, created_at_local, updated_at_local, approved_at_local, row_hash)
      SELECT doc_code, story_id, image_id, status, title, title_hi, why, from_page, from_idx,
        to_page, to_idx, story_en, story_hi, quote_sa, quote_ref, notes, cites, verify, model,
        provenance, created_at_local, updated_at_local, approved_at_local, row_hash FROM r
      ON CONFLICT (doc_code, story_id) DO UPDATE SET
        image_id = EXCLUDED.image_id, status = EXCLUDED.status, title = EXCLUDED.title,
        title_hi = EXCLUDED.title_hi, why = EXCLUDED.why, from_page = EXCLUDED.from_page,
        from_idx = EXCLUDED.from_idx, to_page = EXCLUDED.to_page, to_idx = EXCLUDED.to_idx,
        story_en = EXCLUDED.story_en, story_hi = EXCLUDED.story_hi, quote_sa = EXCLUDED.quote_sa,
        quote_ref = EXCLUDED.quote_ref, notes = EXCLUDED.notes, cites = EXCLUDED.cites,
        verify = EXCLUDED.verify, model = EXCLUDED.model, provenance = EXCLUDED.provenance,
        created_at_local = EXCLUDED.created_at_local, updated_at_local = EXCLUDED.updated_at_local,
        approved_at_local = EXCLUDED.approved_at_local, row_hash = EXCLUDED.row_hash,
        synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'stages' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.stage) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, stage text, status text, reason text, attempts integer, measured text,
        updated_at_local text, row_hash text)
      ORDER BY x.doc_code, x.stage),
    u AS (
      INSERT INTO corpus.stages AS t (doc_code, stage, status, reason, attempts, measured,
                                      updated_at_local, row_hash)
      SELECT doc_code, stage, status, reason, attempts, measured, updated_at_local, row_hash FROM r
      ON CONFLICT (doc_code, stage) DO UPDATE SET
        status = EXCLUDED.status, reason = EXCLUDED.reason, attempts = EXCLUDED.attempts,
        measured = EXCLUDED.measured, updated_at_local = EXCLUDED.updated_at_local,
        row_hash = EXCLUDED.row_hash, synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSIF p_table = 'vectors' THEN
    WITH r AS (
      SELECT DISTINCT ON (x.doc_code, x.page_no, x.idx) x.* FROM jsonb_to_recordset(p_rows) AS x(
        doc_code text, page_no integer, idx integer, model text, source_dim integer,
        embedding text, row_hash text)
      ORDER BY x.doc_code, x.page_no, x.idx),
    u AS (
      INSERT INTO corpus.passage_vectors AS t (doc_code, page_no, idx, model, source_dim, embedding, row_hash)
      SELECT doc_code, page_no, idx, model, source_dim, embedding::public.halfvec(1536), row_hash FROM r
      ON CONFLICT (doc_code, page_no, idx) DO UPDATE SET
        model = EXCLUDED.model, source_dim = EXCLUDED.source_dim, embedding = EXCLUDED.embedding,
        row_hash = EXCLUDED.row_hash, synced_at = now(), retired_at = NULL
      WHERE t.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR t.retired_at IS NOT NULL
      RETURNING 1)
    SELECT count(*) INTO n_changed FROM u;

  ELSE
    RAISE EXCEPTION 'corpus_ingest: unknown table %', p_table;
  END IF;

  -- C4B: every row of the batch is now in the table with this hash; the index follows, and an
  -- unchanged row that the index lacked is added (so a re-send heals a missing index entry)
  PERFORM corpus._index_apply(p_table, ch);
  RETURN jsonb_build_object('table', p_table, 'received', n_in, 'changed', n_changed);
END $$;

-- Retire (never delete), and take the rows out of the index and the digest.
CREATE OR REPLACE FUNCTION public.corpus_retire(p_table text, p_group text, p_keys jsonb, p_run uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE s record; n integer; removed jsonb;
BEGIN
  SELECT * INTO s FROM corpus._spec(p_table);
  IF s.rel IS NULL THEN RAISE EXCEPTION 'corpus_retire: unknown table %', p_table; END IF;
  IF p_keys IS NULL OR jsonb_typeof(p_keys) <> 'array' THEN
    RAISE EXCEPTION 'corpus_retire: p_keys must be a JSON array';
  END IF;
  IF jsonb_array_length(p_keys) > 5000 THEN RAISE EXCEPTION 'corpus_retire: at most 5000 keys per call'; END IF;
  PERFORM pg_advisory_xact_lock(4242001);
  EXECUTE format(
    'WITH u AS (UPDATE %s SET retired_at = now(), synced_at = now()'
    ' WHERE retired_at IS NULL AND %s = $1 AND (%s) IN (SELECT jsonb_array_elements_text($2))'
    ' RETURNING %s AS g, (%s) AS k)'
    ' SELECT count(*), coalesce(jsonb_agg(jsonb_build_array(g, k)), ''[]''::jsonb) FROM u',
    s.rel, s.grp, s.k, s.grp, s.k)
  INTO n, removed USING p_group, p_keys;
  PERFORM corpus._index_remove(p_table, removed);
  RETURN jsonb_build_object('table', p_table, 'group', p_group, 'asked', jsonb_array_length(p_keys), 'retired', n);
END $$;

-- The helpers are for the functions above and the SQL editor only.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['corpus._h64(text, integer)', 'corpus._digest(bigint, numeric, numeric)',
      'corpus._index_apply(text, jsonb)', 'corpus._index_remove(text, jsonb)', 'corpus._rebuild_index(text)',
      'corpus._batch_keys(text, jsonb)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  -- the five entry points keep exactly the C4 grants (service_role only)
  FOREACH f IN ARRAY ARRAY['public.corpus_manifest(text[])', 'public.corpus_keys(text, text)',
      'public.corpus_ingest(text, jsonb, uuid)', 'public.corpus_retire(text, text, jsonb, uuid)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f); END IF;
  END LOOP;
END $$;

COMMIT;

-- ============================================================
-- Checks (one at a time).
-- K1 after step B, per table: rows in the index against live rows (expect equal):
-- SELECT t, (SELECT count(*) FROM corpus.row_index WHERE tbl = t) AS indexed,
--        (SELECT sum(n) FROM corpus.group_digest WHERE tbl = t) AS digested
-- FROM unnest(ARRAY['docs','entities','passages','translations','mentions','stories','stages','vectors']) t;
--
-- K2 the running sums agree with a fresh sum over the index (expect 0 rows):
-- SELECT g.tbl, g.grp FROM corpus.group_digest g
-- LEFT JOIN (SELECT tbl, grp, count(*) n, sum(corpus._h64(k || ' ' || row_hash, 0)) s1,
--                   sum(corpus._h64(k || ' ' || row_hash, 1)) s2 FROM corpus.row_index GROUP BY tbl, grp) r
--   USING (tbl, grp)
-- WHERE corpus._digest(g.n, g.s1, g.s2) IS DISTINCT FROM corpus._digest(coalesce(r.n, 0), coalesce(r.s1, 0), coalesce(r.s2, 0));
--
-- K3 the manifest is fast now (expect "_scheme": "sum64.1" and an answer in well under a second):
-- SELECT length(public.corpus_manifest()::text) AS manifest_chars, public.corpus_manifest(ARRAY['docs']) AS docs;
-- ============================================================
