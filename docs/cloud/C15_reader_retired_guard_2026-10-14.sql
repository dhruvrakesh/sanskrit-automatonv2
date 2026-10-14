-- ============================================================
-- C15 - the reader's meaning search never returns a retired passage (C15_READER_GUARD_2026_10_14)
-- docs/PROVISIONAL_2026-10-14.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C15_checks_2026-10-14.sql, one query per paste.
--
-- Why. public.corpus_reader_match (Ask the corpus, through the edge function search-corpus) and
-- public.corpus_reader_similar ("similar passages") choose the nearest live vectors
-- (corpus.passage_vectors, retired_at IS NULL), then join corpus.passages on the passage's key, without
-- asking whether that passage is retired. The mirror retires a passage's vector with the passage, except
-- when it holds a large retire for a person to confirm (corpus_sync.py: "HELD ... use
-- --allow-mass-retire if that is right"). On 14 Oct it held 68 vectors of seven re-ingested texts: while
-- held, a question could be answered with the English of a retired passage.
--
-- What it changes, and nothing else: in those two functions the one line
--     JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx
-- gains " AND p.retired_at IS NULL", with a marker comment after it. Each is rewritten from its own live
-- definition (pg_get_functiondef). If the line is not there exactly once (the function was changed
-- since), nothing at all is changed: the paste stops with an error naming the function. CREATE OR REPLACE
-- keeps each function's owner, its grants, SECURITY DEFINER and search_path ''. Their signatures and
-- what they return are unchanged, so search-corpus and the reader need nothing.
--
-- Needs C5. Re-running it changes nothing (a function already carrying the marker is left as it is).
-- A re-run of C5 puts the old functions back: run this file again after one.
-- Rollback (one paste):
--   BEGIN;
--   DO $$
--   DECLARE r record; def text;
--   BEGIN
--     FOR r IN SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--              WHERE n.nspname = 'public' AND p.prosrc LIKE '%C15_READER_GUARD_2026_10_14%' LOOP
--       def := pg_get_functiondef(r.oid);
--       def := replace(def, ' AND p.retired_at IS NULL  -- C15_READER_GUARD_2026_10_14', '');
--       EXECUTE def;
--     END LOOP;
--   END $$;
--   COMMIT;
-- ============================================================

BEGIN;

DO $$
DECLARE
  mark constant text := '  -- C15_READER_GUARD_2026_10_14';
  fns  constant text[] := ARRAY[
    'public.corpus_reader_similar(text, integer, integer, integer)',
    'public.corpus_reader_match(public.halfvec, integer, text[])'];
  old  constant text := 'JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx';
  todo text[] := ARRAY[]::text[];
  i integer;
  fn regprocedure;
  def text;
  n_old integer;
BEGIN
  FOR i IN 1 .. array_length(fns, 1) LOOP
    fn := to_regprocedure(fns[i]);
    IF fn IS NULL THEN
      RAISE EXCEPTION 'C15: % is not there (C5 comes first). Nothing was changed.', fns[i];
    END IF;
    def := pg_get_functiondef(fn);
    IF position('C15_READER_GUARD_2026_10_14' IN def) > 0 THEN
      RAISE NOTICE 'C15: % already leaves retired passages out; left as it is.', fns[i];
      CONTINUE;
    END IF;
    n_old := (length(def) - length(replace(def, old, ''))) / length(old);
    IF n_old <> 1 THEN
      RAISE EXCEPTION 'C15: % is not the function C5 made (its join line is there % times). Nothing was changed.',
        fns[i], n_old;
    END IF;
    todo := todo || replace(def, old, old || ' AND p.retired_at IS NULL' || mark);
  END LOOP;
  FOR i IN 1 .. coalesce(array_length(todo, 1), 0) LOOP
    EXECUTE todo[i];
  END LOOP;
  RAISE NOTICE 'C15: % reader function(s) rewritten.', coalesce(array_length(todo, 1), 0);
END $$;

COMMIT;
