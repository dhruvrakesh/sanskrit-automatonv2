/**
 * INDEX_SITE_2026_10_25 - the indexes' genealogies on the site: /corpus/genealogies (the three indexes with their
 * counts and credits, a search by the index's head word folded as the desk folds it, the longest lines), and
 * /corpus/genealogies/:source/:entry (the line as the desk draws it, each step with what it rests on: the index's
 * words and references, the GRETIL verse where both names stand with the names marked, the epics' counts, our own
 * passages as links into the reader; other parents with ?via=, siblings, children), from the five reader functions
 * of docs/cloud/C21; the names page's "In the indexes". Before C21 the pages say so; nothing is rendered as HTML.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn?: string; args?: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => {
      sb.calls.push({ fn, args });
      return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  citeBlocks, collapseNames, epicLine, findIndexPersons, foldName, groupStatements, loadIndexOfName, loadIndexOverview,
  loadIndexTree, markForms, personHref, placeHref, stepChips, type Statement, type Step, type Tree,
} from '@/lib/indexSite';
import { CORPUS_LINKS } from '@/components/navigation/CorpusMenu';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusGenealogies from '@/pages/corpus/CorpusGenealogies';
import CorpusGenealogy from '@/pages/corpus/CorpusGenealogy';
import CorpusNames from '@/pages/corpus/CorpusNames';

const MISSING = (fn: string): RpcAnswer => ({
  data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn} in the schema cache` },
});
const REFUSED: RpcAnswer = { data: null, error: { code: '42501', message: 'The working corpus is open to signed-in readers only.' } };
const one = (v: unknown): RpcAnswer => ({ data: [{ result: v }], error: null });

const person = (entry: number, head: string, extra: Record<string, unknown> = {}) => ({
  entry, head, sex: 'm', named_only: entry < 0, parents: 1, children: 1, up: 1, down: 1, canonical: null, spouses: [], ...extra,
});
const stmt = (extra: Partial<Statement>): Statement => ({
  key: 'k1', source: 'pui', stated_in: 'Daśaratha (II)', entry_id: 13, relation: 'son_of', subject: 'Daśaratha (II)',
  object: 'Aja (IV)', words: 'son of Aja', refs: ['Vi. IV. 4. 86'], n: 1, subject_entry: 13, object_entry: 11,
  subject_canonical: 'Daśaratha', object_canonical: 'Aja', ours: 'named together', passages: 1, texts: 1,
  places: [{ doc: 'vishnu_purana', page: 7, idx: 3, ref: '4.4.86' }], cited: 'both',
  cites: [{ text: 'vi', ref: '4.4.86', verdict: 'both', printed: 'Vi. IV. 4. 86', at: ['4.4.86'], subject_form: 'daśarathaḥ', object_form: 'ajād' },
          { text: 'mbh', ref: '1.90.47', verdict: 'both', at: ['1.90.47'] }],
  best_text: 'vi', best_ref: '4.4.86', together: { mbh: [3, '1.90.47'], hv: [1, '10.1'], ram: [0, ''] }, ...extra,
});
const step = (parent: number, child: number, extra: Partial<Step> = {}): Step => ({
  parent, child, joined: 'rule', both_entries: true, cited: 'both', ours: 'named together',
  epic: { mbh: [3, '1.90.47'], hv: [0, ''], ram: [0, ''] }, items: [stmt({})], ...extra,
});
const TREE: Tree = {
  source: 'pui', entry: 13, me: 2, title: 'Purana Index (V. R. R. Dikshitar, 1951-55)', person: person(13, 'Daśaratha (II)'),
  line: [
    { ...person(10, 'Raghu (I)'), generation: -2, siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(11, 'Aja (IV)'), generation: -1, siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(13, 'Daśaratha (II)', { canonical: 'Daśaratha', spouses: [{ entry: -40, head: 'Kausalyā' }] }), generation: 0,
      siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(14, 'Rāma (II)'), generation: 1, siblings: [{ entry: 17, head: 'Lakṣmaṇa (I)' }], siblings_n: 3,
      other_parents: [{ ...person(-40, 'Kausalyā', { sex: 'f' }), evidence: null }, { ...person(30, 'Ajapāla'), evidence: null }] },
  ],
  steps: [
    step(10, 11, { cited: 'no citation', ours: 'not tied', epic: { mbh: [0, ''], hv: [0, ''], ram: [0, ''] },
      items: [stmt({ key: 'k0', subject: 'Aja (IV)', object: 'Raghu (I)', words: '<b>son</b> of Raghu', refs: [], cites: [],
        cited: 'no citation', ours: 'not tied', places: [], together: {} })] }),
    step(11, 13),
    step(13, 14, { both_entries: false, joined: 'verse', cited: 'one', ours: '', epic: { mbh: [0, ''], hv: [0, ''], ram: [0, ''] },
      items: [stmt({ key: 'k2', subject: 'Rāma (II)', object: 'Daśaratha', words: 'son of Daśaratha', cited: 'one', ours: 'not tied',
        places: [], cites: [{ text: 'bh', ref: '9.10.2', verdict: 'one', printed: 'Bhā. IX. 10. 2', at: ['9.10.2'], subject_form: 'rāmaḥ' }],
        together: {} })] }),
  ],
  down: [[{ ...person(14, 'Rāma (II)'), of: 13, on_line: true, evidence: step(13, 14) },
          { ...person(17, 'Lakṣmaṇa (I)'), of: 13, on_line: false, evidence: step(13, 17, { cited: 'one' }) }]],
  verses: { 'vi|4.4.86': 'ajād daśarathaḥ', 'bh|9.10.2': 'daśarathāt rāmaḥ', 'hv|10.1': 'ikṣvākor vaṃśam' },
  texts: {
    vi: { title: 'Viṣṇupurāṇa', edition: 'Bombay, 1910', rights: 'CC BY-NC-SA 4.0', show: true },
    mbh: { title: 'Mahābhārata, critical edition', edition: 'BORI e-text', rights: 'reference only', show: false },
  },
};
const OVERVIEW = {
  sources: [
    { source: 'inm', title: 'An Index to the Names in the Mahabharata (S. Soerensen, 1904)', edition: 'London, 1904-25', rights: 'CC BY-NC-SA 3.0', persons: 3773, tied: 1010, steps: 2909, statements: 8495, lines: 23 },
    { source: 'pui', title: 'Purana Index (V. R. R. Dikshitar, 1951-55)', edition: 'Madras, 1951-55', rights: 'CC BY-NC-SA 3.0', persons: 10147, tied: 2625, steps: 7779, statements: 12130, lines: 30 },
    { source: 'vei', title: 'Vedic Index of Names and Subjects (Macdonell and Keith, 1912)', edition: 'London, 1912', rights: 'CC BY-NC-SA 3.0', persons: 275, tied: 54, steps: 173, statements: 1396, lines: 0 },
  ],
  texts: [{ code: 'vi', title: 'Viṣṇupurāṇa', edition: 'Bombay, 1910', rights: 'CC BY-NC-SA 4.0', show: true }],
  run: { mark: 'INDEX_SITE_2026_10_25', synced_at: '2026-10-25T14:02:33Z' },
};
const LINES = [
  { source: 'pui', rank: 1, entries: [10, 11, 13, 14, 15, 16, 18, 19], heads: ['Raghu (I)', 'Aja (IV)', 'Daśaratha (II)', 'Rāma (II)', 'Kuśa (I)', 'Atithi (I)', 'Niṣadha', 'Nala'], length: 8, both_steps: 5 },
  { source: 'inm', rank: 1, entries: [1, 2, 3, 4, 5, 6], heads: ['Kāśyapa', 'Indra', 'Arjuna[2]', 'Abhimanyu', 'Parikṣit', 'Janamejaya'], length: 6, both_steps: 2 },
];

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/genealogies" element={<CorpusGenealogies />} />
            <Route path="/corpus/genealogies/:source/:entry" element={<CorpusGenealogy />} />
            <Route path="/corpus/names/:canonical" element={<CorpusNames />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe('names, folded as the desk folds them (relations_view.fold of split_mark)', () => {
  it('the mark, the honorific, the brackets and the diacritics go', () => {
    expect(foldName('Daśaratha (II)')).toBe('dasaratha');
    expect(foldName('Janamejaya[1]')).toBe('janamejaya');
    expect(foldName('2. Kuru')).toBe('kuru');
    expect(foldName('Śrī Rāma')).toBe('rama');
    expect(foldName('Kalmāṣapāda (Mitrasaha- Vi.)')).toBe('kalmasapada');
    expect(foldName('Sabhānar(l)a')).toBe('sabhanara');
    expect(foldName('Brahmán[1]')).toBe('brahman');
    expect(foldName('  ')).toBe('');
  });
});

describe('the loaders', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('ask the reader functions of C21, and read their one row', async () => {
    sb.byFn.corpus_reader_index_overview = one(OVERVIEW);
    const o = await loadIndexOverview();
    expect(sb.calls[0]).toEqual({ fn: 'corpus_reader_index_overview', args: {} });
    expect(o.ok && o.value?.sources.length).toBe(3);
    sb.byFn.corpus_reader_index_tree = one(TREE);
    const t = await loadIndexTree('pui', 14, -40, 9);
    expect(sb.calls[1]).toEqual({ fn: 'corpus_reader_index_tree', args: { p_source: 'pui', p_entry: 14, p_via: -40, p_down: 4 } });
    expect(t.value?.me).toBe(2);
    await loadIndexOfName('Daśaratha');
    expect(sb.calls[2]).toEqual({ fn: 'corpus_reader_index_of_name', args: { p_canonical: 'Daśaratha' } });
  });

  it('find sends the folded name, and nothing for one letter', async () => {
    await findIndexPersons('Daśaratha (II)', 'pui', 99);
    expect(sb.calls[0]).toEqual({ fn: 'corpus_reader_index_find', args: { p_fold: 'dasaratha', p_source: 'pui', p_k: 50 } });
    const r = await findIndexPersons('D');
    expect(r.ok && r.rows.length === 0).toBe(true);
    expect(sb.calls).toHaveLength(1);
  });

  it('a person the index lacks, a missing function, a refusal and an odd answer are told apart', async () => {
    sb.byFn.corpus_reader_index_tree = one({ error: 'no such person in the index' });
    let t = await loadIndexTree('pui', 99999);
    expect([t.ok, t.error, t.missing, t.refused]).toEqual([false, 'no such person in the index', false, false]);
    sb.byFn.corpus_reader_index_tree = MISSING('corpus_reader_index_tree');
    t = await loadIndexTree('pui', 13);
    expect([t.ok, t.missing]).toEqual([false, true]);
    sb.byFn.corpus_reader_index_tree = REFUSED;
    t = await loadIndexTree('pui', 13);
    expect([t.ok, t.refused]).toEqual([false, true]);
    sb.byFn.corpus_reader_index_tree = { data: [], error: null };
    t = await loadIndexTree('pui', 13);
    expect(t.error).toMatch(/unexpected form/);
  });
});

describe('what a step rests on, in words', () => {
  it('the chips, as the desk draws them', () => {
    expect(stepChips(step(11, 13)).map((c) => c.label)).toEqual(['verse ✓', 'MBh 3', 'ours: together']);
    expect(stepChips({ cited: '', epic: {}, ours: 'not tied', joined: 'named' }).map((c) => c.label)).toEqual(['a name only']);
    expect(stepChips({ cited: '', epic: {}, ours: '', joined: 'rule' }).map((c) => c.label)).toEqual(['the index alone']);
  });

  it('verses only of the texts shown, two at most; the names marked; the epics in words', () => {
    const b = citeBlocks(stmt({}), TREE.verses);
    expect(b.map((x) => [x.text, x.verses.length])).toEqual([['vi', 1], ['mbh', 0]]);
    expect(markForms('ajād daśarathaḥ', ['daśarathaḥ', 'ajād'])).toEqual([
      { text: 'ajād', mark: true }, { text: ' ', mark: false }, { text: 'daśarathaḥ', mark: true },
    ]);
    expect(markForms('abc', ['zz'])).toEqual([{ text: 'abc', mark: false }]);
    expect(epicLine({ mbh: [3, '1.90.47'], hv: [1, '10.1'], ram: [0, ''] })).toBe('MBh 1.90.47 and 2 more; HV 10.1');
    expect(personHref('pui', -40)).toBe('/corpus/genealogies/pui/-40');
    expect(personHref('pui', 14, 30)).toBe('/corpus/genealogies/pui/14?via=30');
    expect(placeHref({ doc: 'a b', page: 7, idx: 3, ref: '' })).toBe('/corpus/a%20b?at=7.3');
  });

  it('a name\'s statements in the desk\'s groups, family first, the rest as Other', () => {
    const g = groupStatements([{ relation: 'contemporary_of' }, { relation: 'son_of' }, { relation: 'slew' }, { relation: 'wife_of' }]);
    expect(g.map((x) => [x.label, x.rows.length])).toEqual([['Family', 1], ['Marriage', 1], ['Contemporaries', 1], ['Other', 1]]);
  });

  it('a name given without an entry, stated in several places, is listed once with its count', () => {
    const got = collapseNames([{ entry: -1, head: 'Yayāti' }, { entry: 5, head: 'Yayāti (I)' }, { entry: -2, head: 'Yayāti' },
      { entry: 6, head: 'Yayāti (I)' }]);
    expect(got.map((n) => [n.entry, n.head, n.times])).toEqual([[-1, 'Yayāti', 2], [5, 'Yayāti (I)', 1], [6, 'Yayāti (I)', 1]]);
  });
});

describe('/corpus/genealogies', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('the indexes with their counts, the longest lines opening on their eldest, and the credits', async () => {
    sb.byFn.corpus_reader_index_overview = one(OVERVIEW);
    sb.byFn.corpus_reader_index_lines = { data: LINES, error: null };
    mount('/corpus/genealogies');
    expect(await screen.findByText(/10,147 persons in a line/)).toBeTruthy();
    const a = await screen.findByRole('link', { name: 'Raghu (I) → Nala' });
    expect(a.getAttribute('href')).toBe('/corpus/genealogies/pui/10');
    expect(screen.getByText(/Raghu \(I\) › Aja \(IV\) › Daśaratha \(II\) › Rāma \(II\) › … › Niṣadha › Nala/)).toBeTruthy();
    expect(screen.getByText(/8 generations · 5 of 7 steps/)).toBeTruthy();
    expect(screen.getByText(/No line of six generations or more/)).toBeTruthy();       // the Vedic Index
    expect(screen.getByRole('link', { name: 'The licence' }).getAttribute('href')).toBe('https://creativecommons.org/licenses/by-nc-sa/3.0/');
    fireEvent.click(screen.getByRole('button', { name: 'Mahābhārata names' }));
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Raghu (I) → Nala' })).toBeNull());
    expect(screen.getByRole('link', { name: 'Kāśyapa → Janamejaya' })).toBeTruthy();
  });

  it('finds a person by the head word, folded', async () => {
    sb.byFn.corpus_reader_index_overview = one(OVERVIEW);
    sb.byFn.corpus_reader_index_find = { data: [{ source: 'pui', entry: 13, head: 'Daśaratha (II)', sex: 'm', up: 3, down: 5, canonical: 'Daśaratha', exact: true }], error: null };
    mount('/corpus/genealogies');
    const box = await screen.findByRole('textbox', { name: /A person's name/ });
    fireEvent.change(box, { target: { value: 'dasaratha' } });
    fireEvent.click(screen.getByRole('button', { name: /Find/ }));
    const hit = await screen.findByRole('link', { name: 'Daśaratha (II)' });
    expect(hit.getAttribute('href')).toBe('/corpus/genealogies/pui/13');
    expect(screen.getByText(/lines run up to 2 above and 4 below/)).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_index_find')?.args).toEqual({ p_fold: 'dasaratha', p_source: null, p_k: 30 });
  });

  it('before C21 it says so; before the first sync it says nothing was sent; a refusal is a refusal', async () => {
    sb.byFn.corpus_reader_index_overview = MISSING('corpus_reader_index_overview');
    let v = mount('/corpus/genealogies');
    expect(await screen.findByText(/not switched on yet/)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    v.unmount();
    sb.byFn.corpus_reader_index_overview = one({ ...OVERVIEW, sources: OVERVIEW.sources.map((s) => ({ ...s, persons: 0 })) });
    v = mount('/corpus/genealogies');
    expect(await screen.findByText(/No genealogy has been sent from the desk yet/)).toBeTruthy();
    v.unmount();
    sb.byFn.corpus_reader_index_overview = REFUSED;
    mount('/corpus/genealogies');
    expect(await screen.findByText(/not on the reader list/)).toBeTruthy();
  });
});

describe('/corpus/genealogies/:source/:entry', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('the line with its generations, and the step into the person with what it rests on', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    mount('/corpus/genealogies/pui/13');
    expect(await screen.findByRole('heading', { level: 1, name: /Daśaratha \(II\)/ })).toBeTruthy();
    expect(sb.calls[0]).toEqual({ fn: 'corpus_reader_index_tree', args: { p_source: 'pui', p_entry: 13, p_via: null, p_down: 2 } });
    expect(screen.getByText(/4 generations shown · 1 of 3 steps with both names in the cited verse/)).toBeTruthy();
    const line = screen.getByRole('list', { name: 'The line' });
    expect(within(line).getAllByLabelText(/^generation /).map((n) => n.textContent)).toEqual(['-2', '-1', '0', '+1']);
    expect(within(line).getByRole('link', { name: 'Raghu (I)' }).getAttribute('href')).toBe('/corpus/genealogies/pui/10');
    // the step into the person is chosen first: Aja (IV) -> Dasaratha (II)
    const ev = screen.getByRole('heading', { name: 'What the step rests on' }).parentElement as HTMLElement;
    expect(within(ev).getByText(/both entries state it/)).toBeTruthy();
    expect(within(ev).getByText(/son of Aja/)).toBeTruthy();
    const marks = ev.querySelectorAll('mark');
    expect(Array.from(marks).map((m) => m.textContent)).toEqual(['ajād', 'daśarathaḥ']);
    expect(within(ev).getByText(/Both names in Viṣṇu \(1910\) 4\.4\.86 \(the index prints Vi\. IV\. 4\. 86\)/)).toBeTruthy();
    expect(within(ev).getByText(/Both names in one verse of MBh 1\.90\.47 and 2 more; HV 10\.1/)).toBeTruthy();
    expect(ev.textContent).toContain('ikṣvākor vaṃśam');                       // the Harivamsa's verse, shown
    expect(within(ev).getByRole('link', { name: /4\.4\.86/ }).getAttribute('href')).toBe('/corpus/vishnu_purana?at=7.3');
    expect(within(ev).getByRole('link', { name: 'Aja' }).getAttribute('href')).toBe('/corpus/names/Aja');
  });

  it('other parents with the line through them, siblings, spouses and children; another step chosen', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    mount('/corpus/genealogies/pui/13');
    await screen.findByRole('heading', { level: 1, name: /Daśaratha \(II\)/ });
    const through = screen.getAllByRole('link', { name: 'line through' });
    expect(through.map((a) => a.getAttribute('href'))).toEqual(['/corpus/genealogies/pui/14?via=30']);   // not the name-only mother
    expect(screen.getByText(/3 siblings:/)).toBeTruthy();
    expect(screen.getAllByRole('link', { name: 'Lakṣmaṇa (I)' })[0].getAttribute('href')).toBe('/corpus/genealogies/pui/17');
    expect(screen.getAllByRole('link', { name: 'Kausalyā' })[0].getAttribute('href')).toBe('/corpus/genealogies/pui/-40');
    expect(screen.getByRole('heading', { name: 'Children of Daśaratha (II)' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Rāma (II) ✓' }).className).toContain('border-burgundy');
    fireEvent.click(screen.getByRole('button', { name: 'What the step from Daśaratha (II) to Rāma (II) rests on' }));
    const ev = screen.getByRole('heading', { name: 'What the step rests on' }).parentElement as HTMLElement;
    expect(within(ev).getByText(/one entry states it/)).toBeTruthy();
    expect(within(ev).getByText(/the one whose entry cites the same verse was taken/)).toBeTruthy();
    expect(within(ev).getByText(/One name in Bhāgavata 9\.10\.2/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'What the step from Raghu (I) to Aja (IV) rests on' }));
    expect(within(ev).getByText(/The index gives no verse for this statement/)).toBeTruthy();
    expect(within(ev).getByText(/<b>son<\/b> of Raghu/)).toBeTruthy();                // words are text, never HTML
    expect(ev.querySelector('b b')).toBeNull();
  });

  it('a long passage is cut around the names until opened', async () => {
    const long = 'tatah '.repeat(60) + 'ajād daśarathaḥ ' + 'punah '.repeat(80);
    sb.byFn.corpus_reader_index_tree = one({ ...TREE, verses: { ...TREE.verses, 'vi|4.4.86': long } });
    mount('/corpus/genealogies/pui/13');
    const btn = await screen.findByRole('button', { name: /Show the whole passage/ });
    const q = btn.closest('blockquote') as HTMLElement;
    expect(q.textContent).toContain('ajād daśarathaḥ');
    expect(q.textContent!.length).toBeLessThan(long.length);
    expect(Array.from(q.querySelectorAll('mark')).map((m) => m.textContent)).toEqual(['ajād', 'daśarathaḥ']);
    fireEvent.click(btn);
    expect(q.textContent).toContain(long.trim());
    expect(screen.getByRole('button', { name: 'Show less' }).getAttribute('aria-expanded')).toBe('true');
  });

  it('?via= is sent; a person the index lacks and a missing C21 are told apart', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    let v = mount('/corpus/genealogies/pui/14?via=30');
    await screen.findByRole('heading', { level: 1 });
    expect(sb.calls[0].args).toEqual({ p_source: 'pui', p_entry: 14, p_via: 30, p_down: 2 });
    v.unmount();
    sb.byFn.corpus_reader_index_tree = one({ error: 'no such person in the index' });
    v = mount('/corpus/genealogies/pui/99999');
    expect(await screen.findByText(/This person is not in the index the site has/)).toBeTruthy();
    v.unmount();
    sb.byFn.corpus_reader_index_tree = MISSING('corpus_reader_index_tree');
    mount('/corpus/genealogies/pui/13');
    expect(await screen.findByText(/not switched on yet/)).toBeTruthy();
  });
});

describe('a name of ours in the indexes, and the navigation', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('the names page shows its persons and what the indexes state; nothing before C21', async () => {
    sb.byFn.corpus_reader_index_of_name = one({
      persons: [{ source: 'pui', entry: 13, head: 'Daśaratha (II)', sex: 'm', up: 3, down: 5, parents: 1, children: 4, has_line: true },
                { source: 'pui', entry: 99, head: 'Daśaratha (V)', sex: '', up: 1, down: 1, parents: 0, children: 0, has_line: false }],
      statements: [stmt({})], statements_n: 14,
    });
    let v = mount('/corpus/names/Da%C5%9Baratha');
    expect(await screen.findByRole('heading', { name: 'In the indexes' })).toBeTruthy();
    const lines = screen.getByRole('list', { name: 'Lines of descent' });
    expect(within(lines).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/corpus/genealogies/pui/13']);
    const said = screen.getByRole('group', { name: 'What the indexes state' });
    expect(within(said).getByRole('heading', { name: 'Family' })).toBeTruthy();
    expect(within(said).getByRole('link', { name: 'Aja (IV)' }).getAttribute('href')).toBe('/corpus/names/Aja');
    expect(said.textContent).toContain('Purāṇa Index, the entry Daśaratha (II)');
    expect(screen.getByText(/and 13 more statements/)).toBeTruthy();
    v.unmount();
    sb.byFn.corpus_reader_index_of_name = MISSING('corpus_reader_index_of_name');
    v = mount('/corpus/names/Da%C5%9Baratha');
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_index_of_name')).toBe(true));
    expect(screen.queryByRole('heading', { name: 'In the indexes' })).toBeNull();
  });

  it('the tab and the menu', () => {
    expect(CORPUS_LINKS.map((l) => l.href)).toContain('/corpus/genealogies');
    const tab = (path: string) => {
      const v = render(<MemoryRouter initialEntries={[path]}><CorpusNav /></MemoryRouter>);
      const cur = v.container.querySelector('[aria-current="page"]')?.textContent?.trim();
      v.unmount();
      return cur;
    };
    expect(tab('/corpus/genealogies')).toBe('Genealogies');
    expect(tab('/corpus/genealogies/pui/13')).toBe('Genealogies');
    expect(tab('/corpus/markandeya_purana')).toBe('Library');
    expect(tab('/corpus/names/Aja')).toBe('Names');
  });
});
