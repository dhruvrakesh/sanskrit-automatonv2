-- ============================================================
-- C13 - the Corner's researchers see the work in progress; the offering so far (CORNER_C13_2026_10_10)
-- docs/CORNER_UX_U1_2026-10-10.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C13_checks_2026-10-10.sql, one query per paste.
--
-- Why. The Corner lets an invited researcher ask the desk to write a proposed episode (story_write),
-- to draw a picture for a draft story (story_illustrate), to edit a proposed episode or a draft
-- (story_edit), and to draw the cast and the pages of a graphic novel still being drawn (novel_cast,
-- novel_draw); corner._clean (C9, C10b) accepts all of these from her. But the reader functions showed
-- proposed episodes, drafts and novels in progress to editors only. So the Corner's lists offered her
-- approved work alone ("No proposed episode in this text"), and the links on her own finished requests
-- led to a draft she could not open.
--
-- What it adds:
--   corpus._sees_drafts()     true for an editor (an admin or the super admin), and for anyone the
--                             Corner lets ask (corner._can_request(): invited researchers and
--                             editors). The owner's only, as the other helpers.
--   public.corner_offering()  the working corpus so far, in one row, for the Corner's strip: texts with
--                             English, passages in English, stories approved, drafts, proposed
--                             episodes, pictures approved, graphic novels approved, anthologies
--                             published, the texts with English and no story yet, the requests the desk
--                             finished (in all, and in the last 7 days). For the Corner's people
--                             (corner._gate()); granted to authenticated.
-- What it changes: five reader functions see drafts with corpus._sees_drafts() instead of the editor
-- check, and nothing else:
--   public.corpus_reader_stories(text, boolean)   (C6)  admin := ... has_role admin ...
--   public.corpus_reader_media(text, integer, integer, integer)   (C8)  editor := corpus._is_editor();
--   public.corpus_reader_novels(text)             (C8)  editor := corpus._is_editor();
--   public.corpus_reader_novel(integer)           (C8)  editor := corpus._is_editor();
--   public.corpus_reader_media_file(text, text)   (C8)  editor := corpus._is_editor();
-- Each is rewritten from its own live definition (pg_get_functiondef): exactly that one line is
-- changed, and a marker comment is put after it. If the line is not there exactly once (the function
-- was changed since), nothing at all is changed: the paste stops with an error naming the function.
-- CREATE OR REPLACE keeps each function's owner, its grants, SECURITY DEFINER and search_path ''.
-- A reader of the corpus who is not invited (reader modes 'readers' and 'signed_in') sees what she saw:
-- approved work only. Retired and rejected work stays hidden from everyone, as before.
--
-- Needs C6, C8 and C9 (and what they need). Independent of C10a, C10b, C11 and C12. Re-running it
-- changes nothing (a function already carrying the marker is left as it is). A re-run of C6 or C8 puts
-- their own functions back: run this file again after one.
-- Rollback (one paste; corner_offering is simply dropped):
--   BEGIN;
--   DO $$
--   DECLARE r record; def text;
--   BEGIN
--     FOR r IN SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--              WHERE n.nspname = 'public' AND p.prosrc LIKE '%CORNER_C13_2026_10_10%' LOOP
--       def := pg_get_functiondef(r.oid);
--       def := replace(def, 'admin := corpus._sees_drafts();  -- CORNER_C13_2026_10_10',
--                      'admin := coalesce(public.has_role(auth.uid(), ''admin''::public.app_role), false);');
--       def := replace(def, 'editor := corpus._sees_drafts();  -- CORNER_C13_2026_10_10', 'editor := corpus._is_editor();');
--       EXECUTE def;
--     END LOOP;
--   END $$;
--   DROP FUNCTION IF EXISTS public.corner_offering();
--   DROP FUNCTION IF EXISTS corpus._sees_drafts();
--   COMMIT;
--   NOTIFY pgrst, 'reload schema';
-- ============================================================

BEGIN;

