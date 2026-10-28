-- ============================================================
-- C24 - a search over the scholarly English (C24_SCHOLAR_SEARCH_2026_10_28, Srangam X1C_SITE_2026_10_28)
-- docs/B2_AND_X1C_2026-10-28.md. Paste this whole file once in the Lovable Cloud SQL editor (one transaction), after
-- C22. Read-only checks: docs/cloud/C24_checks_2026-10-28.sql (in C23_checks_2026-10-28.sql), one query per paste.
--
-- Why (X1c). The site's word search (C5, corpus_reader_search) reads the working English and the IAST; the scholarly
-- English (corpus.translations, lang 'en-x-scholar': 1,671 verses of 4 texts on 21 Oct) could be read verse by verse
-- and as prose (C18, C22) but not searched.
--
-- What it adds: one helper, corpus._scholar_fts(text) (the English stemmed, and every word as written, as C4's
-- passages.fts weighs the English and the IAST), a partial GIN index over the live scholarly rows, and
-- public.corpus_reader_scholar_search(q, k, p_doc) behind the readers' gate (C5: signed-in readers only), whose rows
-- have the shape of corpus_reader_search's (doc_code, title, page_no, idx, verse_ref, ord, score, snippet with [[ ]]
-- around the words found), so the site shows them as it shows a word search. Live passages of live texts only.
-- Nothing existing is changed.
--
-- Needs C22 (and so C4, C5, C18). Re-running it changes nothing.
-- Rollback (one paste):
--   DROP FUNCTION IF EXISTS public.corpus_reader_scholar_search(text, integer, text);
--   DROP INDEX IF EXISTS corpus.corpus_translations_scholar_fts;
--   DROP FUNCTION IF EXISTS corpus._scholar_fts(text);
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('public.corpus_reader_scholar_docs()') IS NULL OR to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C24: C22 is not there (C22 comes first). Nothing was changed.';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION corpus._scholar_fts(p text) RETURNS tsvector
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = '' AS $$
  SELECT setweight(to_tsvector('pg_catalog.english'::regconfig, coalesce(p, '')), 'A') ||
         setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(p, '')), 'B')
$$;

CREATE INDEX IF NOT EXISTS corpus_translations_scholar_fts ON corpus.translations
    USING gin (corpus._scholar_fts(translation)) WHERE lang = 'en-x-scholar' AND retired_at IS NULL;

CREATE OR REPLACE FUNCTION public.corpus_reader_scholar_search(q text, k integer DEFAULT 20, p_doc text DEFAULT NULL)
RETURNS TABLE (doc_code text, title text, page_no integer, idx integer, verse_ref text, ord bigint,
               score real, snippet text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE tq tsquery;
BEGIN
  PERFORM corpus._reader_gate();   -- C24_SCHOLAR_SEARCH_2026_10_28
  IF q IS NULL OR length(btrim(q)) < 2 OR length(q) > 200 THEN
    RAISE EXCEPTION 'Search with 2 to 200 characters.' USING ERRCODE = '22023';
  END IF;
  tq := websearch_to_tsquery('pg_catalog.english'::regconfig, q) || websearch_to_tsquery('pg_catalog.simple'::regconfig, q);
  RETURN QUERY
  WITH hits AS (
    SELECT t.doc_code, t.page_no, t.idx, t.translation, ts_rank(corpus._scholar_fts(t.translation), tq) AS r
    FROM corpus.translations t
    WHERE t.lang = 'en-x-scholar' AND t.retired_at IS NULL AND corpus._scholar_fts(t.translation) @@ tq
      AND (p_doc IS NULL OR t.doc_code = p_doc))
  SELECT h.doc_code, coalesce(d.title, h.doc_code), h.page_no, h.idx, p.verse_ref,
         corpus._ordinal(h.doc_code, h.page_no, h.idx), h.r,
         ts_headline('pg_catalog.english'::regconfig, h.translation, tq,
                     'StartSel=[[, StopSel=]], MaxWords=35, MinWords=12, MaxFragments=2, FragmentDelimiter=" ... "')
  FROM hits h
  JOIN corpus.passages p ON p.doc_code = h.doc_code AND p.page_no = h.page_no AND p.idx = h.idx
                        AND p.retired_at IS NULL
  JOIN corpus.docs d ON d.doc_code = h.doc_code AND d.retired_at IS NULL
  ORDER BY h.r DESC, h.doc_code, h.page_no, h.idx
  LIMIT least(greatest(coalesce(k, 20), 1), 50);
END $$;

COMMENT ON FUNCTION public.corpus_reader_scholar_search(text, integer, text) IS
  'C24_SCHOLAR_SEARCH_2026_10_28: words in the scholarly English, live verses only (signed-in readers only).';

DO $$
BEGIN
  REVOKE ALL ON FUNCTION corpus._scholar_fts(text) FROM PUBLIC;
  REVOKE ALL ON FUNCTION public.corpus_reader_scholar_search(text, integer, text) FROM PUBLIC;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.corpus_reader_scholar_search(text, integer, text) FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corpus_reader_scholar_search(text, integer, text) TO authenticated;
  END IF;
END $$;

COMMIT;
