/**
 * Pictures and graphic novels of the working corpus - CORPUS_MEDIA_C8_2026_10_09.
 *
 * The translation desk draws pictures for passages (scripts/images.py) and graphic novels from
 * approved stories (scripts/novel.py). scripts/corpus_media.py puts them here: two JPEG renditions
 * of each picture (480 px 'thumb', 1600 px 'display') in the Srangam Shared Drive, NOT shared by
 * link, and their captions, anchors, plans and status in the private schema corpus (C8).
 *
 * Who sees what is decided by the database (docs/cloud/C8_corpus_media_2026-10-09.sql in the
 * automaton repo), never here: readers see approved pictures and approved novels; admins also
 * see drafts and novels still being drawn. A picture's bytes come through the edge function
 * corpus-media, which asks the database AS THIS READER first (corpus_reader_media_file).
 *
 * The bytes are fetched with the reader's own token (never put in a URL), kept as object URLs for
 * this tab, and kept in the browser's Cache Storage under this user's id, so a picture seen once
 * opens at once next time: a picture is named by its sha256 and never changes.
 *
 * Same contract as corpusLibrary.ts: check `ok` first; `refused` is not a failure; a function the
 * database does not have yet (C8 not applied) is `missing`, and the pages then say so quietly.
 */
import { supabase } from '@/integrations/supabase/client';
import { callMirror, functionMissing, type MirrorResult } from '@/lib/corpusMirror';

export const MEDIA_MARK = 'CORPUS_MEDIA_C8_2026_10_09';
export const GENERATED_LABEL = 'Illustration - generated, not a historical source.';
export const MEDIA_PAGE = 60;

export type Rendition = 'thumb' | 'display';

export interface MediaRow {
  media_key: string; doc_code: string; doc_title: string; kind: string; status: string; title: string | null;
  caption_en: string | null; caption_hi: string | null; context_note: string | null; anchor_page: number | null;
  anchor_idx: number | null; anchor_verse_ref: string | null; story_id: number | null; width: number | null;
  height: number | null; sha256: string; has_thumb: boolean; has_display: boolean; model: string | null;
  license: string | null; approved_at_local: string | null; total: number;
}

export interface NovelRow {
  novel_id: number; doc_code: string; doc_title: string; story_id: number | null; story_title: string | null;
  status: string; title: string | null; title_hi: string | null; audience: string | null; pages: number | null;
  cover_sha: string | null; cover_has_thumb: boolean; approved_at_local: string | null; updated_at_local: string | null;
}

export interface NovelSpeech { who: string | null; line: string | null; cite: string | null }
export interface NovelPage { n: number; scene: string | null; caption: string | null; caption_hi: string | null; speech: NovelSpeech[]; cites: string[] }
export interface NovelCast { name: string | null; look: string | null }
export interface NovelPlan { title: string | null; title_hi: string | null; cast: NovelCast[]; pages: NovelPage[] }
export interface NovelVerify { ok: boolean | null; problems: string[]; cited: string[]; pages: number | null; checked_at: string | null }

export interface NovelMedia {
  key: string; kind: string; seq: number | null; status: string; title: string | null; sha256: string;
  width: number | null; height: number | null; version: number | null; has_thumb: boolean; has_display: boolean;
}

export interface NovelFull extends Omit<NovelRow, 'cover_sha' | 'cover_has_thumb' | 'updated_at_local'> {
  plan: unknown; verify: unknown; cover_seq: number | null; model: string | null; image_model: string | null;
  aspect: string | null; media: NovelMedia[] | null;
}

export interface MediaResult<T> extends MirrorResult<T> { missing: boolean }

async function lib<T>(fn: string, args: Record<string, unknown>): Promise<MediaResult<T>> {
  const r = await callMirror<T>(fn, args);
  return { ...r, missing: functionMissing(r, fn) };
}

export function loadMedia(o: { doc?: string | null; story?: number | null; k?: number; offset?: number } = {}): Promise<MediaResult<MediaRow>> {
  return lib<MediaRow>('corpus_reader_media', {
    p_doc: o.doc || null, p_story: o.story ?? null, k: Math.min(Math.max(o.k ?? MEDIA_PAGE, 1), 200),
    p_offset: Math.max(0, o.offset ?? 0),
  });
}

export function loadNovels(doc?: string | null): Promise<MediaResult<NovelRow>> {
  return lib<NovelRow>('corpus_reader_novels', { p_doc: doc || null });
}

export function loadNovel(id: number): Promise<MediaResult<NovelFull>> {
  return lib<NovelFull>('corpus_reader_novel', { p_id: id });
}

