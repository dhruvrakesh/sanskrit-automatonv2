-- ============================================================
-- C20 - named together, on the site (NAME_LINKS_C20_2026_10_23)
-- docs/RELATIONS_AND_ASK_2026-10-22.md, phases R4 and U2. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C20_checks_2026-10-23.sql, one query per paste.
--
-- The desk stores the names its texts name together (scripts/entity_links.py, the table entity_links). The site
-- holds the same mentions already (corpus.mentions, mirrored), so it counts the same pairs itself rather than receive
-- them: two names in one passage of a live text, a passage naming more than 12 names left out as a list, as on the
-- desk. (On 23 Oct the site counted 45,183 such pairs; the desk 45,994, for the texts only the desk holds.)
--
-- What it adds:
--   corpus.name_links       a materialized view: name_a < name_b, passages, texts, and the first passage that names
--                           both (doc_code, page_no, idx); refreshed nightly at 04:40 UTC by pg_cron (and once here)
--   corpus._refresh_name_links()          the refresh (the owner's and postgres's only)
--   public.corpus_reader_name_links(text, integer)   for the readers (corpus._reader_gate, as every reader function):
--                           the names named with one name, most passages first, each with its first shared passage
--                           and that passage's place in its text (corpus._ordinal), for the name page's links
-- Needs C4 (the mirror), C5 (the reader gate and _ordinal) and C6. Re-running it rebuilds the view.
-- Rollback (one paste):
--   BEGIN;
--   SELECT cron.unschedule('srangam-corpus-name-links') WHERE EXISTS (SELECT 1 FROM cron.job
--     WHERE jobname = 'srangam-corpus-name-links');
--   DROP FUNCTION IF EXISTS public.corpus_reader_name_links(text, integer), corpus._refresh_name_links();
--   DROP MATERIALIZED VIEW IF EXISTS corpus.name_links;
--   COMMIT;
-- ============================================================
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.mentions') IS NULL OR to_regclass('corpus.passages') IS NULL
     OR to_regprocedure('corpus._reader_gate()') IS NULL
     OR to_regprocedure('corpus._ordinal(text,integer,integer)') IS NULL THEN
    RAISE EXCEPTION 'C20 needs C4, C5 and C6 applied first';
  END IF;
END $$;

DROP MATERIALIZED VIEW IF EXISTS corpus.name_links CASCADE;
CREATE MATERIALIZED VIEW corpus.name_links AS
WITH live AS (
  SELECT m.doc_code, m.page_no, m.idx, m.canonical
  FROM corpus.mentions m
  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL
  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx
                        AND p.retired_at IS NULL
  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE '%-RETIRED'
), kept AS (
  SELECT l.* FROM live l
  JOIN (SELECT doc_code, page_no, idx FROM live GROUP BY doc_code, page_no, idx HAVING count(*) <= 12) s
    ON s.doc_code = l.doc_code AND s.page_no = l.page_no AND s.idx = l.idx
), pairs AS (
  SELECT a.canonical AS name_a, b.canonical AS name_b, a.doc_code, a.page_no, a.idx
  FROM kept a JOIN kept b ON b.doc_code = a.doc_code AND b.page_no = a.page_no AND b.idx = a.idx
                         AND a.canonical < b.canonical
)
SELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,
       (array_agg(doc_code ORDER BY doc_code, page_no, idx))[1] AS first_doc,
       (array_agg(page_no ORDER BY doc_code, page_no, idx))[1] AS first_page,
       (array_agg(idx ORDER BY doc_code, page_no, idx))[1] AS first_idx
FROM pairs
GROUP BY name_a, name_b;
CREATE UNIQUE INDEX corpus_name_links_pair ON corpus.name_links (name_a, name_b);
CREATE INDEX corpus_name_links_b ON corpus.name_links (name_b);
REVOKE ALL ON corpus.name_links FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON corpus.name_links FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON corpus.name_links FROM authenticated'; END IF;
END $$;

CREATE OR REPLACE FUNCTION corpus._refresh_name_links()
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  REFRESH MATERIALIZED VIEW CONCURRENTLY corpus.name_links
$$;
REVOKE ALL ON FUNCTION corpus._refresh_name_links() FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.corpus_reader_name_links(p_canonical text, k integer DEFAULT 20)
RETURNS TABLE (canonical text, kind text, passages integer, texts integer, doc_code text, title text,
               page_no integer, idx integer, ord bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  WITH x AS (
    SELECT l.name_b AS other, l.passages, l.texts, l.first_doc, l.first_page, l.first_idx
    FROM corpus.name_links l WHERE l.name_a = p_canonical
    UNION ALL
    SELECT l.name_a, l.passages, l.texts, l.first_doc, l.first_page, l.first_idx
    FROM corpus.name_links l WHERE l.name_b = p_canonical
  ), top AS (
    SELECT * FROM x ORDER BY x.passages DESC, x.other LIMIT least(greatest(coalesce(k, 20), 1), 50)
  )
  SELECT t.other, e.kind, t.passages, t.texts, t.first_doc, coalesce(d.title, t.first_doc), t.first_page,
         t.first_idx, corpus._ordinal(t.first_doc, t.first_page, t.first_idx)
  FROM top t
  LEFT JOIN corpus.entities e ON e.canonical = t.other AND e.retired_at IS NULL
  LEFT JOIN corpus.docs d ON d.doc_code = t.first_doc
  ORDER BY t.passages DESC, t.other;
END $$;

DO $$
DECLARE f text := 'public.corpus_reader_name_links(text, integer)';
BEGIN
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

-- Nightly at 04:40 UTC, after the nightly jobs (03:00-04:15). pg_cron keeps one job of this name.
DO $$
BEGIN
  IF to_regnamespace('cron') IS NOT NULL THEN
    PERFORM cron.schedule('srangam-corpus-name-links', '40 4 * * *',
                          'SELECT corpus._refresh_name_links();');
  ELSE
    RAISE NOTICE 'pg_cron is not here: refresh by hand with SELECT corpus._refresh_name_links();';
  END IF;
END $$;

COMMIT;
