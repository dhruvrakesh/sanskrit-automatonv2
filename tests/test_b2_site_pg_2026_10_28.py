# -*- coding: ascii -*-
"""B2_SITE_2026_10_28 and C23_INDEX_CLAIMS_2026_10_28: the scholars' claims beside the genealogies. index_sync.py
(scheme i2) reads data/shelf/claims.db (read-only): the public-domain works only, the claims whose quotation was found
on the page (exact or close) only, their names tied to ours where one name of ours is the candidate; each relation's
verdict as the desk stored it (kin_ties.scholar: agrees, differs, reversed) with the claims on the site it rests on,
or none when none of them is on the site; each step's best verdict. On a site with C21 alone the claims wait and the
rest is sent and verified; with C23 they go too, and the readers give them: a step's chip, a statement's claims in the
tree, a name's claims, the work's credit.

The made-up shelf of tests/test_index_site_pg_2026_10_25.py, our names Aja, Raghu, Atithi and Kusa added, and a
made-up claims.db: a public-domain work (four claims: one whose quotation was not found) and a work in copyright.
TestBuild runs without a database; TestSite is skipped unless CORPUS_TEST_DSN names a THROWAWAY PostgreSQL."""
import contextlib, io, json, os, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
for p in (str(S), str(REPO), str(Path(__file__).resolve().parent)):
    if p not in sys.path:
        sys.path.insert(0, p)
from tests.test_vamsa_2026_10_25 import make_db, make_zip, load, CHECK  # noqa: E402
from tests.test_index_site_pg_2026_10_25 import extend, AJA, DASA2, RAGHU, U1  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C21 = CLOUD / "C21_index_site_2026-10-25.sql"
C23 = CLOUD / "C23_index_claims_2026-10-28.sql"
BASE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
        CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql", C21]
MARK = "B2_SITE_2026_10_28"
PD = "public domain: published 1923; the author died in 1957 (India: 60 years after; USA: before 1929)"
DASA, AJA_N = "Da\u015baratha", "Aja"
C1, C3, C4 = "phai1923:52:3", "phai1923:61:2", "phai1923:61:4"


def claims_db(path: Path):
    c = sqlite3.connect(str(path))
    c.executescript("""
    CREATE TABLE claim_works(code TEXT PRIMARY KEY, author TEXT, title TEXT, publisher TEXT, year TEXT, source TEXT,
                             handle TEXT, md5 TEXT, licence TEXT, pdf TEXT, pages INTEGER, loaded_at TEXT, mark TEXT);
    CREATE TABLE claims(id INTEGER PRIMARY KEY, read_id INTEGER, work TEXT, pdf_page INTEGER, printed TEXT, n INTEGER,
                        subject TEXT, subject_printed TEXT, relation TEXT, object TEXT, claim TEXT, quote TEXT,
                        quote_check TEXT, quote_score REAL, stance TEXT, hedge TEXT, who TEXT, at TEXT);
    CREATE TABLE claim_cites(claim_id INTEGER, n INTEGER, printed TEXT, work TEXT, locus TEXT, book TEXT, how TEXT,
                             ours TEXT, note TEXT, vei_page TEXT, reader TEXT, score REAL);
    CREATE TABLE claim_links(claim_id INTEGER, role TEXT, name TEXT, pkey TEXT, entity_id INTEGER, canonical TEXT,
                             kind TEXT, how TEXT, cands INTEGER, linker TEXT, at TEXT);
    """)
    c.execute("INSERT INTO claim_works (code, author, title, publisher, year, source, handle, licence) VALUES "
              "('phai1923', 'Hemchandra Raychaudhuri', 'Political History of Ancient India', 'University of Calcutta', "
              "'1923', 'GIPE-004595', '10973/29602', ?)", (PD,))
    c.execute("INSERT INTO claim_works (code, author, title, publisher, year, licence) VALUES "
              "('later1953', 'Someone', 'A Later Book', 'A Press', '1953', 'in copyright to the end of 2040')")
    rows = [  # id, work, page, printed, n, subject, relation, object, claim, quote, check, stance
        (1, "phai1923", 52, "37", 3, DASA, "son_of", AJA_N, "Dasaratha was the son of Aja.",
         "Dasaratha, the son of Aja", "exact", "asserts"),
        (2, "phai1923", 60, "44", 1, AJA_N, "son_of", "Raghu", "Aja was the son of Raghu.", "", "none", "asserts"),
        (3, "phai1923", 61, "45", 2, DASA, "king_of", "Kosala", "Dasaratha was king of Kosala.",
         "Dasaratha, king of Kosala", "close", "reports"),
        (4, "phai1923", 61, "45", 4, "Raghu", "contemporary_of", AJA_N, "Raghu lived in Aja's time.",
         "Raghu ... in the time of Aja", "exact", "doubts"),
        (5, "later1953", 9, "9", 1, DASA, "son_of", AJA_N, "Dasaratha was the son of Aja.", "x", "exact", "asserts"),
    ]
    for cid, work, page, printed, n, s, rel, o, claim, quote, qc, stance in rows:
        c.execute("INSERT INTO claims (id, read_id, work, pdf_page, printed, n, subject, relation, object, claim, quote, "
                  "quote_check, stance, hedge) VALUES (?,1,?,?,?,?,?,?,?,?,?,?,?,'')",
                  (cid, work, page, printed, n, s, rel, o, claim, quote, qc, stance))
    links = [  # claim, role, entity, canonical, how, cands
        (1, "subject", 1, DASA, "exact", 1), (1, "object", 2, AJA_N, "exact", 1),
        (2, "subject", 2, AJA_N, "exact", 1), (2, "object", 3, "Raghu", "spelling", 1),
        (3, "subject", 1, DASA, "exact", 1), (3, "object", 7, "Kosala", "exact", 2), (3, "object", 8, "Kosala", "exact", 2),
        (4, "subject", 3, "Raghu", "spelling", 1), (4, "object", 2, AJA_N, "exact", 1),
        (5, "subject", 1, DASA, "exact", 1), (5, "object", 2, AJA_N, "exact", 1),
    ]
    for cid, role, eid, canonical, how, cands in links:
        c.execute("INSERT INTO claim_links (claim_id, role, name, entity_id, canonical, how, cands) VALUES (?,?,?,?,?,?,?)",
                  (cid, role, canonical, eid, canonical, how, cands))
    c.executemany("INSERT INTO claim_cites (claim_id, n, printed, work, locus, ours, note) VALUES (?,?,?,?,?,?,?)", [
        (1, 1, "Vi. IV. 4. 86", "Visnu Purana", "IV. 4. 86", "vishnu_purana", "ours is the Bombay print"),
        (1, 2, "Ram. I. 70. 20", "Ramayana", "I. 70. 20", "withdrawn_text", "ours is withdrawn"),
        (3, 1, "Ram. II. 1. 1", "Ramayana", "II. 1. 1", None, None)])
    c.commit()
    c.close()


