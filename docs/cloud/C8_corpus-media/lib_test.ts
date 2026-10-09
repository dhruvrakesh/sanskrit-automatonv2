// deno test docs/cloud/C8_corpus-media/lib_test.ts   (no network, no imports from the web)
// CORPUS_MEDIA_C8_2026_10_09
import {
  b64ToBytes, checkUpload, driveFileName, etagOf, FN_VERSION, gunzipLimited, isRefusal, matchesEtag, parseServe,
  pictureHeaders, sha256Hex, signHex, toDeskCall, verifyRequest,
} from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const enc = new TextEncoder();
const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const SHA = "a".repeat(64);

function b64(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

Deno.test("the signature is corpus-ingest's (the same golden value as corpus_sync.py's test)", async () => {
  eq(await signHex("test-secret-for-golden", "1760000000", enc.encode('{"action":"hello"}')),
    "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16");
  ok(FN_VERSION.includes("CORPUS_MEDIA_C8_2026_10_09"));
});

Deno.test("signed, timely requests pass; anything else is refused", async () => {
  const body = enc.encode('{"action":"state"}');
  const sig = await signHex(SECRET, "1760000000", body);
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000100), { ok: true });
  eq((await verifyRequest(SECRET, "1760000000", sig, enc.encode('{"action":"hello"}'), 1760000000)).why, "bad signature");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1760000400)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest("short", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  eq((await verifyRequest(SECRET, "1760000000", null, body, 1760000000)).why, "missing or malformed x-corpus-sig");
});

Deno.test("gzip is undone, with a ceiling", async () => {
  const gz = new Uint8Array(await new Response(new Blob([enc.encode("x".repeat(5000))]).stream()
    .pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
  eq((await gunzipLimited(gz)).length, 5000);
  let threw = false;
  try { await gunzipLimited(gz, 100); } catch { threw = true; }
  ok(threw, "limit");
});

Deno.test("desk actions map to the C8 functions and bad bodies are refused", () => {
  eq(toDeskCall({ action: "state" }).call, { action: "state", rpc: "corpus_media_state", args: {} });
  const row = { media_key: "img:3", sha256: SHA, row_hash: "0123456789" };
  eq(toDeskCall({ action: "upsert_media", rows: [row] }).call?.rpc, "corpus_media_upsert");
  eq(toDeskCall({ action: "upsert_media", rows: [{ ...row, media_key: "pic:1" }] }).error, "rows: a bad media_key");
  eq(toDeskCall({ action: "upsert_media", rows: [{ ...row, sha256: "A".repeat(64) }] }).error, "rows: a bad sha256");
  eq(toDeskCall({ action: "upsert_media", rows: [] }).error, "rows: 1 to 500 pictures");
  eq(toDeskCall({ action: "upsert_novels", rows: [{ novel_id: 1, row_hash: "0123456789" }] }).call?.rpc, "corpus_novels_upsert");
  eq(toDeskCall({ action: "upsert_novels", rows: [{ novel_id: 0, row_hash: "0123456789" }] }).error, "rows: a bad novel_id");
  eq(toDeskCall({ action: "retire", media: ["novel:1:page:2"], novels: [2] }).call?.args,
    { p_media: ["novel:1:page:2"], p_novels: [2] });
  eq(toDeskCall({ action: "retire", media: ["drop table"] }).error, "media: up to 5000 media keys");
  eq(toDeskCall({ action: "upload" }).call, { action: "upload" });
  eq(toDeskCall({ action: "delete" }).error, "unknown action");
  eq(toDeskCall([1]).error, "body must be a JSON object");
});

Deno.test("an upload is checked: names, size and that the bytes are what the desk says", async () => {
  const bytes = enc.encode("not really a jpeg but bytes");
  const good = { sha256: SHA, rendition: "thumb", mime: "image/jpeg", width: 480, height: 640,
                 file_sha256: await sha256Hex(bytes), data: b64(bytes) };
  const r = await checkUpload(good);
  eq(r.upload?.bytes, bytes.length);
  eq((await checkUpload({ ...good, file_sha256: "b".repeat(64) })).error, "data: its sha256 is not file_sha256");
  eq((await checkUpload({ ...good, rendition: "huge" })).error, "rendition: thumb or display");
  eq((await checkUpload({ ...good, mime: "text/html" })).error, "mime: image/jpeg, image/png or image/webp");
  eq((await checkUpload({ ...good, data: "%%%" })).error, "data: not base64");
  eq((await checkUpload({ ...good, width: -1 })).error, "width and height: positive whole numbers");
  eq((await checkUpload({ ...good, sha256: "short" })).error, "sha256: 64 lowercase hex characters");
  eq(b64ToBytes("YWJj")?.length, 3);
  eq(b64ToBytes("abc"), null);
});

Deno.test("reading: the query, the ETag and the headers", () => {
  eq(parseServe(new URL("https://x/f?sha=" + SHA + "&r=display")), { sha: SHA, rendition: "display" });
  eq(parseServe(new URL("https://x/f?sha=" + SHA)), { sha: SHA, rendition: "thumb" });
  eq(parseServe(new URL("https://x/f?sha=nothex")).error, "sha: 64 lowercase hex characters");
  eq(parseServe(new URL("https://x/f?sha=" + SHA + "&r=original")).error, "r: thumb or display");
  const tag = etagOf(SHA, "thumb");
  ok(matchesEtag(tag, tag)); ok(matchesEtag(`W/${tag}, "x"`, tag)); ok(!matchesEtag(null, tag)); ok(!matchesEtag('"y"', tag));
  const h = pictureHeaders("image/jpeg", tag);
  eq(h["Cache-Control"], "private, max-age=2592000, immutable");
  eq(h["Content-Type"], "image/jpeg");
  ok(h["Access-Control-Allow-Headers"].includes("authorization"));
  eq(driveFileName({ sha256: SHA, rendition: "display", mime: "image/jpeg" }), "corpus_aaaaaaaaaaaaaaaa_display.jpg");
  ok(isRefusal({ code: "42501" })); ok(isRefusal({ message: "The working corpus is open to signed-in readers only." }));
  ok(!isRefusal({ message: "timeout" })); ok(!isRefusal(null));
});
