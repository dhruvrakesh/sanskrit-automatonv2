/**
 * CORNER_STATE_S1_2026_10_09 - the Corner knows where things are: the stages of a request and the
 * desk's progress (corner_request_track, and nothing at all while the database does not have it),
 * when the desk comes next, the next steps of a finished request, the desk's report of the mirror,
 * the pictures and its spend (editors), and a request that finishes while the page is open is
 * announced once. The pure rules first; then the page against a mocked supabase, as in
 * corpus-corner.test.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
const toastSpy = vi.hoisted(() => vi.fn());
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));
vi.mock('@/hooks/use-toast', () => ({ toast: toastSpy, useToast: () => ({ toasts: [], toast: toastSpy, dismiss: vi.fn() }) }));

import {
  resultLinks, type CornerKind,
} from '@/lib/corner';
import {
  clockTime, DESK_COMMANDS, DESK_ROOT, finishNotice, IDLE_ME_MS, LIVE_LIST_MS, LIVE_ME_MS, listRefresh, mediaView,
  meRefresh, mirrorView, newlyFinished, nextRound, nextSteps, parseDeskInfo, parseProgress, progressText,
  requestStages, resetTrackMemo, spendView, STATE_MARK,
} from '@/lib/cornerState';
import CorpusCorner from '@/pages/corpus/CorpusCorner';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);
const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString();
/** A local time today (the page shows local times). */
const local = (h: number, m: number, day = 9) => new Date(2026, 9, day, h, m);

const ME = (extra: Record<string, unknown> = {}) => ({
  can_request: true, is_editor: false, is_super_admin: false, daily_cap_usd: 2, committed_today: 0.25,
  researchers_need_approval: true, worker_last_seen: recent, worker_info: null, pending: 1, queued: 2, running: 1,
  mine_open: 1, ...extra,
});

const K = (kind: string, editor: boolean, enabled = true): CornerKind =>
  ({ kind, label: kind, cost_bearing: !editor, editor_only: editor, est_usd: 0.01, unit: 'request', enabled });
const KINDS: CornerKind[] = [
  ...['story_range', 'story_write', 'story_mine', 'picture_passage', 'story_illustrate', 'picture_redraw', 'novel_plan', 'novel_cast', 'novel_draw']
    .map((k) => K(k, false)),
  ...['story_approve', 'story_retire', 'picture_approve', 'picture_retire', 'novel_page_approve', 'novel_approve', 'novel_retire']
    .map((k) => K(k, true)),
];
const RESEARCHER = { isEditor: false, kinds: KINDS };
const EDITOR_V = { isEditor: true, kinds: KINDS };

const REQ = (id: number, extra: Record<string, unknown> = {}) => ({
  id, kind: 'story_range', label: 'A story from passages you choose', doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa',
  params: { from: '25.2', to: '25.9', title: 'Vitasta flows', why: null }, note: null, status: 'pending', est_usd: 0.01,
  cost_usd: null, requested_at: '2026-10-09T10:00:00Z', mine: true, requester: null, decided_at: null, decision_note: null,
  started_at: null, finished_at: null, message: null, result: null, preview: null, total: 1, ...extra,
});
const DOC = {
  doc_code: 'nilamata_seg', title: 'Nīlamata Purāṇa', category: 'purana', passages: 900, english: 450, hindi: 400,
  vectors: 0, stories: 3, published: false, synced_at: null,
};

const T_ASK = '2026-10-09T10:00:00Z';
const T_OK = '2026-10-09T10:05:00Z';
const T_TAKE = '2026-10-09T10:10:00Z';
const T_RUN = '2026-10-09T10:12:00Z';
const T_END = '2026-10-09T10:30:00Z';
const ROW = (status: string, extra: Record<string, unknown> = {}) =>
  ({ status, requested_at: T_ASK, decided_at: null as string | null, started_at: null as string | null, finished_at: null as string | null, ...extra });

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search + l.hash}</output>;
}

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Where />
          <Routes>
            <Route path="/corpus/corner" element={<CorpusCorner />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
  return { qc, ...view };
}

const where = () => screen.getByTestId('where').textContent;

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  toastSpy.mockClear();
  resetTrackMemo();
  vi.stubGlobal('fetch', vi.fn(async () => new Response('jpeg', { status: 200 })));
  Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// ---- the rules ----------------------------------------------------------------------------------

