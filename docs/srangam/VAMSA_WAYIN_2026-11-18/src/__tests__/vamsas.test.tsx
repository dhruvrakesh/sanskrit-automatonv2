/**
 * VAMSA_WAYIN_2026_11_18 - the way in by vaṃśa: the Sūryavaṃśa and the Candravaṃśa across the texts (the list light, a
 * dynasty's generations when opened), each name linked to its text's line, Dikshitar and Raychaudhuri beside each
 * generation; the Dynasties page opens the line asked for (?work=&line=).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({
  vamsas: [] as Record<string, unknown>[], dyn: [] as Record<string, unknown>[],
  calls: [] as { fn?: string; args?: Record<string, unknown> }[], missing: false,
}));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>): Promise<RpcAnswer> => {
      sb.calls.push({ fn, args });
      if (fn === 'corpus_reader_index_vamsas') {
        if (sb.missing) return Promise.resolve({ data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_index_vamsas(p_key) in the schema cache' } });
        const k = args?.p_key as string | null;
        const rows = sb.vamsas.filter((r) => k == null || r.key === k).map((r) => (k == null ? { ...r, rows: [] } : r));
        return Promise.resolve({ data: rows, error: null });
      }
      if (fn === 'corpus_reader_index_dynasties') {
        return Promise.resolve({ data: sb.dyn.filter((r) => args?.p_work == null || r.work === args.p_work), error: null });
      }
      return Promise.resolve({ data: [], error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import { dynastyLineHref, foldPlain, VAMSA_ORDER, type DynastyRow, type VamsaRow } from '@/lib/indexSite';
import CorpusVamsas from '@/pages/corpus/CorpusVamsas';
import CorpusDynasties from '@/pages/corpus/CorpusDynasties';

const SOLAR: VamsaRow = {
  key: 'solar', vamsa: 'surya', ord: 1, anchor: 'Ikṣvāku', father: 'Manu', title: 'the solar line (Aikṣvākas) from Ikṣvāku',
  works: ['ram1', 'vip4'], counts: { agree: 1, most: 0, differ: 1, one: 0, share_agree: 0.5 }, aligned_at: '2026-11-17T23:34:37',
  names: ['Ikṣvāku', 'Kukṣi', 'Vikukṣi'],
  rows: [
    { gen: 0, status: 'agree', name: 'Ikṣvāku', cells: { ram1: { name: 'Ikṣvāku', ref: 'R 1,69.18', words: 'ikṣvākus tu manoḥ sutaḥ', line: 2 }, vip4: { name: 'Ikṣvāku' } },
      pui: { person: 'pui:123', head: 'Ikṣvāku (I)', index: 'agrees', page: true } },
    { gen: 1, status: 'differ', name: 'Kukṣi', cells: { ram1: { name: 'Kukṣi', ref: 'R 1,69.19', line: 2 }, vip4: { name: 'Vikukṣi', ref: 'ViP 4,2.12', line: 4 } },
      canonical: 'Vikukṣi', ray_name_n: 2, ray_n: 1,
      ray: [{ key: 'phai1923:40:2', work: 'phai1923', printed: '37', pdf_page: 40, claim: 'Vikukṣi was the son of Ikṣvāku.' }] },
  ],
};
const KURU: VamsaRow = {
  key: 'kuru', vamsa: 'candra', ord: 11, anchor: 'Kuru', father: 'Saṃvaraṇa', title: 'the Kurus from Kuru', works: ['hv'],
  counts: { agree: 0, most: 0, differ: 0, one: 1 }, aligned_at: '', names: ['Kuru', 'Yudhiṣṭhira'],
  rows: [{ gen: 0, status: 'one', name: 'Kuru', cells: { hv: { name: 'Kuru', ref: 'HV 23.107', line: 3 } } }],
};
const dyn = (work: string, n: number, extra: Partial<DynastyRow>): DynastyRow => ({
  key: `${work}:${n}`, work, n, title: work, text_code: '', label: '', length: 0, steps: [], counts: {}, source: 'S', ...extra,
});

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/genealogies/vamsas" element={<CorpusVamsas />} />
            <Route path="/corpus/genealogies/dynasties" element={<CorpusDynasties />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}
const asked = (fn: string, arg: string) => sb.calls.filter((c) => c.fn === fn).map((c) => c.args?.[arg]);
const open = (title: string) => {
  const d = screen.getByText(title).closest('details') as HTMLDetailsElement;
  d.open = true;
  fireEvent(d, new Event('toggle'));
  return d;
};

beforeEach(() => {
  sb.vamsas = [SOLAR, KURU] as unknown as Record<string, unknown>[];
  sb.dyn = [];
  sb.calls = [];
  sb.missing = false;
});

describe('the way in by vamsa', () => {
  it('lists the two vamsas, the list without generations', async () => {
    mount('/corpus/genealogies/vamsas');
    expect(await screen.findByRole('heading', { name: /Sūryavaṃśa, the solar line/ })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /Candravaṃśa, the lunar line/ })).toBeTruthy();
    expect(VAMSA_ORDER).toEqual(['surya', 'candra']);
    const solar = screen.getByRole('region', { name: /Sūryavaṃśa/ });
    expect(within(solar).getByText('the solar line (Aikṣvākas) from Ikṣvāku')).toBeTruthy();
    expect(within(solar).queryByText('the Kurus from Kuru')).toBeNull();
    expect(asked('corpus_reader_index_vamsas', 'p_key')).toEqual([null]);
    expect(screen.getByText(/2 generations: 1 as every text gives them, 0 as most do, 1 where the texts differ/)).toBeTruthy();
  });

  it('finds a king typed in plain letters', async () => {
    mount('/corpus/genealogies/vamsas');
    await screen.findByText('the solar line (Aikṣvākas) from Ikṣvāku');
    fireEvent.change(screen.getByPlaceholderText(/Find a king/), { target: { value: 'Yudhishthira' } });
    expect(screen.getByText('the Kurus from Kuru')).toBeTruthy();
    expect(screen.queryByText('the solar line (Aikṣvākas) from Ikṣvāku')).toBeNull();
    expect(screen.queryByRole('heading', { name: /Sūryavaṃśa, the solar line/ })).toBeNull();
    fireEvent.change(screen.getByPlaceholderText(/Find a king/), { target: { value: 'Vikukshi' } });
    expect(screen.getByText('found: Vikukṣi')).toBeTruthy();
    expect(foldPlain('Vikukshi')).toBe(foldPlain('Vikukṣi'));
  });

  it('opens a dynasty: each name to its line, Dikshitar and Raychaudhuri beside it', async () => {
    mount('/corpus/genealogies/vamsas');
    await screen.findByText('the solar line (Aikṣvākas) from Ikṣvāku');
    open('the solar line (Aikṣvākas) from Ikṣvāku');
    expect(await screen.findByText('the founder')).toBeTruthy();
    expect(asked('corpus_reader_index_vamsas', 'p_key')).toEqual([null, 'solar']);
    const ram = screen.getAllByRole('link').filter((a) => a.getAttribute('href') === dynastyLineHref('ram1', 2));
    expect(ram.length).toBe(2);
    expect(dynastyLineHref('vip4', 4)).toBe('/corpus/genealogies/dynasties?work=vip4&line=4');
    expect(screen.getByRole('link', { name: 'Ikṣvāku (I)' }).getAttribute('href')).toBe('/corpus/genealogies/pui/123');
    expect(screen.getByRole('link', { name: '2 claims on the name' }).getAttribute('href')).toBe(`/corpus/names/${encodeURIComponent('Vikukṣi')}`);
    expect(screen.getByText('Vikukṣi was the son of Ikṣvāku.')).toBeTruthy();
    expect(screen.getByText('(p. 37)')).toBeTruthy();
    expect(screen.getByText('the texts differ').getAttribute('title')).toMatch(/give different names/);
    const li = screen.getAllByText(/Rāmāyaṇa, book 1:/, { selector: 'span' })[0].closest('li') as HTMLElement;
    expect(li.getAttribute('title')).toBe('R 1,69.18: ikṣvākus tu manoḥ sutaḥ');
  });

  it('says so when C29 is not pasted yet', async () => {
    sb.missing = true;
    mount('/corpus/genealogies/vamsas');
    expect(await screen.findByText(/The vaṃśas are not switched on yet/)).toBeTruthy();
  });
});

describe('the Dynasties page opens the line asked for', () => {
  it('asks for the text named and opens its line', async () => {
    sb.dyn = [
      dyn('hv', 0, { counts: { persons: 561 } }),
      dyn('hv', 1, { length: 2, steps: [{ name: 'Pāṇḍu' }, { name: 'Yudhiṣṭhira', father: 'Pāṇḍu', ref: 'HV 24.22' }] }),
      dyn('hv', 3, { length: 2, steps: [{ name: 'Saṃvaraṇa' }, { name: 'Kuru', father: 'Saṃvaraṇa', ref: 'HV 23.107' }] }),
    ] as unknown as Record<string, unknown>[];
    mount('/corpus/genealogies/dynasties?work=hv&line=3');
    expect(await screen.findByText(/561 persons/)).toBeTruthy();
    expect(asked('corpus_reader_index_dynasties', 'p_work')).toEqual(['hv']);
    const three = screen.getByText(/Saṃvaraṇa to Kuru/).closest('details') as HTMLDetailsElement;
    const one = screen.getByText(/Pāṇḍu to Yudhiṣṭhira/).closest('details') as HTMLDetailsElement;
    expect(three.open).toBe(true);
    expect(one.open).toBe(false);
    expect(screen.getByRole('link', { name: /Begin from a vaṃśa/ }).getAttribute('href')).toBe('/corpus/genealogies/vamsas');
  });
});
