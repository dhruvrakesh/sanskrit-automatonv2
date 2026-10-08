/**
 * corpus-ingest (C4, docs/CORPUS_MIRROR_2026-10-08.md)  CORPUS_MIRROR_C4_2026_10_08
 *
 * The door from the PC's scripts/corpus_sync.py into the PRIVATE corpus mirror (schema
 * "corpus", docs/cloud/C4_corpus_mirror_2026-10-08.sql). Needs C4 applied first.
 *
 * Who may call it: only a request signed with CORPUS_SYNC_SECRET (lib.ts verifyRequest). The
 * gateway's publishable key is needed to reach the function at all, but it is public and is
 * not the boundary. The site, its visitors and its admins never call this function.
 * Body (gzip or JSON): { action: hello | manifest | keys | ingest | retire | run, ... }
 * Each action calls one database function as service_role and returns { ok, result }.
 * Errors: 401 signature, 400 bad request, 413 too large, 422 the database refused (not retried
 * by the client), 500/503 configuration.
 *
 * Secrets used: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (present in every project) and
 * CORPUS_SYNC_SECRET (add it in Lovable Cloud -> Secrets; 64 hex characters; the same value as
 * CORPUS_SYNC_SECRET in the PC's .env). Cost: no AI call; one database call per request.
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import { FN_VERSION, gunzipLimited, logLine, MAX_BODY_BYTES, toCall, verifyRequest } from './lib.ts';

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

serve(async (req) => {
  if (req.method !== 'POST') return json(405, { ok: false, error: 'POST only' });

  const secret = Deno.env.get('CORPUS_SYNC_SECRET') ?? '';
  const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
  if (!secret) return json(503, { ok: false, error: 'CORPUS_SYNC_SECRET is not set in the project secrets' });
  if (!supabaseUrl || !serviceKey) return json(500, { ok: false, error: 'Server is missing Supabase configuration' });

  const declared = Number(req.headers.get('content-length') ?? '0');
  if (declared > MAX_BODY_BYTES) return json(413, { ok: false, error: 'body too large' });
  const raw = new Uint8Array(await req.arrayBuffer());
  if (raw.length > MAX_BODY_BYTES) return json(413, { ok: false, error: 'body too large' });

  const v = await verifyRequest(secret, req.headers.get('x-corpus-ts'), req.headers.get('x-corpus-sig'), raw,
    Math.floor(Date.now() / 1000));
  if (!v.ok) return json(401, { ok: false, error: v.why });

  let payload: unknown;
  try {
    const bytes = req.headers.get('x-corpus-encoding') === 'gzip' ? await gunzipLimited(raw) : raw;
    payload = JSON.parse(new TextDecoder().decode(bytes));
  } catch (e) {
    return json(400, { ok: false, error: 'unreadable body: ' + String((e as Error)?.message ?? e).slice(0, 200) });
  }
  const { call, error } = toCall(payload);
  if (!call) return json(400, { ok: false, error });

  const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const t0 = Date.now();
  const { data, error: dbErr } = await supabase.rpc(call.rpc!, call.args);
  if (dbErr) {
    console.log(logLine(call, Date.now() - t0, 422, null, call.args));
    return json(422, { ok: false, error: `${call.rpc}: ${dbErr.message}`.slice(0, 600) });
  }
  console.log(logLine(call, Date.now() - t0, 200, data, call.args));
  if (call.action === 'hello') {
    const docs = (data as Record<string, Record<string, [number, string]>>)?.docs?.['*'];
    return json(200, { ok: true, result: { fn: FN_VERSION, server_time: new Date().toISOString(), docs_in_mirror: docs ? docs[0] : 0 } });
  }
  return json(200, { ok: true, result: data });
});
