-- ============================================================
-- C17 - where a page's Sanskrit comes from, for the reader (C17_READER_SOURCES_2026_10_14, Srangam S2)
-- docs/SCHOLAR_V21_2026-10-14.md. Paste this whole file once in the Lovable Cloud SQL editor (one
-- transaction). Read-only checks: docs/cloud/C17_checks_2026-10-14.sql, one query per paste.
--
-- Why. The reader says "OCR confidence 52%" for every passage, and marks a passage below 0.5 "the
-- printed page was hard to read". MBh01 is the BORI Critical Edition's own e-text: nothing was read from a
-- scan. corpus.passages.ocr_engine says where each passage's Sanskrit comes from (gretil-bori-etext,
-- gemini-vision:gemini-2.5-flash, tesseract, tesseract-fallback, resegment-devnum ...), but
-- public.corpus_reader_page does not return it, and changing what a function returns means dropping it.
--
-- What it adds, and nothing else: one read-only function,
--     public.corpus_reader_sources(p_doc text) -> (page_no, ocr_engine, passages)
-- the live passages of one text counted by page and engine (a few hundred rows for a long text). It asks
-- corpus._reader_gate() first, as the six reader functions do (C5): signed-in readers only. SECURITY
-- DEFINER, search_path ''. No table, no grant on a table, no change to any other function. The reader
-- calls it once a text; until this is pasted the reader shows what it showed before.
--
-- Needs C5. Re-running it changes nothing.
-- Rollback (one paste):
--   DROP FUNCTION IF EXISTS public.corpus_reader_sources(text);
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C17: corpus._reader_gate() is not there (C5 comes first). Nothing was changed.';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_sources(p_doc text)
RETURNS TABLE (page_no integer, ocr_engine text, passages bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C17_READER_SOURCES_2026_10_14
  RETURN QUERY
  SELECT p.page_no, p.ocr_engine, count(*)::bigint
  FROM corpus.passages p
  WHERE p.doc_code = p_doc AND p.retired_at IS NULL
  GROUP BY p.page_no, p.ocr_engine
  ORDER BY p.page_no, count(*) DESC, p.ocr_engine;
END $$;

COMMENT ON FUNCTION public.corpus_reader_sources(text) IS
  'C17_READER_SOURCES_2026_10_14: the live passages of one text by page and ocr_engine, for the reader (signed-in readers only).';

DO $$
BEGIN
  REVOKE ALL ON FUNCTION public.corpus_reader_sources(text) FROM PUBLIC;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.corpus_reader_sources(text) FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON FUNCTION public.corpus_reader_sources(text) FROM authenticated;
    GRANT EXECUTE ON FUNCTION public.corpus_reader_sources(text) TO authenticated;
  END IF;
END $$;

COMMIT;