describe('the stages of a request', () => {
  const labels = (r: ReturnType<typeof ROW>, t?: Parameters<typeof requestStages>[1]) => requestStages(r, t).map((s) => s.label);
  const states = (r: ReturnType<typeof ROW>, t?: Parameters<typeof requestStages>[1]) => requestStages(r, t).map((s) => s.state);

  it('the marker', () => {
    expect(STATE_MARK).toBe('CORNER_STATE_S1_2026_10_09');
  });

  it('waiting for an editor, then approved, taken, working', () => {
    expect(labels(ROW('pending'))).toEqual(['Asked', 'Waiting for an editor', 'Taken by the desk', 'Working', 'Done']);
    expect(states(ROW('pending'))).toEqual(['past', 'now', 'ahead', 'ahead', 'ahead']);
    expect(requestStages(ROW('pending'))[1].tone).toBe('amber');
    expect(requestStages(ROW('pending'))[0].at).toBe(T_ASK);

    const approved = requestStages(ROW('approved', { decided_at: T_OK }));
    expect(approved.map((s) => s.label)).toEqual(['Asked', 'Approved', 'Taken by the desk', 'Working', 'Done']);
    expect(approved.map((s) => s.state)).toEqual(['past', 'now', 'ahead', 'ahead', 'ahead']);
    expect(approved.map((s) => s.at)).toEqual([T_ASK, T_OK, null, null, null]);

    const claimed = requestStages(ROW('claimed', { decided_at: T_OK }), { claimed_at: T_TAKE, attempts: 2 });
    expect(claimed.map((s) => s.state)).toEqual(['past', 'past', 'now', 'ahead', 'ahead']);
    expect(claimed[2].at).toBe(T_TAKE);
    expect(claimed[2].note).toBe('attempt 2');
    // untracked: the stage is there, without a time
    expect(requestStages(ROW('claimed', { decided_at: T_OK }))[2]).toMatchObject({ label: 'Taken by the desk', state: 'now', at: null, note: null });

    const running = requestStages(ROW('running', { decided_at: T_OK, started_at: T_RUN }), { claimed_at: T_TAKE });
    expect(running.map((s) => s.state)).toEqual(['past', 'past', 'past', 'now', 'ahead']);
    expect(running.map((s) => s.at)).toEqual([T_ASK, T_OK, T_TAKE, T_RUN, null]);
    expect(running[3].tone).toBe('blue');
  });

  it('done, failed, rejected, withdrawn, and a status it does not know', () => {
    const done = requestStages(ROW('done', { decided_at: T_OK, started_at: T_RUN, finished_at: T_END }), { claimed_at: T_TAKE });
    expect(done.map((s) => s.label)).toEqual(['Asked', 'Approved', 'Taken by the desk', 'Working', 'Done']);
    expect(done.map((s) => s.state)).toEqual(['past', 'past', 'past', 'past', 'now']);
    expect(done.every((s) => s.tone === 'green')).toBe(true);
    expect(done[4].at).toBe(T_END);

    const failed = requestStages(ROW('failed', { decided_at: T_OK, started_at: T_RUN, finished_at: T_END }));
    expect(failed.map((s) => s.label)).toEqual(['Asked', 'Approved', 'Taken by the desk', 'Working', 'Failed']);
    expect(failed[4]).toMatchObject({ state: 'now', tone: 'red', at: T_END });
    // failed after three attempts, never started: no Working stage
    expect(labels(ROW('failed', { decided_at: T_OK, finished_at: T_END }))).toEqual(['Asked', 'Approved', 'Taken by the desk', 'Failed']);

    const rejected = requestStages(ROW('rejected', { decided_at: T_OK }));
    expect(rejected.map((s) => s.label)).toEqual(['Asked', 'Rejected']);
    expect(rejected[1]).toMatchObject({ state: 'now', tone: 'red', at: T_OK });

    expect(labels(ROW('cancelled', { finished_at: T_END }))).toEqual(['Asked', 'Withdrawn']);
    expect(requestStages(ROW('cancelled', { finished_at: T_END }))[1]).toMatchObject({ tone: 'muted', at: T_END });
    expect(labels(ROW('cancelled', { decided_at: T_OK, finished_at: T_END }))).toEqual(['Asked', 'Approved', 'Withdrawn']);

    expect(labels(ROW('odd'))).toEqual(['Asked', 'odd']);
  });

  it("the desk's progress, read defensively", () => {
    const p = parseProgress({ step: 3, of: 12, note: 'Drawing page 3 of 12', at: '2026-10-09T10:20:00Z' });
    expect(p).toEqual({ step: 3, of: 12, note: 'Drawing page 3 of 12', at: '2026-10-09T10:20:00Z' });
    expect(progressText(p)).toBe('Drawing page 3 of 12');
    // the desk's notes without a number (worker 1.1: "Writing the story") get the step count after them
    expect(progressText(parseProgress({ step: 2, of: 3, note: 'Writing the story' }))).toBe('Writing the story (step 2 of 3)');
    expect(progressText(parseProgress('{"step": 3, "of": 12, "note": "Drawing page 3 of 12"}'))).toBe('Drawing page 3 of 12');
    expect(progressText(parseProgress({ step: 2, of: 5 }))).toBe('Step 2 of 5');
    expect(parseProgress({ step: 30, of: 12 })).toMatchObject({ step: 12, of: 12 });
    expect(progressText(parseProgress({ step: 1, of: 0, note: 'Writing' }))).toBe('Writing');
    expect(parseProgress({ step: 1, of: 0 })).toBeNull();
    expect(parseProgress(null)).toBeNull();
    expect(parseProgress('not json')).toBeNull();
    expect(parseProgress([1, 2])).toBeNull();
    expect(progressText(null)).toBeNull();
  });
});

