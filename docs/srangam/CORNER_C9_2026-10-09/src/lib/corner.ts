/**
 * The Researchers' Corner - CORNER_C9_2026_10_09.
 *
 * Invited researchers and editors ask the translation desk for stories, pictures and graphic
 * novels drawn from the translated texts, and make anthologies of the approved stories. Everything
 * is decided by the database (docs/cloud/C9_researchers_corner_2026-10-09.sql in the automaton
 * repo), never here: who may ask (corner_me().can_request), who decides (is_editor), what a request
 * costs (its estimate), and the daily cap. The site never generates anything itself: the desk (a
 * PC) takes approved requests on its rounds, and the results come back through the mirror (C4)
 * and the pictures (C8) as drafts until an editor approves them.
 *
 * Same contract as corpusMedia.ts: check `ok` first; `refused` is not a failure; a function the
 * database does not have yet (C9 not applied) is `missing`, and the pages then say so quietly.
 * The reads go through callMirror; the actions keep the server's own sentence (a refusal such as
 * "Only an editor may ask for this." or a reason such as "title: 3 to 200 characters"), which the
 * pages show as it is.
 */
import { supabase } from '@/integrations/supabase/client';
import { callMirror, functionMissing, type MirrorDoc } from '@/lib/corpusMirror';
import { parseAt, storyHref } from '@/lib/corpusLibrary';
import { imagesHref, novelHref, type MediaResult } from '@/lib/corpusMedia';

export const CORNER_MARK = 'CORNER_C9_2026_10_09';
export const CORNER_KEY = ['corner'] as const;
export const CORNER_HREF = '/corpus/corner';
/** How long the desk may be away before the Corner says so (its rounds are every ten minutes). */
export const DESK_LATE_MIN = 30;

export type CornerResult<T> = MediaResult<T>;

// ---- the rows -------------------------------------------------------------------------------

export interface CornerMe {
  can_request: boolean; is_editor: boolean; is_super_admin: boolean; daily_cap_usd: number | string | null;
  committed_today: number | string | null; researchers_need_approval: boolean; worker_last_seen: string | null;
  worker_info: Record<string, unknown> | null; pending: number; queued: number; running: number; mine_open: number;
}

export type KindUnit = 'request' | 'page' | 'chunk';

export interface CornerKind {
  kind: string; label: string; cost_bearing: boolean; editor_only: boolean; est_usd: number | string; unit: KindUnit;
  enabled: boolean;
}

export type RequestStatus = 'pending' | 'approved' | 'claimed' | 'running' | 'done' | 'failed' | 'rejected' | 'cancelled';

export interface RequestPreview {
  story_id: number | null; status: string | null; title: string | null; title_hi: string | null;
  story_en: string | null; verify: unknown;
}

export interface CornerRequest {
  id: number; kind: string; label: string; doc_code: string | null; doc_title: string | null;
  params: Record<string, unknown> | null; note: string | null; status: string; est_usd: number | string | null;
  cost_usd: number | string | null; requested_at: string; mine: boolean; requester: string | null;
  decided_at: string | null; decision_note: string | null; started_at: string | null; finished_at: string | null;
  message: string | null; result: Record<string, unknown> | null; preview: RequestPreview | null; total: number;
}

export interface CreatedRequest { request_id: number; request_status: string; est_usd: number | string; message: string }
export interface Decision { request_status: string; message: string }

export type Audience = 'general' | 'young' | 'scholar';
export const AUDIENCES: { value: Audience; label: string }[] = [
  { value: 'general', label: 'General readers' }, { value: 'young', label: 'Young readers' },
  { value: 'scholar', label: 'Scholars' },
];

export interface CollectionRow {
  id: number; title: string; title_hi: string | null; audience: string; status: string; items: number;
  mine: boolean; owner: string | null; created_at: string; updated_at: string; published_at: string | null;
  cover_sha: string | null; cover_has_thumb: boolean;
}

export interface CollectionPicture {
  media_key: string; sha256: string; width: number | null; height: number | null; status: string | null;
  caption_en: string | null; caption_hi: string | null; model: string | null; has_thumb: boolean; has_display: boolean;
}

