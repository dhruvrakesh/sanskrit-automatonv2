# -*- coding: ascii -*-
"""PEOPLES_2026_10_28: scripts/peoples_index.py, the peoples of the Puranas' lists (Matsya 114, Brahmanda II.16,
Visnu II.3, Vayu 45) as the Purana Index cites them, read in GRETIL's verses, their regions as the texts word them,
tied to our names and to Raychaudhuri's claims. A made-up shelf, claims database and zip in a temp folder; every
database only read; nothing written without --yes, and then only the json and the csv; never the network."""
import contextlib, io, json, sqlite3, sys, tempfile, unittest, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "peoples_index.py"
MARK = "PEOPLES_2026_10_28"
ON = SCRIPT.exists() and (REPO / "scripts" / "vamsa_check.py").exists()
if ON:
    sys.path.insert(0, str(REPO / "scripts"))
    import peoples_index as pi   # noqa: E402

PLAIN = "1_sanskr/tei/transformations/plaintext/"
MATSYA = """# Header
# Text

t\u0101s\u0101\u1e43 nadyupanadya\u015bca \u015bata\u015bo 'tha sahasra\u015ba\u1e25
t\u0101svime kurup\u0101\u00f1c\u0101l\u0101\u1e25 \u015b\u0101lv\u0101\u015bcaiva saj\u0101\u1e45gal\u0101\u1e25 // MatsP_114.34

\u015b\u016brasen\u0101 bhadrak\u0101r\u0101 b\u0101hy\u0101\u1e25 sahapa\u1e6daccar\u0101\u1e25
matsy\u0101\u1e25 kir\u0101t\u0101\u1e25 kuly\u0101\u015bca kuntal\u0101\u1e25 k\u0101\u015biko\u015bal\u0101\u1e25 // MatsP_114.35

\u0101vant\u0101\u015bca kali\u1e45g\u0101\u015bca m\u016bk\u0101\u015bcaiv\u0101ndhakai\u1e25 saha
madhyade\u015b\u0101 janapad\u0101\u1e25 pr\u0101ya\u015ba\u1e25 parik\u012brtit\u0101\u1e25 // MatsP_114.36

g\u0101ndh\u0101r\u0101 yavan\u0101\u015bcaiva sindhusauv\u012bramadrak\u0101\u1e25
\u015bak\u0101 druhy\u0101\u1e25 pulind\u0101\u015bca // MatsP_114.41

setuk\u0101\u1e25 s\u016btik\u0101\u015bcaiva kali\u1e45g\u0101\u015bcaiva sarva\u015ba\u1e25 // MatsP_114.47

k\u0101cch\u012bk\u0101\u015bcaiva saur\u0101\u1e63\u1e6dr\u0101 \u0101nart\u0101 arbudai\u1e25 saha
ityete apar\u0101nt\u0101stu \u015b\u1e5b\u1e47u ye vindhyav\u0101sina\u1e25 // MatsP_114.51
"""
BRAHMANDA = """# Header
# Text

t\u0101svime kurup\u0101\u00f1c\u0101l\u0101\u1e25 \u015b\u0101lv\u0101 m\u0101dreyaj\u0101\u1e45gal\u0101\u1e25 // bndp_1,16.40 //

matsy\u0101\u1e25 ku\u015baly\u0101\u1e25 sau\u015baly\u0101\u1e25 kuntal\u0101\u1e25 k\u0101\u015biko\u015bal\u0101\u1e25 // bndp_1,16.41 //

g\u0101ndh\u0101r\u0101 yavan\u0101\u015bcaiva si\u1e43dhusauv\u012brama\u1e47\u1e0dal\u0101\u1e25 // bndp_1,16.47 //

kekay\u0101 da\u015b\u0101m\u0101lik\u0101\u1e25 // bndp_1,16.48 //

ko\u1e45ka\u1e47\u0101\u1e25 kantal\u0101\u015bc\u0101ndhr\u0101\u1e25 // bndp_1,16.59 //

apar\u0101nt\u0101\u015bca muhm\u0101\u015bca // bndp_1,16.46 //

k\u0101\u015bm\u012br\u0101sta\u1e45ga\u1e47\u0101stath\u0101 // bndp_1,16.53 //
"""