describe('when the desk comes next', () => {
  const seen = local(15, 38).toISOString();
  it('next round, due, away, never', () => {
    expect(nextRound(seen, local(15, 40).getTime())).toEqual({ state: 'next', text: 'next round about 15:48', next: local(15, 48).getTime() });
    expect(nextRound(seen, local(15, 50).getTime()).state).toBe('next');   // two minutes' grace
    expect(nextRound(seen, local(15, 51).getTime())).toMatchObject({ state: 'due', text: 'a round is due' });
    expect(nextRound(seen, local(16, 9).getTime())).toEqual({ state: 'away', text: 'the desk is away - last seen 15:38', next: null });
    expect(nextRound(local(15, 38, 8).toISOString(), local(9, 0).getTime()).text).toBe('the desk is away - last seen 8 Oct 15:38');
    expect(nextRound(null, local(15, 40).getTime())).toEqual({ state: 'never', text: 'the desk has not been seen yet', next: null });
    expect(nextRound('garbage', local(15, 40).getTime()).state).toBe('never');
    expect(nextRound(seen, local(15, 40).getTime(), 15).text).toBe('next round about 15:53');
    expect(nextRound(seen, local(15, 40).getTime(), Number.NaN).text).toBe('next round about 15:48');
  });

  it('local times', () => {
    const now = local(16, 0).getTime();
    expect(clockTime(local(15, 48).toISOString(), now)).toBe('15:48');
    expect(clockTime(local(15, 48, 8).toISOString(), now)).toBe('8 Oct 15:48');
    expect(clockTime(new Date(2025, 9, 8, 15, 48).toISOString(), now)).toBe('8 Oct 2025 15:48');
    expect(clockTime(null, now)).toBe('');
    expect(clockTime('nope', now)).toBe('');
  });

  it('how often the page asks again', () => {
    expect(listRefresh({ ok: true, rows: [{ status: 'done' }, { status: 'running' }] })).toBe(LIVE_LIST_MS);
    expect(LIVE_LIST_MS).toBe(20000);
    expect(listRefresh({ ok: true, rows: [{ status: 'done' }, { status: 'cancelled' }] })).toBe(false);
    expect(listRefresh({ ok: false, rows: [] })).toBe(false);
    expect(listRefresh(undefined)).toBe(false);
    const me = (x: Record<string, unknown>) => ({ ok: true, rows: [ME(x) as never], error: null, refused: false, missing: false });
    expect(meRefresh(me({ mine_open: 1 }))).toBe(LIVE_ME_MS);
    expect(LIVE_ME_MS).toBe(60000);
    expect(meRefresh(me({ mine_open: 0 }))).toBe(IDLE_ME_MS);
    expect(meRefresh(me({ mine_open: 0, is_editor: true, queued: 0, running: 1, pending: 0 }))).toBe(LIVE_ME_MS);
    expect(meRefresh(me({ mine_open: 0, is_editor: true, queued: 0, running: 0, pending: 0 }))).toBe(IDLE_ME_MS);
    expect(meRefresh(undefined)).toBe(LIVE_ME_MS);
  });
});

