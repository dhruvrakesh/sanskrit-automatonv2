# -*- coding: ascii -*-
"""PUBLISH_ENGINE_2026_10_07: without --engine, the publisher labels the text with the one engine every
translated passage records; with mixed engines it guesses nothing. No network, no key."""
import importlib, io, sqlite3, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def fixture(path, engines):
    con = sqlite3.connect(path)
    con.executescript("""
      CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);
      CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,
        iast TEXT, translation TEXT, verse_ref TEXT, quality_score REAL, text_type TEXT, engine TEXT);
      INSERT INTO docs VALUES (1, 'E_doc', 'purana');
    """)
    for i, e in enumerate(engines, 1):
        con.execute("INSERT INTO passages(doc_id,page_no,idx,text,iast,translation,verse_ref,quality_score,text_type,engine)"
                    " VALUES (1,1,?,?,?,?,NULL,0.8,'mula',?)",
                    (i, "\u0930\u093e\u092e\u094b \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f \u0965 %d" % i,
                     "ramo vanam gacchati %d" % i, "Rama goes to the forest, verse %d. //" % i, e))
    con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,engine) VALUES (1,2,1,'x','', 'mula','other:model')")
    con.commit(); con.close()


class Engine(unittest.TestCase):
    def emit(self, engines, *extra):
        import publish_srangam as ps
        importlib.reload(ps)
        tmp = Path(tempfile.mkdtemp())
        fixture(tmp / "c.db", engines)
        old = sys.argv
        sys.argv = ["publish_srangam.py", "--db", str(tmp / "c.db"), "--doc", "E_doc", "--emit-sql", str(tmp / "sql"), *extra]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                ps.main()
        finally:
            sys.argv = old
        return (tmp / "sql" / "E_doc" / "00_text.sql").read_text(encoding="utf-8"), buf.getvalue()

    def test_one_engine_labels_the_text(self):
        t, out = self.emit(["gemini:gemini-2.5-flash"] * 3)
        self.assertIn("'gemini:gemini-2.5-flash'", t)
        self.assertIn("engine label gemini:gemini-2.5-flash", out)

    def test_mixed_engines_guess_nothing(self):
        t, out = self.emit(["gemini:gemini-2.5-flash", "gemini:gemini-2.5-pro", "gemini:gemini-2.5-flash"])
        self.assertNotIn("'gemini:gemini-2.5-", t)
        self.assertIn("record 2 engine label(s)", out)

    def test_explicit_engine_wins(self):
        t, _ = self.emit(["gemini:gemini-2.5-flash"] * 2, "--engine", "human:edited")
        self.assertIn("'human:edited'", t)
        self.assertNotIn("'gemini:gemini-2.5-flash'", t)


if __name__ == "__main__":
    unittest.main()
