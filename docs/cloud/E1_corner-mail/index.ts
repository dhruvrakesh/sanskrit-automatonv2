/**
 * corner-mail (E1, SPEC C10 + E1 2026-10-09, Part C)  MAIL_E1_2026_10_09
 *
 * Sends the Researchers' Corner's queued emails (corner.outbox, C12) through Resend, from the domain
 * nartiang.org. The database writes every email (From, Reply-to, subject, plain-text body); this
 * function only carries them: corner_mail_claim(limit) claims up to 20, each one is POSTed to
 * https://api.resend.com/emails (10 s each, one start every 0.6 s, no new start after 60 s), and
 * corner_mail_done(id, ok, provider_id, error) records each outcome (Resend's id, or the HTTP status
 * and the first 300 characters of its answer). Both functions are granted to service_role only;
 * the database keeps a failed email for another try (5 in all).
 *   POST, two ways in (the x-corpus-sig header decides: a request that carries one must be signed):
 *     1. The desk (its corner worker, once a round): signed as corpus-desk is, x-corpus-ts (unix
 *        seconds, within 5 minutes) and x-corpus-sig = hex HMAC-SHA256(CORPUS_SYNC_SECRET, ts + "." +
 *        body as sent); x-corpus-encoding: gzip is optional (1 MB as sent, 4 MB unzipped).
 *     2. A signed-in person (the site, after a request is made or an invitation is queued): no
 *        x-corpus-sig, Authorization: Bearer <their JWT>. A client built from SUPABASE_URL,
 *        SUPABASE_ANON_KEY and that header calls corner_me(); only a first row with can_request =
 *        true may go on.
 *     { action: 'flush', limit?: 1..20 (10 by default; other numbers are clamped) }
 *         -> { ok: true, result: { configured: true, claimed, sent, failed } }
 *     { action: 'state' } (the desk only) -> { ok: true, result: { configured, fn } }
 *     RESEND_API_KEY not set: { ok: true, result: { configured: false } }, and nothing is claimed.
 *     Refusals { ok: false, error }: 400 a bad body, 401 not signed / not signed in, 403 not allowed,
 *     413 too large, 422 the database refused, 500 configuration missing, 503 the desk signed but
 *     CORPUS_SYNC_SECRET is not set.
 *   OPTIONS 204; any other method 405.
 * No address, body, token or key reaches an answer or a log line: one JSON line per call, with
 * counts and statuses only.
 * Default verify_jwt stays on (no config.toml entry): the desk sends the project's publishable key
 * as its bearer, as it does for corpus-desk, and a person sends their own JWT.
 * Secrets read: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, CORPUS_SYNC_SECRET (all
 * already in the project) and RESEND_API_KEY (added in the project's secrets; nartiang.org must be
 * a verified domain in Resend). Cost: the invocation, and Resend's price per email.
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import {
  CORS, MAX_BODY_BYTES, type Via, canRequest, gunzipLimited, isBearer, parseBody, route, runFlush, sendOne,
  statusCounts, summarize, verifyRequest,
} from './lib.ts';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });
const text = (status: number, body: string, extra: Record<string, string> = {}) =>
  new Response(body, { status, headers: { ...CORS, 'Content-Type': 'text/plain; charset=utf-8', ...extra } });

function env() {
  return {
    url: Deno.env.get('SUPABASE_URL') ?? '',
    anon: Deno.env.get('SUPABASE_ANON_KEY') ?? '',
    service: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    secret: Deno.env.get('CORPUS_SYNC_SECRET') ?? '',
    resend: Deno.env.get('RESEND_API_KEY') ?? '',
  };
}

function log(o: Record<string, unknown>) {
  console.log(JSON.stringify({ fn: 'corner-mail', ...o }));
}

/** A refusal: logged in one line, answered { ok: false, error }. */
function refuse(status: number, error: string, extra: Record<string, unknown> = {}): Response {
  log({ evt: 'refused', status, error, ...extra });
  return json(status, { ok: false, error });
}

const NO_CLIENT = { auth: { persistSession: false, autoRefreshToken: false } };

