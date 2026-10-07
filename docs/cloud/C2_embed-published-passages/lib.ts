// C2 - embed-published-passages: the logic, kept free of network imports so it can be tested
// with plain `deno test` (lib_test.ts). EMBED_PUBLISHED_C2_2026_10_07.
//
// What it does: asks the database which passages of PUBLISHED texts have no vector yet (or a
// vector made from text that has since changed), embeds them with gemini-embedding-001 at 1536
// dimensions (RECALL_768_2026_10_07 chose 1536 over 768), L2-normalises each vector, and upserts
// it into srangam_passage_vectors with the hash of the text it was made from. It stops at the
// first failure and reports it; a re-run resumes from what is still pending. Nothing is deleted.

export const EMBED_MODEL = "gemini-embedding-001";
export const EMBED_DIMS = 1536;
export const MAX_CHARS = 2000; // the local brain (build_embeddings.py) embeds t[:2000] too
export const GEMINI_URL =
  "https://generativelanguage.googleapis.com/v1beta/models/" + EMBED_MODEL + ":batchEmbedContents";

export interface QueueRow {
  passage_id: string;
  doc_code: string;
  content: string;
  source_hash: string;
  total_pending: number | string;
}

export interface VectorRow {
  passage_id: string;
  model: string;
  dim: number;
  embedding: string; // halfvec text literal '[...]'
  source_hash: string;
}

export interface Deps {
  fetchQueue: (limit: number) => Promise<QueueRow[]>;
  embed: (texts: string[]) => Promise<number[][]>;
  upsert: (rows: VectorRow[]) => Promise<void>;
  limit: number;
  batch: number;
  dryRun: boolean;
  deadline: number; // epoch ms; no new batch starts after it
  now?: () => number;
}

export interface RunResult {
  model: string;
  dims: number;
  dry_run: boolean;
  pending_before: number;
  taken: number;
  embedded: number;
  pending_after_estimate: number;
  stopped: "done" | "deadline" | "failure";
  failures: { at: number; error: string }[];
  sample?: { passage_id: string; doc_code: string; chars: number }[];
}

export function clampInt(v: unknown, lo: number, hi: number, dflt: number): number {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  if (!Number.isFinite(n)) return dflt;
  return Math.min(hi, Math.max(lo, Math.trunc(n)));
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

/** pgvector text form. halfvec keeps about 3 significant digits, so 5 decimals lose nothing. */
export function toHalfvecLiteral(v: number[]): string {
  return "[" + v.map((x) => (Math.abs(x) < 5e-6 ? "0" : x.toFixed(5))).join(",") + "]";
}

export function buildBatchRequest(texts: string[]) {
  return {
    requests: texts.map((t) => ({
      model: "models/" + EMBED_MODEL,
      content: { parts: [{ text: t }] },
      taskType: "RETRIEVAL_DOCUMENT",
      outputDimensionality: EMBED_DIMS,
    })),
  };
}

export function parseBatchResponse(json: unknown, expected: number): number[][] {
  const embs = (json as { embeddings?: { values?: number[] }[] })?.embeddings;
  if (!Array.isArray(embs)) throw new Error("no 'embeddings' in the Gemini response");
  if (embs.length !== expected) throw new Error(`expected ${expected} embeddings, got ${embs.length}`);
  return embs.map((e, i) => {
    const v = e?.values;
    if (!Array.isArray(v) || v.length !== EMBED_DIMS) {
      throw new Error(`embedding ${i} has ${Array.isArray(v) ? v.length : "no"} values, expected ${EMBED_DIMS}`);
    }
    return v;
  });
}

type FetchFn = (url: string, init: RequestInit) => Promise<Response>;

/** One batchEmbedContents call, retried on 429 and 5xx (2 s, 4 s, 8 s). The key travels in a
 *  header, never in the URL. */
export async function embedBatchGemini(
  fetchFn: FetchFn,
  apiKey: string,
  texts: string[],
  opts: { retries?: number; sleep?: (ms: number) => Promise<void> } = {},
): Promise<number[][]> {
  const retries = opts.retries ?? 3;
  const sleep = opts.sleep ?? ((ms: number) => new Promise((r) => setTimeout(r, ms)));
  const body = JSON.stringify(buildBatchRequest(texts));
  let last = "";
  for (let attempt = 0; attempt <= retries; attempt++) {
    const res = await fetchFn(GEMINI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
      body,
    });
    if (res.ok) return parseBatchResponse(await res.json(), texts.length);
    last = `Gemini ${res.status}: ${(await res.text()).slice(0, 300)}`;
    if (res.status !== 429 && res.status < 500) break; // 400/401/403: retrying will not help
    if (attempt < retries) await sleep(2000 * 2 ** attempt);
  }
  throw new Error(last);
}

export async function runEmbedding(d: Deps): Promise<RunResult> {
  const now = d.now ?? Date.now;
  const queue = await d.fetchQueue(d.limit);
  const pending = queue.length ? Number(queue[0].total_pending) : 0;
  const out: RunResult = {
    model: EMBED_MODEL, dims: EMBED_DIMS, dry_run: d.dryRun, pending_before: pending,
    taken: queue.length, embedded: 0, pending_after_estimate: pending, stopped: "done", failures: [],
  };
  if (d.dryRun) {
    out.sample = queue.slice(0, 5).map((q) => ({ passage_id: q.passage_id, doc_code: q.doc_code, chars: q.content.length }));
    return out;
  }
  for (let i = 0; i < queue.length; i += d.batch) {
    if (now() > d.deadline) { out.stopped = "deadline"; break; }
    const chunk = queue.slice(i, i + d.batch);
    try {
      const vecs = await d.embed(chunk.map((q) => q.content.slice(0, MAX_CHARS)));
      const rows: VectorRow[] = chunk.map((q, j) => ({
        passage_id: q.passage_id, model: EMBED_MODEL, dim: EMBED_DIMS,
        embedding: toHalfvecLiteral(normalise(vecs[j])), source_hash: q.source_hash,
      }));
      for (let k = 0; k < rows.length; k += 25) await d.upsert(rows.slice(k, k + 25)); // keep each request small
      out.embedded += rows.length;
    } catch (e) {
      out.failures.push({ at: i, error: String((e as Error)?.message ?? e).slice(0, 300) });
      out.stopped = "failure";
      break;
    }
  }
  out.pending_after_estimate = Math.max(0, pending - out.embedded);
  return out;
}
