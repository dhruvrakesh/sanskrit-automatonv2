#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_texts_search_2026_10_07.py  (2026-10-07)  SEARCH_TEXTS_C3A_2026_10_07

For the SRANGAM repo (run from D:\\srangam-42267, on main). Adds "Search the texts by meaning" to
/texts: a box above the list of texts, results as passages (title, reference, translation) with a
link to the right page of the reader. Nothing is generated; the hits are the published passages.

New files (refused if a different file already sits there):
  supabase/functions/search-texts/index.ts, lib.ts   public edge function: the question is embedded
      with gemini-embedding-001 (RETRIEVAL_QUERY, 1536 dims, as C2 stored), match_text_passages()
      runs with the ANON key so RLS shows published texts only; 3-300 characters, k <= 20,
      20 a minute per client per instance; each hit carries its position in the text.
  src/lib/corpusSearch.ts                            client: same contract as corpusTexts.ts (a
      failure is never "nothing found"); readerHref() -> /texts/<doc>?p=<page>#p<page_no>-<idx>
  src/components/texts/TextSearch.tsx                the search box and results
  src/__tests__/corpus-search.test.ts                vitest: failure vs empty, request body, links
Edits (anchored, all-or-nothing):
  supabase/config.toml             append [functions.search-texts] verify_jwt = false (as the others)
  src/pages/texts/TextsIndex.tsx   import and render <TextSearch /> above the list (only when texts load)
  src/pages/texts/TextReader.tsx   scroll to #p<page>-<idx> once the passages arrive (the browser looks
      for the anchor before they exist) and mark that passage; an in-page anchor click marks via :target

Backups .bak_textsearch_<date> for edited files; marker-idempotent.
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_texts_search_2026_10_07.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_texts_search_2026_10_07.py"
Then: npm run typecheck ; npx vitest run src/__tests__/corpus-search.test.ts src/__tests__/corpus-texts-loader.test.ts src/__tests__/query-bounds.test.ts ; npm run build
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "SEARCH_TEXTS_C3A_2026_10_07"

