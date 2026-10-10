import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// LOAD_L2_2026_10_09 - keep the first visit small: the home page no longer downloads the 548 kB
// cultural-terms dataset to look up a word that is not in it, and the two toast hosts load right after
// the first render instead of in the entry bundle.
const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, '../..');
const read = (p: string) => readFileSync(resolve(ROOT, p), 'utf-8');
const app = read('src/App.tsx');
const geo = read('src/components/home/GeomythologySection.tsx');

describe('first download (L2)', () => {
  it('the home sections do not mount the terms tooltip for a word that is not in the dataset', () => {
    expect(geo).not.toMatch(/^import \{ CulturalTermTooltip \}/m);
    expect(geo).not.toMatch(/<CulturalTermTooltip term="samudra">/);
    expect(geo).toMatch(/<span>samudra<\/span>/);
  });

  it('"samudra" is still not a term of the dataset (wrap it again if it ever is)', () => {
    const dir = 'src/data/articles';
    const files = readdirSync(resolve(ROOT, dir)).filter((f) => /cultural-terms.*\.ts$/.test(f));
    expect(files.length).toBeGreaterThan(1);
    for (const f of files) expect(read(`${dir}/${f}`)).not.toMatch(/\bsamudra\b/i);
  });

  it('the toast hosts are loaded lazily, inside a Suspense', () => {
    expect(app).not.toMatch(/^import \{ Toaster \} from "@\/components\/ui\/toaster";/m);
    expect(app).not.toMatch(/^import \{ Toaster as Sonner \}/m);
    expect(app).toMatch(/const Toaster = lazy\(/);
    expect(app).toMatch(/const Sonner = lazy\(/);
    expect(app).toMatch(/<Suspense fallback=\{null\}>\s*<Toaster \/>\s*<Sonner \/>\s*<\/Suspense>/);
  });
});
