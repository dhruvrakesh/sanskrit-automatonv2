-- ============================================================
-- C23 - the scholars' claims beside the genealogies (C23_INDEX_CLAIMS_2026_10_28, Srangam B2_SITE_2026_10_28)
-- docs/B2_AND_X1C_2026-10-28.md. Paste this whole file once in the Lovable Cloud SQL editor (one transaction), AFTER
-- C21. Read-only checks: docs/cloud/C23_checks_2026-10-28.sql, one query per paste.
--
-- Why. Asked on 28 Oct: "B2 (Raychaudhuri's view of each step)". The desk weighs each kinship of the three indexes
-- against Hemchandra Raychaudhuri's Political History of Ancient India (1923; public domain: the author died in 1957;
-- India, 60 years after; the USA, published before 1929): 2,010 claims read from its scan page by page
-- (scholar_claims.py), each checked against the page's own words, their names tied to ours (CLAIMS_LINK); a kinship
-- the book states too is "R agrees", one it states the other way round "R reversed", another relation of the same two
-- "R differs" (kin_index.py). None of it was on the site.
--
-- What it adds, to C21's tables and functions (nothing else is touched):
--   corpus.index_statements.scholars  [{work, verdict, note, claims: [keys]}]: a scholar's view of the relation;
--   corpus.index_steps.scholar        the best verdict of a step's relations (agrees, differs, reversed);
--   corpus.index_claims               the claims of the public-domain works whose quotation was found on the page
--                                     (exact or close), with the page, the book's words as the scan reads them, the
--                                     stance, the works it cites and where we hold them, and the names tied to ours
--                                     (one candidate only; how each tie was made);
--   corpus.index_texts kind 'work'    the work, its edition and its rights.
-- It replaces eight of C21's functions with the same signatures and the claims added: corpus._index_rel,
-- corpus_index_manifest, corpus_index_ingest, corpus._index_statement, corpus._index_step,
-- corpus_reader_index_overview, corpus_reader_index_tree, corpus_reader_index_of_name (and adds corpus._index_claim).
-- So once C23 is pasted, C21 is NOT to be pasted again (it would put back the functions without the claims; C23 again
-- mends it).
--
-- Needs C21 (and so C4, C5). Re-running it changes nothing.
-- Rollback (one paste; the genealogies stay as C21 made them, without the claims):
--   DROP FUNCTION IF EXISTS corpus._index_claim(text);
--   DROP TABLE IF EXISTS corpus.index_claims;
--   ALTER TABLE corpus.index_statements DROP COLUMN IF EXISTS scholars;
--   ALTER TABLE corpus.index_steps DROP COLUMN IF EXISTS scholar;
--   then paste C21 again (its functions without the claims).
-- ============================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.index_statements') IS NULL OR to_regprocedure('corpus._reader_gate()') IS NULL THEN
    RAISE EXCEPTION 'C23: C21 is not there (C21 comes first). Nothing was changed.';
  END IF;
END $$;

ALTER TABLE corpus.index_statements ADD COLUMN IF NOT EXISTS scholars JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE corpus.index_steps ADD COLUMN IF NOT EXISTS scholar TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS corpus.index_claims (
    key                TEXT PRIMARY KEY,         -- work:pdf_page:n
    work               TEXT NOT NULL,            -- corpus.index_texts code of kind 'work' (phai1923)
    pdf_page           INTEGER NOT NULL,         -- the scan's page
    printed            TEXT,                     -- the book's own page number
    n                  INTEGER NOT NULL,         -- the claim's place on the page
    subject            TEXT NOT NULL,
    relation           TEXT NOT NULL,
    object             TEXT,
    claim              TEXT NOT NULL,            -- the claim, as read from the page (scholar_claims.py)
    quote              TEXT,                     -- the book's words for it, as the scan reads them (OCR, uncorrected)
    quote_check        TEXT,                     -- exact or close: found so on the page
    stance             TEXT,                     -- asserts, reports, doubts, rejects
    hedge              TEXT,
    subject_canonical  TEXT,                     -- our name, when the claim's subject is tied to one name of ours
    subject_how        TEXT,                     -- exact, numbered exact (certain); spelling, variant, plural ... (probable)
    object_canonical   TEXT,
    object_how         TEXT,
    cites              JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{printed, work, locus, ours, note}]
    row_hash           TEXT NOT NULL,
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corpus_index_claims_subject ON corpus.index_claims (subject_canonical)
    WHERE subject_canonical IS NOT NULL;
CREATE INDEX IF NOT EXISTS corpus_index_claims_object ON corpus.index_claims (object_canonical)
    WHERE object_canonical IS NOT NULL;
ALTER TABLE corpus.index_claims ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON corpus.index_claims FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON corpus.index_claims FROM anon; END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON corpus.index_claims FROM authenticated; END IF;
END $$;

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
    WHEN 'claims' THEN 'corpus.index_claims'::regclass   -- C23_INDEX_CLAIMS_2026_10_28
  END
