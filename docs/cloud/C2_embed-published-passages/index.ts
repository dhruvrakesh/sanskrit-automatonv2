/**
 * embed-published-passages (C2, docs/CLOUD_BRAIN_2026-10-07.md)  EMBED_PUBLISHED_C2_2026_10_07
 *
 * Makes the cloud half of the Sanskrit brain: one 1536-dimension vector per passage of every
 * PUBLISHED text (srangam_texts.published = true), stored in srangam_passage_vectors, so that
 * match_text_passages() can answer questions over /texts. Needs C1 applied first.
 *
 * Who may call it (as every cost-bearing function here, _shared/auth-gate.ts):
 *   - pg_cron / the SQL editor through public._cron_invoke_edge('embed-published-passages', '{...}')
 *     (x-cron-secret + body._cron), or
 *   - a signed-in admin.
 * Body (all optional): { limit: 1-1000 (200), batch: 1-100 (50), doc_code: text, dry_run: bool }
 * Returns JSON: pending_before, taken, embedded, pending_after_estimate, stopped, failures.
 *
 * Cost: the local ledger measured 56 passages at $0.0015 with this model (2026-10-05), so the
 * 1,655 passages published on 2026-10-07 are about $0.05. Secrets used: SUPABASE_URL,
 * SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY (already used by _shared/ai-provider.ts).
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import { requireAdminOrCron } from '../_shared/auth-gate.ts';
import { clampInt, embedBatchGemini, runEmbedding, type QueueRow, type VectorRow } from './lib.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-cron-secret',
};

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  const body = (await req.clone().json().catch(() => ({}))) as Record<string, unknown>;
  const gate = await requireAdminOrCron(req, body);
  if (gate.error) return gate.error;

  const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
  const geminiKey = Deno.env.get('GEMINI_API_KEY') ?? '';
  if (!supabaseUrl || !serviceKey) return json(500, { error: 'Server is missing Supabase configuration' });
  if (!geminiKey) return json(500, { error: 'GEMINI_API_KEY is not set in the project secrets' });

  const limit = clampInt(body.limit, 1, 1000, 200);
  const batch = clampInt(body.batch, 1, 100, 50);
  const docCode = typeof body.doc_code === 'string' && body.doc_code.trim() ? body.doc_code.trim() : null;
  const dryRun = body.dry_run === true;

  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  try {
    const result = await runEmbedding({
      fetchQueue: async (n) => {
        const { data, error } = await supabase.rpc('srangam_passages_to_embed', { p_limit: n, p_doc_code: docCode });
        if (error) throw new Error(`srangam_passages_to_embed: ${error.message} (is C1 applied?)`);
        return (data ?? []) as QueueRow[];
      },
      embed: (texts) => embedBatchGemini(fetch, geminiKey, texts),
      upsert: async (rows: VectorRow[]) => {
        const { error } = await supabase.from('srangam_passage_vectors').upsert(rows, { onConflict: 'passage_id' });
        if (error) throw new Error(`upsert srangam_passage_vectors: ${error.message}`);
      },
      limit,
      batch,
      dryRun,
      deadline: Date.now() + 100_000, // _cron_invoke_edge waits 120 s; leave room to answer
    });
    console.log(JSON.stringify({ fn: 'embed-published-passages', from_cron: !!gate.fromCron, doc_code: docCode, ...result, sample: undefined }));
    return json(result.stopped === 'failure' ? 502 : 200, { ...result, doc_code: docCode });
  } catch (e) {
    return json(500, { error: String((e as Error)?.message ?? e).slice(0, 500) });
  }
});
