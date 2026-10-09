/**
 * AUTH_ROLE_2026_10_08 - the sign-in loop. A signed-in account that is not an admin, opening /auth,
 * was sent to /admin/tags, and ProtectedRoute sent it back to /auth, round and round. The same race
 * sent admins to /auth and back after each sign-in: the gate decided before has_role had answered.
 * The real AuthProvider, ProtectedRoute and Auth page, against a mocked supabase whose has_role
 * answer is held back until the test releases it.
 * RBAC_RESEARCHERS_2026_10_08: AuthProvider also asks my_roles() (C7), at the same time. Here it
 * answers at once as the database did before C7 (no such function), so every test below is the
 * same as before; rbac-auth.test.tsx covers the roles themselves.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';

type FakeSession = { user: { id: string } } | null;
type Listener = (event: string, session: FakeSession) => void;
type RoleAnswer = { data: boolean; error: null };

const h = vi.hoisted(() => ({
  session: null as FakeSession,
  listeners: [] as Listener[],
  pending: [] as Array<{ uid: string; resolve: (v: RoleAnswer) => void }>,
  answer: null as null | boolean,      // when set, has_role answers at once
  rpcCalls: 0,                         // has_role calls only
  myRolesCalls: 0,                     // LOAD_L1_2026_10_09
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
      signUp: vi.fn(() => Promise.resolve({ error: null })),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
    },
    rpc: (fn: string, args: { _user_id: string }) => {
      if (fn === 'my_roles') {
        h.myRolesCalls += 1;   // LOAD_L1_2026_10_09
        return Promise.resolve({ data: null, error: { code: 'PGRST202', message: 'Could not find the function public.my_roles' } });
      }
      h.rpcCalls += 1;
      if (h.answer !== null) return Promise.resolve({ data: h.answer, error: null });
      return new Promise((resolve) => h.pending.push({ uid: args._user_id, resolve }));
    },
  },
}));

import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/admin/ProtectedRoute';
import Auth from '@/pages/Auth';

function Where() {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search}</output>;
}

function Probe() {
  const { user, isAdmin, roleChecked } = useAuth();
  return <output data-testid="probe">{`${user ? user.id : '-'}|${isAdmin}|${roleChecked}`}</output>;
}

function mount(path: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <Where />
        <Probe />
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/admin/tags" element={<ProtectedRoute><p>admin area</p></ProtectedRoute>} />
          <Route path="/corpus" element={<p>corpus page</p>} />
          <Route path="/corpus/:docCode" element={<p>corpus document</p>} />
          <Route path="/" element={<p>home page</p>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

const where = () => screen.getByTestId('where').textContent;
const release = async (value: boolean) => {
  await act(async () => { h.pending.splice(0).forEach((p) => p.resolve({ data: value, error: null })); });
};

beforeEach(() => {
  h.session = null; h.listeners = []; h.pending = []; h.answer = null; h.rpcCalls = 0; h.myRolesCalls = 0;
});

describe('ProtectedRoute', () => {
  it('a signed-in account that is not an admin is told so, and stays put', async () => {
    h.session = { user: { id: 'reader' } }; h.answer = false;
    mount('/admin/tags');
    expect(await screen.findByText(/This area is for the site's editors/)).toBeInTheDocument();
    expect(where()).toBe('/admin/tags');
    expect(screen.getByRole('link', { name: /Read the working corpus/ }).getAttribute('href')).toBe('/corpus');
    expect(screen.queryByText('admin area')).toBeNull();
  });

  it('an admin waits for the role and is never sent to /auth', async () => {
    h.session = { user: { id: 'admin' } };
    mount('/admin/tags');
    await waitFor(() => expect(h.pending.length).toBe(1));
    expect(screen.getByRole('status', { name: 'Checking access' })).toBeInTheDocument();
    expect(where()).toBe('/admin/tags');
    await release(true);
    expect(await screen.findByText('admin area')).toBeInTheDocument();
    expect(where()).toBe('/admin/tags');
  });

  it('signed out: to /auth, with the admin page to come back to', async () => {
    mount('/admin/tags');
    await waitFor(() => expect(where()).toBe('/auth?next=%2Fadmin%2Ftags'));
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });
});

describe('/auth when already signed in', () => {
  it('not an admin, no next: on to /corpus, not to /admin and back', async () => {
    h.session = { user: { id: 'reader' } };
    mount('/auth');
    await waitFor(() => expect(h.pending.length).toBe(1));
    expect(screen.getByRole('status', { name: 'Signing in' })).toBeInTheDocument();
    expect(where()).toBe('/auth');
    await release(false);
    expect(await screen.findByText('corpus page')).toBeInTheDocument();
    expect(where()).toBe('/corpus');
    expect(h.rpcCalls).toBe(1);
  });

  it('an admin, no next: on to /admin/tags', async () => {
    h.session = { user: { id: 'admin' } }; h.answer = true;
    mount('/auth');
    expect(await screen.findByText('admin area')).toBeInTheDocument();
    expect(where()).toBe('/admin/tags');
  });

  it('with ?next= on this site: back to that page', async () => {
    h.session = { user: { id: 'reader' } }; h.answer = false;
    mount('/auth?next=%2Fcorpus%2Fmarkandeya_purana');
    expect(await screen.findByText('corpus document')).toBeInTheDocument();
    expect(where()).toBe('/corpus/markandeya_purana');
  });
});

describe('the role answer', () => {
  it('a late answer for a user who has signed out is dropped', async () => {
    h.session = { user: { id: 'admin' } };
    mount('/');
    await waitFor(() => expect(h.pending.length).toBe(1));
    expect(screen.getByTestId('probe').textContent).toBe('admin|false|false');
    await act(async () => { h.listeners.forEach((cb) => cb('SIGNED_OUT', null)); });
    await release(true);
    expect(screen.getByTestId('probe').textContent).toBe('-|false|true');
  });

  it('signing out and in again asks again rather than reusing the old answer', async () => {
    h.session = { user: { id: 'admin' } }; h.answer = true;
    mount('/');
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toBe('admin|true|true'));
    await act(async () => { h.listeners.forEach((cb) => cb('SIGNED_OUT', null)); });
    expect(screen.getByTestId('probe').textContent).toBe('-|false|true');
    h.answer = null;
    await act(async () => {
      h.listeners.forEach((cb) => cb('SIGNED_IN', { user: { id: 'admin' } }));
      await new Promise((r) => setTimeout(r, 5));
    });
    expect(screen.getByTestId('probe').textContent).toBe('admin|false|false');
    await release(true);
    expect(screen.getByTestId('probe').textContent).toBe('admin|true|true');
  });
});

describe('LOAD_L1_2026_10_09: one question per page load', () => {
  it('the listener and getSession, together, ask has_role and my_roles once', async () => {
    h.session = { user: { id: 'admin' } };
    mount('/');
    await act(async () => {
      h.listeners.forEach((cb) => cb('INITIAL_SESSION', { user: { id: 'admin' } }));
      h.listeners.forEach((cb) => cb('SIGNED_IN', { user: { id: 'admin' } }));
      await new Promise((r) => setTimeout(r, 5));
    });
    await waitFor(() => expect(h.pending.length).toBe(1));
    expect(h.rpcCalls).toBe(1);
    expect(h.myRolesCalls).toBe(1);
    await release(true);
    expect(screen.getByTestId('probe').textContent).toBe('admin|true|true');
  });

  it('once answered, a later event asks again (a role changed since is seen)', async () => {
    h.session = { user: { id: 'admin' } }; h.answer = true;
    mount('/');
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toBe('admin|true|true'));
    expect(h.rpcCalls).toBe(1);
    h.answer = false;
    await act(async () => {
      h.listeners.forEach((cb) => cb('TOKEN_REFRESHED', { user: { id: 'admin' } }));
      await new Promise((r) => setTimeout(r, 5));
    });
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toBe('admin|false|true'));
    expect(h.rpcCalls).toBe(2);
  });

  it('another user signing in is not given the first user\'s answer', async () => {
    h.session = { user: { id: 'admin' } };
    mount('/');
    await waitFor(() => expect(h.pending.length).toBe(1));
    await act(async () => {
      h.listeners.forEach((cb) => cb('SIGNED_IN', { user: { id: 'reader' } }));
      await new Promise((r) => setTimeout(r, 5));
    });
    expect(h.pending.map((p) => p.uid)).toEqual(['admin', 'reader']);
    await act(async () => { h.pending.splice(0).forEach((p) => p.resolve({ data: p.uid === 'admin', error: null })); });
    expect(screen.getByTestId('probe').textContent).toBe('reader|false|true');
  });
});
