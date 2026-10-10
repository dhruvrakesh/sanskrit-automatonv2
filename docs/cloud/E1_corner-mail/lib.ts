// E1 - corner-mail: the logic, kept free of network imports so it can be tested with plain
// `deno test` (lib_test.ts). MAIL_E1_2026_10_09. Contract: SPEC C10 + E1 (2026-10-09), Part C;
// database: docs/cloud/C12_corner_mail_2026-10-09.sql (corner_mail_claim, corner_mail_done).
//
// One door, POST, two ways in: the desk (signed exactly as corpus-desk is, with CORPUS_SYNC_SECRET)
// or a signed-in person whom corner_me() lets ask the desk (can_request). Actions: flush (send up to
// 20 queued emails through Resend) and state (the desk only: is Resend configured here?).
// The database composes every email; this file only checks the call, shapes Resend's JSON body,
// sends one email with a timeout, and paces a round. Nothing here logs, and no outcome carries an
// address, a body or the key: a send's outcome is its HTTP status, Resend's id, and an error text
// that goes to corner_mail_done only.
// The verify, gunzip and CORS code is a copy of corpus-desk's lib.ts (a function cannot import
// another's folder). Its golden test is the same.

export const FN_VERSION = "corner-mail 1.0";
export const MAX_BODY_BYTES = 1 * 1024 * 1024;   // as sent
export const MAX_JSON_BYTES = 4 * 1024 * 1024;   // after gunzip
export const MAX_SKEW_S = 300;

export const LIMIT_DEFAULT = 10;
export const LIMIT_MAX = 20;                     // corner_mail_claim claims at most 20
export const RESEND_URL = "https://api.resend.com/emails";
export const SEND_TIMEOUT_MS = 10_000;           // each email
export const SEND_GAP_MS = 600;                  // between two sends: under Resend's default 2 a second
export const FLUSH_BUDGET_MS = 60_000;           // no new send starts after this; the rest go back
export const ERROR_TEXT_CHARS = 300;             // of Resend's answer kept with a failure
export const ERROR_MAX_CHARS = 320;              // the whole error text, status included

const enc = new TextEncoder();

export function hexToBytes(hex: string): Uint8Array | null {
  if (!/^[0-9a-f]{64}$/i.test(hex)) return null;
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}

