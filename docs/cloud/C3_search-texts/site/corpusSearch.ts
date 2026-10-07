/**
 * Search the published texts by meaning - SEARCH_TEXTS_C3A_2026_10_07.
 *
 * Calls the edge function search-texts: the question becomes a gemini-embedding-001 query
 * vector (1536 dimensions) and match_text_passages() returns the nearest passages of
 * PUBLISHED texts only (row-level security, as /texts). Nothing is generated: the hits are
 * the passages themselves.
 *
 * Same contract as corpusTexts.ts: a failure is never shown as "nothing found". Check `ok`
 * first; `error` is non-null exactly when ok is false.
 */
import { supabase } from '@/integrations/supabase/client';
import { PASSAGES_PER_PAGE } from '@/lib/corpusDisplay';

const SEARCH_TIMEOUT_MS = 12000;
export const MIN_QUERY = 3;
export const MAX_QUERY = 300;

export interface SearchHit {
  doc_code: string;
  title: string;
  ref: string;
  page_no: number;
  idx: number;
  verse_ref: string | null;
  translation: string;
  similarity: number;
  /** 1-based position of the passage in its text, in the reader's order; null if unknown. */
  ordinal: number | null;
}

export interface SearchResult {
  ok: boolean;
  rows: SearchHit[];
  /** Non-null exactly when ok === false. */
  error: string | null;
}

const fail = (error: string): SearchResult => ({ ok: false, rows: [], error });

async function errorText(err: any): Promise<string> {
  try {
    const j = await err?.context?.json?.();
    if (j && j.error) return String(j.error);
  } catch {
    /* the body was not JSON; fall through */
  }
  return err?.message ? String(err.message) : 'The search failed.';
}

export async function searchTexts(q: string, opts: { k?: number; docCodes?: string[] } = {}): Promise<SearchResult> {
  const query = (q ?? '').replace(/\s+/g, ' ').trim();
  if (query.length < MIN_QUERY) return fail(`Type at least ${MIN_QUERY} characters.`);
  const body: Record<string, unknown> = { q: query.slice(0, MAX_QUERY), k: opts.k ?? 10 };
  if (opts.docCodes && opts.docCodes.length) body.doc_codes = opts.docCodes;
  const call = (supabase as any).functions.invoke('search-texts', { body });
  const timeout = new Promise<any>((resolve) => setTimeout(() => resolve({ __timeout: true }), SEARCH_TIMEOUT_MS));
  const res = await Promise.race([call, timeout]);
  if (res && res.__timeout) return fail('The search took too long. Please try again.');
  if (res && res.error) return fail(await errorText(res.error));
  const rows = res && res.data && Array.isArray(res.data.results) ? (res.data.results as SearchHit[]) : null;
  if (!rows) return fail('The search answered in an unexpected form.');
  return { ok: true, rows, error: null };
}

/** The reader page that holds a hit, with its passage anchor: /texts/<doc>?p=<page>#p<page_no>-<idx>. */
export function readerHref(h: Pick<SearchHit, 'doc_code' | 'page_no' | 'idx' | 'ordinal'>): string {
  const base = `/texts/${encodeURIComponent(h.doc_code)}`;
  const anchor = `#p${h.page_no}-${h.idx}`;
  if (!h.ordinal || h.ordinal < 1) return base + anchor;
  const page = Math.ceil(h.ordinal / PASSAGES_PER_PAGE);
  return (page > 1 ? `${base}?p=${page}` : base) + anchor;
}
