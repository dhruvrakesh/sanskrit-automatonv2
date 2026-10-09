// C9 - corpus-desk: the logic, kept free of network imports so it can be tested with plain
// `deno test` (lib_test.ts). CORNER_C9_2026_10_09. Design: docs/RESEARCHERS_CORNER_2026-10-09.md;
// database: docs/cloud/C9_researchers_corner_2026-10-09.sql.
//
// One door, POST, from the desk's corner worker: signed exactly as corpus-ingest and corpus-media
// are, with x-corpus-ts (unix seconds, within 5 minutes) and x-corpus-sig = hex HMAC-SHA256(
// CORPUS_SYNC_SECRET, ts + "." + body as sent). Actions: hello, state, pull, report, heartbeat.
// Each maps to one C9 desk function run as service_role (hello reads corner_desk_state too).
// The checks here refuse what those functions would otherwise drop or cut without a word: a report's
// result, message, cost or log out of range, a heartbeat's info too long. Lengths of JSON are
// measured as Postgres measures jsonb::text (", " and ": " between items), which is what the
// functions compare with their limits.
// The verify code is a copy of corpus-ingest's lib.ts, as corpus-media's is (a function cannot
// import another's folder). Its golden test is the same.

export const FN_VERSION = "corpus-desk c9.1 (CORNER_C9_2026_10_09)";
export const MAX_BODY_BYTES = 1 * 1024 * 1024;   // as sent
export const MAX_JSON_BYTES = 4 * 1024 * 1024;   // after gunzip
export const MAX_SKEW_S = 300;

export const PULL_DEFAULT = 3;
export const PULL_MAX = 20;                      // corner_desk_pull takes at most 20
export const WORKER_RE = /^[A-Za-z0-9 ._:@-]{1,100}$/;
export const REPORT_STATUSES = ["running", "done", "failed"] as const;
export const MAX_RESULT_CHARS = 20000;           // corner_desk_report keeps a result up to this
export const MAX_MESSAGE_CHARS = 2000;           // ... a message cut to this
export const MAX_LOG_CHARS = 8000;               // ... a log tail cut to this
export const MAX_COST_USD = 100;                 // ... a cost from 0 up to (not including) this
export const MAX_INFO_CHARS = 4000;              // corner_desk_heartbeat keeps info up to this

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

/**
 * The length of a parsed JSON value as Postgres prints it from jsonb (length(p::text)): JSON with
 * ", " between items and ": " after keys; strings escaped as JSON.stringify escapes them. The
 * compact length is a lower bound, so anything already past `limit` compact is not walked.
 */
export function jsonbTextLength(v: unknown, limit = Infinity): number {
  let compact: string | undefined;
  try { compact = JSON.stringify(v); } catch { return Infinity; }
  if (compact === undefined) return Infinity;
  if (compact.length > limit) return compact.length;
  const walk = (x: unknown): number => {
    if (Array.isArray(x)) {
      let n = 2 + 2 * Math.max(0, x.length - 1);
      for (const y of x) n += walk(y);
      return n;
    }
    if (isObj(x)) {
      const keys = Object.keys(x);
      let n = 2 + 2 * Math.max(0, keys.length - 1);
      for (const k of keys) n += JSON.stringify(k).length + 2 + walk(x[k]);
      return n;
    }
    return (JSON.stringify(x) ?? "null").length;
  };
  return walk(v);
}

export type DeskAction = "hello" | "state" | "pull" | "report" | "heartbeat";

export interface DeskCall {
  action: DeskAction;
  rpc?: string;
  args?: Record<string, unknown>;
}

const absent = (v: unknown) => v === undefined || v === null;

/** Validate a desk request and map it to one C9 function (hello is answered by the caller). */
export function toDeskCall(p: unknown): { call?: DeskCall; error?: string } {
  if (!isObj(p)) return { error: "body must be a JSON object" };
  switch (p.action) {
    case "hello":
      return { call: { action: "hello" } };
    case "state":
      return { call: { action: "state", rpc: "corner_desk_state", args: {} } };
    case "pull": {
      const limit = absent(p.limit) ? PULL_DEFAULT : p.limit;
      if (!Number.isInteger(limit) || (limit as number) < 1 || (limit as number) > PULL_MAX) {
        return { error: "limit: a whole number from 1 to 20" };
      }
      if (typeof p.worker !== "string" || !WORKER_RE.test(p.worker)) {
        return { error: "worker: 1 to 100 characters, letters, digits, spaces and . _ : @ -" };
      }
      return { call: { action: "pull", rpc: "corner_desk_pull", args: { p_limit: limit, p_worker: p.worker } } };
    }
    case "report": {
      const id = p.id;
      if (!Number.isSafeInteger(id) || (id as number) < 1) return { error: "id: a positive whole number" };
      const status = p.status;
      if (typeof status !== "string" || !(REPORT_STATUSES as readonly string[]).includes(status)) {
        return { error: "status: running, done or failed" };
      }
      const result = p.result ?? null;
      if (result !== null && (!isObj(result) || jsonbTextLength(result, MAX_RESULT_CHARS) > MAX_RESULT_CHARS)) {
        return { error: "result: a JSON object of at most 20000 characters, or null" };
      }
      const message = p.message ?? null;
      if (message !== null && (typeof message !== "string" || message.length > MAX_MESSAGE_CHARS)) {
        return { error: "message: text of at most 2000 characters, or null" };
      }
      const cost = p.cost_usd ?? null;
      if (cost !== null && (typeof cost !== "number" || !Number.isFinite(cost) || cost < 0 || cost >= MAX_COST_USD)) {
        return { error: "cost_usd: a number of dollars from 0 to under 100, or null" };
      }
      const log = p.log ?? null;
      if (log !== null && (typeof log !== "string" || log.length > MAX_LOG_CHARS)) {
        return { error: "log: text of at most 8000 characters, or null" };
      }
      return {
        call: {
          action: "report", rpc: "corner_desk_report",
          args: { p_id: id, p_status: status, p_result: result, p_message: message, p_cost: cost, p_log: log },
        },
      };
    }
    case "heartbeat": {
      const info = p.info;
      if (!isObj(info) || jsonbTextLength(info, MAX_INFO_CHARS) > MAX_INFO_CHARS) {
        return { error: "info: a JSON object of at most 4000 characters" };
      }
      return { call: { action: "heartbeat", rpc: "corner_desk_heartbeat", args: { p_info: info } } };
    }
    default:
      return { error: "unknown action" };
  }
}

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
