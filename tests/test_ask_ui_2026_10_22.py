# -*- coding: ascii -*-
"""ASK_UI_2026_10_22: the one Ask page (U1). scripts/ask.html is ASCII, loads no script from elsewhere, and every element
its script reads is on the page; /api/ask's sources are enriched (_ask_enrich in scripts/dashboard.py) with the
Sanskrit, the IAST, the engines, the register's state, the scholarly English only where it passed and its Sanskrit is
unchanged, and the names, read-only, and an error never stops Ask; the call comes before the model is asked and the
prompt is untouched; the patcher applies once, from the copies it backed up, and refuses where it does not belong.
A made-up database in a temp folder; never data/context.db, never the network."""
import ast, hashlib, pathlib, re, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "scripts" / "ask.html"
DASH = REPO / "scripts" / "dashboard.py"
PAT = REPO / "scripts" / "patch_ask_ui_2026_10_22.py"
MARK = "ASK_UI_2026_10_22"
PAGE_ON = PAGE.exists() and MARK.encode() in PAGE.read_bytes()
DASH_ON = DASH.exists() and MARK.encode() in DASH.read_bytes()


def src_hash(text) -> str:   # as scripts/scholar_translate.py
    return hashlib.sha256(" ".join(str(text or "").split()).encode("utf-8")).hexdigest()[:16]


def dash_source() -> str:
    return DASH.read_bytes().decode("utf-8").replace("\r\n", "\n")


def function(src: str, name: str) -> str:
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise AssertionError("no function " + name)


@unittest.skipUnless(PAGE_ON, "ASK_UI_2026_10_22 is not applied to scripts/ask.html here")
class ThePage(unittest.TestCase):
    def setUp(self):
        self.b = PAGE.read_bytes()
        self.s = self.b.decode("ascii")
        self.js = re.search(r"<script>(.*)</script>", self.s, re.S).group(1)

    def test_ascii_and_self_contained(self):
        self.assertTrue(all(x < 128 for x in self.b), "ASCII: entities in the HTML, \\u escapes in the script")
        self.assertNotRegex(self.s, r"<script[^>]+src=", "no script from elsewhere")
        for href in re.findall(r'<link[^>]+href="([^"]+)"', self.s):
            self.assertTrue(href.startswith("https://fonts.g"), href)
        self.assertIn('fetch("/api/ask"', self.js)
        self.assertIn("[hidden]{display:none!important}", self.s, "a hidden panel stays hidden whatever its display")

    def test_every_element_the_script_reads_is_there(self):
        ids = set(re.findall(r'\$\("([A-Za-z]+)"\)', self.js))
        have = set(re.findall(r'id="([A-Za-z]+)"', self.s))
        self.assertTrue(ids, "the script reads elements by id")
        self.assertEqual(ids - have, set())

    def test_storage_only_through_the_guarded_helper(self):
        uses = re.findall(r"localStorage\.\w+", self.js)
        self.assertEqual(sorted(set(uses)), ["localStorage.getItem", "localStorage.setItem"])
        helper = re.search(r"function store\(k, v\)\{([^\n]*)\}", self.js)
        self.assertTrue(helper and "try" in helper.group(1) and "catch" in helper.group(1), "every read and write in try")
        self.assertEqual(self.js.count("localStorage."), 2, "only in the helper")

    def test_the_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not on this machine")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "ask.js"
            f.write_text(self.js, encoding="ascii")
            r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipUnless(DASH_ON, "ASK_UI_2026_10_22 is not applied to scripts/dashboard.py here")
