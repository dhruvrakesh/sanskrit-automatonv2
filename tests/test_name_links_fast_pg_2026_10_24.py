# -*- coding: ascii -*-
"""NAME_LINKS_FAST_2026_10_24: corpus.name_links takes each passage's names (2 to 12) as one sorted list and makes the
pairs from it, with no self-join (the first query joined the names to themselves, the planner guessed one row and the
fill ran for minutes: "Server error" on the site). The text: C20a, C20d and the preflight's P4 carry the same fast
query, the 23 Oct file keeps the first; C20c's job has a time limit. Against a real PostgreSQL (CORPUS_TEST_DSN, a
THROWAWAY database): the Supabase stand-ins, C4, C4b, C5; made-up mentions straight into the mirror, a few hundred
passages of them; the fast query gives exactly the pairs of the first; the site as it stood (the first view, empty)
takes C20d twice, is filled by C20b, read through the reader, and the nightly job keeps its id and gains its limit.

  python -m unittest tests.test_name_links_fast_pg_2026_10_24
"""
import os, random, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C20A = CLOUD / "C20a_name_links_view_2026-10-24.sql"
C20B = CLOUD / "C20b_name_links_fill_2026-10-24.sql"
C20C = CLOUD / "C20c_name_links_nightly_2026-10-24.sql"
C20D = CLOUD / "C20d_name_links_fast_2026-10-24.sql"
PRE = CLOUD / "C20_preflight_2026-10-24.sql"
OLD = CLOUD / "C20_name_links_2026-10-23.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql"]
MARK = "NAME_LINKS_FAST_2026_10_24"
ON = C20D.exists() and MARK.encode() in C20A.read_bytes() if C20A.exists() else False
U1 = "11111111-1111-1111-1111-111111111111"
ROLLBACK = """
DO $$ BEGIN
  IF to_regclass('cron.job') IS NOT NULL THEN
    PERFORM cron.unschedule(jobid) FROM cron.job WHERE jobname = 'srangam-corpus-name-links';
  END IF;
END $$;
DROP FUNCTION IF EXISTS public.corpus_reader_name_links(text, integer), corpus._refresh_name_links();
DROP MATERIALIZED VIEW IF EXISTS corpus.name_links;
"""


def text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def view_of(sql: str) -> str:
    """The view's query: from its first WITH to its GROUP BY."""
    i = sql.index("AS\nWITH ") + 3 if "AS\nWITH " in sql else sql.index("WITH ")
    return sql[i:sql.index("GROUP BY name_a, name_b", i) + len("GROUP BY name_a, name_b")]


