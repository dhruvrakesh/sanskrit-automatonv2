/**
 * NAV_RBAC_2026_10_10 - the working corpus in the site's navigation, by role: the header's Corpus
 * menu (with Learn), the phone's bottom tab, Admin for admins only, Sign in while signed out, and the
 * admin sidebar's Working corpus group. useAuth is set per test; supabase answers per function.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

type Answer = { data: unknown; error: { code?: string; message: string } | null };
const sb = vi.hoisted(() => ({ byFn: {} as Record<string, Answer>, calls: [] as string[] }));
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    rpc: (fn: string) => { sb.calls.push(fn); return Promise.resolve(sb.byFn[fn] ?? { data: null, error: null }); },
  },
}));
const auth = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => auth.value }));
// The header's heavier neighbours are not what is tested here.
vi.mock('@/components/navigation/SearchResults', () => ({ SearchResults: () => null }));
vi.mock('@/components/language/EnhancedLanguageSwitcher', () => ({ EnhancedLanguageSwitcher: () => null }));
vi.mock('@/components/ui/theme-toggle', () => ({ ThemeToggle: () => null }));

import { HeaderNav } from '@/components/navigation/HeaderNav';
import { AdminLayout } from '@/components/admin/AdminLayout';
import { CORPUS_LINKS } from '@/components/navigation/CorpusMenu';
import { readsByRole } from '@/lib/corpusAccess';

const NAV = {
  primary: [{ label: 'Articles', href: '/articles' }, { label: 'About', href: '/about' }],
  utilities: { searchPlaceholder: 'Search', languages: ['en'], i18nOptions: { showIAST: false } },
};
const base = { isLoading: false, roleChecked: true, isAdmin: false, isSuperAdmin: false, isResearcher: false, roles: [] as string[],
  refreshRoles: vi.fn(), signOut: vi.fn(() => Promise.resolve()) };
const SIGNED_OUT = { ...base, user: null };
const LOADING = { ...base, user: null, isLoading: true };
const RESEARCHER = { ...base, user: { id: 'kan', email: 'kanika@example.org' }, isResearcher: true, roles: ['researcher'] };
const SUPER = { ...base, user: { id: 'dhruv', email: 'dhruv.rakesh@gmail.com' }, isAdmin: true, isSuperAdmin: true, roles: ['admin', 'super_admin'] };
const PLAIN = { ...base, user: { id: 'u9', email: 'someone@example.org' } };
const ROLES_PENDING = { ...RESEARCHER, roleChecked: false, roles: [] };

function mountHeader() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/']}>
        <HeaderNav />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  sb.byFn = {}; sb.calls = [];
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(NAV) })));
});
afterEach(() => { vi.unstubAllGlobals(); });

describe('who reads the corpus, by role', () => {
  it('researchers, admins and the super admin; nobody else by role alone', () => {
    expect(readsByRole(['researcher'])).toBe(true);
    expect(readsByRole(['admin'])).toBe(true);
    expect(readsByRole(['super_admin'])).toBe(true);
    expect(readsByRole(['user', 'moderator'])).toBe(false);
    expect(readsByRole([])).toBe(false);
    expect(readsByRole(undefined)).toBe(false);
  });

  it('the menu lists every corpus section, Learn and the Corner included', () => {
    const hrefs = CORPUS_LINKS.map((l) => l.href);
    for (const h of ['/corpus', '/corpus/stories', '/corpus/names', '/corpus/images', '/corpus/novels', '/corpus/corner', '/corpus/learn', '/texts']) {
      expect(hrefs).toContain(h);
    }
  });
});

describe('the header', () => {
  it('signed out: Sign in, no Corpus, no Admin, and no question to the database', async () => {
    auth.value = SIGNED_OUT;
    mountHeader();
    expect(await screen.findByRole('link', { name: /Sign in/ })).toHaveAttribute('href', '/auth');
    expect(screen.queryByRole('button', { name: /Corpus/ })).toBeNull();
    expect(screen.queryByRole('link', { name: /Admin/ })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Corpus' })).toBeNull();
    expect(sb.calls).toEqual([]);
  });

  it('while the session is read: neither Sign in nor Admin', async () => {
    auth.value = LOADING;
    mountHeader();
    expect(await screen.findByRole('link', { name: 'Articles' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Sign in/ })).toBeNull();
    expect(screen.queryByRole('link', { name: /Admin/ })).toBeNull();
  });

  it('a researcher: the Corpus menu with Learn and the Corner, the Corpus tab, no Admin, no extra question', async () => {
    auth.value = RESEARCHER;
    mountHeader();
    const btn = await screen.findByRole('button', { name: /Corpus/ });
    expect(screen.queryByRole('link', { name: /Admin/ })).toBeNull();
    expect(screen.queryByRole('link', { name: /Sign in/ })).toBeNull();
    expect(screen.getByRole('link', { name: 'Corpus' })).toHaveAttribute('href', '/corpus');
    fireEvent.click(btn);
    expect(await screen.findByRole('link', { name: /^Learn/ })).toHaveAttribute('href', '/corpus/learn');
    expect(screen.getByRole('link', { name: /^Researchers' Corner/ })).toHaveAttribute('href', '/corpus/corner');
    expect(sb.calls).not.toContain('corpus_reader_allowed');
  });

  it('the super admin: the Corpus menu and Admin', async () => {
    auth.value = SUPER;
    mountHeader();
    expect(await screen.findByRole('button', { name: /Corpus/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Admin/ })).toHaveAttribute('href', '/admin');
  });

  it('roles not read yet: no Corpus menu until they are', async () => {
    auth.value = ROLES_PENDING;
    mountHeader();
    expect(await screen.findByRole('link', { name: 'Articles' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Corpus/ })).toBeNull();
    expect(sb.calls).toEqual([]);
  });

  it('a signed-in account with no role asks the database once: allowed (a reader list, or open to all signed in)', async () => {
    auth.value = PLAIN;
    sb.byFn.corpus_reader_allowed = { data: true, error: null };
    mountHeader();
    expect(await screen.findByRole('button', { name: /Corpus/ })).toBeInTheDocument();
    expect(sb.calls.filter((c) => c === 'corpus_reader_allowed')).toHaveLength(1);
    expect(screen.queryByRole('link', { name: /Admin/ })).toBeNull();
  });

  it('... and not allowed: no Corpus anywhere', async () => {
    auth.value = PLAIN;
    sb.byFn.corpus_reader_allowed = { data: false, error: null };
    mountHeader();
    await waitFor(() => expect(sb.calls).toContain('corpus_reader_allowed'));
    expect(screen.queryByRole('button', { name: /Corpus/ })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Corpus' })).toBeNull();
  });

  it('a database error counts as not allowed', async () => {
    auth.value = PLAIN;
    sb.byFn.corpus_reader_allowed = { data: null, error: { code: 'PGRST202', message: 'Could not find the function' } };
    mountHeader();
    await waitFor(() => expect(sb.calls).toContain('corpus_reader_allowed'));
    expect(screen.queryByRole('button', { name: /Corpus/ })).toBeNull();
  });
});

describe('the admin sidebar', () => {
  const wide = () => Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 1280 });
  const narrow = () => Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 384 });

  it('has the Working corpus group: Library, the Corner, Learn', async () => {
    auth.value = SUPER;
    wide();
    try {
      const qc = new QueryClient();
      render(
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={['/admin']}>
            <AdminLayout />
          </MemoryRouter>
        </QueryClientProvider>,
      );
      expect(await screen.findByText('Working corpus')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /^Learn/ })).toHaveAttribute('href', '/corpus/learn');
      expect(screen.getByRole('link', { name: /Corner \(ask the desk\)/ })).toHaveAttribute('href', '/corpus/corner');
      expect(screen.getByRole('link', { name: /^Library/ })).toHaveAttribute('href', '/corpus');
    } finally { narrow(); }
  });
});