NEW_FILES = {
    'src/lib/corpusSearch.ts': '/**\n * Search the published texts by meaning - SEARCH_TEXTS_C3A_2026_10_07.\n *\n * Calls the edge function search-texts: the question becomes a gemini-embedding-001 query\n * vector (1536 dimensions) and match_text_passages() returns the nearest passages of\n * PUBLISHED texts only (row-level security, as /texts). Nothing is generated: the hits are\n * the passages themselves.\n *\n * Same contract as corpusTexts.ts: a failure is never shown as "nothing found". Check `ok`\n * first; `error` is non-null exactly when ok is false.\n */\nimport { supabase } from \'@/integrations/supabase/client\';\nimport { PASSAGES_PER_PAGE } from \'@/lib/corpusDisplay\';\n\nconst SEARCH_TIMEOUT_MS = 12000;\nexport const MIN_QUERY = 3;\nexport const MAX_QUERY = 300;\n\nexport interface SearchHit {\n  doc_code: string;\n  title: string;\n  ref: string;\n  page_no: number;\n  idx: number;\n  verse_ref: string | null;\n  translation: string;\n  similarity: number;\n  /** 1-based position of the passage in its text, in the reader\'s order; null if unknown. */\n  ordinal: number | null;\n}\n\nexport interface SearchResult {\n  ok: boolean;\n  rows: SearchHit[];\n  /** Non-null exactly when ok === false. */\n  error: string | null;\n}\n\nconst fail = (error: string): SearchResult => ({ ok: false, rows: [], error });\n\nasync function errorText(err: any): Promise<string> {\n  try {\n    const j = await err?.context?.json?.();\n    if (j && j.error) return String(j.error);\n  } catch {\n    /* the body was not JSON; fall through */\n  }\n  return err?.message ? String(err.message) : \'The search failed.\';\n}\n\nexport async function searchTexts(q: string, opts: { k?: number; docCodes?: string[] } = {}): Promise<SearchResult> {\n  const query = (q ?? \'\').replace(/\\s+/g, \' \').trim();\n  if (query.length < MIN_QUERY) return fail(`Type at least ${MIN_QUERY} characters.`);\n  const body: Record<string, unknown> = { q: query.slice(0, MAX_QUERY), k: opts.k ?? 10 };\n  if (opts.docCodes && opts.docCodes.length) body.doc_codes = opts.docCodes;\n  const call = (supabase as any).functions.invoke(\'search-texts\', { body });\n  const timeout = new Promise<any>((resolve) => setTimeout(() => resolve({ __timeout: true }), SEARCH_TIMEOUT_MS));\n  const res = await Promise.race([call, timeout]);\n  if (res && res.__timeout) return fail(\'The search took too long. Please try again.\');\n  if (res && res.error) return fail(await errorText(res.error));\n  const rows = res && res.data && Array.isArray(res.data.results) ? (res.data.results as SearchHit[]) : null;\n  if (!rows) return fail(\'The search answered in an unexpected form.\');\n  return { ok: true, rows, error: null };\n}\n\n/** The reader page that holds a hit, with its passage anchor: /texts/<doc>?p=<page>#p<page_no>-<idx>. */\nexport function readerHref(h: Pick<SearchHit, \'doc_code\' | \'page_no\' | \'idx\' | \'ordinal\'>): string {\n  const base = `/texts/${encodeURIComponent(h.doc_code)}`;\n  const anchor = `#p${h.page_no}-${h.idx}`;\n  if (!h.ordinal || h.ordinal < 1) return base + anchor;\n  const page = Math.ceil(h.ordinal / PASSAGES_PER_PAGE);\n  return (page > 1 ? `${base}?p=${page}` : base) + anchor;\n}\n',
    'src/components/texts/TextSearch.tsx': '/**\n * Search the published texts by meaning - SEARCH_TEXTS_C3A_2026_10_07.\n * Shown on /texts. Results are passages (with their reference and a link to the right page of the\n * reader), never a generated answer.\n */\nimport { FormEvent, useState } from \'react\';\nimport { Link } from \'react-router-dom\';\nimport { useMutation } from \'@tanstack/react-query\';\nimport { AlertTriangle, Loader2, Search } from \'lucide-react\';\nimport { Button } from \'@/components/ui/button\';\nimport { Card, CardContent } from \'@/components/ui/card\';\nimport { Input } from \'@/components/ui/input\';\nimport { displayTranslation, passageLabel } from \'@/lib/corpusDisplay\';\nimport { MAX_QUERY, MIN_QUERY, readerHref, searchTexts } from \'@/lib/corpusSearch\';\n\nconst SNIPPET = 420;\n\nexport default function TextSearch({ docCodes }: { docCodes?: string[] }) {\n  const [q, setQ] = useState(\'\');\n  const m = useMutation({ mutationFn: (query: string) => searchTexts(query, { k: 10, docCodes }) });\n  const r = m.data;\n  const ready = q.trim().length >= MIN_QUERY;\n\n  const submit = (e: FormEvent) => {\n    e.preventDefault();\n    if (ready && !m.isPending) m.mutate(q);\n  };\n\n  return (\n    <section aria-labelledby="text-search-heading" className="mb-8">\n      <Card>\n        <CardContent className="pt-6">\n          <h2 id="text-search-heading" className="font-serif text-lg font-semibold text-foreground">\n            Search the texts by meaning\n          </h2>\n          <p className="mt-1 text-sm text-muted-foreground">\n            Ask in plain English. This finds passages whose translation is closest in meaning, not only\n            the same words. The passages are shown as published; nothing is written for you.\n          </p>\n          <form onSubmit={submit} role="search" className="mt-4 flex flex-col sm:flex-row gap-2">\n            <label htmlFor="text-search-q" className="sr-only">Search the texts</label>\n            <Input\n              id="text-search-q"\n              value={q}\n              maxLength={MAX_QUERY}\n              onChange={(e) => setQ(e.target.value)}\n              placeholder="e.g. why did the king sell his wife and son?"\n            />\n            <Button type="submit" disabled={!ready || m.isPending} className="sm:w-32">\n              {m.isPending\n                ? <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />\n                : <Search className="w-4 h-4 mr-2" aria-hidden="true" />}\n              Search\n            </Button>\n          </form>\n\n          <div aria-live="polite" className="mt-4">\n            {r && !r.ok && (\n              <p role="alert" className="flex items-start gap-2 text-sm text-amber-800 dark:text-amber-200">\n                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />\n                <span>{r.error}</span>\n              </p>\n            )}\n            {r && r.ok && r.rows.length === 0 && (\n              <p className="text-sm text-muted-foreground">No passage of a published text matched. Try other words.</p>\n            )}\n            {r && r.ok && r.rows.length > 0 && (\n              <ol className="space-y-4">\n                {r.rows.map((h) => {\n                  const t = displayTranslation(h.translation);\n                  return (\n                    <li key={`${h.doc_code}-${h.ref}`} className="border-b border-border pb-4 last:border-b-0">\n                      <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">\n                        <span className="font-serif text-sm text-foreground">{h.title}</span>\n                        <span className="font-mono">{passageLabel(h)}</span>\n                      </div>\n                      <p lang="en" className="mt-1 font-serif text-sm leading-relaxed whitespace-pre-line text-foreground">\n                        {t.length > SNIPPET ? `${t.slice(0, SNIPPET).trimEnd()}...` : t}\n                      </p>\n                      <Link to={readerHref(h)} className="mt-1 inline-block text-xs text-burgundy hover:underline">\n                        Read it in the text\n                      </Link>\n                    </li>\n                  );\n                })}\n              </ol>\n            )}\n          </div>\n        </CardContent>\n      </Card>\n    </section>\n  );\n}\n',
    'src/__tests__/corpus-search.test.ts': 'import { describe, it, expect, vi, beforeEach } from \'vitest\';\n\n// SEARCH_TEXTS_C3A_2026_10_07 - the search client keeps "failed" distinct from "nothing found",\n// and links each hit to the reader page that holds it.\nconst state: { res: any; calls: any[] } = { res: null, calls: [] };\n\nvi.mock(\'@/integrations/supabase/client\', () => ({\n  supabase: {\n    functions: {\n      invoke: (name: string, opts: any) => { state.calls.push({ name, opts }); return Promise.resolve(state.res); },\n    },\n  },\n}));\n\nimport { readerHref, searchTexts } from \'@/lib/corpusSearch\';\n\nbeforeEach(() => { state.res = { data: { results: [] }, error: null }; state.calls = []; });\n\ndescribe(\'searchTexts\', () => {\n  it(\'nothing found is ok:true with no rows\', async () => {\n    const r = await searchTexts(\'why did the king sell his wife\');\n    expect(r).toEqual({ ok: true, rows: [], error: null });\n    expect(state.calls[0].name).toBe(\'search-texts\');\n    expect(state.calls[0].opts.body).toEqual({ q: \'why did the king sell his wife\', k: 10 });\n  });\n\n  it(\'a failure is ok:false with the server message, never an empty list\', async () => {\n    state.res = { data: null, error: { message: \'non-2xx\', context: { json: () => Promise.resolve({ error: \'Too many searches in a minute.\' }) } } };\n    const r = await searchTexts(\'dharma\');\n    expect(r.ok).toBe(false);\n    expect(r.error).toBe(\'Too many searches in a minute.\');\n  });\n\n  it(\'an unexpected answer is a failure too\', async () => {\n    state.res = { data: { nope: 1 }, error: null };\n    expect((await searchTexts(\'dharma\')).ok).toBe(false);\n  });\n\n  it(\'refuses a too-short question without calling the server, and passes doc codes\', async () => {\n    expect((await searchTexts(\'  a \')).ok).toBe(false);\n    expect(state.calls.length).toBe(0);\n    await searchTexts(\'dharma\', { docCodes: [\'markandeya_purana\'], k: 5 });\n    expect(state.calls[0].opts.body).toEqual({ q: \'dharma\', k: 5, doc_codes: [\'markandeya_purana\'] });\n  });\n});\n\ndescribe(\'readerHref\', () => {\n  it(\'page 1 has no ?p, later pages do, the anchor is the passage\', () => {\n    expect(readerHref({ doc_code: \'markandeya_purana\', page_no: 1, idx: 4, ordinal: 4 })).toBe(\'/texts/markandeya_purana#p1-4\');\n    expect(readerHref({ doc_code: \'markandeya_purana\', page_no: 60, idx: 10, ordinal: 1001 })).toBe(\'/texts/markandeya_purana?p=21#p60-10\');\n    expect(readerHref({ doc_code: \'markandeya_purana\', page_no: 60, idx: 10, ordinal: 1000 })).toBe(\'/texts/markandeya_purana?p=20#p60-10\');\n  });\n  it(\'without a position it still opens the text\', () => {\n    expect(readerHref({ doc_code: \'a b\', page_no: 2, idx: 3, ordinal: null })).toBe(\'/texts/a%20b#p2-3\');\n  });\n});\n',
    'supabase/functions/search-texts/index.ts': '/**\n * search-texts (C3a, docs/CLOUD_BRAIN_2026-10-07.md)  SEARCH_TEXTS_C3A_2026_10_07\n *\n * Public: search the PUBLISHED Sanskrit texts (/texts) by meaning.\n *   POST { q: "why did Hariscandra sell his wife", k?: 1-20 (8), doc_codes?: ["markandeya_purana"] }\n *   -> { q, results: [{ doc_code, title, ref, page_no, idx, verse_ref, translation, similarity, ordinal }], took_ms }\n *      ordinal = the passage\'s position in its text in the reader\'s order, for a link to the right page.\n *\n * - The question is embedded as RETRIEVAL_QUERY with gemini-embedding-001 at 1536 dimensions\n *   (the size C2 stored, RECALL_768_2026_10_07). About $0.000003 a question.\n * - match_text_passages() is called with the ANON key, so row-level security decides what is\n *   visible: published texts only, exactly what /texts shows.\n * - No text is generated: the reader sees the passages and their references, nothing invented.\n * - Brakes: questions of 3-300 characters, k <= 20, 20 requests a minute per client per\n *   instance, and a small cache so a repeated question is not embedded twice.\n * Secrets: SUPABASE_URL, SUPABASE_ANON_KEY, GEMINI_API_KEY (all already present for other functions).\n */\nimport { serve } from \'https://deno.land/std@0.168.0/http/server.ts\';\nimport { createClient } from \'https://esm.sh/@supabase/supabase-js@2.58.0\';\nimport { embedQuery, type MatchRow, parseInput, RateLimiter, shapeResults, toHalfvecLiteral, VectorCache } from \'./lib.ts\';\n\nconst corsHeaders = {\n  \'Access-Control-Allow-Origin\': \'*\',\n  \'Access-Control-Allow-Headers\': \'authorization, x-client-info, apikey, content-type\',\n  \'Access-Control-Allow-Methods\': \'POST, OPTIONS\',\n};\nconst limiter = new RateLimiter(20, 60_000);\nconst cache = new VectorCache(200);\n\nfunction json(status: number, body: unknown): Response {\n  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders, \'Content-Type\': \'application/json\' } });\n}\n\nserve(async (req) => {\n  if (req.method === \'OPTIONS\') return new Response(null, { headers: corsHeaders });\n  if (req.method !== \'POST\') return json(405, { error: \'Use POST.\' });\n  const t0 = Date.now();\n\n  const client = (req.headers.get(\'x-forwarded-for\') ?? \'\').split(\',\')[0].trim() || \'unknown\';\n  if (!limiter.allow(client)) return json(429, { error: \'Too many searches in a minute. Please wait a little.\' });\n\n  const input = parseInput(await req.json().catch(() => ({})));\n  if (\'error\' in input) return json(400, { error: input.error });\n\n  const url = Deno.env.get(\'SUPABASE_URL\') ?? \'\';\n  const anon = Deno.env.get(\'SUPABASE_ANON_KEY\') ?? \'\';\n  const key = Deno.env.get(\'GEMINI_API_KEY\') ?? \'\';\n  if (!url || !anon || !key) return json(500, { error: \'Search is not configured.\' });\n\n  try {\n    let vec = cache.get(input.q);\n    if (!vec) { vec = await embedQuery(fetch, key, input.q); cache.set(input.q, vec); }\n\n    const sb = createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });\n    const { data, error } = await sb.rpc(\'match_text_passages\', {\n      query_embedding: toHalfvecLiteral(vec), match_count: input.k, doc_codes: input.docCodes,\n    });\n    if (error) return json(502, { error: \'Search failed.\', detail: error.message });\n    const rows = (data ?? []) as MatchRow[];\n\n    const codes = [...new Set(rows.map((r) => r.doc_code))];\n    const titles: Record<string, string> = {};\n    const textIds: Record<string, string> = {};\n    if (codes.length) {\n      const { data: t } = await sb.from(\'srangam_texts\').select(\'id, doc_code, title\').in(\'doc_code\', codes).limit(50);\n      for (const r of (t ?? []) as { id: string; doc_code: string; title: string }[]) {\n        titles[r.doc_code] = r.title; textIds[r.doc_code] = r.id;\n      }\n    }\n    // Where each passage sits in its text, in the reader\'s own order (page_no, idx), so the page can\n    // link to the right page of /texts/:docCode. One count per hit (k <= 20), in parallel.\n    const ordinals = await Promise.all(rows.map(async (r) => {\n      const id = textIds[r.doc_code];\n      if (!id) return null;\n      const { count, error: cErr } = await sb.from(\'srangam_text_passages\')\n        .select(\'id\', { count: \'exact\', head: true })\n        .eq(\'text_id\', id)\n        .or(`page_no.lt.${r.page_no},and(page_no.eq.${r.page_no},idx.lt.${r.idx})`);\n      return cErr || count === null ? null : count + 1;\n    }));\n    const results = shapeResults(rows, titles).map((h, i) => ({ ...h, ordinal: ordinals[i] }));\n    return json(200, { q: input.q, results, took_ms: Date.now() - t0 });\n  } catch (e) {\n    console.error(JSON.stringify({ fn: \'search-texts\', error: String((e as Error)?.message ?? e).slice(0, 300) }));\n    return json(502, { error: \'Search is unavailable just now.\' });\n  }\n});\n',
    'supabase/functions/search-texts/lib.ts': '// C3a - search-texts: search the PUBLISHED Sanskrit texts by meaning. The logic, free of network\n// imports so `deno test lib_test.ts` runs offline. SEARCH_TEXTS_C3A_2026_10_07.\n//\n// A question is embedded with the same model and size as the passages (gemini-embedding-001,\n// 1536 dimensions, C2) but as a RETRIEVAL_QUERY, then match_text_passages() (C1, SECURITY\n// INVOKER, called with the anon key so row-level security applies) returns the nearest passages\n// of published texts. No answer is generated here: the reader sees the passages themselves.\n\nexport const EMBED_MODEL = "gemini-embedding-001";\nexport const EMBED_DIMS = 1536;\nexport const EMBED_URL =\n  "https://generativelanguage.googleapis.com/v1beta/models/" + EMBED_MODEL + ":embedContent";\nexport const MAX_QUERY_CHARS = 300;\nexport const MAX_K = 20;\nexport const DOC_CODE_RE = /^[A-Za-z0-9_.-]{1,80}$/;\n\nexport interface SearchInput { q: string; k: number; docCodes: string[] | null }\n\nexport function parseInput(body: unknown): SearchInput | { error: string } {\n  const b = (body ?? {}) as Record<string, unknown>;\n  const q = typeof b.q === "string" ? b.q.replace(/\\s+/g, " ").trim() : "";\n  if (q.length < 3) return { error: "Ask with at least 3 characters." };\n  if (q.length > MAX_QUERY_CHARS) return { error: `Keep the question under ${MAX_QUERY_CHARS} characters.` };\n  const kRaw = typeof b.k === "number" ? b.k : typeof b.k === "string" ? Number(b.k) : 8;\n  const k = Number.isFinite(kRaw) ? Math.min(MAX_K, Math.max(1, Math.trunc(kRaw))) : 8;\n  let docCodes: string[] | null = null;\n  if (Array.isArray(b.doc_codes) && b.doc_codes.length) {\n    const codes = b.doc_codes.filter((c): c is string => typeof c === "string" && DOC_CODE_RE.test(c)).slice(0, 10);\n    if (codes.length !== b.doc_codes.length) return { error: "doc_codes must be up to 10 text codes." };\n    docCodes = codes;\n  }\n  return { q, k, docCodes };\n}\n\nexport function normalise(v: number[]): number[] {\n  let s = 0;\n  for (const x of v) {\n    if (!Number.isFinite(x)) throw new Error("embedding contains a non-finite value");\n    s += x * x;\n  }\n  const n = Math.sqrt(s);\n  if (n === 0) throw new Error("embedding is all zeros");\n  return v.map((x) => x / n);\n}\n\nexport function toHalfvecLiteral(v: number[]): string {\n  return "[" + v.map((x) => (Math.abs(x) < 5e-6 ? "0" : x.toFixed(5))).join(",") + "]";\n}\n\nexport function buildQueryRequest(q: string) {\n  return {\n    model: "models/" + EMBED_MODEL,\n    content: { parts: [{ text: q }] },\n    taskType: "RETRIEVAL_QUERY",\n    outputDimensionality: EMBED_DIMS,\n  };\n}\n\ntype FetchFn = (url: string, init: RequestInit) => Promise<Response>;\n\n/** One embedContent call; one retry on 429/5xx after 1 s. The key travels in a header. */\nexport async function embedQuery(fetchFn: FetchFn, apiKey: string, q: string,\n                                 sleep: (ms: number) => Promise<void> = (ms) => new Promise((r) => setTimeout(r, ms))): Promise<number[]> {\n  const body = JSON.stringify(buildQueryRequest(q));\n  let last = "";\n  for (let attempt = 0; attempt < 2; attempt++) {\n    const res = await fetchFn(EMBED_URL, {\n      method: "POST",\n      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },\n      body,\n    });\n    if (res.ok) {\n      const j = await res.json() as { embedding?: { values?: number[] } };\n      const v = j?.embedding?.values;\n      if (!Array.isArray(v) || v.length !== EMBED_DIMS) {\n        throw new Error(`the query embedding has ${Array.isArray(v) ? v.length : "no"} values, expected ${EMBED_DIMS}`);\n      }\n      return normalise(v);\n    }\n    last = `Gemini ${res.status}`;\n    if (res.status !== 429 && res.status < 500) break;\n    if (attempt === 0) await sleep(1000);\n  }\n  throw new Error(last);\n}\n\n/** Per-instance limiter: at most `max` requests per `windowMs` from one client key. Edge instances\n *  are short-lived and several may run, so this is a brake on bursts, not an accounting system. */\nexport class RateLimiter {\n  private hits = new Map<string, number[]>();\n  constructor(private max = 20, private windowMs = 60_000, private now: () => number = Date.now) {}\n  allow(key: string): boolean {\n    const t = this.now();\n    const recent = (this.hits.get(key) ?? []).filter((x) => t - x < this.windowMs);\n    if (recent.length >= this.max) { this.hits.set(key, recent); return false; }\n    recent.push(t); this.hits.set(key, recent);\n    if (this.hits.size > 5000) this.hits.clear(); // never let the map grow without bound\n    return true;\n  }\n}\n\n/** Small LRU of query -> vector, so a repeated question costs no second embedding call. */\nexport class VectorCache {\n  private m = new Map<string, number[]>();\n  constructor(private size = 200) {}\n  get(q: string): number[] | undefined {\n    const k = q.toLowerCase(); const v = this.m.get(k);\n    if (v) { this.m.delete(k); this.m.set(k, v); }\n    return v;\n  }\n  set(q: string, v: number[]) {\n    const k = q.toLowerCase(); this.m.delete(k); this.m.set(k, v);\n    if (this.m.size > this.size) this.m.delete(this.m.keys().next().value as string);\n  }\n}\n\nexport interface MatchRow {\n  passage_id: string; doc_code: string; page_no: number; idx: number; verse_ref: string | null;\n  translation: string; similarity: number;\n}\n\nexport function shapeResults(rows: MatchRow[], titles: Record<string, string>) {\n  return rows.map((r) => ({\n    doc_code: r.doc_code,\n    title: titles[r.doc_code] ?? r.doc_code,\n    ref: `${r.page_no}.${r.idx}`,\n    page_no: r.page_no,\n    idx: r.idx,\n    verse_ref: r.verse_ref,\n    translation: r.translation,\n    similarity: Math.round(r.similarity * 1000) / 1000,\n  }));\n}\n',
}

