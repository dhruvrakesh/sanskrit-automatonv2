/**
 * The Researchers' Corner, as it happens - CORNER_STATE_S1_2026_10_09.
 *
 * Where each request is (its stages, with corner_request_track's claim time and progress when the
 * database has it - docs/cloud/C10a_corner_state_2026-10-09.sql - and quietly nothing when it does
 * not), when the desk's next round is due, what to do next with a finished request, and the desk's own
 * report of the mirror, the pictures and its spend (corner_me().worker_info, editors only). Only the
 * Corner's page imports this file; the parts shared with the story, picture and novel pages stay in
 * corner.ts.
 */
import {
  CORNER_HREF, deskIsLate, DESK_LATE_MIN, failed, formatUsd, idOf, idsOf, isOpen, lib, loadRequests, num, parsePages,
  pictureHref, s, statusLabel, when, type CornerKind, type CornerMe, type CornerRequest, type CornerResult,
  type RequestScope, type ResultLink, type Tone,
} from '@/lib/corner';
import { storyHref } from '@/lib/corpusLibrary';
import { novelHref } from '@/lib/corpusMedia';

// ---- CORNER_STATE_S1_2026_10_09: where each request is, and the desk's state ------------------

export const STATE_MARK = 'CORNER_STATE_S1_2026_10_09';
/** The desk's rounds (the task SanskritCornerWorker), unless it reports its own (sync.every_min). */
export const ROUND_MIN = 10;
/** How far past its round the desk may be before the Corner says a round is due. */
export const ROUND_GRACE_MIN = 2;
/** While a listed request is open: the lists with their tracking, and corner_me. */
export const LIVE_LIST_MS = 20 * 1000;
export const LIVE_ME_MS = 60 * 1000;
/** corner_me when nothing is open: slower, but the desk's state on the strip stays true. */
export const IDLE_ME_MS = 5 * 60 * 1000;
export const TRACK_MAX = 100;
/** Once corner_request_track is found missing, it is asked again only after this long. */
const TRACK_RETRY_MS = 10 * 60 * 1000;

/** On the desk (the automaton repo): where its commands run. */
export const DESK_ROOT = 'D:\\Sanksrit Automatons\\sanskrit-automatonv2';
export const DESK_COMMANDS = {
  round: 'Start-ScheduledTask -TaskName SanskritCornerWorker',
  mirror: 'python scripts\\corpus_sync.py --apply',
  media: 'python scripts\\corpus_media.py --apply',
} as const;

export interface TrackProgress { step: number | null; of: number | null; note: string | null; at: string | null }

export interface CornerTrack {
  id: number; status: string | null; decided_at: string | null; claimed_at: string | null; started_at: string | null;
  finished_at: string | null; attempts: number | null; progress: TrackProgress | null;
}

/** A listed request with what corner_request_track says of it (null: not tracked). */
export type LiveRequest = CornerRequest & { track: CornerTrack | null };

const tsOf = (v: unknown): string | null => (typeof v === 'string' && v.trim() && Number.isFinite(Date.parse(v)) ? v : null);
const intOf = (v: unknown): number | null => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isInteger(n) ? n : null;
};
const numOf = (v: unknown): number | null => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
};
const textOf = (v: unknown, n = 500): string | null => (typeof v === 'string' && v.trim() ? v.trim().slice(0, n) : null);
/** A JSON object, or its text; anything else is null. */
const objOf = (v: unknown): Record<string, unknown> | null => {
  let x = v;
  if (typeof v === 'string') {
    try { x = JSON.parse(v); } catch { return null; }
  }
  return x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : null;
};

/** The desk's progress on a request ({"step", "of", "note", "at"}), read defensively. */
export function parseProgress(raw: unknown): TrackProgress | null {
  const p = objOf(raw);
  if (!p) return null;
  const of = intOf(p.of);
  const step = intOf(p.step);
  const counted = of != null && of > 0 && step != null;
  const note = textOf(p.note, 200);
  if (!counted && !note) return null;
  return { step: counted ? Math.min(Math.max(step, 0), of) : null, of: counted ? of : null, note, at: tsOf(p.at) };
}