ENTRIES = [  # id, name, key, head, body; refs: (n, work, ref)
    (1, "Kuntala", "kuntala", "Kuntala", "(II) (c) \u2014 a kingdom of Madhya de\u015ba; a southern country.",
     [(1, "Br.", "II. 16. 41 and 59-60")]),
    (2, "Kuntala", "kuntala", "Kuntalas", "\u2014 a people of southern country;[1]", [(1, "M.", "114. 35"),
                                                                                   (2, "V\u0101.", "45. 110")]),
    (3, "G\u0101ndh\u0101ra", "g\u0101ndh\u0101ra", "G\u0101ndh\u0101ra", "(III) (c) \u2014 a northern kingdom and tribe",
     [(1, "M.", "114. 41"), (2, "Br.", "II. 16. 47")]),
    (4, "Kali\u1e45ga", "kali\u1e45ga", "Kali\u1e45gas", "\u2014 a tribe born of D\u012brghatamas",
     [(1, "M.", "114. 36 and 47"), (2, "V\u0101.", "45. 125")]),
    (5, "Kekaya", "kekaya", "Kekayas(c)", "\u2014 people of Kekaya, a northern kingdom",
     [(1, "Bh\u0101.", "X. 54. 58"), (2, "Br.", "II. 16. 48")]),
    (6, "Atraya", "atraya", "Atraya", "\u2014 a tribe (Atris).", [(1, "V\u0101.", "45. 120")]),
    (7, "Godh\u0101", "godh\u0101", "Godh\u0101", "\u2014 a river.", [(1, "M.", "114. 38")]),   # verse 38: not a list's
    (8, "Matsya", "matsya", "Matsya", "(I) \u2014 a fish.", [(1, "M.", "1. 17")]),           # not cited in a list
    (9, "K\u0101\u015b\u012b", "k\u0101\u015b\u012b", "K\u0101\u015b\u012b", "(I) (c) \u2014 a kingdom of Madhyade\u015ba",
     [(1, "M.", "114. 35"), (2, "Br.", "II. 16. 41")]),
    (10, "A\u1e45ga", "a\u1e45ga", "A\u1e45ga", "(III) (c) \u2014 An eastern kingdom.", [(1, "Br.", "II. 16. 53")]),
    (11, "Apar\u0101nta", "apar\u0101nta", "Apar\u0101nta", "\u2014 a western country.",
     [(1, "M.", "114. 51"), (2, "Br.", "II. 16. 46")]),
]


