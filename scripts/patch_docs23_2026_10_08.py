#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs23_2026_10_08.py  DOCS23_2026_10_08

Records the full mirror push, the manifest timeout and its cure (CORPUS_MIRROR_C4B_2026_10_08), and
the working corpus for signed-in readers (CORPUS_READER_C5_2026_10_08). Appends to
docs/PLATFORM_2026-10-04.md (section 26), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 13) and docs/CORPUS_MIRROR_2026-10-08.md. Marker-idempotent per file, backup first, each
file's line endings kept.

  python scripts/patch_docs23_2026_10_08.py --check
  python scripts/patch_docs23_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS23_2026_10_08"

PLATFORM = """

## 26. The whole corpus is in; a manifest that timed out; reading it signed in (DOCS23_2026_10_08)

**What went up on 2026-10-08.**
- **Vectors.** All 21,931, as 273.6 MB in about 9.5 minutes, batches of 112-113 at 1.5 MB and 2-3 s each.
- **Translations.** 229 new Ganita translations travelled in the same run, alone: an incremental run sends only what changed.
- **Status afterwards.** Every table at 100 percent; translations 13,269 in the mirror against 13,272 here, while the desk kept translating.
- **Privacy (V2).** 18 of 18 objects false for anon and authenticated.
- **The vector gate (M4).** markandeya_purana, 1,216 pairs, avg_cos 1.0000 and min_cos 1.0000.
  - The local 3,072-dim vectors cut to 1,536 dims and renormalised are the site's cloud-made vectors.
  - So questions embedded in the cloud and passages embedded on the PC share one space.

**The timeout (C4b, CORPUS_MIRROR_C4B_2026_10_08).**
- **What failed.** The run's last step stopped with `corpus_manifest: canceling statement due to statement timeout`.
- **Why.**
  - The C4 manifest re-read every row of every mirror table, passages with their search column and 3 KB vectors, and sorted every key, on every call.
  - Every later run would have failed at its first call.
- **The cure.**
  - `corpus.row_index`: one narrow row per live mirror row.
  - `corpus.group_digest`: running sums per table and document.
  - Both are kept by `corpus_ingest`/`corpus_retire` in the same statement as the change.
  - The digest is order-free: count, and the two 64-bit halves of md5(key, row_hash) summed modulo 2^64.
- **Speed.** On a full-size copy the manifest went from 274 ms to 8 ms, and keys for a 21,000-row document from a heap scan to 33 ms. It no longer grows with the corpus.
- **Re-sending heals.** Re-sending a row heals a missing index entry. A batch naming a key twice is refused. Writers take one advisory lock.
- **The client.** corpus_sync.py 4.2 makes the same digest and refuses an older server (no wasted re-send). A final check that cannot run is now reported, and the run is logged anyway.

**Reading it (C5, CORPUS_READER_C5_2026_10_08).**
- **The pages.** Srangam gets `/corpus` (every document with counts, search by words and by meaning) and `/corpus/:docCode` (Sanskrit, IAST, English, Hindi, 50 to a page, and "similar passages" from stored vectors).
- **Who.**
  - Six database functions read the closed schema for the caller after `corpus_reader_allowed()`.
  - An admin may always read; otherwise `corpus.reader_access.mode` decides: `signed_in` (the default), `readers` (a list), or `admins`.
  - Anonymous visitors are refused.
- **Meaning search** is the edge function `search-corpus`. It runs as the reader and has no privilege of its own.
- **Sign-up is open.** On Srangam, `signed_in` means anyone with an account. One SQL line narrows it.
- **Tested.**
  - 6 PostgreSQL tests: anon refused; signed-in reads in signed_in; refused in readers until listed and in admins; admin always.
  - On a full-size copy every reader call took under 120 ms.
  - 11 vitest tests.
  - Typecheck clean; build clean, with the entry chunk 486.1 kB (+0.4 kB) and the pages lazy (8.3 kB and 8.5 kB).
  - Every internal link resolves.
"""