/** "Drawing page 3 of 12": the desk's note, counted; a note with its own numbers is kept as it is. */
export function progressText(p: TrackProgress | null | undefined): string | null {
  if (!p) return null;
  const counted = p.step != null && p.of != null;
  if (p.note && (/\d/.test(p.note) || !counted)) return p.note;
  if (counted) return p.note ? `${p.note} (step ${p.step} of ${p.of})` : `Step ${p.step} of ${p.of}`;
  return null;
}

function trackRow(x: unknown): CornerTrack | null {
  const r = objOf(x);
  const id = r ? intOf(r.id) : null;
  if (!r || id == null) return null;
  return {
    id, status: textOf(r.status, 40), decided_at: tsOf(r.decided_at), claimed_at: tsOf(r.claimed_at),
    started_at: tsOf(r.started_at), finished_at: tsOf(r.finished_at), attempts: intOf(r.attempts),
    progress: parseProgress(r.progress),
  };
}

export function loadTrack(ids: number[]): Promise<CornerResult<CornerTrack>> {
  const clean = [...new Set(ids.filter((i) => Number.isInteger(i) && i > 0))].slice(0, TRACK_MAX);
  return lib<CornerTrack>('corner_request_track', { p_ids: clean });
}

let trackGoneUntil = 0;
/** For tests: forget that corner_request_track was missing. */
export function resetTrackMemo(): void {
  trackGoneUntil = 0;
}

/** A list of requests with their tracking. The list is the answer (its errors are the page's);
 *  the tracking only adds to it, and when the database has no corner_request_track yet (or it
 *  fails) the rows come back untracked, as before, without a word. */
export async function loadLiveRequests(scope: RequestScope, o: { status?: string | null; k?: number; offset?: number } = {}): Promise<CornerResult<LiveRequest>> {
  const r = await loadRequests(scope, o);
  if (!r.ok) return { ...r, rows: [] };
  const ids = r.rows.map((x) => x?.id).filter((i): i is number => Number.isInteger(i) && i > 0);
  const byId = new Map<number, CornerTrack>();
  if (ids.length && Date.now() >= trackGoneUntil) {
    const t = await loadTrack(ids);
    if (t.ok) {
      for (const x of t.rows) {
        const row = trackRow(x);
        if (row) byId.set(row.id, row);
      }
    } else if (t.missing) {
      trackGoneUntil = Date.now() + TRACK_RETRY_MS;
    }
  }
  return { ...r, rows: r.rows.map((x) => ({ ...x, track: byId.get(x.id) ?? null })) };
}

/** How often a list of requests is asked again: while one of them is open, every 20 seconds. */
export function listRefresh(d: { ok: boolean; rows: Pick<CornerRequest, 'status'>[] } | undefined): number | false {
  return d?.ok && d.rows.some((r) => isOpen(r.status)) ? LIVE_LIST_MS : false;
}

/** corner_me: every minute while something is open (the viewer's, or for editors anyone's), else
 *  every five minutes; as before (every minute) while it has no answer. */
export function meRefresh(d: CornerResult<CornerMe> | undefined): number {
  const m = d?.ok ? d.rows[0] : undefined;
  if (!m) return LIVE_ME_MS;
  const open = num(m.mine_open) > 0 || (!!m.is_editor && num(m.pending) + num(m.queued) + num(m.running) > 0);
  return open ? LIVE_ME_MS : IDLE_ME_MS;
}

/** Local time to read: "15:48" today, "7 Oct 15:48" another day, '' for none. */
export function clockTime(ts: string | number | null | undefined, now: number = Date.now()): string {
  if (ts == null || ts === '') return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  const n = new Date(now);
  try {
    const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    if (d.toDateString() === n.toDateString()) return time;
    const date = d.toLocaleDateString('en-GB', d.getFullYear() === n.getFullYear()
      ? { day: 'numeric', month: 'short' } : { day: 'numeric', month: 'short', year: 'numeric' });
    return `${date} ${time}`;
  } catch {
    return d.toISOString().slice(0, 16).replace('T', ' ');
  }
}

