# -*- coding: ascii -*-
"""VAMSA_NAMES_2026_10_25: vamsa_check.py --name shows a statement an index makes more than once (the same subject,
relation and object in one source) once, "x n", with its best check (cited both before one before neither, then the
most epic verses), and says how many distinct statements there are. A made-up kin.db and vamsa.db in a temp folder."""
import contextlib, importlib.util, io, sqlite3, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "vamsa_check.py"
APPLIED = b"VAMSA_NAMES_2026_10_25" in TOOL.read_bytes()
PAR = "Parik\u1e63it"


def load():
    spec = importlib.util.spec_from_file_location("vamsa_check_n", str(TOOL))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@unittest.skipUnless(APPLIED, "VAMSA_NAMES_2026_10_25 is not applied here")
class TheNames(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = Path(self.td.name)
        self.vc = load()
        self.kin, self.store = t / "kin.db", t / "vamsa.db"
        con = sqlite3.connect(str(self.kin))
        con.execute("CREATE TABLE kin (id INTEGER PRIMARY KEY, source TEXT, entry_id INTEGER, head TEXT, subject TEXT, "
                    "relation TEXT, object TEXT, refs TEXT)")
        con.executemany("INSERT INTO kin VALUES (?,?,?,?,?,?,?,?)", [
            (1, "pui", 10, "Janamejaya", "Janamejaya", "son_of", PAR, "[]"),
            (2, "pui", 10, "Janamejaya", "Janamejaya", "son_of", PAR, "[]"),          # the entry says it twice
            (3, "pui", 11, "Janamejaya (II)", "Janamejaya", "son_of", PAR, "[]"),     # and another entry of the name
            (4, "vei", 20, "Janamejaya", "Janamejaya", "son_of", PAR, "[]"),          # another index: its own line
            (5, "pui", 10, "Janamejaya", "Janamejaya", "father_of", "\u015aat\u0101n\u012bka", "[]")])
        con.commit(); con.close()
        con = sqlite3.connect(str(self.store))
        con.executescript(self.vc.SCHEMA)
        rel = lambda kid, src, cited, mbh: (kid, src, 10, cited, "[]", "", "", "", "", "", mbh, "", 0, "", 0, "")
        con.executemany("INSERT INTO vamsa_rel VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            rel(1, "pui", "neither", 3), rel(2, "pui", "both", 1), rel(3, "pui", "both", 7), rel(4, "vei", "one", 0),
            rel(5, "pui", "no citation", 2)])
        con.commit(); con.close()

    def tearDown(self):
        self.td.cleanup()

    def test_a_statement_made_twice_is_shown_once(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.vc.show_name(self.store, self.kin, "Janamejaya")
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("5 relation(s) name Janamejaya, 3 distinct statement(s)", out)
        lines = [x for x in out.splitlines() if x.startswith("  [")]
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("  [Purana Index] Janamejaya son_of %s x3 | cited: both" % PAR), lines[0])
        self.assertIn("together: MBh 7", lines[0], "the best check of the three: cited both, the most verses")
        self.assertTrue(lines[1].startswith("  [Vedic Index] Janamejaya son_of %s | cited: one" % PAR), lines[1])
        self.assertTrue(lines[2].startswith("  [Purana Index] Janamejaya father_of"), lines[2])
        self.assertNotIn(" x", lines[2].split("|")[0])
        self.assertIn("VERDICT: 5 relation(s) of Janamejaya shown as 3 distinct statement(s)", out)


class TheFile(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(all(x < 128 for x in Path(__file__).read_bytes()))


if __name__ == "__main__":
    unittest.main()
