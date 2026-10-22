#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_pg_tests_2026_10_22.py  (2026-10-22)  PG_TESTS_2026_10_22

The 19 test modules that need a real PostgreSQL (CORPUS_TEST_DSN) had never run here: 184 tests skipped in every
suite. Run on 22 Oct in a throwaway PostgreSQL 16 (UTF8) with pgvector 0.8.0, a fresh database per module: 18 modules
passed as they are; tests/test_corpus_sync_pg_2026_10_08.py failed in its setup on a fresh database ("type
public.halfvec does not exist"), because it alone did not apply the test-only Supabase stand-ins
(tests/supabase_stubs_2026_10_08.sql: pgvector, the anon / authenticated / service_role roles, auth.uid()), which the
other modules apply first. Now it applies them too; its 10 tests then pass, its anon / authenticated refusal test
included (it was skipped where those roles were missing). With it, 283 tests pass, 0 fail (the two end-to-end classes
of the corner worker run on the databases C9 and C10a were applied to). The SQL files themselves needed no change.
Needs: pgvector 0.7 or later (halfvec); a UTF8 database (in SQL_ASCII psycopg returns bytes, and most assertions
fail).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_pgtests_<date>.
  python scripts\\patch_pg_tests_2026_10_22.py --check
  python scripts\\patch_pg_tests_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'PG_TESTS_2026_10_22'
TAG = 'pgtests'
FILES = ['tests/test_corpus_sync_pg_2026_10_08.py']
NEEDS = {'tests/test_corpus_sync_pg_2026_10_08.py': 'CORPUS_MIRROR_C4_2026_10_08'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('tests/test_corpus_sync_pg_2026_10_08.py', 1, 'SQL = REPO / "docs" / "cloud" / "C4_corpus_mirror_2026-10-08.sql"\nSQL_B = REPO / "docs" / "cloud" / "C4b_mirror_digests_2026-10-08.sql"\nTABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",\n          "entities", "docs", "row_index", "group_digest"]',
     'SQL = REPO / "docs" / "cloud" / "C4_corpus_mirror_2026-10-08.sql"\nSQL_B = REPO / "docs" / "cloud" / "C4b_mirror_digests_2026-10-08.sql"\nSTUBS = REPO / "tests" / "supabase_stubs_2026_10_08.sql"   # PG_TESTS_2026_10_22: pgvector, anon, authenticated\nTABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",\n          "entities", "docs", "row_index", "group_digest"]')

edit('tests/test_corpus_sync_pg_2026_10_08.py', 2, '        if "supabase.co" in DSN or "pooler" in DSN:\n            raise unittest.SkipTest("refusing to run against a Supabase host")\n        cls.pg.execute(SQL.read_text(encoding="utf-8"))\n        cls.pg.execute(SQL.read_text(encoding="utf-8"))      # twice: the file is re-runnable',
     '        if "supabase.co" in DSN or "pooler" in DSN:\n            raise unittest.SkipTest("refusing to run against a Supabase host")\n        cls.pg.execute(STUBS.read_text(encoding="utf-8"))  # PG_TESTS_2026_10_22: a fresh database has no halfvec\n        cls.pg.execute(SQL.read_text(encoding="utf-8"))\n        cls.pg.execute(SQL.read_text(encoding="utf-8"))      # twice: the file is re-runnable')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
