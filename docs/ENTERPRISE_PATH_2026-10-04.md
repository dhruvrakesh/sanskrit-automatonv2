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


## Addendum 2026-10-08 (11) (DOCS21_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror: all 63 live documents in PostgreSQL, kept current, idempotent (docs/CORPUS_MIRROR_2026-10-08.md) | Built and tested. To apply: P1, C4 SQL, the secret, deploy corpus-ingest, the text push, the vector gate (M4), the vectors, then the 2-hourly task |
| C4b | Ask over the whole corpus (admin-only scope in search-texts using corpus.match_passages) | Open, after C4 |


## Addendum 2026-10-08 (12) (DOCS22_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror | Schema applied, function deployed. Text pushed 10:09 UTC (75,734 passages, 13,040 translations, 317 groups equal). markandeya_purana vectors 1,258. Next: M4, then all vectors, then the 2-hourly task |
| C4p | A push showed nothing until its end | Fixed: [m:ss] progress lines and --status (PROGRESS_2026_10_08) |
| T1 | test_export_mode_joblog race on Windows | Fixed in the test (JOBLOG_RACE_2026_10_08); dashboard unchanged |


## Addendum 2026-10-08 (13) (DOCS23_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror | All in: 63 documents, 75,734 passages, 13,269 translations, 21,931 vectors; M4 cosine 1.0000 |
| C4b | Manifest timed out on the full mirror | Fixed: incremental order-free digests (row_index, group_digest); client 4.2. To apply: C4b SQL, the 8 rebuilds, then a run |
| C5 | The working corpus on the site for signed-in readers | Built: reader functions (C5 SQL), /corpus pages, search-corpus edge function. To apply: C5 SQL, the Srangam files and patch, push, deploy search-corpus |
| T2 | Scheduled mirror task did not start | Check its battery conditions and last result (commands in the reply of 2026-10-08) |


## Addendum 2026-10-08 (14) (DOCS24_2026_10_08)

| # | Item | State |
|---|---|---|
| C4b | Mirror digests | Applied: K1 indexed = digested in all 8 tables, K2 none |
| T2 | Scheduled mirror task | Fixed (battery conditions). 16:35 and 17:18 runs rc=0; 17:18 sent only 4 changed translations, verify 380 equal |
| C5 | /corpus for signed-in readers | SQL applied, mode signed_in; Srangam 60fe0551 pushed. To confirm: search-corpus deployed, Publish, /corpus signed in |
| D3 | Runs die when the console closes | Fixed in code (DASH_HIDDEN_2026_10_08): no window, logs in D:\backups\dashboard_logs, refuses to restart mid-job. To apply: the patch, then a restart while idle |
| A1 | Sign-in loop for signed-in non-admins; admins bounced after sign-in | Fixed in code (AUTH_ROLE_2026_10_08). To apply: the patch in Srangam, push, Publish |


## Addendum 2026-10-08 (15) (DOCS25_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Sign-in loop | Applied: Srangam 4ffb5cbf |
| D3 | Runs die with the console | Released (a0e4515a); in effect at the next idle restart of the dashboard |
| C2 | Cron job 9 | Ran 2026-10-08 04:15 UTC, succeeded |
| C5 | Reader functions | R1 confirmed; search-corpus failed to deploy (cross-folder import). Fixed in code (embed.ts). To apply: the Srangam patch, push, deploy |
| R1 | Navigation and layout of the readers | Built (READER_NAV_2026_10_08, C5b). To apply: C5b SQL, the Srangam patch, push, Publish |
| R2 | Next for the readers | Hindi on the published reader (W6), entity tooltips from mentions, and a chapter list once the chapter field carries numbers |


## Addendum 2026-10-08 (16) (DOCS26_2026_10_08)

| # | Item | State |
|---|---|---|
| C5b | Contents for the reader | Applied (N1 confirmed) |
| R1 | Reader navigation and layout | Applied: Srangam 4b853181; search-corpus deployed (anon 401 as designed) |
| L1 | The desk's library on the site (Shelf, Stories, Names, name chips, ?at=) | Built (C6, CORPUS_LIBRARY_C6_2026_10_08). To apply: C6 SQL, the Srangam patch, push, Publish |
| L2 | Covers, images and editions (HTML, PDF, Booksmith) on the site | Next: a private Storage bucket filled by the mirror run, read through signed URLs |
| L3 | Ask over the corpus (C3b) | Next: answers with citations over corpus_reader_match |
| L4 | Editor actions from the site (approve, titles, shelves) | Design: a request queue the desk pulls and applies; the desk stays the source of truth |
| P1 | Panchang/Jyotish (Streamlit) | A separate app; /jyotish-horoscope describes it. Compare before porting anything |
| V10 | The 10 withheld verses | Still 1,655 on 2026-10-08 evening: paste the six --only files |


