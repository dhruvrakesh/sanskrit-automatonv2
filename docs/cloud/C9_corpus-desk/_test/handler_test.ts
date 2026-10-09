// The corpus-desk handler end to end with the database and the gateway faked.
// Run from supabase/functions/corpus-desk with this folder copied to _test/:
//   deno test --no-remote --allow-env --import-map=_test/import_map.json _test/handler_test.ts
// CORNER_C9_2026_10_09
import { handler } from "./server_stub.ts";
import { FN_VERSION, MAX_BODY_BYTES, MAX_JSON_BYTES, signHex } from "../lib.ts";
import "../index.ts";   // registers its handler with the stand-in serve(); it reads the environment per request

const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const URL_ = "https://p.supabase.co/functions/v1/corpus-desk";
const enc = new TextEncoder();
function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

type Call = { fn: string; args: unknown; key: string; auth: string | null };
type Answer = { data: unknown; error: { message: string; code?: string } | null };
let rpcLog: Call[] = [];
let rpcAnswers: Record<string, Answer> = {};
const g = globalThis as unknown as { __rpc: unknown; __clients: { url: string; key: string; opts?: unknown }[] };
g.__clients = [];
g.__rpc = (fn: string, args: unknown, key: string, auth: string | null) => {
  rpcLog.push({ fn, args, key, auth });
  return rpcAnswers[fn] ?? { data: null, error: null };
};

function setEnv() {
  Deno.env.set("SUPABASE_URL", "https://p.supabase.co");
  Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key");
  Deno.env.set("CORPUS_SYNC_SECRET", SECRET);
}
setEnv();

function reset() { rpcLog = []; rpcAnswers = {}; g.__clients.length = 0; setEnv(); }

