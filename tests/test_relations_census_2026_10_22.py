# -*- coding: ascii -*-
"""RELATIONS_CENSUS_2026_10_22: scripts/relations_census.py measures how the names are joined: names by kind, the
pairs named together in one passage (in how many passages and texts; a passage naming more than 12 is a list, left
out; a retired text left out), one name's neighbours with places, and the index entries that state a kinship as
printed (counted, never stored). The database is opened read-only and is the same bytes after. A made-up database in
a temp folder."""
import csv, hashlib, json, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "relations_census.py"
MARK = "RELATIONS_CENSUS_2026_10_22"


def make_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, verse_ref TEXT, page_no INTEGER, idx INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE shelf_sources (code TEXT, title TEXT);
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, head TEXT, body TEXT);
    """)
    con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "sb"), (2, "mbh"), (3, "old-RETIRED")])
    ents = [(1, "Janaka", "person"), (2, "Y\u0101j\u00f1avalkya", "person"), (3, "Videha", "place"),
            (4, "Aj\u0101ta\u015batru", "person")]
    ents += [(10 + i, "N%d" % i, "person") for i in range(13)]
    con.executemany("INSERT INTO entities VALUES (?,?,?)", ents)
    ps = [(1, 1, "14.1", 1, 1), (2, 1, "14.2", 1, 2), (3, 2, "1.1", 2, 1), (4, 3, "x", 3, 1), (5, 1, "list", 4, 1)]
    con.executemany("INSERT INTO passages VALUES (?,?,?,?,?)", ps)
    m = [(1, 1), (2, 1), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (1, 4), (4, 4)]   # 4 is in the retired text
    m += [(10 + i, 5) for i in range(13)]                                          # 13 names: a list
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)", m)
    con.executemany("INSERT INTO shelf_sources VALUES (?,?)", [("pui", "The Purana Index")])
    con.executemany("INSERT INTO shelf_entries (source, head, body) VALUES (?,?,?)", [
        ("pui", "Akrura", "married the daughter of Ugrasena; a son of Svaphalka."), ("pui", "Agni", "a god.")])
    con.commit()
    con.close()


class TheCensus(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data").mkdir()
        self.db = t / "data" / "context.db"
        make_db(self.db)
        self.md5 = hashlib.md5(self.db.read_bytes()).hexdigest()

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t)] + list(a), capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_the_census(self):
        rc, out = self.run_tool("--name", "janaka")
        self.assertEqual(rc, 0, out)
        j = json.loads((self.t / "exports" / "relations_census.json").read_text(encoding="utf-8"))
        self.assertEqual(j["entities"], 17)
        self.assertEqual(j["mentions"], 20, "the retired text's 2 mentions left out")
        t = j["together"]
        self.assertEqual((t["pairs"], t["in_2_passages"], t["in_2_texts"], t["lists_left_out"]), (3, 1, 1, 1))
        nb = {r["with"]: r for r in j["name"]["with"]}
        self.assertEqual((nb["Y\u0101j\u00f1avalkya"]["passages"], nb["Y\u0101j\u00f1avalkya"]["texts"]), (3, 2))
        self.assertEqual(nb["Videha"]["passages"], 1)
        self.assertNotIn("Aj\u0101ta\u015batru", nb, "named only in the retired text")
        self.assertEqual(j["index"]["pui"]["with_phrase"], {"son of": 1, "daughter of": 1})
        with open(self.t / "exports" / "names_together.csv", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([(r["name_a"], r["name_b"], r["passages"]) for r in rows],
                         [("Janaka", "Y\u0101j\u00f1avalkya", "3")], "only pairs in two passages or more")
        self.assertIn("no relation of kinship or school is stored yet", out)
        self.assertEqual(hashlib.md5(self.db.read_bytes()).hexdigest(), self.md5, "the database is not written")

    def test_immutable_and_no_write(self):
        rc, out = self.run_tool("--db", str(self.db), "--immutable", "--no-write")
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.t / "exports").exists())
        rc, out = self.run_tool("--db", str(self.t / "none.db"))
        self.assertEqual(rc, 2)

    def test_ascii_and_mark(self):
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
