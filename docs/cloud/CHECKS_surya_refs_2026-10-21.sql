-- ============================================================
-- CHECKS for the Surya Siddhanta's references (ETEXT_REFS_2026_10_21, docs/CLAIMS_AND_REFS_2026-10-21.md). Read-only:
-- no schema change, nothing written. ONE QUERY PER PASTE in the Lovable Cloud SQL editor; Export CSV and keep it.
--
-- Run R1 to R4 now, and again after the first mirror run that follows
-- "python scripts\mend_witness.py --doc jyotish_surya_siddhanta__w_etext --yes" (D:\backups\corpus_mirror_log.txt).
-- ============================================================


-- R1 the references and chapters. Now: 515 passages, 497 without a
--    reference, 17 with a value of three or more digits as their reference, 0 with a label's, 3 chapters (1, 2, 260).
--    After: 12 without (the 11 header lines and the title), 0 values, 503 labels, 14 chapters.
SELECT count(*) AS passages,
       count(*) FILTER (WHERE p.verse_ref IS NULL OR p.verse_ref = '') AS no_ref,
       count(*) FILTER (WHERE p.verse_ref ~ '^[0-9]{3,}') AS value_refs,
       count(*) FILTER (WHERE p.verse_ref ~ '^[0-9]{1,2}\.[0-9]{1,3}$') AS label_refs,
       count(DISTINCT p.chapter) AS chapters
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL;


-- R2 the verses of each chapter. After: 1: 71, 2: 69, 3: 52, 4: 26, 5: 17, 6: 24, 7: 24, 8: 21, 9: 18, 10: 16, 11: 23,
--    12: 90, 13: 26, 14: 27 (and the 11 header lines with chapter 1).
SELECT p.chapter, count(*) FILTER (WHERE p.text_type <> 'noise') AS verses, count(*) AS passages
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL
GROUP BY 1
ORDER BY length(p.chapter), p.chapter;


-- R3 the values put back: passages whose text ends with a bracket. Now 30; after 47 (17 more: the 18th, 2.33, ended
--    with a variant's bracket already).
SELECT count(*) AS ending_with_a_bracket
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL AND p.text ~ '\)\s*$';


-- R4 the references the e-text gives twice. After: 3.13, 10.13, 13.21, each with 2 passages.
SELECT p.verse_ref, count(*) AS passages, string_agg(p.page_no || '.' || p.idx, ', ' ORDER BY p.page_no, p.idx) AS at
FROM corpus.passages p
WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL AND p.text_type <> 'noise'
  AND p.verse_ref IS NOT NULL AND p.verse_ref <> ''
GROUP BY 1
HAVING count(*) > 1
ORDER BY 1;
