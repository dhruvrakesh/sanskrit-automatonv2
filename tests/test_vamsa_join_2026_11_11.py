# -*- coding: ascii -*-
"""VAMSA_JOIN_2026_11_11 (G5b, G5c): the Puranas' own lines joined to the Purana Index's persons (scripts/vamsa_join.py):
a person found by the father the index gives him, else by a name the index has once; homonyms apart; a root joined
across chapters by the index; each step's verdict (agrees, differs, new, absent); the line's name from the text. And
index_sync.py's table dynasties: one row a line and one a work, a page link only where the site has a page; sent only
when the site has the table (C28) and corpus-index takes it, and nothing waits when there is nothing to send. With
CORPUS_TEST_DSN (a THROWAWAY PostgreSQL): C28 on C21, C23 and C26, the rows in and verified, the reader for signed-in
readers only, C26's tables untouched. Temp folders only; nothing is called."""
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
CLOUD = REPO / "docs" / "cloud"
sys.path.insert(0, str(S))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import vamsa_read as VR    # noqa: E402
import vamsa_join as VJ    # noqa: E402

MARK = "VAMSA_JOIN_2026_11_11"
DSN = os.environ.get("CORPUS_TEST_DSN", "")
C28 = CLOUD / "C28_index_dynasties_2026-11-11.sql"
IK, VI, SR, MA = "Ik\u1e63v\u0101ku", "Vikuk\u1e63i", "S\u1e5b\u00f1jaya", "Dh\u016bmr\u0101k\u1e63a"


def graph():
    """vamsa_view's graph, as far as vamsa_join reads it: the heads, the parents, the sex."""
    shown = {("pui", 1): "Manu", ("pui", 2): IK, ("pui", 3): VI, ("pui", 4): "Kakutstha",
             ("pui", 5): SR + " (I)", ("pui", 6): SR + " (II)", ("pui", 7): MA, ("pui", 8): "Hary\u0101\u015bva",
             ("pui", 9): "Il\u0101", ("pui", 10): "Pur\u016bravas", ("pui", 11): "Budha", ("inm", 2): IK}
    par = {("pui", 2): {("pui", 1)}, ("pui", 3): {("pui", 2)}, ("pui", 5): {("pui", 7)}, ("pui", 6): {("pui", 8)},
           ("pui", 10): {("pui", 9), ("pui", 11)}, ("pui", 4): {("pui", 8)}}
    return {"shown": shown, "par": par, "sex": {("pui", 9): "f"}}


def st(ref, a, b, ch, rel="son_of", check="verified"):
    return {"ref": ref, "a": a, "rel": rel, "b": b, "words": "x", "check": check, "chapter": ch}


class TheIndex(unittest.TestCase):
    def setUp(self):
        self.ix = VJ.Index(graph())

    def test_found_by_the_father_else_by_a_name_it_has_once(self):
        self.assertEqual(self.ix.person(IK, "Manu"), (2, "father", 1))
        self.assertEqual(self.ix.person(SR, MA), (5, "father", 7), "the homonym told apart by his father")
        self.assertEqual(self.ix.person(SR, "Candra"), (None, "", None), "two of that name, neither father agrees")
        self.assertEqual(self.ix.person("Kakutstha", VI), (4, "name", None), "one of that name: the index gives another")
        self.assertEqual(self.ix.person("Nobody", "Manu"), (None, "", None))
        self.assertEqual(self.ix.fathers(10), [11], "a mother is not a father")

    def test_the_verdicts(self):
        self.assertEqual(self.ix.verdict(2, "father"), "agrees")
        self.assertEqual(self.ix.verdict(4, "name"), "differs")
        self.assertEqual(self.ix.verdict(1, "name"), "new")
        self.assertEqual(self.ix.verdict(None, ""), "absent")


