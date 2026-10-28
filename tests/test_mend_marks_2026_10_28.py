# -*- coding: ascii -*-
"""INLINE_MARKS_2026_10_28: scripts/mend_marks.py takes an edition's note numbers out of its Sanskrit (ASCII digits
glued after a Devanagari letter, or before one, as vision OCR writes the raised numbers of a critical edition), for
the text named only, in its mula, prose and colophons, in the passages vision read (a Tesseract reading's 5 is often
an avagraha); the IAST follows, the raw OCR page (norm) is kept as read, the search row is made again, a scholarly
English made from the old reading is carried to the new; never after a danda, never a decimal or a Devanagari
numeral, never the edition's own matter; a dry run by default; a backup of the database before each --apply, the
manifest next, and --undo puts back exactly that; refused where few verses carry a number, or where numbers follow
nearly every syllable (a svara notation). Temp files only."""
import json, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
TOOL = S / "mend_marks.py"
sys.path.insert(0, str(S))
import mend_marks as mm  # noqa: E402

D = "\u091a\u0948\u0935"          # caiva
W = "\u0926\u094d\u0935\u093e\u0930"   # dvara
M = "\u092e\u0941\u091a\u094d\u092f\u0924\u0947"   # mucyate
DANDA = "\u0964"
VIS = "gemini-vision:gemini-2.5-flash"


