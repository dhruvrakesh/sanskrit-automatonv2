-- ============================================================
-- C1 - corpus brain tables (docs/CLOUD_BRAIN_2026-10-07.md, phase C1)
-- CLOUD_BRAIN_C1_2026_10_07   READY TO APPLY (C0 passed 2026-10-07 15:07: vector 0.8.0, halfvec,
--                             C1 objects absent, B1 and its helpers present)
-- Supersedes C1_corpus_brain_DRAFT_2026-10-07.sql. Added since the draft (C2_PREP_2026_10_07):
--   5. srangam_passages_to_embed() - what the C2 edge function still has to embed;
--   6. explicit REVOKE / GRANT on both functions. Supabase's default privileges give anon and
--      authenticated EXECUTE on every new function by name (S3 lesson, 2026-10-07), so each grant
--      here is spelled out: match_text_passages is public on purpose (SECURITY INVOKER, RLS
--      limits it to published texts); srangam_passages_to_embed is service role only.
--   7. 1536 dimensions, not 768 (RECALL_768_2026_10_07, measured on the local 3,072-dim vectors of
--      21,645 passages, 300 sampled): the first 768 keep 0.893 of each passage's 12 nearest
--      neighbours (0.875 of 5); the first 1536 keep 0.956 (0.948). The plan's bar was 0.90 at k=12, so
--      1536 it is. halfvec(1536) is 3 KB a vector: about 5 MB for today's 1,655 published passages.
--
-- Apply ONLY after C0 (docs/cloud/C0_preflight_2026-10-07.sql) shows:
--   P2 halfvec_available = true   (it is; vector(1536) would also index, as 1536 <= 2000)
--   P3 all false, P4 fn_updated_at = true and fn_has_role = true.
-- Paste the whole file into the Lovable Cloud SQL editor, run it once, then run the
-- verification block at the end (one query at a time) and count objects one by one -
-- "Query succeeded" is not evidence (B1 lesson, docs/CURRENT_STATUS.md 2026-09-08).
-- The SQL-editor path records no row in supabase_migrations.schema_migrations; do NOT
-- hand-insert one. Keep this file's content as the repo migration when Lovable applies it.
--
-- Tested 2026-10-07 on PostgreSQL 16 + pgvector 0.8.0, on top of the B1 migration
-- (20260718120000) with stand-ins for has_role / srangam_update_updated_at / auth.uid():
-- applies cleanly; V1 13 of 13 present; V2 answers; an anonymous caller sees vectors and
-- stories of published texts only (an unpublished story and an unpublished text stay
-- hidden) and cannot write. Not tested against the live database: run C0 first.
-- Re-tested 2026-10-07 (this version) on PostgreSQL 16 + pgvector 0.8.0 with Supabase-like default
-- privileges: V1 14 of 14; V3 as expected; srangam_passages_to_embed returns only published,
-- non-empty passages, drops one once its vector is stored with the same hash, returns it again
-- after its translation changes, and refuses anon ("permission denied for function").
--
-- PURELY ADDITIVE: two new tables, their indexes, RLS, two read-only functions.
-- No existing table, policy, function or trigger is changed. Reuses
-- public.srangam_update_updated_at() and public.has_role(uuid, app_role).
--
-- Rollback (fully reversible, nothing else depends on these):
--   DROP FUNCTION public.srangam_passages_to_embed(integer, text);
--   DROP FUNCTION public.match_text_passages(halfvec, integer, text[]);
--   DROP TABLE public.srangam_passage_vectors;
--   DROP TABLE public.srangam_stories;
-- ============================================================

