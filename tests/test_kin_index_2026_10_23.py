# -*- coding: ascii -*-
"""RELATIONS_INDEX_2026_10_23: scripts/kin_index.py reads the kinships the indexes state (R2) and checks them (R3):
the plan writes nothing; a read is metered, stops at --max-usd and resumes; a relation is kept only when its words
stand in the entry and its direction agrees with them, and an unnamed person is never an object; the names are tied
(the entry's head by the shelf's link); each kept pair is set beside our verses (together, near, never near, not ours)
and beside Raychaudhuri's claims (agrees, reversed); the exports are written. A made-up database and a stub model in a
temp folder; never data/context.db, never the network."""
import contextlib, csv, importlib.util, io, json, re, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "kin_index.py"
MARK = "RELATIONS_INDEX_2026_10_23"
JAN, PAR, AKR, SVA, SAT, ARJ, ABH = 1, 2, 3, 4, 5, 6, 7


def load():
    spec = importlib.util.spec_from_file_location("kin_index_t", str(TOOL))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, verse_ref TEXT, page_no INTEGER, idx INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_variants (entity_id INTEGER, variant TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE shelf_sources (code TEXT, title TEXT, authors TEXT, year TEXT);
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, lnum INTEGER, page TEXT, k1 TEXT, name TEXT,
                                key TEXT, homonym TEXT, head TEXT, body TEXT, notes TEXT);
    CREATE TABLE shelf_links (entry_id INTEGER, entity_id INTEGER, how TEXT);
    """)
    con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "MBh01"), (2, "sb"), (3, "old-RETIRED")])
    ps = [(1, 1, "1.89.47", 1, 1), (2, 2, None, 1, 1), (3, 2, None, 1, 2), (4, 2, None, 1, 3), (5, 2, None, 9, 1),
          (6, 3, None, 1, 1)]
    con.executemany("INSERT INTO passages VALUES (?,?,?,?,?)", ps)
    ents = [(JAN, "Janamejaya", "person"), (PAR, "Parik\u1e63it", "person"), (AKR, "Akr\u016bra", "person"),
            (SVA, "\u015avaphalka", "person"), (SAT, "\u015aat\u0101n\u012bka", "person"), (ARJ, "Arjuna", "person"),
            (ABH, "Abhimanyu", "person")]
    con.executemany("INSERT INTO entities VALUES (?,?,?)", ents)
    m = [(JAN, 1), (PAR, 1), (AKR, 2), (SVA, 4), (SAT, 5), (ABH, 5), (ARJ, 6)]   # Arjuna only in a retired text
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)", m)
    con.executemany("INSERT INTO shelf_sources VALUES (?,?,?,?)", [
        ("pui", "The Purana Index", "V. R. Ramachandra Dikshitar", "1951-1955"),
        ("vei", "Vedic Index of Names and Subjects", "A. A. Macdonell and A. B. Keith", "1912"),
        ("inm", "An Index to the Names in the Mahabharata", "S. S\u00f8rensen", "1904")])
    en = [(10, "pui", "Janamejaya", "\u2014 a son of Parik\u1e63it; father of \u015aat\u0101n\u012bka. V\u0101. 99. 250."),
          (11, "pui", "Akr\u016bra", "\u2014 married the daughter of Ugrasena; a son of \u015avaphalka. M. 45. 28."),
          (12, "pui", "Agni", "\u2014 a god of fire."),
          (20, "vei", "\u015aat\u0101n\u012bka", "\u2014 son of Janamejaya, according to the Pur\u0101\u1e47as."),
          (30, "inm", "Abhimanyu", "son of Arjuna and Subhadr\u0101 (I, 2, 401).")]
    con.executemany("INSERT INTO shelf_entries (id, source, head, body) VALUES (?,?,?,?)", en)
    con.executemany("INSERT INTO shelf_links VALUES (?,?, 'exact')", [(10, JAN), (11, AKR), (20, SAT), (30, ABH)])
    con.commit()
    con.close()


def make_claims(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE claims (id INTEGER PRIMARY KEY, printed TEXT, relation TEXT, claim TEXT);
    CREATE TABLE claim_links (claim_id INTEGER, role TEXT, entity_id INTEGER);
    """)
    con.executemany("INSERT INTO claims VALUES (?,?,?,?)", [(1, "15", "son_of", "Janamejaya was the son of Parikshit."),
                                                             (2, "17", "father_of", "Satanika was the father of Janamejaya.")])
    con.executemany("INSERT INTO claim_links VALUES (?,?,?)", [(1, "subject", JAN), (1, "object", PAR),
                                                                (2, "subject", SAT), (2, "object", JAN)])
    con.commit()
    con.close()


