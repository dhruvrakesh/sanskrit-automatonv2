-- ============================================================
-- C26 - the epithets of the genealogies (C26_INDEX_ALIASES_2026_11_10, Srangam GENEALOGY_HEAL_2026_11_10)
-- docs/GENEALOGY_2026-11-10.md. Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1 and B2 (read-only, before), then
-- the change (one paste, one transaction), then A1, A2 and A3 (read-only, after). Export each result.
--
-- Why. Asked on 10 Nov: "we cant even get the genealogy of Kaunteya (Arjun) right". Soerensen's index defines 5,525 of
-- its 12,647 entries as another person or thing: "Kaunteya (the son of Kunti) = Arjuna", "Partha = Arjuna",
-- "Dhananjaya = Arjuna, q.v."; the Purana Index says "a name of Rama". The site drew such an entry as a person of its
-- own (Kaunti -> Kaunteya, two generations), and a search for "Dhananjaya" found nothing. The desk now ties each such
-- entry to the person's own entry (scripts/vamsa_view.py aliases, read from the index's words, no model) and
-- index_sync.py sends it: on the person's row when it has a line, else on a row of its own so that a search finds it.
--
-- What it changes (nothing else is touched):
--   corpus.index_persons.same_as   [{entry, head, how}]: the persons the entry names ("= Arjuna"), and how each was told
--                                   apart (the entry's number, the only entry of the name, the only one with a line,
--                                   the one with the most kin; "several, not told apart");
--   corpus.index_persons.gloss     the entry's own gloss ("the son of Kunti");
--   corpus_index_manifest          the same, and {"features": {"aliases": true}}: index_sync.py sends the epithets only
--                                   to a site that says so (before C26 it sends the rows without them);
--   corpus_index_ingest            C23's, the persons taking same_as and gloss;
--   corpus._index_person           C21's, with same_as and gloss (the tree and the readers give them);
--   corpus_reader_index_find       C21's, finding an epithet too, with same_as, gloss and has_line (dropped and made
--                                   again: its columns change).
--
-- Needs C21 and C23. Re-running it changes nothing.
-- Rollback (one paste): paste C23 again (its manifest and ingest), then
--   DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer);  and paste C21's find and person;
--   ALTER TABLE corpus.index_persons DROP COLUMN IF EXISTS same_as, DROP COLUMN IF EXISTS gloss;
-- ============================================================

-- B1 (before): C21 and C23 are there, the columns not yet. Expected: true, true, false.
SELECT to_regclass('corpus.index_persons') IS NOT NULL AS c21,
       to_regclass('corpus.index_claims') IS NOT NULL AS c23,
       EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'corpus' AND table_name = 'index_persons'
               AND column_name = 'same_as') AS c26;

-- B2 (before): the persons as the site has them, and the Kaunteya entries. Expected (10 Nov): 14,979 persons; the
-- Kaunteya rows of Soerensen's index (inm) with a line.
SELECT count(*) AS persons, count(*) FILTER (WHERE has_line) AS with_line,
       string_agg(CASE WHEN fold = 'kaunteya' THEN source || ':' || entry || ' ' || head END, '; ') AS kaunteya
FROM corpus.index_persons;

-- THE CHANGE (one paste, from BEGIN to COMMIT).
BEGIN;

DO $$
BEGIN
  IF to_regclass('corpus.index_persons') IS NULL OR to_regclass('corpus.index_claims') IS NULL THEN
    RAISE EXCEPTION 'C26: C21 and C23 come first. Nothing was changed.';
  END IF;
END $$;

ALTER TABLE corpus.index_persons ADD COLUMN IF NOT EXISTS same_as JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE corpus.index_persons ADD COLUMN IF NOT EXISTS gloss TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS corpus_index_persons_fold_alias ON corpus.index_persons (fold text_pattern_ops)
  WHERE same_as <> '[]'::jsonb;

