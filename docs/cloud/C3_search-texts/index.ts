/**
 * search-texts (C3a, docs/CLOUD_BRAIN_2026-10-07.md)  SEARCH_TEXTS_C3A_2026_10_07
 *
 * Public: search the PUBLISHED Sanskrit texts (/texts) by meaning.
 *   POST { q: "why did Hariscandra sell his wife", k?: 1-20 (8), doc_codes?: ["markandeya_purana"] }
 *   -> { q, results: [{ doc_code, title, ref, page_no, idx, verse_ref, translation, similarity, ordinal }], took_ms }
 *      ordinal = the passage's position in its text in the reader's order, for a link to the right page.
 *
 * - The question is embedded as RETRIEVAL_QUERY with gemini-embedding-001 at 1536 dimensions
 *   (the size C2 stored, RECALL_768_2026_10_07). About $0.000003 a question.
 * - match_text_passages() is called with the ANON key, so row-level security decides what is
 *   visible: published texts only, exactly what /texts shows.
 * - No text is generated: the reader sees the passages and their references, nothing invented.
 * - Brakes: questions of 3-300 characters, k <= 20, 20 requests a minute per client per
 *   instance, and a small cache so a repeated question is not embedded twice.
 * Secrets: SUPABASE_URL, SUPABASE_ANON_KEY, GEMINI_API_KEY (all already present for other functions).
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import { embedQuery, type MatchRow, parseInput, RateLimiter, shapeResults, toHalfvecLiteral, VectorCache } from './lib.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const limiter = new RateLimiter(20, 60_000);
const cache = new VectorCache(200);

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });
  if (req.method !== 'POST') return json(405, { error: 'Use POST.' });
  const t0 = Date.now();

  const client = (req.headers.get('x-forwarded-for') ?? '').split(',')[0].trim() || 'unknown';
  if (!limiter.allow(client)) return json(429, { error: 'Too many searches in a minute. Please wait a little.' });

  const input = parseInput(await req.json().catch(() => ({})));
  if ('error' in input) return json(400, { error: input.error });

  const url = Deno.env.get('SUPABASE_URL') ?? '';
  const anon = Deno.env.get('SUPABASE_ANON_KEY') ?? '';
  const key = Deno.env.get('GEMINI_API_KEY') ?? '';
  if (!url || !anon || !key) return json(500, { error: 'Search is not configured.' });

  try {
    let vec = cache.get(input.q);
    if (!vec) { vec = await embedQuery(fetch, key, input.q); cache.set(input.q, vec); }

    const sb = createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data, error } = await sb.rpc('match_text_passages', {
      query_embedding: toHalfvecLiteral(vec), match_count: input.k, doc_codes: input.docCodes,
    });
    if (error) return json(502, { error: 'Search failed.', detail: error.message });
    const rows = (data ?? []) as MatchRow[];

    const codes = [...new Set(rows.map((r) => r.doc_code))];
    const titles: Record<string, string> = {};
    const textIds: Record<string, string> = {};
    if (codes.length) {
      const { data: t } = await sb.from('srangam_texts').select('id, doc_code, title').in('doc_code', codes).limit(50);
      for (const r of (t ?? []) as { id: string; doc_code: string; title: string }[]) {
        titles[r.doc_code] = r.title; textIds[r.doc_code] = r.id;
      }
    }
    // Where each passage sits in its text, in the reader's own order (page_no, idx), so the page can
    // link to the right page of /texts/:docCode. One count per hit (k <= 20), in parallel.
    const ordinals = await Promise.all(rows.map(async (r) => {
      const id = textIds[r.doc_code];
      if (!id) return null;
      const { count, error: cErr } = await sb.from('srangam_text_passages')
        .select('id', { count: 'exact', head: true })
        .eq('text_id', id)
        .or(`page_no.lt.${r.page_no},and(page_no.eq.${r.page_no},idx.lt.${r.idx})`);
      return cErr || count === null ? null : count + 1;
    }));
    const results = shapeResults(rows, titles).map((h, i) => ({ ...h, ordinal: ordinals[i] }));
    return json(200, { q: input.q, results, took_ms: Date.now() - t0 });
  } catch (e) {
    console.error(JSON.stringify({ fn: 'search-texts', error: String((e as Error)?.message ?? e).slice(0, 300) }));
    return json(502, { error: 'Search is unavailable just now.' });
  }
});
