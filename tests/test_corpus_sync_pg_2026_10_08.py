# -*- coding: ascii -*-
"""CORPUS_MIRROR_C4_2026_10_08 against a real PostgreSQL + pgvector: applies
docs/cloud/C4_corpus_mirror_2026-10-08.sql (twice), then syncs the fixture of
tests/test_corpus_sync_2026_10_08.py with PgSink and checks that the SQL functions agree with
the Python side byte for byte (digests), that a second run sends nothing, that changes and
removals travel, and that anon / authenticated are refused everywhere.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own (the corpus schema in it is
emptied), e.g.  set CORPUS_TEST_DSN=postgresql://postgres:pw@localhost:5432/c4test
Needs psycopg (pip install psycopg[binary]). Never points at the live database."""
import os, sqlite3, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import Base, OPEN, GOLDEN_DIGEST  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
SQL = REPO / "docs" / "cloud" / "C4_corpus_mirror_2026-10-08.sql"
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs"]


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class PgMirror(Base):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.pg = psycopg.connect(DSN, autocommit=True)
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg.execute(SQL.read_text(encoding="utf-8"))
        cls.pg.execute(SQL.read_text(encoding="utf-8"))      # twice: the file is re-runnable

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        super().setUp()
        self.pg.execute("TRUNCATE %s" % ", ".join("corpus." + t for t in TABLES))
        self.sink = cs.PgSink(DSN)
        OPEN.append(self.sink.con)

    def q(self, sql, *args):
        return self.pg.execute(sql, args).fetchall()

    def test_full_sync_then_nothing(self):
        s = self.sync(sink=self.sink)
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["verified"]["groups_different"], 0, s["verified"])
        self.assertEqual(self.q("SELECT count(*) FROM corpus.passages")[0][0], 15)
        self.assertEqual(self.q("SELECT count(*) FROM corpus.passage_vectors")[0][0], 10)
        self.assertEqual(self.q("SELECT count(*) FROM corpus.translations WHERE lang='hi'")[0][0], 10)
        self.assertEqual(self.q("SELECT variants FROM corpus.entities WHERE canonical='Indra'")[0][0],
                         ["Indrah", "Sakra"])
        s2 = self.sync(sink=self.sink)
        self.assertEqual(sum(x["upsert"] for x in s2["tables"].values()), 0)
        self.assertEqual(s2["verified"]["groups_different"], 0)
        self.assertEqual(self.q("SELECT count(*) FROM corpus.sync_runs WHERE finished_at IS NOT NULL")[0][0], 2)

    def test_digest_is_the_same_in_sql(self):
        v = self.q("SELECT md5(string_agg(k || ' ' || h, E'\\n' ORDER BY k COLLATE \"C\")) FROM (VALUES "
                   "('10|2','aaa'),('1|20','bbb'),('9|1','ccc'),(U&'\\015Aiva','ddd'),('agni','eee'),"
                   "('Agni','fff'),(U&'\\1E5B\\1E63i','ggg')) v(k, h)")[0][0]
        self.assertEqual(v, GOLDEN_DIGEST)

    def test_change_and_removal_travel(self):
        self.sync(sink=self.sink)
        con = self.rw()
        pid = con.execute("SELECT id FROM passages WHERE doc_id=1 AND page_no=3 AND idx=2").fetchone()[0]
        con.execute("UPDATE passages SET translation='changed' WHERE id=?", (pid,))
        con.execute("DELETE FROM passages WHERE doc_id=2 AND page_no=2 AND idx=3")
        con.commit()
        s = self.sync(sink=self.sink)
        self.assertEqual(s["tables"]["passages"]["changed"], 1)
        self.assertEqual(s["tables"]["passages"]["retired"], 1)
        self.assertEqual(s["verified"]["groups_different"], 0)
        self.assertEqual(self.q("SELECT translation FROM corpus.passages WHERE doc_code='markandeya_purana' "
                                "AND page_no=3 AND idx=2")[0][0], "changed")
        self.assertEqual(self.q("SELECT retired_at IS NOT NULL FROM corpus.passages WHERE "
                                "doc_code='AphorismsOfSandilya' AND page_no=2 AND idx=3")[0][0], True)

    def test_stray_values_do_not_block_a_batch(self):
        con = self.rw()
        con.execute("UPDATE passages SET padas='four', quality_score='0.7', page_no=page_no WHERE doc_id=1 AND idx=1")
        con.commit()
        s = self.sync(sink=self.sink)
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["verified"]["groups_different"], 0)
        self.assertEqual(self.q("SELECT count(*) FROM corpus.passages WHERE padas IS NULL AND quality_score = 0.7")[0][0], 3)

    def test_search_and_vectors_answer(self):
        self.sync(sink=self.sink)
        hits = self.q("SELECT doc_code, page_no, idx FROM corpus.search('passage', 5)")
        self.assertEqual(len(hits), 5)
        # a stored vector finds itself first, at similarity 1
        r = self.q("SELECT m.doc_code, m.page_no, m.idx, round(m.similarity::numeric, 3) FROM corpus.passage_vectors v, "
                   "LATERAL corpus.match_passages(v.embedding, 1) m WHERE v.doc_code='markandeya_purana' "
                   "AND v.page_no=2 AND v.idx=1")
        self.assertEqual(r[0][:3], ("markandeya_purana", 2, 1))
        self.assertEqual(float(r[0][3]), 1.0)
        n = self.q("SELECT vector_dims(embedding::vector) FROM corpus.passage_vectors LIMIT 1")[0][0]
        self.assertEqual(n, 1536)

    def test_site_roles_are_refused(self):
        roles = [r[0] for r in self.q("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")]
        if not roles:
            self.skipTest("no anon/authenticated roles in this database")
        for role in roles:
            for sql in ("SELECT count(*) FROM corpus.passages", "SELECT public.corpus_manifest()",
                        "SELECT public.corpus_ingest('docs', '[]'::jsonb)", "SELECT * FROM corpus.v_docs"):
                with self.subTest(role=role, sql=sql):
                    with self.pg.transaction():
                        self.pg.execute("SET LOCAL ROLE %s" % role)
                        with self.assertRaises(Exception) as e:
                            with self.pg.transaction():
                                self.pg.execute(sql)
                        self.assertIn("permission denied", str(e.exception))

    def test_bad_input_is_refused(self):
        import psycopg
        for sql in ("SELECT public.corpus_ingest('nope', '[]'::jsonb)",
                    "SELECT public.corpus_ingest('docs', '{}'::jsonb)",
                    "SELECT public.corpus_ingest('docs', '[{\"doc_code\": \"x\"}]'::jsonb)",
                    "SELECT public.corpus_keys('nope', '*')"):
            with self.subTest(sql=sql):
                with self.assertRaises(psycopg.Error):
                    self.pg.execute(sql)


if __name__ == "__main__":
    unittest.main()
