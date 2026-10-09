// deno test docs/cloud/C9_corpus-desk/lib_test.ts   (no network, no imports from the web)
// CORNER_C9_2026_10_09
import {
  CORS, FN_VERSION, gunzipLimited, jsonbTextLength, MAX_BODY_BYTES, MAX_JSON_BYTES, signHex, toDeskCall,
  verifyRequest,
} from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const enc = new TextEncoder();
const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

async function gzip(bytes: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(await new Response(new Blob([bytes as BlobPart]).stream()
    .pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
}

Deno.test("the signature is corpus-ingest's (the same golden value as corpus_sync.py's test)", async () => {
  eq(await signHex("test-secret-for-golden", "1760000000", enc.encode('{"action":"hello"}')),
    "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16");
  ok(FN_VERSION === "corpus-desk c9.1 (CORNER_C9_2026_10_09)");
  eq([MAX_BODY_BYTES, MAX_JSON_BYTES], [1048576, 4194304]);
  eq(CORS["Access-Control-Allow-Methods"], "POST, OPTIONS");
});

Deno.test("signed, timely requests pass; anything else is refused", async () => {
  const body = enc.encode('{"action":"state"}');
  const sig = await signHex(SECRET, "1760000000", body);
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000100), { ok: true });
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1759999700), { ok: true }, "300 s early is still in time");
  eq(await verifyRequest(SECRET, "1760000000", sig.toUpperCase(), body, 1760000000), { ok: true }, "hex in capitals");
  eq((await verifyRequest(SECRET, "1760000000", sig, enc.encode('{"action":"hello"}'), 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET + "x", "1760000000", sig, body, 1760000000)).why, "bad signature", "another secret");
  eq((await verifyRequest(SECRET, "1760000001", sig, body, 1760000000)).why, "bad signature", "the ts is signed too");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1760000301)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1759999699)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest("short", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  eq((await verifyRequest("", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  eq((await verifyRequest(SECRET, null, sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000.5", sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000", null, body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", sig.slice(2), body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", "z".repeat(64), body, 1760000000)).why, "missing or malformed x-corpus-sig");
});

Deno.test("gzip is undone, with a ceiling (4 MiB by default)", async () => {
  const gz = await gzip(enc.encode("x".repeat(5000)));
  eq((await gunzipLimited(gz)).length, 5000);
  let threw = "";
  try { await gunzipLimited(gz, 100); } catch (e) { threw = (e as Error).message; }
  eq(threw, "body expands past 100 bytes");
  eq((await gunzipLimited(await gzip(new Uint8Array(MAX_JSON_BYTES)))).length, MAX_JSON_BYTES, "exactly the ceiling");
  threw = "";
  try { await gunzipLimited(await gzip(new Uint8Array(MAX_JSON_BYTES + 1))); } catch (e) { threw = (e as Error).message; }
  eq(threw, `body expands past ${MAX_JSON_BYTES} bytes`);
  threw = "";
  try { await gunzipLimited(enc.encode("not gzip at all")); } catch (e) { threw = (e as Error).message; }
  ok(threw.length > 0, "a body that is not gzip is refused");
});

Deno.test("JSON is measured as Postgres prints jsonb", () => {
  eq(jsonbTextLength({ a: 1, b: [1, 2] }), '{"a": 1, "b": [1, 2]}'.length);
  eq(jsonbTextLength({}), 2);
  eq(jsonbTextLength([]), 2);
  eq(jsonbTextLength({ s: 'say "hi"\n', n: null, t: true, o: { x: [] } }),
    '{"n": null, "o": {"x": []}, "s": "say \\"hi\\"\\n", "t": true}'.length);
  eq(jsonbTextLength({ s: "x".repeat(50) }, 10), JSON.stringify({ s: "x".repeat(50) }).length, "past the limit: compact");
});

Deno.test("hello and state", () => {
  eq(toDeskCall({ action: "hello" }), { call: { action: "hello" } });
  eq(toDeskCall({ action: "state" }), { call: { action: "state", rpc: "corner_desk_state", args: {} } });
  eq(toDeskCall({ action: "state", extra: 1 }).call?.args, {}, "other fields are ignored");
});

Deno.test("pull: limit 1 to 20 (3 by default) and a plain worker name", () => {
  eq(toDeskCall({ action: "pull", worker: "desk-pc:corner_worker@1.0" }).call,
    { action: "pull", rpc: "corner_desk_pull", args: { p_limit: 3, p_worker: "desk-pc:corner_worker@1.0" } });
  eq(toDeskCall({ action: "pull", limit: 20, worker: "My Desk 2" }).call?.args, { p_limit: 20, p_worker: "My Desk 2" });
  eq(toDeskCall({ action: "pull", limit: 1, worker: "w" }).call?.args, { p_limit: 1, p_worker: "w" });
  eq(toDeskCall({ action: "pull", limit: null, worker: "w" }).call?.args, { p_limit: 3, p_worker: "w" });
  eq(toDeskCall({ action: "pull", worker: "w".repeat(100) }).call?.rpc, "corner_desk_pull");
  const LIMIT = "limit: a whole number from 1 to 20";
  for (const limit of [0, 21, -1, 2.5, "3", true, [3]]) {
    eq(toDeskCall({ action: "pull", limit, worker: "w" }).error, LIMIT, `limit ${JSON.stringify(limit)}`);
  }
  const WORKER = "worker: 1 to 100 characters, letters, digits, spaces and . _ : @ -";
  for (const worker of [undefined, null, "", "w".repeat(101), "desk;drop", "d\u00e9sk", "a/b", "tab\t", 7]) {
    eq(toDeskCall({ action: "pull", worker }).error, WORKER, `worker ${JSON.stringify(worker)}`);
  }
});

Deno.test("report: every field checked, absent ones sent as null", () => {
  const good = { action: "report", id: 42, status: "done", result: { story_id: 7 }, message: "drafted",
                 cost_usd: 0.0123, log: "tail of the run" };
  eq(toDeskCall(good).call, {
    action: "report", rpc: "corner_desk_report",
    args: { p_id: 42, p_status: "done", p_result: { story_id: 7 }, p_message: "drafted", p_cost: 0.0123,
            p_log: "tail of the run" },
  });
  eq(toDeskCall({ action: "report", id: 1, status: "running" }).call?.args,
    { p_id: 1, p_status: "running", p_result: null, p_message: null, p_cost: null, p_log: null });
  eq(toDeskCall({ ...good, status: "failed", result: null, message: null, cost_usd: null, log: null }).call?.args,
    { p_id: 42, p_status: "failed", p_result: null, p_message: null, p_cost: null, p_log: null });
  eq(toDeskCall({ ...good, id: Number.MAX_SAFE_INTEGER }).call?.args?.p_id, Number.MAX_SAFE_INTEGER);
  eq(toDeskCall({ ...good, result: {}, cost_usd: 0 }).call?.args?.p_cost, 0);
  eq(toDeskCall({ ...good, cost_usd: 99.9999 }).call?.args?.p_cost, 99.9999);
  eq(toDeskCall({ ...good, message: "m".repeat(2000), log: "l".repeat(8000) }).call?.rpc, "corner_desk_report");
  eq(toDeskCall({ ...good, result: { t: "x".repeat(19991) } }).call?.rpc, "corner_desk_report",
    '{"t": "..."} is exactly 20000 characters');

  const ID = "id: a positive whole number";
  for (const id of [0, -3, 1.5, "42", null, undefined, Number.MAX_SAFE_INTEGER + 1, true]) {
    eq(toDeskCall({ ...good, id }).error, ID, `id ${JSON.stringify(id)}`);
  }
  for (const status of ["claimed", "approved", "DONE", "", null, 1]) {
    eq(toDeskCall({ ...good, status }).error, "status: running, done or failed", `status ${JSON.stringify(status)}`);
  }
  const RESULT = "result: a JSON object of at most 20000 characters, or null";
  for (const result of [[1], "done", 7, false, { t: "x".repeat(19992) }]) {
    eq(toDeskCall({ ...good, result }).error, RESULT, "result");
  }
  // 14007 characters compact but 21007 as Postgres prints it: refused, as the database would drop it.
  const ones = { a: new Array(7000).fill(1) };
  eq([JSON.stringify(ones).length, jsonbTextLength(ones)], [14007, 21007]);
  eq(toDeskCall({ ...good, result: ones }).error, RESULT, "measured as jsonb");
  for (const message of ["m".repeat(2001), 5, { m: 1 }]) {
    eq(toDeskCall({ ...good, message }).error, "message: text of at most 2000 characters, or null");
  }
  const COST = "cost_usd: a number of dollars from 0 to under 100, or null";
  for (const cost_usd of [-0.01, 100, 1e9, "0.01", true]) {
    eq(toDeskCall({ ...good, cost_usd }).error, COST, `cost ${JSON.stringify(cost_usd)}`);
  }
  for (const log of ["l".repeat(8001), ["a"], 0]) {
    eq(toDeskCall({ ...good, log }).error, "log: text of at most 8000 characters, or null");
  }
});

Deno.test("heartbeat: info, a JSON object of at most 4000 characters", () => {
  const info = { host: "desk-pc", version: "corner_worker 1.0", budget_left_usd: 3.5 };
  eq(toDeskCall({ action: "heartbeat", info }).call,
    { action: "heartbeat", rpc: "corner_desk_heartbeat", args: { p_info: info } });
  eq(toDeskCall({ action: "heartbeat", info: {} }).call?.args, { p_info: {} });
  eq(toDeskCall({ action: "heartbeat", info: { t: "x".repeat(3991) } }).call?.rpc, "corner_desk_heartbeat", "4000");
  const INFO = "info: a JSON object of at most 4000 characters";
  for (const bad of [undefined, null, [], "up", 1, { t: "x".repeat(3992) }]) {
    eq(toDeskCall({ action: "heartbeat", info: bad }).error, INFO, `info ${JSON.stringify(bad)?.slice(0, 20)}`);
  }
});

Deno.test("anything else is refused", () => {
  eq(toDeskCall({ action: "approve" }).error, "unknown action");
  eq(toDeskCall({ action: "upload" }).error, "unknown action", "corpus-media's actions are not here");
  eq(toDeskCall({}).error, "unknown action");
  eq(toDeskCall({ action: ["pull"] }).error, "unknown action");
  for (const body of [[1], null, "pull", 3, true, undefined]) {
    eq(toDeskCall(body).error, "body must be a JSON object", `body ${JSON.stringify(body)}`);
  }
});
