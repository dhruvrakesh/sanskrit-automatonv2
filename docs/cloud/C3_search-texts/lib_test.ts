// deno test docs/cloud/C3_search-texts/lib_test.ts   (offline)
import {
  buildQueryRequest, EMBED_DIMS, EMBED_URL, embedQuery, MAX_QUERY_CHARS, parseInput, RateLimiter,
  shapeResults, toHalfvecLiteral, VectorCache,
} from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }
const vec = (s: number) => Array.from({ length: EMBED_DIMS }, (_, i) => Math.cos(s + i));

Deno.test("input: trims, bounds k, refuses short, long and bad doc codes", () => {
  eq(parseInput({ q: "  why   did he sell  ", k: 50 }), { q: "why did he sell", k: 20, docCodes: null });
  eq(parseInput({ q: "dharma", k: "3", doc_codes: ["markandeya_purana"] }), { q: "dharma", k: 3, docCodes: ["markandeya_purana"] });
  ok("error" in parseInput({ q: "ab" }));
  ok("error" in parseInput({ q: "x".repeat(MAX_QUERY_CHARS + 1) }));
  ok("error" in parseInput({ q: "dharma", doc_codes: ["a;drop table"] }));
  ok("error" in parseInput(null));
  eq((parseInput({ q: "dharma", k: "abc" }) as { k: number }).k, 8);
});

Deno.test("query request: RETRIEVAL_QUERY at 1536 dimensions", () => {
  eq(buildQueryRequest("q"), { model: "models/gemini-embedding-001", content: { parts: [{ text: "q" }] },
    taskType: "RETRIEVAL_QUERY", outputDimensionality: 1536 });
});

Deno.test("embed: key in header, normalised result, one retry on 503, none on 403", async () => {
  let n = 0; const seen: RequestInit[] = [];
  const f = (url: string, init: RequestInit) => {
    n++; seen.push(init); eq(url, EMBED_URL);
    if (n === 1) return Promise.resolve(new Response("busy", { status: 503 }));
    return Promise.resolve(new Response(JSON.stringify({ embedding: { values: vec(1).map((x) => x * 7) } }), { status: 200 }));
  };
  const v = await embedQuery(f, "K", "q", () => Promise.resolve());
  eq(n, 2); eq((seen[0].headers as Record<string, string>)["x-goog-api-key"], "K");
  ok(Math.abs(Math.sqrt(v.reduce((s, x) => s + x * x, 0)) - 1) < 1e-9, "unit");
  let m = 0, msg = "";
  try { await embedQuery(() => { m++; return Promise.resolve(new Response("no", { status: 403 })); }, "K", "q", () => Promise.resolve()); }
  catch (e) { msg = String(e); }
  eq(m, 1); ok(msg.includes("403"));
  msg = "";
  try { await embedQuery(() => Promise.resolve(new Response(JSON.stringify({ embedding: { values: [1, 2] } }))), "K", "q"); }
  catch (e) { msg = String(e); }
  ok(msg.includes("expected 1536"), msg);
});

Deno.test("rate limiter: 3 a minute, then refuses, then allows after the window", () => {
  let t = 0; const r = new RateLimiter(3, 60_000, () => t);
  eq([r.allow("a"), r.allow("a"), r.allow("a"), r.allow("a"), r.allow("b")], [true, true, true, false, true]);
  t = 61_000; eq(r.allow("a"), true);
});

Deno.test("cache: case-insensitive, least recently used goes first", () => {
  const c = new VectorCache(2);
  c.set("Dharma", [1]); c.set("artha", [2]); c.get("dharma"); c.set("kama", [3]);
  eq([c.get("DHARMA"), c.get("artha"), c.get("kama")], [[1], undefined, [3]]);
});

Deno.test("results carry title, ref and rounded similarity", () => {
  const out = shapeResults([{ passage_id: "x", doc_code: "markandeya_purana", page_no: 60, idx: 10, verse_ref: null,
    translation: "Alas!", similarity: 0.83456 }], { markandeya_purana: "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a" });
  eq(out[0].ref, "60.10"); eq(out[0].similarity, 0.835); ok(out[0].title.startsWith("M\u0101rka"));
  eq(shapeResults([{ passage_id: "y", doc_code: "zz", page_no: 1, idx: 2, verse_ref: "1.1", translation: "t", similarity: 0.5 }], {})[0].title, "zz");
});

Deno.test("halfvec literal", () => { eq(toHalfvecLiteral([0.12345678, -1, 0]), "[0.12346,-1.00000,0]"); });