-- 1. The helper (the owner's only).
CREATE OR REPLACE FUNCTION corpus._sees_drafts()
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  -- CORNER_C13_2026_10_10: editors, and the Corner's invited researchers, see the work in progress.
  SELECT corpus._is_editor() OR coalesce(corner._can_request(), false)
$$;

-- 2. The five reader functions: one line each, from their live definitions; all or none.
DO $$
DECLARE
  mark constant text := '  -- CORNER_C13_2026_10_10';
  fns  constant text[] := ARRAY[
    'public.corpus_reader_stories(text, boolean)',
    'public.corpus_reader_media(text, integer, integer, integer)',
    'public.corpus_reader_novels(text)',
    'public.corpus_reader_novel(integer)',
    'public.corpus_reader_media_file(text, text)'];
  olds constant text[] := ARRAY[
    'admin := coalesce(public.has_role(auth.uid(), ''admin''::public.app_role), false);',
    'editor := corpus._is_editor();',
    'editor := corpus._is_editor();',
    'editor := corpus._is_editor();',
    'editor := corpus._is_editor();'];
  news constant text[] := ARRAY[
    'admin := corpus._sees_drafts();',
    'editor := corpus._sees_drafts();',
    'editor := corpus._sees_drafts();',
    'editor := corpus._sees_drafts();',
    'editor := corpus._sees_drafts();'];
  todo text[] := ARRAY[]::text[];
  i integer;
  fn regprocedure;
  def text;
  n_old integer;
  n_new integer;
BEGIN
  FOR i IN 1 .. array_length(fns, 1) LOOP
    fn := to_regprocedure(fns[i]);
    IF fn IS NULL THEN
      RAISE EXCEPTION 'C13: % is not there (C6 and C8 come first). Nothing was changed.', fns[i];
    END IF;
    def := pg_get_functiondef(fn);
    n_new := (length(def) - length(replace(def, news[i] || mark, ''))) / length(news[i] || mark);
    n_old := (length(def) - length(replace(def, olds[i], ''))) / length(olds[i]);
    IF n_new = 1 AND n_old = 0 THEN
      RAISE NOTICE 'C13: % already sees drafts with corpus._sees_drafts(); left as it is.', fns[i];
      CONTINUE;
    END IF;
    IF n_old <> 1 OR n_new <> 0 THEN
      RAISE EXCEPTION 'C13: % is not the function C6/C8 made (the line "%" is there % times). Nothing was changed.',
        fns[i], olds[i], n_old;
    END IF;
    todo := todo || replace(def, olds[i], news[i] || mark);
  END LOOP;
  FOR i IN 1 .. coalesce(array_length(todo, 1), 0) LOOP
    EXECUTE todo[i];
  END LOOP;
  RAISE NOTICE 'C13: % reader function(s) rewritten.', coalesce(array_length(todo, 1), 0);
END $$;

-- 3. The offering so far: one row, for the Corner's people.
CREATE OR REPLACE FUNCTION public.corner_offering()
RETURNS TABLE (texts bigint, passages_en bigint, stories_approved bigint, stories_draft bigint,
               stories_proposed bigint, pictures bigint, novels bigint, anthologies bigint, untold bigint,
               done_all bigint, done_7d bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  -- CORNER_C13_2026_10_10
  PERFORM corner._gate();
  RETURN QUERY
  WITH live AS (
    SELECT d.doc_code FROM corpus.docs d WHERE d.retired_at IS NULL
  ), en AS (
    SELECT p.doc_code, count(*) AS n
    FROM corpus.passages p JOIN live l ON l.doc_code = p.doc_code
    WHERE p.retired_at IS NULL AND btrim(coalesce(p.translation, '')) <> ''
    GROUP BY p.doc_code
  ), st AS (
    SELECT s.doc_code, s.status
    FROM corpus.stories s JOIN live l ON l.doc_code = s.doc_code
    WHERE s.retired_at IS NULL AND coalesce(s.status, '') NOT IN ('retired', 'rejected')
  )
  SELECT (SELECT count(*) FROM en),
         (SELECT coalesce(sum(en.n), 0) FROM en)::bigint,
         (SELECT count(*) FROM st WHERE st.status = 'approved'),
         (SELECT count(*) FROM st WHERE st.status = 'draft'),
         (SELECT count(*) FROM st WHERE st.status = 'candidate'),
         (SELECT count(*) FROM corpus.media m JOIN live l ON l.doc_code = m.doc_code
            WHERE m.retired_at IS NULL AND m.novel_id IS NULL AND m.status = 'approved'),
         (SELECT count(*) FROM corpus.novels v JOIN live l ON l.doc_code = v.doc_code
            WHERE v.retired_at IS NULL AND v.status = 'approved'),
         (SELECT count(*) FROM corner.collections c WHERE c.status = 'published'),
         (SELECT count(*) FROM en WHERE NOT EXISTS (SELECT 1 FROM st WHERE st.doc_code = en.doc_code)),
         (SELECT count(*) FROM corner.requests r WHERE r.status = 'done'),
         (SELECT count(*) FROM corner.requests r WHERE r.status = 'done' AND r.finished_at > now() - interval '7 days');
END $$;

-- 4. Who may call what: the helper for nobody but the owner; corner_offering for the site's
--    signed-in people (its gate decides who).
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['corpus._sees_drafts()', 'public.corner_offering()'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corner_offering() TO authenticated;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
