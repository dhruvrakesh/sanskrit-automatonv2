/**
 * CORNER_C10_MAIL_2026_10_09 - the Corner level with the desk: the eight kinds of C10b (edit a story,
 * a picture's words or a novel's page; check a story again; ideas for pictures and a cover; draw an
 * idea; restore a retired picture) and the novels' "again" (redo). The pure rules first; then the
 * reading pages' desk bar (its edit form is loaded only when Edit is clicked, starts from what the
 * page shows, and sends only what changed) and the Corner's new forms and panels, against a mocked
 * supabase, as in corpus-corner.test.tsx. Before C10b nothing new is offered.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
type Invoke = { fn: string; o: unknown };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[], invokes: [] as Invoke[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: {
      invoke: (fn: string, o: unknown) => {
        sb.invokes.push({ fn, o });
        return Promise.resolve({ data: { ok: true, result: { configured: true, claimed: 0, sent: 0, failed: 0 } }, error: null });
      },
    },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));
vi.mock('@/hooks/use-toast', () => ({ toast: vi.fn(), useToast: () => ({ toasts: [], toast: vi.fn(), dismiss: vi.fn() }) }));

import {
  C10_KINDS, C10_MARK, kindUsable, requestSummary, resultLinks,
} from '@/lib/corner';
import {
  changedFields, editFields, fieldProblem, ideaRow, ideaState, mayEdit, parseIdeas, PICTURE_FIELDS, STORY_FIELDS,
} from '@/lib/cornerC10';
import { resetMailMemo } from '@/lib/cornerMail';
import { resetTrackMemo } from '@/lib/cornerState';
import CorpusCorner from '@/pages/corpus/CorpusCorner';
import CorpusStories from '@/pages/corpus/CorpusStories';
import CorpusImages from '@/pages/corpus/CorpusImages';
import CorpusNovels from '@/pages/corpus/CorpusNovels';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);
const flushes = () => sb.invokes.filter((i) => i.fn === 'corner-mail');
const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString();
const SHA = (c: string) => c.repeat(64);

const ME = (extra: Record<string, unknown> = {}) => ({
  can_request: true, is_editor: false, is_super_admin: false, daily_cap_usd: 2, committed_today: 0.25,
  researchers_need_approval: true, worker_last_seen: recent, worker_info: null, pending: 0, queued: 0, running: 0,
  mine_open: 0, ...extra,
});
const EDITOR = () => ME({ is_editor: true });

const K = (kind: string, cost: boolean, editor: boolean, est: number, unit: 'request' | 'page' | 'chunk' = 'request') =>
  ({ kind, label: kind, cost_bearing: cost, editor_only: editor, est_usd: est, unit, enabled: true });
const C9_KINDS = [
  K('story_range', true, false, 0.01), K('story_write', true, false, 0.01), K('story_mine', true, false, 0.01, 'chunk'),
  K('picture_passage', true, false, 0.1), K('story_illustrate', true, false, 0.11), K('picture_redraw', true, false, 0.1),
  K('novel_plan', true, false, 0.02), K('novel_cast', true, false, 0.4), K('novel_draw', true, false, 0.1, 'page'),
  K('story_approve', false, true, 0), K('story_retire', false, true, 0), K('picture_approve', false, true, 0),
  K('picture_retire', false, true, 0), K('novel_page_approve', false, true, 0), K('novel_approve', false, true, 0),
  K('novel_retire', false, true, 0),
];
const KINDS = [
  ...C9_KINDS,
  { ...K('story_edit', false, false, 0), label: 'Edit a story' },
  { ...K('story_verify', false, false, 0), label: 'Check a story against its citations' },
  { ...K('picture_ideas', true, false, 0.02), label: 'Ideas for pictures in a text' },
  { ...K('picture_cover', true, false, 0.01), label: 'An idea for a cover' },
  { ...K('picture_draw', true, false, 0.1), label: 'Draw an idea' },
  { ...K('picture_edit', false, false, 0), label: "Edit a picture's words" },
  { ...K('picture_restore', false, true, 0), label: 'Restore a retired picture' },
  { ...K('novel_page_edit', false, false, 0), label: "Edit a graphic novel's page" },
];
const DOC = {
  doc_code: 'nilamata_seg', title: 'Nilamata Purana', category: 'purana', passages: 900, english: 450, hindi: 400,
  vectors: 0, stories: 3, published: false, synced_at: null,
};
const STORY = (id: number, extra: Record<string, unknown> = {}) => ({
  doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', story_id: id, status: 'draft', title: 'The river goddess',
  title_hi: 'Nadi devi', why: null, from_page: 25, from_idx: 7, to_page: 26, to_idx: 2, from_ord: 300,
  story_en: 'The goddess flowed down from the mountain to the plain.', story_hi: 'Devi bahi.', quote_sa: 'vitasta', quote_ref: '25.7',
  cites: '["25.7"]', verify: '{"ok": true}', model: 'gemini-2.5-flash', approved_at_local: null, updated_at_local: null, ...extra,
});
const PIC = (extra: Record<string, unknown> = {}) => ({
  media_key: 'img:103', doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', kind: 'generated', status: 'draft',
  title: 'The river at dawn', caption_en: 'The river at dawn.', caption_hi: null, context_note: 'Drawn from 25.7.', anchor_page: 25,
  anchor_idx: 7, anchor_verse_ref: null, story_id: null, width: 1200, height: 800, sha256: SHA('a'), has_thumb: true,
  has_display: true, model: 'gemini-3.1-flash-image', license: 'CC BY 4.0', approved_at_local: null, total: 1, ...extra,
});
const PLAN = {
  title: 'The journey', title_hi: null, cast: [{ name: 'Devotee', look: 'A devout brahmin' }],
  pages: [
    { n: 1, scene: 'A riverbank at dawn.', caption: 'A brahmin prayed. [25.7]', caption_hi: 'Prarthana. [25.7]', speech: [], cites: ['25.7'] },
    { n: 2, scene: 'The river runs to the sea.', caption: 'She flowed on. [25.13]', caption_hi: null, speech: [], cites: ['25.13'] },
  ],
};
const NOVEL = (extra: Record<string, unknown> = {}) => ({
  novel_id: 2, doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', story_id: 36, story_title: 'The river goddess',
  status: 'drawing', title: 'The journey', title_hi: null, audience: 'general', pages: 12, approved_at_local: null,
  plan: PLAN, verify: null, cover_seq: 1, model: 'gemini-2.5-flash', image_model: 'gemini-3.1-flash-image', aspect: '3:4',
  media: [
    { key: 'novel:2:page:1', kind: 'novel_page', seq: 1, status: 'draft', title: 'Page 1', sha256: SHA('c'), width: 896, height: 1200, version: 1, has_thumb: true, has_display: true },
    { key: 'novel:2:cast:1', kind: 'novel_cast', seq: 1, status: 'draft', title: 'Devotee', sha256: SHA('d'), width: 800, height: 800, version: 1, has_thumb: true, has_display: true },
  ],
  ...extra,
});
const CREATED = (id: number, message = 'Approved; the desk takes it on its next round.') =>
  ok([{ request_id: id, request_status: 'approved', est_usd: 0, message }]);
const REQ = (id: number, extra: Record<string, unknown> = {}) => ({
  id, kind: 'picture_ideas', label: 'Ideas for pictures in a text', doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana',
  params: { max: 6 }, note: null, status: 'done', est_usd: 0.02, cost_usd: 0.01, requested_at: '2026-10-09T10:00:00Z', mine: true,
  requester: null, decided_at: '2026-10-09T10:00:00Z', decision_note: null, started_at: '2026-10-09T10:05:00Z',
  finished_at: '2026-10-09T10:09:00Z', message: '2 idea(s) for pictures; ask for any of them to be drawn.', result: null, preview: null,
  total: 1, ...extra,
});

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/corner" element={<CorpusCorner />} />
            <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />
            <Route path="/corpus/images" element={<CorpusImages />} />
            <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = []; sb.invokes = [];
  resetTrackMemo();
  resetMailMemo();
  vi.stubGlobal('fetch', vi.fn(async () => new Response('jpeg', { status: 200 })));
  Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
});
afterEach(() => {
  vi.unstubAllGlobals();
});

// ---- the rules ----------------------------------------------------------------------------------

describe('the rules of C10b', () => {
  it('the marker, the kinds, and who is offered them', () => {
    expect(C10_MARK).toBe('CORNER_C10_MAIL_2026_10_09');
    expect([...C10_KINDS].sort()).toEqual([
      'novel_page_edit', 'picture_cover', 'picture_draw', 'picture_edit', 'picture_ideas', 'picture_restore', 'story_edit', 'story_verify',
    ]);
    // before corner_kinds() lists them (C10b not applied): never offered; C9's kinds as before
    expect(kindUsable('story_edit', undefined, true)).toBe(false);
    expect(kindUsable('story_range', undefined, false)).toBe(true);
    expect(kindUsable('picture_restore', { enabled: true, editor_only: true }, false)).toBe(false);
    expect(kindUsable('picture_restore', { enabled: true, editor_only: true }, true)).toBe(true);
    expect(kindUsable('picture_draw', { enabled: false, editor_only: false }, true)).toBe(false);
  });

  it('what each new request asks for, in a line', () => {
    expect(requestSummary('story_edit', { story_id: 41, fields: { title: 'A', story_en: 'B' }, editor: false })).toBe('Edit story 41 (title, English text)');
    expect(requestSummary('story_edit', { story_id: 41, title_hi: 'x' })).toBe('Edit story 41 (Hindi title)');
    expect(requestSummary('story_verify', { story_id: 41 })).toBe('Check story 41 against its citations');
    expect(requestSummary('picture_ideas', { max: 4 })).toBe('Ideas for up to 4 pictures in the text');
    expect(requestSummary('picture_ideas', {})).toBe('Ideas for up to 6 pictures in the text');
    expect(requestSummary('picture_cover', {})).toBe('An idea for a cover of the text');
    expect(requestSummary('picture_draw', { image_id: 120 })).toBe('Draw the idea img:120');
    expect(requestSummary('picture_edit', { image_id: 103, fields: { caption_en: null, license: 'CC' }, editor: true }))
      .toBe('Edit the words of picture img:103 (caption, licence)');
    expect(requestSummary('picture_restore', { image_id: 99 })).toBe('Restore picture img:99');
    expect(requestSummary('novel_page_edit', { novel_id: 2, page: 3, fields: { scene: 'x' } })).toBe('Edit page 3 of graphic novel 2 (scene)');
    expect(requestSummary('novel_cast', { novel_id: 2, redo: true })).toBe('The cast of graphic novel 2, drawn again');
    expect(requestSummary('novel_cast', { novel_id: 2, redo: false })).toBe('The cast of graphic novel 2');
    expect(requestSummary('novel_draw', { novel_id: 2, pages: '', redo: true })).toBe('Graphic novel 2: every page, drawn again');
    expect(requestSummary('novel_draw', { novel_id: 2, pages: '3', redo: true })).toBe('Graphic novel 2: pages 3, drawn again');
    expect(requestSummary('novel_draw', { novel_id: 2, pages: '', redo: false })).toBe('Graphic novel 2: every page still to be drawn');
  });

  it('where the new requests lead', () => {
    // an idea not drawn yet, a retired picture: no link until the desk reports the picture
    expect(resultLinks({ kind: 'picture_draw', doc_code: 'd', params: { image_id: 120 }, result: null })).toEqual([]);
    expect(resultLinks({ kind: 'picture_draw', doc_code: 'd', params: { image_id: 120 }, result: { image_id: 120, status: 'draft' } }))
      .toEqual([{ label: 'The picture', href: '/corpus/images?doc=d&pic=img:120' }]);
    expect(resultLinks({ kind: 'picture_restore', doc_code: 'd', params: { image_id: 99 }, result: null })).toEqual([]);
    expect(resultLinks({ kind: 'picture_restore', doc_code: 'd', params: { image_id: 99 }, result: { image_id: 99, status: 'draft' } }).map((l) => l.href))
      .toEqual(['/corpus/images?doc=d&pic=img:99']);
    // an edit names what is there already
    expect(resultLinks({ kind: 'picture_edit', doc_code: 'd', params: { image_id: 103, fields: {} }, result: null }).map((l) => l.href))
      .toEqual(['/corpus/images?doc=d&pic=img:103']);
    expect(resultLinks({ kind: 'story_edit', doc_code: 'd', params: { story_id: 41 }, result: { story_id: 41, status: 'draft', check_ok: true } }))
      .toEqual([{ label: 'The story', href: '/corpus/stories/d/41' }]);
    expect(resultLinks({ kind: 'novel_page_edit', doc_code: 'd', params: { novel_id: 2, page: 3 }, result: { novel_id: 2, page: 3, check_ok: true, stale: false } }))
      .toEqual([{ label: 'The graphic novel', href: '/corpus/novels/2' }, { label: 'Page 3', href: '/corpus/novels/2#page-3' }]);
    // ideas are not pictures yet
    expect(resultLinks({ kind: 'picture_ideas', doc_code: 'd', params: { max: 6 }, result: { ideas: [{ image_id: 5 }], count: 1 } })).toEqual([]);
  });

  it('the edit forms: which fields, what changed, and the bounds', () => {
    expect(editFields('story_edit', 'candidate', false).map((f) => f.key)).toEqual(['title', 'title_hi']);
    expect(editFields('story_edit', 'draft', false).map((f) => f.key)).toEqual(['title', 'title_hi', 'story_en', 'story_hi']);
    expect(editFields('picture_edit', 'draft', false).map((f) => f.key)).toEqual(['title', 'caption_en', 'caption_hi', 'context_note']);
    expect(editFields('picture_edit', 'draft', true).map((f) => f.key)).toContain('license');
    expect(editFields('novel_page_edit', 'drawing', false).map((f) => f.key)).toEqual(['scene', 'caption', 'caption_hi']);
    expect(mayEdit('approved', false)).toBe(false);
    expect(mayEdit('approved', true)).toBe(true);
    expect(mayEdit('draft', false)).toBe(true);
    expect(mayEdit('retired', true)).toBe(false);
    const before = { title: 'The river', title_hi: 'Nadi', story_en: 'x'.repeat(30), story_hi: null };
    expect(changedFields(STORY_FIELDS, before, { title: '  The river ', title_hi: 'Nadi', story_en: 'x'.repeat(30), story_hi: '' })).toEqual({});
    expect(changedFields(STORY_FIELDS, before, { title: 'The river goddess', title_hi: '', story_en: 'x'.repeat(30) })).toEqual({ title: 'The river goddess', title_hi: '' });
    expect(changedFields(PICTURE_FIELDS, { caption_hi: null }, { caption_hi: ' new ' })).toEqual({ caption_hi: 'new' });
    expect(fieldProblem(STORY_FIELDS[0], 'ab')).toBe('Title: 3 to 300 characters');
    expect(fieldProblem(STORY_FIELDS[0], 'abc')).toBeNull();
    expect(fieldProblem(STORY_FIELDS[2], 'short')).toBe('The story in English: 20 to 6000 characters');
    expect(fieldProblem(STORY_FIELDS[1], '')).toBeNull();
  });

  it('the ideas of a result, and where an idea stands', () => {
    const result = {
      ideas: [
        { image_id: 120, kind: 'generated', title: 'The lake', brief: 'A lake in the mountains.', at: '25.2' },
        { image_id: 121, kind: 'cover', title: 'A cover', brief: 'The valley', at: null },
        { image_id: 120, title: 'again' }, { image_id: 'x' }, null, 'no',
      ],
      count: 2,
    };
    expect(parseIdeas(result)).toEqual([
      { image_id: 120, kind: 'generated', title: 'The lake', brief: 'A lake in the mountains.', at: '25.2' },
      { image_id: 121, kind: 'cover', title: 'A cover', brief: 'The valley', at: null },
    ]);
    expect(parseIdeas(JSON.stringify(result))).toHaveLength(2);
    expect(parseIdeas({ count: 0 })).toEqual([]);
    expect(parseIdeas('nonsense')).toEqual([]);
    expect(parseIdeas(null)).toEqual([]);
    expect(ideaState(ideaRow({ image_id: 1, drawn: true, draw_status: 'done' }))).toBe('drawn');
    expect(ideaState(ideaRow({ image_id: 1, drawn: false, draw_status: 'approved' }))).toBe('asked');
    expect(ideaState(ideaRow({ image_id: 1, drawn: false, draw_status: 'done' }))).toBe('synced');
    expect(ideaState(ideaRow({ image_id: 1, drawn: false, draw_status: 'failed' }))).toBe('waiting');
    expect(ideaState(null)).toBe('waiting');
  });
});

// ---- the reading pages' desk bar -------------------------------------------------------------

describe('editing from a story', () => {
  it('an editor edits a draft: the form starts from the story, and only the title is sent', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36)]);
    sb.byFn.corner_request_create = CREATED(51, 'Approved; the desk makes the change on its next round.');
    mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    const edit = await within(bar).findByRole('button', { name: 'Edit' });
    expect(within(bar).getByRole('button', { name: 'Check again' })).toBeInTheDocument();
    expect(edit).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(edit);
    const form = await within(bar).findByRole('form', { name: 'Edit the story' });
    expect(edit).toHaveAttribute('aria-expanded', 'true');
    expect(within(form).getByLabelText('Title')).toHaveValue('The river goddess');
    expect(within(form).getByLabelText('Title in Hindi')).toHaveValue('Nadi devi');
    expect(within(form).getByLabelText('The story in English')).toHaveValue('The goddess flowed down from the mountain to the plain.');
    expect(within(form).getByLabelText('The story in Hindi')).toHaveValue('Devi bahi.');
    const send = within(form).getByRole('button', { name: 'Send the change' });
    expect(send).toBeDisabled();
    expect(within(form).getByText('Nothing changed yet.')).toBeInTheDocument();
    fireEvent.change(within(form).getByLabelText('Title'), { target: { value: 'ab' } });
    expect(within(form).getByRole('alert')).toHaveTextContent('Title: 3 to 300 characters');
    expect(send).toBeDisabled();
    fireEvent.change(within(form).getByLabelText(/^Title \(changed\)/), { target: { value: '  The river goddess Vitasta ' } });
    expect(send).not.toBeDisabled();
    fireEvent.click(send);
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({
      p_kind: 'story_edit', p_doc: 'nilamata_seg', p_params: { story_id: 36, title: 'The river goddess Vitasta' }, p_note: null,
    });
    expect(await within(bar).findByText(/Approved; the desk makes the change on its next round. \(request #51\)/)).toBeInTheDocument();
    expect(within(bar).queryByRole('form')).toBeNull();
    await waitFor(() => expect(flushes()).toHaveLength(1));
    expect(flushes()[0].o).toEqual({ body: { action: 'flush' } });
  });

  it('Check again asks for story_verify; Cancel closes the form without asking', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36)]);
    sb.byFn.corner_request_create = CREATED(52);
    mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    fireEvent.click(await within(bar).findByRole('button', { name: 'Edit' }));
    fireEvent.click(within(await within(bar).findByRole('form', { name: 'Edit the story' })).getByRole('button', { name: 'Cancel' }));
    expect(within(bar).queryByRole('form')).toBeNull();
    fireEvent.click(within(bar).getByRole('button', { name: 'Check again' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toMatchObject({ p_kind: 'story_verify', p_params: { story_id: 36 } });
    // the bar loads the mail code only now, and asks corner-mail to send what waits
    await waitFor(() => expect(flushes()).toHaveLength(1));
  });

  it('a researcher: no Edit on an approved story (Check again stays); a proposed episode only its titles', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36, { status: 'approved' }), STORY(37, { status: 'candidate', story_en: null, story_hi: null })]);
    const { unmount } = mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    expect(await within(bar).findByRole('button', { name: 'Check again' })).toBeInTheDocument();
    expect(within(bar).queryByRole('button', { name: 'Edit' })).toBeNull();
    unmount();
    mount('/corpus/stories/nilamata_seg/37');
    const bar2 = await screen.findByRole('group', { name: 'Ask the desk' });
    fireEvent.click(await within(bar2).findByRole('button', { name: 'Edit' }));
    const form = await within(bar2).findByRole('form', { name: 'Edit the story' });
    expect(within(form).getByLabelText('Title')).toBeInTheDocument();
    expect(within(form).queryByLabelText('The story in English')).toBeNull();
    expect(within(bar2).queryByRole('button', { name: 'Check again' })).toBeNull();   // not written yet
  });

  it('before C10b: no Edit and no Check again; the bar as before', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(C9_KINDS);
    sb.byFn.corpus_reader_stories = ok([STORY(36)]);
    mount('/corpus/stories/nilamata_seg/36');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    expect(await within(bar).findByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(within(bar).queryByRole('button', { name: 'Edit' })).toBeNull();
    expect(within(bar).queryByRole('button', { name: 'Check again' })).toBeNull();
  });
});

describe("editing a picture's words", () => {
  it('a researcher edits a draft picture (no licence); only the caption is sent', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_media = ok([PIC()]);
    sb.byFn.corner_request_create = CREATED(53);
    mount('/corpus/images?doc=nilamata_seg&pic=img:103');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    fireEvent.click(await within(bar).findByRole('button', { name: 'Edit words' }));
    const form = await within(bar).findByRole('form', { name: "Edit the picture's words" });
    expect(within(form).getByLabelText('Title')).toHaveValue('The river at dawn');
    expect(within(form).getByLabelText('Caption in English')).toHaveValue('The river at dawn.');
    expect(within(form).getByLabelText('Caption in Hindi')).toHaveValue('');
    expect(within(form).getByLabelText('A note on what it shows')).toHaveValue('Drawn from 25.7.');
    expect(within(form).queryByLabelText('Licence')).toBeNull();
    fireEvent.change(within(form).getByLabelText('Caption in Hindi'), { target: { value: 'Subah ki nadi' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Send the change' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toMatchObject({
      p_kind: 'picture_edit', p_params: { image_id: 103, caption_hi: 'Subah ki nadi' },
    });
  });

  it('an editor also changes the licence; a researcher sees no Edit on an approved picture', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_media = ok([PIC({ status: 'approved' })]);
    const { unmount } = mount('/corpus/images?doc=nilamata_seg&pic=img:103');
    const bar = await screen.findByRole('group', { name: 'Ask the desk' });
    fireEvent.click(await within(bar).findByRole('button', { name: 'Edit words' }));
    const form = await within(bar).findByRole('form', { name: "Edit the picture's words" });
    expect(within(form).getByLabelText('Licence')).toHaveValue('CC BY 4.0');
    unmount();
    sb.byFn.corner_me = ok([ME()]);
    mount('/corpus/images?doc=nilamata_seg&pic=img:103');
    const bar2 = await screen.findByRole('group', { name: 'Ask the desk' });
    expect(await within(bar2).findByRole('button', { name: 'Draw again' })).toBeInTheDocument();
    await waitFor(() => expect(called('corner_kinds').length).toBeGreaterThan(0));
    expect(within(bar2).queryByRole('button', { name: 'Edit words' })).toBeNull();
  });
});

describe('a graphic novel: a page edited, the cast and the pages drawn again', () => {
  it('an editor: again, after a second click, with the estimate of every page', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_novel = ok([NOVEL()]);
    sb.byFn.corner_request_create = CREATED(54);
    mount('/corpus/novels/2');
    const bars = await screen.findAllByRole('group', { name: 'Ask the desk' });
    const novelBar = bars[0];
    const all = await within(novelBar).findByRole('button', { name: /Draw every page again/ });
    expect(all).toHaveTextContent('about $1.20');   // 12 pages at $0.10
    expect(within(novelBar).getByRole('button', { name: /Draw the cast again/ })).toHaveTextContent('about $0.40');
    fireEvent.click(all);
    expect(called('corner_request_create')).toHaveLength(0);
    fireEvent.click(within(novelBar).getByRole('button', { name: /Click again to draw every page again/ }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({
      p_kind: 'novel_draw', p_doc: 'nilamata_seg', p_params: { novel_id: 2, pages: '', redo: true }, p_note: null,
    });
    // the plain "Draw the pages" is still what it was
    expect(within(novelBar).getByRole('button', { name: /^Draw the pages/ })).toBeInTheDocument();
  });

  it('a page is edited from its plan: scene and captions prefilled, the caption sent', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_novel = ok([NOVEL()]);
    sb.byFn.corner_request_create = CREATED(55);
    mount('/corpus/novels/2');
    const page1 = await screen.findByRole('region', { name: 'Page 1' });
    const bar = await within(page1).findByRole('group', { name: 'Ask the desk' });
    fireEvent.click(await within(bar).findByRole('button', { name: 'Edit page 1' }));
    const form = await within(bar).findByRole('form', { name: 'Edit page 1' });
    expect(within(form).getByLabelText('The scene the artist is asked for')).toHaveValue('A riverbank at dawn.');
    expect(within(form).getByLabelText('Caption in English')).toHaveValue('A brahmin prayed. [25.7]');
    fireEvent.change(within(form).getByLabelText('Caption in English'), { target: { value: 'A brahmin prayed at dawn. [25.7]' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Send the change' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args.p_params).toEqual({ novel_id: 2, page: 1, caption: 'A brahmin prayed at dawn. [25.7]' });
  });

  it('a researcher: no page edit on an approved novel; nothing "again" before C10b', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_novel = ok([NOVEL({ status: 'approved' })]);
    const { unmount } = mount('/corpus/novels/2');
    const page1 = await screen.findByRole('region', { name: 'Page 1' });
    const bar = await within(page1).findByRole('group', { name: 'Ask the desk' });
    expect(await within(bar).findByRole('button', { name: /Draw page 1 again/ })).toBeInTheDocument();
    expect(within(bar).queryByRole('button', { name: 'Edit page 1' })).toBeNull();
    unmount();
    sb.byFn.corner_kinds = ok(C9_KINDS);
    sb.byFn.corpus_reader_novel = ok([NOVEL()]);
    mount('/corpus/novels/2');
    const bars = await screen.findAllByRole('group', { name: 'Ask the desk' });
    expect(await within(bars[0]).findByRole('button', { name: /Draw the cast/ })).toBeInTheDocument();
    expect(within(bars[0]).queryByRole('button', { name: /again/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Edit page/ })).toBeNull();
  });
});

// ---- the Corner ---------------------------------------------------------------------------------

const IDEAS = [
  { image_id: 120, kind: 'generated', title: 'The lake of Kashmir', brief: 'A wide lake below snowy peaks.', at: '25.2', request_id: 12,
    asked_at: '2026-10-09T10:00:00Z', drawn: false, draw_request_id: null, draw_status: null },
  { image_id: 121, kind: 'generated', title: 'The serpent king', brief: 'Nila rises from the water.', at: '25.4', request_id: 12,
    asked_at: '2026-10-09T10:00:00Z', drawn: true, draw_request_id: 30, draw_status: 'done' },
  { image_id: 122, kind: 'cover', title: 'A cover for the text', brief: 'The valley at dawn.', at: null, request_id: 13,
    asked_at: '2026-10-09T11:00:00Z', drawn: false, draw_request_id: 31, draw_status: 'approved' },
];

describe('/corpus/corner, level with the desk', () => {
  it('ideas for pictures and a cover are asked for; the waiting emails are sent after each', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    sb.byFn.corner_request_create = ok([{ request_id: 60, request_status: 'pending', est_usd: 0.02, message: "Waiting for an editor's approval." }]);
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    const ideas = await screen.findByRole('form', { name: 'Ideas for pictures in a text' });
    expect(within(ideas.parentElement as HTMLElement).getByText('about $0.02')).toBeInTheDocument();
    const max = within(ideas).getByLabelText('How many ideas, at most (1 to 12)');
    expect(max).toHaveValue(6);
    fireEvent.change(max, { target: { value: '13' } });
    expect(within(ideas).getByRole('button', { name: 'Ask the desk' })).toBeDisabled();
    fireEvent.change(max, { target: { value: '4' } });
    await waitFor(() => expect(screen.getByLabelText('The text')).toHaveValue('nilamata_seg'));
    fireEvent.click(within(ideas).getByRole('button', { name: 'Ask the desk' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({ p_kind: 'picture_ideas', p_doc: 'nilamata_seg', p_params: { max: 4 }, p_note: null });
    await waitFor(() => expect(flushes()).toHaveLength(1));

    const cover = screen.getByRole('form', { name: 'An idea for a cover' });
    fireEvent.click(within(cover).getByRole('button', { name: 'Ask the desk' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(2));
    expect(called('corner_request_create')[1].args).toEqual({ p_kind: 'picture_cover', p_doc: 'nilamata_seg', p_params: {}, p_note: null });
    await waitFor(() => expect(flushes()).toHaveLength(2));

    sb.byFn.corner_request_create = { data: null, error: { code: '22023', message: 'max: a whole number from 1 to 12' } };
    fireEvent.click(within(ideas).getByRole('button', { name: 'Ask the desk' }));
    expect(await within(ideas.parentElement as HTMLElement).findByText('max: a whole number from 1 to 12')).toBeInTheDocument();
    expect(flushes()).toHaveLength(2);   // nothing to send after a refusal
  });

  it('the ideas waiting to be drawn: draw one, see a drawn one, one already asked for', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    sb.byFn.corner_ideas = ok(IDEAS);
    sb.byFn.corner_request_create = ok([{ request_id: 61, request_status: 'pending', est_usd: 0.1, message: "Waiting for an editor's approval." }]);
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    const panel = await screen.findByRole('region', { name: /Ideas waiting to be drawn/ });
    expect(called('corner_ideas')[0].args).toEqual({ p_doc: 'nilamata_seg' });
    expect(within(panel).getByText('(1 of 3)')).toBeInTheDocument();
    const lake = within(panel).getByText('The lake of Kashmir').closest('li') as HTMLElement;
    expect(within(lake).getByRole('link', { name: '25.2' })).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.2');
    expect(within(lake).getByText('about $0.10')).toBeInTheDocument();
    const serpent = within(panel).getByText('The serpent king').closest('li') as HTMLElement;
    expect(within(serpent).getByRole('link', { name: 'See the picture' })).toHaveAttribute('href', '/corpus/images?doc=nilamata_seg&pic=img:121');
    expect(within(serpent).queryByRole('button')).toBeNull();
    const cover = within(panel).getByText('A cover for the text').closest('li') as HTMLElement;
    expect(within(cover).getByText('Asked to be drawn (request #31): queued for the desk.')).toBeInTheDocument();
    expect(within(cover).getByText('cover')).toBeInTheDocument();
    fireEvent.click(within(lake).getByRole('button', { name: 'Draw this idea: The lake of Kashmir' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({ p_kind: 'picture_draw', p_doc: 'nilamata_seg', p_params: { image_id: 120 }, p_note: null });
    expect(await within(lake).findByText(/Waiting for an editor's approval. \(request #61\)/)).toBeInTheDocument();
    await waitFor(() => expect(flushes()).toHaveLength(1));
    // a researcher has no retired pictures
    expect(screen.queryByRole('region', { name: /Retired pictures/ })).toBeNull();
    expect(called('corner_retired_pictures')).toEqual([]);
  });

  it('an editor restores a retired picture', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    sb.byFn.corner_retired_pictures = ok([
      { image_id: 99, kind: 'generated', title: 'An old drawing', caption_en: 'The first try.', retired_at: '2026-10-08T10:00:00Z', has_file: false },
    ]);
    sb.byFn.corner_request_create = CREATED(62, 'Approved; the desk restores it on its next round.');
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    const panel = await screen.findByRole('region', { name: /Retired pictures/ });
    expect(called('corner_retired_pictures')[0].args).toEqual({ p_doc: 'nilamata_seg' });
    expect(await within(panel).findByText('Its file is no longer on the site.')).toBeInTheDocument();
    expect(within(panel).getByText('(1)')).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole('button', { name: 'Restore An old drawing' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toEqual({ p_kind: 'picture_restore', p_doc: 'nilamata_seg', p_params: { image_id: 99 }, p_note: null });
    expect(await within(panel).findByText(/the desk restores it on its next round. \(request #62\)/)).toBeInTheDocument();
  });

  it('before C10b: no new forms, and nothing new is asked', async () => {
    sb.byFn.corner_me = ok([EDITOR()]);
    sb.byFn.corner_kinds = ok(C9_KINDS);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    expect(await screen.findByRole('form', { name: 'picture_passage' })).toBeInTheDocument();
    await waitFor(() => expect(called('corner_kinds').length).toBeGreaterThan(0));
    expect(screen.queryByRole('form', { name: /Ideas for pictures/ })).toBeNull();
    expect(screen.queryByRole('form', { name: /cover/ })).toBeNull();
    expect(called('corner_ideas')).toEqual([]);
    expect(called('corner_retired_pictures')).toEqual([]);
  });

  it('my requests: the ideas of a finished request, each with Draw this idea', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corner_requests = ok([REQ(12, {
      result: { ideas: [
        { image_id: 120, kind: 'generated', title: 'The lake of Kashmir', brief: 'A wide lake.', at: '25.2' },
        { image_id: 121, kind: 'generated', title: 'The serpent king', brief: 'Nila rises.', at: '25.4' },
      ], count: 2 },
    })]);
    sb.byFn.corner_ideas = ok(IDEAS);
    sb.byFn.corner_request_create = CREATED(63);
    mount('/corpus/corner?tab=mine');
    const group = await screen.findByRole('group', { name: 'Ideas of request #12' });
    expect(within(group).getByText('The 2 ideas the desk proposed:')).toBeInTheDocument();
    expect(screen.getByText(/Ideas for up to 6 pictures in the text/)).toBeInTheDocument();
    const serpent = within(group).getByText('The serpent king').closest('li') as HTMLElement;
    expect(await within(serpent).findByRole('link', { name: 'See the picture' })).toBeInTheDocument();
    const lake = within(group).getByText('The lake of Kashmir').closest('li') as HTMLElement;
    fireEvent.click(within(lake).getByRole('button', { name: /Draw this idea/ }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toMatchObject({ p_kind: 'picture_draw', p_params: { image_id: 120 } });
  });
});