class TheJoin(unittest.TestCase):
    def test_a_root_joined_across_chapters_by_the_index(self):
        sts = [st("R1", IK, "Manu", 1), st("R9", VI, IK, 9), st("R10", "Kakutstha", VI, 9),
               st("R20", SR, MA, 20), st("R21", "Sahadeva", SR, 20), st("R30", "X", "Y", 30, check="unsupported"),
               st("R40", "Yadava", "Yadu", 40, rel="line_of")]
        j = VJ.join(sts, VJ.Index(graph()))
        names = [[s["name"] for s in ln] for ln in j["lines"]]
        self.assertEqual(names[0], ["Manu", IK, VI, "Kakutstha"])
        self.assertEqual([s["joined"] for s in j["lines"][0]], ["", "", "index", "chapter"])
        self.assertEqual([s["index"] for s in j["lines"][0]], ["", "agrees", "agrees", "differs"])
        self.assertIn([MA, SR, "Sahadeva"], names)
        self.assertEqual(j["counts"]["joined"], 1)
        self.assertEqual((j["counts"]["father"], j["counts"]["name"]), (3, 1))
        self.assertFalse(any("X" in n for n in names))

    def test_the_works_rows_and_the_labels(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "vamsa_read" / "bhp9"
            d.mkdir(parents=True)
            rec = {"work": "bhp9", "chapter": 1, "part": 0, "prompt_version": VR.PROMPT_VERSION, "statements": [
                st("BhP 9.1.1", IK, "Manu", 1), st("BhP 9.1.2", VI, IK, 1), st("BhP 9.1.3", "Kakutstha", VI, 1),
                st("BhP 9.1.4", "Aik\u1e63v\u0101kas", IK, 1, rel="line_of")]}
            (d / "01.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            got = VJ.dynasties(str(Path(td) / "vamsa_read"), "", "", graph=graph())
            self.assertEqual(list(got), ["bhp9"])
            w = got["bhp9"]
            self.assertEqual((w["text"], len(w["lines"]), w["lines"][0]["length"]), ("bh", 1, 4))
            self.assertEqual(w["lines"][0]["label"], "Aik\u1e63v\u0101kas (after %s)" % IK)
            self.assertEqual(w["lines"][0]["steps"][1]["person"], "pui:2")
            self.assertIn("CC BY-NC-SA 4.0", w["source"])
            import index_sync as ix
            rows = ix.dynasty_rows(str(Path(td) / "vamsa_read"), "", "", graph(), {"pui:2"})
            self.assertEqual([r["key"] for r in rows], ["bhp9:0", "bhp9:1"])
            steps = rows[1]["steps"]
            self.assertTrue(steps[1].get("page")); self.assertNotIn("page", steps[2], "no page there")
            self.assertEqual(rows[0]["counts"]["agrees"], 2)
            self.assertTrue(all(r.get("row_hash") for r in rows))
            self.assertEqual(VJ.dynasties(str(Path(td) / "none"), "", "", graph=graph()), {})


class FakeSink:
    name = "fake"

    def __init__(self, man):
        self.man, self.sent = man, {}

    def manifest(self):
        return self.man

    def keys(self, table):
        return {}

    def ingest(self, table, rows):
        self.sent.setdefault(table, []).extend(rows)
        return {"changed": len(rows)}

    def delete(self, table, keys):
        return {"deleted": 0}


class TheSync(unittest.TestCase):
    def test_waits_for_c28_only_with_lines_to_send(self):
        import index_sync as ix
        rows = {t: [] for t in ix.TABLES}
        man = {t: {"n": 0, "digest": ix.digest([])} for t in ix.TABLES if t != "dynasties"}
        man["features"] = {"aliases": True}
        got = ix.sync(rows, FakeSink(man), True, log=lambda *_: None)
        self.assertEqual((got["waiting"], got["verified"]["tables_different"]), ([], []), "nothing to send: no wait")
        rows["dynasties"] = [ix.finish({"key": "vip4:1", "work": "vip4", "n": 1, "steps": []})]
        rows["statements"] = [ix.finish({"key": "s1", "scholars": [{"work": "phai1923", "verdict": "agrees"}]})]
        sink = FakeSink(man)
        got = ix.sync(rows, sink, True, log=lambda *_: None)
        self.assertEqual(got["waiting"], ["dynasties"])
        self.assertIn("scholars", sink.sent["statements"][0], "C28 not there: the claims' verdicts still go (C23 is)")
        man["dynasties"] = {"n": 0, "digest": ix.digest([])}
        sink = FakeSink(man)
        ix.sync(rows, sink, True, log=lambda *_: None)
        self.assertEqual([r["key"] for r in sink.sent["dynasties"]], ["vip4:1"])
        self.assertEqual(ix.TABLES[-1], "meta", "the run's row last")


@unittest.skipUnless(DSN and C28.exists(), "CORPUS_TEST_DSN not set: a THROWAWAY PostgreSQL")
class TheSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        import test_genealogy_heal_2026_11_10 as GH
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        GH.Fixture.setUpClass.__func__(cls)
        cls.pg = psycopg.connect(DSN, autocommit=True)
        cls.pg.execute("DROP SCHEMA IF EXISTS corpus CASCADE")
        cls.pg.execute("DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer)")
        for f in GH.BASE:
            cls.pg.execute(f.read_text(encoding="utf-8"))
        for f in (GH.C26, C28):
            sql = f.read_text(encoding="utf-8")
            change = sql[sql.index("BEGIN;"):sql.index("COMMIT;") + len("COMMIT;")]
            for _ in range(2):
                cls.pg.execute(change)
        cls.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        cls.sink = cls.ix.PgSink(DSN)
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "vip4"
            d.mkdir()
            rec = {"work": "vip4", "chapter": 1, "part": 0, "prompt_version": VR.PROMPT_VERSION,
                   "statements": [st("ViP 4,1.1", IK, "Manu", 1), st("ViP 4,1.2", VI, IK, 1),
                                  st("ViP 4,1.3", "Kakutstha", VI, 1)]}
            (d / "01.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            cls.rows["dynasties"] = cls.ix.dynasty_rows(td, "", "", graph(), {"pui:2"})
        cls.U1 = GH.U1
        cls.got = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)

    @classmethod
    def tearDownClass(cls):
        cls.sink.con.close()
        cls.pg.execute("DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer)")
        cls.pg.close()
        cls.vv._CACHE.clear(); cls.vv.rv._CACHE.clear(); cls.td.cleanup()

    def call(self, sql, args=(), role="authenticated", uid=None):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:  # noqa: BLE001
                return "ERROR: " + str(e).splitlines()[0]

    def test_every_table_in_and_verified(self):
        self.assertEqual((self.got["waiting"], self.got["features_waiting"]), ([], []))
        self.assertEqual(self.got["verified"]["tables_different"], [])
        man = self.pg.execute("SELECT public.corpus_index_manifest()").fetchone()[0]
        self.assertEqual((man["dynasties"]["n"], man["features"]["dynasties"], man["features"]["aliases"]), (2, True, True))
        n = self.pg.execute("SELECT count(*) FROM corpus.index_persons WHERE same_as <> '[]'::jsonb").fetchone()[0]
        self.assertEqual(n, sum(1 for r in self.rows["persons"] if r.get("same_as")), "C26's table as before")
        again = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual((again["sent"], again["deleted"]), (0, 0))

    def test_the_reader_for_signed_in_readers_only(self):
        got = self.call("SELECT key, length, steps FROM public.corpus_reader_index_dynasties('vip4')", uid=self.U1)
        self.assertEqual([r[0] for r in got], ["vip4:0", "vip4:1"])
        self.assertEqual([s["name"] for s in got[1][2]], ["Manu", IK, VI, "Kakutstha"])
        self.assertIn("ERROR", str(self.call("SELECT * FROM public.corpus_reader_index_dynasties(NULL)", role="anon")))
        self.assertIn("ERROR", str(self.call("SELECT public.corpus_index_ingest('dynasties', '[]'::jsonb)", uid=self.U1)))


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (S / "vamsa_join.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(b.isascii(), p.name)
            self.assertIn(MARK.encode(), b, p.name)
        if C28.exists():
            self.assertTrue(C28.read_bytes().isascii())
            self.assertIn(b"C28_INDEX_DYNASTIES_2026_11_11", C28.read_bytes())


if __name__ == "__main__":
    unittest.main()
