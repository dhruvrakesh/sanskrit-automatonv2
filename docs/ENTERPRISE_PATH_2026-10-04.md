# Enterprise path, 2026-10-04 (ENTERPRISE_PATH_2026_10_04)

This is the forward plan for the whole estate. It was written after reading the documentation of all the repos, the database and its backups, the edge functions, and the operations logs. Every number has a source, named in brackets. Where something could not be checked, it says so.

**What this file replaces:**
- It supersedes `docs/ENTERPRISE_PATH_2026-09-06.md` §4 and `ENTERPRISE_ROADMAP.md` as the forward plan. Both stay as history.
- `RUNBOOK.md` stays the operational canon: how to run things.
- `docs/PLATFORM_2026-10-04.md` records what changed this week.
- `D:\sanskrit-symphony\SOURCES_OF_TRUTH.md` stays the register of where each project lives.

## 1. Where things stand (measured 2026-10-04)

| | Value | Source |
|---|---|---|
| Repo HEAD | `main 43bca067` | STATUS_20261004_1949 |
| Documents in the database | 64 | backup_log 2026-10-04 |
| Live texts on the Shelf | 62 | `/shelf` |
| Texts with 20 or more passages | 35 | STATUS_20261004_1949 |
| Verdicts on those 35 | 0 CURRENT; 3 DERIVED-NEEDS-OCR, 23 NEEDS-OCR, 4 NO-SOURCE-PDF, 5 NEEDS-TRANSLATION | corpus_status via STATUS_20261004_1949 |
| Semantic index | 19,905 vectors; 196 translated passages without a vector; 0 stale; 0 orphaned | same |
| Entity layer | 32,092 mentions, 0 orphaned (157 removed by `fix_orphans --apply`, 17:58); 6 cascade triggers | same; backups `context_pre_orphanfix_*` |
| Budget (the app's own ledger) | cap $25.00; recorded spend $17.72 | `budget_state` in the 17:58 backup |
| Spend, last 7 days | translation $1.82, image $1.47, ocr_vision $0.81, entities $0.31, embedding $0.07, image_brief $0.05, ab_test $0.01 | STATUS_20261004_1949 |
| Vision cost per page (repriced) | Cost / pages delivered, ladder retries included (DOCS8_2026_10_05). Last 24 h on 10-04: $0.00542. All history: $0.00407. Per text: Rgveda $0.00646, Shatpatha $0.00348, markandeya $0.00132, Mallapurana $0.00115. | `usage_log`, 2026-10-05 04:00 backup; PLATFORM s11 |
| Translation cost per passage, provider-metered | $0.00036 | corpus_status header (302 calls) |
| Provider account | **Prepaid.** At 2026-10-04 10:55 UTC two image jobs got HTTP 402: "Your prepayment credits are depleted". | `data/jobs.jsonl` |
| Maintenance task | runs every 3 h when idle. 118 STARTs; 62 skipped because the dashboard was busy; 39 skipped with "no API connectivity" (the last at 15:11 on 10-04); 1 FAIL (2026-09-20, embeddings) | `maintenance_log.txt` |
| Backups | daily at 04:00; 41 runs, 33 logged OK; one 0-byte file (`context_pre_maint_20261004_104726.db`) | `backup_log.txt`; `D:\backups` |
| Srangam site | 1 published text: AphorismsOfSandilya, 439 passages | `block_BE` -Verify log, 2026-09-27 |
| Srangam `/texts` route | pushed (`94d67d5`) | `block_BE_20260927_163829.log` |
| Srangam migration history | 65 rows, newest 20260607043411 | Lovable SQL editor, 2026-10-04 |
| Srangam migrations not recorded in that history | 20260718120000 (the corpus tables, applied by hand 2026-09-08) and 20260910120000 (the stats view; not known whether it was applied) | same |
| Srangam status panel | generated 2026-09-27, 7 days old | STATUS_20261004_1949 |

Not verified:
- whether `/texts` is live on the published site;
- whether migration 20260910120000 was ever run;
- the prepaid balance in AI Studio.

## 2. The documentation estate: what to read for what

| Question | Canonical document | Notes |
|---|---|---|
| How do I run X? | `RUNBOOK.md` | Its §0 map predates PLATFORM and EDITIONS; see the RUNBOOK addendum DOCS7. |
| What changed this week? | `docs/PLATFORM_2026-10-04.md` | Covers spend, images, Shelf and orphans. §10 corrects §9. |
| Where does each project live? | `D:\sanskrit-symphony\SOURCES_OF_TRUTH.md` | Block BB says it is stale on the Booksmith remote and the DB size. |
| Single source of truth per system | `docs/OPERATING_MODEL_2026-09-27.md` §1 | `context.db` is the only writable corpus. Supabase holds a published copy. |
| May I retire or delete? | `docs/RETIREMENT_AND_BACKUP_POLICY_2026-09-14.md` | |
| How do OCR, consensus and re-ingest work? | `docs/OCR_CONSENSUS_2026-09-30.md` | |
| Editions and images | `docs/EDITIONS_AND_IMAGES_2026-10-03.md` | |
| Quality formulas | `scripts/text_filters.py` | QUALITY_METHODOLOGY says the code is authoritative. |
| The Srangam bridge | `docs/SRANGAM_BRIDGE_2026-09-27.md` | Only `--emit-sql` is consistent with "no service key". `publish_srangam.py --publish` still asks for one. |
| The Srangam site plan | `D:\srangam-42267\docs\ENTERPRISE_MASTER_PLAN_2026-07-12.md` plus `CONSOLIDATION_PLAN_2026-09-06.md` §9 | The site's `docs/README.md` index dates from 2025-11-23. |

**Stale documents to stop reading:**
- `UPDATING.md`, which is only a pointer.
- RUNBOOK §6, superseded by §6b.
- HINDI_TRACK_DESIGN rule D1, superseded by TRANSLATION_EMPTY_OUTCOMES §7.
- The numbers in `README.md` and `STEPS_TO_RUN.md`: DB size, prices and the quality threshold.
- On the site: `docs/README.md`, `docs/CURRENT_STATUS.md` (2026-07-12), `docs/SANSKRIT_AUTOMATON.md` (it describes a `sanskrit-analyze` function that does not exist), and `docs/CORPUS_BRIDGE_FINDINGS_2026-09-08.md`, where "no UI reads either table" is no longer true.

## 3. Contradictions, and what is true now

| Topic | Docs disagree | True as of 2026-10-04 |
|---|---|---|
| Vision $/page | 0.00028, 0.00087, 0.0015, 0.0054 | It depends on the book: $0.0012-0.0065 a delivered page, retries included. The 24 h figure of $0.0054 was right; PLATFORM s10's retraction of it was wrong (PLATFORM s11). Estimates now use each text's own rate. |
| 2.5 Flash price | $0.15/$0.60 in STEPS_TO_RUN | $0.30/$2.50, per two price trackers. Google's page no longer lists 2.5 Flash. |
| Image cost | $0.045, $0.078 | The ledger records $0.089-0.093 at 1K and $0.125 at 2K, because about 400 output tokens beyond the image itself are priced at $60/M. |
| Q4 judge | "unbuilt" | Built: `judge_sample.py` writes `mt_reviews`, and 40 verdicts are metered. |
| `ab_source_quality` | "never run" | Ran 2026-10-03 on markandeya: fidelity +1.20 (OCR_CONSENSUS §7). |
| Maintenance entity step | `--retry-empty` | `maintenance_runner.ps1` runs `extract_entities --limit 1500` without `--retry-empty`. The runner is the truth. |
| Status panel commit | `block_BD -Emit -Commit` | `-Emit`, then review. `-Commit` pushes Srangam `main`. |
| Hindi prompt | hi-v2, hi-v3 | The file `prompts/hi-production.txt`, identified as `hi-file-18a0d5f5eb` (v4 content). |
| DB size | 210 MB to 943 MB | 943 MB. |
| Hard spend stop | "configure in Google Cloud" | The account is prepaid, so its credit is the hard stop. The app's cap is a second, earlier stop. |
| History row for 20260718120000 | OPERATING_MODEL §5 "add one" vs CORPUS_BRIDGE "do not hand-insert" | Do not hand-insert. Phase 3 item S2 makes the file safe to replay instead. |

## 4. Phases

### Rules for every phase

- Every change is surgical: anchored, marker-idempotent and backed up. A test fails before the change and passes after it.
- Read before you write.
- No git through the bridge. No VACUUM. No push to the web repos' `main` from scripts.
- Supabase is reached only through the Lovable SQL editor.
- One dashboard, restarted only when idle.

### Phase 0: truth and safety (now, this week)

| # | Item | Done when |
|---|---|---|
| 0.1 | CREDITS_COST_2026_10_04: a 402 aborts translation runs; fallback model gemini-2.5-flash-lite; vision estimate uses the mean; Shelf badge and repeated titles | Tests green; the `corpus_status` header says "mean" |
| 0.2 | Reconcile the prepaid credit in AI Studio against `usage_log` for one day | The two differ by less than 10%, or the difference is explained in PLATFORM |
| 0.3 | VERIFY_RANGE_2026_10_04: `block_BE -Verify` reports Content-Range 0-0/439 and whether the stats view is live | Log shows both |
| 0.4 | Srangam migration audit: run `srangam_migration_audit_2026_10_04.sql` Q1-Q6 (read-only) | The one history row not in the repo is identified; objects confirmed present |
| 0.5 | Housekeeping | The 0-byte backup and the two `-wal`/`-shm` sidecars removed; status panel re-emitted (`-Emit`) and published |
| 0.6 | Docs: this file, the RUNBOOK map addendum, PLATFORM §10 | Released |

### Phase 1: corpus quality, clean source first (weeks 1-4)

The order follows `corpus_status`. Each book goes through consensus → drift → re-ingest → translate → QA → embeddings. Spend is quoted at today's measured rates.

| # | Item | Size | Estimate |
|---|---|---|---|
| 1.1 | markandeya_purana: finish English (373/1,268 done), then Hindi `--reference none`, QA, lacunae | 895 EN + 1,266 HI | about $0.80 |
| 1.2 | Rgveda Vol-ii: vision on the remaining pages, merge, re-ingest, translate | 618 pages, then about 11.5k passages | vision about $4.0 at Rgveda's own $0.00646 a page (DOCS8); translation about $4 EN + $4 HI |
| 1.3 | Dhanurveda: vision on the two PDF-backed codes, then ingest into them | `dhanur_veda_shiva_dhanur_veda` 19 pages; `dhanur_veda_vasishtha_dhanur_veda` 32 pages | Vision done 2026-10-05, about $0.06 for 51 pages, all clean. Next: re-ingest and translate. |
| 1.4 | The other NEEDS-OCR texts, largest debris first | 23 texts | about $12-13 (STATUS 19:49, median-based, +11% for the mean) |
| 1.5 | Derived texts (`*_seg`): vision on the source, ingest as `<src>_v2`, re-split to `<doc>_v2` | manu, harita, nilamata | $1.5 (STATUS) |
| 1.6 | NO-SOURCE-PDF: find PDFs for LalitaVistara, Bodhicaryavatara and bodhyana. Vasishtha's PDFs exist under the `dhanur_veda_` code (1.3). | 4 | |
| 1.7 | **RETIRE_BY_PAGE.** `diag_retire_check` matches verse text exactly, so a Tesseract copy can never "match" its own clean re-OCR: Shiva Dhanur Veda gave 204 of 204 verses not found, NOT SAFE. Add a page-coverage mode for the same source re-OCR'd: every retiree page must be covered by the keeper, with a character-mass ratio threshold. | tool + test | |
| 1.8 | MBh01 Hindi: 6,747 passages without Hindi | | about $2.5 |

Gate for calling a text CURRENT: source debris ≤ 5%, English and Hindi lacunae ≤ 5%, current prompt versions, a vector for every translated passage.

### Phase 2: pipeline and UI (weeks 2-6, alongside Phase 1)

| # | Item | Source |
|---|---|---|
| 2.1 | U1: live job output in the dashboard, which ends the need for screenshots of consoles | PLATFORM §5 |
| 2.2 | C1: consensus as a dashboard job with the measured cap | OCR_CONSENSUS |
| 2.3 | Import chain intents (`pipeline_intents.jsonl`, Stage column), PIPELINE_STATE phases 1-4 | PIPELINE_STATE §4 |
| 2.4 | A Windows Job Object for `_run_job`, so killing a parent kills its children | ENTERPRISE_PATH_2026-09-06 #13 |
| 2.5 | Shelf title sweep: confirm the `*` titles, add Devanagari titles. Booksmith and Srangam read `doc_titles.json`. | PLATFORM §7; OPERATING_MODEL Phase 2.3 |
| 2.6 | A maintenance probe that reports a 402 ("credits depleted") instead of "no API connectivity" | maintenance_log |
| 2.7 | Hindi vectors (a design decision) | PLATFORM §2 |

### Phase 3: publishing and the site (weeks 3-8; changes on the Lovable side go through Lovable)

| # | Item | Source |
|---|---|---|
| S1 | Confirm `/texts` is live, then `block_BE -ReaderLive`. Re-emit the status panel weekly. | block_BE log; RUNBOOK §3h |
| S2 | Make 20260718120000 safe to replay (IF NOT EXISTS / DROP POLICY IF EXISTS) through Lovable. Decide on 20260910120000 from Q2. | migration audit |
| S3 | Publish only CURRENT texts (none today), through `--emit-sql` and the publication gate | SRANGAM_BRIDGE |
| S4 | Hindi on the site: an l10n table migration (Lovable), then the bridge | OPERATING_MODEL Phase 2.2 |
| S5 | Security: `gdrive-image-proxy` is open (no auth, `*` origin, any id). Add the allowlist. | Srangam Master Plan 5.1 |
| S6 | Site data-loss bug P0.1: import overwrites multilingual content | Srangam PRIORITY_ROADMAP |
| S7 | Re-index the site docs: replace the 2025-11-23 `docs/README.md` index; mark the stale docs | this file §2 |
| S8 | Images to the site (I5); regenerate `types.ts` for the stats view | EDITIONS; migration audit |

### Phase 4: run it as an enterprise (from week 6)

- **Unattended automation.** Only after two clean weeks (OPERATING_MODEL Phase 4), and read-only first: drift checks, `status_report`, `spend_audit`.
- **Weekly:** prepaid-credit reconciliation, `status_report`, the status panel, and the Shelf title sweep.
- **Monthly:** a restore drill. Restore a `context_YYYYMMDD.db` to a scratch path, then run `diag_brain` and the counts.
- **Docs truth.** Each release that changes behaviour appends to the PLATFORM doc of its week. The RUNBOOK map is updated whenever a doc is added.

## 5. Risk register

| Risk | Status | Control |
|---|---|---|
| Prepaid credit runs out mid-run | Seen 2026-10-04 | CREDITS_COST aborts translation; consensus stops after 5 failures; the app cap trips first if set below the balance. |
| An estimate understates spend | Was median-based | Mean plus 15% headroom; the ledger uses provider token counts. |
| Orphans after deletes | 0 now | 6 cascade triggers; `retire_doc` before/after counts; `diag_orphans`. |
| Retirement destroys unique text | Guarded | `diag_retire_check`; 1.7 adds the page mode. |
| Migration replay fails on the site | Possible (non-idempotent file) | S2. |
| Open proxy on the site | Open | S5. |
| A backup that is not a backup | One 0-byte file | `status_report` flags it; delete it. |
| Docs drift | Continuing | §2 and §3 here; append-only PLATFORM docs. |


## Addendum 2026-10-05: vignettes and the anthology (DOCS9_2026_10_05)

| # | Item | State |
|---|---|---|
| 1.9 | Cited retellings for drawn images; episode mining; anthology export (`scripts/stories.py`, `patch_vignettes`) | Built 2026-10-05; first runs on markandeya_purana and Mallapurana |
| 2.8 | A Story panel on the `/images` cards (write, verify, approve from the page) | Next UI item, alongside U1 |
| 2.9 | Image ideas placed from mined episodes rather than a 40,000-character sample | After 1.9 has run on two books |
| 3.9 | A fidelity check of the cited passages before approval (judge_sample on those passages) | Before an anthology goes outside the team |
| S9 | Approved stories to the Srangam reader beside the passages (needs a site table; Lovable side) | After S4 |


## Addendum 2026-10-05 (2): Stories page, gaps (DOCS10_2026_10_05)

| # | Item | State |
|---|---|---|
| 2.8 | Story review in the browser: write, check, edit, approve, anthology, PDF (`/stories`) | Built 2026-10-05 as its own page (not a panel on `/images`); cards link to the image library |
| 2.10 | verify: sentence split after a citation; speech openers | Built 2026-10-05 (STORIES_UI) |
| 2.11 | Untranslatable passages counted as gaps; running-heads tagging | Built 2026-10-05 (GAPS); first use markandeya_purana |
| 3.10 | Story fidelity: a judge on the cited passages, and a reader's correction loop back to the passage | Open (follows 3.9) |


## Addendum 2026-10-07: pictures, books, brain items; next phases (DOCS11_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.12 | Pictures from stories: propose, draw, approve and redraw on `/stories` | Built 2026-10-07 |
| 2.13 | Book composer: choose texts and stories, order, readers; reading book HTML and PDF; Booksmith edition | Built 2026-10-07 (Booksmith verified on a copy of 0.2.1) |
| 1.10 | Editorial index for Ask (`brain_items`): stories, episodes and images; maintenance step b2 | Built 2026-10-07 |
| 2.14 | Running heads with a page number and a danda (markandeya) | Built 2026-10-07 |
| 2.15 | Retellings per age group (`stories.py retell --audience young`): a variant row with the same checks; citations kept in the data and hidden in the young layout | Next. About $0.01 a story |
| 2.16 | Graphic novels of 10-15 pages from a story or a text (see below) | After 2.15 |
| C0-C4 | The cloud brain on the existing Supabase (Lovable Cloud): vectors as halfvec(768), approved stories and images, an Ask Edge Function. See docs/CLOUD_BRAIN_2026-10-07.md | After the audit Q1-Q6 |

**Graphic novel, as designed (2.16).** Nothing in it is drawn or captioned without a passage behind it.
- **novel plan --story N --pages 12** makes one call (about $0.01). Inputs: the story's passages, the approved retelling and its notes. Output: the pages and their panels, each with a scene, a caption of at most 25 words with its [page.idx] citation, and dialogue only where a passage quotes speech. It also writes a cast sheet that fixes each figure's iconography. The output is checked by the existing verify rules: citations present and in range, and names found in the cited passages.
- **novel cast** draws a reference sheet for each main figure (2-4 images).
- **novel draw** draws one image per page, giving the cast sheets to the image model as reference images so the figures stay the same from page to page. No lettering goes in the images. Captions are typeset in HTML, because script drawn by an image model is unreliable, Devanagari above all.
- Layout is an HTML comic template (page image and caption boxes), then a PDF through `export_pdf.py`. A person approves each page.
- **Cost:** about $1.4 to $1.9 for 12 pages at 1K-2K (13 to 16 images at $0.09-0.13, plus the plan), plus redraws. Budget-gated, a dry run first.


## Addendum 2026-10-07 (2): younger readers, graphic novels, cloud C0/C1 (DOCS12_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.15 | Versions for children 8-12 and readers 13-16 (`retell`, `variant`), used by the books for those ages | Built 2026-10-07 |
| 2.16 | Graphic novels: cited plan, cast sheets as references, pages, per-page approval, book (`novel.py`, "Graphic novels" tab) | Built 2026-10-07 |
| 1.11 | Ask skips noise and frontmatter (running heads) | Built 2026-10-07 |
| 1.12 | Maintenance runs while a long translation is going (embeddings serialised behind it by SQLite, not skipped) | Open: needs a measured test of concurrent writes first |
| 1.13 | Delete the vectors of noise rows (`build_embeddings --prune`) | Open; Ask already filters them |
| C0 | Read-only pre-flight (`docs/cloud/C0_preflight_2026-10-07.sql`) | Ready to run |
| C1 | Vectors, stories, RLS, `match_text_passages` (`docs/cloud/C1_corpus_brain_DRAFT_2026-10-07.sql`) | Drafted and tested on PostgreSQL 16 + pgvector 0.8.0; not applied |
| C2 | Edge function `embed-published-passages` in the Srangam repo | Next, after C1 |


## Addendum 2026-10-07 (3): healing after the audit (DOCS13_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.17 | Bulk re-check of stories, "draft passes / fails" filters, "Next:" line, greyed-button explanations (STORY_RECHECK) | Built 2026-10-07 |
| 1.14 | brain_items loads `.env` (CLI and maintenance b2 failed with "GEMINI_API_KEY not set") | Built 2026-10-07 |
| 1.15 | corpus_status counts rows the translator never sends as gaps (GAPS2) | Built 2026-10-07 |
| S1 | Srangam: inspect 20260201064547 (H1), apply `srangam_cross_reference_stats` (H3), verify (H4) | Ready to run in the SQL editor |
| T1 | Ganita_Yukti_Bhasa translate_both: 709 of 1,460, stopped by the 12:16 restart on 2026-10-07 | Open: resume from the dashboard, machine kept awake |
| 1.12 | Maintenance alongside long translations | Open: measure concurrent writes first |
| 1.13 | Delete the vectors of noise rows | Open; Ask already filters them |
| C0 / C1 / C2 | Cloud pre-flight, corpus brain schema, `embed-published-passages` | C0 ready to run; C1 drafted and tested, not applied; C2 next |


## Addendum 2026-10-07 (4): second pass (DOCS14_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.18 | Story check: title words, quotations, visarga stems (VERIFY_NAMES); 11 of 13 pass, 2 real failures left | Built 2026-10-07 |
| 1.16 | corpus_status `--doc` resolves a unique prefix or case, suggests close codes, never falls through to all texts (DOC_HINT) | Built 2026-10-07 |
| S1 | `srangam_cross_reference_stats` live: 1,561 references, 1,392 public (RLS: both articles published) | Done 2026-10-07 14:40 |
| S2 | Read-only follow-up: the full 20260201064547 statement, who can execute increment_term_usage_counts, the live policies, the 169 hidden references by status, SECURITY DEFINER functions anon can run | Ready to run |
| T1 | Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V: 977 of 2,706 without English, no Hindi (corrects addendum 3) | Open: resume, machine awake |
| T2 | Translation throughput: 91-157 passages an hour, one call per passage | Open: a measured comparison (thinking budget, batching) on a sample, judged by qa_scan, before any change |
| 1.12 / 1.13 | Maintenance alongside long translations; noise vectors | Open; 1.12 matters more now (T1 keeps the dashboard busy for a day or more) |
| C0 / C1 / C2 | Cloud pre-flight, corpus brain schema, `embed-published-passages` | C0 ready to run; C1 drafted and tested, not applied; C2 after C1 |


## Addendum 2026-10-07 (5): Srangam state and lockdown (DOCS15_2026_10_07)

| # | Item | State |
|---|---|---|
| S2 | Read-only follow-up (G1-G5) | Done 15:05-15:06 |
| S3 | Revoke anon (and authenticated where service-role only) on `_cron_invoke_edge`, `reconcile_stuck_admin_jobs`, `get_corpus_correlations`, `get_corpus_correlations_v2` | Ready to run; tested |
| C0 | Cloud pre-flight | Done 15:07: every C1 precondition met |
| C1 | Vectors, stories, RLS, `match_text_passages` | Ready; apply together with C2 |
| C2 | Edge function `embed-published-passages` (GEMINI_API_KEY is already referenced by Srangam edge functions; confirm it is set in Lovable Cloud secrets) | Next |
| W1 | Status panel stale (2026-09-27) and says there is no reading page; the fix (6b15ee7) is local on a feature branch | Open: manual git on main, then Publish |
| W2 | Publish markandeya_purana to /texts (gate report, SQL, review, flip) | Open: your decision |
| W3 | Article titled "....docx (1)"; network type filter offers 5 types, 2 exist | Open: Srangam admin / Lovable |
| W4 | completeWorks needs 100% English; texts whose only gaps cannot be translated as printed are never "complete" | Open: Srangam generator |
| T1 | Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V is NEEDS-OCR (21.9% debris, 0% vision, 339 pages, est $1.08): OCR and re-ingest before translating (corrects addendum 4) | Open |


## Addendum 2026-10-07 (6): the cloud brain's first real step (DOCS16_2026_10_07)

| # | Item | State |
|---|---|---|
| S3 | Function lockdown | Applied 16:13; L3/L4 as expected; post-revoke cron runs to confirm (S4 M6) |
| W2 | markandeya_purana on /texts | Done 16:1x: 1,216 passages, 25 pages |
| W7 | Engine label and IAST title for markandeya (S4 M2/M3); publisher labels by itself from now on (PUBLISH_ENGINE) | M2/M3 ready to run; patch built |
| W1 | Status panel: SITE_CORPUS 2026-10-07 and the "readable on this site" line (SITE_LINE) | Patch built; manual git on main, then Publish |
| R768 | 768 vs 1536 dimensions, measured: recall@12 0.893 vs 0.956 | Done; 1536 chosen |
| C1 | Final file: halfvec(1536), embed queue, explicit grants | Ready to apply; re-tested |
| C2 | `embed-published-passages` edge function + run/schedule SQL | Built and tested offline; deploy, then R1-R5 |
| C3 | Ask on the site: embed the question (RETRIEVAL_QUERY, 1536), match_text_passages, answer with citations | Next, after C2 has run |
| W5 | "<decorative line>" OCR markers shown on the reader (2 passages, p1.4 and p1.6) | Open: strip in the publisher or the reader |
| W6 | Hindi on the reader (B1 has no Hindi column) | Open: needs a column, the publisher and the reader page |
| W3 | Article titled "....docx (1)" | S4 M4/M5 ready |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |


## Addendum 2026-10-07 (7): live state and search (DOCS17_2026_10_07)

| # | Item | State |
|---|---|---|
| S3 | Function lockdown | Done and confirmed: cron ran at every 5-minute run after the revoke |
| W1 | Status panel | Live, measured 2026-10-07 |
| W3 / W7 | Article title; Markandeya label and IAST title | Done |
| C2 | embed-published-passages | Deployed (Lovable redeploy 596aaf80); 500 of 1,655 vectors stored; three more R3 calls |
| C3a | Search the published texts by meaning: `search-texts` edge function + /texts card + reader anchor | Built and checked on a copy (tsc, vitest 18/18, vite build, browser with mocked APIs); patch ready for the Srangam repo |
| C3b | Ask: a generated answer that cites only the matched passages (signed-in users first, as it costs per answer) | Next, after C3a is live |
| W8 | Load time: 505 kB entry chunk (177 kB gzip) | Open: measure what the entry pulls in before splitting |
| W5 / W6 | "<decorative line>" markers on the reader; Hindi on the reader | Open |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |


## Addendum 2026-10-07 (8): search live, stories, load time (DOCS18_2026_10_07)

| # | Item | State |
|---|---|---|
| C2 | embed-published-passages | 1,500 of 1,655; one more R3; NULL guard (C1c) applied |
| C3a | Search the texts by meaning | Live: deployed 12:19 UTC; real search 10 hits; reader link lands and marks |
| ST1 | Story corrections #3, #5, #10 | story_fix.py + fix file; on a copy 13/13 pass; run it, then approve after reading |
| ST2 | Approved stories on the site (srangam_stories) | Next: an --emit-sql bridge for approved stories, like the passages |
| W8 | Load time | Patch: entry 505 -> 486 kB, hero 172 KB off every non-home page; further cuts need Home changes |
| W5 | "<decorative line>" on the reader | Patch ready; p8.1 running head needs a local noise mark, then a site DELETE |
| W6 | Hindi on the reader | Planned: column, publisher, reader (coverage 99.7%) |
| C3b | Ask (generated answer citing only matched passages) | After C3a has run for a while; signed-in users first |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |


## Addendum 2026-10-07 (9): end of day (DOCS19_2026_10_07)

| # | Item | State |
|---|---|---|
| C2 | Passage vectors | Complete, 1,655; nightly cron job 9 |
| W8 / W5 | Load time; reader marks | Live (a3600fe) |
| ST1 | Story corrections | Applied; 13/13 pass; #3 approved, 12 drafts to read and approve |
| EX1 | Empty exports, missing Hindi provenance, raw code titles | Fixed in patch_exports_gate (to apply) |
| NV1 | Novel print layout, cover span, sources | Fixed (to apply); redraw the 4 pickaxe pictures; choose a cover with --cover |
| G1 | Gate withheld verses below a furniture line | Fixed (to apply); republish 10 verses with --only |
| ST2 | Approved stories on the site (srangam_stories) | Next |
| W6 | Hindi on the reader | Next, planned in section 21 |
| C3b | Ask | After C3a has run a while |
| T1 / T2 / 1.12 | Ganita OCR first; translation throughput; maintenance alongside long jobs | Open |


## Addendum 2026-10-08 (10) (DOCS20_2026_10_08)

| # | Item | State |
|---|---|---|
| D1 | Live tab showed a dead run as "Calling API" | Fixed: "stopped" with how to continue (to apply; restart the dashboard) |
| D2 | Spend cap from the dashboard | Added to the Usage tab (to apply) |
| D3 | Runs die when the console closes (nine ended with exit 3221225786 since 2026-09-08; the 2026-10-07 run died with the dashboard) | Open: run the dashboard so a closed window cannot end it (a scheduled task, or pythonw with a log file) |
| G1 | Ten withheld verses | SQL written; paste it (still 1,216 and 439 on the site) |
