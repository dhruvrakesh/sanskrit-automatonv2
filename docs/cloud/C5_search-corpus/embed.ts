// search-corpus: the embedding helpers, its own copy - READER_NAV_2026_10_08.
//
// Lovable Cloud deploys a function from its own folder and _shared/ only, so importing from
// the search-texts folder failed to deploy ("cross-folder import"). This file is a VERBATIM copy of
// search-texts/lib.ts from `export const EMBED_MODEL` up to (not including) `export interface
// MatchRow`: the same model, size, task type, limits and normalisation, so a question is embedded
// exactly as search-texts embeds it. src/__tests__/search-corpus-embed.test.ts fails if the two drift.
// search-texts itself is not touched.

export const EMBED_MODEL = "gemini-embedding-001";
export const EMBED_DIMS = 1536;
export const EMBED_URL =
  "https://generativelanguage.googleapis.com/v1beta/models/" + EMBED_MODEL + ":embedContent";
export const MAX_QUERY_CHARS = 300;
export const MAX_K = 20;
export const DOC_CODE_RE = /^[A-Za-z0-9_.-]{1,80}$/;

export interface SearchInput { q: string; k: number; docCodes: string[] | null }

export function parseInput(body: unknown): SearchInput | { error: string } {
  const b = (body ?? {}) as Record<string, unknown>;
  const q = typeof b.q === "string" ? b.q.replace(/\s+/g, " ").trim() : "";
  if (q.length < 3) return { error: "Ask with at least 3 characters." };
  if (q.length > MAX_QUERY_CHARS) return { error: `Keep the question under ${MAX_QUERY_CHARS} characters.` };
  const kRaw = typeof b.k === "number" ? b.k : typeof b.k === "string" ? Number(b.k) : 8;
  const k = Number.isFinite(kRaw) ? Math.min(MAX_K, Math.max(1, Math.trunc(kRaw))) : 8;
  let docCodes: string[] | null = null;
  if (Array.isArray(b.doc_codes) && b.doc_codes.length) {
    const codes = b.doc_codes.filter((c): c is string => typeof c === "string" && DOC_CODE_RE.test(c)).slice(0, 10);
    if (codes.length !== b.doc_codes.length) return { error: "doc_codes must be up to 10 text codes." };
    docCodes = codes;
  }
  return { q, k, docCodes };
}

export function normalise(v: number[]): number[] {
  let s = 0;
  for (const x of v) {
    if (!Number.isFinite(x)) throw new Error("embedding contains a non-finite value");
    s += x * x;
  }
  const n = Math.sqrt(s);
  if (n === 0) throw new Error("embedding is all zeros");
  return v.map((x) => x / n);
}

export function toHalfvecLiteral(v: number[]): string {
  return "[" + v.map((x) => (Math.abs(x) < 5e-6 ? "0" : x.toFixed(5))).join(",") + "]";
}

export function buildQueryRequest(q: string) {
  return {
    model: "models/" + EMBED_MODEL,
    content: { parts: [{ text: q }] },
    taskType: "RETRIEVAL_QUERY",
    outputDimensionality: EMBED_DIMS,
  };
}

type FetchFn = (url: string, init: RequestInit) => Promise<Response>;

/** One embedContent call; one retry on 429/5xx after 1 s. The key travels in a header. */
export async function embedQuery(fetchFn: FetchFn, apiKey: string, q: string,
                                 sleep: (ms: number) => Promise<void> = (ms) => new Promise((r) => setTimeout(r, ms))): Promise<number[]> {
  const body = JSON.stringify(buildQueryRequest(q));
  let last = "";
  for (let attempt = 0; attempt < 2; attempt++) {
    const res = await fetchFn(EMBED_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
      body,
    });
    if (res.ok) {
      const j = await res.json() as { embedding?: { values?: number[] } };
      const v = j?.embedding?.values;
      if (!Array.isArray(v) || v.length !== EMBED_DIMS) {
        throw new Error(`the query embedding has ${Array.isArray(v) ? v.length : "no"} values, expected ${EMBED_DIMS}`);
      }
      return normalise(v);
    }
    last = `Gemini ${res.status}`;
    if (res.status !== 429 && res.status < 500) break;
    if (attempt === 0) await sleep(1000);
  }
  throw new Error(last);
}

/** Per-instance limiter: at most `max` requests per `windowMs` from one client key. Edge instances
 *  are short-lived and several may run, so this is a brake on bursts, not an accounting system. */
export class RateLimiter {
  private hits = new Map<string, number[]>();
  constructor(private max = 20, private windowMs = 60_000, private now: () => number = Date.now) {}
  allow(key: string): boolean {
    const t = this.now();
    const recent = (this.hits.get(key) ?? []).filter((x) => t - x < this.windowMs);
    if (recent.length >= this.max) { this.hits.set(key, recent); return false; }
    recent.push(t); this.hits.set(key, recent);
    if (this.hits.size > 5000) this.hits.clear(); // never let the map grow without bound
    return true;
  }
}

/** Small LRU of query -> vector, so a repeated question costs no second embedding call. */
export class VectorCache {
  private m = new Map<string, number[]>();
  constructor(private size = 200) {}
  get(q: string): number[] | undefined {
    const k = q.toLowerCase(); const v = this.m.get(k);
    if (v) { this.m.delete(k); this.m.set(k, v); }
    return v;
  }
  set(q: string, v: number[]) {
    const k = q.toLowerCase(); this.m.delete(k); this.m.set(k, v);
    if (this.m.size > this.size) this.m.delete(this.m.keys().next().value as string);
  }
}
