# -*- coding: ascii -*-
"""SHELF_2026_10_21: scholar_shelf.py reads the three Cologne indexes of names (made-up entries in their format here):
the headword from k1 (SLP1), the text without the markup, the footnotes, the bold names (vei), the references with the
work each names and whether our corpus holds it (the Satapatha only in book 14; Soerensen's book I as MBh01, numbered
otherwise; the Purana Index's abbreviations as printed, Ib. for the one before); the plan writes nothing; --yes makes
a backup and the shelf_ tables, tied exactly or loosely to our names, and a second --yes replaces, not adds; --show
and --credits read them; the mirror (corpus_sync.py) does not know them. Temp files only; nothing is called."""
import hashlib, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "scholar_shelf.py"
MARK = "SHELF_2026_10_21"
try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="//www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title type="main">A Test Index</title>
<title type="desc">XML edition</title><editor>A. Editor</editor></titleStmt>
<editionStmt><edition>xml version, <date when="2013">2013</date></edition></editionStmt>
<publicationStmt><publisher>A Library</publisher><pubPlace>A Town</pubPlace><date when="2014-06-30">30 June 2014</date>
<availability><p>Copyright 2014 A Library</p><p>Under <ref target="//creativecommons.org/licenses/by-nc-sa/3.0/legalcode">x</ref>
and <ref target="//creativecommons.org/licenses/by-nc-sa/3.0/">y</ref>.</p></availability></publicationStmt></fileDesc></teiHeader></TEI>
"""
FILL = "".join("<L>%d<pc>2-001<k1>kAla%d<k2>kAla%d\n{@K\u0101la%d.@}\u00a6 a word.\n<LEND>\n\n" % (n, n, n, n) for n in range(10, 130))
VEI = ("<L>1<pc>1-271<k1>janaka<k2>janaka\n"
       "{@Janaka,@}\u00a6 king of Videha, named in the \u015aatapatha Br\u0101hma\u1e47a<sup>1</sup> and the B\u1e5bhad\u0101ra\u1e47yaka "
       "Upani\u1e63ad.<sup>2</sup> A con-\ntemporary of {@Y\u0101j\u00f1avalkya V\u0101ja-@}\n[Page1-272+ 50]\n{@saneya.@}<sup>3</sup>\n"
       "<F>1) xi. 3, 1, 2; xiv. 6, 1, 1.</F>\n<F>2) iii. 1, 1.</F>\n"
       "<F>3) Aitareya Br\u0101hma\u1e47a, viii. 21; Weber, {%Indische Studien,%} 1, 35.</F>\n<LEND>\n\n"
       "<L>2<pc>1-273<k1>parikzit<k2>parikzit\n{@Parik\u1e63it@}\u00a6 a king; see {@Janamejaya.@}\n<LEND>\n\n" + FILL)
INM = ("<L>1<pc>351-1<k1>janamejaya<k2>janamejaya<h>1\n{@Janamejaya@}<sup>1</sup>,\u00a6 son of Parik\u1e63it. "
       "\u00a7 1 (Anukram.): I, {@1@}, 9 ({%r\u0101j\u00f1a\u1e25%}).\u2014\u00a7 595 (\u1e62o\u1e0da\u015bar\u0101j.): VII, {@62@}\u03b1, "
       "2281 (vanquished).\n<LEND>\n\n" + FILL)
PUI = ("<L>1<pc>1-622<k1>janaka<k2>janaka<h>I\n{%Janaka%} (I)\u00a6 \u2014 king of Mithil\u0101.<sup>1</sup>\n"
       "<div n=\"P\"/>Vi. IV. 5. 22-4.\n<F>1) Bh\u0101. IX. 13. 13-14; Ib. X. 71. 9; V\u0101. 89. 2.</F>\n<LEND>\n\n" + FILL)


@unittest.skipUnless(TOOL.exists() and HAVE_IT, "scholar_shelf.py or indic_transliteration is not here")
class TheShelf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shelf_"))
        for code, body in (("vei", VEI), ("inm", INM), ("pui", PUI)):
            d = self.tmp / "cologne" / code / "txt"
            d.mkdir(parents=True)
            (d / ("%s.txt" % code)).write_text("%%***test\n" + body, encoding="utf-8")
            (d / ("%sheader.xml" % code)).write_text(HEADER, encoding="utf-8")
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db)
        con.executescript("""
            CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT UNIQUE);
            CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT);
            CREATE TABLE entities(id INTEGER PRIMARY KEY, canonical TEXT UNIQUE, kind TEXT, notes TEXT, created_at TEXT);
            CREATE TABLE entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER, surface TEXT,
                                         created_at TEXT, UNIQUE(entity_id, passage_id));
            INSERT INTO docs VALUES (1, 'MBh01');
            INSERT INTO passages VALUES (10, 1, 1, 1, 'x'), (11, 1, 1, 2, 'y');
            INSERT INTO entities(id, canonical, kind) VALUES (1, 'Janaka', 'person'), (2, 'Par\u012bk\u1e63it', 'person'),
                (3, 'Janamejaya', 'person'), (4, 'Someone Else', 'person');
            INSERT INTO entity_mentions(entity_id, passage_id, surface) VALUES (1, 10, 'janaka'), (3, 10, 'j'), (3, 11, 'j');
        """)
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_SHELF_NO_DASHBOARD="1", PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, str(TOOL), "--db", self.db, "--dir", str(self.tmp / "cologne"),
                            "--backup-dir", str(self.tmp / "bk")] + list(args),
                           capture_output=True, text=True, encoding="utf-8", env=env)
        return r.returncode, r.stdout + r.stderr

    def test_the_plan_then_the_tables(self):
        md5 = hashlib.md5(Path(self.db).read_bytes()).hexdigest()
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("vei: 122 entries", out)
        self.assertIn("3 index(es) read, 364 entries", out)
        self.assertEqual(hashlib.md5(Path(self.db).read_bytes()).hexdigest(), md5, "the plan writes nothing")
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 0, out)
        self.assertTrue(list((self.tmp / "bk").glob("context_pre_shelf_*.db")), "the backup")
        con = sqlite3.connect(self.db)
        q = lambda s, *p: con.execute(s, p).fetchall()
        jan = q("SELECT id FROM shelf_entries WHERE source = 'vei' AND key = 'janaka'")[0][0]
        refs = q("SELECT n, work, ref, ours FROM shelf_refs WHERE entry_id = ? ORDER BY id", jan)
        self.assertEqual(refs[0], (1, "\u015aatapatha Br\u0101hma\u1e47a", "xi. 3, 1, 2", None))
        self.assertEqual(refs[1], (1, "\u015aatapatha Br\u0101hma\u1e47a", "xiv. 6, 1, 1.", "2015_405693_Shatpath-Brahmanam"))
        self.assertEqual(refs[2][1:], ("B\u1e5bhad\u0101ra\u1e47yaka Upani\u1e63ad", "iii. 1, 1.", "2015_405693_Shatpath-Brahmanam"))
        self.assertEqual(refs[3][1:], ("Aitareya Br\u0101hma\u1e47a", "viii. 21", None))
        self.assertEqual(refs[4][1:3], (None, "Weber, Indische Studien, 1, 35."))
        self.assertEqual(q("SELECT name FROM shelf_xrefs WHERE entry_id = ?", jan), [("Y\u0101j\u00f1avalkya V\u0101jasaneya",)])
        body = q("SELECT body FROM shelf_entries WHERE id = ?", jan)[0][0]
        self.assertIn("A contemporary of Y\u0101j\u00f1avalkya V\u0101jasaneya.[3]", body)
        self.assertEqual(sorted(q("SELECT e.source, e.key, l.entity_id, l.how FROM shelf_links l JOIN shelf_entries e ON "
                                  "e.id = l.entry_id")),
                         [("inm", "janamejaya", 3, "exact"), ("pui", "janaka", 1, "exact"), ("vei", "janaka", 1, "exact"),
                          ("vei", "parik\u1e63it", 2, "loose")])
        inm = q("SELECT r.ref, r.ours FROM shelf_refs r JOIN shelf_entries e ON e.id = r.entry_id WHERE e.source = 'inm' "
                "ORDER BY r.id")
        self.assertEqual(inm, [("I.1.9", "MBh01"), ("VII.62\u03b1.2281", None)])
        pui = q("SELECT r.work, r.ref FROM shelf_refs r JOIN shelf_entries e ON e.id = r.entry_id WHERE e.source = 'pui' "
                "ORDER BY r.id")
        self.assertEqual(pui, [("Vi.", "IV. 5. 22-4"), ("Bh\u0101.", "IX. 13. 13-14"), ("Bh\u0101.", "X. 71. 9"),
                               ("V\u0101.", "89. 2")])
        src = q("SELECT code, entries, licence, credit FROM shelf_sources ORDER BY code")
        self.assertEqual([(c, n) for c, n, _l, _c in src], [("inm", 121), ("pui", 121), ("vei", 122)])
        self.assertEqual(src[0][2], "https://creativecommons.org/licenses/by-nc-sa/3.0/")
        self.assertTrue(src[0][3].startswith("A Test Index, XML edition. version 2013. edited by A. Editor. A Library, A Town."),
                        src[0][3])
        n1 = q("SELECT COUNT(*) FROM shelf_refs")[0][0]
        con.close()
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 0, out)
        con = sqlite3.connect(self.db)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM shelf_refs").fetchone()[0], n1, "replaced, not added")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM shelf_entries").fetchone()[0], 364)
        con.close()
        rc, out = self.run_tool("--show", "Janaka")
        self.assertEqual(rc, 0, out)
        self.assertIn("ours: entity 1 Janaka (person): named 1 time(s) in MBh01 1", out)
        self.assertIn("VEI 1, page 1-271: Janaka   [tied to ours: exact]", out)
        self.assertIn("[ours: 2015_405693_Shatpath-Brahmanam; ours is book 14 only]", out)
        self.assertIn("PUI 1, page 1-622: Janaka (I)   [tied to ours: exact]", out)
        rc, out = self.run_tool("--show", "Parikshit-not-a-name")
        self.assertIn("VERDICT: no index names", out)
        rc, out = self.run_tool("--credits")
        self.assertIn("vei: A Test Index, XML edition.", out)

    def test_too_few_entries_is_not_the_index(self):
        (self.tmp / "cologne" / "pui" / "txt" / "pui.txt").write_text("<L>1<pc>1<k1>a<k2>a\nx\u00a6 y\n<LEND>\n", encoding="utf-8")
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE: pui hold fewer than 100 entries", out)


class TheBoundary(unittest.TestCase):
    def test_local_only(self):
        sync = (SCRIPTS / "corpus_sync.py").read_text(encoding="utf-8")
        self.assertNotIn("shelf_", sync, "the mirror must not send the shelf (PC only, 21 Oct)")
        gi = (REPO / ".gitignore").read_text(encoding="utf-8") if (REPO / ".gitignore").exists() else ""
        if "DOCS78_2026_10_21" in gi:
            self.assertIn("data/shelf/", gi)

    def test_ascii_and_marks(self):
        for f in (TOOL, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
