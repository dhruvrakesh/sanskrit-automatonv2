/**
 * corpus-media (C8, docs/MEDIA_AND_CORNER_2026-10-09.md)  CORPUS_MEDIA_C8_2026_10_09
 *
 * Pictures and graphic novels of the working corpus, kept in the Srangam Shared Drive.
 *   POST (the desk's scripts/corpus_media.py, signed with CORPUS_SYNC_SECRET like corpus-ingest):
 *     { action: hello | state | upsert_media | upsert_novels | retire | upload, ... }
 *     upload puts one rendition (thumb 480 px or display 1600 px) in the folder "Srangam corpus
 *     media" of the Shared Drive, NOT shared by link, once per (sha256, rendition).
 *   GET ?sha=<64 hex>&r=thumb|display with the reader's own Authorization: Bearer <jwt>:
 *     corpus_reader_media_file() decides, as that reader, whether the picture may be shown (the
 *     corpus gate, approved for readers, drafts for editors); only then are the bytes read from
 *     Drive with the service account. 401 no token, 403 not a reader, 404 not visible or no file.
 *     Cache-Control: private, a month, immutable (a sha names one picture for ever).
 * Secrets used, all already in the project: SUPABASE_URL, SUPABASE_ANON_KEY,
 * SUPABASE_SERVICE_ROLE_KEY, CORPUS_SYNC_SECRET (as corpus-ingest), GOOGLE_SERVICE_ACCOUNT_JSON
 * (as generate-article-og, tts-save-drive, context-save-drive). No AI call; no cost per call but
 * the function invocation and Drive's own (free) quota.
 */
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.58.0';
import { getDriveAccessToken, loadServiceAccount, uploadToDrive } from '../_shared/google-drive.ts';
import {
  CORS, FN_VERSION, MAX_BODY_BYTES, checkUpload, driveFileName, etagOf, gunzipLimited, isRefusal, matchesEtag,
  parseServe, pictureHeaders, toDeskCall, verifyRequest,
} from './lib.ts';

const SHARED_DRIVE = '0AHOa_eCfO3arUk9PVA'; // the Srangam Shared Drive (as _shared/google-drive.ts)
const FOLDER_NAME = 'Srangam corpus media';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });
const text = (status: number, body: string) =>
  new Response(body, { status, headers: { ...CORS, 'Content-Type': 'text/plain; charset=utf-8' } });

// One Drive token per warm instance, renewed ten minutes before it ends.
let token: { value: string; until: number } | null = null;
async function driveToken(fresh = false): Promise<string> {
  if (!fresh && token && Date.now() < token.until) return token.value;
  const value = await getDriveAccessToken(loadServiceAccount());
  token = { value, until: Date.now() + 50 * 60 * 1000 };
  return value;
}

function env() {
  return {
    url: Deno.env.get('SUPABASE_URL') ?? '',
    anon: Deno.env.get('SUPABASE_ANON_KEY') ?? '',
    service: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    secret: Deno.env.get('CORPUS_SYNC_SECRET') ?? '',
  };
}

function log(o: Record<string, unknown>) {
  console.log(JSON.stringify({ fn: 'corpus-media', ...o }));
}

// ---- GET: a picture for a signed-in reader ------------------------------------------------------

async function servePicture(req: Request): Promise<Response> {
  const { sha, rendition, error } = parseServe(new URL(req.url));
  if (error) return text(400, error);
  const auth = req.headers.get('Authorization') ?? req.headers.get('authorization') ?? '';
  if (!/^bearer\s+\S+/i.test(auth)) return text(401, 'sign in to see this picture');
  const e = env();
  if (!e.url || !e.anon) return text(500, 'the server is missing its Supabase configuration');

  const reader = createClient(e.url, e.anon, {
    global: { headers: { Authorization: auth } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error: dbErr } = await reader.rpc('corpus_reader_media_file', { p_sha: sha, p_rendition: rendition });
  if (dbErr) {
    if (isRefusal(dbErr)) return text(403, 'the working corpus is open to its readers only');
    log({ evt: 'lookup_failed', sha: sha!.slice(0, 12), error: dbErr.message });
    return text(502, 'the picture could not be looked up');
  }
  const row = Array.isArray(data) ? data[0] : null;
  if (!row || !row.file_id) return text(404, 'no such picture for this reader');

  const etag = etagOf(sha!, rendition!);
  if (matchesEtag(req.headers.get('If-None-Match'), etag)) {
    return new Response(null, { status: 304, headers: pictureHeaders(row.mime, etag) });
  }

  const get = async (fresh: boolean) =>
    fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(row.file_id)}?alt=media&supportsAllDrives=true`, {
      headers: { Authorization: `Bearer ${await driveToken(fresh)}` },
    });
  let res: Response;
  try {
    res = await get(false);
    if (res.status === 401) res = await get(true);
  } catch (err) {
    log({ evt: 'drive_unreachable', error: String(err) });
    return text(502, 'Drive could not be reached');
  }
  if (!res.ok || !res.body) {
    log({ evt: 'drive_error', status: res.status, file: row.file_id });
    return text(502, 'Drive did not return the picture');
  }
  return new Response(res.body, { status: 200, headers: pictureHeaders(row.mime, etag) });
}

// ---- POST: the desk ----------------------------------------------------------------------------

async function folderId(svc: ReturnType<typeof createClient>): Promise<string | undefined> {
  const { data: have } = await svc.rpc('corpus_media_config_get', { p_key: 'drive_folder' });
  if (typeof have === 'string' && have) return have;
  try {
    const res = await fetch('https://www.googleapis.com/drive/v3/files?supportsAllDrives=true', {
      method: 'POST',
      headers: { Authorization: `Bearer ${await driveToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: FOLDER_NAME, mimeType: 'application/vnd.google-apps.folder', parents: [SHARED_DRIVE] }),
    });
    if (!res.ok) throw new Error(`${res.status} ${(await res.text()).slice(0, 200)}`);
    const id = (await res.json()).id as string;
    await svc.rpc('corpus_media_config_set', { p_key: 'drive_folder', p_value: id });
    log({ evt: 'folder_created', folder: id });
    return id;
  } catch (err) {
    log({ evt: 'folder_failed', error: String(err) });   // fall back to the Shared Drive's top level
    return undefined;
  }
}

