/**
 * B2_SITE_2026_10_28 and X1C_SITE_2026_10_28 - the historian's view beside the genealogies, and a search in the
 * scholarly English.
 *
 * B2 (docs/cloud/C23): a step's chips carry the historian's verdict (Raychaudhuri, 1923: agrees, another relation, the
 * other way); a statement's evidence his view with the book's words and page; a strip over the line shows each step by
 * what it rests on and chooses one; "In our corpus" gathers our names on the line, how often our texts name the
 * person, the names named with it (not a kinship) and what the historians say of it; the credits name the work apart
 * from GRETIL's texts; the genealogies page lists the work; a name's page says what the historians say of it. Before
 * C23 none of it is drawn. X1c (docs/cloud/C24): corpus_reader_scholar_search, on /corpus as a third way and on
 * /corpus/scholarly with a choice of text; before C24 it says so quietly. Nothing is rendered as HTML.
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
  claimPage, lineCounts, stepChips, stepStrength, tieLabel, verdictText, viewClaims, type Claim, type Statement,
  type Step, type Tree,
} from '@/lib/indexSite';
import { SCHOLAR_SEARCH_OFF, searchScholar } from '@/lib/scholarSite';
import CorpusGenealogies from '@/pages/corpus/CorpusGenealogies';
import CorpusGenealogy from '@/pages/corpus/CorpusGenealogy';
import CorpusNames from '@/pages/corpus/CorpusNames';
import CorpusHome from '@/pages/corpus/CorpusHome';
import CorpusScholarly from '@/pages/corpus/CorpusScholarly';

const MISSING = (fn: string): RpcAnswer => ({
  data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn}(k, p_doc, q) in the schema cache` },
});
const one = (v: unknown): RpcAnswer => ({ data: [{ result: v }], error: null });

const C1 = 'phai1923:52:3';
const C4 = 'phai1923:61:4';
const claim = (extra: Partial<Claim>): Claim => ({
  key: C1, work: 'phai1923', pdf_page: 52, printed: '37', n: 3, subject: 'Dasaratha', relation: 'son_of', object: 'Aja',
  claim: 'Dasaratha was the son of Aja.', quote: 'Dasaratha, the son of Aja', quote_check: 'exact', stance: 'asserts',
  hedge: '', subject_canonical: 'Daśaratha', subject_how: 'spelling', object_canonical: 'Aja', object_how: 'exact',
  cites: [{ printed: 'Vi. IV. 4. 86', work: 'Viṣṇu Purāṇa', locus: 'IV. 4. 86', ours: 'vishnu_purana', note: '' }], ...extra,
});
const CLAIMS: Record<string, Claim> = {
  [C1]: claim({}),
  [C4]: claim({ key: C4, pdf_page: 61, printed: '45', n: 4, subject: 'Raghu', relation: 'contemporary_of', object: 'Aja',
    claim: 'Raghu lived in the time of Aja.', quote: 'Raghu ... in the <b>time</b> of Aja', quote_check: 'close',
    stance: 'reports', subject_canonical: 'Raghu', subject_how: 'exact', cites: [] }),
};

const person = (entry: number, head: string, extra: Record<string, unknown> = {}) => ({
  entry, head, sex: 'm', named_only: entry < 0, parents: 1, children: 1, up: 1, down: 1, canonical: null, spouses: [], ...extra,
});
const stmt = (extra: Partial<Statement>): Statement => ({
  key: 'k1', source: 'pui', stated_in: 'Daśaratha (II)', entry_id: 13, relation: 'son_of', subject: 'Daśaratha (II)',
  object: 'Aja (IV)', words: 'son of Aja', refs: ['Vi. IV. 4. 86'], n: 1, subject_entry: 13, object_entry: 11,
  subject_canonical: 'Daśaratha', object_canonical: 'Aja', ours: 'not tied', passages: 0, texts: 0, places: [],
  cited: 'no citation', cites: [], best_text: '', best_ref: '', together: {}, ...extra,
});
const step = (parent: number, child: number, extra: Partial<Step> = {}): Step => ({
  parent, child, joined: 'rule', both_entries: true, cited: 'no citation', ours: 'not tied',
  epic: { mbh: [0, ''], hv: [0, ''], ram: [0, ''] }, items: [stmt({})], ...extra,
});
const TREE: Tree = {
  source: 'pui', entry: 13, me: 2, title: 'Purana Index (V. R. R. Dikshitar, 1951-55)', person: person(13, 'Daśaratha (II)'),
  line: [
    { ...person(10, 'Raghu (I)', { canonical: 'Raghu' }), generation: -2, siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(11, 'Aja (IV)', { canonical: 'Aja' }), generation: -1, siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(13, 'Daśaratha (II)', { canonical: 'Daśaratha' }), generation: 0, siblings: [], siblings_n: 0, other_parents: [] },
    { ...person(14, 'Rāma (II)'), generation: 1, siblings: [], siblings_n: 0, other_parents: [] },
  ],
  steps: [
    step(10, 11, { scholar: 'differs', items: [stmt({ key: 'k0', subject: 'Aja (IV)', object: 'Raghu (I)', words: 'son of Raghu',
      subject_canonical: 'Aja', object_canonical: 'Raghu',
      scholars: [{ work: 'phai1923', verdict: 'differs', note: 'p. 45 (contemporary_of): Raghu lived in the time of Aja.', claims: [C4] }] })] }),
    step(11, 13, { scholar: 'agrees', items: [stmt({ scholars: [{ work: 'phai1923', verdict: 'agrees', note: 'p. 37: Dasaratha was the son of Aja.', claims: [C1] }] })] }),
    step(13, 14, { cited: 'one', items: [stmt({ key: 'k2', subject: 'Rāma (II)', object: 'Daśaratha', cited: 'one' })] }),
  ],
  down: [],
  verses: {},
  texts: { vi: { title: 'Viṣṇupurāṇa', edition: 'Bombay, 1910', rights: 'CC BY-NC-SA 4.0', show: true } },
  works: { phai1923: { title: 'Hemchandra Raychaudhuri, Political History of Ancient India', edition: 'University of Calcutta, 1923', rights: 'public domain', show: true } },
  claims: CLAIMS,
};
/** The same tree as C21 alone sends it: no scholars, no works, no claims. */
const TREE_C21: Tree = {
  ...TREE, works: undefined, claims: undefined,
  steps: TREE.steps.map((s) => ({ ...s, scholar: undefined, items: s.items.map((i) => ({ ...i, scholars: undefined })) })),
};

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus" element={<CorpusHome />} />
            <Route path="/corpus/scholarly" element={<CorpusScholarly />} />
            <Route path="/corpus/genealogies" element={<CorpusGenealogies />} />
            <Route path="/corpus/genealogies/:source/:entry" element={<CorpusGenealogy />} />
            <Route path="/corpus/names/:canonical" element={<CorpusNames />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe('the historian\'s view, in words', () => {
  it('a chip a verdict, after the evidence of the texts; nothing without one', () => {
    expect(stepChips(TREE.steps[1]).map((c) => c.label)).toEqual(['Raychaudhuri agrees']);
    expect(stepChips(TREE.steps[0]).map((c) => [c.label, c.tone])).toEqual([['Raychaudhuri: another relation', 'half']]);
    expect(stepChips({ cited: 'both', epic: {}, ours: '', joined: 'rule', scholar: 'reversed' }).map((c) => c.label))
      .toEqual(['verse ✓', 'Raychaudhuri: the other way']);
    expect(stepChips(TREE_C21.steps[1]).map((c) => c.label)).toEqual(['the index alone']);
    expect(stepChips({ cited: '', epic: {}, ours: '', joined: 'rule', scholar: 'odd' }).map((c) => c.label)).toEqual(['the index alone']);
  });

  it('a step\'s strength is the best of what it rests on; how the persons were told apart does not count', () => {
    expect(stepStrength(TREE.steps[1])).toBe('ok');
    expect(stepStrength(TREE.steps[0])).toBe('half');
    expect(stepStrength(TREE.steps[2])).toBe('half');
    expect(stepStrength({ cited: '', epic: { mbh: [2, '1.1.1'] }, ours: '', joined: 'verse' })).toBe('ep');
    expect(stepStrength({ cited: '', epic: {}, ours: '', joined: 'named' })).toBe('no');
    expect(lineCounts(TREE.steps)).toEqual({ verse: 0, epic: 0, ours: 0, agrees: 1, otherwise: 1 });
  });

  it('the verdicts, the ties, the pages and the claims of a view', () => {
    expect(verdictText({ work: 'phai1923', verdict: 'agrees' })).toBe('Raychaudhuri (1923) states it too');
    expect(verdictText({ work: 'phai1923', verdict: 'differs' })).toBe('Raychaudhuri (1923) states another relation of the two');
    expect(verdictText({ work: 'phai1923', verdict: 'reversed' })).toBe('Raychaudhuri (1923) states it the other way round');
    expect(verdictText({ work: 'x', verdict: 'agrees' }, { x: { title: 'A Book' } })).toBe('A Book states it too');
    expect([tieLabel('exact'), tieLabel('numbered exact'), tieLabel('spelling'), tieLabel('plural loose'), tieLabel('')])
      .toEqual(['certain', 'certain', 'probable', 'probable', '']);
    expect(claimPage({ printed: 'ii', pdf_page: 15 })).toBe('p. ii');
    expect(claimPage({ printed: null, pdf_page: 15 })).toBe('scan p. 15');
    const views = [{ work: 'phai1923', verdict: 'agrees', note: '', claims: [C1, 'phai1923:9:9', C1] }];
    expect(viewClaims(views, CLAIMS).map((c) => c.key)).toEqual([C1]);
    expect(viewClaims(views, undefined)).toEqual([]);
  });
});

describe('/corpus/genealogies/:source/:entry with the historian', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('the chips, the counts, the strip and the view with the book\'s words', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    mount('/corpus/genealogies/pui/13');
    expect(await screen.findByRole('heading', { level: 1, name: /Daśaratha \(II\)/ })).toBeTruthy();
    expect(screen.getByText(/1 the historian states too · 1 he states otherwise/)).toBeTruthy();
    const line = screen.getByRole('list', { name: 'The line' });
    expect(within(line).getByText('Raychaudhuri agrees')).toBeTruthy();
    // the step into the person is chosen first: Aja (IV) -> Dasaratha (II)
    const ev = screen.getByRole('heading', { name: 'What the step rests on' }).parentElement as HTMLElement;
    const view = within(ev).getByRole('group', { name: "The historian's view" });
    expect(within(view).getByText('Raychaudhuri (1923) states it too')).toBeTruthy();
    expect(view.textContent).toContain('“Dasaratha, the son of Aja”');
    expect(view.textContent).toContain('Raychaudhuri, p. 37 · the words as on the page');
    expect(within(view).getByRole('link', { name: 'Dasaratha as Daśaratha' }).getAttribute('href')).toBe('/corpus/names/Da%C5%9Baratha');
    expect(view.textContent).toContain('(probable)');
    expect(within(view).getByRole('link', { name: /ours:/ }).getAttribute('href')).toBe('/corpus/vishnu_purana');
    // the strip: one button a step, the chosen one pressed; another chosen from it
    const strip = screen.getByRole('list', { name: 'The steps at a glance' });
    const bs = within(strip).getAllByRole('button');
    expect(bs).toHaveLength(3);
    expect(bs.map((b) => b.getAttribute('aria-pressed'))).toEqual(['false', 'true', 'false']);
    expect(bs[1].getAttribute('aria-label')).toBe('Step 2, Aja (IV) to Daśaratha (II): a verse with both names, one of our passages, or the historian');
    expect(bs[1].className).toContain('bg-emerald-500/70');
    fireEvent.click(bs[0]);
    expect(within(ev).getByText('Raychaudhuri (1923) states another relation of the two')).toBeTruthy();
    expect(ev.textContent).toContain('Raghu ... in the <b>time</b> of Aja');            // the book's words are text, never HTML
    expect(ev.querySelector('blockquote b')).toBeNull();
    expect(ev.textContent).toContain('Raychaudhuri reports it from his sources');
    expect(within(strip).getAllByRole('button')[0].getAttribute('aria-pressed')).toBe('true');
  });

  it('the credits name the historian apart from GRETIL\'s texts', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    mount('/corpus/genealogies/pui/13');
    await screen.findByRole('heading', { level: 1, name: /Daśaratha \(II\)/ });
    const credits = document.querySelector('footer[aria-label="Credits"]') as HTMLElement;
    const gretil = within(credits).getByText(/^The Sanskrit: GRETIL/);
    expect(gretil.textContent).not.toContain('Raychaudhuri');
    const hist = within(credits).getByText(/^The historians:/);
    expect(hist.textContent).toContain('Political History of Ancient India, University of Calcutta, 1923 (public domain)');
    expect(hist.textContent).toContain('Only works in the public domain are shown');
  });

  it('in our corpus: our names on the line, how often our texts name the person, the names named with it, the historian', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE);
    sb.byFn.corpus_reader_names = { data: [{ canonical: 'Daśaratha', kind: 'person', notes: null, variants: null, mentions: 120, texts: 9, total: 1 }], error: null };
    sb.byFn.corpus_reader_name_links = { data: [{ canonical: 'Rāma', kind: 'person', passages: 41, texts: 5, doc_code: 'ramayana', title: 'Rāmāyaṇa', page_no: 1, idx: 1, ord: 1 }], error: null };
    sb.byFn.corpus_reader_index_of_name = one({ persons: [], statements: [], statements_n: 0, claims: [CLAIMS[C1]], claims_n: 7 });
    mount('/corpus/genealogies/pui/13');
    const sec = (await screen.findByRole('heading', { name: 'In our corpus' })).parentElement as HTMLElement;
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_names')?.args).toEqual({ q: 'Daśaratha', p_kind: null, k: 1, p_offset: 0, p_exact: true });
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_name_links')?.args).toEqual({ p_canonical: 'Daśaratha', k: 20 });
    expect(within(sec).getByText(/On this line, named in our texts:/).textContent).toBe('On this line, named in our texts: Raghu · Aja · Daśaratha');
    expect(await within(sec).findByText(/in 120 passages of 9 texts/)).toBeTruthy();
    const tog = await within(sec).findByRole('list', { name: 'Named together with Daśaratha' });
    expect(within(tog).getByRole('link').getAttribute('href')).toBe('/corpus/names/R%C4%81ma');
    expect(sec.textContent).toContain('being named together is not a kinship');
    expect(await within(sec).findByRole('list', { name: 'What the historians say of Daśaratha' })).toBeTruthy();
    expect(within(sec).getByRole('link', { name: 'All 7 on the page of Daśaratha' }).getAttribute('href')).toBe('/corpus/names/Da%C5%9Baratha');
  });

  it('before C23: no chip, no view, no historian in the credits; the strip still shows what the texts say', async () => {
    sb.byFn.corpus_reader_index_tree = one(TREE_C21);
    mount('/corpus/genealogies/pui/13');
    await screen.findByRole('heading', { level: 1, name: /Daśaratha \(II\)/ });
    expect(screen.queryByText(/Raychaudhuri/)).toBeNull();
    expect(screen.queryByText(/the historian states too/)).toBeNull();
    expect(screen.queryByRole('group', { name: "The historian's view" })).toBeNull();
    expect(screen.queryByText(/^The historians:/)).toBeNull();
    const strip = screen.getByRole('list', { name: 'The steps at a glance' });
    expect(within(strip).getAllByRole('button').map((b) => b.className.includes('bg-muted'))).toEqual([true, true, false]);
  });
});