describe('next steps of a done request', () => {
  const done = (kind: string, result: Record<string, unknown> | null, doc: string | null = 'nilamata_seg') =>
    ({ kind, doc_code: doc, status: 'done', result });
  const ask = (q: string) => `/corpus/corner?tab=ask&${q}`;

  it('episodes found: write one of them', () => {
    expect(nextSteps(done('story_mine', { candidates: [7, 8], count: 2 }), RESEARCHER))
      .toEqual([{ label: 'Write one of the proposed episodes', href: ask('kind=story_write&doc=nilamata_seg') }]);
    expect(nextSteps(done('story_mine', { candidates: [7], count: 1 }), RESEARCHER)[0].href)
      .toBe(ask('kind=story_write&doc=nilamata_seg&story_id=7'));
    expect(nextSteps(done('story_mine', { candidates: [], count: 0 }), RESEARCHER)).toEqual([]);
    expect(nextSteps(done('story_mine', {}), RESEARCHER)).toEqual([]);
    expect(nextSteps(done('story_mine', { candidates: [7] }, null), RESEARCHER)).toEqual([]);
    // the proposed episodes are linked as the desk's results too
    expect(resultLinks({ kind: 'story_mine', doc_code: 'd', params: { max: 4 }, result: { candidates: [7, 8], count: 2 } }).map((l) => l.href))
      .toEqual(['/corpus/stories/d/7', '/corpus/stories/d/8']);
  });

  it('a story written: read it, ask for a picture, and (editors) approve it', () => {
    const r = done('story_range', { story_id: 41, status: 'draft', title: 'Vitasta flows', check_ok: true, problems: [] });
    expect(nextSteps(r, RESEARCHER)).toEqual([
      { label: 'Read the draft', href: '/corpus/stories/nilamata_seg/41' },
      { label: 'Ask for a picture of it', href: ask('kind=story_illustrate&doc=nilamata_seg&story_id=41') },
    ]);
    expect(nextSteps(r, EDITOR_V).map((l) => l.label)).toEqual(['Read the draft', 'Ask for a picture of it', 'Approve it']);
    expect(nextSteps(r, EDITOR_V)[2].href).toBe('/corpus/stories/nilamata_seg/41');
    expect(nextSteps(done('story_write', { story_id: 41, status: 'approved' }), EDITOR_V).map((l) => l.label))
      .toEqual(['Read the draft', 'Ask for a picture of it']);
    expect(nextSteps(done('story_write', { status: 'draft' }), EDITOR_V)).toEqual([]);
    // what corner_kinds() says: a kind switched off, or made an editor's
    const off = { isEditor: false, kinds: KINDS.map((k) => (k.kind === 'story_illustrate' ? { ...k, enabled: false } : k)) };
    expect(nextSteps(r, off).map((l) => l.label)).toEqual(['Read the draft']);
    const editorsOnly = { isEditor: false, kinds: KINDS.map((k) => (k.kind === 'story_illustrate' ? { ...k, editor_only: true } : k)) };
    expect(nextSteps(r, editorsOnly).map((l) => l.label)).toEqual(['Read the draft']);
    // before corner_kinds() answers: the editors' kinds stay the editors'
    expect(nextSteps(r, { isEditor: false, kinds: null }).map((l) => l.label)).toEqual(['Read the draft', 'Ask for a picture of it']);
    expect(nextSteps(r, { isEditor: true }).map((l) => l.label)).toEqual(['Read the draft', 'Ask for a picture of it', 'Approve it']);
  });

  it('a picture: see it, and (editors) approve the draft', () => {
    for (const kind of ['picture_passage', 'story_illustrate', 'picture_redraw']) {
      const r = done(kind, { image_id: 103, status: 'draft', story_id: 36, replaces: 99 });
      expect(nextSteps(r, RESEARCHER)).toEqual([{ label: 'See the picture', href: '/corpus/images?doc=nilamata_seg&pic=img:103' }]);
      expect(nextSteps(r, EDITOR_V)).toEqual([
        { label: 'See the picture', href: '/corpus/images?doc=nilamata_seg&pic=img:103' },
        { label: 'Approve it', href: '/corpus/images?doc=nilamata_seg&pic=img:103' },
      ]);
    }
    expect(nextSteps(done('story_illustrate', { image_id: 103, status: 'approved' }), EDITOR_V).map((l) => l.label)).toEqual(['See the picture']);
    expect(nextSteps(done('picture_passage', { status: 'draft' }), EDITOR_V)).toEqual([]);
  });

  it('a graphic novel: plan, cast, pages, read, approve', () => {
    expect(nextSteps(done('novel_plan', { novel_id: 2, status: 'planned', story_id: 36 }), RESEARCHER))
      .toEqual([{ label: 'Draw the cast', href: ask('kind=novel_cast&doc=nilamata_seg&novel_id=2') }]);
    expect(nextSteps(done('novel_cast', { novel_id: 2 }), RESEARCHER))
      .toEqual([{ label: 'Draw the pages', href: ask('kind=novel_draw&doc=nilamata_seg&novel_id=2') }]);
    expect(nextSteps(done('novel_plan', {}), RESEARCHER)).toEqual([]);
    expect(nextSteps(done('novel_cast', null), RESEARCHER)).toEqual([]);

    expect(nextSteps(done('novel_draw', { novel_id: 2, pages: 'all missing' }), RESEARCHER))
      .toEqual([{ label: 'Read the novel', href: '/corpus/novels/2' }]);
    expect(nextSteps(done('novel_draw', { novel_id: 2, pages: 'all missing' }), EDITOR_V))
      .toEqual([{ label: 'Read the novel', href: '/corpus/novels/2' }, { label: 'Approve the pages', href: '/corpus/novels/2' }]);
    expect(nextSteps(done('novel_draw', { novel_id: 2, pages: '3' }), EDITOR_V)[1]).toEqual({ label: 'Approve page 3', href: '/corpus/novels/2#page-3' });
    expect(nextSteps(done('novel_draw', { novel_id: 2, pages: '1-12' }), EDITOR_V)[1]).toEqual({ label: 'Approve the pages', href: '/corpus/novels/2#page-1' });
    const wholeOnly = { isEditor: true, kinds: KINDS.filter((k) => k.kind !== 'novel_page_approve').concat([{ ...K('novel_page_approve', true), enabled: false }]) };
    expect(nextSteps(done('novel_draw', { novel_id: 2, pages: '' }), wholeOnly)[1]).toEqual({ label: 'Approve the novel', href: '/corpus/novels/2' });
    expect(nextSteps(done('novel_draw', { pages: '3' }), EDITOR_V)).toEqual([]);
  });

  it('only for a done request; nothing for the editors\' own kinds', () => {
    expect(nextSteps({ kind: 'story_range', doc_code: 'd', status: 'running', result: { story_id: 1 } }, EDITOR_V)).toEqual([]);
    expect(nextSteps({ kind: 'story_range', doc_code: 'd', status: 'failed', result: { story_id: 1 } }, EDITOR_V)).toEqual([]);
    expect(nextSteps(done('story_approve', { story_id: 41, status: 'approved' }), EDITOR_V)).toEqual([]);
    expect(nextSteps(done('story_range', '{"story_id": 41}' as never), RESEARCHER).map((l) => l.label)).toEqual(['Read the draft', 'Ask for a picture of it']);
  });
});