def extend_b2(t: Path):
    """Our names Raghu, Atithi and Kusa; the desk's verdicts: Dasaratha son of Aja agrees (claim 1); Aja son of Raghu
    agrees too, but its claim's quotation was not found (no R on the site); Raghu and Aja differ (claim 4)."""
    con = sqlite3.connect(str(t / "data" / "context.db"))
    con.execute("INSERT INTO entities VALUES (3, 'Raghu', 'person')")
    con.commit()
    con.close()
    k = sqlite3.connect(str(t / "data" / "shelf" / "kin.db"))
    k.execute("UPDATE kin_ties SET scholar = 'agrees', scholar_note = 'p. 37: Dasaratha was the son of Aja.' "
              "WHERE kin_id = 2")
    k.execute("UPDATE kin_ties SET subject_entity = 2, object_entity = 3, scholar = 'differs', "
              "scholar_note = 'p. 45 (contemporary_of): Raghu lived in Aja''s time.' WHERE kin_id = 1")
    k.commit()
    k.close()


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.t = Path(cls.td.name)
        (cls.t / "data" / "shelf").mkdir(parents=True)
        cls.old_verdicts = os.environ.get("SA_SOURCE_VERDICTS")
        os.environ["SA_SOURCE_VERDICTS"] = str(cls.t / "source_verdicts.jsonl")
        (cls.t / "source_verdicts.jsonl").write_text('{"doc": "withdrawn_text", "status": "withdrawn"}\n',
                                                     encoding="utf-8")
        make_zip(cls.t / "1_sanskr.zip")
        make_db(cls.t)
        extend(cls.t)
        extend_b2(cls.t)
        cls.db = cls.t / "data" / "context.db"
        cls.kin = cls.t / "data" / "shelf" / "kin.db"
        cls.store = cls.t / "data" / "shelf" / "vamsa.db"
        cls.claims = cls.t / "data" / "shelf" / "claims.db"
        claims_db(cls.claims)
        vc = load(CHECK, "vamsa_check_b2")
        with contextlib.redirect_stdout(io.StringIO()):
            assert vc.main(["--zip", str(cls.t / "1_sanskr.zip"), "--kin", str(cls.kin), "--store", str(cls.store),
                            "--exports", str(cls.t / "exports"), "--yes"]) == 0
        cls.ix = load(S / "index_sync.py", "index_sync_b2")
        cls.rows = cls.ix.build(str(cls.db), str(cls.kin), str(cls.store), claims_db=str(cls.claims))

    @classmethod
    def tearDownClass(cls):
        if cls.old_verdicts is None:
            os.environ.pop("SA_SOURCE_VERDICTS", None)
        else:
            os.environ["SA_SOURCE_VERDICTS"] = cls.old_verdicts
        cls.td.cleanup()

    def by_key(self, table):
        return {r["key"]: r for r in self.rows[table]}

    def statement(self, subject, obj):
        return next(s for s in self.rows["statements"] if s["subject"] == subject and s["object"] == obj)


