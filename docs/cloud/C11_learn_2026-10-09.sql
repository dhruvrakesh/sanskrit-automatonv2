-- ============================================================
-- C11 - Learn: training and gamification (LEARN_T1_2026_10_09)
-- Paste this whole file once in the Lovable Cloud SQL editor (one transaction). Read-only checks:
-- docs/cloud/C11_checks_2026-10-09.sql, one query per paste (P1-P2 before, V1-V3 after).
--
-- What it adds, all in a new closed schema learn (no table is granted to anyone):
--   learn.quests  the quest catalogue: key, track (find, read, ask, make, edit), XP, mode and
--                 whether only editors have it. The site holds the words (title, why, steps, the
--                 link to the tool); the database holds the rules. 23 quests, 400 XP in all
--                 (20 quests and 340 XP for a researcher, who does not have the edit track).
--   learn.marks   the self quests a person says they have done ("I did this"): who, which, when.
--                 Honour system; the first time is kept.
-- Auto quests (the ask, make and edit tracks, except printing an anthology) are never stored and
-- can never be marked by hand: each is checked live from the Researchers' Corner (C9) -
-- corner.requests, corner.collections, corner.collection_items (and corner.events for when an
-- anthology first held three stories) - and is done from the earliest row that qualifies.
-- Levels by XP: Reader 0, Explorer 50, Storyteller 120, Curator 200, Keeper 280. A badge for each
-- track when every quest of the track that the person has is done.
--
-- The site's functions (SECURITY DEFINER, to signed-in users only; anon and PUBLIC have none):
--   learn_me()           the caller's quests: done or not, and when
--   learn_summary()      the caller's XP, level, next level, badges, quests done of the total
--   learn_mark(p_quest)  "I did this" for one of the caller's self quests (idempotent)
--   learn_team()         editors only: every member's progress and last activity
-- Who may do what:
--   - a reader of the working corpus (C5/C7 gate) who is a researcher, an admin or the super
--     admin (corner._can_request(), C9) sees and marks their own progress; any other reader is
--     refused (42501);
--   - the edit track is shown to editors (admins and the super admin) only;
--   - only editors see learn_team(): members are the users with the role researcher, admin or
--     super_admin in public.user_roles. There is no public leaderboard.
-- Nothing here spends anything or changes the Corner: the ask track's quests are done by asking
-- the desk in the Corner as usual (a researcher's paid request still waits for an editor and
-- counts against the day's cap).
--
-- Needs C9 (and so C4, C5, C7a, C7, C8). Purely additive: nothing that exists is changed.
-- Re-running it changes no person's progress; it refreshes the catalogue (track, XP, mode,
-- editors_only, order) and the functions.
-- Rollback:
--   DROP FUNCTION IF EXISTS public.learn_me(), public.learn_summary(), public.learn_mark(text),
--     public.learn_team();
--   DROP SCHEMA IF EXISTS learn CASCADE;
--
-- Tested 2026-10-09 on PostgreSQL 16 with the Supabase stand-ins (tests/test_learn_pg_2026_10_09.py).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corner.requests') IS NULL OR to_regclass('corner.collections') IS NULL
     OR to_regclass('corner.collection_items') IS NULL OR to_regclass('corner.events') IS NULL
     OR to_regprocedure('corner._can_request()') IS NULL THEN
    RAISE EXCEPTION 'C11: needs C9 (the Researchers'' Corner: corner.requests and corner._can_request are missing).';
  END IF;
  IF to_regprocedure('corpus._is_editor()') IS NULL OR to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C11: needs C5 and C8 (corpus._reader_gate and corpus._is_editor are missing).';
  END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS learn;
REVOKE ALL ON SCHEMA learn FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE 'REVOKE ALL ON SCHEMA learn FROM anon'; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON SCHEMA learn FROM authenticated'; END IF;
END $$;