CREATE OR REPLACE FUNCTION public.corpus_index_manifest()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE t text; n bigint; d text; result jsonb := '{}'::jsonb;
BEGIN
  FOREACH t IN ARRAY ARRAY['texts', 'persons', 'steps', 'statements', 'lines', 'verses', 'meta', 'claims'] LOOP
    EXECUTE format('SELECT count(*), md5(coalesce(string_agg(key || '':'' || row_hash, '','' ORDER BY key COLLATE "C"), '''')) FROM %s',
                   corpus._index_rel(t)) INTO n, d;
    result := result || jsonb_build_object(t, jsonb_build_object('n', n, 'digest', d));
  END LOOP;
  -- C26_INDEX_ALIASES_2026_11_10: what this site takes beyond the tables (index_sync.py asks before it sends)
  RETURN result || jsonb_build_object('features', jsonb_build_object('aliases', true));
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
    -- C26_INDEX_ALIASES_2026_11_10: and the epithets (same_as, gloss)
    INSERT INTO corpus.index_persons AS t (key, source, entry, head, fold, sex, named_only, has_line, up, down,
                                           parents_n, children_n, canonical, spouses, main_up, main_down, same_as,
                                           gloss, row_hash)
    SELECT x.key, x.source, x.entry, x.head, x.fold, x.sex, coalesce(x.named_only, false), coalesce(x.has_line, false),
           coalesce(x.up, 1), coalesce(x.down, 1), coalesce(x.parents_n, 0), coalesce(x.children_n, 0), x.canonical,
           coalesce(x.spouses, '[]'::jsonb), coalesce(x.main_up, '{}'), coalesce(x.main_down, '{}'),
           coalesce(x.same_as, '[]'::jsonb), coalesce(x.gloss, ''), x.row_hash
    FROM jsonb_to_recordset(p_rows) AS x(key text, source text, entry integer, head text, fold text, sex text,
                                          named_only boolean, has_line boolean, up integer, down integer,
                                          parents_n integer, children_n integer, canonical text, spouses jsonb,
                                          main_up integer[], main_down integer[], same_as jsonb, gloss text,
                                          row_hash text)
    ON CONFLICT (key) DO UPDATE SET source = excluded.source, entry = excluded.entry, head = excluded.head,
      fold = excluded.fold, sex = excluded.sex, named_only = excluded.named_only, has_line = excluded.has_line,
      up = excluded.up, down = excluded.down, parents_n = excluded.parents_n, children_n = excluded.children_n,
      canonical = excluded.canonical, spouses = excluded.spouses, main_up = excluded.main_up,
      main_down = excluded.main_down, same_as = excluded.same_as, gloss = excluded.gloss, row_hash = excluded.row_hash,
      synced_at = now()
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

CREATE OR REPLACE FUNCTION corpus._index_person(p_source text, p_entry integer) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT coalesce(
    (SELECT jsonb_build_object('entry', x.entry, 'head', x.head, 'sex', coalesce(x.sex, ''), 'named_only', x.named_only,
                               'parents', x.parents_n, 'children', x.children_n, 'up', x.up, 'down', x.down,
                               'canonical', x.canonical, 'spouses', x.spouses,
                               'same_as', x.same_as, 'gloss', x.gloss)   -- C26_INDEX_ALIASES_2026_11_10
     FROM corpus.index_persons x WHERE x.source = p_source AND x.entry = p_entry),
    jsonb_build_object('entry', p_entry, 'head', p_entry::text, 'sex', '', 'named_only', p_entry < 0, 'parents', 0,
                       'children', 0, 'up', 1, 'down', 1, 'canonical', NULL, 'spouses', '[]'::jsonb,
                       'same_as', '[]'::jsonb, 'gloss', ''))
$$;

DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer);
CREATE FUNCTION public.corpus_reader_index_find(p_fold text, p_source text DEFAULT NULL, p_k integer DEFAULT 20)
RETURNS TABLE (source text, entry integer, head text, sex text, up integer, down integer, canonical text, exact boolean,
               same_as jsonb, gloss text, has_line boolean)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
DECLARE f text := lower(regexp_replace(coalesce(p_fold, ''), '[^a-zA-Z0-9]+', '', 'g'));
BEGIN
  PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25
  IF length(f) < 2 THEN RETURN; END IF;
  RETURN QUERY
  SELECT p.source, p.entry, p.head, coalesce(p.sex, ''), p.up, p.down, p.canonical, p.fold = f, p.same_as, p.gloss,
         p.has_line
  FROM corpus.index_persons p
  WHERE (p.has_line OR p.same_as <> '[]'::jsonb) AND p.fold LIKE f || '%' AND (p_source IS NULL OR p.source = p_source)
  ORDER BY (p.fold <> f), (p.same_as = '[]'::jsonb), -(p.up + p.down), p.head COLLATE "C", p.source, p.entry
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

COMMENT ON FUNCTION public.corpus_reader_index_find(text, text, integer) IS
  'C26_INDEX_ALIASES_2026_11_10: the index''s persons by head word, an epithet too (with same_as), signed-in readers only.';

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
  EXECUTE 'REVOKE ALL ON FUNCTION corpus._index_person(text, integer) FROM PUBLIC';
  f := 'public.corpus_reader_index_find(text, text, integer)';
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', f); END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f);
  END IF;
END $$;

COMMIT;

-- A1 (after): the columns and the manifest's feature. Expected: true, true, true.
SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'corpus' AND table_name = 'index_persons'
               AND column_name = 'same_as') AS same_as,
       EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'corpus' AND table_name = 'index_persons'
               AND column_name = 'gloss') AS gloss,
       coalesce((public.corpus_index_manifest() -> 'features' ->> 'aliases')::boolean, false) AS manifest_says_aliases;

-- A2 (after the next index_sync.py --apply): the epithets the site holds. Expected: some thousands with same_as; the
-- Kaunteya rows naming Arjuna, Bhimasena, Karna and Yudhisthira.
SELECT count(*) FILTER (WHERE same_as <> '[]'::jsonb) AS with_same_as,
       count(*) FILTER (WHERE same_as <> '[]'::jsonb AND NOT has_line) AS epithet_rows,
       string_agg(CASE WHEN fold = 'kaunteya' THEN head || ' = ' ||
                  (SELECT string_agg(x ->> 'head', ', ') FROM jsonb_array_elements(same_as) x) END, '; ') AS kaunteya
FROM corpus.index_persons;

-- A3 (after): the readers' functions keep their grants (signed-in readers only). Expected: false, true, false.
SELECT has_function_privilege('anon', 'public.corpus_reader_index_find(text, text, integer)', 'EXECUTE') AS anon_find,
       has_function_privilege('authenticated', 'public.corpus_reader_index_find(text, text, integer)', 'EXECUTE') AS reader_find,
       has_function_privilege('authenticated', 'public.corpus_index_ingest(text, jsonb)', 'EXECUTE') AS reader_ingest;
