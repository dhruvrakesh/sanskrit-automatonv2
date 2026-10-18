/**
 * EDITIONS_SITE_2026_10_18 - /editions lists the scholarly editions from public/scholarly/index.json (written by the
 * automaton's publish_editions.py): each with its counts, its credits and licence, and a link to its static page; no
 * index yet (404, or the site's own page answering for it) is "none yet"; any other failure is shown as a failure;
 * an entry with an unsafe file or link is dropped.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

import Editions from '@/pages/Editions';
import { cleanEditions, loadEditions, EDITIONS_INDEX } from '@/lib/editions';

const DEVI = {
  slug: 'devimahatmya', title: 'Devīmāhātmya', subtitle: 'Mārkaṇḍeya Purāṇa, adhyāyas 81 to 93',
  file: '/scholarly/devimahatmya.html', verses: 669, passed: 632, flagged: 37, engines: 'Claude Sonnet 5.5',
  judge: 'Gemini 2.5 Flash', bytes: 1042521, made_at: '2026-10-18T12:00:00+00:00',
  source: { name: 'Mārkaṇḍeyapurāṇa 1-93, GRETIL', url: 'https://gretil.sub.uni-goettingen.de/x.htm',
            credit: 'data entry by members of the Sansknet Project', licence: 'CC BY-NC-SA 4.0',
            licence_url: 'https://creativecommons.org/licenses/by-nc-sa/4.0/' },
  licence: { name: 'CC BY-NC-SA 4.0', url: 'https://creativecommons.org/licenses/by-nc-sa/4.0/' },
};

type Answer = { ok: boolean; status: number; text: () => Promise<string> };
const answer = (status: number, body: string): Answer => ({ ok: status >= 200 && status < 300, status, text: () => Promise.resolve(body) });

function page(fetchImpl: () => Promise<Answer>) {
  vi.stubGlobal('fetch', vi.fn(fetchImpl));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter><Editions /></MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

afterEach(() => { vi.unstubAllGlobals(); });

describe('the editions page', () => {
  it('lists an edition with its counts, its credits and a link to its page', async () => {
    page(() => Promise.resolve(answer(200, JSON.stringify({ editions: [DEVI] }))));
    const read = await screen.findByText('Read the edition');
    expect(read.getAttribute('href')).toBe('/scholarly/devimahatmya.html');
    expect(screen.getByText('669 verses in scholarly English')).toBeTruthy();
    expect(screen.getByText('632 passed the judge')).toBeTruthy();
    expect(screen.getByText(/37 marked/)).toBeTruthy();
    expect(screen.getByText('Mārkaṇḍeyapurāṇa 1-93, GRETIL').getAttribute('href'))
      .toBe('https://gretil.sub.uni-goettingen.de/x.htm');
    expect(screen.getAllByText('CC BY-NC-SA 4.0').length).toBe(2);
    expect(screen.getByText(/1\.0 MB/)).toBeTruthy();
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(EDITIONS_INDEX);
  });

  it('no index yet is "none yet", whether a 404 or the site answering with its own page', async () => {
    page(() => Promise.resolve(answer(404, '')));
    expect(await screen.findByText('No edition is published yet.')).toBeTruthy();
    expect(await loadEditions((() => Promise.resolve(answer(200, '<!doctype html><html></html>'))) as unknown as typeof fetch))
      .toEqual({ ok: true, editions: [] });
  });

  it('a failure is shown as a failure, not as none', async () => {
    page(() => Promise.reject(new Error('offline')));
    expect(await screen.findByText('The editions could not be loaded.')).toBeTruthy();
    expect(screen.getByText('offline')).toBeTruthy();
    expect(await loadEditions((() => Promise.resolve(answer(500, 'x'))) as unknown as typeof fetch))
      .toEqual({ ok: false, error: 'the index answered 500' });
  });
});

describe('cleanEditions', () => {
  it('keeps a well-formed entry and drops an unsafe one', () => {
    const bad = [
      { ...DEVI, slug: 'other', file: '/scholarly/devimahatmya.html' },
      { ...DEVI, slug: 'evil', file: 'javascript:alert(1)' },
      { ...DEVI, slug: 'Bad Slug', file: '/scholarly/Bad Slug.html' },
      { ...DEVI, slug: 'notitle', file: '/scholarly/notitle.html', title: '' },
    ];
    const out = cleanEditions({ editions: [DEVI, ...bad, null, 3] });
    expect(out.map((e) => e.slug)).toEqual(['devimahatmya']);
    const http = cleanEditions({ editions: [{ ...DEVI, source: { ...DEVI.source, url: 'http://x.org' } }] });
    expect(http[0].source.url).toBe('');
    expect(cleanEditions(null)).toEqual([]);
  });
});
