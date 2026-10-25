-- ============================================================
-- C21 - the genealogies of the indexes on the site (C21_INDEX_SITE_2026_10_25, Srangam INDEX_SITE_2026_10_25)
-- docs/INDEX_SITE_2026-10-25.md. Paste this whole file once in the Lovable Cloud SQL editor (one transaction).
-- Read-only checks: docs/cloud/C21_checks_2026-10-25.sql, one query per paste.
--
-- Why. Asked on 25 Oct: "i thought ill see the geneaologies of kings on a react front end and our carefully built
-- db mirrored from local to supabase!" The desk reads the kinships of the three indexes (data/shelf/kin.db:
-- kin_index.py), checks each against the Sanskrit verse it cites (data/shelf/vamsa.db: vamsa_check.py) and against
-- our own passages (entity_links), and draws the lines of descent (the dashboard's /vamsa). None of it was on the
-- site. Decided (H2): the relations derived from the indexes may go to the site with their credit and the notice
-- of their licence (the Cologne digitizations, CC BY-NC-SA 3.0) while the site is non-commercial; GRETIL's verses
-- with their credit (CC BY-NC-SA 4.0); the Mahabharata's e-text never (its counts and references only).
-- Raychaudhuri's claims are not sent (their mirror is B2).
--
-- What it adds: seven tables in the private schema corpus, filled by the PC's scripts/index_sync.py through the
-- edge function corpus-index (HMAC-signed, as corpus-ingest), recomputed from the desk each run (a row gone there
-- is deleted here: these are derived, not records):
--   corpus.index_texts       the sources and the GRETIL texts, with their credits and rights (show: the words may
--                            be shown);
--   corpus.index_persons     each person of an index that has a parent, a child or a spouse in it: the head word,
--                            sex where the index says it, how far the line runs up and down, our name when the
--                            entry is tied to it, the spouses, and the line up and down the desk draws (main_up,
--                            main_down: vamsa_view.py's rule, so the site draws the line the desk draws);
--   corpus.index_steps       each parent-child step, with what it rests on: how its persons were told apart, both
--                            entries or one, the best check of its citations and of our texts, the epics' verses;
--   corpus.index_statements  each kept relation the indexes state (all kinds: family, marriage, learning, rule),
--                            with the entry's words, its references, its checks and our passages that name both;
--   corpus.index_lines       the longest lines of each index;
--   corpus.index_verses      the GRETIL verses where both names stand (shown texts only);
--   corpus.index_meta        what the last run sent.
-- Four service functions (service_role only: the edge function) and five reader functions behind the readers'
-- gate (C5, corpus._reader_gate(): signed-in readers only): corpus_reader_index_overview(),
-- corpus_reader_index_lines(source), corpus_reader_index_find(folded name, source, k),
-- corpus_reader_index_tree(source, entry, via, down) and corpus_reader_index_of_name(canonical).
-- The overview, a tree and a name's statements come as one row (result jsonb), as every reader's rows come to
-- the site (src/lib/corpusMirror.ts callMirror reads a list).
-- Nothing existing is changed.
--
-- Needs C4 and C5. Re-running it changes nothing.
-- Rollback (one paste):
--   DROP FUNCTION IF EXISTS public.corpus_reader_index_overview(), public.corpus_reader_index_lines(text),
--     public.corpus_reader_index_find(text, text, integer), public.corpus_reader_index_tree(text, integer, integer, integer),
--     public.corpus_reader_index_of_name(text), public.corpus_index_manifest(), public.corpus_index_keys(text),
--     public.corpus_index_ingest(text, jsonb), public.corpus_index_delete(text, jsonb),
--     corpus._index_person(text, integer), corpus._index_step(text, integer, integer), corpus._index_statement(text),
--     corpus._index_relation_rank(text);
--   DROP TABLE IF EXISTS corpus.index_meta, corpus.index_verses, corpus.index_lines, corpus.index_statements,
--     corpus.index_steps, corpus.index_persons, corpus.index_texts;
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C21: corpus._reader_gate() is not there (C5 comes first). Nothing was changed.';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS corpus.index_texts (
    key        TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,            -- 'index' (the three indexes) or 'text' (a text whose verses are checked)
    code       TEXT NOT NULL,
    title      TEXT,
    edition    TEXT,
    rights     TEXT,
    show       BOOLEAN NOT NULL DEFAULT false,
    row_hash   TEXT NOT NULL,
    synced_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus.index_persons (
    key         TEXT PRIMARY KEY,         -- source:entry
    source      TEXT NOT NULL,
    entry       INTEGER NOT NULL,         -- the index's entry; below 0: a person the index names whose entry cannot be told
    head        TEXT NOT NULL,
    fold        TEXT NOT NULL,            -- the head word folded (relations_view.split_mark), for the search
    sex         TEXT,
    named_only  BOOLEAN NOT NULL DEFAULT false,
    has_line    BOOLEAN NOT NULL DEFAULT false,   -- has a parent or a child in the index
    up          INTEGER NOT NULL DEFAULT 1,
    down        INTEGER NOT NULL DEFAULT 1,
    parents_n   INTEGER NOT NULL DEFAULT 0,
    children_n  INTEGER NOT NULL DEFAULT 0,
    canonical   TEXT,                     -- our name (corpus.entities.canonical), when the entry is tied to it
    spouses     JSONB NOT NULL DEFAULT '[]'::jsonb,
    main_up     INTEGER[] NOT NULL DEFAULT '{}',  -- the line up, the eldest first, the person left out
    main_down   INTEGER[] NOT NULL DEFAULT '{}',  -- the line down, the person left out
    row_hash    TEXT NOT NULL,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, entry)
);
CREATE INDEX IF NOT EXISTS corpus_index_persons_fold ON corpus.index_persons (fold text_pattern_ops) WHERE has_line;
CREATE INDEX IF NOT EXISTS corpus_index_persons_canonical ON corpus.index_persons (canonical) WHERE canonical IS NOT NULL;

CREATE TABLE IF NOT EXISTS corpus.index_steps (
    key           TEXT PRIMARY KEY,       -- source:parent:child
    source        TEXT NOT NULL,
    parent        INTEGER NOT NULL,
    child         INTEGER NOT NULL,
    joined        TEXT,                   -- rule, verse or named: how its persons were told apart
    both_entries  BOOLEAN NOT NULL DEFAULT false,
    cited         TEXT,                   -- the best check of its citations (vamsa_check.py)
    ours          TEXT,                   -- the best check against our texts (kin_index.py)
    epic          JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {mbh|hv|ram: [verses naming both, the first]}
    statements    TEXT[] NOT NULL DEFAULT '{}',          -- corpus.index_statements keys, as the desk orders them
    verse_keys    TEXT[] NOT NULL DEFAULT '{}',          -- corpus.index_verses keys its checks found
    row_hash      TEXT NOT NULL,
    synced_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, parent, child)
);
CREATE INDEX IF NOT EXISTS corpus_index_steps_child ON corpus.index_steps (source, child);

