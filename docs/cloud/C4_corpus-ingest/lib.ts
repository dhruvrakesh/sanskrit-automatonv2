// C4 - corpus-ingest: the logic, kept free of network imports so it can be tested with plain
// `deno test` (lib_test.ts). CORPUS_MIRROR_C4_2026_10_08. Design: docs/CORPUS_MIRROR_2026-10-08.md.
//
// The function is the only door from the PC into the private corpus mirror (schema "corpus").
// A request is accepted only when it carries x-corpus-ts (unix seconds, within 5 minutes of the
// server clock) and x-corpus-sig = hex HMAC-SHA256(CORPUS_SYNC_SECRET, ts + "." + body as sent).
// The body is gzip (x-corpus-encoding: gzip) or plain JSON. Each request maps to exactly one of
// the five C4 database functions, which run as service_role here; the service key never leaves
// Supabase and the PC holds only the shared secret, which can write to the mirror and nothing else.

export const FN_VERSION = "corpus-ingest c4.1 (CORPUS_MIRROR_C4_2026_10_08)";
export const TABLES = ["docs", "entities", "passages", "translations", "mentions", "stories", "stages", "vectors"];
export const MAX_BODY_BYTES = 8 * 1024 * 1024;   // as sent (gzip)
export const MAX_JSON_BYTES = 48 * 1024 * 1024;  // after gunzip
export const MAX_SKEW_S = 300;
export const MAX_ROWS = 2000;
export const MAX_KEYS = 5000;

const enc = new TextEncoder();
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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

const isStr = (v: unknown, max = 300): v is string => typeof v === "string" && v.length > 0 && v.length <= max;

/** Validate the request body and map it to one database function. */
export function toCall(p: unknown): { call?: Call; error?: string } {
  if (!p || typeof p !== "object" || Array.isArray(p)) return { error: "body must be a JSON object" };
  const b = p as Record<string, unknown>;
  const action = b.action;
  const table = b.table;
  const runOk = (v: unknown) => v === undefined || v === null || (typeof v === "string" && UUID_RE.test(v));
  const tableOk = () => isStr(table, 40) && TABLES.includes(table as string);
  switch (action) {
    case "hello":
      return { call: { action, rpc: "corpus_manifest", args: { p_tables: ["docs"] } } };
    case "manifest": {
      const t = b.tables ?? TABLES;
      if (!Array.isArray(t) || t.length === 0 || t.some((x) => !TABLES.includes(x as string))) {
        return { error: "tables must be a list of: " + TABLES.join(", ") };
      }
      return { call: { action, rpc: "corpus_manifest", args: { p_tables: t } } };
    }
    case "keys":
      if (!tableOk()) return { error: "unknown table" };
      if (!isStr(b.group)) return { error: "group is required" };
      return { call: { action, rpc: "corpus_keys", args: { p_table: table, p_group: b.group } } };
    case "ingest":
      if (!tableOk()) return { error: "unknown table" };
      if (!Array.isArray(b.rows) || b.rows.length === 0) return { error: "rows must be a non-empty list" };
      if (b.rows.length > MAX_ROWS) return { error: `at most ${MAX_ROWS} rows per request` };
      if (!runOk(b.run_id)) return { error: "run_id must be a uuid" };
      return { call: { action, rpc: "corpus_ingest", args: { p_table: table, p_rows: b.rows, p_run: b.run_id ?? null } } };
    case "retire":
      if (!tableOk()) return { error: "unknown table" };
      if (!isStr(b.group)) return { error: "group is required" };
      if (!Array.isArray(b.keys) || b.keys.length === 0 || b.keys.some((k) => typeof k !== "string")) {
        return { error: "keys must be a non-empty list of strings" };
      }
      if (b.keys.length > MAX_KEYS) return { error: `at most ${MAX_KEYS} keys per request` };
      if (!runOk(b.run_id)) return { error: "run_id must be a uuid" };
      return {
        call: { action, rpc: "corpus_retire", args: { p_table: table, p_group: b.group, p_keys: b.keys, p_run: b.run_id ?? null } },
      };
    case "run":
      if (typeof b.run_id !== "string" || !UUID_RE.test(b.run_id)) return { error: "run_id must be a uuid" };
      return {
        call: { action, rpc: "corpus_run", args: { p_run: b.run_id, p_info: b.info ?? null, p_finish: b.finish === true } },
      };
    default:
      return { error: "unknown action" };
  }
}

/** A one-line log record: what was asked and how much, never the rows. */
export function logLine(call: Call, ms: number, status: number, result: unknown, args?: Record<string, unknown>) {
  const rows = Array.isArray(args?.p_rows) ? (args!.p_rows as unknown[]).length : undefined;
  const keys = Array.isArray(args?.p_keys) ? (args!.p_keys as unknown[]).length : undefined;
  const r = (result && typeof result === "object") ? result as Record<string, unknown> : {};
  return JSON.stringify({
    fn: "corpus-ingest", action: call.action, table: args?.p_table, group: args?.p_group, rows, keys,
    changed: r.changed, retired: r.retired, status, ms,
  });
}
