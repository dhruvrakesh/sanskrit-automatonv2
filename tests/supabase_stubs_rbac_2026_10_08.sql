-- Test-only stand-ins for C7 (RBAC_RESEARCHERS_2026_10_08), on top of supabase_stubs_2026_10_08.sql.
-- Never run this on the live database: there auth.users and the user_roles policies already exist.
CREATE TABLE IF NOT EXISTS auth.users (
    id                  uuid PRIMARY KEY,
    email               varchar(255),
    email_confirmed_at  timestamptz,
    last_sign_in_at     timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);
-- public.user_roles as the Srangam migration 20251110042316 made it (the stub has two columns).
ALTER TABLE public.user_roles ADD COLUMN IF NOT EXISTS id uuid NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE public.user_roles ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.user_roles ADD COLUMN IF NOT EXISTS created_by uuid;
ALTER TABLE public.user_roles ADD COLUMN IF NOT EXISTS notes text;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_roles TO authenticated;
DROP POLICY IF EXISTS "Admins can view all roles" ON public.user_roles;
CREATE POLICY "Admins can view all roles" ON public.user_roles FOR SELECT TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));
DROP POLICY IF EXISTS "Only admins can manage roles" ON public.user_roles;
CREATE POLICY "Only admins can manage roles" ON public.user_roles FOR ALL TO authenticated
  USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));