describe("the desk's report of itself", () => {
  const now = local(16, 0).getTime();
  const SYNC = {
    every_min: 10,
    mirror: { at: local(15, 30).toISOString(), ok: true, stopped: 'done', error: null, equal: 14, different: 0, client: 'corpus_sync.py 2.4' },
    media: { at: local(14, 32).toISOString(), ok: true, stopped: 'done', error: null, files_needed: 114, files_on_drive: 114, pictures: 57 },
  };
  const INFO = { at: local(15, 58).toISOString(), client: 'corner_worker.py 1.1', budget: { cap: 32, spent: 26.63, left: 5.37, paused: false }, sync: SYNC };

  it('absent, older, and full', () => {
    expect(parseDeskInfo(null)).toEqual({ at: null, client: null, budget: null, sync: null });
    expect(parseDeskInfo('not json')).toEqual({ at: null, client: null, budget: null, sync: null });
    const older = parseDeskInfo({ client: 'corner_worker.py 1.0', at: '2026-10-09T10:00:00Z', budget: { cap: 32, spent: 1, left: 31, paused: false } });
    expect(older.sync).toBeNull();
    expect(older.budget).toEqual({ cap: 32, spent: 1, left: 31, paused: false });
    expect(older.client).toBe('corner_worker.py 1.0');
    const full = parseDeskInfo(JSON.stringify(INFO));
    expect(full.sync?.every_min).toBe(10);
    expect(full.sync?.mirror).toMatchObject({ ok: true, stopped: 'done', equal: 14, different: 0, client: 'corpus_sync.py 2.4' });
    expect(full.sync?.media).toMatchObject({ files_needed: 114, files_on_drive: 114, pictures: 57 });
    expect(parseDeskInfo({ sync: { mirror: null, media: null } }).sync).toEqual({ every_min: 10, mirror: null, media: null });
    expect(parseDeskInfo({ budget: { spent: 1 } }).budget).toBeNull();
    expect(parseDeskInfo({ budget: { cap: '32', spent: '30' } }).budget).toEqual({ cap: 32, spent: 30, left: 2, paused: false });
  });

  it('the mirror and the pictures in words', () => {
    const info = parseDeskInfo(INFO);
    expect(mirrorView(info.sync!.mirror!, now)).toEqual({ state: 'in_step', tone: 'green', text: 'in step at 15:30' });
    expect(mirrorView({ ...info.sync!.mirror!, different: 3 }, now)).toMatchObject({ state: 'behind', text: '3 groups differ at 15:30' });
    expect(mirrorView({ ...info.sync!.mirror!, different: 1 }, now).text).toBe('1 group differs at 15:30');
    expect(mirrorView({ ...info.sync!.mirror!, ok: false, stopped: 'error', error: 'corpus-ingest HTTP 500: boom\nmore' }, now))
      .toEqual({ state: 'stopped', tone: 'red', text: 'stopped at 15:30 (corpus-ingest HTTP 500: boom)' });
    expect(mirrorView({ ...info.sync!.mirror!, ok: false, stopped: 'budget' }, now).text).toBe("stopped at 15:30 (the desk's spend cap)");
    expect(mirrorView({ ...info.sync!.mirror!, error: 'x'.repeat(200) }, now).text).toMatch(/^stopped at 15:30 \(x{77}\.\.\.\)$/);
    expect(mirrorView({ ...info.sync!.mirror!, at: null }, now).text).toBe('in step');

    expect(mediaView(info.sync!.media!, now)).toEqual({ state: 'in_step', tone: 'green', text: '114 of 114 files on Drive at 14:32' });
    expect(mediaView({ ...info.sync!.media!, files_on_drive: 100 }, now)).toMatchObject({ state: 'behind', tone: 'amber', text: '100 of 114 files on Drive at 14:32' });
    expect(mediaView({ ...info.sync!.media!, ok: false, stopped: 'error', error: 'Drive quota exceeded' }, now).text).toBe('stopped at 14:32 (Drive quota exceeded)');
    expect(mediaView({ ...info.sync!.media!, files_needed: null }, now).text).toBe('in step at 14:32');

    expect(spendView(info.budget!)).toEqual({ tone: 'muted', text: '$5.37 of $32 left' });
    expect(spendView({ ...info.budget!, paused: true })).toEqual({ tone: 'red', text: 'paused, $5.37 of $32 left' });
    expect(spendView({ cap: 32, spent: 32, left: 0, paused: false }).tone).toBe('amber');
  });
});

