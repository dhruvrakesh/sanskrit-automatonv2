// deno test docs/cloud/C23_corpus-index/lib_test.ts   (no network, no imports from the web)
// C21_INDEX_SITE_2026_10_25, C23_INDEX_CLAIMS_2026_10_28
import { FN_VERSION, gunzipLimited, hexToBytes, logLine, MAX_KEYS, MAX_ROWS, signHex, TABLES, toCall, verifyRequest }
  from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const enc = new TextEncoder();
const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

async function gzip(s: string): Promise<Uint8Array> {
  const stream = new Blob([enc.encode(s)]).stream().pipeThrough(new CompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

Deno.test("the signature is the one corpus_sync.sign makes (the golden value of C4's test and the Python test)", async () => {
  eq(await signHex("test-secret-for-golden", "1760000000", enc.encode('{"action":"hello"}')),
    "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16");
});

Deno.test("a correctly signed, timely request passes; a gzip body is signed as sent", async () => {
  const body = enc.encode('{"action":"hello"}');
  const sig = await signHex(SECRET, "1760000000", body);
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000100), { ok: true });
  const gz = await gzip('{"action":"keys","table":"persons"}');
  const gsig = await signHex(SECRET, "1760000000", gz);
  eq(await verifyRequest(SECRET, "1760000000", gsig, gz, 1760000000), { ok: true });
});

Deno.test("wrong secret, changed body, stale clock, bad headers and a short server secret are refused", async () => {
  const body = enc.encode('{"action":"hello"}');
  const sig = await signHex(SECRET, "1760000000", body);
  const other = await signHex(SECRET.replace("0", "1"), "1760000000", body);
  eq((await verifyRequest(SECRET, "1760000000", other, body, 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET, "1760000000", sig, enc.encode('{"action":"keys"}'), 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1760000301)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1759999699)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest(SECRET, null, sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "17600000x0", sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000", "zz", body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", null, body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest("short", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  eq((await verifyRequest("", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  // a signature made for one timestamp does not pass for another
  eq((await verifyRequest(SECRET, "1760000001", sig, body, 1760000000)).why, "bad signature");
});

Deno.test("gunzip round-trips Devanagari and refuses a body that expands past the limit", async () => {
  const s = JSON.stringify({ action: "ingest", table: "persons", rows: [{ key: "pe:1", head: "जनमेजय" }] });
  eq(new TextDecoder().decode(await gunzipLimited(await gzip(s))), s);
  let threw = false;
  try { await gunzipLimited(await gzip("x".repeat(100_000)), 1000); } catch { threw = true; }
  ok(threw, "limit enforced");
});

Deno.test("each action maps to exactly one C21 service function", () => {
  eq(TABLES, ["texts", "persons", "steps", "statements", "claims", "lines", "verses", "meta"]);
  eq(toCall({ action: "keys", table: "claims" }).call?.args, { p_table: "claims" }, "C23: the claims");
  eq(toCall({ action: "hello" }).call, { action: "hello", rpc: "corpus_index_manifest", args: {} });
  eq(toCall({ action: "manifest" }).call, { action: "manifest", rpc: "corpus_index_manifest", args: {} });
  eq(toCall({ action: "keys", table: "steps" }).call,
    { action: "keys", rpc: "corpus_index_keys", args: { p_table: "steps" } });
  eq(toCall({ action: "ingest", table: "persons", rows: [{ key: "pe:1", row_hash: "h" }] }).call,
    { action: "ingest", rpc: "corpus_index_ingest", args: { p_table: "persons", p_rows: [{ key: "pe:1", row_hash: "h" }] } });
  eq(toCall({ action: "delete", table: "lines", keys: ["pe:1"] }).call,
    { action: "delete", rpc: "corpus_index_delete", args: { p_table: "lines", p_keys: ["pe:1"] } });
  for (const t of TABLES) eq(toCall({ action: "keys", table: t }).call?.args, { p_table: t }, t);
});

Deno.test("bad requests are refused before the database", () => {
  ok(toCall(null).error);
  ok(toCall("hello").error);
  ok(toCall([1]).error);
  ok(toCall({}).error);
  ok(toCall({ action: "drop" }).error);
  ok(toCall({ action: "retire", table: "persons", keys: ["k"] }).error, "corpus-ingest's actions are not this door's");
  ok(toCall({ action: "keys" }).error);
  ok(toCall({ action: "keys", table: "passages" }).error, "a mirror table is not an index table");
  ok(toCall({ action: "keys", table: "corpus.index_persons" }).error);
  ok(toCall({ action: "ingest", table: "persons" }).error);
  ok(toCall({ action: "ingest", table: "persons", rows: [] }).error);
  ok(toCall({ action: "ingest", table: "persons", rows: {} }).error);
  ok(toCall({ action: "ingest", table: "persons", rows: Array(MAX_ROWS + 1).fill({}) }).error);
  ok(!toCall({ action: "ingest", table: "persons", rows: Array(MAX_ROWS).fill({}) }).error, "the ceiling itself is allowed");
  ok(toCall({ action: "delete", table: "persons", keys: [] }).error);
  ok(toCall({ action: "delete", table: "persons", keys: [1] }).error);
  ok(toCall({ action: "delete", table: "persons", keys: Array(MAX_KEYS + 1).fill("k") }).error);
});

Deno.test("the log line says what was asked and how much, never the rows", () => {
  const c = toCall({ action: "ingest", table: "persons", rows: [{ key: "pe:1", head: "secret words" }] }).call!;
  const line = logLine(c, 12, 200, { rows: 1, changed: 1 }, c.args);
  eq(JSON.parse(line), { fn: "corpus-index", action: "ingest", table: "persons", rows: 1, changed: 1, status: 200, ms: 12 });
  ok(!line.includes("secret words"));
});

Deno.test("hex parsing and version", () => {
  eq(hexToBytes("00".repeat(32))?.length, 32);
  eq(hexToBytes("0g".repeat(32)), null);
  eq(hexToBytes("00"), null);
  ok(FN_VERSION.includes("C21_INDEX_SITE_2026_10_25"));
  ok(FN_VERSION.includes("C23_INDEX_CLAIMS_2026_10_28"));
});
