# -*- coding: ascii -*-
"""PG_TESTS_2026_10_22: tests/test_corpus_sync_pg_2026_10_08.py applies the test-only Supabase stand-ins
(tests/supabase_stubs_2026_10_08.sql: pgvector, the roles, auth.uid()) before C4, as every other PostgreSQL test
module does, so that it runs on a fresh database; the patcher applies once, from the copy it found. Reads the files
only; needs no database."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
T = REPO / "tests" / "test_corpus_sync_pg_2026_10_08.py"
STUBS = REPO / "tests" / "supabase_stubs_2026_10_08.sql"
PAT = REPO / "scripts" / "patch_pg_tests_2026_10_22.py"
MARK = "PG_TESTS_2026_10_22"
APPLIED = MARK.encode() in T.read_bytes()


@unittest.skipUnless(APPLIED, "PG_TESTS_2026_10_22 is not applied here")
class TheSetup(unittest.TestCase):
    def test_the_stand_ins_come_first(self):
        s = T.read_text(encoding="ascii")
        self.assertIn('STUBS = REPO / "tests" / "supabase_stubs_2026_10_08.sql"', s)
        i = s.index('cls.pg.execute(STUBS.read_text(encoding="utf-8"))')
        self.assertLess(i, s.index('cls.pg.execute(SQL.read_text(encoding="utf-8"))'))
        self.assertGreater(i, s.index('"refusing to run against a Supabase host"'), "never on a Supabase host")

    def test_the_stand_ins_are_re_runnable_and_test_only(self):
        q = STUBS.read_text(encoding="utf-8")
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;", q)
        self.assertIn("Never run this on", q)
        for role in ("anon", "authenticated", "service_role"):
            self.assertIn("rolname = '%s') THEN CREATE ROLE %s" % (role, role), q)


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(T.parent.glob(T.name + ".bak_pgtests_*"))
        if not baks:
            self.skipTest("no .bak_pgtests_ copy here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "tests").mkdir()
            shutil.copy2(baks[0], t / "tests" / T.name)
            pat = [sys.executable, str(PAT)]
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((t / "tests" / T.name).read_bytes(), T.read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