class TestBuild(Fixture):
    def test_scheme_and_tables(self):
        self.assertEqual(self.ix.SCHEME, "i2")
        self.assertIn("claims", self.ix.TABLES)
        self.assertEqual(self.ix.TABLES[-1], "meta")
        self.assertEqual(self.rows["meta"][0]["value"]["counts"]["claims"], 3)

    def test_only_the_public_domain_and_the_found_quotations(self):
        C = self.by_key("claims")
        self.assertEqual(sorted(C), sorted([C1, C3, C4]), "claim 2 (no quotation found) and the 1953 book left out")
        self.assertNotIn("work:later1953", self.by_key("texts"))
        w = self.by_key("texts")["work:phai1923"]
        self.assertEqual((w["kind"], w["show"]), ("work", True))
        self.assertTrue(w["rights"].startswith("public domain"))
        self.assertIn("Hemchandra Raychaudhuri, Political History of Ancient India", w["title"])
        self.assertIn("GIPE-004595", w["edition"])

    def test_a_claims_ties_and_cites(self):
        c = self.by_key("claims")[C1]
        self.assertEqual((c["subject_canonical"], c["subject_how"], c["object_canonical"]), (DASA, "exact", AJA_N))
        self.assertEqual((c["printed"], c["pdf_page"], c["n"], c["stance"], c["quote_check"]), ("37", 52, 3, "asserts", "exact"))
        self.assertEqual([x["ours"] for x in c["cites"]], ["vishnu_purana", None], "a withdrawn text is not ours on the site")
        self.assertEqual(c["cites"][1]["note"], "")
        c3 = self.by_key("claims")[C3]
        self.assertEqual((c3["subject_canonical"], c3["object_canonical"]), (DASA, None), "two of ours could be Kosala")
        c4 = self.by_key("claims")[C4]
        self.assertEqual((c4["subject_canonical"], c4["subject_how"]), ("Raghu", "spelling"), "a probable tie, with its how")

    def test_the_desks_verdicts_with_the_claims_they_rest_on(self):
        s = self.statement("Da\u015baratha (II)", "Aja (IV)")
        self.assertEqual(s["scholars"], [{"work": "phai1923", "verdict": "agrees",
                                          "note": "p. 37: Dasaratha was the son of Aja.", "claims": [C1]}])
        d = self.statement("Aja (IV)", "Raghu (I)")
        self.assertEqual([(x["verdict"], x["claims"]) for x in d["scholars"]], [("differs", [C4])])
        n = sum(1 for s in self.rows["statements"] if s.get("scholars"))
        self.assertEqual(n, 2)

    def test_a_steps_best_verdict(self):
        st = self.by_key("steps")
        self.assertEqual(st["pui:%d:%d" % (AJA, DASA2)]["scholar"], "agrees")
        self.assertEqual(st["pui:%d:%d" % (RAGHU, AJA)]["scholar"], "differs")
        self.assertEqual({s.get("scholar", "") for k, s in st.items() if k not in ("pui:%d:%d" % (AJA, DASA2),
                                                                           "pui:%d:%d" % (RAGHU, AJA))}, {""})

    def test_without_claims_db_nothing_of_them(self):
        r = self.ix.build(str(self.db), str(self.kin), str(self.store), claims_db=str(self.t / "none.db"))
        self.assertEqual(r["claims"], [])
        self.assertFalse(any(s.get("scholars") for s in r["statements"]))
        self.assertFalse(any("scholar" in s for s in r["steps"]), "no verdict, no field: the i1 hash is kept")
        self.assertNotIn("work:phai1923", {x["key"] for x in r["texts"]})

    def test_source_is_ascii_and_marked(self):
        raw = (S / "index_sync.py").read_bytes()
        self.assertTrue(raw.isascii())
        self.assertIn(MARK.encode(), raw)
        self.assertIn(b"C23_INDEX_CLAIMS_2026_10_28", C23.read_bytes())


