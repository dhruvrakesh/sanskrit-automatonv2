-- ============================================================
-- C4 - the private corpus mirror (docs/CORPUS_MIRROR_2026-10-08.md)
-- CORPUS_MIRROR_C4_2026_10_08
--
-- What it is: a PRIVATE copy of the local brain (data/context.db) in PostgreSQL, kept current
-- by scripts/corpus_sync.py. It mirrors every live document, not only the published ones:
-- passages (Sanskrit, IAST, English), the Hindi and other translations, entities and their
-- mentions, stories, pipeline stages, and the passage vectors (the local 3,072-dim
-- gemini-embedding-001 vectors cut to their first 1,536 dims and renormalised, the same size as
-- srangam_passage_vectors). Raw OCR (passages.norm, 286 MB), OCR variants, the SQLite search
-- index, the MT cache and the usage ledger stay at home.
--
-- Who can see it: nobody from the site. The schema "corpus" is not one the Data API serves;
-- anon and authenticated get no privilege on it, every table has RLS on with no policy, and
-- the five functions below run only for service_role (the corpus-ingest edge function) and
-- for the SQL editor. The public reader keeps using srangam_texts / srangam_text_passages,
-- which only the publish gate fills.
--
-- How it stays idempotent: every row carries row_hash (md5 of its mirrored columns, made by
-- corpus_sync.py). corpus_manifest() gives, per table and document, a count and a digest of
-- (key, row_hash); the sync compares that with the same digest made locally and only for a
-- document that differs asks corpus_keys() and sends the rows whose hash differs.
-- corpus_ingest() upserts with ON CONFLICT ... WHERE row_hash IS DISTINCT FROM ..., so sending
-- a batch twice changes nothing. A row that is gone locally is RETIRED (retired_at set), never
-- deleted; it comes back by itself if the row returns.
--
-- Apply ONLY after C4_preflight_2026-10-08.sql shows: vector in public, schema corpus absent,
-- service_role present. Paste the whole file into the Lovable Cloud SQL editor, run it once,
-- then run the checks at the end one at a time. It is safe to run again (IF NOT EXISTS /
-- CREATE OR REPLACE; grants re-applied). The SQL-editor path records no row in
-- supabase_migrations.schema_migrations; do NOT hand-insert one.
--
-- Tested 2026-10-08 on PostgreSQL 16 + pgvector 0.8.0 with Supabase-like roles (anon,
-- authenticated, service_role) and default privileges: applies cleanly, and twice; V1 all
-- present; anon and authenticated are refused on every table and function; a full sync from a
-- fixture, then a second sync, sends 0 rows (tests/test_corpus_sync_pg_2026_10_08.py).
--
-- PURELY ADDITIVE: one new schema, its tables, five functions in public. Nothing existing is
-- changed. Rollback (nothing else depends on it):
--   DROP FUNCTION public.corpus_ingest(text, jsonb, uuid);
--   DROP FUNCTION public.corpus_manifest(text[]);
--   DROP FUNCTION public.corpus_keys(text, text);
--   DROP FUNCTION public.corpus_retire(text, text, jsonb, uuid);
--   DROP FUNCTION public.corpus_run(uuid, jsonb, boolean);
--   DROP SCHEMA corpus CASCADE;
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS corpus;
REVOKE ALL ON SCHEMA corpus FROM PUBLIC;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE 'REVOKE ALL ON SCHEMA corpus FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN EXECUTE 'REVOKE ALL ON SCHEMA corpus FROM authenticated'; END IF;
END $$;

-- 1. Documents (live ones; retired documents stay at home).
CREATE TABLE IF NOT EXISTS corpus.docs (
    doc_code          TEXT PRIMARY KEY,
    local_id          INTEGER,
    title             TEXT,
    category          TEXT,
    src_name          TEXT,             -- file name only, never the local path
    glossary          TEXT,
    created_at_local  TEXT,
    row_hash          TEXT NOT NULL,
    synced_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at        TIMESTAMPTZ
);

