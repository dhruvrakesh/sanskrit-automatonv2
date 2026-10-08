-- ============================================================
-- C5 - the working corpus for signed-in readers (docs/CORPUS_MIRROR_2026-10-08.md, "Reading it")
-- CORPUS_READER_C5_2026_10_08
--
-- What it adds: six read-only functions that the Srangam pages /corpus and /corpus/:docCode (and
-- the edge function search-corpus) call AS THE SIGNED-IN READER. The schema corpus stays closed:
-- no table or view is granted to anyone; these functions read it for the caller after one check,
-- corpus_reader_allowed():
--   - an admin (has_role(uid, 'admin')) may always read;
--   - corpus.reader_access.mode decides for everyone else:
--       'signed_in' (the default here): any signed-in user;
--       'readers': only users listed in corpus.readers;
--       'admins': admins only.
--   Not signed in = refused (42501), whatever the mode. A missing setting row means 'admins'.
-- Change it in the SQL editor, at any time:
--   UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();
--   INSERT INTO corpus.readers (user_id, note) VALUES ('<auth.users id>', 'name') ON CONFLICT DO NOTHING;
-- NOTE: Srangam's sign-up page is open, so 'signed_in' means anyone who makes an account. The
-- mirror holds unreviewed machine translation and raw OCR (every page says so); no personal data.
--
-- Needs C4 and C4b (the counts come from corpus.group_digest). Purely additive: one settings
-- table, one reader list, three partial indexes, eight functions. Nothing existing is changed.
-- Rollback:
--   DROP FUNCTION public.corpus_reader_allowed(), public.corpus_reader_docs(text),
--     public.corpus_reader_page(text, integer, integer), public.corpus_reader_search(text, integer, text),
--     public.corpus_reader_similar(text, integer, integer, integer),
--     public.corpus_reader_match(public.halfvec, integer, text[]), corpus._reader_gate(), corpus._ordinal(text, integer, integer);
--   DROP TABLE corpus.reader_access, corpus.readers;
--   DROP INDEX corpus.corpus_passages_live, corpus.corpus_passages_english, corpus.corpus_translations_hindi;
--
-- Tested 2026-10-08 on PostgreSQL 16 + pgvector 0.8.0 with stand-ins for auth.uid() and has_role():
-- anon is refused everywhere; a signed-in user reads in mode 'signed_in', is refused in 'readers'
-- until listed and in 'admins'; an admin always reads (tests/test_corpus_sync_pg_2026_10_08.py).
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS corpus.reader_access (
    id          BOOLEAN PRIMARY KEY DEFAULT true CHECK (id),
    mode        TEXT NOT NULL DEFAULT 'signed_in' CHECK (mode IN ('signed_in', 'readers', 'admins')),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO corpus.reader_access (id, mode) VALUES (true, 'signed_in') ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS corpus.readers (
    user_id   UUID PRIMARY KEY,
    note      TEXT,
    added_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['reader_access', 'readers'] LOOP
    EXECUTE format('ALTER TABLE corpus.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corpus.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- Fast counts and positions for the reader pages (index-only where the visibility map allows).
CREATE INDEX IF NOT EXISTS corpus_passages_live ON corpus.passages (doc_code, page_no, idx)
    WHERE retired_at IS NULL;
CREATE INDEX IF NOT EXISTS corpus_passages_english ON corpus.passages (doc_code)
    WHERE retired_at IS NULL AND btrim(coalesce(translation, '')) <> '';
CREATE INDEX IF NOT EXISTS corpus_translations_hindi ON corpus.translations (doc_code)
    WHERE retired_at IS NULL AND lang = 'hi' AND btrim(coalesce(translation, '')) <> '';

-- May the caller read the working corpus?
CREATE OR REPLACE FUNCTION public.corpus_reader_allowed()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    coalesce(public.has_role(auth.uid(), 'admin'::public.app_role), false)
    OR coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins') = 'signed_in'
    OR (coalesce((SELECT a.mode FROM corpus.reader_access a WHERE a.id), 'admins') = 'readers'
        AND EXISTS (SELECT 1 FROM corpus.readers r WHERE r.user_id = auth.uid())))
$$;

CREATE OR REPLACE FUNCTION corpus._reader_gate()
RETURNS void LANGUAGE plpgsql STABLE SET search_path = '' AS $$
BEGIN
  IF NOT public.corpus_reader_allowed() THEN
    RAISE EXCEPTION 'The working corpus is open to signed-in readers only.' USING ERRCODE = '42501';
  END IF;
END $$;

-- 1-based position of a passage in its document, in reading order (page_no, idx), live rows only.
CREATE OR REPLACE FUNCTION corpus._ordinal(p_doc text, p_page integer, p_idx integer)
RETURNS bigint LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT count(*) + 1 FROM corpus.passages p
  WHERE p.doc_code = p_doc AND p.retired_at IS NULL AND (p.page_no, p.idx) < (p_page, p_idx)
$$;

-- The documents, with counts. p_doc: one document only (the reader page's header).
CREATE OR REPLACE FUNCTION public.corpus_reader_docs(p_doc text DEFAULT NULL)
RETURNS TABLE (doc_code text, title text, category text, passages bigint, english bigint, hindi bigint,
               vectors bigint, stories bigint, published boolean, synced_at timestamptz)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  SELECT d.doc_code, coalesce(d.title, d.doc_code), d.category,
         coalesce((SELECT g.n FROM corpus.group_digest g WHERE g.tbl = 'passages' AND g.grp = d.doc_code), 0)::bigint,
         (SELECT count(*) FROM corpus.passages p WHERE p.doc_code = d.doc_code
            AND p.retired_at IS NULL AND btrim(coalesce(p.translation, '')) <> ''),
         (SELECT count(*) FROM corpus.translations t WHERE t.doc_code = d.doc_code
            AND t.retired_at IS NULL AND t.lang = 'hi' AND btrim(coalesce(t.translation, '')) <> ''),
         coalesce((SELECT g.n FROM corpus.group_digest g WHERE g.tbl = 'vectors' AND g.grp = d.doc_code), 0)::bigint,
         coalesce((SELECT g.n FROM corpus.group_digest g WHERE g.tbl = 'stories' AND g.grp = d.doc_code), 0)::bigint,
         EXISTS (SELECT 1 FROM public.srangam_texts s WHERE s.doc_code = d.doc_code AND s.published),
         d.synced_at
  FROM corpus.docs d
  WHERE d.retired_at IS NULL AND (p_doc IS NULL OR d.doc_code = p_doc)
  ORDER BY 4 DESC, 1;
END $$;

-- One page of a document in reading order, with the Hindi beside the English. At most 100 rows.
CREATE OR REPLACE FUNCTION public.corpus_reader_page(p_doc text, p_offset integer DEFAULT 0, p_limit integer DEFAULT 50)
RETURNS TABLE (ord bigint, page_no integer, idx integer, verse_ref text, chapter text, text_type text,
               sanskrit text, iast text, translation text, hindi text, quality_score double precision,
               translation_qa double precision, engine text, translated_at text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  SELECT greatest(p_offset, 0) + row_number() OVER (ORDER BY p.page_no, p.idx),
         p.page_no, p.idx, p.verse_ref, p.chapter, p.text_type, p.text, p.iast, p.translation, h.translation,
         p.quality_score, p.translation_qa, p.engine, p.translated_at
  FROM (SELECT * FROM corpus.passages x
        WHERE x.doc_code = p_doc AND x.retired_at IS NULL
        ORDER BY x.page_no, x.idx
        OFFSET greatest(p_offset, 0) LIMIT least(greatest(coalesce(p_limit, 50), 1), 100)) p
  LEFT JOIN corpus.translations h
    ON h.doc_code = p.doc_code AND h.page_no = p.page_no AND h.idx = p.idx AND h.lang = 'hi' AND h.retired_at IS NULL
  ORDER BY p.page_no, p.idx;
END $$;

-- Words in the English (stemmed) and the IAST (as written). snippet marks the words with [[ ]].
CREATE OR REPLACE FUNCTION public.corpus_reader_search(q text, k integer DEFAULT 20, p_doc text DEFAULT NULL)
RETURNS TABLE (doc_code text, title text, page_no integer, idx integer, verse_ref text, ord bigint,
               score real, snippet text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE tq tsquery;
BEGIN
  PERFORM corpus._reader_gate();
  IF q IS NULL OR length(btrim(q)) < 2 OR length(q) > 200 THEN
    RAISE EXCEPTION 'Search with 2 to 200 characters.' USING ERRCODE = '22023';
  END IF;
  tq := websearch_to_tsquery('pg_catalog.english'::regconfig, q) || websearch_to_tsquery('pg_catalog.simple'::regconfig, q);
  RETURN QUERY
  WITH hits AS (
    SELECT p.doc_code, p.page_no, p.idx, p.verse_ref, p.translation, p.iast, ts_rank(p.fts, tq) AS r
    FROM corpus.passages p
    WHERE p.retired_at IS NULL AND p.fts @@ tq AND (p_doc IS NULL OR p.doc_code = p_doc)
    ORDER BY r DESC, p.doc_code, p.page_no, p.idx
    LIMIT least(greatest(coalesce(k, 20), 1), 50))
  SELECT h.doc_code, coalesce(d.title, h.doc_code), h.page_no, h.idx, h.verse_ref,
         corpus._ordinal(h.doc_code, h.page_no, h.idx), h.r,
         ts_headline('pg_catalog.english'::regconfig,
                     coalesce(nullif(btrim(coalesce(h.translation, '')), ''), h.iast, ''), tq,
                     'StartSel=[[, StopSel=]], MaxWords=35, MinWords=12, MaxFragments=2, FragmentDelimiter=" ... "')
  FROM hits h LEFT JOIN corpus.docs d ON d.doc_code = h.doc_code
  ORDER BY h.r DESC, h.doc_code, h.page_no, h.idx;
END $$;

-- Passages nearest in meaning to one passage, from its stored vector (no AI call).
CREATE OR REPLACE FUNCTION public.corpus_reader_similar(p_doc text, p_page integer, p_idx integer, k integer DEFAULT 8)
RETURNS TABLE (doc_code text, title text, page_no integer, idx integer, verse_ref text, ord bigint,
               similarity double precision, snippet text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE qv public.halfvec;
BEGIN
  PERFORM corpus._reader_gate();
  SELECT v.embedding INTO qv FROM corpus.passage_vectors v
  WHERE v.doc_code = p_doc AND v.page_no = p_page AND v.idx = p_idx AND v.retired_at IS NULL;
  IF qv IS NULL THEN RETURN; END IF;   -- not embedded yet: no neighbours, not an error
  RETURN QUERY
  SELECT m.doc_code, coalesce(d.title, m.doc_code), m.page_no, m.idx, p.verse_ref,
         corpus._ordinal(m.doc_code, m.page_no, m.idx), m.sim, left(p.translation, 420)
  FROM (SELECT v.doc_code, v.page_no, v.idx, 1 - (v.embedding OPERATOR(public.<=>) qv) AS sim
        FROM corpus.passage_vectors v
        WHERE v.retired_at IS NULL
        ORDER BY v.embedding OPERATOR(public.<=>) qv
        LIMIT least(greatest(coalesce(k, 8), 1), 20) + 1) m
  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx
  LEFT JOIN corpus.docs d ON d.doc_code = m.doc_code
  WHERE NOT (m.doc_code = p_doc AND m.page_no = p_page AND m.idx = p_idx)
  ORDER BY m.sim DESC
  LIMIT least(greatest(coalesce(k, 8), 1), 20);
END $$;

-- A question's vector (made by the edge function search-corpus) against the whole corpus.
CREATE OR REPLACE FUNCTION public.corpus_reader_match(query_embedding public.halfvec, k integer DEFAULT 10,
                                                      doc_codes text[] DEFAULT NULL)
RETURNS TABLE (doc_code text, title text, page_no integer, idx integer, verse_ref text, ord bigint,
               similarity double precision, snippet text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  IF query_embedding IS NULL THEN RETURN; END IF;
  RETURN QUERY
  SELECT m.doc_code, coalesce(d.title, m.doc_code), m.page_no, m.idx, p.verse_ref,
         corpus._ordinal(m.doc_code, m.page_no, m.idx), m.sim, left(p.translation, 420)
  FROM (SELECT v.doc_code, v.page_no, v.idx, 1 - (v.embedding OPERATOR(public.<=>) query_embedding) AS sim
        FROM corpus.passage_vectors v
        WHERE v.retired_at IS NULL AND (doc_codes IS NULL OR v.doc_code = ANY (doc_codes))
        ORDER BY v.embedding OPERATOR(public.<=>) query_embedding
        LIMIT least(greatest(coalesce(k, 10), 1), 20)) m
  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx
  LEFT JOIN corpus.docs d ON d.doc_code = m.doc_code
  ORDER BY m.sim DESC;
END $$;

-- Who may call what: the reader functions for signed-in callers only (each checks the caller
-- again); the helpers for nobody but the owner.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_allowed()', 'public.corpus_reader_docs(text)',
      'public.corpus_reader_page(text, integer, integer)', 'public.corpus_reader_search(text, integer, text)',
      'public.corpus_reader_similar(text, integer, integer, integer)',
      'public.corpus_reader_match(public.halfvec, integer, text[])',
      'corpus._reader_gate()', 'corpus._ordinal(text, integer, integer)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corpus_reader_allowed(), public.corpus_reader_docs(text),
      public.corpus_reader_page(text, integer, integer), public.corpus_reader_search(text, integer, text),
      public.corpus_reader_similar(text, integer, integer, integer),
      public.corpus_reader_match(public.halfvec, integer, text[]) TO authenticated;
  END IF;
END $$;

COMMIT;

-- ============================================================
-- Checks (one at a time).
-- R1 who may call the reader functions (expect anon false and authenticated true on all six):
-- SELECT p.oid::regprocedure, has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
-- FROM pg_proc p WHERE p.proname LIKE 'corpus\_reader\_%' ORDER BY 1;
-- R2 the access mode (expect signed_in unless you changed it):
-- SELECT mode, updated_at FROM corpus.reader_access;
-- R3 the editor itself is not a signed-in user, so this is refused there, by design:
-- SELECT * FROM public.corpus_reader_docs();   -- expect: open to signed-in readers only
-- ============================================================
