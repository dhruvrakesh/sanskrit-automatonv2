-- MATCH_NULL_GUARD_2026_10_07 - match_text_passages returns nothing for a missing question vector
--
-- Why: on 2026-10-07 the C2 check R5 asked for the neighbours of Markandeya 60.10 before that
-- passage had a vector (the queue runs AphorismsOfSandilya first). The sub-select gave NULL, and
-- match_text_passages answered with six arbitrary Sandilya passages whose similarity was NULL:
-- "1 - (embedding <=> NULL)" is NULL, and ORDER BY NULL keeps no order. It looked like a result.
-- With this guard a NULL question vector gives zero rows, which is the honest answer.
--
-- Not STRICT on purpose: STRICT would return nothing whenever ANY argument is NULL, and doc_codes
-- is NULL by default (search-texts and /texts send it NULL), so every search would go empty.
--
-- CREATE OR REPLACE with the same signature and return type keeps the owner and the grants
-- (anon, authenticated, service_role EXECUTE stay as C1 set them). Only the WHERE line changes.
-- Tested 2026-10-07 on PostgreSQL 16 + pgvector 0.8.0: before, a NULL vector gave 6 rows with
-- NULL similarity; after, 0 rows; a real vector still returns itself first at 1.000; proacl
-- identical before and after; doc_codes still filters; at 4,058 vectors the plan (auto_explain) is
-- the same as C1's apart from a one-time "$1 IS NOT NULL" filter. (At these sizes both versions
-- sort every vector exactly instead of walking the HNSW index: exact, and fast at this scale.)
--
-- Run in the Lovable Cloud SQL editor: G1 first, then G2 and G3 one at a time.
-- Rollback: re-run section 4 of docs/cloud/C1_corpus_brain_2026-10-07.sql (the WHERE line without
-- "query_embedding IS NOT NULL AND").

-- G1. Replace the function (one statement).
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
    WHERE query_embedding IS NOT NULL
      AND t.published = TRUE AND (doc_codes IS NULL OR t.doc_code = ANY (doc_codes))
    ORDER BY v.embedding <=> query_embedding
    LIMIT LEAST(GREATEST(match_count, 1), 50);
$$;

-- G2. Grants unchanged (read-only). Expect "=X/postgres" (PUBLIC; PostgreSQL's default for a new
--     function, which C1 left in place because this function is public on purpose and RLS decides
--     what it returns) plus postgres, anon, authenticated and service_role with X.
--     Live result 2026-10-07 17:46 IST: {=X/postgres,postgres=X/postgres,anon=X/postgres,
--     authenticated=X/postgres,service_role=X/postgres}, security_definer false; G3 rows = 0.
SELECT p.oid::regprocedure AS fn, p.proacl, p.prosecdef AS security_definer
FROM pg_proc p WHERE p.proname = 'match_text_passages';

-- G3. A NULL question now returns nothing (read-only). Expect rows = 0.
SELECT count(*) AS rows FROM public.match_text_passages(NULL::halfvec(1536), 6);
