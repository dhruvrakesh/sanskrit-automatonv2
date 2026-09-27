# -*- coding: ascii -*-
"""PUBLISH_BRIDGE_2026_09_27 - publish_srangam.py --emit-sql, without a network or a key.
Run: python -m unittest tests.test_publish_bridge -v   (from the repo root)."""
import sqlite3, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import publish_srangam as ps


def fixture(path):
    con = sqlite3.connect(path)
    con.executescript("""
      CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);
      CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,
        iast TEXT, translation TEXT, verse_ref TEXT, quality_score REAL, text_type TEXT);
      INSERT INTO docs VALUES (1, 'T_doc', 'bhakti');
    """)
    rows = [(1, 1, 1, "\u0930\u093e\u092e\u094b \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f \u0965", "ramo vanam gacchati", "Rama's forest walk. //", None, 0.8, "mula"),
            (1, 1, 2, "\u0938\u0940\u0924\u093e \u0917\u091a\u094d\u091b\u0924\u093f \u0965", None, "Sita goes. //", "1.2", None, "mula"),
            (1, 1, 3, "\u0936\u0941\u0926\u094d\u0927\u092e\u094d", None, "errata", None, 0.5, "frontmatter"),
            (1, 2, 1, "\u0915\u094b\u0921\u094d", None, "", None, 0.9, "mula")]
    con.executemany("INSERT INTO passages(doc_id,page_no,idx,text,iast,translation,verse_ref,quality_score,text_type)"
                    " VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


class Bridge(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        fixture(self.tmp / "c.db")

    def run_cli(self, *argv):
        old = sys.argv
        sys.argv = ["publish_srangam.py", "--db", str(self.tmp / "c.db")] + list(argv)
        try:
            ps.main()
        finally:
            sys.argv = old

    def test_emit_sql_files(self):
        self.run_cli("--doc", "T_doc", "--emit-sql", str(self.tmp / "sql"), "--sql-batch", "1")
        out = self.tmp / "sql" / "T_doc"
        names = sorted(p.name for p in out.glob("*.sql"))
        # frontmatter withheld by the gate, empty translation never selected: 2 rows, 1 per file
        self.assertEqual(names, ["00_text.sql", "01_passages.sql", "02_passages.sql", "99_verify.sql"])
        p1 = (out / "01_passages.sql").read_text(encoding="utf-8")
        self.assertIn("'Rama''s forest walk. //'", p1)            # quote doubled
        self.assertIn("ON CONFLICT (text_id, page_no, idx) DO UPDATE", p1)
        self.assertNotIn("published", p1.split("never\n")[-1].replace("changes srangam_texts.published", ""))
        t = (out / "00_text.sql").read_text(encoding="utf-8")
        self.assertIn("ON CONFLICT (doc_code) DO UPDATE", t)
        self.assertNotIn("published =", t)
        v = (out / "99_verify.sql").read_text(encoding="utf-8")
        self.assertIn("(1,1),(1,2)", v)
        self.assertIn("2 AS local_passages", v)
        self.assertTrue((out / "MANIFEST.txt").exists())

    def test_gate_report_runs(self):
        self.run_cli("--doc", "T_doc", "--gate-report")

    def test_dry_run_has_no_title_column_crash(self):
        self.run_cli("--doc", "T_doc", "--dry-run")


if __name__ == "__main__":
    unittest.main()