def make(db: Path, verses: list, other=None):
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT UNIQUE);
    CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT,
      translation TEXT, iast TEXT, norm TEXT, text_type TEXT, ocr_engine TEXT);
    CREATE TABLE scholar_translations(id INTEGER PRIMARY KEY, passage_id INTEGER, doc_code TEXT, src_hash TEXT,
      translation TEXT);
    CREATE VIRTUAL TABLE passages_fts USING fts5(text, iast, translation);
    """)
    con.execute("INSERT INTO docs VALUES (1, 'H'), (2, 'T')")
    for i, v in enumerate(verses, 1):
        t, tt, oe = (tuple(v) + (VIS,))[:3]
        con.execute("INSERT INTO passages VALUES (?, 1, 1, ?, ?, ?, ?, ?, ?, ?)", (i, i, t, "en %d" % i, "ia %d" % i, t, tt,
                                                                               oe))
        con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES (?, ?, ?, ?)", (i, t, "ia", "en"))
        con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, translation) VALUES (?, 'H', ?, 'x')",
                    (i, mm.src_hash(t)))
    for j, t in enumerate(other or [], 100):
        con.execute("INSERT INTO passages VALUES (?, 2, 1, ?, ?, NULL, NULL, NULL, 'mula', ?)", (j, j, t, VIS))
    con.commit(); con.close()


class TheRule(unittest.TestCase):
    def test_what_is_a_note_number(self):
        self.assertEqual(mm.mend(D + "21 " + W + "13" + M + " " + DANDA), (D + " " + W + M + " " + DANDA, 2))
        self.assertEqual(mm.mend(DANDA + "12 " + DANDA)[1], 0, "after a danda: a number of the verse")
        self.assertEqual(mm.mend(D + " 16 " + D)[1], 0, "standing apart")
        self.assertEqual(mm.mend(D + "1.2")[1], 0, "a decimal or a reference")
        self.assertEqual(mm.mend(D + "\u0967\u0968")[1], 0, "a Devanagari numeral")
        self.assertEqual(mm.mend(D + "1234")[1], 0, "four digits: not a note")
        self.assertEqual(mm.mend(DANDA + " 4" + M), (DANDA + " " + M, 1), "a number that opens a reading")
        self.assertEqual(mm.mend('"37' + M)[1], 1, "after a quotation mark")
        self.assertEqual(mm.mend("1234" + M)[1], 0, "four digits before a word: not a note")
        self.assertEqual(mm.mend("1.2" + M)[1], 0, "a reference before a word")
        self.assertEqual(mm.mend("")[1], 0)
        self.assertEqual(mm.src_hash(" a  b "), mm.src_hash("a b"))


class TheTool(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.db = self.t / "c.db"
        verses = [(D + "21 " + M + " " + DANDA, "mula"), (W + "13" + M + " " + DANDA, "mula"), (M + " " + DANDA, "mula"),
                  ("Introduction, chapter" + D + "9", "frontmatter"), (D + "3 " + DANDA, "colophon"),
                  (D + "5" + M, "mula", "tesseract-fallback")]
        make(self.db, verses, other=[D + "5" + M])

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a):
        r = subprocess.run([sys.executable, str(TOOL), "--db", str(self.db), "--out", str(self.t),
                            "--backup-dir", str(self.t / "bk")] + list(a),
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        return r.returncode, r.stdout + r.stderr

    def rows(self):
        con = sqlite3.connect(str(self.db))
        try:
            return ({r[0]: r[1:] for r in con.execute("SELECT id, text, iast, norm, text_type FROM passages")},
                    {r[0]: r[1] for r in con.execute("SELECT passage_id, src_hash FROM scholar_translations")},
                    {r[0]: r[1] for r in con.execute("SELECT rowid, text FROM passages_fts")})
        finally:
            con.close()

    def test_dry_run_writes_nothing(self):
        before = self.db.read_bytes()
        rc, out = self.run_tool("--doc", "H", "--show", "3")
        self.assertEqual(rc, 0, out)
        self.assertIn("3 verse(s) read by vision; 3 note number(s) in 3 passage(s); 2 of those verses (66.7%); "
                      "3 scholarly row(s) carried; 1 passage(s) with digits left (not read by vision)", out)
        self.assertIn("a dry run; nothing written", out)
        self.assertEqual(self.db.read_bytes(), before)

    def test_apply_then_nothing_then_undo(self):
        rc, out = self.run_tool("--doc", "H", "--apply")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(list((self.t / "bk").glob("context_pre_mendmarks_H_*.db"))), 1, "a backup before anything")
        p, h, f = self.rows()
        self.assertEqual(p[1][0], D + " " + M + " " + DANDA)
        self.assertEqual(p[2][0], W + M + " " + DANDA)
        self.assertEqual(p[3][0], M + " " + DANDA, "no number: untouched")
        self.assertEqual(p[4][0], "Introduction, chapter" + D + "9", "the edition's own matter: untouched")
        self.assertEqual(p[5][0], D + " " + DANDA, "a colophon is mended")
        self.assertEqual(p[6][0], D + "5" + M, "a Tesseract reading: its 5 may be an avagraha, left as it is")
        self.assertEqual(p[1][2], D + "21 " + M + " " + DANDA, "the raw OCR page (norm) is evidence: kept as read")
        for i in (1, 2, 5):
            self.assertEqual(h[i], mm.src_hash(p[i][0]), "the scholarly English carried to the mended text")
            self.assertEqual(f[i], p[i][0], "the search row made again")
        self.assertEqual(h[3], mm.src_hash(M + " " + DANDA))
        man = sorted(self.t.glob("mend_marks_H_*.json"))
        self.assertEqual(len(man), 1)
        j = json.loads(man[0].read_text(encoding="utf-8"))
        self.assertEqual((j["mark"], len(j["changes"]), len(j["scholar"])), ("INLINE_MARKS_2026_10_28", 3, 3))
        rc, out = self.run_tool("--doc", "H")
        self.assertIn("nothing to mend", out)
        rc, out = self.run_tool("--undo", str(man[0]))
        self.assertIn("(dry run)", out)
        rc, out = self.run_tool("--undo", str(man[0]), "--apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("put back 3 passage(s)", out)
        p2, h2, f2 = self.rows()
        self.assertEqual(p2[1][0], D + "21 " + M + " " + DANDA)
        self.assertEqual(h2[1], mm.src_hash(D + "21 " + M + " " + DANDA))
        self.assertEqual(f2[1], p2[1][0])

    def test_refusals(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 2)
        self.assertIn("REFUSE: name the text", out)
        rc, out = self.run_tool("--doc", "NOPE")
        self.assertIn("no text NOPE", out)
        con = sqlite3.connect(str(self.db))
        con.executemany("INSERT INTO passages VALUES (?, 2, 2, ?, ?, NULL, NULL, NULL, 'mula', ?)",
                        [(200 + k, k, M + " " + DANDA, VIS) for k in range(40)])
        con.commit(); con.close()
        rc, out = self.run_tool("--doc", "T", "--apply")
        self.assertEqual(rc, 1, out)
        self.assertIn("REFUSE: only 2.4%", out)
        self.assertIn(D + "5" + M, self.rows()[0][100][0], "nothing written")
        con = sqlite3.connect(str(self.db))
        con.execute("INSERT INTO docs VALUES (3, 'S')")
        sv = "".join(M[k % len(M)] + "123"[k % 3] for k in range(30))   # a digit after every letter
        con.executemany("INSERT INTO passages VALUES (?, 3, 1, ?, ?, NULL, NULL, NULL, 'mula', ?)",
                        [(300, 0, sv, VIS)] + [(301 + k, k + 1, D + "4 " + M, VIS) for k in range(5)])
        con.commit(); con.close()
        rc, out = self.run_tool("--doc", "S", "--apply")
        self.assertEqual(rc, 1, out)
        self.assertIn("REFUSE: 1 passage(s) carry a number after nearly every syllable", out)
        self.assertEqual(self.rows()[0][300][0], sv, "nothing written")

    def test_ascii_and_marked(self):
        b = TOOL.read_bytes()
        self.assertTrue(b.isascii())
        self.assertIn(b"INLINE_MARKS_2026_10_28", b)


if __name__ == "__main__":
    unittest.main()
