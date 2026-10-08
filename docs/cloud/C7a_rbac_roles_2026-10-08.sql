-- ============================================================
-- C7a - two new roles (RBAC_RESEARCHERS_2026_10_08). STEP 2 of 4. Paste THIS FILE ALONE.
--
-- The order (docs/cloud/C7_checks_2026-10-08.sql has every check, one query per paste):
--   1. Preflight P1-P7 (read-only), one at a time, export each result.
--   2. C7a: this file, and nothing else in the editor. Then, as a SEPARATE run, check V0.
--   3. C7: the whole of C7_rbac_researchers_2026-10-08.sql, in one paste.
--   4. Verify V1-V7, one at a time.
--
-- Why alone: the Lovable Cloud SQL editor runs one paste as one transaction, and PostgreSQL will
-- not let a new enum value be read or used in the transaction that added it (error 55P04,
-- "unsafe use of new value ... New enum values must be committed before they can be used").
-- Anything that reads app_role in the same paste - even SELECT enum_range(...) - makes the whole
-- paste fail and roll back, values included. That happened once, on 2026-10-08 at 21:14, and
-- changed nothing (the enum stayed {admin,moderator,user}; C7's own guard then refused to run).
--
--   super_admin  grants and removes roles, invites researchers, sets who may read the corpus.
--   researcher   an invited fellow researcher: reads the working corpus in the modes
--                'signed_in' and 'readers'.
-- Adding enum values changes nothing that exists: every policy that checks role = 'admin' still
-- checks 'admin', and no row changes. Re-running this file is harmless (IF NOT EXISTS: a NOTICE).
-- Lovable regenerates src/integrations/supabase/types.ts on its own; the site does not need that.
--
-- Rollback: enum values cannot be dropped in place. Unused (C7 not applied, or rolled back), they
-- are inert and can stay.
-- ============================================================

ALTER TYPE public.app_role ADD VALUE IF NOT EXISTS 'super_admin';
ALTER TYPE public.app_role ADD VALUE IF NOT EXISTS 'researcher';
