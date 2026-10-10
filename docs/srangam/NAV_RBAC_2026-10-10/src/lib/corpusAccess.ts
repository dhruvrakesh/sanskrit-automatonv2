/**
 * Who may open the working corpus - NAV_RBAC_2026_10_10.
 *
 * The navigation shows the working corpus (and Learn, inside it) only to those the database lets
 * read it (public.corpus_reader_allowed(), C5 + C7): admins and the super admin always; researchers
 * while the access mode is 'readers'; anyone signed in while it is 'signed_in'; people on the reader
 * list. The roles the site already holds (AuthContext, my_roles) answer for researchers, admins and
 * the super admin with no request at all; only a signed-in account with none of those roles asks
 * corpus_reader_allowed(), once, and keeps the answer for ten minutes. Signed out: no request, no
 * link. The pages themselves still ask the database: this only decides what the menus show.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';

export const NAV_RBAC_MARK = 'NAV_RBAC_2026_10_10';

/** The roles that always read the working corpus in the access mode in use ('readers'). */
export const CORPUS_ROLES: readonly string[] = ['researcher', 'admin', 'super_admin'];

export const readsByRole = (roles: readonly string[] | null | undefined): boolean =>
  !!roles && roles.some((r) => CORPUS_ROLES.includes(r));

export interface CorpusAccess {
  /** Show the working corpus in the menus. */
  canRead: boolean;
  /** The answer is known (false while the session or the roles are still being read). */
  checked: boolean;
}

async function askAllowed(): Promise<boolean> {
  try {
    const db = supabase as unknown as { rpc: (fn: string) => PromiseLike<{ data: unknown; error: unknown }> };
    const { data, error } = await db.rpc('corpus_reader_allowed');
    return !error && data === true;
  } catch {
    return false;
  }
}

export function useCorpusAccess(): CorpusAccess {
  const { user, roles, roleChecked, isLoading } = useAuth();
  const uid = user?.id ?? null;
  const byRole = readsByRole(roles);
  const ask = !!uid && roleChecked && !byRole;
  const q = useQuery({
    queryKey: ['corpus', 'reader-allowed', uid],
    queryFn: askAllowed,
    enabled: ask,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
  if (!uid) return { canRead: false, checked: !isLoading };
  if (!roleChecked) return { canRead: false, checked: false };
  if (byRole) return { canRead: true, checked: true };
  return { canRead: q.data === true, checked: q.isFetched };
}
