/**
 * CORNER_C10_MAIL_2026_10_09 - email from the Researchers' Corner (C12 in the database, the edge
 * function corner-mail): each person's choice in Settings, the super admin's settings, the editors'
 * line on the queue in Sync, an invitation sent from nartiang.org on /admin/researchers, and the
 * waiting emails sent after every request (fire and forget, never an error on the page). Without C12
 * (corner_mail_prefs missing) there is no email control anywhere. The pure rules first; then the
 * pages against a mocked supabase, as in corpus-corner.test.tsx and rbac-pages.test.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
type Call = { fn: string; args: Record<string, unknown> };
type InvokeAnswer = { data: unknown; error: unknown };
const sb = vi.hoisted(() => ({
  byFn: {} as Record<string, RpcAnswer>,
  calls: [] as Call[],
  invokes: [] as { fn: string; o: unknown }[],
  invoke: null as null | (() => Promise<InvokeAnswer>),
}));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string, args: Record<string, unknown>) => { sb.calls.push({ fn, args }); return Promise.resolve(sb.byFn[fn] ?? { data: [], error: null }); },
    functions: {
      invoke: (fn: string, o: unknown) => {
        sb.invokes.push({ fn, o });
        return sb.invoke ? sb.invoke() : Promise.resolve({ data: { ok: true, result: { configured: true, claimed: 1, sent: 1, failed: 0 } }, error: null });
      },
    },
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'jwt-of-reader', user: { id: 'u1' } } } }) },
  },
}));
const auth = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('@/hooks/use-toast', () => ({ toast: vi.fn(), useToast: () => ({ toasts: [], toast: vi.fn(), dismiss: vi.fn() }) }));
vi.mock('sonner', () => ({ toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), info: vi.fn() }) }));

import {
  cleanMailFrom, cleanReplyTo, cleanSiteUrl, flushMail, loadMailPrefs, loadMailState, MAIL_MARK, mailInvite, mailLineText,
  mailShown, resetMailMemo, saveMailPrefs,
} from '@/lib/cornerMail';
import { clockTime, resetTrackMemo } from '@/lib/cornerState';
import CorpusCorner from '@/pages/corpus/CorpusCorner';
import Researchers from '@/pages/admin/Researchers';

const ok = (data: unknown): RpcAnswer => ({ data, error: null });
const MISSING = (fn: string): RpcAnswer => ({ data: null, error: { code: 'PGRST202', message: `Could not find the function public.${fn} without parameters in the schema cache` } });
const called = (fn: string) => sb.calls.filter((c) => c.fn === fn);
const flushes = () => sb.invokes.filter((i) => i.fn === 'corner-mail');
const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString();

const ME = (extra: Record<string, unknown> = {}) => ({
  can_request: true, is_editor: false, is_super_admin: false, daily_cap_usd: 2, committed_today: 0.25,
  researchers_need_approval: true, worker_last_seen: recent, worker_info: null, pending: 1, queued: 0, running: 0,
  mine_open: 0, ...extra,
});
const PREFS = (extra: Record<string, unknown> = {}) => ({
  on_my_requests: true, on_queue: true, mail_enabled: true, is_editor: false, mail_from: null, ...extra,
});
const DOC = {
  doc_code: 'nilamata_seg', title: 'Nilamata Purana', category: 'purana', passages: 900, english: 450, hindi: 400,
  vectors: 0, stories: 3, published: false, synced_at: null,
};
const READER = { user: { id: 'u1' }, isLoading: false };
const SUPER = {
  user: { id: 'dhruv', email: 'dhruv.rakesh@gmail.com' }, isLoading: false, roleChecked: true, isAdmin: true,
  isSuperAdmin: true, isResearcher: false, roles: ['admin', 'super_admin'], refreshRoles: vi.fn(() => Promise.resolve()),
  signOut: vi.fn(() => Promise.resolve()),
};
const TOKEN = 'c0ffee'.repeat(10) + 'beef';

function mount(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/corpus/corner" element={<CorpusCorner />} />
            <Route path="/admin/researchers" element={<Researchers />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = []; sb.invokes = []; sb.invoke = null;
  auth.value = READER;
  resetTrackMemo();
  resetMailMemo();
  vi.stubGlobal('fetch', vi.fn(async () => new Response('jpeg', { status: 200 })));
});
afterEach(() => {
  vi.unstubAllGlobals();
});

// ---- the rules ----------------------------------------------------------------------------------

describe('the rules of the Corner\'s email', () => {
  it('the settings are checked as the database checks them', () => {
    expect(MAIL_MARK).toBe('CORNER_C10_MAIL_2026_10_09');
    expect(cleanMailFrom(' Srangam desk <desk@nartiang.org> ')).toBe('Srangam desk <desk@nartiang.org>');
    expect(cleanMailFrom('desk@nartiang.org')).toBeNull();
    expect(cleanMailFrom('Desk <desk@nartiang>')).toBeNull();
    expect(cleanMailFrom('A <b> <desk@nartiang.org>')).toBeNull();
    expect(cleanMailFrom(`${'x'.repeat(61)} <desk@nartiang.org>`)).toBeNull();
    expect(cleanReplyTo('')).toBe('');
    expect(cleanReplyTo(' editor@nartiang.org ')).toBe('editor@nartiang.org');
    expect(cleanReplyTo('Editor <editor@nartiang.org>')).toBeNull();
    expect(cleanSiteUrl('https://srangam.nartiang.org')).toBe('https://srangam.nartiang.org');
    expect(cleanSiteUrl('https://Srangam.Nartiang.org/')).toBe('https://srangam.nartiang.org');
    expect(cleanSiteUrl('https://srangam.nartiang.org:8443')).toBe('https://srangam.nartiang.org:8443');
    expect(cleanSiteUrl('http://srangam.nartiang.org')).toBeNull();
    expect(cleanSiteUrl('https://srangam.nartiang.org/corpus')).toBeNull();
    expect(cleanSiteUrl('')).toBeNull();
  });

  it('the queue in a line', () => {
    const now = new Date(2026, 9, 9, 16, 0).getTime();
    const at = new Date(2026, 9, 9, 15, 2).toISOString();
    const clock = (ts: string) => clockTime(ts, now);
    expect(mailLineText({ mail_enabled: true, waiting: 2, sent_today: 5, failed_7d: 1, last_sent_at: at, last_error: null }, clock))
      .toBe('on: 2 waiting, 5 sent today, 1 email given up in the last 7 days; last sent 15:02');
    expect(mailLineText({ mail_enabled: true, waiting: 1, sent_today: 0, failed_7d: 2, last_sent_at: null, last_error: null }, clock))
      .toBe('on: 1 waiting, 0 sent today, 2 emails given up in the last 7 days');
    expect(mailLineText({ mail_enabled: true, waiting: 0, sent_today: 0, failed_7d: 0, last_sent_at: null, last_error: null }))
      .toBe('on: 0 waiting, 0 sent today');
    expect(mailLineText({ mail_enabled: false, waiting: 0, sent_today: 0, failed_7d: 3, last_sent_at: null, last_error: null }, clock)).toBe('off');
    expect(mailLineText({ mail_enabled: false, waiting: 4, sent_today: 0, failed_7d: 0, last_sent_at: null, last_error: null }, clock)).toBe('off (4 waiting)');
  });

  it('the database functions: their answers read defensively, a missing one said so', async () => {
    sb.byFn.corner_mail_prefs = ok([{ on_my_requests: false, on_queue: null, mail_enabled: true, is_editor: true, mail_from: 'Srangam desk <desk@nartiang.org>' }]);
    const p = await loadMailPrefs();
    expect(p).toMatchObject({ ok: true, missing: false });
    expect(p.data).toEqual({ on_my_requests: false, on_queue: true, mail_enabled: true, is_editor: true, mail_from: 'Srangam desk <desk@nartiang.org>' });
    expect(mailShown(p)).toBe(true);
    sb.byFn.corner_mail_prefs = ok([]);
    expect(mailShown(await loadMailPrefs())).toBe(false);
    sb.byFn.corner_mail_prefs = MISSING('corner_mail_prefs');
    const gone = await loadMailPrefs();
    expect(gone).toMatchObject({ ok: false, missing: true, data: null });
    expect(mailShown(gone)).toBe(false);
    sb.byFn.corner_mail_prefs = { data: null, error: { code: '42501', message: "The Researchers' Corner is open to invited researchers and editors." } };
    expect(await loadMailPrefs()).toMatchObject({ ok: false, refused: true, missing: false });

    sb.byFn.corner_mail_prefs_set = ok(true);
    expect(await saveMailPrefs(false, null)).toMatchObject({ ok: true, data: true });
    expect(called('corner_mail_prefs_set')[0].args).toEqual({ p_on_my_requests: false, p_on_queue: null });

    sb.byFn.corner_mail_state = ok([{ mail_enabled: true, waiting: '2', sent_today: 5, failed_7d: null, last_sent_at: 'nope', last_error: ' 422 bad ' }]);
    expect((await loadMailState()).data).toEqual({ mail_enabled: true, waiting: 2, sent_today: 5, failed_7d: 0, last_sent_at: null, last_error: '422 bad' });

    sb.byFn.corner_mail_invite = ok('queued');
    expect(await mailInvite('i3', TOKEN)).toMatchObject({ ok: true, data: 'queued' });
    expect(called('corner_mail_invite')[0].args).toEqual({ p_invite: 'i3', p_token: TOKEN });
    sb.byFn.corner_mail_invite = { data: null, error: { code: '22023', message: 'Email is off; the super admin turns it on in Corner -> Settings' } };
    expect(await mailInvite('i3', TOKEN)).toMatchObject({ ok: false, error: 'Email is off; the super admin turns it on in Corner -> Settings' });
  });

  it('flushMail asks corner-mail to send, never fails, and stops asking once it is not deployed', async () => {
    await flushMail();
    expect(flushes()).toEqual([{ fn: 'corner-mail', o: { body: { action: 'flush' } } }]);
    sb.invoke = () => Promise.reject(new Error('network down'));
    await expect(flushMail()).resolves.toBeUndefined();
    sb.invoke = () => { throw new Error('thrown at once'); };
    await expect(flushMail()).resolves.toBeUndefined();
    sb.invoke = () => Promise.resolve({ data: null, error: { name: 'FunctionsHttpError', message: 'Edge Function returned a non-2xx status code', context: { status: 403 } } });
    await flushMail();
    expect(flushes()).toHaveLength(4);
    sb.invoke = () => Promise.resolve({ data: null, error: { name: 'FunctionsHttpError', message: 'Edge Function returned a non-2xx status code', context: { status: 404 } } });
    await flushMail();
    expect(flushes()).toHaveLength(5);
    await flushMail();
    await flushMail();
    expect(flushes()).toHaveLength(5);   // not deployed: not asked again for a while
    resetMailMemo();
    await flushMail();
    expect(flushes()).toHaveLength(6);
  });
});

// ---- the Corner ---------------------------------------------------------------------------------

describe('/corpus/corner, email', () => {
  it('a researcher: Settings has the one choice, kept as soon as it is changed', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_mail_prefs = ok([PREFS()]);
    sb.byFn.corner_mail_prefs_set = ok(true);
    mount('/corpus/corner?tab=settings');
    const box = await screen.findByRole('checkbox', { name: 'Email me when my requests finish' });
    expect(screen.getByRole('tab', { name: 'Settings' })).toHaveAttribute('aria-selected', 'true');
    expect(box).toBeChecked();
    expect(screen.queryByRole('checkbox', { name: /researcher's request waits/ })).toBeNull();
    expect(screen.queryByLabelText('Dollars a day')).toBeNull();     // the super admin's
    expect(screen.queryByText(/Email from the Corner \(super admin\)/)).toBeNull();
    expect(screen.getByText(/The emails come from nartiang.org to the address you sign in with/)).toBeInTheDocument();
    expect(screen.queryByText(/is off at the moment/)).toBeNull();
    fireEvent.click(box);
    await waitFor(() => expect(called('corner_mail_prefs_set')).toHaveLength(1));
    expect(called('corner_mail_prefs_set')[0].args).toEqual({ p_on_my_requests: false, p_on_queue: null });
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(box).not.toBeChecked();
  });

  it('a refused change is put back and the reason shown; mail off is said', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_mail_prefs = ok([PREFS({ mail_enabled: false })]);
    sb.byFn.corner_mail_prefs_set = { data: null, error: { code: '42501', message: "The Researchers' Corner is open to invited researchers and editors." } };
    mount('/corpus/corner?tab=settings');
    const box = await screen.findByRole('checkbox', { name: 'Email me when my requests finish' });
    expect(screen.getByText(/Email from the Corner is off at the moment/)).toBeInTheDocument();
    fireEvent.click(box);
    expect(await screen.findByRole('alert')).toHaveTextContent('open to invited researchers and editors');
    expect(box).toBeChecked();
  });

  it('without C12 there is no Settings tab for a researcher, and no email anywhere', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corner_mail_prefs = MISSING('corner_mail_prefs');
    mount('/corpus/corner?tab=settings');
    expect(await screen.findByRole('tab', { name: 'Ask the desk' })).toHaveAttribute('aria-selected', 'true');
    await waitFor(() => expect(called('corner_mail_prefs')).toHaveLength(1));
    expect(screen.queryByRole('tab', { name: 'Settings' })).toBeNull();
    expect(screen.queryByText(/Email me/)).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('an editor also chooses the queue emails, and sees the mail line in Sync', async () => {
    sb.byFn.corner_me = ok([ME({ is_editor: true })]);
    sb.byFn.corner_mail_prefs = ok([PREFS({ is_editor: true, on_queue: true })]);
    sb.byFn.corner_mail_prefs_set = ok(true);
    sb.byFn.corner_mail_state = ok([{
      mail_enabled: true, waiting: 2, sent_today: 5, failed_7d: 1, last_sent_at: new Date(Date.now() - 60000).toISOString(),
      last_error: 'HTTP 422: the domain is not verified',
    }]);
    const view = mount('/corpus/corner?tab=settings');
    const queue = await screen.findByRole('checkbox', { name: "Email me when a researcher's request waits" });
    fireEvent.click(queue);
    await waitFor(() => expect(called('corner_mail_prefs_set')).toHaveLength(1));
    expect(called('corner_mail_prefs_set')[0].args).toEqual({ p_on_my_requests: null, p_on_queue: false });
    view.unmount();

    mount('/corpus/corner?tab=sync');
    const line = await screen.findByRole('region', { name: 'Email' });
    expect(within(line).getByText(/^on: 2 waiting, 5 sent today, 1 email given up in the last 7 days; last sent \d{2}:\d{2}$/)).toBeInTheDocument();
    expect(within(line).getByText('HTTP 422: the domain is not verified')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'The mirror' })).toBeInTheDocument();
  });

  it('the super admin: email on, From checked first, Reply-to emptied, the site address', async () => {
    sb.byFn.corner_me = ok([ME({ is_editor: true, is_super_admin: true })]);
    sb.byFn.corner_mail_prefs = ok([PREFS({ is_editor: true, mail_enabled: false, mail_from: 'Srangam desk <desk@nartiang.org>' })]);
    sb.byFn.corner_settings_set = ok('true');
    mount('/corpus/corner?tab=settings');
    expect(await screen.findByLabelText('Dollars a day')).toBeInTheDocument();   // as before
    const card = (await screen.findByText('Email from the Corner (super admin)')).closest('div.space-y-4') as HTMLElement;
    const row = (label: string) => within(card).getByText(label, { selector: 'p' }).closest('div.space-y-2') as HTMLElement;
    const sending = within(card).getByRole('checkbox', { name: "Send the Corner's emails" });
    expect(sending).not.toBeChecked();
    fireEvent.click(sending);
    fireEvent.click(within(row('Sending')).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(called('corner_settings_set')).toHaveLength(1));
    expect(called('corner_settings_set')[0].args).toEqual({ p_key: 'mail_enabled', p_value: 'true' });
    expect(await within(row('Sending')).findByText('Saved: on')).toBeInTheDocument();

    const from = within(card).getByLabelText('Name and address');
    expect(from).toHaveValue('Srangam desk <desk@nartiang.org>');
    fireEvent.change(from, { target: { value: 'desk@nartiang.org' } });
    fireEvent.click(within(row('From')).getByRole('button', { name: 'Save' }));
    expect(await within(row('From')).findByRole('alert')).toHaveTextContent(/A name and an address/);
    expect(called('corner_settings_set')).toHaveLength(1);
    sb.byFn.corner_settings_set = ok('The Srangam desk <corner@nartiang.org>');
    fireEvent.change(from, { target: { value: ' The Srangam desk <corner@nartiang.org> ' } });
    fireEvent.click(within(row('From')).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(called('corner_settings_set')).toHaveLength(2));
    expect(called('corner_settings_set')[1].args).toEqual({ p_key: 'mail_from', p_value: 'The Srangam desk <corner@nartiang.org>' });

    sb.byFn.corner_settings_set = ok('');
    fireEvent.click(within(row('Reply-to')).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(called('corner_settings_set')).toHaveLength(3));
    expect(called('corner_settings_set')[2].args).toEqual({ p_key: 'mail_reply_to', p_value: '' });
    expect(await within(row('Reply-to')).findByText('Saved: (none)')).toBeInTheDocument();

    sb.byFn.corner_settings_set = ok('https://srangam.nartiang.org');
    fireEvent.change(within(card).getByLabelText('Address', { selector: '#mail-site' }), { target: { value: 'https://Srangam.nartiang.org/' } });
    fireEvent.click(within(row("The site's address in the emails")).getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(called('corner_settings_set')).toHaveLength(4));
    expect(called('corner_settings_set')[3].args).toEqual({ p_key: 'site_url', p_value: 'https://srangam.nartiang.org' });
  });

  it('the waiting emails are sent after a request is made, not after a refusal', async () => {
    sb.byFn.corner_me = ok([ME()]);
    sb.byFn.corpus_reader_docs = ok([DOC]);
    sb.byFn.corner_request_create = ok([{ request_id: 7, request_status: 'pending', est_usd: 0.01, message: "Waiting for an editor's approval." }]);
    mount('/corpus/corner?tab=ask&kind=story_range&doc=nilamata_seg&from=25.2&to=25.9');
    const form = await screen.findByRole('form', { name: 'A story from passages you choose' });
    await waitFor(() => expect(screen.getByLabelText('The text')).toHaveValue('nilamata_seg'));
    fireEvent.change(within(form).getByLabelText('A working title'), { target: { value: 'Vitasta flows' } });
    sb.byFn.corner_request_create = { data: null, error: { code: '22023', message: 'from and to must be translated passages of this text' } };
    fireEvent.click(within(form).getByRole('button', { name: 'Ask the desk' }));
    expect(await screen.findByText('from and to must be translated passages of this text')).toBeInTheDocument();
    expect(flushes()).toHaveLength(0);
    sb.byFn.corner_request_create = ok([{ request_id: 7, request_status: 'pending', est_usd: 0.01, message: "Waiting for an editor's approval." }]);
    fireEvent.click(within(form).getByRole('button', { name: 'Ask the desk' }));
    expect(await screen.findByText(/\(request #7\)/)).toBeInTheDocument();
    await waitFor(() => expect(flushes()).toHaveLength(1));
    expect(flushes()[0].o).toEqual({ body: { action: 'flush' } });
  });

  it('and after an editor decides (a rejection is emailed at once); a failing corner-mail says nothing', async () => {
    sb.byFn.corner_me = ok([ME({ is_editor: true })]);
    sb.byFn.corner_requests = ok([{
      id: 8, kind: 'story_range', label: 'A story from passages you choose', doc_code: 'nilamata_seg', doc_title: 'Nilamata Purana',
      params: { from: '25.2', to: '25.9', title: 'Vitasta flows' }, note: null, status: 'pending', est_usd: 0.01, cost_usd: null,
      requested_at: '2026-10-09T10:00:00Z', mine: false, requester: 'researcher@uni.edu', decided_at: null, decision_note: null,
      started_at: null, finished_at: null, message: null, result: null, preview: null, total: 1,
    }]);
    sb.byFn.corner_request_decide = ok([{ request_status: 'rejected', message: 'Rejected.' }]);
    sb.invoke = () => Promise.reject(new Error('Failed to send a request to the Edge Function'));
    mount('/corpus/corner?tab=queue');
    const queue = await screen.findByRole('region', { name: 'Waiting for an editor' });
    fireEvent.click(await within(queue).findByRole('button', { name: 'Reject' }));
    await waitFor(() => expect(called('corner_request_decide')).toHaveLength(1));
    expect(await within(queue).findByText('Rejected.')).toBeInTheDocument();
    await waitFor(() => expect(flushes()).toHaveLength(1));
    expect(screen.queryByText(/Edge Function/)).toBeNull();
  });
});

// ---- the super admin's invitation -------------------------------------------------------------

describe('/admin/researchers: an invitation sent from nartiang.org', () => {
  const adminData = () => {
    auth.value = SUPER;
    sb.byFn.corpus_access_mode = ok('signed_in');
    sb.byFn.research_invites_list = ok([]);
    sb.byFn.rbac_members_list = ok([]);
    sb.byFn.rbac_audit_list = ok([]);
    sb.byFn.research_invite_create = ok([{ invite_id: 'i3', email: 'new@uni.test', token: TOKEN, expires_at: '2026-10-22T10:00:00Z', reissued: false }]);
  };
  const make = async () => {
    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: 'new@uni.test' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create invitation' })); });
    return screen.findByLabelText('Invitation link');
  };

  it('queues the email with the token, then asks corner-mail to send it; the mailto stays', async () => {
    adminData();
    sb.byFn.corner_mail_prefs = ok([PREFS({ is_editor: true, mail_from: 'Srangam desk <desk@nartiang.org>' })]);
    sb.byFn.corner_mail_invite = ok('queued');
    mount('/admin/researchers');
    await make();
    expect(screen.getByRole('link', { name: /Email it/ }).getAttribute('href')).toMatch(/^mailto:new@uni.test\?subject=/);
    const send = await screen.findByRole('button', { name: 'Send it from nartiang.org' });
    expect(called('corner_mail_invite')).toHaveLength(0);
    await act(async () => { fireEvent.click(send); });
    await waitFor(() => expect(called('corner_mail_invite')).toHaveLength(1));
    expect(called('corner_mail_invite')[0].args).toEqual({ p_invite: 'i3', p_token: TOKEN });
    expect(await screen.findByText(/Queued: it is sent from nartiang.org/)).toBeInTheDocument();
    await waitFor(() => expect(flushes()).toHaveLength(1));
    expect(screen.getByRole('button', { name: 'Send it again from nartiang.org' })).toBeInTheDocument();
  });

  it("the server's refusal is shown; with mail off the button waits and says where to turn it on", async () => {
    adminData();
    sb.byFn.corner_mail_prefs = ok([PREFS({ is_editor: true, mail_enabled: true })]);
    sb.byFn.corner_mail_invite = { data: null, error: { code: '22023', message: 'not a pending invitation' } };
    const view = mount('/admin/researchers');
    await make();
    await act(async () => { fireEvent.click(await screen.findByRole('button', { name: 'Send it from nartiang.org' })); });
    expect(await screen.findByText('not a pending invitation')).toBeInTheDocument();
    expect(flushes()).toHaveLength(0);
    view.unmount();

    sb.byFn.corner_mail_prefs = ok([PREFS({ is_editor: true, mail_enabled: false })]);
    mount('/admin/researchers');
    await make();
    expect(await screen.findByRole('button', { name: 'Send it from nartiang.org' })).toBeDisabled();
    expect(screen.getByRole('link', { name: /the Researchers' Corner, Settings/ })).toHaveAttribute('href', '/corpus/corner?tab=settings');
  });

  it('without C12 there is no such button, and nothing is asked of the mail before an invitation is made', async () => {
    adminData();
    sb.byFn.corner_mail_prefs = MISSING('corner_mail_prefs');
    mount('/admin/researchers');
    await screen.findByLabelText('Email address');
    expect(called('corner_mail_prefs')).toHaveLength(0);
    await make();
    await waitFor(() => expect(called('corner_mail_prefs')).toHaveLength(1));
    expect(screen.queryByRole('button', { name: /nartiang.org/ })).toBeNull();
    expect(screen.getByRole('link', { name: /Email it/ })).toBeInTheDocument();
  });
});
