# -*- coding: ascii -*-
"""C22_SCHOLAR_SITE_2026_10_25 against a real PostgreSQL: public.corpus_reader_scholar_docs() lists every live text
with a scholarly English (its counts as C18 counts them, its first such verse and that verse's place in the reader),
and public.corpus_reader_scholar_prose(p_doc, p_after_page, p_after_idx, p_limit) gives one text's scholarly rows in
reading order, page after page by keyset, with what the site needs to group chapters (reference, chapter, a colophon);
signed-in readers only (the C5 gate). Applies the Supabase stand-ins, C4, C4b, C5, C18 and C22 (C22 twice), fills
the mirror from the corpus_sync fixture and test_scholar_mirror's scholarly English with PgSink.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one."""
import json, os, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import Base, OPEN  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C18 = CLOUD / "C18_reader_scholar_2026-10-18.sql"
C22 = CLOUD / "C22_scholar_site_2026-10-25.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql", C18, C22, C22]
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest", "readers"]
U1 = "11111111-1111-1111-1111-111111111111"
MIRROR = b"SCHOLAR_MIRROR_2026_10_18" in (REPO / "scripts" / "corpus_sync.py").read_bytes()
DOC = "markandeya_purana"
ITI = "\u0907\u0924\u093f"


@unittest.skipUnless(DSN and MIRROR and C18.exists() and C22.exists(),
                     "CORPUS_TEST_DSN is not set (or SCHOLAR_MIRROR / C18 / C22 not here)")
