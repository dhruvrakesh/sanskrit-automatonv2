# -*- coding: ascii -*-
"""ASK_PROF_2026_10_23: the Professor (B4, A1). Asked with mode "professor", /api/ask gives the model the scholarly
English where a verse has it, the IAST, the names the verses name with whom our texts name them (entity_links), what
Raychaudhuri says of those names (claims.db: the latest read of each page only) and the relations the indexes state
(kin.db: only those whose words stand in the entry and whose direction agrees); each such statement numbered [S1] ...
The verses mode is as before; the model is told not to speak as any real person; without the shelf it answers from
the verses and the links. scripts/ask.html offers the two modes and shows the [S] statements. A made-up database in a
temp folder; the dashboard's functions are read from its source, never imported; never the network."""
import ast, json, pathlib, re, sqlite3, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "scripts" / "dashboard.py"
PAGE = REPO / "scripts" / "ask.html"
PAT = REPO / "scripts" / "patch_ask_prof_2026_10_23.py"
MARK = "ASK_PROF_2026_10_23"
ON = DASH.exists() and MARK.encode() in DASH.read_bytes()


def source() -> str:
    return DASH.read_bytes().decode("utf-8").replace("\r\n", "\n")


def pick(src: str, names) -> str:
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out.append(ast.get_source_segment(src, node))
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            out.append(ast.get_source_segment(src, node))
    return "\n\n".join(out)


