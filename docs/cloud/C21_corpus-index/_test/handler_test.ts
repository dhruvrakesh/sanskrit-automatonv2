// The corpus-index handler end to end with the database and the gateway faked.
// Run from docs/cloud/C21_corpus-index:
//   deno test --no-remote --allow-env --import-map=_test/import_map.json _test/handler_test.ts
// C21_INDEX_SITE_2026_10_25
import { handler } from "./server_stub.ts";
import { FN_VERSION, MAX_BODY_BYTES, signHex } from "../lib.ts";
import "../index.ts";   // registers its handler with the stand-in serve(); it reads the environment per request

const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const URL_ = "https://p.supabase.co/functions/v1/corpus-index";
const enc = new TextEncoder();
function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

type Call = { fn: string; args: unknown; key: string };
type Answer = { data: unknown; error: { message: string; code?: string } | null };
let rpcLog: Call[] = [];
let rpcAnswers: Record<string, Answer> = {};
const g = globalThis as unknown as { __rpc: unknown; __clients: { url: string; key: string; opts?: unknown }[] };
g.__clients = [];
g.__rpc = (fn: string, args: unknown, key: string) => {
  rpcLog.push({ fn, args, key });
  return rpcAnswers[fn] ?? { data: null, error: null };
};
function setEnv() {
  Deno.env.set("SUPABASE_URL", "https://p.supabase.co");
  Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key");
  Deno.env.set("CORPUS_SYNC_SECRET", SECRET);
}
function reset() { rpcLog = []; rpcAnswers = {}; g.__clients.length = 0; setEnv(); }
const realLog = console.log;
const logged: string[] = [];
console.log = (...a: unknown[]) => { logged.push(a.map(String).join(" ")); };

async function gzip(bytes: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(await new Response(new Blob([bytes as BlobPart]).stream()
    .pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
}
async function send(raw: Uint8Array, headers: Record<string, string> = {}, signed = true, skewS = 0) {
  const ts = String(Math.floor(Date.now() / 1000) + skewS);
  const sig: Record<string, string> = signed ? { "x-corpus-ts": ts, "x-corpus-sig": await signHex(SECRET, ts, raw) } : {};
  return handler!(new Request(URL_, { method: "POST", body: raw as BodyInit, headers: { ...sig, ...headers } }));
}
const post = (body: unknown, headers: Record<string, string> = {}) => send(enc.encode(JSON.stringify(body)), headers);
async function answer(res: Response) { return { status: res.status, body: await res.json() }; }

Deno.test("anything but POST is 405", async () => {
  reset();
  for (const method of ["GET", "PUT", "DELETE"]) {
    const r = await handler!(new Request(URL_, { method }));
    eq(r.status, 405, method);
  }
  eq(rpcLog.length, 0);
});

Deno.test("unsigned, wrongly signed or stale: 401 with the reason; no client, no database", async () => {
  reset();
  const raw = enc.encode('{"action":"hello"}');
  eq(await answer(await send(raw, {}, false)), { status: 401, body: { ok: false, error: "missing or malformed x-corpus-ts" } });
  eq((await answer(await send(raw, { "x-corpus-sig": "0".repeat(64) }))).body.error, "bad signature");
  eq((await answer(await send(raw, {}, true, -301))).body.error, "x-corpus-ts is more than 5 minutes off");
  const ts = String(Math.floor(Date.now() / 1000));
  const other = await signHex(SECRET, ts, enc.encode('{"action":"manifest"}'));
  eq((await answer(await send(raw, { "x-corpus-ts": ts, "x-corpus-sig": other }, false))).body.error, "bad signature");
  Deno.env.set("CORPUS_SYNC_SECRET", "too-short");
  eq((await answer(await post({ action: "hello" }))).body.error, "server secret missing or too short");
  eq(rpcLog.length, 0);
  eq(g.__clients.length, 0, "no client is made before the signature holds");
});

Deno.test("configuration missing: 503 for the secret, 500 for Supabase's own", async () => {
  reset();
  Deno.env.delete("CORPUS_SYNC_SECRET");
  eq((await answer(await post({ action: "hello" }))).status, 503);
  setEnv();
  Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY");
  eq((await answer(await post({ action: "hello" }))).status, 500);
  eq(rpcLog.length, 0);
});

Deno.test("too large: 413 before the signature is even read", async () => {
  reset();
  const big = new Uint8Array(MAX_BODY_BYTES + 1);
  const r = await handler!(new Request(URL_, { method: "POST", body: big as BodyInit }));
  eq(r.status, 413);
  eq(rpcLog.length, 0);
});

Deno.test("hello: the manifest is read as service_role and the answer names the function and the persons", async () => {
  reset();
  rpcAnswers.corpus_index_manifest = { data: { persons: { n: 9373, digest: "d" }, steps: { n: 1, digest: "e" } }, error: null };
  const a = await answer(await post({ action: "hello" }));
  eq(a.status, 200);
  eq(a.body.result.fn, FN_VERSION);
  eq(a.body.result.persons, 9373);
  ok(typeof a.body.result.server_time === "string");
  eq(rpcLog, [{ fn: "corpus_index_manifest", args: {}, key: "service-key" }]);
  eq(g.__clients[0].key, "service-key");
});

Deno.test("manifest, keys, ingest (gzip) and delete pass through exactly one call each", async () => {
  reset();
  rpcAnswers.corpus_index_manifest = { data: { persons: { n: 2, digest: "x" } }, error: null };
  rpcAnswers.corpus_index_keys = { data: { "pe:1": "h" }, error: null };
  rpcAnswers.corpus_index_ingest = { data: { rows: 1, changed: 1 }, error: null };
  rpcAnswers.corpus_index_delete = { data: { deleted: 1 }, error: null };
  eq((await answer(await post({ action: "manifest" }))).body, { ok: true, result: { persons: { n: 2, digest: "x" } } });
  eq((await answer(await post({ action: "keys", table: "persons" }))).body.result, { "pe:1": "h" });
  const rows = [{ key: "pe:1", head: "जनमेजय", row_hash: "h" }];
  const gz = await gzip(enc.encode(JSON.stringify({ action: "ingest", table: "persons", rows })));
  eq((await answer(await send(gz, { "x-corpus-encoding": "gzip" }))).body.result, { rows: 1, changed: 1 });
  eq((await answer(await post({ action: "delete", table: "steps", keys: ["pe:1:2"] }))).body.result, { deleted: 1 });
  eq(rpcLog.map((c) => c.fn), ["corpus_index_manifest", "corpus_index_keys", "corpus_index_ingest", "corpus_index_delete"]);
  eq(rpcLog[2].args, { p_table: "persons", p_rows: rows });
  eq(rpcLog[3].args, { p_table: "steps", p_keys: ["pe:1:2"] });
  ok(!logged.join("\n").includes("जन"), "rows never reach the log");
});

Deno.test("bad body: 400; the database refusing: 422 with its message", async () => {
  reset();
  eq((await answer(await send(enc.encode("not json")))).status, 400);
  eq((await answer(await send(enc.encode("{}"), { "x-corpus-encoding": "gzip" }))).status, 400);
  eq((await answer(await post({ action: "keys", table: "passages" }))).body, { ok: false, error: "unknown table" });
  eq(rpcLog.length, 0);
  rpcAnswers.corpus_index_ingest = { data: null, error: { message: "at most 2000 rows per call" } };
  const a = await answer(await post({ action: "ingest", table: "persons", rows: [{ key: "k" }] }));
  eq(a, { status: 422, body: { ok: false, error: "corpus_index_ingest: at most 2000 rows per call" } });
  console.log = realLog;
});
