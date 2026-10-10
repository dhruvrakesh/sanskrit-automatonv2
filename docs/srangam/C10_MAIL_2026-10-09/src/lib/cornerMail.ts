/**
 * Email from the Researchers' Corner - CORNER_C10_MAIL_2026_10_09.
 *
 * The database writes every email and queues it (docs/cloud/C12_corner_mail_2026-10-09.sql in the
 * automaton repo: corner.outbox, filled by a trigger on the requests and by corner_mail_invite); the
 * edge function corner-mail sends what is queued, through Resend, from nartiang.org. The site only
 * reads and sets each person's choice (corner_mail_prefs, corner_mail_prefs_set), shows editors the
 * state of the queue (corner_mail_state), queues an invitation's email for the super admin
 * (corner_mail_invite), and, after it has made a request, asks corner-mail to send what is waiting
 * (flushMail) so an editor hears of it at once instead of at the desk's next round.
 *
 * This file stands alone (only the supabase client), so the admin's Researchers page and the reading
 * pages' DeskActions can use it without the rest of the Corner. Before C12 the functions are missing,
 * every answer says so (`missing`), and the pages show no email controls at all.
 */
import { supabase } from '@/integrations/supabase/client';

export const MAIL_MARK = 'CORNER_C10_MAIL_2026_10_09';
/** Under the Corner's key, so what refreshes the Corner refreshes these too. */
export const MAIL_KEY = ['corner', 'mail'] as const;
export const MAIL_PREFS_KEY = [...MAIL_KEY, 'prefs'] as const;
export const MAIL_STATE_KEY = [...MAIL_KEY, 'state'] as const;
export const MAIL_FN = 'corner-mail';

export interface MailPrefs {
  on_my_requests: boolean; on_queue: boolean; mail_enabled: boolean; is_editor: boolean;
  /** The From line; the super admin's answer only (null for everyone else). */
  mail_from: string | null;
}

export interface MailState {
  mail_enabled: boolean; waiting: number; sent_today: number; failed_7d: number; last_sent_at: string | null;
  last_error: string | null;
}

export interface MailResult<T> {
  ok: boolean;
  data: T | null;
  /** Non-null exactly when ok === false: the server's own sentence where it gave one. */
  error: string | null;
  /** The database does not have this function yet (C12 not applied). */
  missing: boolean;
  refused: boolean;
}

const TIMEOUT_MS = 15000;
const MISSING_RE = /PGRST202|could not find the function|does not exist|schema cache/i;
const REFUSED_RE = /permission denied|not allowed|42501|only the super admin|only an editor|open to invited/i;

type RpcAnswer = { data: unknown; error: { message?: string; code?: string } | null };
type Timeout = { __timeout: true };
/** The generated types do not list C12's functions; this is the one untyped door to them. */
const db = supabase as unknown as {
  rpc: (fn: string, args: Record<string, unknown>) => PromiseLike<RpcAnswer>;
  functions?: { invoke: (fn: string, o: { body: unknown }) => PromiseLike<{ data: unknown; error: unknown }> };
};

const fail = <T,>(error: string, missing = false, refused = false): MailResult<T> => ({ ok: false, data: null, error, missing, refused });

async function call(fn: string, args: Record<string, unknown>): Promise<MailResult<unknown>> {
  let res: RpcAnswer | Timeout | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    res = await Promise.race<RpcAnswer | Timeout>([
      db.rpc(fn, args),
      new Promise<Timeout>((resolve) => { timer = setTimeout(() => resolve({ __timeout: true }), TIMEOUT_MS); }),
    ]);
  } catch (e) {
    return fail(e instanceof Error && e.message ? e.message : 'The database could not be reached.');
  } finally {
    clearTimeout(timer);
  }
  if (!res) return fail('The database gave no answer.');
  if ('__timeout' in res) return fail('The database took too long to answer. Please try again.');
  if (res.error) {
    const msg = String(res.error.message ?? res.error);
    const code = String(res.error.code ?? '');
    const missing = code === 'PGRST202' || (msg.includes(fn) && MISSING_RE.test(msg));
    return fail(msg || 'The request failed.', missing, !missing && (code === '42501' || REFUSED_RE.test(msg)));
  }
  return { ok: true, data: res.data, error: null, missing: false, refused: false };
}

const bool = (v: unknown): boolean => v === true || v === 'true' || v === 't';
const count = (v: unknown): number => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
};
const textOr = (v: unknown, n: number): string | null => (typeof v === 'string' && v.trim() ? v.trim().slice(0, n) : null);
const firstRow = (data: unknown): Record<string, unknown> | null => {
  const r = Array.isArray(data) ? data[0] : data;
  return r && typeof r === 'object' && !Array.isArray(r) ? (r as Record<string, unknown>) : null;
};

/** The person's own choice, whether mail is on, and (super admin) the From line. ok with data null:
 *  no answer row, which the pages treat as "no email here". */
export async function loadMailPrefs(): Promise<MailResult<MailPrefs>> {
  const r = await call('corner_mail_prefs', {});
  if (!r.ok) return { ...r, data: null };
  const x = firstRow(r.data);
  return {
    ...r,
    data: x ? {
      on_my_requests: x.on_my_requests !== false && x.on_my_requests !== 'false', on_queue: x.on_queue !== false && x.on_queue !== 'false',
      mail_enabled: bool(x.mail_enabled), is_editor: bool(x.is_editor), mail_from: textOr(x.mail_from, 320),
    } : null,
  };
}