@unittest.skipUnless(DSN and C21.exists() and C23.exists(), "CORPUS_TEST_DSN is not set (a throwaway PostgreSQL)")
class TestSite(Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        cls.pg.execute("DROP SCHEMA IF EXISTS corpus CASCADE")
        for f in BASE:
            cls.pg.execute(f.read_text(encoding="utf-8"))
        cls.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        cls.sink = cls.ix.PgSink(DSN)
        cls.before = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)   # C21 alone: the claims wait
        for _ in range(2):
            cls.pg.execute(C23.read_text(encoding="utf-8"))
        cls.after = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)

    @classmethod
    def tearDownClass(cls):
        cls.sink.con.close()
        cls.pg.close()
        super().tearDownClass()

    def call(self, sql, args=(), role="authenticated", uid=U1):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:  # noqa: BLE001
                return "ERROR: " + str(e).splitlines()[0]

    def test_on_c21_alone_the_claims_wait_and_the_rest_is_verified(self):
        self.assertEqual(self.before["waiting"], ["claims"])
        self.assertEqual(self.before["verified"]["tables_different"], [])
        self.assertEqual(self.before["verified"]["tables_equal"], len(self.ix.TABLES) - 1)

    def test_with_c23_the_claims_go_and_all_is_verified(self):
        self.assertEqual(self.after["waiting"], [])
        self.assertEqual(self.after["verified"]["tables_different"], [])
        self.assertEqual(self.after["tables"]["claims"]["send"], 3)
        # the statements and steps that carry a verdict go again, now with it (C21 had no column for it)
        self.assertEqual(self.after["tables"]["statements"]["send"], 2)
        self.assertEqual(self.after["tables"]["steps"]["send"], 2)
        n = self.pg.execute("SELECT count(*) FROM corpus.index_statements WHERE scholars <> '[]'::jsonb").fetchone()[0]
        self.assertEqual(n, 2)
        again = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual((again["sent"], again["deleted"]), (0, 0))

    def test_the_tree_carries_the_verdicts_and_their_claims(self):
        T = self.call("SELECT result FROM public.corpus_reader_index_tree('pui', %s, NULL, 2)", (DASA2,))[0][0]
        st = next(s for s in T["steps"] if s["parent"] == AJA and s["child"] == DASA2)
        self.assertEqual(st["scholar"], "agrees")
        self.assertEqual(st["items"][0]["scholars"][0]["claims"], [C1])
        self.assertEqual(T["claims"][C1]["claim"], "Dasaratha was the son of Aja.")
        self.assertEqual(T["claims"][C1]["cites"][0]["ours"], "vishnu_purana")
        self.assertIn(C4, T["claims"])
        self.assertTrue(T["works"]["phai1923"]["rights"].startswith("public domain"))
        self.assertNotIn("phai1923", T["texts"], "the texts stay as C21 gave them: GRETIL's, credited apart")

    def test_a_names_claims(self):
        N = self.call("SELECT result FROM public.corpus_reader_index_of_name(%s)", (DASA,))[0][0]
        self.assertEqual([c["key"] for c in N["claims"]], [C1, C3])
        self.assertEqual(N["claims_n"], 2)
        R = self.call("SELECT result FROM public.corpus_reader_index_of_name(%s)", ("Raghu",))[0][0]
        self.assertEqual([c["key"] for c in R["claims"]], [C4])

    def test_the_overview_names_the_work(self):
        O = self.call("SELECT result FROM public.corpus_reader_index_overview()")[0][0]
        self.assertEqual([(w["code"], w["claims"]) for w in O["works"]], [("phai1923", 3)])
        self.assertNotIn("phai1923", [t["code"] for t in O["texts"]], "the GRETIL texts are listed apart")

    def test_the_gate_and_the_door(self):
        self.assertTrue(str(self.call("SELECT result FROM public.corpus_reader_index_of_name('x')", role="anon",
                                      uid=None)).startswith("ERROR"))
        self.assertIn("permission denied", str(self.call("SELECT count(*) FROM corpus.index_claims")))
        self.assertIn("permission denied", str(self.call("SELECT public.corpus_index_keys('claims')")))
        self.assertIsInstance(self.call("SELECT public.corpus_index_keys('claims')", role="service_role", uid=None), list)

    def test_a_claim_gone_from_the_desk_is_deleted(self):
        rows = dict(self.rows)
        rows["claims"] = [r for r in self.rows["claims"] if r["key"] != C3]
        got = self.ix.sync(rows, self.sink, True, log=lambda *_: None)
        self.assertEqual(got["deleted"], 1)
        self.assertEqual(got["verified"]["tables_different"], [])
        back = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual(back["sent"], 1)


PAT = S / "patch_b2_site_2026_10_28.py"
PFILES = ("scripts/index_sync.py", "tests/test_index_site_pg_2026_10_25.py")


def as_left(rel: str) -> bytes:
    """The file as the patch left it: the oldest later backup that carries MARK, else the file now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*") if ".bak_b2site_" not in b.name and MARK.encode() in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


@unittest.skipUnless(PAT.exists(), "patch_b2_site_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in PFILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_b2site_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 2 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in PFILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual(got, as_left(rel), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