EDITS = {
    "src/pages/texts/TextsIndex.tsx": [
        ("import", "import { listPublishedTexts } from '@/lib/corpusTexts';\n",
         "import { listPublishedTexts } from '@/lib/corpusTexts';\n"
         "import TextSearch from '@/components/texts/TextSearch';   // SEARCH_TEXTS_C3A_2026_10_07\n"),
        ("render", "      </header>\n\n      {q.isLoading && (\n",
         "      </header>\n\n"
         "      {r && r.ok && r.rows.length > 0 && <TextSearch />}\n\n"
         "      {q.isLoading && (\n"),
    ],
    "src/pages/texts/TextReader.tsx": [
        ("import", "import { Helmet } from 'react-helmet-async';\nimport { Link, useParams, useSearchParams } from 'react-router-dom';\n",
         "import { useEffect, useState } from 'react';\n"
         "import { Helmet } from 'react-helmet-async';\nimport { Link, useParams, useSearchParams } from 'react-router-dom';\n"),
        ("scroll", "  const passages = passQ.data;\n",
         "  const passages = passQ.data;\n\n"
         "  // SEARCH_TEXTS_C3A_2026_10_07: a link from search lands here with #p<page>-<idx>. The browser looks\n"
         "  // for that anchor before the passages exist (and :target never applies to a later element), so\n"
         "  // once they have arrived, scroll to it and mark it.\n"
         "  const [arrived, setArrived] = useState<string | null>(null);\n"
         "  useEffect(() => {\n"
         "    const h = window.location.hash;\n"
         "    if (!h || !passages || !passages.ok || !/^#p\\d+-\\d+$/.test(h)) return;\n"
         "    const el = document.getElementById(h.slice(1));\n"
         "    if (!el) return;\n"
         "    setArrived(h.slice(1));\n"
         "    el.scrollIntoView({ behavior: 'smooth', block: 'start' });\n"
         "  }, [passages]);\n"),
        ("highlight", '<li key={p.id} id={`p${p.page_no}-${p.idx}`} className="border-b border-border pb-6 last:border-b-0">',
         '<li key={p.id} id={`p${p.page_no}-${p.idx}`} className={`border-b border-border pb-6 last:border-b-0 scroll-mt-24 '
         'target:rounded-md target:bg-amber-50/70 target:px-3 dark:target:bg-amber-950/30${'
         'arrived === `p${p.page_no}-${p.idx}` ? \' rounded-md bg-amber-50/70 px-3 dark:bg-amber-950/30\' : \'\'}`}>'),
    ],
}


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=".", help="the Srangam repo root (default: the current folder)")
    args = ap.parse_args()
    root = Path(args.root)
    if not (root / "src" / "pages" / "texts" / "TextsIndex.tsx").exists():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267) or pass --root."); return 2
    problems, writes, creates = [], [], []
    for rel, edits in EDITS.items():
        p = root / rel
        src, nl = load(p)
        if MARK in src:
            continue
        for label, old, new in edits:
            c = src.count(old)
            if c != 1:
                problems.append("%s %s: matched %d times, expected 1" % (rel, label, c))
            else:
                src = src.replace(old, new)
        writes.append((p, src, nl))
    for rel, text in NEW_FILES.items():
        p = root / rel
        if p.exists():
            if load(p)[0] == text:
                continue
            problems.append("%s exists with other content; not overwriting" % rel)
        else:
            creates.append((p, text))
    # config.toml: the gateway's JWT check off, as for every other function here (auth-gate.ts note);
    # this function is public by design and does its own input limits. Appended once, never edited.
    cfg = root / "supabase" / "config.toml"
    cfg_add = None
    if cfg.exists():
        ctext, cnl = load(cfg)
        if "[functions.search-texts]" not in ctext:
            cfg_add = (cfg, ctext.rstrip("\n") + "\n\n[functions.search-texts]\nverify_jwt = false\n", cnl)
    else:
        problems.append("supabase/config.toml not found")
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if cfg_add:
        writes.append(cfg_add)
    if not writes and not creates:
        print("Already applied (%s). Nothing to do." % MARK); return 0
    if args.check:
        print("CHECK OK: %d file(s) to edit, %d to create. Nothing written." % (len(writes), len(creates))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    for p, text, nl in writes:
        shutil.copy2(p, p.with_name(p.name + ".bak_textsearch_" + stamp))
        t = p.with_name(p.name + ".tmp_textsearch"); t.write_bytes(text.replace("\n", nl).encode("utf-8")); os.replace(t, p)
        print("edited  %s" % p)
    for p, text in creates:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        print("created %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