def make(root: Path):
    db = root / "context.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, lnum INTEGER, page TEXT, k1 TEXT, name TEXT,
                                key TEXT, homonym TEXT, head TEXT, body TEXT, notes TEXT);
    CREATE TABLE shelf_refs (id INTEGER PRIMARY KEY, entry_id INTEGER, n INTEGER, work TEXT, ref TEXT, ours TEXT,
                             note TEXT);
    CREATE TABLE shelf_links (entry_id INTEGER, entity_id INTEGER, how TEXT);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    """)
    for eid, name, key, head, body, refs in ENTRIES:
        con.execute("INSERT INTO shelf_entries (id, source, name, key, head, body) VALUES (?,?,?,?,?,?)",
                    (eid, "pui", name, key, head, body))
        for n, work, ref in refs:
            con.execute("INSERT INTO shelf_refs (entry_id, n, work, ref) VALUES (?,?,?,?)", (eid, n, work, ref))
    con.executemany("INSERT INTO entities VALUES (?,?,?)", [(10, "G\u0101ndh\u0101ra", "place"), (11, "Kekaya", "people")])
    con.executemany("INSERT INTO shelf_links VALUES (?,?,?)", [(3, 10, "exact"), (5, 11, "exact")])
    con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "MBh01"), (2, "old-RETIRED")])
    con.executemany("INSERT INTO passages VALUES (?,?)", [(100, 1), (101, 1), (102, 2)])
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)",
                    [(10, 100), (10, 101), (10, 102), (11, 101)])
    con.commit()
    con.close()
    (root / "shelf").mkdir()
    c = sqlite3.connect(str(root / "shelf" / "claims.db"))
    c.executescript("""
    CREATE TABLE claim_works (code TEXT PRIMARY KEY, author TEXT, title TEXT, year TEXT, licence TEXT);
    CREATE TABLE claim_reads (id INTEGER PRIMARY KEY, work TEXT, pdf_page INTEGER, status TEXT);
    CREATE TABLE claims (id INTEGER PRIMARY KEY, read_id INTEGER, work TEXT, pdf_page INTEGER, printed TEXT,
                         relation TEXT, claim TEXT, quote_check TEXT);
    CREATE TABLE claim_links (claim_id INTEGER, role TEXT, entity_id INTEGER);
    """)
    c.execute("INSERT INTO claim_works VALUES ('phai1923', 'Hemchandra Raychaudhuri', 'Political History', '1923', "
              "'public domain: published 1923')")
    c.executemany("INSERT INTO claim_reads VALUES (?,?,?,?)", [(1, "phai1923", 48, "ok"), (2, "phai1923", 48, "ok"),
                                                               (3, "phai1923", 50, "ok")])
    c.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?)", [
        (1, 1, "phai1923", 48, "30", "located_in", "An old read.", "exact"),
        (2, 2, "phai1923", 48, "30", "located_in", "Gandhara lay in the north-west.", "exact"),
        (3, 3, "phai1923", 50, "32", "other", "A quotation not on the page.", "none"),
        (4, 3, "phai1923", 50, "32", "king_of", "Nagnajit was king of Gandhara.", "close")])
    c.executemany("INSERT INTO claim_links VALUES (?,?,?)", [(1, "subject", 10), (2, "subject", 10), (3, "subject", 10),
                                                              (4, "object", 10)])
    c.commit()
    c.close()
    zp = root / "1_sanskr.zip"
    with zipfile.ZipFile(str(zp), "w") as z:
        z.writestr(PLAIN + "sa_matsyapurANa1-176.txt", MATSYA)
        z.writestr(PLAIN + "sa_brahmANDapurANa.txt", BRAHMANDA)
    return str(db), str(root / "shelf" / "claims.db"), zp


@unittest.skipUnless(ON, "scripts/peoples_index.py or scripts/vamsa_check.py is not here")
class ThePeoples(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.db, self.cdb, self.zp = make(self.t)

    def tearDown(self):
        self.td.cleanup()

    def rows(self, res):
        return {r["key"]: r for r in res["rows"]}

    def test_who_is_in_and_where(self):
        before = {p.name: p.read_bytes() for p in list(self.t.glob("*.db")) + list((self.t / "shelf").glob("*.db"))}
        res = pi.build(self.db, self.cdb, self.zp)
        rows = self.rows(res)
        self.assertEqual(set(rows), {"kuntala", "g\u0101ndh\u0101ra", "kali\u1e45ga", "kekaya", "atraya", "k\u0101\u015b\u012b",
                                     "a\u1e45ga", "apar\u0101nta"},
                         "the entries that cite a verse of a list; a verse outside the lists (M. 114. 38) and a "
                         "citation elsewhere are not")
        ku = rows["kuntala"]
        self.assertEqual([e["head"] for e in ku["entries"]], ["Kuntala", "Kuntalas"], "one name, one row")
        self.assertEqual([x["cited"] for x in ku["lists"]["br"]], [41, 59, 60])
        self.assertEqual(ku["regions"], {"m": [pi.MADHYA], "br": [pi.MADHYA]},
                         "the Brahmanda's 59 reads kantalah: not the name, so not found there")
        self.assertEqual([x["verdict"] for x in ku["lists"]["br"]], ["named", "not found", "not found"])
        self.assertEqual(ku["agree"], "agree")
        self.assertEqual(ku["lists"]["va"], [{"cited": 110, "found": [], "verdict": "not held"}])
        ka = rows["kali\u1e45ga"]
        self.assertEqual(ka["regions"]["m"], [pi.MADHYA, pi.DAKSINA, pi.APARANTA],
                         "the Matsya names the Kalingas twice: 36 (madhyadesa) and 47 (the southern and western)")
        ga = rows["g\u0101ndh\u0101ra"]
        self.assertEqual(ga["regions"], {"m": [pi.UDICYA], "br": [pi.UDICYA]})
        self.assertEqual(ga["ours"]["passages"], 2, "the retired text is not counted")
        self.assertEqual([c["claim"] for c in ga["raychaudhuri"]],
                         ["Gandhara lay in the north-west.", "Nagnajit was king of Gandhara."],
                         "the latest read of a page; the quotation found on the page")
        ke = rows["kekaya"]
        self.assertEqual(ke["regions"], {"br": [pi.UDICYA]})
        self.assertEqual(ke["agree"], "", "in one list only")
        self.assertEqual(list(rows["atraya"]["lists"]), ["va"])
        kasi = rows["k\u0101\u015b\u012b"]
        self.assertEqual([f["form"] for x in kasi["lists"]["m"] for f in x["found"]], ["k\u0101\u015biko\u015bal\u0101\u1e25"],
                         "a member of a compound")
        self.assertEqual(kasi["agree"], "agree")
        self.assertEqual([x["verdict"] for x in rows["a\u1e45ga"]["lists"]["br"]], ["not found"],
                         "the anga of tanganah is not the Angas")
        ap = rows["apar\u0101nta"]
        self.assertEqual([x["verdict"] for x in ap["lists"]["m"]], ["not found"], "the Matsya's closing word is no people")
        self.assertEqual(ap["regions"], {"br": [pi.UDICYA]}, "the Brahmanda's northern list names a people Aparanta")
        s = res["summary"]
        self.assertEqual((s["peoples"], s["vayu_only"], s["raychaudhuri"], s["in_our_texts"]), (8, 1, 1, 2))
        after = {p.name: p.read_bytes() for p in list(self.t.glob("*.db")) + list((self.t / "shelf").glob("*.db"))}
        self.assertEqual(before, after, "read-only")

    def test_the_regions_of_the_texts(self):
        self.assertEqual(pi.region_of("m", (114, 36)), (pi.MADHYA,))
        self.assertEqual(pi.region_of("m", (114, 38)), (), "Govardhana and the Godavari: not a list")
        self.assertEqual(pi.region_of("m", (114, 51)), (pi.DAKSINA, pi.APARANTA), "no boundary in the Matsya")
        self.assertEqual(pi.region_of("br", (1, 16, 59)), (pi.DAKSINA,))
        self.assertEqual(pi.region_of("br", (1, 16, 60)), (pi.APARANTA,))
        self.assertEqual(pi.region_of("br", (1, 16, 66)), (), "the closing words only")
        self.assertEqual(pi.region_of("vi", (2, 3, 16)), ())

    def test_the_index_s_own_words(self):
        self.assertIn(("br", (2, 16), [48]), pi.text_cites("Bh\u0101. X. [50 (V) 3]; 52. 11 [14] Br. II. 16. 48."),
                      "a reference after a bracketed one")
        self.assertEqual(pi.text_cites("Br. II. 18. 50; 16. 47"), [("br", (2, 18), [50]), ("br", (2, 16), [47])],
                         "a bare reference keeps the pada")
        self.assertEqual(pi.text_cites("M. 114. 36 and 47; V\u0101. 45. 110, 127; 47. 42."),
                         [("m", (114,), [36, 47]), ("va", (45,), [110, 127]), ("va", (47,), [42])])
        self.assertEqual(pi.text_cites("eastern country M. P.; a Kingdom"), [])

    def test_without_the_zip(self):
        res = pi.build(self.db, self.cdb, self.t / "none.zip")
        ga = self.rows(res)["g\u0101ndh\u0101ra"]
        self.assertEqual([x["verdict"] for x in ga["lists"]["m"]], ["not held"])
        self.assertFalse(res["lists"]["m"]["held"])

    def test_the_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = pi.main(["--db", self.db, "--claims-db", self.cdb, "--zip", str(self.zp),
                          "--json", str(self.t / "p.json"), "--csv", str(self.t / "p.csv")])
        self.assertEqual(rc, 0)
        s = out.getvalue()
        self.assertIn("VERDICT: 8 peoples in the Puranas' lists", s)
        self.assertIn("; nothing written", s)
        self.assertIn("Not read: B. C. Law, Tribes in Ancient India", s)
        self.assertFalse((self.t / "p.json").exists())
        with contextlib.redirect_stdout(io.StringIO()):
            rc = pi.main(["--db", self.db, "--claims-db", self.cdb, "--zip", str(self.zp), "--yes",
                          "--json", str(self.t / "p.json"), "--csv", str(self.t / "p.csv")])
        self.assertEqual(rc, 0)
        data = json.loads((self.t / "p.json").read_text(encoding="utf-8"))
        self.assertEqual(data["mark"], MARK)
        self.assertEqual(len(data["rows"]), 8)
        self.assertIn("kuntala,Kuntala,Kuntala; Kuntalas,35,", (self.t / "p.csv").read_text(encoding="utf-8"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = pi.main(["--db", self.db, "--claims-db", self.cdb, "--zip", str(self.zp), "--name", "Kekaya"])
        self.assertEqual(rc, 0)
        self.assertIn("Dikshitar s.v. Kekayas(c)", out.getvalue())


class TheFile(unittest.TestCase):
    def test_ascii_and_mark(self):
        for f in (SCRIPT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
