import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.38.4";

import { requireAdmin } from '../_shared/auth-gate.ts';
// AI_GATEWAY_OFF_2026_11_17: the project's own keys, Gemini first and OpenAI second (_shared/ai-provider.ts);
// never the Lovable AI Gateway. aiExtractCitations is ai-provider's generic structured-JSON call.
import { aiExtractCitations } from '../_shared/ai-provider.ts';
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version',
};

// Phase 19a: Fetch historical examples per category for context
async function fetchCategoryExamples(supabase: any) {
  const categories = ['Period', 'Concept', 'Location', 'Methodology', 'Subject'];
  const examples: Record<string, any[]> = {};
  
  for (const category of categories) {
    const { data } = await supabase
      .from('srangam_tags')
      .select('tag_name, usage_count')
      .eq('category', category)
      .order('usage_count', { ascending: false })
      .limit(10);
    
    examples[category.toLowerCase()] = data || [];
  }
  
  return examples;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }
  const __gate = await requireAdmin(req);
  if (__gate.error) return __gate.error;

  const startTime = Date.now();

  try {
    const { tags } = await req.json();

    if (!tags || !Array.isArray(tags) || tags.length === 0) {
      return new Response(
        JSON.stringify({ error: 'Tags array is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // AI_GATEWAY_OFF_2026_11_17: the project's own Gemini key, else its OpenAI key
    if (!Deno.env.get("GEMINI_API_KEY") && !Deno.env.get("OPENAI_API_KEY")) {
      console.error("Neither GEMINI_API_KEY nor OPENAI_API_KEY is configured");
      return new Response(
        JSON.stringify({ error: "AI service not configured" }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Initialize Supabase client to fetch historical context
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Phase 19a: Fetch existing categorized tags as examples
    console.log(`🔍 Fetching category examples for context...`);
    const categoryExamples = await fetchCategoryExamples(supabase);
    
    const exampleCounts = Object.entries(categoryExamples)
      .map(([cat, tags]) => `${cat}: ${tags.length}`)
      .join(', ');
    console.log(`📚 Found examples: ${exampleCounts}`);

    console.log(`🤖 Suggesting categories for ${tags.length} tags with historical context...`);

    // Phase 19a: Enhanced system prompt with historical examples
    const systemPrompt = `You are an expert in academic taxonomy and South Asian studies. Your task is to categorize tags consistently with existing categorizations.

EXISTING CATEGORIZATIONS (follow these patterns):

**Period** (Historical eras, dynasties, time periods):
${categoryExamples.period.map(t => `- "${t.tag_name}" (used ${t.usage_count}×)`).join('\n') || '- No examples yet'}

**Concept** (Abstract ideas, practices, themes):
${categoryExamples.concept.map(t => `- "${t.tag_name}" (used ${t.usage_count}×)`).join('\n') || '- No examples yet'}

**Location** (Geographical places, regions):
${categoryExamples.location.map(t => `- "${t.tag_name}" (used ${t.usage_count}×)`).join('\n') || '- No examples yet'}

**Methodology** (Research methods, academic approaches):
${categoryExamples.methodology.map(t => `- "${t.tag_name}" (used ${t.usage_count}×)`).join('\n') || '- No examples yet'}

**Subject** (Specific topics, religions, traditions):
${categoryExamples.subject.map(t => `- "${t.tag_name}" (used ${t.usage_count}×)`).join('\n') || '- No examples yet'}

CATEGORY DEFINITIONS:
- Period: Historical eras, dynasties, empires, centuries, time periods (e.g., "Mauryan Empire", "Vedic Period", "Medieval Period", "7th Century CE")
- Concept: Abstract ideas, practices, themes, processes (e.g., "Maritime Trade", "Ritual Practices", "Religious Pluralism", "Cultural Exchange")
- Location: Geographical places, regions, cities, water bodies (e.g., "Tamil Nadu", "Kerala", "Indian Ocean", "Thanjavur")
- Methodology: Research methods, academic approaches, disciplines (e.g., "Epigraphy", "Archaeological Survey", "Textual Analysis", "Comparative Study")
- Subject: Specific topics, religions, traditions, art forms (e.g., "Buddhism", "Shaivism", "Sanskrit Literature", "Temple Architecture")

GUIDELINES:
1. Match new tags to the category of similar existing tags
2. Personal names (e.g., "Baba Ala Singh", "Raja Chola") → Subject
3. Dynasties and empires → Period
4. Geographic features and places → Location
5. Religious practices and traditions → Subject
6. Trade routes and exchange patterns → Concept

Return a JSON object with this exact structure:
{
  "suggestions": [
    {
      "tagId": "tag-id-here",
      "category": "Period|Concept|Location|Methodology|Subject",
      "reasoning": "Brief explanation referencing similar existing tags"
    }
  ]
}`;

    const userPrompt = `Categorize these tags consistently with the existing taxonomy:\n\n${tags.map((t: any) => 
      `- "${t.tag_name}" (ID: ${t.id}, Usage: ${t.usage_count || 0}${t.description ? `, Description: ${t.description}` : ''})`
    ).join('\n')}`;

    // AI_GATEWAY_OFF_2026_11_17: Gemini 2.5 Flash on the project's key, OpenAI gpt-4o-mini if Gemini fails
    let content = '';
    try {
      const ai = await aiExtractCitations({
        system: systemPrompt,
        user: userPrompt,
        timeoutMs: 60_000,
        telemetry: { function_name: 'suggest-tag-categories', purpose: 'tag_categories' },
      });
      console.log(`AI categorization by ${ai.provider} ${ai.model} in ${ai.latency_ms}ms`);
      content = ai.raw;
    } catch (aiError) {
      // both own keys failed (Gemini, then OpenAI): said plainly, never sent to another gateway
      const detail = aiError instanceof Error ? aiError.message : String(aiError);
      console.error("AI error (Gemini and OpenAI keys):", detail);
      if (/\b429\b/.test(detail)) {
        return new Response(
          JSON.stringify({ error: "Rate limit or quota reached on the project's Gemini and OpenAI keys. Please try again later or recharge a key." }),
          { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      return new Response(
        JSON.stringify({ error: "AI categorization failed (Gemini and OpenAI keys)", detail: detail.slice(0, 200) }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (!content) {
      console.error('No content in AI response');
      return new Response(
        JSON.stringify({ error: 'AI returned empty response' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Parse JSON from response (handle markdown code blocks)
    let jsonContent = content;
    const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      jsonContent = jsonMatch[1].trim();
    }
    
    let parsed;
    try {
      parsed = JSON.parse(jsonContent);
    } catch (parseError) {
      console.error('Failed to parse AI response:', jsonContent);
      return new Response(
        JSON.stringify({ 
          success: false, 
          suggestions: [],
          error: 'AI returned invalid JSON format' 
        }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }
    
    // Robust parsing to handle various response formats
    let suggestions = [];
    if (Array.isArray(parsed)) {
      suggestions = parsed;
    } else if (parsed.suggestions && Array.isArray(parsed.suggestions)) {
      suggestions = parsed.suggestions;
    } else if (parsed.categories && Array.isArray(parsed.categories)) {
      suggestions = parsed.categories;
    } else {
      console.error('Unexpected AI response format:', parsed);
      return new Response(
        JSON.stringify({ 
          success: false, 
          suggestions: [],
          error: 'AI returned unexpected format' 
        }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Validate we have suggestions
    if (!Array.isArray(suggestions) || suggestions.length === 0) {
      console.warn('No valid suggestions returned from AI');
      return new Response(
        JSON.stringify({ 
          success: false, 
          suggestions: [],
          message: 'No valid suggestions returned from AI' 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const elapsed = Date.now() - startTime;
    console.log(`✅ Generated ${suggestions.length} category suggestions in ${elapsed}ms`);

    return new Response(
      JSON.stringify({ 
        success: true, 
        suggestions,
        context: {
          examplesUsed: Object.fromEntries(
            Object.entries(categoryExamples).map(([k, v]) => [k, v.length])
          ),
          processingTimeMs: elapsed
        },
        message: `Successfully categorized ${suggestions.length} tags with historical context` 
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in suggest-tag-categories function:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
