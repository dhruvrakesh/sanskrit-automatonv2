# Sanskrit Automaton — Enterprise Hardening Roadmap

*Written 2026-08-26. Evidence-based; every claim below cites a file:line in the
current tree. The system is RUNNING and FUNCTIONAL — every phase is designed to be
surgical, reversible, and deployed at a controlled moment, never a rewrite.*

---

## Honest assessment: what is solid vs. fragile

**Solid.** WAL + `busy_timeout` + `synchronous=NORMAL` are correctly defined in the
canonical helper (`db_utils.py:17-28`). Backups are now automated, pruned, logged, and
**restorable** (`UPDATING.md` §5). OCR discovery, the false-"done" feedback, hyphenated
doc names, and the misleading job labels are all fixed. Data is safe (55 docs / 13,677
EN / 5,136 HI / 5,135 entities).

**Baseline measured 2026-08-27** (read-only, `diag_baseline.py`): DB is a **normal local
file** on a **fixed NTFS disk** (`DriveType Fixed`, `Attributes = Archive`, not a reparse
point) = **mirror mode, WAL-safe locally**. `journal_mode=wal`, `page_size=4096`.
**Load times are excellent** — per-doc coverage aggregate `0.00s`, full counts `0.07s`
— so the DB layer is *not* a performance bottleneck. Corpus: 56 docs / 13,746 EN /
5,136 HI / 5,169 entities / 22,894 mentions / 13,544 embeddings. EN quality histogram:
0.8–1.0 = 754; 0.6–0.8 = 3,223; **0.4–0.6 = 9,479 (~69%)**; <0.4 = 301.

**Fragile — the real root causes (corrected after measurement).**

1. **A file-sync client touching the hot WAL sidecars is the `SQLITE_IOERR` suspect.**
   Correction: an earlier draft claimed raw connections use `busy_timeout=0`. That is
   wrong — Python's `sqlite3.connect()` defaults `timeout=5.0` (a 5-second busy timeout);
   `db_utils.connect()` (`db_utils.py:189-194`) extends it to 30s. So raw connections in
   `translate_passages.py:193` and `dashboard.py` (`764, 831, 850, 1136, 1218, 1314,
   1415, 1478`, plus `connect()` at `298`) already wait 5s, not 0. Unifying to 30s is
   cheap insurance, **not** the root cause. The `disk I/O error` symptom on a *local* WAL
   DB is the classic signature of another process (a sync client — Google Drive and/or
   Dropbox, both present) reading/locking `context.db-wal` / `context.db-shm` mid-write.
   The fix is to keep any sync client off the live DB and its sidecars. (Phase 1.)

2. **Storage: confirmed local (mirror), so the fix is light.** No relocation of the whole
   DB is required for WAL safety. Either exclude `context.db*` (db, `-wal`, `-shm`) from
   the sync client, or move just the live DB to a sibling non-synced local folder and
   keep syncing only the consistent `db_backup.py` outputs. (Phase 1/2.)

The semaphore-and-callback work is fine and stays, but it is throughput/UX, not the
substrate.

---

## Phase 0 — Measure (read-only, run now)

Establish a baseline before changing anything. Confirms Drive mode, journal mode, WAL
sidecar files, DB size, per-connection `busy_timeout`, and a load-time number. All
read-only; safe to run while jobs are active. Commands are in the chat message that
accompanies this document.

**Exit criteria:** we know (a) Drive mode (stream vs mirror), (b) that `journal_mode=wal`,
(c) the load-time baseline for the heaviest dashboard query, (d) the quality-score
distribution baseline.

---

## Phase 1 — Keep sync clients off the live DB  *(the actual root-cause fix)*

**Confirm first.** Identify which sync client (Google Drive mirror and/or Dropbox — both
run on this machine) actually covers `D:\Sanksrit Automatons\...`. If *none* does, the
`disk I/O error` attribution to "Drive sync" was inherited from earlier notes and must be
re-investigated (capture the actual SQLite error + offending process next time it fires).

**Change (if a sync client covers the folder).** Preferred: relocate just the **live** DB
to a sibling *non-synced* local folder (still on fast local disk, e.g.
`D:\SanskritAutomatonLive\context.db`), and keep syncing only the consistent
`db_backup.py` outputs to the cloud. Alternative: use the sync client's selective-sync /
ignore rules to exclude `context.db`, `context.db-wal`, `context.db-shm`. Either removes
the mid-write contention on the WAL sidecars that produces `SQLITE_IOERR`.

**Effect.** Eliminates the real source of "disk I/O error while a job runs," and removes
any file-access stalls the sync client causes (the DB queries themselves are already
sub-100ms, so this is where perceived slowness actually lives).

