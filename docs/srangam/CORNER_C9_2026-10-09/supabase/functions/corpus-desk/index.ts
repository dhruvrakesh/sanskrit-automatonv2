/**
 * corpus-desk (C9, docs/RESEARCHERS_CORNER_2026-10-09.md)  CORNER_C9_2026_10_09
 *
 * The desk's door to the Researchers' Corner. The desk's corner worker takes the requests that are
 * approved, carries them out on the desk with its own scripts (stories.py, images.py, novel.py,
 * within the desk's spend cap), and reports back here what it did.
 *   POST (signed with CORPUS_SYNC_SECRET like corpus-ingest and corpus-media):
 *     x-corpus-ts (unix seconds, within 5 minutes) and x-corpus-sig = hex HMAC-SHA256(secret,
 *     ts + "." + body as sent); x-corpus-encoding: gzip is optional (at most 4 MB unzipped).
 *     { action: hello | state | pull | report | heartbeat, ... }, each one C9 database function
 *     run as service_role (the four corner_desk_* functions are granted to service_role only):
 *       hello      { fn, state }          the version, and corner_desk_state()
 *       state      corner_desk_state()    queued, running, pending, the desk's last_seen
 *       pull       corner_desk_pull(limit, worker)   claims up to 20 approved requests, oldest first
 *       report     corner_desk_report(id, status, result, message, cost_usd, log)
 *       heartbeat  corner_desk_heartbeat(info)       the daily cap, today's commitment, the queue
 *     Answers { ok: true, result } or { ok: false, error }: 400 a bad body, 401 not signed,
 *     413 too large, 422 the database refused, 503 the secret is not set.
 *   OPTIONS 204; any other method 405.
 * POST from the desk only: no user's JWT is ever read. The desk sends the project's publishable key
 * as its bearer, as it does for corpus-ingest, so the default settings need no config.toml entry; the
 * signature is the gate. Secrets used, all already in the project: SUPABASE_URL,
 * SUPABASE_SERVICE_ROLE_KEY, CORPUS_SYNC_SECRET (as corpus-ingest and corpus-media). No AI call;
 * no cost per call but the function invocation.
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import { CORS, FN_VERSION, MAX_BODY_BYTES, gunzipLimited, toDeskCall, verifyRequest } from './lib.ts';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });
const text = (status: number, body: string, extra: Record<string, string> = {}) =>
  new Response(body, { status, headers: { ...CORS, 'Content-Type': 'text/plain; charset=utf-8', ...extra } });

function env() {
  return {
    url: Deno.env.get('SUPABASE_URL') ?? '',
    service: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    secret: Deno.env.get('CORPUS_SYNC_SECRET') ?? '',
  };
}

function log(o: Record<string, unknown>) {
  console.log(JSON.stringify({ fn: 'corpus-desk', ...o }));
}

/** A refusal before any database call: logged in one line, answered { ok: false, error }. */
function refuse(status: number, error: string): Response {
  log({ evt: 'refused', status, error });
  return json(status, { ok: false, error });
}

async function desk(req: Request): Promise<Response> {
  const e = env();
  if (!e.secret) return refuse(503, 'CORPUS_SYNC_SECRET is not set in the project secrets');
  if (!e.url || !e.service) return refuse(500, 'Server is missing Supabase configuration');
  const declared = Number(req.headers.get('content-length') ?? '0');
  if (declared > MAX_BODY_BYTES) return refuse(413, 'body too large');
  const raw = new Uint8Array(await req.arrayBuffer());
  if (raw.length > MAX_BODY_BYTES) return refuse(413, 'body too large');
  const v = await verifyRequest(e.secret, req.headers.get('x-corpus-ts'), req.headers.get('x-corpus-sig'), raw,
    Math.floor(Date.now() / 1000));
  if (!v.ok) return refuse(401, v.why ?? 'not signed');

  let bytes: Uint8Array = raw;
  if (req.headers.get('x-corpus-encoding') === 'gzip') {
    try {
      bytes = await gunzipLimited(raw);
    } catch (err) {
      const msg = String((err as Error)?.message ?? err).slice(0, 200);
      if (/expands past/.test(msg)) return refuse(413, 'body too large once unzipped');
      return refuse(400, 'unreadable body: ' + msg);
    }
  }
  let payload: unknown;
  try {
    payload = JSON.parse(new TextDecoder().decode(bytes));
  } catch (err) {
    return refuse(400, 'unreadable body: ' + String((err as Error)?.message ?? err).slice(0, 200));
  }
  const { call, error } = toDeskCall(payload);
  if (!call) return refuse(400, error ?? 'bad request');

  const svc = createClient(e.url, e.service, { auth: { persistSession: false, autoRefreshToken: false } });
  const rpc = call.rpc ?? 'corner_desk_state';   // hello answers with the state too
  const t0 = Date.now();
  const { data, error: dbErr } = await svc.rpc(rpc, call.args ?? {});
  const ms = Date.now() - t0;
  if (dbErr) {
    log({ evt: 'rpc_failed', action: call.action, rpc, ms, error: String(dbErr.message).slice(0, 300) });
    return json(422, { ok: false, error: `${rpc}: ${dbErr.message}`.slice(0, 600) });
  }
  const a = call.args ?? {};
  log({
    evt: 'rpc', action: call.action, rpc, ms,
    ...(call.action === 'pull' ? { worker: a.p_worker, claimed: Array.isArray(data) ? data.length : null } : {}),
    ...(call.action === 'report' ? { id: a.p_id, status: a.p_status, recorded: data === true } : {}),
  });
  return json(200, { ok: true, result: call.action === 'hello' ? { fn: FN_VERSION, state: data } : data });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  try {
    if (req.method === 'POST') return await desk(req);
    return text(405, 'POST', { 'Allow': 'POST, OPTIONS' });
  } catch (err) {
    log({ evt: 'unhandled', error: String(err).slice(0, 300) });
    return json(500, { ok: false, error: 'unexpected error' });
  }
});