export interface CollectionItem {
  pos: number; doc_code: string; doc_title: string | null; story_id: number; status: string | null;
  title: string | null; title_hi: string | null; story_en: string | null; story_hi: string | null;
  quote_sa: string | null; quote_ref: string | null; cites: string | null; from_page: number | null;
  from_idx: number | null; to_page: number | null; to_idx: number | null; model: string | null;
  picture: CollectionPicture | null;
}

export interface CollectionFull {
  id: number; title: string; title_hi: string | null; intro: string | null; audience: string; status: string;
  mine: boolean; can_edit: boolean; created_at: string; updated_at: string; published_at: string | null;
  items: unknown;
}

export interface SavedCollection { collection_id: number; collection_status: string }
export interface CollectionState { collection_status: string; message: string }

// ---- reads ----------------------------------------------------------------------------------

async function lib<T>(fn: string, args: Record<string, unknown>): Promise<CornerResult<T>> {
  const r = await callMirror<T>(fn, args);
  return { ...r, missing: functionMissing(r, fn) };
}

export function loadMe(): Promise<CornerResult<CornerMe>> {
  return lib<CornerMe>('corner_me', {});
}

export function loadKinds(): Promise<CornerResult<CornerKind>> {
  return lib<CornerKind>('corner_kinds', {});
}

export type RequestScope = 'mine' | 'queue' | 'all';

export function loadRequests(scope: RequestScope, o: { status?: string | null; k?: number; offset?: number } = {}): Promise<CornerResult<CornerRequest>> {
  return lib<CornerRequest>('corner_requests', {
    p_scope: scope, p_status: o.status || null, k: Math.min(Math.max(o.k ?? 50, 1), 200), p_offset: Math.max(0, o.offset ?? 0),
  });
}

export function loadCollections(scope: 'mine' | 'published' | 'all' = 'all'): Promise<CornerResult<CollectionRow>> {
  return lib<CollectionRow>('corner_collections', { p_scope: scope });
}

export function loadCollection(id: number): Promise<CornerResult<CollectionFull>> {
  return lib<CollectionFull>('corner_collection', { p_id: id });
}

// ---- actions --------------------------------------------------------------------------------

const TIMEOUT_MS = 15000;
const REFUSED_RE = /signed-in readers only|permission denied|not allowed|42501/i;

const failed = <T,>(error: string, refused = false): CornerResult<T> => ({ ok: false, rows: [], error, refused, missing: false });

type RpcAnswer = { data: unknown; error: { message?: string; code?: string } | null };
type Timeout = { __timeout: true };
/** The generated types do not list C9's functions; this is the one untyped door to them. */
const db = supabase as unknown as { rpc: (fn: string, args: Record<string, unknown>) => PromiseLike<RpcAnswer> };

/** One action: the rows it answers with (a scalar answer becomes one row), or the server's own
 *  sentence. The same refusal rule as corpusMirror.ts, but the sentence is kept. */
async function act<T>(fn: string, args: Record<string, unknown>, scalar = false): Promise<CornerResult<T>> {
  let res: RpcAnswer | Timeout | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    res = await Promise.race<RpcAnswer | Timeout>([
      db.rpc(fn, args),
      new Promise<Timeout>((resolve) => { timer = setTimeout(() => resolve({ __timeout: true }), TIMEOUT_MS); }),
    ]);
  } catch (e) {
    return failed<T>(e instanceof Error && e.message ? e.message : 'The working corpus could not be reached.');
  } finally {
    clearTimeout(timer);
  }
  if (!res) return failed<T>('The working corpus answered in an unexpected form.');
  if ('__timeout' in res) return failed<T>('The working corpus took too long to answer. Please try again.');
  if (res.error) {
    const msg = String(res.error.message ?? res.error);
    const refused = res.error.code === '42501' || REFUSED_RE.test(msg);
    const r = failed<T>(msg || 'The request failed.', refused);
    return { ...r, missing: functionMissing(r, fn) };
  }
  if (scalar) return { ok: true, rows: res.data == null ? [] : [res.data as T], error: null, refused: false, missing: false };
  if (!Array.isArray(res.data)) return failed<T>('The working corpus answered in an unexpected form.');
  return { ok: true, rows: res.data as T[], error: null, refused: false, missing: false };
}

export function createRequest(kind: string, doc: string, params: Record<string, unknown>, note?: string | null): Promise<CornerResult<CreatedRequest>> {
  return act<CreatedRequest>('corner_request_create', {
    p_kind: kind, p_doc: doc, p_params: params, p_note: (note ?? '').trim() || null,
  });
}

