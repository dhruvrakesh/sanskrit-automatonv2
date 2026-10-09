// The corpus-media handler end to end with Drive, the database and the gateway faked.
// Run inside the Srangam layout (the function imports ../_shared/google-drive.ts), from
// supabase/functions/corpus-media with this folder copied to _test/:
//   deno test --no-remote --allow-env --import-map=_test/import_map.json _test/handler_test.ts
// CORPUS_MEDIA_C8_2026_10_09
import { handler } from "./server_stub.ts";
import { signHex, sha256Hex } from "../lib.ts";
import "../index.ts";   // registers its handler with the stand-in serve(); it reads the environment per request

const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const SHA = "c".repeat(64);
function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

async function pem(): Promise<string> {
  const k = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048,
    publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
  const der = new Uint8Array(await crypto.subtle.exportKey("pkcs8", k.privateKey));
  let s = ""; for (const b of der) s += String.fromCharCode(b);
  return "-----BEGIN PRIVATE KEY-----\n" + btoa(s) + "\n-----END PRIVATE KEY-----";
}

type Call = { fn: string; args: unknown; key: string; auth: string | null };
let rpcLog: Call[] = [];
let rpcAnswers: Record<string, { data: unknown; error: { message: string; code?: string } | null }> = {};
let fetchLog: { url: string; method: string; auth: string | null }[] = [];
let driveBody = new Uint8Array([1, 2, 3]);

(globalThis as unknown as { __rpc: unknown }).__rpc = (fn: string, args: unknown, key: string, auth: string | null) => {
  rpcLog.push({ fn, args, key, auth });
  return rpcAnswers[fn] ?? { data: null, error: null };
};
const realFetch = globalThis.fetch;
globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
  const url = String(input instanceof Request ? input.url : input);
  const h = new Headers(init?.headers);
  fetchLog.push({ url, method: init?.method ?? "GET", auth: h.get("Authorization") });
  if (url.startsWith("https://oauth2.googleapis.com/token")) return Response.json({ access_token: "drive-token" });
  if (url.includes("/upload/drive/v3/files")) return Response.json({ id: "NEWFILE123" });
  if (url.startsWith("https://www.googleapis.com/drive/v3/files?")) return Response.json({ id: "FOLDER123" });
  if (url.includes("alt=media")) return new Response(driveBody, { status: 200 });
  return new Response("unexpected " + url, { status: 599 });
}) as typeof fetch;

Deno.env.set("SUPABASE_URL", "https://p.supabase.co");
Deno.env.set("SUPABASE_ANON_KEY", "anon-key");
Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key");
Deno.env.set("CORPUS_SYNC_SECRET", SECRET);
Deno.env.set("GOOGLE_SERVICE_ACCOUNT_JSON", JSON.stringify({ client_email: "sa@x.iam.gserviceaccount.com", private_key: await pem() }));

function reset() { rpcLog = []; fetchLog = []; rpcAnswers = {}; }
const get = (q: string, headers: Record<string, string> = {}) =>
  handler!(new Request("https://p.supabase.co/functions/v1/corpus-media" + q, { headers }));
async function post(body: unknown, signed = true) {
  const raw = new TextEncoder().encode(JSON.stringify(body));
  const ts = String(Math.floor(Date.now() / 1000));
  return handler!(new Request("https://p.supabase.co/functions/v1/corpus-media", {
    method: "POST", body: raw,
    headers: signed ? { "x-corpus-ts": ts, "x-corpus-sig": await signHex(SECRET, ts, raw) } : {},
  }));
}

Deno.test("GET: no token 401; not a reader 403; not visible 404", async () => {
  reset();
  eq((await get(`?sha=${SHA}&r=thumb`)).status, 401);
  rpcAnswers.corpus_reader_media_file = { data: null, error: { code: "42501", message: "open to signed-in readers only" } };
  eq((await get(`?sha=${SHA}&r=thumb`, { Authorization: "Bearer user-jwt" })).status, 403);
  rpcAnswers.corpus_reader_media_file = { data: [], error: null };
  eq((await get(`?sha=${SHA}&r=thumb`, { Authorization: "Bearer user-jwt" })).status, 404);
  eq((await get(`?sha=nothex`, { Authorization: "Bearer user-jwt" })).status, 400);
  ok(fetchLog.length === 0, "Drive is never asked before the database says yes");
  eq(rpcLog[0].key, "anon-key", "the lookup runs as the reader, with the anon key");
  eq(rpcLog[0].auth, "Bearer user-jwt");
});

