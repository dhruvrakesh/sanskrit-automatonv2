# -*- coding: ascii -*-
"""HEADS2_2026_10_07: running heads printed with a page number and a double danda, as in
markandeya_purana ("6 markandeya puranam ||"), are found; refrains and speaker lines are not."""
import importlib, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DEV = "\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f"
HEAD = "\u092e\u093e\u0930\u094d\u0915\u0923\u094d\u0921\u0947\u092f \u092a\u0941\u0930\u093e\u0923\u0902 \u0965"
UVACA = "\u092e\u093e\u0930\u094d\u0915\u0923\u094d\u0921\u0947\u092f \u0909\u0935\u093e\u091a \u0965"
VERSE = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941"
         "\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f"
         "\u0941\u0924\u094d\u0938\u0935\u0903 \u0964")
REFRAIN = "\u0928\u092e\u0903 \u0936\u093f\u0935\u093e\u092f \u0965"


def dn(n):
    return "".join(DEV[int(c)] for c in str(n))


class Heads2(unittest.TestCase):
    def setUp(self):
        import db_utils, classify_noise
        importlib.reload(classify_noise)
        self.cn = classify_noise
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('M')")
        self.heads, self.translated_heads = [], []
        for pg in range(2, 14, 2):                  # even pages carry the running head, numbered
            done = "Markandeya Purana" if pg in (4, 8) else ""
            rows = [("%s %s" % (dn(pg), HEAD), done, "head"),
                    (UVACA, "", "keep"),               # a speaker line, often first after the head
                    (VERSE, "fine", "keep"),
                    ("%s %s%s\u0965" % (REFRAIN, "\u0965", dn(pg + 40)), "", "keep")]   # a numbered refrain, last line
            for i, (t, en, kind) in enumerate(rows, 1):
                pid = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation) "
                                  "VALUES(1,?,?,?,'mula',?)", (pg, i, t, en)).lastrowid
                if kind == "head":
                    (self.translated_heads if en else self.heads).append(pid)
        con.commit(); con.close()
        self.con = sqlite3.connect(self.db)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_numbered_head_with_double_danda_is_found(self):
        hits, groups = self.cn.running_heads(self.con, "M", 3, 60)
        self.assertEqual(sorted(h[0] for h in hits), sorted(self.heads))
        self.assertEqual([(g[2], g[3], g[4]) for g in groups], [(6, 4, 2)], "6 pages, 4 untranslated, 2 translated")

    def test_include_translated(self):
        hits, _ = self.cn.running_heads(self.con, "M", 3, 60, include_translated=True)
        self.assertEqual(sorted(h[0] for h in hits), sorted(self.heads + self.translated_heads))

    def test_a_long_first_line_with_a_danda_is_verse(self):
        self.con.execute("UPDATE passages SET text=? || ' ' || text WHERE idx=1", (VERSE,)); self.con.commit()
        hits, _ = self.cn.running_heads(self.con, "M", 3, 120)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
