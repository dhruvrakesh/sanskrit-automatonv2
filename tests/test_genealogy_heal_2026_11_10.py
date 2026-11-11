# -*- coding: ascii -*-
"""GENEALOGY_HEAL_2026_11_10 and C26_INDEX_ALIASES_2026_11_10: the genealogies mended from the indexes' own words.
scripts/vamsa_view.py draws a son begotten by another (Arjuna by Indra) up through his mother's husband (Pandu), never
lets a line pass to a person married to one already on it (Kasyapa, Aditi's husband, under Aditi), and ties an entry
the index defines as another ("Kaunteya (the son of Kunti) = Arjuna"; "Dhananjaya = Arjuna, q.v."; the Purana Index's
"a name of Rama") to that person's entry; a plural ("the sons of Kunti") to the persons its singular entries name.
scripts/index_sync.py sends the epithets (same_as, gloss) only to a site with C26 (its manifest says so), on the
person's row, or on a row of the epithet's own; docs/cloud/C26_index_aliases_2026-11-10.sql takes them, and the
readers give them (find, the tree).

A made-up shelf in a temp folder; never data/context.db, never the network, no model. TestSite is skipped unless
CORPUS_TEST_DSN names a THROWAWAY PostgreSQL."""
import contextlib, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
CLOUD = REPO / "docs" / "cloud"
for p in (str(S), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)
DSN = os.environ.get("CORPUS_TEST_DSN", "")
C26 = CLOUD / "C26_index_aliases_2026-11-10.sql"
BASE = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
        CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
        CLOUD / "C21_index_site_2026-10-25.sql", CLOUD / "C23_index_claims_2026-10-28.sql"]
MARK = "GENEALOGY_HEAL_2026_11_10"
U1 = "00000000-0000-0000-0000-0000000000a1"

