-- CHECKS_held_2026-10-21.sql  (DOCS82_2026_10_21)
-- Read-only. Paste ONE block at a time into the Lovable Cloud SQL editor (Run). Nothing here writes.
-- Why: every live text has on the site the passages it has here, but the Hayasirsa, held in repair (1,531 there, sent
-- on 8 Oct; 1,706 here): the 175. The site also has 246 more mentions and 158 more vectors than the live texts here
-- (39,808 and 25,346, the Hayasirsa's new passages having 0 mentions and 1 vector here). H1 tells whether they are
-- the Hayasirsa's held version; H2 and H3 give every text's count, to set beside the RUNBOOK's command (DOCS82).

-- H1. The Hayasirsa's held version there.
SELECT (SELECT count(*) FROM corpus.mentions
         WHERE doc_code = 'HAYASHIRSHA_PANCARATRA' AND retired_at IS NULL) AS mentions_live,
       (SELECT count(*) FROM corpus.passage_vectors
         WHERE doc_code = 'HAYASHIRSHA_PANCARATRA' AND retired_at IS NULL) AS vectors_live,
       (SELECT count(*) FROM corpus.translations
         WHERE doc_code = 'HAYASHIRSHA_PANCARATRA' AND retired_at IS NULL) AS translation_rows_live;

-- H2. Every text's live mentions there.
SELECT doc_code, count(*) AS mentions
FROM corpus.mentions WHERE retired_at IS NULL
GROUP BY doc_code ORDER BY doc_code;

-- H3. Every text's live vectors there.
SELECT doc_code, count(*) AS vectors
FROM corpus.passage_vectors WHERE retired_at IS NULL
GROUP BY doc_code ORDER BY doc_code;
