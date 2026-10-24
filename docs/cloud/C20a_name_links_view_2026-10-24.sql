-- ============================================================
-- C20a - named together, on the site: the definitions (NAME_LINKS_C20_SPLIT_2026_10_24)
-- docs/RELATIONS_AND_ASK_2026-10-22.md, phases R4 and U2. ONE PASTE in the Lovable Cloud SQL editor (one short
-- transaction: it defines, it fills nothing, so it takes well under a second). First: C20_preflight_2026-10-24.sql.
-- Then C20b (the fill), then C20c (the nightly job), then C20_checks_2026-10-24.sql.
--
-- It replaces C20_name_links_2026-10-23.sql, which did all of this in one paste and ended "Server error" on the site.
-- The view and the reader are the same; what changed:
--   * the view is created WITH NO DATA; C20b fills it (the slow part alone, so a failure there says so);
--   * corpus._refresh_name_links() returns what it did ({"pairs", "was_filled", "ms"}), fills an empty view plainly
--     and a filled one CONCURRENTLY (readers keep reading while it refreshes);
--   * public.corpus_reader_name_links() returns no rows while the view is empty, so the name pages stay as they are
--     (the site shows "Named together with" only when there are rows);
--   * the nightly job is its own paste (C20c).
--
-- What it adds:
--   corpus.name_links       a materialized view: name_a < name_b, passages, texts, and the first passage that names
--                           both (first_doc, first_page, first_idx). Two names in one passage of a live text; a passage
--                           naming more than 12 names is left out as a list, as on the desk (scripts/entity_links.py).
--   corpus._refresh_name_links()                     the fill and the refresh (the owner's only)
--   public.corpus_reader_name_links(text, integer)   for the readers (corpus._reader_gate, as every reader function)
-- Needs C4 (the mirror), C5 (the reader gate and _ordinal) and C6. Re-running it empties the view until C20b runs.
-- Rollback (one paste):
--   BEGIN;
--   SELECT cron.unschedule('srangam-corpus-name-links') WHERE EXISTS (SELECT 1 FROM cron.job
--     WHERE jobname = 'srangam-corpus-name-links');
--   DROP FUNCTION IF EXISTS public.corpus_reader_name_links(text, integer), corpus._refresh_name_links();
--   DROP MATERIALIZED VIEW IF EXISTS corpus.name_links;
--   COMMIT;
-- Tested 2026-10-24 on PostgreSQL 16 with pg_cron 1.6, as a role that is not a superuser.
-- ============================================================
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.mentions') IS NULL OR to_regclass('corpus.passages') IS NULL
     OR to_regclass('corpus.docs') IS NULL OR to_regclass('corpus.entities') IS NULL
     OR to_regprocedure('corpus._reader_gate()') IS NULL
     OR to_regprocedure('corpus._ordinal(text,integer,integer)') IS NULL THEN
    RAISE EXCEPTION 'C20a needs C4, C5 and C6 applied first';
  END IF;
END $$;

DROP MATERIALIZED VIEW IF EXISTS corpus.name_links CASCADE;
DROP FUNCTION IF EXISTS corpus._refresh_name_links();

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

-- The fill (an empty view) or the refresh (a filled one, CONCURRENTLY: readers are not blocked). Returns
-- {"pairs": the view's rows after, "was_filled": whether it held rows before, "ms": how long it took}.
CREATE FUNCTION corpus._refresh_name_links()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  t0  timestamptz := clock_timestamp();
  was boolean;
  n   bigint;
BEGIN
  SELECT c.relispopulated INTO was FROM pg_catalog.pg_class c WHERE c.oid = 'corpus.name_links'::regclass;
  IF was THEN
    REFRESH MATERIALIZED VIEW CONCURRENTLY corpus.name_links;
  ELSE
    REFRESH MATERIALIZED VIEW corpus.name_links;
  END IF;
  SELECT count(*) INTO n FROM corpus.name_links;
  RETURN jsonb_build_object('pairs', n, 'was_filled', was,
                            'ms', round(extract(epoch FROM clock_timestamp() - t0) * 1000));
END $$;
REVOKE ALL ON FUNCTION corpus._refresh_name_links() FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON FUNCTION corpus._refresh_name_links() FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON FUNCTION corpus._refresh_name_links() FROM authenticated'; END IF;
END $$;

-- The names named with one name, most passages first, each with its first shared passage and that passage's place
-- in its text (corpus._ordinal), for the name page's links. No rows while the view is empty.
CREATE OR REPLACE FUNCTION public.corpus_reader_name_links(p_canonical text, k integer DEFAULT 20)
RETURNS TABLE (canonical text, kind text, passages integer, texts integer, doc_code text, title text,
               page_no integer, idx integer, ord bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();
  IF NOT coalesce((SELECT c.relispopulated FROM pg_catalog.pg_class c
                   WHERE c.oid = to_regclass('corpus.name_links')), false) THEN
    RETURN;
  END IF;
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

COMMIT;
