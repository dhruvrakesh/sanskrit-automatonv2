/**
 * READER_NAV_2026_10_08 - the published reader's contents and paging. The loaders are mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

const TEXT = {
  id: 'cd889e11', doc_code: 'AphorismsOfSandilya', title: 'Sandilya Bhakti Sutra', category: 'bhakti',
  source_note: null, translation_engine: null, passage_count: 120, published: true,
};
const mocks = vi.hoisted(() => ({ one: vi.fn(), passages: vi.fn(), keys: vi.fn() }));
vi.mock('@/lib/corpusTexts', () => ({
  loadTextByDocCode: mocks.one, loadPassages: mocks.passages, loadPassageKeys: mocks.keys,
}));
vi.mock('@/lib/corpusSearch', () => ({
  MIN_QUERY: 3, MAX_QUERY: 300, searchTexts: vi.fn(), readerHref: () => '/texts/x',
}));

import TextReader from '@/pages/texts/TextReader';

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.search + l.hash}</output>;
}

const KEYS = Array.from({ length: 120 }, (_, n) => ({ page_no: Math.floor(n / 5) + 7, idx: (n % 5) + 1 }));

beforeEach(() => {
  mocks.one.mockReset(); mocks.passages.mockReset(); mocks.keys.mockReset();
  try { window.localStorage.clear(); } catch { /* none */ }
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  Element.prototype.scrollIntoView = vi.fn();
  mocks.one.mockResolvedValue({ ok: true, row: TEXT, error: null });
  mocks.passages.mockResolvedValue({
    ok: true, total: 120, error: null,
    rows: [{ id: 'x1', page_no: 7, idx: 1, sanskrit: 'SKT', iast: 'iast', translation: 'One. //', verse_ref: '1', quality_score: 0.9 }],
  });
  mocks.keys.mockResolvedValue({ ok: true, rows: KEYS, total: 120, error: null });
});

describe('/texts/:docCode navigation', () => {
  it('fetches the next page ahead, reads the keys only for the contents, and goes to a scan page', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <HelmetProvider><QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/texts/AphorismsOfSandilya']}>
          <Where />
          <Routes><Route path="/texts/:docCode" element={<TextReader />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider></HelmetProvider>,
    );
    expect(await screen.findByText('One.')).toBeTruthy();
    await waitFor(() => expect(mocks.passages).toHaveBeenCalledWith('cd889e11', { offset: 50, limit: 50 }));
    expect(mocks.keys).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: /Contents/ }));
    const panel = await screen.findByRole('dialog');
    expect(await within(panel).findByText('scan pages 17–26')).toBeTruthy();
    expect(mocks.keys).toHaveBeenCalledWith('cd889e11', 120);
    fireEvent.change(within(panel).getByLabelText(/scan page/), { target: { value: '30' } });
    await act(async () => { fireEvent.click(within(panel).getByRole('button', { name: 'Go' })); });
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('?p=3'));
  });
});