describe('the genealogies page and a name\'s page', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('the genealogies page lists the historian\'s work with its claims, and credits it', async () => {
    sb.byFn.corpus_reader_index_overview = one({
      sources: [{ source: 'pui', title: 'Purana Index', edition: 'Madras, 1951-55', rights: 'CC BY-NC-SA 3.0', persons: 10147, tied: 2625, steps: 7779, statements: 12130, lines: 30 }],
      texts: [], run: null,
      works: [{ code: 'phai1923', title: 'Hemchandra Raychaudhuri, Political History of Ancient India', edition: 'University of Calcutta, 1923', rights: 'public domain', show: true, claims: 1904 }],
    });
    mount('/corpus/genealogies');
    expect(await screen.findByRole('heading', { name: "The historians' view" })).toBeTruthy();
    const ws = screen.getByRole('list', { name: 'The historians' });
    expect(ws.textContent).toContain('1,904 claims read from the book');
    expect(screen.getByText(/^The historians:/)).toBeTruthy();
    expect(screen.getAllByRole('link', { name: 'The licence' })).toHaveLength(1);
  });

  it('before C23 the genealogies page is as it was', async () => {
    sb.byFn.corpus_reader_index_overview = one({
      sources: [{ source: 'pui', title: 'Purana Index', edition: 'Madras, 1951-55', rights: 'CC BY-NC-SA 3.0', persons: 10147, tied: 2625, steps: 7779, statements: 12130, lines: 30 }],
      texts: [], run: null,
    });
    mount('/corpus/genealogies');
    expect(await screen.findByText(/10,147 persons in a line/)).toBeTruthy();
    expect(screen.queryByRole('heading', { name: "The historians' view" })).toBeNull();
  });

  it('a name\'s page says what the historians say of it, even with no person in the indexes', async () => {
    sb.byFn.corpus_reader_index_of_name = one({ persons: [], statements: [], statements_n: 0, claims: [CLAIMS[C1], CLAIMS[C4]], claims_n: 12 });
    mount('/corpus/names/Aja');
    expect(await screen.findByRole('heading', { name: 'What the historians say' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'In the indexes' })).toBeNull();
    const l = screen.getByRole('list', { name: 'What the historians say of Aja' });
    expect(within(l).getAllByRole('listitem')).toHaveLength(2);
    expect(l.textContent).toContain('Dasaratha was the son of Aja.');
    expect(within(l).getAllByText('Aja').length).toBeGreaterThan(0);                   // this page's own name, not a link
    expect(within(l).queryByRole('link', { name: 'Aja' })).toBeNull();
    expect(screen.getByText(/and 10 more claims of the book/)).toBeTruthy();
  });
});

