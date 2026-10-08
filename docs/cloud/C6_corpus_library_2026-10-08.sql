-- ============================================================
-- C6 - the library over the working corpus (/corpus, /corpus/stories, /corpus/names)
-- CORPUS_LIBRARY_C6_2026_10_08
--
-- What it adds: five read-only functions for the Srangam library pages and one index. Like C5 and
-- C5b, each function reads the closed schema for the caller after corpus._reader_gate()
-- (signed-in readers / the reader list / admins, as corpus.reader_access.mode says), and only
-- signed-in callers may execute them. Nothing in the schema is granted to anyone.
--
--   corpus_reader_progress()             every live text's pipeline stages (ingest, ocr, segment,
--                                        classify, iast, translate_en, translate_hi, qa, entities,
--                                        embed, morph, export, book) with status and reason, as
--                                        the translation desk measured them (corpus.stages).
--   corpus_reader_stories(p_doc, p_full) the stories drawn from the texts (corpus.stories).
--                                        A reader sees APPROVED stories only; an admin also sees
--                                        drafts and candidates, marked by status. Retired and
--                                        rejected stories are never returned. p_full = false
--                                        leaves the long texts out (for lists).
--   corpus_reader_names(q, p_kind, k, p_offset, p_exact)
--                                        the names index (corpus.entities): people, deities, places,
--                                        peoples, rivers, mountains and others, with how often and
--                                        in how many texts each is named (corpus.mentions).
--   corpus_reader_name(p_canonical, k, p_offset)
--                                        every passage that names one entity, in reading order,
--                                        with its reading position (for links) and the English.
--   corpus_reader_page_names(p_doc, p_offset, p_limit)
--                                        the names in one reader page of a text (the reader's
--                                        name chips), the same 50 passages as corpus_reader_page.
--
-- Approval stays a person's decision: a story becomes visible to readers when it is approved on
-- the translation desk (scripts/stories.py approve, or the dashboard's Stories page) and the
-- two-hourly mirror run carries it here.
--
-- Needs C4, C4b and C5 (corpus._reader_gate, corpus._ordinal). Purely additive.
-- Rollback:
--   DROP FUNCTION public.corpus_reader_progress(), public.corpus_reader_stories(text, boolean),
--     public.corpus_reader_names(text, text, integer, integer, boolean),
--     public.corpus_reader_name(text, integer, integer),
--     public.corpus_reader_page_names(text, integer, integer);
--   DROP INDEX corpus.corpus_mentions_canonical;
--
-- Tested 2026-10-08 on PostgreSQL 16 with the Supabase stand-ins
-- (tests/test_corpus_library_pg_2026_10_08.py): anon refused everywhere; a reader sees approved
-- stories only and an admin all but retired; names counted per text; the page's names match the
-- page's passages; 32,000 mentions answer in well under a second.
-- ============================================================

BEGIN;

CREATE INDEX IF NOT EXISTS corpus_mentions_canonical ON corpus.mentions (canonical)
    WHERE retired_at IS NULL;

-- Pipeline stages of every live text, in the desk's order.
CREATE OR REPLACE FUNCTION public.corpus_reader_progress()
RETURNS TABLE (doc_code text, stage text, status text, reason text, updated_at_local text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  SELECT s.doc_code, s.stage, s.status, left(s.reason, 300), s.updated_at_local
  FROM corpus.stages s
  JOIN corpus.docs d ON d.doc_code = s.doc_code AND d.retired_at IS NULL
  WHERE s.retired_at IS NULL AND s.stage <> 'retired'
  ORDER BY s.doc_code,
           coalesce(array_position(ARRAY['ingest', 'ocr', 'segment', 'classify', 'iast', 'translate_en',
             'translate_hi', 'qa', 'entities', 'embed', 'morph', 'export', 'book'], s.stage), 99),
           s.stage;
END $$;

-- Stories: approved for readers; admins also see drafts and candidates.
CREATE OR REPLACE FUNCTION public.corpus_reader_stories(p_doc text DEFAULT NULL, p_full boolean DEFAULT false)
RETURNS TABLE (doc_code text, doc_title text, story_id integer, status text, title text, title_hi text,
               why text, from_page integer, from_idx integer, to_page integer, to_idx integer,
               from_ord bigint, story_en text, story_hi text, quote_sa text, quote_ref text, cites text,
               verify text, model text, approved_at_local text, updated_at_local text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE admin boolean;
BEGIN
  PERFORM corpus._reader_gate();
  admin := coalesce(public.has_role(auth.uid(), 'admin'::public.app_role), false);
  RETURN QUERY
  SELECT s.doc_code, coalesce(d.title, s.doc_code), s.story_id, s.status, s.title, s.title_hi,
         CASE WHEN p_full THEN s.why END,
         s.from_page, s.from_idx, s.to_page, s.to_idx,
         CASE WHEN s.from_page IS NOT NULL AND s.from_idx IS NOT NULL
              THEN corpus._ordinal(s.doc_code, s.from_page, s.from_idx) END,
         CASE WHEN p_full THEN s.story_en END,
         CASE WHEN p_full THEN s.story_hi END,
         s.quote_sa, s.quote_ref,
         CASE WHEN p_full THEN s.cites END,
         CASE WHEN p_full THEN s.verify END,
         s.model, s.approved_at_local, s.updated_at_local
  FROM corpus.stories s
  JOIN corpus.docs d ON d.doc_code = s.doc_code AND d.retired_at IS NULL
  WHERE s.retired_at IS NULL
    AND coalesce(s.status, '') NOT IN ('retired', 'rejected')
    AND (p_doc IS NULL OR s.doc_code = p_doc)
    AND (s.status = 'approved' OR admin)
  ORDER BY s.doc_code, s.from_page NULLS LAST, s.from_idx NULLS LAST, s.story_id;
END $$;

-- The names index, with how often and in how many texts each name occurs.
CREATE OR REPLACE FUNCTION public.corpus_reader_names(q text DEFAULT NULL, p_kind text DEFAULT NULL,
                                                      k integer DEFAULT 60, p_offset integer DEFAULT 0,
                                                      p_exact boolean DEFAULT false)
RETURNS TABLE (canonical text, kind text, notes text, variants text[], mentions bigint, texts bigint,
               total bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE pat text;
BEGIN
  PERFORM corpus._reader_gate();
  IF q IS NOT NULL AND length(q) > 100 THEN
    RAISE EXCEPTION 'Search names with at most 100 characters.' USING ERRCODE = '22023';
  END IF;
  pat := '%' || replace(replace(replace(btrim(coalesce(q, '')), '\', '\\'), '%', '\%'), '_', '\_') || '%';
  RETURN QUERY
  WITH m AS (
    SELECT x.canonical, count(*) AS n, count(DISTINCT x.doc_code) AS t
    FROM corpus.mentions x WHERE x.retired_at IS NULL GROUP BY x.canonical),
  e AS (
    SELECT en.canonical, en.kind, en.notes, en.variants, coalesce(m.n, 0) AS n, coalesce(m.t, 0) AS t
    FROM corpus.entities en LEFT JOIN m ON m.canonical = en.canonical
    WHERE en.retired_at IS NULL
      AND (p_kind IS NULL OR en.kind = p_kind)
      AND (CASE
             WHEN coalesce(btrim(q), '') = '' THEN true
             WHEN p_exact THEN en.canonical = btrim(q)
             ELSE en.canonical ILIKE pat OR EXISTS (SELECT 1 FROM unnest(en.variants) v WHERE v ILIKE pat)
           END))
  SELECT e.canonical, e.kind, left(e.notes, 600), e.variants[1:12], e.n, e.t, count(*) OVER ()
  FROM e
  ORDER BY e.n DESC, e.canonical
  OFFSET greatest(coalesce(p_offset, 0), 0) LIMIT least(greatest(coalesce(k, 60), 1), 200);
END $$;

-- Every passage that names one entity, in reading order.
CREATE OR REPLACE FUNCTION public.corpus_reader_name(p_canonical text, k integer DEFAULT 50, p_offset integer DEFAULT 0)
RETURNS TABLE (doc_code text, title text, page_no integer, idx integer, verse_ref text, ord bigint,
               surface text, snippet text, total bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  WITH hits AS (
    SELECT x.doc_code, x.page_no, x.idx, x.surface, count(*) OVER () AS total
    FROM corpus.mentions x
    WHERE x.canonical = p_canonical AND x.retired_at IS NULL
    ORDER BY x.doc_code, x.page_no, x.idx
    OFFSET greatest(coalesce(p_offset, 0), 0) LIMIT least(greatest(coalesce(k, 50), 1), 100))
  SELECT h.doc_code, coalesce(d.title, h.doc_code), h.page_no, h.idx, p.verse_ref,
         corpus._ordinal(h.doc_code, h.page_no, h.idx), h.surface,
         left(coalesce(nullif(btrim(coalesce(p.translation, '')), ''), p.iast, p.text, ''), 300), h.total
  FROM hits h
  JOIN corpus.passages p ON p.doc_code = h.doc_code AND p.page_no = h.page_no AND p.idx = h.idx
                        AND p.retired_at IS NULL
  LEFT JOIN corpus.docs d ON d.doc_code = h.doc_code
  ORDER BY h.doc_code, h.page_no, h.idx;
END $$;

-- The names in one reader page (the same passages as corpus_reader_page with the same offset).
CREATE OR REPLACE FUNCTION public.corpus_reader_page_names(p_doc text, p_offset integer DEFAULT 0, p_limit integer DEFAULT 50)
RETURNS TABLE (page_no integer, idx integer, canonical text, surface text, kind text, notes text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  WITH pg AS (
    SELECT x.page_no, x.idx FROM corpus.passages x
    WHERE x.doc_code = p_doc AND x.retired_at IS NULL
    ORDER BY x.page_no, x.idx
    OFFSET greatest(p_offset, 0) LIMIT least(greatest(coalesce(p_limit, 50), 1), 100))
  SELECT pg.page_no, pg.idx, m.canonical, m.surface, e.kind, left(e.notes, 300)
  FROM pg
  JOIN corpus.mentions m ON m.doc_code = p_doc AND m.page_no = pg.page_no AND m.idx = pg.idx
                        AND m.retired_at IS NULL
  LEFT JOIN corpus.entities e ON e.canonical = m.canonical AND e.retired_at IS NULL
  ORDER BY pg.page_no, pg.idx, m.canonical;
END $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_progress()', 'public.corpus_reader_stories(text, boolean)',
      'public.corpus_reader_names(text, text, integer, integer, boolean)',
      'public.corpus_reader_name(text, integer, integer)',
      'public.corpus_reader_page_names(text, integer, integer)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
    END IF;
  END LOOP;
END $$;

COMMIT;

-- ============================================================
-- Checks (one at a time).
-- L1 who may call them (expect anon false and authenticated true on all five):
-- SELECT p.oid::regprocedure, has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated
-- FROM pg_proc p WHERE p.proname IN ('corpus_reader_progress', 'corpus_reader_stories', 'corpus_reader_names',
--   'corpus_reader_name', 'corpus_reader_page_names') ORDER BY 1;
-- L2 what the pages will show, read directly (admin only, in the editor):
-- SELECT status, count(*) FROM corpus.stories WHERE retired_at IS NULL GROUP BY 1 ORDER BY 2 DESC;
-- SELECT kind, count(*) FROM corpus.entities WHERE retired_at IS NULL GROUP BY 1 ORDER BY 2 DESC;
-- SELECT stage, status, count(*) FROM corpus.stages WHERE retired_at IS NULL GROUP BY 1, 2 ORDER BY 1, 2;
-- L3 the editor is not a signed-in user, so this is refused there, by design:
-- SELECT * FROM public.corpus_reader_progress();   -- expect: open to signed-in readers only
-- ============================================================