-- 2. Entities (one row per canonical name; variants folded in).
CREATE TABLE IF NOT EXISTS corpus.entities (
    canonical         TEXT PRIMARY KEY,
    local_id          INTEGER,
    kind              TEXT,
    notes             TEXT,
    variants          TEXT[],
    created_at_local  TEXT,
    row_hash          TEXT NOT NULL,
    synced_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at        TIMESTAMPTZ
);

-- 3. Passages, keyed as the local UNIQUE(doc, page_no, idx). local_id is informational only:
--    the local id changes when a document is re-ingested, the key does not.
CREATE TABLE IF NOT EXISTS corpus.passages (
    doc_code           TEXT NOT NULL REFERENCES corpus.docs(doc_code),
    page_no            INTEGER NOT NULL,
    idx                INTEGER NOT NULL,
    local_id           BIGINT,
    text               TEXT,
    iast               TEXT,
    translation        TEXT,
    verse_ref          TEXT,
    chapter            TEXT,
    text_type          TEXT,
    chandas            TEXT,
    padas              INTEGER,
    quality_score      DOUBLE PRECISION,
    translation_score  DOUBLE PRECISION,
    translation_qa     DOUBLE PRECISION,
    engine             TEXT,
    mt_prompt_version  TEXT,
    translated_at      TEXT,             -- verbatim from the local row (mixed formats)
    ocr_engine         TEXT,
    sandhi             TEXT,
    morph              TEXT,
    source             TEXT,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at         TIMESTAMPTZ,
    fts                TSVECTOR GENERATED ALWAYS AS (
                         setweight(to_tsvector('pg_catalog.english'::regconfig, coalesce(translation, '')), 'A') ||
                         setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(iast, '')), 'B')) STORED,
    PRIMARY KEY (doc_code, page_no, idx)
);
CREATE INDEX IF NOT EXISTS corpus_passages_fts ON corpus.passages USING gin (fts);
CREATE INDEX IF NOT EXISTS corpus_passages_verse ON corpus.passages (doc_code, verse_ref);

-- 4. Translations other than the English on the passage (translations_l10n: Hindi today).
CREATE TABLE IF NOT EXISTS corpus.translations (
    doc_code           TEXT NOT NULL,
    page_no            INTEGER NOT NULL,
    idx                INTEGER NOT NULL,
    lang               TEXT NOT NULL,
    translation        TEXT,
    engine             TEXT,
    mt_prompt_version  TEXT,
    translation_score  DOUBLE PRECISION,
    translation_qa     DOUBLE PRECISION,
    translated_at      TEXT,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at         TIMESTAMPTZ,
    PRIMARY KEY (doc_code, page_no, idx, lang),
    FOREIGN KEY (doc_code, page_no, idx) REFERENCES corpus.passages(doc_code, page_no, idx)
);

-- 5. Entity mentions (one row per entity per passage, as the local UNIQUE(entity, passage)).
CREATE TABLE IF NOT EXISTS corpus.mentions (
    doc_code    TEXT NOT NULL,
    page_no     INTEGER NOT NULL,
    idx         INTEGER NOT NULL,
    canonical   TEXT NOT NULL REFERENCES corpus.entities(canonical),
    surface     TEXT,
    row_hash    TEXT NOT NULL,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at  TIMESTAMPTZ,
    PRIMARY KEY (doc_code, page_no, idx, canonical),
    FOREIGN KEY (doc_code, page_no, idx) REFERENCES corpus.passages(doc_code, page_no, idx)
);
CREATE INDEX IF NOT EXISTS corpus_mentions_entity ON corpus.mentions (canonical);