export type RoundState = 'never' | 'away' | 'due' | 'next';
export interface Round { state: RoundState; text: string; next: number | null }

/** When the desk comes next: "next round about 15:48", "a round is due" (more than two minutes
 *  past), "the desk is away - last seen 15:02" (more than DESK_LATE_MIN), or never seen. */
export function nextRound(lastSeen: string | null | undefined, now: number = Date.now(), everyMin: number = ROUND_MIN): Round {
  const t = lastSeen ? Date.parse(lastSeen) : NaN;
  if (!Number.isFinite(t)) return { state: 'never', text: 'the desk has not been seen yet', next: null };
  if (deskIsLate(lastSeen, now)) return { state: 'away', text: `the desk is away - last seen ${clockTime(t, now)}`, next: null };
  const every = Number.isFinite(everyMin) && everyMin >= 1 && everyMin <= 24 * 60 ? everyMin : ROUND_MIN;
  const next = t + every * 60000;
  if (now > next + ROUND_GRACE_MIN * 60000) return { state: 'due', text: 'a round is due', next };
  return { state: 'next', text: `next round about ${clockTime(next, now)}`, next };
}

export type StageKey = 'asked' | 'approved' | 'claimed' | 'working' | 'done';
/** past: reached; now: where the request is (or how it ended); ahead: not yet. */
export type StageState = 'past' | 'now' | 'ahead';
export interface Stage { key: StageKey; label: string; at: string | null; state: StageState; tone: Tone; note: string | null }

const STAGE_LABELS: Record<StageKey, string> = {
  asked: 'Asked', approved: 'Approved', claimed: 'Taken by the desk', working: 'Working', done: 'Done',
};

/** Asked -> Approved -> Taken by the desk -> Working -> Done, each with its time when known; or how
 *  it stopped (Waiting for an editor, Rejected, Withdrawn, Failed) in the place it stopped. */
export function requestStages(
  r: Pick<CornerRequest, 'status' | 'requested_at' | 'decided_at' | 'started_at' | 'finished_at'>,
  t?: Partial<Pick<CornerTrack, 'decided_at' | 'claimed_at' | 'started_at' | 'finished_at' | 'attempts'>> | null,
): Stage[] {
  const at: Record<StageKey, string | null> = {
    asked: tsOf(r.requested_at),
    approved: tsOf(r.decided_at) ?? tsOf(t?.decided_at),
    claimed: tsOf(t?.claimed_at),
    working: tsOf(r.started_at) ?? tsOf(t?.started_at),
    done: tsOf(r.finished_at) ?? tsOf(t?.finished_at),
  };
  const stage = (key: StageKey, state: StageState, tone: Tone, label = STAGE_LABELS[key], time: string | null = at[key]): Stage =>
    ({ key, label, at: state === 'ahead' ? null : time, state, tone, note: null });
  const past = (key: StageKey, tone: Tone = 'blue') => stage(key, 'past', tone);
  const ahead = (key: StageKey) => stage(key, 'ahead', 'muted');
  let out: Stage[];
  switch (r.status) {
    case 'pending':
      out = [past('asked'), stage('approved', 'now', 'amber', 'Waiting for an editor', null), ahead('claimed'), ahead('working'), ahead('done')];
      break;
    case 'approved':
      out = [past('asked'), stage('approved', 'now', 'blue'), ahead('claimed'), ahead('working'), ahead('done')];
      break;
    case 'claimed':
      out = [past('asked'), past('approved'), stage('claimed', 'now', 'blue'), ahead('working'), ahead('done')];
      break;
    case 'running':
      out = [past('asked'), past('approved'), past('claimed'), stage('working', 'now', 'blue'), ahead('done')];
      break;
    case 'done':
      out = [past('asked', 'green'), past('approved', 'green'), past('claimed', 'green'), past('working', 'green'), stage('done', 'now', 'green')];
      break;
    case 'failed':
      out = [past('asked'), past('approved'), past('claimed'), ...(at.working ? [past('working')] : []), stage('done', 'now', 'red', 'Failed')];
      break;
    case 'rejected':
      out = [past('asked'), stage('approved', 'now', 'red', 'Rejected')];
      break;
    case 'cancelled':
      out = [past('asked'), ...(at.approved ? [past('approved')] : []), stage('done', 'now', 'muted', 'Withdrawn')];
      break;
    default:
      out = [past('asked'), stage('approved', 'now', 'muted', statusLabel(r.status), null)];
  }
  const tries = t?.attempts ?? null;
  if (tries != null && tries > 1) {
    const c = out.find((x) => x.key === 'claimed' && x.state !== 'ahead');
    if (c) c.note = `attempt ${tries}`;
  }
  return out;
}

