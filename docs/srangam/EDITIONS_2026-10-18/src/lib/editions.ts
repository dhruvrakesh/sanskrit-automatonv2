/**
 * The scholarly editions - EDITIONS_SITE_2026_10_18.
 *
 * The automaton's scripts/publish_editions.py writes each edition as a static page, public/scholarly/<slug>.html,
 * and their list, public/scholarly/index.json, which /editions reads here. No database and no sign-in: the files
 * are served as they are. A missing index (or the site's own page answering for it) means no edition is published
 * yet; any other failure is a failure, never "none".
 */

export const EDITIONS_INDEX = '/scholarly/index.json';

export interface EditionSource {
  name?: string;
  url?: string;
  credit?: string;
  licence?: string;
  licence_url?: string;
  note?: string;
}

export interface EditionLicence {
  name?: string;
  url?: string;
  note?: string;
}

export interface Edition {
  slug: string;
  title: string;
  subtitle: string;
  file: string;
  verses: number;
  passed: number;
  flagged: number;
  engines: string;
  judge: string;
  source: EditionSource;
  licence: EditionLicence;
  bytes: number;
  made_at: string;
}

export type EditionsResult = { ok: true; editions: Edition[] } | { ok: false; error: string };

const SLUG = /^[a-z0-9][a-z0-9-]{1,59}$/;
const FILE = /^\/scholarly\/[a-z0-9][a-z0-9-]{1,59}\.html$/;
const HTTPS = /^https:\/\/[^\s"'<>]+$/;

const str = (v: unknown, max = 400): string => (typeof v === 'string' ? v.slice(0, max) : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : 0);
const url = (v: unknown): string => (typeof v === 'string' && HTTPS.test(v) ? v : '');

/** The index's editions that are well formed: a safe slug and file, numbers that are numbers, https links only. */
export function cleanEditions(raw: unknown): Edition[] {
  const list = (raw && typeof raw === 'object' && Array.isArray((raw as { editions?: unknown }).editions))
    ? (raw as { editions: unknown[] }).editions : [];
  const out: Edition[] = [];
  for (const x of list) {
    if (!x || typeof x !== 'object') continue;
    const e = x as Record<string, unknown>;
    const slug = str(e.slug, 60);
    const file = str(e.file, 100);
    if (!SLUG.test(slug) || !FILE.test(file) || file !== `/scholarly/${slug}.html` || !str(e.title)) continue;
    const s = (e.source && typeof e.source === 'object' ? e.source : {}) as Record<string, unknown>;
    const l = (e.licence && typeof e.licence === 'object' ? e.licence : {}) as Record<string, unknown>;
    out.push({
      slug, file, title: str(e.title, 200), subtitle: str(e.subtitle, 300),
      verses: num(e.verses), passed: num(e.passed), flagged: num(e.flagged),
      engines: str(e.engines, 200), judge: str(e.judge, 200),
      source: {
        name: str(s.name), url: url(s.url), credit: str(s.credit), licence: str(s.licence, 80),
        licence_url: url(s.licence_url), note: str(s.note),
      },
      licence: { name: str(l.name, 80), url: url(l.url), note: str(l.note) },
      bytes: num(e.bytes), made_at: str(e.made_at, 40),
    });
  }
  return out;
}

/** The published editions, from public/scholarly/index.json. */
export async function loadEditions(fetchImpl: typeof fetch = fetch): Promise<EditionsResult> {
  try {
    const r = await fetchImpl(EDITIONS_INDEX, { cache: 'no-cache' });
    if (r.status === 404) return { ok: true, editions: [] };
    if (!r.ok) return { ok: false, error: `the index answered ${r.status}` };
    const text = await r.text();
    let j: unknown;
    try {
      j = JSON.parse(text);
    } catch {
      // The site answers a path it does not have with its own page: no index yet.
      if (text.trimStart().startsWith('<')) return { ok: true, editions: [] };
      return { ok: false, error: 'the index is not JSON' };
    }
    return { ok: true, editions: cleanEditions(j) };
  } catch (e) {
    return { ok: false, error: String((e as Error)?.message ?? e) };
  }
}

/** "0.9 MB". */
export function megabytes(bytes: number): string {
  return `${(bytes / 1e6).toFixed(1)} MB`;
}

/** "18 Oct 2026", or '' for a date that is not one. */
export function madeOn(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}