describe('a request that finishes', () => {
  it('is announced once, in words that say what came of it', () => {
    expect(finishNotice({ id: 5, kind: 'story_mine', status: 'done', result: { candidates: [1, 2, 3, 4, 5, 6], count: 6 }, message: '6 episode(s) proposed; an editor or you can ask for each to be written.' }))
      .toEqual({ id: 5, ok: true, title: 'Request #5 is done', detail: '6 episodes proposed', line: 'Request #5 is done: 6 episodes proposed.' });
    expect(finishNotice({ id: 5, kind: 'story_mine', status: 'done', result: { candidates: [9], count: 1 }, message: null }).detail).toBe('1 episode proposed');
    expect(finishNotice({ id: 5, kind: 'story_mine', status: 'done', result: { candidates: [], count: 0 }, message: null }).detail).toBe('no new episode was found');
    expect(finishNotice({ id: 9, kind: 'story_range', status: 'done', result: { story_id: 41 }, message: 'Story #41 written.' }).line)
      .toBe('Request #9 is done: Story #41 written.');
    expect(finishNotice({ id: 4, kind: 'picture_passage', status: 'done', result: { image_id: 103 }, message: 'Picture #103 drawn; an editor approves it.' }).line)
      .toBe('Request #4 is done: Picture #103 drawn.');
    expect(finishNotice({ id: 3, kind: 'novel_draw', status: 'failed', result: null, message: 'the desk could not do it: no pages' }))
      .toMatchObject({ ok: false, title: 'Request #3 failed', line: 'Request #3 failed: the desk could not do it: no pages.' });
    expect(finishNotice({ id: 3, kind: 'novel_draw', status: 'failed', result: null, message: null }).line).toBe('Request #3 failed.');
    const before = new Map([[5, 'running'], [6, 'done'], [7, 'pending'], [9, 'claimed']]);
    const rows = [{ id: 5, status: 'done' }, { id: 6, status: 'done' }, { id: 7, status: 'cancelled' }, { id: 8, status: 'done' }, { id: 9, status: 'failed' }];
    expect(newlyFinished(before, rows).map((r) => r.id)).toEqual([5, 9]);
  });
});

// ---- the page -----------------------------------------------------------------------------------

const TRACK = (id: number, extra: Record<string, unknown> = {}) => ({
  id, status: 'running', decided_at: T_OK, claimed_at: T_TAKE, started_at: T_RUN, finished_at: null, attempts: 1, progress: null, ...extra,
});
const NOVEL_DRAW = REQ(5, {
  kind: 'novel_draw', label: "Draw a graphic novel's pages", params: { novel_id: 2, pages: '' }, status: 'running',
  decided_at: T_OK, started_at: T_RUN,
});

