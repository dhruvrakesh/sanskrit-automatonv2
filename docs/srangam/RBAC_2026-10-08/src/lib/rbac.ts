/**
 * Roles and research invitations - RBAC_RESEARCHERS_2026_10_08.
 *
 * The database decides everything (docs/cloud/C7 in the automaton repository): the super admin
 * invites, a researcher accepts, and corpus_reader_allowed() lets researchers read. These are thin,
 * typed calls to its functions, plus the pure rules the pages share (links, the email text, what
 * each answer means). A function the database does not have yet (C7 not applied) is reported as
 * `missing`, so the pages can say so instead of failing.
 */
import { supabase } from '@/integrations/supabase/client';

export type Role = 'super_admin' | 'admin' | 'researcher' | 'moderator' | 'user';
export type AccessMode = 'signed_in' | 'readers' | 'admins';
export type InviteStatus = 'pending' | 'accepted' | 'revoked' | 'expired' | 'invalid';
export type AcceptResult =
  | 'accepted' | 'already_accepted' | 'used' | 'revoked' | 'expired' | 'wrong_email' | 'unconfirmed' | 'invalid';

export interface CreatedInvite { invite_id: string; email: string; token: string; expires_at: string; reissued: boolean }
export interface InviteRow {
  id: string; email: string; note: string | null; status: InviteStatus; created_at: string; expires_at: string;
  accepted_at: string | null; revoked_at: string | null; invited_by_email: string | null; accepted_by_email: string | null;
}
export interface InvitePeek { status: InviteStatus; email_hint: string | null; expires_at: string | null; role: string | null; for_you: boolean | null }
export interface MemberRow {
  user_id: string; email: string | null; roles: string[]; since: string | null; last_sign_in_at: string | null;
  on_reader_list: boolean; invited_by_email: string | null;
}
export interface AuditRow { at: string; actor_email: string | null; action: string; target_email: string | null; detail: Record<string, unknown> | null }

export interface RbacResult<T> {
  ok: boolean;
  data: T | null;
  /** Non-null exactly when ok === false. */
  error: string | null;
  /** The database does not have this function yet (C7 not applied). */
  missing: boolean;
  /** The database refused the caller (not signed in, or not the super admin). */
  refused: boolean;
}

const TIMEOUT_MS = 15000;
const MISSING_RE = /PGRST202|could not find the function|does not exist|schema cache/i;
const REFUSED_RE = /Only the super admin|permission denied|42501|Sign in to accept/i;

/** A token as the database issues it: 64 lowercase hex characters. */
export const TOKEN_RE = /^[0-9a-f]{64}$/;
export const isInviteToken = (t: string | null | undefined): t is string => !!t && TOKEN_RE.test(t);

type RpcAnswer = { data: unknown; error: { message?: string; code?: string } | null };
type Timeout = { __timeout: true };
/** The generated types do not list C7's functions yet; this is the one untyped door to them. */
const db = supabase as unknown as { rpc: (fn: string, args?: Record<string, unknown>) => PromiseLike<RpcAnswer> };

export async function callRbac<T>(fn: string, args?: Record<string, unknown>): Promise<RbacResult<T>> {
  let res: RpcAnswer | Timeout | undefined;
  try {
    const call = args ? db.rpc(fn, args) : db.rpc(fn);
    res = await Promise.race<RpcAnswer | Timeout>([
      call,
      new Promise<Timeout>((resolve) => setTimeout(() => resolve({ __timeout: true }), TIMEOUT_MS)),
    ]);
  } catch (e) {
    const msg = e instanceof Error && e.message ? e.message : 'The database could not be reached.';
    return { ok: false, data: null, error: msg, missing: false, refused: false };
  }
  if (!res) {
    return { ok: false, data: null, error: 'The database gave no answer.', missing: false, refused: false };
  }
  if ('__timeout' in res) {
    return { ok: false, data: null, error: 'The database took too long to answer. Please try again.', missing: false, refused: false };
  }
  if (res.error) {
    const msg = String(res.error.message ?? res.error);
    const code = String(res.error.code ?? '');
    const missing = code === 'PGRST202' || (msg.includes(fn) && MISSING_RE.test(msg));
    const refused = !missing && (code === '42501' || REFUSED_RE.test(msg));
    return { ok: false, data: null, error: msg, missing, refused };
  }
  return { ok: true, data: res.data as T, error: null, missing: false, refused: false };
}

const rows = <T,>(r: RbacResult<T[]>): RbacResult<T[]> =>
  r.ok && !Array.isArray(r.data) ? { ...r, ok: false, data: null, error: 'The database answered in an unexpected form.' } : r;

