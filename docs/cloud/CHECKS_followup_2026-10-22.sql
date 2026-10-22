-- CHECKS_followup_2026-10-22.sql  (DOCS86_2026_10_22, docs/DEBT_2026-10-22.md section 7)
-- Read-only. Paste ONE block at a time into the Lovable Cloud SQL editor (Run). Nothing here writes.
-- Why: CHECKS_debt H3 found the Daivat-Sanhita live in the corpus (13,887 passages, no English, no title). Who may
-- read the corpus is set by corpus.reader_access (C5, C7); whether the public site lists a text by
-- public.srangam_texts.published. These say which applies to it, before its rights (Satavalekar's edition) are decided;
-- and the Surya e-text's new working English after the mirror's runs.

-- J1. Who may read the corpus mirror: signed_in (anyone with an account), readers (the list), or admins.
SELECT mode, updated_at FROM corpus.reader_access;

-- J2. Is the Daivat-Sanhita listed on the public site? (no row: it is not a site text)
SELECT doc_code, published FROM public.srangam_texts WHERE doc_code = 'Daivat-Sanhita';

-- J3. The Surya e-text on the site: live passages, those with the working English, vectors, mentions.
SELECT (SELECT count(*) FROM corpus.passages p WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL) AS passages,
       (SELECT count(*) FROM corpus.passages p WHERE p.doc_code = 'jyotish_surya_siddhanta__w_etext' AND p.retired_at IS NULL
           AND btrim(coalesce(p.translation, '')) <> '') AS working_english,
       (SELECT count(*) FROM corpus.passage_vectors v WHERE v.doc_code = 'jyotish_surya_siddhanta__w_etext' AND v.retired_at IS NULL) AS vectors,
       (SELECT count(*) FROM corpus.mentions m WHERE m.doc_code = 'jyotish_surya_siddhanta__w_etext' AND m.retired_at IS NULL) AS mentions;