async function upload(svc: ReturnType<typeof createClient>, p: Record<string, unknown>): Promise<Response> {
  const { upload: u, error } = await checkUpload(p);
  if (!u) return json(400, { ok: false, error });
  const { data: existing, error: getErr } = await svc.rpc('corpus_media_file_get', { p_sha: u.sha256, p_rendition: u.rendition });
  if (getErr) return json(422, { ok: false, error: `corpus_media_file_get: ${getErr.message}`.slice(0, 600) });
  if (existing && (existing as { file_id?: string }).file_id) {
    return json(200, { ok: true, result: { skipped: true, file_id: (existing as { file_id: string }).file_id } });
  }
  let fileId: string;
  try {
    const parent = await folderId(svc);
    ({ fileId } = await uploadToDrive({
      accessToken: await driveToken(),
      fileName: driveFileName(u),
      mimeType: u.mime,
      body: { kind: 'base64', data: u.data },
      parentFolderId: parent,
      shareAnyone: false,
    }));
  } catch (err) {
    log({ evt: 'upload_failed', sha: u.sha256.slice(0, 12), error: String(err).slice(0, 300) });
    return json(502, { ok: false, error: 'Drive upload failed: ' + String(err).slice(0, 300) });
  }
  const { data: put, error: putErr } = await svc.rpc('corpus_media_file_put', {
    p_row: {
      sha256: u.sha256, rendition: u.rendition, storage: 'gdrive', file_id: fileId, mime: u.mime, bytes: u.bytes,
      width: u.width, height: u.height, file_sha256: u.file_sha256,
    },
  });
  if (putErr) {
    log({ evt: 'record_failed', file: fileId, error: putErr.message });
    return json(422, { ok: false, error: `corpus_media_file_put: ${putErr.message}`.slice(0, 600) });
  }
  log({ evt: 'uploaded', sha: u.sha256.slice(0, 12), rendition: u.rendition, bytes: u.bytes, file: fileId, recorded: put });
  return json(200, { ok: true, result: { uploaded: true, file_id: fileId, recorded: put === true } });
}

async function desk(req: Request): Promise<Response> {
  const e = env();
  if (!e.secret) return json(503, { ok: false, error: 'CORPUS_SYNC_SECRET is not set in the project secrets' });
  if (!e.url || !e.service) return json(500, { ok: false, error: 'Server is missing Supabase configuration' });
  const declared = Number(req.headers.get('content-length') ?? '0');
  if (declared > MAX_BODY_BYTES) return json(413, { ok: false, error: 'body too large' });
  const raw = new Uint8Array(await req.arrayBuffer());
  if (raw.length > MAX_BODY_BYTES) return json(413, { ok: false, error: 'body too large' });
  const v = await verifyRequest(e.secret, req.headers.get('x-corpus-ts'), req.headers.get('x-corpus-sig'), raw,
    Math.floor(Date.now() / 1000));
  if (!v.ok) return json(401, { ok: false, error: v.why });

  let payload: Record<string, unknown>;
  try {
    const bytes = req.headers.get('x-corpus-encoding') === 'gzip' ? await gunzipLimited(raw) : raw;
    payload = JSON.parse(new TextDecoder().decode(bytes));
  } catch (err) {
    return json(400, { ok: false, error: 'unreadable body: ' + String((err as Error)?.message ?? err).slice(0, 200) });
  }
  const { call, error } = toDeskCall(payload);
  if (!call) return json(400, { ok: false, error });

  const svc = createClient(e.url, e.service, { auth: { persistSession: false, autoRefreshToken: false } });
  if (call.action === 'hello') {
    return json(200, { ok: true, result: { fn: FN_VERSION, drive: !!Deno.env.get('GOOGLE_SERVICE_ACCOUNT_JSON') } });
  }
  if (call.action === 'upload') return await upload(svc, payload);

  const t0 = Date.now();
  const { data, error: dbErr } = await svc.rpc(call.rpc!, call.args);
  if (dbErr) {
    log({ evt: 'rpc_failed', rpc: call.rpc, ms: Date.now() - t0, error: dbErr.message });
    return json(422, { ok: false, error: `${call.rpc}: ${dbErr.message}`.slice(0, 600) });
  }
  log({ evt: 'rpc', rpc: call.rpc, ms: Date.now() - t0 });
  return json(200, { ok: true, result: data });
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  try {
    if (req.method === 'GET') return await servePicture(req);
    if (req.method === 'POST') return await desk(req);
    return text(405, 'GET or POST');
  } catch (err) {
    log({ evt: 'unhandled', error: String(err).slice(0, 300) });
    return json(500, { ok: false, error: 'unexpected error' });
  }
});
