// deno test docs/cloud/C4_corpus-ingest/lib_test.ts   (no network, no imports from the web)
// CORPUS_MIRROR_C4_2026_10_08
import { FN_VERSION, gunzipLimited, hexToBytes, MAX_KEYS, MAX_ROWS, signHex, TABLES, toCall, verifyRequest } from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const enc = new TextEncoder();
const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const RUN = "6f1c2b3a-1d2e-4f5a-8b9c-0d1e2f3a4b5c";

async function gzip(s: string): Promise<Uint8Array> {
  const stream = new Blob([enc.encode(s)]).stream().pipeThrough(new CompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

Deno.test("the signature is the one corpus_sync.py makes (golden value shared with the Python test)", async () => {
  eq(await signHex("test-secret-for-golden", "1760000000", enc.encode('{"action":"hello"}')),
    "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16");
});

Deno.test("a correctly signed, timely request passes", async () => {
  const body = enc.encode('{"action":"hello"}');
  const sig = await signHex(SECRET, "1760000000", body);
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000100), { ok: true });
});

Deno.test("wrong secret, changed body, stale clock, bad headers and a short server secret are refused", async () => {
  const body = enc.encode('{"action":"hello"}');
  const sig = await signHex(SECRET, "1760000000", body);
  const other = await signHex(SECRET.replace("0", "1"), "1760000000", body);
  eq((await verifyRequest(SECRET, "1760000000", other, body, 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET, "1760000000", sig, enc.encode('{"action":"keys"}'), 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1760000301)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest(SECRET, null, sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000", "zz", body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest("short", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  // a signature made for one timestamp does not pass for another
  eq((await verifyRequest(SECRET, "1760000001", sig, body, 1760000000)).why, "bad signature");
});

Deno.test("gunzip round-trips and refuses a body that expands past the limit", async () => {
  const s = JSON.stringify({ action: "ingest", rows: [{ a: "श्लोक" }] });
  eq(new TextDecoder().decode(await gunzipLimited(await gzip(s))), s);
  let threw = false;
  try { await gunzipLimited(await gzip("x".repeat(100_000)), 1000); } catch { threw = true; }
  ok(threw, "limit enforced");
});

Deno.test("each action maps to exactly one database function", () => {
  eq(toCall({ action: "hello" }).call?.rpc, "corpus_manifest");
  eq(toCall({ action: "manifest" }).call?.args, { p_tables: TABLES });
  eq(toCall({ action: "manifest", tables: ["docs"] }).call?.args, { p_tables: ["docs"] });
  eq(toCall({ action: "keys", table: "passages", group: "markandeya_purana" }).call,
    { action: "keys", rpc: "corpus_keys", args: { p_table: "passages", p_group: "markandeya_purana" } });
  eq(toCall({ action: "ingest", table: "docs", rows: [{ doc_code: "x", row_hash: "h" }], run_id: RUN }).call?.args,
    { p_table: "docs", p_rows: [{ doc_code: "x", row_hash: "h" }], p_run: RUN });
  eq(toCall({ action: "retire", table: "passages", group: "d", keys: ["1|2"] }).call?.rpc, "corpus_retire");
  eq(toCall({ action: "run", run_id: RUN, finish: true }).call?.args, { p_run: RUN, p_info: null, p_finish: true });
});

Deno.test("bad requests are refused before the database", () => {
  ok(toCall(null).error);
  ok(toCall([1]).error);
  ok(toCall({ action: "drop" }).error);
  ok(toCall({ action: "manifest", tables: ["users"] }).error);
  ok(toCall({ action: "keys", table: "auth.users", group: "*" }).error);
  ok(toCall({ action: "keys", table: "docs" }).error);
  ok(toCall({ action: "ingest", table: "docs", rows: [] }).error);
  ok(toCall({ action: "ingest", table: "docs", rows: Array(MAX_ROWS + 1).fill({}) }).error);
  ok(toCall({ action: "ingest", table: "docs", rows: [{}], run_id: "not-a-uuid" }).error);
  ok(toCall({ action: "retire", table: "docs", group: "*", keys: [1] }).error);
  ok(toCall({ action: "retire", table: "docs", group: "*", keys: Array(MAX_KEYS + 1).fill("k") }).error);
  ok(toCall({ action: "run", run_id: "x" }).error);
});

Deno.test("hex parsing and version", () => {
  eq(hexToBytes("00".repeat(32))?.length, 32);
  eq(hexToBytes("0g".repeat(32)), null);
  eq(hexToBytes("00"), null);
  ok(FN_VERSION.includes("CORPUS_MIRROR_C4_2026_10_08"));
});
