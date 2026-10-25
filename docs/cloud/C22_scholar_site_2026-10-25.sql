-- ============================================================
-- C22 - the scholarly English as the desk has it: every text that has it, and each read as prose
-- (C22_SCHOLAR_SITE_2026_10_25, Srangam SCHOLAR_SITE_2026_10_25). docs/SCHOLAR_SITE_2026-10-25.md.
-- Paste this whole file once in the Lovable Cloud SQL editor (one transaction). Read-only checks:
-- docs/cloud/C22_checks_2026-10-25.sql, one query per paste.
--
-- Why. Asked on 25 Oct: "why isnt scholary and prose available on srangam? i thought we were getting the best
-- bits of our local app on srangam online." The desk (127.0.0.1:5057) has /scholar (every text with a scholarly
-- English, with its counts) and /scholar/<doc>/prose (the text read as a book: a sentence over verses whole, the
-- verse numbers small, the notes at each chapter's end). The site had the scholarly English only verse by verse
-- inside the reader (C18) and in two static editions (/editions); nothing listed the texts that have it, and
-- nothing read it as prose.
--
-- What it adds, and nothing else: one partial index and two read-only functions.
--     corpus.corpus_translations_scholar   (doc_code, page_no, idx) of the live scholarly rows only
--                                          (lang en-x-scholar and en-x-scholar-meta, about 4,000 rows);
--     public.corpus_reader_scholar_docs()
--         -> (doc_code, title, category, passages, verses, flagged, accepted, fidelity, first_page, first_idx,
--             first_ord, last_made)
--        every live text with a scholarly English: how many of its verses have one, how many wait for a person
--        (flagged, as C18 counts them), how many a person accepted, the judge's mean fidelity, its first such verse
--        (and that verse's place in the reader, first_ord, as corpus_reader_page numbers it), and when the last
--        was made;
--     public.corpus_reader_scholar_prose(p_doc text, p_after_page integer, p_after_idx integer, p_limit integer)
--         -> (page_no, idx, verse_ref, chapter, has_sanskrit, colophon, scholar, meta, made_at)
--        the text's scholarly rows in reading order, after (p_after_page, p_after_idx) (NULL: from the start), at
--        most p_limit (1 to 500, default 300) a call: the verse's reference and chapter, whether it shows Sanskrit
--        and whether that Sanskrit opens with "iti" (a colophon), so that the site groups chapters as the edition
--        does (export_html.py _ref_chapters).
-- Each asks corpus._reader_gate() first, as the reader functions do (C5): signed-in readers only. SECURITY
-- DEFINER, search_path ''. meta is returned as text and never parsed here (the site parses it), so a malformed
-- row can never make a call fail; the flags are read as C18 reads them. No table, no grant on a table, no change
-- to any other function; the mirror (corpus_sync.py) and its ingest are untouched.
--
-- Needs C4, C4b, C5 and C18. Re-running it changes nothing.
-- Rollback (one paste):
--   DROP FUNCTION IF EXISTS public.corpus_reader_scholar_prose(text, integer, integer, integer);
--   DROP FUNCTION IF EXISTS public.corpus_reader_scholar_docs();
--   DROP INDEX IF EXISTS corpus.corpus_translations_scholar;
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('corpus._reader_gate()') IS NULL OR to_regprocedure('corpus._ordinal(text, integer, integer)') IS NULL THEN
    RAISE EXCEPTION 'C22: corpus._reader_gate() or corpus._ordinal() is not there (C5 comes first). Nothing was changed.';
  END IF;
  IF to_regprocedure('public.corpus_reader_scholar_count(text)') IS NULL THEN
    RAISE EXCEPTION 'C22: public.corpus_reader_scholar_count(text) is not there (C18 comes first). Nothing was changed.';
  END IF;
  IF to_regclass('corpus.translations') IS NULL OR to_regclass('corpus.passages') IS NULL OR to_regclass('corpus.docs') IS NULL THEN
    RAISE EXCEPTION 'C22: corpus.translations, corpus.passages or corpus.docs is not there (C4 comes first). Nothing was changed.';
  END IF;
END $$;

-- The live scholarly rows only: both functions read them by text, in reading order.
CREATE INDEX IF NOT EXISTS corpus_translations_scholar ON corpus.translations (doc_code, page_no, idx)
    WHERE retired_at IS NULL AND lang IN ('en-x-scholar', 'en-x-scholar-meta');

CREATE OR REPLACE FUNCTION public.corpus_reader_scholar_docs()
RETURNS TABLE (doc_code text, title text, category text, passages bigint, verses bigint, flagged bigint,
               accepted bigint, fidelity double precision, first_page integer, first_idx integer, first_ord bigint,
               last_made text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C22_SCHOLAR_SITE_2026_10_25
  RETURN QUERY
  WITH en AS (
    SELECT t.doc_code, t.page_no, t.idx, t.translation_score, t.translated_at
    FROM corpus.translations t
    JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx AND p.retired_at IS NULL
    WHERE t.lang = 'en-x-scholar' AND t.retired_at IS NULL AND btrim(coalesce(t.translation, '')) <> ''
  ), meta AS (
    SELECT t.doc_code, t.page_no, t.idx, t.translation AS m
    FROM corpus.translations t
    WHERE t.lang = 'en-x-scholar-meta' AND t.retired_at IS NULL
  ), agg AS (
    SELECT en.doc_code,
           count(*)::bigint AS verses,
           count(*) FILTER (WHERE position('"flag":true' IN coalesce(meta.m, '')) > 0)::bigint AS flagged,
           count(*) FILTER (WHERE position('"accepted":true' IN coalesce(meta.m, '')) > 0)::bigint AS accepted,
           avg(en.translation_score) AS fidelity,
           (array_agg(en.page_no ORDER BY en.page_no, en.idx))[1] AS first_page,
           (array_agg(en.idx ORDER BY en.page_no, en.idx))[1] AS first_idx,
           max(en.translated_at) AS last_made
    FROM en
    LEFT JOIN meta ON meta.doc_code = en.doc_code AND meta.page_no = en.page_no AND meta.idx = en.idx
    GROUP BY en.doc_code
  )
  SELECT d.doc_code, coalesce(d.title, d.doc_code), d.category,
         coalesce((SELECT g.n FROM corpus.group_digest g WHERE g.tbl = 'passages' AND g.grp = d.doc_code), 0)::bigint,
         a.verses, a.flagged, a.accepted, a.fidelity, a.first_page, a.first_idx,
         corpus._ordinal(d.doc_code, a.first_page, a.first_idx),
         a.last_made
  FROM agg a
  JOIN corpus.docs d ON d.doc_code = a.doc_code AND d.retired_at IS NULL
  ORDER BY a.verses DESC, d.doc_code;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_scholar_prose(p_doc text, p_after_page integer DEFAULT NULL,
                                                              p_after_idx integer DEFAULT NULL,
                                                              p_limit integer DEFAULT 300)
RETURNS TABLE (page_no integer, idx integer, verse_ref text, chapter text, has_sanskrit boolean, colophon boolean,
               scholar text, meta text, made_at text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C22_SCHOLAR_SITE_2026_10_25
  RETURN QUERY
  SELECT p.page_no, p.idx, p.verse_ref, p.chapter,
         btrim(coalesce(p.text, '')) <> '',
         btrim(coalesce(p.text, '')) LIKE U&'\0907\0924\093F%',      -- the Sanskrit opens with "iti": a colophon
         s.translation, m.translation, coalesce(s.translated_at, m.translated_at)
  FROM corpus.translations m
  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx AND p.retired_at IS NULL
  LEFT JOIN corpus.translations s
    ON s.doc_code = m.doc_code AND s.page_no = m.page_no AND s.idx = m.idx
   AND s.lang = 'en-x-scholar' AND s.retired_at IS NULL
  WHERE m.doc_code = p_doc AND m.lang = 'en-x-scholar-meta' AND m.retired_at IS NULL
    AND (p_after_page IS NULL OR (m.page_no, m.idx) > (p_after_page, coalesce(p_after_idx, -2147483648)))
  ORDER BY m.page_no, m.idx
  LIMIT least(greatest(coalesce(p_limit, 300), 1), 500);
END $$;

COMMENT ON FUNCTION public.corpus_reader_scholar_docs() IS
  'C22_SCHOLAR_SITE_2026_10_25: every live text with a scholarly English, with its counts and its first such verse (signed-in readers only).';
COMMENT ON FUNCTION public.corpus_reader_scholar_prose(text, integer, integer, integer) IS
  'C22_SCHOLAR_SITE_2026_10_25: one text''s scholarly English in reading order, for its prose page, after a (page, idx), at most 500 rows a call (signed-in readers only).';

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_scholar_docs()',
                           'public.corpus_reader_scholar_prose(text, integer, integer, integer)'] LOOP
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
