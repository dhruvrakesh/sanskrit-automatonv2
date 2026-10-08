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
SQL_B = REPO / "docs" / "cloud" / "C4b_mirror_digests_2026-10-08.sql"
TABLES = ["sync_runs", "passage_vectors", "mentions", "translations", "stories", "stages", "passages",
          "entities", "docs", "row_index", "group_digest"]
K2 = """SELECT g.tbl, g.grp FROM corpus.group_digest g
LEFT JOIN (SELECT tbl, grp, count(*) n, sum(corpus._h64(k || ' ' || row_hash, 0)) s1,
                  sum(corpus._h64(k || ' ' || row_hash, 1)) s2 FROM corpus.row_index GROUP BY tbl, grp) r
  USING (tbl, grp)
WHERE corpus._digest(g.n, g.s1, g.s2) IS DISTINCT FROM corpus._digest(coalesce(r.n, 0), coalesce(r.s1, 0), coalesce(r.s2, 0))"""


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
        cls.pg.execute(SQL_B.read_text(encoding="utf-8"))    # C4b on top, twice as well
        cls.pg.execute(SQL_B.read_text(encoding="utf-8"))

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
        v = self.q("SELECT corpus._digest(count(*), sum(corpus._h64(k || ' ' || h, 0)), "
                   "sum(corpus._h64(k || ' ' || h, 1))) FROM (VALUES "
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

    def test_running_digests_stay_equal_to_a_fresh_sum(self):
        self.sync(sink=self.sink)
        con = self.rw()
        con.execute("UPDATE passages SET translation='again' WHERE doc_id=1 AND page_no=1 AND idx=1")
        con.execute("DELETE FROM passages WHERE doc_id=2 AND page_no=1 AND idx=1")
        con.execute("DELETE FROM translations_l10n WHERE passage_id NOT IN (SELECT id FROM passages)")
        con.commit()
        s = self.sync(sink=self.sink)
        self.assertEqual(s["verified"]["groups_different"], 0, s["verified"])
        self.assertEqual(self.q(K2), [])
        live = self.q("SELECT count(*) FROM corpus.passages WHERE retired_at IS NULL")[0][0]
        idx = self.q("SELECT count(*) FROM corpus.row_index WHERE tbl='passages'")[0][0]
        self.assertEqual((live, idx), (14, 14))
        m = self.q("SELECT public.corpus_manifest(ARRAY['passages'])")[0][0]
        self.assertEqual(m["_scheme"], cs.DIGEST_SCHEME)

    def test_rebuild_matches_the_running_sums_and_a_resend_heals_the_index(self):
        self.sync(sink=self.sink)
        before = self.q("SELECT public.corpus_manifest()")[0][0]
        for t in cs.TABLES:
            self.q("SELECT corpus._rebuild_index(%s)", t)
        self.assertEqual(self.q("SELECT public.corpus_manifest()")[0][0], before)
        # lose part of the index: the next run re-sends those rows and the index is whole again
        self.pg.execute("DELETE FROM corpus.row_index WHERE tbl='passages' AND grp='markandeya_purana' AND k LIKE '1|%'")
        for t in cs.TABLES:
            self.q("SELECT corpus._rebuild_index(%s)", t) if t != "passages" else None
        self.pg.execute("DELETE FROM corpus.group_digest WHERE tbl='passages'")
        self.pg.execute("INSERT INTO corpus.group_digest SELECT 'passages', grp, count(*), sum(corpus._h64(k||' '||row_hash,0)), "
                        "sum(corpus._h64(k||' '||row_hash,1)) FROM corpus.row_index WHERE tbl='passages' GROUP BY grp")
        s = self.sync(sink=self.sink)
        self.assertEqual(s["tables"]["passages"]["upsert"], 3)
        self.assertEqual(s["tables"]["passages"]["changed"], 0)       # the rows were there; only the index lacked them
        self.assertEqual(s["verified"]["groups_different"], 0)
        self.assertEqual(self.q("SELECT public.corpus_manifest()")[0][0], before)

    def test_a_batch_naming_a_key_twice_is_refused(self):
        import psycopg
        row = '{"doc_code": "x", "row_hash": "h"}'
        with self.assertRaises(psycopg.Error) as e:
            self.pg.execute("SELECT public.corpus_ingest('docs', '[%s, %s]'::jsonb)" % (row, row))
        self.assertIn("names a key twice", str(e.exception))

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
