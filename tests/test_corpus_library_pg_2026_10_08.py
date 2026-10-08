# -*- coding: ascii -*-
"""CORPUS_LIBRARY_C6_2026_10_08 against a real PostgreSQL: the five library functions of
docs/cloud/C6 (progress, stories, names, one name, the names of a reader page). Applies the
Supabase stand-ins, C4, C4b, C5, C5b and C6 (C6 twice), writes rows straight into the mirror
tables, then calls the functions as anon, as a signed-in reader and as an admin.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corpus_library_pg_2026_10_08
"""
import os, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
         CLOUD / "C5b_corpus_reader_outline_2026-10-08.sql",
         CLOUD / "C6_corpus_library_2026-10-08.sql", CLOUD / "C6_corpus_library_2026-10-08.sql"]
U1 = "11111111-1111-1111-1111-111111111111"
ADMIN = "22222222-2222-2222-2222-222222222222"
FIVE = ["SELECT * FROM public.corpus_reader_progress()",
        "SELECT * FROM public.corpus_reader_stories()",
        "SELECT * FROM public.corpus_reader_names()",
        "SELECT * FROM public.corpus_reader_name('Garuda')",
        "SELECT * FROM public.corpus_reader_page_names('mark')"]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Library(unittest.TestCase):
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
        x = self.pg.execute
        x("TRUNCATE corpus.passage_vectors, corpus.mentions, corpus.translations, corpus.stories, corpus.stages, "
          "corpus.passages, corpus.entities, corpus.docs, corpus.row_index, corpus.group_digest, corpus.readers")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("INSERT INTO public.user_roles VALUES (%s, 'admin') ON CONFLICT DO NOTHING", (ADMIN,))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('mark', 'Markandeya', 'x'), ('nir', NULL, 'x')")
        x("INSERT INTO corpus.docs (doc_code, title, row_hash, retired_at) VALUES ('gone', 'Gone', 'x', now())")
        rows = [("mark", n // 10 + 1, n % 10 + 1, "t%d" % n, "iast %d" % n, "Verse %d about things." % n) for n in range(120)]
        rows += [("nir", 1, i, "n%d" % i, "niast %d" % i, "" if i == 2 else "Nir %d" % i) for i in range(1, 6)]
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.passages (doc_code, page_no, idx, text, iast, translation, row_hash) "
                          "VALUES (%s, %s, %s, %s, %s, %s, 'x')", rows)
        x("INSERT INTO corpus.entities (canonical, kind, notes, variants, row_hash) VALUES "
          "('Garuda', 'deity', 'the eagle', ARRAY['Garutman','Suparna'], 'x'), "
          "('Ganga', 'river', NULL, ARRAY['Bhagirathi'], 'x'), "
          "('Rama', 'person', NULL, NULL, 'x'), ('100%', 'other', NULL, NULL, 'x')")
        x("INSERT INTO corpus.entities (canonical, kind, row_hash, retired_at) VALUES ('Old', 'person', 'x', now())")
        ms = [("mark", 1, 2, "Garuda", "garuDa"), ("mark", 6, 1, "Garuda", "Garutman"), ("mark", 6, 1, "Ganga", "ganga"),
              ("mark", 7, 3, "Garuda", "suparna"), ("nir", 1, 2, "Garuda", "garuda"), ("nir", 1, 3, "Rama", "rama")]
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, surface, row_hash) "
                          "VALUES (%s, %s, %s, %s, %s, 'x')", ms)
        x("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, surface, row_hash, retired_at) "
          "VALUES ('mark', 2, 2, 'Rama', 'r', 'x', now())")
        st = [("mark", 1, "approved", "The bird", 1, 2), ("mark", 2, "draft", "The king", 6, 1),
              ("mark", 3, "candidate", "An episode", 7, 3), ("mark", 4, "retired", "Old one", 2, 2),
              ("nir", 5, "rejected", "No", 1, 1), ("gone", 6, "approved", "Of a retired text", 1, 1)]
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.stories (doc_code, story_id, status, title, from_page, from_idx, "
                          "story_en, story_hi, why, cites, verify, row_hash) VALUES "
                          "(%s, %s, %s, %s, %s, %s, 'Long English', 'Long Hindi', 'because', '[\"1.2\"]', "
                          "'{\"ok\": true}', 'x')", st)
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, row_hash, retired_at) "
          "VALUES ('mark', 9, 'approved', 'retired row', 'x', now())")
        sg = [("mark", "translate_en", "done", "97% translated"), ("mark", "ingest", "done", "120 passages"),
              ("mark", "book", "pending", "no Booksmith build"), ("mark", "retired", "done", "x"),
              ("mark", "zzz_custom", "pending", "later"), ("gone", "ingest", "done", "x")]
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.stages (doc_code, stage, status, reason, row_hash) "
                          "VALUES (%s, %s, %s, %s, 'x')", sg)

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

    def test_anon_and_no_subject_are_refused_everywhere(self):
        for sql in FIVE:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
                self.assertIn("signed-in readers only", self.call(sql, uid=None))

    def test_progress_in_the_desks_order(self):
        r = self.call("SELECT doc_code, stage, status, reason FROM public.corpus_reader_progress()")
        self.assertEqual([x[1] for x in r], ["ingest", "translate_en", "book", "zzz_custom"])
        self.assertTrue(all(x[0] == "mark" for x in r))           # the retired text is left out
        self.assertEqual(r[2][3], "no Booksmith build")

    def test_stories_approved_for_readers_all_but_retired_for_admins(self):
        r = self.call("SELECT story_id, status, story_en, why, cites, from_ord FROM public.corpus_reader_stories()")
        self.assertEqual([(x[0], x[1]) for x in r], [(1, "approved")])
        self.assertEqual(r[0][2:5], (None, None, None))            # lists carry no long texts
        self.assertEqual(r[0][5], 2)                               # page 1 idx 2 is the 2nd passage
        r = self.call("SELECT story_id, status FROM public.corpus_reader_stories()", uid=ADMIN)
        self.assertEqual(r, [(1, "approved"), (2, "draft"), (3, "candidate")])
        r = self.call("SELECT story_id, story_en, story_hi, why, cites, verify, from_ord "
                      "FROM public.corpus_reader_stories('mark', true)", uid=ADMIN)
        self.assertEqual(r[1], (2, "Long English", "Long Hindi", "because", '["1.2"]', '{"ok": true}', 51))
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_stories('nir', true)", uid=ADMIN), [])

    def test_names_index_counts_variants_kinds_and_paging(self):
        r = self.call("SELECT canonical, kind, mentions, texts, total FROM public.corpus_reader_names()")
        self.assertEqual(r[0], ("Garuda", "deity", 4, 2, 4))       # the retired name and mention never count
        self.assertEqual({x[0] for x in r}, {"Garuda", "Ganga", "Rama", "100%"})
        self.assertEqual([x[0] for x in self.call("SELECT canonical FROM public.corpus_reader_names('suparn')")], ["Garuda"])
        self.assertEqual([x[0] for x in self.call("SELECT canonical FROM public.corpus_reader_names(NULL, 'river')")], ["Ganga"])
        self.assertEqual([x[0] for x in self.call("SELECT canonical FROM public.corpus_reader_names('Ga', NULL, 60, 0, true)")], [])
        self.assertEqual([x[0] for x in self.call("SELECT canonical FROM public.corpus_reader_names('Ganga', NULL, 60, 0, true)")], ["Ganga"])
        self.assertEqual([x[0] for x in self.call("SELECT canonical FROM public.corpus_reader_names(%s)", ("%",))], ["100%"])
        r = self.call("SELECT canonical, total FROM public.corpus_reader_names(NULL, NULL, 2, 2)")
        self.assertEqual(len(r), 2); self.assertEqual(r[0][1], 4)
        self.assertIn("at most 100", self.call("SELECT * FROM public.corpus_reader_names(%s)", ("x" * 101,)))

    def test_one_name_in_reading_order_with_positions_and_snippets(self):
        r = self.call("SELECT doc_code, title, page_no, idx, ord, surface, snippet, total "
                      "FROM public.corpus_reader_name('Garuda')")
        self.assertEqual([(x[0], x[2], x[3], x[4]) for x in r],
                         [("mark", 1, 2, 2), ("mark", 6, 1, 51), ("mark", 7, 3, 63), ("nir", 1, 2, 2)])
        self.assertEqual(r[0][1], "Markandeya"); self.assertEqual(r[3][1], "nir")
        self.assertEqual(r[0][6], "Verse 1 about things.")
        self.assertEqual(r[3][6], "niast 2")                       # no English: the IAST
        self.assertTrue(all(x[7] == 4 for x in r))
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_name('Garuda', 2, 2)")), 2)

    def test_the_names_of_one_reader_page(self):
        r = self.call("SELECT page_no, idx, canonical, kind FROM public.corpus_reader_page_names('mark', 50, 50)")
        self.assertEqual(r, [(6, 1, "Ganga", "river"), (6, 1, "Garuda", "deity"), (7, 3, "Garuda", "deity")])
        r = self.call("SELECT page_no, idx, canonical FROM public.corpus_reader_page_names('mark', 0, 50)")
        self.assertEqual(r, [(1, 2, "Garuda")])                    # the retired Rama mention is not shown

    def test_large_counts_answer_quickly(self):
        ents = [("E%05d" % i, "person", "x") for i in range(8000)]
        with self.pg.cursor() as c:
            c.executemany("INSERT INTO corpus.entities (canonical, kind, row_hash) VALUES (%s, %s, %s)", ents)
            c.executemany("INSERT INTO corpus.passages (doc_code, page_no, idx, text, translation, row_hash) "
                          "VALUES ('mark', %s, %s, 't', 'tr', 'x')", [(p, i) for p in range(100, 420) for i in range(1, 101)])
            c.executemany("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, row_hash) "
                          "VALUES ('mark', %s, %s, %s, 'x')",
                          [(100 + n // 100, n % 100 + 1, "E%05d" % (n % 8000)) for n in range(32000)])
        self.pg.execute("ANALYZE corpus.mentions"); self.pg.execute("ANALYZE corpus.entities")
        t0 = time.perf_counter(); r = self.call("SELECT * FROM public.corpus_reader_names()"); t1 = time.perf_counter()
        self.assertEqual(len(r), 60)
        r2 = self.call("SELECT * FROM public.corpus_reader_name('E00007')"); t2 = time.perf_counter()
        self.assertEqual(len(r2), 4)
        r3 = self.call("SELECT * FROM public.corpus_reader_page_names('mark', 5000, 50)"); t3 = time.perf_counter()
        self.assertGreater(len(r3), 0)
        self.assertLess(t1 - t0, 1.0); self.assertLess(t2 - t1, 0.5); self.assertLess(t3 - t2, 0.5)
        print("\n  names %.0f ms, one name %.0f ms, page names %.0f ms" % ((t1 - t0) * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3))


if __name__ == "__main__":
    unittest.main()
