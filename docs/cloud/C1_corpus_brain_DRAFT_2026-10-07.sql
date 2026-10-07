-- ============================================================
-- C1 - corpus brain tables (docs/CLOUD_BRAIN_2026-10-07.md, phase C1)
-- CLOUD_BRAIN_C1_2026_10_07   *** DRAFT FOR REVIEW - NOT APPLIED ***
--
-- Apply ONLY after C0 (docs/cloud/C0_preflight_2026-10-07.sql) shows:
--   P2 halfvec_available = true   (otherwise replace halfvec(768) with vector(768) and
--                                  halfvec_cosine_ops with vector_cosine_ops below)
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
--
-- PURELY ADDITIVE: two new tables, their indexes, RLS, one read-only function.
-- No existing table, policy, function or trigger is changed. Reuses
-- public.srangam_update_updated_at() and public.has_role(uuid, app_role).
--
-- Rollback (fully reversible, nothing else depends on these):
--   DROP FUNCTION public.match_text_passages(halfvec, integer, text[]);
--   DROP TABLE public.srangam_passage_vectors;
--   DROP TABLE public.srangam_stories;
-- ============================================================

-- 1. One vector per published passage, made IN THE CLOUD (phase C2 edge function) from
--    srangam_text_passages.translation, so no vector ever travels through the SQL editor.
CREATE TABLE public.srangam_passage_vectors (
    passage_id  UUID PRIMARY KEY REFERENCES public.srangam_text_passages(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,                 -- e.g. 'gemini-embedding-001'
    dim         INTEGER NOT NULL DEFAULT 768,
    embedding   halfvec(768) NOT NULL,         -- output_dimensionality 768, L2-normalised
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
    query_embedding halfvec(768),
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

-- ============================================================
-- Post-apply verification (one query at a time). Expect every row present = true.
-- V1:
-- SELECT 'table srangam_passage_vectors' AS object, to_regclass('public.srangam_passage_vectors') IS NOT NULL AS present
-- UNION ALL SELECT 'table srangam_stories', to_regclass('public.srangam_stories') IS NOT NULL
-- UNION ALL SELECT 'index hnsw', to_regclass('public.idx_srangam_passage_vectors_hnsw') IS NOT NULL
-- UNION ALL SELECT 'index stories_text', to_regclass('public.idx_srangam_stories_text') IS NOT NULL
-- UNION ALL SELECT 'function match_text_passages', EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'match_text_passages')
-- UNION ALL SELECT 'policy ' || tablename || ': ' || policyname, true FROM pg_policies
--           WHERE schemaname = 'public' AND tablename IN ('srangam_passage_vectors', 'srangam_stories')
-- UNION ALL SELECT 'trigger ' || tgname, true FROM pg_trigger
--           WHERE NOT tgisinternal AND tgrelid IN ('public.srangam_passage_vectors'::regclass, 'public.srangam_stories'::regclass)
-- UNION ALL SELECT 'rls on ' || relname, relrowsecurity FROM pg_class
--           WHERE relnamespace = 'public'::regnamespace AND relname IN ('srangam_passage_vectors', 'srangam_stories');
-- Expect: 2 tables, 2 indexes, 1 function, 4 policies, 2 triggers, RLS on for both (13 rows, all true).
-- V2 (the function answers, even with no vectors yet; expect 0 rows and no error):
-- SELECT * FROM public.match_text_passages(array_fill(0, ARRAY[768])::halfvec(768), 3);
-- ============================================================
