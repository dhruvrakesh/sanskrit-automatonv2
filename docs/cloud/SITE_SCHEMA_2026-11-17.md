# The site's corpus schema, traced to its SQL (I2, DOCS116_2026_11_16)

Read on 17 Nov 2026 from Srangam's database (Lovable Cloud SQL editor, read-only; the owner's CSV exports of 20:28 IST)
and from this repository's docs\cloud (70 SQL files, 7 of them create a corpus table). Every table of the schema
corpus and every function public.corpus_* on the site has its SQL here, and nothing made here is missing there:
26 tables and 48 functions, both ways. Srangam's own supabase/migrations (66 files, the last of 10 Sep) holds none
of them: they were pasted in the Lovable Cloud SQL editor, one block at a time, as the handover's rules ask. This
file is the record of that schema; a change to it is a new docs\cloud file and a new line here.

## Tables (schema corpus)

| Table | Made by | Rows on 17 Nov (planner's estimate) | Size |
|---|---|---|---|
| docs | C4_corpus_mirror_2026-10-08.sql | 63 | 64 kB |
| entities | C4_corpus_mirror_2026-10-08.sql | 14,019 | 4088 kB |
| group_digest | C4b_mirror_digests_2026-10-08.sql | 302 | 112 kB |
| index_claims | C23_index_claims_2026-10-28.sql | 6,062 | 3088 kB |
| index_dynasties | C28_index_dynasties_2026-11-11.sql | 106 | 312 kB |
| index_lines | C21_index_site_2026-10-25.sql | 53 | 88 kB |
| index_meta | C21_index_site_2026-10-25.sql | not analysed yet | 32 kB |
| index_persons | C21_index_site_2026-10-25.sql | 20,221 | 7752 kB |
| index_statements | C21_index_site_2026-10-25.sql | 22,021 | 15 MB |
| index_steps | C21_index_site_2026-10-25.sql | 10,861 | 4824 kB |
| index_texts | C21_index_site_2026-10-25.sql | not analysed yet | 32 kB |
| index_verses | C21_index_site_2026-10-25.sql | 5,702 | 1520 kB |
| media | C8_corpus_media_2026-10-09.sql | 57 | 248 kB |
| media_config | C8_corpus_media_2026-10-09.sql | not analysed yet | 32 kB |
| media_files | C8_corpus_media_2026-10-09.sql | 114 | 168 kB |
| mentions | C4_corpus_mirror_2026-10-08.sql | 47,944 | 15 MB |
| novels | C8_corpus_media_2026-10-09.sql | not analysed yet | 96 kB |
| passage_vectors | C4_corpus_mirror_2026-10-08.sql | 30,434 | 265 MB |
| passages | C4_corpus_mirror_2026-10-08.sql | 165,169 | 324 MB |
| reader_access | C5_corpus_reader_2026-10-08.sql | not analysed yet | 32 kB |
| readers | C5_corpus_reader_2026-10-08.sql | not analysed yet | 16 kB |
| row_index | C4b_mirror_digests_2026-10-08.sql | 201,016 | 63 MB |
| stages | C4_corpus_mirror_2026-10-08.sql | 767 | 680 kB |
| stories | C4_corpus_mirror_2026-10-08.sql | 82 | 440 kB |
| sync_runs | C4_corpus_mirror_2026-10-08.sql | 367 | 256 kB |
| translations | C4_corpus_mirror_2026-10-08.sql | 28,275 | 26 MB |

## Functions (public.corpus_*)

| Function | Arguments | Made, then changed, by |
|---|---|---|
| corpus_access_mode | - | C7_rbac_researchers_2026-10-08.sql |
| corpus_access_mode_set | p_mode text | C7_rbac_researchers_2026-10-08.sql |
| corpus_index_delete | p_table text, p_keys jsonb | C21_index_site_2026-10-25.sql |
| corpus_index_ingest | p_table text, p_rows jsonb | C21_index_site_2026-10-25.sql, C23_index_claims_2026-10-28.sql, C26_index_aliases_2026-11-10.sql, C28_index_dynasties_2026-11-11.sql |
| corpus_index_keys | p_table text | C21_index_site_2026-10-25.sql |
| corpus_index_manifest | - | C21_index_site_2026-10-25.sql, C23_index_claims_2026-10-28.sql, C26_index_aliases_2026-11-10.sql, C28_index_dynasties_2026-11-11.sql |
| corpus_ingest | p_table text, p_rows jsonb, p_run uuid | C4_corpus_mirror_2026-10-08.sql, C4b_mirror_digests_2026-10-08.sql |
| corpus_keys | p_table text, p_group text | C4_corpus_mirror_2026-10-08.sql, C4b_mirror_digests_2026-10-08.sql |
| corpus_manifest | p_tables text[] | C4_corpus_mirror_2026-10-08.sql, C4b_mirror_digests_2026-10-08.sql |
| corpus_media_config_get | p_key text | C8_corpus_media_2026-10-09.sql |
| corpus_media_config_set | p_key text, p_value text | C8_corpus_media_2026-10-09.sql |
| corpus_media_file_get | p_sha text, p_rendition text | C8_corpus_media_2026-10-09.sql |
| corpus_media_file_put | p_row jsonb | C8_corpus_media_2026-10-09.sql |
| corpus_media_retire | p_media text[], p_novels integer[] | C8_corpus_media_2026-10-09.sql |
| corpus_media_state | - | C8_corpus_media_2026-10-09.sql |
| corpus_media_upsert | p_rows jsonb | C8_corpus_media_2026-10-09.sql |
| corpus_novels_upsert | p_rows jsonb | C8_corpus_media_2026-10-09.sql |
| corpus_reader_allowed | - | C5_corpus_reader_2026-10-08.sql, C7_rbac_researchers_2026-10-08.sql |
| corpus_reader_docs | p_doc text | C5_corpus_reader_2026-10-08.sql |
| corpus_reader_index_dynasties | p_work text | C28_index_dynasties_2026-11-11.sql |
| corpus_reader_index_find | p_fold text, p_source text, p_k integer | C21_index_site_2026-10-25.sql, C26_index_aliases_2026-11-10.sql |
| corpus_reader_index_lines | p_source text | C21_index_site_2026-10-25.sql |
| corpus_reader_index_of_name | p_canonical text | C21_index_site_2026-10-25.sql, C23_index_claims_2026-10-28.sql |
| corpus_reader_index_overview | - | C21_index_site_2026-10-25.sql, C23_index_claims_2026-10-28.sql |
| corpus_reader_index_tree | p_source text, p_entry integer, p_via integer, p_down integer | C21_index_site_2026-10-25.sql, C23_index_claims_2026-10-28.sql, C26_index_aliases_2026-11-10.sql |
| corpus_reader_match | query_embedding halfvec, k integer, doc_codes text[] | C5_corpus_reader_2026-10-08.sql |
| corpus_reader_media | p_doc text, p_story integer, k integer, p_offset integer | C8_corpus_media_2026-10-09.sql |
| corpus_reader_media_file | p_sha text, p_rendition text | C8_corpus_media_2026-10-09.sql |
| corpus_reader_name | p_canonical text, k integer, p_offset integer | C6_corpus_library_2026-10-08.sql |
| corpus_reader_name_links | p_canonical text, k integer | C20_name_links_2026-10-23.sql, C20a_name_links_view_2026-10-24.sql |
| corpus_reader_names | q text, p_kind text, k integer, p_offset integer, p_exact boolean | C6_corpus_library_2026-10-08.sql |
| corpus_reader_novel | p_id integer | C8_corpus_media_2026-10-09.sql |
| corpus_reader_novels | p_doc text | C8_corpus_media_2026-10-09.sql |
| corpus_reader_outline | p_doc text, p_per_page integer | C5b_corpus_reader_outline_2026-10-08.sql |
| corpus_reader_page | p_doc text, p_offset integer, p_limit integer | C5_corpus_reader_2026-10-08.sql |
| corpus_reader_page_names | p_doc text, p_offset integer, p_limit integer | C6_corpus_library_2026-10-08.sql |
| corpus_reader_progress | - | C6_corpus_library_2026-10-08.sql |
| corpus_reader_scholar | p_doc text, p_offset integer, p_limit integer | C18_reader_scholar_2026-10-18.sql |
| corpus_reader_scholar_count | p_doc text | C18_reader_scholar_2026-10-18.sql |
| corpus_reader_scholar_docs | - | C22_scholar_site_2026-10-25.sql |
| corpus_reader_scholar_prose | p_doc text, p_after_page integer, p_after_idx integer, p_limit integer | C22_scholar_site_2026-10-25.sql |
| corpus_reader_scholar_search | q text, k integer, p_doc text | C24_scholar_search_2026-10-28.sql |
| corpus_reader_search | q text, k integer, p_doc text | C5_corpus_reader_2026-10-08.sql |
| corpus_reader_similar | p_doc text, p_page integer, p_idx integer, k integer | C5_corpus_reader_2026-10-08.sql |
| corpus_reader_sources | p_doc text | C17_reader_sources_2026-10-14.sql |
| corpus_reader_stories | p_doc text, p_full boolean | C6_corpus_library_2026-10-08.sql |
| corpus_retire | p_table text, p_group text, p_keys jsonb, p_run uuid | C4_corpus_mirror_2026-10-08.sql, C4b_mirror_digests_2026-10-08.sql |
| corpus_run | p_run uuid, p_info jsonb, p_finish boolean | C4_corpus_mirror_2026-10-08.sql |

## To check it again (read-only, one block per paste)

```sql
select c.relname as table_name, c.reltuples::bigint as approx_rows, pg_size_pretty(pg_total_relation_size(c.oid)) as size
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'corpus' and c.relkind = 'r'
order by c.relname;
```

```sql
select p.proname, pg_get_function_identity_arguments(p.oid) as args
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname like 'corpus\_%'
order by 1;
```
