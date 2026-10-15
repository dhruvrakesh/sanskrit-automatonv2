/**
 * READER_SOURCES_2026_10_14 (S2) - the reader names where a passage's Sanskrit comes from.
 * An e-text (MBh01, the BORI Critical Edition's own text) is not given an OCR confidence and is never
 * marked a hard-to-read scan; a scan names its reader (Tesseract, a vision model) beside its OCR
 * confidence; a passage whose engine is not recorded is shown as before. The corpus reader asks
 * public.corpus_reader_sources (C17) once a text, and shows what it showed before when that fails.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn?: string; args?: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import { readingOf, readingsByPage } from '@/lib/corpusDisplay';
import { loadMirrorSources } from '@/lib/corpusMirror';
import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock from '@/components/reader/PassageBlock';
import CorpusDoc from '@/pages/corpus/CorpusDoc';

const VERSE = 'नारायणं नमस्कृत्य नरं चैव नरोत्तमम्';

describe('readingOf', () => {
  it('names an e-text and the scans', () => {
    expect(readingOf('gretil-bori-etext')).toEqual({ kind: 'etext', label: 'the BORI Critical Edition e-text (from GRETIL)', scan: false });
    expect(readingOf('gretil-other')?.scan).toBe(false);
    expect(readingOf('gemini-vision:gemini-2.5-flash')).toEqual({ kind: 'vision', label: 'read from the scan by a vision model', scan: true });
    expect(readingOf('tesseract')?.label).toBe('read from the scan by Tesseract OCR');
    expect(readingOf('tesseract-fallback')?.kind).toBe('tesseract');
    expect(readingOf('resegment-devnum')?.kind).toBe('resegment');
    expect(readingOf('someone-new')).toEqual({ kind: 'other', label: 'read by someone-new', scan: true });
    expect(readingOf(null)).toBeNull();
    expect(readingOf('  ')).toBeNull();
  });

  it('takes the engine of most of a page, and leaves an unrecorded page out', () => {
    const m = readingsByPage([
      { page_no: 1, ocr_engine: 'gretil-bori-etext', passages: 3 },
      { page_no: 2, ocr_engine: null, passages: 1 }, { page_no: 2, ocr_engine: 'tesseract', passages: 2 },
      { page_no: 3, ocr_engine: null, passages: 4 }, { page_no: 3, ocr_engine: 'tesseract', passages: 1 },
      { not: 'a row' } as never,
    ]);
    expect([...m.entries()]).toEqual([[1, 'gretil-bori-etext'], [2, 'tesseract']]);
    expect(readingsByPage(null).size).toBe(0);
  });
});

describe('the passage block', () => {
  const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
  const p = (extra: Record<string, unknown>) => ({
    page_no: 1, idx: 1, verse_ref: '1.1.0', sanskrit: VERSE, iast: null, translation: 'Bowing to Nārāyaṇa. //',
    quality_score: 0.45, text_type: 'mula', ...extra,
  });

  it('an e-text is named, not called OCR, and not marked hard to read', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ reading: 'gretil-bori-etext' })} />);
    expect(screen.queryByText('hard-to-read scan')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'About this passage' }));
    expect(screen.getByText('the BORI Critical Edition e-text (from GRETIL)')).toBeTruthy();
    expect(screen.queryByText(/OCR confidence/)).toBeNull();
    expect(screen.getByText('Typed from the edition (an e-text) and translated by machine; not reviewed.')).toBeTruthy();
  });

  it('a scan names its reader beside its OCR confidence', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ reading: 'tesseract' })} />);
    expect(screen.getByText('hard-to-read scan')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'About this passage' }));
    expect(screen.getByText('read from the scan by Tesseract OCR; OCR confidence 45%: the printed page was hard to read')).toBeTruthy();
    expect(screen.getByText('Read by machine from the scan and translated by machine; not reviewed.')).toBeTruthy();
  });

  it('without a recorded engine it is as before', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({})} />);
    expect(screen.getByText('hard-to-read scan')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'About this passage' }));
    expect(screen.getByText('OCR confidence 45%: the printed page was hard to read')).toBeTruthy();
  });
});

const DOC = {
  doc_code: 'MBh01', title: 'Mahabharata, Adiparvan', category: 'mahabharata', passages: 4, english: 4,
  hindi: 0, vectors: 0, stories: 0, published: false, synced_at: '2026-10-14T15:42:24Z',
};
const row = (ord: number, page: number) => ({
  ord, page_no: page, idx: ord, verse_ref: `1.${page}.${ord}`, chapter: String(page), text_type: 'mula',
  sanskrit: VERSE, iast: null, translation: `Verse ${ord}. //`, hindi: null, quality_score: 0.45,
  translation_qa: null, engine: 'gemini', translated_at: '2026-10-01',
});

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/:docCode" element={<CorpusDoc />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe('/corpus/:docCode', () => {
  beforeEach(() => {
    sb.calls = [];
    sb.byFn = {
      corpus_reader_docs: { data: [DOC], error: null },
      corpus_reader_page: { data: [row(1, 1), row(2, 1), row(3, 2), row(4, 2)], error: null },
    };
    try { window.localStorage.clear(); } catch { /* none */ }
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('asks once a text where its pages come from', async () => {
    const r = await loadMirrorSources('MBh01');
    expect(r.ok).toBe(true);
    expect(sb.calls.at(-1)).toEqual({ fn: 'corpus_reader_sources', args: { p_doc: 'MBh01' } });
  });

  it('marks only the scanned page hard to read', async () => {
    sb.byFn.corpus_reader_sources = {
      data: [{ page_no: 1, ocr_engine: 'gretil-bori-etext', passages: 2 }, { page_no: 2, ocr_engine: 'tesseract', passages: 2 }],
      error: null,
    };
    mount('/corpus/MBh01');
    expect(await screen.findByText('Verse 1.')).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText('hard-to-read scan')).toHaveLength(2));   // page 2's two passages
    expect(sb.calls.filter((c) => c.fn === 'corpus_reader_sources')).toHaveLength(1);
  });

  it('shows what it showed before when the function is not there yet', async () => {
    sb.byFn.corpus_reader_sources = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_sources' } };
    mount('/corpus/MBh01');
    expect(await screen.findByText('Verse 4.')).toBeTruthy();
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_sources')).toBe(true));
    expect(screen.getAllByText('hard-to-read scan')).toHaveLength(4);
  });
});
