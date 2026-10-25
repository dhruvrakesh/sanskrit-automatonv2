// corpus-index: the logic, kept free of network imports so it can be tested with plain `deno test` (lib_test.ts).
// C21_INDEX_SITE_2026_10_25 (the automaton's docs/cloud/C21_index_site_2026-10-25.sql, docs/INDEX_SITE_2026-10-25.md).
//
// The door from the PC's scripts/index_sync.py into the indexes' genealogies (corpus.index_*). The same lock as
// corpus-ingest: a request is accepted only when it carries x-corpus-ts (unix seconds, within 5 minutes of the server
// clock) and x-corpus-sig = hex HMAC-SHA256(CORPUS_SYNC_SECRET, ts + "." + body as sent); the body is gzip
// (x-corpus-encoding: gzip) or plain JSON. Each request maps to exactly one of the four C21 service functions, which
// run as service_role here; the service key never leaves Supabase.

export const FN_VERSION = "corpus-index i1 (C21_INDEX_SITE_2026_10_25)";
export const TABLES = ["texts", "persons", "steps", "statements", "lines", "verses", "meta"];
export const MAX_BODY_BYTES = 8 * 1024 * 1024;   // as sent (gzip)
export const MAX_JSON_BYTES = 48 * 1024 * 1024;  // after gunzip
export const MAX_SKEW_S = 300;
export const MAX_ROWS = 2000;
export const MAX_KEYS = 5000;

const enc = new TextEncoder();

export function hexToBytes(hex: string): Uint8Array | null {
  if (!/^[0-9a-f]{64}$/i.test(hex)) return null;
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

export async function signHex(secret: string, ts: string, body: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const data = concat(enc.encode(ts + "."), body);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, data as BufferSource));
  return Array.from(sig, (b) => b.toString(16).padStart(2, "0")).join("");
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
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
  const good = await crypto.subtle.verify("HMAC", key, sig as BufferSource,
    concat(enc.encode(ts + "."), body) as BufferSource);
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

export interface Call {
  action: string;
  rpc?: string;
  args?: Record<string, unknown>;
}

/** Validate the request body and map it to one database function. */
export function toCall(p: unknown): { call?: Call; error?: string } {
  if (!p || typeof p !== "object" || Array.isArray(p)) return { error: "body must be a JSON object" };
  const b = p as Record<string, unknown>;
  const table = b.table;
  const tableOk = () => typeof table === "string" && TABLES.includes(table);
  switch (b.action) {
    case "hello":
    case "manifest":
      return { call: { action: b.action as string, rpc: "corpus_index_manifest", args: {} } };
    case "keys":
      if (!tableOk()) return { error: "unknown table" };
      return { call: { action: "keys", rpc: "corpus_index_keys", args: { p_table: table } } };
    case "ingest":
      if (!tableOk()) return { error: "unknown table" };
      if (!Array.isArray(b.rows) || b.rows.length === 0) return { error: "rows must be a non-empty list" };
      if (b.rows.length > MAX_ROWS) return { error: `at most ${MAX_ROWS} rows per request` };
      return { call: { action: "ingest", rpc: "corpus_index_ingest", args: { p_table: table, p_rows: b.rows } } };
    case "delete":
      if (!tableOk()) return { error: "unknown table" };
      if (!Array.isArray(b.keys) || b.keys.length === 0 || b.keys.some((k) => typeof k !== "string")) {
        return { error: "keys must be a non-empty list of strings" };
      }
      if (b.keys.length > MAX_KEYS) return { error: `at most ${MAX_KEYS} keys per request` };
      return { call: { action: "delete", rpc: "corpus_index_delete", args: { p_table: table, p_keys: b.keys } } };
    default:
      return { error: "unknown action" };
  }
}

/** A one-line log record: what was asked and how much, never the rows. */
export function logLine(call: Call, ms: number, status: number, result: unknown, args?: Record<string, unknown>) {
  const rows = Array.isArray(args?.p_rows) ? (args!.p_rows as unknown[]).length : undefined;
  const keys = Array.isArray(args?.p_keys) ? (args!.p_keys as unknown[]).length : undefined;
  const r = (result && typeof result === "object") ? result as Record<string, unknown> : {};
  return JSON.stringify({ fn: "corpus-index", action: call.action, table: args?.p_table, rows, keys,
    changed: r.changed, deleted: r.deleted, status, ms });
}
