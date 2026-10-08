/**
 * The library over the working corpus - CORPUS_LIBRARY_C6_2026_10_08.
 *
 * Shelves (src/data/corpusShelf.json, written by the automaton's scripts/emit_corpus_shelf.py from
 * the same configs/collections.json the dashboard's Shelf page uses), each text's pipeline
 * progress, its stories, and the names index - read through the C6 database functions, which
 * check the reader first (docs/cloud/C6_corpus_library_2026-10-08.sql in the automaton repo).
 *
 * Same contract as corpusMirror.ts: check `ok` first; `refused` is not a failure; a function the
 * database does not have yet (C6 not applied) is `missing`, and the pages then leave that part out.
 */
import shelfFile from '@/data/corpusShelf.json';
import { displayTitle, PASSAGES_PER_PAGE } from '@/lib/corpusDisplay';
import { callMirror, functionMissing, type MirrorDoc, type MirrorResult } from '@/lib/corpusMirror';

// ---- shelves --------------------------------------------------------------------------------

export interface ShelfCollection { key: string; title: string; title_sa: string; order: number; members: string[] }
export interface ShelfBook { derived_title: string; series: { title: string; number: number | null } | null }
export interface ShelfFile { collections: ShelfCollection[]; books: Record<string, ShelfBook> }

export const SHELF: ShelfFile = shelfFile as unknown as ShelfFile;

export interface ShelfSection<T> { key: string; title: string; title_sa: string; order: number; books: T[] }

/** The texts on their shelves, in shelf order; a text on no shelf goes to "Other texts". Empty
 *  shelves are left out. Within a shelf the shelf file's order is kept (series stay in sequence). */
export function shelve<T extends { doc_code: string }>(docs: T[], shelf: ShelfFile = SHELF): ShelfSection<T>[] {
  const byCode = new Map(docs.map((d) => [d.doc_code, d]));
  const placed = new Set<string>();
  const out: ShelfSection<T>[] = [];
  let other: ShelfSection<T> | null = null;
  for (const c of [...shelf.collections].sort((a, b) => a.order - b.order)) {
    const books = c.members.map((m) => byCode.get(m)).filter((d): d is T => !!d);
    books.forEach((b) => placed.add(b.doc_code));
    const sec = { key: c.key, title: c.title, title_sa: c.title_sa, order: c.order, books };
    if (c.key === 'other') other = sec;
    else if (books.length) out.push(sec);
  }
  const rest = docs.filter((d) => !placed.has(d.doc_code));
  if (rest.length) {
    const sec = other ?? { key: 'other', title: 'Other texts', title_sa: '', order: 999, books: [] };
    out.push({ ...sec, books: [...sec.books, ...rest] });
  }
  return out;
}

/** The title to show: a confirmed one (it reaches the mirror from doc_titles.json), else the one
 *  the desk derives from the code, marked as derived. */
export function bookTitle(doc: { doc_code: string; title?: string | null }, shelf: ShelfFile = SHELF): { title: string; derived: boolean } {
  const t = (doc.title ?? '').trim();
  if (t && t !== doc.doc_code) return { title: t, derived: false };
  const d = shelf.books[doc.doc_code]?.derived_title;
  return { title: d || displayTitle(null, doc.doc_code), derived: true };
}

export function seriesLabel(code: string, shelf: ShelfFile = SHELF): string | null {
  const s = shelf.books[code]?.series;
  if (!s) return null;
  return s.number != null ? `${s.title} · ${s.number}` : s.title;
}

// ---- pipeline progress ----------------------------------------------------------------------

export interface StageRow { doc_code: string; stage: string; status: string | null; reason: string | null; updated_at_local: string | null }

export const STAGE_LABELS: Record<string, string> = {
  ingest: 'Ingest', ocr: 'OCR', segment: 'Verses', classify: 'Kinds', iast: 'IAST', translate_en: 'English',
  translate_hi: 'Hindi', qa: 'Checks', entities: 'Names', embed: 'Meaning index', morph: 'Grammar',
  export: 'Exports', book: 'Book',
};

export interface StageSummary { done: number; total: number; degraded: number; blocked: number; pending: number }

export function stageSummary(rows: StageRow[]): StageSummary {
  const s = { done: 0, total: rows.length, degraded: 0, blocked: 0, pending: 0 };
  for (const r of rows) {
    if (r.status === 'done') s.done += 1;
    else if (r.status === 'degraded') s.degraded += 1;
    else if (r.status === 'blocked') s.blocked += 1;
    else s.pending += 1;
  }
  return s;
}

/** Rows that look like stage rows, grouped by text (anything else in the answer is ignored). */
export function stagesByDoc(rows: unknown[]): Map<string, StageRow[]> {
  const m = new Map<string, StageRow[]>();
  for (const x of rows) {
    const r = x as StageRow;
    if (!r || typeof r.doc_code !== 'string' || typeof r.stage !== 'string') continue;
    m.set(r.doc_code, [...(m.get(r.doc_code) ?? []), r]);
  }
  return m;
}

// ---- stories --------------------------------------------------------------------------------

export interface StoryRow {
  doc_code: string; doc_title: string; story_id: number; status: string | null; title: string | null;
  title_hi: string | null; why: string | null; from_page: number | null; from_idx: number | null;
  to_page: number | null; to_idx: number | null; from_ord: number | null; story_en: string | null;
  story_hi: string | null; quote_sa: string | null; quote_ref: string | null; cites: string | null;
  verify: string | null; model: string | null; approved_at_local: string | null; updated_at_local: string | null;
}

export function isStory(x: unknown): x is StoryRow {
  const r = x as StoryRow;
  return !!r && typeof r.doc_code === 'string' && typeof r.story_id === 'number';
}

