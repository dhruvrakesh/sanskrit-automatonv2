# -*- coding: ascii -*-
"""TEXT_HYGIENE_2026_10_03. python -m unittest tests.test_text_hygiene -v
Throwaway SQLite only; never touches data/context.db, the network or the API."""
import importlib.util, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("hygiene_under_test", str(REPO / "scripts" / "diag_text_hygiene.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


AP = ("\u0968\u096b \u0938\u0941\u0916\u0902 P. \u0968\u096c \u0905\u0917\u094d\u0928\u093f\u0935\u0943\u0926\u094d"
      "\u0927\u094c \u0935\u093f\u0928\u093e\u0936\u0936\u094d\u091a P.")
VERSE = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915"
         "\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u0964 \u0967\u0968 \u0965")
LOOP = "\u0905\u0917\u094d\u0928\u093f\u092e\u0942" + "\u091b\u094d" * 12
META = "[The Sanskrit verse to be translated is missing from the prompt.]"


class Hygiene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_detectors(self):
        self.assertTrue(self.m.is_apparatus(AP))
        self.assertFalse(self.m.is_apparatus(VERSE), "a verse number before the double danda is not apparatus")
        self.assertTrue(self.m.has_unit_loop(LOOP))
        self.assertFalse(self.m.has_unit_loop(VERSE))
        self.assertTrue(self.m.is_meta(META))
        self.assertFalse(self.m.is_meta("Now [the king] went. //"))
        self.assertFalse(self.m.is_meta("[ILLEGIBLE]"), "lacuna marks are counted by measure_lacunae, not here")

    def test_census_scope_and_paid_counts(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            c = sqlite3.connect(db)
            c.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
                            " translation TEXT, text_type TEXT);"
                            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
                            "INSERT INTO docs VALUES(1,'X');")
            c.executemany("INSERT INTO passages VALUES(?,?,?,?,?,?,?)", [
                (1, 1, 1, 1, AP, "Now that bold person", "mula"),
                (2, 1, 1, 2, LOOP, None, "mula"),
                (3, 1, 1, 3, VERSE, META, "mula"),
                (4, 1, 1, 4, AP, "x", "noise")])
            c.execute("INSERT INTO translations_l10n VALUES(1,'hi','y')")
            c.commit(); c.close()
            ro = self.m.open_ro(str(db))
            try:
                rows, samples = self.m.census(ro, None, 2)
            finally:
                ro.close()
            r = rows[0]
            self.assertEqual((r["passages"], r["apparatus"], r["apparatus_en_paid"], r["apparatus_hi_paid"]), (3, 1, 1, 1))
            self.assertEqual((r["unitloop"], r["meta_en"], r["meta_hi"]), (1, 1, 0))
            self.assertEqual(len(samples[("X", "apparatus")]), 1)


if __name__ == "__main__":
    unittest.main()
