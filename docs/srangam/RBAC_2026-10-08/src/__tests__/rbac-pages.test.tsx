/**
 * RBAC_RESEARCHERS_2026_10_08 - the pages: /admin/researchers (the super admin's), /invite/:token
 * (the researcher's), the admin sidebar and the corpus refusal. useAuth is set per test; supabase
 * answers per database function. And the pure rules of src/lib/rbac.ts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type Answer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({
  byFn: {} as Record<string, Answer | ((args: Record<string, unknown>) => Answer)>,
  calls: [] as Array<{ fn: string; args?: Record<string, unknown> }>,
}));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args?: Record<string, unknown>) => {
      sb.calls.push({ fn, args });
      const v = sb.byFn[fn];
      return Promise.resolve(typeof v === 'function' ? v(args ?? {}) : v ?? { data: [], error: null });
    },
  },
}));
const auth = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('sonner', () => ({ toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), info: vi.fn() }) }));

import Researchers from '@/pages/admin/Researchers';
import InviteAccept from '@/pages/InviteAccept';
import { AdminLayout } from '@/components/admin/AdminLayout';
import { CorpusRefused } from '@/components/corpus/CorpusGate';
import {
  auditDetail, callRbac, inviteEmail, inviteLink, isInviteToken, mailtoHref, peekInvite,
} from '@/lib/rbac';

const TOKEN = 'c0ffee'.repeat(10) + 'beef';
const ok = (data: unknown): Answer => ({ data, error: null });
const MISSING = (fn: string): Answer => ({ data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn}` } });

const SUPER = {
  user: { id: 'dhruv', email: 'dhruv.rakesh@gmail.com' }, isLoading: false, roleChecked: true, isAdmin: true,
  isSuperAdmin: true, isResearcher: false, roles: ['admin', 'super_admin'], refreshRoles: vi.fn(() => Promise.resolve()),
  signOut: vi.fn(() => Promise.resolve()),
};
const ADMIN = { ...SUPER, user: { id: 'ed', email: 'editor@srangam.test' }, isSuperAdmin: false, roles: ['admin'] };
const SCHOLAR = {
  ...SUPER, user: { id: 'sch', email: 'scholar@uni.test' }, isAdmin: false, isSuperAdmin: false, roles: [],
  refreshRoles: vi.fn(() => Promise.resolve()),
};
const SIGNED_OUT = { ...SUPER, user: null, isAdmin: false, isSuperAdmin: false, roles: [] };

const INVITES = [
  { id: 'i1', email: 'scholar@uni.test', note: 'Nirukta', status: 'pending', created_at: '2026-10-08T10:00:00Z',
    expires_at: '2026-10-22T10:00:00Z', accepted_at: null, revoked_at: null, invited_by_email: 'dhruv.rakesh@gmail.com', accepted_by_email: null },
  { id: 'i2', email: 'old@uni.test', note: null, status: 'accepted', created_at: '2026-10-01T10:00:00Z',
    expires_at: '2026-10-15T10:00:00Z', accepted_at: '2026-10-02T10:00:00Z', revoked_at: null, invited_by_email: 'dhruv.rakesh@gmail.com', accepted_by_email: 'old@uni.test' },
];
const MEMBERS = [
  { user_id: 'dhruv', email: 'dhruv.rakesh@gmail.com', roles: ['admin', 'super_admin'], since: '2025-11-10T00:00:00Z', last_sign_in_at: null, on_reader_list: false, invited_by_email: null },
  { user_id: 'old', email: 'old@uni.test', roles: ['researcher'], since: '2026-10-02T10:00:00Z', last_sign_in_at: null, on_reader_list: false, invited_by_email: 'dhruv.rakesh@gmail.com' },
];
const AUDIT = [{ at: '2026-10-08T11:00:00Z', actor_email: 'dhruv.rakesh@gmail.com', action: 'access_mode', target_email: null, detail: { from: 'signed_in', to: 'readers' } }];

function mount(path: string, el: JSX.Element, route: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={route} element={el} />
            <Route path="*" element={<p>elsewhere</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

const adminData = () => {
  sb.byFn.corpus_access_mode = ok('signed_in');
  sb.byFn.research_invites_list = ok(INVITES);
  sb.byFn.rbac_members_list = ok(MEMBERS);
  sb.byFn.rbac_audit_list = ok(AUDIT);
};
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  auth.value = SUPER;
  SCHOLAR.refreshRoles.mockClear();
});

describe('rules', () => {
  it('tokens, links and the email', () => {
    expect(isInviteToken(TOKEN)).toBe(true);
    expect(isInviteToken(TOKEN.toUpperCase())).toBe(false);
    expect(isInviteToken('abc')).toBe(false);
    expect(inviteLink('https://srangam.app/', TOKEN)).toBe(`https://srangam.app/invite/${TOKEN}`);
    const m = inviteEmail(`https://srangam.app/invite/${TOKEN}`, 'a+b@uni.test', '2026-10-22T10:00:00Z', ' Welcome ');
    expect(m.body).toContain(`https://srangam.app/invite/${TOKEN}`);
    expect(m.body).toContain('(a+b@uni.test)');
    expect(m.body).toContain('22 October 2026');
    expect(m.body.endsWith('Welcome')).toBe(true);
    const href = mailtoHref('a+b@uni.test', m.subject, m.body);
    expect(href.startsWith('mailto:a%2Bb@uni.test?subject=Invitation%3A')).toBe(true);
    expect(decodeURIComponent(href.split('&body=')[1])).toBe(m.body);
    expect(auditDetail(AUDIT[0])).toBe('Anyone signed in → Invited researchers');
    expect(auditDetail({ ...AUDIT[0], action: 'role_granted', detail: { role: 'super_admin' } })).toBe('Super admin');
  });

  it('a missing function, a refusal, a malformed token', async () => {
    sb.byFn.my_roles = MISSING('my_roles');
    expect(await callRbac('my_roles')).toMatchObject({ ok: false, missing: true, refused: false });
    sb.byFn.research_invites_list = { data: null, error: { code: '42501', message: 'Only the super admin may do this.' } };
    expect(await callRbac('research_invites_list', { k: 5 })).toMatchObject({ ok: false, missing: false, refused: true });
    expect((await peekInvite('nope')).data?.status).toBe('invalid');
    expect(called('research_invite_peek')).toHaveLength(0);
  });
});

describe('/admin/researchers', () => {
  it('an admin who is not the super admin is told so, and nothing is asked', async () => {
    auth.value = ADMIN;
    mount('/admin/researchers', <Researchers />, '/admin/researchers');
    expect(await screen.findByText('Super admin only')).toBeInTheDocument();
    expect(sb.calls).toHaveLength(0);
  });

  it('the super admin sees the mode, the invitations, the people and the log', async () => {
    adminData();
    mount('/admin/researchers', <Researchers />, '/admin/researchers');
    expect(await screen.findByText('scholar@uni.test')).toBeInTheDocument();
    expect(screen.getByText('Waiting')).toBeInTheDocument();
    expect(screen.getAllByText('old@uni.test').length).toBeGreaterThan(0);
    expect(screen.getByText('Changed who may read')).toBeInTheDocument();
    const now = screen.getByText('now');
    expect(now.closest('label')?.textContent).toContain('Anyone signed in');
    expect(screen.getByRole('button', { name: 'Withdraw the invitation for scholar@uni.test' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Withdraw the invitation for old@/ })).toBeNull();
  });

  it('making an invitation shows the link once, with copy and email', async () => {
    adminData();
    sb.byFn.research_invite_create = ok([{ invite_id: 'i3', email: 'new@uni.test', token: TOKEN, expires_at: '2026-10-22T10:00:00Z', reissued: false }]);
    mount('/admin/researchers', <Researchers />, '/admin/researchers');
    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: ' New@uni.test ' } });
    fireEvent.change(screen.getByLabelText('Valid for'), { target: { value: '30' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create invitation' })); });
    const link = await screen.findByLabelText('Invitation link');
    expect((link as HTMLInputElement).value).toBe(`${window.location.origin}/invite/${TOKEN}`);
    expect(called('research_invite_create')[0].args).toEqual({ p_email: 'New@uni.test', p_note: null, p_days: 30 });
    const mail = screen.getByRole('link', { name: /Email it/ }).getAttribute('href') ?? '';
    expect(mail.startsWith('mailto:new@uni.test?subject=')).toBe(true);
    expect(decodeURIComponent(mail)).toContain(`/invite/${TOKEN}`);
    expect(screen.getByText(/This link is shown once/)).toBeInTheDocument();
  });

  it('withdraw, remove (after confirming) and change the mode', async () => {
    adminData();
    sb.byFn.research_invite_revoke = ok(true);
    sb.byFn.researcher_remove = ok(true);
    sb.byFn.corpus_access_mode_set = ok('readers');
    mount('/admin/researchers', <Researchers />, '/admin/researchers');
    const withdraw = await screen.findByRole('button', { name: 'Withdraw the invitation for scholar@uni.test' });
    await act(async () => { fireEvent.click(withdraw); });
    await waitFor(() => expect(called('research_invite_revoke')[0]?.args).toEqual({ p_id: 'i1' }));
    fireEvent.click(screen.getByRole('button', { name: 'Remove the researcher role from old@uni.test' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(called('researcher_remove')).toHaveLength(0);
    await act(async () => { fireEvent.click(within(dialog).getByRole('button', { name: 'Remove' })); });
    await waitFor(() => expect(called('researcher_remove')[0]?.args).toEqual({ p_user: 'old' }));
    fireEvent.click(screen.getByRole('radio', { name: /Invited researchers/ }));
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Change to: Invited researchers' })); });
    await waitFor(() => expect(called('corpus_access_mode_set')[0]?.args).toEqual({ p_mode: 'readers' }));
  });

  it('before C7 it says which SQL to run', async () => {
    for (const fn of ['corpus_access_mode', 'research_invites_list', 'rbac_members_list', 'rbac_audit_list']) sb.byFn[fn] = MISSING(fn);
    mount('/admin/researchers', <Researchers />, '/admin/researchers');
    expect(await screen.findByText(/C7_rbac_researchers_2026-10-08.sql/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create invitation' })).toBeDisabled();
  });
});

describe('/invite/:token', () => {
  const peek = (status: string, for_you: boolean | null) =>
    ok([{ status, email_hint: 's***@uni.test', expires_at: '2026-10-22T10:00:00Z', role: 'researcher', for_you }]);

  it('a malformed link is refused without asking the database', async () => {
    auth.value = SIGNED_OUT;
    mount('/invite/xyz', <InviteAccept />, '/invite/:token');
    expect(await screen.findByText('This link is not valid')).toBeInTheDocument();
    expect(sb.calls).toHaveLength(0);
  });

  it('signed out: the masked address, then sign up or sign in and come back', async () => {
    auth.value = SIGNED_OUT;
    sb.byFn.research_invite_peek = peek('pending', null);
    mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
    expect(await screen.findByText('s***@uni.test')).toBeInTheDocument();
    expect(called('research_invite_peek')[0].args).toEqual({ p_token: TOKEN });
    const next = encodeURIComponent(`/invite/${TOKEN}`);
    expect(screen.getByRole('link', { name: /Create an account/ }).getAttribute('href')).toBe(`/auth?next=${next}&tab=signup`);
    expect(screen.getByRole('link', { name: /I have an account/ }).getAttribute('href')).toBe(`/auth?next=${next}`);
  });

  it('signed in with another address: told so, with a way to sign out', async () => {
    auth.value = { ...SCHOLAR, user: { id: 'x', email: 'someone@else.test' } };
    sb.byFn.research_invite_peek = peek('pending', false);
    mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
    expect(await screen.findByText(/but this invitation is for/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Accept/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Sign out/ }));
    expect(SCHOLAR.signOut).toHaveBeenCalled();
  });

  it('the invited researcher accepts, the roles are asked again, and on to the corpus', async () => {
    auth.value = SCHOLAR;
    sb.byFn.research_invite_peek = peek('pending', true);
    sb.byFn.research_invite_accept = ok('accepted');
    mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
    const accept = await screen.findByRole('button', { name: 'Accept the invitation' });
    await act(async () => { fireEvent.click(accept); });
    expect(await screen.findByText('You are a Srangam researcher')).toBeInTheDocument();
    expect(called('research_invite_accept')[0].args).toEqual({ p_token: TOKEN });
    expect(SCHOLAR.refreshRoles).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('link', { name: /Open the working corpus/ }).getAttribute('href')).toBe('/corpus');
  });

  it('an unconfirmed address is asked to confirm first', async () => {
    auth.value = SCHOLAR;
    sb.byFn.research_invite_peek = peek('pending', true);
    sb.byFn.research_invite_accept = ok('unconfirmed');
    mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
    const accept = await screen.findByRole('button', { name: 'Accept the invitation' });
    await act(async () => { fireEvent.click(accept); });
    expect(await screen.findByText(/Confirm your email address first/)).toBeInTheDocument();
    expect(SCHOLAR.refreshRoles).not.toHaveBeenCalled();
  });

  it('withdrawn, expired and used links say so', async () => {
    auth.value = SIGNED_OUT;
    for (const [status, title] of [['revoked', 'Invitation withdrawn'], ['expired', 'Invitation expired'], ['accepted', 'Already used']]) {
      sb.byFn.research_invite_peek = peek(status, null);
      const { unmount } = mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
      expect(await screen.findByText(title)).toBeInTheDocument();
      unmount();
    }
  });

  it('before C7: not switched on yet', async () => {
    auth.value = SIGNED_OUT;
    sb.byFn.research_invite_peek = MISSING('research_invite_peek');
    mount(`/invite/${TOKEN}`, <InviteAccept />, '/invite/:token');
    expect(await screen.findByText(/not switched on yet/)).toBeInTheDocument();
  });
});

describe('the admin sidebar and the corpus refusal', () => {
  // The sidebar is a closed drawer at the suite's phone width; these two look at the desktop one.
  const wide = () => Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 1280 });
  const narrow = () => Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 384 });

  it('Researchers is in the sidebar for the super admin only, with the badge', async () => {
    wide();
    try {
      mount('/admin', <AdminLayout />, '/admin');
      expect(await screen.findByRole('link', { name: /Researchers/ })).toHaveAttribute('href', '/admin/researchers');
      expect(screen.getByText('Super admin')).toBeInTheDocument();
    } finally { narrow(); }
  });

  it('an admin sees neither', async () => {
    auth.value = ADMIN;
    wide();
    try {
      mount('/admin', <AdminLayout />, '/admin');
      expect(await screen.findByText('Admin')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Corpus Correlations/ })).toBeInTheDocument();
      expect(screen.queryByRole('link', { name: /Researchers/ })).toBeNull();
      expect(screen.queryByText('Super admin')).toBeNull();
    } finally { narrow(); }
  });

  it('the refusal says how researchers get in', () => {
    render(<CorpusRefused />);
    expect(screen.getByText(/not on the reader list/)).toBeInTheDocument();
    expect(screen.getByText(/open to\s+invited researchers/)).toBeInTheDocument();
  });
});
