import { describe, it, expect, vi, beforeEach } from 'vitest';

// SEARCH_TEXTS_C3A_2026_10_07 - the search client keeps "failed" distinct from "nothing found",
// and links each hit to the reader page that holds it.
const state: { res: any; calls: any[] } = { res: null, calls: [] };

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    functions: {
      invoke: (name: string, opts: any) => { state.calls.push({ name, opts }); return Promise.resolve(state.res); },
    },
  },
}));

import { readerHref, searchTexts } from '@/lib/corpusSearch';

beforeEach(() => { state.res = { data: { results: [] }, error: null }; state.calls = []; });

describe('searchTexts', () => {
  it('nothing found is ok:true with no rows', async () => {
    const r = await searchTexts('why did the king sell his wife');
    expect(r).toEqual({ ok: true, rows: [], error: null });
    expect(state.calls[0].name).toBe('search-texts');
    expect(state.calls[0].opts.body).toEqual({ q: 'why did the king sell his wife', k: 10 });
  });

  it('a failure is ok:false with the server message, never an empty list', async () => {
    state.res = { data: null, error: { message: 'non-2xx', context: { json: () => Promise.resolve({ error: 'Too many searches in a minute.' }) } } };
    const r = await searchTexts('dharma');
    expect(r.ok).toBe(false);
    expect(r.error).toBe('Too many searches in a minute.');
  });

  it('an unexpected answer is a failure too', async () => {
    state.res = { data: { nope: 1 }, error: null };
    expect((await searchTexts('dharma')).ok).toBe(false);
  });

  it('refuses a too-short question without calling the server, and passes doc codes', async () => {
    expect((await searchTexts('  a ')).ok).toBe(false);
    expect(state.calls.length).toBe(0);
    await searchTexts('dharma', { docCodes: ['markandeya_purana'], k: 5 });
    expect(state.calls[0].opts.body).toEqual({ q: 'dharma', k: 5, doc_codes: ['markandeya_purana'] });
  });
});

describe('readerHref', () => {
  it('page 1 has no ?p, later pages do, the anchor is the passage', () => {
    expect(readerHref({ doc_code: 'markandeya_purana', page_no: 1, idx: 4, ordinal: 4 })).toBe('/texts/markandeya_purana#p1-4');
    expect(readerHref({ doc_code: 'markandeya_purana', page_no: 60, idx: 10, ordinal: 1001 })).toBe('/texts/markandeya_purana?p=21#p60-10');
    expect(readerHref({ doc_code: 'markandeya_purana', page_no: 60, idx: 10, ordinal: 1000 })).toBe('/texts/markandeya_purana?p=20#p60-10');
  });
  it('without a position it still opens the text', () => {
    expect(readerHref({ doc_code: 'a b', page_no: 2, idx: 3, ordinal: null })).toBe('/texts/a%20b#p2-3');
  });
});
