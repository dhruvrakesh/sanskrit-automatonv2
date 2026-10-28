# -*- coding: ascii -*-
"""INDEX_SITE_2026_10_25: the indexes' genealogies on the site. scripts/index_sync.py computes, from the stores the
dashboard's Vamsa page reads (context.db, kin.db, vamsa.db; read-only), the rows of docs/cloud/C21 (the persons and
their lines, the steps with their evidence, every kept relation, the longest lines, the GRETIL verses, the run), and
sends what differs; the site reads them through C21's reader functions (signed-in readers only, the C5 gate).

The made-up shelf of tests/test_vamsa_2026_10_25.py (Raghu -> Aja -> Dasaratha (II) -> Rama (II) -> Kusa -> Atithi,
Soerensen's Janamejaya son of Pariksit, the Mahabharata e-text never shown), with four rows more: Laksmana (I) son of
Dasaratha (II) (a brother on the line), Rama (II) son of Kausalya (a mother the index has no entry for), Atithi's row
twice (one statement, counted twice), and Dasaratha (II) son of Aja (IV) tied to our names with a passage where both
stand. Never data/context.db, never the network, no model.

TestBuild runs without a database. TestSite is skipped unless CORPUS_TEST_DSN names a THROWAWAY PostgreSQL you own
(it applies the Supabase stand-ins, C4, C4b, C5 and C21 twice); never the live one."""
import contextlib, copy, gzip, hashlib, io, json, os, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
for p in (str(S), str(REPO), str(Path(__file__).resolve().parent)):
    if p not in sys.path:
        sys.path.insert(0, p)
from tests.test_vamsa_2026_10_25 import make_db, make_zip, load, CHECK  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
C21 = CLOUD / "C21_index_site_2026-10-25.sql"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql", C21, C21]
INDEX_TABLES = ["index_texts", "index_persons", "index_steps", "index_statements", "index_lines", "index_verses",
                "index_meta"]
U1 = "11111111-1111-1111-1111-111111111111"
MARK = "INDEX_SITE_2026_10_25"
DASA2, RAMA2, LAKS1, ATITHI, AJA, RAGHU, KUSA = 13, 14, 17, 16, 11, 10, 15
EPIC_WORDS = "janamejaya\u1e25 p\u0101rik\u1e63ita\u1e25"     # the made-up Mahabharata line: never sent


