/**
 * LEARN_T1_2026_10_09 - Learn the working corpus: the quests, XP, levels and badges, the "I did
 * this" button, the editors' Team panel, the page without C11, and the Learn tab. The pure rules
 * first; then the page against a mocked supabase whose answers are set per database function.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
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
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  BADGES, badgeName, doneDate, groupByTrack, LEARN_MARK, LEVELS, levelFor, levelProgress, markedDone, nextQuest, QUESTS,
  refusedByCorpus, summarize, TOOLBOX, trackProgress, TRACKS, type QuestRow,
} from '@/lib/learn';
import CorpusLearn from '@/pages/corpus/CorpusLearn';
import CorpusNav from '@/components/corpus/CorpusNav';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);

// The catalogue as C11 seeds it.
const CAT: [string, string, number, 'self' | 'auto', boolean][] = [
  ['find_library', 'find', 10, 'self', false], ['find_passage', 'find', 10, 'self', false], ['find_views', 'find', 10, 'self', false],
  ['find_search', 'find', 10, 'self', false], ['find_meaning', 'find', 10, 'self', false], ['find_names', 'find', 10, 'self', false],
  ['read_story', 'read', 10, 'self', false], ['read_picture', 'read', 10, 'self', false], ['read_novel', 'read', 10, 'self', false],
  ['read_texts', 'read', 10, 'self', false],
  ['ask_any', 'ask', 20, 'auto', false], ['ask_story', 'ask', 20, 'auto', false], ['ask_done', 'ask', 20, 'auto', false],
  ['ask_write', 'ask', 20, 'auto', false], ['ask_picture', 'ask', 20, 'auto', false], ['ask_novel', 'ask', 20, 'auto', false],
  ['make_anthology', 'make', 30, 'auto', false], ['make_three', 'make', 30, 'auto', false], ['make_published', 'make', 50, 'auto', false],
  ['make_print', 'make', 10, 'self', false],
  ['edit_decide', 'edit', 20, 'auto', true], ['edit_approve', 'edit', 20, 'auto', true], ['edit_publish', 'edit', 20, 'auto', true],
];
const AT = '2026-10-09T08:30:00Z';
const rowsFor = (editor: boolean, done: string[] = []): QuestRow[] => CAT
  .filter((c) => editor || !c[4])
  .map(([quest, track, xp, mode, editors_only]) => ({ quest, track, xp, mode, editors_only, done: done.includes(quest), done_at: done.includes(quest) ? AT : null }));
const FIND = ['find_library', 'find_passage', 'find_views', 'find_search', 'find_meaning', 'find_names'];
const SUMMARY = (extra: Record<string, unknown> = {}) => ({
  xp: 60, level: 'Explorer', level_index: 1, next_level: 'Storyteller', next_level_xp: 120, badges: ['find'],
  quests_done: 6, quests_total: 20, ...extra,
});
const MISSING = (fn: string): RpcAnswer => ({
  data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn} without parameters in the schema cache` },
});

function mount(path = '/corpus/learn') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/learn" element={<CorpusLearn />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
});

describe('the rules', () => {
  it('every quest of the catalogue has its words and a link; the tracks, badges and levels are named', () => {
    expect(LEARN_MARK).toBe('LEARN_T1_2026_10_09');
    for (const [key] of CAT) {
      expect(QUESTS[key], key).toBeDefined();
      expect(QUESTS[key].title.length, key).toBeGreaterThan(5);
      expect(QUESTS[key].steps.length, key).toBeGreaterThan(0);
      expect(QUESTS[key].href, key).toMatch(/^\/(corpus|texts)/);
    }
    expect(Object.keys(QUESTS).sort()).toEqual(CAT.map((c) => c[0]).sort());
    expect(QUESTS.find_passage.href).toBe('/corpus/nilamata_seg?at=25.7');
    expect(QUESTS.ask_story.href).toBe('/corpus/corner?tab=ask&kind=story_range');
    expect(QUESTS.make_anthology.href).toBe('/corpus/anthologies/new');
    expect(QUESTS.read_texts.href).toBe('/texts');
    expect(QUESTS.find_views.steps.join(' ')).toMatch(/IAST, English and Hindi/);
    expect(TRACKS.map((t) => t.key)).toEqual(['find', 'read', 'ask', 'make', 'edit']);
    expect(BADGES).toEqual({ find: 'Wayfinder', read: 'Close reader', ask: 'Desk hand', make: 'Anthologist', edit: "Editor's hand" });
    expect(badgeName('make')).toBe('Anthologist');
    expect(badgeName('later')).toBe('later');
    expect(LEVELS.map((l) => [l.name, l.min])).toEqual([['Reader', 0], ['Explorer', 50], ['Storyteller', 120], ['Curator', 200], ['Keeper', 280]]);
    expect(TOOLBOX.map((t) => t.name)).toEqual(['Library', 'Reader', 'Search', 'Names', 'Stories', 'Pictures', 'Graphic novels',
      'Published texts', "Researchers' Corner", 'Anthologies']);
  });

  it('groups by track, counts progress and suggests the next quest', () => {
    const res = groupByTrack(rowsFor(false, FIND));
    expect(res.map((g) => g.key)).toEqual(['find', 'read', 'ask', 'make']);   // no edit track for a researcher
    expect(res[0]).toMatchObject({ title: 'Find your way', badge: 'Wayfinder', done: 6, total: 6, xp: 60, xpDone: 60, complete: true });
    expect(res[3]).toMatchObject({ done: 0, total: 4, xp: 120, complete: false });
    expect(res[3].quests.map((q) => q.quest)).toEqual(['make_anthology', 'make_three', 'make_published', 'make_print']);
    expect(groupByTrack(rowsFor(true)).map((g) => g.key)).toEqual(['find', 'read', 'ask', 'make', 'edit']);
    expect(groupByTrack([null, { x: 1 }, ...rowsFor(false)]).flatMap((g) => g.quests)).toHaveLength(20);
    expect(trackProgress([])).toEqual({ done: 0, total: 0, xp: 0, xpDone: 0, complete: false });
    expect(nextQuest(rowsFor(false))?.quest).toBe('find_library');
    expect(nextQuest(rowsFor(false, FIND))?.quest).toBe('read_story');
    expect(nextQuest(rowsFor(false, CAT.map((c) => c[0])))).toBeNull();
    // a quest the site has no words for yet still shows
    const later = groupByTrack([{ quest: 'find_later', track: 'find', xp: 5, mode: 'self', editors_only: false, done: false, done_at: null }]);
    expect(later[0].quests[0].copy.title).toBe('find later');
  });

  it('levels, the XP bar and the summary as the database makes them', () => {
    expect(levelFor(0)).toEqual({ level: LEVELS[0], next: LEVELS[1] });
    expect(levelFor(49).level.name).toBe('Reader');
    expect(levelFor(50).level.name).toBe('Explorer');
    expect(levelFor(199)).toEqual({ level: LEVELS[2], next: LEVELS[3] });
    expect(levelFor(400)).toEqual({ level: LEVELS[4], next: null });
    expect(levelProgress({ xp: 85, next_level_xp: 120 })).toEqual({ min: 50, max: 120, now: 85, pct: 50, toNext: 35 });
    expect(levelProgress({ xp: 300, next_level_xp: null })).toEqual({ min: 280, max: 300, now: 300, pct: 100, toNext: null });
    expect(summarize(rowsFor(false, FIND))).toEqual(SUMMARY());
    const all = summarize(rowsFor(true, CAT.map((c) => c[0])));
    expect(all).toEqual({ xp: 400, level: 'Keeper', level_index: 4, next_level: null, next_level_xp: null,
      badges: ['find', 'read', 'ask', 'make', 'edit'], quests_done: 23, quests_total: 23 });
    expect(summarize(rowsFor(false, CAT.map((c) => c[0]))).xp).toBe(340);
    expect(doneDate('2026-10-09T08:30:00Z')).toBe('9 Oct 2026');
    expect(doneDate(null)).toBe('');
    expect(doneDate('nonsense')).toBe('');
    const marked = markedDone(rowsFor(false), 'read_story', '2026-10-09T10:00:00Z');
    expect(marked?.find((r) => r.quest === 'read_story')).toMatchObject({ done: true, done_at: '2026-10-09T10:00:00Z' });
    expect(marked?.filter((r) => r.done)).toHaveLength(1);
    expect(refusedByCorpus({ refused: true, error: 'The working corpus is open to signed-in readers only.' })).toBe(true);
    expect(refusedByCorpus({ refused: true, error: 'Learn is open to invited researchers and editors.' })).toBe(false);
  });
});

describe('/corpus/learn', () => {
  it('a researcher: their level, XP and badges, four tracks, no editors\' track and no team', async () => {
    sb.byFn.learn_me = ok(rowsFor(false, FIND));
    sb.byFn.learn_summary = ok([SUMMARY()]);
    mount();
    expect(await screen.findByRole('heading', { level: 2, name: 'Find your way' })).toBeInTheDocument();
    const heads = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(heads).toEqual(['Your progress', 'Find your way', 'Read what the desk made', 'Ask the desk', 'Make and publish',
      'Your toolbox', 'How the desk works']);
    await waitFor(() => expect(called('learn_summary')).toHaveLength(1));
    const progress = screen.getByRole('region', { name: 'Your progress' });
    expect(within(progress).getByText('Explorer')).toBeInTheDocument();
    expect(within(progress).getByText('60')).toBeInTheDocument();
    expect(within(progress).getByText('6 of 20')).toBeInTheDocument();
    const bar = within(progress).getByRole('progressbar', { name: 'XP towards Storyteller' });
    expect(bar).toHaveAttribute('aria-valuemin', '50');
    expect(bar).toHaveAttribute('aria-valuemax', '120');
    expect(bar).toHaveAttribute('aria-valuenow', '60');
    expect(bar).toHaveAttribute('aria-valuetext', '60 XP, 60 more to Storyteller');
    expect(within(progress).getByText('60 XP more to Storyteller (at 120 XP).')).toBeInTheDocument();
    const badges = within(progress).getByRole('list', { name: 'Badges' });
    expect(within(badges).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'Wayfinderearned', 'Close readernot yet: finish Read what the desk made', 'Desk handnot yet: finish Ask the desk',
      'Anthologistnot yet: finish Make and publish']);
    const find = screen.getByRole('region', { name: 'Find your way' });
    expect(within(find).getByText('Badge earned: Wayfinder')).toBeInTheDocument();
    expect(within(find).getByRole('progressbar', { name: 'Find your way: quests done' })).toHaveAttribute('aria-valuenow', '6');
    expect(within(find).getAllByText('Done on 9 Oct 2026')).toHaveLength(6);
    expect(within(find).queryByRole('button', { name: /I did this/ })).toBeNull();
    expect(within(find).getByRole('link', { name: 'Try it: Jump straight to a passage' })).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.7');
    expect(screen.getByText('Next quest:').parentElement).toHaveTextContent('Read a story and open one of its citations');
    expect(screen.queryByRole('region', { name: 'For editors' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Team' })).toBeNull();
    expect(called('learn_team')).toEqual([]);
    expect(screen.getByRole('navigation', { name: 'On this page' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Learn | Working Corpus | Srangam'));
    expect(document.querySelector('meta[name="robots"]')?.getAttribute('content')).toBe('noindex, nofollow');
  });

  it('auto quests are checked for you, with no "I did this"; the Ask track says what a request costs', async () => {
    sb.byFn.learn_me = ok(rowsFor(false, ['ask_any']));
    sb.byFn.learn_summary = ok([SUMMARY({ xp: 20, level: 'Reader', level_index: 0, next_level: 'Explorer', next_level_xp: 50, badges: [], quests_done: 1 })]);
    mount();
    const ask = await screen.findByRole('region', { name: 'Ask the desk' });
    expect(within(ask).queryByRole('button')).toBeNull();
    expect(within(ask).getAllByText('Checked for you from the Corner')).toHaveLength(5);
    expect(within(ask).getByText('Done on 9 Oct 2026 (checked for you)')).toBeInTheDocument();
    expect(within(ask).getByText(/still waits for an editor's approval and counts against the day's cap/)).toBeInTheDocument();
    expect(within(ask).getByRole('link', { name: 'Try it: Ask for a story from passages you choose' }))
      .toHaveAttribute('href', '/corpus/corner?tab=ask&kind=story_range');
    const make = screen.getByRole('region', { name: 'Make and publish' });
    expect(within(make).getAllByRole('button').map((b) => b.getAttribute('aria-label'))).toEqual(['I did this: Print an anthology or save it as PDF']);
  });

  it('"I did this" marks a self quest and the page shows it done', async () => {
    sb.byFn.learn_me = ok(rowsFor(false, FIND));
    sb.byFn.learn_summary = ok([SUMMARY()]);
    sb.byFn.learn_mark = ok(true);
    mount();
    const read = await screen.findByRole('region', { name: 'Read what the desk made' });
    const btn = within(read).getByRole('button', { name: 'I did this: Read a story and open one of its citations' });
    expect(btn).toHaveTextContent('I did this');
    sb.byFn.learn_me = ok(rowsFor(false, [...FIND, 'read_story']));
    sb.byFn.learn_summary = ok([SUMMARY({ xp: 70, quests_done: 7 })]);
    fireEvent.click(btn);
    await waitFor(() => expect(called('learn_mark')).toHaveLength(1));
    expect(called('learn_mark')[0].args).toEqual({ p_quest: 'read_story' });
    await waitFor(() => expect(within(read).queryByRole('button', { name: 'I did this: Read a story and open one of its citations' })).toBeNull());
    expect(within(read).getByText(/^Done on/)).toBeInTheDocument();
    expect(within(read).getByRole('progressbar', { name: 'Read what the desk made: quests done' })).toHaveAttribute('aria-valuenow', '1');
    await waitFor(() => expect(within(screen.getByRole('region', { name: 'Your progress' })).getByText('70')).toBeInTheDocument());
    expect(called('learn_me').length).toBeGreaterThanOrEqual(2);              // read again after marking
  });

  it("the server's refusal of a mark is shown as it is", async () => {
    sb.byFn.learn_me = ok(rowsFor(false));
    sb.byFn.learn_summary = ok([SUMMARY({ xp: 0, level: 'Reader', badges: [], quests_done: 0 })]);
    sb.byFn.learn_mark = { data: null, error: { code: '22023', message: 'No such quest: find_library.' } };
    mount();
    fireEvent.click(await screen.findByRole('button', { name: 'I did this: Open the Library and pick a text' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No such quest: find_library.');
    expect(screen.getByRole('button', { name: 'I did this: Open the Library and pick a text' })).toBeInTheDocument();
  });

  it('an editor: the editors\' track and the team', async () => {
    sb.byFn.learn_me = ok(rowsFor(true, ['edit_decide']));
    sb.byFn.learn_summary = ok([SUMMARY({ xp: 20, level: 'Reader', level_index: 0, next_level: 'Explorer', next_level_xp: 50, badges: [], quests_done: 1, quests_total: 23 })]);
    sb.byFn.learn_team = ok([
      { user_id: 'u-r', email: 'kanika@example.org', roles: ['researcher'], xp: 100, level: 'Explorer', quests_done: 8, last_activity: '2026-10-09T10:05:00Z' },
      { user_id: 'u-s', email: 'dhruv.rakesh@gmail.com', roles: ['admin', 'super_admin'], xp: 0, level: 'Reader', quests_done: 0, last_activity: null },
    ]);
    mount();
    const edit = await screen.findByRole('region', { name: 'For editors' });
    expect(within(edit).getByText('Done on 9 Oct 2026 (checked for you)')).toBeInTheDocument();
    expect(within(edit).queryByRole('button')).toBeNull();
    const team = await screen.findByRole('region', { name: 'Team' });
    expect(await within(team).findByText('kanika@example.org')).toBeInTheDocument();
    expect(called('learn_team')).toHaveLength(1);
    const items = within(team).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('researcher');
    expect(items[0]).toHaveTextContent('Explorer · 100 XP · 8 quests done');
    expect(items[0]).toHaveTextContent(/Last activity: 9 Oct 2026/);
    expect(items[1]).toHaveTextContent('admin, super admin');
    expect(items[1]).toHaveTextContent('Reader · 0 XP · 0 quests done');
    expect(items[1]).toHaveTextContent('Last activity: none yet');
    const badges = within(screen.getByRole('region', { name: 'Your progress' })).getByRole('list', { name: 'Badges' });
    expect(within(badges).getAllByRole('listitem')).toHaveLength(5);
    expect(within(badges).getByText("Editor's hand")).toBeInTheDocument();
    expect(within(screen.getByRole('navigation', { name: 'On this page' })).getByRole('link', { name: 'Team' })).toHaveAttribute('href', '#team');
  });

  it('without C11: the toolbox and how the desk works, a quiet note, no error', async () => {
    sb.byFn.learn_me = MISSING('learn_me');
    mount();
    expect(await screen.findByText(/Progress is not switched on here yet/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('heading', { level: 2, name: 'Your toolbox' })).toBeInTheDocument();
    const desk = screen.getByRole('region', { name: 'How the desk works' });
    expect(within(desk).getAllByRole('listitem').map((li) => li.querySelector('p')?.textContent)).toEqual([
      '1You ask', '2An editor approves', '3The desk takes it', '4Results arrive as drafts']);
    expect(within(desk).getByText(/about every 10 minutes/)).toBeInTheDocument();
    const tools = screen.getByRole('region', { name: 'Your toolbox' });
    expect(within(tools).getByRole('link', { name: 'Names' })).toHaveAttribute('href', '/corpus/names');
    expect(within(tools).getByRole('link', { name: 'Published texts' })).toHaveAttribute('href', '/texts');
    expect(within(tools).getAllByRole('link')).toHaveLength(10);
    expect(screen.queryByRole('region', { name: 'Your progress' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Find your way' })).toBeNull();
    expect(screen.queryByRole('button', { name: /I did this/ })).toBeNull();
    expect(called('learn_summary')).toEqual([]);
    expect(called('learn_team')).toEqual([]);
  });

  it('a reader who is not invited: why, and the toolbox; not a reader at all: the refusal only', async () => {
    sb.byFn.learn_me = { data: null, error: { code: '42501', message: 'Learn is open to invited researchers and editors.' } };
    const { unmount } = mount();
    expect(await screen.findByText('The quests are for invited researchers and editors.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Your toolbox' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Your progress' })).toBeNull();
    unmount();
    sb.byFn.learn_me = { data: null, error: { code: '42501', message: 'The working corpus is open to signed-in readers only.' } };
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('The working corpus is open to signed-in readers only.');
    expect(screen.queryByRole('region', { name: 'Your toolbox' })).toBeNull();
  });

  it('a loading failure is a failure, and the toolbox stays', async () => {
    sb.byFn.learn_me = { data: null, error: { code: '57014', message: 'canceling statement due to statement timeout' } };
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('Your progress could not be loaded.');
    expect(screen.getByRole('region', { name: 'Your toolbox' })).toBeInTheDocument();
  });

  it('without learn_summary, the page counts from the quests', async () => {
    sb.byFn.learn_me = ok(rowsFor(false, [...FIND, 'read_story', 'read_picture', 'read_novel', 'read_texts', 'ask_any']));
    sb.byFn.learn_summary = MISSING('learn_summary');
    mount();
    const progress = await screen.findByRole('region', { name: 'Your progress' });
    expect(await within(progress).findByText('120')).toBeInTheDocument();
    expect(within(progress).getByText('Storyteller')).toBeInTheDocument();
    expect(within(progress).getByText('11 of 20')).toBeInTheDocument();
  });
});

describe('the corpus tabs', () => {
  it('Learn is a tab, lit on /corpus/learn while the Library is not', () => {
    const { unmount } = render(<MemoryRouter initialEntries={['/corpus/learn']}><CorpusNav /></MemoryRouter>);
    const lit = screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent?.trim());
    expect(lit).toEqual(['Learn']);
    expect(screen.getByRole('link', { name: 'Learn' })).toHaveAttribute('href', '/corpus/learn');
    const names = screen.getAllByRole('link').map((a) => a.textContent?.trim());
    expect(names.indexOf('Learn')).toBeGreaterThan(names.indexOf('Corner'));
    unmount();
    render(<MemoryRouter initialEntries={['/corpus/nilamata_seg']}><CorpusNav /></MemoryRouter>);
    expect(screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent?.trim())).toEqual(['Library']);
  });
});
