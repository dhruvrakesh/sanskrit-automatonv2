-- ============================================================
-- C8 - pictures and graphic novels in the working corpus (CORPUS_MEDIA_C8_2026_10_09)
-- docs/MEDIA_AND_CORNER_2026-10-09.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C8_checks_2026-10-09.sql, one query per paste.
--
-- What it adds, all in the closed schema corpus (no table is granted to anyone):
--   corpus.media        one row per picture the translation desk made: image-library pictures
--                       (key img:<id>), and the pages and cast sheets of graphic novels
--                       (novel:<id>:page:<n>, novel:<id>:cast:<n>). Captions, the verse it is
--                       anchored to, status, model, licence, the sha256 of the desk's file.
--   corpus.media_files  where each picture's renditions are kept: 'thumb' (480 px) and 'display'
--                       (1600 px) JPEGs in the Srangam Shared Drive, PRIVATE (not shared by link).
--                       Keyed by the original's sha256, so a picture is uploaded once.
--   corpus.novels       one row per graphic novel: its plan (pages, captions in English and Hindi
--                       with citations, speech, the scene asked for), check, cast and status.
--   corpus.media_config one setting: the Drive folder the pictures go to.
-- Who sees what (the same rule as the stories, C6): a reader sees APPROVED pictures and APPROVED
-- novels (with every page of them); an admin (or the super admin) also sees drafts and novels
-- still being planned or drawn. Retired is never shown. The reader gate (C5/C7) applies first.
--
-- Functions:
--   for signed-in readers (each passes corpus._reader_gate() first):
--     corpus_reader_media(p_doc, p_story, k, p_offset)   the pictures (not the novels' pages)
--     corpus_reader_novels(p_doc)                        the graphic novels, with a cover
--     corpus_reader_novel(p_id)                          one novel: plan, check and its pictures
--     corpus_reader_media_file(p_sha, p_rendition)       where a visible picture's file is; the
--                                                        corpus-media edge function calls it AS THE
--                                                        READER before it fetches the bytes
--   for service_role only (the corpus-media edge function, on a request signed with
--   CORPUS_SYNC_SECRET by the desk's scripts/corpus_media.py):
--     corpus_media_state(), corpus_media_upsert(jsonb), corpus_novels_upsert(jsonb),
--     corpus_media_retire(text[], integer[]), corpus_media_file_get(text, text),
--     corpus_media_file_put(jsonb), corpus_media_config_get(text), corpus_media_config_set(text, text)
--
-- Needs C4 and C5 (corpus.docs, corpus._reader_gate) and C7a (the role super_admin). Purely
-- additive: nothing that exists is changed. Re-running it changes nothing.
-- Rollback:
--   DROP FUNCTION IF EXISTS public.corpus_reader_media(text, integer, integer, integer),
--     public.corpus_reader_novels(text), public.corpus_reader_novel(integer),
--     public.corpus_reader_media_file(text, text), public.corpus_media_state(),
--     public.corpus_media_upsert(jsonb), public.corpus_novels_upsert(jsonb),
--     public.corpus_media_retire(text[], integer[]), public.corpus_media_file_get(text, text),
--     public.corpus_media_file_put(jsonb), public.corpus_media_config_get(text),
--     public.corpus_media_config_set(text, text),
--     corpus._is_editor(), corpus._media_visible(text, text, integer, boolean);
--   DROP TABLE IF EXISTS corpus.media_files, corpus.media, corpus.novels, corpus.media_config;
--   (the files in Drive stay; delete the folder "Srangam corpus media" there if wanted)
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins
-- (tests/test_corpus_media_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.docs') IS NULL OR to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C8: needs C4 and C5 (corpus.docs and corpus._reader_gate are missing).';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                 JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE n.nspname = 'public' AND t.typname = 'app_role' AND e.enumlabel = 'super_admin') THEN
    RAISE EXCEPTION 'C8: needs C7a (app_role has no super_admin).';
  END IF;
END $$;

-- 1. Tables.
CREATE TABLE IF NOT EXISTS corpus.media (
    media_key          TEXT PRIMARY KEY CHECK (media_key ~ '^(img:[0-9]{1,9}|novel:[0-9]{1,9}:(page|cast):[0-9]{1,3})$'),
    doc_code           TEXT NOT NULL REFERENCES corpus.docs(doc_code),
    kind               TEXT NOT NULL CHECK (kind IN ('generated', 'cover', 'edition-plate', 'diagram', 'photo',
                                                     'novel_page', 'novel_cast')),
    status             TEXT NOT NULL CHECK (status IN ('draft', 'approved')),
    title              TEXT,
    caption_en         TEXT,
    caption_hi         TEXT,
    context_note       TEXT,
    anchor_page        INTEGER,
    anchor_idx         INTEGER,
    anchor_verse_ref   TEXT,
    story_id           INTEGER,
    novel_id           INTEGER,
    seq                INTEGER,
    version            INTEGER,
    width              INTEGER,
    height             INTEGER,
    sha256             TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    model              TEXT,
    license            TEXT,
    provenance         TEXT,
    created_at_local   TEXT,
    approved_at_local  TEXT,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS corpus_media_doc ON corpus.media (doc_code) WHERE retired_at IS NULL;
CREATE INDEX IF NOT EXISTS corpus_media_story ON corpus.media (story_id) WHERE retired_at IS NULL AND story_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS corpus_media_novel ON corpus.media (novel_id) WHERE retired_at IS NULL AND novel_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS corpus_media_sha ON corpus.media (sha256);

CREATE TABLE IF NOT EXISTS corpus.media_files (
    sha256       TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    rendition    TEXT NOT NULL CHECK (rendition IN ('thumb', 'display')),
    storage      TEXT NOT NULL DEFAULT 'gdrive' CHECK (storage IN ('gdrive')),
    file_id      TEXT NOT NULL CHECK (length(file_id) BETWEEN 10 AND 200),
    mime         TEXT NOT NULL CHECK (mime IN ('image/jpeg', 'image/png', 'image/webp')),
    bytes        INTEGER NOT NULL CHECK (bytes > 0 AND bytes <= 4194304),
    width        INTEGER,
    height       INTEGER,
    file_sha256  TEXT NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (sha256, rendition)
);

CREATE TABLE IF NOT EXISTS corpus.novels (
    novel_id           INTEGER PRIMARY KEY,
    doc_code           TEXT NOT NULL REFERENCES corpus.docs(doc_code),
    story_id           INTEGER,
    status             TEXT NOT NULL CHECK (status IN ('plan', 'drawing', 'approved')),
    audience           TEXT,
    title              TEXT,
    title_hi           TEXT,
    pages              INTEGER,
    plan               JSONB,
    verify             JSONB,
    cover_seq          INTEGER,
    model              TEXT,
    image_model        TEXT,
    aspect             TEXT,
    provenance         TEXT,
    created_at_local   TEXT,
    updated_at_local   TEXT,
    approved_at_local  TEXT,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS corpus_novels_doc ON corpus.novels (doc_code) WHERE retired_at IS NULL;

CREATE TABLE IF NOT EXISTS corpus.media_config (
    key         TEXT PRIMARY KEY CHECK (key IN ('drive_folder')),
    value       TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['media', 'media_files', 'novels', 'media_config'] LOOP
    EXECUTE format('ALTER TABLE corpus.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corpus.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- 2. Helpers (the owner's only).
-- An editor: an admin or the super admin (who also holds admin). Sees drafts.
CREATE OR REPLACE FUNCTION corpus._is_editor()
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    coalesce(public.has_role(auth.uid(), 'admin'::public.app_role), false)
    OR coalesce(public.has_role(auth.uid(), 'super_admin'::public.app_role), false))
$$;

-- May this picture be shown? Novel pictures follow their novel; the others their own status.
CREATE OR REPLACE FUNCTION corpus._media_visible(p_kind text, p_status text, p_novel integer, p_editor boolean)
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT CASE
    WHEN p_editor THEN true
    WHEN p_novel IS NULL THEN p_status = 'approved'
    ELSE EXISTS (SELECT 1 FROM corpus.novels n
                 WHERE n.novel_id = p_novel AND n.retired_at IS NULL AND n.status = 'approved')
  END
$$;

-- 3. The desk's side (service_role, through the corpus-media edge function).
CREATE OR REPLACE FUNCTION public.corpus_media_state()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT jsonb_build_object(
    'scheme', 'media.1',
    'docs', (SELECT coalesce(jsonb_agg(d.doc_code ORDER BY d.doc_code), '[]'::jsonb)
             FROM corpus.docs d WHERE d.retired_at IS NULL),
    'media', (SELECT coalesce(jsonb_object_agg(m.media_key, m.row_hash), '{}'::jsonb)
              FROM corpus.media m WHERE m.retired_at IS NULL),
    'novels', (SELECT coalesce(jsonb_object_agg(n.novel_id::text, n.row_hash), '{}'::jsonb)
               FROM corpus.novels n WHERE n.retired_at IS NULL),
    'files', (SELECT coalesce(jsonb_agg(f.sha256 || ':' || f.rendition ORDER BY f.sha256, f.rendition), '[]'::jsonb)
              FROM corpus.media_files f),
    'drive_folder', (SELECT c.value FROM corpus.media_config c WHERE c.key = 'drive_folder'))
$$;

CREATE OR REPLACE FUNCTION public.corpus_media_upsert(p_rows jsonb)
RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE n integer;
BEGIN
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' OR jsonb_array_length(p_rows) > 500 THEN
    RAISE EXCEPTION 'p_rows must be a JSON array of at most 500 rows' USING ERRCODE = '22023';
  END IF;
  INSERT INTO corpus.media AS m (media_key, doc_code, kind, status, title, caption_en, caption_hi, context_note,
      anchor_page, anchor_idx, anchor_verse_ref, story_id, novel_id, seq, version, width, height, sha256,
      model, license, provenance, created_at_local, approved_at_local, row_hash)
  SELECT r.media_key, r.doc_code, r.kind, r.status, r.title, r.caption_en, r.caption_hi, r.context_note,
         r.anchor_page, r.anchor_idx, r.anchor_verse_ref, r.story_id, r.novel_id, r.seq, r.version, r.width,
         r.height, r.sha256, r.model, r.license, r.provenance, r.created_at_local, r.approved_at_local, r.row_hash
  FROM jsonb_to_recordset(p_rows) AS r(media_key text, doc_code text, kind text, status text, title text,
      caption_en text, caption_hi text, context_note text, anchor_page integer, anchor_idx integer,
      anchor_verse_ref text, story_id integer, novel_id integer, seq integer, version integer, width integer,
      height integer, sha256 text, model text, license text, provenance text, created_at_local text,
      approved_at_local text, row_hash text)
  ON CONFLICT (media_key) DO UPDATE SET
      doc_code = EXCLUDED.doc_code, kind = EXCLUDED.kind, status = EXCLUDED.status, title = EXCLUDED.title,
      caption_en = EXCLUDED.caption_en, caption_hi = EXCLUDED.caption_hi, context_note = EXCLUDED.context_note,
      anchor_page = EXCLUDED.anchor_page, anchor_idx = EXCLUDED.anchor_idx,
      anchor_verse_ref = EXCLUDED.anchor_verse_ref, story_id = EXCLUDED.story_id, novel_id = EXCLUDED.novel_id,
      seq = EXCLUDED.seq, version = EXCLUDED.version, width = EXCLUDED.width, height = EXCLUDED.height,
      sha256 = EXCLUDED.sha256, model = EXCLUDED.model, license = EXCLUDED.license,
      provenance = EXCLUDED.provenance, created_at_local = EXCLUDED.created_at_local,
      approved_at_local = EXCLUDED.approved_at_local, row_hash = EXCLUDED.row_hash,
      synced_at = now(), retired_at = NULL
  WHERE m.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR m.retired_at IS NOT NULL;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_novels_upsert(p_rows jsonb)
RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE n integer;
BEGIN
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' OR jsonb_array_length(p_rows) > 100 THEN
    RAISE EXCEPTION 'p_rows must be a JSON array of at most 100 rows' USING ERRCODE = '22023';
  END IF;
  INSERT INTO corpus.novels AS v (novel_id, doc_code, story_id, status, audience, title, title_hi, pages, plan,
      verify, cover_seq, model, image_model, aspect, provenance, created_at_local, updated_at_local,
      approved_at_local, row_hash)
  SELECT r.novel_id, r.doc_code, r.story_id, r.status, r.audience, r.title, r.title_hi, r.pages, r.plan,
         r.verify, r.cover_seq, r.model, r.image_model, r.aspect, r.provenance, r.created_at_local,
         r.updated_at_local, r.approved_at_local, r.row_hash
  FROM jsonb_to_recordset(p_rows) AS r(novel_id integer, doc_code text, story_id integer, status text,
      audience text, title text, title_hi text, pages integer, plan jsonb, verify jsonb, cover_seq integer,
      model text, image_model text, aspect text, provenance text, created_at_local text, updated_at_local text,
      approved_at_local text, row_hash text)
  ON CONFLICT (novel_id) DO UPDATE SET
      doc_code = EXCLUDED.doc_code, story_id = EXCLUDED.story_id, status = EXCLUDED.status,
      audience = EXCLUDED.audience, title = EXCLUDED.title, title_hi = EXCLUDED.title_hi, pages = EXCLUDED.pages,
      plan = EXCLUDED.plan, verify = EXCLUDED.verify, cover_seq = EXCLUDED.cover_seq, model = EXCLUDED.model,
      image_model = EXCLUDED.image_model, aspect = EXCLUDED.aspect, provenance = EXCLUDED.provenance,
      created_at_local = EXCLUDED.created_at_local, updated_at_local = EXCLUDED.updated_at_local,
      approved_at_local = EXCLUDED.approved_at_local, row_hash = EXCLUDED.row_hash,
      synced_at = now(), retired_at = NULL
  WHERE v.row_hash IS DISTINCT FROM EXCLUDED.row_hash OR v.retired_at IS NOT NULL;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_media_retire(p_media text[], p_novels integer[])
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE a integer; b integer;
BEGIN
  IF coalesce(cardinality(p_media), 0) > 5000 OR coalesce(cardinality(p_novels), 0) > 1000 THEN
    RAISE EXCEPTION 'at most 5000 pictures and 1000 novels a call' USING ERRCODE = '22023';
  END IF;
  UPDATE corpus.media m SET retired_at = now()
  WHERE m.media_key = ANY (coalesce(p_media, ARRAY[]::text[])) AND m.retired_at IS NULL;
  GET DIAGNOSTICS a = ROW_COUNT;
  UPDATE corpus.novels v SET retired_at = now()
  WHERE v.novel_id = ANY (coalesce(p_novels, ARRAY[]::integer[])) AND v.retired_at IS NULL;
  GET DIAGNOSTICS b = ROW_COUNT;
  RETURN jsonb_build_object('media', a, 'novels', b);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_media_file_get(p_sha text, p_rendition text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT to_jsonb(f) FROM corpus.media_files f WHERE f.sha256 = p_sha AND f.rendition = p_rendition
$$;

CREATE OR REPLACE FUNCTION public.corpus_media_file_put(p_row jsonb)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE n integer;
BEGIN
  INSERT INTO corpus.media_files (sha256, rendition, storage, file_id, mime, bytes, width, height, file_sha256)
  SELECT r.sha256, r.rendition, coalesce(r.storage, 'gdrive'), r.file_id, r.mime, r.bytes, r.width, r.height,
         r.file_sha256
  FROM jsonb_to_record(p_row) AS r(sha256 text, rendition text, storage text, file_id text, mime text,
       bytes integer, width integer, height integer, file_sha256 text)
  ON CONFLICT (sha256, rendition) DO NOTHING;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n > 0;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_media_config_get(p_key text)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT c.value FROM corpus.media_config c WHERE c.key = p_key
$$;

CREATE OR REPLACE FUNCTION public.corpus_media_config_set(p_key text, p_value text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  INSERT INTO corpus.media_config (key, value, updated_at) VALUES (p_key, p_value, now())
  ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();
  RETURN p_value;
END $$;

-- 4. The readers' side.
CREATE OR REPLACE FUNCTION public.corpus_reader_media(p_doc text DEFAULT NULL, p_story integer DEFAULT NULL,
                                                     k integer DEFAULT 60, p_offset integer DEFAULT 0)
RETURNS TABLE (media_key text, doc_code text, doc_title text, kind text, status text, title text,
               caption_en text, caption_hi text, context_note text, anchor_page integer, anchor_idx integer,
               anchor_verse_ref text, story_id integer, width integer, height integer, sha256 text,
               has_thumb boolean, has_display boolean, model text, license text, approved_at_local text,
               total bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corpus._reader_gate();
  editor := corpus._is_editor();
  RETURN QUERY
  WITH v AS (
    SELECT m.*, coalesce(d.title, m.doc_code) AS dtitle
    FROM corpus.media m
    JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL
    WHERE m.retired_at IS NULL AND m.novel_id IS NULL
      AND (p_doc IS NULL OR m.doc_code = p_doc)
      AND (p_story IS NULL OR m.story_id = p_story)
      AND corpus._media_visible(m.kind, m.status, m.novel_id, editor)
  )
  SELECT v.media_key, v.doc_code, v.dtitle, v.kind, v.status, v.title, v.caption_en, v.caption_hi, v.context_note,
         v.anchor_page, v.anchor_idx, v.anchor_verse_ref, v.story_id, v.width, v.height, v.sha256,
         EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = v.sha256 AND f.rendition = 'thumb'),
         EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = v.sha256 AND f.rendition = 'display'),
         v.model, v.license, v.approved_at_local, count(*) OVER ()
  FROM v
  ORDER BY v.doc_code, v.anchor_page NULLS LAST, v.anchor_idx NULLS LAST, v.media_key
  LIMIT least(greatest(coalesce(k, 60), 1), 200) OFFSET greatest(coalesce(p_offset, 0), 0);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_novels(p_doc text DEFAULT NULL)
RETURNS TABLE (novel_id integer, doc_code text, doc_title text, story_id integer, story_title text,
               status text, title text, title_hi text, audience text, pages integer, cover_sha text,
               cover_has_thumb boolean, approved_at_local text, updated_at_local text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corpus._reader_gate();
  editor := corpus._is_editor();
  RETURN QUERY
  SELECT n.novel_id, n.doc_code, coalesce(d.title, n.doc_code), n.story_id,
         (SELECT s.title FROM corpus.stories s WHERE s.doc_code = n.doc_code AND s.story_id = n.story_id
            AND s.retired_at IS NULL),
         n.status, n.title, n.title_hi, n.audience, n.pages, c.sha256,
         EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = c.sha256 AND f.rendition = 'thumb'),
         n.approved_at_local, n.updated_at_local
  FROM corpus.novels n
  JOIN corpus.docs d ON d.doc_code = n.doc_code AND d.retired_at IS NULL
  LEFT JOIN LATERAL (
    SELECT m.sha256 FROM corpus.media m
    WHERE m.novel_id = n.novel_id AND m.kind = 'novel_page' AND m.retired_at IS NULL
    ORDER BY (m.seq = coalesce(n.cover_seq, 1)) DESC, m.seq LIMIT 1) c ON true
  WHERE n.retired_at IS NULL
    AND (p_doc IS NULL OR n.doc_code = p_doc)
    AND (n.status = 'approved' OR editor)
  ORDER BY n.doc_code, n.novel_id;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_novel(p_id integer)
RETURNS TABLE (novel_id integer, doc_code text, doc_title text, story_id integer, story_title text,
               status text, title text, title_hi text, audience text, pages integer, plan jsonb, verify jsonb,
               cover_seq integer, model text, image_model text, aspect text, approved_at_local text,
               media jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corpus._reader_gate();
  editor := corpus._is_editor();
  RETURN QUERY
  SELECT n.novel_id, n.doc_code, coalesce(d.title, n.doc_code), n.story_id,
         (SELECT s.title FROM corpus.stories s WHERE s.doc_code = n.doc_code AND s.story_id = n.story_id
            AND s.retired_at IS NULL),
         n.status, n.title, n.title_hi, n.audience, n.pages, n.plan, n.verify, n.cover_seq, n.model,
         n.image_model, n.aspect, n.approved_at_local,
         (SELECT coalesce(jsonb_agg(jsonb_build_object(
                    'key', m.media_key, 'kind', m.kind, 'seq', m.seq, 'status', m.status, 'title', m.title,
                    'sha256', m.sha256, 'width', m.width, 'height', m.height, 'version', m.version,
                    'has_thumb', EXISTS (SELECT 1 FROM corpus.media_files f
                                         WHERE f.sha256 = m.sha256 AND f.rendition = 'thumb'),
                    'has_display', EXISTS (SELECT 1 FROM corpus.media_files f
                                           WHERE f.sha256 = m.sha256 AND f.rendition = 'display'))
                  ORDER BY m.kind DESC, m.seq), '[]'::jsonb)
            FROM corpus.media m WHERE m.novel_id = n.novel_id AND m.retired_at IS NULL)
  FROM corpus.novels n
  JOIN corpus.docs d ON d.doc_code = n.doc_code AND d.retired_at IS NULL
  WHERE n.novel_id = p_id AND n.retired_at IS NULL AND (n.status = 'approved' OR editor);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_media_file(p_sha text, p_rendition text)
RETURNS TABLE (file_id text, mime text, bytes integer, storage text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corpus._reader_gate();
  IF p_sha IS NULL OR p_sha !~ '^[0-9a-f]{64}$' OR p_rendition IS NULL OR p_rendition NOT IN ('thumb', 'display') THEN
    RETURN;
  END IF;
  editor := corpus._is_editor();
  RETURN QUERY
  SELECT f.file_id, f.mime, f.bytes, f.storage
  FROM corpus.media_files f
  WHERE f.sha256 = p_sha AND f.rendition = p_rendition
    AND EXISTS (SELECT 1 FROM corpus.media m
                JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL
                WHERE m.sha256 = p_sha AND m.retired_at IS NULL
                  AND corpus._media_visible(m.kind, m.status, m.novel_id, editor));
END $$;

-- 5. Who may call what.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['corpus._is_editor()', 'corpus._media_visible(text, text, integer, boolean)',
      'public.corpus_media_state()', 'public.corpus_media_upsert(jsonb)', 'public.corpus_novels_upsert(jsonb)',
      'public.corpus_media_retire(text[], integer[])', 'public.corpus_media_file_get(text, text)',
      'public.corpus_media_file_put(jsonb)', 'public.corpus_media_config_get(text)',
      'public.corpus_media_config_set(text, text)',
      'public.corpus_reader_media(text, integer, integer, integer)', 'public.corpus_reader_novels(text)',
      'public.corpus_reader_novel(integer)', 'public.corpus_reader_media_file(text, text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corpus_reader_media(text, integer, integer, integer),
      public.corpus_reader_novels(text), public.corpus_reader_novel(integer),
      public.corpus_reader_media_file(text, text) TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.corpus_media_state(), public.corpus_media_upsert(jsonb),
      public.corpus_novels_upsert(jsonb), public.corpus_media_retire(text[], integer[]),
      public.corpus_media_file_get(text, text), public.corpus_media_file_put(jsonb),
      public.corpus_media_config_get(text), public.corpus_media_config_set(text, text) TO service_role;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
