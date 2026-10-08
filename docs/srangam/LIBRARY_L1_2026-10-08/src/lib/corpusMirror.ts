/**
 * The working corpus for signed-in readers - CORPUS_READER_C5_2026_10_08.
 *
 * The private mirror of the whole Sanskrit brain (schema `corpus`, kept current from the
 * translation PC by corpus_sync.py) is read only through six database functions, each of which
 * checks the caller first (corpus_reader_allowed(): signed-in users, or a reader list, or admins).
 * So this page can never show more than the database lets this user see.
 *
 * Same contract as corpusTexts.ts: check `ok` first; `error` is non-null exactly when ok is false;
 * `refused` tells "you may not read this" apart from "it failed to load".
 */
import { supabase } from '@/integrations/supabase/client';
import { PASSAGES_PER_PAGE } from '@/lib/corpusDisplay';

const TIMEOUT_MS = 15000;
export const MIN_WORDS = 2;
export const MIN_MEANING = 3;
export const MAX_QUERY = 200;
export const REFUSED_TEXT = 'The working corpus is open to signed-in readers only.';

export interface MirrorDoc {
  doc_code: string;
  title: string;
  category: string | null;
  passages: number;
  english: number;
  hindi: number;
  vectors: number;
  stories: number;
  published: boolean;
  synced_at: string | null;
}

export interface MirrorPassage {
  ord: number;
  page_no: number;
  idx: number;
  verse_ref: string | null;
  chapter: string | null;
  text_type: string | null;
  sanskrit: string | null;
  iast: string | null;
  translation: string | null;
  hindi: string | null;
  quality_score: number | null;
  translation_qa: number | null;
  engine: string | null;
  translated_at: string | null;
}

export interface MirrorHit {
  doc_code: string;
  title: string;
  page_no: number;
  idx: number;
  verse_ref: string | null;
  ord: number | null;
  score?: number;
  similarity?: number;
  snippet: string | null;
}

export interface MirrorResult<T> {
  ok: boolean;
  rows: T[];
  /** Non-null exactly when ok === false. */
  error: string | null;
  /** True when the database refused this reader (not signed in, or not on the reader list). */
  refused: boolean;
}

const fail = <T,>(error: string, refused = false): MirrorResult<T> => ({ ok: false, rows: [], error, refused });

const REFUSED_RE = /signed-in readers only|permission denied|not allowed|42501/i;

function timeout(): Promise<{ __timeout: true }> {
  return new Promise((resolve) => setTimeout(() => resolve({ __timeout: true }), TIMEOUT_MS));
}

async function rpc<T>(fn: string, args: Record<string, unknown>): Promise<MirrorResult<T>> {
  let res: any;
  try {
    res = await Promise.race([(supabase as any).rpc(fn, args), timeout()]);
  } catch (e: any) {
    return fail<T>(e?.message ? String(e.message) : 'The working corpus could not be reached.');
  }
  if (res && res.__timeout) return fail<T>('The working corpus took too long to answer. Please try again.');
  if (res && res.error) {
    const msg = String(res.error.message ?? res.error);
    const refused = res.error.code === '42501' || REFUSED_RE.test(msg);
    return fail<T>(refused ? REFUSED_TEXT : msg, refused);
  }
  if (!res || !Array.isArray(res.data)) return fail<T>('The working corpus answered in an unexpected form.');
  return { ok: true, rows: res.data as T[], error: null, refused: false };
}

const clean = (q: string) => (q ?? '').replace(/\s+/g, ' ').trim();

export function listMirrorDocs(): Promise<MirrorResult<MirrorDoc>> {
  return rpc<MirrorDoc>('corpus_reader_docs', {});
}

export function loadMirrorDoc(docCode: string | undefined): Promise<MirrorResult<MirrorDoc>> {
  if (!docCode) return Promise.resolve(fail<MirrorDoc>('No document was named.'));
  return rpc<MirrorDoc>('corpus_reader_docs', { p_doc: docCode });
}

export function loadMirrorPage(docCode: string, page: number): Promise<MirrorResult<MirrorPassage>> {
  const p = Math.max(1, Math.trunc(page) || 1);
  return rpc<MirrorPassage>('corpus_reader_page', {
    p_doc: docCode, p_offset: (p - 1) * PASSAGES_PER_PAGE, p_limit: PASSAGES_PER_PAGE,
  });
}

export function searchMirrorWords(q: string, docCode?: string | null): Promise<MirrorResult<MirrorHit>> {
  const query = clean(q);
  if (query.length < MIN_WORDS) return Promise.resolve(fail<MirrorHit>(`Type at least ${MIN_WORDS} characters.`));
  return rpc<MirrorHit>('corpus_reader_search', { q: query.slice(0, MAX_QUERY), k: 30, p_doc: docCode || null });
}

export function similarPassages(docCode: string, pageNo: number, idx: number): Promise<MirrorResult<MirrorHit>> {
  return rpc<MirrorHit>('corpus_reader_similar', { p_doc: docCode, p_page: pageNo, p_idx: idx, k: 8 });
}

