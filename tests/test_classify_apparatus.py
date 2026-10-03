# -*- coding: ascii -*-
"""APPARATUS_TAG_2026_10_03. python -m unittest tests.test_classify_apparatus -v
Throwaway SQLite only."""
import importlib.util, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def load():
    spec = importlib.util.spec_from_file_location("apparatus_under_test", str(REPO / "scripts" / "classify_apparatus.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


AP = ("\u0968\u096b \u0938\u0941\u0916\u0902 P. \u0968\u096c \u0905\u0917\u094d\u0928\u093f\u0935\u0943\u0926\u094d"
      "\u0927\u094c \u0935\u093f\u0928\u093e\u0936\u0936\u094d\u091a P.")
VERSE = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915"
         "\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u0964 \u0967\u0968 \u0965")


class Apparatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_tag_keeps_translation_and_undo_restores(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT,"
                              " text TEXT, translation TEXT, text_type TEXT);"
                              "INSERT INTO docs VALUES(1,'X');")
            con.executemany("INSERT INTO passages VALUES(?,?,?,?,?,?,?)", [
                (1, 1, 1, 1, AP, "paid translation", "prose"),
                (2, 1, 1, 2, VERSE, "a verse", "mula"),
                (3, 1, 1, 3, AP, None, "frontmatter")])
            con.commit()
            hits = self.m.find(con)
            self.assertEqual([h[0] for h in hits], [1], "only the apparatus row not already excluded")
            man = Path(t) / "m.json"
            self.assertEqual(self.m.apply_tags(con, hits, man), 1)
            self.assertEqual(con.execute("SELECT text_type, translation FROM passages WHERE id=1").fetchone(),
                             ("noise", "paid translation"))
            self.assertEqual(self.m.find(con), [], "idempotent: a second run finds nothing")
            self.m.undo(con, man)
            self.assertEqual(con.execute("SELECT text_type FROM passages WHERE id=1").fetchone()[0], "prose")
            con.close()

    def test_colophon_with_footnote_tail_is_not_apparatus_and_reconcile_restores_it(self):
        colophon = ("\u0907\u0924\u093f \u0936\u094d\u0930\u0940\u092e\u0932\u094d\u0932\u092a\u0941\u0930\u093e\u0923\u0947 "
                    "\u0928\u093e\u092e \u0924\u0943\u0924\u0940\u092f\u094b\u093d\u0927\u094d\u092f\u093e\u092f\u0903 \u0964 " + AP)
        self.assertFalse(self.m.is_apparatus(colophon))
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT,"
                              " text TEXT, translation TEXT, text_type TEXT);"
                              "INSERT INTO docs VALUES(1,'X');")
            con.executemany("INSERT INTO passages VALUES(?,?,?,?,?,?,?)", [
                (1, 1, 63, 8, colophon, "Thus ends", "noise"), (2, 1, 64, 10, AP, "x", "noise")])
            con.commit()
            man = Path(t) / "m.json"
            man.write_text('{"rows": [{"id": 1, "page": 63, "idx": 8, "prev": "mula"},'
                           ' {"id": 2, "page": 64, "idx": 10, "prev": "prose"}]}', encoding="utf-8")
            res = self.m.reconcile(con, man)
            self.assertEqual([r[0] for r in res], [1])
            self.assertEqual(con.execute("SELECT text_type FROM passages ORDER BY id").fetchall(), [("mula",), ("noise",)])
            con.close()


if __name__ == "__main__":
    unittest.main()
