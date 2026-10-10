/**
 * CORNER_UX_U1_2026_10_10 - the Corner's guide: the offering so far, where to begin, what to make,
 * what is ready in a text ("Set it up" fills a form and asks nothing), passages chosen in the text, the
 * text remembered on this browser, and the Reply-to that no longer looks saved. The pure rules first;
 * then the page against a mocked supabase, as in corpus-corner.test.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: () => Promise.resolve({ data: { ok: true }, error: null }) },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));
vi.mock('@/hooks/use-toast', () => ({ toast: vi.fn(), useToast: () => ({ toasts: [], toast: vi.fn(), dismiss: vi.fn() }) }));

import {
  briefFrom, firstWords, GUIDE_MARK, goalCounts, goalOf, offeringParts, parseGoal, parseOffering, rangeNote, readyNow,
  recallDoc, rememberDoc, shows, surpriseText, textState, textStateLine, translatedTexts, untoldLine, untoldTexts,
  type Offering,
} from '@/lib/cornerGuide';
import { resetMailMemo } from '@/lib/cornerMail';
import { resetTrackMemo } from '@/lib/cornerState';
import { MailAdminCard } from '@/components/corpus/CornerPanels';
import CorpusCorner from '@/pages/corpus/CorpusCorner';
import CorpusAnthology from '@/pages/corpus/CorpusAnthology';
import type { StoryRow } from '@/lib/corpusLibrary';
import type { MediaRow, NovelRow } from '@/lib/corpusMedia';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);
const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString();

const ME = (extra: Record<string, unknown> = {}) => ({
  can_request: true, is_editor: false, is_super_admin: false, daily_cap_usd: 2, committed_today: 0, researchers_need_approval: true,
  worker_last_seen: recent, worker_info: null, pending: 0, queued: 0, running: 0, mine_open: 0, ...extra,
});
const K = (kind: string, est: number, unit: 'request' | 'page' | 'chunk' = 'request', editor = false) =>
  ({ kind, label: kind, cost_bearing: est > 0, editor_only: editor, est_usd: est, unit, enabled: true });
const KINDS = [
  K('story_range', 0.01), K('story_write', 0.01), K('story_mine', 0.01, 'chunk'), K('picture_passage', 0.1), K('story_illustrate', 0.11),
  K('picture_redraw', 0.1), K('novel_plan', 0.02), K('novel_cast', 0.4), K('novel_draw', 0.1, 'page'), K('story_approve', 0, 'request', true),
  K('picture_ideas', 0.02), K('picture_cover', 0.01), K('picture_draw', 0.1),
].map((k) => ({ ...k, label: ({ story_range: 'A story from passages you choose', story_write: 'Write a proposed episode',
  picture_passage: 'A picture for a passage', novel_plan: 'Plan a graphic novel from a story', story_illustrate: 'A picture for a story',
  story_mine: 'Find episodes in a text', picture_ideas: 'Ideas for pictures in a text' } as Record<string, string>)[k.kind] ?? k.kind }));
const DOC = (code: string, title: string, english: number, stories: number, passages = 900) => ({
  doc_code: code, title, category: 'purana', passages, english, hindi: Math.floor(english / 2), vectors: 0, stories, published: false, synced_at: null,
});
const DOCS = [DOC('nilamata_seg', 'Nilamata Purana', 450, 3), DOC('harita_smriti', 'Harita Smriti', 300, 0), DOC('atri', 'Atri Smriti', 120, 0),
  DOC('empty_doc', 'Untranslated', 0, 0)];
const STORY = (id: number, status: string, extra: Record<string, unknown> = {}): StoryRow => ({
  doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', story_id: id, status, title: `Story ${id}`, title_hi: null, why: null,
  from_page: 25, from_idx: 1, to_page: 25, to_idx: 4, from_ord: 300, story_en: null, story_hi: null, quote_sa: null, quote_ref: null,
  cites: null, verify: null, model: null, approved_at_local: null, updated_at_local: null, ...extra,
}) as StoryRow;
const PIC = (id: number, storyId: number | null, status = 'approved'): MediaRow => ({
  media_key: `img:${id}`, doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', kind: 'generated', status, title: `Picture ${id}`,
  caption_en: null, caption_hi: null, context_note: null, anchor_page: 25, anchor_idx: 1, anchor_verse_ref: null, story_id: storyId,
  width: 1, height: 1, sha256: 'a'.repeat(64), has_thumb: true, has_display: true, model: null, license: null, approved_at_local: null, total: 1,
}) as MediaRow;
const NOVEL = (id: number, storyId: number, status = 'approved'): NovelRow => ({
  novel_id: id, doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana', story_id: storyId, story_title: null, status, title: `Novel ${id}`,
  title_hi: null, audience: 'general', pages: 12, cover_sha: null, cover_has_thumb: false, approved_at_local: null, updated_at_local: null,
}) as NovelRow;
const OFFERING: Offering = {
  texts: 51, passages_en: 31204, stories_approved: 42, stories_draft: 3, stories_proposed: 7, pictures: 114, novels: 1, anthologies: 2,
  untold: 23, done_all: 40, done_7d: 6,
};
const PASSAGE = (idx: number, translation: string | null) => ({
  ord: 300 + idx, page_no: 25, idx, verse_ref: null, chapter: null, text_type: 'mula', sanskrit: 'sa', iast: 'sa', translation, hindi: null,
  quality_score: null, translation_qa: null, engine: null, translated_at: null,
});

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/corner" element={<CorpusCorner />} />
            <Route path="/corpus/anthologies/new" element={<CorpusAnthology />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

const textSelect = () => screen.getByLabelText('The text') as HTMLSelectElement;

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  resetMailMemo(); resetTrackMemo();
  try { window.localStorage.clear(); } catch { /* none */ }
  vi.stubGlobal('fetch', vi.fn(async () => new Response('jpeg', { status: 200 })));
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

