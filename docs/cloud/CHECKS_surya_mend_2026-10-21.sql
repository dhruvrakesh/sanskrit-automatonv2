-- ============================================================
-- CHECKS for the Surya Siddhanta's mend (WITNESS_MEND_2026_10_21, docs/SHELF_AND_SURYA_2026-10-21.md). Read-only:
-- no schema change, nothing written. ONE QUERY PER PASTE in the Lovable Cloud SQL editor; Export CSV and keep it.
--
-- Run M1 to M5 now (the 16:31 IST mirror run of 21 Oct sent the e-text with the misspelt Sanskrit), and again after
-- the first mirror run that follows "python scripts\mend_witness.py --doc ... --yes" (D:\backups\corpus_mirror_log.txt
-- shows it: passages jyotish_surya_siddhanta__w_etext: 515 to send).
-- ============================================================


-- M1 the Surya e-text on the site, passages by kind. Now: 515 (mula, prose, frontmatter). After: the same 515, with 11
--    of page 1 'noise' (GRETIL's English header).
SELECT p.text_type, count(*) AS passages
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL
GROUP BY 1
ORDER BY 1;


-- M2 the visarga written as h with a virama at a word's end (h = chr(2361), the virama = chr(2381); the dandas
--    chr(2404), chr(2405)). Now: about 362. After: 0.
SELECT count(*) AS h_virama_passages
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL
  AND p.text ~ (chr(2361) || chr(2381) || '([[:space:]]|$|' || chr(2404) || '|' || chr(2405) || '|[(])');


-- M3 the Surya's scholarly English rows. Now: 915 in all (en-x-scholar and en-x-scholar-meta). After: the rows of the
--    7 header lines retired; the rest the same English, synced again.
SELECT t.lang, count(*) AS rows, max(t.synced_at) AS last_synced
FROM corpus.translations t
WHERE t.doc_code = 'jyotish_surya_siddhanta__w_etext' AND t.retired_at IS NULL AND t.lang LIKE 'en-x-scholar%'
GROUP BY 1
ORDER BY 1;


-- M4 page 1 as the reader has it. After: idx 2 to 12 in Latin letters ("Header" ... "Text"), noise, no scholarly
--    English; idx 13 begins "1.01a:" with the visarga.
SELECT p.idx, p.text_type, left(p.text, 70) AS text,
       (SELECT count(*) FROM corpus.translations t
         WHERE t.doc_code = p.doc_code AND t.page_no = p.page_no AND t.idx = p.idx
           AND t.retired_at IS NULL AND t.lang = 'en-x-scholar') AS scholar_rows
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.page_no = 1 AND p.retired_at IS NULL
ORDER BY p.idx;


-- M5 the Markandeya's GRETIL witness, page 1. After its mend: idx 2 to 10 in Latin letters, noise.
SELECT p.idx, p.text_type, left(p.text, 70) AS text
FROM corpus.passages p
WHERE p.doc_code = 'markandeya_purana__w_gretil' AND p.page_no = 1 AND p.retired_at IS NULL
ORDER BY p.idx
LIMIT 14;