describe('a search in the scholarly English (X1c)', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  const HIT = { doc_code: 'markandeya_purana__w_gretil', title: 'Mārkaṇḍeya Purāṇa', page_no: 626, idx: 1, verse_ref: '81.1', ord: 1201, score: 0.6,
    snippet: 'Sāvarṇi, the son of the Sun, is called the eighth [[*Manu*]]. //' };

  it('asks C24 with the words, at most 50, and takes the English\'s own marks out', async () => {
    sb.byFn.corpus_reader_scholar_search = { data: [HIT], error: null };
    const r = await searchScholar('  eighth   Manu ', 'markandeya_purana__w_gretil', 99);
    expect(sb.calls[0]).toEqual({ fn: 'corpus_reader_scholar_search', args: { q: 'eighth Manu', k: 50, p_doc: 'markandeya_purana__w_gretil' } });
    expect(r.ok && r.rows[0].snippet).toBe('Sāvarṇi, the son of the Sun, is called the eighth [[Manu]].');
    const short = await searchScholar('a');
    expect([short.ok, sb.calls.length]).toEqual([false, 1]);
    sb.byFn.corpus_reader_scholar_search = MISSING('corpus_reader_scholar_search');
    const m = await searchScholar('Manu');
    expect([m.ok, m.missing, m.error]).toEqual([false, true, SCHOLAR_SEARCH_OFF]);
  });

  it('/corpus: the third way finds the words in the scholarly English, with both ways to the verse', async () => {
    sb.byFn.corpus_reader_docs = { data: [{ doc_code: 'markandeya_purana__w_gretil', title: 'Mārkaṇḍeya Purāṇa', category: 'purana', passages: 5240, english: 5000, hindi: 5000, vectors: 0, stories: 0, published: true, synced_at: '2026-10-28T01:00:00Z' }], error: null };
    sb.byFn.corpus_reader_scholar_search = { data: [HIT], error: null };
    mount('/corpus');
    fireEvent.click(await screen.findByRole('button', { name: 'In the scholarly English' }));
    expect(screen.getByRole('button', { name: 'In the scholarly English' }).getAttribute('aria-pressed')).toBe('true');
    fireEvent.change(screen.getByLabelText('Search the working corpus'), { target: { value: 'Manu' } });
    fireEvent.click(screen.getByRole('button', { name: /^Search$/ }));
    expect(await screen.findByText('Manu', { selector: 'mark' })).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_scholar_search')?.args).toEqual({ q: 'Manu', k: 30, p_doc: null });
    expect(screen.getByRole('link', { name: 'Beside the Sanskrit' }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil?p=25#p626-1');
    expect(screen.getByRole('link', { name: 'The text as prose' }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil/prose');
  });

  it('/corpus/scholarly: a search over one text; before C24 it says so quietly', async () => {
    sb.byFn.corpus_reader_scholar_docs = { data: [
      { doc_code: 'markandeya_purana__w_gretil', title: 'Mārkaṇḍeya Purāṇa', category: null, passages: 5240, verses: 1408, flagged: 0, accepted: 0, fidelity: 4.6, first_page: 626, first_idx: 2, first_ord: 1202, last_made: null },
      { doc_code: 'MBh01', title: 'Mahābhārata, Ādiparvan', category: null, passages: 900, verses: 24, flagged: 0, accepted: 0, fidelity: null, first_page: 1, first_idx: 1, first_ord: 1, last_made: null },
    ], error: null };
    sb.byFn.corpus_reader_scholar_search = MISSING('corpus_reader_scholar_search');
    mount('/corpus/scholarly');
    const box = await screen.findByRole('textbox', { name: 'Search the scholarly English' });
    fireEvent.change(screen.getByRole('combobox', { name: 'In which text' }), { target: { value: 'MBh01' } });
    fireEvent.change(box, { target: { value: 'Pāṇḍu' } });
    fireEvent.click(screen.getByRole('button', { name: /^Search$/ }));
    expect(await screen.findByText(SCHOLAR_SEARCH_OFF)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_scholar_search')?.args).toEqual({ q: 'Pāṇḍu', k: 30, p_doc: 'MBh01' });
    sb.byFn.corpus_reader_scholar_search = { data: [], error: null };
    fireEvent.click(screen.getByRole('button', { name: /^Search$/ }));
    await waitFor(() => expect(screen.getByText(/No verse of the scholarly English has these words/)).toBeTruthy());
  });
});
