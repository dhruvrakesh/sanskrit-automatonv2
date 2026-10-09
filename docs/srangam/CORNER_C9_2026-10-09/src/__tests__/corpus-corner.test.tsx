/**
 * CORNER_C9_2026_10_09 - the Researchers' Corner: asking the desk, following and deciding requests,
 * the settings, the anthologies, and the desk's buttons on the reading pages. The pure rules
 * first; then the pages against a mocked supabase whose answers are set per database function.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  CORNER_MARK, deskIsLate, estimateFor, formatUsd, imageIdOf, lastSeenText, parsePages, requestSummary, resultLinks,
  statusLabel, statusTone,
} from '@/lib/corner';
import CorpusCorner from '@/pages/corpus/CorpusCorner';
import CorpusAnthology from '@/pages/corpus/CorpusAnthology';
import CorpusStories from '@/pages/corpus/CorpusStories';
import CorpusNav from '@/components/corpus/CorpusNav';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);
const NOW = Date.parse('2026-10-09T12:00:00Z');
const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString();

const ME = (extra: Record<string, unknown> = {}) => ({
  can_request: true, is_editor: false, is_super_admin: false, daily_cap_usd: 2, committed_today: 0.25,
  researchers_need_approval: true, worker_last_seen: recent, worker_info: null, pending: 1, queued: 2, running: 0,
  mine_open: 1, ...extra,
});
const EDITOR = () => ME({ is_editor: true });
const SUPER = () => ME({ is_editor: true, is_super_admin: true });
const READER = () => ME({ can_request: false });

const K = (kind: string, label: string, cost: boolean, editor: boolean, est: number, unit: 'request' | 'page' | 'chunk' = 'request') =>
  ({ kind, label, cost_bearing: cost, editor_only: editor, est_usd: est, unit, enabled: true });
const KINDS = [
  K('story_range', 'A story from passages you choose', true, false, 0.01),
  K('story_write', 'Write a proposed episode', true, false, 0.01),
  K('story_mine', 'Find episodes in a text', true, false, 0.01, 'chunk'),
  K('picture_passage', 'A picture for a passage', true, false, 0.1),
  K('story_illustrate', 'A picture for a story', true, false, 0.11),
  K('picture_redraw', 'Draw a picture again', true, false, 0.1),
  K('novel_plan', 'Plan a graphic novel from a story', true, false, 0.02),
  K('novel_cast', "Draw a graphic novel's cast", true, false, 0.4),
  K('novel_draw', "Draw a graphic novel's pages", true, false, 0.1, 'page'),
  K('story_approve', 'Approve a story', false, true, 0),
  K('story_retire', 'Retire a story', false, true, 0),
  K('picture_approve', 'Approve a picture', false, true, 0),
  K('picture_retire', 'Retire a picture', false, true, 0),
  K('novel_page_approve', "Approve a graphic novel's page", false, true, 0),
  K('novel_approve', 'Approve a graphic novel', false, true, 0),
  K('novel_retire', 'Retire a graphic novel', false, true, 0),
];
const DOC = {
  doc_code: 'nilamata_seg', title: 'Nīlamata Purāṇa', category: 'purana', passages: 900, english: 450, hindi: 400,
  vectors: 0, stories: 3, published: false, synced_at: null,
};
const REQ = (id: number, extra: Record<string, unknown> = {}) => ({
  id, kind: 'story_range', label: 'A story from passages you choose', doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa',
  params: { from: '25.2', to: '25.9', title: 'Vitasta flows', why: null }, note: null, status: 'pending', est_usd: 0.01,
  cost_usd: null, requested_at: '2026-10-09T10:00:00Z', mine: true, requester: null, decided_at: null, decision_note: null,
  started_at: null, finished_at: null, message: null, result: null, preview: null, total: 2, ...extra,
});
const STORY = (id: number, extra: Record<string, unknown> = {}) => ({
  doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa', story_id: id, status: 'approved', title: `Story title ${id}`,
  title_hi: null, why: null, from_page: 25, from_idx: id, to_page: 26, to_idx: 2, from_ord: 300, story_en: 'The goddess flowed.',
  story_hi: 'देवी बही।', quote_sa: 'वितस्ता', quote_ref: '25.7', cites: '["25.7"]', verify: '{"ok": true}', model: 'gemini-2.5-flash',
  approved_at_local: null, updated_at_local: null, ...extra,
});
const SHA = (c: string) => c.repeat(64);
const ITEM = (pos: number, extra: Record<string, unknown> = {}) => ({
  pos, doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa', story_id: 30 + pos, status: 'approved', title: `Tale ${pos}`,
  title_hi: `कथा ${pos}`, story_en: `The English of tale ${pos}.`, story_hi: `कथा ${pos} की हिंदी।`, quote_sa: `श्लोक ${pos}`,
  quote_ref: `25.${pos}`, cites: '["25.1"]', from_page: 25, from_idx: pos, to_page: 26, to_idx: 3, model: 'gemini-2.5-flash',
  picture: null, ...extra,
});
const COLLECTION = (extra: Record<string, unknown> = {}) => ({
  id: 3, title: 'Rivers of Kashmir', title_hi: 'कश्मीर की नदियाँ', intro: 'Tales of the rivers.', audience: 'general',
  status: 'published', mine: false, can_edit: false, created_at: 'x', updated_at: 'y', published_at: 'z',
  items: [ITEM(2), ITEM(1, { picture: { media_key: 'img:9', sha256: SHA('a'), width: 1200, height: 800, status: 'approved', caption_en: 'The river', caption_hi: null, model: 'gemini-3.1-flash-image', has_thumb: true, has_display: true } })],
  ...extra,
});
const COLL_ROW = { id: 3, title: 'Rivers of Kashmir', title_hi: null, audience: 'general', status: 'published', items: 2, mine: false, owner: null, created_at: 'x', updated_at: 'y', published_at: 'z', cover_sha: SHA('b'), cover_has_thumb: true };

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search + l.hash}</output>;
}

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Where />
          <Routes>
            <Route path="/corpus/corner" element={<CorpusCorner />} />
            <Route path="/corpus/anthologies/new" element={<CorpusAnthology />} />
            <Route path="/corpus/anthologies/:collectionId" element={<CorpusAnthology />} />
            <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />
            <Route path="/corpus/:docCode" element={<p>the reader</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

const where = () => screen.getByTestId('where').textContent;

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  vi.stubGlobal('fetch', vi.fn(async () => new Response('jpeg', { status: 200 })));
  Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
});

describe('the rules', () => {
  it('money, statuses and the desk', () => {
    expect(CORNER_MARK).toBe('CORNER_C9_2026_10_09');
    expect(formatUsd(0.1)).toBe('$0.10');
    expect(formatUsd('2')).toBe('$2.00');
    expect(formatUsd(0.004)).toBe('$0.01');
    expect(formatUsd(0)).toBe('$0.00');
    expect(formatUsd(null)).toBe('$0.00');
    expect(statusLabel('pending')).toBe('waiting for an editor');
    expect(statusLabel('approved')).toBe('queued for the desk');
    expect(statusLabel('claimed')).toBe('the desk is working on it');
    expect(statusLabel('running')).toBe('the desk is working on it');
    expect(statusLabel('cancelled')).toBe('withdrawn');
    expect([statusTone('pending'), statusTone('running'), statusTone('done'), statusTone('failed'), statusTone('cancelled')])
      .toEqual(['amber', 'blue', 'green', 'red', 'muted']);
    expect(lastSeenText(null, NOW)).toBe('never');
    expect(lastSeenText('2026-10-09T11:59:40Z', NOW)).toBe('just now');
    expect(lastSeenText('2026-10-09T11:55:00Z', NOW)).toBe('5 minutes ago');
    expect(lastSeenText('2026-10-09T11:59:00Z', NOW)).toBe('1 minute ago');
    expect(lastSeenText('2026-10-09T09:00:00Z', NOW)).toBe('3 hours ago');
    expect(lastSeenText('2026-10-07T12:00:00Z', NOW)).toBe('2 days ago');
    expect(deskIsLate('2026-10-09T11:55:00Z', NOW)).toBe(false);
    expect(deskIsLate('2026-10-09T11:00:00Z', NOW)).toBe(true);
    expect(deskIsLate(null, NOW)).toBe(true);
  });

  it('what a request asks for, and where its results are', () => {
    expect(requestSummary('story_range', { from: '25.2', to: '25.9', title: 'Vitasta flows' })).toBe("Passages 25.2-25.9: 'Vitasta flows'");
    expect(requestSummary('novel_draw', { novel_id: 2, pages: '' })).toMatch(/every page still to be drawn/);
    expect(requestSummary('novel_draw', { novel_id: 2, pages: '1-3' })).toBe('Graphic novel 2: pages 1-3');
    expect(requestSummary('picture_redraw', { image_id: 103 })).toBe('Draw picture img:103 again');
    expect(resultLinks({ kind: 'story_range', doc_code: 'nilamata_seg', params: {}, result: { story_id: 41 } }))
      .toEqual([{ label: 'The story', href: '/corpus/stories/nilamata_seg/41' }]);
    expect(resultLinks({ kind: 'story_illustrate', doc_code: 'nilamata_seg', params: { story_id: 36 }, result: { image_id: 'img:103' } }))
      .toEqual([
        { label: 'The picture', href: '/corpus/images?doc=nilamata_seg&pic=img:103' },
        { label: 'The story', href: '/corpus/stories/nilamata_seg/36' },
      ]);
    expect(resultLinks({ kind: 'picture_redraw', doc_code: null, params: { image_id: 5 }, result: null }))
      .toEqual([{ label: 'The picture', href: '/corpus/images?pic=img:5' }]);
    expect(resultLinks({ kind: 'novel_plan', doc_code: 'd', params: { story_id: 3 }, result: { novel_id: 2 } }).map((l) => l.href))
      .toEqual(['/corpus/novels/2', '/corpus/stories/d/3']);
    expect(resultLinks({ kind: 'story_mine', doc_code: 'd', params: { max: 4 }, result: { ids: [7, 8, 'x'] } }))
      .toEqual([{ label: 'Story 7', href: '/corpus/stories/d/7' }, { label: 'Story 8', href: '/corpus/stories/d/8' }]);
    expect(imageIdOf('img:103')).toBe(103);
    expect(imageIdOf('novel:2:page:1')).toBeNull();
  });

  it('estimates as the database makes them', () => {
    const chunk = KINDS.find((k) => k.kind === 'story_mine');
    const page = KINDS.find((k) => k.kind === 'novel_draw');
    const flat = KINDS.find((k) => k.kind === 'picture_passage');
    const free = KINDS.find((k) => k.kind === 'story_approve');
    expect(estimateFor(chunk, {}, { english: 450 })).toBeCloseTo(0.03);
    expect(estimateFor(chunk, {}, { english: 0 })).toBeCloseTo(0.01);
    expect(estimateFor(page, { pages: '1,3,5-7' })).toBeCloseTo(0.5);
    expect(estimateFor(page, { pages: '' }, { pages: 8 })).toBeCloseTo(0.8);
    expect(estimateFor(page, { pages: '' })).toBeCloseTo(1.2);
    expect(estimateFor(flat, {})).toBeCloseTo(0.1);
    expect(estimateFor(free, {})).toBe(0);
    expect(parsePages('1-3,2,5')).toEqual([1, 2, 3, 5]);
    expect(parsePages('0-3')).toBeNull();
    expect(parsePages('3-1')).toBeNull();
    expect(parsePages('1-17')).toBeNull();
    expect(parsePages('one')).toBeNull();
  });
});

describe('/corpus/corner', () => {
  it('a reader without rights: how to get in, the published anthologies, no forms', async () => {
    sb.byFn.corner_me = ok([READER()]);
    sb.byFn.corner_collections = ok([COLL_ROW]);
    mount('/corpus/corner');
    expect(await screen.findByText(/is for invited researchers and editors/)).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Rivers of Kashmir' })).toHaveAttribute('href', '/corpus/anthologies/3');
    expect(called('corner_collections')[0].args).toEqual({ p_scope: 'published' });
    expect(screen.queryByRole('form')).toBeNull();
    expect(screen.queryByRole('tab')).toBeNull();
    expect(screen.queryByText(/New anthology/)).toBeNull();
    expect(called('corner_requests')).toEqual([]);
    await waitFor(() => expect(document.title).toBe("Researchers' Corner | Working Corpus | Srangam"));
    expect(document.querySelector('meta[name="robots"]')?.getAttribute('content')).toBe('noindex, nofollow');
  });

  it('without C9 it says so quietly', async () => {
    sb.byFn.corner_me = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corner_me without parameters in the schema cache' } };
    mount('/corpus/corner');
    expect(await screen.findByText(/The Researchers' Corner is not available here yet/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('a researcher asks for a story from a deep link, and is told what happens next', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC, { ...DOC, doc_code: 'empty_doc', title: 'Untranslated', english: 0 }]);
    sb.byFn.corner_request_create = ok([{ request_id: 7, request_status: 'pending', est_usd: 0.01, message: "Waiting for an editor's approval." }]);
    mount('/corpus/corner?tab=ask&kind=story_range&doc=nilamata_seg&from=25.2&to=25.9');
    const form = await screen.findByRole('form', { name: 'A story from passages you choose' });
    expect(screen.getByText(/Desk last seen: 5 minutes ago/)).toBeInTheDocument();
    expect(screen.queryByText(/Today:/)).toBeNull();   // the cap is for editors
    expect(screen.queryByRole('tab', { name: /Queue/ })).toBeNull();
    expect(screen.queryByRole('tab', { name: /Settings/ })).toBeNull();
    await waitFor(() => expect(screen.getByLabelText('The text')).toHaveValue('nilamata_seg'));
    expect(within(screen.getByLabelText('The text')).queryByText('Untranslated')).toBeNull();
    expect(within(form).getByLabelText('From passage')).toHaveValue('25.2');
    expect(within(form).getByLabelText('To passage')).toHaveValue('25.9');
    expect(within(form).getByText('about $0.01')).toBeInTheDocument();
    const submit = within(form).getByRole('button', { name: 'Ask the desk' });
    expect(submit).toBeDisabled();   // no title yet
    fireEvent.change(within(form).getByLabelText('A working title'), { target: { value: 'Vitasta flows' } });
    fireEvent.change(within(form).getByLabelText('Note for the editor (optional)'), { target: { value: 'For the river chapter' } });
    fireEvent.click(submit);
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({
      p_kind: 'story_range', p_doc: 'nilamata_seg', p_params: { from: '25.2', to: '25.9', title: 'Vitasta flows', why: '' },
      p_note: 'For the river chapter',
    });
    expect(await within(form.parentElement as HTMLElement).findByText(/Waiting for an editor's approval. \(request #7\)/)).toBeInTheDocument();
    expect(within(form.parentElement as HTMLElement).getByRole('link', { name: 'See your requests' })).toHaveAttribute('href', '/corpus/corner?tab=mine');
  });

  it("the server's reason is shown as it is", async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    sb.byFn.corner_request_create = { data: null, error: { code: '22023', message: 'from and to must be translated passages of this text' } };
    mount('/corpus/corner?tab=ask&kind=story_range&doc=nilamata_seg&from=1.1&to=1.2');
    const form = await screen.findByRole('form', { name: 'A story from passages you choose' });
    fireEvent.change(within(form).getByLabelText('A working title'), { target: { value: 'Something' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Ask the desk' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('from and to must be translated passages of this text');
  });

  it('my requests: a done one with its preview and its story, an open one withdrawn', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_requests = ok([
      REQ(9, {
        status: 'done', cost_usd: 0.012, message: 'Written and checked.', result: { story_id: 41 },
        preview: { story_id: 41, status: 'draft', title: 'Vitastā flows to the sea', title_hi: null, story_en: 'x'.repeat(400), verify: '{"ok": true, "problems": []}' },
      }),
      REQ(8, { status: 'pending', note: 'please' }),
    ]);
    sb.byFn.corner_request_cancel = ok([{ request_status: 'cancelled', message: 'Withdrawn.' }]);
    mount('/corpus/corner?tab=mine');
    expect(await screen.findByText('Vitastā flows to the sea')).toBeInTheDocument();
    expect(called('corner_requests')[0].args).toEqual({ p_scope: 'mine', p_status: null, k: 100, p_offset: 0 });
    const done = screen.getByText('#9').closest('li') as HTMLElement;
    expect(within(done).getByText('done')).toBeInTheDocument();
    expect(within(done).getByText(/Checked against its citations/)).toBeInTheDocument();
    expect(within(done).getByText(/^x{300}\.\.\.$/)).toBeInTheDocument();
    expect(within(done).getByText("Passages 25.2-25.9: 'Vitasta flows'", { exact: false })).toBeInTheDocument();
    expect(within(done).getByRole('link', { name: 'The story' })).toHaveAttribute('href', '/corpus/stories/nilamata_seg/41');
    expect(within(done).getByText(/cost \$0.01/)).toBeInTheDocument();
    expect(within(done).queryByRole('button', { name: 'Withdraw' })).toBeNull();
    const open = screen.getByText('#8').closest('li') as HTMLElement;
    expect(within(open).getByText('waiting for an editor')).toBeInTheDocument();
    fireEvent.click(within(open).getByRole('button', { name: 'Withdraw' }));
    await waitFor(() => expect(called('corner_request_cancel')[0]?.args).toEqual({ p_id: 8 }));
  });

  it('an editor approves and rejects from the queue, and sees the day committed', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_requests = ok([REQ(8, { requester: 'researcher@uni.edu', note: 'For the river chapter', mine: false })]);
    sb.byFn.corner_request_decide = ok([{ request_status: 'approved', message: 'Approved; the desk takes it on its next round.' }]);
    mount('/corpus/corner?tab=queue');
    expect(await screen.findByText('Today: $0.25 of $2.00 committed')).toBeInTheDocument();
    const queue = screen.getByRole('region', { name: 'Waiting for an editor' });
    expect(await within(queue).findByText(/by researcher@uni.edu/)).toBeInTheDocument();
    expect(within(queue).getByText('For the river chapter')).toBeInTheDocument();
    fireEvent.change(within(queue).getByLabelText('Note to the researcher (optional)'), { target: { value: 'Good range' } });
    fireEvent.click(within(queue).getByRole('button', { name: /^Approve/ }));
    await waitFor(() => expect(called('corner_request_decide')).toHaveLength(1));
    expect(called('corner_request_decide')[0].args).toEqual({ p_id: 8, p_approve: true, p_note: 'Good range' });
    await waitFor(() => expect(within(screen.getByRole('region', { name: 'Waiting for an editor' })).getByRole('button', { name: 'Reject' })).not.toBeDisabled());
    fireEvent.click(within(screen.getByRole('region', { name: 'Waiting for an editor' })).getByRole('button', { name: 'Reject' }));
    await waitFor(() => expect(called('corner_request_decide')).toHaveLength(2));
    expect(called('corner_request_decide')[1].args).toMatchObject({ p_id: 8, p_approve: false });
    expect(called('corner_requests').some((c) => c.args.p_scope === 'queue')).toBe(true);
    expect(called('corner_requests').some((c) => c.args.p_scope === 'all' && c.args.k === 50)).toBe(true);
  });

  it('the desk not seen for a while is marked', async () => {
    sb.byFn.corner_me = ok([ME({ worker_last_seen: null })]);
    mount('/corpus/corner?tab=mine');
    expect(await screen.findByText(/Desk last seen: never/)).toBeInTheDocument();
    expect(screen.getByText(/approved requests wait until it is back/)).toBeInTheDocument();
  });

  it('the super admin sets the cap and the approval rule (a scalar answer)', async () => {
    sb.byFn.corner_me = ok([SUPER()]);
    sb.byFn.corner_settings_set = ok('3.50');
    mount('/corpus/corner?tab=settings');
    const cap = await screen.findByLabelText('Dollars a day');
    expect(cap).toHaveValue(2);
    fireEvent.change(cap, { target: { value: '3.5' } });
    fireEvent.click(cap.closest('div.space-y-2')!.querySelector('button')!);
    await waitFor(() => expect(called('corner_settings_set')[0]?.args).toEqual({ p_key: 'daily_cap_usd', p_value: '3.50' }));
    expect(await screen.findByText('Saved: 3.50')).toBeInTheDocument();
    const need = screen.getByRole('checkbox', { name: /wait for an editor/ });
    expect(need).toBeChecked();
    fireEvent.click(need);
    fireEvent.click(need.closest('div.space-y-2')!.querySelector('button')!);
    await waitFor(() => expect(called('corner_settings_set')[1]?.args).toEqual({ p_key: 'researchers_need_approval', p_value: 'false' }));
    fireEvent.change(screen.getByLabelText('Dollars a day'), { target: { value: '80' } });
    fireEvent.click(screen.getByLabelText('Dollars a day').closest('div.space-y-2')!.querySelector('button')!);
    expect(await screen.findByText(/0 to 50, India time/, { selector: '[role="alert"] span' })).toBeInTheDocument();
    expect(called('corner_settings_set')).toHaveLength(2);
  });

  it('the anthologies tab: covers, drafts marked, and a new one', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_collections = ok([COLL_ROW, { ...COLL_ROW, id: 4, title: 'My draft', status: 'draft', mine: true, cover_sha: null, cover_has_thumb: false }]);
    mount('/corpus/corner?tab=anthologies');
    expect(await screen.findByRole('link', { name: 'My draft' })).toHaveAttribute('href', '/corpus/anthologies/4');
    expect(called('corner_collections')[0].args).toEqual({ p_scope: 'all' });
    expect(screen.getByText('draft')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /New anthology/ })).toHaveAttribute('href', '/corpus/anthologies/new');
  });
});

describe('an anthology', () => {
  it('reads in order, with its picture, quotes and sources; prints; readers do not edit it', async () => {
    sb.byFn.corner_me = ok([READER()]);
    sb.byFn.corner_collection = ok([COLLECTION()]);
    const print = vi.fn();
    vi.stubGlobal('print', print);
    mount('/corpus/anthologies/3');
    expect(await screen.findByRole('heading', { level: 1, name: 'Rivers of Kashmir' })).toBeInTheDocument();
    expect(called('corner_collection')[0].args).toEqual({ p_id: 3 });
    const heads = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(heads).toEqual(['Tale 1', 'Tale 2']);
    const one = screen.getByRole('region', { name: 'Tale 1' });
    expect(within(one).getByText('The river')).toBeInTheDocument();
    expect(within(one).getByText(/generated, not a historical source/)).toBeInTheDocument();
    expect(within(one).getByText('श्लोक 1')).toHaveAttribute('lang', 'sa');
    expect(within(one).getByRole('link', { name: '25.1' })).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.1');
    expect(within(one).getByRole('link', { name: /Nīlamata Purāṇa, passages 25.1-26.3/ })).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.1');
    const two = screen.getByRole('region', { name: 'Tale 2' });
    expect(two.className).toContain('print:break-before-page');
    expect(one.className).not.toContain('print:break-before-page');
    fireEvent.click(screen.getByRole('button', { name: 'Hindi' }));
    expect(screen.queryByText('The English of tale 1.')).toBeNull();
    expect(screen.getByText('कथा 1 की हिंदी।')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Print or save as PDF/ }));
    expect(print).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('link', { name: /Edit/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Publish|Retire/ })).toBeNull();
    vi.unstubAllGlobals();
  });

  it('an editor publishes; retiring asks twice', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_collection = ok([COLLECTION({ status: 'draft', can_edit: true })]);
    sb.byFn.corner_collection_publish = ok([{ collection_status: 'published', message: 'Published to the readers of the working corpus.' }]);
    sb.byFn.corner_collection_retire = ok([{ collection_status: 'retired', message: 'Retired.' }]);
    mount('/corpus/anthologies/3');
    expect(await screen.findByRole('link', { name: /Edit/ })).toHaveAttribute('href', '/corpus/anthologies/3?edit=1');
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));
    await waitFor(() => expect(called('corner_collection_publish')[0]?.args).toEqual({ p_id: 3, p_publish: true }));
    expect(await screen.findByText('Published to the readers of the working corpus.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retire' }));
    expect(called('corner_collection_retire')).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: 'Click again to retire it' }));
    await waitFor(() => expect(called('corner_collection_retire')[0]?.args).toEqual({ p_id: 3 }));
    await waitFor(() => expect(where()).toBe('/corpus/corner?tab=anthologies'));
  });

  it('the builder saves the stories in the order chosen', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corpus_reader_stories = ok([STORY(1), STORY(2), STORY(3, { status: 'candidate' })]);
    sb.byFn.corner_collection_save = ok([{ collection_id: 12, collection_status: 'draft' }]);
    mount('/corpus/anthologies/new');
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: 'River tales' } });
    fireEvent.change(screen.getByLabelText('Introduction (optional)'), { target: { value: 'An introduction.' } });
    fireEvent.change(screen.getByLabelText('For'), { target: { value: 'young' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Add "Story title 2"' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add "Story title 1"' }));
    expect(screen.queryByRole('button', { name: 'Add "Story title 3"' })).toBeNull();   // a candidate is not written yet
    expect(screen.getByRole('button', { name: 'Add "Story title 2"' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Move "Story title 1" up' }));
    fireEvent.change(screen.getByLabelText('Find a story'), { target: { value: 'title 1' } });
    expect(screen.queryByRole('button', { name: 'Add "Story title 2"' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(called('corner_collection_save')).toHaveLength(1));
    expect(called('corner_collection_save')[0].args).toEqual({
      p_id: null, p_title: 'River tales', p_title_hi: null, p_intro: 'An introduction.', p_audience: 'young',
      p_items: [{ doc_code: 'nilamata_seg', story_id: 1 }, { doc_code: 'nilamata_seg', story_id: 2 }],
    });
    await waitFor(() => expect(where()).toBe('/corpus/anthologies/12'));
  });

  it('is not made by a reader without rights', async () => {
    sb.byFn.corner_me = ok([READER()]);
    mount('/corpus/anthologies/new');
    expect(await screen.findByText(/is for invited researchers and editors/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Title')).toBeNull();
  });
});

describe('asking the desk from a story', () => {
  it('an editor sees Approve for a draft, and retiring asks twice', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36, { status: 'draft' })]);
    sb.byFn.corner_request_create = ok([{ request_id: 21, request_status: 'approved', est_usd: 0, message: 'Approved; the desk takes it on its next round.' }]);
    mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    expect(await within(bar).findByText('about $0.11')).toBeInTheDocument();
    expect(within(bar).getByRole('button', { name: /Illustrate/ })).toHaveTextContent('about $0.11');
    expect(within(bar).queryByRole('button', { name: 'Write it' })).toBeNull();
    expect(within(bar).queryByRole('link', { name: 'Plan a graphic novel' })).toBeNull();
    fireEvent.click(within(bar).getByRole('button', { name: 'Approve' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({ p_kind: 'story_approve', p_doc: 'nilamata_seg', p_params: { story_id: 36 }, p_note: null });
    expect(await within(bar).findByText(/Approved; the desk takes it on its next round. \(request #21\)/)).toBeInTheDocument();
    fireEvent.click(within(bar).getByRole('button', { name: 'Retire' }));
    expect(called('corner_request_create')).toHaveLength(1);
    fireEvent.click(within(bar).getByRole('button', { name: 'Click again to retire the story' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(2));
    expect(called('corner_request_create')[1].args).toMatchObject({ p_kind: 'story_retire', p_params: { story_id: 36 } });
  });

  it('a researcher plans a novel from an approved story through the Corner', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36)]);
    mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    expect(within(bar).queryByRole('button', { name: 'Approve' })).toBeNull();
    expect(within(bar).queryByRole('button', { name: 'Retire' })).toBeNull();
    expect(within(bar).getByRole('link', { name: 'Plan a graphic novel' }))
      .toHaveAttribute('href', '/corpus/corner?tab=ask&kind=novel_plan&doc=nilamata_seg&story_id=36');
  });

  it('is not there for a reader who may not ask', async () => {
    sb.byFn.corner_me = ok([READER()]);
    sb.byFn.corpus_reader_stories = ok([STORY(36, { status: 'draft' })]);
    mount('/corpus/stories/nilamata_seg/36');
    expect(await screen.findByText('The goddess flowed.', { selector: 'div' })).toBeInTheDocument();
    await waitFor(() => expect(called('corner_me').length).toBeGreaterThan(0));
    expect(screen.queryByRole('group', { name: 'Ask the desk' })).toBeNull();
    expect(called('corner_kinds')).toEqual([]);
  });
});

describe('the corpus tabs', () => {
  it('the Corner is lit on the Corner and on an anthology; the Library is not', () => {
    for (const path of ['/corpus/corner', '/corpus/anthologies/3', '/corpus/anthologies/new']) {
      const { unmount } = render(<MemoryRouter initialEntries={[path]}><CorpusNav /></MemoryRouter>);
      const lit = screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent?.trim());
      expect(lit).toEqual(['Corner']);
      expect(screen.getByRole('link', { name: 'Corner' })).toHaveAttribute('href', '/corpus/corner');
      unmount();
    }
    render(<MemoryRouter initialEntries={['/corpus/markandeya_purana']}><CorpusNav /></MemoryRouter>);
    const names = screen.getAllByRole('link').map((a) => a.textContent?.trim());
    expect(names.indexOf('Corner')).toBe(names.indexOf('Published texts') - 1);
    expect(screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent?.trim())).toEqual(['Library']);
  });
});