export async function signHex(secret: string, ts: string, body: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, concat(enc.encode(ts + "."), body) as BufferSource));
  return Array.from(sig, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Constant-time check (crypto.subtle.verify) of the signature, and of the clock. */
export async function verifyRequest(
  secret: string, ts: string | null, sigHex: string | null, body: Uint8Array, nowS: number,
): Promise<{ ok: boolean; why?: string }> {
  if (!secret || secret.length < 32) return { ok: false, why: "server secret missing or too short" };
  if (!ts || !/^\d{9,11}$/.test(ts)) return { ok: false, why: "missing or malformed x-corpus-ts" };
  if (Math.abs(nowS - Number(ts)) > MAX_SKEW_S) return { ok: false, why: "x-corpus-ts is more than 5 minutes off" };
  const sig = hexToBytes(sigHex ?? "");
  if (!sig) return { ok: false, why: "missing or malformed x-corpus-sig" };
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const good = await crypto.subtle.verify("HMAC", key, sig as BufferSource, concat(enc.encode(ts + "."), body) as BufferSource);
  return good ? { ok: true } : { ok: false, why: "bad signature" };
}

/** gunzip with a ceiling, so a small compressed body cannot expand without bound. */
export async function gunzipLimited(body: Uint8Array, limit = MAX_JSON_BYTES): Promise<Uint8Array> {
  const stream = new Blob([body as BlobPart]).stream().pipeThrough(new DecompressionStream("gzip"));
  const reader = stream.getReader();
  const parts: Uint8Array[] = [];
  let n = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    n += value.length;
    if (n > limit) {
      await reader.cancel();
      throw new Error(`body expands past ${limit} bytes`);
    }
    parts.push(value);
  }
  const out = new Uint8Array(n);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

// ---- the call --------------------------------------------------------------------------------

export type MailAction = "flush" | "state";
export interface MailCall { action: MailAction; limit: number }
export type Via = "desk" | "user";

/**
 * { action: 'flush', limit?: number } or { action: 'state' }; other fields are ignored. A limit
 * that is absent or null is 10; any other number is cut to a whole number and clamped to 1..20
 * (corner_mail_claim clamps the same way). Anything else is refused with a sentence.
 */
export function parseBody(p: unknown): MailCall | string {
  if (!isObj(p)) return "body must be a JSON object";
  if (p.action === "state") return { action: "state", limit: LIMIT_DEFAULT };
  if (p.action !== "flush") return "unknown action";
  const limit = p.limit;
  if (limit === undefined || limit === null) return { action: "flush", limit: LIMIT_DEFAULT };
  if (typeof limit !== "number" || !Number.isFinite(limit)) return "limit: a number from 1 to 20";
  return { action: "flush", limit: Math.min(LIMIT_MAX, Math.max(1, Math.trunc(limit))) };
}

export type Step =
  | { refuse: { status: number; error: string } }
  | { answer: Record<string, unknown> }
  | { flush: number };

/**
 * What a checked call does. 'state' is the desk's only; it says whether RESEND_API_KEY is set.
 * Without the key a flush answers { configured: false } and claims nothing (a claimed email would
 * only wait 10 minutes for its next try).
 */
export function route(call: MailCall, via: Via, configured: boolean): Step {
  if (call.action === "state") {
    if (via !== "desk") return { refuse: { status: 403, error: "state: for the desk only" } };
    return { answer: { configured, fn: FN_VERSION } };
  }
  if (!configured) return { answer: { configured: false } };
  return { flush: call.limit };
}

/** "Bearer <token>", as a signed-in person's request carries it. */
export function isBearer(h: string | null): h is string {
  return typeof h === "string" && /^bearer\s+\S+$/i.test(h.trim());
}

/** corner_me() answers a table; the caller may flush only when its first row has can_request true. */
export function canRequest(data: unknown): boolean {
  const row = Array.isArray(data) ? data[0] : null;
  return isObj(row) && row.can_request === true;
}

// ---- one email -------------------------------------------------------------------------------

/** A row of corner_mail_claim(p_limit). */
export interface MailRow {
  id: number;
  to_email: string;
  mail_from: string;
  reply_to?: string | null;
  subject: string;
  body: string;
}

export interface ResendPayload {
  from: string;
  to: string[];
  subject: string;
  text: string;
  reply_to?: string;
}

/** Resend's JSON body for one row: plain text; reply_to only when the row has one. */
export function resendPayload(row: MailRow): ResendPayload {
  const out: ResendPayload = { from: row.mail_from, to: [row.to_email], subject: row.subject, text: row.body };
  const replyTo = typeof row.reply_to === "string" ? row.reply_to.trim() : "";
  if (replyTo) out.reply_to = replyTo;
  return out;
}

/** The longest start of s, in whole characters (a surrogate pair is never split), of at most n UTF-16 units. */
function cut(s: string, n: number): string {
  if (s.length <= n) return s;
  let out = "";
  for (const ch of s) {
    if (out.length + ch.length > n) break;
    out += ch;
  }
  return out;
}

/**
 * The error kept with a failed send: the HTTP status (or timeout, network, deferred), then the first
 * 300 characters of the answer on one line; control characters (NUL included, which Postgres text
 * refuses) become spaces. At most 320 characters in all.
 */
export function errorText(status: number | string, text: unknown): string {
  // deno-lint-ignore no-control-regex
  const t = cut(String(text ?? "").replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim(), ERROR_TEXT_CHARS);
  return cut(t ? `${status}: ${t}` : String(status), ERROR_MAX_CHARS);
}

export interface SendOutcome {
  ok: boolean;
  status: number | string;
  providerId: string | null;
  error: string | null;
}

type FetchFn = (url: string, init: RequestInit) => Promise<Response>;

/**
 * POST one email to Resend, aborted after timeoutMs. Any 2xx is sent (Resend's id when its answer
 * has one); a 2xx whose body cannot be read is still sent, so it is not sent twice. Never throws.
 */
export async function sendOne(
  payload: ResendPayload, apiKey: string, fetchFn: FetchFn, timeoutMs = SEND_TIMEOUT_MS,
): Promise<SendOutcome> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetchFn(RESEND_URL, {
      method: "POST",
      headers: { "Authorization": `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: ctl.signal,
    });
    let text = "";
    try { text = await res.text(); } catch { /* the status is what counts */ }
    if (res.ok) {
      let id: string | null = null;
      try {
        const j = JSON.parse(text);
        if (isObj(j) && typeof j.id === "string" && j.id) id = j.id;
      } catch { /* sent, without an id */ }
      return { ok: true, status: res.status, providerId: id, error: null };
    }
    return { ok: false, status: res.status, providerId: null, error: errorText(res.status, text) };
  } catch (err) {
    if (ctl.signal.aborted) {
      return { ok: false, status: "timeout", providerId: null,
               error: errorText("timeout", `no answer from Resend within ${timeoutMs / 1000} s`) };
    }
    return { ok: false, status: "network", providerId: null, error: errorText("network", (err as Error)?.message ?? err) };
  } finally {
    clearTimeout(timer);
  }
}

// ---- a round ---------------------------------------------------------------------------------

export interface FlushDeps {
  send: (payload: ResendPayload) => Promise<SendOutcome>;
  /** corner_mail_done(id, ok, provider_id, error): true when the database recorded it. */
  done: (id: number, ok: boolean, providerId: string | null, error: string | null) => Promise<boolean>;
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
  gapMs?: number;
  budgetMs?: number;
}

export interface FlushItem { ok: boolean; status: number | string; recorded: boolean }

/**
 * Send the claimed rows one after another, at least gapMs apart, and record each outcome. Once
 * budgetMs has passed no new send starts: the rest are recorded as not sent ("deferred"), which
 * hands them back at once for the next round. A row without a usable id cannot be recorded and is
 * not sent (it comes back after its 10-minute claim).
 */
export async function runFlush(rows: unknown[], deps: FlushDeps): Promise<FlushItem[]> {
  const now = deps.now ?? Date.now;
  const sleep = deps.sleep ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
  const gap = deps.gapMs ?? SEND_GAP_MS;
  const budget = deps.budgetMs ?? FLUSH_BUDGET_MS;
  const t0 = now();
  let lastStart = -Infinity;
  const out: FlushItem[] = [];
  for (const row of rows) {
    if (!isObj(row) || !Number.isSafeInteger(row.id) || (row.id as number) < 1) {
      out.push({ ok: false, status: "bad row", recorded: false });
      continue;
    }
    const r = row as unknown as MailRow;
    let o: SendOutcome;
    if (now() - t0 >= budget) {
      o = { ok: false, status: "deferred", providerId: null,
            error: errorText("deferred", "not sent: out of time in this round") };
    } else {
      const wait = lastStart + gap - now();
      if (wait > 0) await sleep(wait);
      lastStart = now();
      try {
        o = await deps.send(resendPayload(r));
      } catch (err) {
        o = { ok: false, status: "network", providerId: null, error: errorText("network", (err as Error)?.message ?? err) };
      }
    }
    let recorded = false;
    try {
      recorded = await deps.done(r.id, o.ok, o.ok ? o.providerId : null, o.ok ? null : o.error);
    } catch {
      recorded = false;
    }
    out.push({ ok: o.ok, status: o.status, recorded });
  }
  return out;
}

/** The answer's counts. */
export function summarize(results: { ok: boolean }[]): { claimed: number; sent: number; failed: number } {
  const sent = results.filter((r) => r.ok).length;
  return { claimed: results.length, sent, failed: results.length - sent };
}

/** How many of each status, for the log line ({"200": 3, "422": 1}). */
export function statusCounts(results: { status: number | string }[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of results) out[String(r.status)] = (out[String(r.status)] ?? 0) + 1;
  return out;
}

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
