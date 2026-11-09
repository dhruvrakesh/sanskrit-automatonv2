# -*- coding: ascii -*-
"""STORY_QUALITY_2026_11_09: stories.py gives the model the scholarly English where it stands (marked), mines and
writes a witness that has only scholarly English, writes with Claude when SA_STORY_WRITER names it (through
claude_engine, its credit asked first) and with gemini otherwise; the miner is told a treatise has no episode; the
check takes a lowercase IAST word for a common noun and finds a name spelt otherwise, and still fails an invented one.
images.py reads the first JSON value of a reply with something after it, and waits as a 429 asks. A made-up database
in a temp folder; no network: gemini is a stub, Claude a fake module."""
import importlib, json, os, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MARK = "STORY_QUALITY_2026_11_09"
SP = ROOT / "scripts" / "stories.py"
ON = SP.exists() and MARK.encode() in SP.read_bytes()

SA = {(2, 3): "\u0924\u094d\u0930\u0947\u0924\u093e\u0926\u094d\u0935\u093e\u092a\u0930\u092f\u094b\u0903 \u0938\u0928\u094d\u0927\u094c",
      (2, 4): "\u0938 \u0938\u0930\u094d\u0935\u0902 \u0915\u094d\u0937\u0924\u094d\u0930\u092e\u094d \u0909\u0924\u094d\u0938\u093e\u0926\u094d\u092f",
      (2, 5): "\u092a\u093f\u0924\u0943\u0928\u094d \u0938\u0928\u094d\u0924\u0930\u094d\u092a\u092f\u093e\u092e\u093e\u0938",
      (2, 6): "\u090b\u091a\u0940\u0915\u092a\u094d\u0930\u092e\u0941\u0916\u093e\u0903"}
IAST = {(2, 3): "tret\u0101dv\u0101parayo\u1e25 sandhau", (2, 4): "sa sarva\u1e43 k\u1e63atram uts\u0101dya",
        (2, 5): "pit\u1e5bn santarpay\u0101m\u0101sa", (2, 6): "\u1e5bc\u012bkapramukh\u0101\u1e25 k\u1e63atriy\u0101n"}
EN = {(2, 3): "At the juncture of the Treta and Dvapara, Rama slew the warriors.",
      (2, 4): "He destroyed all the warrior class.",
      (2, 5): "He gratified his ancestors with the lakes of blood.",
      (2, 6): "The ancestors led by Rcika approached him."}


def make(d: str, scholarly: bool = True) -> str:
    import db_utils, cost_tracker, images
    db = str(Path(d) / "t.db")
    con = sqlite3.connect(db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con); images.ensure_schema(con)
    con.execute("UPDATE budget_state SET budget_usd=100, spent_usd=0, paused=0 WHERE id=1")
    con.execute("INSERT INTO docs(code) VALUES('M')")
    con.execute("INSERT INTO docs(code) VALUES('W__w_gretil')")
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    for (p, i), en in EN.items():
        if "iast" in cols:
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,iast,translation,text_type) VALUES(1,?,?,?,?,?,'mula')",
                        (p, i, SA[(p, i)], IAST[(p, i)], en))
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,iast,translation,text_type) VALUES(2,?,?,?,?,'','mula')",
                        (p, i, SA[(p, i)], IAST[(p, i)]))
        else:
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,?,?,?,?,'mula')",
                        (p, i, SA[(p, i)], en))
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(2,?,?,?,'','mula')",
                        (p, i, SA[(p, i)]))
    if scholarly:
        import stories
        con.execute("""CREATE TABLE IF NOT EXISTS scholar_translations(id INTEGER PRIMARY KEY, passage_id INTEGER,
                       doc_code TEXT, page_no INTEGER, idx INTEGER, src_hash TEXT, translation TEXT, status TEXT,
                       review_verdict TEXT)""")
        pid = lambda doc, p, i: con.execute("SELECT p.id FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=? "
                                            "AND page_no=? AND idx=?", (doc, p, i)).fetchone()[0]
        h = stories._src_hash
        rows = [("M", 2, 4, h(SA[(2, 4)]), "He wiped out the whole ksatra, the kingly order.", "passed", None),
                ("M", 2, 5, h("an older reading"), "A stale scholarly line.", "passed", None),          # Sanskrit changed
                ("M", 2, 6, h(SA[(2, 6)]), "A flagged line.", "flagged", None),
                ("M", 2, 3, h(SA[(2, 3)]), "A rejected line.", "passed", "reject"),
                ("W__w_gretil", 2, 4, h(SA[(2, 4)]), "The witness's scholarly line.", "flagged", "accept")]
        for doc, p, i, hh, tr, st, rv in rows:
            con.execute("INSERT INTO scholar_translations(passage_id, doc_code, page_no, idx, src_hash, translation, "
                        "status, review_verdict) VALUES (?,?,?,?,?,?,?,?)", (pid(doc, p, i), doc, p, i, hh, tr, st, rv))
    con.commit(); con.close()
    return db


