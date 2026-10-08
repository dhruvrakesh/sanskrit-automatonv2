// deno test docs/cloud/C5_search-corpus/lib_test.ts   (no network)   CORPUS_READER_C5_2026_10_08
import { isRefusal, readerToken, shapeHits } from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}

Deno.test("a reader's session is a bearer token that is not the publishable key", () => {
  eq(readerToken("Bearer eyJ.user.jwt", "eyJ.anon"), "eyJ.user.jwt");
  eq(readerToken("bearer   eyJ.user.jwt  ", "eyJ.anon"), "eyJ.user.jwt");
  eq(readerToken("Bearer eyJ.anon", "eyJ.anon"), null, "the anon key is not a session");
  eq(readerToken(null, "x"), null);
  eq(readerToken("Basic abc", "x"), null);
  eq(readerToken("Bearer", "x"), null);
});

Deno.test("hits are shaped for the page; nothing else passes", () => {
  eq(shapeHits(null), []);
  eq(shapeHits([{ doc_code: "d", title: "T", page_no: 3, idx: 2, verse_ref: null, ord: 51, similarity: 0.87654, snippet: "s" }]),
    [{ doc_code: "d", title: "T", page_no: 3, idx: 2, verse_ref: null, ord: 51, similarity: 0.877, snippet: "s" }]);
});

Deno.test("the reader gate's refusal is told apart from a failure", () => {
  eq(isRefusal({ code: "42501", message: "x" }), true);
  eq(isRefusal({ message: "The working corpus is open to signed-in readers only." }), true);
  eq(isRefusal({ message: "permission denied for function corpus_reader_match" }), true);
  eq(isRefusal({ code: "57014", message: "canceling statement due to statement timeout" }), false);
  eq(isRefusal(null), false);
});