RUNBOOK = """

## The mirror after C4b; reading it on the site (DOCS23_2026_10_08)

- **"_scheme" error from corpus_sync.py.** The mirror is on the old digest: apply `docs/cloud/C4b_mirror_digests_2026-10-08.sql` (steps A and B in its header), then run again.
- **Check the digests in the SQL editor.** K1-K3 at the end of the C4b file. If K2 lists a table, run `SELECT corpus._rebuild_index('<table>');` for it.
- **Who may read /corpus.** `SELECT mode FROM corpus.reader_access;`
  - Readers only: `UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();`
  - Add a reader: `INSERT INTO corpus.readers (user_id, note) VALUES ('<id from auth.users>', 'name');`
  - Admins only: mode `'admins'`.
- **"Meaning search is not switched on yet" on /corpus.** Deploy the edge function `search-corpus` through Lovable. Word search and reading work without it.
"""

EP = """

## Addendum 2026-10-08 (13) (DOCS23_2026_10_08)

| # | Item | State |
|---|---|---|
| C4 | Private corpus mirror | All in: 63 documents, 75,734 passages, 13,269 translations, 21,931 vectors; M4 cosine 1.0000 |
| C4b | Manifest timed out on the full mirror | Fixed: incremental order-free digests (row_index, group_digest); client 4.2. To apply: C4b SQL, the 8 rebuilds, then a run |
| C5 | The working corpus on the site for signed-in readers | Built: reader functions (C5 SQL), /corpus pages, search-corpus edge function. To apply: C5 SQL, the Srangam files and patch, push, deploy search-corpus |
| T2 | Scheduled mirror task did not start | Check its battery conditions and last result (commands in the reply of 2026-10-08) |
"""

MIRROR = """

## C4b: digests that do not re-read the mirror (DOCS23_2026_10_08)

- **The timeout.** After all 21,931 vectors were in, the run's final check failed with `corpus_manifest: canceling statement due to statement timeout`. The C4 manifest re-read and sorted every row of every table on every call.
- **The cure.** `docs/cloud/C4b_mirror_digests_2026-10-08.sql` keeps `corpus.row_index` (key and row_hash) and `corpus.group_digest` (count and running sums) current inside `corpus_ingest`/`corpus_retire`.
  - The digest is order-free: `count:sum1:sum2` over md5(key + ' ' + row_hash), modulo 2^64. A change subtracts the old row and adds the new one.
  - The manifest reads a few hundred small rows (8 ms on a full-size copy), and `corpus_keys` reads an index range.
- **Apply.**
  - Step A: the file once.
  - Step B: `SELECT corpus._rebuild_index('<table>');` for each of the 8 tables, one at a time.
  - Then K1-K3. Then corpus_sync.py 4.2, which checks `"_scheme": "sum64.1"` and refuses an older server.

## Reading it: /corpus for signed-in readers (DOCS23_2026_10_08)

- **SQL.** `docs/cloud/C5_corpus_reader_2026-10-08.sql` adds six functions:
  - `corpus_reader_allowed`;
  - `corpus_reader_docs`, `corpus_reader_page`, `corpus_reader_search`;
  - `corpus_reader_similar`, `corpus_reader_match`.
- **Access.** Each reads the closed schema for the caller after one check:
  - an admin may always read;
  - otherwise `corpus.reader_access.mode` decides: `signed_in` (default), `readers` (the list in `corpus.readers`) or `admins`.
  - Not signed in is refused. Nothing in the schema is granted to anyone.
- **Site (Srangam repo).**
  - `src/lib/corpusMirror.ts`.
  - `src/pages/corpus/CorpusHome.tsx` (/corpus: documents with counts, search by words and by meaning).
  - `src/pages/corpus/CorpusDoc.tsx` (/corpus/:docCode: Sanskrit, IAST, English, Hindi, similar passages).
  - `src/components/corpus/CorpusGate.tsx`.
  - `src/lib/safeNext.ts` (/auth?next= brings a reader back).
  - Wired by `scripts/patch_corpus_reader_2026_10_08.py` (App.tsx routes, Auth.tsx next, a link on /texts).
- **Meaning search.** `supabase/functions/search-corpus` embeds the question as search-texts does and calls `corpus_reader_match` as the reader. M4 showed the mirror's vectors and the cloud's are the same (cosine 1.0000), so questions and passages share one space.
- **Sign-up on Srangam is open.** `signed_in` means anyone with an account. The pages say that nothing is reviewed, and they are marked noindex.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP), (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs23_" + stamp))
        t = p.with_name(p.name + ".tmp_docs23"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
