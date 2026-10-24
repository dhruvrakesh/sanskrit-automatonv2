-- ============================================================
-- C20c - named together, on the site: the nightly refresh (NAME_LINKS_C20_SPLIT_2026_10_24)
-- ONE STATEMENT in the Lovable Cloud SQL editor, after C20b. Every night at 04:40 UTC, after the nightly jobs
-- (03:00-04:15): the names the mirror brought in the day are counted in. pg_cron keeps one job of a name, so pasting
-- it again changes nothing. Expect one row: a jobid.
-- Undo: SELECT cron.unschedule('srangam-corpus-name-links');
-- ============================================================
SELECT cron.schedule('srangam-corpus-name-links', '40 4 * * *', 'SELECT corpus._refresh_name_links();') AS jobid;
