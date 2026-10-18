-- ============================================================
-- C18 - the scholarly English in the reader (C18_READER_SCHOLAR_2026_10_18, Srangam SCHOLAR_READER_2026_10_18)
-- docs/SCHOLAR_READER_2026-10-18.md. Paste this whole file once in the Lovable Cloud SQL editor (one
-- transaction). Read-only checks: docs/cloud/C18_checks_2026-10-18.sql, one query per paste.
--
-- Why. The automaton's scholarly English (scholar_translate.py: the register of an unabridged translation,
-- every word rendered, names and terms kept and explained in notes, judged verse by verse) reached the site
-- only as static editions (/editions). corpus_sync.py (SCHOLAR_MIRROR_2026_10_18) now sends it into
-- corpus.translations beside the Hindi, as two rows a verse:
--     lang 'en-x-scholar'       its English; translation_score its fidelity, translation_qa its fluency (1 to 5);
--     lang 'en-x-scholar-meta'  JSON in translation: status, flag, accepted, judge, notes, doubts, range, with.
-- Every function here asks for lang 'hi' only, so nothing the site shows changes until the reader asks for them.
--
-- What it adds, and nothing else: two read-only functions,
--     public.corpus_reader_scholar(p_doc text, p_offset integer, p_limit integer)
--         -> (page_no, idx, scholar, meta, fidelity, fluency, engine, made_at)
--        the scholarly rows of one reader page: the same window of live passages as corpus_reader_page
--        (ordered by page and passage, the same offset and limit), only the passages that have them;
--     public.corpus_reader_scholar_count(p_doc text) -> (verses, flagged)
--        how many of a text's verses have a scholarly English, and how many of those wait for a person.
-- Each asks corpus._reader_gate() first, as the reader functions do (C5): signed-in readers only. SECURITY
-- DEFINER, search_path ''. No table, no index, no grant on a table, no change to any other function. meta is
-- returned as text (the reader parses it), so a malformed row can never make the call fail. The reader calls
-- them once a page and once a text; until this is pasted those calls fail and the reader shows what it showed
-- before.
--
-- Needs C5. Re-running it changes nothing.
-- Rollback (one paste):
--   DROP FUNCTION IF EXISTS public.corpus_reader_scholar(text, integer, integer);
--   DROP FUNCTION IF EXISTS public.corpus_reader_scholar_count(text);
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C18: corpus._reader_gate() is not there (C5 comes first). Nothing was changed.';
  END IF;
  IF to_regclass('corpus.translations') IS NULL OR to_regclass('corpus.passages') IS NULL THEN
    RAISE EXCEPTION 'C18: corpus.translations or corpus.passages is not there (C4 comes first). Nothing was changed.';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_scholar(p_doc text, p_offset integer DEFAULT 0, p_limit integer DEFAULT 50)
RETURNS TABLE (page_no integer, idx integer, scholar text, meta text, fidelity double precision,
               fluency double precision, engine text, made_at text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C18_READER_SCHOLAR_2026_10_18
  RETURN QUERY
  SELECT p.page_no, p.idx, s.translation, m.translation, s.translation_score, s.translation_qa, s.engine,
         coalesce(s.translated_at, m.translated_at)
  FROM (SELECT x.doc_code, x.page_no, x.idx FROM corpus.passages x
        WHERE x.doc_code = p_doc AND x.retired_at IS NULL
        ORDER BY x.page_no, x.idx
        OFFSET greatest(p_offset, 0) LIMIT least(greatest(coalesce(p_limit, 50), 1), 100)) p
  LEFT JOIN corpus.translations s
    ON s.doc_code = p.doc_code AND s.page_no = p.page_no AND s.idx = p.idx
   AND s.lang = 'en-x-scholar' AND s.retired_at IS NULL
  LEFT JOIN corpus.translations m
    ON m.doc_code = p.doc_code AND m.page_no = p.page_no AND m.idx = p.idx
   AND m.lang = 'en-x-scholar-meta' AND m.retired_at IS NULL
  WHERE s.doc_code IS NOT NULL OR m.doc_code IS NOT NULL
  ORDER BY p.page_no, p.idx;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_scholar_count(p_doc text)
RETURNS TABLE (verses bigint, flagged bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C18_READER_SCHOLAR_2026_10_18
  RETURN QUERY
  SELECT count(*) FILTER (WHERE t.lang = 'en-x-scholar')::bigint,
         count(*) FILTER (WHERE t.lang = 'en-x-scholar-meta' AND position('"flag":true' IN coalesce(t.translation, '')) > 0
                            AND EXISTS (SELECT 1 FROM corpus.translations e
                                        WHERE e.doc_code = t.doc_code AND e.page_no = t.page_no AND e.idx = t.idx
                                          AND e.lang = 'en-x-scholar' AND e.retired_at IS NULL))::bigint
  FROM corpus.translations t
  JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx AND p.retired_at IS NULL
  WHERE t.doc_code = p_doc AND t.retired_at IS NULL AND t.lang IN ('en-x-scholar', 'en-x-scholar-meta');
END $$;

COMMENT ON FUNCTION public.corpus_reader_scholar(text, integer, integer) IS
  'C18_READER_SCHOLAR_2026_10_18: the scholarly English (en-x-scholar, en-x-scholar-meta) of one reader page, the window of corpus_reader_page (signed-in readers only).';
COMMENT ON FUNCTION public.corpus_reader_scholar_count(text) IS
  'C18_READER_SCHOLAR_2026_10_18: how many of a text''s verses have a scholarly English, and how many wait for a person (signed-in readers only).';

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_scholar(text, integer, integer)', 'public.corpus_reader_scholar_count(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f);
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
    END IF;
  END LOOP;
END $$;

COMMIT;
