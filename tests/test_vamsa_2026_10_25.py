# -*- coding: ascii -*-
"""VAMSA_CHECK_2026_10_25 and VAMSA_UI_2026_10_25: the indexes' kinships read against GRETIL's Sanskrit
(scripts/vamsa_check.py) and the lines of descent drawn from them (scripts/vamsa_view.py, scripts/vamsa.html, /vamsa,
/api/vamsa). A made-up zip, database and kin.db in a temp folder; never data/context.db, never the network, no
model."""
import hashlib, importlib.util, io, json, sqlite3, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
CHECK = S / "vamsa_check.py"
VIEW = S / "vamsa_view.py"
PAGE = S / "vamsa.html"
PAT = S / "patch_vamsa_ui_2026_10_25.py"
MARK_C, MARK_U = "VAMSA_CHECK_2026_10_25", "VAMSA_UI_2026_10_25"
PLAIN = "1_sanskr/tei/transformations/plaintext/"


def load(path: Path, name: str):
    if str(S) not in sys.path:
        sys.path.insert(0, str(S))
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tei(prefix: str, verses: list) -> str:
    out = ["# Header", "  a made-up text", "# Text", ""]
    for ref, words in verses:
        out.append("%s // %s_%s //" % (words, prefix, ref))
        out.append("")
    return "\n".join(out)


def make_zip(p: Path):
    with zipfile.ZipFile(str(p), "w") as z:
        z.writestr(PLAIN + "sa_viSNupurANa.txt", tei("vip", [
            ("4,4.85", "raghor aja\u1e25"), ("4,4.86", "aj\u0101d da\u015baratha\u1e25"),
            ("4,4.87", "da\u015barath\u0101d r\u0101malak\u1e63ma\u1e47abharata\u015batrughn\u0101\u1e25")]))
        z.writestr(PLAIN + "sa_viSNupurANa-crit.txt", tei("ViP", [("4,4.86", "aj\u0101d da\u015baratha\u1e25")]))
        z.writestr(PLAIN + "sa_bhAgavatapurANa.txt", tei("bhp", [
            ("09.10.001", "\u015br\u012b\u015buka uv\u0101ca"), ("09.10.002", "da\u015barath\u0101t r\u0101ma\u1e25")]))
        z.writestr(PLAIN + "sa_brahmANDapurANa.txt", tei("bndp", [("2,63.199", "r\u0101m\u0101t ku\u015ba\u1e25")]))
        z.writestr(PLAIN + "sa_matsyapurANa1-176.txt", tei("MatsP", [("12,49", "tato 'jap\u0101las tasm\u0101t")]))
        z.writestr(PLAIN + "sa_harivaMza.txt", tei("HV", [("10,1", "ik\u1e63v\u0101kor va\u1e43\u015bam")]))
        z.writestr(PLAIN + "sa_rAmAyaNa.txt", tei("R", [("1,069.017", "aj\u0101d da\u015baratha\u1e25 r\u0101jan")]))
        z.writestr("1_sanskr/2_epic/mbh/mbh1-18u.htm",
                   "<html><body>\n01,090.047\tjanamejaya\u1e25 p\u0101rik\u1e63ita\u1e25 parik\u1e63ita\u1e25 suta\u1e25<BR>\n"
                   "01,090.048\t\u015bat\u0101n\u012bka\u1e25<BR>\n01,000.000*0001_01\tparik\u1e63ito janamejayaH star<BR>\n"
                   "</body></html>\n")


