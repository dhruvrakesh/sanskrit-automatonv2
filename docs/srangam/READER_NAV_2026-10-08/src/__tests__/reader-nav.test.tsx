/**
 * READER_NAV_2026_10_08 - navigation and layout of /corpus/:docCode and /texts/:docCode.
 * The display rules as pure functions; the shared passage block and reading bar; then the corpus
 * reader against a mocked supabase (contents, a scan page, find in this text, the page fetched ahead).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn?: string; name?: string; args?: Record<string, unknown>; opts?: unknown };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: (name: string, opts: unknown) => { sb.calls.push({ name, opts }); return Promise.resolve({ data: { results: [] }, error: null }); } },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  displayTitle, gutterRef, isMisreadLine, outlineFromKeys, passageWhere, readerPageForScan, readerPageOf,
  scanRange, sourceLines,
} from '@/lib/corpusDisplay';
import { DEFAULT_PREFS, loadPrefs, parsePrefs, savePrefs } from '@/lib/readerPrefs';
import PassageBlock from '@/components/reader/PassageBlock';
import ReaderToolbar from '@/components/reader/ReaderToolbar';
import CorpusDoc from '@/pages/corpus/CorpusDoc';

const DOC = {
  doc_code: 'nirukta', title: 'nirukta', category: 'vedanga', passages: 120, english: 110,
  hindi: 100, vectors: 100, stories: 0, published: false, synced_at: '2026-10-08T10:09:41Z',
};
const row = (ord: number, extra: Record<string, unknown> = {}) => ({
  ord, page_no: Math.floor((ord - 1) / 5) + 1, idx: ((ord - 1) % 5) + 1, verse_ref: null, chapter: null,
  text_type: 'mula', sanskrit: `अथ ${ord}`, iast: `atha ${ord}`, translation: `Verse ${ord}. //`, hindi: null,
  quality_score: 0.9, translation_qa: 0.8, engine: 'gemini', translated_at: '2026-10-01', ...extra,
});
const OUTLINE = [
  { kind: 'page', ord: 1, reader_page: 1, page_no: 1, idx: 1, last_page_no: 10, label: null },
  { kind: 'colophon', ord: 30, reader_page: 1, page_no: 6, idx: 5, last_page_no: null, label: 'Thus ends the first chapter. //' },
  { kind: 'page', ord: 51, reader_page: 2, page_no: 11, idx: 1, last_page_no: 20, label: null },
  { kind: 'page', ord: 101, reader_page: 3, page_no: 21, idx: 1, last_page_no: 24, label: null },
];

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.search + l.hash}</output>;
}

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Where />
          <Routes>
            <Route path="/corpus/:docCode" element={<CorpusDoc />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  try { window.localStorage.clear(); } catch { /* none */ }
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  Element.prototype.scrollIntoView = vi.fn();
});

describe('display rules', () => {
  it('a misread line is one with Latin letters and no Devanagari, marked only beside Devanagari', () => {
    expect(isMisreadLine('ay Trae: ।')).toBe(true);
    expect(isMisreadLine('अथ प्रथमोऽध्यायः ।')).toBe(false);
    expect(isMisreadLine('१२ ।')).toBe(false);
    expect(isMisreadLine('ab')).toBe(false);
    const nirukta = sourceLines('ay Trae: ।\nअथ प्रथमोऽध्यायः ।', "ay Trae: |\natha prathamo'dhyāyaḥ |");
    expect(nirukta.sa.map((l) => l.misread)).toEqual([true, false]);
    expect(nirukta.ia.map((l) => l.misread)).toEqual([true, false]);
    // the book's own English (a preface) has no Devanagari at all: nothing is marked
    expect(sourceLines('ADVERTISEMENT\nThe present edition', null).sa.every((l) => !l.misread)).toBe(true);
    // IAST with a different number of lines is not paired
    expect(sourceLines('ay Trae: ।\nअथ', 'atha').ia[0].misread).toBe(false);
  });

  it('titles, references and pages', () => {
    expect(displayTitle('nirukta', 'nirukta')).toBe('Nirukta');
    expect(displayTitle(null, 'markandeya_purana')).toBe('Markandeya Purana');
    expect(displayTitle('Śāṇḍilya Bhakti Sūtra', 'AphorismsOfSandilya')).toBe('Śāṇḍilya Bhakti Sūtra');
    expect(gutterRef({ page_no: 18, idx: 3 })).toBe('18.3');
    expect(passageWhere({ page_no: 18, idx: 3, verse_ref: '1.2' })).toBe('Scan page 18, passage 3; the edition numbers it 1.2');
    expect(readerPageOf(1)).toBe(1);
    expect(readerPageOf(50)).toBe(1);
    expect(readerPageOf(51)).toBe(2);
    expect(scanRange({ page_no: 4, last_page_no: 9 })).toBe('scan pages 4–9');
    expect(scanRange({ page_no: 4, last_page_no: 4 })).toBe('scan page 4');
  });

  it('contents from keys, and the reader page of a scan page', () => {
    const keys = Array.from({ length: 120 }, (_, n) => ({ page_no: Math.floor(n / 5) + 1, idx: (n % 5) + 1 }));
    const pages = outlineFromKeys(keys);
    expect(pages).toEqual([
      { reader_page: 1, page_no: 1, idx: 1, last_page_no: 10 },
      { reader_page: 2, page_no: 11, idx: 1, last_page_no: 20 },
      { reader_page: 3, page_no: 21, idx: 1, last_page_no: 24 },
    ]);
    expect(readerPageForScan(pages, 18)).toBe(2);
    expect(readerPageForScan(pages, 10)).toBe(1);
    expect(readerPageForScan(pages, 0)).toBe(1);
    expect(readerPageForScan(pages, 99)).toBe(3);
    // a scan page with no passages goes to the next reader page that has a later one
    const gap = [{ reader_page: 1, page_no: 1, idx: 1, last_page_no: 4 }, { reader_page: 2, page_no: 8, idx: 1, last_page_no: 9 }];
    expect(readerPageForScan(gap, 6)).toBe(2);
    expect(readerPageForScan([], 3)).toBeNull();
  });

  it('preferences survive bad or blocked storage', () => {
    expect(parsePrefs(null)).toEqual(DEFAULT_PREFS);
    expect(parsePrefs('{nope')).toEqual(DEFAULT_PREFS);
    expect(parsePrefs('{"layout":"stacked","hindi":false,"iast":"x"}')).toEqual({ ...DEFAULT_PREFS, layout: 'stacked', hindi: false });
    savePrefs({ ...DEFAULT_PREFS, iast: false });
    expect(loadPrefs().iast).toBe(false);
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    expect(loadPrefs()).toEqual(DEFAULT_PREFS);
    spy.mockRestore();
  });
});