/** Kinds only an editor may ask for, when corner_kinds() has not said. */
export const EDITOR_KINDS: ReadonlySet<string> = new Set([
  'story_approve', 'story_retire', 'picture_approve', 'picture_retire', 'novel_page_approve', 'novel_approve', 'novel_retire',
]);

export interface Viewer { isEditor: boolean; kinds?: readonly Pick<CornerKind, 'kind' | 'enabled' | 'editor_only'>[] | null }

/** May this viewer ask for this kind: as corner_kinds() says, else editors' kinds for editors only. */
export function mayAsk(kind: string, v: Viewer): boolean {
  const k = v.kinds?.find((x) => x && x.kind === kind);
  if (k) return k.enabled !== false && (!k.editor_only || v.isEditor);
  return !EDITOR_KINDS.has(kind) || v.isEditor;
}

/** A deep link that opens the Ask form of a kind, prefilled (as DeskActions' "Plan a graphic novel"). */
export function askHref(kind: string, doc: string, extra: Record<string, string | number> = {}): string {
  const more = Object.entries(extra).map(([k, v]) => `&${k}=${encodeURIComponent(String(v))}`).join('');
  return `${CORNER_HREF}?tab=ask&kind=${kind}&doc=${encodeURIComponent(doc)}${more}`;
}

/** What a viewer can do next with a finished request, from what the desk reported (the result keys
 *  corner_worker.py writes); a step whose key is missing, or that the viewer may not ask for, is left out.
 *  The editors' approvals open the page where the desk's Approve button is (the story, the picture,
 *  the novel), so it is read before it is approved. */
export function nextSteps(row: Pick<CornerRequest, 'kind' | 'doc_code' | 'status' | 'result'>, v: Viewer): ResultLink[] {
  if (row.status !== 'done') return [];
  const doc = row.doc_code;
  const r = objOf(row.result) ?? {};
  const out: ResultLink[] = [];
  const ask = (kind: string, label: string, extra: Record<string, string | number> = {}) => {
    if (doc && mayAsk(kind, v)) out.push({ label, href: askHref(kind, doc, extra) });
  };
  const draft = r.status == null || r.status === 'draft';
  const sid = idOf(r.story_id);
  const iid = idOf(r.image_id);
  const nid = idOf(r.novel_id);
  switch (row.kind) {
    case 'story_mine': {
      const ids = idsOf(r.candidates);
      if (ids.length > 0 || num(r.count) > 0) ask('story_write', 'Write one of the proposed episodes', ids.length === 1 ? { story_id: ids[0] } : {});
      break;
    }
    case 'story_range':
    case 'story_write':
      if (sid != null && doc) {
        const href = storyHref({ doc_code: doc, story_id: sid });
        out.push({ label: 'Read the draft', href });
        ask('story_illustrate', 'Ask for a picture of it', { story_id: sid });
        if (draft && mayAsk('story_approve', v)) out.push({ label: 'Approve it', href });
      }
      break;
    case 'picture_passage':
    case 'story_illustrate':
    case 'picture_redraw':
      if (iid != null) {
        const href = pictureHref(doc, iid);
        out.push({ label: 'See the picture', href });
        if (draft && mayAsk('picture_approve', v)) out.push({ label: 'Approve it', href });
      }
      break;
    case 'novel_plan':
      if (nid != null) ask('novel_cast', 'Draw the cast', { novel_id: nid });
      break;
    case 'novel_cast':
      if (nid != null) ask('novel_draw', 'Draw the pages', { novel_id: nid });
      break;
    case 'novel_draw':
      if (nid != null) {
        const pages = typeof r.pages === 'string' ? parsePages(r.pages) : null;
        out.push({ label: 'Read the novel', href: novelHref(nid) });
        if (mayAsk('novel_page_approve', v)) {
          out.push(pages && pages.length === 1
            ? { label: `Approve page ${pages[0]}`, href: novelHref(nid, pages[0]) }
            : { label: 'Approve the pages', href: novelHref(nid, pages?.[0]) });
        } else if (mayAsk('novel_approve', v)) {
          out.push({ label: 'Approve the novel', href: novelHref(nid) });
        }
      }
      break;
    default:
      break;
  }
  return out;
}