Deno.test("GET: a visible picture comes from Drive with the service account, cacheable privately", async () => {
  reset();
  rpcAnswers.corpus_reader_media_file = { data: [{ file_id: "FILE9", mime: "image/jpeg", bytes: 3, storage: "gdrive" }], error: null };
  const res = await get(`?sha=${SHA}&r=display`, { Authorization: "Bearer user-jwt" });
  eq(res.status, 200);
  eq(Array.from(new Uint8Array(await res.arrayBuffer())), [1, 2, 3]);
  eq(res.headers.get("Cache-Control"), "private, max-age=2592000, immutable");
  eq(res.headers.get("Content-Type"), "image/jpeg");
  const drive = fetchLog.find((f) => f.url.includes("alt=media"))!;
  ok(drive.url.includes("/files/FILE9?alt=media&supportsAllDrives=true"));
  eq(drive.auth, "Bearer drive-token");
  const etag = res.headers.get("ETag")!;
  fetchLog = [];
  const again = await get(`?sha=${SHA}&r=display`, { Authorization: "Bearer user-jwt", "If-None-Match": etag });
  eq(again.status, 304);
  ok(!fetchLog.some((f) => f.url.includes("alt=media")), "a 304 does not touch Drive");
});

Deno.test("POST: unsigned is refused; hello and state answer", async () => {
  reset();
  eq((await post({ action: "hello" }, false)).status, 401);
  const h = await (await post({ action: "hello" })).json();
  eq([h.ok, h.result.drive], [true, true]);
  rpcAnswers.corpus_media_state = { data: { scheme: "media.1" }, error: null };
  const s = await (await post({ action: "state" })).json();
  eq(s.result, { scheme: "media.1" });
  eq(rpcLog.at(-1)!.key, "service-key");
  eq((await post({ action: "upsert_media", rows: [] })).status, 400);
});

Deno.test("POST upload: into the folder, never shared by link, recorded once", async () => {
  reset();
  const bytes = new TextEncoder().encode("jpeg-bytes");
  let s = ""; for (const b of bytes) s += String.fromCharCode(b);
  const body = { action: "upload", sha256: SHA, rendition: "thumb", mime: "image/jpeg", width: 480, height: 640,
                 file_sha256: await sha256Hex(bytes), data: btoa(s) };
  rpcAnswers.corpus_media_file_get = { data: null, error: null };
  rpcAnswers.corpus_media_config_get = { data: null, error: null };
  rpcAnswers.corpus_media_file_put = { data: true, error: null };
  const r = await (await post(body)).json();
  eq(r, { ok: true, result: { uploaded: true, file_id: "NEWFILE123", recorded: true } });
  ok(fetchLog.some((f) => f.url.startsWith("https://www.googleapis.com/drive/v3/files?") && f.method === "POST"), "folder made");
  ok(!fetchLog.some((f) => f.url.includes("/permissions")), "no anyone-with-link permission");
  eq(rpcLog.find((c) => c.fn === "corpus_media_config_set")!.args, { p_key: "drive_folder", p_value: "FOLDER123" });
  const put = rpcLog.find((c) => c.fn === "corpus_media_file_put")!.args as { p_row: Record<string, unknown> };
  eq([put.p_row.file_id, put.p_row.bytes, put.p_row.rendition], ["NEWFILE123", bytes.length, "thumb"]);

  reset();
  rpcAnswers.corpus_media_file_get = { data: { file_id: "OLD1" }, error: null };
  const again = await (await post(body)).json();
  eq(again.result, { skipped: true, file_id: "OLD1" });
  ok(!fetchLog.some((f) => f.url.includes("/upload/")), "an existing rendition is not uploaded again");

  reset();
  const bad = await post({ ...body, file_sha256: "d".repeat(64) });
  eq(bad.status, 400);
});

addEventListener("unload", () => { globalThis.fetch = realFetch; });