CREATE TABLE IF NOT EXISTS corpus.index_statements (
    key                TEXT PRIMARY KEY,
    source             TEXT NOT NULL,
    entry_id           INTEGER NOT NULL,
    head               TEXT,              -- the entry that states it
    subject            TEXT NOT NULL,
    relation           TEXT NOT NULL,
    object             TEXT NOT NULL,
    words              TEXT,              -- the entry's own words for it
    refs               JSONB NOT NULL DEFAULT '[]'::jsonb,
    n                  INTEGER NOT NULL DEFAULT 1,   -- how many times the entry states it
    subject_entry      INTEGER,
    object_entry       INTEGER,
    subject_canonical  TEXT,
    object_canonical   TEXT,
    ours               TEXT,              -- named together, named near, both named never near, one not in our texts ...
    passages           INTEGER NOT NULL DEFAULT 0,
    texts              INTEGER NOT NULL DEFAULT 0,
    places             JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{doc, page, idx, ref}]: our passages naming both
    cited              TEXT,
    cites              JSONB NOT NULL DEFAULT '[]'::jsonb,
    best_text          TEXT,
    best_ref           TEXT,
    together           JSONB NOT NULL DEFAULT '{}'::jsonb,
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corpus_index_statements_subject ON corpus.index_statements (subject_canonical)
    WHERE subject_canonical IS NOT NULL;
CREATE INDEX IF NOT EXISTS corpus_index_statements_object ON corpus.index_statements (object_canonical)
    WHERE object_canonical IS NOT NULL;

