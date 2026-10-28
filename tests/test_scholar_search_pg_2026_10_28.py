# -*- coding: ascii -*-
"""C24_SCHOLAR_SEARCH_2026_10_28 against a real PostgreSQL: public.corpus_reader_scholar_search(q, k, p_doc) finds words
in the scholarly English (stemmed, and as written), live verses of live texts only, behind the readers' gate, its rows
shaped as corpus_reader_search's (the snippet's words marked [[ ]]). Applies the Supabase stand-ins, C4, C4b, C5, C18,
C22 and C24 (C24 twice), fills the mirror from the corpus_sync fixture and test_scholar_mirror's scholarly English.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one."""
import os, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import Base, OPEN  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C24 = CLOUD / "C24_scholar_search_2026-10-28.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
         CLOUD / "C18_reader_scholar_2026-10-18.sql", CLOUD / "C22_scholar_site_2026-10-25.sql", C24, C24]
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest", "readers"]
U1 = "11111111-1111-1111-1111-111111111111"
DOC = "markandeya_purana"


class TheText(unittest.TestCase):
    def test_marked_ascii_and_gated(self):
        s = C24.read_bytes()
        self.assertTrue(s.isascii())
        self.assertIn(b"C24_SCHOLAR_SEARCH_2026_10_28", s)
        self.assertIn(b"PERFORM corpus._reader_gate();", s)
        self.assertIn(b"WHERE lang = 'en-x-scholar' AND retired_at IS NULL", s, "the partial index")


@unittest.skipUnless(DSN and C24.exists(), "CORPUS_TEST_DSN is not set (a throwaway PostgreSQL)")
class ScholarSearch(Base):
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
        import test_scholar_mirror_2026_10_18 as TS
        TS.add_scholar(self.db)
        self.pg.execute("TRUNCATE %s" % ", ".join("corpus." + t for t in TABLES))
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        sink = cs.PgSink(DSN)
        OPEN.append(sink.con)
        s = self.sync(sink=sink)
        self.assertEqual(s["verified"]["groups_different"], 0, s)

    def call(self, sql, args=(), role="authenticated", uid=U1):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:  # noqa: BLE001
                return "ERROR: " + str(e).splitlines()[0]

    def search(self, q, k=20, doc=None):
        return self.call("SELECT doc_code, page_no, idx, verse_ref, ord, snippet FROM "
                         "public.corpus_reader_scholar_search(%s, %s, %s)", (q, k, doc))

    def test_a_word_of_the_scholarly_english(self):
        got = self.search("Manu")
        self.assertEqual([(r[0], r[1], r[2]) for r in got], [(DOC, 1, 1)])
        self.assertIn("[[Manu]]", got[0][5])
        self.assertEqual(got[0][3], "1.1")
        self.assertIsNotNone(got[0][4], "the verse's place in the reader")

    def test_stemmed_and_never_the_rejected_or_stale(self):
        got = self.search("verses")       # "verse" in three rows, "verses" in the sentence over two
        keys = sorted((r[1], r[2]) for r in got)
        self.assertIn((1, 2), keys)
        self.assertIn((1, 3), keys)
        self.assertNotIn((3, 1), keys, "rejected: not mirrored")
        self.assertEqual(self.search("Rejected"), [])
        self.assertEqual(self.search("Old"), [], "the older version is replaced")

    def test_one_text_and_the_limits(self):
        self.assertEqual(self.search("Manu", doc="nilamata_seg"), [])
        self.assertEqual(len(self.search("verse", k=1)), 1)
        self.assertTrue(str(self.search("x")).startswith("ERROR"), "two characters at least")

    def test_the_gate(self):
        self.assertTrue(str(self.call("SELECT * FROM public.corpus_reader_scholar_search('Manu')", role="anon",
                                      uid=None)).startswith("ERROR"))
        self.assertTrue(str(self.call("SELECT * FROM public.corpus_reader_scholar_search('Manu')",
                                      uid=None)).startswith("ERROR"))

    def test_a_retired_verse_is_not_found(self):
        self.pg.execute("UPDATE corpus.passages SET retired_at = now() WHERE doc_code = %s AND page_no = 1 AND idx = 1",
                        (DOC,))
        try:
            self.assertEqual(self.search("Manu"), [])
        finally:
            self.pg.execute("UPDATE corpus.passages SET retired_at = NULL WHERE doc_code = %s AND page_no = 1 AND idx = 1",
                            (DOC,))


if __name__ == "__main__":
    unittest.main()
