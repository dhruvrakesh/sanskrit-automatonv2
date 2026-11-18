/**
 * DYNASTIES_WORKS_2026_11_18 - the Dynasties page loads one work's lines at a time (so the desk may send all 17 works
 * it reads without a heavier page), lists the 17 works by title, and finds a name typed in plain letters.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({ rows: [] as Record<string, unknown>[], calls: [] as { fn?: string; args?: Record<string, unknown> }[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>): Promise<RpcAnswer> => {
      sb.calls.push({ fn, args });
      if (fn !== 'corpus_reader_index_dynasties') return Promise.resolve({ data: [], error: null });
      return Promise.resolve({ data: sb.rows.filter((r) => args?.p_work == null || r.work === args.p_work), error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import { foldPlain, WORK_ORDER, WORK_TITLE, type DynastyRow } from '@/lib/indexSite';
import CorpusDynasties from '@/pages/corpus/CorpusDynasties';

const row = (work: string, n: number, extra: Partial<DynastyRow>): DynastyRow => ({
  key: `${work}:${n}`, work, n, title: work, text_code: '', label: '', length: 0, steps: [], counts: {}, source: 'S', ...extra,
});
const ROWS: DynastyRow[] = [
  row('vip4', 0, { counts: { persons: 715, father: 493, name: 35, agrees: 493, differs: 33, new: 2, absent: 187 } }),
  row('vip4', 1, { length: 3, label: 'Aikṣvākas (after Ikṣvāku)', steps: [{ name: 'Manu' }, { name: 'Ikṣvāku', father: 'Manu', ref: 'ViP 4,2.11' }, { name: 'Vikukṣi', father: 'Ikṣvāku', ref: 'ViP 4,2.12' }] }),
  row('vip4', 2, { length: 2, steps: [{ name: 'Triśaṅku' }, { name: 'Hariścandra', father: 'Triśaṅku', ref: 'ViP 4,3.24' }] }),
  row('hv', 0, { counts: { persons: 561, father: 250, name: 27, agrees: 250, differs: 20, new: 4, absent: 284 } }),
  row('hv', 1, { length: 2, steps: [{ name: 'Pāṇḍu' }, { name: 'Yudhiṣṭhira', father: 'Pāṇḍu', ref: 'HV 24.22' }] }),
];

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/corpus/genealogies/dynasties']}>
          <Routes><Route path="/corpus/genealogies/dynasties" element={<CorpusDynasties />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => { sb.rows = ROWS as unknown as Record<string, unknown>[]; sb.calls = []; });

describe('the dynasties, one work at a time', () => {
  it('names a plain spelling as its IAST', () => {
    expect(foldPlain('Harishchandra')).toBe(foldPlain('Hariścandra'));
    expect(foldPlain('Shantanu')).toBe(foldPlain('Śaṃtanu'));
    expect(foldPlain('Yudhishthira')).toBe(foldPlain('Yudhiṣṭhira'));
    expect(foldPlain('Ikshvaku')).toBe(foldPlain('Ikṣvāku'));
    expect(foldPlain('Devavrata')).not.toBe(foldPlain('Devarāta'));
  });

  it('lists the 17 works by title, the three of before first', () => {
    expect(WORK_ORDER.length).toBe(17);
    expect(WORK_ORDER.slice(0, 3)).toEqual(['vip4', 'bhp9', 'bhp12']);
    for (const w of WORK_ORDER) expect(WORK_TITLE[w], w).toBeTruthy();
  });

  it('asks for the first work only, then for the work chosen', async () => {
    mount();
    expect(await screen.findByText(/715 persons/)).toBeTruthy();
    const asked = () => sb.calls.filter((c) => c.fn === 'corpus_reader_index_dynasties').map((c) => c.args?.p_work);
    expect(asked()).toEqual(['vip4']);
    fireEvent.click(screen.getByRole('button', { name: 'Harivaṃśa' }));
    expect(await screen.findByText(/561 persons/)).toBeTruthy();
    expect(asked()).toEqual(['vip4', 'hv']);
    expect(screen.queryByText(/715 persons/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Matsyapurāṇa' }));
    expect(await screen.findByText('No dynasty of this text has been sent from the desk yet.')).toBeTruthy();
  });

  it('finds a name typed in plain letters', async () => {
    mount();
    await screen.findByText(/715 persons/);
    fireEvent.change(screen.getByPlaceholderText(/Find a name in the lines/), { target: { value: 'Harishchandra' } });
    expect(screen.getByText(/Triśaṅku to Hariścandra/)).toBeTruthy();
    expect(screen.queryByText('Aikṣvākas (after Ikṣvāku)')).toBeNull();
    fireEvent.change(screen.getByPlaceholderText(/Find a name in the lines/), { target: { value: 'Ikshvaku' } });
    expect(screen.getByText('Aikṣvākas (after Ikṣvāku)')).toBeTruthy();
  });
});