# the entries (inm: Soerensen; pui: the Purana Index)
ARJ2, ARJ1, PANDU, KUNTI, INDRA, KASY, ADITI, MARICI, BRAHMAN, VISNU, DAKSA, ABHI, BHIMA = range(100, 113)
YUDH, MADRI, NAKULA, JAYANTA, DEVASENA, GUHA = range(114, 120)
K1, K2, KPL, DHAN, RAMA2, RAMA3, DASARATHI, DASA = 120, 121, 122, 123, 200, 201, 202, 203
ENTRIES = [  # id, source, lnum, name, head, body
    (ARJ2, "inm", 1, "Arjuna", "Arjuna[2]", "P\u0101\u1e47\u1e0dava. \u00a7 4 (Anukram.): I, 1, 109"),
    (ARJ1, "inm", 2, "Arjuna", "Arjuna[1]", "K\u0101rtav\u012brya, king of the Haihayas"),
    (PANDU, "inm", 3, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "son of Vy\u0101sa by Amb\u0101lik\u0101"),
    (KUNTI, "inm", 4, "Kunt\u012b", "Kunt\u012b", "wife of P\u0101\u1e47\u1e0du"),
    (INDRA, "inm", 5, "Indra", "Indra", "the king of the gods"),
    (KASY, "inm", 6, "Ka\u015byapa", "Ka\u015byapa", "a Praj\u0101pati"),
    (ADITI, "inm", 7, "Aditi", "Aditi", "daughter of Dak\u1e63a"),
    (MARICI, "inm", 8, "Mar\u012bci", "Mar\u012bci", "son of Brahman"),
    (BRAHMAN, "inm", 9, "Brahman", "Brahman", "the creator"),
    (VISNU, "inm", 10, "Vi\u1e63\u1e47u", "Vi\u1e63\u1e47u", "the god"),
    (DAKSA, "inm", 11, "Dak\u1e63a", "Dak\u1e63a", "a Praj\u0101pati"),
    (ABHI, "inm", 12, "Abhimanyu", "Abhimanyu", "son of Arjuna"),
    (BHIMA, "inm", 13, "Bh\u012bmasena", "Bh\u012bmasena", "son of P\u0101\u1e47\u1e0du"),
    (YUDH, "inm", 14, "Yudhi\u1e63\u1e6dhira", "Yudhi\u1e63\u1e6dhira", "the eldest Pandava"),
    (MADRI, "inm", 15, "M\u0101dr\u012b", "M\u0101dr\u012b", "wife of Pandu"),
    (NAKULA, "inm", 16, "Nakula", "Nakula", "son of Madri"),
    (JAYANTA, "inm", 17, "Jayanta", "Jayanta", "son of Indra"),
    (DEVASENA, "inm", 18, "Devasen\u0101", "Devasen\u0101", "daughter of Indra"),
    (GUHA, "inm", 19, "Guha", "Guha", "a made-up grandson"),
    (K1, "inm", 20, "Kaunteya", "Kaunteya[1]", "(\u201cthe son of Kunt\u012b\u201d) = Arjuna: I, 2275 (B\u012bbhatsu\u1e25)"),
    (K2, "inm", 21, "Kaunteya", "Kaunteya[2]", "(do.) = Bh\u012bmasena: I, 2242, 5021"),
    (KPL, "inm", 22, "Kaunteya", "Kaunteya", "pl. (\u02da\u0101\u1e25) and dual (\u02daau) (\u201cthe sons of Kunt\u012b\u201d): I, 185"),
    (DHAN, "inm", 23, "Dhana\u00f1jaya", "Dhana\u00f1jaya[1]", "= Arjuna, q.v."),
    (RAMA2, "pui", 1, "R\u0101ma", "R\u0101ma (II)", "\u2014 son of Da\u015baratha"),
    (RAMA3, "pui", 2, "R\u0101ma", "R\u0101ma (III)", "\u2014 a sage"),
    (DASARATHI, "pui", 3, "D\u0101\u015barathi", "D\u0101\u015barathi", "\u2014 a name of R\u0101ma, who destroyed R\u0101vana."),
    (DASA, "pui", 4, "Da\u015baratha", "Da\u015baratha (II)", "\u2014 king of Ayodhy\u0101"),
]
KIN = [  # id, src, entry, head, subject, relation, object
    (1, "inm", ARJ2, "Arjuna[2]", "Arjuna[2]", "son_of", "Indra"),
    (2, "inm", ARJ2, "Arjuna[2]", "Arjuna[2]", "son_of", "Kunt\u012b"),
    (3, "inm", ARJ2, "Arjuna[2]", "Arjuna[2]", "father_of", "Abhimanyu"),
    (4, "inm", PANDU, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "father_of", "Arjuna"),   # which Arjuna: "shared"
    (5, "inm", PANDU, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "husband_of", "Kunt\u012b"),
    (6, "inm", PANDU, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "father_of", "Bh\u012bmasena"),
    (7, "inm", INDRA, "Indra", "Indra", "son_of", "Ka\u015byapa"),
    (8, "inm", INDRA, "Indra", "Indra", "son_of", "Aditi"),
    (9, "inm", KASY, "Ka\u015byapa", "Ka\u015byapa", "son_of", "Mar\u012bci"),
    (10, "inm", KASY, "Ka\u015byapa", "Ka\u015byapa", "husband_of", "Aditi"),
    (11, "inm", MARICI, "Mar\u012bci", "Mar\u012bci", "son_of", "Brahman"),
    (12, "inm", BRAHMAN, "Brahman", "Brahman", "son_of", "Vi\u1e63\u1e47u"),
    (13, "inm", VISNU, "Vi\u1e63\u1e47u", "Vi\u1e63\u1e47u", "son_of", "Aditi"),
    (14, "inm", ADITI, "Aditi", "Aditi", "daughter_of", "Dak\u1e63a"),
    (15, "inm", K1, "Kaunteya[1]", "Kaunteya[1]", "son_of", "Kunt\u012b"),
    (16, "inm", KPL, "Kaunteya", "Kaunteya", "son_of", "Kunt\u012b"),
    (17, "pui", RAMA2, "R\u0101ma (II)", "R\u0101ma (II)", "son_of", "Da\u015baratha (II)"),
    (18, "inm", PANDU, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "husband_of", "M\u0101dr\u012b"),
    (19, "inm", PANDU, "P\u0101\u1e47\u1e0du", "P\u0101\u1e47\u1e0du", "father_of", "Yudhi\u1e63\u1e6dhira"),
    (20, "inm", ARJ2, "Arjuna[2]", "Yudhi\u1e63\u1e6dhira", "son_of", "Kunt\u012b"),
    (21, "inm", ARJ2, "Arjuna[2]", "Nakula", "son_of", "M\u0101dr\u012b"),
    (22, "inm", INDRA, "Indra", "Indra", "father_of", "Jayanta"),
    (23, "inm", INDRA, "Indra", "Indra", "father_of", "Devasen\u0101"),
    (24, "inm", DEVASENA, "Devasen\u0101", "Devasen\u0101", "daughter_of", "Indra"),
    (25, "inm", DEVASENA, "Devasen\u0101", "Devasen\u0101", "mother_of", "Guha"),
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make_shelf(t: Path):
    (t / "data" / "shelf").mkdir(parents=True)
    con = sqlite3.connect(str(t / "data" / "context.db"))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_variants (entity_id INTEGER, variant TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, lnum INTEGER, name TEXT, head TEXT, body TEXT);
    CREATE TABLE shelf_links (entry_id INTEGER, entity_id INTEGER, how TEXT);
    """)
    con.executemany("INSERT INTO shelf_entries VALUES (?,?,?,?,?,?)", ENTRIES)
    con.commit()
    con.close()
    k = sqlite3.connect(str(t / "data" / "shelf" / "kin.db"))
    k.executescript("""
    CREATE TABLE kin_done (entry_id INTEGER, source TEXT, entry_sha TEXT, read_id INTEGER, prompt_version TEXT,
                           engine TEXT);
    CREATE TABLE kin (id INTEGER PRIMARY KEY, read_id INTEGER, source TEXT, entry_id INTEGER, head TEXT, subject TEXT,
                      relation TEXT, object TEXT, words TEXT, refs TEXT, words_check TEXT, direction TEXT, at TEXT);
    CREATE TABLE kin_ties (kin_id INTEGER PRIMARY KEY, subject_entity INTEGER, object_entity INTEGER, how_subject TEXT,
                           how_object TEXT, verdict TEXT, passages INTEGER, texts INTEGER, places TEXT, scholar TEXT,
                           scholar_note TEXT, checked_at TEXT, mark TEXT);
    """)
    for kid, src, eid, head, subj, rel, obj in KIN:
        k.execute("INSERT INTO kin VALUES (?,1,?,?,?,?,?,?,'the words','[]','exact','agrees','')",
                  (kid, src, eid, head, subj, rel, obj))
        k.execute("INSERT INTO kin_ties (kin_id, verdict, passages, texts, places, scholar, scholar_note) "
                  "VALUES (?, 'not tied', 0, 0, '[]', '', '')", (kid,))
    k.executemany("INSERT INTO kin_done (entry_id, source, read_id, prompt_version, engine) VALUES (?,?,1,'v','e')",
                  sorted({(r[2], r[1]) for r in KIN}))
    k.commit()
    k.close()
    v = sqlite3.connect(str(t / "data" / "shelf" / "vamsa.db"))
    v.executescript("""
    CREATE TABLE vamsa_meta (k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE vamsa_texts (code TEXT PRIMARY KEY, title TEXT, edition TEXT, rights TEXT, member TEXT, sha256 TEXT,
                              verses INTEGER, show INTEGER);
    CREATE TABLE vamsa_rel (kin_id INTEGER PRIMARY KEY, source TEXT, entry_id INTEGER, cited TEXT, cites TEXT,
                            both_texts TEXT, best_text TEXT, best_ref TEXT, subject_form TEXT, object_form TEXT,
                            mbh INTEGER, mbh_first TEXT, hv INTEGER, hv_first TEXT, ram INTEGER, ram_first TEXT);
    CREATE TABLE vamsa_verses (text TEXT, ref TEXT, words TEXT, PRIMARY KEY (text, ref));
    """)
    v.commit()
    v.close()


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.t = Path(cls.td.name)
        make_shelf(cls.t)
        cls.db = str(cls.t / "data" / "context.db")
        cls.kin = str(cls.t / "data" / "shelf" / "kin.db")
        cls.store = str(cls.t / "data" / "shelf" / "vamsa.db")
        cls.vv = sys.modules.get("vamsa_view") or load(S / "vamsa_view.py", "vamsa_view")
        cls.vv._CACHE.clear()
        cls.vv.rv._CACHE.clear()
        cls.ix = load(S / "index_sync.py", "index_sync_heal")
        cls.g = cls.vv._graph(cls.db, cls.kin)
        cls.al = cls.vv.aliases(cls.db, cls.kin)
        cls.rows = cls.ix.build(cls.db, cls.kin, cls.store)

    @classmethod
    def tearDownClass(cls):
        cls.vv._CACHE.clear()
        cls.vv.rv._CACHE.clear()
        cls.td.cleanup()

    def person(self, src, e):
        return next(r for r in self.rows["persons"] if r["key"] == "%s:%d" % (src, e))


class TestRules(Fixture):
    def test_arjuna_up_through_pandu_not_indra(self):
        up = self.vv._main_up(self.g, "inm", ARJ2)
        self.assertEqual(up, [PANDU, ARJ2])
        self.assertNotIn(INDRA, up)
        self.assertEqual(self.vv._legal(self.g, ("inm", ARJ2)), {("inm", PANDU)})

    def test_the_begetter_stays_as_another_parent(self):
        tr = self.vv.tree(self.db, self.kin, self.store, "inm", ARJ2)
        me = tr["line"][tr["me"]]
        self.assertIn(INDRA, [p["entry"] for p in me["other_parents"]])
        via = self.vv.tree(self.db, self.kin, self.store, "inm", ARJ2, via=INDRA)   # "line through" Indra still works
        self.assertIn(INDRA, [r["entry"] for r in via["line"]])

    def test_down_from_the_begetter_not_into_another_fathers_line(self):
        self.assertNotIn(ARJ2, self.vv._main_down(self.g, "inm", INDRA))
        self.assertEqual(self.vv._main_down(self.g, "inm", PANDU)[:2], [ARJ2, ABHI])

    def test_down_a_son_before_a_daughter(self):
        # Devasena's line (to Guha) is the longer, but the line of descent goes through the son
        self.assertEqual(self.vv._main_down(self.g, "inm", INDRA), [JAYANTA])

    def test_a_name_of_several_entries_joined_by_the_names_they_share(self):
        ev = self.vv._evidence(self.g, self.vv._vamsa(self.store), "inm", PANDU, ARJ2)
        self.assertEqual(ev["joined"], "shared")   # Pandu's entry and the Pandava's both name Kunti, Madri, Yudhisthira
        self.assertNotIn(("inm", ARJ1), self.g["chi"].get(("inm", PANDU), set()))

    def test_no_line_turns_back(self):
        down = self.vv._main_down(self.g, "inm", DAKSA)
        self.assertEqual(down, [ADITI, VISNU, BRAHMAN, MARICI])   # not on to Kasyapa, Aditi's husband
        up = self.vv._main_up(self.g, "inm", INDRA)
        self.assertNotIn(ADITI, up[:up.index(KASY)] if KASY in up else up[:-1])

    def test_lines_are_the_rule(self):
        got = self.vv.lines(self.db, self.kin, min_len=2)["lines"]["inm"]
        self.assertTrue(got)
        for ln in got:
            for a, b in zip(ln["entries"], ln["entries"][1:]):
                lg = self.vv._legal(self.g, ("inm", b))
                self.assertTrue(not lg or ("inm", a) in lg, (a, b))
            # a father's line: no woman on it (Dakshas line to Aditi is not one)
            self.assertFalse([e for e in ln["entries"] if self.g["sex"].get(("inm", e)) == "f"], ln["heads"])


class TestAliases(Fixture):
    def test_kaunteya_is_arjuna(self):
        a = self.al[("inm", K1)]
        self.assertEqual(a["gloss"], "the son of Kunt\u012b")
        self.assertEqual([x["entry"] for x in a["same_as"]], [ARJ2])
        self.assertEqual(a["same_as"][0]["how"], "the only entry of that name with a line")

    def test_do_takes_the_gloss_before_it(self):
        a = self.al[("inm", K2)]
        self.assertEqual((a["gloss"], [x["entry"] for x in a["same_as"]]), ("the son of Kunt\u012b", [BHIMA]))
        self.assertEqual(a["same_as"][0]["how"], "the index's only entry of that name")

    def test_the_plural_names_the_singulars_persons(self):
        a = self.al[("inm", KPL)]
        self.assertEqual(a["gloss"], "the sons of Kunt\u012b")
        self.assertEqual(sorted(x["entry"] for x in a["same_as"]), sorted([ARJ2, BHIMA]))
        self.assertEqual({x["how"] for x in a["same_as"]}, {"the singular entries of this name"})

    def test_a_purana_index_name_of(self):
        a = self.al[("pui", DASARATHI)]
        self.assertEqual([x["entry"] for x in a["same_as"]], [RAMA2])

    def test_parse(self):
        p = self.vv._alias_parse
        self.assertEqual(p("inm", "(= Parik\u1e63it): I, 40")["targets"], ["Parik\u1e63it"])
        self.assertEqual(p("inm", "dual (\u02da\u012b) = R\u0101ma and Lak\u1e63ma\u1e47a: III")["targets"],
                         ["R\u0101ma", "Lak\u1e63ma\u1e47a"])
        self.assertEqual(p("inm", "= R\u0101ma[1], q.v.")["targets"], ["R\u0101ma[1]"])
        self.assertEqual(p("inm", "(No. 4) (whose contemplation) = No. 3. XII, 12864."), {})
        self.assertEqual(p("inm", "= \u201cthe Great Spirit\u201d: XII, 339"), {})
        self.assertEqual(p("inm", "son of Vy\u0101sa by Amb\u0101lik\u0101"), {})


class TestBuild(Fixture):
    def test_rows_carry_the_epithets(self):
        r = self.person("inm", K1)
        self.assertEqual(([x["entry"] for x in r["same_as"]], r["gloss"]), ([ARJ2], "the son of Kunt\u012b"))
        self.assertTrue(r["has_line"])
        d = self.person("inm", DHAN)   # an epithet of its own: no line, no spouse
        self.assertEqual((d["has_line"], d["spouses"], [x["entry"] for x in d["same_as"]]), (False, [], [ARJ2]))
        self.assertNotIn("same_as", self.person("inm", ARJ2))   # a row without an epithet is as it was

    def test_arjunas_row_runs_up_through_pandu(self):
        self.assertEqual(self.person("inm", ARJ2)["main_up"], [PANDU])

    def test_without_aliases_is_the_old_site(self):
        w = self.ix.without_aliases(self.rows)
        keys = {r["key"] for r in w["persons"]}
        self.assertNotIn("inm:%d" % DHAN, keys)
        k1 = next(r for r in w["persons"] if r["key"] == "inm:%d" % K1)
        self.assertNotIn("same_as", k1)
        self.assertEqual(k1["row_hash"], self.ix.finish({k: v for k, v in k1.items() if k != "row_hash"})["row_hash"])
        same = {r["key"]: r["row_hash"] for r in self.rows["persons"] if "same_as" not in r and "gloss" not in r}
        self.assertTrue(all(r["row_hash"] == same[r["key"]] for r in w["persons"] if r["key"] in same))

    def test_the_none_sink_waits_for_c26(self):
        got = self.ix.sync(self.rows, self.ix.NoneSink(), False, log=lambda *_: None)
        self.assertEqual(got["features_waiting"], ["aliases"])

    def test_c26_text(self):
        sql = C26.read_text(encoding="utf-8")
        self.assertTrue(all(ord(c) < 128 for c in sql))
        for s in ("C26_INDEX_ALIASES_2026_11_10", "ADD COLUMN IF NOT EXISTS same_as", "'features'",
                  "DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer)",
                  "GRANT EXECUTE ON FUNCTION %s TO authenticated", "-- B1 (before)", "-- A3 (after)"):
            self.assertIn(s, sql)
        self.assertEqual(sql.count("BEGIN;"), 1)
        self.assertEqual(sql.count("COMMIT;"), 1)


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN not set: a THROWAWAY PostgreSQL")
class TestSite(Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        cls.pg.execute("DROP SCHEMA IF EXISTS corpus CASCADE")
        # C26 changes find's columns: a find left by an earlier run is dropped, so C21 can make its own
        cls.pg.execute("DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer)")
        for f in BASE:
            cls.pg.execute(f.read_text(encoding="utf-8"))
        cls.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        cls.sink = cls.ix.PgSink(DSN)
        cls.before = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)   # C23 alone: the epithets wait
        cls.before_cols = cls.pg.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'corpus' AND "
            "table_name = 'index_persons' AND column_name = 'same_as'").fetchone()[0]
        cls.before_n = cls.pg.execute("SELECT count(*) FROM corpus.index_persons").fetchone()[0]
        sql = C26.read_text(encoding="utf-8")
        change = sql[sql.index("BEGIN;"):sql.index("COMMIT;") + len("COMMIT;")]
        for _ in range(2):
            cls.pg.execute(change)
        cls.after = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)

    @classmethod
    def tearDownClass(cls):
        cls.sink.con.close()
        cls.pg.execute("DROP FUNCTION IF EXISTS public.corpus_reader_index_find(text, text, integer)")   # as C21 found it
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

    def test_before_c26_the_rest_goes_and_is_verified(self):
        self.assertEqual((self.before["features_waiting"], self.before["waiting"]), (["aliases"], []))
        self.assertEqual(self.before["verified"]["tables_different"], [])
        self.assertEqual(self.before_cols, 0)
        self.assertEqual(self.before_n, len(self.ix.without_aliases(self.rows)["persons"]))

    def test_with_c26_the_epithets_go(self):
        self.assertEqual(self.after["features_waiting"], [])
        self.assertEqual(self.after["verified"]["tables_different"], [])
        n = self.pg.execute("SELECT count(*) FROM corpus.index_persons WHERE same_as <> '[]'::jsonb").fetchone()[0]
        self.assertEqual(n, sum(1 for r in self.rows["persons"] if r.get("same_as")))
        again = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual((again["sent"], again["deleted"]), (0, 0))
        man = self.pg.execute("SELECT public.corpus_index_manifest()").fetchone()[0]
        self.assertTrue(man["features"]["aliases"])

    def test_find_gives_the_epithet(self):
        got = self.call("SELECT entry, same_as, gloss, has_line FROM public.corpus_reader_index_find('dhananjaya', NULL, 20)")
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0][0], got[0][1][0]["entry"], got[0][3]), (DHAN, ARJ2, False))
        k = self.call("SELECT entry, same_as FROM public.corpus_reader_index_find('kaunteya', 'inm', 20)")
        self.assertEqual({e for e, _s in k}, {K1, K2, KPL})
        self.assertIn("ERROR", str(self.call("SELECT * FROM public.corpus_reader_index_find('kaunteya')", role="anon",
                                             uid=None)))

    def test_the_tree_gives_the_person_its_epithet(self):
        T = self.call("SELECT result FROM public.corpus_reader_index_tree('inm', %s, NULL, 2)", (K1,))[0][0]
        self.assertEqual([x["entry"] for x in T["person"]["same_as"]], [ARJ2])
        self.assertEqual(T["person"]["gloss"], "the son of Kunt\u012b")
        A = self.call("SELECT result FROM public.corpus_reader_index_tree('inm', %s, NULL, 2)", (ARJ2,))[0][0]
        self.assertEqual([r["entry"] for r in A["line"]][:2], [PANDU, ARJ2])
        self.assertEqual(A["person"]["same_as"], [])


# ---- CLAIMS_EPUB_2026_11_10: B. C. Law's Ancient Indian Tribes (1926), private reading ---------------------------
def make_epub(p: Path, pages: dict):
    """A made-up EPUB as the Internet Archive makes them: content.opf, page_N.html in the spine, image_000N_00.jpeg."""
    with zipfile.ZipFile(str(p), "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        items = "".join('<item id="chapter_%d" href="page_%d.html" media-type="application/xhtml+xml"/>' % (k, k)
                        for k in sorted(pages))
        spine = "".join('<itemref idref="chapter_%d"/>' % k for k in sorted(pages))
        z.writestr("EPUB/content.opf", '<package><manifest><item id="nav" href="nav.xhtml"/>%s</manifest>'
                                       '<spine><itemref idref="nav"/>%s</spine></package>' % (items, spine))
        for k, text in pages.items():
            z.writestr("EPUB/page_%d.html" % k, "<html><head><title>Page %d</title></head><body>%s</body></html>"
                       % (k, "".join("<p>%s</p>" % x for x in text.split("\n"))))
            z.writestr("EPUB/image_%04d_00.jpeg" % k, b"\xff\xd8JPEG%d" % k)


class TestLaw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc = load(S / "scholar_claims.py", "scholar_claims_law")
        cls.w = cls.sc.WORKS["law1926"]

    def test_the_work_is_private(self):
        self.assertFalse(self.w["licence"].lower().startswith("public domain"))
        self.assertIn("private reading", self.w["licence"])
        self.assertEqual((self.w["md5"], self.w["pdf_pages"], self.w["format"]),
                         ("20edab5f62d1d54bf6772339d99d41f6", 226, "epub"))

    def test_raychaudhuris_prompt_is_as_it_was(self):
        self.assertEqual(self.sc.system_for(self.sc.WORKS["phai1923"]), self.sc.SYSTEM)
        s = self.sc.system_for(self.w)
        self.assertIn("a print of 1926", s)
        self.assertNotIn("POLITICAL HISTORY OF INDIA", s)
        self.assertIn("scan", s[len(self.sc.SYSTEM) - 200:])

    def test_the_printed_pages(self):
        po, pd = self.sc.printed_of, self.sc.pdf_of
        self.assertEqual([po(self.w, n) for n in (12, 16, 39, 41, 42, 74, 131, 132, 146, 156, 210, 211)],
                         ["preface", "1", "24", "", "25", "55", "112", "117", "129", "137", "191", ""])
        self.assertEqual([pd(self.w, p) for p in ("1", "25", "113", "117", "191", "192", "preface")],
                         [16, 42, None, 132, 210, None, 12])
        self.assertEqual(self.sc.parse_pages(self.w, "1-3"), [16, 17, 18])
        with self.assertRaises(ValueError):
            self.sc.parse_pages(self.w, "113")

    def test_epub_pages_and_their_scans(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "b.epub"
            make_epub(p, {15: "The text on this page is estimated to be only 20.97% accurate ANCIENT INDIAN TRIBES 1\n"
                              "Divodasa, the son of Bhimasena, king of Kasi", 16: "2 THE KASIS\nPratardana &amp; Bhrgu",
                          17: ""})
            got = self.sc.extract_epub(p)
            self.assertEqual([n for n, _t in got], [16, 17, 18])
            self.assertEqual(got[0][1], "ANCIENT INDIAN TRIBES 1\nDivodasa, the son of Bhimasena, king of Kasi")
            self.assertEqual(got[1][1], "2 THE KASIS\nPratardana & Bhrgu")
            self.assertEqual(self.sc.page_image(self.w, p, 17), b"\xff\xd8JPEG16")
            self.assertEqual(self.sc.page_image(self.sc.WORKS["phai1923"], p, 17), b"")

    def test_a_page_is_read_with_its_scan(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            p = t / "b.epub"
            make_epub(p, {15: "ANCIENT INDIAN TRIBES 1\nDivodasa, the son of Bhimasena, king of Kasi, had a son"})
            db = t / "context.db"
            c = sqlite3.connect(str(db))
            c.executescript("CREATE TABLE usage_log (id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, doc TEXT, engine TEXT, "
                            "in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL, units INTEGER, duration_s REAL, "
                            "ok INTEGER, note TEXT);")
            c.commit()
            c.close()
            con = self.sc.open_store(str(t / "claims.db"))
            self.sc.store_pages(con, "law1926", self.w, self.sc.extract_epub(p), str(p))
            seen = []

            def caller(system, prompt, image=b""):
                seen.append((system, prompt, image))
                import types
                ns = types.SimpleNamespace
                return ns(text=json.dumps({"claims": [{"subject": "Divod\u0101sa", "relation": "son_of",
                                                         "object": "Bh\u012bmasena", "claim": "Divodasa was the son of "
                                                         "Bhimasena, king of Kasi.", "quote": "Divodasa, the son of "
                                                         "Bhimasena, king of Kasi", "cites": [], "stance": "asserts"}]}),
                          candidates=[ns(finish_reason="STOP")],
                          usage_metadata=ns(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=0,
                                            total_token_count=150))
            import usage_meter
            old = (usage_meter.budget_ok, usage_meter.meter)
            usage_meter.budget_ok = lambda *a, **k: True
            usage_meter.meter = lambda **k: 0.001
            try:
                a = type("A", (), {"model": "gemini-2.5-flash", "max_usd": 1.0, "db": str(db), "think": 0, "pdf": str(p)})
                todo = [r for r in con.execute("SELECT pdf_page, printed, text, sha256 FROM claim_pages")]
                got = self.sc.read_pages(a, con, "law1926", self.w, todo, caller)
            finally:
                usage_meter.budget_ok, usage_meter.meter = old
            self.assertEqual((got["read"], got["claims"], got["failed"]), (1, 1, 0))
            self.assertEqual(seen[0][2], b"\xff\xd8JPEG15")
            self.assertIn("a print of 1926", seen[0][0])
            row = con.execute("SELECT prompt_version FROM claim_reads").fetchone()
            self.assertEqual(row[0], "claims-v1-img")
            self.assertEqual(con.execute("SELECT quote_check, printed FROM claims").fetchone(), ("exact", "1"))
            self.assertEqual(set(self.sc.done_pages(con, "law1926", "gemini:gemini-2.5-flash", "claims-v1-img")), {16})
            self.assertEqual(self.sc.done_pages(con, "law1926", "gemini:gemini-2.5-flash"), {})
            con.close()

    def test_a_quote_the_ocr_put_inside_a_value(self):
        # Raychaudhuri p. 252 (pdf 270) was refused six times: the model copied the scan's "'uccessors as it is
        raw = ('{\n  "claims": [\n    {\n      "subject": "Kanishka and his successors",\n'
               '      "subject_printed": "Kanishka and his "\'uccessors",\n      "relation": "other",\n'
               '      "object": "",\n      "claim": "They kept the old way of dating.",\n'
               '      "quote": "Kanishka and his "\'uccessors adopted",\n      "cites": [\n'
               '        "Ep. Ind., XIY, p. 141"\n      ],\n      "stance": "asserts",\n      "hedge": "",\n'
               '      "who": ""\n    }\n  ]\n}')
        got = self.sc.parse_reply(raw)
        self.assertEqual(got[0]["subject_printed"], 'Kanishka and his "\'uccessors')
        self.assertEqual(got[0]["cites"], ["Ep. Ind., XIY, p. 141"])
        self.assertEqual(self.sc.parse_reply('{"claims": []}'), [])

    def test_a_work_in_copyright_is_never_the_historians_verdict(self):
        ki = load(S / "kin_index.py", "kin_index_law")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "claims.db"
            c = sqlite3.connect(str(p))
            c.executescript("""
            CREATE TABLE claim_works(code TEXT PRIMARY KEY, author TEXT, title TEXT, year TEXT, licence TEXT);
            CREATE TABLE claims(id INTEGER PRIMARY KEY, printed TEXT, relation TEXT, claim TEXT, work TEXT);
            CREATE TABLE claim_links(claim_id INTEGER, role TEXT, entity_id INTEGER);
            INSERT INTO claim_works VALUES ('phai1923', 'Hemchandra Raychaudhuri', 'Political History', '1923',
                                            'public domain: published 1923');
            INSERT INTO claim_works VALUES ('law1926', 'Bimala Churn Law', 'Ancient Indian Tribes', '1926',
                                            'in copyright in India to the end of 2029');
            INSERT INTO claims VALUES (1, '37', 'son_of', 'R says so.', 'phai1923');
            INSERT INTO claims VALUES (2, '5', 'son_of', 'Law says so.', 'law1926');
            INSERT INTO claim_links VALUES (1, 'subject', 1), (1, 'object', 2), (2, 'subject', 3), (2, 'object', 4);
            """)
            c.commit()
            c.close()
            ci = ki.claims_index(str(p))
            said = [x[2] for v in ci["pair"].values() for x in v]
            self.assertEqual(said, ["R says so."])


if __name__ == "__main__":
    unittest.main()
