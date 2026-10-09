/**
 * CORPUS_MEDIA_C8_2026_10_09 - the pictures and graphic novels of the working corpus. The pure
 * rules first; then how a picture is fetched (the reader's token in a header, never in a URL;
 * once per tab); then the pages against a mocked supabase whose answers are set per function.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, RpcAnswer>, calls: [] as Call[], session: true }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: { invoke: () => Promise.resolve({ data: { results: [] }, error: null }) },
    auth: {
      getSession: () => Promise.resolve({ data: { session: sb.session ? { access_token: 'jwt-of-reader', user: { id: 'u1' } } : null } }),
    },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false }) }));

import {
  anchorRef, citeParts, forgetPictures, isGenerated, novelHref, novelPictures, parseNovelVerify, parsePlan, pictureUrl,
  PictureError,
} from '@/lib/corpusMedia';
import CorpusImages from '@/pages/corpus/CorpusImages';
import CorpusNovels from '@/pages/corpus/CorpusNovels';
import CorpusStories from '@/pages/corpus/CorpusStories';
import CorpusNav from '@/components/corpus/CorpusNav';

const SHA = (c: string) => c.repeat(64);
const PIC = (key: string, extra: Record<string, unknown> = {}) => ({
  media_key: key, doc_code: 'Mallapurana', doc_title: 'Mallapurāṇa', kind: 'generated', status: 'approved',
  title: 'Types of Wrestling Arenas', caption_en: 'Three arenas: square, triangular, round.', caption_hi: 'तीन अखाड़े',
  context_note: null, anchor_page: 69, anchor_idx: 1, anchor_verse_ref: null, story_id: null, width: 1408, height: 768,
  sha256: SHA('a'), has_thumb: true, has_display: true, model: 'gemini-3.1-flash-image', license: null,
  approved_at_local: '2026-10-04T10:00:00', total: 2, ...extra,
});
const NOVEL = {
  novel_id: 2, doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa', story_id: 36, story_title: "Vitastā's Journey",
  status: 'drawing', title: "The River Goddess Vitastā's Journey", title_hi: 'वितस्ता की यात्रा', audience: 'general', pages: 2,
  cover_sha: SHA('c'), cover_has_thumb: true, approved_at_local: null, updated_at_local: '2026-10-08',
};
const PLAN = {
  title: NOVEL.title, title_hi: NOVEL.title_hi,
  cast: [{ name: 'Devotee', look: 'A devout brahmin' }, { name: 'Devī Vitastā', look: 'A serene goddess' }],
  pages: [
    { n: 2, scene: 'The river runs to the sea.', caption: 'She flowed on to the Sindhu. [25.13]', caption_hi: 'वह सिंधु तक बही। [25.13]',
      speech: [{ who: 'Devotee', line: 'Flow as far as the Sindhu.', cite: '25.9, 25.10' }], cites: ['25.13'] },
    { n: 1, scene: 'A riverbank at dawn.', caption: 'A brahmin prayed to the goddess. [25.7, 25.8]', caption_hi: 'एक ब्राह्मण ने प्रार्थना की। [25.7, 25.8]',
      speech: [{ who: 'Devotee', line: 'O Devī, grant me grace.', cite: '25.8' }], cites: ['25.7', '25.8'] },
  ],
};
const FULL = {
  ...NOVEL, plan: PLAN, verify: { ok: false, problems: ['names not found in the cited passages: Vitastā'], cited: ['25.7', '25.8', '25.13'], pages: 2, checked_at: 'x' },
  cover_seq: 1, model: 'gemini-2.5-flash', image_model: 'gemini-3.1-flash-image', aspect: '3:4',
  media: [
    { key: 'novel:2:page:1', kind: 'novel_page', seq: 1, status: 'draft', title: 'Page 1', sha256: SHA('c'), width: 896, height: 1200, version: 1, has_thumb: true, has_display: true },
    { key: 'novel:2:cast:1', kind: 'novel_cast', seq: 1, status: 'draft', title: 'Devotee', sha256: SHA('d'), width: 800, height: 800, version: 1, has_thumb: true, has_display: true },
  ],
};
const STORY = {
  doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa', story_id: 36, status: 'approved', title: "Vitastā's Journey",
  title_hi: null, why: null, from_page: 25, from_idx: 7, to_page: 26, to_idx: 2, from_ord: 300, story_en: 'The goddess flowed.',
  story_hi: null, quote_sa: 'वितस्ता', quote_ref: '25.7', cites: '["25.7"]', verify: '{"ok": true}', model: 'gemini-2.5-flash',
  approved_at_local: '2026-10-08T09:00:00', updated_at_local: null,
};

const fetchMock = vi.fn();

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
            <Route path="/corpus/images" element={<CorpusImages />} />
            <Route path="/corpus/novels" element={<CorpusNovels />} />
            <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />
            <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />
            <Route path="/corpus/:docCode" element={<p>the reader</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = []; sb.session = true;
  forgetPictures();
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => new Response('jpeg-bytes', { status: 200, headers: { 'Content-Type': 'image/jpeg' } }));
  vi.stubGlobal('fetch', fetchMock);
  let n = 0;
  (URL as any).createObjectURL = vi.fn(() => `blob:picture-${++n}`);
  (URL as any).revokeObjectURL = vi.fn();
});

describe('the rules', () => {
  it('plans are read defensively and in page order', () => {
    const p = parsePlan(JSON.stringify(PLAN));
    expect(p.pages.map((q) => q.n)).toEqual([1, 2]);
    expect(p.pages[0].speech[0]).toEqual({ who: 'Devotee', line: 'O Devī, grant me grace.', cite: '25.8' });
    expect(p.cast.map((c) => c.name)).toEqual(['Devotee', 'Devī Vitastā']);
    expect(parsePlan('not json')).toEqual({ title: null, title_hi: null, cast: [], pages: [] });
    expect(parsePlan({ pages: [{ n: 'x' }, { n: 3, cites: ['3.1', 'drop table', 7] }] }).pages).toEqual([
      { n: 3, scene: null, caption: null, caption_hi: null, speech: [], cites: ['3.1'] },
    ]);
    expect(parseNovelVerify(null).ok).toBeNull();
    expect(parseNovelVerify(FULL.verify).cited).toEqual(['25.7', '25.8', '25.13']);
  });

  it('citations in captions, anchors, kinds and links', () => {
    expect(citeParts('A prayer. [25.7, 25.8] Then [x] more')).toEqual([
      { text: 'A prayer. ', refs: [] }, { text: '', refs: ['25.7', '25.8'] }, { text: ' Then [x] more', refs: [] },
    ]);
    expect(anchorRef({ anchor_page: 69, anchor_idx: 1 })).toBe('69.1');
    expect(anchorRef({ anchor_page: 0, anchor_idx: 0 })).toBeNull();   // a cover has no passage
    expect(isGenerated('cover')).toBe(true);
    expect(isGenerated('edition-plate')).toBe(false);
    expect(novelHref(2, 3)).toBe('/corpus/novels/2#page-3');
    const { pages, cast } = novelPictures(FULL.media);
    expect([...pages.keys()]).toEqual([1]);
    expect(cast.get(1)?.title).toBe('Devotee');
  });
});

describe('a picture', () => {
  it('is fetched with the token in a header, once per tab', async () => {
    const u = await pictureUrl(SHA('a'), 'thumb');
    expect(u).toBe('blob:picture-1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/functions\/v1\/corpus-media\?sha=a{64}&r=thumb$/);
    expect(String(url)).not.toContain('jwt');
    expect(init.headers.Authorization).toBe('Bearer jwt-of-reader');
    expect(await pictureUrl(SHA('a'), 'thumb')).toBe('blob:picture-1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await pictureUrl(SHA('a'), 'display');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('says why it cannot be shown, and is asked again next time', async () => {
    fetchMock.mockImplementationOnce(async () => new Response('no', { status: 404 }));
    await expect(pictureUrl(SHA('b'))).rejects.toMatchObject({ status: 404 });
    await expect(pictureUrl(SHA('b'))).resolves.toMatch(/^blob:/);
    await expect(pictureUrl('nothex')).rejects.toBeInstanceOf(PictureError);
    sb.session = false;
    await expect(pictureUrl(SHA('e'))).rejects.toMatchObject({ status: 401 });
  });
});

describe('/corpus/images', () => {
  it('the pictures, their passages, the draft mark, and one opened by its link', async () => {
    sb.byFn.corpus_reader_media = { data: [PIC('img:3'), PIC('img:4', { status: 'draft', title: 'Stances', anchor_page: 73, anchor_idx: 10, sha256: SHA('b') })], error: null };
    mount('/corpus/images');
    expect(await screen.findByText('Types of Wrestling Arenas')).toBeInTheDocument();
    expect(screen.getByText('draft')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '69.1' })).toHaveAttribute('href', '/corpus/Mallapurana?at=69.1');
    fireEvent.click(screen.getByText('Stances'));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/corpus/images?pic=img%3A4'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/read the passage 73.10/)).toBeInTheDocument();
    expect(within(dialog).getByText(/generated, not a historical source/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: /Previous/ }));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/corpus/images?pic=img%3A3'));
    expect(await within(await screen.findByRole('dialog')).findByText('तीन अखाड़े')).toBeInTheDocument();
  });

  it('LOAD_L1_2026_10_09: all texts are asked once; a text is asked for itself', async () => {
    sb.byFn.corpus_reader_media = { data: [PIC('img:3'), PIC('img:5', { doc_code: 'nilamata_seg', doc_title: 'Nīlamata Purāṇa', title: 'Vitastā', sha256: SHA('e') })], error: null };
    mount('/corpus/images');
    expect(await screen.findByText('Types of Wrestling Arenas')).toBeInTheDocument();
    expect(screen.getByText('Vitastā')).toBeInTheDocument();
    expect(sb.calls.filter((c) => c.fn === 'corpus_reader_media').map((c) => c.args)).toEqual([
      expect.objectContaining({ k: 200 }),
    ]);
    fireEvent.click(screen.getByRole('button', { name: /Nīlamata Purāṇa/ }));
    await waitFor(() => expect(sb.calls.filter((c) => c.fn === 'corpus_reader_media').length).toBe(2));
    expect(sb.calls.filter((c) => c.fn === 'corpus_reader_media')[1].args).toMatchObject({ p_doc: 'nilamata_seg', k: 60 });
  });

  it('without C8 it says so quietly; a refusal is a refusal', async () => {
    sb.byFn.corpus_reader_media = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_media(k, p_doc, p_offset, p_story) in the schema cache' } };
    const { unmount } = mount('/corpus/images');
    expect(await screen.findByText(/The pictures are not available here yet/)).toBeInTheDocument();
    unmount();
    sb.byFn.corpus_reader_media = { data: null, error: { code: '42501', message: 'The working corpus is open to signed-in readers only.' } };
    mount('/corpus/images');
    expect(await screen.findByText(/not on the reader list/)).toBeInTheDocument();
  });
});

describe('/corpus/novels', () => {
  it('the list marks a novel still being drawn', async () => {
    sb.byFn.corpus_reader_novels = { data: [NOVEL], error: null };
    mount('/corpus/novels');
    expect(await screen.findByRole('link', { name: NOVEL.title })).toHaveAttribute('href', '/corpus/novels/2');
    expect(screen.getByText('being drawn')).toBeInTheDocument();
    expect(screen.getByText(/from the story/)).toHaveAttribute('href', '/corpus/stories/nilamata_seg/36');
  });

  it('a novel: pages in order, citations as links, speech with its verse, Hindi on its own', async () => {
    sb.byFn.corpus_reader_novel = { data: [FULL], error: null };
    mount('/corpus/novels/2');
    expect(await screen.findByRole('heading', { level: 1, name: NOVEL.title })).toBeInTheDocument();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_novel')?.args).toEqual({ p_id: 2 });
    const p1 = screen.getByRole('region', { name: 'Page 1' });
    expect(within(p1).getAllByRole('link', { name: '25.8' })[0]).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.8');
    expect(within(p1).getByText(/O Devī, grant me grace/)).toBeInTheDocument();
    expect(within(p1).getAllByRole('link', { name: '25.8' })).toHaveLength(3);   // the English caption's, the line's, the Hindi caption's
    expect(within(p1).getByText('draft')).toBeInTheDocument();
    const p2 = screen.getByRole('region', { name: 'Page 2' });
    expect(within(p2).getByText('Picture to come')).toBeInTheDocument();   // no picture for page 2 yet
    expect(within(p2).getByRole('link', { name: '25.10' })).toHaveAttribute('href', '/corpus/nilamata_seg?at=25.10');
    expect(screen.getByText(/names not found in the cited passages/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'The cast' })).toHaveTextContent('Devī Vitastā');
    fireEvent.click(screen.getByRole('button', { name: 'Hindi' }));
    expect(screen.queryByText(/A brahmin prayed to the goddess/)).toBeNull();
    expect(screen.getByText(/एक ब्राह्मण ने प्रार्थना की।/)).toBeInTheDocument();
  });

  it('a novel the reader may not see is not found', async () => {
    sb.byFn.corpus_reader_novel = { data: [], error: null };
    mount('/corpus/novels/9');
    expect(await screen.findByText('Graphic novel not found')).toBeInTheDocument();
  });
});

describe('a story with its picture and its novel', () => {
  it('heads the story, and links to the novel', async () => {
    sb.byFn.corpus_reader_stories = { data: [STORY], error: null };
    sb.byFn.corpus_reader_media = { data: [PIC('img:103', { doc_code: 'nilamata_seg', story_id: 36, caption_en: "Vitastā's swift journey" })], error: null };
    sb.byFn.corpus_reader_novels = { data: [NOVEL], error: null };
    mount('/corpus/stories/nilamata_seg/36');
    expect(await screen.findByText("Vitastā's swift journey")).toBeInTheDocument();
    expect(sb.calls.find((c) => c.fn === 'corpus_reader_media')?.args).toMatchObject({ p_doc: 'nilamata_seg', p_story: 36 });
    expect(screen.getByRole('link', { name: /Read it as a graphic novel/ })).toHaveAttribute('href', '/corpus/novels/2');
  });

  it('without C8 the story reads as before', async () => {
    sb.byFn.corpus_reader_stories = { data: [STORY], error: null };
    sb.byFn.corpus_reader_media = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_media' } };
    sb.byFn.corpus_reader_novels = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_reader_novels' } };
    mount('/corpus/stories/nilamata_seg/36');
    expect(await screen.findByText('The goddess flowed.')).toBeInTheDocument();
    expect(screen.queryByText(/graphic novel/)).toBeNull();
    expect(screen.queryByText(/could not be loaded/)).toBeNull();
  });
});

describe('the corpus tabs', () => {
  it('Pictures and Graphic novels have their own tab; the Library tab is not lit on them', () => {
    for (const [path, on] of [['/corpus/images', 'Pictures'], ['/corpus/novels/2', 'Graphic novels'], ['/corpus/markandeya_purana', 'Library']] as const) {
      const { unmount } = render(<MemoryRouter initialEntries={[path]}><CorpusNav /></MemoryRouter>);
      const lit = screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent?.trim());
      expect(lit).toEqual([on]);
      unmount();
    }
  });
});
