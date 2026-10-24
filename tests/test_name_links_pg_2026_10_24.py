# -*- coding: ascii -*-
"""NAME_LINKS_C20_SPLIT_2026_10_24 against a real PostgreSQL: docs/cloud/C20a (the definitions, the view WITH NO DATA),
C20b (the fill) and C20c (the nightly job), which replace the one-paste C20 of 23 Oct that ended "Server error" on the
site. Applies the Supabase stand-ins, C4, C4b and C5, then C20a twice; made-up mentions straight into the mirror.
The view stays empty until the fill, and the reader then gives no rows (the name page stays as it was); the fill
counts the desk's pairs (two names in one passage of a live text, a passage of more than 12 names left out); a second
fill refreshes CONCURRENTLY; the reader is the signed-in readers' only, the refresh nobody's but the owner's; the job
is kept once however often C20c is pasted (when pg_cron is in the test database).

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_name_links_pg_2026_10_24
"""
import json, os, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C20A = CLOUD / "C20a_name_links_view_2026-10-24.sql"
C20B = CLOUD / "C20b_name_links_fill_2026-10-24.sql"
C20C = CLOUD / "C20c_name_links_nightly_2026-10-24.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql"]
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
DOCS = [("sb", "Satapatha", None), ("mbh", "Adiparvan", None), ("old", "Old", "now"), ("x-RETIRED", "X", None)]
PASSAGES = [("sb", 1, 1, None), ("sb", 1, 2, None), ("sb", 2, 1, None), ("sb", 3, 1, "now"), ("mbh", 1, 1, None),
            ("mbh", 1, 2, None), ("old", 1, 1, None), ("x-RETIRED", 1, 1, None)]
NAMES = ["Janaka", "Yajnavalkya", "Videha", "Ajatasatru"] + ["N%d" % i for i in range(1, 14)]
MENTIONS = [("sb", 1, 1, "Janaka", None), ("sb", 1, 1, "Yajnavalkya", None),
            ("sb", 1, 2, "Janaka", None), ("sb", 1, 2, "Yajnavalkya", None), ("sb", 1, 2, "Videha", None),
            ("mbh", 1, 1, "Janaka", None), ("mbh", 1, 1, "Yajnavalkya", None),
            ("old", 1, 1, "Janaka", None), ("old", 1, 1, "Ajatasatru", None),            # a retired text
            ("x-RETIRED", 1, 1, "Janaka", None), ("x-RETIRED", 1, 1, "Ajatasatru", None),  # its code says retired
            ("sb", 3, 1, "Janaka", None), ("sb", 3, 1, "Ajatasatru", None),              # a retired passage
            ("sb", 2, 1, "Janaka", None), ("sb", 2, 1, "Videha", "now")]                 # a retired mention
MENTIONS += [("mbh", 1, 2, "N%d" % i, None) for i in range(1, 14)]                       # a list of 13 names


