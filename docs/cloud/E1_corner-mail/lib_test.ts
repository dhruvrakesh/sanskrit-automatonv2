// deno test --no-remote docs/cloud/E1_corner-mail/lib_test.ts   (no network, no imports from the web)
// MAIL_E1_2026_10_09
import {
  canRequest, CORS, errorText, FLUSH_BUDGET_MS, FN_VERSION, gunzipLimited, isBearer, LIMIT_DEFAULT, LIMIT_MAX,
  MAX_BODY_BYTES, MAX_JSON_BYTES, type MailRow, parseBody, RESEND_URL, resendPayload, route, runFlush,
  SEND_GAP_MS, SEND_TIMEOUT_MS, sendOne, type SendOutcome, signHex, statusCounts, summarize, verifyRequest,
} from "./lib.ts";

function eq(a: unknown, b: unknown, msg = "") {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error(`${msg} expected ${B}, got ${A}`);
}
function ok(c: unknown, msg = "") { if (!c) throw new Error("assertion failed " + msg); }

const enc = new TextEncoder();
const SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const KEY = "re_test_key_never_shown";
const ROW: MailRow = {
  id: 7, to_email: "reader@example.org", mail_from: "Srangam desk <desk@nartiang.org>", reply_to: null,
  subject: "Srangam: request #12 is done - Find episodes in a text", body: "What you asked for ...",
};