async function gzip(bytes: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(await new Response(new Blob([bytes as BlobPart]).stream()
    .pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
}
/** POST raw bytes, signed over exactly those bytes (unless signed is false). */
async function send(raw: Uint8Array, headers: Record<string, string> = {}, signed = true, skewS = 0) {
  const ts = String(Math.floor(Date.now() / 1000) + skewS);
  const sig: Record<string, string> = signed ? { "x-corpus-ts": ts, "x-corpus-sig": await signHex(SECRET, ts, raw) } : {};
  return handler!(new Request(URL_, { method: "POST", body: raw as BodyInit, headers: { ...sig, ...headers } }));
}
const post = (body: unknown, headers: Record<string, string> = {}) => send(enc.encode(JSON.stringify(body)), headers);
async function answer(res: Response) { return { status: res.status, body: await res.json() }; }

Deno.test("OPTIONS 204 with CORS; anything but POST is 405 POST", async () => {
  reset();
  const o = await handler!(new Request(URL_, { method: "OPTIONS" }));
  eq(o.status, 204);
  eq(o.headers.get("Access-Control-Allow-Methods"), "POST, OPTIONS");
  eq(o.headers.get("Access-Control-Allow-Origin"), "*");
  for (const method of ["GET", "PUT", "DELETE", "PATCH"]) {
    const r = await handler!(new Request(URL_, { method }));
    eq([r.status, await r.text()], [405, "POST"], method);
    eq(r.headers.get("Allow"), "POST, OPTIONS");
  }
  eq(rpcLog.length, 0);
});

Deno.test("unsigned, wrongly signed or stale: 401 with the reason; the database is not asked", async () => {
  reset();
  const raw = enc.encode('{"action":"state"}');
  eq(await answer(await send(raw, {}, false)), { status: 401, body: { ok: false, error: "missing or malformed x-corpus-ts" } });
  eq((await answer(await send(raw, { "x-corpus-sig": "0".repeat(64) }))).body.error, "bad signature");
  eq((await answer(await send(raw, {}, true, -301))).body.error, "x-corpus-ts is more than 5 minutes off");
  eq((await answer(await send(raw, {}, true, 400))).status, 401);
  // signed over other bytes than those sent
  const ts = String(Math.floor(Date.now() / 1000));
  const other = await signHex(SECRET, ts, enc.encode('{"action":"hello"}'));
  eq((await answer(await send(raw, { "x-corpus-ts": ts, "x-corpus-sig": other }, false))).body.error, "bad signature");
  Deno.env.set("CORPUS_SYNC_SECRET", "too-short");
  eq((await answer(await post({ action: "state" }))).body.error, "server secret missing or too short");
  eq(rpcLog.length, 0);
  eq(g.__clients.length, 0, "no client is made before the signature holds");
});

Deno.test("no secret 503; no Supabase configuration 500", async () => {
  reset();
  Deno.env.delete("CORPUS_SYNC_SECRET");
  eq(await answer(await post({ action: "hello" })),
    { status: 503, body: { ok: false, error: "CORPUS_SYNC_SECRET is not set in the project secrets" } });
  setEnv();
  Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY");
  eq(await answer(await post({ action: "hello" })),
    { status: 500, body: { ok: false, error: "Server is missing Supabase configuration" } });
  setEnv();
  Deno.env.delete("SUPABASE_URL");
  eq((await post({ action: "hello" })).status, 500);
  eq(rpcLog.length, 0);
});

Deno.test("too large: 413, declared, sent, or once unzipped", async () => {
  reset();
  const declared = await send(enc.encode('{"action":"state"}'), { "content-length": String(MAX_BODY_BYTES + 1) });
  eq(await answer(declared), { status: 413, body: { ok: false, error: "body too large" } });
  const big = new Uint8Array(MAX_BODY_BYTES + 1).fill(32);
  eq(await answer(await send(big)), { status: 413, body: { ok: false, error: "body too large" } });
  eq((await send(big, {}, false)).status, 413, "the size is checked before the signature");
  const bomb = await gzip(new Uint8Array(MAX_JSON_BYTES + 1).fill(32));
  ok(bomb.length < MAX_BODY_BYTES);
  eq(await answer(await send(bomb, { "x-corpus-encoding": "gzip" })),
    { status: 413, body: { ok: false, error: "body too large once unzipped" } });
  eq(rpcLog.length, 0);
});

Deno.test("unreadable or wrong bodies: 400 with the reason", async () => {
  reset();
  const bad = await answer(await send(enc.encode("{not json")));
  eq(bad.status, 400);
  ok(String(bad.body.error).startsWith("unreadable body: "), bad.body.error);
  eq((await answer(await send(enc.encode('{"action":"state"}'), { "x-corpus-encoding": "gzip" }))).status, 400,
    "said gzip, was not");
  eq(await answer(await post([1, 2])), { status: 400, body: { ok: false, error: "body must be a JSON object" } });
  eq(await answer(await post({ action: "delete" })), { status: 400, body: { ok: false, error: "unknown action" } });
  eq((await answer(await post({ action: "pull", worker: "desk;drop" }))).body.error,
    "worker: 1 to 100 characters, letters, digits, spaces and . _ : @ -");
  eq((await answer(await post({ action: "report", id: "5", status: "done" }))).body.error, "id: a positive whole number");
  eq((await answer(await post({ action: "report", id: 5, status: "claimed" }))).body.error, "status: running, done or failed");
  eq((await answer(await post({ action: "heartbeat", info: [1] }))).body.error,
    "info: a JSON object of at most 4000 characters");
  eq(rpcLog.length, 0);
});

Deno.test("hello: the version and corner_desk_state(), as service_role, no user JWT", async () => {
  reset();
  const state = { scheme: "corner.1", queued: 2, running: 0, pending: 1, last_seen: null };
  rpcAnswers.corner_desk_state = { data: state, error: null };
  const h = await answer(await post({ action: "hello" }, { Authorization: "Bearer some-user-jwt" }));
  eq(h, { status: 200, body: { ok: true, result: { fn: FN_VERSION, state } } });
  eq(rpcLog, [{ fn: "corner_desk_state", args: {}, key: "service-key", auth: null }]);
  eq(g.__clients, [{ url: "https://p.supabase.co", key: "service-key",
                     opts: { auth: { persistSession: false, autoRefreshToken: false } } }]);
});

Deno.test("state, pull, report, heartbeat: the right function with the right arguments", async () => {
  reset();
  rpcAnswers.corner_desk_state = { data: { scheme: "corner.1", queued: 0 }, error: null };
  eq(await answer(await post({ action: "state" })), { status: 200, body: { ok: true, result: { scheme: "corner.1", queued: 0 } } });
  eq(rpcLog.at(-1), { fn: "corner_desk_state", args: {}, key: "service-key", auth: null });

  const claimed = [{ id: 5, kind: "story_range", doc_code: "VR", params: { from: "18.2", to: "18.9" }, est_usd: 0.01,
                     attempts: 1, requested_at: "2026-10-09T05:00:00+00:00" }];
  rpcAnswers.corner_desk_pull = { data: claimed, error: null };
  eq(await answer(await post({ action: "pull", worker: "desk-pc" })), { status: 200, body: { ok: true, result: claimed } });
  eq(rpcLog.at(-1)!.fn, "corner_desk_pull");
  eq(rpcLog.at(-1)!.args, { p_limit: 3, p_worker: "desk-pc" });
  await post({ action: "pull", limit: 20, worker: "desk-pc:corner_worker@1" });
  eq(rpcLog.at(-1)!.args, { p_limit: 20, p_worker: "desk-pc:corner_worker@1" });

  rpcAnswers.corner_desk_report = { data: true, error: null };
  const rep = { action: "report", id: 5, status: "done", result: { story_id: 31 }, message: "a draft story",
                cost_usd: 0.0087, log: "stories.py --range ... ok" };
  eq(await answer(await post(rep)), { status: 200, body: { ok: true, result: true } });
  eq(rpcLog.at(-1), { fn: "corner_desk_report",
    args: { p_id: 5, p_status: "done", p_result: { story_id: 31 }, p_message: "a draft story", p_cost: 0.0087,
            p_log: "stories.py --range ... ok" }, key: "service-key", auth: null });
  rpcAnswers.corner_desk_report = { data: false, error: null };
  eq(await answer(await post({ action: "report", id: 6, status: "running" })),
    { status: 200, body: { ok: true, result: false } }, "not the desk's to report: false, not an error");
  eq(rpcLog.at(-1)!.args, { p_id: 6, p_status: "running", p_result: null, p_message: null, p_cost: null, p_log: null });

  const beat = { scheme: "corner.1", daily_cap_usd: 2, committed_today: 0.12, queued: 1 };
  rpcAnswers.corner_desk_heartbeat = { data: beat, error: null };
  const info = { host: "desk-pc", worker: "corner_worker 1.0", budget_left_usd: 3.4 };
  eq(await answer(await post({ action: "heartbeat", info })), { status: 200, body: { ok: true, result: beat } });
  eq(rpcLog.at(-1)!.args, { p_info: info });
  eq(rpcLog.map((c) => c.fn), ["corner_desk_state", "corner_desk_pull", "corner_desk_pull", "corner_desk_report",
    "corner_desk_report", "corner_desk_heartbeat"]);
  ok(rpcLog.every((c) => c.key === "service-key" && c.auth === null));
});

Deno.test("gzip: signed as sent, then unzipped", async () => {
  reset();
  rpcAnswers.corner_desk_heartbeat = { data: { scheme: "corner.1" }, error: null };
  const gz = await gzip(enc.encode(JSON.stringify({ action: "heartbeat", info: { host: "desk-pc" } })));
  eq(await answer(await send(gz, { "x-corpus-encoding": "gzip" })), { status: 200, body: { ok: true, result: { scheme: "corner.1" } } });
  eq(rpcLog.at(-1)!.args, { p_info: { host: "desk-pc" } });
});

Deno.test("a database error is 422 '<rpc>: <message>', at most 600 characters", async () => {
  reset();
  rpcAnswers.corner_desk_pull = { data: null, error: { message: "permission denied for function corner_desk_pull", code: "42501" } };
  eq(await answer(await post({ action: "pull", worker: "desk-pc" })),
    { status: 422, body: { ok: false, error: "corner_desk_pull: permission denied for function corner_desk_pull" } });
  rpcAnswers.corner_desk_report = { data: null, error: { message: "p_status: " + "x".repeat(1000) } };
  const long = await answer(await post({ action: "report", id: 1, status: "done" }));
  eq(long.status, 422);
  eq(long.body.error.length, 600);
  ok(long.body.error.startsWith("corner_desk_report: p_status: "));
  rpcAnswers.corner_desk_state = { data: null, error: { message: "Could not find the function public.corner_desk_state" } };
  eq(await answer(await post({ action: "hello" })),
    { status: 422, body: { ok: false, error: "corner_desk_state: Could not find the function public.corner_desk_state" } },
    "hello before the C9 SQL is pasted");
});

Deno.test("one JSON log line per call, without the secret or the desk's text", async () => {
  reset();
  const lines: string[] = [];
  const real = console.log;
  console.log = (...a: unknown[]) => { lines.push(a.map(String).join(" ")); };
  try {
    rpcAnswers.corner_desk_pull = { data: [{ id: 1 }, { id: 2 }], error: null };
    await post({ action: "pull", limit: 2, worker: "desk-pc" });
    rpcAnswers.corner_desk_report = { data: true, error: null };
    await post({ action: "report", id: 2, status: "failed", message: "private-message", log: "private-log-tail" });
    await send(enc.encode('{"action":"state"}'), {}, false);
  } finally {
    console.log = real;
  }
  eq(lines.length, 3);
  const [pull, rep, refused] = lines.map((l) => JSON.parse(l));
  eq([pull.fn, pull.evt, pull.action, pull.rpc, typeof pull.ms, pull.worker, pull.claimed],
    ["corpus-desk", "rpc", "pull", "corner_desk_pull", "number", "desk-pc", 2]);
  eq([rep.evt, rep.rpc, rep.id, rep.status, rep.recorded], ["rpc", "corner_desk_report", 2, "failed", true]);
  eq(refused, { fn: "corpus-desk", evt: "refused", status: 401, error: "missing or malformed x-corpus-ts" });
  ok(!lines.some((l) => l.includes(SECRET) || l.includes("private-")), "nothing private is logged");
});
