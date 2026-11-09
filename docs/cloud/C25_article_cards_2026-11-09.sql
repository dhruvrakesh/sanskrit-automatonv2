-- C25_article_cards_2026-11-09.sql  (LOAD_CARDS_2026_11_09; docs\LOAD_AND_STORIES_2026-11-09.md)
-- The list pages of Srangam (the home page, /articles) read every published article with select('*'): measured on
-- 9 Nov 2026, 2,329 KB of the home page's 3,091 KB, of which `content` was 4.64 MB of 4.73 MB uncompressed, read only to
-- learn which languages have a body. This view gives the cards' columns and those languages, computed here with the
-- rule src/hooks/useArticles.ts used (a key whose value is a non-empty string; none: 'en').
-- security_invoker: the view reads srangam_articles as the visitor does, under the table's own row-level security.
-- Lovable Cloud SQL editor. ONE BLOCK PER PASTE: B1, B2, then V (the view), then A1, A2. Nothing is changed but V.

-- B1 (before): no relation of this name yet. Expected: one row, NULL.
SELECT to_regclass('public.srangam_article_cards') AS existing;

-- B2 (before): the published articles and their body languages, from the table itself. Expected (9 Nov): 50 rows.
SELECT count(*) AS published,
       sum((SELECT count(*) FROM jsonb_each(a.content) e
             WHERE jsonb_typeof(e.value) = 'string' AND btrim(e.value #>> '{}') <> '')) AS body_languages
FROM public.srangam_articles a
WHERE a.status = 'published';

-- V: the view (one block).
BEGIN;
CREATE OR REPLACE VIEW public.srangam_article_cards
WITH (security_invoker = true) AS
SELECT a.id, a.slug, a.slug_alias, a.title, a.dek, a.theme, a.tags, a.read_time_minutes, a.author,
       a.published_date, a.created_at, a.status,
       COALESCE(
         (SELECT array_agg(e.key ORDER BY e.key)
            FROM jsonb_each(CASE WHEN jsonb_typeof(a.content) = 'object' THEN a.content ELSE '{}'::jsonb END) AS e(key, value)
           WHERE jsonb_typeof(e.value) = 'string' AND btrim(e.value #>> '{}') <> ''),
         ARRAY['en']::text[]) AS body_languages
FROM public.srangam_articles a;
COMMENT ON VIEW public.srangam_article_cards IS
  'LOAD_CARDS_2026_11_09: the article cards without their bodies; body_languages as src/hooks/useArticles.ts computes them';
GRANT SELECT ON public.srangam_article_cards TO anon, authenticated;
COMMIT;

-- A1 (after): the same count as B2's published, and the languages summed equal B2's (where every article has one).
SELECT count(*) AS published, sum(cardinality(body_languages)) AS body_languages
FROM public.srangam_article_cards
WHERE status = 'published';

-- A2 (after): the view is invoker's rights and readable by the site's visitors. Expected: security_invoker=true; anon
-- and authenticated with SELECT.
SELECT c.relname, c.reloptions,
       has_table_privilege('anon', 'public.srangam_article_cards', 'SELECT') AS anon_select,
       has_table_privilege('authenticated', 'public.srangam_article_cards', 'SELECT') AS authenticated_select
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'srangam_article_cards';