export const FINISHED: readonly string[] = ['done', 'failed'];

/** The requests that were open when last seen and are done or failed now. */
export function newlyFinished<T extends Pick<CornerRequest, 'id' | 'status'>>(before: ReadonlyMap<number, string>, rows: readonly T[]): T[] {
  return rows.filter((r) => !!r && FINISHED.includes(r.status) && isOpen(before.get(r.id)));
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const firstClause = (s: string | null | undefined): string | null => {
  const c = (s ?? '').trim().split(/;\s|\.\s|\n/)[0].replace(/\.$/, '').trim();
  return c ? (c.length > 160 ? `${c.slice(0, 157).trimEnd()}...` : c) : null;
};

export interface FinishNotice { id: number; ok: boolean; title: string; detail: string | null; line: string }

/** "Request #5 is done: 6 episodes proposed." or "Request #5 failed: <the desk's reason>." */
export function finishNotice(row: Pick<CornerRequest, 'id' | 'kind' | 'status' | 'result' | 'message'>): FinishNotice {
  const ok = row.status === 'done';
  const r = objOf(row.result) ?? {};
  let detail: string | null = null;
  if (ok && row.kind === 'story_mine') {
    const n = intOf(r.count) ?? (Array.isArray(r.candidates) ? r.candidates.length : null);
    if (n != null) detail = n > 0 ? `${plural(n, 'episode')} proposed` : 'no new episode was found';
  }
  detail = detail ?? firstClause(row.message);
  const title = ok ? `Request #${row.id} is done` : `Request #${row.id} failed`;
  return { id: row.id, ok, title, detail, line: detail ? `${title}: ${detail}.` : `${title}.` };
}

// the desk's report of itself (corner_me().worker_info, editors only)

export interface DeskBudget { cap: number; spent: number; left: number; paused: boolean }
interface RunBase { at: string | null; ok: boolean | null; stopped: string | null; error: string | null }
export interface MirrorRun extends RunBase { equal: number | null; different: number | null; client: string | null }
export interface MediaRun extends RunBase { files_needed: number | null; files_on_drive: number | null; pictures: number | null }
export interface DeskSync { every_min: number; mirror: MirrorRun | null; media: MediaRun | null }
export interface DeskInfo { at: string | null; client: string | null; budget: DeskBudget | null; sync: DeskSync | null }

const runBase = (x: Record<string, unknown>): RunBase => ({
  at: tsOf(x.at),
  ok: typeof x.ok === 'boolean' ? x.ok : null,
  stopped: typeof x.stopped === 'string' ? textOf(x.stopped, 40) : x.stopped === true ? 'stopped' : null,
  error: textOf(x.error, 2000),
});

/** worker_info read defensively: anything absent (an older desk) is null. */
export function parseDeskInfo(raw: unknown): DeskInfo {
  const w = objOf(raw);
  if (!w) return { at: null, client: null, budget: null, sync: null };
  const b = objOf(w.budget);
  const cap = b ? numOf(b.cap) : null;
  let budget: DeskBudget | null = null;
  if (b && cap != null) {
    const spent = numOf(b.spent) ?? 0;
    budget = { cap, spent, left: numOf(b.left) ?? Math.max(0, cap - spent), paused: b.paused === true };
  }
  const s = objOf(w.sync);
  let sync: DeskSync | null = null;
  if (s) {
    const m = objOf(s.mirror);
    const d = objOf(s.media);
    const every = intOf(s.every_min);
    sync = {
      every_min: every != null && every >= 1 && every <= 24 * 60 ? every : ROUND_MIN,
      mirror: m ? { ...runBase(m), equal: intOf(m.equal), different: intOf(m.different), client: textOf(m.client, 120) } : null,
      media: d ? { ...runBase(d), files_needed: intOf(d.files_needed), files_on_drive: intOf(d.files_on_drive), pictures: intOf(d.pictures) } : null,
    };
  }
  return { at: tsOf(w.at), client: textOf(w.client, 120), budget, sync };
}

export type RunState = 'in_step' | 'behind' | 'stopped';
export interface RunView { state: RunState; tone: Tone; text: string }

const shortError = (e: string | null, n = 80): string | null => {
  const line = (e ?? '').split('\n')[0].trim();
  if (!line) return null;
  return line.length > n ? `${line.slice(0, n - 3).trimEnd()}...` : line;
};
const brokeOff = (x: RunBase) => (x.stopped != null && x.stopped !== 'done') || !!x.error;
const stoppedView = (x: RunBase, atText: string): RunView => {
  const why = shortError(x.error) ?? (x.stopped === 'budget' ? "the desk's spend cap" : null);
  return { state: 'stopped', tone: 'red', text: `stopped${atText}${why ? ` (${why})` : ''}` };
};

/** The mirror's last run: "in step at 15:30", "3 groups differ at 15:30", "stopped at 14:32 (why)". */
export function mirrorView(m: MirrorRun, now: number = Date.now()): RunView {
  const at = clockTime(m.at, now);
  const atText = at ? ` at ${at}` : '';
  if (brokeOff(m)) return stoppedView(m, atText);
  const diff = m.different ?? 0;
  if (diff > 0) return { state: 'behind', tone: 'amber', text: `${plural(diff, 'group')} ${diff === 1 ? 'differs' : 'differ'}${atText}` };
  if (m.ok === false) return stoppedView(m, atText);
  return { state: 'in_step', tone: 'green', text: `in step${atText}` };
}

/** The pictures' last run: "114 of 114 files on Drive at 14:32", or "stopped at 14:32 (why)". */
export function mediaView(m: MediaRun, now: number = Date.now()): RunView {
  const at = clockTime(m.at, now);
  const atText = at ? ` at ${at}` : '';
  if (brokeOff(m)) return stoppedView(m, atText);
  const need = m.files_needed;
  const have = m.files_on_drive;
  const files = need != null && have != null ? `${have} of ${need} files on Drive${atText}` : null;
  if (files && have! < need!) return { state: 'behind', tone: 'amber', text: files };
  if (m.ok === false) return stoppedView(m, atText);
  return { state: 'in_step', tone: 'green', text: files ?? `in step${atText}` };
}

/** "$32", "$5.37". */
export const usdShort = (v: unknown): string => (Number.isInteger(num(v)) ? `$${num(v)}` : formatUsd(v));

/** The desk's own spend cap: "$5.37 of $32 left", paused or not. */
export function spendView(b: DeskBudget): { tone: Tone; text: string } {
  const text = `${usdShort(b.left)} of ${usdShort(b.cap)} left`;
  if (b.paused) return { tone: 'red', text: `paused, ${text}` };
  return { tone: b.left <= 0 ? 'amber' : 'muted', text };
}
