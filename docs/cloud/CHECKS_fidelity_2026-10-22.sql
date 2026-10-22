-- CHECKS_fidelity_2026-10-22.sql  (DOCS84_2026_10_22, FIDELITY_2026_10_22)
-- Read-only. Paste ONE block at a time into the Lovable Cloud SQL editor (Run). Nothing here writes.
-- Why: docs/FIDELITY_2026-10-22.md measured four texts letter by letter on 22 Oct. Where an e-text is the better
-- Sanskrit to translate (the Surya's, GRETIL's Markandeya), these show what the site holds of each before anything
-- is regenerated, so that the same count can be read again after it; and that the local witnesses are not there.

-- F1. The texts measured: live passages, vectors and mentions on the site.
SELECT d.doc_code,
       (SELECT count(*) FROM corpus.passages p
         WHERE p.doc_code = d.doc_code AND p.retired_at IS NULL) AS passages,
       (SELECT count(*) FROM corpus.passage_vectors v
         WHERE v.doc_code = d.doc_code AND v.retired_at IS NULL) AS vectors,
       (SELECT count(*) FROM corpus.mentions m
         WHERE m.doc_code = d.doc_code AND m.retired_at IS NULL) AS mentions
FROM (VALUES ('markandeya_purana'), ('markandeya_purana__w_gretil'),
             ('jyotish_surya_siddhanta'), ('jyotish_surya_siddhanta__w_etext'),
             ('2015_405693_Shatpath-Brahmanam')) AS d(doc_code)
ORDER BY d.doc_code;

-- F2. Their live translation rows, by language (the working English, the scholarly English, the Hindi).
SELECT doc_code, lang, count(*) AS rows_live
FROM corpus.translations
WHERE retired_at IS NULL
  AND doc_code IN ('markandeya_purana', 'markandeya_purana__w_gretil',
                   'jyotish_surya_siddhanta', 'jyotish_surya_siddhanta__w_etext',
                   '2015_405693_Shatpath-Brahmanam')
GROUP BY doc_code, lang
ORDER BY doc_code, lang;

-- F3. The local witnesses (GRETIL's Satapatha, whole and kanda 14): nothing of them should be live on the site.
SELECT doc_code,
       count(*) FILTER (WHERE retired_at IS NULL) AS live,
       count(*) FILTER (WHERE retired_at IS NOT NULL) AS retired
FROM corpus.passages
WHERE doc_code IN ('satapatha_madhyandina__w_gretil', '2015_405693_Shatpath-Brahmanam__w_gretil')
GROUP BY doc_code
ORDER BY doc_code;
