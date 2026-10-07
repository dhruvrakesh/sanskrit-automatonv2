# -*- coding: ascii -*-
"""DOC_HINT_2026_10_07: corpus_status --doc with a code that is not in docs says so, resolves a unique
prefix or another case, suggests the closest codes, and never falls through to "all docs". No network."""
import importlib, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CODES = ["Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V", "markandeya_purana", "Markandeya_Old_1890",
         "AphorismsOfSandilya"]


class DocHint(unittest.TestCase):
    def setUp(self):
        import corpus_status
        importlib.reload(corpus_status)
        self.cs = corpus_status
        self.tmp = Path(tempfile.mkdtemp(prefix="dochint_"))
        self.db = str(self.tmp / "context.db")
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT UNIQUE, category TEXT)")
        con.executemany("INSERT INTO docs(code) VALUES(?)", [(c,) for c in CODES])
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unique_prefix_is_used_with_a_note(self):
        out, notes = self.cs.resolve_docs(self.db, ["Ganita_Yukti_Bhasa"])
        self.assertEqual(out, ["Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V"])
        self.assertTrue(notes and notes[0].startswith("# note:") and "using Ganita_Yukti_Bhasa_of_" in notes[0], notes)

    def test_exact_and_case(self):
        out, notes = self.cs.resolve_docs(self.db, ["markandeya_purana", "aphorismsofsandilya"])
        self.assertEqual(out, ["markandeya_purana", "AphorismsOfSandilya"])
        self.assertEqual(len(notes), 1)

    def test_ambiguous_or_unknown_is_suggested_not_guessed(self):
        out, notes = self.cs.resolve_docs(self.db, ["markandeya", "ganita yukti"])
        self.assertEqual(out, [])
        self.assertIn("markandeya_purana", notes[0]); self.assertIn("Markandeya_Old_1890", notes[0])
        self.assertIn("Did you mean", notes[1])

    def test_nothing_matched_stops_instead_of_reporting_everything(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_status.py"), "--db", self.db,
                            "--doc", "no_such_text"], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("no text has the code 'no_such_text'", r.stdout)
        self.assertIn("nothing to report", r.stdout)


if __name__ == "__main__":
    unittest.main()