@unittest.skipUnless(ON, "NAME_LINKS_FAST_2026_10_24 is not applied here")
class TheText(unittest.TestCase):
    def test_one_fast_query(self):
        fast = view_of(text(C20A))
        self.assertIn("WITH ORDINALITY", fast)
        self.assertNotIn("JOIN kept b", fast, "no self-join")
        self.assertIn("HAVING count(*) BETWEEN 2 AND 12", fast, "the desk's list rule")
        self.assertIn("m.doc_code NOT LIKE '%-RETIRED'", fast)
        self.assertIn("p.retired_at IS NULL", fast, "the passage still live (corpus_passages_live)")
        self.assertEqual(view_of(text(C20D)), fast, "C20d gives the site the same query")
        self.assertIn(fast, text(PRE), "P4 times it")
        if OLD.exists():
            self.assertIn("JOIN kept b", view_of(text(OLD)), "the 23 Oct file keeps the first, for the record")

    def test_the_job_has_a_limit(self):
        for f in (C20C, C20D):
            self.assertIn("'SET statement_timeout = ''5min''; SELECT corpus._refresh_name_links();'", text(f), f.name)
        d = text(C20D)
        self.assertIn("WITH NO DATA;", d)
        self.assertLess(d.index("BEGIN;"), d.index("DROP MATERIALIZED VIEW corpus.name_links;"))
        self.assertTrue(d.rstrip().endswith("COMMIT;"))

    def test_ascii_and_marks(self):
        for f in (C20A, C20C, C20D, CLOUD / "C20d_checks_2026-10-24.sql", PRE, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


@unittest.skipUnless(DSN and ON, "CORPUS_TEST_DSN is not set (or NAME_LINKS_FAST not here)")
class TheFastFill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        for f in FILES:
            cls.pg.execute(f.read_text(encoding="utf-8"))
        cls.pg.execute(ROLLBACK)
        x = cls.pg.execute
        x("TRUNCATE corpus.mentions, corpus.passages, corpus.entities, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        rnd = random.Random(20261024)
        docs = ["d%02d" % i for i in range(12)] + ["gone", "x-RETIRED"]
        for d in docs:
            x("INSERT INTO corpus.docs (doc_code, title, row_hash, retired_at) VALUES (%s, %s, 'h', "
              "CASE WHEN %s = 'gone' THEN now() END)", (d, d.upper(), d))
        names = ["N%03d" % i for i in range(120)]
        for n in names:
            x("INSERT INTO corpus.entities (canonical, kind, row_hash) VALUES (%s, 'person', 'h')", (n,))
        for d in docs:
            for pg in range(1, 6):
                for idx in range(1, 9):
                    x("INSERT INTO corpus.passages (doc_code, page_no, idx, row_hash, retired_at) VALUES "
                      "(%s, %s, %s, 'h', CASE WHEN %s THEN now() END)", (d, pg, idx, rnd.random() < 0.05))
                    k = rnd.choice([0, 0, 1, 2, 2, 3, 4, 6, 13])         # now and then a list of 13
                    for n in rnd.sample(names, k):
                        x("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, row_hash, retired_at) "
                          "VALUES (%s, %s, %s, %s, 'h', CASE WHEN %s THEN now() END)",
                          (d, pg, idx, n, rnd.random() < 0.04))
        cls.cron = cls.pg.execute("SELECT to_regclass('cron.job') IS NOT NULL").fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.pg.execute(ROLLBACK)
        cls.pg.close()

    def site_as_it_stood(self):
        """C20a as pasted on 24 Oct: the same functions, the view with the first query, empty."""
        self.pg.execute(ROLLBACK)
        self.pg.execute(text(C20A))
        self.pg.execute("DROP MATERIALIZED VIEW corpus.name_links")
        self.pg.execute("CREATE MATERIALIZED VIEW corpus.name_links AS %s WITH NO DATA" % view_of(text(OLD)))
        self.pg.execute("CREATE UNIQUE INDEX corpus_name_links_pair ON corpus.name_links (name_a, name_b)")

    def test_the_same_pairs(self):
        old, fast = view_of(text(OLD)), view_of(text(C20A))
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL enable_nestloop = off")      # the first query, in a plan that ends
            a = self.pg.execute("SELECT count(*) FROM ((%s) EXCEPT ALL (%s)) z" % (old, fast)).fetchone()[0]
            b = self.pg.execute("SELECT count(*) FROM ((%s) EXCEPT ALL (%s)) z" % (fast, old)).fetchone()[0]
            n = self.pg.execute("SELECT count(*) FROM (%s) z" % fast).fetchone()[0]
        self.assertEqual((a, b), (0, 0), "the same pairs, the same counts, the same first passage")
        self.assertGreater(n, 500)
        plan = "\n".join(r[0] for r in self.pg.execute("EXPLAIN SELECT count(*) FROM (%s) z" % fast).fetchall())
        self.assertNotIn("CTE Scan on kept", plan, "no self-join for the planner to guess wrong")

    def test_c20d_then_the_fill(self):
        self.site_as_it_stood()
        if self.cron:
            self.pg.execute("SELECT cron.schedule('srangam-corpus-name-links', '40 4 * * *', "
                            "'SELECT corpus._refresh_name_links();')")      # C20c as pasted on 24 Oct
            before = self.pg.execute("SELECT jobid FROM cron.job WHERE jobname = 'srangam-corpus-name-links'"
                                     ).fetchone()[0]
        self.pg.execute(text(C20D))
        self.pg.execute(text(C20D))
        f1 = self.pg.execute(text(CLOUD / "C20d_checks_2026-10-24.sql").split("\n\n\n")[1]).fetchone()
        self.assertEqual(tuple(f1), (True, False), "fast, empty")
        got = self.pg.execute(text(C20B)).fetchone()[0]
        self.assertFalse(got["was_filled"])
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL enable_nestloop = off")
            want = self.pg.execute("SELECT count(*) FROM (%s) z" % view_of(text(OLD))).fetchone()[0]
        self.assertEqual(got["pairs"], want)
        rows = self.pg.execute("SELECT name_a, passages FROM corpus.name_links ORDER BY passages DESC LIMIT 1"
                               ).fetchall()
        name = rows[0][0]
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE authenticated")
            self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (U1,))
            seen = self.pg.execute("SELECT * FROM public.corpus_reader_name_links(%s, 5)", (name,)).fetchall()
        self.assertTrue(seen, "the reader reads the fast view")
        if self.cron:
            after = self.pg.execute("SELECT jobid, command FROM cron.job WHERE jobname = 'srangam-corpus-name-links'"
                                    ).fetchall()
            self.assertEqual(after, [(before, "SET statement_timeout = '5min'; SELECT corpus._refresh_name_links();")])
            self.pg.execute(after[0][1])
            self.pg.execute("RESET statement_timeout")
            self.assertTrue(self.pg.execute("SELECT relispopulated FROM pg_class WHERE oid = "
                                            "'corpus.name_links'::regclass").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