REPLIES = {
    "Janamejaya": [{"subject": "Janamejaya", "relation": "son_of", "object": "Parik\u1e63it", "words": "a son of Parik\u1e63it",
                    "refs": ["V\u0101. 99. 250"]},
                   {"subject": "Janamejaya", "relation": "father_of", "object": "\u015aat\u0101n\u012bka",
                    "words": "father of \u015aat\u0101n\u012bka", "refs": []},
                   {"subject": "Janamejaya", "relation": "son_of", "object": "\u015aat\u0101n\u012bka",
                    "words": "father of \u015aat\u0101n\u012bka", "refs": []},                     # the direction wrong
                   {"subject": "Janamejaya", "relation": "brother_of", "object": "Arjuna", "words": "brother of Arjuna",
                    "refs": []}],                                                                 # not in the entry
    "Akr\u016bra": [{"subject": "Akr\u016bra", "relation": "son_of", "object": "\u015avaphalka",
                     "words": "a son of \u015avaphalka", "refs": ["M. 45. 28"]},
                    {"subject": "Akr\u016bra", "relation": "married", "object": "the daughter of Ugrasena",
                     "words": "married the daughter of Ugrasena", "refs": []}],                   # an unnamed person
    "\u015aat\u0101n\u012bka": [{"subject": "\u015aat\u0101n\u012bka", "relation": "son_of", "object": "Janamejaya",
                                "words": "son of Janamejaya", "refs": []}],
    "Abhimanyu": [{"subject": "Abhimanyu", "relation": "son_of", "object": "Arjuna", "words": "son of Arjuna",
                   "refs": ["I, 2, 401"]}],
}


def stub(calls):
    def call(system, prompt):
        calls.append(prompt)
        out = []
        for k, head in re.findall(r"^\[(\d+)\] (\S+)", prompt, flags=re.M):
            for r in REPLIES.get(head, []):
                out.append(dict(r, entry=int(k)))
        ns = types.SimpleNamespace
        return ns(text=json.dumps({"relations": out}, ensure_ascii=False), candidates=[ns(finish_reason="STOP")],
                  usage_metadata=ns(prompt_token_count=900, candidates_token_count=150, thoughts_token_count=0,
                                    total_token_count=1050))
    return call


