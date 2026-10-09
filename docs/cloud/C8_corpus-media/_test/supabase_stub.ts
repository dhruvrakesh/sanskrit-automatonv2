// Test stand-in for esm.sh/@supabase/supabase-js: rpc() answers from globalThis.__rpc.
type Rpc = (fn: string, args: Record<string, unknown> | undefined, key: string, auth: string | null) =>
  { data: unknown; error: { message: string; code?: string } | null };
export function createClient(_url: string, key: string, opts?: { global?: { headers?: Record<string, string> }; auth?: unknown }) {
  const auth = opts?.global?.headers?.Authorization ?? null;
  return {
    rpc: (fn: string, args?: Record<string, unknown>) =>
      Promise.resolve(((globalThis as unknown as { __rpc: Rpc }).__rpc)(fn, args, key, auth)),
  };
}
