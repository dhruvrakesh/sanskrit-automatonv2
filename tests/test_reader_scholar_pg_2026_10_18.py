# -*- coding: ascii -*-
"""C18_READER_SCHOLAR_2026_10_18 against a real PostgreSQL: public.corpus_reader_scholar(p_doc, p_offset, p_limit) gives
the scholarly English (en-x-scholar, en-x-scholar-meta, sent by corpus_sync.py with SCHOLAR_MIRROR_2026_10_18) of the
same window of live passages as corpus_reader_page, and public.corpus_reader_scholar_count(p_doc) how many verses have
one and how many of those wait for a person; signed-in readers only (the C5 gate). Applies the Supabase stand-ins, C4,
C4b, C5 and C18 (C18 twice), fills the mirror from the corpus_sync fixture and test_scholar_mirror's scholarly English
with PgSink. corpus_reader_page still joins only the Hindi.

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
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql", C18, C18]
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest", "readers"]
U1 = "11111111-1111-1111-1111-111111111111"
MIRROR = b"SCHOLAR_MIRROR_2026_10_18" in (REPO / "scripts" / "corpus_sync.py").read_bytes()


@unittest.skipUnless(DSN and MIRROR and C18.exists(), "CORPUS_TEST_DSN is not set (or SCHOLAR_MIRROR / C18 not here)")
class ReaderScholar(Base):
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

    def test_a_page_of_scholarly_english(self):
        rows = self.call("SELECT page_no, idx, scholar, meta, fidelity, fluency, engine, made_at "
                         "FROM public.corpus_reader_scholar(%s, 0, 50)", ("markandeya_purana",))
        self.assertEqual([(r[0], r[1]) for r in rows], [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)],
                         "only the passages that have it; the rejected and the stale left out")
        r11 = rows[0]
        self.assertEqual((r11[2], r11[4], r11[5], r11[6], r11[7]),
                         ("The first verse names *Manu*. //", 5.0, 4.0, "anthropic:claude-sonnet-5-5",
                          "2026-10-18T10:00:00+00:00"))
        self.assertEqual(json.loads(r11[3])["notes"][0]["anchor"], "*Manu*")
        r22 = rows[4]
        self.assertIsNone(r22[2], "a sentence's later verse has no English of its own")
        self.assertEqual(json.loads(r22[3])["with"], "2.1\u20132")
        self.assertEqual(r22[7], "2026-10-18T11:00:00+00:00", "its date from the meta row")
        # the window is corpus_reader_page's: page 2 of 3 passages a page is scan page 2
        w = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar(%s, 3, 3)", ("markandeya_purana",))
        p = self.call("SELECT page_no, idx FROM public.corpus_reader_page(%s, 3, 3)", ("markandeya_purana",))
        self.assertEqual(w, [(2, 1), (2, 2)])
        self.assertEqual([x for x in p if x in w], w)
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar(%s, 0, 50)", ("AphorismsOfSandilya",)), [])

    def test_the_counts_and_a_retired_passage(self):
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar_count(%s)", ("markandeya_purana",)),
                         [(4, 1)], "four verses with an English; one flagged and not yet read (1.2)")
        self.pg.execute("UPDATE corpus.passages SET retired_at = now() WHERE doc_code = 'markandeya_purana' "
                        "AND page_no = 1 AND idx = 2")
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar_count(%s)", ("markandeya_purana",)),
                         [(3, 0)])
        rows = self.call("SELECT page_no, idx FROM public.corpus_reader_scholar(%s, 0, 50)", ("markandeya_purana",))
        self.assertNotIn((1, 2), rows)
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_scholar_count(%s)", ("no_such_text",)), [(0, 0)])

    def test_the_reader_page_still_reads_the_hindi(self):
        rows = self.call("SELECT page_no, idx, hindi FROM public.corpus_reader_page(%s, 0, 3)", ("markandeya_purana",))
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[0][2] and not rows[0][2].startswith("{"), "the Hindi, not a scholarly row")
        n = self.call("SELECT hindi FROM public.corpus_reader_docs(%s)", ("markandeya_purana",))
        self.assertEqual(n, [(6,)], "the Hindi count is unchanged by the scholarly rows")

    def test_who_may_call_them(self):
        for fn in ("public.corpus_reader_scholar('markandeya_purana', 0, 50)",
                   "public.corpus_reader_scholar_count('markandeya_purana')"):
            r = self.call("SELECT * FROM %s" % fn, role="anon", uid=None)
            self.assertIsInstance(r, str); self.assertIn("permission denied", r)
            r = self.call("SELECT * FROM %s" % fn, uid=None)
            self.assertIn("signed-in readers only", r)
        priv = self.pg.execute("SELECT p.proname, has_function_privilege('anon', p.oid, 'EXECUTE'), "
                               "has_function_privilege('authenticated', p.oid, 'EXECUTE'), p.prosecdef, p.proconfig "
                               "FROM pg_proc p WHERE p.proname IN ('corpus_reader_scholar', 'corpus_reader_scholar_count') "
                               "ORDER BY 1").fetchall()
        self.assertEqual(priv, [("corpus_reader_scholar", False, True, True, ['search_path=""']),
                                ("corpus_reader_scholar_count", False, True, True, ['search_path=""'])])


if __name__ == "__main__":
    unittest.main()