// ---- the rules ------------------------------------------------------------------------------

describe('the rules of the guide', () => {
  it('goals: of a kind, from the address, and which sections each shows', () => {
    expect(GUIDE_MARK).toBe('CORNER_UX_U1_2026_10_10');
    expect([goalOf('story_range'), goalOf('picture_draw'), goalOf('novel_cast'), goalOf('story_edit'), goalOf(null)])
      .toEqual(['story', 'picture', 'novel', null, null]);
    expect([parseGoal('novel'), parseGoal('all'), parseGoal('x'), parseGoal(null)]).toEqual(['novel', 'all', null, null]);
    expect([shows('all', 'story'), shows('picture', 'story'), shows('picture', 'picture')]).toEqual([true, false, true]);
  });

  it('texts: translated only, by title; where to begin; surprise me', () => {
    const t = translatedTexts([...DOCS, null, { doc_code: '' }]);
    expect(t.map((x) => x.doc_code)).toEqual(['atri', 'harita_smriti', 'nilamata_seg']);
    expect(t.map((x) => x.untold)).toEqual([true, true, false]);
    expect(untoldTexts(t).map((x) => x.doc_code)).toEqual(['harita_smriti', 'atri']);   // the most English first
    expect(surpriseText(t, null, () => 0.99)?.doc_code).toBe('harita_smriti');          // an untold text
    expect(surpriseText(t, 'harita_smriti', () => 0)?.doc_code).toBe('atri');           // never the one chosen
    const told = t.map((x) => ({ ...x, untold: false }));
    expect(surpriseText(told, 'atri', () => 0)?.doc_code).toBe('harita_smriti');        // else any other text
    expect(surpriseText([], null)).toBeNull();
  });

  it('the offering so far: from corner_offering, else from the texts', () => {
    expect(parseOffering({ ...OFFERING, texts: '51' })).toEqual(OFFERING);
    expect(parseOffering({ texts: 1 })).toBeNull();
    expect(offeringParts(OFFERING, [])).toEqual([
      '51 texts in English', '31,204 passages translated', '42 stories told', '114 pictures', '1 graphic novel',
      '2 anthologies published', '6 requests done this week']);
    expect(offeringParts({ ...OFFERING, pictures: 0, novels: 0, anthologies: 0, done_7d: 0, stories_approved: 1 }, []))
      .toEqual(['51 texts in English', '31,204 passages translated', '1 story told']);
    const t = translatedTexts(DOCS);
    expect(offeringParts(null, t)).toEqual(['3 texts in English', '870 passages translated']);
    expect(offeringParts(null, [])).toEqual([]);
    // counted from the texts, as the list and "Where to begin" count them
    expect(untoldLine(t)).toBe('2 texts are waiting for their first story');
    expect(untoldLine(t.filter((x) => x.doc_code !== 'atri'))).toBe('1 text is waiting for its first story');
    expect(untoldLine(t.filter((x) => !x.untold))).toBeNull();
  });

  it('one text: what it has, in a line', () => {
    const s = textState([STORY(1, 'approved'), STORY(2, 'draft'), STORY(3, 'candidate'), STORY(4, 'retired')], [PIC(1, 1)], [NOVEL(1, 1)]);
    expect(s).toEqual({ approved: 1, drafts: 1, proposed: 1, pictures: 1, novels: 1 });
    expect(textStateLine(s)).toBe('3 stories (1 approved, 1 draft, 1 proposed) · 1 picture · 1 graphic novel');
    expect(textStateLine({ approved: 2, drafts: 0, proposed: 0, pictures: 0, novels: 0 })).toBe('2 approved stories · 0 pictures · 0 graphic novels');
    expect(textStateLine({ approved: 0, drafts: 0, proposed: 0, pictures: 0, novels: 0 })).toBe('No story yet · 0 pictures · 0 graphic novels');
  });

  it('ready in this text: the first step first, only what this viewer may ask for', () => {
    const all = () => true;
    const base = { usable: all, seesDrafts: true, textStories: 0 };
    expect(readyNow({ ...base, stories: [], pics: [], novels: [] }).map((s) => s.kind)).toEqual(['story_mine', 'picture_ideas']);
    // the text has stories this viewer is not shown (drafts, before C13): no "find its episodes"
    expect(readyNow({ ...base, stories: [], pics: [], novels: [], textStories: 3 }).map((s) => s.kind)).toEqual(['picture_ideas']);
    // a viewer not shown the drafts: "no picture" may mean "none approved", so nothing of the kind is offered
    expect(readyNow({ ...base, seesDrafts: false, stories: [], pics: [], novels: [] }).map((s) => s.kind)).toEqual(['story_mine']);
    expect(readyNow({ ...base, seesDrafts: false, stories: [STORY(34, 'approved')], pics: [], novels: [], textStories: 1 })).toEqual([]);
    const stories = [STORY(36, 'candidate'), STORY(34, 'approved'), STORY(35, 'draft'), STORY(41, 'approved'), STORY(9, 'retired')];
    const r = readyNow({ ...base, textStories: 5, stories, pics: [PIC(4, 34)], novels: [NOVEL(1, 34)], max: 10 });
    expect(r.map((s) => s.key)).toEqual(['story_write:36', 'story_illustrate:41', 'story_illustrate:35', 'novel_plan:41']);
    expect(r[0]).toMatchObject({ title: 'Write "Story 36"', goal: 'story', fill: { story_id: '36' } });
    expect(r[1].why).toMatch(/approved story with no picture/);
    expect(goalCounts(r)).toEqual({ story: 1, picture: 2, novel: 1 });
    expect(readyNow({ ...base, textStories: 5, stories, pics: [PIC(4, 34)], novels: [], max: 3 }).length).toBe(3);
    const noPaid = readyNow({ ...base, textStories: 5, stories, pics: [], novels: [], usable: (k) => k === 'novel_plan' });
    expect(noPaid.map((s) => s.kind)).toEqual(['novel_plan']);
    expect(readyNow({ ...base, stories: [], pics: [], novels: [], usable: () => false })).toEqual([]);
  });

  it('passages chosen in the text', () => {
    expect(rangeNote(null, { ref: '25.2', ord: 2 })).toBeNull();
    expect(rangeNote({ ref: '25.2', ord: 2 }, { ref: '25.4', ord: 4 })).toEqual({ ok: true, text: '3 passages.' });
    expect(rangeNote({ ref: '25.2', ord: 2 }, { ref: '25.2', ord: 2 })).toEqual({ ok: true, text: '1 passage.' });
    expect(rangeNote({ ref: '25.4', ord: 4 }, { ref: '25.2', ord: 2 })?.ok).toBe(false);
    expect(rangeNote({ ref: '1.1', ord: 1 }, { ref: '9.9', ord: 61 })).toEqual({ ok: false, text: '61 passages: a story is drawn from 60 at most.' });
    expect(firstWords('  The   king said  ')).toBe('The king said');
    expect(firstWords('word '.repeat(60), 30)).toBe('word word word word word word...');
    expect(briefFrom(null)).toBe('');
    expect(briefFrom('x'.repeat(700)).length).toBeLessThanOrEqual(603);
  });

  it('the text chosen last time, remembered on this browser only, and never a failure', () => {
    expect(recallDoc()).toBeNull();
    rememberDoc('nilamata_seg');
    expect(recallDoc()).toBe('nilamata_seg');
    rememberDoc('bad code <x>');
    expect(recallDoc()).toBe('nilamata_seg');
    const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied'); });
    const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied'); });
    expect(recallDoc()).toBeNull();
    expect(() => rememberDoc('atri')).not.toThrow();
    get.mockRestore(); set.mockRestore();
  });
});