class ScholarSite(Base):
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
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def docs(self):
        return self.call("SELECT doc_code, passages, verses, flagged, accepted, round(fidelity::numeric, 2), first_page, "
                         "first_idx, first_ord, last_made FROM public.corpus_reader_scholar_docs()")

    def test_every_text_with_a_scholarly_english(self):
        self.assertEqual(self.docs(), [(DOC, 9, 4, 1, 1, 3.75, 1, 1, 1, "2026-10-18T11:00:00+00:00")],
                         "4 verses with an English (1.1, 1.2, 1.3, 2.1); 1.2 flagged; 1.3 read by a person; the "
                         "rejected and the stale left out; a text without any is not listed")
        n = self.call("SELECT * FROM public.corpus_reader_scholar_count(%s)", (DOC,))
        self.assertEqual(n, [(4, 1)], "the same counts as C18's")

    def test_the_first_verse_and_its_place_in_the_reader(self):
        self.pg.execute("UPDATE corpus.translations SET retired_at = now() WHERE doc_code = %s AND page_no = 1 "
                        "AND lang IN ('en-x-scholar', 'en-x-scholar-meta')", (DOC,))
        d = self.docs()
        self.assertEqual([(r[2], r[3], r[4], r[6], r[7], r[8]) for r in d], [(1, 0, 0, 2, 1, 4)],
                         "only the sentence of page 2 is left: its first verse is the reader's fourth passage")

    def test_a_retired_passage_and_a_retired_text(self):
        self.pg.execute("UPDATE corpus.passages SET retired_at = now() WHERE doc_code = %s AND page_no = 1 AND idx = 2",
                        (DOC,))
        self.assertEqual([(r[2], r[3]) for r in self.docs()], [(3, 0)])
        rows = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar_prose(%s)", (DOC,))
        self.assertNotIn((1, 2), rows)
        self.pg.execute("UPDATE corpus.docs SET retired_at = now() WHERE doc_code = %s", (DOC,))
        self.assertEqual(self.docs(), [], "a retired text is not listed")

    def test_the_prose_in_reading_order(self):
        rows = self.call("SELECT page_no, idx, verse_ref, chapter, has_sanskrit, colophon, scholar, meta, made_at "
                         "FROM public.corpus_reader_scholar_prose(%s)", (DOC,))
        self.assertEqual([(r[0], r[1]) for r in rows], [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)])
        r11 = rows[0]
        self.assertEqual((r11[2], r11[4], r11[5], r11[6], r11[8]),
                         ("1.1", True, False, "The first verse names *Manu*. //", "2026-10-18T10:00:00+00:00"))
        self.assertEqual(json.loads(r11[7])["notes"][0]["note"], "The progenitor.")
        r21, r22 = rows[3], rows[4]
        self.assertEqual(r21[6], "The sentence over two verses.")
        self.assertEqual(json.loads(r21[7])["range"], "2.1\u20132")
        self.assertIsNone(r22[6], "a sentence's later verse has no English of its own")
        self.assertEqual(json.loads(r22[7])["with"], "2.1\u20132")
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar_prose(%s)", ("AphorismsOfSandilya",)), [])
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar_prose(%s)", ("no_such_text",)), [])

    def test_page_after_page_by_keyset(self):
        a = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar_prose(%s, NULL, NULL, 2)", (DOC,))
        b = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar_prose(%s, 1, 2, 2)", (DOC,))
        c = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar_prose(%s, 2, 1, 2)", (DOC,))
        d = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar_prose(%s, 2, 2, 2)", (DOC,))
        self.assertEqual((a, b, c, d), ([(1, 1), (1, 2)], [(1, 3), (2, 1)], [(2, 2)], []))
        self.assertEqual(self.call("SELECT page_no FROM public.corpus_reader_scholar_prose(%s, 1, NULL, 9)", (DOC,)),
                         [(1,), (1,), (1,), (2,), (2,)], "a page alone means from that page's start")
        self.assertEqual(len(self.call("SELECT 1 FROM public.corpus_reader_scholar_prose(%s, NULL, NULL, 0)", (DOC,))), 1,
                         "at least one row a call")
        big = self.call("SELECT 1 FROM public.corpus_reader_scholar_prose(%s, NULL, NULL, 100000)", (DOC,))
        self.assertEqual(len(big), 5)

    def test_a_colophon_is_marked(self):
        self.pg.execute("UPDATE corpus.passages SET text = %s WHERE doc_code = %s AND page_no = 1 AND idx = 3",
                        (ITI + " \u0936\u094d\u0930\u0940", DOC))
        rows = self.call("SELECT page_no, idx, colophon FROM public.corpus_reader_scholar_prose(%s)", (DOC,))
        self.assertEqual([r[2] for r in rows], [False, False, True, False, False])

    def test_the_reader_and_the_hindi_are_as_before(self):
        rows = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar(%s, 0, 50)", (DOC,))
        self.assertEqual(rows, [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)])
        n = self.call("SELECT hindi FROM public.corpus_reader_docs(%s)", (DOC,))
        self.assertEqual(n, [(6,)])
        ix = self.pg.execute("SELECT indexdef FROM pg_indexes WHERE schemaname = 'corpus' AND indexname = "
                             "'corpus_translations_scholar'").fetchall()
        self.assertEqual(len(ix), 1)
        self.assertIn("en-x-scholar-meta", ix[0][0])

    def test_who_may_call_them(self):
        for fn in ("public.corpus_reader_scholar_docs()", "public.corpus_reader_scholar_prose('%s')" % DOC):
            r = self.call("SELECT * FROM %s" % fn, role="anon", uid=None)
            self.assertIsInstance(r, str)
            self.assertIn("permission denied", r)
            r = self.call("SELECT * FROM %s" % fn, uid=None)
            self.assertIn("signed-in readers only", r)
        priv = self.pg.execute("SELECT p.proname, has_function_privilege('anon', p.oid, 'EXECUTE'), "
                               "has_function_privilege('authenticated', p.oid, 'EXECUTE'), p.prosecdef, p.proconfig "
                               "FROM pg_proc p WHERE p.proname IN ('corpus_reader_scholar_docs', "
                               "'corpus_reader_scholar_prose') ORDER BY 1").fetchall()
        self.assertEqual(priv, [("corpus_reader_scholar_docs", False, True, True, ['search_path=""']),
                                ("corpus_reader_scholar_prose", False, True, True, ['search_path=""'])])


if __name__ == "__main__":
    unittest.main()
