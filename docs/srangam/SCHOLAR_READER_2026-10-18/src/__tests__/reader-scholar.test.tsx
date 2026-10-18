/**
 * SCHOLAR_READER_2026_10_18 - the scholarly English in the corpus reader.
 * A verse with a scholarly English shows it first, labelled, with its standing (judged faithful, flagged, its
 * Sanskrit in doubt, read by a person) and its notes in a popover; its working English folds under it. A verse whose
 * sentence is given with an earlier verse says so. A malformed meta row gives the English alone. The reader asks
 * public.corpus_reader_scholar_count once a text, and corpus_reader_scholar once a page only for a text that has
 * scholarly English; before C18 is pasted the count fails, nothing else is asked, and the reader is as before.
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

import { emphasisParts, engineName, parseScholar, scholarByPassage, scholarStatus } from '@/lib/scholarReading';
import { loadMirrorScholar, loadMirrorScholarCount, type MirrorScholarRow } from '@/lib/corpusMirror';
import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock from '@/components/reader/PassageBlock';
import CorpusDoc from '@/pages/corpus/CorpusDoc';

const VERSE = 'सावर्णिः सूर्यतनयो यो मनुः कथ्यतेऽष्टमः';
const META = JSON.stringify({
  status: 'passed', flag: false, accepted: false, judge: 'gemini:gemini-2.5-flash',
  notes: [{ anchor: 'Sāvarṇi', note: 'The eighth *Manu*.', kind: 'name' }, { anchor: 'x', note: '' }, 'junk'],
});
const srow = (extra: Partial<MirrorScholarRow>): MirrorScholarRow => ({
  page_no: 1, idx: 1, scholar: 'Sāvarṇi, the son of the Sun, is called the eighth *Manu*. //', meta: META,
  fidelity: 5, fluency: 4, engine: 'anthropic:claude-sonnet-5-5', made_at: '2026-10-18T08:00:44+00:00', ...extra,
});

describe('parseScholar', () => {
  it('reads the English, its standing and its notes', () => {
    const s = parseScholar(srow({}))!;
    expect(s.text).toContain('eighth *Manu*');
    expect((({ status, flag, accepted, fidelity, fluency, judge }) => ({ status, flag, accepted, fidelity, fluency, judge }))(s))
      .toEqual({ status: 'passed', flag: false, accepted: false, fidelity: 5, fluency: 4, judge: 'gemini:gemini-2.5-flash' });
    expect(s.notes).toEqual([{ anchor: 'Sāvarṇi', note: 'The eighth *Manu*.', kind: 'name' }]);
    expect(s.with).toBeNull();
  });

  it('a malformed meta row gives the English alone; an empty row nothing', () => {
    const s = parseScholar(srow({ meta: '{not json' }))!;
    expect(s.text).toContain('Sāvarṇi');
    expect((({ status, flag, notes }) => ({ status, flag, notes }))(s)).toEqual({ status: '', flag: false, notes: [] });
    expect(parseScholar(srow({ scholar: null, meta: null }))).toBeNull();
    expect(parseScholar(srow({ scholar: '  ', meta: '[]' }))).toBeNull();
    expect(parseScholar(null)).toBeNull();
  });

  it('a verse given with the sentence before it', () => {
    const s = parseScholar(srow({ scholar: null, meta: JSON.stringify({ status: 'passed', with: '81.3–4' }) }))!;
    expect((({ text, with: w }) => ({ text, w }))(s)).toEqual({ text: '', w: '81.3–4' });
  });

  it('a flag from its status when the row has none; a person lifts it', () => {
    expect(parseScholar(srow({ meta: JSON.stringify({ status: 'flagged' }) }))!.flag).toBe(true);
    expect(parseScholar(srow({ meta: JSON.stringify({ status: 'source_doubt', accepted: true }) }))!.flag).toBe(false);
  });

  it('by passage, skipping what is not a row', () => {
    const m = scholarByPassage([srow({}), srow({ page_no: 2, idx: 3 }), { page_no: 'x' } as never, srow({ idx: 9, scholar: null, meta: null })]);
    expect([...m.keys()]).toEqual(['p1-1', 'p2-3']);
    expect(scholarByPassage(null).size).toBe(0);
  });
});

describe('the words', () => {
  it('italics and engines', () => {
    expect(emphasisParts('the *Manu* of *this* age')).toEqual([
      { text: 'the ', em: false }, { text: 'Manu', em: true }, { text: ' of ', em: false }, { text: 'this', em: true }, { text: ' age', em: false },
    ]);
    expect(emphasisParts('2 * 3 = 6')).toEqual([{ text: '2 * 3 = 6', em: false }]);
    expect(engineName('anthropic:claude-sonnet-5-5')).toBe('Claude Sonnet 5.5');
    expect(engineName('gemini:gemini-2.5-pro')).toBe('Gemini 2.5 Pro');
    expect(engineName('someone')).toBe('someone');
  });

  it('the standing', () => {
    const s = parseScholar(srow({}))!;
    expect(scholarStatus(s).label).toBe('judged faithful');
    expect(scholarStatus(s).title).toBe('Judged verse by verse against the Sanskrit by Gemini 2.5 Flash (fidelity 5 of 5, fluency 4 of 5); not yet read by a person.');
    expect(scholarStatus({ ...s, status: 'flagged', flag: true }).label).toBe('flagged by the judge');
    expect(scholarStatus({ ...s, status: 'source_doubt', flag: true }).label).toBe('the Sanskrit in doubt');
    expect(scholarStatus({ ...s, accepted: true }).label).toBe('read by a person');
  });
});

describe('the passage block', () => {
  const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
  const p = (extra: Record<string, unknown>) => ({
    page_no: 1, idx: 1, verse_ref: '81.1', sanskrit: VERSE, iast: null, translation: 'Savarni, son of the Sun. //',
    quality_score: null, text_type: 'mula', ...extra,
  });

  it('the scholarly English first, the working English folded under it', () => {
    const { container } = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ scholar: parseScholar(srow({})) })} />);
    expect(screen.getByText('Scholarly English')).toBeTruthy();
    expect(screen.getByText('judged faithful')).toBeTruthy();
    expect(container.querySelector('[data-scholar="english"] em')?.textContent).toBe('Manu');
    expect(container.querySelector('details summary')?.textContent).toBe('Working English (machine)');
    expect(container.querySelector('details p')?.textContent).toBe('Savarni, son of the Sun.');
    expect(container.innerHTML).not.toContain('*Manu*');
    fireEvent.click(screen.getByRole('button', { name: 'About the scholarly English' }));
    expect(screen.getByText('1 note')).toBeTruthy();
    expect(screen.getByText(/Claude Sonnet 5\.5, 2026-10-18; read by a critic and revised/)).toBeTruthy();
    expect(document.body.textContent).toContain('The eighth Manu.');
  });

  it('a verse with a scholarly English only is never "Not translated yet"', () => {
    const { container } = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ translation: null, scholar: parseScholar(srow({})) })} />);
    expect(screen.queryByText('Not translated yet.')).toBeNull();
    expect(container.querySelector('details')).toBeNull();
  });

  it('a flagged verse, and one given with the sentence before it', () => {
    const flagged = parseScholar(srow({ meta: JSON.stringify({ status: 'flagged', flag: true, doubts: 'The reading may be *corrupt*.' }) }));
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ scholar: flagged })} />);
    expect(screen.getByText('flagged by the judge')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'About the scholarly English' }));
    expect(screen.getByText(/The translator.s doubt:/)).toBeTruthy();
    const w = parseScholar(srow({ idx: 2, scholar: null, meta: JSON.stringify({ status: 'passed', with: '81.3–4' }) }));
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ idx: 2, scholar: w })} />);
    expect(screen.getByText('Its scholarly English is given with the sentence at 81.3–4.')).toBeTruthy();
  });

  it('without one it is as before', () => {
    const { container } = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({})} />);
    expect(screen.queryByText('Scholarly English')).toBeNull();
    expect(container.querySelector('details')).toBeNull();
    expect(screen.getByText('Savarni, son of the Sun.')).toBeTruthy();
  });

  it('English off hides both', () => {
    wrap(<PassageBlock prefs={{ ...DEFAULT_PREFS, english: false }} p={p({ scholar: parseScholar(srow({})) })} />);
    expect(screen.queryByText('Scholarly English')).toBeNull();
    expect(screen.queryByText('Working English (machine)')).toBeNull();
  });
});

const DOC = {
  doc_code: 'markandeya_purana__w_gretil', title: 'Markandeya Purana (GRETIL)', category: 'purana', passages: 3, english: 0,
  hindi: 0, vectors: 0, stories: 0, published: false, synced_at: '2026-10-18T15:42:24Z',
};
const row = (idx: number) => ({
  ord: idx, page_no: 626, idx, verse_ref: `81.${idx}`, chapter: '81', text_type: 'mula', sanskrit: VERSE, iast: null,
  translation: null, hindi: null, quality_score: null, translation_qa: null, engine: null, translated_at: null,
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
      corpus_reader_page: { data: [row(1), row(2), row(3)], error: null },
    };
    try { window.localStorage.clear(); } catch { /* none */ }
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('asks for a page and for the count as the reader page does', async () => {
    await loadMirrorScholar('MBh01', 3);
    expect(sb.calls[sb.calls.length - 1]).toEqual({ fn: 'corpus_reader_scholar', args: { p_doc: 'MBh01', p_offset: 100, p_limit: 50 } });
    await loadMirrorScholarCount('MBh01');
    expect(sb.calls[sb.calls.length - 1]).toEqual({ fn: 'corpus_reader_scholar_count', args: { p_doc: 'MBh01' } });
  });

  it('shows a page of scholarly English, and its count in the header', async () => {
    sb.byFn.corpus_reader_scholar_count = { data: [{ verses: 2, flagged: 1 }], error: null };
    sb.byFn.corpus_reader_scholar = {
      data: [srow({ page_no: 626, idx: 1 }), srow({ page_no: 626, idx: 2, meta: JSON.stringify({ status: 'flagged', flag: true }) })],
      error: null,
    };
    mount('/corpus/markandeya_purana__w_gretil');
    expect(await screen.findByText('2 in scholarly English')).toBeTruthy();
    await waitFor(() => expect(document.querySelectorAll('[data-scholar="english"]')).toHaveLength(2));
    expect(screen.getByText('flagged by the judge')).toBeTruthy();
    expect(screen.getAllByText('Not translated yet.')).toHaveLength(1);   // 81.3 has neither
    const call = sb.calls.find((c) => c.fn === 'corpus_reader_scholar');
    expect(call?.args).toEqual({ p_doc: 'markandeya_purana__w_gretil', p_offset: 0, p_limit: 50 });
  });

  it('a text without scholarly English is asked once, not page by page', async () => {
    sb.byFn.corpus_reader_scholar_count = { data: [{ verses: 0, flagged: 0 }], error: null };
    mount('/corpus/markandeya_purana__w_gretil');
    expect(await screen.findAllByText('Not translated yet.')).toHaveLength(3);
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_scholar_count')).toBe(true));
    expect(sb.calls.some((c) => c.fn === 'corpus_reader_scholar')).toBe(false);
    expect(screen.queryByText(/in scholarly English/)).toBeNull();
  });

  it('is as before when C18 is not there yet', async () => {
    sb.byFn.corpus_reader_scholar_count = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_scholar_count' } };
    mount('/corpus/markandeya_purana__w_gretil');
    expect(await screen.findAllByText('Not translated yet.')).toHaveLength(3);
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_scholar_count')).toBe(true));
    expect(sb.calls.some((c) => c.fn === 'corpus_reader_scholar')).toBe(false);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