// ---- the page -------------------------------------------------------------------------------

describe('/corpus/corner, guided', () => {
  it('a first visit: the offering so far, where to begin, and no forms until a text is chosen', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    sb.byFn.corner_offering = ok([OFFERING]);
    mount('/corpus/corner');
    const strip = await screen.findByRole('region', { name: 'The offering so far' });
    expect(strip).toHaveTextContent('51 texts in English · 31,204 passages translated · 42 stories told · 114 pictures');
    expect(strip).toHaveTextContent('2 texts are waiting for their first story.');   // as the shelf below counts them
    const shelf = await screen.findByRole('region', { name: 'Where to begin' });
    expect(within(shelf).getAllByRole('button').map((b) => b.textContent)).toEqual(['Harita Smriti300 in English', 'Atri Smriti120 in English']);
    expect(screen.queryByRole('form')).toBeNull();
    expect(screen.getByText('Choose a text, then what to make from it: a story, a picture or a graphic novel.')).toBeInTheDocument();
    // the list groups the texts waiting for their first story
    const groups = Array.from(textSelect().querySelectorAll('optgroup')).map((g) => g.label);
    expect(groups).toEqual(['Waiting for their first story', 'With stories']);
    expect(within(textSelect().querySelector('optgroup[label="With stories"]') as HTMLElement).getByText('Nilamata Purana')).toBeInTheDocument();
    expect(within(textSelect()).queryByText('Untranslated')).toBeNull();

    fireEvent.click(within(shelf).getByRole('button', { name: /Harita Smriti/ }));
    expect(textSelect()).toHaveValue('harita_smriti');
    expect(await screen.findByRole('form', { name: 'A story from passages you choose' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Where to begin' })).toBeNull();
    expect(window.localStorage.getItem('srangam.corner.lastDoc')).toBe('harita_smriti');
    // nothing was asked of the desk
    expect(called('corner_request_create')).toEqual([]);
  });

  it('before C13 the strip is made from the texts alone, quietly', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    sb.byFn.corner_offering = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corner_offering without parameters in the schema cache' } };
    mount('/corpus/corner');
    const strip = await screen.findByRole('region', { name: 'The offering so far' });
    await waitFor(() => expect(strip).toHaveTextContent('3 texts in English · 870 passages translated.'));
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('the text chosen last time is offered, not chosen for you; Surprise me chooses one waiting for its first story', async () => {
    window.localStorage.setItem('srangam.corner.lastDoc', 'nilamata_seg');
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    mount('/corpus/corner?tab=ask');
    const go = await screen.findByRole('button', { name: 'Continue with Nilamata Purana' });
    expect(textSelect()).toHaveValue('');
    fireEvent.click(go);
    expect(textSelect()).toHaveValue('nilamata_seg');
    vi.spyOn(Math, 'random').mockReturnValue(0);
    fireEvent.click(screen.getByRole('button', { name: 'Surprise me' }));
    expect(textSelect()).toHaveValue('atri');            // the first of the texts waiting for their first story
  });

  it('what to make: a goal shows its own requests; Everything shows them all', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    expect(await screen.findByRole('form', { name: 'A story from passages you choose' })).toBeInTheDocument();
    const goals = screen.getByRole('group', { name: 'What to make' });
    expect(within(goals).getByRole('button', { name: /Everything/ })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(goals).getByRole('button', { name: /A picture/ }));
    expect(screen.queryByRole('form', { name: 'A story from passages you choose' })).toBeNull();
    expect(screen.getByRole('form', { name: 'A picture for a passage' })).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Plan a graphic novel from a story' })).toBeNull();
    fireEvent.click(within(goals).getByRole('button', { name: /Everything/ }));
    expect(screen.getByRole('form', { name: 'A story from passages you choose' })).toBeInTheDocument();
    expect(within(goals).getByRole('link', { name: 'An anthology' })).toHaveAttribute('href', '/corpus/corner?tab=anthologies');
  });

  it('a Learn link with a kind and no text: choose the text, and that goal is shown', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    mount('/corpus/corner?tab=ask&kind=novel_plan');
    await screen.findByRole('region', { name: 'Where to begin' });
    expect(screen.queryByRole('form')).toBeNull();
    fireEvent.change(textSelect(), { target: { value: 'nilamata_seg' } });
    expect(await screen.findByRole('form', { name: 'Plan a graphic novel from a story' })).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'A story from passages you choose' })).toBeNull();
    expect(screen.getByRole('button', { name: /A graphic novel/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('ready in this text: Set it up fills the form and goes to it, and asks nothing', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    sb.byFn.corpus_reader_stories = ok([STORY(36, 'candidate'), STORY(34, 'approved'), STORY(41, 'approved')]);
    sb.byFn.corpus_reader_media = ok([PIC(4, 34)]);
    sb.byFn.corpus_reader_novels = ok([NOVEL(1, 34)]);
    sb.byFn.corner_offering = ok([OFFERING]);   // C13 is there: a researcher is shown the work in progress
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    const ready = await screen.findByRole('region', { name: 'Ready in this text' });
    expect(within(ready).getAllByRole('listitem').map((li) => li.querySelector('p')?.textContent))
      .toEqual(['Write "Story 36"', 'A picture for "Story 41"', 'A graphic novel of "Story 41"']);
    expect(screen.getByText(/3 stories \(2 approved, 1 proposed\) · 1 picture · 1 graphic novel/)).toBeInTheDocument();
    const goals = screen.getByRole('group', { name: 'What to make' });
    expect(within(goals).getByRole('button', { name: /A story/ })).toHaveTextContent('1 ready');
    expect(within(goals).getByRole('button', { name: /A picture/ })).toHaveTextContent('1 ready');
    expect(within(ready).getAllByText('about $0.01')).toHaveLength(1);

    fireEvent.click(within(ready).getByRole('button', { name: 'Set it up: Write "Story 36"' }));
    const write = screen.getByRole('form', { name: 'Write a proposed episode' });
    expect(within(write).getByLabelText('The proposed episode')).toHaveValue('36');
    expect(document.getElementById('ask-story_write')?.className).toMatch(/border-burgundy/);
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    await waitFor(() => expect(document.activeElement).toBe(within(write).getByLabelText('The proposed episode')));
    fireEvent.click(within(ready).getByRole('button', { name: 'Set it up: A graphic novel of "Story 41"' }));
    expect(within(screen.getByRole('form', { name: 'Plan a graphic novel from a story' })).getByLabelText('The approved story')).toHaveValue('41');
    expect(called('corner_request_create')).toEqual([]);
    // with a goal chosen, only its own suggestions; what was typed in a form hidden meanwhile is kept
    fireEvent.change(within(write).getByLabelText('Note for the editor (optional)'), { target: { value: 'For the river chapter' } });
    fireEvent.click(within(goals).getByRole('button', { name: /A picture/ }));
    expect(within(screen.getByRole('region', { name: 'Ready in this text' })).getAllByRole('listitem')).toHaveLength(1);
    expect(screen.queryByRole('form', { name: 'Write a proposed episode' })).toBeNull();
    fireEvent.click(within(goals).getByRole('button', { name: /A story/ }));
    expect(within(screen.getByRole('form', { name: 'Write a proposed episode' })).getByLabelText('Note for the editor (optional)'))
      .toHaveValue('For the river chapter');
  });

  it('before C13 a researcher is offered only what her view can tell: no picture or novel suggestions', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    sb.byFn.corpus_reader_stories = ok([STORY(34, 'approved'), STORY(41, 'approved')]);
    sb.byFn.corner_offering = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corner_offering without parameters in the schema cache' } };
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    expect(await screen.findByRole('form', { name: 'A story from passages you choose' })).toBeInTheDocument();
    await waitFor(() => expect(called('corpus_reader_novels').length).toBeGreaterThan(0));
    await waitFor(() => expect(screen.getByText(/2 approved stories · 0 pictures · 0 graphic novels/)).toBeInTheDocument());
    expect(screen.queryByRole('region', { name: 'Ready in this text' })).toBeNull();
    // an editor is shown everything, so she is offered them
  });

  it('a story from passages chosen in the text, and a picture whose brief starts from the English', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_kinds = ok(KINDS);
    sb.byFn.corpus_reader_docs = ok(DOCS);
    sb.byFn.corpus_reader_page = ok([PASSAGE(1, 'The lake of Kashmir lay below the snowy peaks.'), PASSAGE(2, 'Nila rose.'),
      PASSAGE(3, null), PASSAGE(4, 'The goddess flowed down to the plain.'), { ...PASSAGE(5, 'Book one, chapter two'), text_type: 'noise' }]);
    sb.byFn.corner_request_create = ok([{ request_id: 7, request_status: 'pending', est_usd: 0.01, message: "Waiting for an editor's approval." }]);
    mount('/corpus/corner?tab=ask&doc=nilamata_seg');
    const form = await screen.findByRole('form', { name: 'A story from passages you choose' });
    expect(within(form).getByLabelText('From passage')).toHaveAttribute('placeholder', 'such as 25.2');
    fireEvent.click(within(form).getByRole('button', { name: 'Choose them in the text' }));
    const text = await within(form).findByRole('region', { name: 'Choose the passages in the text' });
    await within(text).findByText('The lake of Kashmir lay below the snowy peaks.');
    expect(called('corpus_reader_page')[0].args).toEqual({ p_doc: 'nilamata_seg', p_offset: 0, p_limit: 50 });
    expect(within(text).getByText('Not translated yet')).toBeInTheDocument();
    expect(within(text).queryByRole('button', { name: 'From here: 25.3' })).toBeNull();
    expect(within(text).getByText('Passages 1 to 50 of 900')).toBeInTheDocument();
    fireEvent.click(within(text).getByRole('button', { name: 'From here: 25.2' }));
    fireEvent.click(within(text).getByRole('button', { name: 'To here: 25.4' }));
    expect(within(form).getByLabelText('From passage')).toHaveValue('25.2');
    expect(within(form).getByLabelText('To passage')).toHaveValue('25.4');
    expect(within(form).getByText('3 passages.')).toBeInTheDocument();
    fireEvent.change(within(form).getByLabelText('A working title'), { target: { value: 'The lake' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Ask the desk' }));
    await waitFor(() => expect(called('corner_request_create')).toHaveLength(1));
    expect(called('corner_request_create')[0].args).toMatchObject({ p_kind: 'story_range', p_params: { from: '25.2', to: '25.4', title: 'The lake' } });
    expect(await within(form.parentElement as HTMLElement).findByRole('link', { name: 'Learn' })).toHaveAttribute('href', '/corpus/learn');
    // typing a reference again forgets the place chosen in the text
    fireEvent.change(within(form).getByLabelText('To passage'), { target: { value: '25.9' } });
    expect(within(form).queryByText('3 passages.')).toBeNull();

    const pic = screen.getByRole('form', { name: 'A picture for a passage' });
    fireEvent.click(within(pic).getByRole('button', { name: 'Choose it in the text' }));
    expect(within(form).queryByRole('region', { name: 'Choose the passages in the text' })).toBeNull();   // one at a time
    const one = await within(pic).findByRole('region', { name: 'Choose the passage in the text' });
    fireEvent.click(await within(one).findByRole('button', { name: 'This one: 25.1' }));
    expect(within(pic).getByLabelText('The passage')).toHaveValue('25.1');
    const brief = within(pic).getByLabelText('What the picture should show');
    expect(brief).toHaveValue('The lake of Kashmir lay below the snowy peaks.');
    // the brief follows the passage until it is written in
    fireEvent.click(within(one).getByRole('button', { name: 'This one: 25.2' }));
    expect(brief).toHaveValue('Nila rose.');
    fireEvent.change(brief, { target: { value: 'Nila rises from the lake, crowned, his people behind him.' } });
    fireEvent.click(within(one).getByRole('button', { name: 'This one: 25.4' }));
    expect(within(pic).getByLabelText('The passage')).toHaveValue('25.4');
    expect(brief).toHaveValue('Nila rises from the lake, crowned, his people behind him.');
    expect(within(one).getByText(/a running head or front matter/)).toBeInTheDocument();
    expect(within(one).queryByRole('button', { name: 'This one: 25.5' })).toBeNull();
    fireEvent.click(within(one).getByRole('button', { name: 'Close the text' }));
    expect(within(pic).queryByRole('region', { name: 'Choose the passage in the text' })).toBeNull();
    // another text: its passages are not this one's
    fireEvent.change(textSelect(), { target: { value: 'harita_smriti' } });
    expect(within(screen.getByRole('form', { name: 'A picture for a passage' })).getByLabelText('The passage')).toHaveValue('');
    expect(within(screen.getByRole('form', { name: 'A story from passages you choose' })).getByLabelText('From passage')).toHaveValue('');
  });
});

describe('an anthology holds approved stories only', () => {
  it('a researcher, shown drafts once C13 is in, is offered approved stories alone; an editor sees drafts too', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corpus_reader_stories = ok([STORY(34, 'approved'), STORY(35, 'draft'), STORY(36, 'candidate')]);
    const view = mount('/corpus/anthologies/new');
    expect(await screen.findByRole('button', { name: 'Add "Story 34"' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add "Story 35"' })).toBeNull();   // corner_collection_save would refuse it
    expect(screen.queryByRole('button', { name: 'Add "Story 36"' })).toBeNull();
    view.unmount();
    sb.byFn.corner_me = ok([ME({ is_editor: true })]);
    mount('/corpus/anthologies/new');
    expect(await screen.findByRole('button', { name: 'Add "Story 35"' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add "Story 36"' })).toBeNull();
  });
});

describe('the Reply-to setting', () => {
  it('no longer shows an address that looks saved, and says why nartiang.org will not do', () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <MailAdminCard prefs={{ on_my_requests: true, on_queue: true, mail_enabled: true, is_editor: true, mail_from: 'Srangam desk <desk@nartiang.org>' }} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    const reply = screen.getByLabelText('Address', { selector: '#mail-reply' });
    expect(reply).toHaveValue('');
    expect(reply).toHaveAttribute('placeholder', 'an inbox you read');
    expect(screen.getByText(/nartiang.org receives no mail/)).toBeInTheDocument();
    expect(screen.getByLabelText('Address', { selector: '#mail-site' })).toHaveAttribute('placeholder', 'such as https://srangam.nartiang.org');
  });
});
