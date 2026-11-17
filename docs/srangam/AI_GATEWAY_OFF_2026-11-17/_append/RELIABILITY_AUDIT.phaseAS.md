## Phase AS - The last two AI calls off the Lovable AI Gateway (AI_GATEWAY_OFF_2026_11_17, 2026-11-17)

Asked on 17 Nov: "I1: move the two site functions off the Lovable gateway". The project's rule (Phase H.2d,
_shared/ai-provider.ts): every AI call uses the project's own keys, GEMINI_API_KEY first and OPENAI_API_KEY second,
never the Lovable AI Gateway, with one usage ledger (srangam_ai_usage, Phase T.1). On 17 Nov two edge functions still
called https://ai.gateway.lovable.dev with LOVABLE_API_KEY: detect-duplicate-articles (google/gemini-2.5-flash) and
suggest-tag-categories (google/gemini-3-flash-preview). No other file under supabase/functions named the gateway.

### AS.1 - What changes
- supabase/functions/detect-duplicate-articles/index.ts: the AI comparison of two excerpts calls aiExtractCitations
  (ai-provider's generic structured-JSON call: Gemini 2.5 Flash, one retry on 429/5xx, then OpenAI gpt-4o-mini),
  with telemetry function_name 'detect-duplicate-articles', purpose 'duplicate_check'. With neither key it says "AI
  not available" as before; when both keys fail it says "AI API error (Gemini and OpenAI keys)" and the exact, title
  and hash checks decide as before.
- supabase/functions/suggest-tag-categories/index.ts: the same call, purpose 'tag_categories'; the prompt, the
  examples and the response's shape are unchanged. With neither key: "AI service not configured" (500), as before;
  a 429 from the keys says so (429); any other failure "AI categorization failed (Gemini and OpenAI keys)" (500). The
  gateway's 402 ("AI credits exhausted") is gone with the gateway.
- src/__tests__/ai-gateway-off.test.ts: new; fails if any file under supabase/functions names ai.gateway.lovable.dev
  or LOVABLE_API_KEY, or if the two functions stop calling ai-provider with their telemetry.

### AS.2 - Not done, named
- The site runs the new code only once both functions are deployed again (asked of Lovable); until then the deployed
  versions still call the gateway.
- The LOVABLE_API_KEY secret is not removed here; nothing in the repository reads it now.
- Tag suggestions move from Gemini 3 Flash (preview) to Gemini 2.5 Flash; their quality was not compared.

### Invariants added (Phase AS)
69. No edge function calls the Lovable AI Gateway or reads LOVABLE_API_KEY: every AI call goes through
    _shared/ai-provider.ts on the project's own Gemini key first and its OpenAI key second, and is logged in
    srangam_ai_usage; when both keys fail the function says so and calls nothing else.
