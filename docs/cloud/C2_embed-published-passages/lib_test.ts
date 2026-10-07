// deno test docs/cloud/C2_embed-published-passages/lib_test.ts   (no network, no imports from the web)
import {
  buildBatchRequest, clampInt, EMBED_DIMS, embedBatchGemini, GEMINI_URL, MAX_CHARS, normalise,
  parseBatchResponse, type QueueRow, runEmbedding, toHalfvecLiteral, type VectorRow,
} from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const vec = (seed: number) => Array.from({ length: EMBED_DIMS }, (_, i) => Math.sin(seed + i) * 3);
const rows = (n: number, pending = n): QueueRow[] =>
  Array.from({ length: n }, (_, i) => ({
    passage_id: `p${i}`, doc_code: "markandeya_purana", content: `iast ${i} \u2014 english ${i}`,
    source_hash: `h${i}`, total_pending: String(pending),
  }));

Deno.test("request shape: model, task type, 1536 dimensions, one request per text", () => {
  const r = buildBatchRequest(["a", "b"]);
  eq(r.requests.length, 2);
  eq(r.requests[0], { model: "models/gemini-embedding-001", content: { parts: [{ text: "a" }] },
    taskType: "RETRIEVAL_DOCUMENT", outputDimensionality: 1536 });
});

Deno.test("normalise gives unit length and refuses zeros and NaN", () => {
  const n = normalise(vec(1));
  const len = Math.sqrt(n.reduce((s, x) => s + x * x, 0));
  ok(Math.abs(len - 1) < 1e-9, "unit length");
  let threw = false; try { normalise(new Array(EMBED_DIMS).fill(0)); } catch { threw = true; } ok(threw, "zeros");
  threw = false; try { normalise([1, NaN]); } catch { threw = true; } ok(threw, "NaN");
});

Deno.test("halfvec literal is pgvector text form", () => {
  eq(toHalfvecLiteral([0.5, -0.25, 0.000001]), "[0.50000,-0.25000,0]");
});

Deno.test("parse refuses a wrong count or a wrong dimension", () => {
  let threw = false; try { parseBatchResponse({ embeddings: [{ values: vec(1) }] }, 2); } catch { threw = true; } ok(threw);
  threw = false; try { parseBatchResponse({ embeddings: [{ values: [1, 2, 3] }] }, 1); } catch { threw = true; } ok(threw);
  eq(parseBatchResponse({ embeddings: [{ values: vec(1) }] }, 1).length, 1);
});

Deno.test("Gemini call: key in a header, not the URL; retried on 429; not retried on 400", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  let n = 0;
  const fakeFetch = (url: string, init: RequestInit) => {
    calls.push({ url, init }); n++;
    if (n === 1) return Promise.resolve(new Response("slow down", { status: 429 }));
    return Promise.resolve(new Response(JSON.stringify({ embeddings: [{ values: vec(2) }] }), { status: 200 }));
  };
  const slept: number[] = [];
  const out = await embedBatchGemini(fakeFetch, "SECRET", ["x"], { sleep: (ms) => { slept.push(ms); return Promise.resolve(); } });
  eq(out.length, 1); eq(calls.length, 2); eq(slept, [2000]);
  eq(calls[0].url, GEMINI_URL); ok(!calls[0].url.includes("SECRET"), "key not in URL");
  eq((calls[0].init.headers as Record<string, string>)["x-goog-api-key"], "SECRET");

  let c400 = 0;
  const bad = () => { c400++; return Promise.resolve(new Response("bad key", { status: 400 })); };
  let msg = ""; try { await embedBatchGemini(bad, "K", ["x"], { sleep: () => Promise.resolve() }); } catch (e) { msg = String(e); }
  eq(c400, 1); ok(msg.includes("Gemini 400"), msg);
});

Deno.test("run: embeds in batches, truncates to 2000 chars, upserts at most 25 rows per request", async () => {
  const q = rows(60, 75);
  q[0].content = "x".repeat(MAX_CHARS + 500);
  const seenTexts: string[][] = [];
  const upserts: VectorRow[][] = [];
  const r = await runEmbedding({
    fetchQueue: (n) => { eq(n, 200); return Promise.resolve(q); },
    embed: (t) => { seenTexts.push(t); return Promise.resolve(t.map((_, i) => vec(i))); },
    upsert: (rs) => { upserts.push(rs); return Promise.resolve(); },
    limit: 200, batch: 50, dryRun: false, deadline: Date.now() + 60_000,
  });
  eq([r.pending_before, r.taken, r.embedded, r.pending_after_estimate, r.stopped], [75, 60, 60, 15, "done"]);
  eq(seenTexts.map((t) => t.length), [50, 10]);
  eq(seenTexts[0][0].length, MAX_CHARS);
  eq(upserts.map((u) => u.length), [25, 25, 10]);
  const row = upserts[0][1];
  eq([row.passage_id, row.model, row.dim, row.source_hash], ["p1", "gemini-embedding-001", 1536, "h1"]);
  ok(row.embedding.startsWith("[") && row.embedding.split(",").length === 1536, "literal");
});

Deno.test("run: dry run calls neither the model nor the database writer", async () => {
  let embeds = 0, ups = 0;
  const r = await runEmbedding({
    fetchQueue: () => Promise.resolve(rows(3)),
    embed: () => { embeds++; return Promise.resolve([]); },
    upsert: () => { ups++; return Promise.resolve(); },
    limit: 10, batch: 2, dryRun: true, deadline: Date.now() + 1000,
  });
  eq([embeds, ups, r.embedded, r.dry_run, r.sample?.length], [0, 0, 0, true, 3]);
});

Deno.test("run: stops at the first failure and reports it; nothing after it is attempted", async () => {
  let calls = 0;
  const r = await runEmbedding({
    fetchQueue: () => Promise.resolve(rows(6)),
    embed: (t) => { calls++; if (calls === 2) return Promise.reject(new Error("Gemini 503: busy")); return Promise.resolve(t.map((_, i) => vec(i))); },
    upsert: () => Promise.resolve(),
    limit: 10, batch: 2, dryRun: false, deadline: Date.now() + 60_000,
  });
  eq([r.embedded, r.stopped, r.failures.length, r.failures[0].at, calls], [2, "failure", 1, 2, 2]);
  ok(r.failures[0].error.includes("503"));
});

Deno.test("run: no new batch after the deadline; empty queue is a clean no-op", async () => {
  let t = 0;
  const r = await runEmbedding({
    fetchQueue: () => Promise.resolve(rows(6)),
    embed: (x) => Promise.resolve(x.map((_, i) => vec(i))),
    upsert: () => Promise.resolve(),
    limit: 10, batch: 2, dryRun: false, deadline: 1, now: () => (t++ === 0 ? 0 : 5),
  });
  eq([r.embedded, r.stopped], [2, "deadline"]);
  const e = await runEmbedding({
    fetchQueue: () => Promise.resolve([]), embed: () => Promise.resolve([]), upsert: () => Promise.resolve(),
    limit: 10, batch: 2, dryRun: false, deadline: Date.now() + 1000,
  });
  eq([e.pending_before, e.taken, e.embedded, e.stopped], [0, 0, 0, "done"]);
});

Deno.test("clampInt", () => {
  eq([clampInt(undefined, 1, 10, 5), clampInt("7", 1, 10, 5), clampInt(99, 1, 10, 5), clampInt(-3, 1, 10, 5), clampInt(2.9, 1, 10, 5)],
     [5, 7, 10, 1, 2]);
});
