/**
 * NAME_LINKS_SITE_2026_10_23 - "Named together with" on a name's page (/corpus/names/:canonical): the names a passage
 * names beside this one, from corpus_reader_name_links (docs/cloud/C20 in the automaton repo), most passages first,
 * each a link to its own page and to the first passage that names both. Until C20 is applied (the function missing),
 * or when no other name is named with it, the section is not shown and the page is as before.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import CorpusNames from '@/pages/corpus/CorpusNames';
import { loadNameLinks } from '@/lib/corpusLibrary';

const SB = '2015_405693_Shatpath-Brahmanam';
const HEAD = { canonical: 'Janaka', kind: 'person', notes: null, variants: null, mentions: 47, texts: 4, total: 1 };
const HIT = { doc_code: SB, title: 'Śatapatha Brāhmaṇa', page_no: 95, idx: 5, verse_ref: null, ord: 120, surface: 'Janaka', snippet: 'Janaka of Videha.', total: 1 };
const LINKS = [
  { canonical: 'Yājñavalkya', kind: 'person', passages: 33, texts: 1, doc_code: SB, title: 'Śatapatha Brāhmaṇa', page_no: 95, idx: 3, ord: 118 },
  { canonical: 'Videha', kind: 'place', passages: 29, texts: 2, doc_code: SB, title: 'Śatapatha Brāhmaṇa', page_no: 95, idx: 5, ord: 120 },
];

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/names/:canonical" element={<CorpusNames />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {
    corpus_reader_names: { data: [HEAD], error: null },
    corpus_reader_name: { data: [HIT], error: null },
  };
  sb.calls = [];
});

describe('Named together with', () => {
  it('lists the names named beside this one, each to its page and to the first passage of both', async () => {
    sb.byFn.corpus_reader_name_links = { data: LINKS, error: null };
    mount('/corpus/names/Janaka');
    const h = await screen.findByRole('heading', { name: /Named together with/ });
    const section = h.closest('section') as HTMLElement;
    const yaj = within(section).getByRole('link', { name: 'Yājñavalkya' });
    expect(yaj.getAttribute('href')).toBe('/corpus/names/Y%C4%81j%C3%B1avalkya');
    expect(within(section).getByText(/33 passages/)).toBeTruthy();
    expect(within(section).getByText(/29 passages · 2 texts/)).toBeTruthy();
    const first = within(section).getAllByRole('link', { name: 'first together' });
    expect(first.map((a) => a.getAttribute('href'))).toEqual([`/corpus/${SB}?p=3#p95-3`, `/corpus/${SB}?p=3#p95-5`]);
    expect(within(section).getByText(/does not say how they are related/)).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_name_links')?.args).toEqual({ p_canonical: 'Janaka', k: 20 });
    expect(await screen.findByText('Janaka of Videha.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Read it in the text' })).toBeTruthy();
  });

  it('is not shown before C20 is applied, and the page is as before', async () => {
    sb.byFn.corpus_reader_name_links = {
      data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_name_links(k, p_canonical) in the schema cache' },
    };
    mount('/corpus/names/Janaka');
    expect(await screen.findByText('Janaka of Videha.')).toBeTruthy();
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_name_links')).toBe(true));
    expect(screen.queryByRole('heading', { name: /Named together with/ })).toBeNull();
    expect(screen.queryByText(/could not find the function/i)).toBeNull();
  });

  it('is not shown for a name never named with another', async () => {
    mount('/corpus/names/Janaka');
    expect(await screen.findByText('Janaka of Videha.')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: /Named together with/ })).toBeNull();
  });

  it('asks for at most 50', async () => {
    await loadNameLinks('Janaka', 500);
    expect(sb.calls[sb.calls.length - 1]).toEqual({ fn: 'corpus_reader_name_links', args: { p_canonical: 'Janaka', k: 50 } });
  });
});