$$;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE t text; n bigint; d text; result jsonb := '{}'::jsonb;
BEGIN
  FOREACH t IN ARRAY ARRAY['texts', 'persons', 'steps', 'statements', 'lines', 'verses', 'meta', 'claims'] LOOP
    EXECUTE format('SELECT count(*), md5(coalesce(string_agg(key || '':'' || row_hash, '','' ORDER BY key COLLATE "C"), '''')) FROM %s',
                   corpus._index_rel(t)) INTO n, d;
    result := result || jsonb_build_object(t, jsonb_build_object('n', n, 'digest', d));
  END LOOP;
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
                                         verse_keys, scholar, row_hash)
    SELECT x.key, x.source, x.parent, x.child, x.joined, coalesce(x.both_entries, false), x.cited, x.ours,
           coalesce(x.epic, '{}'::jsonb), coalesce(x.statements, '{}'), coalesce(x.verse_keys, '{}'),
           coalesce(x.scholar, ''), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, parent integer, child integer, joined text,
                                          both_entries boolean, cited text, ours text, epic jsonb, statements text[],
                                          verse_keys text[], scholar text, row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, parent = excluded.parent, child = excluded.child,
      joined = excluded.joined, both_entries = excluded.both_entries, cited = excluded.cited, ours = excluded.ours,
      epic = excluded.epic, statements = excluded.statements, verse_keys = excluded.verse_keys,
      scholar = excluded.scholar, row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSIF p_table = 'statements' THEN
    INSERT INTO corpus.index_statements AS t (key, source, entry_id, head, subject, relation, object, words, refs, n,
                                              subject_entry, object_entry, subject_canonical, object_canonical, ours,
                                              passages, texts, places, cited, cites, best_text, best_ref, together,
                                              scholars, row_hash)
    SELECT x.key, x.source, x.entry_id, x.head, x.subject, x.relation, x.object, x.words, coalesce(x.refs, '[]'::jsonb),
           coalesce(x.n, 1), x.subject_entry, x.object_entry, x.subject_canonical, x.object_canonical, x.ours,
           coalesce(x.passages, 0), coalesce(x.texts, 0), coalesce(x.places, '[]'::jsonb), x.cited,
           coalesce(x.cites, '[]'::jsonb), x.best_text, x.best_ref, coalesce(x.together, '{}'::jsonb),
           coalesce(x.scholars, '[]'::jsonb), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, entry_id integer, head text, subject text,
                                          relation text, object text, words text, refs jsonb, n integer,
                                          subject_entry integer, object_entry integer, subject_canonical text,
                                          object_canonical text, ours text, passages integer, texts integer,
                                          places jsonb, cited text, cites jsonb, best_text text, best_ref text,
                                          together jsonb, scholars jsonb, row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, entry_id = excluded.entry_id, head = excluded.head,
      subject = excluded.subject, relation = excluded.relation, object = excluded.object, words = excluded.words,
      refs = excluded.refs, n = excluded.n, subject_entry = excluded.subject_entry,
      object_entry = excluded.object_entry, subject_canonical = excluded.subject_canonical,
      object_canonical = excluded.object_canonical, ours = excluded.ours, passages = excluded.passages,
      texts = excluded.texts, places = excluded.places, cited = excluded.cited, cites = excluded.cites,
      best_text = excluded.best_text, best_ref = excluded.best_ref, together = excluded.together,
      scholars = excluded.scholars, row_hash = excluded.row_hash, synced_at = now()
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
  ELSIF p_table = 'claims' THEN   -- C23_INDEX_CLAIMS_2026_10_28
    INSERT INTO corpus.index_claims AS t (key, work, pdf_page, printed, n, subject, relation, object, claim, quote,
                                          quote_check, stance, hedge, subject_canonical, subject_how, object_canonical,
                                          object_how, cites, row_hash)
    SELECT x.key, x.work, x.pdf_page, x.printed, x.n, x.subject, x.relation, x.object, x.claim, x.quote, x.quote_check,
           x.stance, x.hedge, x.subject_canonical, x.subject_how, x.object_canonical, x.object_how,
           coalesce(x.cites, '[]'::jsonb), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, work text, pdf_page integer, printed text, n integer, subject text,
                                          relation text, object text, claim text, quote text, quote_check text,
                                          stance text, hedge text, subject_canonical text, subject_how text,
                                          object_canonical text, object_how text, cites jsonb, row_hash text)
    ON CONFLICT (key) DO UPDATE SET work = excluded.work, pdf_page = excluded.pdf_page, printed = excluded.printed,
      n = excluded.n, subject = excluded.subject, relation = excluded.relation, object = excluded.object,
      claim = excluded.claim, quote = excluded.quote, quote_check = excluded.quote_check, stance = excluded.stance,
      hedge = excluded.hedge, subject_canonical = excluded.subject_canonical, subject_how = excluded.subject_how,
      object_canonical = excluded.object_canonical, object_how = excluded.object_how, cites = excluded.cites,
      row_hash = excluded.row_hash, synced_at = now()
    WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
  ELSE
    RAISE EXCEPTION 'corpus_index_ingest: unknown table %', p_table;
  END IF;
  GET DIAGNOSTICS n_changed = ROW_COUNT;
  RETURN jsonb_build_object('rows', n_in, 'changed', n_changed);
END $$;

CREATE OR REPLACE FUNCTION corpus._index_claim(p_key text) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('key', c.key, 'work', c.work, 'pdf_page', c.pdf_page, 'printed', c.printed, 'n', c.n,
                            'subject', c.subject, 'relation', c.relation, 'object', c.object, 'claim', c.claim,
                            'quote', c.quote, 'quote_check', c.quote_check, 'stance', c.stance, 'hedge', c.hedge,
                            'subject_canonical', c.subject_canonical, 'subject_how', c.subject_how,
                            'object_canonical', c.object_canonical, 'object_how', c.object_how, 'cites', c.cites)
  FROM corpus.index_claims c WHERE c.key = p_key
$$;

CREATE OR REPLACE FUNCTION corpus._index_statement(p_key text) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('key', s.key, 'source', s.source, 'stated_in', s.head, 'entry_id', s.entry_id, 'relation', s.relation,
                            'subject', s.subject, 'object', s.object, 'words', s.words, 'refs', s.refs, 'n', s.n,
                            'subject_entry', s.subject_entry, 'object_entry', s.object_entry,
                            'subject_canonical', s.subject_canonical, 'object_canonical', s.object_canonical,
                            'ours', s.ours, 'passages', s.passages, 'texts', s.texts, 'places', s.places,
                            'cited', s.cited, 'cites', s.cites, 'best_text', s.best_text, 'best_ref', s.best_ref,
                            'together', s.together, 'scholars', s.scholars)
  FROM corpus.index_statements s WHERE s.key = p_key
$$;

CREATE OR REPLACE FUNCTION corpus._index_step(p_source text, p_parent integer, p_child integer) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT jsonb_build_object('parent', s.parent, 'child', s.child, 'joined', s.joined, 'both_entries', s.both_entries,
                            'cited', s.cited, 'ours', s.ours, 'epic', s.epic, 'scholar', s.scholar,
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
    'works', coalesce((SELECT jsonb_agg(jsonb_build_object('code', t.code, 'title', t.title, 'edition', t.edition,
                                                           'rights', t.rights,
                                                           'claims', (SELECT count(*) FROM corpus.index_claims c
                                                                      WHERE c.work = t.code)) ORDER BY t.key)
                       FROM corpus.index_texts t WHERE t.kind = 'work'), '[]'::jsonb),
    'run', (SELECT m.value || jsonb_build_object('synced_at', m.synced_at) FROM corpus.index_meta m WHERE m.key = 'run'));
END $$;

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
                       FROM corpus.index_texts t WHERE t.kind = 'text'), '{}'::jsonb),
    -- C23_INDEX_CLAIMS_2026_10_28: the scholars' works (apart from the texts, whose credit is GRETIL's), and the
    -- claims the shown statements rest on
    'works', coalesce((SELECT jsonb_object_agg(t.code, jsonb_build_object('title', t.title, 'edition', t.edition,
                                                                          'rights', t.rights, 'show', t.show))
                       FROM corpus.index_texts t WHERE t.kind = 'work'), '{}'::jsonb),
    'claims', coalesce((SELECT jsonb_object_agg(c.key, corpus._index_claim(c.key)) FROM corpus.index_claims c
                        WHERE c.key IN (SELECT jsonb_array_elements_text(sv -> 'claims')
                                        FROM corpus.index_steps s
                                        CROSS JOIN LATERAL unnest(s.statements) AS k(key)
                                        JOIN corpus.index_statements z ON z.key = k.key
                                        CROSS JOIN LATERAL jsonb_array_elements(z.scholars) AS sv
                                        WHERE s.key = ANY (used))), '{}'::jsonb));
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
                     WHERE s.subject_canonical = p_canonical OR s.object_canonical = p_canonical),
    -- C23_INDEX_CLAIMS_2026_10_28: what the scholars' works say of the name (60 at most, in the book's order)
    'claims', coalesce((SELECT jsonb_agg(corpus._index_claim(q.key) ORDER BY q.work, q.pdf_page, q.n)
                        FROM (SELECT c.key, c.work, c.pdf_page, c.n FROM corpus.index_claims c
                              WHERE c.subject_canonical = p_canonical OR c.object_canonical = p_canonical
                              ORDER BY c.work, c.pdf_page, c.n LIMIT 60) q), '[]'::jsonb),
    'claims_n', (SELECT count(*) FROM corpus.index_claims c
                 WHERE c.subject_canonical = p_canonical OR c.object_canonical = p_canonical));
END $$;

COMMENT ON TABLE corpus.index_claims IS 'C23_INDEX_CLAIMS_2026_10_28: the scholars'' claims (public-domain works only), from the desk (index_sync.py).';

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['public.corpus_index_manifest()', 'public.corpus_index_ingest(text, jsonb)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f); END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
      EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f); END IF;
  END LOOP;
  FOREACH f IN ARRAY ARRAY['corpus._index_rel(text)', 'corpus._index_statement(text)',
                           'corpus._index_step(text, integer, integer)', 'corpus._index_claim(text)'] LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  END LOOP;
  FOREACH f IN ARRAY ARRAY['public.corpus_reader_index_overview()',
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