async function gzip(bytes: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(await new Response(new Blob([bytes as BlobPart]).stream()
    .pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
}

Deno.test("the signature is corpus-desk's (the same golden value as corpus_sync.py's test)", async () => {
  eq(await signHex("test-secret-for-golden", "1760000000", enc.encode('{"action":"hello"}')),
    "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16");
  eq(FN_VERSION, "corner-mail 1.0");
  eq([MAX_BODY_BYTES, MAX_JSON_BYTES], [1048576, 4194304]);
  eq([LIMIT_DEFAULT, LIMIT_MAX, SEND_TIMEOUT_MS, SEND_GAP_MS, FLUSH_BUDGET_MS], [10, 20, 10000, 600, 60000]);
  eq(RESEND_URL, "https://api.resend.com/emails");
  eq(CORS, {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  });
});

Deno.test("signatures: a signed, timely request passes; stale, wrong or missing is refused", async () => {
  const body = enc.encode('{"action":"flush","limit":10}');
  const sig = await signHex(SECRET, "1760000000", body);
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000100), { ok: true });
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1760000300), { ok: true }, "300 s late is still in time");
  eq(await verifyRequest(SECRET, "1760000000", sig, body, 1759999700), { ok: true }, "300 s early is still in time");
  eq(await verifyRequest(SECRET, "1760000000", sig.toUpperCase(), body, 1760000000), { ok: true }, "hex in capitals");
  // stale
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1760000301)).why, "x-corpus-ts is more than 5 minutes off");
  eq((await verifyRequest(SECRET, "1760000000", sig, body, 1759999699)).why, "x-corpus-ts is more than 5 minutes off");
  // wrong
  eq((await verifyRequest(SECRET, "1760000000", sig, enc.encode('{"action":"flush","limit":20}'), 1760000000)).why,
    "bad signature", "another body");
  eq((await verifyRequest(SECRET + "x", "1760000000", sig, body, 1760000000)).why, "bad signature", "another secret");
  eq((await verifyRequest(SECRET, "1760000001", sig, body, 1760000000)).why, "bad signature", "the ts is signed too");
  eq((await verifyRequest(SECRET, "1760000000", "0".repeat(64), body, 1760000000)).why, "bad signature");
  // missing or malformed
  eq((await verifyRequest(SECRET, null, sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "", sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000.5", sig, body, 1760000000)).why, "missing or malformed x-corpus-ts");
  eq((await verifyRequest(SECRET, "1760000000", null, body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", "", body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", sig.slice(2), body, 1760000000)).why, "missing or malformed x-corpus-sig");
  eq((await verifyRequest(SECRET, "1760000000", "z".repeat(64), body, 1760000000)).why, "missing or malformed x-corpus-sig");
  // the server's secret
  eq((await verifyRequest("short", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
  eq((await verifyRequest("", "1760000000", sig, body, 1760000000)).why, "server secret missing or too short");
});

Deno.test("gzip is undone, with a ceiling (4 MiB by default)", async () => {
  const gz = await gzip(enc.encode('{"action":"flush"}'));
  eq(new TextDecoder().decode(await gunzipLimited(gz)), '{"action":"flush"}');
  const big = await gzip(enc.encode("x".repeat(5000)));
  eq((await gunzipLimited(big)).length, 5000);
  let threw = "";
  try { await gunzipLimited(big, 100); } catch (e) { threw = (e as Error).message; }
  eq(threw, "body expands past 100 bytes");
  eq((await gunzipLimited(await gzip(new Uint8Array(MAX_JSON_BYTES)))).length, MAX_JSON_BYTES, "exactly the ceiling");
  threw = "";
  try { await gunzipLimited(await gzip(new Uint8Array(MAX_JSON_BYTES + 1))); } catch (e) { threw = (e as Error).message; }
  eq(threw, `body expands past ${MAX_JSON_BYTES} bytes`);
  threw = "";
  try { await gunzipLimited(enc.encode("not gzip at all")); } catch (e) { threw = (e as Error).message; }
  ok(threw.length > 0, "a body that is not gzip is refused");
});

Deno.test("parseBody: flush with a limit of 10 by default, clamped to 1..20; state; nothing else", () => {
  eq(parseBody({ action: "flush" }), { action: "flush", limit: 10 });
  eq(parseBody({ action: "flush", limit: null }), { action: "flush", limit: 10 });
  eq(parseBody({ action: "flush", limit: 1 }), { action: "flush", limit: 1 });
  eq(parseBody({ action: "flush", limit: 20 }), { action: "flush", limit: 20 });
  eq(parseBody({ action: "flush", limit: 7, extra: "ignored" }), { action: "flush", limit: 7 });
  for (const [given, want] of [[0, 1], [-5, 1], [0.5, 1], [21, 20], [1e9, 20], [2.7, 2], [19.99, 19]]) {
    eq(parseBody({ action: "flush", limit: given }), { action: "flush", limit: want }, `limit ${given}`);
  }
  for (const limit of ["5", true, [3], { n: 1 }, NaN, Infinity]) {
    eq(parseBody({ action: "flush", limit }), "limit: a number from 1 to 20", `limit ${String(limit)}`);
  }
  eq(parseBody({ action: "state" }), { action: "state", limit: 10 });
  eq(parseBody({ action: "state", limit: "x" }), { action: "state", limit: 10 }, "state ignores limit");
  for (const action of ["send", "claim", "hello", "pull", "FLUSH", "", null, ["flush"], undefined]) {
    eq(parseBody({ action }), "unknown action", `action ${JSON.stringify(action)}`);
  }
  eq(parseBody({}), "unknown action");
  for (const body of [[1], null, "flush", 3, true, undefined]) {
    eq(parseBody(body), "body must be a JSON object", `body ${JSON.stringify(body)}`);
  }
});

Deno.test("route: no key means configured false and nothing claimed; state is the desk's only", () => {
  const flush = { action: "flush" as const, limit: 10 };
  const state = { action: "state" as const, limit: 10 };
  eq(route(flush, "desk", false), { answer: { configured: false } });
  eq(route(flush, "user", false), { answer: { configured: false } });
  eq(route(flush, "desk", true), { flush: 10 });
  eq(route({ action: "flush", limit: 3 }, "user", true), { flush: 3 });
  eq(route(state, "desk", true), { answer: { configured: true, fn: "corner-mail 1.0" } });
  eq(route(state, "desk", false), { answer: { configured: false, fn: "corner-mail 1.0" } });
  eq(route(state, "user", true), { refuse: { status: 403, error: "state: for the desk only" } });
  eq(route(state, "user", false), { refuse: { status: 403, error: "state: for the desk only" } });
});

Deno.test("a signed-in person: a bearer header, and corner_me's first row with can_request true", () => {
  ok(isBearer("Bearer eyJhbGciOi.x.y"));
  ok(isBearer("bearer abc"));
  for (const h of [null, "", "Bearer", "Bearer ", "Basic abc", "abc", "Bearer a b"]) ok(!isBearer(h), `header ${h}`);
  ok(canRequest([{ can_request: true, is_editor: false }]));
  ok(canRequest([{ can_request: true }, { can_request: false }]), "only the first row counts");
  ok(!canRequest([{ can_request: false }, { can_request: true }]), "only the first row counts");
  for (const d of [[], null, undefined, { can_request: true }, [{ can_request: "true" }], [{ can_request: 1 }],
                   [{}], [null], "t", true]) {
    ok(!canRequest(d), `data ${JSON.stringify(d)}`);
  }
});

Deno.test("resendPayload: plain text, and reply_to only when the row has one", () => {
  eq(resendPayload(ROW), {
    from: "Srangam desk <desk@nartiang.org>", to: ["reader@example.org"],
    subject: "Srangam: request #12 is done - Find episodes in a text", text: "What you asked for ...",
  });
  for (const reply_to of [null, undefined, "", "   "]) {
    const p = resendPayload({ ...ROW, reply_to });
    ok(!("reply_to" in p), `no reply_to key for ${JSON.stringify(reply_to)}`);
    ok(!JSON.stringify(p).includes("reply_to"));
  }
  const { reply_to: _drop, ...noKey } = ROW;
  ok(!("reply_to" in resendPayload(noKey as MailRow)), "absent from the row");
  eq(resendPayload({ ...ROW, reply_to: "editors@nartiang.org" }), {
    from: "Srangam desk <desk@nartiang.org>", to: ["reader@example.org"],
    subject: "Srangam: request #12 is done - Find episodes in a text", text: "What you asked for ...",
    reply_to: "editors@nartiang.org",
  });
  eq(resendPayload({ ...ROW, reply_to: " editors@nartiang.org " }).reply_to, "editors@nartiang.org");
  eq(Object.keys(resendPayload({ ...ROW, reply_to: "a@b.org" })), ["from", "to", "subject", "text", "reply_to"]);
});

Deno.test("errorText: the status and the first 300 characters, at most 320 in all", () => {
  eq(errorText(422, '{"statusCode":422,"name":"validation_error"}'), '422: {"statusCode":422,"name":"validation_error"}');
  eq(errorText(502, ""), "502");
  eq(errorText(500, null), "500");
  eq(errorText("timeout", "no answer"), "timeout: no answer");
  eq(errorText(403, "line one\n  line two\r\n\tthree"), "403: line one line two three", "one line");
  eq(errorText(400, "a\u0000b"), "400: a b", "no NUL for Postgres");
  const long = "x".repeat(1000);
  const t = errorText(422, long);
  eq(t, "422: " + "x".repeat(300));
  ok(t.length <= 320);
  ok(errorText("s".repeat(400), long).length === 320, "a long status is cut too");
  const emoji = errorText(429, "\u{1F600}".repeat(400));   // 2 UTF-16 units each
  ok(emoji.length <= 320, "at most 320 units");
  ok(!/[\uD800-\uDBFF]$/.test(emoji), "a surrogate pair is never split");
  eq(emoji, "429: " + "\u{1F600}".repeat(150));
  eq(errorText(422, "y".repeat(299) + "\u{1F600}"), "422: " + "y".repeat(299), "a pair at the edge is left out whole");
});

Deno.test("summarize and statusCounts", () => {
  eq(summarize([]), { claimed: 0, sent: 0, failed: 0 });
  eq(summarize([{ ok: true }, { ok: false }, { ok: true }, { ok: true }]), { claimed: 4, sent: 3, failed: 1 });
  eq(summarize([{ ok: false }, { ok: false }]), { claimed: 2, sent: 0, failed: 2 });
  eq(statusCounts([]), {});
  eq(statusCounts([{ status: 200 }, { status: 422 }, { status: 200 }, { status: "timeout" }]),
    { "200": 2, "422": 1, "timeout": 1 });
});

// ---- sendOne, with fetch faked ----------------------------------------------------------------

type Seen = { url: string; init: RequestInit };
function fakeFetch(answer: (seen: Seen) => Promise<Response> | Response) {
  const seen: Seen[] = [];
  const fn = (url: string, init: RequestInit) => {
    const s = { url, init };
    seen.push(s);
    return Promise.resolve(answer(s));
  };
  return { fn, seen };
}

Deno.test("sendOne: one POST to Resend with the key and the JSON body; a 2xx is sent with its id", async () => {
  const f = fakeFetch(() => new Response('{"id":"49a3999c-0ce1-4ea6-ab68-afcd6dc2e794"}', { status: 200 }));
  const p = resendPayload({ ...ROW, reply_to: "editors@nartiang.org" });
  const o = await sendOne(p, KEY, f.fn);
  eq(o, { ok: true, status: 200, providerId: "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794", error: null });
  eq(f.seen.length, 1);
  eq(f.seen[0].url, "https://api.resend.com/emails");
  eq(f.seen[0].init.method, "POST");
  eq(f.seen[0].init.headers, { "Authorization": `Bearer ${KEY}`, "Content-Type": "application/json" });
  eq(JSON.parse(String(f.seen[0].init.body)), p);
  ok(f.seen[0].init.signal instanceof AbortSignal, "a signal for the timeout");
  ok(!JSON.stringify(o).includes(KEY) && !JSON.stringify(o).includes("reader@"), "no key or address in the outcome");

  eq(await sendOne(p, KEY, fakeFetch(() => new Response("", { status: 202 })).fn),
    { ok: true, status: 202, providerId: null, error: null }, "a 2xx without a JSON body is still sent");
  eq(await sendOne(p, KEY, fakeFetch(() => new Response('{"id":5}', { status: 200 })).fn),
    { ok: true, status: 200, providerId: null, error: null }, "an id that is not text is not kept");
});

Deno.test("sendOne: an error answer, a timeout and a network failure are not sent", async () => {
  const p = resendPayload(ROW);
  const msg = '{"statusCode":403,"message":"The nartiang.org domain is not verified.","name":"validation_error"}';
  eq(await sendOne(p, KEY, fakeFetch(() => new Response(msg, { status: 403 })).fn),
    { ok: false, status: 403, providerId: null, error: "403: " + msg });
  const long = await sendOne(p, KEY, fakeFetch(() => new Response("e".repeat(5000), { status: 500 })).fn);
  eq([long.ok, long.status, long.error], [false, 500, "500: " + "e".repeat(300)]);
  eq((await sendOne(p, KEY, fakeFetch(() => new Response("slow down", { status: 429 })).fn)).error, "429: slow down");

  // A Resend that never answers: aborted after the timeout (20 ms here, 10 s in the function).
  const hang = (_u: string, init: RequestInit) => new Promise<Response>((_res, rej) => {
    init.signal?.addEventListener("abort", () => rej(new DOMException("The signal has been aborted", "AbortError")));
  });
  const t0 = Date.now();
  eq(await sendOne(p, KEY, hang, 20),
    { ok: false, status: "timeout", providerId: null, error: "timeout: no answer from Resend within 0.02 s" });
  ok(Date.now() - t0 < 2000, "the timeout ends the wait");

  const down = () => Promise.reject(new TypeError("error sending request: connection refused"));
  eq(await sendOne(p, KEY, down),
    { ok: false, status: "network", providerId: null, error: "network: error sending request: connection refused" });
});

// ---- runFlush, with time, Resend and the database faked ---------------------------------------

function clock() {
  let t = 1_000_000;
  const sleeps: number[] = [];
  return {
    now: () => t,
    sleep: (ms: number) => { sleeps.push(ms); t += ms; return Promise.resolve(); },
    tick: (ms: number) => { t += ms; },
    sleeps,
  };
}
const SENT = (id: string): SendOutcome => ({ ok: true, status: 200, providerId: id, error: null });

Deno.test("runFlush: each row sent once and recorded, 0.6 s apart", async () => {
  const c = clock();
  const sent: unknown[] = [];
  const done: unknown[][] = [];
  const rows = [ROW, { ...ROW, id: 8, reply_to: "editors@nartiang.org" }, { ...ROW, id: 9 }];
  let n = 0;
  const out = await runFlush(rows, {
    now: c.now, sleep: c.sleep,
    send: (p) => {
      sent.push(p);
      c.tick(100);   // Resend takes 0.1 s
      n++;
      return Promise.resolve(n === 2 ? { ok: false, status: 422, providerId: null, error: "422: bad" } : SENT(`r${n}`));
    },
    done: (...a) => { done.push(a); return Promise.resolve(true); },
  });
  eq(sent, rows.map((r) => resendPayload(r as MailRow)));
  eq(done, [[7, true, "r1", null], [8, false, null, "422: bad"], [9, true, "r3", null]]);
  eq(out, [{ ok: true, status: 200, recorded: true }, { ok: false, status: 422, recorded: true },
           { ok: true, status: 200, recorded: true }]);
  eq(c.sleeps, [500, 500], "the first goes at once, the next 0.6 s after the one before started");
  eq(summarize(out), { claimed: 3, sent: 2, failed: 1 });
});

Deno.test("runFlush: out of time, the rest go back unsent; a record that fails is counted", async () => {
  const c = clock();
  const sent: number[] = [];
  const done: unknown[][] = [];
  const rows = [1, 2, 3, 4].map((id) => ({ ...ROW, id }));
  const out = await runFlush(rows, {
    now: c.now, sleep: c.sleep, budgetMs: 25_000,
    send: () => { sent.push(1); c.tick(10_000); return Promise.resolve(SENT("x")); },
    done: (id, ...rest) => {
      done.push([id, ...rest]);
      return id === 2 ? Promise.reject(new Error("db down")) : Promise.resolve(id !== 3);
    },
  });
  eq(sent.length, 3, "started at 0, 10 and 20 s; not at 30");
  eq(done[3], [4, false, null, "deferred: not sent: out of time in this round"]);
  eq(out.map((r) => [r.ok, r.status, r.recorded]),
    [[true, 200, true], [true, 200, false], [true, 200, false], [false, "deferred", true]]);
  eq(summarize(out), { claimed: 4, sent: 3, failed: 1 });
});

Deno.test("runFlush: rows without a usable id are neither sent nor recorded; a throwing send is a failure", async () => {
  const sent: unknown[] = [];
  const done: unknown[][] = [];
  const out = await runFlush([null, "x", { ...ROW, id: 0 }, { ...ROW, id: "7" }, { ...ROW, id: 1.5 }, { ...ROW, id: 3 }], {
    sleep: () => Promise.resolve(),
    send: (p) => { sent.push(p); return Promise.reject(new Error("boom")); },
    done: (...a) => { done.push(a); return Promise.resolve(true); },
  });
  eq(sent.length, 1);
  eq(done, [[3, false, null, "network: boom"]]);
  eq(out.map((r) => r.status), ["bad row", "bad row", "bad row", "bad row", "bad row", "network"]);
  eq(summarize(out), { claimed: 6, sent: 0, failed: 6 });
  eq(await runFlush([], { send: () => Promise.resolve(SENT("x")), done: () => Promise.resolve(true) }), []);
});
