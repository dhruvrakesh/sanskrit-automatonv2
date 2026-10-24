-- ============================================================
-- C20d - named together, on the site: the fast fill (NAME_LINKS_FAST_2026_10_24)
-- ONE PASTE in the Lovable Cloud SQL editor (one short transaction; it fills nothing). For the site as it stands on
-- 24 Oct: C20a and C20c pasted, the view empty, the fill (C20b) and P4 ended "Server error".
--
-- Why they failed: C20a's query joined each passage's names to themselves. On a copy the size of the site (48,491
-- mentions, a 917 MB passages table) the planner guessed that the names left after the 12-name rule were ONE row and
-- joined them pair by pair (some 1.6 billion comparisons): it ran more than 5 minutes; the editor gives up long before. The query
-- below takes each passage's names (2 to 12) as one sorted list and makes the pairs from that list: no self-join, so
-- no such guess can make it slow. The same pairs, proven equal on that copy (58,913 pairs, none different), in 0.2 s;
-- the passage check reads only the index corpus_passages_live (C5).
--
-- What it does: replaces corpus.name_links with the fast query (created WITH NO DATA: C20b fills it), the same
-- indexes and grants; and gives the nightly job a 5-minute limit of its own (SET statement_timeout), so a slow night
-- never holds the database. The reader and the refresh functions are not touched.
-- Then: C20d_checks_2026-10-24.sql F1, C20b_name_links_fill_2026-10-24.sql (expect seconds), F1 again, F2, and
-- C20_checks_2026-10-24.sql V2-V5. Pasting it again empties the view until C20b runs again.
-- Rollback: C20a_name_links_view_2026-10-24.sql as it stands defines the same fast view.
-- Tested 2026-10-24 on PostgreSQL 16 with pg_cron 1.6 (tests/test_name_links_fast_pg_2026_10_24.py).
-- ============================================================
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.name_links') IS NULL OR to_regprocedure('corpus._refresh_name_links()') IS NULL
     OR to_regprocedure('public.corpus_reader_name_links(text,integer)') IS NULL THEN
    RAISE EXCEPTION 'C20d needs C20a applied first';
  END IF;
END $$;

DROP MATERIALIZED VIEW corpus.name_links;
CREATE MATERIALIZED VIEW corpus.name_links AS
WITH named AS (
  SELECT m.doc_code, m.page_no, m.idx, m.canonical
  FROM corpus.mentions m
  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL
  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE '%-RETIRED'
), few AS (
  SELECT n.doc_code, n.page_no, n.idx, array_agg(n.canonical ORDER BY n.canonical) AS names
  FROM named n
  GROUP BY n.doc_code, n.page_no, n.idx
  HAVING count(*) BETWEEN 2 AND 12
), live AS (
  SELECT f.doc_code, f.page_no, f.idx, f.names FROM few f
  WHERE EXISTS (SELECT 1 FROM corpus.passages p WHERE p.doc_code = f.doc_code AND p.page_no = f.page_no
                AND p.idx = f.idx AND p.retired_at IS NULL)
), pairs AS (
  SELECT x.a AS name_a, y.b AS name_b, l.doc_code, l.page_no, l.idx
  FROM live l
  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS x(a, i)
  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS y(b, j)
  WHERE x.i < y.j
)
SELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,
       (array_agg(doc_code ORDER BY doc_code, page_no, idx))[1] AS first_doc,
       (array_agg(page_no ORDER BY doc_code, page_no, idx))[1] AS first_page,
       (array_agg(idx ORDER BY doc_code, page_no, idx))[1] AS first_idx
FROM pairs
GROUP BY name_a, name_b
WITH NO DATA;
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

-- The nightly job (C20c) with a time limit of its own; pg_cron keeps one job of a name, so its jobid stays.
DO $$
BEGIN
  IF to_regclass('cron.job') IS NOT NULL
     AND EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'srangam-corpus-name-links') THEN
    PERFORM cron.schedule('srangam-corpus-name-links', '40 4 * * *',
                          'SET statement_timeout = ''5min''; SELECT corpus._refresh_name_links();');
  END IF;
END $$;

COMMIT;