export const myRoles = () => callRbac<string[]>('my_roles');
export const listInvites = async (k = 200) => rows(await callRbac<InviteRow[]>('research_invites_list', { k }));
export const listMembers = async () => rows(await callRbac<MemberRow[]>('rbac_members_list'));
export const listAudit = async (k = 50) => rows(await callRbac<AuditRow[]>('rbac_audit_list', { k }));
export const getAccessMode = () => callRbac<AccessMode>('corpus_access_mode');
export const setAccessMode = (mode: AccessMode) => callRbac<AccessMode>('corpus_access_mode_set', { p_mode: mode });
export const revokeInvite = (id: string) => callRbac<boolean>('research_invite_revoke', { p_id: id });
export const removeResearcher = (userId: string) => callRbac<boolean>('researcher_remove', { p_user: userId });
export const acceptInvite = (token: string) => callRbac<AcceptResult>('research_invite_accept', { p_token: token });

export async function createInvite(email: string, note: string, days: number): Promise<RbacResult<CreatedInvite>> {
  const r = rows(await callRbac<CreatedInvite[]>('research_invite_create', {
    p_email: email.trim(), p_note: note.trim() || null, p_days: days,
  }));
  if (!r.ok) return { ...r, data: null };
  const first = r.data && r.data[0];
  return first ? { ...r, data: first } : { ...r, ok: false, data: null, error: 'No invitation came back.' };
}

export async function peekInvite(token: string): Promise<RbacResult<InvitePeek>> {
  if (!isInviteToken(token)) {
    return { ok: true, data: { status: 'invalid', email_hint: null, expires_at: null, role: null, for_you: null }, error: null, missing: false, refused: false };
  }
  const r = rows(await callRbac<InvitePeek[]>('research_invite_peek', { p_token: token }));
  if (!r.ok) return { ...r, data: null };
  return { ...r, data: (r.data && r.data[0]) || { status: 'invalid', email_hint: null, expires_at: null, role: null, for_you: null } };
}

// ---- the pure rules ---------------------------------------------------------------------------

export const INVITE_DAYS = [7, 14, 30, 60, 90] as const;

export function inviteLink(origin: string, token: string): string {
  return `${origin.replace(/\/+$/, '')}/invite/${token}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function inviteEmail(link: string, email: string, expiresAt: string, note?: string | null): { subject: string; body: string } {
  const subject = 'Invitation: the Srangam working corpus';
  const lines = [
    'Dear colleague,',
    '',
    'You are invited to read the Srangam working corpus as a researcher: the Sanskrit texts with IAST, '
      + 'English and Hindi as they stand on the translation desk, with the stories drawn from them and the names index.',
    '',
    `Open this link, then sign in or create an account with this email address (${email}):`,
    link,
    '',
    `The link works once, for this address, until ${formatDate(expiresAt)}.`,
  ];
  if (note && note.trim()) lines.push('', note.trim());
  return { subject, body: lines.join('\n') };
}

export function mailtoHref(email: string, subject: string, body: string): string {
  const to = encodeURIComponent(email).replace(/%40/g, '@');
  return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export const ROLE_LABEL: Record<string, string> = {
  super_admin: 'Super admin', admin: 'Admin', researcher: 'Researcher', moderator: 'Moderator', user: 'User',
};

export const MODE_TEXT: Record<AccessMode, { label: string; help: string }> = {
  signed_in: { label: 'Anyone signed in', help: 'Anyone who makes an account can read. The sign-up page is open.' },
  readers: { label: 'Invited researchers', help: 'Researchers who accepted an invitation, people on the old reader list, and admins.' },
  admins: { label: 'Admins only', help: 'Only admins and the super admin. Researchers are shut out too.' },
};

export const STATUS_TEXT: Record<InviteStatus, string> = {
  pending: 'Waiting', accepted: 'Accepted', revoked: 'Withdrawn', expired: 'Expired', invalid: 'Not valid',
};

export const ACCEPT_TEXT: Record<AcceptResult, string> = {
  accepted: 'Welcome. You can now read the working corpus.',
  already_accepted: 'You have already accepted this invitation. You can read the working corpus.',
  used: 'This invitation has already been used by another account.',
  revoked: 'This invitation was withdrawn. Ask the editor for a new one.',
  expired: 'This invitation has expired. Ask the editor for a new one.',
  wrong_email: 'This invitation is for a different email address. Sign in with the address it was sent to.',
  unconfirmed: 'Confirm your email address first: open the email the site sent you, then come back to this link.',
  invalid: 'This invitation link is not valid. Check that the whole link was copied, or ask the editor for a new one.',
};

export const AUDIT_TEXT: Record<string, string> = {
  invite_created: 'Invited', invite_reissued: 'Invited again (old link void)', invite_revoked: 'Withdrew the invitation',
  invite_accepted: 'Accepted the invitation', role_granted: 'Role granted', role_revoked: 'Role removed',
  role_changed: 'Role changed', access_mode: 'Changed who may read',
};

export function auditDetail(a: AuditRow): string {
  const d = a.detail ?? {};
  if (a.action === 'access_mode') {
    const from = MODE_TEXT[d.from as AccessMode]?.label ?? String(d.from ?? '');
    const to = MODE_TEXT[d.to as AccessMode]?.label ?? String(d.to ?? '');
    return `${from} → ${to}`;
  }
  if (typeof d.role === 'string') return ROLE_LABEL[d.role] ?? d.role;
  if (typeof d.days === 'number') return `${d.days} days`;
  return '';
}
