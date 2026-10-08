# -*- coding: ascii -*-
"""READER_NAV_2026_10_08 against a real PostgreSQL: corpus_reader_outline() (docs/cloud/C5b), the
contents of the corpus reader. Applies the Supabase stand-ins, C4, C4b, C5 and C5b (C5b twice),
writes passages straight into corpus.passages, then calls the function as anon, as a signed-in
reader and with the mode narrowed.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corpus_reader_nav_pg_2026_10_08
"""
import os, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
         CLOUD / "C5b_corpus_reader_outline_2026-10-08.sql", CLOUD / "C5b_corpus_reader_outline_2026-10-08.sql"]
U1 = "11111111-1111-1111-1111-111111111111"


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Outline(unittest.TestCase):
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
        self.pg.execute("TRUNCATE corpus.passage_vectors, corpus.mentions, corpus.translations, corpus.stories, "
                        "corpus.stages, corpus.passages, corpus.entities, corpus.docs, corpus.row_index, "
                        "corpus.group_digest, corpus.readers")
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        self.pg.execute("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('nir', 'Nirukta', 'x')")
        # 120 passages: scan pages 1..24, five to a page. Colophons at ord 30 (translated), 51 (not).
        rows = []
        for n in range(120):
            page, idx = n // 5 + 1, n % 5 + 1
            ord_ = n + 1
            tt = "colophon" if ord_ in (30, 51) else ("noise" if ord_ == 7 else "mula")
            tr = "Thus ends the first chapter." if ord_ == 30 else ("" if ord_ == 51 else "verse %d" % ord_)
            rows.append(("nir", page, idx, "text %d" % ord_, tr, tt))
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.passages (doc_code, page_no, idx, text, translation, text_type, row_hash) "
                          "VALUES (%s, %s, %s, %s, %s, %s, 'x')", rows)
        # a retired passage in the middle never counts
        self.pg.execute("INSERT INTO corpus.passages (doc_code, page_no, idx, text, row_hash, retired_at) "
                        "VALUES ('nir', 3, 99, 'gone', 'x', now())")

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

    def test_anon_is_refused(self):
        r = self.call("SELECT * FROM public.corpus_reader_outline('nir')", role="anon", uid=None)
        self.assertIn("permission denied", r)
        r = self.call("SELECT * FROM public.corpus_reader_outline('nir')", uid=None)
        self.assertIn("signed-in readers only", r)

    def test_pages_and_colophons_in_reading_order(self):
        r = self.call("SELECT kind, ord, reader_page, page_no, idx, last_page_no, label "
                      "FROM public.corpus_reader_outline('nir')")
        self.assertNotIsInstance(r, str, r)
        pages = [x for x in r if x[0] == "page"]
        self.assertEqual([(x[1], x[2], x[3], x[4], x[5]) for x in pages],
                         [(1, 1, 1, 1, 10), (51, 2, 11, 1, 20), (101, 3, 21, 1, 24)])
        cols = [x for x in r if x[0] == "colophon"]
        self.assertEqual([(x[1], x[2], x[3], x[4]) for x in cols], [(30, 1, 6, 5), (51, 2, 11, 1)])
        self.assertEqual(cols[0][6], "Thus ends the first chapter.")
        self.assertEqual(cols[1][6], "text 51")                       # not translated: its Sanskrit
        self.assertEqual([x[1] for x in r], sorted(x[1] for x in r))  # reading order
        i = [x[:2] for x in r].index(("page", 51))
        self.assertEqual(r[i + 1][:2], ("colophon", 51))              # the page row first

    def test_page_size_is_clamped(self):
        r = self.call("SELECT ord FROM public.corpus_reader_outline('nir', 1) WHERE kind = 'page'")
        self.assertEqual([x[0] for x in r], list(range(1, 121, 10)))     # at least 10
        r = self.call("SELECT ord FROM public.corpus_reader_outline('nir', 1000) WHERE kind = 'page'")
        self.assertEqual([x[0] for x in r], [1, 101])                    # at most 100

    def test_unknown_document_is_empty_and_mode_is_respected(self):
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_outline('nope')"), [])
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corpus_reader_outline('nir')"))

    def test_a_large_document_answers_quickly(self):
        rows = [("big", n // 60 + 1, n % 60 + 1, "t", "tr", "colophon" if n % 700 == 699 else "mula")
                for n in range(21128)]
        self.pg.execute("INSERT INTO corpus.docs (doc_code, row_hash) VALUES ('big', 'x')")
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.passages (doc_code, page_no, idx, text, translation, text_type, row_hash) "
                          "VALUES (%s, %s, %s, %s, %s, %s, 'x')", rows)
        self.pg.execute("ANALYZE corpus.passages")
        t0 = time.perf_counter()
        r = self.call("SELECT kind FROM public.corpus_reader_outline('big')")
        took = time.perf_counter() - t0
        self.assertEqual(sum(1 for x in r if x[0] == "page"), 423)
        self.assertEqual(sum(1 for x in r if x[0] == "colophon"), 30)
        self.assertLess(took, 1.0, "outline took %.3f s" % took)
        print("\n  outline of 21,128 passages: %.0f ms" % (took * 1000))


if __name__ == "__main__":
    unittest.main()
