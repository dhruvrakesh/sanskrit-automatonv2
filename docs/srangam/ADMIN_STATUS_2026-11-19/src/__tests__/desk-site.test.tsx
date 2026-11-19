/**
 * ADMIN_STATUS_2026_11_19 - the desk and the site at a glance (the super admin): the mirror, the genealogies sent, the
 * desk's worker, who may read, the AI calls; "as of" and Refresh; a late desk, a late mirror and a call through another
 * provider said plainly; a refusal and a missing function said as such.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

type RpcAnswer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({ answer: null as unknown as RpcAnswer, calls: 0 }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string): Promise<RpcAnswer> => {
      if (fn === 'corpus_admin_status') sb.calls += 1;
      return Promise.resolve(fn === 'corpus_admin_status' ? sb.answer : { data: [], error: null });
    },
    functions: { invoke: () => Promise.resolve({ data: {}, error: null }) },
  },
}));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, isLoading: false, isAdmin: true, isSuperAdmin: true }) }));

import DeskSite, { ago, late, type AdminStatus } from '@/pages/admin/DeskSite';

const minAgo = (m: number) => new Date(Date.now() - m * 60000).toISOString();
function status(extra: Partial<AdminStatus> = {}): AdminStatus {
  return {
    as_of: minAgo(0),
    mirror: { texts: 212, retired: 9, last_text_synced: minAgo(90), passages_about: 151000, translations_about: 0,
              last_run: { started_at: minAgo(40), finished_at: minAgo(38) } },
    index: { dynasties: { rows: 517, last_changed: minAgo(300) }, vamsas: { rows: 10, last_changed: minAgo(200) },
             meta: { rows: 1, last_changed: minAgo(200) } },
    index_run: { mark: 'INDEX_SITE_2026_10_25', scheme: 'i2' },
    desk: { last_seen: minAgo(4), queued: 0, running: 0, pending: 1 },
    access: { mode: 'readers', since: '2026-10-09T01:29:51Z', readers_listed: 0, roles: { admin: 1, researcher: 3, super_admin: 1 } },
    ai_7d: [{ provider: 'gemini', model: 'gemini-2.5-flash', ok: true, calls: 28, last_call: minAgo(500) }],
    ai_functions_7d: { 'extract-citations': 28 },
    ...extra,
  };
}

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider><QueryClientProvider client={qc}><MemoryRouter><DeskSite /></MemoryRouter></QueryClientProvider></HelmetProvider>,
  );
}

beforeEach(() => { sb.answer = { data: [{ result: status() }], error: null }; sb.calls = 0; });

describe('the desk and the site', () => {
  it('says what the desk sends, when, and who may read it', async () => {
    mount();
    expect(await screen.findByText('Dynasties (the lines of 17 texts)')).toBeTruthy();
    expect(screen.getByText('517')).toBeTruthy();
    expect(screen.getByText('Vaṃśas (the dynasties across the texts)')).toBeTruthy();
    expect(screen.getByText('212')).toBeTruthy();
    expect(screen.getByText('about 1,51,000')).toBeTruthy();
    expect(screen.getByText('not counted yet')).toBeTruthy();
    expect(screen.getByText('admins, researchers and the readers listed')).toBeTruthy();
    expect(screen.getByText('Role: super admin')).toBeTruthy();
    expect(screen.getByText('gemini · gemini-2.5-flash')).toBeTruthy();
    expect(screen.getByLabelText('As of').textContent).toMatch(/^As of /);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('link', { name: 'Sūryavaṃśa and Candravaṃśa' }).getAttribute('href')).toBe('/corpus/genealogies/vamsas');
  });

  it('reads again only when asked', async () => {
    mount();
    await screen.findByText('517');
    expect(sb.calls).toBe(1);
    fireEvent.click(screen.getByRole('button', { name: /Refresh/ }));
    await vi.waitFor(() => expect(sb.calls).toBe(2));
  });

  it('says a late desk, a late mirror and another provider plainly', async () => {
    sb.answer = { data: [{ result: status({
      desk: { last_seen: minAgo(120), queued: 2, running: 0, pending: 0 },
      mirror: { texts: 1, retired: 0, last_text_synced: null, passages_about: 0, translations_about: 0, last_run: { started_at: minAgo(600), finished_at: null } },
      ai_7d: [{ provider: 'lovable', model: 'google/gemini-2.5-flash', ok: false, calls: 2, last_call: minAgo(5) }],
    }) }], error: null };
    mount();
    expect(await screen.findByText(/The desk has not been seen for more than 30 minutes/)).toBeTruthy();
    expect(screen.getByText(/The mirror has not run for more than 3 hours/)).toBeTruthy();
    expect(screen.getByText(/Calls went through lovable: the site should use your own Gemini or OpenAI key/)).toBeTruthy();
    expect(screen.getByText(/2 call\(s\) failed/)).toBeTruthy();
  });

  it('a refusal and a missing function are said as such', async () => {
    sb.answer = { data: null, error: { code: '42501', message: 'Only the super admin may do this.' } };
    const a = mount();
    expect(await screen.findByText('Only the super admin may see the desk and the site.')).toBeTruthy();
    a.unmount();
    sb.answer = { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.corpus_admin_status without parameters in the schema cache' } };
    mount();
    expect(await screen.findByText(/This page is not switched on yet/)).toBeTruthy();
  });

  it('counts the time plainly', () => {
    const now = new Date('2026-11-19T12:00:00Z');
    expect(ago(null, now)).toBe('never');
    expect(ago('2026-11-19T11:55:00Z', now)).toBe('5 min ago');
    expect(ago('2026-11-19T09:00:00Z', now)).toBe('3 h ago');
    expect(ago('2026-11-15T12:00:00Z', now)).toBe('4 days ago');
    expect(late('2026-11-19T11:50:00Z', 30, now)).toBe(false);
    expect(late('2026-11-19T11:00:00Z', 30, now)).toBe(true);
    expect(late(null, 30, now)).toBe(true);
  });
});
