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

**Fragile — the real root causes.**

1. **Hot paths bypass the hardened connection helper.** `db_utils.connect()`
   (`db_utils.py:189-194`) applies WAL + `busy_timeout=30000`. But the workhorse
   `translate_passages.py:193` uses `sqlite3.connect(args.db)` **raw**, and
   `dashboard.py` opens raw connections in ~10 endpoints (`764, 831, 850, 1136, 1218,
   1314, 1415, 1478`, plus its own no-pragma `connect()` at `298`). Raw connections get
   `busy_timeout=0` → a dashboard read that overlaps a translate write throws
   `SQLITE_BUSY` / "disk I/O error" **instantly** instead of waiting. **This is the
   concurrency error we have been papering over with the single-writer semaphore.**

2. **Storage location is unverified.** The live DB is at
   `D:\Sanksrit Automatons\...\data\context.db` on a Google-Drive-managed path. If Drive
   runs in **stream** mode the file is virtual and WAL is explicitly unsupported by
   SQLite on network/virtual filesystems; if Drive runs in **mirror** mode the file is a
   real local file (WAL-safe) and only *backup* copies risk a torn read. We must
   determine which before prescribing a move. (Phase 0.)

The semaphore-and-callback work is fine and stays, but it is throughput/UX, not the
substrate. The substrate is Phases 1–2.

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

## Phase 1 — Unify & harden DB access  *(highest value, lowest risk)*

**Change.** Route every connection through one helper that always sets
`busy_timeout=30000` + WAL: fix `translate_passages.py:193` and the raw
`sqlite3.connect` sites in `dashboard.py` to call a shared `open_db()` (or minimally,
execute `PRAGMA busy_timeout=30000` immediately after connect). No schema change, no
data change.

**Effect.** Dashboard reads no longer error during a translate write (WAL already allows
readers concurrent with one writer; `busy_timeout` makes any writer-vs-writer contention
*wait* up to 30s rather than fail). Removes the entire class of "disk I/O error while a
job runs" without touching the semaphore.

**Risk / rollback.** Additive pragma only; behavior strictly more tolerant. Rollback =
revert the two files. Deploy at a dashboard restart (translation resumes idempotently).

**Verification.** With a translate job running, hammer a dashboard read endpoint in a
loop and confirm zero errors (Phase-1 verify script).

---

## Phase 2 — Right-size the storage substrate  *(decided by Phase 0)*

**If Drive is in STREAM mode** (virtual files): relocate the **live** DB to a local,
non-synced folder (e.g. `C:\SanskritAutomaton\data\context.db`); keep only the *backups*
flowing to Drive. This removes the unsupported "WAL on virtual FS" condition and, because
a 411 MB file is no longer re-synced on every write, **improves load/IO times** directly.
Cutover uses the existing `db_backup.py` for a consistent move; the dashboard's `--db`
arg and the backup runner's `$src` are repointed. Rollback = point `--db` back.

**If Drive is in MIRROR mode** (local files): the live DB is already WAL-safe locally; the
only real risk is Drive uploading a torn copy. Mitigation is lighter — exclude the live
`context.db` (and `-wal`/`-shm`) from sync, and continue syncing the consistent
`db_backup.py` outputs. No relocation needed.

**Risk / rollback.** One path change; fully reversible. Do it during an idle window with a
fresh backup in hand.

---

## Phase 3 — Reconsider concurrency on the healed substrate  *(optional, measured)*

Once connections are unified (Phase 1) and storage is local/WAL-safe (Phase 2), the
single-writer translate semaphore is no longer needed for *DB safety* — WAL supports one
writer + many readers, and `busy_timeout` serializes the rare writer overlap. Its
remaining justification is **Gemini API rate-limiting**. Options, to be A/B-measured, not
assumed: keep `1` (simplest, current), or raise to `2` and watch for 429s and lock waits.
The parallel-OCR pipeline (already shipped) stays regardless.

---

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
