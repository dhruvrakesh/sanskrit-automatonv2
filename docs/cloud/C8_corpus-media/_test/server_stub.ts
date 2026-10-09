// Test stand-in for deno.land/std/http/server.ts: keeps the handler instead of listening.
export let handler: ((r: Request) => Response | Promise<Response>) | null = null;
export function serve(h: (r: Request) => Response | Promise<Response>): void { handler = h; }