**Risk / rollback.** A relocation is one path change (`--db` arg + backup runner `$src`);
fully reversible. Do it during an idle window with a fresh backup in hand.

**Cheap insurance (bundle in the same restart).** Unify raw connections to
`busy_timeout=30000` (matches `db_utils`) so the rare writer-vs-writer overlap waits 30s
instead of 5s. Not the root cause — just belt-and-suspenders.

**Verification.** With a translate job running, hammer a dashboard read endpoint in a loop
and confirm zero errors before/after.

---

## Phase 2 — (folded into Phase 1)

Storage is confirmed **local/mirror**, so no heavy migration is needed — the light
"keep sync off the live DB" step in Phase 1 is the whole fix. Reassess only if the
sync-client diagnostic shows something unexpected.

---

## Phase 3 — Reconsider concurrency on the healed substrate  *(optional, measured)*

Once connections are unified (Phase 1) and storage is local/WAL-safe (Phase 2), the
single-writer translate semaphore is no longer needed for *DB safety* — WAL supports one
writer + many readers, and `busy_timeout` serializes the rare writer overlap. Its
remaining justification is **Gemini API rate-limiting**. Options, to be A/B-measured, not
assumed: keep `1` (simplest, current), or raise to `2` and watch for 429s and lock waits.
The parallel-OCR pipeline (already shipped) stays regardless.

---

## Phase 3.5 — Calibrate the quality metric BEFORE mass action  *(new; benchmarked)*

**Reconciled with `docs/QUALITY_LOOP_DESIGN` + `HINDI_TRACK_DESIGN` (2026-08-27).** The
Phase-Q loop already exists: provenance columns, the `translation_qa` heuristic scorer,
`translation_history`, and `retranslate.py`/`heal_lowqa.py`. `translation_qa` is high
(≈0.99 mean) — but the design docs are explicit that this is **structural** soundness,
**not** certified semantic fidelity. The one designed-but-UNBUILT piece is **Q4: the
sampled LLM-judge** (`judge_sample.py` + an `mt_reviews` table) that grades fidelity and
fluency 1–5 against source+IAST. That is the real quality frontier — build it (bilingual
en+hi from birth per HINDI_TRACK HI-5), plus score the manual MBh01-vs-Debroy sheet, and
THEN the "is 0.988 actually faithful?" question is answered. `quality_score` is a separate
axis (source-corruption gate) and stays as-is. Est. cost: ~$0.03–0.05 for a 5% MBh01
sample — trivially within the $8 budget envelope (`cost_tracker.py`).

**Root-cause decision tree — run `diag_provenance.py` FIRST, then pick ONE lever:**

- **A/B: low score tracks OLD engine / prompt version / early months** → the fix is
  **re-translate** the weak verses with `gemini-2.5-pro` + current prompt
  (`retranslate.py` / `heal_lowqa.py`). Cheapest, most surgical; no re-OCR, no re-source.
  This is the *expected* culprit given the PDFs are high quality.
- **C: source `text` Devanagari purity is low for a doc** → OCR/source is genuinely noisy
  → **re-OCR** that doc's high-quality PDF at 400–600 DPI, or re-source clean e-text.
- **Neither** (clean source + current engine, still low) → the *scorer* is miscalibrated →
  fix `score_translation_quality`, not the translations.

Auto-download/auto-populate from archive.org is **rejected as a blanket strategy**: (a)
the PDFs are already high quality, (b) raw archive OCR text discards the verse/`chandas`/
daṇḍa structure our pipeline extracts, harming translation context, (c) it adds source
variance. Use archive only surgically, for genuinely broken sources (corrupt PDFs), via
the purity-gated `archive_source_finder.py`.

## Phase 4 — Quality & observability

**Translation fidelity (the Debroy track).** The ceiling is OCR noise, not the model
(e.g. Shatpatha's live output shows garbled Devanagari, `skip:198`). Import clean e-text
for OCR-limited works from GRETIL / sanskritdocuments.org, re-ingest on a clean base, then
re-run embeddings + entities. This is the single biggest fidelity lever.

**Observability.** Persist per-job metrics (verses/min, skip%, err%, lock-wait time) to
`usage_log`; surface a small trends panel. Add a verification harness (a subagent QA pass)
for high-stakes re-translations.

---

## Operating discipline (the part that makes it "enterprise")

- **Measure → change one thing → verify → commit → next.** No multi-change restarts of a
  live system without a stated rollback.
- **Every change: risk + rollback named up front** (as above).
- **A fresh backup exists before any Phase-2 storage move.**
- **Docs updated in the same commit as the change** (`UPDATING.md`, this file).