export function isMedia(x: unknown): x is MediaRow {
  const r = x as MediaRow;
  return !!r && typeof r.media_key === 'string' && typeof r.sha256 === 'string' && /^[0-9a-f]{64}$/.test(r.sha256);
}

export function isNovel(x: unknown): x is NovelRow {
  const r = x as NovelRow;
  return !!r && typeof r.novel_id === 'number' && typeof r.doc_code === 'string';
}

export function novelHref(id: number, page?: number): string {
  return `/corpus/novels/${id}${page ? `#page-${page}` : ''}`;
}

export function imagesHref(doc?: string | null): string {
  return doc ? `/corpus/images?doc=${encodeURIComponent(doc)}` : '/corpus/images';
}

/** "Page 69, passage 1" style anchor of a picture, as the reader's margin reference ("69.1"). */
export function anchorRef(m: Pick<MediaRow, 'anchor_page' | 'anchor_idx'>): string | null {
  if (m.anchor_page == null || m.anchor_idx == null || m.anchor_page < 1) return null;
  return `${m.anchor_page}.${m.anchor_idx}`;
}

export const KIND_LABELS: Record<string, string> = {
  generated: 'Illustration', cover: 'Cover', 'edition-plate': 'Plate from an edition', diagram: 'Diagram',
  photo: 'Photograph', novel_page: 'Page', novel_cast: 'Cast sheet',
};

/** Pictures the desk generated carry the label; plates and photographs are sources of their own. */
export function isGenerated(kind: string | null | undefined): boolean {
  return kind === 'generated' || kind === 'cover' || kind === 'novel_page' || kind === 'novel_cast';
}

const str = (v: unknown, n = 4000): string | null => (typeof v === 'string' && v.trim() ? v.slice(0, n) : null);
const refs = (v: unknown, n: number): string[] =>
  Array.isArray(v) ? v.filter((c): c is string => typeof c === 'string' && /^\d+\.\d+$/.test(c)).slice(0, n) : [];

/** The plan as the desk wrote it (a JSON object, or its text); anything malformed is dropped. */
export function parsePlan(raw: unknown): NovelPlan {
  let p: any = raw;
  if (typeof raw === 'string') {
    try { p = JSON.parse(raw); } catch { p = null; }
  }
  if (!p || typeof p !== 'object' || Array.isArray(p)) return { title: null, title_hi: null, cast: [], pages: [] };
  const cast = (Array.isArray(p.cast) ? p.cast : []).slice(0, 40)
    .filter((c: any) => c && typeof c === 'object')
    .map((c: any) => ({ name: str(c.name, 200), look: str(c.look) }));
  const pages: NovelPage[] = (Array.isArray(p.pages) ? p.pages : []).slice(0, 200)
    .filter((q: any) => q && typeof q === 'object' && Number.isInteger(q.n) && q.n > 0)
    .map((q: any) => ({
      n: q.n, scene: str(q.scene), caption: str(q.caption), caption_hi: str(q.caption_hi),
      speech: (Array.isArray(q.speech) ? q.speech : []).slice(0, 20).filter((s: any) => s && typeof s === 'object')
        .map((s: any) => ({ who: str(s.who, 200), line: str(s.line), cite: str(s.cite, 40) })),
      cites: refs(q.cites, 100),
    }))
    .sort((a: NovelPage, b: NovelPage) => a.n - b.n);
  return { title: str(p.title, 500), title_hi: str(p.title_hi, 500), cast, pages };
}

export function parseNovelVerify(raw: unknown): NovelVerify {
  let v: any = raw;
  if (typeof raw === 'string') {
    try { v = JSON.parse(raw); } catch { v = null; }
  }
  if (!v || typeof v !== 'object') return { ok: null, problems: [], cited: [], pages: null, checked_at: null };
  return {
    ok: typeof v.ok === 'boolean' ? v.ok : null,
    problems: Array.isArray(v.problems) ? v.problems.map(String).slice(0, 20) : [],
    cited: refs(v.cited, 400),
    pages: typeof v.pages === 'number' ? v.pages : null,
    checked_at: typeof v.checked_at === 'string' ? v.checked_at : null,
  };
}

/** The pictures of one novel by kind and number. */
export function novelPictures(media: NovelMedia[] | null | undefined): { pages: Map<number, NovelMedia>; cast: Map<number, NovelMedia> } {
  const pages = new Map<number, NovelMedia>();
  const cast = new Map<number, NovelMedia>();
  for (const m of media ?? []) {
    if (!m || typeof m.sha256 !== 'string' || typeof m.seq !== 'number') continue;
    if (m.kind === 'novel_page') pages.set(m.seq, m);
    else if (m.kind === 'novel_cast') cast.set(m.seq, m);
  }
  return { pages, cast };
}

