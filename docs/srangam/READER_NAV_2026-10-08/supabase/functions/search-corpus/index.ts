/**
 * search-corpus (C5, docs/CORPUS_MIRROR_2026-10-08.md "Reading it")  CORPUS_READER_C5_2026_10_08
 *
 * Signed-in readers: search the WHOLE working corpus (the private mirror, schema corpus) by meaning.
 *   POST { q: "why did the king sell his wife", k?: 1-20 (8), doc_codes?: ["markandeya_purana"] }
 *   with the reader's session (supabase.functions.invoke sends it when the reader is signed in)
 *   -> { q, results: [{ doc_code, title, page_no, idx, verse_ref, ord, similarity, snippet }], took_ms }
 *
 * - Every database call runs AS THE READER (publishable key + the reader's JWT), so the database
 *   decides who may read: corpus_reader_allowed() / corpus_reader_match() (C5). This function holds
 *   no privilege of its own and never uses the service role.
 * - The question is embedded exactly as search-texts does (gemini-embedding-001, 1536 dimensions,
 *   RETRIEVAL_QUERY; a verbatim copy of the search-texts helpers in ./embed.ts). The mirror's vectors are the local ones cut to 1536
 *   dimensions; on 2026-10-08 they matched the site's cloud-made vectors at cosine 1.0000 over
 *   1,216 passages (M4), so questions and passages share one space. About $0.000003 a question.
 * - No text is generated: the reader sees passages and references.
 * - Brakes: 3-300 characters, k <= 20, 20 questions a minute per reader per instance, a small cache.
 * Secrets: SUPABASE_URL, SUPABASE_ANON_KEY, GEMINI_API_KEY (already present for search-texts).
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
// READER_NAV_2026_10_08: its own copy (embed.ts); Lovable deploys a function's own folder only.
import { embedQuery, parseInput, RateLimiter, toHalfvecLiteral, VectorCache } from './embed.ts';
import { isRefusal, readerToken, shapeHits } from './lib.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const limiter = new RateLimiter(20, 60_000);
const cache = new VectorCache(200);
const REFUSED = 'The working corpus is open to signed-in readers only.';

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });
  if (req.method !== 'POST') return json(405, { error: 'Use POST.' });
  const t0 = Date.now();

  const url = Deno.env.get('SUPABASE_URL') ?? '';
  const anon = Deno.env.get('SUPABASE_ANON_KEY') ?? '';
  const key = Deno.env.get('GEMINI_API_KEY') ?? '';
  if (!url || !anon || !key) return json(500, { error: 'Search is not configured.' });

  const token = readerToken(req.headers.get('Authorization'), anon);
  if (!token) return json(401, { error: REFUSED });

  const input = parseInput(await req.json().catch(() => ({})));
  if ('error' in input) return json(400, { error: input.error });

  const sb = createClient(url, anon, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: who, error: whoErr } = await sb.auth.getUser(token);
  if (whoErr || !who?.user) return json(401, { error: REFUSED });
  if (!limiter.allow(who.user.id)) return json(429, { error: 'Too many searches in a minute. Please wait a little.' });

  const { data: allowed, error: aErr } = await sb.rpc('corpus_reader_allowed');
  if (aErr && !isRefusal(aErr)) return json(502, { error: 'Search failed.', detail: aErr.message });
  if (allowed !== true) return json(403, { error: REFUSED });

  try {
    let vec = cache.get(input.q);
    if (!vec) { vec = await embedQuery(fetch, key, input.q); cache.set(input.q, vec); }
    const { data, error } = await sb.rpc('corpus_reader_match', {
      query_embedding: toHalfvecLiteral(vec), k: input.k, doc_codes: input.docCodes,
    });
    if (error) return isRefusal(error) ? json(403, { error: REFUSED }) : json(502, { error: 'Search failed.', detail: error.message });
    return json(200, { q: input.q, results: shapeHits(data), took_ms: Date.now() - t0 });
  } catch (e) {
    console.error(JSON.stringify({ fn: 'search-corpus', error: String((e as Error)?.message ?? e).slice(0, 300) }));
    return json(502, { error: 'Search is unavailable just now.' });
  }
});
