// Test stand-in for esm.sh/@supabase/supabase-js: rpc() answers from globalThis.__rpc, and each
// createClient() is recorded in globalThis.__clients (when the test keeps that list).
type Rpc = (fn: string, args: Record<string, unknown> | undefined, key: string) =>
  { data: unknown; error: { message: string; code?: string } | null };
export function createClient(url: string, key: string, opts?: unknown) {
  const g = globalThis as unknown as { __rpc: Rpc; __clients?: { url: string; key: string; opts?: unknown }[] };
  g.__clients?.push({ url, key, opts });
  return { rpc: (fn: string, args?: Record<string, unknown>) => Promise.resolve(g.__rpc(fn, args, key)) };
}
