-- Test-only stand-ins for what Supabase provides (CORPUS_READER_C5_2026_10_08). Never run this on
-- the live database: there auth.uid(), app_role, has_role() and srangam_texts already exist.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN CREATE ROLE anon NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN CREATE ROLE service_role NOLOGIN BYPASSRLS; END IF;
END $$;
CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'app_role') THEN
    CREATE TYPE public.app_role AS ENUM ('admin', 'moderator', 'user');
  END IF;
END $$;
CREATE TABLE IF NOT EXISTS public.user_roles (user_id uuid, role public.app_role, PRIMARY KEY (user_id, role));
CREATE OR REPLACE FUNCTION public.has_role(_user_id uuid, _role public.app_role) RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS
  $$ SELECT EXISTS (SELECT 1 FROM public.user_roles r WHERE r.user_id = _user_id AND r.role = _role) $$;
CREATE TABLE IF NOT EXISTS public.srangam_texts (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), doc_code text UNIQUE);
ALTER TABLE public.srangam_texts ADD COLUMN IF NOT EXISTS published boolean NOT NULL DEFAULT false;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