describe('the passage block', () => {
  const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);

  it('margin reference with its tooltip, the Sanskrit beside the translation, a misread line marked', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={{
      page_no: 1, idx: 1, verse_ref: '1.1', sanskrit: 'ay Trae: ।\nअथ प्रथमोऽध्यायः ।', iast: "ay Trae: |\natha prathamo'dhyāyaḥ |",
      translation: 'Now, the first chapter. //', hindi: 'अब पहला अध्याय।', quality_score: 0.42, text_type: 'mula',
    }} />);
    const ref = screen.getByRole('link', { name: '1.1' });
    expect(ref.getAttribute('href')).toBe('#p1-1');
    expect(ref.getAttribute('title')).toContain('Scan page 1, passage 1');
    expect(screen.getByTitle("The edition's own number for this passage").textContent).toBe('1.1');
    const bad = screen.getByText('ay Trae: ।');
    expect(bad.getAttribute('title')).toMatch(/misread/);
    expect(screen.getByText('अथ प्रथमोऽध्यायः ।').getAttribute('title')).toBeNull();
    expect(screen.getByText('Now, the first chapter.')).toBeTruthy();
    expect(screen.getByText('अब पहला अध्याय।')).toBeTruthy();
    expect(screen.getByText('hard-to-read scan').getAttribute('title')).toContain('42%');
    expect(document.querySelector('.lg\\:grid-cols-2')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'About this passage' })).toBeTruthy();
  });

  it('stacked, without IAST or Hindi, says when a passage is not translated', () => {
    wrap(<PassageBlock prefs={{ ...DEFAULT_PREFS, layout: 'stacked', iast: false, hindi: false }} p={{
      page_no: 2, idx: 1, verse_ref: null, sanskrit: 'मूल', iast: 'mūla', translation: null, hindi: 'हिन्दी', quality_score: null,
    }} />);
    expect(screen.queryByText('mūla')).toBeNull();
    expect(screen.queryByText('हिन्दी')).toBeNull();
    expect(screen.getByText('Not translated yet.')).toBeTruthy();
    expect(document.querySelector('.lg\\:grid-cols-2')).toBeNull();
  });

  it('scanner noise is folded until asked for; a colophon is labelled', () => {
    wrap(<>
      <PassageBlock prefs={DEFAULT_PREFS} p={{ page_no: 3, idx: 1, verse_ref: null, sanskrit: '~~ ||| ~~', iast: null, translation: null, quality_score: 0.3, text_type: 'noise' }} />
      <PassageBlock prefs={DEFAULT_PREFS} p={{ page_no: 3, idx: 2, verse_ref: null, sanskrit: 'इति प्रथमोऽध्यायः', iast: null, translation: 'Thus ends the first chapter.', quality_score: 0.9, text_type: 'colophon' }} />
    </>);
    expect(screen.queryByText('~~ ||| ~~')).toBeNull();
    expect(screen.getByText('Scanner noise, not text.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Show it' }));
    expect(screen.getByText('~~ ||| ~~')).toBeTruthy();
    expect(screen.getByText('Colophon').getAttribute('title')).toMatch(/closing line/);
  });
});

