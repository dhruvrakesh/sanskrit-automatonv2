# -*- coding: ascii -*-
"""CORPUS_READER_C5_2026_10_08 against a real PostgreSQL + pgvector: who may read the working corpus
through the six reader functions, and what they return. Applies the Supabase stand-ins
(tests/supabase_stubs_2026_10_08.sql), C4, C4b and C5 (C5 twice), fills the mirror from the fixture
of tests/test_corpus_sync_2026_10_08.py with PgSink, then calls the functions as anon, as a
signed-in user (request.jwt.claim.sub, as PostgREST sets it) and as an admin.

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
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
         CLOUD / "C5_corpus_reader_2026-10-08.sql"]
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest", "readers"]
U1 = "11111111-1111-1111-1111-111111111111"      # a signed-in user
ADMIN = "22222222-2222-2222-2222-222222222222"


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class ReaderAccess(Base):
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
        self.pg.execute("INSERT INTO public.user_roles VALUES (%s, 'admin') ON CONFLICT DO NOTHING", (ADMIN,))
        self.pg.execute("INSERT INTO public.srangam_texts (doc_code, published) VALUES ('markandeya_purana', true) "
                        "ON CONFLICT (doc_code) DO UPDATE SET published = true")
        sink = cs.PgSink(DSN)
        OPEN.append(sink.con)
        s = self.sync(sink=sink)
        self.assertEqual(s["verified"]["groups_different"], 0)

    def call(self, sql, args=(), role="authenticated", uid=U1):
        """Run one statement as `role` with the JWT subject `uid` (None = no subject); rows or an error text."""
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def test_anon_is_refused_everywhere(self):
        for sql in ("SELECT public.corpus_reader_allowed()", "SELECT * FROM public.corpus_reader_docs()",
                    "SELECT * FROM public.corpus_reader_page('markandeya_purana', 0, 10)",
                    "SELECT * FROM public.corpus_reader_search('passage', 5)",
                    "SELECT * FROM corpus.passages"):
            with self.subTest(sql=sql):
                r = self.call(sql, role="anon", uid=None)
                self.assertIsInstance(r, str)
                self.assertIn("permission denied", r)

    def test_signed_in_without_a_subject_is_refused(self):
        r = self.call("SELECT * FROM public.corpus_reader_docs()", uid=None)
        self.assertIn("signed-in readers only", r)

    def test_a_signed_in_reader_sees_documents_pages_words_and_neighbours(self):
        docs = self.call("SELECT doc_code, passages, english, hindi, vectors, stories, published "
                         "FROM public.corpus_reader_docs()")
        self.assertEqual(docs, [("markandeya_purana", 9, 6, 6, 6, 1, True), ("AphorismsOfSandilya", 6, 4, 4, 4, 0, False)])
        page = self.call("SELECT ord, page_no, idx, translation, hindi FROM public.corpus_reader_page('markandeya_purana', 3, 2)")
        self.assertEqual([r[:3] for r in page], [(4, 2, 1), (5, 2, 2)])
        self.assertEqual(page[0][3], "the passage 1.2.1")
        self.assertTrue(page[0][4])
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_page('markandeya_purana', 0, 500)")), 9)
        hits = self.call("SELECT doc_code, page_no, idx, ord, snippet FROM public.corpus_reader_search('passage', 50, 'AphorismsOfSandilya')")
        self.assertEqual(len(hits), 4)
        self.assertTrue(all("[[" in h[4] for h in hits))
        self.assertEqual(hits[0][3], 1)
        near = self.call("SELECT doc_code, page_no, idx, ord, similarity FROM public.corpus_reader_similar('markandeya_purana', 2, 1, 3)")
        self.assertEqual(len(near), 3)
        self.assertNotIn(("markandeya_purana", 2, 1), [n[:3] for n in near])
        self.assertTrue(near[0][4] >= near[1][4] >= near[2][4])
        # a vector as the question: its own passage first, at similarity 1
        own = self.call("SELECT r.doc_code, r.page_no, r.idx, round(r.similarity::numeric, 3) FROM "
                        "(SELECT embedding FROM corpus.passage_vectors WHERE doc_code='markandeya_purana' AND page_no=2 AND idx=1) q, "
                        "LATERAL public.corpus_reader_match(q.embedding, 3, NULL) r", role="postgres", uid=U1)
        self.assertEqual(own[0][:3], ("markandeya_purana", 2, 1))
        self.assertEqual(float(own[0][3]), 1.0)

    def test_the_reader_never_reaches_the_tables_directly(self):
        for sql in ("SELECT count(*) FROM corpus.passages", "SELECT * FROM corpus.reader_access",
                    "SELECT public.corpus_manifest()", "SELECT public.corpus_ingest('docs', '[]'::jsonb)",
                    "UPDATE corpus.reader_access SET mode = 'signed_in'"):
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql))

    def test_modes_readers_and_admins(self):
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'readers'")
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corpus_reader_docs()"))
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_docs()", uid=ADMIN)), 2)
        self.pg.execute("INSERT INTO corpus.readers (user_id, note) VALUES (%s, 'test')", (U1,))
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_docs()")), 2)
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corpus_reader_docs()"))
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_docs()", uid=ADMIN)), 2)
        self.pg.execute("DELETE FROM corpus.reader_access")      # no setting row: admins only
        self.assertEqual(self.call("SELECT public.corpus_reader_allowed()"), [(False,)])
        self.assertEqual(self.call("SELECT public.corpus_reader_allowed()", uid=ADMIN), [(True,)])
        self.pg.execute("INSERT INTO corpus.reader_access (id, mode) VALUES (true, 'signed_in')")

    def test_bad_search_input_is_refused(self):
        self.assertIn("2 to 200 characters", self.call("SELECT * FROM public.corpus_reader_search('a', 5)"))
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_similar('nope', 1, 1, 5)"), [])


if __name__ == "__main__":
    unittest.main()