CREATE TABLE IF NOT EXISTS corpus.index_lines (
    key         TEXT PRIMARY KEY,         -- source:rank
    source      TEXT NOT NULL,
    rank        INTEGER NOT NULL,
    entries     INTEGER[] NOT NULL,
    heads       TEXT[] NOT NULL,
    length      INTEGER NOT NULL,
    both_steps  INTEGER NOT NULL DEFAULT 0,
    row_hash    TEXT NOT NULL,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus.index_verses (
    key        TEXT PRIMARY KEY,          -- text|ref
    text       TEXT NOT NULL,
    ref        TEXT NOT NULL,
    words      TEXT NOT NULL,
    row_hash   TEXT NOT NULL,
    synced_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus.index_meta (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    row_hash   TEXT NOT NULL,
    synced_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['index_texts', 'index_persons', 'index_steps', 'index_statements', 'index_lines',
                           'index_verses', 'index_meta'] LOOP
    EXECUTE format('ALTER TABLE corpus.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON corpus.%I FROM PUBLIC', t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM anon', t); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON corpus.%I FROM authenticated', t); END IF;
  END LOOP;
END $$;

-- ---- the service functions (the edge function corpus-index, as service_role) ------------------------------------

CREATE OR REPLACE FUNCTION corpus._index_rel(p_table text) RETURNS regclass
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT CASE p_table
    WHEN 'texts' THEN 'corpus.index_texts'::regclass
    WHEN 'persons' THEN 'corpus.index_persons'::regclass
    WHEN 'steps' THEN 'corpus.index_steps'::regclass
    WHEN 'statements' THEN 'corpus.index_statements'::regclass
    WHEN 'lines' THEN 'corpus.index_lines'::regclass
    WHEN 'verses' THEN 'corpus.index_verses'::regclass
    WHEN 'meta' THEN 'corpus.index_meta'::regclass
  END
$$;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE t text; n bigint; d text; result jsonb := '{}'::jsonb;
BEGIN
  FOREACH t IN ARRAY ARRAY['texts', 'persons', 'steps', 'statements', 'lines', 'verses', 'meta'] LOOP
    EXECUTE format('SELECT count(*), md5(coalesce(string_agg(key || '':'' || row_hash, '','' ORDER BY key COLLATE "C"), '''')) FROM %s',
                   corpus._index_rel(t)) INTO n, d;
    result := result || jsonb_build_object(t, jsonb_build_object('n', n, 'digest', d));
  END LOOP;
  RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_keys(p_table text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE r regclass := corpus._index_rel(p_table); result jsonb;
BEGIN
  IF r IS NULL THEN RAISE EXCEPTION 'corpus_index_keys: unknown table %', p_table; END IF;
  EXECUTE format('SELECT coalesce(jsonb_object_agg(key, row_hash), ''{}''::jsonb) FROM %s', r) INTO result;
  RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_ingest(p_table text, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE n_in integer; n_changed integer := 0;
BEGIN
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' THEN
    RAISE EXCEPTION 'corpus_index_ingest: p_rows must be a JSON array';
  END IF;
  n_in := jsonb_array_length(p_rows);
  IF n_in > 2000 THEN RAISE EXCEPTION 'corpus_index_ingest: at most 2000 rows a call'; END IF;
  IF p_table = 'texts' THEN
    INSERT INTO corpus.index_texts AS t (key, kind, code, title, edition, rights, show, row_hash)
    SELECT x.key, x.kind, x.code, x.title, x.edition, x.rights, coalesce(x.show, false), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, kind text, code text, title text, edition text, rights text,
                                          show boolean, row_hash text)
    ON CONFLICT (key) DO UPDATE SET kind = excluded.kind, code = excluded.code, title = excluded.title,
      edition = excluded.edition, rights = excluded.rights, show = excluded.show, row_hash = excluded.row_hash,
      synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'persons' THEN
    INSERT INTO corpus.index_persons AS t (key, source, entry, head, fold, sex, named_only, has_line, up, down,
                                           parents_n, children_n, canonical, spouses, main_up, main_down, row_hash)
    SELECT x.key, x.source, x.entry, x.head, x.fold, x.sex, coalesce(x.named_only, false), coalesce(x.has_line, false),
           coalesce(x.up, 1), coalesce(x.down, 1), coalesce(x.parents_n, 0), coalesce(x.children_n, 0), x.canonical,
           coalesce(x.spouses, '[]'::jsonb), coalesce(x.main_up, '{}'), coalesce(x.main_down, '{}'), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, entry integer, head text, fold text, sex text,
                                          named_only boolean, has_line boolean, up integer, down integer,
                                          parents_n integer, children_n integer, canonical text, spouses jsonb,
                                          main_up integer[], main_down integer[], row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, entry = excluded.entry, head = excluded.head,
      fold = excluded.fold, sex = excluded.sex, named_only = excluded.named_only, has_line = excluded.has_line,
      up = excluded.up, down = excluded.down, parents_n = excluded.parents_n, children_n = excluded.children_n,
      canonical = excluded.canonical, spouses = excluded.spouses, main_up = excluded.main_up,
      main_down = excluded.main_down, row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'steps' THEN
    INSERT INTO corpus.index_steps AS t (key, source, parent, child, joined, both_entries, cited, ours, epic, statements,
                                         verse_keys, row_hash)
    SELECT x.key, x.source, x.parent, x.child, x.joined, coalesce(x.both_entries, false), x.cited, x.ours,
           coalesce(x.epic, '{}'::jsonb), coalesce(x.statements, '{}'), coalesce(x.verse_keys, '{}'), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, parent integer, child integer, joined text,
                                          both_entries boolean, cited text, ours text, epic jsonb, statements text[],
                                          verse_keys text[], row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, parent = excluded.parent, child = excluded.child,
      joined = excluded.joined, both_entries = excluded.both_entries, cited = excluded.cited, ours = excluded.ours,
      epic = excluded.epic, statements = excluded.statements, verse_keys = excluded.verse_keys,
      row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'statements' THEN
    INSERT INTO corpus.index_statements AS t (key, source, entry_id, head, subject, relation, object, words, refs, n,
                                              subject_entry, object_entry, subject_canonical, object_canonical, ours,
                                              passages, texts, places, cited, cites, best_text, best_ref, together,
                                              row_hash)
    SELECT x.key, x.source, x.entry_id, x.head, x.subject, x.relation, x.object, x.words, coalesce(x.refs, '[]'::jsonb),
           coalesce(x.n, 1), x.subject_entry, x.object_entry, x.subject_canonical, x.object_canonical, x.ours,
           coalesce(x.passages, 0), coalesce(x.texts, 0), coalesce(x.places, '[]'::jsonb), x.cited,
           coalesce(x.cites, '[]'::jsonb), x.best_text, x.best_ref, coalesce(x.together, '{}'::jsonb), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, entry_id integer, head text, subject text,
                                          relation text, object text, words text, refs jsonb, n integer,
                                          subject_entry integer, object_entry integer, subject_canonical text,
                                          object_canonical text, ours text, passages integer, texts integer,
                                          places jsonb, cited text, cites jsonb, best_text text, best_ref text,
                                          together jsonb, row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, entry_id = excluded.entry_id, head = excluded.head,
      subject = excluded.subject, relation = excluded.relation, object = excluded.object, words = excluded.words,
      refs = excluded.refs, n = excluded.n, subject_entry = excluded.subject_entry,
      object_entry = excluded.object_entry, subject_canonical = excluded.subject_canonical,
      object_canonical = excluded.object_canonical, ours = excluded.ours, passages = excluded.passages,
      texts = excluded.texts, places = excluded.places, cited = excluded.cited, cites = excluded.cites,
      best_text = excluded.best_text, best_ref = excluded.best_ref, together = excluded.together,
      row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'lines' THEN
    INSERT INTO corpus.index_lines AS t (key, source, rank, entries, heads, length, both_steps, row_hash)
    SELECT x.key, x.source, x.rank, x.entries, x.heads, x.length, coalesce(x.both_steps, 0), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, rank integer, entries integer[], heads text[],
                                          length integer, both_steps integer, row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, rank = excluded.rank, entries = excluded.entries,
      heads = excluded.heads, length = excluded.length, both_steps = excluded.both_steps,
      row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'verses' THEN
    INSERT INTO corpus.index_verses AS t (key, text, ref, words, row_hash)
    SELECT x.key, x.text, x.ref, x.words, x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, text text, ref text, words text, row_hash text)
    ON CONFLICT (key) DO UPDATE SET text = excluded.text, ref = excluded.ref, words = excluded.words,
      row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'meta' THEN
    INSERT INTO corpus.index_meta AS t (key, value, row_hash)
    SELECT x.key, x.value, x.row_hash FROM jsonb_to_recordset(p_rows) AS x(key text, value jsonb, row_hash text)
    ON CONFLICT (key) DO UPDATE SET value = excluded.value, row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSE
    RAISE EXCEPTION 'corpus_index_ingest: unknown table %', p_table;
  END IF;
  GET DIAGNOSTICS n_changed = ROW_COUNT;
  RETURN jsonb_build_object('rows', n_in, 'changed', n_changed);
END $$;

CREATE OR REPLACE FUNCTION public.corpus_index_delete(p_table text, p_keys jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE r regclass := corpus._index_rel(p_table); n integer;
BEGIN
  IF r IS NULL THEN RAISE EXCEPTION 'corpus_index_delete: unknown table %', p_table; END IF;
  IF p_keys IS NULL OR jsonb_typeof(p_keys) <> 'array' THEN
    RAISE EXCEPTION 'corpus_index_delete: p_keys must be a JSON array';
  END IF;
  IF jsonb_array_length(p_keys) > 5000 THEN RAISE EXCEPTION 'corpus_index_delete: at most 5000 keys a call'; END IF;
  EXECUTE format('DELETE FROM %s WHERE key IN (SELECT jsonb_array_elements_text($1))', r) USING p_keys;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN jsonb_build_object('deleted', n);
END $$;

-- ---- what the readers read -----------------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION corpus._index_person(p_source text, p_entry integer) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT coalesce(
    (SELECT jsonb_build_object('entry', x.entry, 'head', x.head, 'sex', coalesce(x.sex, ''), 'named_only', x.named_only,
                               'parents', x.parents_n, 'children', x.children_n, 'up', x.up, 'down', x.down,
                               'canonical', x.canonical, 'spouses', x.spouses)
     FROM corpus.index_persons x WHERE x.source = p_source AND x.entry = p_entry),
    jsonb_build_object('entry', p_entry, 'head', p_entry::text, 'sex', '', 'named_only', p_entry < 0, 'parents', 0,
                       'children', 0, 'up', 1, 'down', 1, 'canonical', NULL, 'spouses', '[]'::jsonb))
$$;

CREATE OR REPLACE FUNCTION corpus._index_statement(p_key text) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('key', s.key, 'source', s.source, 'stated_in', s.head, 'entry_id', s.entry_id, 'relation', s.relation,
                            'subject', s.subject, 'object', s.object, 'words', s.words, 'refs', s.refs, 'n', s.n,
                            'subject_entry', s.subject_entry, 'object_entry', s.object_entry,
                            'subject_canonical', s.subject_canonical, 'object_canonical', s.object_canonical,
                            'ours', s.ours, 'passages', s.passages, 'texts', s.texts, 'places', s.places,
                            'cited', s.cited, 'cites', s.cites, 'best_text', s.best_text, 'best_ref', s.best_ref,
                            'together', s.together)
  FROM corpus.index_statements s WHERE s.key = p_key
$$;

CREATE OR REPLACE FUNCTION corpus._index_step(p_source text, p_parent integer, p_child integer) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('parent', s.parent, 'child', s.child, 'joined', s.joined, 'both_entries', s.both_entries,
                            'cited', s.cited, 'ours', s.ours, 'epic', s.epic,
                            'items', coalesce((SELECT jsonb_agg(corpus._index_statement(k.key) ORDER BY k.n)
                                               FROM unnest(s.statements) WITH ORDINALITY AS k(key, n)
                                               WHERE EXISTS (SELECT 1 FROM corpus.index_statements z WHERE z.key = k.key)),
                                              '[]'::jsonb))
  FROM corpus.index_steps s WHERE s.source = p_source AND s.parent = p_parent AND s.child = p_child
$$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_overview()
RETURNS TABLE (result jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  RETURN QUERY SELECT jsonb_build_object(
    'sources', coalesce((SELECT jsonb_agg(jsonb_build_object(
        'source', t.code, 'title', t.title, 'edition', t.edition, 'rights', t.rights,
        'persons', (SELECT count(*) FROM corpus.index_persons p WHERE p.source = t.code AND p.has_line),
        'tied', (SELECT count(*) FROM corpus.index_persons p WHERE p.source = t.code AND p.canonical IS NOT NULL),
        'steps', (SELECT count(*) FROM corpus.index_steps s WHERE s.source = t.code),
        'statements', (SELECT count(*) FROM corpus.index_statements s WHERE s.source = t.code),
        'lines', (SELECT count(*) FROM corpus.index_lines l WHERE l.source = t.code)) ORDER BY t.key)
      FROM corpus.index_texts t WHERE t.kind = 'index'), '[]'::jsonb),
    'texts', coalesce((SELECT jsonb_agg(jsonb_build_object('code', t.code, 'title', t.title, 'edition', t.edition,
                                                           'rights', t.rights, 'show', t.show) ORDER BY t.key)
                       FROM corpus.index_texts t WHERE t.kind = 'text'), '[]'::jsonb),
    'run', (SELECT m.value || jsonb_build_object('synced_at', m.synced_at) FROM corpus.index_meta m WHERE m.key = 'run'));
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_lines(p_source text DEFAULT NULL)
RETURNS TABLE (source text, rank integer, entries integer[], heads text[], length integer, both_steps integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  RETURN QUERY
  SELECT l.source, l.rank, l.entries, l.heads, l.length, l.both_steps FROM corpus.index_lines l
  WHERE p_source IS NULL OR l.source = p_source
  ORDER BY l.source, l.rank;
END $$;

CREATE OR REPLACE FUNCTION public.corpus_reader_index_find(p_fold text, p_source text DEFAULT NULL, p_k integer DEFAULT 20)
RETURNS TABLE (source text, entry integer, head text, sex text, up integer, down integer, canonical text, exact boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE f text := lower(regexp_replace(coalesce(p_fold, ''), '[^a-zA-Z0-9]+', '', 'g'));
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  IF length(f) < 2 THEN RETURN; END IF;
  RETURN QUERY
  SELECT p.source, p.entry, p.head, coalesce(p.sex, ''), p.up, p.down, p.canonical, p.fold = f
  FROM corpus.index_persons p
  WHERE p.has_line AND p.fold LIKE f || '%' AND (p_source IS NULL OR p.source = p_source)
  ORDER BY (p.fold <> f), -(p.up + p.down), p.head COLLATE "C", p.source, p.entry
  LIMIT least(greatest(coalesce(p_k, 20), 1), 50);
END $$;

-- One person of one index: the line up and down (main_up, main_down, as the desk draws it; through p_via, a parent,
-- when the index gives the person two), each step with its evidence, each rung's siblings and other parents, the
-- children and grandchildren (p_down generations, 4 at most, 24 a generation), the GRETIL verses the checks found.
-- Names are ordered as the desk orders them (code points: COLLATE "C"), so the site draws what /vamsa draws.
CREATE OR REPLACE FUNCTION public.corpus_reader_index_tree(p_source text, p_entry integer, p_via integer DEFAULT NULL,
                                                           p_down integer DEFAULT 2)
RETURNS TABLE (result jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  me_row corpus.index_persons;
  via_up integer[];
  line integer[];
  me integer;
  n integer;
  i integer;
  e integer;
  par integer;
  rungs jsonb := '[]'::jsonb;
  steps jsonb := '[]'::jsonb;
  gens jsonb := '[]'::jsonb;
  gen jsonb;
  used text[] := '{}';
  level integer[];
  nxt integer[];
  seen integer[];
  r record;
  sib jsonb;
  sib_n integer;
  others jsonb;
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  SELECT * INTO me_row FROM corpus.index_persons x WHERE x.source = p_source AND x.entry = p_entry;
  IF NOT FOUND THEN
    RETURN QUERY SELECT jsonb_build_object('error', 'no such person in the index'); RETURN;
  END IF;
  IF p_via IS NOT NULL AND EXISTS (SELECT 1 FROM corpus.index_steps s WHERE s.source = p_source AND s.parent = p_via
                                   AND s.child = p_entry) THEN
    SELECT x.main_up INTO via_up FROM corpus.index_persons x WHERE x.source = p_source AND x.entry = p_via;
    via_up := coalesce(via_up, '{}') || p_via;
    IF NOT (p_entry = ANY (via_up)) THEN
      line := via_up || p_entry || me_row.main_down;
    END IF;
  END IF;
  IF line IS NULL THEN
    line := me_row.main_up || p_entry || me_row.main_down;
  END IF;
  n := array_length(line, 1);
  me := array_position(line, p_entry);
  FOR i IN 1..n LOOP
    e := line[i];
    par := CASE WHEN i > 1 THEN line[i - 1] END;
    sib := '[]'::jsonb; sib_n := 0;
    IF par IS NOT NULL THEN
      SELECT coalesce(jsonb_agg(jsonb_build_object('entry', q.entry, 'head', q.head) ORDER BY q.head COLLATE "C", q.entry)
                      FILTER (WHERE q.rn <= 16), '[]'::jsonb), count(*)
      INTO sib, sib_n
      FROM (SELECT s.child AS entry, coalesce(p.head, s.child::text) AS head,
                   row_number() OVER (ORDER BY coalesce(p.head, s.child::text) COLLATE "C", s.child) AS rn
            FROM corpus.index_steps s
            LEFT JOIN corpus.index_persons p ON p.source = s.source AND p.entry = s.child
            WHERE s.source = p_source AND s.parent = par AND s.child <> e) q;
    END IF;
    others := '[]'::jsonb;
    FOR r IN SELECT s.parent, s.key FROM corpus.index_steps s
             LEFT JOIN corpus.index_persons p ON p.source = s.source AND p.entry = s.parent
             WHERE s.source = p_source AND s.child = e AND (par IS NULL OR s.parent <> par)
             ORDER BY coalesce(p.head, s.parent::text) COLLATE "C", s.parent LIMIT 4 LOOP
      others := others || jsonb_build_array(corpus._index_person(p_source, r.parent)
                                            || jsonb_build_object('evidence', corpus._index_step(p_source, r.parent, e)));
      used := used || r.key;
    END LOOP;
    rungs := rungs || jsonb_build_array(corpus._index_person(p_source, e) || jsonb_build_object(
      'generation', i - me, 'siblings', sib, 'siblings_n', sib_n, 'other_parents', others));
    IF i < n THEN
      steps := steps || jsonb_build_array(corpus._index_step(p_source, line[i], line[i + 1]));
      used := used || (p_source || ':' || line[i] || ':' || line[i + 1]);
    END IF;
  END LOOP;
  level := ARRAY[p_entry];
  seen := line[1:me];
  FOR i IN 1..least(greatest(coalesce(p_down, 2), 0), 4) LOOP
    gen := '[]'::jsonb;
    nxt := '{}';
    FOR r IN SELECT s.parent, s.child, s.key FROM unnest(level) WITH ORDINALITY AS lv(entry, pos)
             JOIN corpus.index_steps s ON s.source = p_source AND s.parent = lv.entry
             LEFT JOIN corpus.index_persons p ON p.source = s.source AND p.entry = s.child
             ORDER BY lv.pos, coalesce(p.head, s.child::text) COLLATE "C", s.child LOOP
      CONTINUE WHEN r.child = ANY (seen) OR r.child = ANY (nxt);
      EXIT WHEN coalesce(array_length(nxt, 1), 0) >= 24;
      nxt := nxt || r.child;
      gen := gen || jsonb_build_array(corpus._index_person(p_source, r.child) || jsonb_build_object(
        'of', r.parent, 'on_line', r.child = ANY (line[me + 1:n]),
        'evidence', corpus._index_step(p_source, r.parent, r.child)));
      used := used || r.key;
    END LOOP;
    EXIT WHEN coalesce(array_length(nxt, 1), 0) = 0;
    seen := seen || nxt;
    gens := gens || jsonb_build_array(gen);
    level := nxt;
  END LOOP;
  RETURN QUERY SELECT jsonb_build_object(
    'source', p_source, 'entry', p_entry, 'me', me - 1,
    'title', (SELECT t.title FROM corpus.index_texts t WHERE t.kind = 'index' AND t.code = p_source),
    'person', corpus._index_person(p_source, p_entry),
    'line', rungs, 'steps', steps, 'down', gens,
    'verses', coalesce((SELECT jsonb_object_agg(v.key, v.words) FROM corpus.index_verses v
                        WHERE v.key IN (SELECT unnest(s.verse_keys) FROM corpus.index_steps s
                                        WHERE s.key = ANY (used))), '{}'::jsonb),
    'texts', coalesce((SELECT jsonb_object_agg(t.code, jsonb_build_object('title', t.title, 'edition', t.edition,
                                                                          'rights', t.rights, 'show', t.show))
                       FROM corpus.index_texts t WHERE t.kind = 'text'), '{}'::jsonb));
END $$;

-- The desk's groups of relations (relations_view.py GROUPS), in the order a name's page lists them: family, marriage,
-- siblings, rule, learning, time, the rest.
CREATE OR REPLACE FUNCTION corpus._index_relation_rank(p_relation text) RETURNS integer
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
  SELECT CASE
    WHEN p_relation IN ('son_of', 'daughter_of', 'father_of', 'mother_of', 'grandson_of', 'granddaughter_of',
                        'grandfather_of', 'descendant_of', 'ancestor_of') THEN 0
    WHEN p_relation IN ('wife_of', 'husband_of', 'married') THEN 1
    WHEN p_relation IN ('brother_of', 'sister_of') THEN 2
    WHEN p_relation IN ('king_of', 'queen_of', 'successor_of', 'predecessor_of') THEN 3
    WHEN p_relation IN ('pupil_of', 'teacher_of', 'priest_of', 'patron_of') THEN 4
    WHEN p_relation = 'contemporary_of' THEN 5
    ELSE 6 END
$$;

-- A name of ours: the persons of the indexes tied to it, and what the indexes state of it (80 statements at most,
-- the family's first).
CREATE OR REPLACE FUNCTION public.corpus_reader_index_of_name(p_canonical text)
RETURNS TABLE (result jsonb) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  RETURN QUERY SELECT jsonb_build_object(
    'persons', coalesce((SELECT jsonb_agg(jsonb_build_object('source', p.source, 'entry', p.entry, 'head', p.head,
                                                             'sex', coalesce(p.sex, ''), 'up', p.up, 'down', p.down,
                                                             'parents', p.parents_n, 'children', p.children_n,
                                                             'has_line', p.has_line)
                                          ORDER BY p.source, -(p.up + p.down), p.head COLLATE "C")
                         FROM corpus.index_persons p WHERE p.canonical = p_canonical), '[]'::jsonb),
    'statements', coalesce((SELECT jsonb_agg(corpus._index_statement(q.key) ORDER BY q.rank, q.source, q.relation, q.key)
                            FROM (SELECT s.key, s.source, s.relation, corpus._index_relation_rank(s.relation) AS rank
                                  FROM corpus.index_statements s
                                  WHERE s.subject_canonical = p_canonical OR s.object_canonical = p_canonical
                                  ORDER BY 4, s.source, s.relation, s.key LIMIT 80) q), '[]'::jsonb),
    'statements_n', (SELECT count(*) FROM corpus.index_statements s
                     WHERE s.subject_canonical = p_canonical OR s.object_canonical = p_canonical));
END $$;

COMMENT ON TABLE corpus.index_persons IS 'C21_INDEX_SITE_2026_10_25: the persons of the indexes'' lines, from the desk (index_sync.py).';
COMMENT ON FUNCTION public.corpus_reader_index_tree(text, integer, integer, integer) IS
  'C21_INDEX_SITE_2026_10_25: one person of one index, the line up and down with each step''s evidence (signed-in readers only).';

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_index_manifest()', 'public.corpus_index_keys(text)',
                           'public.corpus_index_ingest(text, jsonb)', 'public.corpus_index_delete(text, jsonb)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f); END IF;
  END LOOP;
  FOREACH f IN ARRAY ARRAY['corpus._index_rel(text)', 'corpus._index_person(text, integer)',
                           'corpus._index_statement(text)', 'corpus._index_step(text, integer, integer)',
                           'corpus._index_relation_rank(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  END LOOP;
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_index_overview()', 'public.corpus_reader_index_lines(text)',
                           'public.corpus_reader_index_find(text, text, integer)',
                           'public.corpus_reader_index_tree(text, integer, integer, integer)',
                           'public.corpus_reader_index_of_name(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
    END IF;
  END LOOP;
END $$;

COMMIT;
