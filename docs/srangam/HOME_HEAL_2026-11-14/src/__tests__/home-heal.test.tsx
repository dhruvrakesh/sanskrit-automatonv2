import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CorpusStartSection, { START_DOORS } from '@/components/home/CorpusStartSection';

// HOME_HEAL_2026_11_14: the home page's links all lead somewhere; "Start here" names the texts in plain words.
const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, '../..');
const read = (p: string) => readFileSync(resolve(ROOT, p), 'utf-8');
const app = read('src/App.tsx');
const geo = read('src/components/home/GeomythologySection.tsx');
const home = read('src/pages/Home.tsx');
const meta = read('src/data/articles/meta.ts');
const routes = new Set([...app.matchAll(/<Route path="([^"]+)"/g)].map((m) => m[1]));
const isRoute = (p: string) =>
  routes.has(p) || [...routes].some((r) => r.endsWith('/*') && (p === r.slice(0, -2) || p.startsWith(r.slice(0, -1))));

describe('the home page heals (HOME_HEAL)', () => {
  it('every Geomythology card opens an article that exists', () => {
    const paths = [...geo.matchAll(/^\s+path: '([^']+)',/gm)].map((m) => m[1]);
    expect(paths).toHaveLength(4);
    for (const p of paths) {
      expect(p.startsWith('/articles/')).toBe(true);
      expect(meta).toContain(`"${p.slice('/articles/'.length)}": {`);
    }
    expect(paths).not.toContain('/sacred-ecology');
    expect(paths).toContain('/articles/sacred-tree-harvest-rhythms');
  });

  it('the old /sacred-ecology link is sent to the series', () => {
    expect(app).toContain('<Route path="/sacred-ecology" element={<Navigate to="/articles/sacred-tree-harvest-rhythms" replace />} />');
  });

  it('every link written on the home page is a route', () => {
    const own = [...home.matchAll(/(?:to|path)[=:] ?["']((?:\/[a-z0-9-]+)+)["']/g)].map((m) => m[1]);
    expect(own.length).toBeGreaterThan(10);
    for (const p of own) expect(isRoute(p), p).toBe(true);
  });

  it('every door of "Start here" is a route', () => {
    expect(START_DOORS.length).toBe(7);
    for (const d of START_DOORS) expect(isRoute(d.to), d.to).toBe(true);
    expect(START_DOORS.filter((d) => d.open).map((d) => d.to)).toEqual(['/texts', '/editions']);
  });

  it('"Start here" is lazy, before the featured articles', () => {
    expect(home).toMatch(/const CorpusStartSection = lazy\(\(\) => import\("@\/components\/home\/CorpusStartSection"\)\);/);
    expect(home.indexOf('<CorpusStartSection />')).toBeGreaterThan(0);
    expect(home.indexOf('<CorpusStartSection />')).toBeLessThan(home.indexOf('{/* Featured Articles - Enhanced Browsing */}'));
  });

  it('it renders the doors and says which need an invitation', () => {
    render(<MemoryRouter><CorpusStartSection /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'Start here: the texts themselves' })).toBeTruthy();
    expect(screen.getAllByText('Open to all')).toHaveLength(2);
    expect(screen.getAllByText('For invited readers')).toHaveLength(5);
    const link = screen.getByRole('link', { name: /Follow a line of kings/ });
    expect(link.getAttribute('href')).toBe('/corpus/genealogies/dynasties');
  });
});