export function decideRequest(id: number, approve: boolean, note?: string | null): Promise<CornerResult<Decision>> {
  return act<Decision>('corner_request_decide', { p_id: id, p_approve: approve, p_note: (note ?? '').trim() || null });
}

export function cancelRequest(id: number): Promise<CornerResult<Decision>> {
  return act<Decision>('corner_request_cancel', { p_id: id });
}

export type SettingKey = 'daily_cap_usd' | 'researchers_need_approval' | 'max_pending_per_person';

/** corner_settings_set answers with the value it kept (a scalar, not a table). */
export function setSetting(key: SettingKey, value: string): Promise<CornerResult<string>> {
  return act<string>('corner_settings_set', { p_key: key, p_value: value }, true);
}

export interface CollectionDraft {
  id: number | null; title: string; title_hi: string; intro: string; audience: Audience;
  items: { doc_code: string; story_id: number }[];
}

export function saveCollection(d: CollectionDraft): Promise<CornerResult<SavedCollection>> {
  return act<SavedCollection>('corner_collection_save', {
    p_id: d.id, p_title: d.title.trim(), p_title_hi: d.title_hi.trim() || null, p_intro: d.intro.trim() || null,
    p_audience: d.audience, p_items: d.items.map((i) => ({ doc_code: i.doc_code, story_id: i.story_id })),
  });
}

export function publishCollection(id: number, publish: boolean): Promise<CornerResult<CollectionState>> {
  return act<CollectionState>('corner_collection_publish', { p_id: id, p_publish: publish });
}

export function retireCollection(id: number): Promise<CornerResult<CollectionState>> {
  return act<CollectionState>('corner_collection_retire', { p_id: id });
}

// ---- the rules the pages share --------------------------------------------------------------

export const num = (v: unknown): number => {
  const n = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : 0;
};

/** "$0.10": always two decimals; anything above nothing shows at least "$0.01". */
export function formatUsd(v: unknown): string {
  const n = num(v);
  if (n > 0 && n < 0.01) return '$0.01';
  return `$${n.toFixed(2)}`;
}

export const OPEN_STATUSES: readonly string[] = ['pending', 'approved', 'claimed', 'running'];
export const isOpen = (status: string | null | undefined): boolean => !!status && OPEN_STATUSES.includes(status);
export const canWithdraw = (status: string | null | undefined): boolean => status === 'pending' || status === 'approved';

const STATUS_LABELS: Record<string, string> = {
  pending: 'waiting for an editor', approved: 'queued for the desk', claimed: 'the desk is working on it',
  running: 'the desk is working on it', done: 'done', failed: 'failed', rejected: 'rejected', cancelled: 'withdrawn',
};

export function statusLabel(status: string | null | undefined): string {
  return (status && STATUS_LABELS[status]) || status || 'unknown';
}

export type Tone = 'amber' | 'blue' | 'green' | 'red' | 'muted';

export function statusTone(status: string | null | undefined): Tone {
  switch (status) {
    case 'pending': return 'amber';
    case 'approved': case 'claimed': case 'running': return 'blue';
    case 'done': return 'green';
    case 'failed': case 'rejected': return 'red';
    default: return 'muted';
  }
}

export const TONE_CLASS: Record<Tone, string> = {
  amber: 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200',
  blue: 'bg-sky-100 text-sky-900 dark:bg-sky-900/30 dark:text-sky-200',
  green: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  red: 'bg-red-100 text-red-900 dark:bg-red-900/30 dark:text-red-200',
  muted: 'bg-muted text-muted-foreground',
};

const s = (v: unknown): string => (v == null ? '' : String(v).trim());

