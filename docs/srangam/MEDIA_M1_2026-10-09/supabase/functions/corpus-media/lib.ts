// C8 - corpus-media: the logic, kept free of network imports so it can be tested with plain
// `deno test` (lib_test.ts). CORPUS_MEDIA_C8_2026_10_09. Design: docs/MEDIA_AND_CORNER_2026-10-09.md.
//
// Two doors in one function:
//   POST, from the desk (scripts/corpus_media.py): signed exactly as corpus-ingest is, with
//     x-corpus-ts (unix seconds, within 5 minutes) and x-corpus-sig = hex HMAC-SHA256(
//     CORPUS_SYNC_SECRET, ts + "." + body as sent). Actions: hello, state, upsert_media,
//     upsert_novels, retire, upload. Each maps to one C8 database function run as service_role,
//     except upload, which also puts the picture in the Srangam Shared Drive (not shared by link).
//   GET ?sha=<64 hex>&r=thumb|display, from a signed-in reader's browser: the reader's own JWT asks
//     corpus_reader_media_file() whether this reader may see the picture; only then are the bytes
//     fetched from Drive with the service account and returned, cacheable by that browser only.
// The verify code is a copy of corpus-ingest's lib.ts (a function cannot import another's folder;
// that is what broke the first search-corpus deploy). Its golden test is the same.

