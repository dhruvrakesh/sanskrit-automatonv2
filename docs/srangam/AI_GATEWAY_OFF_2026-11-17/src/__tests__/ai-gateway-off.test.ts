/**
 * AI_GATEWAY_OFF_2026_11_17 - every AI call of the edge functions goes through the project's own keys
 * (_shared/ai-provider.ts: GEMINI_API_KEY first, OPENAI_API_KEY second), never through the Lovable AI
 * Gateway. detect-duplicate-articles and suggest-tag-categories were the last two on the gateway.
 * Static: reads the functions' source, calls nothing.
 */
import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';

const FN = resolve(__dirname, '../../supabase/functions');
const read = (f: string) => readFileSync(resolve(FN, f), 'utf-8').replace(/\r\n/g, '\n');

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...sources(p));
    else if (/\.(ts|js|mjs)$/.test(name)) out.push(p);
  }
  return out;
}

describe('AI calls use the project keys, not the Lovable AI Gateway', () => {
  it('no edge function names the gateway or its key', () => {
    const offenders = sources(FN).filter((p) => {
      const src = readFileSync(p, 'utf-8');
      return /ai\.gateway\.lovable\.dev/.test(src) || /LOVABLE_API_KEY/.test(src);
    });
    expect(offenders).toEqual([]);
  });

  it('the two functions call ai-provider with telemetry', () => {
    for (const [fn, purpose] of [
      ['detect-duplicate-articles', 'duplicate_check'],
      ['suggest-tag-categories', 'tag_categories'],
    ]) {
      const src = read(`${fn}/index.ts`);
      expect(src, fn).toMatch(/from '\.\.\/_shared\/ai-provider\.ts'/);
      expect(src, fn).toContain('aiExtractCitations(');
      expect(src, fn).toContain(`function_name: '${fn}'`);
      expect(src, fn).toContain(`purpose: '${purpose}'`);
      expect(src, fn).toContain('GEMINI_API_KEY');
      expect(src, fn).toContain('OPENAI_API_KEY');
      expect(src, fn).toContain('AI_GATEWAY_OFF_2026_11_17');
    }
  });

  it('ai-provider still offers the generic JSON call, Gemini first and OpenAI second', () => {
    const src = read('_shared/ai-provider.ts');
    expect(src).toMatch(/export async function aiExtractCitations\(/);
    expect(src).toMatch(/export class NoAIProviderError/);
    const g = src.indexOf("Deno.env.get('GEMINI_API_KEY')");
    const o = src.indexOf("Deno.env.get('OPENAI_API_KEY')");
    expect(g).toBeGreaterThan(0);
    expect(o).toBeGreaterThan(g);
  });
});