describe('the reading bar', () => {
  it('arrow keys turn the page, but not while typing; the select goes to any page; toggles set prefs', () => {
    const go = vi.fn(); const setPrefs = vi.fn();
    render(
      <ReaderToolbar page={2} lastPage={5} perPage={50} total={230} go={go} prefs={DEFAULT_PREFS} setPrefs={setPrefs} hindi>
        <input aria-label="a field" />
      </ReaderToolbar>,
    );
    expect(screen.getAllByText(/Page 2 of 5/).length).toBeGreaterThan(0);
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(go).toHaveBeenLastCalledWith(3);
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(go).toHaveBeenLastCalledWith(1);
    go.mockClear();
    fireEvent.keyDown(screen.getByLabelText('a field'), { key: 'ArrowRight' });
    expect(go).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Go to page'), { target: { value: '5' } });
    expect(go).toHaveBeenLastCalledWith(5);
    fireEvent.click(screen.getByLabelText('Show the Hindi'));
    expect(setPrefs).toHaveBeenLastCalledWith({ hindi: false });
    fireEvent.click(screen.getByLabelText('Show the translation beside the Sanskrit'));
    expect(setPrefs).toHaveBeenLastCalledWith({ layout: 'stacked' });
    expect(screen.queryByLabelText('Show scanner noise')).toBeNull();
  });
});

describe('/corpus/:docCode', () => {
  beforeEach(() => {
    sb.byFn = {
      corpus_reader_docs: { data: [DOC], error: null },
      corpus_reader_page: { data: Array.from({ length: 50 }, (_, i) => row(i + 1, i === 6 ? { text_type: 'noise' } : {})), error: null },
      corpus_reader_outline: { data: OUTLINE, error: null },
      corpus_reader_search: { data: [{ doc_code: 'nirukta', title: 'nirukta', page_no: 18, idx: 2, verse_ref: null, ord: 87, score: 0.3, snippet: 'the [[cow]] is' }], error: null },
    };
  });

  it('a readable title, the next page fetched ahead, contents only when opened', async () => {
    mount('/corpus/nirukta');
    expect(await screen.findByRole('heading', { name: 'Nirukta' })).toBeTruthy();
    expect(await screen.findByText('Verse 1.')).toBeTruthy();
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_page' && c.args?.p_offset === 50)).toBe(true));
    expect(sb.calls.some((c) => c.fn === 'corpus_reader_outline')).toBe(false);
    expect(screen.getByText('Scanner noise, not text.')).toBeTruthy();
    expect(screen.getByLabelText('Show scanner noise')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Contents/ }));
    const panel = await screen.findByRole('dialog');
    expect(await within(panel).findByText('scan pages 11–20')).toBeTruthy();
    expect(within(panel).getByText(/Thus ends the first chapter\./)).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_outline')?.args).toEqual({ p_doc: 'nirukta', p_per_page: 50 });
    fireEvent.click(within(panel).getByRole('button', { name: /Page 2/ }));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('?p=2'));
  });

  it('go to a scan page: the reader page that holds it', async () => {
    mount('/corpus/nirukta');
    await screen.findByText('Verse 1.');
    fireEvent.click(screen.getByRole('button', { name: /Contents/ }));
    const panel = await screen.findByRole('dialog');
    fireEvent.change(within(panel).getByLabelText(/scan page/), { target: { value: '18' } });
    await act(async () => { fireEvent.click(within(panel).getByRole('button', { name: 'Go' })); });
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('?p=2'));
  });

  it('without C5b the contents fall back to plain page numbers, and say so', async () => {
    sb.byFn.corpus_reader_outline = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_outline' } };
    mount('/corpus/nirukta');
    await screen.findByText('Verse 1.');
    fireEvent.click(screen.getByRole('button', { name: /Contents/ }));
    const panel = await screen.findByRole('dialog');
    expect(await within(panel).findByText(/not available yet/)).toBeTruthy();
    expect(within(panel).getByRole('button', { name: 'Page 3' })).toBeTruthy();
  });

  it('find in this text searches this document only and links to the passage', async () => {
    mount('/corpus/nirukta');
    await screen.findByText('Verse 1.');
    fireEvent.change(screen.getByLabelText('Find in this text'), { target: { value: 'cow' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find' }));
    const mark = await screen.findByText('cow', { selector: 'mark' });
    expect(mark).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_search')?.args).toEqual({ q: 'cow', k: 30, p_doc: 'nirukta' });
    expect(screen.getByRole('link', { name: 'p18.2' }).getAttribute('href')).toBe('/corpus/nirukta?p=2#p18-2');
  });
});
