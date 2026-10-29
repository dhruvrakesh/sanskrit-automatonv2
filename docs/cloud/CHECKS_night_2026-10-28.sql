-- CHECKS_night_2026-10-28.sql  (DOCS101_2026_10_28: after the mirror's tick of 18:33 IST, 28 Oct)
-- Read-only. ONE QUERY PER PASTE in the Lovable Cloud SQL editor; export each result.
-- The tick of 18:33 sent the Karanagama (restored: 1,909 passages, 1,491 translations, 229 not sent), the Gandharva
-- Veda's own text (794 passages), and the listed editions' noise (the Mallapurana's 44, the Ganita's 9, the
-- Akasabhairava's 38). corpus_sync's verify: 374 groups equal, 0 different.

-- N1 (R3 again): a listed edition's noise withheld as its frontmatter is (RIGHTS_NOISE_2026_10_28).
-- Expected: withheld = noise_live and with_words = 0 for the Ganita (9), the Mallapurana (44), the Akasabhairava (38)
-- and the Karanagama (5); the Hayasirsa (held) keeps its last version (61, with words) until it is released.
SELECT p.doc_code,
       count(*) FILTER (WHERE p.retired_at IS NULL) AS noise_live,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND p.text LIKE '[The edition''s own matter, not shown on the site:%') AS withheld,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND (p.translation IS NOT NULL OR p.iast IS NOT NULL)) AS with_words
FROM corpus.passages p
WHERE p.text_type = 'noise'
  AND p.doc_code IN ('Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V', 'Mallapurana', 'AkashBhairavaKalpam',
                     'HAYASHIRSHA_PANCARATRA', 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi')
GROUP BY p.doc_code
ORDER BY p.doc_code;

-- N2: the Karanagama on the site, by the passage's type. Expected: frontmatter 993 live, 993 withheld, 0 with words;
-- noise 5, 5, 0; mula 874, prose 34 and colophon 3 live and not withheld (their IAST counts as words).
SELECT p.text_type,
       count(*) FILTER (WHERE p.retired_at IS NULL) AS live,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND p.text LIKE '[The edition''s own matter, not shown on the site:%') AS withheld,
       count(*) FILTER (WHERE p.retired_at IS NULL
                          AND (p.translation IS NOT NULL OR p.iast IS NOT NULL)) AS with_words
FROM corpus.passages p
WHERE p.doc_code = 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi'
GROUP BY p.text_type
ORDER BY p.text_type;

-- N3: no translation of the Karanagama's own matter is live (any language). Expected: no rows, or live = 0.
SELECT t.lang, p.text_type, count(*) FILTER (WHERE t.retired_at IS NULL) AS live
FROM corpus.translations t
JOIN corpus.passages p ON p.doc_code = t.doc_code AND p.page_no = t.page_no AND p.idx = t.idx
WHERE t.doc_code = 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi'
  AND p.text_type IN ('frontmatter', 'noise')
GROUP BY t.lang, p.text_type
ORDER BY t.lang, p.text_type;

-- N4: the Gandharva Veda's own text, on the site since 18:33 (Tesseract's reading, no English yet). Expected: 794
-- live, 0 with English. What to do with it is yours (docs\ASKS_2026-10-22.md, section 14).
SELECT p.doc_code,
       count(*) FILTER (WHERE p.retired_at IS NULL) AS live,
       count(*) FILTER (WHERE p.retired_at IS NULL AND coalesce(p.translation, '') <> '') AS with_english
FROM corpus.passages p
WHERE p.doc_code = 'gandharva_veda_natya_shastra'
GROUP BY p.doc_code;
