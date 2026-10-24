# -*- coding: ascii -*-
"""RELATIONS_UI_2026_10_24: the dashboard's Relations page. scripts/relations_view.py reads, for one of our names,
whom our texts name it with (entity_links), what the indexes state of each person of that name, kept apart by entry
(Janamejaya (I), son of Puru; Janamejaya (II), son of Pariksit), the line of descent through each by the index's own
entries, and Raychaudhuri's claims; it opens every database read-only. The page and its wiring: /relations,
/api/relations, the links from the Ask page, the library and the dashboard. A made-up database in a temp folder;
never data/context.db, never the network."""
import ast, importlib.util, json, sqlite3, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VIEW = REPO / "scripts" / "relations_view.py"
PAGE = REPO / "scripts" / "relations.html"
DASH = REPO / "scripts" / "dashboard.py"
ASK = REPO / "scripts" / "ask.html"
HOME = REPO / "scripts" / "dashboard_static.html"
PAT = REPO / "scripts" / "patch_relations_ui_2026_10_24.py"
MARK = "RELATIONS_UI_2026_10_24"
JAN, PAR, SAT, ABH, PUR, YAY = 1, 2, 3, 4, 5, 6


def load():
    spec = importlib.util.spec_from_file_location("relations_view_t", str(VIEW))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make(t: Path):
    con = sqlite3.connect(str(t / "data" / "context.db"))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_variants (entity_id INTEGER, variant TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE entity_links (a INTEGER, b INTEGER, rel TEXT, passages INTEGER, texts INTEGER, docs TEXT,
                               places TEXT, built_at TEXT, mark TEXT, PRIMARY KEY (a, b, rel));
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, head TEXT, body TEXT);
    CREATE TABLE shelf_links (entry_id INTEGER, entity_id INTEGER, how TEXT);
    """)
    con.execute("INSERT INTO docs VALUES (1, 'MBh01')")
    con.executemany("INSERT INTO passages VALUES (?, 1)", [(1,), (2,), (3,)])
    con.executemany("INSERT INTO entities VALUES (?,?,?)", [
        (JAN, "Janamejaya", "person"), (PAR, "Par\u012bk\u1e63it", "person"), (SAT, "\u015aat\u0101n\u012bka", "person"),
        (ABH, "Abhimanyu", "person"), (PUR, "P\u016bru", "person"), (YAY, "Yay\u0101ti", "person")])
    con.execute("INSERT INTO entity_variants VALUES (?, 'Parikshit')", (PAR,))
    con.execute("INSERT INTO entity_variants VALUES (?, 'Puru')", (JAN,))     # an epithet: never ties Puru's entries
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)",
                    [(JAN, 1), (JAN, 2), (PAR, 1), (SAT, 2), (ABH, 3)])
    con.executemany("INSERT INTO entity_links VALUES (?,?,?,?,?,?,?,?,?)", [
        (JAN, PAR, "together", 1, 1, '["MBh01"]', '[[1, "MBh01", "1.89.47"]]', "", ""),
        (JAN, SAT, "near", 1, 1, '["MBh01"]', '[[2, "MBh01", "1.89.48"]]', "", "")])
    con.executemany("INSERT INTO shelf_entries (id, source, head) VALUES (?, 'pui', ?)", [
        (10, "Yay\u0101ti"), (11, "P\u016bru (I)"), (12, "P\u016bru (II)"), (13, "Janamejaya (I)"),
        (14, "Janamejaya (II)"), (16, "Abhimanyu"), (17, "Par\u012bk\u1e63it (I)"), (18, "\u015aat\u0101n\u012bka")])
    con.executemany("INSERT INTO shelf_links VALUES (?,?, 'exact')", [(13, JAN), (14, JAN)])
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
    rows = [  # id, entry, head, subject, relation, object, words, check, direction, s, o, verdict, scholar
        (1, 14, "Janamejaya (II)", "Janamejaya (II)", "son_of", "Par\u012bk\u1e63it (I)", "son of Par\u012bk\u1e63it",
         "exact", "agrees", JAN, PAR, "named together", "agrees"),
        (2, 14, "Janamejaya (II)", "Janamejaya (II)", "father_of", "\u015aat\u0101n\u012bka", "father of \u015aat\u0101n\u012bka",
         "exact", "agrees", JAN, SAT, "named near", ""),
        (3, 17, "Par\u012bk\u1e63it (I)", "Par\u012bk\u1e63it (I)", "son_of", "Abhimanyu", "son of Abhimanyu", "exact",
         "agrees", PAR, ABH, "both named, never near", ""),
        (4, 13, "Janamejaya (I)", "Janamejaya (I)", "son_of", "P\u016bru (I)", "son of P\u016bru", "exact", "agrees",
         JAN, PUR, "one not in our texts", ""),
        (5, 18, "\u015aat\u0101n\u012bka", "\u015aat\u0101n\u012bka", "son_of", "Janamejaya", "son of Janamejaya", "exact",
         "agrees", SAT, JAN, "named near", ""),
        (6, 11, "P\u016bru (I)", "P\u016bru (I)", "son_of", "Yay\u0101ti", "son of Yay\u0101ti", "exact", "agrees", PUR, YAY,
         "one not in our texts", ""),
        (7, 14, "Janamejaya (II)", "Janamejaya (II)", "brother_of", "Arjuna", "brother of Arjuna", "none", "agrees",
         JAN, None, "not tied", ""),                                                    # not in the entry: left out
    ]
    for (i, e, h, s, r, o, w, c, d, se, oe, v, sch) in rows:
        k.execute("INSERT INTO kin VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (i, 100 + e, "pui", e, h, s, r, o, w, '["V\u0101. 99"]',
                                                                      c, d, ""))
        k.execute("INSERT INTO kin_ties VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (i, se, oe, "", "", v, 1, 1,
                                                                            '["MBh01 1.89.47"]', sch, "p. 15", "", ""))
    for e in (11, 13, 14, 17, 18):
        k.execute("INSERT INTO kin_done VALUES (?, 'pui', 'x', ?, 'kin-v1', 'gemini:x')", (e, 100 + e))
    k.commit()
    k.close()
    c = sqlite3.connect(str(t / "data" / "shelf" / "claims.db"))
    c.executescript("""
    CREATE TABLE claim_reads (id INTEGER PRIMARY KEY, status TEXT, work TEXT, pdf_page INTEGER);
    CREATE TABLE claims (id INTEGER PRIMARY KEY, printed TEXT, relation TEXT, claim TEXT, stance TEXT, hedge TEXT,
                         read_id INTEGER);
    CREATE TABLE claim_links (claim_id INTEGER, role TEXT, entity_id INTEGER);
    """)
    c.executemany("INSERT INTO claim_reads VALUES (?,?,?,?)", [(1, "ok", "phai1923", 30), (2, "ok", "phai1923", 30)])
    c.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?)", [
        (1, "15", "son_of", "Janamejaya was the son of Parikshit.", "", "", 2),
        (2, "15", "son_of", "An older read of the same page.", "", "", 1)])
    c.executemany("INSERT INTO claim_links VALUES (?,?,?)", [(1, "subject", JAN), (2, "subject", JAN)])
    c.commit()
    c.close()


@unittest.skipUnless(VIEW.exists(), "scripts/relations_view.py is not here")
class TheView(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "shelf").mkdir(parents=True)
        make(t)
        self.m = load()
        self.db = str(t / "data" / "context.db")
        self.shelf = t / "data" / "shelf"

    def tearDown(self):
        self.td.cleanup()

    def test_find(self):
        got = self.m.find(self.db, "janam")
        self.assertEqual(got[0]["name"], "Janamejaya")
        self.assertEqual(self.m.find(self.db, "Pariksit")[0]["via"], "name", "the diacritics folded")
        got = self.m.find(self.db, "Parikshit")[0]
        self.assertEqual((got["id"], got["via"], got["exact"]), (PAR, "variant", False), "a variant finds the name")
        self.assertEqual(self.m.find(self.db, "")[0]["name"], "Janamejaya", "no text: the most named first")

    def test_the_view(self):
        v = self.m.view(self.db, JAN, self.shelf)
        self.assertEqual((v["entity"]["name"], v["entity"]["mentions"], v["entity"]["texts"]), ("Janamejaya", 2, 1))
        self.assertEqual([(x["name"], x["passages"]) for x in v["together"]], [("Par\u012bk\u1e63it", 1)])
        self.assertEqual(v["together"][0]["places"], [{"doc": "MBh01", "ref": "1.89.47"}])
        self.assertEqual([x["name"] for x in v["near"]], ["\u015aat\u0101n\u012bka"])
        heads = {p["head"]: p for p in v["persons"]}
        self.assertEqual(set(heads), {"Janamejaya (I)", "Janamejaya (II)"},
                         "the two persons apart; Puru's entries not his, though Puru is one of his forms")
        two = heads["Janamejaya (II)"]
        self.assertEqual(sorted(x["relation"] for x in two["own"]), ["father_of", "son_of"], "the unkept one left out")
        self.assertEqual([x["stated_in"] for x in two["named_in"]], ["\u015aat\u0101n\u012bka"],
                         "Satanika's entry names him (the one Janamejaya that names Satanika)")
        self.assertEqual([[n["head"] for n in g] for g in two["up"]], [["Par\u012bk\u1e63it (I)"], ["Abhimanyu"]])
        self.assertEqual([[(n["head"], n["both"]) for n in g] for g in two["down"]], [[("\u015aat\u0101n\u012bka", True)]])
        one = heads["Janamejaya (I)"]
        self.assertEqual([[n["head"] for n in g] for g in one["up"]], [["P\u016bru (I)"], ["Yay\u0101ti"]])
        self.assertEqual(one["down"], [], "Satanika is not his son")
        son = [x for x in two["own"] if x["relation"] == "son_of"][0]
        self.assertEqual((son["verdict"], son["raychaudhuri"], son["other_entity"], son["group"]),
                         ("named together", "agrees", PAR, "family"))
        self.assertEqual(v["claims"], [{"page": "15", "relation": "son_of", "claim": "Janamejaya was the son of Parikshit.",
                                        "source": self.m.CLAIMS_SOURCE}], "the latest read of the page only")
        json.dumps(v)

    def test_read_only_and_missing(self):
        before = (self.t / "data" / "context.db").stat().st_mtime_ns
        self.m.view(self.db, JAN, self.shelf)
        self.assertEqual((self.t / "data" / "context.db").stat().st_mtime_ns, before)
        self.assertEqual(self.m.view(self.db, 999, self.shelf)["error"], "no such name")
        (self.shelf / "kin.db").unlink()
        (self.shelf / "claims.db").unlink()
        m2 = load()
        v = m2.view(self.db, JAN, self.shelf)
        self.assertEqual((v["persons"], v["claims"], v["read"]["claims"]), ([], [], False), "without the shelf")


class TheWiring(unittest.TestCase):
    def test_the_page(self):
        if not PAGE.exists():
            self.skipTest("relations.html is not here")
        s = PAGE.read_text(encoding="ascii")
        self.assertIn(MARK, s)
        for x in ('"/api/relations?"', 'id="graph"', "named together only", "Line of descent in the",
                  "never through another person of the same name", 'data-f="src" data-v="vei"', "Raychaudhuri"):
            self.assertIn(x, s, x)
        self.assertNotIn("<script src", s, "no script from elsewhere")

    def test_the_routes_and_links(self):
        src = DASH.read_text(encoding="utf-8")
        if MARK not in src:
            self.skipTest("RELATIONS_UI_2026_10_24 is not applied to scripts/dashboard.py here")
        tree = ast.parse(src)
        fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for name, route in (("relations_page", "/relations"), ("api_relations", "/api/relations")):
            self.assertIn(name, fns)
            decos = [ast.get_source_segment(src, d) for d in fns[name].decorator_list]
            self.assertIn('app.get("%s")' % route, decos)
        body = ast.get_source_segment(src, fns["api_relations"])
        self.assertIn("rv.view(db, eid", body)
        self.assertIn('rv.find(db, request.args.get("find", "")', body)
        self.assertIn('href="/relations"', src, "the library links it")
        self.assertIn('href="/relations"', ASK.read_text(encoding="utf-8"))
        self.assertIn('"<div><a href=\\"/relations?name=" + encodeURIComponent(n.name)', ASK.read_text(encoding="utf-8"),
                      "the Professor's names lead to the page")
        self.assertIn('href="/relations" target="_blank"', HOME.read_text(encoding="utf-8"))

    def test_ascii_and_marks(self):
        for f in (VIEW, PAGE, PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