async function mail(req: Request): Promise<Response> {
  const e = env();
  if (!e.url || !e.service) return refuse(500, 'Server is missing Supabase configuration');
  const declared = Number(req.headers.get('content-length') ?? '0');
  if (declared > MAX_BODY_BYTES) return refuse(413, 'body too large');
  const raw = new Uint8Array(await req.arrayBuffer());
  if (raw.length > MAX_BODY_BYTES) return refuse(413, 'body too large');

  let via: Via;
  let bytes: Uint8Array = raw;
  const sig = req.headers.get('x-corpus-sig');
  if (sig !== null) {
    if (!e.secret) return refuse(503, 'CORPUS_SYNC_SECRET is not set in the project secrets');
    const v = await verifyRequest(e.secret, req.headers.get('x-corpus-ts'), sig, raw, Math.floor(Date.now() / 1000));
    if (!v.ok) return refuse(401, v.why ?? 'not signed');
    via = 'desk';
    if (req.headers.get('x-corpus-encoding') === 'gzip') {
      try {
        bytes = await gunzipLimited(raw);
      } catch (err) {
        if (/expands past/.test(String((err as Error)?.message ?? err))) return refuse(413, 'body too large once unzipped');
        return refuse(400, 'unreadable body: not gzip');
      }
    }
  } else {
    const authz = req.headers.get('Authorization');
    if (!isBearer(authz)) return refuse(401, 'not signed in');
    if (!e.anon) return refuse(500, 'Server is missing Supabase configuration');
    const user = createClient(e.url, e.anon, { global: { headers: { Authorization: authz } }, ...NO_CLIENT });
    const { data, error } = await user.rpc('corner_me');
    if (error || !canRequest(data)) {
      return refuse(403, 'only a signed-in researcher who may ask the desk can send its mail', {
        via: 'user', code: error ? (error.code ?? 'error') : 'cannot_request',
      });
    }
    via = 'user';
  }

  let payload: unknown;
  try {
    payload = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return refuse(400, 'unreadable body: not JSON', { via });   // the parser's message would quote the body
  }
  const call = parseBody(payload);
  if (typeof call === 'string') return refuse(400, call, { via });
  const step = route(call, via, !!e.resend);
  if ('refuse' in step) return refuse(step.refuse.status, step.refuse.error, { via });
  if ('answer' in step) {
    log({ evt: call.action, via, configured: step.answer.configured === true });
    return json(200, { ok: true, result: step.answer });
  }

  const svc = createClient(e.url, e.service, NO_CLIENT);
  const t0 = Date.now();
  const { data, error } = await svc.rpc('corner_mail_claim', { p_limit: step.flush });
  if (error) {
    log({ evt: 'rpc_failed', via, rpc: 'corner_mail_claim', code: error.code ?? null,
          error: String(error.message).slice(0, 300) });
    return json(422, { ok: false, error: `corner_mail_claim: ${error.message}`.slice(0, 600) });
  }
  const rows: unknown[] = Array.isArray(data) ? data : [];
  const key = e.resend;
  const results = await runFlush(rows, {
    send: (p) => sendOne(p, key, (url, init) => fetch(url, init)),
    done: async (id, ok, providerId, err) => {
      const r = await svc.rpc('corner_mail_done', { p_id: id, p_ok: ok, p_provider_id: providerId, p_error: err });
      return !r.error && r.data === true;
    },
  });
  const sum = summarize(results);
  log({
    evt: 'flush', via, limit: step.flush, ...sum, statuses: statusCounts(results),
    unrecorded: results.filter((r) => !r.recorded).length, ms: Date.now() - t0,
  });
  return json(200, { ok: true, result: { configured: true, ...sum } });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  try {
    if (req.method === 'POST') return await mail(req);
    return text(405, 'POST', { 'Allow': 'POST, OPTIONS' });
  } catch (err) {
    log({ evt: 'unhandled', error: String(err).slice(0, 300) });   // sends and records are caught in runFlush
    return json(500, { ok: false, error: 'unexpected error' });
  }
});
