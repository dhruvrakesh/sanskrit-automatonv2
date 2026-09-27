-- DATASETTE_QUERIES_2026_09_27
-- The standard read-only checks for query_snapshot.db (Datasette, :8001).
-- Paste ONE query at a time into the Datasette SQL box.
--
-- Datasette reads a SNAPSHOT, not the live database. Refresh it first:
--   & 'D:\Sanksrit Automatons\_ops_2026-09-10\block_BB_bridge.ps1' -RefreshSnapshot
-- All of these are SELECTs; Datasette refuses anything else anyway.
-- Columns are those of scripts/db_utils.py (passages, translations_l10n,
-- translation_history, docs).

-- Q1  English: how many translations each prompt version produced
SELECT COALESCE(mt_prompt_version, '(none)') AS prompt, COUNT(*) AS n
FROM passages WHERE TRIM(COALESCE(translation, '')) <> ''
GROUP BY 1 ORDER BY n DESC;

-- Q2  Hindi: the same
SELECT COALESCE(mt_prompt_version, '(none)') AS prompt, COUNT(*) AS n
FROM translations_l10n WHERE lang = 'hi' AND TRIM(COALESCE(translation, '')) <> ''
GROUP BY 1 ORDER BY n DESC;

-- Q3  Coverage per document (live verses only), largest first
SELECT d.code,
       COUNT(*) AS verses,
       SUM(TRIM(COALESCE(p.translation, '')) <> '') AS en,
       (SELECT COUNT(*) FROM translations_l10n l JOIN passages q ON q.id = l.passage_id
         WHERE q.doc_id = d.id AND l.lang = 'hi' AND TRIM(COALESCE(l.translation, '')) <> '') AS hi,
       ROUND(100.0 * SUM(TRIM(COALESCE(p.translation, '')) <> '') / COUNT(*), 1) AS en_pct
FROM docs d JOIN passages p ON p.doc_id = d.id
WHERE COALESCE(p.text_type, 'mula') NOT IN ('noise', 'frontmatter')
  AND d.code NOT LIKE '%-RETIRED'
GROUP BY d.id ORDER BY verses DESC;

-- Q4  What was written in the last 24 hours (English and Hindi)
SELECT 'en' AS lang, COUNT(*) AS n, MIN(translated_at) AS first, MAX(translated_at) AS last
FROM passages WHERE translated_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 day')
UNION ALL
SELECT 'hi', COUNT(*), MIN(translated_at), MAX(translated_at)
FROM translations_l10n WHERE lang = 'hi' AND translated_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 day');

-- Q5  Spot-check: translations that carry a lacuna mark, weakest scans first
SELECT d.code, p.page_no, p.idx, ROUND(p.quality_score, 2) AS q,
       substr(p.text, 1, 60) AS sa, substr(p.translation, 1, 140) AS en
FROM passages p JOIN docs d ON d.id = p.doc_id
WHERE p.translation LIKE '%[ILLEGIBLE]%'
ORDER BY p.quality_score ASC, d.code, p.page_no LIMIT 50;

-- Q6  Hindi that still begins with the Sanskrit it translates (expect ~0 after FILTERS3)
SELECT d.code, p.page_no, p.idx, substr(l.translation, 1, 80) AS hi
FROM translations_l10n l JOIN passages p ON p.id = l.passage_id JOIN docs d ON d.id = p.doc_id
WHERE l.lang = 'hi' AND length(p.text) > 20
  AND substr(l.translation, 1, 20) = substr(p.text, 1, 20)
LIMIT 50;

-- Q7  Remediation history: every superseded or removed translation, by reason
SELECT reason, COALESCE(lang, 'en') AS lang, COUNT(*) AS n, MAX(translated_at) AS latest_original
FROM translation_history GROUP BY reason, lang ORDER BY n DESC;

-- Q8  One document, verse by verse (change the code; English and Hindi side by side)
SELECT p.page_no, p.idx, substr(p.text, 1, 60) AS sa,
       substr(p.translation, 1, 100) AS en, substr(l.translation, 1, 100) AS hi,
       p.mt_prompt_version AS en_prompt, l.mt_prompt_version AS hi_prompt
FROM passages p JOIN docs d ON d.id = p.doc_id
LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
WHERE d.code = 'AphorismsOfSandilya'
ORDER BY p.page_no, p.idx LIMIT 200;

-- Q9  Still empty per document and language, among live verses (what a retry plan sees,
--     before its "went past" and parking rules; plan_empty_retries.py is the authority)
SELECT d.code,
       SUM(TRIM(COALESCE(p.translation, '')) = '') AS en_empty,
       SUM(NOT EXISTS (SELECT 1 FROM translations_l10n l WHERE l.passage_id = p.id AND l.lang = 'hi'
                       AND TRIM(COALESCE(l.translation, '')) <> '')) AS hi_empty
FROM docs d JOIN passages p ON p.doc_id = d.id
WHERE COALESCE(p.text_type, 'mula') NOT IN ('noise', 'frontmatter') AND d.code NOT LIKE '%-RETIRED'
GROUP BY d.id HAVING en_empty > 0 OR hi_empty > 0 ORDER BY en_empty DESC;