-- 1. One vector per published passage, made IN THE CLOUD (phase C2 edge function) from
--    srangam_text_passages.translation, so no vector ever travels through the SQL editor.
CREATE TABLE public.srangam_passage_vectors (
    passage_id  UUID PRIMARY KEY REFERENCES public.srangam_text_passages(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,                 -- e.g. 'gemini-embedding-001'
    dim         INTEGER NOT NULL DEFAULT 1536,
    embedding   halfvec(1536) NOT NULL,        -- output_dimensionality 1536, L2-normalised (RECALL_768)
    source_hash TEXT NOT NULL,                 -- md5(translation) it was made from: re-embed when it changes
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_srangam_passage_vectors_hnsw
    ON public.srangam_passage_vectors USING hnsw (embedding halfvec_cosine_ops);

-- 2. Approved stories (and their approved versions for younger readers), pushed with the
--    same --emit-sql bridge as the passages. story_key = the automaton's doc_stories.id.
CREATE TABLE public.srangam_stories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_key   INTEGER NOT NULL,
    audience    TEXT NOT NULL DEFAULT 'general' CHECK (audience IN ('general', 'young', 'teen')),
    text_id     UUID NOT NULL REFERENCES public.srangam_texts(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    title_hi    TEXT,
    story_en    TEXT NOT NULL,
    story_hi    TEXT,
    quote_sa    TEXT,
    quote_ref   TEXT,
    notes       TEXT,
    from_ref    TEXT NOT NULL,                 -- 'page.idx'
    to_ref      TEXT NOT NULL,
    cites       JSONB NOT NULL DEFAULT '[]'::jsonb,
    image_url   TEXT,                          -- a picture shipped with the site (public/corpus-images/...)
    approved_at TIMESTAMPTZ,
    published   BOOLEAN NOT NULL DEFAULT FALSE,  -- flipped by an admin AFTER review, like srangam_texts
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT srangam_stories_unique UNIQUE (story_key, audience)   -- publisher upsert key
);
CREATE INDEX idx_srangam_stories_text ON public.srangam_stories(text_id, published);

CREATE TRIGGER update_srangam_passage_vectors_updated_at
    BEFORE UPDATE ON public.srangam_passage_vectors
    FOR EACH ROW EXECUTE FUNCTION public.srangam_update_updated_at();
CREATE TRIGGER update_srangam_stories_updated_at
    BEFORE UPDATE ON public.srangam_stories
    FOR EACH ROW EXECUTE FUNCTION public.srangam_update_updated_at();

-- 3. RLS: the public reads only what belongs to a published text; admins manage; the
--    C2/C3 edge functions write with the service role (it bypasses RLS by design).
ALTER TABLE public.srangam_passage_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.srangam_stories         ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read vectors of published texts"
    ON public.srangam_passage_vectors FOR SELECT TO public
    USING (EXISTS (SELECT 1 FROM public.srangam_text_passages p
                   JOIN public.srangam_texts t ON t.id = p.text_id
                   WHERE p.id = passage_id AND t.published = TRUE));
CREATE POLICY "Admin manage vectors"
    ON public.srangam_passage_vectors FOR ALL TO authenticated
    USING (public.has_role(auth.uid(), 'admin'))
    WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Public read published stories of published texts"
    ON public.srangam_stories FOR SELECT TO public
    USING (published = TRUE AND EXISTS (SELECT 1 FROM public.srangam_texts t
                                        WHERE t.id = text_id AND t.published = TRUE));
CREATE POLICY "Admin manage stories"
    ON public.srangam_stories FOR ALL TO authenticated
    USING (public.has_role(auth.uid(), 'admin'))
    WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- 4. Nearest passages to a question vector. SECURITY INVOKER: the caller's RLS applies, so
--    an anonymous caller only ever reaches published texts.
CREATE OR REPLACE FUNCTION public.match_text_passages(
    query_embedding halfvec(1536),
    match_count     INTEGER DEFAULT 12,
    doc_codes       TEXT[]  DEFAULT NULL)
RETURNS TABLE (passage_id UUID, doc_code TEXT, page_no INTEGER, idx INTEGER, verse_ref TEXT,
               translation TEXT, similarity DOUBLE PRECISION)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public
AS $$
    SELECT p.id, t.doc_code, p.page_no, p.idx, p.verse_ref, p.translation,
           1 - (v.embedding <=> query_embedding) AS similarity
    FROM public.srangam_passage_vectors v
    JOIN public.srangam_text_passages p ON p.id = v.passage_id
    JOIN public.srangam_texts t ON t.id = p.text_id
    WHERE t.published = TRUE AND (doc_codes IS NULL OR t.doc_code = ANY (doc_codes))
    ORDER BY v.embedding <=> query_embedding
    LIMIT LEAST(GREATEST(match_count, 1), 50);
$$;

-- 5. What the C2 edge function still has to embed: passages of published texts with no vector yet,
--    or whose text changed since (source_hash). The text embedded is the one the local brain uses
--    (build_embeddings.py): "<iast> -- <translation>" when there is IAST, else the translation.
--    total_pending counts every such passage, before the LIMIT.
CREATE OR REPLACE FUNCTION public.srangam_passages_to_embed(
    p_limit    INTEGER DEFAULT 200,
    p_doc_code TEXT    DEFAULT NULL)
RETURNS TABLE (passage_id UUID, doc_code TEXT, content TEXT, source_hash TEXT, total_pending BIGINT)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public
AS $$
    WITH c AS (
        SELECT p.id, t.doc_code, p.page_no, p.idx,
               CASE WHEN btrim(COALESCE(p.iast, '')) <> ''
                    THEN btrim(p.iast) || ' ' || chr(8212) || ' ' || btrim(p.translation)
                    ELSE btrim(p.translation) END AS content
        FROM public.srangam_text_passages p
        JOIN public.srangam_texts t ON t.id = p.text_id
        WHERE t.published = TRUE AND btrim(p.translation) <> ''
          AND (p_doc_code IS NULL OR t.doc_code = p_doc_code)
    ), todo AS (
        SELECT c.*, md5(c.content) AS h
        FROM c LEFT JOIN public.srangam_passage_vectors v ON v.passage_id = c.id
        WHERE v.passage_id IS NULL OR v.source_hash <> md5(c.content)
    )
    SELECT todo.id, todo.doc_code, todo.content, todo.h, count(*) OVER ()
    FROM todo
    ORDER BY todo.doc_code, todo.page_no, todo.idx
    LIMIT LEAST(GREATEST(p_limit, 1), 1000);
$$;

-- 6. Who may call what (spelled out; see the header).
REVOKE EXECUTE ON FUNCTION public.srangam_passages_to_embed(integer, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.srangam_passages_to_embed(integer, text) TO service_role;
GRANT  EXECUTE ON FUNCTION public.match_text_passages(halfvec, integer, text[]) TO anon, authenticated, service_role;

-- ============================================================
-- Post-apply verification (one query at a time). Expect every row present = true.
-- V1:
-- SELECT 'table srangam_passage_vectors' AS object, to_regclass('public.srangam_passage_vectors') IS NOT NULL AS present
-- UNION ALL SELECT 'table srangam_stories', to_regclass('public.srangam_stories') IS NOT NULL
-- UNION ALL SELECT 'index hnsw', to_regclass('public.idx_srangam_passage_vectors_hnsw') IS NOT NULL
-- UNION ALL SELECT 'index stories_text', to_regclass('public.idx_srangam_stories_text') IS NOT NULL
-- UNION ALL SELECT 'function match_text_passages', EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'match_text_passages')
-- UNION ALL SELECT 'function srangam_passages_to_embed', EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'srangam_passages_to_embed')
-- UNION ALL SELECT 'policy ' || tablename || ': ' || policyname, true FROM pg_policies
--           WHERE schemaname = 'public' AND tablename IN ('srangam_passage_vectors', 'srangam_stories')
-- UNION ALL SELECT 'trigger ' || tgname, true FROM pg_trigger
--           WHERE NOT tgisinternal AND tgrelid IN ('public.srangam_passage_vectors'::regclass, 'public.srangam_stories'::regclass)
-- UNION ALL SELECT 'rls on ' || relname, relrowsecurity FROM pg_class
--           WHERE relnamespace = 'public'::regnamespace AND relname IN ('srangam_passage_vectors', 'srangam_stories');
-- Expect: 2 tables, 2 indexes, 2 functions, 4 policies, 2 triggers, RLS on for both (14 rows, all true).
-- V2 (the function answers, even with no vectors yet; expect 0 rows and no error):
-- SELECT * FROM public.match_text_passages(array_fill(0, ARRAY[1536])::halfvec(1536), 3);
-- V3 (who may call the functions; expect match_text_passages true/true/true and
--     srangam_passages_to_embed false/false/true):
-- SELECT p.oid::regprocedure AS function,
--        has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
--        has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_role
-- FROM pg_proc p WHERE p.proname IN ('match_text_passages', 'srangam_passages_to_embed') ORDER BY 1;
-- V4 (what C2 will embed; expect total_pending = the published passages, 1,655 on 2026-10-07):
-- SELECT doc_code, count(*) AS rows_returned, max(total_pending) AS total_pending
-- FROM public.srangam_passages_to_embed(1000) GROUP BY doc_code;
-- ============================================================