-- 1. Tables.
CREATE TABLE IF NOT EXISTS learn.quests (
    key           TEXT PRIMARY KEY CHECK (key ~ '^[a-z_]{3,40}$'),
    track         TEXT NOT NULL CHECK (track ~ '^[a-z_]{2,20}$'),
    xp            INTEGER NOT NULL CHECK (xp >= 0 AND xp <= 1000),
    mode          TEXT NOT NULL CHECK (mode IN ('self', 'auto')),
    editors_only  BOOLEAN NOT NULL DEFAULT false,
    sort          INTEGER NOT NULL DEFAULT 1000
);
-- How each auto quest is checked is in learn._auto_done below.
INSERT INTO learn.quests (key, track, xp, mode, editors_only, sort) VALUES
  ('find_library',   'find', 10, 'self', false, 110),
  ('find_passage',   'find', 10, 'self', false, 120),
  ('find_views',     'find', 10, 'self', false, 130),
  ('find_search',    'find', 10, 'self', false, 140),
  ('find_meaning',   'find', 10, 'self', false, 150),
  ('find_names',     'find', 10, 'self', false, 160),
  ('read_story',     'read', 10, 'self', false, 210),
  ('read_picture',   'read', 10, 'self', false, 220),
  ('read_novel',     'read', 10, 'self', false, 230),
  ('read_texts',     'read', 10, 'self', false, 240),
  ('ask_any',        'ask',  20, 'auto', false, 310),
  ('ask_story',      'ask',  20, 'auto', false, 320),
  ('ask_done',       'ask',  20, 'auto', false, 330),
  ('ask_write',      'ask',  20, 'auto', false, 340),
  ('ask_picture',    'ask',  20, 'auto', false, 350),
  ('ask_novel',      'ask',  20, 'auto', false, 360),
  ('make_anthology', 'make', 30, 'auto', false, 410),
  ('make_three',     'make', 30, 'auto', false, 420),
  ('make_published', 'make', 50, 'auto', false, 430),
  ('make_print',     'make', 10, 'self', false, 440),
  ('edit_decide',    'edit', 20, 'auto', true,  510),
  ('edit_approve',   'edit', 20, 'auto', true,  520),
  ('edit_publish',   'edit', 20, 'auto', true,  530)
ON CONFLICT (key) DO UPDATE SET track = EXCLUDED.track, xp = EXCLUDED.xp, mode = EXCLUDED.mode,
  editors_only = EXCLUDED.editors_only, sort = EXCLUDED.sort;

CREATE TABLE IF NOT EXISTS learn.marks (
    user_id  UUID NOT NULL,
    quest    TEXT NOT NULL REFERENCES learn.quests(key),
    done_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, quest)
);
CREATE INDEX IF NOT EXISTS learn_marks_quest ON learn.marks (quest);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['quests', 'marks'] LOOP
    EXECUTE format('ALTER TABLE learn.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON learn.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON learn.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON learn.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- 2. Helpers (the owner's only).
-- Learn is for those who may ask the desk: a reader of the corpus who is a researcher or an editor.
CREATE OR REPLACE FUNCTION learn._gate()
RETURNS void LANGUAGE plpgsql STABLE SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();
  IF NOT corner._can_request() THEN
    RAISE EXCEPTION 'Learn is open to invited researchers and editors.' USING ERRCODE = '42501';
  END IF;
END $$;

-- The levels, by the XP they start at.
CREATE OR REPLACE FUNCTION learn._levels()
RETURNS TABLE (level_index integer, level text, min_xp integer)
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT v.i, v.name, v.xp
  FROM (VALUES (0, 'Reader', 0), (1, 'Explorer', 50), (2, 'Storyteller', 120), (3, 'Curator', 200),
               (4, 'Keeper', 280)) AS v (i, name, xp)
$$;

