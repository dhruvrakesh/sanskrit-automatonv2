-- CHECKS_rights_2026-10-28.sql  (RIGHTS_FRONTMATTER_2026_10_28, DOCS99_2026_10_28, docs/REPAIR_AND_SOURCES_2026-10-28.md)
-- Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL editor; export each result.
-- After the first mirror tick that follows patch_rights_frontmatter_2026_10_28.py.

-- R1: the editions' own matter as the site has it. Expected after the tick: for the Ganita Yukti Bhasa,
-- the Mallapurana, the Akasabhairava and the Astadhyayi, withheld = frontmatter_live (48, 43, 194, 1) and
-- with_words = 0. The Hayasirsa (held) keeps its last version until it is released; the Karanagama is
-- withdrawn (no live rows).
SELECT p.doc_code,
       count(*) FILTER (WHERE p.retired_at IS NULL) AS frontmatter_live,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND p.text LIKE '[The edition''s own matter, not shown on the site:%') AS withheld,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND (p.translation IS NOT NULL OR p.iast IS NOT NULL)) AS with_words
FROM corpus.passages p
WHERE p.text_type = 'frontmatter'
  AND p.doc_code IN ('Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V', 'Mallapurana', 'AkashBhairavaKalpam', 'Astadhyayi',
                     'HAYASHIRSHA_PANCARATRA', 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi')
GROUP BY p.doc_code
ORDER BY p.doc_code;

-- R2: no translation row of that matter stays live (any language). Expected: no rows, or live = 0.
SELECT t.doc_code, t.lang, count(*) FILTER (WHERE t.retired_at IS NULL) AS live
FROM corpus.translations t
JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx
WHERE p.text_type = 'frontmatter'
  AND p.doc_code IN ('Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V', 'Mallapurana', 'AkashBhairavaKalpam', 'Astadhyayi')
GROUP BY t.doc_code, t.lang
ORDER BY t.doc_code, t.lang;