-- 6. Stories, every status (the site's srangam_stories holds approved ones only).
CREATE TABLE IF NOT EXISTS corpus.stories (
    doc_code           TEXT NOT NULL REFERENCES corpus.docs(doc_code),
    story_id           INTEGER NOT NULL,
    image_id           INTEGER,
    status             TEXT,
    title              TEXT,
    title_hi           TEXT,
    why                TEXT,
    from_page          INTEGER,
    from_idx           INTEGER,
    to_page            INTEGER,
    to_idx             INTEGER,
    story_en           TEXT,
    story_hi           TEXT,
    quote_sa           TEXT,
    quote_ref          TEXT,
    notes              TEXT,
    cites              TEXT,
    verify             TEXT,
    model              TEXT,
    provenance         TEXT,
    created_at_local   TEXT,
    updated_at_local   TEXT,
    approved_at_local  TEXT,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at         TIMESTAMPTZ,
    PRIMARY KEY (doc_code, story_id)
);

-- 7. Pipeline stages per document (doc_stage): what is done, pending, degraded.
CREATE TABLE IF NOT EXISTS corpus.stages (
    doc_code          TEXT NOT NULL REFERENCES corpus.docs(doc_code),
    stage             TEXT NOT NULL,
    status            TEXT,
    reason            TEXT,
    attempts          INTEGER,
    measured          TEXT,
    updated_at_local  TEXT,
    row_hash          TEXT NOT NULL,
    synced_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at        TIMESTAMPTZ,
    PRIMARY KEY (doc_code, stage)
);

-- 8. Passage vectors: the local vector's first 1,536 dims, renormalised.
CREATE TABLE IF NOT EXISTS corpus.passage_vectors (
    doc_code    TEXT NOT NULL,
    page_no     INTEGER NOT NULL,
    idx         INTEGER NOT NULL,
    model       TEXT NOT NULL,
    source_dim  INTEGER NOT NULL,
    embedding   public.halfvec(1536) NOT NULL,
    row_hash    TEXT NOT NULL,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at  TIMESTAMPTZ,
    PRIMARY KEY (doc_code, page_no, idx),
    FOREIGN KEY (doc_code, page_no, idx) REFERENCES corpus.passages(doc_code, page_no, idx)
);
CREATE INDEX IF NOT EXISTS corpus_passage_vectors_hnsw
    ON corpus.passage_vectors USING hnsw (embedding public.halfvec_cosine_ops);

-- 9. One row per sync run (what was sent, by which client version).
CREATE TABLE IF NOT EXISTS corpus.sync_runs (
    run_id       UUID PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    info         JSONB
);

-- Nobody but the owner (and service_role, which bypasses RLS) reaches these tables.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['docs','entities','passages','translations','mentions','stories','stages',
                           'passage_vectors','sync_runs'] LOOP
    EXECUTE format('ALTER TABLE corpus.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corpus.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- 10. Where each table's key and group live. The key text is what corpus_sync.py builds, byte
--     for byte: digests compare (key || ' ' || row_hash) joined by newlines, ordered COLLATE "C".
CREATE OR REPLACE FUNCTION corpus._spec(p_table text, OUT rel text, OUT grp text, OUT k text)
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT s.rel, s.grp, s.k FROM (VALUES
    ('docs',         'corpus.docs',            '''*''',    'doc_code'),
    ('entities',     'corpus.entities',        '''*''',    'canonical'),
    ('passages',     'corpus.passages',        'doc_code', 'page_no::text || ''|'' || idx::text'),
    ('translations', 'corpus.translations',    'doc_code', 'page_no::text || ''|'' || idx::text || ''|'' || lang'),
    ('mentions',     'corpus.mentions',        'doc_code', 'page_no::text || ''|'' || idx::text || ''|'' || canonical'),
    ('stories',      'corpus.stories',         'doc_code', 'story_id::text'),
    ('stages',       'corpus.stages',          'doc_code', 'stage'),
    ('vectors',      'corpus.passage_vectors', 'doc_code', 'page_no::text || ''|'' || idx::text')
  ) AS s(t, rel, grp, k) WHERE s.t = p_table
$$;

-- 11. Per table, per group (document, or '*'): [row count, digest]. Retired rows excluded.
CREATE OR REPLACE FUNCTION public.corpus_manifest(p_tables text[] DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  t text; s record; part jsonb; result jsonb := '{}'::jsonb;
BEGIN
  FOREACH t IN ARRAY coalesce(p_tables,
      ARRAY['docs','entities','passages','translations','mentions','stories','stages','vectors']) LOOP
    SELECT * INTO s FROM corpus._spec(t);
    IF s.rel IS NULL THEN RAISE EXCEPTION 'corpus_manifest: unknown table %', t; END IF;
    EXECUTE format(
      'SELECT coalesce(jsonb_object_agg(g, jsonb_build_array(n, d)), ''{}''::jsonb) FROM ('
      ' SELECT %s AS g, count(*) AS n,'
      '  md5(string_agg((%s) || '' '' || row_hash, E''\n'' ORDER BY (%s) COLLATE "C")) AS d'
      ' FROM %s WHERE retired_at IS NULL GROUP BY 1) q', s.grp, s.k, s.k, s.rel)
    INTO part;
    result := result || jsonb_build_object(t, part);
  END LOOP;
  RETURN result;
END $$;

-- 12. {key: row_hash} for one table and group, live rows only. One JSON value, so the Data
--     API's row limit does not cut a large document short.
CREATE OR REPLACE FUNCTION public.corpus_keys(p_table text, p_group text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE s record; result jsonb;
BEGIN
  SELECT * INTO s FROM corpus._spec(p_table);
  IF s.rel IS NULL THEN RAISE EXCEPTION 'corpus_keys: unknown table %', p_table; END IF;
  EXECUTE format('SELECT coalesce(jsonb_object_agg(%s, row_hash), ''{}''::jsonb) FROM %s'
                 ' WHERE retired_at IS NULL AND %s = $1', s.k, s.rel, s.grp)
  INTO result USING p_group;
  RETURN result;
END $$;

-- 13. Upsert up to 2,000 rows of one table. Returns {received, changed}. A row whose row_hash is
--     unchanged (and not retired) is left alone, so a repeated batch changes nothing.
CREATE OR REPLACE FUNCTION public.corpus_ingest(p_table text, p_rows jsonb, p_run uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0;
BEGIN
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_ingest: % rows; at most 2000 per call', n_in; END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_rows) e
             WHERE jsonb_typeof(e) <> 'object' OR coalesce(e->>'row_hash', '') = '') THEN
    RAISE EXCEPTION 'corpus_ingest: every row needs a row_hash';
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

  RETURN jsonb_build_object('table', p_table, 'received', n_in, 'changed', n_changed);
END $$;

-- 14. Retire (never delete) rows that are gone locally: up to 5,000 keys of one table and group.
CREATE OR REPLACE FUNCTION public.corpus_retire(p_table text, p_group text, p_keys jsonb, p_run uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE s record; n integer;
BEGIN
  SELECT * INTO s FROM corpus._spec(p_table);
  IF s.rel IS NULL THEN RAISE EXCEPTION 'corpus_retire: unknown table %', p_table; END IF;
  IF p_keys IS NULL OR jsonb_typeof(p_keys) <> 'array' THEN
    RAISE EXCEPTION 'corpus_retire: p_keys must be a JSON array';
  END IF;
  IF jsonb_array_length(p_keys) > 5000 THEN RAISE EXCEPTION 'corpus_retire: at most 5000 keys per call'; END IF;
  EXECUTE format(
    'WITH u AS (UPDATE %s SET retired_at = now(), synced_at = now()'
    ' WHERE retired_at IS NULL AND %s = $1 AND (%s) IN (SELECT jsonb_array_elements_text($2))'
    ' RETURNING 1) SELECT count(*) FROM u', s.rel, s.grp, s.k)
  INTO n USING p_group, p_keys;
  RETURN jsonb_build_object('table', p_table, 'group', p_group, 'asked', jsonb_array_length(p_keys), 'retired', n);
END $$;

-- 15. Start or finish a run record.
CREATE OR REPLACE FUNCTION public.corpus_run(p_run uuid, p_info jsonb DEFAULT NULL, p_finish boolean DEFAULT false)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF p_run IS NULL THEN RAISE EXCEPTION 'corpus_run: p_run is required'; END IF;
  INSERT INTO corpus.sync_runs AS t (run_id, info) VALUES (p_run, p_info)
  ON CONFLICT (run_id) DO UPDATE SET
    info = coalesce(t.info, '{}'::jsonb) || coalesce(EXCLUDED.info, '{}'::jsonb),
    finished_at = CASE WHEN p_finish THEN now() ELSE t.finished_at END;
  RETURN jsonb_build_object('run_id', p_run, 'finished', p_finish, 'server_time', now());
END $$;

-- 16. For reading in the SQL editor (owner only, like the tables).
CREATE OR REPLACE VIEW corpus.v_docs WITH (security_invoker = true) AS
SELECT d.doc_code, d.title, d.category,
       (SELECT count(*) FROM corpus.passages p WHERE p.doc_code = d.doc_code AND p.retired_at IS NULL) AS passages,
       (SELECT count(*) FROM corpus.passages p WHERE p.doc_code = d.doc_code AND p.retired_at IS NULL
          AND btrim(coalesce(p.translation, '')) <> '') AS english,
       (SELECT count(*) FROM corpus.translations l WHERE l.doc_code = d.doc_code AND l.retired_at IS NULL
          AND l.lang = 'hi' AND btrim(coalesce(l.translation, '')) <> '') AS hindi,
       (SELECT count(*) FROM corpus.passage_vectors v WHERE v.doc_code = d.doc_code AND v.retired_at IS NULL) AS vectors,
       (SELECT count(*) FROM corpus.stories s WHERE s.doc_code = d.doc_code AND s.retired_at IS NULL) AS stories,
       (SELECT max(p.translated_at) FROM corpus.passages p WHERE p.doc_code = d.doc_code) AS last_translated_at,
       d.synced_at
FROM corpus.docs d WHERE d.retired_at IS NULL;

-- Word search over English (stemmed) and IAST (as written). Example:
--   SELECT * FROM corpus.search('cremation ground', 20);
--   SELECT * FROM corpus.search('agni', 20, 'markandeya_purana');
CREATE OR REPLACE FUNCTION corpus.search(q text, k integer DEFAULT 20, p_doc text DEFAULT NULL)
RETURNS TABLE (doc_code text, page_no integer, idx integer, verse_ref text, rank real,
               iast text, translation text)
LANGUAGE sql STABLE SET search_path = '' AS $$
  WITH qq AS (SELECT websearch_to_tsquery('pg_catalog.english'::regconfig, q) ||
                     websearch_to_tsquery('pg_catalog.simple'::regconfig, q) AS tq)
  SELECT p.doc_code, p.page_no, p.idx, p.verse_ref, ts_rank(p.fts, qq.tq) AS rank,
         left(p.iast, 300), left(p.translation, 500)
  FROM corpus.passages p, qq
  WHERE p.retired_at IS NULL AND p.fts @@ qq.tq AND (p_doc IS NULL OR p.doc_code = p_doc)
  ORDER BY rank DESC, p.doc_code, p.page_no, p.idx
  LIMIT least(greatest(k, 1), 200)
$$;

-- Nearest passages to a vector (for the SQL editor and, later, an admin-only search scope).
CREATE OR REPLACE FUNCTION corpus.match_passages(query_embedding public.halfvec(1536), k integer DEFAULT 12,
                                                 p_doc text DEFAULT NULL)
RETURNS TABLE (doc_code text, page_no integer, idx integer, similarity double precision)
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT v.doc_code, v.page_no, v.idx,
         1 - (v.embedding OPERATOR(public.<=>) query_embedding) AS similarity
  FROM corpus.passage_vectors v
  WHERE query_embedding IS NOT NULL AND v.retired_at IS NULL AND (p_doc IS NULL OR v.doc_code = p_doc)
  ORDER BY v.embedding OPERATOR(public.<=>) query_embedding
  LIMIT least(greatest(k, 1), 100)
$$;

-- Who may call what (spelled out: Supabase's default privileges grant new functions to anon
-- and authenticated by name - the S3 lesson of 2026-10-07).
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'public.corpus_manifest(text[])', 'public.corpus_keys(text, text)',
      'public.corpus_ingest(text, jsonb, uuid)', 'public.corpus_retire(text, text, jsonb, uuid)',
      'public.corpus_run(uuid, jsonb, boolean)', 'corpus._spec(text)',
      'corpus.search(text, integer, text)', 'corpus.match_passages(public.halfvec, integer, text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.corpus_manifest(text[]), public.corpus_keys(text, text),
      public.corpus_ingest(text, jsonb, uuid), public.corpus_retire(text, text, jsonb, uuid),
      public.corpus_run(uuid, jsonb, boolean) TO service_role;
  END IF;
  -- the view too: a default privilege can grant a new view to anon by name
  EXECUTE 'REVOKE ALL ON corpus.v_docs FROM PUBLIC';
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON corpus.v_docs FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON corpus.v_docs FROM authenticated'; END IF;
END $$;

COMMIT;

-- ============================================================
-- Checks after applying (one query at a time).
-- V1 objects (expect 9 tables, 4 indexes, 8 functions, 1 view, RLS on for all 9; 22 rows, all true):
-- SELECT 'table ' || c.relname AS object, true AS present FROM pg_class c
--   WHERE c.relnamespace = to_regnamespace('corpus') AND c.relkind = 'r'
-- UNION ALL SELECT 'rls on ' || c.relname, c.relrowsecurity FROM pg_class c
--   WHERE c.relnamespace = to_regnamespace('corpus') AND c.relkind = 'r'
-- UNION ALL SELECT 'index ' || i, to_regclass('corpus.' || i) IS NOT NULL FROM unnest(ARRAY[
--   'corpus_passages_fts','corpus_passages_verse','corpus_mentions_entity','corpus_passage_vectors_hnsw']) i
-- UNION ALL SELECT 'function ' || p.oid::regprocedure::text, true FROM pg_proc p
--   WHERE p.proname IN ('corpus_manifest','corpus_keys','corpus_ingest','corpus_retire','corpus_run')
--      OR (p.pronamespace = to_regnamespace('corpus'))
-- UNION ALL SELECT 'view v_docs', to_regclass('corpus.v_docs') IS NOT NULL;
--
-- V2 nobody from the site can reach it (expect every column false):
-- SELECT c.relname,
--        has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
--        has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select,
--        has_table_privilege('anon', c.oid, 'INSERT') AS anon_insert,
--        has_schema_privilege('anon', 'corpus', 'USAGE') AS anon_schema
-- FROM pg_class c WHERE c.relnamespace = to_regnamespace('corpus') AND c.relkind IN ('r', 'v')
-- UNION ALL
-- SELECT p.oid::regprocedure::text, has_function_privilege('anon', p.oid, 'EXECUTE'),
--        has_function_privilege('authenticated', p.oid, 'EXECUTE'), false, false
-- FROM pg_proc p WHERE p.proname LIKE 'corpus\_%' OR p.pronamespace = to_regnamespace('corpus');
--
-- V3 the edge function's role may call the five functions (expect 5 rows, true):
-- SELECT p.oid::regprocedure, has_function_privilege('service_role', p.oid, 'EXECUTE')
-- FROM pg_proc p WHERE p.proname IN ('corpus_manifest','corpus_keys','corpus_ingest','corpus_retire','corpus_run');
--
-- V4 the manifest answers on an empty mirror (expect {"docs": {}, ...} with eight empty objects):
-- SELECT public.corpus_manifest();
-- ============================================================
