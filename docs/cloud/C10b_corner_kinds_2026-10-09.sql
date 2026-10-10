-- ============================================================
-- C10b - the Corner level with the desk: eight new kinds of request (CORNER_C10B_2026_10_09)
-- docs/RESEARCHERS_CORNER_2026-10-09.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C10b_checks_2026-10-09.sql, one query per paste.
--
-- What it adds:
--   corner.kinds  eight new rows (the estimates in USD at the desk's prices, as in C9; an estimate
--                 changed since is kept on a re-run):
--     story_edit       Edit a story                          free                       sort 25
--     story_verify     Check a story against its citations   free                       sort 26
--     picture_ideas    Ideas for pictures in a text          paid, $0.02 a request      sort 42
--     picture_cover    An idea for a cover                   paid, $0.01 a request      sort 44
--     picture_draw     Draw an idea                          paid, $0.10 a request      sort 46
--     picture_edit     Edit a picture's words                free                       sort 65
--     picture_restore  Restore a retired picture             free, editors only         sort 145
--     novel_page_edit  Edit a graphic novel's page           free                       sort 155
--   A free request is approved at once (as in C9: only paid requests of researchers wait for an
--   editor); the desk re-checks every one of them against its own database before it acts.
--   public.corner_ideas(p_doc)             the ideas for pictures the desk proposed for a text (done
--                                          picture_ideas and picture_cover requests, everyone's),
--                                          newest first, at most 200: whether each is drawn, and the
--                                          newest request to draw it. For researchers and editors.
--   public.corner_retired_pictures(p_doc)  a text's retired pictures, newest first, at most 200, and
--                                          whether the site still has the file. Editors only.
-- What it changes (CREATE OR REPLACE; the same signatures, the same grants: nobody but the owner):
--   corner._clean     every C9 kind is checked and returned exactly as in C9, but for two: the
--                     parameters of novel_cast and novel_draw now always carry "redo": true|false
--                     (true when the asker gave redo true or 1: draw the cast, or every page asked
--                     for, again even where there is a picture). The eight new kinds are checked
--                     against the mirror: the story, picture or novel of this text, what may be
--                     changed (an approved story, picture or novel is changed by an editor only; a
--                     picture's licence by an editor only; a proposed episode only in its title), and
--                     the bounds of every field. An edit carries {"fields": {...}, "editor": true|false}.
--   corner._estimate  as in C9. novel_draw with no pages is priced at every page of the novel, with
--                     redo or without (as C9 did).
--
-- The order: the desk's worker 1.2 FIRST (docs/desk/CORNER_C10_2026-10-09, patched in by
-- scripts/patch_corner_worker_c10_2026_10_09.py: it knows the new kinds and "redo", and is harmless
-- before this file), THEN this file. C12 (the Corner's mail) is independent of it: before or after.
-- Worker 1.1 would fail a request of a new kind it does not know, and would draw a "redo" request
-- without redrawing.
--
-- Needs C9 (and so C8). C10a is not needed by this file, but comes before it in the order. Purely
-- additive but for corner._clean and corner._estimate. Re-running it changes nothing. A re-run of C9
-- puts C9's corner._clean back (and the new kinds would then be refused as unknown): run this file
-- again after any re-run of C9.
-- Rollback (one paste: C9's own corner._clean and corner._estimate again, then the rest; a kind that
-- a request uses stays in corner.kinds, unknown to corner._clean from then on):
--   BEGIN;
--   CREATE OR REPLACE FUNCTION corner._clean(p_kind text, p_doc text, p jsonb)
--   RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = '' AS $$
--   DECLARE a integer[]; b integer[]; sid integer; iid integer; nid integer; st text; pg integer[]; npages integer;
--   BEGIN
--     IF p IS NULL OR jsonb_typeof(p) <> 'object' THEN PERFORM corner._bad('params: a JSON object'); END IF;
--     IF p_doc IS NULL OR NOT EXISTS (SELECT 1 FROM corpus.docs d WHERE d.doc_code = p_doc AND d.retired_at IS NULL) THEN
--       PERFORM corner._bad('doc: a text of the working corpus');
--     END IF;
--     IF p_kind = 'story_range' THEN
--       a := corner._ref(p ->> 'from'); b := corner._ref(p ->> 'to');
--       IF a IS NULL OR b IS NULL THEN PERFORM corner._bad('from and to: passage references such as 18.2'); END IF;
--       IF a > b THEN PERFORM corner._bad('from must come before to'); END IF;
--       IF NOT corner._passage_ok(p_doc, a) OR NOT corner._passage_ok(p_doc, b) THEN
--         PERFORM corner._bad('from and to must be translated passages of this text');
--       END IF;
--       IF (SELECT count(*) FROM corpus.passages q WHERE q.doc_code = p_doc AND q.retired_at IS NULL
--             AND (q.page_no, q.idx) >= (a[1], a[2]) AND (q.page_no, q.idx) <= (b[1], b[2])) > 60 THEN
--         PERFORM corner._bad('a story is drawn from at most 60 passages; choose a shorter range');
--       END IF;
--       RETURN jsonb_build_object('from', a[1] || '.' || a[2], 'to', b[1] || '.' || b[2],
--         'title', corner._text(p, 'title', 3, 200, 'title'), 'why', corner._text(p, 'why', 0, 1000, 'why'));
--     ELSIF p_kind = 'story_mine' THEN
--       RETURN jsonb_build_object('max', corner._int(p, 'max', 1, 12, 'max'));
--     ELSIF p_kind = 'picture_passage' THEN
--       a := corner._ref(p ->> 'at');
--       IF NOT corner._passage_ok(p_doc, a) THEN PERFORM corner._bad('at: a translated passage of this text, such as 18.2'); END IF;
--       RETURN jsonb_build_object('at', a[1] || '.' || a[2], 'title', corner._text(p, 'title', 3, 200, 'title'),
--         'brief', corner._text(p, 'brief', 20, 2000, 'brief (what the picture should show)'),
--         'caption_en', corner._text(p, 'caption_en', 0, 500, 'caption'));
--     ELSIF p_kind IN ('story_write', 'story_illustrate', 'novel_plan', 'story_approve', 'story_retire') THEN
--       sid := corner._int(p, 'story_id', 1, 2000000000, 'story_id');
--       SELECT s.status INTO st FROM corpus.stories s
--       WHERE s.doc_code = p_doc AND s.story_id = sid AND s.retired_at IS NULL;
--       IF NOT FOUND OR st IN ('retired', 'rejected') THEN PERFORM corner._bad('story_id: a story of this text'); END IF;
--       IF p_kind = 'story_write' AND st NOT IN ('candidate', 'draft') THEN
--         PERFORM corner._bad('only a proposed episode or a draft is written (again)');
--       END IF;
--       IF p_kind = 'novel_plan' THEN
--         IF st <> 'approved' THEN PERFORM corner._bad('a graphic novel is planned from an approved story'); END IF;
--         IF coalesce(p ->> 'audience', 'general') NOT IN ('young', 'teen', 'general') THEN
--           PERFORM corner._bad('audience: young, teen or general');
--         END IF;
--         RETURN jsonb_build_object('story_id', sid, 'pages', corner._int(coalesce(p, '{}') || jsonb_build_object(
--                  'pages', coalesce(p ->> 'pages', '12')), 'pages', 8, 16, 'pages'),
--                'audience', coalesce(p ->> 'audience', 'general'));
--       END IF;
--       IF p_kind = 'story_illustrate' AND EXISTS (SELECT 1 FROM corpus.media m WHERE m.doc_code = p_doc AND m.story_id = sid
--                                                  AND m.novel_id IS NULL AND m.retired_at IS NULL) THEN
--         PERFORM corner._bad('this story already has a picture; ask for that picture to be drawn again instead');
--       END IF;
--       IF p_kind = 'story_approve' THEN
--         IF st <> 'draft' THEN PERFORM corner._bad('only a draft story is approved'); END IF;
--         RETURN jsonb_build_object('story_id', sid, 'force', coalesce(p ->> 'force', 'false') IN ('true', '1'));
--       END IF;
--       RETURN jsonb_build_object('story_id', sid);
--     ELSIF p_kind IN ('picture_redraw', 'picture_approve', 'picture_retire') THEN
--       iid := corner._int(p, 'image_id', 1, 2000000000, 'image_id');
--       SELECT m.status INTO st FROM corpus.media m WHERE m.media_key = 'img:' || iid AND m.doc_code = p_doc
--         AND m.retired_at IS NULL;
--       IF NOT FOUND THEN PERFORM corner._bad('image_id: a picture of this text'); END IF;
--       IF p_kind = 'picture_approve' AND st <> 'draft' THEN PERFORM corner._bad('only a draft picture is approved'); END IF;
--       RETURN jsonb_build_object('image_id', iid);
--     ELSIF p_kind IN ('novel_cast', 'novel_draw', 'novel_page_approve', 'novel_approve', 'novel_retire') THEN
--       nid := corner._int(p, 'novel_id', 1, 2000000000, 'novel_id');
--       SELECT v.pages INTO npages FROM corpus.novels v WHERE v.novel_id = nid AND v.doc_code = p_doc AND v.retired_at IS NULL;
--       IF NOT FOUND THEN PERFORM corner._bad('novel_id: a graphic novel of this text'); END IF;
--       IF p_kind = 'novel_draw' THEN
--         IF coalesce(p ->> 'pages', '') = '' THEN
--           RETURN jsonb_build_object('novel_id', nid, 'pages', '');
--         END IF;
--         pg := corner._pages(p ->> 'pages');
--         IF pg IS NULL THEN PERFORM corner._bad('pages: such as 1-12 or 1,3,5-7 (1 to 16)'); END IF;
--         RETURN jsonb_build_object('novel_id', nid, 'pages', p ->> 'pages');
--       ELSIF p_kind = 'novel_page_approve' THEN
--         RETURN jsonb_build_object('novel_id', nid, 'page', corner._int(p, 'page', 1, 16, 'page'));
--       ELSIF p_kind = 'novel_approve' THEN
--         RETURN jsonb_build_object('novel_id', nid, 'force', coalesce(p ->> 'force', 'false') IN ('true', '1'));
--       END IF;
--       RETURN jsonb_build_object('novel_id', nid);
--     END IF;
--     PERFORM corner._bad('unknown kind');
--     RETURN NULL;
--   END $$;
--
--   CREATE OR REPLACE FUNCTION corner._estimate(p_kind text, p_doc text, p jsonb)
--   RETURNS numeric LANGUAGE plpgsql STABLE SET search_path = '' AS $$
--   DECLARE k corner.kinds; n integer;
--   BEGIN
--     SELECT * INTO k FROM corner.kinds WHERE kind = p_kind;
--     IF NOT k.cost_bearing THEN RETURN 0; END IF;
--     IF k.unit = 'chunk' THEN
--       SELECT greatest(1, ceil(count(*) / 150.0))::integer INTO n FROM corpus.passages q
--       WHERE q.doc_code = p_doc AND q.retired_at IS NULL AND btrim(coalesce(q.translation, '')) <> '';
--       RETURN round(k.est_usd * n, 4);
--     ELSIF k.unit = 'page' THEN
--       IF coalesce(p ->> 'pages', '') = '' THEN
--         SELECT coalesce(v.pages, 12) INTO n FROM corpus.novels v WHERE v.novel_id = (p ->> 'novel_id')::integer;
--       ELSE
--         n := coalesce(cardinality(corner._pages(p ->> 'pages')), 12);
--       END IF;
--       RETURN round(k.est_usd * coalesce(n, 12), 4);
--     END IF;
--     RETURN k.est_usd;
--   END $$;
--   DROP FUNCTION IF EXISTS public.corner_ideas(text), public.corner_retired_pictures(text);
--   DELETE FROM corner.kinds k
--   WHERE k.kind IN ('story_edit', 'story_verify', 'picture_ideas', 'picture_cover', 'picture_draw',
--                    'picture_edit', 'picture_restore', 'novel_page_edit')
--     AND NOT EXISTS (SELECT 1 FROM corner.requests r WHERE r.kind = k.kind);
--   COMMIT;
--   NOTIFY pgrst, 'reload schema';
-- (Worker 1.2 can stay on the desk after a rollback: it only meets the new kinds if they are asked for.)
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins (tests/test_corner_kinds_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corner.kinds') IS NULL OR to_regclass('corner.requests') IS NULL
     OR to_regprocedure('corner._clean(text, text, jsonb)') IS NULL
     OR to_regprocedure('corner._estimate(text, text, jsonb)') IS NULL
     OR to_regprocedure('corner._gate()') IS NULL OR to_regprocedure('corner._editor_gate()') IS NULL
     OR to_regprocedure('corner._bad(text)') IS NULL
     OR to_regprocedure('corner._text(jsonb, text, integer, integer, text)') IS NULL
     OR to_regprocedure('corner._int(jsonb, text, integer, integer, text)') IS NULL
     OR to_regclass('corpus.media') IS NULL OR to_regclass('corpus.media_files') IS NULL
     OR to_regclass('corpus.novels') IS NULL OR to_regprocedure('corpus._is_editor()') IS NULL THEN
    RAISE EXCEPTION 'C10b: needs C9 (corner.kinds, corner._clean or the corner helpers are missing).';
  END IF;
END $$;

-- 1. The new kinds (as in C9: the estimate is set when a kind is added, and kept on a re-run).
INSERT INTO corner.kinds (kind, label, cost_bearing, editor_only, est_usd, unit, sort) VALUES
  ('story_edit',      'Edit a story',                          false, false, 0,      'request', 25),
  ('story_verify',    'Check a story against its citations',   false, false, 0,      'request', 26),
  ('picture_ideas',   'Ideas for pictures in a text',          true,  false, 0.0200, 'request', 42),
  ('picture_cover',   'An idea for a cover',                   true,  false, 0.0100, 'request', 44),
  ('picture_draw',    'Draw an idea',                          true,  false, 0.1000, 'request', 46),
  ('picture_edit',    'Edit a picture''s words',               false, false, 0,      'request', 65),
  ('picture_restore', 'Restore a retired picture',             false, true,  0,      'request', 145),
  ('novel_page_edit', 'Edit a graphic novel''s page',          false, false, 0,      'request', 155)
ON CONFLICT (kind) DO UPDATE SET label = EXCLUDED.label, cost_bearing = EXCLUDED.cost_bearing,
  editor_only = EXCLUDED.editor_only, unit = EXCLUDED.unit, sort = EXCLUDED.sort;

-- 2. The request's parameters, checked against the mirror and normalised; raises 22023 with a reason.
--    C9's branches first, as C9 wrote them (novel_cast and novel_draw gain "redo"), then the new kinds.
CREATE OR REPLACE FUNCTION corner._clean(p_kind text, p_doc text, p jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE a integer[]; b integer[]; sid integer; iid integer; nid integer; st text; pg integer[]; npages integer;
        redo boolean; ed boolean; f jsonb; fk text; fmin integer; fmax integer; pno integer;
BEGIN
  -- CORNER_C10B_2026_10_09: C9's corner._clean with "redo" and the eight new kinds.
  IF p IS NULL OR jsonb_typeof(p) <> 'object' THEN PERFORM corner._bad('params: a JSON object'); END IF;
  IF p_doc IS NULL OR NOT EXISTS (SELECT 1 FROM corpus.docs d WHERE d.doc_code = p_doc AND d.retired_at IS NULL) THEN
    PERFORM corner._bad('doc: a text of the working corpus');
  END IF;
  IF p_kind = 'story_range' THEN
    a := corner._ref(p ->> 'from'); b := corner._ref(p ->> 'to');
    IF a IS NULL OR b IS NULL THEN PERFORM corner._bad('from and to: passage references such as 18.2'); END IF;
    IF a > b THEN PERFORM corner._bad('from must come before to'); END IF;
    IF NOT corner._passage_ok(p_doc, a) OR NOT corner._passage_ok(p_doc, b) THEN
      PERFORM corner._bad('from and to must be translated passages of this text');
    END IF;
    IF (SELECT count(*) FROM corpus.passages q WHERE q.doc_code = p_doc AND q.retired_at IS NULL
          AND (q.page_no, q.idx) >= (a[1], a[2]) AND (q.page_no, q.idx) <= (b[1], b[2])) > 60 THEN
      PERFORM corner._bad('a story is drawn from at most 60 passages; choose a shorter range');
    END IF;
    RETURN jsonb_build_object('from', a[1] || '.' || a[2], 'to', b[1] || '.' || b[2],
      'title', corner._text(p, 'title', 3, 200, 'title'), 'why', corner._text(p, 'why', 0, 1000, 'why'));
  ELSIF p_kind = 'story_mine' THEN
    RETURN jsonb_build_object('max', corner._int(p, 'max', 1, 12, 'max'));
  ELSIF p_kind = 'picture_passage' THEN
    a := corner._ref(p ->> 'at');
    IF NOT corner._passage_ok(p_doc, a) THEN PERFORM corner._bad('at: a translated passage of this text, such as 18.2'); END IF;
    RETURN jsonb_build_object('at', a[1] || '.' || a[2], 'title', corner._text(p, 'title', 3, 200, 'title'),
      'brief', corner._text(p, 'brief', 20, 2000, 'brief (what the picture should show)'),
      'caption_en', corner._text(p, 'caption_en', 0, 500, 'caption'));
  ELSIF p_kind IN ('story_write', 'story_illustrate', 'novel_plan', 'story_approve', 'story_retire') THEN
    sid := corner._int(p, 'story_id', 1, 2000000000, 'story_id');
    SELECT s.status INTO st FROM corpus.stories s
    WHERE s.doc_code = p_doc AND s.story_id = sid AND s.retired_at IS NULL;
    IF NOT FOUND OR st IN ('retired', 'rejected') THEN PERFORM corner._bad('story_id: a story of this text'); END IF;
    IF p_kind = 'story_write' AND st NOT IN ('candidate', 'draft') THEN
      PERFORM corner._bad('only a proposed episode or a draft is written (again)');
    END IF;
    IF p_kind = 'novel_plan' THEN
      IF st <> 'approved' THEN PERFORM corner._bad('a graphic novel is planned from an approved story'); END IF;
      IF coalesce(p ->> 'audience', 'general') NOT IN ('young', 'teen', 'general') THEN
        PERFORM corner._bad('audience: young, teen or general');
      END IF;
      RETURN jsonb_build_object('story_id', sid, 'pages', corner._int(coalesce(p, '{}') || jsonb_build_object(
               'pages', coalesce(p ->> 'pages', '12')), 'pages', 8, 16, 'pages'),
             'audience', coalesce(p ->> 'audience', 'general'));
    END IF;
    IF p_kind = 'story_illustrate' AND EXISTS (SELECT 1 FROM corpus.media m WHERE m.doc_code = p_doc AND m.story_id = sid
                                               AND m.novel_id IS NULL AND m.retired_at IS NULL) THEN
      PERFORM corner._bad('this story already has a picture; ask for that picture to be drawn again instead');
    END IF;
    IF p_kind = 'story_approve' THEN
      IF st <> 'draft' THEN PERFORM corner._bad('only a draft story is approved'); END IF;
      RETURN jsonb_build_object('story_id', sid, 'force', coalesce(p ->> 'force', 'false') IN ('true', '1'));
    END IF;
    RETURN jsonb_build_object('story_id', sid);
  ELSIF p_kind IN ('picture_redraw', 'picture_approve', 'picture_retire') THEN
    iid := corner._int(p, 'image_id', 1, 2000000000, 'image_id');
    SELECT m.status INTO st FROM corpus.media m WHERE m.media_key = 'img:' || iid AND m.doc_code = p_doc
      AND m.retired_at IS NULL;
    IF NOT FOUND THEN PERFORM corner._bad('image_id: a picture of this text'); END IF;
    IF p_kind = 'picture_approve' AND st <> 'draft' THEN PERFORM corner._bad('only a draft picture is approved'); END IF;
    RETURN jsonb_build_object('image_id', iid);
  ELSIF p_kind IN ('novel_cast', 'novel_draw', 'novel_page_approve', 'novel_approve', 'novel_retire') THEN
    nid := corner._int(p, 'novel_id', 1, 2000000000, 'novel_id');
    SELECT v.pages INTO npages FROM corpus.novels v WHERE v.novel_id = nid AND v.doc_code = p_doc AND v.retired_at IS NULL;
    IF NOT FOUND THEN PERFORM corner._bad('novel_id: a graphic novel of this text'); END IF;
    -- C10b: draw the cast, or the pages asked for, again even where there is a picture.
    redo := coalesce(p ->> 'redo', 'false') IN ('true', '1');
    IF p_kind = 'novel_draw' THEN
      IF coalesce(p ->> 'pages', '') = '' THEN
        RETURN jsonb_build_object('novel_id', nid, 'pages', '', 'redo', redo);
      END IF;
      pg := corner._pages(p ->> 'pages');
      IF pg IS NULL THEN PERFORM corner._bad('pages: such as 1-12 or 1,3,5-7 (1 to 16)'); END IF;
      RETURN jsonb_build_object('novel_id', nid, 'pages', p ->> 'pages', 'redo', redo);
    ELSIF p_kind = 'novel_cast' THEN
      RETURN jsonb_build_object('novel_id', nid, 'redo', redo);
    ELSIF p_kind = 'novel_page_approve' THEN
      RETURN jsonb_build_object('novel_id', nid, 'page', corner._int(p, 'page', 1, 16, 'page'));
    ELSIF p_kind = 'novel_approve' THEN
      RETURN jsonb_build_object('novel_id', nid, 'force', coalesce(p ->> 'force', 'false') IN ('true', '1'));
    END IF;
    RETURN jsonb_build_object('novel_id', nid);

  -- C10b: the new kinds. A field is given when its key is there and is not null; a text field is
  -- trimmed, and an empty one (where allowed) is null: it clears the field.
  ELSIF p_kind IN ('story_edit', 'story_verify') THEN
    sid := corner._int(p, 'story_id', 1, 2000000000, 'story_id');
    SELECT s.status INTO st FROM corpus.stories s
    WHERE s.doc_code = p_doc AND s.story_id = sid AND s.retired_at IS NULL;
    IF NOT FOUND OR st IN ('retired', 'rejected') THEN PERFORM corner._bad('story_id: a story of this text'); END IF;
    IF p_kind = 'story_verify' THEN
      IF st IS NULL OR st NOT IN ('draft', 'approved') THEN PERFORM corner._bad('only a written story is checked'); END IF;
      RETURN jsonb_build_object('story_id', sid);
    END IF;
    ed := corpus._is_editor();
    IF st = 'approved' AND NOT ed THEN PERFORM corner._bad('only an editor changes an approved story'); END IF;
    IF st = 'candidate' AND ((p ? 'story_en' AND jsonb_typeof(p -> 'story_en') <> 'null')
                             OR (p ? 'story_hi' AND jsonb_typeof(p -> 'story_hi') <> 'null')) THEN
      PERFORM corner._bad('a proposed episode: only its title; ask for it to be written first');
    END IF;
    f := '{}'::jsonb;
    FOR fk, fmin, fmax IN SELECT v.k, v.mn, v.mx FROM (VALUES ('title', 3, 300), ('title_hi', 0, 300),
                                                              ('story_en', 20, 6000), ('story_hi', 0, 8000)) v (k, mn, mx) LOOP
      IF p ? fk AND jsonb_typeof(p -> fk) <> 'null' THEN
        f := f || jsonb_build_object(fk, corner._text(p, fk, fmin, fmax, fk));
      END IF;
    END LOOP;
    IF f = '{}'::jsonb THEN PERFORM corner._bad('nothing to change: give title, title_hi, story_en or story_hi'); END IF;
    RETURN jsonb_build_object('story_id', sid, 'fields', f, 'editor', ed);
  ELSIF p_kind = 'picture_ideas' THEN
    RETURN jsonb_build_object('max', corner._int(p || jsonb_build_object('max', coalesce(p ->> 'max', '6')),
                                                 'max', 1, 12, 'max'));
  ELSIF p_kind = 'picture_cover' THEN
    RETURN '{}'::jsonb;
  ELSIF p_kind = 'picture_draw' THEN
    iid := corner._int(p, 'image_id', 1, 2000000000, 'image_id');
    IF NOT EXISTS (SELECT 1 FROM corner.requests r
                   WHERE r.kind IN ('picture_ideas', 'picture_cover') AND r.doc_code = p_doc AND r.status = 'done'
                     AND r.result -> 'ideas' @> jsonb_build_array(jsonb_build_object('image_id', iid))) THEN
      PERFORM corner._bad('image_id: an idea the desk proposed for this text');
    END IF;
    IF EXISTS (SELECT 1 FROM corpus.media m WHERE m.media_key = 'img:' || iid AND m.retired_at IS NULL) THEN
      PERFORM corner._bad('this idea is drawn already');
    END IF;
    RETURN jsonb_build_object('image_id', iid);
  ELSIF p_kind = 'picture_edit' THEN
    iid := corner._int(p, 'image_id', 1, 2000000000, 'image_id');
    SELECT m.status INTO st FROM corpus.media m WHERE m.media_key = 'img:' || iid AND m.doc_code = p_doc
      AND m.retired_at IS NULL;
    IF NOT FOUND THEN PERFORM corner._bad('image_id: a picture of this text'); END IF;
    ed := corpus._is_editor();
    IF st = 'approved' AND NOT ed THEN PERFORM corner._bad('only an editor changes an approved picture'); END IF;
    IF p ? 'license' AND jsonb_typeof(p -> 'license') <> 'null' AND NOT ed THEN
      PERFORM corner._bad('only an editor changes a picture''s licence');
    END IF;
    f := '{}'::jsonb;
    FOR fk, fmin, fmax IN SELECT v.k, v.mn, v.mx FROM (VALUES ('title', 3, 200), ('caption_en', 0, 500),
                                                              ('caption_hi', 0, 500), ('context_note', 0, 1000),
                                                              ('license', 0, 200)) v (k, mn, mx) LOOP
      IF p ? fk AND jsonb_typeof(p -> fk) <> 'null' THEN
        f := f || jsonb_build_object(fk, corner._text(p, fk, fmin, fmax, fk));
      END IF;
    END LOOP;
    IF f = '{}'::jsonb THEN
      PERFORM corner._bad('nothing to change: give title, caption_en, caption_hi, context_note or license');
    END IF;
    RETURN jsonb_build_object('image_id', iid, 'fields', f, 'editor', ed);
  ELSIF p_kind = 'picture_restore' THEN
    iid := corner._int(p, 'image_id', 1, 2000000000, 'image_id');
    IF NOT EXISTS (SELECT 1 FROM corpus.media m WHERE m.media_key = 'img:' || iid AND m.doc_code = p_doc
                     AND m.retired_at IS NOT NULL) THEN
      PERFORM corner._bad('image_id: a retired picture of this text');
    END IF;
    RETURN jsonb_build_object('image_id', iid);
  ELSIF p_kind = 'novel_page_edit' THEN
    nid := corner._int(p, 'novel_id', 1, 2000000000, 'novel_id');
    SELECT v.pages, v.status INTO npages, st FROM corpus.novels v
    WHERE v.novel_id = nid AND v.doc_code = p_doc AND v.retired_at IS NULL;
    IF NOT FOUND THEN PERFORM corner._bad('novel_id: a graphic novel of this text'); END IF;
    ed := corpus._is_editor();
    IF st = 'approved' AND NOT ed THEN PERFORM corner._bad('only an editor changes an approved graphic novel'); END IF;
    IF coalesce(npages, 0) < 1 THEN PERFORM corner._bad('this graphic novel has no pages yet'); END IF;
    pno := corner._int(p, 'page', 1, least(npages, 16), 'page');
    f := '{}'::jsonb;
    FOR fk, fmin, fmax IN SELECT v.k, v.mn, v.mx FROM (VALUES ('scene', 10, 2000), ('caption', 0, 2000),
                                                              ('caption_hi', 0, 2000)) v (k, mn, mx) LOOP
      IF p ? fk AND jsonb_typeof(p -> fk) <> 'null' THEN
        f := f || jsonb_build_object(fk, corner._text(p, fk, fmin, fmax, fk));
      END IF;
    END LOOP;
    IF f = '{}'::jsonb THEN PERFORM corner._bad('nothing to change: give scene, caption or caption_hi'); END IF;
    RETURN jsonb_build_object('novel_id', nid, 'page', pno, 'fields', f, 'editor', ed);
  END IF;
  PERFORM corner._bad('unknown kind');
  RETURN NULL;
END $$;

-- 3. The estimate, as in C9 (unit request, page or chunk). novel_draw with no pages is every page of
--    the novel, with redo (every page is drawn again) or without (as C9: the desk may draw fewer).
CREATE OR REPLACE FUNCTION corner._estimate(p_kind text, p_doc text, p jsonb)
RETURNS numeric LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE k corner.kinds; n integer;
BEGIN
  -- CORNER_C10B_2026_10_09: C9's corner._estimate; the new paid kinds are priced per request.
  SELECT * INTO k FROM corner.kinds WHERE kind = p_kind;
  IF NOT k.cost_bearing THEN RETURN 0; END IF;
  IF k.unit = 'chunk' THEN
    SELECT greatest(1, ceil(count(*) / 150.0))::integer INTO n FROM corpus.passages q
    WHERE q.doc_code = p_doc AND q.retired_at IS NULL AND btrim(coalesce(q.translation, '')) <> '';
    RETURN round(k.est_usd * n, 4);
  ELSIF k.unit = 'page' THEN
    IF coalesce(p ->> 'pages', '') = '' THEN
      SELECT coalesce(v.pages, 12) INTO n FROM corpus.novels v WHERE v.novel_id = (p ->> 'novel_id')::integer;
    ELSE
      n := coalesce(cardinality(corner._pages(p ->> 'pages')), 12);
    END IF;
    RETURN round(k.est_usd * coalesce(n, 12), 4);
  END IF;
  RETURN k.est_usd;
END $$;

-- 4. The ideas for pictures the desk proposed for a text: every done picture_ideas and picture_cover
--    request's result {"ideas": [{"image_id", "kind", "title", "brief", "at"}, ...]}, everyone's,
--    newest first (an idea in two results: the newer), at most 200. An idea is shown only with a
--    whole-number image_id, as picture_draw finds it. drawn: the mirror has its picture (not
--    retired); draw_*: the newest request to draw it, whatever became of it.
CREATE OR REPLACE FUNCTION public.corner_ideas(p_doc text)
RETURNS TABLE (image_id integer, kind text, title text, brief text, at text, request_id bigint,
               asked_at timestamptz, drawn boolean, draw_request_id bigint, draw_status text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corner._gate();
  RETURN QUERY
  WITH e AS (
    SELECT CASE WHEN jsonb_typeof(x.idea -> 'image_id') = 'number' AND x.idea ->> 'image_id' ~ '^[0-9]{1,9}$'
                THEN (x.idea ->> 'image_id')::integer END AS iid,
           x.idea, x.n, r.id AS rid, r.requested_at AS asked
    FROM corner.requests r
    CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN jsonb_typeof(r.result -> 'ideas') = 'array'
                                                 THEN r.result -> 'ideas' ELSE '[]'::jsonb END)
                       WITH ORDINALITY AS x (idea, n)
    WHERE r.kind IN ('picture_ideas', 'picture_cover') AND r.doc_code = p_doc AND r.status = 'done'
      AND jsonb_typeof(x.idea) = 'object'
  ), i AS (
    SELECT DISTINCT ON (e.iid) e.iid, e.idea, e.n, e.rid, e.asked
    FROM e WHERE e.iid IS NOT NULL
    ORDER BY e.iid, e.asked DESC, e.rid DESC, e.n
  )
  SELECT i.iid, left(i.idea ->> 'kind', 40), left(i.idea ->> 'title', 300), left(i.idea ->> 'brief', 2000),
         left(i.idea ->> 'at', 40), i.rid, i.asked,
         EXISTS (SELECT 1 FROM corpus.media m WHERE m.media_key = 'img:' || i.iid AND m.retired_at IS NULL),
         d.id, d.status
  FROM i
  LEFT JOIN LATERAL (
    SELECT q.id, q.status FROM corner.requests q
    WHERE q.kind = 'picture_draw' AND q.doc_code = p_doc AND q.params @> jsonb_build_object('image_id', i.iid)
    ORDER BY q.requested_at DESC, q.id DESC LIMIT 1) d ON true
  ORDER BY i.asked DESC, i.rid DESC, i.n
  LIMIT 200;
END $$;

-- 5. A text's retired pictures (not the novels' pages), newest first, at most 200: for an editor
--    deciding what to restore. has_file: the site still has its display rendition.
CREATE OR REPLACE FUNCTION public.corner_retired_pictures(p_doc text)
RETURNS TABLE (image_id integer, kind text, title text, caption_en text, retired_at timestamptz, has_file boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corner._editor_gate();
  RETURN QUERY
  SELECT split_part(m.media_key, ':', 2)::integer, m.kind, m.title, m.caption_en, m.retired_at,
         EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'display')
  FROM corpus.media m
  WHERE m.media_key ~ '^img:' AND m.doc_code = p_doc AND m.retired_at IS NOT NULL
  ORDER BY m.retired_at DESC, split_part(m.media_key, ':', 2)::integer DESC
  LIMIT 200;
END $$;

-- 6. Who may call what: the two new functions for the site's signed-in people (their gates decide
--    who), the helpers for nobody but the owner, as in C9.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['corner._clean(text, text, jsonb)', 'corner._estimate(text, text, jsonb)',
                           'public.corner_ideas(text)', 'public.corner_retired_pictures(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corner_ideas(text), public.corner_retired_pictures(text) TO authenticated;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
