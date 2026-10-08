// C5 - search-corpus: the parts that need no network, for `deno test lib_test.ts`.
// CORPUS_READER_C5_2026_10_08.

/** The caller's bearer token, or null. The publishable (anon) key is not a reader's session. */
export function readerToken(authHeader: string | null, anonKey: string): string | null {
  const m = /^Bearer\s+(\S+)$/i.exec((authHeader ?? "").trim());
  if (!m) return null;
  if (anonKey && m[1] === anonKey) return null;
  return m[1];
}

export interface CorpusHit {
  doc_code: string; title: string; page_no: number; idx: number; verse_ref: string | null;
  ord: number | null; similarity: number; snippet: string | null;
}

/** Rows of corpus_reader_match() as the page reads them (similarity to 3 decimals). */
export function shapeHits(rows: unknown): CorpusHit[] {
  if (!Array.isArray(rows)) return [];
  return rows.map((r) => {
    const x = r as Record<string, unknown>;
    return {
      doc_code: String(x.doc_code ?? ""),
      title: String(x.title ?? x.doc_code ?? ""),
      page_no: Number(x.page_no),
      idx: Number(x.idx),
      verse_ref: x.verse_ref == null ? null : String(x.verse_ref),
      ord: x.ord == null ? null : Number(x.ord),
      similarity: Math.round(Number(x.similarity) * 1000) / 1000,
      snippet: x.snippet == null ? null : String(x.snippet),
    };
  });
}

/** True when a database error is the reader gate's refusal (not a failure). */
export function isRefusal(err: { code?: string; message?: string } | null | undefined): boolean {
  if (!err) return false;
  return err.code === "42501" || /signed-in readers only|permission denied/i.test(err.message ?? "");
}
