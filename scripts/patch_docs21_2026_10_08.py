#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs21_2026_10_08.py  DOCS21_2026_10_08

Records the private corpus mirror (CORPUS_MIRROR_C4_2026_10_08, docs/CORPUS_MIRROR_2026-10-08.md):
appends section 24 to docs/PLATFORM_2026-10-04.md, a RUNBOOK.md entry and an
docs/ENTERPRISE_PATH_2026-10-04.md addendum, and git-ignores data/corpus_sync_log.jsonl.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs21_2026_10_08.py --check
  python scripts/patch_docs21_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS21_2026_10_08"

PLATFORM = """

## 24. The whole brain in PostgreSQL, kept current (CORPUS_MIRROR_C4_2026_10_08; DOCS21_2026_10_08)

**The question.** Could the whole 1 GB brain go to PostgreSQL for querying, and stay current while translation goes on? Until now only published text did: 2 texts, about 1,655 passages.

**What the 983 MB file holds** (`context_20261008.db`, read-only):
- **Mirrored, about 105 MB of rows:**
  - 63 live documents;
  - 75,734 passages;
  - 12,517 Hindi rows;
  - 8,269 entities and 32,861 mentions;
  - 44 stories and 767 stage rows.
- **Vectors.** 21,931 vectors (281 MB) are cut to 1,536 dims.
- **Left at home:**
  - `passages.norm`, the raw OCR page repeated on every passage of that page (286 MB);
  - SQLite's own search index (216 MB);
  - mt_cache (48 MB);
  - the usage tables;
  - the 3 retired documents.

**How (docs/CORPUS_MIRROR_2026-10-08.md).**
- **The schema.** A private schema `corpus` (C4 SQL): RLS on with no policy, no grant to anon or authenticated, not served by the Data API.
- **The PC side.** `scripts/corpus_sync.py`, read-only on context.db.
- **The cloud side.** The `corpus-ingest` edge function, which accepts only HMAC-signed requests. The secret is `CORPUS_SYNC_SECRET`; the service role stays in Supabase.
- **What travels.** Each row carries a content hash, and each table and document has a digest. Only rows whose hash differs travel. Upserts ignore unchanged rows, and rows gone locally are retired, never deleted.
- **Re-runnable.** Repeated and interrupted runs are harmless. Every run ends by comparing digests ("N groups equal, 0 different").

**Gate before the vectors.** M4 compares the mirror's vectors (local, cut to 1,536) with the site's C2 vectors for markandeya_purana. Expect avg_cos >= 0.99.

**Tested.**
- 21 unit tests, with no database and no network (an in-memory server, and an HTTP stub that checks signature and gzip).
- 7 tests on PostgreSQL 16 + pgvector 0.8.0.
- 7 Deno tests.
- End to end, the real index.ts in front of PostgreSQL as service_role.
- A full-size copy: 248 s for the first push, then 3.1 s with nothing to send, 265 MB in PostgreSQL.
- The real backup: planned, and type-audited with 0 problems.
"""

RUNBOOK = """

## The private corpus mirror (DOCS21_2026_10_08)

- **What it is.** A private PostgreSQL copy of the whole brain, for querying from anywhere: `docs/CORPUS_MIRROR_2026-10-08.md`, steps 1-9.
- **The plan.** `python scripts\\corpus_sync.py` prints what would be sent and sends nothing. Add `--apply` to send.
- **Check the connection.** `python scripts\\corpus_sync.py --hello`.
- **One document.** `python scripts\\corpus_sync.py --apply --doc markandeya_purana`. A partial run never retires documents.
- **HELD lines.** A large retire (a re-segmented or emptied document) is held. Read the line, then re-run with `--allow-mass-retire` if it is right.
- **"stopped=budget".** `--max-mb` was reached; the next run carries on.
- **The scheduled tick.** `scripts\\corpus_mirror_task.ps1`, every 2 hours, logs to `D:\\backups\\corpus_mirror_log.txt`. It skips quietly until CORPUS_SYNC_SECRET is in .env.
- **Rotating the secret.** Make a new one, replace it in .env and in Lovable Cloud -> Secrets. Requests signed with the old one get 401.
"""

EP = """

## Addendum 2026-10-08 (11) (DOCS21_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror: all 63 live documents in PostgreSQL, kept current, idempotent (docs/CORPUS_MIRROR_2026-10-08.md) | Built and tested. To apply: P1, C4 SQL, the secret, deploy corpus-ingest, the text push, the vector gate (M4), the vectors, then the 2-hourly task |
| C4b | Ask over the whole corpus (admin-only scope in search-texts using corpus.match_passages) | Open, after C4 |
"""

GITIGNORE = """
# CORPUS_MIRROR_C4_2026_10_08 (DOCS21_2026_10_08): the mirror's run log stays local
data/corpus_sync_log.jsonl
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP), (Path(".gitignore"), GITIGNORE)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs21_" + stamp))
        t = p.with_name(p.name + ".tmp_docs21"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