def extend(t: Path):
    """The fixture's four rows more, and our names and a passage for one step."""
    con = sqlite3.connect(str(t / "data" / "context.db"))
    con.executescript("""
    ALTER TABLE passages ADD COLUMN page_no INTEGER;
    ALTER TABLE passages ADD COLUMN idx INTEGER;
    CREATE TABLE entity_links (a INTEGER, b INTEGER, rel TEXT, passages INTEGER, texts INTEGER, places TEXT);
    """)
    con.execute("INSERT INTO shelf_entries (id, source, head) VALUES (17, 'pui', 'Lak\u1e63ma\u1e47a (I)')")
    con.execute("INSERT INTO entities VALUES (2, 'Aja', 'person')")
    con.execute("INSERT INTO shelf_links VALUES (11, 2, 'exact')")
    con.execute("INSERT INTO docs VALUES (1, 'vishnu_purana')")
    con.execute("INSERT INTO docs VALUES (2, 'withdrawn_text')")
    con.executemany("INSERT INTO passages (id, doc_id, page_no, idx) VALUES (?, ?, ?, ?)",
                    [(100, 1, 7, 3), (101, 2, 1, 1), (102, 9, 1, 1)])
    # the first place is in a text withdrawn from the site, the third in one the desk no longer has: neither is sent
    con.execute("INSERT INTO entity_links VALUES (1, 2, 'together', 3, 3, ?)",
                (json.dumps([[101, "withdrawn_text", "1.1"], [100, "vishnu_purana", "4.4.86"],
                             [102, "not_here", "2.2"]]),))
    con.commit()
    con.close()
    k = sqlite3.connect(str(t / "data" / "shelf" / "kin.db"))
    rows = [  # id, entry, head, relation, object, refs
        (12, LAKS1, "Lak\u1e63ma\u1e47a (I)", "son_of", "Da\u015baratha (II)", ["Vi. IV. 4. 87"]),
        (13, RAMA2, "R\u0101ma (II)", "son_of", "Kausaly\u0101", ["Bh\u0101. IX. 10. 2"]),
        (14, ATITHI, "Atithi (I)", "son_of", "Ku\u015ba (I)", ["V\u0101. 88. 199"]),
    ]
    for kid, eid, head, rel, obj, refs in rows:
        k.execute("INSERT INTO kin VALUES (?,1,'pui',?,?,?,?,?,?,?,'exact','agrees','')",
                  (kid, eid, head, head, rel, obj, "the words", json.dumps(refs, ensure_ascii=False)))
        k.execute("INSERT INTO kin_ties (kin_id, verdict, passages, texts, places, scholar, scholar_note) "
                  "VALUES (?, 'not tied', 0, 0, '[]', '', '')", (kid,))
    k.execute("INSERT INTO kin_done (entry_id, source, read_id, prompt_version, engine) VALUES (?, 'pui', 1, 'v', 'e')",
              (LAKS1,))
    k.execute("UPDATE kin_ties SET subject_entity = 1, object_entity = 2, verdict = 'together', passages = 1, "
              "texts = 1 WHERE kin_id = 2")
    k.commit()
    k.close()


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.t = Path(cls.td.name)
        (cls.t / "data" / "shelf").mkdir(parents=True)
        cls.old_verdicts = os.environ.get("SA_SOURCE_VERDICTS")
        os.environ["SA_SOURCE_VERDICTS"] = str(cls.t / "source_verdicts.jsonl")   # never the PC's own register
        (cls.t / "source_verdicts.jsonl").write_text('{"doc": "withdrawn_text", "status": "withdrawn"}\n',
                                                     encoding="utf-8")
        make_zip(cls.t / "1_sanskr.zip")
        make_db(cls.t)
        extend(cls.t)
        cls.db = cls.t / "data" / "context.db"
        cls.kin = cls.t / "data" / "shelf" / "kin.db"
        cls.store = cls.t / "data" / "shelf" / "vamsa.db"
        vc = load(CHECK, "vamsa_check_ix")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = vc.main(["--zip", str(cls.t / "1_sanskr.zip"), "--kin", str(cls.kin), "--store", str(cls.store),
                          "--exports", str(cls.t / "exports"), "--yes"])
        assert rc == 0, "vamsa_check failed on the fixture"
        cls.before = (md5(cls.db), md5(cls.kin), md5(cls.store))
        cls.ix = load(S / "index_sync.py", "index_sync")
        cls.vv = sys.modules.get("vamsa_view") or load(S / "vamsa_view.py", "vamsa_view")
        cls.rows = cls.ix.build(str(cls.db), str(cls.kin), str(cls.store))

    @classmethod
    def tearDownClass(cls):
        if cls.old_verdicts is None:
            os.environ.pop("SA_SOURCE_VERDICTS", None)
        else:
            os.environ["SA_SOURCE_VERDICTS"] = cls.old_verdicts
        cls.td.cleanup()

    def by_key(self, table):
        return {r["key"]: r for r in self.rows[table]}


