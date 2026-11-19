/**
 * VAMSA_FINDINGS_SITE_2026_11_19 - our findings on the vamsa page: the count on a dynasty, the findings above its
 * generations when opened, each source with its words on hover and its link (the generation, the verse's line,
 * Dikshitar's person), Raychaudhuri's claim and page, B. C. Law's page only; nothing new until C31 is pasted.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({
  vamsas: [] as Record<string, unknown>[], findings: [] as Record<string, unknown>[],
  calls: [] as { fn?: string; args?: Record<string, unknown> }[], missing: false,
}));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>): Promise<RpcAnswer> => {
      sb.calls.push({ fn, args });
      if (fn === 'corpus_reader_index_vamsas') {
        const k = args?.p_key as string | null;
        const rows = sb.vamsas.filter((r) => k == null || r.key === k).map((r) => (k == null ? { ...r, rows: [] } : r));
        return Promise.resolve({ data: rows, error: null });
      }
      if (fn === 'corpus_reader_index_vamsa_findings') {
        if (sb.missing) return Promise.resolve({ data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_index_vamsa_findings without parameters in the schema cache' } });
        return Promise.resolve({ data: sb.findings, error: null });
      }
      return Promise.resolve({ data: [], error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import { dayOf, dynastyLineHref, findingCiteText, findingMade, FINDING_KIND, type VamsaFinding, type VamsaRow } from '@/lib/indexSite';
import CorpusVamsas from '@/pages/corpus/CorpusVamsas';

const SOLAR: VamsaRow = {
  key: 'solar', vamsa: 'surya', ord: 1, anchor: 'Ikṣvāku', father: 'Manu', title: 'the solar line (Aikṣvākas) from Ikṣvāku',
  works: ['ram1', 'bhp9'], counts: { agree: 1, most: 0, differ: 0, one: 0 }, aligned_at: '2026-11-17T23:34:37',
  names: ['Ikṣvāku'],
  rows: [{ gen: 0, status: 'agree', name: 'Ikṣvāku', cells: { ram1: { name: 'Ikṣvāku', ref: 'R 1,69.18', words: 'ikṣvākus tu manoḥ sutaḥ', line: 3 } } }],
};
const KURU: VamsaRow = {
  key: 'kuru', vamsa: 'candra', ord: 11, anchor: 'Kuru', father: 'Saṃvaraṇa', title: 'the Kurus from Kuru', works: ['hv'],
  counts: { agree: 0, most: 0, differ: 0, one: 1 }, aligned_at: '', names: ['Kuru'],
  rows: [{ gen: 0, status: 'one', name: 'Kuru', cells: { hv: { name: 'Kuru', ref: 'HV 23.107', line: 3 } } }],
};
const F1: VamsaFinding = {
  n: 1, kind: 'agreement',
  text: 'The seven texts agree that Ikṣvāku was a son of Manu, and the Index gives him the same father.',
  cites: [
    { t: 'gen', gen: 0, name: 'Ikṣvāku' },
    { t: 'index', person: 'pui:17973', head: 'Ikṣvāku', page: true },
    { t: 'verse', work: 'ram1', ref: 'R 1,69.18', gen: 0, name: 'Ikṣvāku', words: 'ikṣvākus tu manoḥ sutaḥ', line: 3 },
    { t: 'verse', work: 'vip4', ref: 'ViP 4,1.7', gen: 0, name: 'Ikṣvāku', words: 'manorikṣvāku' },
    { t: 'second', work: 'vip4', ref: 'ViP 4,2.18', name: 'Vikukṣi', other: 'Śaśāda', words: 'śaśādasaṃjñāmavāpa' },
    { t: 'law', page: '40' },
    { t: 'ray', key: 'phai1923:67:20', printed: '49', pdf_page: 67, claim: 'The royal family of Kosala is represented as being descended from a king named Ikṣvāku.' },
  ],
  model: 'claude-sonnet-5-5', prompt: 'vamsa-findings-v2', read_at: '2026-11-19T12:52:03', approved_at: '2026-11-19T13:08:03',
};

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/corpus/genealogies/vamsas']}>
          <Routes><Route path="/corpus/genealogies/vamsas" element={<CorpusVamsas />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}
const open = (title: string) => {
  const d = screen.getByText(title).closest('details') as HTMLDetailsElement;
  d.open = true;
  fireEvent(d, new Event('toggle'));
  return d;
};

beforeEach(() => {
  sb.vamsas = [SOLAR, KURU] as unknown as Record<string, unknown>[];
  sb.findings = [{ key: 'solar', vamsa: 'surya', ord: 1, title: SOLAR.title, findings: [F1] }];
  sb.calls = [];
  sb.missing = false;
});

describe('our findings on the vamsa page', () => {
  it('counts them on the dynasty, one read for all', async () => {
    mount();
    expect(await screen.findByText('1 finding')).toBeTruthy();
    expect(sb.calls.filter((c) => c.fn === 'corpus_reader_index_vamsa_findings').length).toBe(1);
    const kuru = screen.getByText('the Kurus from Kuru').closest('summary') as HTMLElement;
    expect(within(kuru).queryByText(/finding/)).toBeNull();
  });

  it('shows them above the generations, each source with its words and its link', async () => {
    mount();
    await screen.findByText('1 finding');
    open('the solar line (Aikṣvākas) from Ikṣvāku');
    const sec = await screen.findByRole('region', { name: 'Our findings on solar' });
    expect(within(sec).getByText('Our findings (1)')).toBeTruthy();
    expect(within(sec).getByText(F1.text)).toBeTruthy();
    expect(within(sec).getByText(FINDING_KIND.agreement.label).getAttribute('title')).toMatch(/say the same/);
    expect(within(sec).getByRole('link', { name: 'the founder' }).getAttribute('href')).toBe('#vamsa-solar-g0');
    const verse = within(sec).getByRole('link', { name: 'R 1,69.18' });
    expect(verse.getAttribute('href')).toBe(dynastyLineHref('ram1', 3));
    expect(verse.getAttribute('title')).toBe('Rāmāyaṇa, book 1, R 1,69.18: Ikṣvāku. ikṣvākus tu manoḥ sutaḥ');
    expect(within(sec).getByText('ViP 4,1.7').getAttribute('title')).toMatch(/manorikṣvāku$/);
    expect(within(sec).getByText('ViP 4,2.18 (second name)').getAttribute('title')).toMatch(/Vikukṣi is also called Śaśāda/);
    expect(within(sec).getByRole('link', { name: 'Purāṇa Index: Ikṣvāku' }).getAttribute('href')).toBe('/corpus/genealogies/pui/17973');
    expect(within(sec).getByText('Raychaudhuri, p. 49').getAttribute('title')).toMatch(/descended from a king named Ikṣvāku\.$/);
    const law = within(sec).getByText('B. C. Law, p. 40');
    expect(law.getAttribute('title')).toBe('B. C. Law, Ancient Indian Tribes (Lahore, 1926), p. 40. In copyright: read on the desk and never quoted here; the finding says it in our own words.');
    expect(within(sec).getByText(/Proposed by a model \(claude-sonnet-5-5\) on 19 Nov 2026, checked by machine, read against its verses and approved by a person on 19 Nov 2026\./)).toBeTruthy();
    expect(await screen.findByText('the founder', { selector: 'span' })).toBeTruthy();
    expect(document.getElementById('vamsa-solar-g0')).toBeTruthy();
  });

  it('Law by his page only, whatever else a source carries', () => {
    const t = findingCiteText({ t: 'law', page: '97', claim: 'his own words' } as unknown as VamsaFinding['cites'][number]);
    expect(t.label).toBe('B. C. Law, p. 97');
    expect(t.title).not.toMatch(/his own words/);
    expect(findingCiteText({ t: 'gen', gen: 13, name: 'Bhīmasena' })).toEqual({ label: 'generation 13', title: 'Bhīmasena: this generation in the list below' });
    expect(dayOf('2026-11-19T13:08:03')).toBe('19 Nov 2026');
    expect(dayOf('')).toBe('');
    expect(findingMade({ model: '', read_at: '', approved_at: '' })).toBe('Proposed by a model (Claude), checked by machine, read against its verses and approved by a person.');
  });

  it('nothing new until C31 is pasted, and the page works as before', async () => {
    sb.missing = true;
    mount();
    expect(await screen.findByText('the solar line (Aikṣvākas) from Ikṣvāku')).toBeTruthy();
    open('the solar line (Aikṣvākas) from Ikṣvāku');
    expect(await screen.findByText('the founder')).toBeTruthy();
    expect(screen.queryByRole('region', { name: /Our findings on/ })).toBeNull();
    expect(screen.queryByText(/^\d+ findings?$/)).toBeNull();
  });
});
