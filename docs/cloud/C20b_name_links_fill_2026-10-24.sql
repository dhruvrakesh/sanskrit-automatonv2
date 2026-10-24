-- ============================================================
-- C20b - named together, on the site: the fill (NAME_LINKS_C20_SPLIT_2026_10_24)
-- ONE STATEMENT in the Lovable Cloud SQL editor, after C20a. This is the slow part: P4 of C20_preflight_2026-10-24.sql
-- said how long it takes. Expect one row: {"ms": ..., "pairs": about 45000, "was_filled": false}.
-- Pasting it again refreshes the view (CONCURRENTLY: the name pages keep reading) and says "was_filled": true.
-- "Server error" here, after a P4 under 20 seconds: send the screenshot; nothing is half done (the view stays empty
-- and the name pages stay as they are).
-- ============================================================
SELECT corpus._refresh_name_links() AS filled;