class TestBuild(Fixture):
    def test_tables_and_run(self):
        self.assertEqual(sorted(self.rows), sorted(self.ix.TABLES))
        run = self.rows["meta"][0]
        # B2_SITE_2026_10_28: the scheme is index_sync's own (i2 adds the scholars' claims)
        self.assertEqual((run["key"], run["value"]["mark"], run["value"]["scheme"]), ("run", MARK, self.ix.SCHEME))
        self.assertIn(self.ix.SCHEME, ("i1", "i2"))
        self.assertEqual(run["value"]["counts"], {t: len(self.rows[t]) for t in self.ix.TABLES if t != "meta"})
        for t in self.ix.TABLES:
            keys = [r["key"] for r in self.rows[t]]
            self.assertEqual(len(keys), len(set(keys)), t)
            for r in self.rows[t]:
                self.assertRegex(r["row_hash"], "^[0-9a-f]{32}$")

    def test_the_line_the_desk_draws(self):
        P = self.by_key("persons")
        d = P["pui:%d" % DASA2]
        self.assertEqual(d["head"], "Da\u015baratha (II)")
        self.assertEqual(d["fold"], "dasaratha")
        self.assertEqual(d["main_up"], [RAGHU, AJA])
        self.assertEqual(d["main_down"][:2], [RAMA2, KUSA])
        self.assertEqual(d["canonical"], "Da\u015baratha")                 # our name, by the exact shelf link
        self.assertTrue(d["has_line"])
        r = P["pui:%d" % RAMA2]
        self.assertEqual(r["main_up"], [RAGHU, AJA, DASA2], "the father's line, not the mother's")
        self.assertEqual(r["parents_n"], 2)
        T = self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", DASA2)
        self.assertEqual([x["entry"] for x in T["line"]], d["main_up"] + [DASA2] + d["main_down"])

    def test_a_mother_without_an_entry(self):
        P = self.by_key("persons")
        mothers = [p for p in P.values() if p["source"] == "pui" and p["entry"] < 0
                   and p["head"].startswith("Kausaly")]
        self.assertTrue(mothers, "the named-only parent is a person of its own")
        self.assertTrue(all(m["named_only"] for m in mothers))
        steps = self.by_key("steps")
        self.assertTrue(any(s["child"] == RAMA2 and s["parent"] < 0 for s in steps.values()))

    def test_steps_carry_their_evidence(self):
        st = self.by_key("steps")["pui:%d:%d" % (AJA, DASA2)]
        self.assertEqual(st["cited"], "both")                               # Vi. IV. 4. 86 names both
        self.assertIn("vi|4.4.86", st["verse_keys"])
        S_ = self.by_key("statements")
        self.assertTrue(st["statements"])
        for k in st["statements"]:
            self.assertIn(k, S_)
        s = S_[st["statements"][0]]
        self.assertEqual((s["subject"], s["relation"], s["object"]), ("Da\u015baratha (II)", "son_of", "Aja (IV)"))
        self.assertEqual(s["refs"], ["Vi. IV. 4. 86"])
        self.assertEqual((s["subject_canonical"], s["object_canonical"]), ("Da\u015baratha", "Aja"))
        self.assertEqual(s["places"], [{"doc": "vishnu_purana", "page": 7, "idx": 3, "ref": "4.4.86"}],
                         "only the texts the mirror carries")
        self.assertEqual(s["ours"], "together")
        vi = [c for c in s["cites"] if c.get("text") == "vi"]
        self.assertTrue(vi and vi[0]["verdict"] == "both" and vi[0].get("subject_form") and vi[0].get("object_form"),
                        s["cites"])
        V = self.by_key("verses")
        self.assertEqual(V["vi|4.4.86"]["words"], "aj\u0101d da\u015baratha\u1e25")

    def test_one_statement_counted_twice(self):
        n = [s for s in self.rows["statements"] if s["subject"] == "Atithi (I)" and s["object"] == "Ku\u015ba (I)"]
        self.assertEqual(len(n), 1)
        self.assertEqual(n[0]["n"], 2)

    def test_every_relation_kept_not_only_kinship(self):
        rels = {s["relation"] for s in self.rows["statements"]}
        self.assertTrue({"son_of", "father_of", "married", "king_of"} <= rels, rels)

    def test_rights_and_the_epic(self):
        T = self.by_key("texts")
        for code in ("pui", "vei", "inm"):
            self.assertIn("CC BY-NC-SA 3.0", T["index:" + code]["rights"])
            self.assertIn("Cologne", T["index:" + code]["edition"])
        self.assertFalse(T["text:mbh"]["show"])
        self.assertTrue(T["text:vi"]["show"])
        self.assertFalse([k for k in self.by_key("verses") if k.startswith("mbh|")])
        for st in self.rows["steps"]:
            self.assertFalse([k for k in st["verse_keys"] if k.startswith("mbh|")])
        blob = json.dumps(self.rows, ensure_ascii=False)
        self.assertNotIn(EPIC_WORDS, blob, "the Mahabharata e-text's words never leave the desk")
        self.assertNotIn("p\u0101rik\u1e63ita\u1e25 parik\u1e63ita\u1e25", blob)

    def test_deterministic_and_read_only(self):
        again = self.ix.build(str(self.db), str(self.kin), str(self.store))
        for t in self.ix.TABLES:
            self.assertEqual([(r["key"], r["row_hash"]) for r in again[t]],
                             [(r["key"], r["row_hash"]) for r in self.rows[t]], t)
        self.assertEqual((md5(self.db), md5(self.kin), md5(self.store)), self.before)

    def test_digest_is_the_servers(self):
        pairs = [("b", "2"), ("a", "1"), ("a:2", "3")]
        self.assertEqual(self.ix.digest(pairs), hashlib.md5(b"a:1,a:2:3,b:2").hexdigest())
        self.assertEqual(self.ix.digest([]), hashlib.md5(b"").hexdigest())

    def test_chunks_keep_the_ceilings(self):
        rows = [{"key": str(i), "w": "x" * 100} for i in range(2500)]
        parts = list(self.ix.chunks(rows))
        self.assertEqual(sum(len(p) for p in parts), 2500)
        self.assertTrue(all(len(p) <= self.ix.MAX_ROWS for p in parts))

    def test_cli_plan_and_dump(self):
        import corpus_sync as cs
        old = cs.load_config
        cs.load_config = lambda *a, **k: {}                                  # the PC's .env is not read into the tests
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = self.ix.main(["--db", str(self.db), "--kin-db", str(self.kin), "--vamsa-db", str(self.store),
                                   "--sink", "none"])
        finally:
            cs.load_config = old
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("VERDICT: the plan:", out.getvalue())
        self.assertIn("(no network: --sink none)", out.getvalue())
        dump = self.t / "exports" / "index_site.json.gz"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = self.ix.main(["--db", str(self.db), "--kin-db", str(self.kin), "--vamsa-db", str(self.store),
                               "--dump", str(dump)])
        self.assertEqual(rc, 0)
        got = json.loads(gzip.decompress(dump.read_bytes()).decode("utf-8"))
        self.assertEqual(len(got["persons"]), len(self.rows["persons"]))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = self.ix.main(["--db", str(self.t / "nothing.db"), "--sink", "none"])
        self.assertEqual(rc, 1)
        self.assertIn("VERDICT: refused", out.getvalue())

    def test_the_scheduled_tick_waits_quietly(self):
        import corpus_sync as cs
        old = cs.load_config
        cs.load_config = lambda *a, **k: {}                                  # never the PC's .env, never the network
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = self.ix.main(["--apply", "--if-configured", "--db", str(self.db), "--kin-db", str(self.kin),
                                   "--vamsa-db", str(self.store)])
        finally:
            cs.load_config = old
        self.assertEqual(rc, 0)
        self.assertIn("VERDICT: not configured", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = self.ix.main(["--if-configured", "--sink", "none", "--db", str(self.t / "nothing.db")])
        self.assertEqual(rc, 0, "a store not there yet is not a failure of the tick")
        self.assertTrue(self.ix.not_ready("corpus-index is not deployed yet (HTTP 404): ask Lovable to deploy"))
        self.assertTrue(self.ix.not_ready('corpus-index HTTP 422: {"ok":false,"error":"corpus_index_manifest: Could not '
                                          'find the function public.corpus_index_manifest without parameters in the '
                                          'schema cache"}'))
        self.assertFalse(self.ix.not_ready("corpus-index HTTP 401: bad signature"))
        self.assertFalse(self.ix.not_ready("corpus-index unreachable: timed out"))

    def test_source_is_ascii_and_marked(self):
        raw = (S / "index_sync.py").read_bytes()
        self.assertTrue(all(b < 128 for b in raw))
        self.assertIn(MARK.encode(), raw)
        sql = C21.read_bytes()
        self.assertIn(b"C21_INDEX_SITE_2026_10_25", sql)
        self.assertNotIn(b"anthropic", sql.lower())


@unittest.skipUnless(DSN and C21.exists(), "CORPUS_TEST_DSN is not set (a throwaway PostgreSQL)")
class TestSite(Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        for f in FILES:
            cls.pg.execute(f.read_text(encoding="utf-8"))
        cls.pg.execute("TRUNCATE %s" % ", ".join("corpus." + t for t in INDEX_TABLES))
        cls.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")
        cls.sink = cls.ix.PgSink(DSN)
        cls.first = cls.ix.sync(cls.rows, cls.sink, True, log=lambda *_: None)

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

    def tree(self, entry, via=None, down=2, source="pui"):
        got = self.call("SELECT result FROM public.corpus_reader_index_tree(%s, %s, %s, %s)", (source, entry, via, down))
        self.assertIsInstance(got, list, got)
        return got[0][0]

    def test_sent_and_verified_then_nothing_to_send(self):
        self.assertEqual(self.first["verified"]["tables_different"], [], self.first)
        self.assertEqual(self.first["sent"], sum(len(self.rows[t]) for t in self.ix.TABLES))
        again = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual((again["sent"], again["deleted"], again["changed"]), (0, 0, 0))
        n = dict(self.pg.execute("SELECT 'persons', count(*) FROM corpus.index_persons").fetchall())
        self.assertEqual(n["persons"], len(self.rows["persons"]))

    def test_tree_is_the_desks(self):
        T = self.tree(DASA2)
        D = self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", DASA2)
        self.assertEqual([r["entry"] for r in T["line"]], [r["entry"] for r in D["line"]])
        self.assertEqual([r["head"] for r in T["line"]][:3], ["Raghu (I)", "Aja (IV)", "Da\u015baratha (II)"])
        self.assertEqual(T["me"], D["me"])
        self.assertEqual(T["line"][T["me"]]["generation"], 0)
        self.assertEqual(T["line"][0]["generation"], -T["me"])
        self.assertEqual(T["title"], self.by_key("texts")["index:pui"]["title"])
        st = T["steps"][1]
        self.assertEqual((st["parent"], st["child"], st["cited"]), (AJA, DASA2, "both"))
        self.assertEqual(st["items"][0]["places"], [{"doc": "vishnu_purana", "page": 7, "idx": 3, "ref": "4.4.86"}])
        self.assertEqual(T["verses"]["vi|4.4.86"], "aj\u0101d da\u015baratha\u1e25")
        self.assertTrue(T["texts"]["vi"]["show"])
        self.assertFalse(T["texts"]["mbh"]["show"])
        self.assertNotIn(EPIC_WORDS, json.dumps(T, ensure_ascii=False))
        rama = T["line"][T["me"] + 1]
        self.assertEqual(rama["entry"], RAMA2)
        self.assertEqual([s["entry"] for s in rama["siblings"]], [LAKS1])
        self.assertEqual(rama["siblings_n"], 1)
        self.assertTrue(rama["other_parents"] and rama["other_parents"][0]["named_only"])
        self.assertIn("evidence", rama["other_parents"][0])
        kids = T["down"][0]
        self.assertEqual(sorted(k["entry"] for k in kids), sorted([RAMA2, LAKS1]))
        self.assertTrue(next(k for k in kids if k["entry"] == RAMA2)["on_line"])
        self.assertFalse(next(k for k in kids if k["entry"] == LAKS1)["on_line"])
        self.assertTrue(all(k["of"] == DASA2 for k in kids))

    def test_every_persons_tree_is_the_desks(self):
        for p in self.rows["persons"]:
            if not p["has_line"]:
                continue
            T = self.tree(p["entry"], source=p["source"])
            D = self.vv.tree(str(self.db), str(self.kin), str(self.store), p["source"], p["entry"])
            self.assertEqual([r["entry"] for r in T["line"]], [r["entry"] for r in D["line"]], p["key"])
            self.assertEqual(T["me"], D["me"], p["key"])

    def test_via_the_other_parent(self):
        mother = next(s["parent"] for s in self.rows["steps"] if s["child"] == RAMA2 and s["parent"] < 0)
        T = self.tree(RAMA2, via=mother)
        D = self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", RAMA2, via=mother)
        self.assertEqual([r["entry"] for r in T["line"]], [r["entry"] for r in D["line"]])
        self.assertEqual(T["line"][T["me"] - 1]["entry"], mother)
        self.assertEqual([r["entry"] for r in self.tree(RAMA2, via=999)["line"]],
                         [r["entry"] for r in self.tree(RAMA2)["line"]], "a via that is no parent is ignored")
        self.assertEqual(self.tree(99999), {"error": "no such person in the index"})

    def test_down_is_capped(self):
        self.assertEqual(self.tree(RAGHU, down=0)["down"], [])
        self.assertLessEqual(len(self.tree(RAGHU, down=99)["down"]), 4)

    def test_find(self):
        got = self.call("SELECT source, entry, head, exact FROM public.corpus_reader_index_find(%s, NULL, 10)",
                        ("dasa",))
        self.assertEqual(got[0][:2], ("pui", DASA2), got)                  # the longer line first
        self.assertFalse(any(r[3] for r in got), "a prefix is not the name")
        got = self.call("SELECT entry, exact FROM public.corpus_reader_index_find(%s, 'pui', 10)", ("dasaratha",))
        self.assertEqual(got[0], (DASA2, True))
        self.assertTrue(all(r[1] for r in got))
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_index_find(%s, NULL, 10)", ("d",)), [])
        got = self.call("SELECT entry FROM public.corpus_reader_index_find(%s, 'inm', 10)", ("janam",))
        self.assertEqual(got, [(20,)])
        self.assertEqual(len(self.call("SELECT * FROM public.corpus_reader_index_find(%s, NULL, 999)", ("a",))), 0)

    def test_lines_and_overview(self):
        L = self.call("SELECT source, rank, heads FROM public.corpus_reader_index_lines('pui')")
        self.assertEqual(L[0][:2], ("pui", 1))
        self.assertEqual(L[0][2][0], "Raghu (I)")
        O = self.call("SELECT result FROM public.corpus_reader_index_overview()")[0][0]
        self.assertEqual([s["source"] for s in O["sources"]], ["inm", "pui", "vei"])
        pui = next(s for s in O["sources"] if s["source"] == "pui")
        self.assertEqual(pui["persons"], len([p for p in self.rows["persons"] if p["source"] == "pui" and p["has_line"]]))
        self.assertNotIn("mbh", [x["code"] for x in O["texts"] if x["show"]])
        self.assertIn("CC BY-NC-SA 3.0", pui["rights"])
        self.assertEqual(O["run"]["mark"], MARK)
        self.assertIn("synced_at", O["run"])

    def test_a_name_of_ours(self):
        N = self.call("SELECT result FROM public.corpus_reader_index_of_name(%s)", ("Da\u015baratha",))[0][0]
        self.assertIn(("pui", DASA2), [(p["source"], p["entry"]) for p in N["persons"]])
        self.assertGreaterEqual(N["statements_n"], 1)
        s = next(x for x in N["statements"] if x["object"] == "Aja (IV)")
        self.assertEqual(s["places"][0]["doc"], "vishnu_purana")
        self.assertEqual(s["source"], "pui")
        ranks = [0 if x["relation"] in ("son_of", "father_of", "mother_of", "daughter_of") else
                 1 if x["relation"] in ("married", "wife_of", "husband_of") else 9 for x in N["statements"]]
        self.assertEqual(ranks, sorted(ranks), "the family first, then marriage, then the rest")
        N2 = self.call("SELECT result FROM public.corpus_reader_index_of_name(%s)", ("nobody",))[0][0]
        self.assertEqual((N2["persons"], N2["statements"], N2["statements_n"]), ([], [], 0))

    def test_the_gate_and_the_service_door(self):
        for sql in ("SELECT public.corpus_reader_index_overview()",
                    "SELECT public.corpus_reader_index_tree('pui', 13, NULL, 2)"):
            self.assertTrue(str(self.call(sql, role="anon", uid=None)).startswith("ERROR"), sql)
            self.assertTrue(str(self.call(sql, role="authenticated", uid=None)).startswith("ERROR"), sql)
        for sql in ("SELECT public.corpus_index_manifest()", "SELECT public.corpus_index_keys('persons')",
                    "SELECT public.corpus_index_delete('persons', '[\"pui:13\"]'::jsonb)"):
            self.assertIn("permission denied", str(self.call(sql)), sql)
            self.assertIn("permission denied", str(self.call(sql, role="anon", uid=None)), sql)
        self.assertIn("permission denied", str(self.call("SELECT count(*) FROM corpus.index_persons")))
        self.assertIsInstance(self.call("SELECT public.corpus_index_manifest()", role="service_role", uid=None), list)
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")
        try:
            self.assertTrue(str(self.call("SELECT public.corpus_reader_index_overview()")).startswith("ERROR"))
        finally:
            self.pg.execute("UPDATE corpus.reader_access SET mode = 'signed_in'")

    def test_ingest_refuses_bad_calls(self):
        self.assertIn("unknown table", str(self.call("SELECT public.corpus_index_keys('passages')",
                                                       role="service_role", uid=None)))
        self.assertIn("JSON array", str(self.call("SELECT public.corpus_index_ingest('persons', '{}'::jsonb)",
                                                    role="service_role", uid=None)))

    def test_a_row_gone_from_the_desk_is_deleted_and_comes_back(self):
        rows = copy.deepcopy(self.rows)
        gone = "pui:%d" % ATITHI
        rows["persons"] = [r for r in rows["persons"] if r["key"] != gone]
        rows["lines"][0] = self.ix.finish({k: v for k, v in rows["lines"][0].items() if k != "row_hash"} |
                                          {"length": rows["lines"][0]["length"] + 100})
        old = self.ix.MAX_ROWS
        self.ix.MAX_ROWS = 3                                                # several chunks a table
        try:
            got = self.ix.sync(rows, self.sink, True, log=lambda *_: None)
        finally:
            self.ix.MAX_ROWS = old
        self.assertEqual(got["verified"]["tables_different"], [])
        self.assertEqual((got["deleted"], got["changed"]), (1, 1))
        self.assertEqual(self.pg.execute("SELECT count(*) FROM corpus.index_persons WHERE key = %s",
                                         (gone,)).fetchone()[0], 0)
        back = self.ix.sync(self.rows, self.sink, True, log=lambda *_: None)
        self.assertEqual(back["verified"]["tables_different"], [])
        self.assertEqual((back["sent"], back["deleted"]), (2, 0))


if __name__ == "__main__":
    unittest.main()