export const FN_VERSION = "corpus-media c8.1 (CORPUS_MEDIA_C8_2026_10_09)";
export const MAX_BODY_BYTES = 6 * 1024 * 1024;   // as sent
export const MAX_JSON_BYTES = 24 * 1024 * 1024;  // after gunzip
export const MAX_FILE_BYTES = 4 * 1024 * 1024;   // one rendition, decoded (the table's own limit)
export const MAX_SKEW_S = 300;
export const RENDITIONS = ["thumb", "display"] as const;
export const MIMES = ["image/jpeg", "image/png", "image/webp"] as const;
export const SHA_RE = /^[0-9a-f]{64}$/;
const KEY_RE = /^(img:[0-9]{1,9}|novel:[0-9]{1,9}:(page|cast):[0-9]{1,3})$/;

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

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes as BufferSource));
  return Array.from(d, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function b64ToBytes(b64: string): Uint8Array | null {
  if (typeof b64 !== "string" || b64.length === 0 || b64.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) return null;
  try {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  } catch {
    return null;
  }
}

export interface DeskCall {
  action: "hello" | "state" | "upsert_media" | "upsert_novels" | "retire" | "upload";
  rpc?: string;
  args?: Record<string, unknown>;
}

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

/** Validate a desk request and map it to one C8 function (upload is handled by the caller). */
export function toDeskCall(p: unknown): { call?: DeskCall; error?: string } {
  if (!isObj(p)) return { error: "body must be a JSON object" };
  const a = p.action;
  switch (a) {
    case "hello":
      return { call: { action: "hello" } };
    case "state":
      return { call: { action: "state", rpc: "corpus_media_state", args: {} } };
    case "upsert_media": {
      const rows = p.rows;
      if (!Array.isArray(rows) || rows.length === 0 || rows.length > 500) return { error: "rows: 1 to 500 pictures" };
      for (const r of rows) {
        if (!isObj(r) || typeof r.media_key !== "string" || !KEY_RE.test(r.media_key)) return { error: "rows: a bad media_key" };
        if (typeof r.sha256 !== "string" || !SHA_RE.test(r.sha256)) return { error: "rows: a bad sha256" };
        if (typeof r.row_hash !== "string" || r.row_hash.length < 8 || r.row_hash.length > 128) return { error: "rows: a bad row_hash" };
      }
      return { call: { action: "upsert_media", rpc: "corpus_media_upsert", args: { p_rows: rows } } };
    }
    case "upsert_novels": {
      const rows = p.rows;
      if (!Array.isArray(rows) || rows.length === 0 || rows.length > 100) return { error: "rows: 1 to 100 novels" };
      for (const r of rows) {
        if (!isObj(r) || !Number.isInteger(r.novel_id) || (r.novel_id as number) < 1) return { error: "rows: a bad novel_id" };
        if (typeof r.row_hash !== "string" || r.row_hash.length < 8 || r.row_hash.length > 128) return { error: "rows: a bad row_hash" };
      }
      return { call: { action: "upsert_novels", rpc: "corpus_novels_upsert", args: { p_rows: rows } } };
    }
    case "retire": {
      const media = p.media ?? [];
      const novels = p.novels ?? [];
      if (!Array.isArray(media) || media.length > 5000 || media.some((k) => typeof k !== "string" || !KEY_RE.test(k))) {
        return { error: "media: up to 5000 media keys" };
      }
      if (!Array.isArray(novels) || novels.length > 1000 || novels.some((n) => !Number.isInteger(n) || n < 1)) {
        return { error: "novels: up to 1000 novel ids" };
      }
      return { call: { action: "retire", rpc: "corpus_media_retire", args: { p_media: media, p_novels: novels } } };
    }
    case "upload":
      return { call: { action: "upload" } };
    default:
      return { error: "unknown action" };
  }
}

export interface Upload {
  sha256: string; rendition: string; mime: string; width: number | null; height: number | null;
  file_sha256: string; bytes: number; data: string;
}

/** Check an upload: the names, the size, and that the bytes are the ones the desk says they are. */
export async function checkUpload(p: Record<string, unknown>): Promise<{ upload?: Upload; error?: string }> {
  const { sha256, rendition, mime, width, height, file_sha256, data } = p;
  if (typeof sha256 !== "string" || !SHA_RE.test(sha256)) return { error: "sha256: 64 lowercase hex characters" };
  if (typeof rendition !== "string" || !(RENDITIONS as readonly string[]).includes(rendition)) return { error: "rendition: thumb or display" };
  if (typeof mime !== "string" || !(MIMES as readonly string[]).includes(mime)) return { error: "mime: image/jpeg, image/png or image/webp" };
  if (typeof file_sha256 !== "string" || !SHA_RE.test(file_sha256)) return { error: "file_sha256: 64 lowercase hex characters" };
  const dim = (v: unknown) => v === null || v === undefined || (Number.isInteger(v) && (v as number) > 0 && (v as number) <= 20000);
  if (!dim(width) || !dim(height)) return { error: "width and height: positive whole numbers" };
  if (typeof data !== "string" || data.length > Math.ceil(MAX_FILE_BYTES / 3) * 4 + 4) return { error: "data: base64, at most 4 MB decoded" };
  const bytes = b64ToBytes(data);
  if (!bytes || bytes.length === 0) return { error: "data: not base64" };
  if (bytes.length > MAX_FILE_BYTES) return { error: "data: more than 4 MB" };
  if ((await sha256Hex(bytes)) !== file_sha256) return { error: "data: its sha256 is not file_sha256" };
  return {
    upload: {
      sha256, rendition, mime, width: (width as number) ?? null, height: (height as number) ?? null,
      file_sha256, bytes: bytes.length, data,
    },
  };
}

export function driveFileName(u: Pick<Upload, "sha256" | "rendition" | "mime">): string {
  const ext = u.mime === "image/png" ? "png" : u.mime === "image/webp" ? "webp" : "jpg";
  return `corpus_${u.sha256.slice(0, 16)}_${u.rendition}.${ext}`;
}

/** GET ?sha=&r= -> the picture asked for, or why not. */
export function parseServe(url: URL): { sha?: string; rendition?: string; error?: string } {
  const sha = url.searchParams.get("sha") ?? "";
  const rendition = url.searchParams.get("r") ?? "thumb";
  if (!SHA_RE.test(sha)) return { error: "sha: 64 lowercase hex characters" };
  if (!(RENDITIONS as readonly string[]).includes(rendition)) return { error: "r: thumb or display" };
  return { sha, rendition };
}

export const etagOf = (sha: string, rendition: string) => `"${sha.slice(0, 32)}-${rendition}"`;

/** Does If-None-Match name this ETag (a list, or *)? */
export function matchesEtag(ifNoneMatch: string | null, etag: string): boolean {
  if (!ifNoneMatch) return false;
  return ifNoneMatch.split(",").map((s) => s.trim().replace(/^W\//, "")).some((t) => t === etag || t === "*");
}

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, if-none-match",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Expose-Headers": "etag",
};

/** Headers for a picture: this browser may keep it a month; nothing shared may keep it at all. */
export function pictureHeaders(mime: string, etag: string): Record<string, string> {
  return {
    ...CORS,
    "Content-Type": mime,
    "Cache-Control": "private, max-age=2592000, immutable",
    "ETag": etag,
    "X-Content-Type-Options": "nosniff",
    "Vary": "Authorization",
  };
}

/** A refusal from corpus_reader_media_file: the reader may not read the corpus at all. */
export function isRefusal(err: { code?: string; message?: string } | null | undefined): boolean {
  if (!err) return false;
  return err.code === "42501" || /signed-in readers only|permission denied/i.test(err.message ?? "");
}
