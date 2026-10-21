-- CHECKS_brain_counts_2026-10-21.sql  (DOCS81_2026_10_21)
-- Read-only. Paste ONE block at a time into the Lovable Cloud SQL editor (Run). Nothing here writes.
-- Why: docs/BRAIN_PATH_2026-10-21.md section 1 said every passage is mirrored; the site holds 99,966 live passages,
-- 100,141 are live here (the withdrawn texts hold 73,878). These count the live rows (retired_at IS NULL, as the
-- mirror's own manifest counts them), text by text, so that the 175 between can be named.

-- B1. The live rows of each layer, and the vectors with the retired rows too.
SELECT 'docs' AS layer, count(*) AS n FROM corpus.docs WHERE retired_at IS NULL
UNION ALL SELECT 'passages', count(*) FROM corpus.passages WHERE retired_at IS NULL
UNION ALL SELECT 'translations, every language', count(*) FROM corpus.translations WHERE retired_at IS NULL
UNION ALL SELECT 'scholarly English (en-x-scholar)', count(*) FROM corpus.translations
          WHERE retired_at IS NULL AND lang = 'en-x-scholar'
UNION ALL SELECT 'entities', count(*) FROM corpus.entities WHERE retired_at IS NULL
UNION ALL SELECT 'mentions', count(*) FROM corpus.mentions WHERE retired_at IS NULL
UNION ALL SELECT 'vectors, live', count(*) FROM corpus.passage_vectors WHERE retired_at IS NULL
UNION ALL SELECT 'vectors, retired too', count(*) FROM corpus.passage_vectors;

-- B2. The Hayasirsa, held in repair: the site keeps its last version (1,706 passages here).
SELECT count(*) FILTER (WHERE retired_at IS NULL) AS live,
       count(*) FILTER (WHERE retired_at IS NOT NULL) AS retired,
       max(synced_at) AS last_sent
FROM corpus.passages WHERE doc_code = 'HAYASHIRSHA_PANCARATRA';

-- B3. The withdrawn texts: none of their passages should be live there.
SELECT doc_code,
       count(*) FILTER (WHERE retired_at IS NULL) AS live,
       count(*) FILTER (WHERE retired_at IS NOT NULL) AS retired
FROM corpus.passages
WHERE doc_code IN ('Thakur_Prasad_Dwivedi_Lala_Baijnath_Yoga_vasistha',
                   'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi',
                   'Bodhicaryavatara')
GROUP BY doc_code ORDER BY doc_code;

-- B4. Every text's live passages there, to set beside the same count here (the RUNBOOK's command, DOCS81).
SELECT doc_code, count(*) AS live
FROM corpus.passages WHERE retired_at IS NULL
GROUP BY doc_code ORDER BY doc_code;