/** What a request asks for, in a line ("Passages 25.2-25.9: 'Vitasta flows'"). */
export function requestSummary(kind: string, params: Record<string, unknown> | null | undefined): string {
  const p = params ?? {};
  const title = s(p.title) ? `: '${s(p.title)}'` : '';
  switch (kind) {
    case 'story_range': return `Passages ${s(p.from)}-${s(p.to)}${title}`;
    case 'story_write': return `Write story ${s(p.story_id)}`;
    case 'story_mine': return `Find up to ${s(p.max) || '?'} episodes in the text`;
    case 'picture_passage': return `A picture for passage ${s(p.at)}${title}`;
    case 'story_illustrate': return `A picture for story ${s(p.story_id)}`;
    case 'picture_redraw': return `Draw picture img:${s(p.image_id)} again`;
    case 'novel_plan': return `A graphic novel from story ${s(p.story_id)}: ${s(p.pages) || '12'} pages, for ${s(p.audience) || 'general'} readers`;
    case 'novel_cast': return `The cast of graphic novel ${s(p.novel_id)}`;
    case 'novel_draw': return `Graphic novel ${s(p.novel_id)}: ${s(p.pages) ? `pages ${s(p.pages)}` : 'every page still to be drawn'}`;
    case 'story_approve': return `Approve story ${s(p.story_id)}${p.force === true ? ' (even with problems)' : ''}`;
    case 'story_retire': return `Retire story ${s(p.story_id)}`;
    case 'picture_approve': return `Approve picture img:${s(p.image_id)}`;
    case 'picture_retire': return `Retire picture img:${s(p.image_id)}`;
    case 'novel_page_approve': return `Approve page ${s(p.page)} of graphic novel ${s(p.novel_id)}`;
    case 'novel_approve': return `Approve graphic novel ${s(p.novel_id)}${p.force === true ? ' (even with problems)' : ''}`;
    case 'novel_retire': return `Retire graphic novel ${s(p.novel_id)}`;
    default: return kind;
  }
}

const idOf = (v: unknown): number | null => {
  const m = /^(?:img:)?(\d{1,10})$/.exec(s(v));
  return m && Number(m[1]) > 0 ? Number(m[1]) : null;
};
const idsOf = (v: unknown): number[] => (Array.isArray(v) ? v.map(idOf).filter((x): x is number => x != null).slice(0, 20) : []);

/** The number of a picture of a text ("img:103" -> 103); other keys (covers, novel pages) are null. */
export function imageIdOf(mediaKey: string | null | undefined): number | null {
  const m = /^img:(\d{1,10})$/.exec(mediaKey ?? '');
  return m ? Number(m[1]) : null;
}

export function pictureHref(doc: string | null | undefined, imageId: number): string {
  return doc ? `${imagesHref(doc)}&pic=img:${imageId}` : `${imagesHref(null)}?pic=img:${imageId}`;
}

export interface ResultLink { label: string; href: string }

const STORY_KINDS = new Set(['story_range', 'story_write', 'story_mine', 'story_approve', 'story_retire']);
const PICTURE_KINDS = new Set(['picture_passage', 'story_illustrate', 'picture_redraw', 'picture_approve', 'picture_retire']);
const NOVEL_KINDS = new Set(['novel_plan', 'novel_cast', 'novel_draw', 'novel_page_approve', 'novel_approve', 'novel_retire']);

/** Where to see what a request made or touched: from the desk's result, else from what it named. */
export function resultLinks(row: Pick<CornerRequest, 'kind' | 'doc_code' | 'params' | 'result'>): ResultLink[] {
  const doc = row.doc_code;
  const r = row.result ?? {};
  const p = row.params ?? {};
  const out: ResultLink[] = [];
  const add = (label: string, href: string) => { if (!out.some((l) => l.href === href)) out.push({ label, href }); };
  const story = (id: number, label = 'The story') => { if (doc) add(label, storyHref({ doc_code: doc, story_id: id })); };
  const picture = (id: number, label = 'The picture') => add(label, pictureHref(doc, id));
  const novel = (id: number, label = 'The graphic novel') => add(label, novelHref(id));

  // What the desk made.
  const sid = idOf(r.story_id);
  const iid = idOf(r.image_id);
  const nid = idOf(r.novel_id);
  if (sid != null) story(sid);
  if (iid != null) picture(iid);
  if (nid != null) novel(nid);
  const many = (ids: number[], f: (id: number, label: string) => void, what: string) => ids.forEach((id) => f(id, `${what} ${id}`));
  many(idsOf(r.story_ids), story, 'Story');
  many(idsOf(r.image_ids), picture, 'Picture');
  many(idsOf(r.novel_ids), novel, 'Graphic novel');
  const ids = idsOf(r.ids);
  if (STORY_KINDS.has(row.kind)) many(ids, story, 'Story');
  else if (PICTURE_KINDS.has(row.kind)) many(ids, picture, 'Picture');
  else if (NOVEL_KINDS.has(row.kind)) many(ids, novel, 'Graphic novel');

  // What the request named (an episode written, a picture drawn again, a novel's cast ...).
  const ps = idOf(p.story_id);
  const pi = idOf(p.image_id);
  const pn = idOf(p.novel_id);
  if (ps != null) story(ps);
  if (pi != null) picture(pi);
  if (pn != null) novel(pn);
  return out;
}

