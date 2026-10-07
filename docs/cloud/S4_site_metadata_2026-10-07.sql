-- SRANGAM_SITE_S4_2026_10_07 - small one-offs after Markandeya went live (paste ONE block at a time)
-- M1, M4 and M6 only read. M2, M3 and M5 each change one row and say so with RETURNING.

-- M1. What the site holds (read-only). The status panel generator carries these as SITE_CORPUS
--     (patch_site_line_2026_10_07.py sets 2 / 2 / 1655). Expect texts 2, published 2, passages 1655.
SELECT count(*) AS texts, count(*) FILTER (WHERE published) AS published,
       (SELECT count(*) FROM public.srangam_text_passages) AS passages
FROM public.srangam_texts;

-- M2. The engine label /texts shows under each title. markandeya_purana was published without one;
--     all 1,258 of its translated passages record gemini:gemini-2.5-flash (context.db, 2026-10-07).
UPDATE public.srangam_texts SET translation_engine = 'gemini:gemini-2.5-flash'
WHERE doc_code = 'markandeya_purana' AND translation_engine IS NULL
RETURNING doc_code, title, translation_engine, published;

-- M3. Optional: the title in IAST, as the Sandilya Bhakti Sutra already is ("Markandeya Purana"
--     came from book.yaml). U&'...' keeps this file ASCII: it reads Ma-macron-rka-n-dot-d-dot-eya
--     Pura-macron-n-dot-a. A later --emit-sql keeps it (the publisher replaces a title only with --title).
UPDATE public.srangam_texts SET title = U&'M\0101rka\1E47\1E0Deya Pur\0101\1E47a'
WHERE doc_code = 'markandeya_purana'
RETURNING doc_code, title;

-- M4. The article whose title is a file name, and anything else like it (read-only).
SELECT id, slug, status, title->>'en' AS title_en FROM public.srangam_articles
WHERE title->>'en' ILIKE 'Reassessing the Antiquity of the Rigveda%' OR title::text ~* '\.(docx|md|pdf)'
ORDER BY slug;

-- M5. Optional, after M4 shows it is the only one: drop ".docx (1)" from the English title. The slug
--     (and so every link to the article) stays as it is. Its OG image and SEO text were generated
--     from the old title: regenerate them from the Srangam admin afterwards.
UPDATE public.srangam_articles
SET title = jsonb_set(title, '{en}', to_jsonb('Reassessing the Antiquity of the Rigveda'::text))
WHERE id = '02b560dc-aaad-4e73-bdc5-0d4ea20bbcf0' AND title->>'en' = 'Reassessing the Antiquity of the Rigveda.docx (1)'
RETURNING id, slug, title;

-- M6. S3 L5 again (read-only). The 16:14 export ended at the 10:40 UTC watchdog run, a few minutes
--     BEFORE the revoke; this shows the runs after it. Expect "succeeded" every 5 minutes.
SELECT j.jobid, j.jobname, d.status, d.return_message, d.start_time
FROM cron.job_run_details d JOIN cron.job j ON j.jobid = d.jobid
WHERE d.start_time > now() - interval '30 minutes' OR (j.jobid <> 1 AND d.start_time > now() - interval '1 day')
ORDER BY d.start_time DESC LIMIT 20;
