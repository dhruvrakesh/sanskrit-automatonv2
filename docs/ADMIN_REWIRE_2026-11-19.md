# The admin pages and the landing pages, rewired (19 Nov 2026)

ADMIN_REWIRE_2026_11_19. Asked on 19 Nov: "alot of the admin dashboard and landing pages need to be reimagined and
rewired to reflect present state of local and online deployment and linkages." This page says what is there (read on
19 Nov in Srangam at cc32c10, and in the automaton at 4090724), what is missing, and the path, step by step. Each step
is its own kit: additive first, md5-guarded, with its tests and its Phase in docs/RELIABILITY_AUDIT.md; no page moves
or goes without the owner's word.

## 1. What is there

| Page | Route | Reads | Says now | Gap |
|---|---|---|---|---|
| Dashboard | /admin | srangam_articles (the last 10), srangam_tags, srangam_cross_references, srangam_cultural_terms (counts), the content status, the themes | the articles only | nothing of the working corpus, the desk, the genealogies, who may read, the AI calls |
| Articles, Import Articles, GitHub Sync | /admin/articles, /admin/import, /admin/github-sync | srangam_articles; markdown-to-article-import, scan-github-markdown, batch-import-from-github | the article pipeline | none for this ask |
| Tag Management | /admin/tags | the tags; suggest-tag-categories | 19 Nov screen: 51% uncategorized | the suggestions (I1, on the own keys since 17 Nov) never called |
| Cross-References, Cultural Terms | /admin/cross-refs, /admin/cultural-terms | the articles' references; enrich-cultural-term | the articles' terms | none for this ask |
| Purana References | /admin/purana-refs | srangam_admin_jobs, srangam_articles | 19 Nov screen: 50 articles, 9 processed, 47 references, 29 of high confidence | it reads the articles; it does not say so, nor link to Dikshitar's Purana Index on the Genealogies pages |
| Analytics, Context Management | /admin/analytics, /admin/context | srangam_articles; srangam_context_snapshots | the articles | none for this ask |
| Data Health | /admin/data-health | bibliography, evidence, markdown sources; backfill-bibliography, generate-article-og | the articles' tables | no check of the corpus mirror or of the genealogies sent |
| Geography & Media | /admin/geography-media | pins, OG images | 19 Nov screen: 46 of 50 with pins, 200 pins, 50 of 50 OG images | none for this ask |
| Corpus Correlations | /admin/corpus-correlations | correlate-corpus | the correlations | none for this ask |
| Researchers | /admin/researchers (super admin) | rbac_members_list, research_invites_list, corpus_access_mode | the invitations, the roles, the readers' setting | none |
| Library, Corner, Learn | /corpus, /corpus/corner, /corpus/learn | the mirror | the working corpus | the Library's landing does not say the counts or the new pages (the vamsas) |
| Home, "Start here" | / | CorpusStartSection (HOME_HEAL_2026_11_14) | seven doors: /texts and /editions (open to all), five working-corpus doors | the five need an invitation and do not say so; the dynasty door names neither the 17 texts nor the vamsa page |

On 19 Nov the working corpus could be read by 1 admin, 1 super admin and 3 researchers (corpus.readers: 0 listed).

## 2. What the site did not show, though its database holds it

The desk's worker (corner.worker: its heartbeat every 10 minutes), the mirror's runs (corpus.sync_runs), when each
genealogy table last changed (corpus.index_*), who may read (corpus.reader_access, corpus.readers, public.user_roles),
and the site's AI calls (srangam_ai_usage). A1 shows them. The desk's own figures (the Claude credit, its jobs, the
translation queue, R1's findings before approval) stay on the desk (127.0.0.1:5057): they are not sent to the site.

## 3. The path

| Step | What | State |
|---|---|---|
| A1 | /admin/desk-site, "Desk and site" (super admin): the desk's worker, the mirror, the genealogies sent, who may read, the AI calls of 7 days; "as of" and Refresh; a late desk or mirror, a failed call or a call not through the own keys said in words. One read-only function (docs/cloud/C30_admin_status_2026-11-19.sql), the kit ADMIN_STATUS (docs/srangam/ADMIN_STATUS_2026-11-19) | built 19 Nov |
| A2 | /admin in two halves: "The articles" (as now) and "The working corpus" (the counts of A1 that a plain admin may see, the desk's last heartbeat, links to the Library, the Genealogies, the vamsas, the editions); the sidebar grouped: Articles; Working corpus and desk; Genealogies; People and access; AI and operations (the same pages, regrouped) | yours to approve: the grouping |
| A3 | The landing pages: Home's "Start here" with the open doors first (/texts, /editions) and the reader doors marked "for invited readers" with the way to ask; the dynasty door naming the 17 texts, a door to the vamsas; /corpus with the same doors and its counts | yours to approve: the words |
| A4 | Tag Management: "suggest categories" run once (I1's first call, your own key), then the 51% uncategorized; Purana References says it reads the articles and links to the Genealogies | A4a is one click of yours; A4b a small text change |
| A5 | Data Health: the corpus checks beside the articles' (the mirror's and the genealogies' digests equal, as index_sync.py reports them) | later: a reader-safe digest function first |

## 4. The guardrails of the rewiring

- Additive first: a new page, a new section, a new function; a page renamed, moved or removed only with the owner's word.
- Every status view fed by the desk says "as of" and has a Refresh (the owner's rule for views fed by another system).
- Status functions read only, for the super admin unless the owner opens them; a refusal is said as a refusal.
- A call to an AI model that is not through the own Gemini or OpenAI key is shown in words, never hidden.
- Kits written only over the version main has (md5), tests with each, a Phase in docs/RELIABILITY_AUDIT.md.