/** The passages a story cites ("10.8"), from its JSON list; anything else is ignored. */
export function parseCites(cites: string | null | undefined): string[] {
  if (!cites) return [];
  try {
    const v = JSON.parse(cites);
    return Array.isArray(v) ? v.filter((c): c is string => typeof c === 'string' && /^\d+\.\d+$/.test(c)).slice(0, 200) : [];
  } catch {
    return [];
  }
}

export interface VerifySummary { ok: boolean | null; problems: string[]; words: number | null; checked_at: string | null }

export function parseVerify(verify: string | null | undefined): VerifySummary {
  const none = { ok: null, problems: [], words: null, checked_at: null };
  if (!verify) return none;
  try {
    const v = JSON.parse(verify) as Record<string, unknown>;
    return {
      ok: typeof v.ok === 'boolean' ? v.ok : null,
      problems: Array.isArray(v.problems) ? v.problems.map(String).slice(0, 20) : [],
      words: typeof v.words === 'number' ? v.words : null,
      checked_at: typeof v.checked_at === 'string' ? v.checked_at : null,
    };
  } catch {
    return none;
  }
}

export function storyHref(s: { doc_code: string; story_id: number }): string {
  return `/corpus/stories/${encodeURIComponent(s.doc_code)}/${s.story_id}`;
}

/** A link to a passage by its margin reference ("10.8" = scan page 10, passage 8); the reader
 *  finds the right page (?at=). */
export function atHref(docCode: string, ref: string): string {
  return `/corpus/${encodeURIComponent(docCode)}?at=${encodeURIComponent(ref)}`;
}

export function fromHref(s: Pick<StoryRow, 'doc_code' | 'from_page' | 'from_idx' | 'from_ord'>): string {
  const base = `/corpus/${encodeURIComponent(s.doc_code)}`;
  if (s.from_page == null || s.from_idx == null) return base;
  const anchor = `#p${s.from_page}-${s.from_idx}`;
  if (!s.from_ord || s.from_ord < 1) return atHref(s.doc_code, `${s.from_page}.${s.from_idx}`);
  const p = Math.ceil(s.from_ord / PASSAGES_PER_PAGE);
  return (p > 1 ? `${base}?p=${p}` : base) + anchor;
}

/** "18.2" -> { page: 18, idx: 2 }, or null. */
export function parseAt(v: string | null | undefined): { page: number; idx: number } | null {
  const m = /^(\d{1,6})\.(\d{1,6})$/.exec((v ?? '').trim());
  return m ? { page: Number(m[1]), idx: Number(m[2]) } : null;
}

// ---- names ----------------------------------------------------------------------------------

export interface NameRow { canonical: string; kind: string | null; notes: string | null; variants: string[] | null; mentions: number; texts: number; total: number }
export interface NameHit { doc_code: string; title: string; page_no: number; idx: number; verse_ref: string | null; ord: number | null; surface: string | null; snippet: string | null; total: number }
export interface PageName { page_no: number; idx: number; canonical: string; surface: string | null; kind: string | null; notes: string | null }

export const NAME_KINDS = ['person', 'deity', 'place', 'people', 'river', 'mountain', 'other'] as const;
export const KIND_LABELS: Record<string, string> = {
  person: 'People', deity: 'Deities', place: 'Places', people: 'Peoples and clans', river: 'Rivers',
  mountain: 'Mountains', other: 'Other names',
};

export function nameHref(canonical: string): string {
  return `/corpus/names/${encodeURIComponent(canonical)}`;
}

/** The names of one reader page, by passage ("p6-1"). */
export function namesByPassage(rows: unknown[]): Map<string, PageName[]> {
  const m = new Map<string, PageName[]>();
  for (const x of rows) {
    const r = x as PageName;
    if (!r || typeof r.canonical !== 'string' || typeof r.page_no !== 'number' || typeof r.idx !== 'number') continue;
    const k = `p${r.page_no}-${r.idx}`;
    m.set(k, [...(m.get(k) ?? []), r]);
  }
  return m;
}

// ---- loaders --------------------------------------------------------------------------------

export interface LibResult<T> extends MirrorResult<T> { missing: boolean }

async function lib<T>(fn: string, args: Record<string, unknown>): Promise<LibResult<T>> {
  const r = await callMirror<T>(fn, args);
  return { ...r, missing: functionMissing(r, fn) };
}

export function loadProgress(): Promise<LibResult<StageRow>> {
  return lib<StageRow>('corpus_reader_progress', {});
}

export function loadStories(docCode?: string | null, full = false): Promise<LibResult<StoryRow>> {
  return lib<StoryRow>('corpus_reader_stories', { p_doc: docCode || null, p_full: full });
}

export function loadNames(o: { q?: string; kind?: string | null; k?: number; offset?: number; exact?: boolean } = {}): Promise<LibResult<NameRow>> {
  return lib<NameRow>('corpus_reader_names', {
    q: (o.q ?? '').replace(/\s+/g, ' ').trim().slice(0, 100) || null,
    p_kind: o.kind || null, k: o.k ?? 60, p_offset: Math.max(0, o.offset ?? 0), p_exact: !!o.exact,
  });
}

export function loadName(canonical: string, offset = 0, k = 50): Promise<LibResult<NameHit>> {
  return lib<NameHit>('corpus_reader_name', { p_canonical: canonical, k, p_offset: Math.max(0, offset) });
}

export function loadPageNames(docCode: string, page: number): Promise<LibResult<PageName>> {
  const p = Math.max(1, Math.trunc(page) || 1);
  return lib<PageName>('corpus_reader_page_names', {
    p_doc: docCode, p_offset: (p - 1) * PASSAGES_PER_PAGE, p_limit: PASSAGES_PER_PAGE,
  });
}

export type { MirrorDoc };
