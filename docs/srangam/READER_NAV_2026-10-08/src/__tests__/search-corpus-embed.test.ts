/**
 * READER_NAV_2026_10_08 - search-corpus deploys from its own folder, so it carries a copy of the
 * search-texts embedding helpers (supabase/functions/search-corpus/embed.ts). A question must be
 * embedded exactly as search-texts embeds it, so the copy must stay verbatim: this fails if it drifts.
 */
import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const FN = resolve(__dirname, '../../supabase/functions');
const read = (f: string) => readFileSync(resolve(FN, f), 'utf-8').replace(/\r\n/g, '\n');

describe('search-corpus embed.ts', () => {
  it('is a verbatim copy of the search-texts helpers', () => {
    const lib = read('search-texts/lib.ts');
    const copy = read('search-corpus/embed.ts');
    const at = (src: string, re: RegExp) => src.search(re);
    const a = at(lib, /^export const EMBED_MODEL/m);
    const b = at(lib, /^export interface MatchRow/m);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    expect(copy.slice(at(copy, /^export const EMBED_MODEL/m)).trimEnd()).toBe(lib.slice(a, b).trimEnd());
  });

  it('search-corpus imports nothing from another function folder', () => {
    for (const f of readdirSync(resolve(FN, 'search-corpus')).filter((x) => x.endsWith('.ts'))) {
      const src = read(`search-corpus/${f}`);
      const imports = src.split('\n').filter((l) => /^\s*import\b|\bfrom\s+['"]/.test(l));
      for (const l of imports) expect(l, `${f}: ${l}`).not.toMatch(/from\s+['"]\.\.\//);
    }
  });
});
