-- ============================================================
-- C9 - the Researchers' Corner (CORNER_C9_2026_10_09)
-- docs/RESEARCHERS_CORNER_2026-10-09.md. Paste this whole file once in the Lovable Cloud SQL editor
-- (one transaction). Read-only checks: docs/cloud/C9_checks_2026-10-09.sql, one query per paste.
--
-- What it adds, all in a new closed schema corner (no table is granted to anyone):
--   corner.kinds        what can be asked of the desk: a story from passages, an episode written,
--                       episodes found in a text, a picture for a passage or a story, a picture
--                       drawn again, a graphic novel planned, its cast drawn, its pages drawn; and
--                       the editors' decisions (approve or retire a story, a picture, a novel page,
--                       a novel). Each with an estimate in USD from the desk's own prices.
--   corner.requests     every request: who asked, what, the estimate, the decision (an editor
--                       approves a researcher's paid request), and what the desk did with it.
--   corner.collections  anthologies: approved stories chosen across texts, in order, with a title
--   corner.collection_items  and an introduction; drafts for their owner, published to the readers.
--   corner.settings     the daily cap (USD, India time), whether researchers' paid requests wait
--                       for an editor, and how many may wait per person.
--   corner.worker       when the desk last came for work, and what it said about itself.
--   corner.events       who did what, when.
-- Who may do what:
--   - readers of the working corpus (C5/C7 gate) see published anthologies and corner_me();
--   - researchers, admins and the super admin ask the desk and make anthologies;
--   - admins and the super admin (editors) approve or reject researchers' requests, make the
--     editors' decisions, and publish anthologies; the super admin changes the settings;
--   - the desk (service_role, through the corpus-desk edge function, signed with
--     CORPUS_SYNC_SECRET) takes approved requests and reports what it did.
-- The site never generates anything itself: every request is carried out on the desk by its own
-- scripts (stories.py, images.py, novel.py) within the desk's spend cap, and the results come back
-- through the mirror (C4) and the pictures (C8) as drafts until an editor approves them.
--
-- Needs C4, C5, C7a, C7 and C8. Purely additive: nothing that exists is changed. Re-running it
-- changes nothing (the estimates and settings already set are kept).
-- Rollback:
--   DROP FUNCTION IF EXISTS public.corner_me(), public.corner_kinds(),
--     public.corner_request_create(text, text, jsonb, text), public.corner_requests(text, text, integer, integer),
--     public.corner_request_decide(bigint, boolean, text), public.corner_request_cancel(bigint),
--     public.corner_settings_set(text, text), public.corner_collection_save(bigint, text, text, text, text, jsonb),
--     public.corner_collections(text), public.corner_collection(bigint),
--     public.corner_collection_publish(bigint, boolean), public.corner_collection_retire(bigint),
--     public.corner_desk_pull(integer, text), public.corner_desk_report(bigint, text, jsonb, text, numeric, text),
--     public.corner_desk_heartbeat(jsonb), public.corner_desk_state();
--   DROP SCHEMA IF EXISTS corner CASCADE;
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins (tests/test_corner_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.media') IS NULL OR to_regprocedure('corpus._is_editor()') IS NULL THEN
    RAISE EXCEPTION 'C9: needs C8 (corpus.media and corpus._is_editor are missing).';
  END IF;
  IF to_regprocedure('public.my_roles()') IS NULL OR to_regprocedure('public.corpus_reader_allowed()') IS NULL THEN
    RAISE EXCEPTION 'C9: needs C5 and C7 (corpus_reader_allowed and my_roles are missing).';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                 JOIN pg_namespace n ON n.oid = t.typnamespace
                 WHERE n.nspname = 'public' AND t.typname = 'app_role' AND e.enumlabel = 'researcher') THEN
    RAISE EXCEPTION 'C9: needs C7a (app_role has no researcher).';
  END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS corner;
REVOKE ALL ON SCHEMA corner FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE 'REVOKE ALL ON SCHEMA corner FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON SCHEMA corner FROM authenticated'; END IF;
END $$;

-- 1. Tables.
CREATE TABLE IF NOT EXISTS corner.kinds (
    kind          TEXT PRIMARY KEY CHECK (kind ~ '^[a-z_]{3,40}$'),
    label         TEXT NOT NULL,
    cost_bearing  BOOLEAN NOT NULL,
    editor_only   BOOLEAN NOT NULL,
    est_usd       NUMERIC(8,4) NOT NULL CHECK (est_usd >= 0 AND est_usd <= 10),
    unit          TEXT NOT NULL CHECK (unit IN ('request', 'page', 'chunk')),
    sort          INTEGER NOT NULL DEFAULT 100,
    enabled       BOOLEAN NOT NULL DEFAULT true
);
-- est_usd: one gemini-2.5-flash text call is about $0.01 at the desk's prices (cost_tracker.py);
-- one gemini-3.1-flash-image picture about $0.091 at 1K (images.py), rounded up.
INSERT INTO corner.kinds (kind, label, cost_bearing, editor_only, est_usd, unit, sort) VALUES
  ('story_range',        'A story from passages you choose',        true,  false, 0.0100, 'request', 10),
  ('story_write',        'Write a proposed episode',                 true,  false, 0.0100, 'request', 20),
  ('story_mine',         'Find episodes in a text',                  true,  false, 0.0100, 'chunk',   30),
  ('picture_passage',    'A picture for a passage',                  true,  false, 0.1000, 'request', 40),
  ('story_illustrate',   'A picture for a story',                    true,  false, 0.1100, 'request', 50),
  ('picture_redraw',     'Draw a picture again',                     true,  false, 0.1000, 'request', 60),
  ('novel_plan',         'Plan a graphic novel from a story',        true,  false, 0.0200, 'request', 70),
  ('novel_cast',         'Draw a graphic novel''s cast',             true,  false, 0.4000, 'request', 80),
  ('novel_draw',         'Draw a graphic novel''s pages',            true,  false, 0.1000, 'page',    90),
  ('story_approve',      'Approve a story',                          false, true,  0,      'request', 110),
  ('story_retire',       'Retire a story',                           false, true,  0,      'request', 120),
  ('picture_approve',    'Approve a picture',                        false, true,  0,      'request', 130),
  ('picture_retire',     'Retire a picture',                         false, true,  0,      'request', 140),
  ('novel_page_approve', 'Approve a graphic novel''s page',          false, true,  0,      'request', 150),
  ('novel_approve',      'Approve a graphic novel',                  false, true,  0,      'request', 160),
  ('novel_retire',       'Retire a graphic novel',                   false, true,  0,      'request', 170)
ON CONFLICT (kind) DO UPDATE SET label = EXCLUDED.label, cost_bearing = EXCLUDED.cost_bearing,
  editor_only = EXCLUDED.editor_only, unit = EXCLUDED.unit, sort = EXCLUDED.sort;

CREATE TABLE IF NOT EXISTS corner.settings (
    key         TEXT PRIMARY KEY CHECK (key IN ('daily_cap_usd', 'researchers_need_approval', 'max_pending_per_person')),
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  UUID
);
INSERT INTO corner.settings (key, value) VALUES
  ('daily_cap_usd', '2.00'), ('researchers_need_approval', 'true'), ('max_pending_per_person', '20')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS corner.requests (
    id             BIGSERIAL PRIMARY KEY,
    kind           TEXT NOT NULL REFERENCES corner.kinds(kind),
    doc_code       TEXT REFERENCES corpus.docs(doc_code),
    params         JSONB NOT NULL DEFAULT '{}'::jsonb,
    note           TEXT CHECK (note IS NULL OR length(note) <= 2000),
    requested_by   UUID NOT NULL,
    requested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    status         TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled',
                                                   'claimed', 'running', 'done', 'failed')),
    est_usd        NUMERIC(8,4) NOT NULL DEFAULT 0,
    decided_by     UUID,
    decided_at     TIMESTAMPTZ,
    decision_note  TEXT CHECK (decision_note IS NULL OR length(decision_note) <= 2000),
    claimed_at     TIMESTAMPTZ,
    worker         TEXT,
    attempts       INTEGER NOT NULL DEFAULT 0,
    started_at     TIMESTAMPTZ,
    finished_at    TIMESTAMPTZ,
    result         JSONB,
    message        TEXT,
    cost_usd       NUMERIC(8,4),
    log_tail       TEXT
);
CREATE INDEX IF NOT EXISTS corner_requests_status ON corner.requests (status, decided_at, id);
CREATE INDEX IF NOT EXISTS corner_requests_mine ON corner.requests (requested_by, requested_at DESC);

