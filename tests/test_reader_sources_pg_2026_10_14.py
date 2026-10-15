# -*- coding: ascii -*-
"""C17_READER_SOURCES_2026_10_14 against a real PostgreSQL: public.corpus_reader_sources(p_doc) counts one text's live
passages by page and ocr_engine, for signed-in readers only (the C5 gate), and leaves retired passages out. Applies
the Supabase stand-ins, C4, C4b, C5 and C17 (C17 twice), fills the mirror from the corpus_sync fixture with PgSink,
then sets engines as the automaton does.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one."""
import os, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import Base, OPEN  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C17 = CLOUD / "C17_reader_sources_2026-10-14.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql", C17, C17]
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest", "readers"]
U1 = "11111111-1111-1111-1111-111111111111"


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class ReaderSources(Base):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        for f in FILES:
            cls.pg.execute(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        super().setUp()
        self.pg.execute("TRUNCATE %s" % ", ".join("corpus." + t for t in TABLES))
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        sink = cs.PgSink(DSN)
        OPEN.append(sink.con)
        s = self.sync(sink=sink)
        self.assertEqual(s["verified"]["groups_different"], 0)
        x = self.pg.execute
        x("UPDATE corpus.passages SET ocr_engine = 'gretil-bori-etext' WHERE doc_code = 'markandeya_purana' AND page_no = 1")
        x("UPDATE corpus.passages SET ocr_engine = 'tesseract' WHERE doc_code = 'markandeya_purana' AND page_no = 2 "
          "AND idx < 3")
        x("UPDATE corpus.passages SET retired_at = now() WHERE doc_code = 'markandeya_purana' AND page_no = 3 AND idx = 3")

    def call(self, sql, args=(), role="authenticated", uid=U1):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def test_a_signed_in_reader_gets_each_page_and_its_engines(self):
        rows = self.call("SELECT page_no, ocr_engine, passages FROM public.corpus_reader_sources(%s)",
                         ("markandeya_purana",))
        self.assertEqual(rows, [(1, "gretil-bori-etext", 3), (2, "tesseract", 2), (2, None, 1), (3, None, 2)],
                         "the most passages first on a page; the retired one left out")
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_sources(%s)", ("no_such_text",)), [])

    def test_who_may_call_it(self):
        r = self.call("SELECT * FROM public.corpus_reader_sources('markandeya_purana')", role="anon", uid=None)
        self.assertIsInstance(r, str); self.assertIn("permission denied", r)
        r = self.call("SELECT * FROM public.corpus_reader_sources('markandeya_purana')", uid=None)
        self.assertIn("signed-in readers only", r)
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'readers'")
        r = self.call("SELECT * FROM public.corpus_reader_sources('markandeya_purana')")
        self.assertIn("signed-in readers only", r, "not on the reader list")
        priv = self.pg.execute("SELECT has_function_privilege('anon', p.oid, 'EXECUTE'), "
                               "has_function_privilege('authenticated', p.oid, 'EXECUTE'), p.prosecdef, p.proconfig "
                               "FROM pg_proc p WHERE p.proname = 'corpus_reader_sources'").fetchall()
        self.assertEqual(priv, [(False, True, True, ['search_path=""'])])


if __name__ == "__main__":
    unittest.main()
