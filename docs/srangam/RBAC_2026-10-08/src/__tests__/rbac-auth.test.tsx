/**
 * RBAC_RESEARCHERS_2026_10_08 - the roles in AuthProvider, and the sign-up path of an invited
 * researcher. The real AuthProvider and Auth page against a mocked supabase: has_role answers
 * whether the account is an admin (as before), my_roles answers its roles (C7) or does not exist
 * (before C7).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';

type FakeSession = { user: { id: string; email?: string } } | null;
type Listener = (event: string, session: FakeSession) => void;

const h = vi.hoisted(() => ({
  session: null as FakeSession,
  listeners: [] as Listener[],
  admin: false,
  roles: null as null | string[],           // null: my_roles does not exist (before C7)
  calls: [] as string[],
  signUps: [] as Array<{ email: string; password: string; options?: { emailRedirectTo?: string } }>,
}));

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: {
      onAuthStateChange: (cb: Listener) => {
        h.listeners.push(cb);
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
      getSession: () => Promise.resolve({ data: { session: h.session } }),
      signInWithPassword: vi.fn(() => Promise.resolve({ error: null })),
      signUp: vi.fn((a: { email: string; password: string; options?: { emailRedirectTo?: string } }) => {
        h.signUps.push(a);
        return Promise.resolve({ data: { session: null, user: null }, error: null });
      }),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
    },
    rpc: (fn: string) => {
      h.calls.push(fn);
      if (fn === 'has_role') return Promise.resolve({ data: h.admin, error: null });
      if (fn === 'my_roles') {
        return Promise.resolve(h.roles
          ? { data: h.roles, error: null }
          : { data: null, error: { code: 'PGRST202', message: 'Could not find the function public.my_roles' } });
      }
      return Promise.resolve({ data: null, error: null });
    },
  },
}));

import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import Auth from '@/pages/Auth';

const TOKEN = 'ab'.repeat(32);

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search}</output>;
}

function Probe() {
  const { roles, isAdmin, isSuperAdmin, isResearcher, roleChecked, refreshRoles } = useAuth();
  return (
    <>
      <output data-testid="probe">{`${roles.join(',')}|${isAdmin}|${isSuperAdmin}|${isResearcher}|${roleChecked}`}</output>
      <button type="button" onClick={() => { refreshRoles(); }}>refresh roles</button>
    </>
  );
}

function mount(path: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <Where />
        <Probe />
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/invite/:token" element={<p>invite page</p>} />
          <Route path="/admin/tags" element={<p>admin area</p>} />
          <Route path="/corpus" element={<p>corpus page</p>} />
          <Route path="/" element={<p>home page</p>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

const probe = () => screen.getByTestId('probe').textContent;

beforeEach(() => {
  h.session = null; h.listeners = []; h.admin = false; h.roles = null; h.calls = []; h.signUps = [];
});

describe('roles in AuthProvider', () => {
  it('the super admin: both questions asked together, isSuperAdmin once known', async () => {
    h.session = { user: { id: 'dhruv' } }; h.admin = true; h.roles = ['admin', 'super_admin'];
    mount('/');
    await waitFor(() => expect(probe()).toBe('admin,super_admin|true|true|false|true'));
    expect(h.calls.filter((c) => c === 'has_role')).toHaveLength(1);
    expect(h.calls.filter((c) => c === 'my_roles')).toHaveLength(1);
  });

  it('a researcher reads as a researcher and not as an admin', async () => {
    h.session = { user: { id: 'scholar' } }; h.roles = ['researcher'];
    mount('/');
    await waitFor(() => expect(probe()).toBe('researcher|false|false|true|true'));
  });

  it('before C7 (no my_roles): the roles follow has_role, nothing breaks', async () => {
    h.session = { user: { id: 'dhruv' } }; h.admin = true;
    mount('/');
    await waitFor(() => expect(probe()).toBe('admin|true|false|false|true'));
  });

  it('refreshRoles asks again (after accepting an invitation)', async () => {
    h.session = { user: { id: 'scholar' } }; h.roles = [];
    mount('/');
    await waitFor(() => expect(probe()).toBe('|false|false|false|true'));
    h.roles = ['researcher'];
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'refresh roles' })); });
    await waitFor(() => expect(probe()).toBe('researcher|false|false|true|true'));
  });

  it('signing out clears the roles', async () => {
    h.session = { user: { id: 'dhruv' } }; h.admin = true; h.roles = ['admin', 'super_admin'];
    mount('/');
    await waitFor(() => expect(probe()).toBe('admin,super_admin|true|true|false|true'));
    await act(async () => { h.listeners.forEach((cb) => cb('SIGNED_OUT', null)); });
    expect(probe()).toBe('|false|false|false|true');
  });
});

describe('the Auth page for an invited researcher', () => {
  it('?tab=signup opens the sign-up form; the confirmation email comes back to the invitation', async () => {
    mount(`/auth?next=%2Finvite%2F${TOKEN}&tab=signup`);
    expect(await screen.findByText(/with the email address your invitation was sent to/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Email', { selector: '#signup-email' }), { target: { value: 'scholar@uni.test' } });
    fireEvent.change(screen.getByLabelText('Password', { selector: '#signup-password' }), { target: { value: 'secret12' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create Account' })); });
    expect(h.signUps).toHaveLength(1);
    expect(h.signUps[0].options?.emailRedirectTo).toBe(`${window.location.origin}/invite/${TOKEN}`);
  });

  it('without next the confirmation email still goes to /admin/tags, as before', async () => {
    mount('/auth?tab=signup');
    fireEvent.change(await screen.findByLabelText('Email', { selector: '#signup-email' }), { target: { value: 'a@b.test' } });
    fireEvent.change(screen.getByLabelText('Password', { selector: '#signup-password' }), { target: { value: 'secret12' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create Account' })); });
    expect(h.signUps[0].options?.emailRedirectTo).toBe(`${window.location.origin}/admin/tags`);
  });

  it('the login tab stays the default', async () => {
    mount('/auth');
    expect(await screen.findByRole('button', { name: 'Sign In' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create Account' })).toBeNull();
  });

  it('signed in already: straight back to the invitation', async () => {
    h.session = { user: { id: 'scholar' } }; h.roles = [];
    mount(`/auth?next=%2Finvite%2F${TOKEN}`);
    expect(await screen.findByText('invite page')).toBeInTheDocument();
    expect(screen.getByTestId('where').textContent).toBe(`/invite/${TOKEN}`);
  });
});
