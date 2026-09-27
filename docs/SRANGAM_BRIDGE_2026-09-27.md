# Automaton → Srangam bridge: state, fix, and the SQL-editor route (2026-09-27)

Marker: `PUBLISH_BRIDGE_2026_09_27`. This page reconciles three sources:

- the Srangam repo docs, in particular `docs/CORPUS_BRIDGE_FINDINGS_2026-09-08.md` and `docs/APPS_AND_CORPUS_INTEGRATION_2026-07-18.md`;
- the migration `supabase/migrations/20260718120000_srangam_texts_corpus.sql`;
- `scripts/publish_srangam.py` in this repo.

## What was true before today

- **Tables exist but are empty.** The migration was pasted into the Lovable Cloud SQL editor on 2026-09-08 and passed 7/7 checks, so `srangam_texts` and `srangam_text_passages` exist. Nothing reads them yet: no route and no component (Findings, 2026-09-08).
- **No route in.** `publish_srangam.py` requires `SUPABASE_SERVICE_ROLE_KEY`. House rule: there is no service-role key on this machine. Findings calls this "THE ONE BLOCKER".
- **The script could not have run anyway.** This was verified in the code on 2026-09-27:
  1. The `if __name__ == "__main__": main()` guard sat above `gate_rows()` and `doc_title()`, so a real push stopped with a NameError.
  2. `--dry-run` read `doc['title']`, but `docs` has no title column.
  3. `--gate-report` and `--no-gate` were parsed, but the publication gate was never called.

## What changed (`scripts/patch_publish_bridge.py`)

- **The three defects are fixed.** The gate now runs before every push, dry run and SQL export.
- **New mode: `--emit-sql DIR`.** It writes the same upserts as UTF-8 files, under `DIR/<doc_code>/`, for the Lovable Cloud SQL editor:
  - `00_text.sql`
  - `NN_passages.sql` — 200 passages per file by default, or fewer when a file would pass 450 KB
  - `99_verify.sql`
  - `MANIFEST.txt`, which lists each file with its sha256
- **How the files behave:**
  - They are written by the program, never by a shell redirect or the clipboard, as CONSOLIDATION_PLAN §10 requires.
  - Every file can be re-run without changing its content. None of them deletes anything or touches `srangam_texts.published`.
  - Each ends with a SELECT, because the SQL editor shows only the last result.
  - `99_verify.sql` is read-only. It compares the local passage count with the remote count and lists **stale** rows: rows on the site that are no longer in the local publishable set. The bridge never deletes those; removing one is a human decision.

**Tested on 2026-09-27 against real PostgreSQL**, using the migration's own DDL and RLS, with stubs for `auth.uid()`, `has_role()` and the `updated_at` trigger function. AphorismsOfSandilya (453 translated passages; the gate withheld 17, leaving 436) produced 5 files:

- The files ran twice with identical results: 436 local, 436 remote, 0 stale.
- `published` stayed `true` after a re-run.
- The sanskrit, IAST and translation text of all 436 rows is byte-identical to `context.db` (md5 compared row by row).

## Using it

```
python scripts/publish_srangam.py --doc AphorismsOfSandilya --gate-report
python scripts/publish_srangam.py --doc AphorismsOfSandilya --emit-sql "D:\Sanksrit Automatons\_ops_2026-09-10\srangam_sql" --engine gemini:gemini-2.5-flash
```

Paste the files into the Lovable Cloud SQL editor in `MANIFEST.txt` order. The text lands unpublished. Once you have reviewed it, run `UPDATE public.srangam_texts SET published = true WHERE doc_code = '<code>';` in the same editor.

## Known gaps (not changed here)

- **No Hindi on the site yet.** The schema has no Hindi or prompt-version column, so only English travels. Adding them needs a new migration through Lovable; that is a decision for the site owner.
- **No reader page.** The `/texts` route (APPS §B3) does not exist yet, so published rows are not visible on the site.
- **Migration history is incomplete.** `supabase_migrations.schema_migrations` has no row for `20260718120000`, and `types.ts` has not been regenerated (Findings caveats).
- **Engine label.** `translation_engine` is sent only when you pass `--engine`. Without it, the existing label is kept (COALESCE).