/** Keep the person's choice; a null leaves that one as it was. */
export async function saveMailPrefs(onMyRequests: boolean | null, onQueue: boolean | null): Promise<MailResult<boolean>> {
  const r = await call('corner_mail_prefs_set', { p_on_my_requests: onMyRequests, p_on_queue: onQueue });
  return r.ok ? { ...r, data: r.data === true } : { ...r, data: null };
}

/** Editors: is mail on, and how the queue stands. */
export async function loadMailState(): Promise<MailResult<MailState>> {
  const r = await call('corner_mail_state', {});
  if (!r.ok) return { ...r, data: null };
  const x = firstRow(r.data);
  return {
    ...r,
    data: x ? {
      mail_enabled: bool(x.mail_enabled), waiting: count(x.waiting), sent_today: count(x.sent_today), failed_7d: count(x.failed_7d),
      last_sent_at: typeof x.last_sent_at === 'string' && Number.isFinite(Date.parse(x.last_sent_at)) ? x.last_sent_at : null,
      last_error: textOr(x.last_error, 300),
    } : null,
  };
}

/** The super admin: queue the email of an invitation just made (its token is known only now).
 *  Answers 'queued', or the server's sentence ("Email is off; ...", "not a pending invitation"). */
export async function mailInvite(inviteId: string, token: string): Promise<MailResult<string>> {
  const r = await call('corner_mail_invite', { p_invite: inviteId, p_token: token });
  return r.ok ? { ...r, data: typeof r.data === 'string' ? r.data : 'queued' } : { ...r, data: null };
}

/** Whether to show any email control: only when corner_mail_prefs answered with a row. */
export function mailShown(r: MailResult<MailPrefs> | undefined | null): r is MailResult<MailPrefs> & { data: MailPrefs } {
  return !!r && r.ok && !!r.data;
}

// ---- sending what is waiting ----------------------------------------------------------------

/** After corner-mail answered 404 (not deployed), it is not asked again for this long. */
const GONE_MS = 10 * 60 * 1000;
let goneUntil = 0;

/** For tests: forget that corner-mail was not there. */
export function resetMailMemo(): void {
  goneUntil = 0;
}

const statusOf = (e: unknown): number | null => {
  const c = e && typeof e === 'object' ? (e as { context?: { status?: unknown } }).context : null;
  return c && typeof c.status === 'number' ? c.status : null;
};

/** Ask corner-mail (as the signed-in person) to send the emails waiting. Fire and forget: it never
 *  throws and never rejects, and the page does not wait for it; the desk sends them on its next round
 *  anyway. */
export function flushMail(): Promise<void> {
  if (Date.now() < goneUntil) return Promise.resolve();
  return (async () => {
    try {
      const f = db.functions;
      if (!f || typeof f.invoke !== 'function') return;
      const { error } = await f.invoke(MAIL_FN, { body: { action: 'flush' } });
      if (error && statusOf(error) === 404) goneUntil = Date.now() + GONE_MS;
    } catch {
      /* never mind: the desk sends them on its next round */
    }
  })();
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The editors' line on the queue: "on: 2 waiting, 5 sent today, 1 email given up in the last 7
 *  days; last sent 15:02", or "off". `clock` writes a time (the Corner's clockTime). */
export function mailLineText(m: MailState, clock: (ts: string) => string = (ts) => ts): string {
  if (!m.mail_enabled) return m.waiting > 0 ? `off (${m.waiting} waiting)` : 'off';
  const parts = [`${m.waiting} waiting`, `${m.sent_today} sent today`];
  if (m.failed_7d > 0) parts.push(`${plural(m.failed_7d, 'email')} given up in the last 7 days`);
  const last = m.last_sent_at ? `; last sent ${clock(m.last_sent_at)}` : '';
  return `on: ${parts.join(', ')}${last}`;
}

// ---- the settings, checked as the database checks them --------------------------------------

export const MAIL_FROM_RE = /^[^<>@]{1,60} <[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}>$/;
export const ADDRESS_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
export const SITE_URL_RE = /^https:\/\/[a-z0-9.-]+(:[0-9]+)?$/;
export const DEFAULT_FROM = 'Srangam desk <desk@nartiang.org>';
export const DEFAULT_SITE = 'https://srangam.nartiang.org';

// eslint-disable-next-line no-control-regex
const CONTROL_RE = /[\u0000-\u001f\u007f]/;

/** The value to save, or null when the database would refuse it. */
export function cleanMailFrom(v: string): string | null {
  const x = v.trim();
  return x.length <= 320 && !CONTROL_RE.test(x) && MAIL_FROM_RE.test(x) ? x : null;
}
export function cleanReplyTo(v: string): string | null {
  const x = v.trim();
  return x === '' || (x.length <= 254 && ADDRESS_RE.test(x)) ? x : null;
}
export function cleanSiteUrl(v: string): string | null {
  const x = v.trim().replace(/\/+$/, '').toLowerCase();
  return x.length <= 200 && SITE_URL_RE.test(x) ? x : null;
}
