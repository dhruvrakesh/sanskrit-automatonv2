/**
 * SCHOLAR_SITE_2026_10_25 - the scholarly English as the desk has it: /corpus/scholarly lists every text that has it
 * (corpus_reader_scholar_docs, docs/cloud/C22), and /corpus/:docCode/prose reads one as prose (corpus_reader_scholar_prose):
 * chapters as the edition makes them (the verses' own two-part references, a heading with the next verse, a colophon
 * with the one before; else a numeric chapter; else the page), a sentence over verses whole after its range, a
 * paragraph where a speaker begins, the notes numbered after their anchors and listed at the chapter's end, a flagged
 * verse marked; PROSE_BATCH rows a call, the next after the last row read. Before C22 is pasted both pages say so.
 * The reader's header links a text with scholarly English to its prose; an edition links its own prose page only.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn?: string; args?: Record<string, unknown> };
const sb = vi.hoisted(() => ({
  byFn: {} as Record<string, RpcAnswer>,
  calls: [] as Call[],
  prose: null as null | ((args: Record<string, unknown>) => RpcAnswer),
}));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => {
      sb.calls.push({ fn, args });
      if (fn === 'corpus_reader_scholar_prose' && sb.prose) return Promise.resolve(sb.prose(args));
      return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  PROSE_BATCH, chapterKeys, loadScholarDocs, loadScholarProse, proseChapters, proseHref, verseHref, verseLabel,
  withNotes, type ProseRow,
} from '@/lib/scholarSite';
import { cleanEditions } from '@/lib/editions';
import { CORPUS_LINKS } from '@/components/navigation/CorpusMenu';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusScholarly from '@/pages/corpus/CorpusScholarly';
import CorpusProse from '@/pages/corpus/CorpusProse';
import CorpusDoc from '@/pages/corpus/CorpusDoc';

const ITI = 'इति श्रीमार्कण्डेयपुराणे';
const meta = (o: Record<string, unknown>) => JSON.stringify({ status: 'passed', flag: false, accepted: false, ...o });
const prow = (extra: Partial<ProseRow>): ProseRow => ({
  page_no: 626, idx: 1, verse_ref: '81.1', chapter: null, has_sanskrit: true, colophon: false,
  scholar: 'Mārkaṇḍeya said: Sāvarṇi, the son of the Sun, is called the eighth *Manu*. //', meta: meta({}),
  made_at: '2026-10-18T08:00:44+00:00', ...extra,
});

describe('the loaders', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; sb.prose = null; });

  it('ask the two functions of C22', async () => {
    await loadScholarDocs();
    expect(sb.calls[0]).toEqual({ fn: 'corpus_reader_scholar_docs', args: {} });
    await loadScholarProse('MBh01', null);
    expect(sb.calls[1]).toEqual({ fn: 'corpus_reader_scholar_prose', args: { p_doc: 'MBh01', p_after_page: null, p_after_idx: null, p_limit: PROSE_BATCH } });
    await loadScholarProse('MBh01', { page: 3, idx: 7 }, 10);
    expect(sb.calls[2].args).toEqual({ p_doc: 'MBh01', p_after_page: 3, p_after_idx: 7, p_limit: 10 });
    expect(proseHref('a b')).toBe('/corpus/a%20b/prose');
    expect(verseHref('MBh01', 3, 7)).toBe('/corpus/MBh01?at=3.7');
  });
});

describe('the chapters, as the edition makes them', () => {
  it('by the verses\' own references; a heading with the next verse, a colophon with the one before', () => {
    const rows = [
      prow({ idx: 1, verse_ref: null }),                       // a speaker's line, no reference: with 81.1
      prow({ idx: 2, verse_ref: '81.1' }),
      prow({ idx: 3, verse_ref: '81.2' }),
      prow({ idx: 4, verse_ref: null, colophon: true }),       // iti ...: with 81
      prow({ idx: 5, verse_ref: '628.5' }),                    // a page.idx would be its own: a two-part number
      prow({ idx: 6, verse_ref: '82.1' }),
      prow({ idx: 7, verse_ref: null }),                       // nothing after it: with the one before
    ];
    expect(chapterKeys(rows).map((k) => `${k.kind}:${k.value}`)).toEqual([
      'chapter:81', 'chapter:81', 'chapter:81', 'chapter:81', 'chapter:628', 'chapter:82', 'chapter:82',
    ]);
  });

  it('else a numeric chapter, else the page; a chapter that is not a number is never a heading', () => {
    const rows = [
      prow({ page_no: 1, verse_ref: '1.1.8', chapter: '1' }),
      prow({ page_no: 1, idx: 2, verse_ref: '1.1.9', chapter: '1' }),
      prow({ page_no: 2, idx: 1, verse_ref: null, chapter: 'पर्व' }),
      prow({ page_no: 3, idx: 1, verse_ref: null, chapter: null }),
    ];
    expect(chapterKeys(rows).map((k) => `${k.kind}:${k.value}`)).toEqual(['chapter:1', 'chapter:1', 'page:2', 'page:3']);
  });
});

describe('the words of a verse', () => {
  it('a note after its anchor, in italics or not; one whose anchor is not there at the end', () => {
    expect(withNotes('the eighth *Manu* of this age', [{ anchor: '*Manu*', n: 1 }, { anchor: 'nowhere', n: 2 }, { anchor: 'eighth', n: 3 }]))
      .toEqual([
        { text: 'the eighth', em: false }, { note: 3 }, { text: ' ', em: false }, { text: 'Manu', em: true }, { note: 1 },
        { text: ' of this age', em: false }, { note: 2 },
      ]);
    expect(withNotes('Manu', [{ anchor: 'Ma', n: 1 }])).toEqual([{ text: 'Ma', em: false }, { note: 1 }, { text: 'nu', em: false }]);
    expect(verseLabel('81.18–19')).toBe('18–19');
    expect(verseLabel('1.1.15')).toBe('15');
    expect(verseLabel(null)).toBe('');
  });

  it('a sentence whole after its range; speakers begin paragraphs; notes in reading order, the doubt last', () => {
    const rows = [
      prow({ idx: 1, verse_ref: '81.1', scholar: 'Mārkaṇḍeya said: Hear of *Sāvarṇi*. //',
             meta: meta({ notes: [{ anchor: 'Hear', note: 'Listen.' }, { anchor: '*Sāvarṇi*', note: 'The eighth *Manu*.' }] }) }),
      prow({ idx: 2, verse_ref: '81.2', scholar: 'The sentence over two verses.',
             meta: meta({ range: '81.2–3', flag: true, status: 'flagged', doubts: 'The reading may be corrupt.' }) }),
      prow({ idx: 3, verse_ref: '81.3', scholar: null, meta: meta({ with: '81.2–3' }) }),
      prow({ idx: 4, verse_ref: '81.4', scholar: 'Krauṣṭuki said: Tell me more. //' }),
      prow({ idx: 5, verse_ref: '81.5', scholar: '  ', meta: null }),
    ];
    const [c] = proseChapters(rows);
    expect(c.label).toBe('Adhyāya 81');
    expect(c.paragraphs.map((p) => p.map((s) => s.label))).toEqual([['1', '2–3'], ['4']]);
    const [s1, s2] = c.paragraphs[0];
    expect(s1.tokens).toEqual([
      { text: 'Mārkaṇḍeya said: Hear', em: false }, { note: 1 }, { text: ' of ', em: false }, { text: 'Sāvarṇi', em: true },
      { note: 2 }, { text: '.', em: false },
    ]);
    expect(s2.flag).toBe(true);
    expect(s2.tokens[s2.tokens.length - 1]).toEqual({ note: 3 });
    expect(c.notes).toEqual([
      { n: 1, ref: '1', anchor: 'Hear', note: 'Listen.' },
      { n: 2, ref: '1', anchor: 'Sāvarṇi', note: 'The eighth *Manu*.' },
      { n: 3, ref: '2–3', anchor: 'The reading', note: 'The reading may be corrupt.' },
    ]);
  });

  it('eight verses at most to a paragraph; a person\'s reading lifts the mark', () => {
    const rows = Array.from({ length: 10 }, (_, i) => prow({ idx: i + 1, verse_ref: `81.${i + 1}`, scholar: `Verse ${i + 1}. //`,
      meta: meta(i === 0 ? { status: 'flagged', flag: false, accepted: true } : {}) }));
    const [c] = proseChapters(rows);
    expect(c.paragraphs.map((p) => p.length)).toEqual([8, 2]);
    expect(c.paragraphs[0][0].flag).toBe(false);
    expect(proseChapters([])).toEqual([]);
  });
});

const DOC = {
  doc_code: 'markandeya_purana__w_gretil', title: 'Mārkaṇḍeya Purāṇa (GRETIL)', category: 'purana', passages: 5240,
  english: 0, hindi: 0, vectors: 0, stories: 0, published: false, synced_at: '2026-10-25T09:03:00Z',
};
const SDOC = {
  doc_code: 'markandeya_purana__w_gretil', title: 'Mārkaṇḍeya Purāṇa (GRETIL)', category: 'purana', passages: 5240,
  verses: 1408, flagged: 117, accepted: 0, fidelity: 4.62, first_page: 81, first_idx: 2, first_ord: 1210,
  last_made: '2026-10-18T08:00:44+00:00',
};

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/scholarly" element={<CorpusScholarly />} />
            <Route path="/corpus/:docCode/prose" element={<CorpusProse />} />
            <Route path="/corpus/:docCode" element={<CorpusDoc />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe('/corpus/scholarly', () => {
  beforeEach(() => { sb.calls = []; sb.byFn = {}; sb.prose = null; });

  it('lists every text with a scholarly English, with its counts and two ways in', async () => {
    sb.byFn.corpus_reader_scholar_docs = { data: [SDOC], error: null };
    mount('/corpus/scholarly');
    expect(await screen.findByText(/1,408 verses in scholarly English of 5,240 passages \(27%\)/)).toBeTruthy();
    expect(screen.getByText(/117 wait for a person/)).toBeTruthy();
    expect(screen.getByText(/mean fidelity 4\.6 of 5/)).toBeTruthy();
    expect(screen.getByRole('link', { name: /As prose/ }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil/prose');
    expect(screen.getByRole('link', { name: /Verse by verse/ }).getAttribute('href'))
      .toBe('/corpus/markandeya_purana__w_gretil?p=25#p81-2');
    expect(screen.getByText('1 text, 1,408 verses in scholarly English.')).toBeTruthy();
  });

  it('before C22 it says so and points to the editions; a refusal is a refusal', async () => {
    sb.byFn.corpus_reader_scholar_docs = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_scholar_docs without parameters in the schema cache' } };
    const v = mount('/corpus/scholarly');
    expect(await screen.findByText(/is not switched on yet/)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    v.unmount();
    sb.byFn.corpus_reader_scholar_docs = { data: null, error: { code: '42501', message: 'The working corpus is open to signed-in readers only.' } };
    mount('/corpus/scholarly');
    expect(await screen.findByText(/not on the reader list/)).toBeTruthy();
  });
});

describe('/corpus/:docCode/prose', () => {
  beforeEach(() => {
    sb.calls = [];
    sb.prose = null;
    sb.byFn = {
      corpus_reader_docs: { data: [DOC], error: null },
      corpus_reader_scholar_count: { data: [{ verses: 3, flagged: 1 }], error: null },
    };
  });

  it('reads the text as prose: chapters, verse numbers to the reader, notes, the flagged marked', async () => {
    sb.prose = () => ({
      data: [
        prow({ idx: 1, verse_ref: '81.1', meta: meta({ notes: [{ anchor: '*Manu*', note: 'The progenitor.' }] }) }),
        prow({ idx: 2, verse_ref: '81.2', scholar: 'A doubted verse. //', meta: meta({ status: 'flagged', flag: true }) }),
        prow({ page_no: 640, idx: 1, verse_ref: '82.5', scholar: 'The next adhyāya. //' }),
        prow({ page_no: 640, idx: 2, verse_ref: null, colophon: true, scholar: 'Thus ends the eighty-second. //' }),
      ],
      error: null,
    });
    const { container } = mount('/corpus/markandeya_purana__w_gretil/prose');
    expect(await screen.findByRole('heading', { name: 'Adhyāya 81' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Adhyāya 82' })).toBeTruthy();
    expect(screen.getByText(/3 verses/)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'verse by verse, beside the Sanskrit' }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil');
    expect(screen.getByRole('link', { name: '1' }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil?at=626.1');
    expect(screen.getByText('The progenitor.')).toBeTruthy();
    expect(container.querySelector('#ch-1 sup a')?.getAttribute('href')).toBe('#ch-1-n1');
    expect(container.querySelector('[data-flag="true"]')?.textContent).toContain('A doubted verse.');
    expect(container.innerHTML).not.toContain('*Manu*');
    expect(container.textContent).not.toContain('//');
    expect(screen.queryByRole('button', { name: 'Read on' })).toBeNull();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_scholar_prose')?.args)
      .toEqual({ p_doc: 'markandeya_purana__w_gretil', p_after_page: null, p_after_idx: null, p_limit: PROSE_BATCH });
  });

  it('a full batch offers the rest, asked after its last row', async () => {
    const batch = Array.from({ length: PROSE_BATCH }, (_, i) => prow({ idx: i + 1, verse_ref: `81.${i + 1}`, scholar: `Verse ${i + 1}.` }));
    sb.prose = (args) => ({ data: args.p_after_page == null ? batch : [prow({ page_no: 700, idx: 1, verse_ref: '82.1', scholar: 'The last.' })], error: null });
    mount('/corpus/markandeya_purana__w_gretil/prose');
    const more = await screen.findByRole('button', { name: 'Read on' });
    fireEvent.click(more);
    expect(await screen.findByText('The last.')).toBeTruthy();
    const asks = sb.calls.filter((c) => c.fn === 'corpus_reader_scholar_prose');
    expect(asks[1].args).toEqual({ p_doc: 'markandeya_purana__w_gretil', p_after_page: 626, p_after_idx: PROSE_BATCH, p_limit: PROSE_BATCH });
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Read on' })).toBeNull());
  });

  it('before C22 it says so and links the reader', async () => {
    sb.byFn.corpus_reader_scholar_prose = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_scholar_prose(p_after_idx, p_after_page, p_doc, p_limit) in the schema cache' } };
    mount('/corpus/markandeya_purana__w_gretil/prose');
    expect(await screen.findByText(/Reading as prose is not switched on yet/)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'the reader' }).getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil');
  });
});

describe('the ways to it', () => {
  beforeEach(() => {
    sb.calls = [];
    sb.prose = null;
    sb.byFn = {
      corpus_reader_docs: { data: [DOC], error: null },
      corpus_reader_page: { data: [], error: null },
      corpus_reader_scholar_count: { data: [{ verses: 3, flagged: 0 }], error: null },
    };
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  });
  afterEach(() => { try { window.localStorage.clear(); } catch { /* none */ } });

  it('the reader links a text with scholarly English to its prose', async () => {
    mount('/corpus/markandeya_purana__w_gretil');
    const a = await screen.findByRole('link', { name: 'read it as prose' });
    expect(a.getAttribute('href')).toBe('/corpus/markandeya_purana__w_gretil/prose');
  });

  it('the menus, and the tab that is current', () => {
    expect(CORPUS_LINKS.map((l) => l.href)).toContain('/corpus/scholarly');
    const tab = (path: string) => {
      const v = render(<MemoryRouter initialEntries={[path]}><CorpusNav /></MemoryRouter>);
      const cur = v.container.querySelector('[aria-current="page"]')?.textContent?.trim();
      v.unmount();
      return cur;
    };
    expect(tab('/corpus/markandeya_purana__w_gretil/prose')).toBe('Scholarly English');
    expect(tab('/corpus/scholarly')).toBe('Scholarly English');
    expect(tab('/corpus/markandeya_purana__w_gretil')).toBe('Library');
  });

  it('an edition links its own prose page only', () => {
    const base = { slug: 'devimahatmya', title: 'Devīmāhātmya', file: '/scholarly/devimahatmya.html' };
    expect(cleanEditions({ editions: [{ ...base, prose: '/scholarly/devimahatmya-prose.html' }] })[0].prose).toBe('/scholarly/devimahatmya-prose.html');
    expect(cleanEditions({ editions: [{ ...base, prose: 'javascript:alert(1)' }] })[0].prose).toBe('');
    expect(cleanEditions({ editions: [{ ...base, prose: '/scholarly/other-prose.html' }] })[0].prose).toBe('');
    expect(cleanEditions({ editions: [base] })[0].prose).toBe('');
  });
});
