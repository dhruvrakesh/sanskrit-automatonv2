/**
 * GENEALOGY_HEAL_2026_11_10 - the genealogy pages in plain words, and the epithets (docs/cloud/C26 in the automaton
 * repo). Asked on 10 Nov: "such a genealogy front end does not make sense for anybody ... we cant even get the
 * genealogy of Kaunteya (Arjun) right". An epithet ("Kaunteya, the son of Kuntī, = Arjuna") sends the reader to the
 * person it names; a plural lists its persons; a found epithet links to its person; "How to read this page" says
 * what each mark means; Sørensen's pages say why no cited verse is shown and count the epics' verses instead; a step
 * joined by the names both entries give says so. Nothing is rendered as HTML.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as { fn?: string; args?: Record<string, unknown> }[] }));
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
  epithetHow, epithetKind, GUIDE, JOIN_SHARED, SOURCE_NOTE, stepChips, stepStrength, type Step, type Tree,
} from '@/lib/indexSite';
import CorpusGenealogies from '@/pages/corpus/CorpusGenealogies';
import CorpusGenealogy from '@/pages/corpus/CorpusGenealogy';

const one = (v: unknown): RpcAnswer => ({ data: [{ result: v }], error: null });
const person = (entry: number, head: string, extra: Record<string, unknown> = {}) => ({
  entry, head, sex: 'm', named_only: false, parents: 1, children: 1, up: 1, down: 1, canonical: null, spouses: [], ...extra,
});
const step = (parent: number, child: number, extra: Partial<Step> = {}): Step => ({
  parent, child, joined: 'rule', both_entries: false, cited: '', ours: '', epic: { mbh: [7, '1.114.1'], hv: [0, ''], ram: [0, ''] },
  items: [], ...extra,
});
const ARJUNA = { entry: 4635, head: 'Arjuna[2]', how: 'the only entry of that name with a line' };

function kaunteya(extra: Record<string, unknown>): Tree {
  return {
    source: 'inm', entry: 9364, me: 1, title: 'An Index to the Names in the Mahabharata (S. Soerensen, 1904)',
    person: person(9364, 'Kaunteya[1]', extra),
    line: [
      { ...person(10027, 'Kuntī', { sex: 'f' }), generation: -1, siblings: [], siblings_n: 0, other_parents: [] },
      { ...person(9364, 'Kaunteya[1]', extra), generation: 0, siblings: [], siblings_n: 0, other_parents: [] },
    ],
    steps: [step(10027, 9364)],
    down: [], verses: {}, texts: {},
  };
}

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/genealogies" element={<CorpusGenealogies />} />
            <Route path="/corpus/genealogies/:source/:entry" element={<CorpusGenealogy />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe('the marks, in words', () => {
  it('a step joined by the names both entries give says so, and is not counted as evidence', () => {
    const st = { cited: '', epic: {}, ours: '', joined: 'shared' };
    expect(stepChips(st).map((c) => c.label)).toEqual([JOIN_SHARED]);
    expect(stepStrength(st)).toBe('no');
    expect(stepStrength({ ...st, epic: { mbh: [2, '1.1.1'] } })).toBe('ep');
  });

  it('the kinds of epithet', () => {
    expect(epithetKind({})).toBe('');
    expect(epithetKind({ same_as: [ARJUNA] })).toBe('one');
    expect(epithetKind({ same_as: [ARJUNA, { entry: 1, head: 'Bhīmasena[3]', how: 'the singular entries of this name' }] })).toBe('group');
    const nt = 'several entries of that name, not told apart';
    expect(epithetKind({ same_as: [{ entry: 1, head: 'Rāma[1]', how: nt }, { entry: 2, head: 'Rāma[2]', how: nt }] })).toBe('unsure');
    expect(epithetHow(ARJUNA.how)).toBe('the only entry of that name with parents or children');
  });

  it('the guide names every mark, and the index notes say why', () => {
    const terms = GUIDE.map((g) => g.term);
    expect(terms).toContain('The coloured strip');
    expect(terms).toContain('Two fathers');
    expect(terms).toContain('Epithets');
    expect(GUIDE.find((g) => g.term === 'Two fathers')?.text).toMatch(/Arjuna: Pāṇḍu and Indra/);
    expect(SOURCE_NOTE.inm).toMatch(/Calcutta edition/);
  });
});

describe('a person page', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('Kaunteya¹ sends the reader to Arjuna', async () => {
    sb.byFn.corpus_reader_index_tree = one(kaunteya({ same_as: [ARJUNA], gloss: 'the son of Kuntī' }));
    mount('/corpus/genealogies/inm/9364');
    const note = await screen.findByRole('note', { name: 'An epithet' });
    expect(note.textContent).toMatch(/Kaunteya\[1\] \(“the son of Kuntī”\) is another name for Arjuna\[2\], not a person of its own/);
    const a = screen.getAllByRole('link', { name: 'Arjuna[2]' })[0];
    expect(a.getAttribute('href')).toBe('/corpus/genealogies/inm/4635');
    expect(screen.getByText(/1 of 1 steps named together in the epics’ verses|1 of 1 steps named together in the epics' verses/)).toBeTruthy();
    expect(screen.getByText(/Calcutta edition of the Mahābhārata/)).toBeTruthy();
    const guide = screen.getByText('How to read this page');
    fireEvent.click(guide);
    expect(screen.getByText('Two fathers')).toBeTruthy();
  });

  it('the plural lists its persons; a person without an epithet has no note', async () => {
    const xs = [ARJUNA, { entry: 1, head: 'Bhīmasena[3]', how: 'the singular entries of this name' },
      { entry: 2, head: 'Karṇa[1]', how: 'the singular entries of this name' }, { entry: 3, head: 'Yudhiṣṭhira', how: 'the singular entries of this name' }];
    sb.byFn.corpus_reader_index_tree = one(kaunteya({ same_as: xs, gloss: 'the sons of Kuntī' }));
    const v = mount('/corpus/genealogies/inm/9368');
    const note = await screen.findByRole('note', { name: 'An epithet' });
    expect(note.textContent).toMatch(/names 4 persons: Arjuna\[2\], Bhīmasena\[3\], Karṇa\[1\] and Yudhiṣṭhira/);
    v.unmount();
    sb.byFn.corpus_reader_index_tree = one(kaunteya({}));
    mount('/corpus/genealogies/inm/9364');
    await screen.findByText('How to read this page');
    expect(screen.queryByRole('note', { name: 'An epithet' })).toBeNull();
  });
});

describe('the genealogies page', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; });

  it('a found epithet links to the person it names', async () => {
    sb.byFn.corpus_reader_index_overview = one({ sources: [{ source: 'inm', title: 'Soerensen', edition: '', rights: '', persons: 1, tied: 0, steps: 1, statements: 1, lines: 0 }], texts: [], run: null });
    sb.byFn.corpus_reader_index_find = { data: [
      { source: 'inm', entry: 7186, head: 'Dhanañjaya[1]', sex: '', up: 1, down: 1, canonical: null, exact: true, same_as: [ARJUNA], gloss: '', has_line: false },
    ], error: null };
    mount('/corpus/genealogies?q=dhananjaya');
    const hit = await screen.findByRole('link', { name: 'Dhanañjaya[1]' });
    expect(hit.getAttribute('href')).toBe('/corpus/genealogies/inm/7186');
    expect(screen.getByRole('link', { name: 'Arjuna[2]' }).getAttribute('href')).toBe('/corpus/genealogies/inm/4635');
    expect(screen.getByText(/an epithet: open the person it names/)).toBeTruthy();
    expect(screen.getByText('How to read this page')).toBeTruthy();
    expect(screen.getByText(/The longest fathers’ lines|The longest fathers' lines/)).toBeTruthy();
  });
});