def make(root: Path, shelf: bool = True) -> str:
    (root / "shelf").mkdir(parents=True, exist_ok=True)
    db = root / "context.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    CREATE TABLE entity_links (a INTEGER, b INTEGER, rel TEXT, passages INTEGER, texts INTEGER, docs TEXT, places TEXT,
                               built_at TEXT, mark TEXT, PRIMARY KEY (a, b, rel));
    """)
    con.executemany("INSERT INTO entities VALUES (?,?,?)", [(1, "Janaka", "person"), (2, "Y\u0101j\u00f1avalkya", "person"),
                                                            (3, "Videha", "place"), (4, "Agni", "deity")])
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)",
                    [(1, 11), (2, 11), (1, 12), (3, 12), (4, 13)])
    con.executemany("INSERT INTO entity_links VALUES (?,?,?,?,?,'','[]','t','m')",
                    [(1, 2, "together", 33, 1), (1, 3, "together", 29, 2), (1, 2, "near", 76, 1)])
    con.commit()
    con.close()
    if shelf:
        c = sqlite3.connect(str(root / "shelf" / "claims.db"))
        c.executescript("""
        CREATE TABLE claim_reads (id INTEGER PRIMARY KEY, work TEXT, pdf_page INTEGER, status TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, read_id INTEGER, work TEXT, pdf_page INTEGER, printed TEXT,
                             relation TEXT, claim TEXT, stance TEXT, hedge TEXT);
        CREATE TABLE claim_links (claim_id INTEGER, role TEXT, entity_id INTEGER);
        """)
        c.executemany("INSERT INTO claim_reads VALUES (?,?,?,?)", [(1, "phai1923", 36, "ok"), (2, "phai1923", 36, "ok")])
        c.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?)", [
            (1, 1, "phai1923", 36, "18", "contemporary_of", "An old reading of the page.", "asserts", ""),
            (2, 2, "phai1923", 36, "18", "contemporary_of", "Y\u0101j\u00f1avalkya was a contemporary of Janaka.", "asserts", ""),
            (3, 2, "phai1923", 36, "18", "other", "Janaka was a famous king.", "asserts", "according to tradition")])
        c.executemany("INSERT INTO claim_links VALUES (?,?,?)", [(1, "object", 1), (2, "object", 1), (2, "subject", 2),
                                                                  (3, "subject", 1)])
        c.commit()
        c.close()
        k = sqlite3.connect(str(root / "shelf" / "kin.db"))
        k.executescript("""
        CREATE TABLE kin (id INTEGER PRIMARY KEY, read_id INTEGER, source TEXT, entry_id INTEGER, head TEXT, subject TEXT,
                          relation TEXT, object TEXT, words TEXT, refs TEXT, words_check TEXT, direction TEXT, at TEXT);
        CREATE TABLE kin_ties (kin_id INTEGER PRIMARY KEY, subject_entity INTEGER, object_entity INTEGER, how_subject TEXT,
                               how_object TEXT, verdict TEXT, passages INTEGER, texts INTEGER, places TEXT, scholar TEXT,
                               scholar_note TEXT, checked_at TEXT, mark TEXT);
        """)
        k.executemany("INSERT INTO kin (id, source, head, subject, relation, object, words, refs, words_check, direction) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?)", [
                          (1, "vei", "Janaka", "Janaka", "king_of", "Videha", "king of Videha", '["iii. 3. 1"]', "exact", "agrees"),
                          (2, "vei", "Janaka", "Janaka", "father_of", "Agni", "a hymn to Agni", "[]", "none", "unknown"),
                          (3, "pui", "Janaka", "Janaka", "son_of", "Videha", "father of Videha", "[]", "exact", "disagrees")])
        k.executemany("INSERT INTO kin_ties (kin_id, subject_entity, object_entity, verdict) VALUES (?,?,?,?)",
                      [(1, 1, 3, "named together"), (2, 1, 4, "not tied"), (3, 1, 3, "named together")])
        k.commit()
        k.close()
    return str(db)


SOURCES = [
    {"n": 1, "tag": "sb p95.1", "doc": "sb", "page_no": 95, "idx": 1, "english": "Janaka of Videha sacrificed.",
     "pid": 11, "iast": "janako ha vaideha\u1e25", "scholar": "Janaka, king of Videha, offered a sacrifice."},
    {"n": 2, "tag": "sb p95.5", "doc": "sb", "page_no": 95, "idx": 5, "english": "The Kurus and Panchalas came.", "pid": 12},
    {"n": 3, "tag": "story:x", "doc": "story", "page_no": 0, "idx": 0, "english": "A retelling.", "kind": "story",
     "link": "/stories", "label": "retelling"},
]


@unittest.skipUnless(ON, "ASK_PROF_2026_10_23 is not applied to scripts/dashboard.py here")
class TheProfessor(unittest.TestCase):
    def setUp(self):
        self.src = source()
        code = pick(self.src, {"_ask_scholarly", "_ask_prof_message", "_PROF_SHELF", "_PROF_CLAIM_RELS",
                               "_ASK_SYSTEM_PROF"})
        self.ns = {"sqlite3": sqlite3, "pathlib": pathlib, "json": json}
        exec(compile(code, "dashboard.prof", "exec"), self.ns)
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_what_the_professor_reads(self):
        db = make(self.t)
        before = {p.name: p.read_bytes() for p in list(self.t.glob("*.db")) + list((self.t / "shelf").glob("*.db"))}
        sch = self.ns["_ask_scholarly"](db, [dict(s) for s in SOURCES])
        names = [n["name"] for n in sch["names"]]
        self.assertEqual(names[0], "Janaka", "named in both passages")
        self.assertEqual(set(names), {"Janaka", "Y\u0101j\u00f1avalkya", "Videha"}, "only the names of these passages")
        jan = sch["names"][0]
        self.assertEqual([(x["name"], x["passages"]) for x in jan["together"]], [("Y\u0101j\u00f1avalkya", 33), ("Videha", 29)],
                         "together only, most passages first")
        texts = [i["text"] for i in sch["items"]]
        self.assertIn("Y\u0101j\u00f1avalkya was a contemporary of Janaka.", texts)
        self.assertNotIn("An old reading of the page.", texts, "the latest read of a page only")
        kin = [i for i in sch["items"] if i["kind"] == "index"]
        self.assertEqual(len(kin), 1, "words not in the entry, and a wrong direction, are left out")
        self.assertEqual((kin[0]["source"], kin[0]["where"]), ("Vedic Index (Macdonell and Keith)", "s.v. Janaka"))
        self.assertIn("king of Videha", kin[0]["text"])
        self.assertEqual([i["n"] for i in sch["items"]], ["S%d" % k for k in range(1, len(sch["items"]) + 1)])
        self.assertEqual(sch["read"], {"links": True, "claims": True, "indexes": True})
        after = {p.name: p.read_bytes() for p in list(self.t.glob("*.db")) + list((self.t / "shelf").glob("*.db"))}
        self.assertEqual(before, after, "read-only")
        msg = self.ns["_ask_prof_message"]("Who was Janaka?", SOURCES, sch)
        self.assertIn("[1] [sb p95.1] IAST: janako ha vaideha\u1e25 | scholarly English: Janaka, king of Videha", msg)
        self.assertIn("[2] [sb p95.5] working English: The Kurus", msg)
        self.assertIn("(EDITORIAL: retelling)", msg)
        self.assertIn("- Janaka (person), in 2 of the passages: named with Y\u0101j\u00f1avalkya (33 passages, 1 texts)", msg)
        self.assertRegex(msg, r"\[S\d\] Raychaudhuri, Political History of Ancient India \(1923\), p\. 18, on ")
        self.assertTrue(msg.rstrip().endswith("Answer as the professor, citing [tags] and [S numbers]:"))

    def test_without_the_shelf(self):
        db = make(self.t, shelf=False)
        sch = self.ns["_ask_scholarly"](db, [dict(s) for s in SOURCES])
        self.assertEqual(sch["items"], [])
        self.assertEqual(sch["read"], {"links": True, "claims": False, "indexes": False})
        self.assertIn("(none for these names)", self.ns["_ask_prof_message"]("q", SOURCES, sch))
        self.assertEqual(self.ns["_ask_scholarly"](db, [{"n": 1, "tag": "x"}])["names"], [], "no passage id, no names")

    def test_the_instruction(self):
        s = self.ns["_ASK_SYSTEM_PROF"]
        for x in ("USING ONLY the evidence given", "do not speak as any real person", "never quote or paraphrase a "
                  "scholar from memory", "how firm each inference is", "[S2]"):
            self.assertIn(x, s)

    def test_the_wiring(self):
        tree = ast.parse(self.src)
        api = [ast.get_source_segment(self.src, n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "api_ask"][0]
        self.assertIn('ask_mode = "professor" if str(data.get("mode") or "") == "professor" else "verses"', api)
        self.assertLess(api.index("_ask_enrich(db, sources)"), api.index("_ask_scholarly(db, sources)"))
        self.assertIn('_sys = _ASK_SYSTEM_PROF if ask_mode == "professor" else _ASK_SYSTEM', api)
        self.assertIn('kind=("ask_prof" if ask_mode == "professor" else "ask")', api)
        self.assertIn('"ask_mode": ask_mode, "scholarly": scholarly', api)
        self.assertIn('user_msg = "PASSAGES:\\n" + "\\n".join(ctx) + f"\\n\\nQUESTION: {q}\\n\\nAnswer, citing [tags]:"', api,
                      "the verses mode is as before")


@unittest.skipUnless(PAGE.exists() and MARK.encode() in PAGE.read_bytes(), "the page is not here")
class ThePage(unittest.TestCase):
    def test_the_modes_and_the_statements(self):
        s = PAGE.read_bytes().decode("ascii")
        self.assertIn('data-mode="professor"', s)
        self.assertIn("mode: MODE", s)
        js = re.search(r"<script>(.*)</script>", s, re.S).group(1)
        ids = set(re.findall(r'\$\("([A-Za-z]+)"\)', js))
        self.assertEqual(ids - set(re.findall(r'id="([A-Za-z]+)"', s)), set())
        self.assertIn('class="cite sch"', js)
        self.assertEqual(js.count("localStorage."), 2, "storage only through the guarded helper")


class ThePatcher(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
