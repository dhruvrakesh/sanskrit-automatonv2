# -*- coding: ascii -*-
"""ASK_ROOM_2026_10_28: the Professor's room. gemini-2.5-flash counts its thinking inside max_output_tokens, and at
3,072 the Professor's answers were cut (28 Oct: 545 and 423 characters for 3,068 tokens). The room is now 16,384 for
the Professor and 6,144 for the verses; an answer cut at the limit says so; a reply with no part is "no text", not an
error; each claim is cited by its own work, and a work in copyright is marked as private reading. The dashboard's
functions are read from its source, never imported; made-up databases in a temp folder; never the network."""
import ast, json, pathlib, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "scripts" / "dashboard.py"
PAT = REPO / "scripts" / "patch_ask_room_2026_10_28.py"
MARK = "ASK_ROOM_2026_10_28"
ON = DASH.exists() and MARK.encode() in DASH.read_bytes()


def source() -> str:
    return DASH.read_bytes().decode("utf-8").replace("\r\n", "\n")


def pick(src: str, names) -> str:
    out = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out.append(ast.get_source_segment(src, node))
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            out.append(ast.get_source_segment(src, node))
    return "\n\n".join(out)


def make(root: Path) -> str:
    (root / "shelf").mkdir(parents=True, exist_ok=True)
    db = root / "context.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    """)
    con.executemany("INSERT INTO entities VALUES (?,?,?)", [(1, "Gandh\u0101ra", "place")])
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)", [(1, 11)])
    con.commit()
    con.close()
    c = sqlite3.connect(str(root / "shelf" / "claims.db"))
    c.executescript("""
    CREATE TABLE claim_works (code TEXT PRIMARY KEY, author TEXT, title TEXT, year TEXT, licence TEXT);
    CREATE TABLE claim_reads (id INTEGER PRIMARY KEY, work TEXT, pdf_page INTEGER, status TEXT);
    CREATE TABLE claims (id INTEGER PRIMARY KEY, read_id INTEGER, work TEXT, pdf_page INTEGER, printed TEXT,
                         relation TEXT, claim TEXT, stance TEXT, hedge TEXT);
    CREATE TABLE claim_links (claim_id INTEGER, role TEXT, entity_id INTEGER);
    """)
    c.executemany("INSERT INTO claim_works VALUES (?,?,?,?,?)", [
        ("phai1923", "Hemchandra Raychaudhuri", "Political History of Ancient India", "1923",
         "public domain: published 1923"),
        ("tribes1943", "B. C. Law", "Tribes in Ancient India", "1943", "in copyright in India to the end of 2029")])
    c.executemany("INSERT INTO claim_reads VALUES (?,?,?,?)", [(1, "phai1923", 41, "ok"), (2, "tribes1943", 10, "ok")])
    c.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?)", [
        (1, 1, "phai1923", 41, "23", "located_in", "Gandhara lay in the north-west.", "asserts", ""),
        (2, 2, "tribes1943", 10, "7", "located_in", "A private reading of Gandhara.", "asserts", "")])
    c.executemany("INSERT INTO claim_links VALUES (?,?,?)", [(1, "subject", 1), (2, "subject", 1)])
    c.commit()
    c.close()
    return str(db)


def resp(text=None, finish=None, parts=None):
    ns = types.SimpleNamespace

    class R:
        candidates = [ns(finish_reason=finish, content=ns(parts=[ns(text=p) for p in (parts or [])]))]

        @property
        def text(self):
            if text is None:
                raise ValueError("The response.text quick accessor requires a valid Part; finish_reason is 2")
            return text
    return R()


@unittest.skipUnless(ON, "ASK_ROOM_2026_10_28 is not applied to scripts/dashboard.py here")
class TheRoom(unittest.TestCase):
    def setUp(self):
        self.src = source()
        code = pick(self.src, {"_ASK_ROOM", "_ask_text", "_ask_cut", "_ask_scholarly", "_PROF_SHELF",
                               "_PROF_CLAIM_RELS"})
        self.ns = {"sqlite3": sqlite3, "pathlib": pathlib, "json": json}
        exec(compile(code, "dashboard.room", "exec"), self.ns)

    def test_the_room(self):
        self.assertEqual(self.ns["_ASK_ROOM"], {"professor": 16384, "verses": 6144})

    def test_a_cut_answer_is_seen(self):
        cut = self.ns["_ask_cut"]
        self.assertTrue(cut(resp("x", types.SimpleNamespace(name="MAX_TOKENS"))))
        self.assertFalse(cut(resp("x", types.SimpleNamespace(name="STOP"))))
        self.assertTrue(cut(resp("x", 2)), "the enum's number")
        self.assertFalse(cut(resp("x", 1)))
        self.assertTrue(cut(resp("x", "FinishReason.MAX_TOKENS")))
        self.assertFalse(cut(types.SimpleNamespace(candidates=[])), "no candidate")

    def test_the_text(self):
        t = self.ns["_ask_text"]
        self.assertEqual(t(resp("  an answer  ")), "an answer")
        self.assertEqual(t(resp(None, 2, ["half ", "an answer"])), "half an answer", "the parts when .text raises")
        self.assertEqual(t(resp(None, 2, [])), "", "no part: no text, no error")

    def test_each_claim_by_its_work(self):
        with tempfile.TemporaryDirectory() as td:
            db = make(Path(td))
            sch = self.ns["_ask_scholarly"](db, [{"n": 1, "tag": "x", "pid": 11}])
        by = {i["text"]: i for i in sch["items"]}
        ray = by["Gandhara lay in the north-west."]
        self.assertEqual(ray["source"], "Raychaudhuri, Political History of Ancient India (1923)", "as before")
        self.assertNotIn("private", ray["note"])
        law = by["A private reading of Gandhara."]
        self.assertEqual(law["source"], "B. C. Law, Tribes in Ancient India (1943)")
        self.assertIn("in copyright: private reading on this PC, never on the site", law["note"])

    def test_the_wiring(self):
        api = [ast.get_source_segment(self.src, n) for n in ast.parse(self.src).body
               if isinstance(n, ast.FunctionDef) and n.name == "api_ask"][0]
        self.assertIn("max_output_tokens=_ASK_ROOM[ask_mode]", api)
        self.assertNotIn("3072", api)
        self.assertLess(api.index("_cut = False"), api.index("import google.generativeai as genai"))
        self.assertIn("_cut = _ask_cut(resp)", api)
        self.assertIn("The answer was cut at the length limit", api)
        self.assertIn('"cut": _cut', api)
        self.assertIn("answer = _ask_text(resp) or", api)
        self.assertIn('kind=("ask_prof" if ask_mode == "professor" else "ask")', api, "the meter as before")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    def test_the_patcher_writes_once_and_keeps_crlf(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        baks = sorted(DASH.parent.glob("dashboard.py.bak_askroom_*"))
        if not baks:
            self.skipTest("no backup of the file before the patch here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            raw = baks[0].read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            (t / "scripts" / "dashboard.py").write_bytes(raw)
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = (t / "scripts" / "dashboard.py").read_bytes()
            self.assertIn(MARK.encode(), out)
            self.assertNotIn(b"\n", out.replace(b"\r\n", b""), "CRLF kept")
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r.stdout)


if __name__ == "__main__":
    unittest.main()