def make_db(t: Path):
    con = sqlite3.connect(str(t / "data" / "context.db"))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_variants (entity_id INTEGER, variant TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, head TEXT, body TEXT);
    CREATE TABLE shelf_links (entry_id INTEGER, entity_id INTEGER, how TEXT);
    """)
    con.execute("INSERT INTO entities VALUES (1, 'Da\u015baratha', 'person')")
    con.executemany("INSERT INTO shelf_entries (id, source, head) VALUES (?, ?, ?)", [
        (10, "pui", "Raghu (I)"), (11, "pui", "Aja (IV)"), (12, "pui", "Da\u015baratha (I)"),
        (13, "pui", "Da\u015baratha (II)"), (14, "pui", "R\u0101ma (II)"), (15, "pui", "Ku\u015ba (I)"),
        (16, "pui", "Atithi (I)"), (20, "inm", "Janamejaya[1]"), (21, "inm", "Parik\u1e63it"),
        (30, "pui", "Ajap\u0101la"), (31, "pui", "Indra (I)")])
    con.execute("INSERT INTO shelf_links VALUES (13, 1, 'exact')")
    con.commit()
    con.close()
    k = sqlite3.connect(str(t / "data" / "shelf" / "kin.db"))
    k.executescript("""
    CREATE TABLE kin_done (entry_id INTEGER, source TEXT, entry_sha TEXT, read_id INTEGER, prompt_version TEXT,
                           engine TEXT);
    CREATE TABLE kin (id INTEGER PRIMARY KEY, read_id INTEGER, source TEXT, entry_id INTEGER, head TEXT, subject TEXT,
                      relation TEXT, object TEXT, words TEXT, refs TEXT, words_check TEXT, direction TEXT, at TEXT);
    CREATE TABLE kin_ties (kin_id INTEGER PRIMARY KEY, subject_entity INTEGER, object_entity INTEGER, how_subject TEXT,
                           how_object TEXT, verdict TEXT, passages INTEGER, texts INTEGER, places TEXT, scholar TEXT,
                           scholar_note TEXT, checked_at TEXT, mark TEXT);
    """)
    rows = [  # id, src, entry, head, subject, relation, object, refs
        (1, "pui", 11, "Aja (IV)", "Aja (IV)", "son_of", "Raghu (I)", ["Vi. IV. 4. 85"]),
        (2, "pui", 13, "Da\u015baratha (II)", "Da\u015baratha (II)", "son_of", "Aja (IV)", ["Vi. IV. 4. 86"]),
        (3, "pui", 13, "Da\u015baratha (II)", "Da\u015baratha (II)", "married", "Kausaly\u0101",
         ["Bh\u0101. IX. 10. 2"]),
        (11, "pui", 14, "R\u0101ma (II)", "R\u0101ma (II)", "father_of", "\u015ar\u012b Ku\u015ba", []),
        (4, "pui", 14, "R\u0101ma (II)", "R\u0101ma (II)", "son_of", "Da\u015baratha", ["Bh\u0101. IX. 10. 2"]),
        (5, "pui", 15, "Ku\u015ba (I)", "Ku\u015ba (I)", "son_of", "R\u0101ma (II)", ["Br. III. 63. 199"]),
        (6, "pui", 16, "Atithi (I)", "Atithi (I)", "son_of", "Ku\u015ba (I)", ["V\u0101. 88. 199"]),
        (7, "pui", 30, "Ajap\u0101la", "Ajap\u0101la", "father_of", "Da\u015baratha", ["M. 12. 49"]),
        (8, "pui", 31, "Indra (I)", "Indra (I)", "king_of", "Gods", ["M. 200. 3"]),
        (9, "inm", 20, "Janamejaya[1]", "Janamejaya[1]", "son_of", "Parik\u1e63it", ["I, 95, 3830"]),
        (10, "pui", 12, "Da\u015baratha (I)", "Da\u015baratha (I)", "son_of", "M\u016blaka", []),
    ]
    for kid, src, eid, head, subj, rel, obj, refs in rows:
        k.execute("INSERT INTO kin VALUES (?,1,?,?,?,?,?,?,?,?,'exact','agrees','')",
                  (kid, src, eid, head, subj, rel, obj, "the words", json.dumps(refs, ensure_ascii=False)))
        k.execute("INSERT INTO kin_ties (kin_id, verdict, passages, texts, places, scholar, scholar_note) "
                  "VALUES (?, 'not tied', 0, 0, '[]', ?, '')", (kid, "agrees" if kid == 2 else ""))
    k.executemany("INSERT INTO kin_done (entry_id, source, read_id, prompt_version, engine) VALUES (?,?,1,'v','e')",
                  sorted({(r[2], r[1]) for r in rows}))
    k.commit()
    k.close()


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.t = Path(cls.td.name)
        (cls.t / "data" / "shelf").mkdir(parents=True)
        cls.zip = cls.t / "1_sanskr.zip"
        make_zip(cls.zip)
        make_db(cls.t)
        cls.vc = load(CHECK, "vamsa_check_t")
        cls.store = cls.t / "data" / "shelf" / "vamsa.db"
        cls.kin = cls.t / "data" / "shelf" / "kin.db"
        cls.db = cls.t / "data" / "context.db"
        cls.before = (md5(cls.kin), md5(cls.db))
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            cls.rc = cls.vc.main(["--zip", str(cls.zip), "--kin", str(cls.kin), "--store", str(cls.store),
                                  "--exports", str(cls.t / "exports"), "--yes"])
        finally:
            sys.stdout = old
        cls.out = buf.getvalue()

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def rel(self, kid):
        con = sqlite3.connect(str(self.store))
        try:
            return con.execute("SELECT cited, best_text, best_ref, subject_form, object_form, mbh, mbh_first, cites "
                               "FROM vamsa_rel WHERE kin_id = ?", (kid,)).fetchone()
        finally:
            con.close()


class TestLetters(Base):
    def test_skeleton(self):
        vc = self.vc
        self.assertEqual(vc.skel("sa\u1e43jaya"), vc.skel("sa\u00f1jaya"))
        self.assertEqual(vc.skel("bharata"), "Brt")
        self.assertTrue(vc.word_form(vc.name_key("Aja (IV)"), "aj\u0101d"))          # a short name by its case forms
        self.assertFalse(vc.word_form(vc.name_key("Bh\u016bta"), "bh\u016bt\u0101ni"))   # not the neuter plural
        self.assertTrue(vc.word_form(vc.name_key("Da\u015baratha"), "da\u015barath\u0101t"))
        self.assertTrue(vc.word_form(vc.name_key("Purudv\u0101n"), "purudvantam"))

    def test_english_and_short(self):
        vc = self.vc
        self.assertIsNone(vc.name_key("Gods"))
        self.assertIsNotNone(vc.name_key("Paurava race"))
        self.assertEqual(vc.keys_of("Ap"), [])                         # too short to look for
        self.assertIn("anu\u1e25", vc.keys_of("Anu")[0][3])           # Anu, by its case forms
        self.assertTrue(vc.keys_of("Chola"))                           # with the old spelling as a second key

    def test_citations(self):
        vc = self.vc
        c = vc.parse_cites(["Br. III. 71. 145 & 189."])
        self.assertEqual((c[0][0], c[0][1], c[0][2]), ("br", (3, 71), [145, 189]))
        self.assertEqual(vc.parse_cites(["M. 44. 63-5"])[0][2], [63, 64, 65])
        c = vc.parse_cites(["Br. II. 23. 3; IV. 29. 123"])
        self.assertEqual([(x[0], x[1]) for x in c], [("br", (2, 23)), ("br", (4, 29))])
        self.assertEqual(vc.parse_cites(["Bha. IX. 9. 17-18"])[0][:3], ("bh", (9, 9), [17, 18]))
        self.assertEqual(vc.parse_cites(["M. 49. 42", "50. 78"])[1][:3], ("m", (50,), [78]))
        self.assertEqual(vc.gretil_keys("br", (3, 70), 46), [("br", (2, 70, 46))])
        self.assertEqual(vc.gretil_keys("m", (200,), 3), [])
        self.assertEqual(vc.gretil_keys("va", (88,), 5), [])


class TestCheck(Base):
    def test_ran(self):
        self.assertEqual(self.rc, 0, self.out)
        self.assertIn("VERDICT:", self.out)
        self.assertTrue((self.t / "exports" / "vamsa_checks.csv").exists())
        s = json.loads((self.t / "exports" / "vamsa_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["mark"], MARK_C)

    def test_verdicts(self):
        self.assertEqual(self.rel(2)[:3], ("both", "vi", "4.4.86"))       # Vi. IV. 4. 86: aj\u0101d da\u015baratha\u1e25
        self.assertEqual(self.rel(5)[:3], ("both", "br", "2.63.199"))     # Br. III -> GRETIL part 2
        self.assertEqual(self.rel(6)[0], "not held")                       # the Vayu
        self.assertEqual(self.rel(7)[0], "one")                            # the Matsya names Ajapala only
        self.assertEqual(self.rel(8)[0], "not looked for")                 # "Gods"
        self.assertEqual(self.rel(10)[0], "no citation")

    def test_epic_counts_without_words(self):
        r = self.rel(9)
        self.assertEqual((r[5], r[6]), (1, "1.90.47"))                     # the star line is not the CE's text
        con = sqlite3.connect(str(self.store))
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM vamsa_verses WHERE text = 'mbh'").fetchone()[0], 0)
            self.assertTrue(con.execute("SELECT words FROM vamsa_verses WHERE text = 'vi' AND ref = '4.4.86'").fetchone())
            show = dict(con.execute("SELECT code, show FROM vamsa_texts"))
        finally:
            con.close()
        self.assertEqual(show["mbh"], 0)
        self.assertEqual(show["vi"], 1)

    def test_scheduled_and_inputs_untouched(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = self.vc.main(["--zip", str(self.zip), "--kin", str(self.kin), "--store", str(self.store),
                               "--exports", str(self.t / "exports"), "--scheduled"])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        self.assertIn("nothing new", buf.getvalue())
        self.assertEqual((md5(self.kin), md5(self.db)), self.before)

    def test_plan_writes_nothing(self):
        other = self.t / "plan_store.db"
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = self.vc.main(["--zip", str(self.zip), "--kin", str(self.kin), "--store", str(other),
                               "--exports", str(self.t / "exports_plan")])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        self.assertFalse(other.exists())
        self.assertFalse((self.t / "exports_plan").exists())
        self.assertIn("the plan", buf.getvalue())


class TestView(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vv = load(VIEW, "vamsa_view_t")

    def test_tree(self):
        T = self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", 13)
        heads = [r["head"] for r in T["line"]]
        self.assertEqual(heads[:3], ["Raghu (I)", "Aja (IV)", "Da\u015baratha (II)"])
        self.assertIn("R\u0101ma (II)", heads)
        self.assertIn("Ku\u015ba (I)", heads)
        self.assertEqual(T["line"][T["me"]]["head"], "Da\u015baratha (II)")
        step = T["steps"][1]                                            # Aja (IV) -> Dasaratha (II)
        self.assertEqual(step["cited"], "both")
        self.assertEqual(step["scholar"], "agrees")
        self.assertTrue(any(k.startswith("vi|4.4.86") for k in T["verses"]))
        i = heads.index("R\u0101ma (II)")
        self.assertIn(T["steps"][i - 1]["joined"], ("rule", "verse"))
        self.assertEqual(T["line"][T["me"]]["entity"], 1)               # our name, through the exact shelf link

    def test_honorific(self):
        g = self.vv._graph(str(self.db), str(self.kin))
        # Rama (II) father_of "Sri Kusa": the honorific aside, the one entry of the name
        self.assertIn(("pui", 14, 15), g["edges"])

    def test_join_by_shared_verse(self):
        g = self.vv._graph(str(self.db), str(self.kin))
        # Rama (II) son_of "Dasaratha": two entries of the name; Dasaratha (II)'s entry cites Bha. IX. 10. 2 too
        self.assertIn(("pui", 13, 14), g["edges"])
        self.assertTrue(any(r["join_object"] == "verse" for r in g["edges"][("pui", 13, 14)]))

    def test_named_only(self):
        g = self.vv._graph(str(self.db), str(self.kin))
        # Ajapala father_of "Dasaratha": no shared verse, two entries of the name: a leaf of its own, never a join
        kids = [c for (s, p, c) in g["edges"] if s == "pui" and p == 30]
        self.assertTrue(kids and all(c < 0 for c in kids))

    def test_lines_find_and_readonly(self):
        L = self.vv.lines(str(self.db), str(self.kin), min_len=3)
        self.assertTrue(L["lines"]["pui"])
        self.assertEqual(L["lines"]["pui"][0]["heads"][0], "Raghu (I)")
        F = self.vv.find(str(self.db), str(self.kin), "Da\u015baratha")
        self.assertTrue(F and F[0]["head"].startswith("Da\u015baratha"))
        self.assertEqual(self.vv.find(str(self.db), str(self.kin), ""), [])
        self.assertIn("error", self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", 99999))
        self.assertEqual((md5(self.kin), md5(self.db)), self.before)

    def test_via(self):
        T = self.vv.tree(str(self.db), str(self.kin), str(self.store), "pui", 13, via=11)
        self.assertEqual(T["line"][T["me"] - 1]["head"], "Aja (IV)")


class TestWiring(unittest.TestCase):
    def test_sources_ascii_and_marked(self):
        for p, mark in ((CHECK, MARK_C), (VIEW, MARK_U), (PAGE, MARK_U), (PAT, MARK_U)):
            raw = p.read_bytes()
            self.assertTrue(all(b < 128 for b in raw), p.name)
            self.assertIn(mark.encode(), raw, p.name)

    def test_page(self):
        t = PAGE.read_text(encoding="ascii")
        for s in ("/api/vamsa?", "lines: 1", "find:", "via", "mode=professor", "rights",
                  "@media (max-width:760px)"):
            self.assertIn(s, t)
        self.assertNotIn("localStorage", t)

    def test_dashboard_and_pages(self):
        d = (S / "dashboard.py").read_text(encoding="utf-8")
        if MARK_U not in d:
            self.skipTest("patch_vamsa_ui_2026_10_25.py not applied yet")
        self.assertIn('@app.get("/vamsa")', d)
        self.assertIn('@app.get("/api/vamsa")', d)
        self.assertIn('href="/vamsa"', (S / "dashboard_static.html").read_text(encoding="utf-8"))
        self.assertIn("/vamsa?src=", (S / "relations.html").read_text(encoding="utf-8"))
        a = (S / "ask.html").read_text(encoding="utf-8")
        self.assertIn('P.get("q")', a)
        self.assertNotIn("ask();\n  })();", a)          # the question is put in the box, never asked

    def test_patch_replays(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for f in ("dashboard.py", "dashboard_static.html", "relations.html", "ask.html"):
                src = S / f
                bak = sorted(S.glob(f + ".bak_vamsaui_*"))
                (t / "scripts" / f).write_bytes((bak[0] if bak else src).read_bytes())
            for f in ("vamsa_view.py", "vamsa.html", "vamsa_check.py"):
                (t / "scripts" / f).write_bytes((S / f).read_bytes())
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=str(t), capture_output=True, text=True)
            if "already carries" in r.stdout and "CHECK OK" not in r.stdout and "wrote" not in r.stdout:
                self.skipTest("only patched copies to replay against")
            self.assertIn("CHECK OK", r.stdout + r.stderr)
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r2 = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r2.stdout)


if __name__ == "__main__":
    unittest.main()
