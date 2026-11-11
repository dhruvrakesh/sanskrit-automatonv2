/**
 * DYNASTIES_2026_11_11 - the dynasties as the Purāṇas trace them (docs/cloud/C28 in the automaton repo). The lines of a
 * text, the first opened, each step with its verse, its words, what the Purāṇa Index says and a link where the
 * genealogies have the person's page; the texts as buttons; a name found in the lines; the work's counts in words;
 * "not switched on yet" before C28, "nothing sent yet" before the desk's first send; the Genealogies page links here.
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

import { DYNASTIES, dynastyCountsText, dynastyPersonHref, INDEX_SAYS, type DynastyRow } from '@/lib/indexSite';
import CorpusDynasties from '@/pages/corpus/CorpusDynasties';
import CorpusGenealogies from '@/pages/corpus/CorpusGenealogies';

const SRC = 'sa_viSNupurANa.txt; GRETIL (gretil.sub.uni-goettingen.de), CC BY-NC-SA 4.0 (data entry: members of the Sansknet Project)';
const row = (work: string, n: number, extra: Partial<DynastyRow>): DynastyRow => ({
  key: `${work}:${n}`, work, n, title: work, text_code: 'vi', label: '', length: 0, steps: [], counts: {}, source: SRC, ...extra,
});
const ROWS: DynastyRow[] = [
  row('vip4', 0, { counts: { persons: 715, father: 493, name: 35, agrees: 493, differs: 33, new: 2, absent: 187, joined: 1 } }),
  row('vip4', 1, {
    length: 4, label: 'Aikṣvākas (after Ikṣvāku)', steps: [
      { name: 'Manu', person: 'pui:1' },
      { name: 'Ikṣvāku', father: 'Manu', ref: 'ViP 4,2.11', words: 'manorikṣvākuḥ putro jajñe', person: 'pui:2', index_head: 'Ikṣvāku', how: 'father', index: 'agrees', page: true },
      { name: 'Vikukṣi', father: 'Ikṣvāku', ref: 'ViP 4,2.12', words: 'vikukṣinimidaṇḍākhyāstrayaḥ putrā', person: 'pui:3', how: 'father', index: 'agrees', joined: 'index' },
      { name: 'Kakutstha', father: 'Vikukṣi', ref: 'ViP 4,2.20', words: 'kakutsthasaṃjñām', person: 'pui:4', how: 'name', index: 'differs' },
    ],
  }),
  row('vip4', 2, { length: 3, steps: [{ name: 'Yadu' }, { name: 'Sahasrajit', father: 'Yadu', ref: 'ViP 4,11.2', words: 'sahasrajit', index: 'absent' }, { name: 'Śatajit', father: 'Sahasrajit', ref: 'ViP 4,11.3', index: 'absent' }] }),
  row('bhp9', 0, { title: 'bhp9', text_code: 'bh', counts: { persons: 716, father: 481, name: 25, differs: 20, absent: 210 } }),
  row('bhp9', 1, { text_code: 'bh', length: 3, steps: [{ name: 'Marīci' }, { name: 'Kaśyapa', father: 'Marīci', ref: 'BhP 9.1.10', index: 'agrees' }, { name: 'Vivasvat', father: 'Kaśyapa', ref: 'BhP 9.1.10', index: 'agrees' }] }),
];

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/genealogies" element={<CorpusGenealogies />} />
            <Route path="/corpus/genealogies/dynasties" element={<CorpusDynasties />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => { sb.byFn = {}; sb.calls = []; });

describe('the dynasties, in words', () => {
  it('says what the index says of a step and links a person only where the genealogies have a page', () => {
    expect(Object.keys(INDEX_SAYS).sort()).toEqual(['absent', 'agrees', 'differs', 'new']);
    expect(dynastyPersonHref({ person: 'pui:2', page: true })).toBe('/corpus/genealogies/pui/2');
    expect(dynastyPersonHref({ person: 'pui:3' })).toBeNull();
    expect(dynastyCountsText(ROWS[0].counts)).toBe('715 persons; 528 found in the Purāṇa Index (493 with the same father); 33 with another father there; 187 not in it.');
    expect(DYNASTIES).toBe('/corpus/genealogies/dynasties');
  });
});

describe('the Dynasties page', () => {
  it('draws the first text\'s lines, the first opened, each step with its verse and the index\'s word', async () => {
    sb.byFn.corpus_reader_index_dynasties = { data: ROWS, error: null };
    mount('/corpus/genealogies/dynasties');
    expect(await screen.findByText(/715 persons; 528 found in the Purāṇa Index/)).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_index_dynasties')?.args).toEqual({ p_work: null });
    expect(screen.getByText('Aikṣvākas (after Ikṣvāku)')).toBeTruthy();
    const ik = screen.getByRole('link', { name: 'Ikṣvāku' });
    expect(ik.getAttribute('href')).toBe('/corpus/genealogies/pui/2');
    expect(screen.queryByRole('link', { name: 'Vikukṣi' })).toBeNull();
    expect(screen.getAllByText('index agrees').length).toBeGreaterThan(0);
    expect(screen.getByText('index differs')).toBeTruthy();
    expect(screen.getByText('joined by the index')).toBeTruthy();
    expect(screen.getByText('manorikṣvākuḥ putro jajñe')).toBeTruthy();
    expect(screen.getByText('ViP 4,2.11')).toBeTruthy();
    expect(screen.getByText(/CC BY-NC-SA 4.0/)).toBeTruthy();
  });

  it('switches texts and finds a name in the lines', async () => {
    sb.byFn.corpus_reader_index_dynasties = { data: ROWS, error: null };
    mount('/corpus/genealogies/dynasties');
    await screen.findByText(/715 persons/);
    fireEvent.change(screen.getByPlaceholderText(/Find a name in the lines/), { target: { value: 'sahasra' } });
    expect(screen.queryByText('Aikṣvākas (after Ikṣvāku)')).toBeNull();
    expect(screen.getByText(/Yadu to Śatajit/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Bhāgavatapurāṇa, book 9' }));
    expect(screen.getByText(/716 persons/)).toBeTruthy();
  });

  it('says so before C28 is pasted, and before anything is sent', async () => {
    sb.byFn.corpus_reader_index_dynasties = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_index_dynasties(p_work) in the schema cache' } };
    mount('/corpus/genealogies/dynasties');
    expect(await screen.findByText(/The dynasties are not switched on yet/)).toBeTruthy();
  });

  it('says that nothing has been sent yet', async () => {
    sb.byFn.corpus_reader_index_dynasties = { data: [], error: null };
    mount('/corpus/genealogies/dynasties');
    expect(await screen.findByText('No dynasty has been sent from the desk yet.')).toBeTruthy();
  });

  it('is linked from the Genealogies page', async () => {
    mount('/corpus/genealogies');
    const a = await screen.findByRole('link', { name: /The dynasties, as the Purāṇas trace them/ });
    expect(a.getAttribute('href')).toBe('/corpus/genealogies/dynasties');
  });
});