/** A caption's text with its bracketed citations ("... [25.7, 25.8]") split out, for links. */
export function citeParts(s: string | null | undefined): { text: string; refs: string[] }[] {
  const out: { text: string; refs: string[] }[] = [];
  const re = /\[\s*(\d+\.\d+(?:\s*[,;]\s*\d+\.\d+)*)\s*\]/g;
  const src = s ?? '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) out.push({ text: src.slice(last, m.index), refs: [] });
    out.push({ text: '', refs: m[1].split(/\s*[,;]\s*/) });
    last = m.index + m[0].length;
  }
  if (last < src.length) out.push({ text: src.slice(last), refs: [] });
  return out;
}

// ---- the bytes ------------------------------------------------------------------------------

const FN_URL = `${import.meta.env.VITE_SUPABASE_URL ?? ''}/functions/v1/corpus-media`;
const ANON = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? '') as string;
const CACHE_NAME = 'srangam-corpus-media-v1';
const MAX_URLS = 400;          // object URLs kept for this tab; the oldest are let go
const MAX_PARALLEL = 6;        // pictures fetched at once (each is one edge call and one Drive read)

export class PictureError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

const urls = new Map<string, Promise<string>>();
let running = 0;
const queue: (() => void)[] = [];

async function slot<T>(f: () => Promise<T>): Promise<T> {
  if (running >= MAX_PARALLEL) await new Promise<void>((r) => queue.push(r));
  running += 1;
  try {
    return await f();
  } finally {
    running -= 1;
    queue.shift()?.();
  }
}

async function session(): Promise<{ token: string; uid: string } | null> {
  try {
    const { data } = await (supabase as any).auth.getSession();
    const s = data?.session;
    return s?.access_token ? { token: s.access_token as string, uid: String(s.user?.id ?? 'anon') } : null;
  } catch {
    return null;
  }
}

function cacheKey(uid: string, sha: string, r: Rendition): string {
  return `https://corpus-media.cache/${encodeURIComponent(uid)}/${sha}/${r}`;
}

async function fromCache(key: string): Promise<Blob | null> {
  try {
    if (typeof caches === 'undefined') return null;
    const c = await caches.open(CACHE_NAME);
    const hit = await c.match(key);
    return hit ? await hit.blob() : null;
  } catch {
    return null;
  }
}

async function toCache(key: string, blob: Blob): Promise<void> {
  try {
    if (typeof caches === 'undefined') return;
    const c = await caches.open(CACHE_NAME);
    await c.put(key, new Response(blob, { headers: { 'Content-Type': blob.type || 'image/jpeg' } }));
  } catch {
    /* quota, private mode: the network copy is enough */
  }
}

async function fetchBlob(sha: string, r: Rendition): Promise<Blob> {
  const s = await session();
  if (!s) throw new PictureError(401, 'Sign in to see this picture.');
  const key = cacheKey(s.uid, sha, r);
  const cached = await fromCache(key);
  if (cached) return cached;
  return slot(async () => {
    let res: Response;
    try {
      res = await fetch(`${FN_URL}?sha=${sha}&r=${r}`, {
        headers: { Authorization: `Bearer ${s.token}`, apikey: ANON },
      });
    } catch {
      throw new PictureError(0, 'The picture could not be reached.');
    }
    if (!res.ok) {
      const msg = res.status === 404 ? 'This picture is not available.'
        : res.status === 401 || res.status === 403 ? 'This picture is for the corpus readers only.'
          : 'The picture could not be loaded.';
      throw new PictureError(res.status, msg);
    }
    const blob = await res.blob();
    void toCache(key, blob);
    return blob;
  });
}

/** An object URL for a picture's rendition: fetched once per tab, kept across visits. */
export function pictureUrl(sha: string, r: Rendition = 'thumb'): Promise<string> {
  if (!/^[0-9a-f]{64}$/.test(sha)) return Promise.reject(new PictureError(400, 'Not a picture.'));
  const k = `${sha}:${r}`;
  const have = urls.get(k);
  if (have) return have;
  const p = fetchBlob(sha, r).then((b) => URL.createObjectURL(b));
  p.catch(() => urls.delete(k));
  urls.set(k, p);
  if (urls.size > MAX_URLS) {
    const [oldest, op] = urls.entries().next().value as [string, Promise<string>];
    urls.delete(oldest);
    op.then((u) => setTimeout(() => URL.revokeObjectURL(u), 60_000)).catch(() => undefined);
  }
  return p;
}

/** For tests and sign-out: forget this tab's pictures. */
export function forgetPictures(): void {
  for (const p of urls.values()) p.then((u) => URL.revokeObjectURL(u)).catch(() => undefined);
  urls.clear();
}
