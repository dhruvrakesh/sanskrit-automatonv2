-- ============================================================
-- C5b - contents for the corpus reader (/corpus/:docCode)   READER_NAV_2026_10_08
--
-- What it adds: ONE read-only function, public.corpus_reader_outline(p_doc, p_per_page), for the
-- reader's "Contents" panel and its "go to scan page" box. Like the six C5 functions it reads the
-- closed schema for the caller after corpus._reader_gate() (signed-in readers / the reader list /
-- admins, as corpus.reader_access.mode says), and only signed-in callers may execute it.
--
-- It returns, in reading order:
--   kind 'page'     one row per reader page (p_per_page passages, 50 by default): its first
--                   passage (ord, page_no, idx) and the last scan page it reaches (last_page_no),
--                   so the panel can say "Page 3 - scan pages 11-15".
--   kind 'colophon' every passage the automaton typed 'colophon' (the closing line of a chapter or
--                   section), with up to 160 characters of its English (or its Sanskrit when it is
--                   not translated): the landmarks a reader navigates by.
-- Why not chapters: corpus.passages.chapter mostly holds the division word alone ('sarga',
-- 'parva') without its number (nirukta: 5 distinct values over 179 of 2,095 rows), so a contents
-- list built on it would mislead. Colophons and scan pages are what the data can honestly support.
--
-- Needs C4 and C5 (corpus._reader_gate). Purely additive: nothing existing is changed.
-- Rollback:  DROP FUNCTION public.corpus_reader_outline(text, integer);
--
-- Tested 2026-10-08 on PostgreSQL 16 with the Supabase stand-ins
-- (tests/test_corpus_reader_nav_pg_2026_10_08.py): anon refused; a signed-in reader gets one 'page'
-- row per 50 passages with the right scan-page range, and the colophons in order; a document of
-- 21,128 passages answers in well under a second.
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.corpus_reader_outline(p_doc text, p_per_page integer DEFAULT 50)
RETURNS TABLE (kind text, ord bigint, reader_page integer, page_no integer, idx integer,
               last_page_no integer, label text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE per integer := least(greatest(coalesce(p_per_page, 50), 10), 100);
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  WITH o AS (
    SELECT row_number() OVER (ORDER BY p.page_no, p.idx) AS ord, p.page_no, p.idx, p.text_type,
           p.translation, p.text
    FROM corpus.passages p
    WHERE p.doc_code = p_doc AND p.retired_at IS NULL),
  g AS (
    SELECT o.*, ((o.ord - 1) / per + 1)::integer AS rp FROM o),
  h AS (
    SELECT g.*, max(g.page_no) OVER (PARTITION BY g.rp) AS last_pg FROM g)
  SELECT x.kind, x.ord, x.rp, x.page_no, x.idx, x.last_pg, x.label
  FROM (
    SELECT 'page'::text AS kind, h.ord, h.rp, h.page_no, h.idx, h.last_pg::integer AS last_pg,
           NULL::text AS label, 0 AS sort2
    FROM h WHERE (h.ord - 1) % per = 0
    UNION ALL
    SELECT 'colophon'::text, h.ord, h.rp, h.page_no, h.idx, NULL::integer,
           left(coalesce(nullif(btrim(coalesce(h.translation, '')), ''), btrim(coalesce(h.text, ''))), 160), 1
    FROM h WHERE h.text_type = 'colophon') x
  ORDER BY x.ord, x.sort2
  LIMIT 5000;
END $$;

DO $$
BEGIN
  REVOKE ALL ON FUNCTION public.corpus_reader_outline(text, integer) FROM PUBLIC;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.corpus_reader_outline(text, integer) FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON FUNCTION public.corpus_reader_outline(text, integer) FROM authenticated;
    GRANT EXECUTE ON FUNCTION public.corpus_reader_outline(text, integer) TO authenticated;
  END IF;
END $$;

COMMIT;

-- ============================================================
-- Checks (one at a time).
-- N1 who may call it (expect anon false, authenticated true):
-- SELECT has_function_privilege('anon', 'public.corpus_reader_outline(text, integer)', 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', 'public.corpus_reader_outline(text, integer)', 'EXECUTE') AS authenticated;
-- N2 the editor is not a signed-in user, so this is refused there, by design:
-- SELECT * FROM public.corpus_reader_outline('nirukta');   -- expect: open to signed-in readers only
-- N3 what it will return, read directly (admin only, in the editor): pages and colophons for nirukta
-- SELECT count(*) FILTER (WHERE (ord - 1) % 50 = 0) AS reader_pages,
--        count(*) FILTER (WHERE text_type = 'colophon') AS colophons
-- FROM (SELECT row_number() OVER (ORDER BY page_no, idx) AS ord, text_type
--       FROM corpus.passages WHERE doc_code = 'nirukta' AND retired_at IS NULL) s;
-- ============================================================