-- When an auto quest was first done by this person, from the Corner's own rows; NULL if not yet.
-- Every timestamp is coalesced to one that is never NULL, so a qualifying row always counts.
CREATE OR REPLACE FUNCTION learn._auto_done(p_key text, p_user uuid)
RETURNS timestamptz LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT CASE p_key
    -- any request you made, whatever became of it
    WHEN 'ask_any' THEN (SELECT min(r.requested_at) FROM corner.requests r WHERE r.requested_by = p_user)
    WHEN 'ask_story' THEN (SELECT min(r.requested_at) FROM corner.requests r
                           WHERE r.requested_by = p_user AND r.kind = 'story_range')
    -- one of your requests that the desk finished
    WHEN 'ask_done' THEN (SELECT min(coalesce(r.finished_at, r.started_at, r.decided_at, r.requested_at))
                          FROM corner.requests r WHERE r.requested_by = p_user AND r.status = 'done')
    WHEN 'ask_write' THEN (SELECT min(r.requested_at) FROM corner.requests r
                           WHERE r.requested_by = p_user AND r.kind = 'story_write')
    WHEN 'ask_picture' THEN (SELECT min(r.requested_at) FROM corner.requests r
                             WHERE r.requested_by = p_user AND r.kind IN ('picture_passage', 'story_illustrate'))
    WHEN 'ask_novel' THEN (SELECT min(r.requested_at) FROM corner.requests r
                           WHERE r.requested_by = p_user AND r.kind = 'novel_plan')
    -- an anthology you made (a draft counts)
    WHEN 'make_anthology' THEN (SELECT min(c.created_at) FROM corner.collections c WHERE c.created_by = p_user)
    -- one of your anthologies holds three stories or more now; done when it was first saved so
    -- (corner.events), else when it was last saved
    WHEN 'make_three' THEN (
      SELECT min(coalesce(
               (SELECT min(e.at) FROM corner.events e
                 WHERE e.collection_id = c.id AND e.action IN ('collection_created', 'collection_saved')
                   AND coalesce(e.detail ->> 'items', '') ~ '^[0-9]{1,6}$' AND (e.detail ->> 'items')::integer >= 3),
               c.updated_at, c.created_at))
      FROM corner.collections c
      WHERE c.created_by = p_user
        AND (SELECT count(*) FROM corner.collection_items i WHERE i.collection_id = c.id) >= 3)
    -- one of your anthologies was published by an editor (published_at is kept when it is
    -- unpublished or retired later)
    WHEN 'make_published' THEN (SELECT min(coalesce(c.published_at, c.updated_at)) FROM corner.collections c
                                WHERE c.created_by = p_user AND (c.published_at IS NOT NULL OR c.status = 'published'))
    -- editors: you approved or rejected a request someone else made (decided_by is set only by a
    -- decision, or to the asker on a request approved at once, which is not someone else's)
    WHEN 'edit_decide' THEN (SELECT min(coalesce(r.decided_at, r.requested_at)) FROM corner.requests r
                             WHERE r.decided_by = p_user AND r.requested_by <> p_user)
    -- editors: you asked the desk to approve a story
    WHEN 'edit_approve' THEN (SELECT min(r.requested_at) FROM corner.requests r
                              WHERE r.requested_by = p_user AND r.kind = 'story_approve')
    -- editors: you published an anthology
    WHEN 'edit_publish' THEN (SELECT min(coalesce(c.published_at, c.updated_at)) FROM corner.collections c
                              WHERE c.published_by = p_user)
  END
$$;

-- One person's quests: those they have (the edit track for editors only), and when each was done.
CREATE OR REPLACE FUNCTION learn._progress(p_user uuid, p_editor boolean)
RETURNS TABLE (quest text, track text, xp integer, mode text, editors_only boolean, sort integer, done_at timestamptz)
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT q.key, q.track, q.xp, q.mode, q.editors_only, q.sort,
         CASE WHEN q.mode = 'self'
              THEN (SELECT m.done_at FROM learn.marks m WHERE m.user_id = p_user AND m.quest = q.key)
              ELSE learn._auto_done(q.key, p_user) END
  FROM learn.quests q
  WHERE p_user IS NOT NULL AND (NOT q.editors_only OR coalesce(p_editor, false))
$$;

-- One person's XP, level, next level, badges (the tracks they have finished, in track order) and
-- quests done of those they have.
CREATE OR REPLACE FUNCTION learn._summary(p_user uuid, p_editor boolean)
RETURNS TABLE (xp integer, level text, level_index integer, next_level text, next_level_xp integer,
               badges text[], quests_done integer, quests_total integer)
LANGUAGE sql STABLE SET search_path = '' AS $$
  WITH p AS (
    SELECT * FROM learn._progress(p_user, p_editor)
  ), t AS (
    SELECT coalesce(sum(p.xp) FILTER (WHERE p.done_at IS NOT NULL), 0)::integer AS xp,
           (count(*) FILTER (WHERE p.done_at IS NOT NULL))::integer AS done,
           count(*)::integer AS total
    FROM p
  ), b AS (
    SELECT p.track, min(p.sort) AS s FROM p GROUP BY p.track HAVING bool_and(p.done_at IS NOT NULL)
  ), cur AS (
    SELECT l.level_index, l.level FROM learn._levels() l, t WHERE l.min_xp <= t.xp
    ORDER BY l.min_xp DESC LIMIT 1
  ), nxt AS (
    SELECT l.level, l.min_xp FROM learn._levels() l, t WHERE l.min_xp > t.xp
    ORDER BY l.min_xp LIMIT 1
  )
  SELECT t.xp, (SELECT cur.level FROM cur), (SELECT cur.level_index FROM cur),
         (SELECT nxt.level FROM nxt), (SELECT nxt.min_xp FROM nxt),
         coalesce((SELECT array_agg(b.track ORDER BY b.s) FROM b), ARRAY[]::text[]),
         t.done, t.total
  FROM t
$$;

-- The latest of a person's marks, requests asked or decided, and anthologies made or published.
CREATE OR REPLACE FUNCTION learn._last_activity(p_user uuid)
RETURNS timestamptz LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT greatest(
    (SELECT max(m.done_at) FROM learn.marks m WHERE m.user_id = p_user),
    (SELECT max(r.requested_at) FROM corner.requests r WHERE r.requested_by = p_user),
    (SELECT max(r.decided_at) FROM corner.requests r WHERE r.decided_by = p_user),
    (SELECT max(greatest(c.created_at, c.updated_at)) FROM corner.collections c WHERE c.created_by = p_user),
    (SELECT max(c.published_at) FROM corner.collections c WHERE c.published_by = p_user))
$$;

-- 3. The site's functions.
CREATE OR REPLACE FUNCTION public.learn_me()
RETURNS TABLE (quest text, track text, xp integer, mode text, editors_only boolean, done boolean, done_at timestamptz)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM learn._gate();
  RETURN QUERY
  SELECT p.quest, p.track, p.xp, p.mode, p.editors_only, p.done_at IS NOT NULL, p.done_at
  FROM learn._progress(auth.uid(), corpus._is_editor()) p
  ORDER BY p.sort, p.quest;
END $$;

CREATE OR REPLACE FUNCTION public.learn_summary()
RETURNS TABLE (xp integer, level text, level_index integer, next_level text, next_level_xp integer,
               badges text[], quests_done integer, quests_total integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM learn._gate();
  RETURN QUERY
  SELECT s.xp, s.level, s.level_index, s.next_level, s.next_level_xp, s.badges, s.quests_done, s.quests_total
  FROM learn._summary(auth.uid(), corpus._is_editor()) s;
END $$;

-- "I did this": true when this call marked it, false when it was marked already (the first time
-- is kept). Only a self quest the caller has; an auto quest is checked, never marked.
CREATE OR REPLACE FUNCTION public.learn_mark(p_quest text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = '' AS $$
DECLARE q learn.quests; n integer;
BEGIN
  PERFORM learn._gate();
  SELECT * INTO q FROM learn.quests x WHERE x.key = btrim(coalesce(p_quest, ''));
  IF NOT FOUND OR (q.editors_only AND NOT corpus._is_editor()) THEN
    RAISE EXCEPTION 'No such quest: %.', left(coalesce(nullif(btrim(p_quest), ''), '(none named)'), 60)
      USING ERRCODE = '22023';
  END IF;
  IF q.mode <> 'self' THEN
    RAISE EXCEPTION 'The quest % is checked for you from the Researchers'' Corner; it cannot be marked by hand.', q.key
      USING ERRCODE = '22023';
  END IF;
  INSERT INTO learn.marks (user_id, quest) VALUES (auth.uid(), q.key) ON CONFLICT (user_id, quest) DO NOTHING;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n > 0;
END $$;

-- Editors only: every member (a researcher, an admin or the super admin) with their progress.
CREATE OR REPLACE FUNCTION public.learn_team()
RETURNS TABLE (user_id uuid, email text, roles text[], xp integer, level text, quests_done integer,
               last_activity timestamptz)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM learn._gate();
  IF NOT corpus._is_editor() THEN
    RAISE EXCEPTION 'Only an editor (an admin or the super admin) may see the team''s progress.' USING ERRCODE = '42501';
  END IF;
  RETURN QUERY
  WITH m AS (
    SELECT r.user_id AS uid, array_agg(r.role::text ORDER BY r.role::text) AS roles
    FROM public.user_roles r
    GROUP BY r.user_id
    HAVING bool_or(r.role::text IN ('researcher', 'admin', 'super_admin'))
  )
  SELECT m.uid, u.email::text, m.roles, s.xp, s.level, s.quests_done, learn._last_activity(m.uid)
  FROM m
  LEFT JOIN auth.users u ON u.id = m.uid
  CROSS JOIN LATERAL learn._summary(m.uid, 'admin' = ANY (m.roles) OR 'super_admin' = ANY (m.roles)) s
  ORDER BY s.xp DESC, u.email NULLS LAST, m.uid;
END $$;

-- 4. Who may call what.
DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'learn._gate()', 'learn._levels()', 'learn._auto_done(text, uuid)', 'learn._progress(uuid, boolean)',
      'learn._summary(uuid, boolean)', 'learn._last_activity(uuid)',
      'public.learn_me()', 'public.learn_summary()', 'public.learn_mark(text)', 'public.learn_team()'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.learn_me(), public.learn_summary(), public.learn_mark(text),
      public.learn_team() TO authenticated;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
