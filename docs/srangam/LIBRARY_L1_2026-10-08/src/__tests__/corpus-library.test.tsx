/**
 * CORPUS_LIBRARY_C6_2026_10_08 - the library over the working corpus: shelves, progress, stories,
 * names, the names in the reader, and ?at= links. The pure rules first; then the pages against a
 * mocked supabase whose answers are set per database function.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
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

import shelfJson from '@/data/corpusShelf.json';
import {
  atHref, bookTitle, fromHref, namesByPassage, parseAt, parseCites, parseVerify, seriesLabel, shelve, SHELF,
  stageSummary, stagesByDoc, storyHref, type ShelfFile,
} from '@/lib/corpusLibrary';
import CorpusHome from '@/pages/corpus/CorpusHome';
import CorpusDoc from '@/pages/corpus/CorpusDoc';
import CorpusStories from '@/pages/corpus/CorpusStories';
import CorpusNames from '@/pages/corpus/CorpusNames';

const doc = (code: string, extra: Record<string, unknown> = {}) => ({
  doc_code: code, title: code, category: 'purana', passages: 1222, english: 1219, hindi: 1216, vectors: 1200,
  stories: 13, published: false, synced_at: '2026-10-08T10:00:00Z', ...extra,
});
const MARK = doc('markandeya_purana', { title: 'Mārkaṇḍeya Purāṇa', published: true });
const NIR = doc('nirukta', { category: 'vedanga', passages: 120, english: 110, hindi: 0, stories: 0 });
const STAGES = ['ingest', 'ocr', 'segment', 'translate_en', 'translate_hi'].map((stage, i) => ({
  doc_code: 'nirukta', stage, status: i === 2 ? 'degraded' : i === 4 ? 'pending' : 'done',
  reason: i === 2 ? 'only 53.8% of rows are verse-shaped' : 'ok', updated_at_local: '2026-09-27',
}));
const STORY = {
  doc_code: 'markandeya_purana', doc_title: 'Mārkaṇḍeya Purāṇa', story_id: 1, status: 'approved',
  title: 'Śamīka finds the fledglings', title_hi: 'शमीक को चूजे मिलते हैं', why: 'A rescue.', from_page: 10, from_idx: 8,
  to_page: 15, to_idx: 3, from_ord: 120, story_en: 'The bird-children were full of worry.', story_hi: 'पक्षी-बच्चे चिंतित थे।',
  quote_sa: 'स तत्र शब्दमश्रृणोत्', quote_ref: '11.6', cites: '["10.8","11.6","bad"]',
  verify: '{"ok": true, "problems": [], "words": 162}', model: 'gemini-2.5-flash', approved_at_local: '2026-10-08T09:00:00',
  updated_at_local: null,
};

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search + l.hash}</output>;
}

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Where />
          <Routes>
            <Route path="/corpus" element={<CorpusHome />} />
            <Route path="/corpus/stories" element={<CorpusStories />} />
            <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />
            <Route path="/corpus/names" element={<CorpusNames />} />
            <Route path="/corpus/names/:canonical" element={<CorpusNames />} />
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

describe('the rules', () => {
  it('the shelf file: every text on one shelf, shelves in order', () => {
    const f = shelfJson as unknown as ShelfFile;
    const all = f.collections.flatMap((c) => c.members);
    expect(new Set(all).size).toBe(all.length);
    expect(f.collections.map((c) => c.order)).toEqual([...f.collections.map((c) => c.order)].sort((a, b) => a - b));
    expect(Object.keys(f.books).sort()).toEqual([...all].sort());
    expect(f.collections.find((c) => c.key === 'vedanga')?.members).toContain('nirukta');
  });

  it('shelving, titles and series', () => {
    const shelf: ShelfFile = {
      collections: [
        { key: 'b', title: 'B', title_sa: '', order: 20, members: ['y'] },
        { key: 'a', title: 'A', title_sa: 'अ', order: 10, members: ['x2', 'x1'] },
        { key: 'empty', title: 'E', title_sa: '', order: 15, members: ['nope'] },
        { key: 'other', title: 'Other texts', title_sa: '', order: 999, members: [] },
      ],
      books: { x1: { derived_title: 'X One', series: { title: 'Series', number: 1 } }, x2: { derived_title: 'X Two', series: null }, y: { derived_title: 'Why', series: null } },
    };
    const docs = [{ doc_code: 'x1' }, { doc_code: 'z' }, { doc_code: 'x2' }, { doc_code: 'y' }];
    expect(shelve(docs, shelf).map((s) => [s.key, s.books.map((b) => b.doc_code)])).toEqual([
      ['a', ['x2', 'x1']], ['b', ['y']], ['other', ['z']],
    ]);
    expect(bookTitle({ doc_code: 'x1', title: 'x1' }, shelf)).toEqual({ title: 'X One', derived: true });
    expect(bookTitle({ doc_code: 'x1', title: 'Confirmed' }, shelf)).toEqual({ title: 'Confirmed', derived: false });
    expect(bookTitle({ doc_code: 'q_r', title: null }, shelf)).toEqual({ title: 'Q R', derived: true });
    expect(seriesLabel('x1', shelf)).toBe('Series · 1');
    expect(seriesLabel('harita_tritiya_sthanam', SHELF)).toMatch(/Saṃhitā · 3$/);
  });

  it('stages, citations, checks and links', () => {
    expect(stageSummary(STAGES)).toEqual({ done: 3, total: 5, degraded: 1, blocked: 0, pending: 1 });
    expect([...stagesByDoc([...STAGES, { doc_code: 'x' }, null, MARK]).keys()]).toEqual(['nirukta']);
    expect(parseCites(STORY.cites)).toEqual(['10.8', '11.6']);
    expect(parseCites('not json')).toEqual([]);
    expect(parseVerify(STORY.verify)).toEqual({ ok: true, problems: [], words: 162, checked_at: null });
    expect(parseVerify('{').ok).toBeNull();
    expect(storyHref(STORY)).toBe('/corpus/stories/markandeya_purana/1');
    expect(atHref('markandeya_purana', '11.6')).toBe('/corpus/markandeya_purana?at=11.6');
    expect(fromHref(STORY)).toBe('/corpus/markandeya_purana?p=3#p10-8');
    expect(fromHref({ ...STORY, from_ord: null })).toBe('/corpus/markandeya_purana?at=10.8');
    expect(parseAt('18.2')).toEqual({ page: 18, idx: 2 });
    expect(parseAt('18')).toBeNull();
    expect(parseAt('x.2')).toBeNull();
    const m = namesByPassage([{ page_no: 6, idx: 1, canonical: 'Garuda' }, { page_no: 6, idx: 1, canonical: 'Ganga' }, { bad: 1 }]);
    expect(m.get('p6-1')?.map((n) => n.canonical)).toEqual(['Garuda', 'Ganga']);
  });
});

describe('/corpus, the library', () => {
  beforeEach(() => {
    sb.byFn = {
      corpus_reader_docs: { data: [MARK, NIR], error: null },
      corpus_reader_progress: { data: STAGES, error: null },
      corpus_reader_stories: { data: [{ ...STORY, story_en: null, story_hi: null }], error: null },
    };
  });

  it('texts on their shelves, in shelf order, with derived titles marked, stages and stories', async () => {
    mount('/corpus');
    const ved = await screen.findByRole('heading', { name: /Vedāṅgas/ });
    const pur = screen.getByRole('heading', { name: /Purāṇas/ });
    expect(ved.compareDocumentPosition(pur) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const nir = screen.getByRole('link', { name: 'Nirukta' });
    expect(nir.getAttribute('href')).toBe('/corpus/nirukta');
    expect(nir.getAttribute('title')).toMatch(/derived from the file name/);
    expect(screen.getByRole('link', { name: 'Mārkaṇḍeya Purāṇa' }).getAttribute('title')).toBeNull();
    expect(await screen.findByRole('button', { name: 'The stages of this text' })).toBeTruthy();
    expect(screen.getByText('3 of 5 stages')).toBeTruthy();
    expect(screen.getAllByRole('link', { name: /Stories/ }).map((a) => a.getAttribute('href'))).toContain('/corpus/stories?doc=markandeya_purana');
    expect(screen.getByText(/1 story/)).toBeTruthy();
    expect(screen.getByRole('progressbar', { name: 'English: 92%' })).toBeTruthy();
  });

  it('filter, sort and narrow', async () => {
    mount('/corpus');
    await screen.findByRole('heading', { name: /Vedāṅgas/ });
    fireEvent.change(screen.getByLabelText('Filter the library'), { target: { value: 'nirukta' } });
    expect(screen.queryByRole('link', { name: 'Mārkaṇḍeya Purāṇa' })).toBeNull();
    expect(screen.getByText('1 of 2 texts')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Filter the library'), { target: { value: 'markandeya' } });
    expect(screen.getByRole('link', { name: 'Mārkaṇḍeya Purāṇa' })).toBeTruthy();   // diacritics folded
    fireEvent.change(screen.getByLabelText('Filter the library'), { target: { value: '' } });
    fireEvent.change(screen.getByLabelText('Sort the library'), { target: { value: 'title' } });
    expect(screen.queryByRole('heading', { name: /Vedāṅgas/ })).toBeNull();
    fireEvent.click(screen.getByLabelText(/with stories/));
    expect(screen.queryByRole('link', { name: 'Nirukta' })).toBeNull();
  });

  it('without C6 the library still shows every text, without stages or stories', async () => {
    const missing = (fn: string) => ({ data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn} without parameters in the schema cache` } });
    sb.byFn.corpus_reader_progress = missing('corpus_reader_progress');
    sb.byFn.corpus_reader_stories = missing('corpus_reader_stories');
    mount('/corpus');
    expect(await screen.findByRole('link', { name: 'Nirukta' })).toBeTruthy();
    await waitFor(() => expect(sb.calls.filter((c) => c.fn === 'corpus_reader_stories').length).toBeGreaterThan(0));
    expect(screen.queryByRole('button', { name: 'The stages of this text' })).toBeNull();
    expect(screen.queryByLabelText(/with stories/)).toBeNull();
  });
});

describe('/corpus/stories', () => {
  it('the list, one text at a time', async () => {
    sb.byFn.corpus_reader_stories = { data: [{ ...STORY, story_en: null }, { ...STORY, doc_code: 'nilamata_seg', doc_title: 'Nīlamata', story_id: 22, title: 'The lake', status: 'draft' }], error: null };
    mount('/corpus/stories');
    const link = await screen.findByRole('link', { name: 'Śamīka finds the fledglings' });
    expect(link.getAttribute('href')).toBe('/corpus/stories/markandeya_purana/1');
    expect(screen.getByText('draft')).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_stories')?.args).toEqual({ p_doc: null, p_full: false });
    fireEvent.click(screen.getByRole('button', { name: /Nīlamata/ }));
    expect(screen.queryByRole('link', { name: 'Śamīka finds the fledglings' })).toBeNull();
    expect(screen.getByTestId('where').textContent).toBe('/corpus/stories?doc=nilamata_seg');
  });

  it('none approved yet says so', async () => {
    mount('/corpus/stories');
    expect(await screen.findByText(/No story has been approved yet/)).toBeTruthy();
  });

  it('one story: the Sanskrit line, both languages, its citations as links, its check', async () => {
    sb.byFn.corpus_reader_stories = { data: [STORY], error: null };
    mount('/corpus/stories/markandeya_purana/1');
    expect(await screen.findByRole('heading', { name: 'Śamīka finds the fledglings' })).toBeTruthy();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_stories')?.args).toEqual({ p_doc: 'markandeya_purana', p_full: true });
    expect(screen.getByText('स तत्र शब्दमश्रृणोत्')).toBeTruthy();
    expect(screen.getAllByRole('link', { name: '11.6' }).map((a) => a.getAttribute('href'))).toEqual(['/corpus/markandeya_purana?at=11.6', '/corpus/markandeya_purana?at=11.6']);
    expect(screen.getByText('The bird-children were full of worry.')).toBeTruthy();
    expect(screen.getByText('पक्षी-बच्चे चिंतित थे।')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'English' }));
    expect(screen.queryByText('पक्षी-बच्चे चिंतित थे।')).toBeNull();
    expect(screen.getByRole('link', { name: '10.8' }).getAttribute('href')).toBe('/corpus/markandeya_purana?at=10.8');
    expect(screen.getByText(/every citation is in the text; 162 words/)).toBeTruthy();
    expect(screen.getByRole('link', { name: /10\.8.15\.3/ }).getAttribute('href')).toBe('/corpus/markandeya_purana?p=3#p10-8');
  });
});

describe('/corpus/names', () => {
  it('the index with counts, a kind, and one name with its passages', async () => {
    sb.byFn.corpus_reader_names = { data: [{ canonical: 'Garuḍa', kind: 'deity', notes: 'the eagle', variants: ['Suparṇa'], mentions: 4, texts: 2, total: 1 }], error: null };
    mount('/corpus/names');
    const link = await screen.findByRole('link', { name: 'Garuḍa' });
    expect(link.getAttribute('href')).toBe('/corpus/names/Garu%E1%B8%8Da');
    expect(screen.getByText(/4 · 2 texts/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Rivers' }));
    await waitFor(() => expect(sb.calls.some((c) => c.fn === 'corpus_reader_names' && c.args.p_kind === 'river')).toBe(true));

    sb.byFn.corpus_reader_name = { data: [{ doc_code: 'markandeya_purana', title: 'Mārkaṇḍeya Purāṇa', page_no: 6, idx: 1, verse_ref: null, ord: 51, surface: 'Suparṇa', snippet: 'Suparṇa flew. //', total: 1 }], error: null };
    fireEvent.click(screen.getByRole('button', { name: 'All names' }));
    fireEvent.click(await screen.findByRole('link', { name: 'Garuḍa' }));
    expect(await screen.findByRole('heading', { name: 'Garuḍa' })).toBeTruthy();
    expect(await screen.findByText('Suparṇa flew.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Read it in the text' }).getAttribute('href')).toBe('/corpus/markandeya_purana?p=2#p6-1');
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_name')?.args).toEqual({ p_canonical: 'Garuḍa', k: 50, p_offset: 0 });
  });
});

describe('/corpus/:docCode with names and ?at=', () => {
  const PASSAGE = { ord: 1, page_no: 6, idx: 1, verse_ref: null, chapter: null, text_type: 'mula', sanskrit: 'गरुडः', iast: 'garuḍaḥ', translation: 'Garuda flew. //', hindi: null, quality_score: 0.9, translation_qa: 1, engine: 'gemini', translated_at: null };

  it('chips for the names in each passage, which the reader can turn off', async () => {
    sb.byFn = {
      corpus_reader_docs: { data: [MARK], error: null },
      corpus_reader_page: { data: [PASSAGE], error: null },
      corpus_reader_page_names: { data: [{ page_no: 6, idx: 1, canonical: 'Garuḍa', surface: 'garuḍaḥ', kind: 'deity', notes: 'the eagle' }], error: null },
    };
    mount('/corpus/markandeya_purana');
    const chip = await screen.findByRole('button', { name: 'Garuḍa' });
    fireEvent.click(chip);
    const card = await screen.findByRole('dialog');
    expect(within(card).getByRole('link', { name: /Every passage that names Garuḍa/ }).getAttribute('href')).toBe('/corpus/names/Garu%E1%B8%8Da');
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_page_names')?.args).toEqual({ p_doc: 'markandeya_purana', p_offset: 0, p_limit: 50 });
    fireEvent.keyDown(card, { key: 'Escape' });
    fireEvent.click(screen.getByLabelText('Show the names in each passage'));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Garuḍa' })).toBeNull());
  });

  it('?at=18.2 lands on the reader page that holds scan page 18', async () => {
    sb.byFn = {
      corpus_reader_docs: { data: [MARK], error: null },
      corpus_reader_outline: { data: [
        { kind: 'page', ord: 1, reader_page: 1, page_no: 1, idx: 1, last_page_no: 10, label: null },
        { kind: 'page', ord: 51, reader_page: 2, page_no: 11, idx: 1, last_page_no: 20, label: null },
      ], error: null },
      corpus_reader_page: { data: [PASSAGE], error: null },
    };
    mount('/corpus/markandeya_purana?at=18.2');
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/corpus/markandeya_purana?p=2#p18-2'));
    expect(sb.calls.filter((c) => c.fn === 'corpus_reader_page').every((c) => c.args.p_offset !== 0)).toBe(true);
  });
});
