-- ============================================================
-- C7a - two new roles (RBAC_RESEARCHERS_2026_10_08). RUN THIS ALONE, FIRST, then C7.
--
-- PostgreSQL will not let a new enum value be used in the transaction that added it, so the
-- values go in on their own; C7 uses them and refuses to run until they are here.
--   super_admin  grants and removes roles, invites researchers, sets who may read the corpus.
--   researcher   an invited fellow researcher: reads the working corpus whatever the mode
--                except 'admins'.
-- Adding enum values changes nothing that exists: every policy that checks role = 'admin' still
-- checks 'admin', and no row changes. Lovable regenerates src/integrations/supabase/types.ts on
-- its own; the site does not need that to work.
--
-- Rollback: enum values cannot be dropped in place. If they are unused (C7 rolled back) they are
-- harmless and can stay.
--
-- Check first (expect {admin,moderator,user}), then run the two lines, then check again
-- (expect {admin,moderator,user,super_admin,researcher}):
--   SELECT enum_range(NULL::public.app_role);
-- ============================================================

ALTER TYPE public.app_role ADD VALUE IF NOT EXISTS 'super_admin';
ALTER TYPE public.app_role ADD VALUE IF NOT EXISTS 'researcher';