async function errorBody(err: any): Promise<{ status: number | null; text: string | null }> {
  const status = typeof err?.context?.status === 'number' ? err.context.status : null;
  try {
    const j = await err?.context?.json?.();
    if (j && j.error) return { status, text: String(j.error) };
  } catch {
    /* not JSON */
  }
  return { status, text: err?.message ? String(err.message) : null };
}

/** Meaning search over the whole corpus, through the edge function search-corpus (as this reader). */
export async function searchMirrorMeaning(q: string, docCodes?: string[]): Promise<MirrorResult<MirrorHit>> {
  const query = clean(q);
  if (query.length < MIN_MEANING) return fail<MirrorHit>(`Type at least ${MIN_MEANING} characters.`);
  const body: Record<string, unknown> = { q: query.slice(0, 300), k: 12 };
  if (docCodes && docCodes.length) body.doc_codes = docCodes;
  let res: any;
  try {
    res = await Promise.race([(supabase as any).functions.invoke('search-corpus', { body }), timeout()]);
  } catch (e: any) {
    return fail<MirrorHit>(e?.message ? String(e.message) : 'Meaning search could not be reached.');
  }
  if (res && res.__timeout) return fail<MirrorHit>('Meaning search took too long. Please try again.');
  if (res && res.error) {
    const { status, text } = await errorBody(res.error);
    if (status === 404) return fail<MirrorHit>('Meaning search is not switched on yet. Word search works now.');
    if (status === 401 || status === 403 || (text && REFUSED_RE.test(text))) return fail<MirrorHit>(REFUSED_TEXT, true);
    return fail<MirrorHit>(text || 'Meaning search failed.');
  }
  const rows = res && res.data && Array.isArray(res.data.results) ? (res.data.results as MirrorHit[]) : null;
  if (!rows) return fail<MirrorHit>('Meaning search answered in an unexpected form.');
  return { ok: true, rows, error: null, refused: false };
}

/** The page of /corpus/:docCode that holds a passage, with its anchor. */
export function mirrorHref(h: { doc_code: string; page_no: number; idx: number; ord?: number | null }): string {
  const base = `/corpus/${encodeURIComponent(h.doc_code)}`;
  const anchor = `#p${h.page_no}-${h.idx}`;
  if (!h.ord || h.ord < 1) return base + anchor;
  const page = Math.ceil(h.ord / PASSAGES_PER_PAGE);
  return (page > 1 ? `${base}?p=${page}` : base) + anchor;
}

/** Split a search snippet on its [[ ]] marks, for <mark> without any HTML from the server. */
export function snippetParts(s: string | null | undefined): { text: string; mark: boolean }[] {
  const out: { text: string; mark: boolean }[] = [];
  const re = /\[\[(.*?)\]\]/g;
  const src = s ?? '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) out.push({ text: src.slice(last, m.index), mark: false });
    out.push({ text: m[1], mark: true });
    last = m.index + m[0].length;
  }
  if (last < src.length) out.push({ text: src.slice(last), mark: false });
  return out;
}

/** A share as a whole percent, never NaN. */
export function share(part: number, whole: number): string {
  if (!whole) return '-';
  return `${Math.round((100 * part) / whole)}%`;
}

// ---- READER_NAV_2026_10_08: the contents of one text (docs/cloud/C5b, corpus_reader_outline) ----

export interface MirrorOutlineRow {
  kind: 'page' | 'colophon';
  ord: number;
  reader_page: number;
  page_no: number;
  idx: number;
  last_page_no: number | null;
  label: string | null;
}

/** True when the database has no corpus_reader_outline yet (C5b not applied): the reader then
 *  falls back to plain page numbers instead of calling it a failure. */
export function outlineMissing(r: MirrorResult<unknown>): boolean {
  return !r.ok && !r.refused && /corpus_reader_outline|PGRST202|could not find the function|does not exist/i.test(r.error ?? '');
}

export function loadMirrorOutline(docCode: string): Promise<MirrorResult<MirrorOutlineRow>> {
  return rpc<MirrorOutlineRow>('corpus_reader_outline', { p_doc: docCode, p_per_page: PASSAGES_PER_PAGE });
}

// ---- CORPUS_LIBRARY_C6_2026_10_08: shared by the library pages (src/lib/corpusLibrary.ts) ----

/** Call one of the reader functions with the same contract as everything above. */
export function callMirror<T>(fn: string, args: Record<string, unknown>): Promise<MirrorResult<T>> {
  return rpc<T>(fn, args);
}

/** True when the database has no such function yet (its SQL is not applied): pages then fall back
 *  quietly instead of calling it a failure. */
export function functionMissing(r: MirrorResult<unknown>, fn: string): boolean {
  if (r.ok || r.refused) return false;
  const e = r.error ?? '';
  return e.includes(fn) && /PGRST202|could not find the function|does not exist|schema cache/i.test(e);
}
