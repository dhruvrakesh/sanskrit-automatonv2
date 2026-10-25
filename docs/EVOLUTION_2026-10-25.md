# How the project grew: February to 25 October 2026

EVOLUTION_2026_10_25. Traced from the repository's own history (.git/logs/HEAD: about two hundred commits, the first
on 15 Feb 2026), the dated documents in docs\ and the spend ledger (data\budget_changes.jsonl). Each stage names the
markers its code carries, so any claim here can be checked in the code.

## The stages

| When | Stage | What it brought | Where it lives |
|---|---|---|---|
| 15 Feb | The first commit | An audit's fixes: the dashboard's document checks, ingest on db_utils' schema | git history |
| 14-16 Jun | **v2: a pipeline with a dashboard** | Gemini 2.5 Pro then Flash as the engine; OCR, ingest, translate as jobs with history; the cost tracker with a cap and an automatic pause (budget_state); the pipeline queue; danda-preserving verse segmentation, IAST, metre detection, translation with a context window; the three-column reader (Sanskrit, English, notes) | ARCHITECTURE.md, scripts\dashboard.py, cost_tracker.py |
| 19-22 Jul | **The critical edition and the quality loop** | The Mahabharata's Adiparvan imported from the BORI e-text (MBh01) with a benchmark harness; translation provenance, a heuristic QA score, re-translation that keeps history (Q1-Q3); empty and refused answers never cached (5,899 poisoned rows purged) | docs\QUALITY_LOOP_DESIGN_2026-07-20.md |
| 1-16 Aug | **Hindi, editions, healing** | The Sanskrit-to-Hindi track anchored by the verified English; the scholarly edition export (Debroy's conventions: italic terms, verse references, footnotes); the source-echo guard; the QA panel and non-destructive Heal | docs\HINDI_TRACK_DESIGN_2026-08-01.md |
| 23-30 Aug | **Ask, names, and the OCR settled by measurement** | Ask the Corpus with cited verses, then by meaning (embeddings); the names layer (entities, variants, mentions); the LLM judge of fidelity (Q4); the maintenance task (idle- and online-guarded); the finding that re-OCR does not help (the failure is misread Devanagari), so vision OCR (ocr_vision.py) for the pages Tesseract garbles; QUALITY_METHODOLOGY.md | BENCHMARKS.md, QUALITY_METHODOLOGY.md |
| 6-14 Sep | **Consistency** | The semantic layer made operable; orphans found; line endings pinned; Booksmith editions by language; retirement made complete or not at all; the nilamata source retired with its verses grafted back | docs\RETIREMENT_AND_BACKUP_POLICY_2026-09-14.md |
| 27-30 Sep | **Operating model** | Paid-but-empty outputs kept; unreadable verses parked; one dashboard only; every book's stage derived; exports name their edition | docs\OPERATING_MODEL_2026-09-27.md, PIPELINE_STATE |
| 1-5 Oct | **Consensus and the meter** | OCR consensus in one command (Tesseract, vision on the queued pages, audit, merge, drift); every paid call metered and gated; prepaid credits; stories and pictures | docs\OCR_CONSENSUS_2026-09-30.md, COST_TRUTH |
| 7-10 Oct | **The site: Srangam** | Srangam healed and locked down (S1-S3); the cloud brain (C1-C3a: 1,536 dimensions, search by meaning); the private corpus mirror in PostgreSQL (C4, C4b); the working corpus, library, roles, media and the Researchers' Corner (C5-C13); mail from nartiang.org | docs\CORPUS_MIRROR_2026-10-08.md, RESEARCHERS_CORNER |
| 11-14 Oct | **Repair and redemption** | The repair path for one text and the Source desk; an e-text as a witness; the readings benchmarked; the in-place re-ingest; the path of every text; what of the paid translation is redeemed; the scholarly English (v1 to v2.1) | docs\REPAIR_PATH_2026-10-10.md, REDEEM, SCHOLAR |
| 15-18 Oct | **Engines and benchmarks** | The thinking metered as billed; Claude as an engine of the scholarly English, capped by its credit and judged by Gemini; BM1-BM3 against published translations (private, never ingested); the translation desk; scholarly editions on the site | docs\BENCH_*, TRANSLATION_DESK, EDITIONS_SITE |
| 19-22 Oct | **The scholars' shelf and the witnesses** | The leak guard; Raychaudhuri's Political History read into claims tied to our names; the Cologne indexes on the shelf; GRETIL's two zips read as a library of witnesses; fidelity measured akshara by akshara; the debt collected | docs\SHELF_AND_SURYA, CLAIMS_AND_REFS, FIDELITY, DEBT |
| 23-24 Oct | **Relations** | The links our texts make between names (entity_links); one Ask page and the Professor; the indexes' kinships read and checked (kin_index.py: 22,431 read); the desk's health mailed; "named together" on the site (45,183 pairs); lines of descent by the index's own entries; the Relations page | docs\RELATIONS_AND_ASK_2026-10-22.md |
| 25 Oct | **Vamsa and consolidation** | The Purana Index's citations read in GRETIL's Sanskrit (4,910 relations with both names in the cited verse); the Vamsa page; the scans' repair kept going by itself within an allowance | docs\VAMSA_2026-10-25.md, CONSOLIDATION_2026-10-25.md |

## What stayed constant

- **Source before translation.** From August's OCR measurement to October's repair path: a damaged scan is repaired
  or replaced by a better witness before it is translated; the critical edition wherever it exists.
- **Measured, not assumed.** Each decision names its measurement (the OCR A/B of 29 Aug; the cost meter of 4 and 15
  Oct; the fidelity of 22 Oct; the matching rules of 25 Oct tuned on the real data, for precision).
- **Nothing silent.** Every script ends with VERDICT, NEXT and ALSO; the maintenance task logs a TICK before any
  guard (28 Aug) and a FAIL instead of stopping in silence (24 Oct).
- **Surgical changes.** Anchored, all-or-nothing, marker-idempotent patches with backups; a test for each.
- **Rights respected.** Copyrighted scholars read privately and never published; BORI's notice kept; GRETIL's licence
  credited; the Daivat-Sanhita withdrawn until 2029.

## The spend, as the ledger has it

The cap was raised as the work grew, each time by hand on the dashboard: $25 to $29 (8 Oct, $23.70 spent), $45 (12
Oct), $60 (15 Oct), $70 (16 Oct), $80 (17 Oct), $85 (18 Oct, $73.26 spent), $95 (22 Oct), $100 and $110 (23 Oct),
$115 (24 Oct, $103.48 spent). On 25 Oct, 09:00: $106.43 spent, $8.57 left.

## Where it stands (25 Oct)

84 texts' codes in the database, 26,552 passages with English and 15,597 with Hindi (the backup of 25 Oct); 13,369
names with 40,624 mentions in 15,095 passages; 45,261 pairs named together and 233,071 named near. With this release
the repository holds 78 documents in docs\, 184 scripts besides 275 patch scripts, and 199 test modules.