class TheSources(unittest.TestCase):
    def setUp(self):
        src = dash_source()
        self.fn_src = function(src, "_ask_enrich")
        self.api = function(src, "api_ask")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def enrich_fn(self, register=None, broken_scholar=False):
        def _scholar_st():
            if broken_scholar:
                raise ImportError("no scholar_translate here")
            return types.SimpleNamespace(src_hash=src_hash)
        ns = {"sqlite3": sqlite3, "pathlib": pathlib, "_scholar_st": _scholar_st,
              "_source_verdicts": lambda folder=None: dict(register or {})}
        exec(compile(self.fn_src, "dashboard._ask_enrich", "exec"), ns)
        return ns["_ask_enrich"]

    def make_db(self, full=True) -> str:
        db = self.t / ("full.db" if full else "bare.db")
        con = sqlite3.connect(str(db))
        cols = ", iast TEXT, engine TEXT, ocr_engine TEXT" if full else ""
        con.executescript("""
        CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
        CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, verse_ref TEXT,
                               text TEXT, translation TEXT%s);""" % cols)
        con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "sb"), (2, "sb__w_gretil")])
        ps = [(11, 1, 1, 1, "\u091c\u0928\u0915\u094b \u0939 \u0935\u0948\u0926\u0947\u0939\u0903"),
              (12, 1, 1, 2, "\u0905\u0925 \u0939"), (13, 1, 1, 3, "\u0924\u0924\u094d\u0930"),
              (21, 2, 1, 1, "\u0938\u0903")]
        if full:
            con.executemany("INSERT INTO passages (id, doc_id, page_no, idx, text, iast, engine, ocr_engine) "
                            "VALUES (?,?,?,?,?,?,?,?)", [p + ("janako ha vaideha\u1e25", "gemini:gemini-2.5-flash",
                                                              "tesseract") for p in ps])
            con.executescript("""
            CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
            CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
            CREATE TABLE scholar_translations (id INTEGER PRIMARY KEY, passage_id INTEGER, translation TEXT,
                                               status TEXT, review_verdict TEXT, src_hash TEXT, engine TEXT);""")
            con.executemany("INSERT INTO entities VALUES (?,?,?)", [(1, "Videha", "place"), (2, "Janaka", "person"),
                                                                    (3, "Y\u0101j\u00f1avalkya", "person")])
            con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)",
                            [(1, 11), (2, 11), (3, 11), (2, 11)])
            h = {pid: src_hash(text) for pid, _, _, _, text in ps}
            con.executemany("INSERT INTO scholar_translations (passage_id, translation, status, review_verdict, src_hash, "
                            "engine) VALUES (?,?,?,?,?,?)", [
                                (11, "Janaka of Videha.", "passed", None, h[11], "anthropic:claude-sonnet-5-5"),
                                (12, "An older reading.", "passed", None, h[12], "x"),
                                (12, "Then, indeed.", "passed", "reject", h[12], "x"),   # the latest is rejected
                                (13, "There.", "passed", None, "0" * 16, "x"),          # its Sanskrit changed since
                                (21, "He.", "flagged", "accept", h[21], "y")])          # accepted by a person
        else:
            con.executemany("INSERT INTO passages (id, doc_id, page_no, idx, text) VALUES (?,?,?,?,?)", ps)
        con.commit()
        con.close()
        return str(db)

    def sources(self):
        return [{"n": 1, "tag": "sb p1.1", "doc": "sb", "page_no": 1, "idx": 1, "english": "Janaka."},
                {"n": 2, "tag": "sb p1.2", "doc": "sb", "page_no": 1, "idx": 2, "english": "Then."},
                {"n": 3, "tag": "sb p1.3", "doc": "sb", "page_no": 1, "idx": 3, "english": "There."},
                {"n": 4, "tag": "sb__w_gretil p1.1", "doc": "sb__w_gretil", "page_no": 1, "idx": 1, "english": "He."},
                {"n": 5, "tag": "story:x", "doc": "story", "page_no": 0, "idx": 0, "english": "A retelling.",
                 "kind": "story", "link": "/stories", "label": "retelling"},
                {"n": 6, "tag": "gone p9.9", "doc": "gone", "page_no": 9, "idx": 9, "english": "?"}]

    def test_what_each_verse_carries(self):
        db = self.make_db()
        before = hashlib.md5(Path(db).read_bytes()).hexdigest()
        s = self.sources()
        self.enrich_fn({"sb": {"status": "translate_as_is"}})(db, s)
        a = s[0]
        self.assertEqual((a["pid"], a["iast"], a["mt"], a["ocr"], a["witness"], a["state"]),
                         (11, "janako ha vaideha\u1e25", "gemini:gemini-2.5-flash", "tesseract", False, "translate_as_is"))
        self.assertTrue(a["sanskrit"].startswith("\u091c\u0928\u0915\u094b"))
        self.assertEqual((a["scholar"], a["scholar_state"], a["scholar_engine"]),
                         ("Janaka of Videha.", "passed", "anthropic:claude-sonnet-5-5"))
        self.assertEqual([x["name"] for x in a["names"]], ["Janaka", "Y\u0101j\u00f1avalkya", "Videha"],
                         "persons first, each once")
        self.assertNotIn("scholar", s[1], "the latest scholarly row was rejected")
        self.assertNotIn("scholar", s[2], "the Sanskrit changed since the scholarly English")
        self.assertEqual((s[3]["scholar_state"], s[3]["witness"]), ("accepted", True))
        self.assertNotIn("state", s[3])
        self.assertEqual(s[4], self.sources()[4], "an editorial item is left as it is")
        self.assertEqual(s[5], self.sources()[5], "a verse not found is left as it is")
        self.assertEqual(hashlib.md5(Path(db).read_bytes()).hexdigest(), before, "read-only")

    def test_never_stops_ask(self):
        db = self.make_db(full=False)
        s = self.sources()
        self.enrich_fn(broken_scholar=True)(db, s)
        self.assertEqual(s[0]["pid"], 11)
        self.assertNotIn("iast", s[0])
        self.assertNotIn("names", s[0])
        self.assertNotIn("scholar", s[0])
        s = self.sources()
        self.enrich_fn()(str(self.t / "none" / "missing.db"), s)
        self.assertEqual(s, self.sources(), "a database it cannot open leaves the sources as they were")

    def test_the_model_is_sent_the_same(self):
        i = self.api.find("_ask_enrich(db, sources)")
        self.assertGreater(i, self.api.find("sources.append"), "after the sources are made")
        self.assertLess(i, self.api.find('user_msg = "PASSAGES:'), "before the model is asked")
        self.assertLess(i, self.api.find("budget_ok"), "so the spend-cap reply carries them too")
        self.assertEqual(self.api.count("_ask_enrich("), 1)
        self.assertIn('ctx.append(f"[{i}] [{tag}] {(tr or \'\')[:600]}")', self.api, "the prompt is untouched")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/ask.html", "tests/test_ui_clarity_2026_10_22.py")

    def test_applies_once_from_its_backups(self):
        if not (PAGE_ON and DASH_ON):
            self.skipTest("not applied here")
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_askui_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_askui_ copies here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / f)
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                got = (t / f).read_bytes()   # the file as it is, or a later patch's backup of it
                later = [x.read_bytes() for x in sorted((REPO / f).parent.glob(Path(f).name + ".bak_*"))
                         if ".bak_askui_" not in x.name]
                self.assertTrue(got == (REPO / f).read_bytes() or got in later, f)
            got = (t / "scripts" / "dashboard.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
            self.assertEqual(function(got, "_ask_enrich"), function(dash_source(), "_ask_enrich"))
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertIn("Nothing to do", r.stdout)

    def test_refuses_where_it_does_not_belong(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            (t / "scripts" / "dashboard.py").write_text("x = 1\n", encoding="utf-8")
            (t / "scripts" / "ask.html").write_text("<html></html>\n", encoding="utf-8")
            (t / "tests").mkdir()
            (t / "tests" / "test_ui_clarity_2026_10_22.py").write_text("# UI_CLARITY_2026_10_22\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("REFUSE", r.stdout)
            self.assertEqual((t / "scripts" / "dashboard.py").read_text(encoding="utf-8"), "x = 1\n", "nothing written")
            self.assertFalse(list((t / "scripts").glob("*.bak_*")))

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