def stub(payload, calls):
    def http(url, body=None, timeout=180):
        calls.append(body)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload) + "\n}"}]}}],
                "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 300, "thoughtsTokenCount": 100}}
    return http


STORY = {"title": "Parasurama's lakes", "title_hi": "t",
         "story_en": ("At the juncture of the Treta and Dvapara, Rama slew the warriors again and again [2.3]. "
                      "He wiped out the whole kingly order, the ksatriyas of the earth [2.4]. "
                      "With their blood he made lakes and gratified his ancestors in them [2.5]. "
                      "Then his ancestors, led by \u1e5ac\u012bka, came to him and asked him to stop [2.6]. ") * 3,
         "story_hi": "x [2.4]", "quote_sa": SA[(2, 4)], "quote_ref": "2.4", "notes": "", "cites": ["2.4"]}


@unittest.skipUnless(ON, "STORY_QUALITY_2026_11_09 is not applied to scripts/stories.py here")
class TheStories(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ.pop("SA_STORY_WRITER", None)
        os.environ.pop("SA_STORY_SCHOLARLY", None)
        import stories
        self.s = importlib.reload(stories)
        self.tmp = tempfile.TemporaryDirectory()
        self.db = make(self.tmp.name)
        self.con = sqlite3.connect(self.db)
        self.s.ensure_schema(self.con)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()
        os.environ.clear(); os.environ.update(self.keep)
        sys.modules.pop("claude_engine_fake", None)

    def test_the_scholarly_english_where_it_stands(self):
        sch = self.s.scholarly(self.con, "M")
        self.assertEqual(sch, {(2, 4): "He wiped out the whole ksatra, the kingly order."},
                         "passed and unchanged only: not stale, not flagged, not rejected")
        rows = {(r[0], r[1]): r[4] for r in self.s.passages(self.con, "M")}
        self.assertEqual(rows[(2, 4)], "He wiped out the whole ksatra, the kingly order.")
        self.assertEqual(rows[(2, 5)], EN[(2, 5)], "the working English where the scholarly is stale")
        self.assertEqual(len(rows), 4)
        w = self.s.passages(self.con, "W__w_gretil")
        self.assertEqual([(r[0], r[1], r[4]) for r in w], [(2, 4, "The witness's scholarly line.")],
                         "a witness with scholarly English alone (accepted by a person)")
        block = self.s._prompt_block(self.s.passages(self.con, "M"), True, sch)
        self.assertIn("[2.4]\nSA: ", block)
        self.assertIn("EN (scholarly): He wiped out", block)
        self.assertIn("[2.5]\nSA: ", block)
        self.assertIn("\nEN: He gratified", block)
        os.environ["SA_STORY_SCHOLARLY"] = "0"
        self.assertEqual(self.s.scholarly(self.con, "M"), {})

    def test_the_check(self):
        given = self.s.passages(self.con, "M")
        v = self.s.verify(STORY, given)
        self.assertTrue(v["ok"], v["problems"])
        bad = dict(STORY, story_en=STORY["story_en"].replace("\u1e5ac\u012bka", "Mrnjiga"))
        txt = " ".join(self.s.verify(bad, given)["problems"])
        self.assertIn("names not found in the cited passages: Mrnjiga", txt, "an invented name still fails")
        loose = dict(STORY, story_en=STORY["story_en"].replace("\u1e5ac\u012bka", "Richika").replace(
            "the ksatriyas", "the Kshatriyas"))
        self.assertTrue(self.s.verify(loose, given)["ok"], self.s.verify(loose, given)["problems"])

    def test_the_miner_skips_a_treatise(self):
        self.assertIn("return {\"episodes\": []}: an explanation is not a story", self.s.MINE_SYSTEM)
        self.assertIn("%d", self.s.MINE_SYSTEM)
        self.assertIn("(7) Tell it as a storyteller would", self.s.STORY_SYSTEM)
        self.assertIn("(6)", self.s.STORY_SYSTEM)

    def test_gemini_writes_by_default_and_a_reply_with_a_trailing_brace_is_read(self):
        sid = self.con.execute("INSERT INTO doc_stories(doc_id,status,title,from_page,from_idx,to_page,to_idx) "
                               "VALUES(1,'candidate','t',2,3,2,6)").lastrowid
        self.con.commit()
        calls = []
        v = self.s.write_story(self.con, sid, "M", self.db, http=stub(STORY, calls))
        self.assertTrue(v["ok"], v["problems"])
        prompt = calls[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("EN (scholarly): He wiped out", prompt)
        model, prov = self.con.execute("SELECT model, provenance FROM doc_stories WHERE id=?", (sid,)).fetchone()
        self.assertEqual(model, self.s.MODEL)
        self.assertEqual(json.loads(prov)["scholarly"], 1)

    def test_claude_writes_when_named_and_asks_its_credit_first(self):
        import stories
        sent = []

        class Msg:
            usage = {"input_tokens": 9000, "output_tokens": 3000}
        fake = types.ModuleType("claude_engine")
        fake.parse_engine = lambda e: ("claude-sonnet-5-5", "medium")
        fake.engine_name = lambda m, e=None: "anthropic:%s@%s" % (m, e)
        fake._get = lambda o, n, d=None: getattr(o, n, d)
        fake.text_of = lambda m: "```json\n" + json.dumps(STORY) + "\n```"
        fake.meter = lambda con, kind, doc, model, usage, dur, units=1: sent.append(("meter", kind, doc, model))
        fake.ok = True
        fake.budget_ok = lambda con: fake.ok

        class Client:
            def __init__(self, model, effort):
                sent.append(("client", model, effort))

            def create(self, system, user, max_tokens):
                sent.append(("create", "Respond with one JSON object only" in system, max_tokens))
                return Msg()
        fake.Client = Client
        keep = sys.modules.get("claude_engine")
        sys.modules["claude_engine"] = fake
        try:
            os.environ["SA_STORY_WRITER"] = "anthropic:claude-sonnet-5-5@medium"
            s = importlib.reload(stories)
            sid = self.con.execute("INSERT INTO doc_stories(doc_id,status,title,from_page,from_idx,to_page,to_idx) "
                                   "VALUES(1,'candidate','t',2,3,2,6)").lastrowid
            self.con.commit()
            v = s.write_story(self.con, sid, "M", self.db)
            self.assertTrue(v["ok"], v["problems"])
            self.assertEqual(sent[0], ("client", "claude-sonnet-5-5", "medium"))
            self.assertEqual(sent[1], ("create", True, 8000))
            self.assertEqual(sent[2], ("meter", "story", "M", "claude-sonnet-5-5"))
            self.assertEqual(self.con.execute("SELECT model FROM doc_stories WHERE id=?", (sid,)).fetchone()[0],
                             "anthropic:claude-sonnet-5-5@medium")
            self.assertIn("from the Claude credit", s.writer_cost())
            calls = []
            s.write_story(self.con, sid, "M", self.db, http=stub(STORY, calls))
            self.assertEqual(len(calls), 1, "a stub given: gemini, never a paid API in a test")
            fake.ok = False
            with self.assertRaises(SystemExit) as cm:
                s.write_story(self.con, sid, "M", self.db)
            self.assertIn("the Claude credit allows no more calls", str(cm.exception))
        finally:
            if keep is not None:
                sys.modules["claude_engine"] = keep
            else:
                sys.modules.pop("claude_engine", None)
            os.environ.pop("SA_STORY_WRITER", None)
            importlib.reload(stories)


class TheImages(unittest.TestCase):
    def setUp(self):
        import images
        self.im = images
        if not hasattr(images, "parse_json_text"):
            self.skipTest("STORY_QUALITY_2026_11_09 is not applied to scripts/images.py here")

    def test_the_json_and_the_wait(self):
        im = self.im
        self.assertEqual(im.parse_json_text('{"a": 1}\n}'), {"a": 1}, "an extra brace after the object")
        self.assertEqual(im.parse_json_text("```json\n[1, 2]\n```"), [1, 2])
        self.assertEqual(im.parse_json_text('Here it is: {"b": 2} {"c": 3}'), {"b": 2})
        with self.assertRaises(SystemExit) as cm:
            im.parse_json_text("no json here")
        self.assertIn("not the JSON asked for", str(cm.exception))
        self.assertEqual(im.retry_wait(429, '{"error": {"details": [{"retryDelay": "37s"}]}}', 0), 38.0)
        self.assertEqual(im.retry_wait(429, '{"retryDelay": "300s"}', 1), 60.0)
        self.assertEqual(im.retry_wait(429, "{}", 1), 30.0)
        self.assertEqual(im.retry_wait(503, "", 2), 12.0)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (ROOT / "scripts" / "patch_story_quality_2026_11_09.py", Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