class TheKinships(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "shelf").mkdir(parents=True)
        self.db = t / "data" / "context.db"
        make_db(self.db)
        make_claims(t / "data" / "shelf" / "claims.db")
        self.m = load()
        self.calls = []

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a, caller=True):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.m.main(["--root", str(self.t)] + list(a), caller=stub(self.calls) if caller else None)
        return rc, buf.getvalue()

    def rows(self):
        with open(self.t / "exports" / "kin_edges.csv", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def test_the_plan_writes_nothing(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        self.assertIn("4 entries to read", out, "the entry of Agni names no kinship")
        self.assertIn("NEXT: python scripts\\kin_index.py --yes", out)
        self.assertFalse((self.t / "data" / "shelf" / "kin.db").exists())
        self.assertEqual(self.calls, [])

    def test_read_and_check(self):
        rc, out = self.run_main("--yes")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls), 3, "one call for each index: the two Purana entries go together")
        self.assertIn("] Janamejaya", self.calls[0])
        rows = self.rows()
        self.assertEqual(len(rows), 7, "the unnamed daughter is never an object")
        kept = {(r["subject"], r["relation"], r["object"]): r for r in rows if r["kept"] == "True"}
        self.assertEqual(len(kept), 5, "the wrong direction and the words not in the entry are set aside")
        bad = {(r["relation"], r["words_check"], r["direction"]) for r in rows if r["kept"] != "True"}
        self.assertEqual(bad, {("son_of", "exact", "disagrees"), ("brother_of", "none", "agrees")})
        jp = kept[("Janamejaya", "son_of", "Parik\u1e63it")]
        self.assertEqual((jp["verdict"], jp["passages"], jp["places"]), ("named together", "1", "MBh01 1.89.47"))
        self.assertEqual(jp["raychaudhuri"], "agrees")
        self.assertEqual(kept[("Akr\u016bra", "son_of", "\u015avaphalka")]["verdict"], "named near")
        js = kept[("Janamejaya", "father_of", "\u015aat\u0101n\u012bka")]
        self.assertEqual((js["verdict"], js["raychaudhuri"]), ("both named, never near", "reversed"))
        self.assertEqual(kept[("Abhimanyu", "son_of", "Arjuna")]["verdict"], "one not in our texts")
        with open(self.t / "exports" / "kin_agreement.csv", encoding="utf-8-sig") as f:
            ag = list(csv.DictReader(f))
        pair = [r for r in ag if {r["a"], r["b"]} == {"Janamejaya", "\u015aat\u0101n\u012bka"}][0]
        self.assertEqual((pair["sources"], pair["state"]), ("pui,vei,phai1923", "differ"),
                         "the two indexes agree; Raychaudhuri states the reverse")
        cards = (self.t / "exports" / "kin_cards.md").read_text(encoding="utf-8")
        self.assertIn("**son of Parik\u1e63it.** Purana Index, s.v. Janamejaya: \"a son of Parik\u1e63it\" "
                      "(V\u0101. 99. 250). Our texts name both together in 1 passage(s) of 1 text(s): MBh01 1.89.47. "
                      "Raychaudhuri agrees: p. 15: Janamejaya was the son of Parikshit.", cards)
        self.assertNotIn("brother of Arjuna", cards)
        m = json.loads((self.t / "exports" / "kin_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(m["by_source"]["pui"]["kept"], 3)
        con = sqlite3.connect(str(self.db))
        self.assertEqual(con.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'kinship'").fetchone()[0], 3,
                         "every call metered")
        con.close()
        rc, out = self.run_main("--yes")
        self.assertEqual(len(self.calls), 3, "read once: a second run reads nothing")
        self.assertIn("0 entries to read", out)

    def test_the_cap_and_the_show(self):
        rc, out = self.run_main("--yes", "--max-usd", "0.0001")
        self.assertEqual(self.calls, [], out)
        self.assertIn("stopped: --max-usd", out)
        self.run_main("--yes")
        rc, out = self.run_main("--show", "Janamejaya")
        self.assertIn("relation(s) name Janamejaya", out)
        self.assertIn("son_of Parik\u1e63it", out)

    def test_lineages(self):
        m = self.m
        rows = [{"kept": True, "relation": "son_of", "subject_entity": 2, "object_entity": 1, "subject_name": "B",
                 "object_name": "A", "source": "pui"},
                {"kept": True, "relation": "father_of", "subject_entity": 2, "object_entity": 3, "subject_name": "B",
                 "object_name": "C", "source": "vei"},
                {"kept": True, "relation": "son_of", "subject_entity": 4, "object_entity": 3, "subject_name": "D",
                 "object_name": "C", "source": "pui"}]
        got = m.lineages(rows, min_len=4)
        self.assertEqual(got, [(["A", "B", "C", "D"], ["pui", "vei", "pui"])])
        self.assertEqual(m.norm("son_of", 7, 9), m.norm("father_of", 9, 7))

    def test_ascii_and_mark(self):
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