## Addendum 2026-10-08 (17) (DOCS27_2026_10_08)

| # | Item | State |
|---|---|---|
| L1 | The desk's library on the site | Applied: C6 in the DB; automaton 5113170a; Srangam f9fbde31 |
| A1 | Roles: super admin, invited researchers, audit log (C7a, C7, RBAC_RESEARCHERS_2026_10_08) | Built and tested (14 PG, 26 vitest). To apply: C7a alone, C7, the Srangam patch, push, Publish |
| A2 | Close the corpus to plain sign-ups (mode 'readers') | After the first researcher has accepted: one switch on /admin/researchers |
| A3 | Automatic invitation email | Next: edge function (service role or Resend); needs the /invite/* redirect allowed and a sending domain |
| A4 | Researchers' requests (corrections, texts) | With L4: the request queue the desk pulls |
| V10 | The 10 withheld verses | In progress: markandeya_purana passage_count 1,219, published; the remaining --only files to paste |


## Addendum 2026-10-08 (18) (DOCS28_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Roles: super admin, invited researchers, audit log | Site: Srangam 4d70389f, pushed. Database: first attempt 21:14 rolled back cleanly, so C7 is still to apply: P1-P7, C7a ALONE, V0, C7, V1-V7 (C7_checks) |
| A1d | Srangam docs: the order; RELIABILITY_AUDIT Phase X and invariants 23-26 | patch_rbac_docs_2026_10_08.py, after A1 or before it (documentation only) |
| A2 | Close the corpus to plain sign-ups (mode 'readers') | After the first researcher has accepted: the switch on /admin/researchers |
| A3 | Invitation email sent by the site | Next: an edge function on `_shared/auth-gate.ts` (requireUser, then `is_super_admin()`), using the service role for `auth.admin.inviteUserByEmail` (new accounts) or a provider such as Resend. Needs `/invite/*` allowed as an auth redirect URL in Lovable Cloud |
| A4 | Researchers' requests (corrections, texts) | With L4: a request queue the desk pulls |
| A5 | Types | Lovable regenerates `types.ts` with the new enum values and functions when it next syncs the schema; the site does not depend on it (typed wrappers in `src/lib/rbac.ts`) |


## Addendum 2026-10-08 (19) (DOCS29_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Roles: super admin, invited researchers, audit log | Applied: C7 at 21:41 IST, V0-V7 as expected; automaton 455522a2, Srangam bdc5b797 pushed |
| A1p | Publish and one invitation end to end | Next: Publish in Lovable; invite an address you can read; accept in a private window |
| A2 | Mode 'readers' | After A1p, if wanted (the switch on /admin/researchers) |
| D3 | The dashboard without a window | Done: running through the launcher since 19:52; the error log is empty |
| O1 | Health of everything scheduled | PC side healthy (mirror, maintenance embeddings, backup, dashboard). Cloud side: OPS_health H1-H4 to confirm |
| V10 | The 10 withheld verses | In progress: H3 shows passage_count against passages and vectors per text; job 9 embeds them the night after |


## Addendum 2026-10-09 (20) (DOCS30_2026_10_09)

| # | Item | State |
|---|---|---|
| M1 | Pictures and graphic novels on the site, private in the Shared Drive | Built and tested: C8 (8 PG tests), corpus-media (10 Deno tests), corpus_media.py (15), the site (12 vitest, typecheck, build). Next: the RUNBOOK steps (C8, Srangam patch, deploy, the first push) |
| M1s | The pictures in the two-hourly tick, and the PC kept awake for it | `patch_media_task_2026_10_09.py`, after the first manual push |
| M2 | Editors approve, retire or redraw from the site; the desk applies it | Next after M1 |
| R1 | The Researchers' Corner `/corpus/corner`: saved passages, notes, my requests | Designed (docs/MEDIA_AND_CORNER_2026-10-09.md, section 3) |
| R2 | Requests (story, picture, novel, correction), with approval for spend | Designed; defaults in section 3 |
| R3 | The desk worker runs requests with the existing CLIs, within the live budget | Designed |
| R4 | Spend, caps and audit per request and researcher | Designed |
| A1p | Publish and one invitation end to end | Still open |
| V10 | The withheld verses (markandeya 01/99; Sandilya 00/01/99) | Still open |


## Addendum 2026-10-09 (21) (DOCS31_2026_10_09)

| # | Item | State |
|---|---|---|
| M1 | Pictures and graphic novels on the site | Live: C8 applied and checked, corpus-media deployed, 57 pictures / 114 renditions / 2 novels pushed; the task carries them every 2 h |
| R1-R3, M2 | The Researchers' Corner: requests carried out on the desk, the editors' queue and decisions, anthologies, print | Built and tested (C9 7, corpus-desk 19, worker 10, site 20). Next: the RUNBOOK steps |
| R5 | Young and teen versions on the site | Next: mirror `doc_story_variants` (a C4 addition) |
| P2 | A public page for published anthologies | Your decision: it needs a public path for their pictures |
| B1 | The desk's typeset books (Booksmith, `stories.py book`, `novel.py build`) on the site | Next: chunked uploads to Drive; the site's print covers it until then |
| A1p | Publish and one invitation end to end | Still open |
| V10 | The withheld verses | Still open |


## Addendum 2026-10-09 (22) (DOCS32_2026_10_09)

| # | Item | State |
|---|---|---|
| R1-R3, M2 | The Researchers' Corner | Switched on: C9 applied and checked, corpus-desk deployed, the worker live, the site published, two researchers invited. Next: the first story, picture and novel plan through it |
| L1 | Fewer questions per page | Built: one role check per user at a time; the Pictures page asks once (Srangam LOAD_L1, 4 new tests) |
| C10 | The Corner level with the desk's own pages | Next, after the first round trip. Free kinds: edit a story, check it again, edit a picture, restore a picture, edit a novel page. Paid kinds: picture ideas for a text, a cover. A "draw again" option for a novel's pages and cast (`--redo`) |
| L2 | The first load | Next: the entry chunk is 498 KB (175 KB gzip) on every first visit. Measure what the home and corpus pages load before changing any chunking |
| R5, B1, P2, R6 | Young and teen versions; the desk's books on the site; a public anthology page; notifications | As in addendum 21 |
| A1p | Publish and one invitation end to end | Done for the invitations (Kanika, Parth) |
| V10 | The withheld verses | Still open |


## Addendum 2026-10-09 (23) (DOCS33_2026_10_09)

| # | Item | State |
|---|---|---|
| L1 | Fewer questions per page | Live (e2d53dd): one role check per page |
| S0 | The mirror past a timed-out batch | Live (client 4.3, 67b45ce3); the mirror back in step at 15:30 (392 groups equal, 0 different) |
| C10a, S1 | The Corner as it happens | Built and tested: progress, stages, next steps, live refresh; editors' Sync tab. Next: switch on (RUNBOOK) |
| T1 | Learn: quests, XP, levels, badges, toolbox, Team panel | Built and tested (C11 + the site). Next: switch on |
| C10 | The Corner level with the desk's own pages | Next: story_edit, story_verify, picture_edit, picture_restore, novel_page_edit, picture_ideas, picture_cover, draw again |
| L2 | The first load (entry 491 KB, 173 KB gzip) | Next: measure first |
| T2 | Learn, second round | After C10 |
| R5, B1, P2, R6 | As in addendum 21 | As before |


## Addendum 2026-10-09 (24) (DOCS34_2026_10_09)

| # | Item | State |
|---|---|---|
| C10a, S1 | The Corner as it happens | Live: ffdacb5f, Srangam 84409ca, C10a, desk worker 1.1 |
| T1 | Learn: quests, XP, levels, badges, toolbox, Team panel | Live: C11, Srangam 84409ca |
| C10 | The Corner level with the desk's own pages | Next |
| L2 | The first load: entry 498.92 kB (175.78 kB gzip) | Next: measure what the home and corpus pages fetch first |
| T2 | Learn, second round | After C10 |
| R5, B1, P2, R6 | As in addendum 21 | As before |


## Addendum 2026-10-09 (25) (DOCS35_2026_10_09)

| # | Item | State |
|---|---|---|
| C10a, S1, T1 | The Corner as it happens; Learn | Live (C10a pasted 9 Oct evening; corner_request_track answers) |
| C10 | The Corner level with the desk: edits, check again, ideas, covers, draw an idea, restore, novel page edits, redo | Built and tested (worker 1.2, C10b, the site). Next: switch on (RUNBOOK) |
| R6, A3 | Email from nartiang.org: requests done/failed/waiting/not approved, invitations | Built and tested (C12, corner-mail, the site). Needs RESEND_API_KEY and Email on |
| L2 | The first visit | Two cuts built (P3, P4). Next: P2 after a check in Hindi and Tamil; P1 by traffic mix |
| T2 | Learn quests for C10's kinds | Next |
| R5, B1, P2 | As in addendum 21 | As before |


## Addendum 2026-10-10 (26) (DOCS36_2026_10_10)

| # | Item | State |
|---|---|---|
| C10 | The Corner level with the desk | Live: worker 1.2 (07:28), C10b, Srangam 852d852 |
| R6, A3 | Email from nartiang.org | Database and site live; RESEND_API_KEY added; next: Lovable deploys corner-mail, then Reply-to and Email on |
| L2 | The first visit | P3 and P4 live (852d852). Next: P2 after a check in Hindi and Tamil |
| N1 | The working corpus and Learn in the navigation, by role | Built and tested (NAV_RBAC_2026_10_10). Next: push and Publish |
| T2 | Learn quests for C10's kinds | Next |


## Addendum 2026-10-10 (27) (DOCS37_2026_10_10)

| # | Item | State |
|---|---|---|
| N1 | The working corpus and Learn in the navigation, by role | Live (Srangam ab15244) |
| R6, A3 | Email from nartiang.org | Live: corner-mail deployed, email on. Next: Reply-to set to a real inbox, and a first email |
| U1 | The Corner, guided (`docs/CORNER_UX_U1_2026-10-10.md`) | Built and tested (CORNER_UX_U1_2026_10_10). Next: push and Publish |
| C13 | Researchers see the work in progress; the offering so far | Built and tested. Next: your paste (recommended) |
| U2 | Sparks across the corpus; a weekly team goal | Next: one read-only function; the goal is your decision |
| U3 (T2) | Learn, second round | Next: C10's kinds; the first story of a text |
| U4 (P2) | Sharing what is published | Your decision: pictures need a public path |
| U5 | The editors' queue, by value | Later |
| L2 | The first visit | P2 after a check in Hindi and Tamil, as before |


## Addendum 2026-10-10 (28) (DOCS38_2026_10_10)

| # | Item | State |
|---|---|---|
| D1 | The dashboard: one status read at a time, `/api/health`, the Library says why and follows its runs, Usage, History, Queue | Built and tested (DESK_HEAL_2026_10_10). Next: patch; restart when idle |
| D2 | Maintenance beside an OCR job, looking again between steps | Built and tested. Next: patch (takes effect at the next run) |
| H2 | The Srangam Hub v2: the corpus end to end (this PC, the cloud, the site); light checks; detached Start | Built and tested (HUB_V2_2026_10_10). Next: patch; restart the hub; commit in the hub's repository |
| O1 | Karan Aagama's source | Held by the debris guard. Next: the OCR consensus plan (no spend), then translate |
| O2 | Ganita Yukti Bhasa | Its last English run: 1 of 180 translated, 180 below the OCR quality bar. Next: re-OCR, not translation |
| C13 | Researchers see the work in progress | As in addendum 27: your paste, when chosen |


## Addendum 2026-10-10 (29) (DOCS39_2026_10_10)

| # | Item | State |
|---|---|---|
| C13 | Researchers see the work in progress; the offering so far | **Live** (13:04), checked P1, V1-V3; the strip reads from the database |
| U1 | The Corner, guided | **Live** (Srangam d1752d4, published) |
| R6, A3 | Email from nartiang.org | Reply-to still empty (D2). Next: set it, then a first email |
| D3 | Every press visible: the Log follows every job and says what it did; live output | Built and tested (LIVE_LOG_2026_10_10). Next: patch, reload; live output on the restart |
| H3 | The hub's last runs, held texts, OCR progress | Built and tested (HUB_V2_1_2026_10_10). Next: patch, restart the hub |
| O1 | Karan Aagama | Consensus run: 145 of 183 pages stale. Your decision: re-ingest (replaces 1,603 English and 1,425 Hindi) or translate the rest with `--allow-debris` |
| O3 | Natyasastra, Tantric Texts | Held; nothing to lose. Next: consensus plan, then vision, re-ingest, translate |
| O4 | Hayashirsha | Held; 1,174 Hindi exist. Your decision, as O1 |
| U1.1 | Two editions with one title in the Corner's list (Vasishtha and Shiva Dhanur Veda) | Next: tell them apart |