describe('/corpus/corner, state-aware', () => {
  it('a researcher sees the stages with their times, and the desk drawing page 3 of 12', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_requests = ok([NOVEL_DRAW]);
    sb.byFn.corner_request_track = ok([TRACK(5, { progress: { step: 3, of: 12, note: 'Drawing page 3 of 12', at: '2026-10-09T10:20:00Z' } })]);
    mount('/corpus/corner?tab=mine');
    expect(await screen.findByText('Drawing page 3 of 12')).toBeInTheDocument();
    expect(called('corner_request_track')[0].args).toEqual({ p_ids: [5] });
    const stages = screen.getByRole('list', { name: 'Stages of request #5' });
    const items = within(stages).getAllByRole('listitem');
    expect(items.map((li) => li.querySelector('span.flex')?.textContent)).toEqual(['Asked', 'Approved', 'Taken by the desk', 'Working', 'Done (not yet)']);
    expect(items.map((li) => li.querySelector('time')?.textContent ?? null)).toEqual([clockTime(T_ASK), clockTime(T_OK), clockTime(T_TAKE), clockTime(T_RUN), null]);
    expect(items[3]).toHaveAttribute('aria-current', 'step');
    expect(items[4]).not.toHaveAttribute('aria-current');
    const bar = screen.getByRole('progressbar', { name: 'Progress of request #5' });
    expect(bar).toHaveAttribute('aria-valuenow', '3');
    expect(bar).toHaveAttribute('aria-valuemax', '12');
    expect(bar).toHaveAttribute('aria-valuetext', 'Drawing page 3 of 12');
    // the strip: when the desk comes next; the editors' chips and Sync tab are not a researcher's
    expect(screen.getByText(/^Next round about \d{2}:\d{2}$/)).toBeInTheDocument();
    expect(screen.getByText(/Desk last seen: 5 minutes ago/)).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: "The desk's sync" })).toBeNull();
    expect(screen.queryByRole('tab', { name: 'Sync' })).toBeNull();
    expect(screen.getByRole('tab', { name: /My requests/ })).toHaveAttribute('aria-selected', 'true');
  });

  it('without corner_request_track the page is as before: no claim time, no progress, no error', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_requests = ok([NOVEL_DRAW, REQ(6, { status: 'claimed', decided_at: T_OK })]);
    sb.byFn.corner_request_track = {
      data: null,
      error: { code: 'PGRST202', message: 'Could not find the function public.corner_request_track(p_ids) in the schema cache' },
    };
    const { qc } = mount('/corpus/corner?tab=mine');
    const stages = await screen.findByRole('list', { name: 'Stages of request #5' });
    const items = within(stages).getAllByRole('listitem');
    expect(items[2].querySelector('time')).toBeNull();   // the claim time is only known through the track
    expect(items[3].querySelector('time')?.textContent).toBe(clockTime(T_RUN));
    expect(within(screen.getByRole('list', { name: 'Stages of request #6' })).getAllByRole('listitem')[2]).toHaveAttribute('aria-current', 'step');
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.queryByText(/Drawing page/)).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByText(/could not be loaded|not available here yet/)).toBeNull();
    expect(called('corner_request_track')).toHaveLength(1);
    await act(async () => { await qc.invalidateQueries({ queryKey: ['corner', 'requests'] }); });
    await waitFor(() => expect(called('corner_requests').length).toBe(2));
    expect(called('corner_request_track')).toHaveLength(1);   // not asked again for a while
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('an editor sees the sync chips and the Sync tab, with what to run on the desk', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } });
    sb.byFn.corner_me = ok([ME({
      is_editor: true,
      worker_info: {
        at: recent, client: 'corner_worker.py 1.1', budget: { cap: 32, spent: 26.63, left: 5.37, paused: false },
        sync: {
          every_min: 10,
          mirror: { at: local(10, 0).toISOString(), ok: true, stopped: 'done', error: null, equal: 14, different: 0, client: 'corpus_sync.py 2.4' },
          media: { at: local(10, 1).toISOString(), ok: false, stopped: 'error', error: 'Drive quota exceeded', files_needed: 114, files_on_drive: 100, pictures: 57 },
        },
      },
    })]);
    mount('/corpus/corner?tab=sync');
    const chips = await screen.findByRole('list', { name: "The desk's sync" });
    const links = within(chips).getAllByRole('link');
    expect(links.map((a) => a.textContent)).toEqual([
      `Mirror: in step at ${clockTime(local(10, 0).toISOString())}`,
      `Pictures: stopped at ${clockTime(local(10, 1).toISOString())} (Drive quota exceeded)`,
      'Desk spend: $5.37 of $32 left',
    ]);
    expect(links[0]).toHaveAttribute('href', '/corpus/corner?tab=sync');
    expect(screen.getByText('Today: $0.25 of $2.00 committed')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Sync' })).toHaveAttribute('aria-selected', 'true');

    const mirror = screen.getByRole('region', { name: 'The mirror' });
    expect(within(mirror).getByText('in step at ' + clockTime(local(10, 0).toISOString()))).toBeInTheDocument();
    expect(within(mirror).getByText('14 equal, 0 different')).toBeInTheDocument();
    expect(within(mirror).getByText('corpus_sync.py 2.4')).toBeInTheDocument();
    expect(within(mirror).getByText('If it falls out of step, run this on the desk:')).toBeInTheDocument();
    expect(within(mirror).getByText(DESK_COMMANDS.mirror)).toBeInTheDocument();
    const pictures = screen.getByRole('region', { name: 'Pictures' });
    expect(within(pictures).getByText('Not in step. Run this on the desk:')).toBeInTheDocument();
    expect(within(pictures).getByText('100 of 114 files')).toBeInTheDocument();
    expect(within(pictures).getByText('57')).toBeInTheDocument();
    expect(within(pictures).getByText('Drive quota exceeded')).toBeInTheDocument();
    expect(within(pictures).getByText('python scripts\\corpus_media.py --apply')).toBeInTheDocument();
    expect(within(pictures).getByText(DESK_ROOT)).toHaveTextContent('D:\\Sanksrit Automatons\\sanskrit-automatonv2');
    fireEvent.click(within(pictures).getByRole('button', { name: 'Copy python scripts\\corpus_media.py --apply' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('python scripts\\corpus_media.py --apply'));
    expect(await within(pictures).findByText('Copied.')).toBeInTheDocument();
    const deskCard = screen.getAllByRole('region', { name: 'The desk' }).find((r) => r.tagName === 'SECTION' && r.querySelector('h2'));
    expect(deskCard).toBeDefined();
    expect(within(deskCard!).getByText('every 10 minutes')).toBeInTheDocument();
    expect(within(deskCard!).getByText(/^Next round about \d{2}:\d{2}$/)).toBeInTheDocument();
    expect(within(deskCard!).getByText('To start a round now, run this in PowerShell on the desk:')).toBeInTheDocument();
    expect(within(deskCard!).getByText(DESK_COMMANDS.round)).toBeInTheDocument();
    expect(screen.queryByText(/has not reported its sync state/)).toBeNull();
  });

  it('an editor with an older desk: what it reported, and that the sync state is not reported yet', async () => {
    sb.byFn.corner_me = ok([ME({
      is_editor: true, worker_last_seen: null,
      worker_info: { at: recent, client: 'corner_worker.py 1.0', budget: { cap: 32, spent: 32, left: 0, paused: true } },
    })]);
    mount('/corpus/corner?tab=sync');
    expect(await screen.findByText('The desk has not reported its sync state yet (an older desk version).')).toBeInTheDocument();
    const chips = screen.getByRole('list', { name: "The desk's sync" });
    expect(within(chips).getAllByRole('link').map((a) => a.textContent)).toEqual(['Desk spend: paused, $0 of $32 left']);
    expect(within(screen.getByRole('region', { name: 'The mirror' })).getByText('Not reported yet.')).toBeInTheDocument();
    const deskCard = screen.getAllByRole('region', { name: 'The desk' }).find((r) => r.querySelector('h2'))!;
    expect(within(deskCard).getByText('The desk has not been seen yet')).toBeInTheDocument();
    expect(within(deskCard).getByText('The desk is late. Start a round in PowerShell on the desk:')).toBeInTheDocument();
    expect(within(deskCard).getByText('Start-ScheduledTask -TaskName SanskritCornerWorker')).toBeInTheDocument();
  });

  it('a researcher has no Sync tab, even when asked for it', async () => {
    sb.byFn.corner_me = ok([ME({ worker_info: { budget: { cap: 32, spent: 1, left: 31, paused: false } } })]);
    sb.byFn.corner_kinds = ok(KINDS);
    mount('/corpus/corner?tab=sync');
    expect(await screen.findByRole('tab', { name: 'Ask the desk' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByRole('tab', { name: 'Sync' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'The mirror' })).toBeNull();
    expect(screen.queryByRole('list', { name: "The desk's sync" })).toBeNull();
    expect(screen.queryByText(/Desk spend/)).toBeNull();
  });

  it('a request that is done (or failed) between two refetches is announced once, with its next step', async () => {
    sb.byFn.corner_me = ok([ME({ mine_open: 2 })]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    const MINE = REQ(5, { kind: 'story_mine', label: 'Find episodes in a text', params: { max: 6 }, status: 'running', decided_at: T_OK, started_at: T_RUN });
    const PIC = REQ(6, { kind: 'picture_passage', label: 'A picture for a passage', params: { at: '25.7', title: 'The river' }, status: 'running', decided_at: T_OK, started_at: T_RUN });
    sb.byFn.corner_requests = ok([MINE, PIC]);
    sb.byFn.corner_request_track = ok([TRACK(5), TRACK(6)]);
    const { qc } = mount('/corpus/corner?tab=mine');
    expect(await screen.findByText('#5')).toBeInTheDocument();
    expect(toastSpy).not.toHaveBeenCalled();

    sb.byFn.corner_requests = ok([
      { ...MINE, status: 'done', finished_at: T_END, cost_usd: 0.03, result: { candidates: [11, 12, 13, 14, 15, 16], count: 6 }, message: '6 episode(s) proposed; an editor or you can ask for each to be written.' },
      { ...PIC, status: 'failed', finished_at: T_END, message: "the desk could not do it: passage 25.7 is not translated" },
    ]);
    sb.byFn.corner_request_track = ok([TRACK(5, { status: 'done', finished_at: T_END }), TRACK(6, { status: 'failed', finished_at: T_END })]);
    await act(async () => { await qc.invalidateQueries({ queryKey: ['corner', 'requests'] }); });
    const line = await screen.findByText('Request #5 is done: 6 episodes proposed.');
    expect(line.closest('[aria-live="polite"]')).not.toBeNull();
    expect(screen.getByText('Request #6 failed: the desk could not do it: passage 25.7 is not translated.')).toBeInTheDocument();
    expect(toastSpy).toHaveBeenCalledTimes(2);
    expect(toastSpy).toHaveBeenCalledWith({ title: 'Request #5 is done', description: '6 episodes proposed', variant: 'default' });
    expect(toastSpy).toHaveBeenCalledWith(expect.objectContaining({ title: 'Request #6 failed', variant: 'destructive' }));
    const done = screen.getByText('#5').closest('li') as HTMLElement;
    const stages = within(done).getByRole('list', { name: 'Stages of request #5' });
    expect(within(stages).getAllByRole('listitem')[4]).toHaveAttribute('aria-current', 'step');
    expect(within(stages).getAllByRole('listitem')[4].querySelector('time')?.textContent).toBe(clockTime(T_END));
    expect(within(screen.getByText('#6').closest('li') as HTMLElement).getByText('Failed')).toBeInTheDocument();

    // asked again: nothing new to say
    await act(async () => { await qc.invalidateQueries({ queryKey: ['corner', 'requests'] }); });
    await waitFor(() => expect(called('corner_requests').length).toBeGreaterThanOrEqual(3));
    expect(toastSpy).toHaveBeenCalledTimes(2);
    expect(screen.getAllByText('Request #5 is done: 6 episodes proposed.')).toHaveLength(1);

    // the next step opens the Ask form, prefilled
    const next = await within(done).findByRole('group', { name: 'Next steps' });
    const write = within(next).getByRole('link', { name: 'Write one of the proposed episodes' });
    expect(write).toHaveAttribute('href', '/corpus/corner?tab=ask&kind=story_write&doc=nilamata_seg');
    expect(within(done).getByRole('link', { name: 'Story 11' })).toHaveAttribute('href', '/corpus/stories/nilamata_seg/11');
    fireEvent.click(write);
    await waitFor(() => expect(where()).toBe('/corpus/corner?tab=ask&kind=story_write&doc=nilamata_seg'));
    expect(await screen.findByRole('form', { name: 'story_write' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText('The text')).toHaveValue('nilamata_seg'));
  });

  it('the lists are asked again every 20 seconds while a request is open, and not when none is', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_requests = ok([NOVEL_DRAW]);
    mount('/corpus/corner?tab=mine');
    expect(await screen.findByText('#5')).toBeInTheDocument();
    const first = called('corner_requests').length;
    await act(async () => { await vi.advanceTimersByTimeAsync(LIVE_LIST_MS + 500); });
    expect(called('corner_requests').length).toBe(first + 1);
    expect(called('corner_request_track').length).toBe(first + 1);
    sb.byFn.corner_requests = ok([{ ...NOVEL_DRAW, status: 'done', finished_at: T_END }]);
    await act(async () => { await vi.advanceTimersByTimeAsync(LIVE_LIST_MS + 500); });
    const settled = called('corner_requests').length;
    await act(async () => { await vi.advanceTimersByTimeAsync(3 * LIVE_LIST_MS); });
    expect(called('corner_requests').length).toBe(settled);
  });
});
