-- CHECKS_debt_2026-10-22.sql  (DOCS85_2026_10_22, docs/DEBT_2026-10-22.md)
-- Read-only. Paste ONE block at a time into the Lovable Cloud SQL editor (Run). Nothing here writes.
-- Why: the debt register of 22 Oct says what the site holds of the Hayasirsa (held in repair), of the e-text
-- witnesses (two adopted, the others local only) and of the Daivat-Sanhita (its source in question), and that the
-- mirror's runs finish. These read it on the site, so that the register is checked, not believed.

-- H1. The Hayasirsa on the site: its last version, kept while the text is in repair.
SELECT (SELECT count(*) FROM corpus.passages p
         WHERE p.doc_code = 'HAYASHIRSHA_PANCARATRA' AND p.retired_at IS NULL) AS passages,
       (SELECT count(*) FROM corpus.passages p
         WHERE p.doc_code = 'HAYASHIRSHA_PANCARATRA' AND p.retired_at IS NULL
           AND btrim(coalesce(p.translation, '')) <> '') AS working_english,
       (SELECT count(*) FROM corpus.translations t
         WHERE t.doc_code = 'HAYASHIRSHA_PANCARATRA' AND t.retired_at IS NULL AND t.lang = 'hi') AS hindi,
       (SELECT count(*) FROM corpus.translations t
         WHERE t.doc_code = 'HAYASHIRSHA_PANCARATRA' AND t.retired_at IS NULL
           AND t.lang LIKE 'en-x-scholar%') AS scholarly_rows,
       (SELECT count(*) FROM corpus.passage_vectors v
         WHERE v.doc_code = 'HAYASHIRSHA_PANCARATRA' AND v.retired_at IS NULL) AS vectors,
       (SELECT count(*) FROM corpus.mentions m
         WHERE m.doc_code = 'HAYASHIRSHA_PANCARATRA' AND m.retired_at IS NULL) AS mentions;

-- H2. The e-text witnesses on the site: the Markandeya's and the Surya's are adopted (live); GRETIL's Satapatha and
-- Nirukta are local witnesses and should have no rows here.
SELECT doc_code,
       count(*) FILTER (WHERE retired_at IS NULL) AS live,
       count(*) FILTER (WHERE retired_at IS NOT NULL) AS retired
FROM corpus.passages
WHERE doc_code LIKE '%\_\_w\_%'
GROUP BY doc_code
ORDER BY doc_code;

-- H3. The Daivat-Sanhita on the site: its passages and translations, before its source is decided.
SELECT (SELECT count(*) FROM corpus.passages p
         WHERE p.doc_code = 'Daivat-Sanhita' AND p.retired_at IS NULL) AS passages,
       (SELECT count(*) FROM corpus.passages p
         WHERE p.doc_code = 'Daivat-Sanhita' AND p.retired_at IS NULL
           AND btrim(coalesce(p.translation, '')) <> '') AS working_english,
       (SELECT count(*) FROM corpus.translations t
         WHERE t.doc_code = 'Daivat-Sanhita' AND t.retired_at IS NULL) AS translation_rows,
       (SELECT d.title FROM corpus.docs d WHERE d.doc_code = 'Daivat-Sanhita') AS title;

-- H4. The mirror's last ten runs: each should have finished.
SELECT run_id, started_at, finished_at, finished_at - started_at AS took
FROM corpus.sync_runs
ORDER BY started_at DESC
LIMIT 10;