CREATE TABLE IF NOT EXISTS corner.collections (
    id            BIGSERIAL PRIMARY KEY,
    title         TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    title_hi      TEXT CHECK (title_hi IS NULL OR length(title_hi) <= 300),
    intro         TEXT CHECK (intro IS NULL OR length(intro) <= 8000),
    audience      TEXT NOT NULL DEFAULT 'general' CHECK (audience IN ('general', 'young', 'scholar')),
    status        TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'retired')),
    created_by    UUID NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_by  UUID,
    published_at  TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS corner.collection_items (
    collection_id  BIGINT NOT NULL REFERENCES corner.collections(id) ON DELETE CASCADE,
    pos            INTEGER NOT NULL,
    doc_code       TEXT NOT NULL,
    story_id       INTEGER NOT NULL,
    PRIMARY KEY (collection_id, pos),
    UNIQUE (collection_id, doc_code, story_id)
);

CREATE TABLE IF NOT EXISTS corner.worker (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    last_seen  TIMESTAMPTZ,
    info       JSONB
);
INSERT INTO corner.worker (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS corner.events (
    id             BIGSERIAL PRIMARY KEY,
    at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor          UUID,
    request_id     BIGINT,
    collection_id  BIGINT,
    action         TEXT NOT NULL,
    detail         JSONB
);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['kinds', 'settings', 'requests', 'collections', 'collection_items', 'worker', 'events'] LOOP
    EXECUTE format('ALTER TABLE corner.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corner.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corner.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corner.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- 2. Helpers (the owner's only).
CREATE OR REPLACE FUNCTION corner._setting(p_key text)
RETURNS text LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT s.value FROM corner.settings s WHERE s.key = p_key
$$;

CREATE OR REPLACE FUNCTION corner._today()
RETURNS date LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT (now() AT TIME ZONE 'Asia/Kolkata')::date
$$;

-- What today's approved requests commit (India time): the desk's cost where it reported one, else
-- the estimate.
CREATE OR REPLACE FUNCTION corner._committed_today()
RETURNS numeric LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT coalesce(sum(coalesce(r.cost_usd, r.est_usd)), 0)
  FROM corner.requests r
  WHERE r.status IN ('approved', 'claimed', 'running', 'done', 'failed') AND r.decided_at IS NOT NULL
    AND (r.decided_at AT TIME ZONE 'Asia/Kolkata')::date = corner._today()
$$;

CREATE OR REPLACE FUNCTION corner._is_super()
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND coalesce(public.has_role(auth.uid(), 'super_admin'::public.app_role), false)
$$;

-- May this person ask the desk? A reader of the corpus who is a researcher or an editor.
CREATE OR REPLACE FUNCTION corner._can_request()
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND coalesce(public.corpus_reader_allowed(), false) AND (
    corpus._is_editor() OR coalesce(public.has_role(auth.uid(), 'researcher'::public.app_role), false))
$$;

CREATE OR REPLACE FUNCTION corner._gate()
RETURNS void LANGUAGE plpgsql STABLE SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();
  IF NOT corner._can_request() THEN
    RAISE EXCEPTION 'The Researchers'' Corner is open to invited researchers and editors.' USING ERRCODE = '42501';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION corner._editor_gate()
RETURNS void LANGUAGE plpgsql STABLE SET search_path = '' AS $$
BEGIN
  PERFORM corner._gate();
  IF NOT corpus._is_editor() THEN
    RAISE EXCEPTION 'Only an editor (an admin or the super admin) may do this.' USING ERRCODE = '42501';
  END IF;
END $$;

-- "18.2" -> {18, 2}, or NULL.
CREATE OR REPLACE FUNCTION corner._ref(p text)
RETURNS integer[] LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT CASE WHEN p ~ '^\s*[0-9]{1,6}\.[0-9]{1,6}\s*$'
              THEN ARRAY[split_part(btrim(p), '.', 1)::integer, split_part(btrim(p), '.', 2)::integer] END
$$;

CREATE OR REPLACE FUNCTION corner._passage_ok(p_doc text, p_ref integer[])
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT p_ref IS NOT NULL AND EXISTS (
    SELECT 1 FROM corpus.passages p
    WHERE p.doc_code = p_doc AND p.page_no = p_ref[1] AND p.idx = p_ref[2] AND p.retired_at IS NULL
      AND btrim(coalesce(p.translation, '')) <> ''
      AND coalesce(p.text_type, 'mula') NOT IN ('noise', 'frontmatter'))
$$;

-- "1-12", "1,3,5-7" -> the page numbers (1-16), or NULL if malformed.
CREATE OR REPLACE FUNCTION corner._pages(p text)
RETURNS integer[] LANGUAGE plpgsql IMMUTABLE SET search_path = '' AS $$
DECLARE part text; a integer; b integer; out integer[] := ARRAY[]::integer[];
BEGIN
  IF p IS NULL OR p !~ '^[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*$' THEN RETURN NULL; END IF;
  FOREACH part IN ARRAY string_to_array(p, ',') LOOP
    a := split_part(part, '-', 1)::integer;
    b := coalesce(nullif(split_part(part, '-', 2), '')::integer, a);
    IF a < 1 OR b > 16 OR b < a THEN RETURN NULL; END IF;
    FOR i IN a..b LOOP
      IF NOT i = ANY (out) THEN out := out || i; END IF;
    END LOOP;
  END LOOP;
  RETURN out;
END $$;

CREATE OR REPLACE FUNCTION corner._bad(p_msg text)
RETURNS void LANGUAGE plpgsql IMMUTABLE SET search_path = '' AS $$
BEGIN
  RAISE EXCEPTION '%', p_msg USING ERRCODE = '22023';
END $$;

CREATE OR REPLACE FUNCTION corner._text(p jsonb, p_key text, p_min integer, p_max integer, p_what text)
RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path = '' AS $$
DECLARE v text := btrim(coalesce(p ->> p_key, ''));
BEGIN
  IF length(v) < p_min OR length(v) > p_max THEN
    PERFORM corner._bad(format('%s: %s to %s characters', p_what, p_min, p_max));
  END IF;
  RETURN nullif(v, '');
END $$;

CREATE OR REPLACE FUNCTION corner._int(p jsonb, p_key text, p_min integer, p_max integer, p_what text)
RETURNS integer LANGUAGE plpgsql IMMUTABLE SET search_path = '' AS $$
DECLARE v text := btrim(coalesce(p ->> p_key, ''));
BEGIN
  IF v !~ '^[0-9]{1,9}$' OR v::bigint < p_min OR v::bigint > p_max THEN
    PERFORM corner._bad(format('%s: a whole number from %s to %s', p_what, p_min, p_max));
  END IF;
  RETURN v::integer;
END $$;

-- The request's parameters, checked against the mirror and normalised; raises 22023 with a reason.
CREATE OR REPLACE FUNCTION corner._clean(p_kind text, p_doc text, p jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE a integer[]; b integer[]; sid integer; iid integer; nid integer; st text; pg integer[]; npages integer;
BEGIN
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
    IF p_kind = 'novel_draw' THEN
      IF coalesce(p ->> 'pages', '') = '' THEN
        RETURN jsonb_build_object('novel_id', nid, 'pages', '');
      END IF;
      pg := corner._pages(p ->> 'pages');
      IF pg IS NULL THEN PERFORM corner._bad('pages: such as 1-12 or 1,3,5-7 (1 to 16)'); END IF;
      RETURN jsonb_build_object('novel_id', nid, 'pages', p ->> 'pages');
    ELSIF p_kind = 'novel_page_approve' THEN
      RETURN jsonb_build_object('novel_id', nid, 'page', corner._int(p, 'page', 1, 16, 'page'));
    ELSIF p_kind = 'novel_approve' THEN
      RETURN jsonb_build_object('novel_id', nid, 'force', coalesce(p ->> 'force', 'false') IN ('true', '1'));
    END IF;
    RETURN jsonb_build_object('novel_id', nid);
  END IF;
  PERFORM corner._bad('unknown kind');
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION corner._estimate(p_kind text, p_doc text, p jsonb)
RETURNS numeric LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE k corner.kinds; n integer;
BEGIN
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

CREATE OR REPLACE FUNCTION corner._log(p_action text, p_request bigint, p_collection bigint, p_detail jsonb)
RETURNS void LANGUAGE sql VOLATILE SET search_path = '' AS $$
  INSERT INTO corner.events (actor, request_id, collection_id, action, detail)
  VALUES (auth.uid(), p_request, p_collection, p_action, p_detail)
$$;

-- 3. What a reader may ask about the Corner.
CREATE OR REPLACE FUNCTION public.corner_me()
RETURNS TABLE (can_request boolean, is_editor boolean, is_super_admin boolean, daily_cap_usd numeric,
               committed_today numeric, researchers_need_approval boolean, worker_last_seen timestamptz,
               worker_info jsonb, pending bigint, queued bigint, running bigint, mine_open bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY
  SELECT corner._can_request(), corpus._is_editor(), corner._is_super(),
         coalesce(corner._setting('daily_cap_usd'), '0')::numeric, corner._committed_today(),
         coalesce(corner._setting('researchers_need_approval'), 'true') = 'true',
         (SELECT w.last_seen FROM corner.worker w WHERE w.id = 1),
         CASE WHEN corpus._is_editor() THEN (SELECT w.info FROM corner.worker w WHERE w.id = 1) END,
         (SELECT count(*) FROM corner.requests r WHERE r.status = 'pending'),
         (SELECT count(*) FROM corner.requests r WHERE r.status = 'approved'),
         (SELECT count(*) FROM corner.requests r WHERE r.status IN ('claimed', 'running')),
         (SELECT count(*) FROM corner.requests r WHERE r.requested_by = auth.uid()
            AND r.status IN ('pending', 'approved', 'claimed', 'running'));
END $$;

CREATE OR REPLACE FUNCTION public.corner_kinds()
RETURNS TABLE (kind text, label text, cost_bearing boolean, editor_only boolean, est_usd numeric, unit text,
               enabled boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();
  RETURN QUERY SELECT k.kind, k.label, k.cost_bearing, k.editor_only, k.est_usd, k.unit, k.enabled
               FROM corner.kinds k ORDER BY k.sort, k.kind;
END $$;

-- 4. Asking, deciding, cancelling.
CREATE OR REPLACE FUNCTION public.corner_request_create(p_kind text, p_doc text, p_params jsonb DEFAULT '{}'::jsonb,
                                                       p_note text DEFAULT NULL)
RETURNS TABLE (request_id bigint, request_status text, est_usd numeric, message text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  k corner.kinds; editor boolean; clean jsonb; est numeric; st text; cap numeric; used numeric;
  rid bigint; old_id bigint; old_st text; npend integer; maxp integer;
BEGIN
  PERFORM corner._gate();
  SELECT * INTO k FROM corner.kinds x WHERE x.kind = p_kind;
  IF NOT FOUND OR NOT k.enabled THEN PERFORM corner._bad('kind: not something the desk can be asked for'); END IF;
  editor := corpus._is_editor();
  IF k.editor_only AND NOT editor THEN
    RAISE EXCEPTION 'Only an editor (an admin or the super admin) may ask for this.' USING ERRCODE = '42501';
  END IF;
  IF p_note IS NOT NULL AND length(p_note) > 2000 THEN PERFORM corner._bad('note: at most 2000 characters'); END IF;
  clean := corner._clean(p_kind, p_doc, coalesce(p_params, '{}'::jsonb));
  est := corner._estimate(p_kind, p_doc, clean);

  SELECT r.id, r.status INTO old_id, old_st FROM corner.requests r
  WHERE r.kind = p_kind AND r.doc_code = p_doc AND r.params = clean
    AND r.status IN ('pending', 'approved', 'claimed', 'running')
  ORDER BY r.id LIMIT 1;
  IF FOUND THEN
    RETURN QUERY SELECT old_id, old_st, est, 'The same request is already open (#' || old_id || ').';
    RETURN;
  END IF;

  IF NOT editor THEN
    maxp := coalesce(corner._setting('max_pending_per_person'), '20')::integer;
    SELECT count(*) INTO npend FROM corner.requests r WHERE r.requested_by = auth.uid() AND r.status = 'pending';
    IF npend >= maxp THEN
      PERFORM corner._bad(format('You have %s requests waiting for an editor; wait for them first.', npend));
    END IF;
  END IF;

  IF editor OR NOT k.cost_bearing OR coalesce(corner._setting('researchers_need_approval'), 'true') <> 'true' THEN
    IF k.cost_bearing THEN
      cap := coalesce(corner._setting('daily_cap_usd'), '0')::numeric;
      used := corner._committed_today();
      IF used + est > cap THEN
        RAISE EXCEPTION 'Today''s cap for the Corner is $% and $% is already committed; this request is estimated at $%.',
          cap, round(used, 2), round(est, 2) USING ERRCODE = '22023';
      END IF;
    END IF;
    st := 'approved';
  ELSE
    st := 'pending';
  END IF;

  INSERT INTO corner.requests (kind, doc_code, params, note, requested_by, status, est_usd, decided_by, decided_at)
  VALUES (p_kind, p_doc, clean, nullif(btrim(coalesce(p_note, '')), ''), auth.uid(), st, est,
          CASE WHEN st = 'approved' THEN auth.uid() END, CASE WHEN st = 'approved' THEN now() END)
  RETURNING id INTO rid;
  PERFORM corner._log('request_' || st, rid, NULL, jsonb_build_object('kind', p_kind, 'doc', p_doc, 'est', est));
  RETURN QUERY SELECT rid, st, est,
    CASE WHEN st = 'pending' THEN 'Waiting for an editor''s approval.'
         ELSE 'Approved; the desk takes it on its next round.' END;
END $$;

CREATE OR REPLACE FUNCTION public.corner_requests(p_scope text DEFAULT 'mine', p_status text DEFAULT NULL,
                                                 k integer DEFAULT 50, p_offset integer DEFAULT 0)
RETURNS TABLE (id bigint, kind text, label text, doc_code text, doc_title text, params jsonb, note text,
               status text, est_usd numeric, cost_usd numeric, requested_at timestamptz, mine boolean,
               requester text, decided_at timestamptz, decision_note text, started_at timestamptz,
               finished_at timestamptz, message text, result jsonb, preview jsonb, total bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean;
BEGIN
  PERFORM corner._gate();
  editor := corpus._is_editor();
  IF p_scope NOT IN ('mine', 'queue', 'all') THEN PERFORM corner._bad('scope: mine, queue or all'); END IF;
  IF p_scope <> 'mine' AND NOT editor THEN
    RAISE EXCEPTION 'Only an editor may see everyone''s requests.' USING ERRCODE = '42501';
  END IF;
  RETURN QUERY
  WITH v AS (
    SELECT r.* FROM corner.requests r
    WHERE (p_scope <> 'mine' OR r.requested_by = auth.uid())
      AND (p_scope <> 'queue' OR r.status = 'pending')
      AND (p_status IS NULL OR r.status = p_status)
  )
  SELECT v.id, v.kind, kk.label, v.doc_code, coalesce(d.title, v.doc_code), v.params, v.note, v.status, v.est_usd,
         v.cost_usd, v.requested_at, v.requested_by = auth.uid(),
         CASE WHEN editor THEN (SELECT u.email::text FROM auth.users u WHERE u.id = v.requested_by) END,
         v.decided_at, v.decision_note, v.started_at, v.finished_at, v.message, v.result,
         (SELECT jsonb_build_object('story_id', s.story_id, 'status', s.status, 'title', s.title,
                   'title_hi', s.title_hi, 'story_en', left(s.story_en, 1500), 'verify', s.verify)
            FROM corpus.stories s
           WHERE v.result ? 'story_id' AND s.doc_code = v.doc_code AND s.retired_at IS NULL
             AND s.story_id = CASE WHEN (v.result ->> 'story_id') ~ '^[0-9]{1,9}$'
                                   THEN (v.result ->> 'story_id')::integer END),
         count(*) OVER ()
  FROM v
  JOIN corner.kinds kk ON kk.kind = v.kind
  LEFT JOIN corpus.docs d ON d.doc_code = v.doc_code
  ORDER BY v.requested_at DESC, v.id DESC
  LIMIT least(greatest(coalesce(k, 50), 1), 200) OFFSET greatest(coalesce(p_offset, 0), 0);
END $$;

CREATE OR REPLACE FUNCTION public.corner_request_decide(p_id bigint, p_approve boolean, p_note text DEFAULT NULL)
RETURNS TABLE (request_status text, message text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r corner.requests; cap numeric; used numeric;
BEGIN
  PERFORM corner._editor_gate();
  SELECT * INTO r FROM corner.requests x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND THEN PERFORM corner._bad('no such request'); END IF;
  IF r.status <> 'pending' THEN
    RETURN QUERY SELECT r.status, 'This request is ' || r.status || ', not waiting.'; RETURN;
  END IF;
  IF p_note IS NOT NULL AND length(p_note) > 2000 THEN PERFORM corner._bad('note: at most 2000 characters'); END IF;
  IF coalesce(p_approve, false) THEN
    cap := coalesce(corner._setting('daily_cap_usd'), '0')::numeric;
    used := corner._committed_today();
    IF used + r.est_usd > cap THEN
      RAISE EXCEPTION 'Today''s cap for the Corner is $% and $% is already committed; this request is estimated at $%.',
        cap, round(used, 2), round(r.est_usd, 2) USING ERRCODE = '22023';
    END IF;
  END IF;
  UPDATE corner.requests x SET status = CASE WHEN p_approve THEN 'approved' ELSE 'rejected' END,
         decided_by = auth.uid(), decided_at = now(), decision_note = nullif(btrim(coalesce(p_note, '')), '')
  WHERE x.id = p_id;
  PERFORM corner._log(CASE WHEN p_approve THEN 'approved' ELSE 'rejected' END, p_id, NULL, NULL);
  RETURN QUERY SELECT CASE WHEN p_approve THEN 'approved' ELSE 'rejected' END,
    CASE WHEN p_approve THEN 'Approved; the desk takes it on its next round.' ELSE 'Rejected.' END;
END $$;

CREATE OR REPLACE FUNCTION public.corner_request_cancel(p_id bigint)
RETURNS TABLE (request_status text, message text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r corner.requests;
BEGIN
  PERFORM corner._gate();
  SELECT * INTO r FROM corner.requests x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR (r.requested_by <> auth.uid() AND NOT corpus._is_editor()) THEN
    PERFORM corner._bad('no such request of yours');
  END IF;
  IF r.status NOT IN ('pending', 'approved') THEN
    RETURN QUERY SELECT r.status, 'The desk has already taken it; it cannot be withdrawn now.'; RETURN;
  END IF;
  UPDATE corner.requests x SET status = 'cancelled', finished_at = now() WHERE x.id = p_id;
  PERFORM corner._log('cancelled', p_id, NULL, NULL);
  RETURN QUERY SELECT 'cancelled'::text, 'Withdrawn.'::text;
END $$;

CREATE OR REPLACE FUNCTION public.corner_settings_set(p_key text, p_value text)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corner._gate();
  IF NOT corner._is_super() THEN
    RAISE EXCEPTION 'Only the super admin changes the Corner''s settings.' USING ERRCODE = '42501';
  END IF;
  IF p_key = 'daily_cap_usd' THEN
    IF p_value !~ '^[0-9]{1,2}(\.[0-9]{1,2})?$' OR p_value::numeric > 50 THEN
      PERFORM corner._bad('daily_cap_usd: 0 to 50 dollars');
    END IF;
  ELSIF p_key = 'researchers_need_approval' THEN
    IF p_value NOT IN ('true', 'false') THEN PERFORM corner._bad('researchers_need_approval: true or false'); END IF;
  ELSIF p_key = 'max_pending_per_person' THEN
    IF p_value !~ '^[0-9]{1,3}$' OR p_value::integer < 1 OR p_value::integer > 200 THEN
      PERFORM corner._bad('max_pending_per_person: 1 to 200');
    END IF;
  ELSE
    PERFORM corner._bad('no such setting');
  END IF;
  UPDATE corner.settings s SET value = p_value, updated_at = now(), updated_by = auth.uid() WHERE s.key = p_key;
  PERFORM corner._log('setting', NULL, NULL, jsonb_build_object('key', p_key, 'value', p_value));
  RETURN p_value;
END $$;

-- 5. Anthologies.
CREATE OR REPLACE FUNCTION public.corner_collection_save(p_id bigint, p_title text, p_title_hi text, p_intro text,
                                                        p_audience text, p_items jsonb)
RETURNS TABLE (collection_id bigint, collection_status text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE c corner.collections; editor boolean; cid bigint; it jsonb; n integer := 0; sst text; seen text[] := ARRAY[]::text[];
        ikey text;
BEGIN
  PERFORM corner._gate();
  editor := corpus._is_editor();
  IF p_title IS NULL OR length(btrim(p_title)) < 1 OR length(p_title) > 300 THEN PERFORM corner._bad('title: 1 to 300 characters'); END IF;
  IF p_title_hi IS NOT NULL AND length(p_title_hi) > 300 THEN PERFORM corner._bad('title_hi: at most 300 characters'); END IF;
  IF p_intro IS NOT NULL AND length(p_intro) > 8000 THEN PERFORM corner._bad('intro: at most 8000 characters'); END IF;
  IF coalesce(p_audience, 'general') NOT IN ('general', 'young', 'scholar') THEN PERFORM corner._bad('audience: general, young or scholar'); END IF;
  IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items) > 200 THEN
    PERFORM corner._bad('items: a list of at most 200 stories');
  END IF;

  IF p_id IS NULL THEN
    INSERT INTO corner.collections (title, title_hi, intro, audience, created_by)
    VALUES (btrim(p_title), nullif(btrim(coalesce(p_title_hi, '')), ''), nullif(btrim(coalesce(p_intro, '')), ''),
            coalesce(p_audience, 'general'), auth.uid())
    RETURNING * INTO c;
  ELSE
    SELECT * INTO c FROM corner.collections x WHERE x.id = p_id FOR UPDATE;
    IF NOT FOUND OR c.status = 'retired' OR (c.created_by <> auth.uid() AND NOT editor) THEN
      PERFORM corner._bad('no such anthology of yours');
    END IF;
    IF c.status = 'published' AND NOT editor THEN
      PERFORM corner._bad('a published anthology is changed by an editor');
    END IF;
    UPDATE corner.collections x SET title = btrim(p_title), title_hi = nullif(btrim(coalesce(p_title_hi, '')), ''),
           intro = nullif(btrim(coalesce(p_intro, '')), ''), audience = coalesce(p_audience, 'general'), updated_at = now()
    WHERE x.id = p_id RETURNING * INTO c;
  END IF;
  cid := c.id;

  DELETE FROM corner.collection_items i WHERE i.collection_id = cid;
  FOR it IN SELECT value FROM jsonb_array_elements(p_items) LOOP
    IF jsonb_typeof(it) <> 'object' OR coalesce(it ->> 'doc_code', '') = '' OR coalesce(it ->> 'story_id', '') !~ '^[0-9]{1,9}$' THEN
      PERFORM corner._bad('items: each one {doc_code, story_id}');
    END IF;
    ikey := (it ->> 'doc_code') || ':' || (it ->> 'story_id');
    CONTINUE WHEN ikey = ANY (seen);
    seen := seen || ikey;
    SELECT s.status INTO sst FROM corpus.stories s
    WHERE s.doc_code = it ->> 'doc_code' AND s.story_id = (it ->> 'story_id')::integer AND s.retired_at IS NULL;
    IF NOT FOUND OR sst IN ('retired', 'rejected') OR (sst <> 'approved' AND NOT editor) THEN
      PERFORM corner._bad('items: ' || ikey || ' is not an approved story');
    END IF;
    IF c.status = 'published' AND sst <> 'approved' THEN
      PERFORM corner._bad('items: a published anthology holds approved stories only (' || ikey || ')');
    END IF;
    n := n + 1;
    INSERT INTO corner.collection_items (collection_id, pos, doc_code, story_id)
    VALUES (cid, n, it ->> 'doc_code', (it ->> 'story_id')::integer);
  END LOOP;
  PERFORM corner._log(CASE WHEN p_id IS NULL THEN 'collection_created' ELSE 'collection_saved' END, NULL, cid,
                      jsonb_build_object('items', n));
  RETURN QUERY SELECT cid, c.status;
END $$;

-- The picture of a story (its own approved picture, or a draft for an editor).
CREATE OR REPLACE FUNCTION corner._story_picture(p_doc text, p_story integer, p_editor boolean)
RETURNS jsonb LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('media_key', m.media_key, 'sha256', m.sha256, 'width', m.width, 'height', m.height,
           'status', m.status, 'caption_en', m.caption_en, 'caption_hi', m.caption_hi, 'model', m.model,
           'has_thumb', EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'thumb'),
           'has_display', EXISTS (SELECT 1 FROM corpus.media_files f WHERE f.sha256 = m.sha256 AND f.rendition = 'display'))
  FROM corpus.media m
  WHERE m.doc_code = p_doc AND m.story_id = p_story AND m.novel_id IS NULL AND m.retired_at IS NULL
    AND (m.status = 'approved' OR p_editor)
  ORDER BY (m.status = 'approved') DESC, m.media_key
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION public.corner_collections(p_scope text DEFAULT 'all')
RETURNS TABLE (id bigint, title text, title_hi text, audience text, status text, items bigint, mine boolean,
               owner text, created_at timestamptz, updated_at timestamptz, published_at timestamptz,
               cover_sha text, cover_has_thumb boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean; can boolean;
BEGIN
  PERFORM corpus._reader_gate();
  editor := corpus._is_editor();
  can := corner._can_request();
  IF p_scope NOT IN ('mine', 'published', 'all') THEN PERFORM corner._bad('scope: mine, published or all'); END IF;
  RETURN QUERY
  SELECT c.id, c.title, c.title_hi, c.audience, c.status,
         (SELECT count(*) FROM corner.collection_items i WHERE i.collection_id = c.id),
         c.created_by = auth.uid(),
         CASE WHEN editor THEN (SELECT u.email::text FROM auth.users u WHERE u.id = c.created_by) END,
         c.created_at, c.updated_at, c.published_at, p.pic ->> 'sha256', coalesce((p.pic ->> 'has_thumb')::boolean, false)
  FROM corner.collections c
  LEFT JOIN LATERAL (
    SELECT corner._story_picture(i.doc_code, i.story_id, editor) AS pic
    FROM corner.collection_items i
    WHERE i.collection_id = c.id AND corner._story_picture(i.doc_code, i.story_id, editor) IS NOT NULL
    ORDER BY i.pos LIMIT 1) p ON true
  WHERE c.status <> 'retired'
    AND (c.status = 'published' OR (can AND (c.created_by = auth.uid() OR editor)))
    AND (p_scope <> 'mine' OR c.created_by = auth.uid())
    AND (p_scope <> 'published' OR c.status = 'published')
  ORDER BY (c.status = 'published') DESC, coalesce(c.published_at, c.updated_at) DESC, c.id DESC;
END $$;

CREATE OR REPLACE FUNCTION public.corner_collection(p_id bigint)
RETURNS TABLE (id bigint, title text, title_hi text, intro text, audience text, status text, mine boolean,
               can_edit boolean, created_at timestamptz, updated_at timestamptz, published_at timestamptz, items jsonb)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE editor boolean; can boolean;
BEGIN
  PERFORM corpus._reader_gate();
  editor := corpus._is_editor();
  can := corner._can_request();
  RETURN QUERY
  SELECT c.id, c.title, c.title_hi, c.intro, c.audience, c.status, c.created_by = auth.uid(),
         can AND ((c.status = 'draft' AND c.created_by = auth.uid()) OR editor),
         c.created_at, c.updated_at, c.published_at,
         (SELECT coalesce(jsonb_agg(jsonb_build_object(
                    'pos', i.pos, 'doc_code', i.doc_code, 'doc_title', coalesce(d.title, i.doc_code),
                    'story_id', i.story_id, 'status', s.status, 'title', s.title, 'title_hi', s.title_hi,
                    'story_en', s.story_en, 'story_hi', s.story_hi, 'quote_sa', s.quote_sa, 'quote_ref', s.quote_ref,
                    'cites', s.cites, 'from_page', s.from_page, 'from_idx', s.from_idx, 'to_page', s.to_page,
                    'to_idx', s.to_idx, 'model', s.model,
                    'picture', corner._story_picture(i.doc_code, i.story_id, editor))
                  ORDER BY i.pos), '[]'::jsonb)
            FROM corner.collection_items i
            JOIN corpus.stories s ON s.doc_code = i.doc_code AND s.story_id = i.story_id AND s.retired_at IS NULL
            LEFT JOIN corpus.docs d ON d.doc_code = i.doc_code
           WHERE i.collection_id = c.id AND (s.status = 'approved' OR editor
                 OR (c.status = 'draft' AND c.created_by = auth.uid() AND s.status = 'approved')))
  FROM corner.collections c
  WHERE c.id = p_id AND c.status <> 'retired'
    AND (c.status = 'published' OR (can AND (c.created_by = auth.uid() OR editor)));
END $$;

CREATE OR REPLACE FUNCTION public.corner_collection_publish(p_id bigint, p_publish boolean)
RETURNS TABLE (collection_status text, message text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE c corner.collections; n integer; bad integer;
BEGIN
  PERFORM corner._editor_gate();
  SELECT * INTO c FROM corner.collections x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR c.status = 'retired' THEN PERFORM corner._bad('no such anthology'); END IF;
  IF coalesce(p_publish, false) THEN
    SELECT count(*), count(*) FILTER (WHERE s.status IS DISTINCT FROM 'approved' OR s.retired_at IS NOT NULL)
      INTO n, bad
    FROM corner.collection_items i
    LEFT JOIN corpus.stories s ON s.doc_code = i.doc_code AND s.story_id = i.story_id
    WHERE i.collection_id = p_id;
    IF n = 0 THEN PERFORM corner._bad('an anthology needs at least one story'); END IF;
    IF bad > 0 THEN PERFORM corner._bad(format('%s of its %s stories are not approved', bad, n)); END IF;
    UPDATE corner.collections x SET status = 'published', published_by = auth.uid(), published_at = now(), updated_at = now()
    WHERE x.id = p_id;
  ELSE
    UPDATE corner.collections x SET status = 'draft', updated_at = now() WHERE x.id = p_id;
  END IF;
  PERFORM corner._log(CASE WHEN p_publish THEN 'published' ELSE 'unpublished' END, NULL, p_id, NULL);
  RETURN QUERY SELECT CASE WHEN p_publish THEN 'published' ELSE 'draft' END,
    CASE WHEN p_publish THEN 'Published to the readers of the working corpus.' ELSE 'Back to draft.' END;
END $$;

CREATE OR REPLACE FUNCTION public.corner_collection_retire(p_id bigint)
RETURNS TABLE (collection_status text, message text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE c corner.collections;
BEGIN
  PERFORM corner._gate();
  SELECT * INTO c FROM corner.collections x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR c.status = 'retired' OR ((c.created_by <> auth.uid() OR c.status = 'published') AND NOT corpus._is_editor()) THEN
    PERFORM corner._bad('no such anthology of yours (a published one is retired by an editor)');
  END IF;
  UPDATE corner.collections x SET status = 'retired', updated_at = now() WHERE x.id = p_id;
  PERFORM corner._log('collection_retired', NULL, p_id, NULL);
  RETURN QUERY SELECT 'retired'::text, 'Retired.'::text;
END $$;

-- 6. The desk's side (service_role, through the corpus-desk edge function).
CREATE OR REPLACE FUNCTION public.corner_desk_pull(p_limit integer, p_worker text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE out jsonb;
BEGIN
  -- A request the desk took and never finished (the PC slept, the run was killed) goes back once
  -- three hours have passed; after three attempts it is failed.
  UPDATE corner.requests r
     SET status = CASE WHEN r.attempts >= 3 THEN 'failed' ELSE 'approved' END,
         message = CASE WHEN r.attempts >= 3 THEN 'The desk did not finish it in three attempts.'
                        ELSE 'Taken again: the desk did not finish it the last time.' END,
         finished_at = CASE WHEN r.attempts >= 3 THEN now() END, claimed_at = NULL, worker = NULL
   WHERE r.status IN ('claimed', 'running') AND r.claimed_at < now() - interval '3 hours';
  WITH c AS (
    SELECT r.id FROM corner.requests r WHERE r.status = 'approved'
    ORDER BY r.decided_at, r.id LIMIT least(greatest(coalesce(p_limit, 1), 1), 20) FOR UPDATE SKIP LOCKED
  ), u AS (
    UPDATE corner.requests r SET status = 'claimed', claimed_at = now(), worker = left(coalesce(p_worker, 'desk'), 100),
           attempts = r.attempts + 1
    FROM c WHERE r.id = c.id
    RETURNING r.id, r.kind, r.doc_code, r.params, r.est_usd, r.attempts, r.requested_at, r.decided_at
  )
  SELECT coalesce(jsonb_agg(jsonb_build_object('id', u.id, 'kind', u.kind, 'doc_code', u.doc_code, 'params', u.params,
           'est_usd', u.est_usd, 'attempts', u.attempts, 'requested_at', u.requested_at) ORDER BY u.decided_at, u.id),
         '[]'::jsonb)
    INTO out FROM u;
  UPDATE corner.worker w SET last_seen = now() WHERE w.id = 1;
  RETURN out;
END $$;

CREATE OR REPLACE FUNCTION public.corner_desk_report(p_id bigint, p_status text, p_result jsonb, p_message text,
                                                    p_cost numeric, p_log text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r corner.requests;
BEGIN
  IF p_status NOT IN ('running', 'done', 'failed') THEN
    RAISE EXCEPTION 'p_status: running, done or failed' USING ERRCODE = '22023';
  END IF;
  SELECT * INTO r FROM corner.requests x WHERE x.id = p_id FOR UPDATE;
  IF NOT FOUND OR r.status NOT IN ('claimed', 'running') THEN
    RETURN false;
  END IF;
  UPDATE corner.requests x SET
      status = p_status,
      started_at = CASE WHEN p_status = 'running' THEN now() ELSE coalesce(x.started_at, now()) END,
      finished_at = CASE WHEN p_status IN ('done', 'failed') THEN now() END,
      result = CASE WHEN p_result IS NOT NULL AND jsonb_typeof(p_result) = 'object' AND length(p_result::text) <= 20000
                    THEN p_result ELSE x.result END,
      message = coalesce(left(p_message, 2000), x.message),
      cost_usd = CASE WHEN p_cost IS NOT NULL AND p_cost >= 0 AND p_cost < 100 THEN p_cost ELSE x.cost_usd END,
      log_tail = coalesce(left(p_log, 8000), x.log_tail)
  WHERE x.id = p_id;
  INSERT INTO corner.events (request_id, action, detail)
  VALUES (p_id, 'desk_' || p_status, jsonb_build_object('cost', p_cost, 'message', left(p_message, 300)));
  UPDATE corner.worker w SET last_seen = now() WHERE w.id = 1;
  RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.corner_desk_heartbeat(p_info jsonb)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  UPDATE corner.worker w SET last_seen = now(),
         info = CASE WHEN p_info IS NOT NULL AND jsonb_typeof(p_info) = 'object' AND length(p_info::text) <= 4000
                     THEN p_info ELSE w.info END
  WHERE w.id = 1;
  RETURN jsonb_build_object('scheme', 'corner.1',
    'daily_cap_usd', coalesce(corner._setting('daily_cap_usd'), '0')::numeric,
    'committed_today', corner._committed_today(),
    'queued', (SELECT count(*) FROM corner.requests r WHERE r.status = 'approved'));
END $$;

CREATE OR REPLACE FUNCTION public.corner_desk_state()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT jsonb_build_object('scheme', 'corner.1',
    'queued', (SELECT count(*) FROM corner.requests r WHERE r.status = 'approved'),
    'running', (SELECT count(*) FROM corner.requests r WHERE r.status IN ('claimed', 'running')),
    'pending', (SELECT count(*) FROM corner.requests r WHERE r.status = 'pending'),
    'last_seen', (SELECT w.last_seen FROM corner.worker w WHERE w.id = 1))
$$;

-- 7. Who may call what.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'corner._setting(text)', 'corner._today()', 'corner._committed_today()', 'corner._is_super()',
      'corner._can_request()', 'corner._gate()', 'corner._editor_gate()', 'corner._ref(text)',
      'corner._passage_ok(text, integer[])', 'corner._pages(text)', 'corner._bad(text)',
      'corner._text(jsonb, text, integer, integer, text)', 'corner._int(jsonb, text, integer, integer, text)',
      'corner._clean(text, text, jsonb)', 'corner._estimate(text, text, jsonb)',
      'corner._log(text, bigint, bigint, jsonb)', 'corner._story_picture(text, integer, boolean)',
      'public.corner_me()', 'public.corner_kinds()', 'public.corner_request_create(text, text, jsonb, text)',
      'public.corner_requests(text, text, integer, integer)', 'public.corner_request_decide(bigint, boolean, text)',
      'public.corner_request_cancel(bigint)', 'public.corner_settings_set(text, text)',
      'public.corner_collection_save(bigint, text, text, text, text, jsonb)', 'public.corner_collections(text)',
      'public.corner_collection(bigint)', 'public.corner_collection_publish(bigint, boolean)',
      'public.corner_collection_retire(bigint)', 'public.corner_desk_pull(integer, text)',
      'public.corner_desk_report(bigint, text, jsonb, text, numeric, text)', 'public.corner_desk_heartbeat(jsonb)',
      'public.corner_desk_state()'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.corner_me(), public.corner_kinds(),
      public.corner_request_create(text, text, jsonb, text), public.corner_requests(text, text, integer, integer),
      public.corner_request_decide(bigint, boolean, text), public.corner_request_cancel(bigint),
      public.corner_settings_set(text, text), public.corner_collection_save(bigint, text, text, text, text, jsonb),
      public.corner_collections(text), public.corner_collection(bigint),
      public.corner_collection_publish(bigint, boolean), public.corner_collection_retire(bigint) TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.corner_desk_pull(integer, text),
      public.corner_desk_report(bigint, text, jsonb, text, numeric, text), public.corner_desk_heartbeat(jsonb),
      public.corner_desk_state() TO service_role;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