def statements(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class NameLinks(unittest.TestCase):
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
        for code, title, ret in DOCS:
            x("INSERT INTO corpus.docs (doc_code, title, row_hash, retired_at) VALUES (%s, %s, 'h', "
              "CASE WHEN %s::text = 'now' THEN now() END)", (code, title, ret))
        for code, pg, idx, ret in PASSAGES:
            x("INSERT INTO corpus.passages (doc_code, page_no, idx, row_hash, retired_at) VALUES (%s, %s, %s, 'h', "
              "CASE WHEN %s::text = 'now' THEN now() END)", (code, pg, idx, ret))
        for n in NAMES:
            x("INSERT INTO corpus.entities (canonical, kind, row_hash) VALUES (%s, %s, 'h')",
              (n, "place" if n == "Videha" else "person"))
        for code, pg, idx, n, ret in MENTIONS:
            x("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, row_hash, retired_at) VALUES "
              "(%s, %s, %s, %s, 'h', CASE WHEN %s::text = 'now' THEN now() END)", (code, pg, idx, n, ret))
        cls.cron = cls.pg.execute("SELECT to_regclass('cron.job') IS NOT NULL").fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.pg.execute(ROLLBACK)
        cls.pg.close()

    def setUp(self):
        self.pg.execute(statements(C20A))      # twice over the class: it may be pasted again; each test from empty
        self.pg.execute(statements(C20A))

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

    def fill(self) -> dict:
        r = self.pg.execute(statements(C20B)).fetchone()[0]
        return r if isinstance(r, dict) else json.loads(r)

    def filled(self) -> bool:
        return self.pg.execute("SELECT relispopulated FROM pg_class WHERE oid = 'corpus.name_links'::regclass"
                               ).fetchone()[0]

    def test_empty_until_filled(self):
        self.assertFalse(self.filled(), "C20a fills nothing: it is quick on the site")
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_name_links(%s, 20)", ("Janaka",)), [],
                         "no rows, no error, while the view is empty: the name page stays as it was")

    def test_the_fill_and_the_refresh(self):
        got = self.fill()
        self.assertEqual((got["pairs"], got["was_filled"]), (3, False), got)
        self.assertIsInstance(got["ms"], (int, float))
        rows = self.pg.execute("SELECT name_a, name_b, passages, texts, first_doc, first_page, first_idx "
                               "FROM corpus.name_links ORDER BY 1, 2").fetchall()
        self.assertEqual(rows, [("Janaka", "Videha", 1, 1, "sb", 1, 2), ("Janaka", "Yajnavalkya", 3, 2, "mbh", 1, 1),
                                ("Videha", "Yajnavalkya", 1, 1, "sb", 1, 2)],
                         "retired texts, passages and mentions left out; the list of 13 left out")
        again = self.fill()
        self.assertEqual((again["pairs"], again["was_filled"]), (3, True), "the second fill refreshes CONCURRENTLY")
        self.pg.execute("INSERT INTO corpus.mentions (doc_code, page_no, idx, canonical, row_hash) "
                        "VALUES ('sb', 2, 1, 'Yajnavalkya', 'h')")
        try:
            self.assertEqual(self.fill()["pairs"], 3)
            self.assertEqual(self.pg.execute("SELECT passages FROM corpus.name_links WHERE name_a = 'Janaka' AND "
                                             "name_b = 'Yajnavalkya'").fetchone()[0], 4,
                             "a new mention is counted at the next refresh")
        finally:
            self.pg.execute("DELETE FROM corpus.mentions WHERE doc_code = 'sb' AND page_no = 2 AND idx = 1 "
                            "AND canonical = 'Yajnavalkya'")

    def test_the_reader(self):
        self.fill()
        rows = self.call("SELECT canonical, kind, passages, texts, doc_code, title, page_no, idx, ord "
                         "FROM public.corpus_reader_name_links(%s, 20)", ("Janaka",))
        self.assertEqual(rows, [("Yajnavalkya", "person", 3, 2, "mbh", "Adiparvan", 1, 1, 1),
                                ("Videha", "place", 1, 1, "sb", "Satapatha", 1, 2, 2)])
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_name_links(%s, 1)", ("Janaka",))), 1)
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_name_links(%s, 0)", ("Janaka",))), 1,
                         "k is kept between 1 and 50")
        self.assertIn("ERROR", str(self.call("SELECT * FROM public.corpus_reader_name_links(%s, 20)", ("Janaka",),
                                             uid=None)), "not signed in: the gate refuses")
        self.assertIn("permission denied", str(self.call("SELECT * FROM public.corpus_reader_name_links(%s, 20)",
                                                         ("Janaka",), role="anon", uid=None)))
        self.assertIn("permission denied", str(self.call("SELECT corpus._refresh_name_links()")),
                      "the refresh is the owner's only")
        self.assertIn("permission denied", str(self.call("SELECT count(*) FROM corpus.name_links")),
                      "the view itself is read through the reader only")

    def test_the_nightly_job(self):
        if not self.cron:
            self.skipTest("pg_cron is not in the test database")
        a = self.pg.execute(statements(C20C)).fetchone()[0]
        b = self.pg.execute(statements(C20C)).fetchone()[0]
        self.assertEqual(a, b, "pasted twice: one job")
        rows = self.pg.execute("SELECT schedule, command, active FROM cron.job WHERE jobname = "
                               "'srangam-corpus-name-links'").fetchall()
        self.assertEqual(rows, [("40 4 * * *", "SELECT corpus._refresh_name_links();", True)])
        self.pg.execute(rows[0][1])
        self.assertTrue(self.filled(), "the job's own command fills the view")


class TheFiles(unittest.TestCase):
    def test_the_split(self):
        for f in (C20A, C20B, C20C, CLOUD / "C20_preflight_2026-10-24.sql", CLOUD / "C20_checks_2026-10-24.sql",
                  Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(b"NAME_LINKS_C20_SPLIT_2026_10_24", b, f.name)
        a = statements(C20A)
        self.assertIn("WITH NO DATA;", a, "C20a fills nothing")
        self.assertNotIn("cron.schedule", a.split("BEGIN;", 1)[1], "the job is C20c's")
        self.assertIn("HAVING count(*) <= 12", a, "the desk's list rule")
        self.assertIn("m.doc_code NOT LIKE '%-RETIRED'", a)
        self.assertIn("PERFORM corpus._reader_gate();", a)
        self.assertIn("REFRESH MATERIALIZED VIEW CONCURRENTLY corpus.name_links;", a)
        for f in (C20B, C20C):
            body = [ln for ln in statements(f).splitlines() if ln.strip() and not ln.startswith("--")]
            self.assertEqual(len(body), 1, "%s is one statement" % f.name)
        view = a[a.index("WITH live AS ("):a.index("GROUP BY name_a, name_b") + len("GROUP BY name_a, name_b")]
        pre = statements(CLOUD / "C20_preflight_2026-10-24.sql")
        self.assertIn(view, pre, "P4 times the view's own query")
        old = CLOUD / "C20_name_links_2026-10-23.sql"
        if old.exists():
            self.assertIn(view, statements(old), "the same pairs as the 23 Oct C20 (and the site's own count)")


if __name__ == "__main__":
    unittest.main()