/** "1-12", "1,3,5-7" -> the page numbers (1 to 16), or null if malformed; as corner._pages. */
export function parsePages(spec: string | null | undefined): number[] | null {
  const v = (spec ?? '').replace(/\s+/g, '');
  if (!/^[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*$/.test(v)) return null;
  const out: number[] = [];
  for (const part of v.split(',')) {
    const [x, y] = part.split('-');
    const a = Number(x);
    const b = y === undefined ? a : Number(y);
    if (a < 1 || b > 16 || b < a) return null;
    for (let i = a; i <= b; i += 1) if (!out.includes(i)) out.push(i);
  }
  return out;
}

/** The estimate as the database will make it (corner._estimate), from what the page knows. */
export function estimateFor(
  kind: Pick<CornerKind, 'cost_bearing' | 'est_usd' | 'unit'> | null | undefined,
  params: Record<string, unknown> = {},
  extra: { english?: number | null; pages?: number | null } = {},
): number {
  if (!kind || !kind.cost_bearing) return 0;
  const est = num(kind.est_usd);
  if (kind.unit === 'chunk') return est * Math.max(1, Math.ceil(num(extra.english) / 150));
  if (kind.unit === 'page') {
    const spec = s(params.pages);
    const n = spec ? (parsePages(spec)?.length ?? 12) : (extra.pages && extra.pages > 0 ? extra.pages : 12);
    return est * n;
  }
  return est;
}

export const aboutUsd = (v: number): string => `about ${formatUsd(v)}`;

/** "never", "just now", "5 minutes ago", "3 hours ago", "2 days ago". */
export function lastSeenText(ts: string | null | undefined, now: number = Date.now()): string {
  if (!ts) return 'never';
  const t = Date.parse(ts);
  if (!Number.isFinite(t)) return 'never';
  const min = Math.floor(Math.max(0, now - t) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min} minute${min === 1 ? '' : 's'} ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} hour${h === 1 ? '' : 's'} ago`;
  const d = Math.floor(h / 24);
  return `${d} day${d === 1 ? '' : 's'} ago`;
}

export function deskIsLate(ts: string | null | undefined, now: number = Date.now()): boolean {
  if (!ts) return true;
  const t = Date.parse(ts);
  return !Number.isFinite(t) || now - t > DESK_LATE_MIN * 60000;
}

/** A passage reference as the desk takes it ("25.2"), or null. */
export function cleanRef(v: string | null | undefined): string | null {
  const a = parseAt(v);
  return a ? `${a.page}.${a.idx}` : null;
}

/** A date and time to read ("9 Oct 2026, 14:05"), or '' for none. */
export function when(ts: string | null | undefined): string {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  try {
    return d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return d.toISOString().slice(0, 16).replace('T', ' ');
  }
}

/** The items of an anthology, read defensively and in their order. */
export function collectionItems(raw: unknown): CollectionItem[] {
  let v: unknown = raw;
  if (typeof raw === 'string') {
    try { v = JSON.parse(raw); } catch { v = null; }
  }
  if (!Array.isArray(v)) return [];
  return v
    .filter((x): x is CollectionItem => !!x && typeof x === 'object' && typeof (x as CollectionItem).doc_code === 'string'
      && typeof (x as CollectionItem).story_id === 'number')
    .map((x) => ({
      ...x,
      picture: x.picture && typeof x.picture === 'object' && typeof x.picture.sha256 === 'string'
        && /^[0-9a-f]{64}$/.test(x.picture.sha256) ? x.picture : null,
    }))
    .sort((a, b) => num(a.pos) - num(b.pos));
}

export const AUDIENCE_LABEL: Record<string, string> = { general: 'for general readers', young: 'for young readers', scholar: 'for scholars' };

/** A story's verify answer, as text for parseVerify (the preview may carry it as text or JSON). */
export function verifyText(v: unknown): string | null {
  if (v == null) return null;
  if (typeof v === 'string') return v;
  try { return JSON.stringify(v); } catch { return null; }
}

export type { MirrorDoc };
