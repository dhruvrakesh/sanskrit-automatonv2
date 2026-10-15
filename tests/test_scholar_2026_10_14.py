# -*- coding: ascii -*-
"""SCHOLAR_2026_10_14 (with HOLD_2026_10_14): scripts/scholar_translate.py, a scholarly English beside the working
one (what it sends and what it leaves out, the passes, the versions, the caps, the pages), and its patcher
(dashboard.py: /scholar and the Library's holds; translate_passages.py: a withdrawn or set-aside text is refused).
Temp files only; no model is called (the calls are stubs, and the one --yes run has no key)."""
import hashlib, importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ST = load("scholar_translate_t", SCRIPTS / "scholar_translate.py")

V6 = "\u0938\u0941\u0916\u093e\u0938\u0940\u0928\u0902 \u0924\u0924\u0938\u094d \u0924\u0902 \u0924\u0941 \u0935\u093f\u0936\u094d\u0930\u093e\u0928\u094d\u0924\u092e\u094d \u0909\u092a\u0932\u0915\u094d\u0937\u094d\u092f \u091a"
V7 = "\u0915\u0941\u0924 \u0906\u0917\u092e\u094d\u092f\u0924\u0947 \u0938\u094c\u0924\u0947 \u0915\u094d\u0935 \u091a\u093e\u092f\u0902 \u0935\u093f\u0939\u0943\u0924\u0938\u094d \u0924\u094d\u0935\u092f\u093e"
V8 = ("\u0938\u0942\u0924 \u0909\u0935\u093e\u091a\n\u091c\u0928\u092e\u0947\u091c\u092f\u0938\u094d\u092f \u0930\u093e\u091c\u0930\u094d\u0937\u0947\u0903 "
      "\u0938\u0930\u094d\u092a\u0938\u0924\u094d\u0930\u0947 \u092e\u0939\u093e\u0924\u094d\u092e\u0928\u0903\n\u0938\u092e\u0940\u092a\u0947 "
      "\u092a\u093e\u0930\u094d\u0925\u093f\u0935\u0947\u0928\u094d\u0926\u094d\u0930\u0938\u094d\u092f \u0938\u092e\u094d\u092f\u0915\u094d "
      "\u092a\u093e\u0930\u093f\u0915\u094d\u0937\u093f\u0924\u0938\u094d\u092f \u091a")
V9 = "\u0915\u0943\u0937\u094d\u0923\u0926\u094d\u0935\u0948\u092a\u093e\u092f\u0928\u092a\u094d\u0930\u094b\u0915\u094d\u0924\u093e\u0903 \u0938\u0941\u092a\u0941\u0923\u094d\u092f\u093e \u0935\u093f\u0935\u093f\u0927\u093e\u0903 \u0915\u0925\u093e\u0903"
I8 = "s\u016bta uv\u0101ca\njanamejayasya r\u0101jar\u1e63e\u1e25 sarpasatre mah\u0101tmana\u1e25\nsam\u012bpe p\u0101rthivendrasya samyak p\u0101rik\u1e63itasya ca"
HINDI = ("\u0936\u0948\u0935\u092d\u093e\u0930\u0924\u0940 \u0936\u094b\u0927\u092a\u094d\u0930\u0924\u093f\u0937\u094d\u0920\u093e\u0928 \u0915\u0940 "
         "\u0938\u094d\u0925\u093e\u092a\u0928\u093e \u091c\u093f\u0928\u0915\u0940 \u0938\u0902\u0915\u0932\u094d\u092a\u0928\u093e "
         "\u0930\u0939\u0940, \u0909\u0938 \u092e\u0939\u093e\u0928\u094d \u0935\u093f\u092d\u0942\u0924\u093f \u0915\u0947 "
         "\u0915\u093e\u0930\u0923 \u092f\u0939 \u0917\u094d\u0930\u0928\u094d\u0925 \u0939\u0948")
ERRATA = ("\u092a\u0943\u0937\u094d\u0920\u0947 \u092a\u0919\u094d\u0915\u094d\u0924\u094c \u0905\u0936\u0941\u0926\u094d\u0927\u092e\u094d "
          "\u0936\u0941\u0926\u094d\u0927\u092e\u094d \u0964 \u0967 \u096b \u0935\u093e\u092e\u093e\u0915\u094d\u0937\u0940")
APPARATUS = ("\u0967 \u096b \u0935\u093e\u092e\u093e\u0915\u094d\u0937\u0940 \u0935\u093e\u092e\u093e\u0915\u094d\u0937\u093f \u0964 "
             "\u0968\u0969 \u0967\u096e \u0905\u0938\u094d\u0924\u094d\u0930\u093e\u0926\u094c \u0967 \u096d "
             "\u0905\u092e\u0930\u0947\u0936\u094d\u0935\u0930\u093f")
NUMBERED = V6 + " \u0965 \u0967\u0968 \u0965"
SUTRAS = "\u0967.\u0967.\u0967 \u0935\u0943\u0926\u094d\u0927\u093f\u0930\u093e\u0926\u0948\u091a\u094d\n\u0967.\u0967.\u0968 \u0905\u0926\u0947\u0919\u094d\u0917\u0941\u0923\u0903 \u0907\u0924\u093f \u0938\u0942\u0924\u094d\u0930\u092e\u094d"
SANSKRIT_KE = "\u0915\u0947 \u0924\u0947 \u092a\u0941\u0930\u0941\u0937\u093e\u0903 \u0915\u0941\u0924\u0903 \u0906\u0917\u0924\u093e\u0903"


def md5(p) -> str:
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def fixture(td: Path, register=None) -> Path:
    import db_utils
    db = td / "context.db"
    con = sqlite3.connect(str(db))
    db_utils.ensure_schema(con)
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "ocr_engine" not in cols:
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
    con.executescript("""
      CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY, canonical TEXT UNIQUE, kind TEXT, notes TEXT, created_at TEXT);
      CREATE TABLE IF NOT EXISTS entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER, surface TEXT,
        created_at TEXT, UNIQUE(entity_id, passage_id));""")
    con.execute("INSERT INTO docs(code, category) VALUES ('MBh01', 'mahabharata')")
    did = con.execute("SELECT id FROM docs WHERE code='MBh01'").fetchone()[0]
    rows = [("1.1.6", V6, "sukh\u0101s\u012bna\u1e43 tatas", "Then a sage, seeing him seated. //", "mula"),
            ("1.1.7", V7, "kuta \u0101gamyate saute", "O son of a s\u016bta, where do you come from? //", "mula"),
            ("1.1.8", V8, I8, "The s\u016bta said: I was near Janamejaya and P\u0101rik\u1e63ita. //", "mula"),
            ("1.1.9", V9, "k\u1e5b\u1e63\u1e47advaip\u0101yanaprokt\u0101\u1e25", "The stories. //", "mula"),
            ("1.1.99", "x", "", "", "noise"),
            ("1.1.10", ERRATA, "", "", "mula"),
            ("1.1.11", V6 + " ee ie", "", "", "mula")]
    for k, (ref, t, ia, en, tt) in enumerate(rows, 1):
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, iast, translation, verse_ref, chapter, text_type, "
                    "quality_score, ocr_engine) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (did, 1, k, t, ia, en, ref, "1", tt, 0.53, "gretil-bori-etext"))
    p8 = con.execute("SELECT id FROM passages WHERE verse_ref='1.1.8'").fetchone()[0]
    con.execute("INSERT INTO entities VALUES (7, 'Janamejaya', 'person', NULL, NULL)")
    con.execute("INSERT INTO entities VALUES (8, 'P\u0101rik\u1e63ita', 'person', NULL, NULL)")
    con.execute("INSERT INTO entity_mentions VALUES (1, 7, ?, 'janamejayasya', NULL)", (p8,))
    con.execute("INSERT INTO entity_mentions VALUES (2, 8, ?, 'p\u0101rik\u1e63itasya', NULL)", (p8,))
    con.commit(); con.close()
    reg = td / "source_verdicts.jsonl"
    reg.write_text("".join(json.dumps(r) + "\n" for r in (register or [])), encoding="utf-8")
    return db


def args(db, **kw):
    a = types.SimpleNamespace(db=str(db), doc="MBh01", pages=None, from_ref=None, only_page=None, only_idx=None, limit=24,
                              rounds=2, engine=ST.ENGINE, judge_engine=ST.JUDGE, min_quality=0.35, max_usd=1.0, redo=False,
                              log_dir=str(Path(db).parent / "logs"))
    for k, v in kw.items():
        setattr(a, k, v)
    return a


class Stub:
    """Scripted answers: ask(kind, msg) pops the next answer of that kind; each call costs $0.01, a judge $0.0002."""

    def __init__(self, drafts, critics, judges):
        self.drafts, self.critics, self.judges = list(drafts), list(critics), list(judges)
        self.spent, self.msgs = 0.0, []

    def ask(self, kind, msg):
        self.msgs.append((kind, msg))
        self.spent += 0.01
        q = self.drafts if kind == "draft" else self.critics
        a = q.pop(0) if q else None
        if isinstance(a, Exception):
            raise a
        return a, 0.01

    def judge(self, src, iast, english):
        self.spent += 0.0002
        f, l = self.judges.pop(0) if self.judges else (4, 4)
        return f, l, "ok", 0.0002


def draft(t, notes=(), gl=(), doubts=""):
    return {"translation": t, "notes": list(notes), "glossary": list(gl), "doubts": doubts}


def crit(v, fid=5, comp=5, issues=()):
    return {"fidelity": fid, "completeness": comp, "issues": list(issues), "verdict": v}


ACCEPT = crit("accept")
MAJOR = crit("revise", 3, 4, [{"type": "misreading", "where": "p\u0101rik\u1e63itasya", "fix": "the son of Parik\u1e63it",
                               "severity": "major"}])


class TheReadiness(unittest.TestCase):
    def test_what_is_sent_and_what_is_not(self):
        r = ST.readiness
        self.assertIsNone(r(V8, "mula", 0.53))
        self.assertIsNone(r(V8, "colophon", None), "a colophon is verse too")
        self.assertEqual(r(V8, "noise"), "noise or front matter")
        self.assertEqual(r(V8, "frontmatter"), "noise or front matter")
        self.assertEqual(r("\u0938\u0942\u0924 \u0909\u0935\u093e\u091a", "mula"), "fewer than 8 Devanagari signs")
        self.assertIn("OCR debris", r(V6 + " ee ie", "mula"))
        self.assertIn("below quality 0.35", r(V8, "mula", 0.2))
        self.assertIsNone(r(V8, "mula", 0.2, min_quality=0.1))
        self.assertIn("numbers among the words", r(ERRATA, "mula"))
        self.assertIn("numbers among the words", r(APPARATUS, "mula"))
        self.assertIsNone(r(NUMBERED, "mula"), "a verse number between dandas is not an index")
        self.assertIsNone(r(SUTRAS, "mula"), "a sutra's own number is not an index")
        self.assertIn("Hindi prose", r(HINDI, "mula"))
        self.assertIsNone(r(SANSKRIT_KE, "mula"), "one word that is Hindi too does not make Hindi")
        self.assertEqual(len(ST.hindi_words(HINDI)), 4)


class TheDryRun(unittest.TestCase):
    def run_(self, db, *extra, env=None):
        e = dict(os.environ, PYTHONIOENCODING="utf-8", **(env or {}))
        return subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc", "MBh01"]
                              + list(extra), capture_output=True, text=True, encoding="utf-8", cwd=str(Path(db).parent),
                              env=e)

    def test_free_read_only_and_what_it_prints(self):
        with tempfile.TemporaryDirectory() as d:
            db = fixture(Path(d))
            before = md5(db)
            r = self.run_(db, "--pages", "1", "--show-prompt")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            o = r.stdout
            self.assertIn("DRY RUN (nothing called, nothing written)", o)
            self.assertIn("the source: the BORI Critical Edition e-text (gretil-bori-etext)", o)
            self.assertIn("chosen: 4 verse(s), 1.1.6 to 1.1.9", o)
            self.assertIn("left out: 1 (noise or front matter)", o)
            self.assertIn("left out: 1 (numbers among the words", o)
            self.assertIn("left out: 1 (OCR debris", o)
            self.assertIn("a prior until 10 verses are measured", o)
            self.assertRegex(o, r"NEXT: python scripts\\scholar_translate\.py --doc MBh01 --pages 1 --limit 24 --yes "
                                r"--max-usd \d+\.\d\d")
            self.assertIn("translation of the Mah\u0101bh\u0101rata, Book 1, for a critical-edition", o)
            self.assertIn("Never quote or reconstruct any published translation.", o)
            self.assertIn("THE VERSE TO TRANSLATE [1.1.6]", o)
            self.assertEqual(md5(db), before, "the dry run writes nothing")
            con = sqlite3.connect(str(db))
            con.execute("UPDATE passages SET ocr_engine = NULL"); con.commit(); con.close()
            (Path(d) / "raw").mkdir()
            (Path(d) / "raw" / "MBh01_0001.jsonl").write_text(json.dumps({"engine": "gretil-bori-etext"}) + "\n",
                                                               encoding="utf-8")
            o = self.run_(db, "--pages", "1").stdout
            self.assertIn("the source: the BORI Critical Edition e-text (gretil-bori-etext)", o, "from its page file")
            before = md5(db)
            con = sqlite3.connect(str(db))
            self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name='scholar_translations'").fetchone())
            con.close()
            self.assertFalse((Path(d) / "data" / "scholar").exists())

    def test_the_prompt_carries_the_context_and_the_glossary(self):
        with tempfile.TemporaryDirectory() as d:
            db = fixture(Path(d))
            con = sqlite3.connect(str(db))
            allp = ST.load_text(con, "MBh01")
            i = next(k for k, x in enumerate(allp) if x["ref"] == "1.1.8")
            b, af = ST.context(allp, i, {})
            self.assertEqual([y["ref"] for y, _ in b], ["1.1.6", "1.1.7"])
            self.assertEqual([y["ref"] for y in af], ["1.1.9", "1.1.10"], "the next two usable passages")
            gl = ST.glossary(con, "MBh01", allp[i], b)
            self.assertEqual([g["term"] for g in gl], ["Janamejaya", "P\u0101rik\u1e63ita"])
            m = ST.verse_message(ST.doc_meta(con, "MBh01", allp), allp[i], b, af, gl)
            con.close()
            self.assertIn("TEXT: The Mah\u0101bh\u0101rata, Book 1. SOURCE: the BORI Critical Edition e-text.", m)
            self.assertIn("GLOSSARY (keep these spellings; it does not say who is who):\n- Janamejaya (person)", m)
            self.assertIn("[1.1.7] " + V7 + "\n   English: O son of a s\u016bta, where do you come from? //", m)
            self.assertIn("THE VERSE TO TRANSLATE [1.1.8]:\n" + V8 + "\nIAST: " + I8, m)
            self.assertIn("THE VERSES AFTER (Sanskrit only, for understanding only):\n[1.1.9] " + V9, m)
            self.assertLess(m.index("THE VERSES BEFORE"), m.index("THE VERSE TO TRANSLATE"))

    def test_a_held_text_is_refused_whole(self):
        for st in ("withdrawn", "set_aside", "in_repair"):
            with tempfile.TemporaryDirectory() as d:
                db = fixture(Path(d), [{"doc": "MBh01", "status": "released"},
                                       {"doc": "MBh01", "status": st, "at": "2026-10-14T10:00", "reason": "why"}])
                before = md5(db)
                r = self.run_(db, "--yes", "--max-usd", "0")
                self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
                self.assertIn("REFUSE: MBh01 is %s" % ST.HELD[st], r.stdout)
                self.assertEqual(md5(db), before)
        with tempfile.TemporaryDirectory() as d:
            db = fixture(Path(d), [{"doc": "MBh01", "status": "withdrawn"}, {"doc": "MBh01", "status": "restored"}])
            self.assertEqual(self.run_(db).returncode, 0, "the latest record counts")

    def test_without_a_key_nothing_is_called_or_written(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            (t / "scripts").mkdir()
            for f in ("scholar_translate.py", "db_utils.py", "usage_meter.py", "cost_tracker.py", "env_loader.py",
                      "iast_utils.py"):
                shutil.copy2(SCRIPTS / f, t / "scripts" / f)
            db = fixture(t)
            before = md5(db)
            env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
            env["PYTHONIOENCODING"] = "utf-8"
            r = subprocess.run([sys.executable, str(t / "scripts" / "scholar_translate.py"), "--db", str(db), "--doc",
                                "MBh01", "--yes", "--max-usd", "0"], capture_output=True, text=True, encoding="utf-8",
                               cwd=str(t), env=env)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("REFUSE: GEMINI_API_KEY is not set", r.stdout)
            self.assertEqual(md5(db), before, "the database is not even opened for writing")


class TheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = fixture(self.td)
        self.busy = ST.busy_with
        ST.busy_with = lambda doc: None

    def tearDown(self):
        ST.busy_with = self.busy
        self.tmp.cleanup()

    def go(self, stub, budget_ok=None, **kw):
        import db_utils
        a = args(self.db, **kw)
        con = db_utils.connect(str(self.db))
        try:
            ST.ensure_schema(con)
            allp = ST.load_text(con, "MBh01")
            done = ST.latest_rows(con, "MBh01")
            picked, left, skipped = ST.choose(a, allp, done)
            meta = ST.doc_meta(con, "MBh01", allp)
            price = {"typical": 0.03, "most": 0.06, "call": 0.01, "how": "test"}
            res = ST.run(a, allp, picked, meta, done, stub, con, price, budget_ok)
            rows = [dict(zip([d[0] for d in con.execute("SELECT * FROM scholar_translations").description], r))
                    for r in con.execute("SELECT * FROM scholar_translations ORDER BY id")]
            gl = con.execute("SELECT term, rendering, source FROM scholar_glossary ORDER BY term").fetchall()
        finally:
            con.close()
        return res, rows, gl, picked, skipped

    def test_draft_critic_revision_judge_and_the_versions(self):
        n8 = [{"anchor": "Janamejaya", "kind": "name", "note": "the son of Parik\u1e63it"}]
        stub = Stub(drafts=[draft("Then a certain sage there saw him seated. //"),
                            draft("O son of the s\u016bta, where have you come from? //"),
                            draft("I was near Janamejaya and P\u0101rik\u1e63ita. //"),
                            draft("The s\u016bta said: I was at the snake sacrifice of Janamejaya, the son of Parik\u1e63it. //",
                                  n8, [{"term": "Ugra\u015bravas", "rendering": "Ugra\u015bravas", "kind": "person",
                                        "note": "the s\u016bta"}]),
                            draft("The stories told by K\u1e5b\u1e63\u1e47a Dvaip\u0101yana. //", doubts="vai: a filler"),
                            draft("rev 1 //", doubts="vai: a filler"), draft("rev 2 //", doubts="vai: a filler")],
                    critics=[ACCEPT, ACCEPT, MAJOR, ACCEPT, MAJOR, MAJOR, MAJOR],
                    judges=[(5, 5), (3, 4), (4, 4), (2, 4), (5, 5), (2, 3), (2, 4), (2, 3)])
        res, rows, gl, picked, _ = self.go(stub)
        self.assertEqual(len(picked), 4)
        self.assertEqual(res["passed"], ["1.1.6", "1.1.7", "1.1.8"]); self.assertEqual(res["flagged"], ["1.1.9"])
        self.assertEqual(res["stopped"], "")
        r8 = rows[2]
        self.assertEqual((r8["verse_ref"], r8["version"], r8["passes"], r8["status"]), ("1.1.8", 1, 2, "passed"))
        self.assertEqual(r8["draft"], "I was near Janamejaya and P\u0101rik\u1e63ita. //")
        self.assertIn("the son of Parik\u1e63it. //", r8["translation"])
        self.assertEqual(json.loads(r8["notes"]), n8)
        self.assertEqual([c["verdict"] for c in json.loads(r8["critique"])], ["revise", "accept"])
        self.assertEqual((r8["fidelity"], r8["fluency"], r8["working_fidelity"], r8["working_fluency"]), (5, 5, 2, 3))
        self.assertAlmostEqual(r8["cost_usd"], 0.0404, places=6)
        self.assertEqual(r8["src_hash"], ST.src_hash(V8)); self.assertEqual(r8["engine"], "gemini:gemini-2.5-pro")
        self.assertEqual(r8["prompt_version"], "%s+%s" % (ST.PROMPT_VERSION, ST.CRITIC_VERSION))   # v2 since SCHOLAR_V2
        r9 = rows[3]
        self.assertEqual((r9["passes"], r9["status"]), (3, "flagged"), "two revisions at most, then a person reads it")
        self.assertEqual(r9["doubts"], "vai: a filler")
        self.assertEqual(gl, [("Ugra\u015bravas", "Ugra\u015bravas", "scholar")], "only a passed verse adds to the glossary")
        kinds = [k for k, _ in stub.msgs]
        self.assertEqual(kinds.count("draft"), 4 + 1 + 2)
        m8 = [m for k, m in stub.msgs if k == "draft"][2]
        self.assertIn("English: O son of the s\u016bta, where have you come from? //", m8,
                      "the verse before gives its scholarly English once it passed")
        rv = [m for k, m in stub.msgs if k == "draft"][3]
        self.assertIn("YOUR DRAFT:", rv); self.assertIn("- [major misreading] p\u0101rik\u1e63itasya: the son of Parik", rv)
        self.assertIn("THE DRAFT TRANSLATION:\nI was near Janamejaya", [m for k, m in stub.msgs if k == "critic"][2])
        log = Path(res["log"]).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log), 4)
        self.assertEqual(json.loads(log[2])["working_english"], "The s\u016bta said: I was near Janamejaya and "
                                                                 "P\u0101rik\u1e63ita. //")
        # again: done verses are not sent; --redo makes version 2; a changed reading makes the row stale
        res, rows, gl, picked, skipped = self.go(Stub([], [], []))
        self.assertEqual((picked, len(skipped)), ([], 4))
        res, rows, gl, picked, _ = self.go(Stub([draft("v2 //")], [ACCEPT], [(5, 5), (2, 2)]), only_page=1, only_idx=3,
                                           redo=True)
        self.assertEqual([(r["verse_ref"], r["version"]) for r in rows if r["verse_ref"] == "1.1.8"],
                         [("1.1.8", 1), ("1.1.8", 2)])
        con = sqlite3.connect(str(self.db))
        con.execute("UPDATE passages SET text = text || ' \u0964' WHERE verse_ref = '1.1.6'")
        con.commit(); con.close()
        res, rows, gl, picked, skipped = self.go(Stub([], [], []), limit=1)
        self.assertEqual(len(picked), 1)
        res, rows, gl, picked, skipped = self.go(Stub([draft("again //")], [ACCEPT], [(5, 5), (4, 4)]))
        self.assertEqual(res["passed"], ["1.1.6"])

    def test_a_source_doubt(self):
        src = crit("revise", 3, 3, [{"type": "source", "where": "x", "fix": "read y", "severity": "major"}])
        res, rows, *_ = self.go(Stub([draft("a //"), draft("b //"), draft("c //")], [src, src, src], []), limit=1)
        self.assertEqual(res["source_doubt"], ["1.1.6"]); self.assertEqual(rows[0]["passes"], 3)

    def test_the_caps(self):
        res, rows, *_ = self.go(Stub([draft("a //")] * 4, [ACCEPT] * 4, []), max_usd=0.05)
        self.assertEqual(len(rows), 1)
        self.assertIn("--max-usd $0.05 is reached", res["stopped"])
        res, rows, *_ = self.go(Stub([draft("a //")], [MAJOR, MAJOR], []), max_usd=0.035, limit=1, redo=True)
        self.assertIn("not revised: --max-usd $0.04 would be passed", rows[-1]["doubts"])
        res, rows, *_ = self.go(Stub([], [], []), budget_ok=lambda con, c: False, redo=True)
        self.assertIn("the spend cap is reached", res["stopped"])
        ST.busy_with = lambda doc: [{"kind": "translate", "doc": doc}]
        res, rows, *_ = self.go(Stub([], [], []), redo=True)
        self.assertIn("the dashboard changes MBh01 now (translate)", res["stopped"])
        ST.busy_with = self.busy
        self.assertEqual(ST.QUIET_KINDS[0], "translate_hi", "a Hindi job does not stop it")
        boom = ST.CallFailed("down")
        res, rows, *_ = self.go(Stub([boom, boom, boom, boom], [], []), redo=True)
        self.assertEqual(len(res["failed"]), 3); self.assertIn("three verses running failed", res["stopped"])

    def test_answers_are_cleaned(self):
        self.assertIsNone(ST.clean_draft({"notes": []}))
        d = ST.clean_draft({"translation": " t //", "notes": [{"anchor": "a", "note": ""}, "x", {"note": "n"}],
                            "glossary": [{"term": ""}, {"term": "Kuru", "kind": "people"}]})
        self.assertEqual(d["notes"], [{"anchor": "", "kind": "", "note": "n"}])
        self.assertEqual([g["term"] for g in d["glossary"]], ["Kuru"])
        c = ST.clean_critique({"fidelity": "5", "completeness": 9, "issues": [{"severity": "MAJOR"}], "verdict": "Accept"})
        self.assertEqual((c["fidelity"], c["completeness"], c["issues"][0]["severity"], c["verdict"]),
                         (5, None, "major", "accept"))
        self.assertFalse(ST.accepted(c))
        self.assertEqual(ST.parse_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(ST.parse_json('noise {"a": 2} noise'), {"a": 2})
        self.assertIsNone(ST.parse_json("[1]"))


class APersonsWord(unittest.TestCase):
    def test_review_and_a_glossary_entry(self):
        with tempfile.TemporaryDirectory() as d:
            db = fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            allp = ST.load_text(con, "MBh01")
            x = next(p for p in allp if p["ref"] == "1.1.8")
            rec = {"passage_id": x["id"], "doc_code": "MBh01", "page_no": 1, "idx": 3, "verse_ref": "1.1.8",
                   "src_hash": ST.src_hash(x["text"]), "translation": "t //", "status": "flagged", "created_at": ST.now()}
            ST.store(con, rec)
            con.close()
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db),
                                             "--doc", "MBh01"] + list(a), capture_output=True, text=True,
                                            encoding="utf-8", cwd=d, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            r = run("--review", "1.1.8")
            self.assertEqual(r.returncode, 1); self.assertIn("--review needs --by", r.stdout)
            r = run("--review", "1.1.8,1.1.7", "--by", "Dhruv", "--note", "checked against the CE")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("1.1.8: version 1 accepted by Dhruv", r.stdout)
            self.assertIn("1.1.7: no scholarly English to review", r.stdout)
            r = run("--term", "P\u0101rik\u1e63ita", "--rendering", "the son of Parik\u1e63it", "--kind", "epithet",
                    "--note", "Janamejaya")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            con = sqlite3.connect(str(db))
            self.assertEqual(con.execute("SELECT reviewed_by, review_verdict, review_note FROM scholar_translations")
                             .fetchone(), ("Dhruv", "accept", "checked against the CE"))
            allp = ST.load_text(con, "MBh01")
            i = next(k for k, p in enumerate(allp) if p["ref"] == "1.1.8")
            b, _ = ST.context(allp, i, {})
            gl = ST.glossary(con, "MBh01", allp[i], b)
            self.assertEqual((gl[0]["term"], gl[0]["rendering"], gl[0]["source"]),
                             ("P\u0101rik\u1e63ita", "the son of Parik\u1e63it", "person"), "a person's entry wins")
            self.assertIn("- P\u0101rik\u1e63ita = the son of Parik\u1e63it (epithet): Janamejaya", ST.gloss_lines(gl))
            con.execute("UPDATE passages SET text = text || ' \u0964' WHERE verse_ref = '1.1.8'")
            con.commit(); con.close()
            r = run("--review", "1.1.8", "--by", "Dhruv")
            self.assertIn("1.1.8: stale", r.stdout)


class ThePages(unittest.TestCase):
    def test_the_report_and_the_index(self):
        with tempfile.TemporaryDirectory() as d:
            db = fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            allp = ST.load_text(con, "MBh01")
            for x, st, t in ((allp[2], "passed", "The *s\u016bta* said: I was with Janamejaya <b>. //"), (allp[3], "flagged", "x //")):
                ST.store(con, {"passage_id": x["id"], "doc_code": "MBh01", "page_no": 1, "idx": x["idx"],
                               "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]), "translation": t,
                               "notes": json.dumps([{"anchor": "Janamejaya", "kind": "name", "note": "a king"}]),
                               "critique": json.dumps([MAJOR, ACCEPT]), "draft": "first", "passes": 2, "fidelity": 5,
                               "fluency": 4, "working_fidelity": 2, "working_fluency": 3, "status": st, "cost_usd": 0.05,
                               "created_at": "2026-10-14T12:00:00+00:00"})
            con.execute("UPDATE passages SET text = 'changed' WHERE id = ?", (allp[3]["id"],))
            con.commit()
            h = ST.render_doc(con, "MBh01", nav=True)
            self.assertIn("<em>s\u016bta</em>", h); self.assertIn("Janamejaya<sup>1</sup>", h); self.assertIn("&lt;b&gt;", h)
            self.assertIn('<span class="st passed">passed</span>', h); self.assertIn('<span class="st stale">stale</span>', h)
            self.assertIn("the judge's fidelity: scholarly <b>5.00</b>, working <b>2.00</b>", h)
            self.assertIn("The working English (on the site)</div><p class=\"wk\">The s\u016bta said: I was near", h)
            self.assertIn("major misreading, at p\u0101rik\u1e63itasya", h)
            self.assertIn('<a href="/scholar">Scholarly English</a>', h)
            self.assertIn("@media(max-width:820px)", h)
            ix = ST.render_index(con, nav=True)
            self.assertIn('<a href="/scholar/MBh01">MBh01</a>', ix)
            self.assertIn("No scholarly English for <b>Other</b> yet", ST.render_doc(con, "Other"))
            con.close()
            r = subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc", "MBh01",
                                "--report", "--exports", str(Path(d) / "ex")], capture_output=True, text=True,
                               encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = (Path(d) / "ex" / "scholar_MBh01.html").read_text(encoding="utf-8")
            self.assertIn("<title>Scholarly English: MBh01</title>", out); self.assertNotIn('href="/library"', out)
            e = sqlite3.connect(":memory:")
            self.assertIn("None yet. The pilot is the first chapter", ST.render_index(e))
            e.close()


class TheDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_redeem_2026_10_14 as base
        cls.base = base
        cls.d = load("dashboard_scholar", SCRIPTS / "dashboard.py")
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.d.SOURCE_DESK_DIR = t / "source_desk"
        cls.fx = base.corpus(t / "fx")
        cls.orig = (cls.d.REDEEM_FILE, cls.d.PATH_FILE)
        cls.d.REDEEM_FILE = t / "redeem.json"
        cls.d.REDEEM_FILE.write_text(json.dumps(base.RD.ledger(base.args(cls.fx))), encoding="utf-8")
        cls.d.PATH_FILE = t / "text_path.json"
        cls.d.PATH_FILE.write_text(json.dumps({"texts": [
            {"doc": "Mixed", "path": "repair", "why": "Tesseract's text: debris <material>"},
            {"doc": "Clean", "path": "translate", "why": "no debris"}]}), encoding="utf-8")
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.d.REDEEM_FILE, cls.d.PATH_FILE = cls.orig
        cls.tmp.cleanup()

    def test_the_library_holds_what_the_path_holds(self):
        h = self.c.get("/library?db=" + str(self.fx["db"])).get_data(as_text=True)
        card = lambda doc: re.search(r'<div class="card-wrap" data-doc="%s">(.*?)<div class="bsacts"' % doc, h, re.S).group(1)
        m = card("Mixed")
        self.assertNotIn("Finish EN</button>", m); self.assertNotIn("Add Hindi</button>", m)
        self.assertIn("Finish EN and Add Hindi are not offered now: repair its scan first (the path: Tesseract&#x27;s "
                      "text: debris &lt;material&gt;)", m)
        self.assertIn("Add Hindi</button>", card("Clean"), "the path says translate: offered")
        g = card("Gone")
        self.assertNotIn("Finish EN</button>", g)
        self.assertIn("not offered now: a better source first (its scan is not here)", g, "not charted: the count says")
        self.assertIn('href="/scholar"', h); self.assertIn("&#128220; Scholarly English", h)
        self.assertIn("if(j.ok===false && /HOLD_2026_10_14/.test(out)) return {word:'held'", h)
        self.assertEqual(self.d._hold_reason("Bod", {"status": "withdrawn"}), "withdrawn from the site: a better source first")
        self.assertEqual(self.d._hold_note("Bod", "x", {"status": "withdrawn"}), "", "the register's own note says it")
        self.assertEqual(self.d._hold_reason("Nobody", None, {}), "")

    def test_the_path_file_is_read_again_only_when_it_changes(self):
        a = self.d._path_texts()
        self.assertIs(self.d._path_texts(), a)
        self.d.PATH_FILE.write_text(json.dumps({"texts": [{"doc": "Mixed", "path": "translate"}]}) + " ", encoding="utf-8")
        self.assertEqual(self.d._hold_reason("Mixed"), "")
        self.d.PATH_FILE.write_text("not json", encoding="utf-8")
        self.assertEqual(self.d._path_texts(), {})
        self.d.PATH_FILE.write_text(json.dumps({"texts": [
            {"doc": "Mixed", "path": "repair", "why": "Tesseract's text: debris <material>"},
            {"doc": "Clean", "path": "translate", "why": "no debris"}]}), encoding="utf-8")

    def test_the_scholar_pages(self):
        db = self.fx["db"]
        r = self.c.get("/scholar?db=" + str(db))
        self.assertEqual(r.status_code, 200); self.assertIn("None yet.", r.get_data(as_text=True))
        import db_utils
        con = db_utils.connect(str(db))
        ST.ensure_schema(con)
        pid, pg, idx = con.execute("SELECT p.id, p.page_no, p.idx FROM passages p JOIN docs d ON d.id=p.doc_id WHERE "
                                   "d.code='Clean' LIMIT 1").fetchone()
        text = con.execute("SELECT text FROM passages WHERE id=?", (pid,)).fetchone()[0]
        ST.store(con, {"passage_id": pid, "doc_code": "Clean", "page_no": pg, "idx": idx, "verse_ref": "1.1",
                       "src_hash": ST.src_hash(text), "translation": "On the field of *dharma* //", "status": "passed",
                       "cost_usd": 0.04, "created_at": "2026-10-14T12:00:00+00:00"})
        con.close()
        h = self.c.get("/scholar?db=" + str(db)).get_data(as_text=True)
        self.assertIn('<a href="/scholar/Clean">Clean</a>', h)
        r = self.c.get("/scholar/Clean?db=" + str(db))
        self.assertEqual(r.status_code, 200)
        self.assertIn("On the field of <em>dharma</em> //", r.get_data(as_text=True))
        self.assertEqual(self.c.get("/scholar/bad doc").status_code, 400)
        self.assertEqual(self.c.get("/scholar/Clean?db=" + str(self.t / "nothing" / "x.db")).status_code, 500)


class TheTranslateHold(unittest.TestCase):
    def test_withdrawn_or_set_aside_is_refused_before_any_call(self):
        import translate_passages as tp
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            reg = t / "reg.jsonl"
            old = os.environ.get("SA_SOURCE_VERDICTS")
            os.environ["SA_SOURCE_VERDICTS"] = str(reg)
            try:
                for recs, want in (([{"doc": "J", "status": "withdrawn", "at": "2026-10-12T13:56", "reason": "damaged"}],
                                    "REFUSING (HOLD_2026_10_14): J is withdrawn from the site in data/source_verdicts.jsonl "
                                    "(2026-10-12T13:56: damaged). Nothing was sent. A better source first."),
                                   ([{"doc": "J", "status": "set_aside"}], "J is set aside"),
                                   ([{"doc": "J", "status": "withdrawn"}, {"doc": "J", "status": "restored"}], None),
                                   ([], None)):
                    reg.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
                    m = tp._hold_message("J")
                    if want is None:
                        self.assertIsNone(m)
                    else:
                        self.assertIn(want, m); self.assertIn("--allow-held", m)
            finally:
                if old is None:
                    os.environ.pop("SA_SOURCE_VERDICTS", None)
                else:
                    os.environ["SA_SOURCE_VERDICTS"] = old
            import db_utils
            db = str(t / "t.db")
            con = sqlite3.connect(db); db_utils.ensure_schema(con)
            con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
            con.execute("INSERT INTO docs(code) VALUES('J')")
            for i in range(10):
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,ocr_engine) VALUES(1,?,1,?, 'mula', "
                            "'tesseract')", (i + 1, V6 + " CHARA IATA"))
            con.commit(); con.close()
            inbox = t / "inbox"; inbox.mkdir()
            for i in range(3):
                (inbox / ("J_%04d.pdf" % (i + 1))).write_bytes(b"%PDF")
            reg.write_text(json.dumps({"doc": "J", "status": "withdrawn"}) + "\n", encoding="utf-8")
            base = [sys.executable, str(SCRIPTS / "translate_passages.py"), "--db", db, "--doc", "J", "--progress",
                    str(t / "p.json"), "--config", str(t / "c.json")]
            env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_SOURCE_VERDICTS=str(reg), SA_INBOX_DIR=str(inbox))
            env.pop("SA_ALLOW_HELD", None)
            r = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", cwd=str(REPO), env=env)
            self.assertEqual(r.returncode, 4, r.stdout + r.stderr); self.assertIn("REFUSING (HOLD_2026_10_14)", r.stdout)
            env["SA_ALLOW_HELD"] = "1"   # let through: the debris guard is next, and it holds (exit 3), so nothing is sent
            r = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", cwd=str(REPO), env=env)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr); self.assertNotIn("HOLD_2026_10_14", r.stdout)
            r = subprocess.run(base + ["--allow-held"], capture_output=True, text=True, encoding="utf-8", cwd=str(REPO),
                               env=dict(env, SA_ALLOW_HELD=""))
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)


class ThePatcher(unittest.TestCase):
    FILES = ("dashboard.py", "translate_passages.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_scholar_*")) for f in self.FILES}
        gib = sorted(REPO.glob(".gitignore.bak_scholar_*"))
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_2026_10_14.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            (t / ".gitignore").write_bytes(b"data/redeem.json\r\n")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("scripts/scholar_translate.py (SCHOLAR_2026_10_14) is not there",
                                                             r.stdout)
            shutil.copy2(SCRIPTS / "scholar_translate.py", t / "scripts" / "scholar_translate.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("CHECK OK: 3 file(s) to write", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_scholarv2_*"))   # SCHOLAR_V2_2026_10_14 came after (dashboard.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            g = (t / ".gitignore").read_bytes()
            self.assertTrue(g.endswith(b"# SCHOLAR_2026_10_14: the scholarly English runs' logs stay local\r\ndata/scholar/\r\n"),
                            "its line endings kept")
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            if gib:   # the repo's own .gitignore, as it was: the same result
                shutil.copy2(gib[0], t / ".gitignore")
                r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                later = sorted(REPO.glob(".gitignore.bak_hygiene_*"))   # REPO_HYGIENE_2026_10_15 came after (PILOT_FIX)
                want = later[0] if later else (REPO / ".gitignore")
                self.assertEqual((t / ".gitignore").read_bytes(), want.read_bytes())
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b"if(j.ok===false && /KILLED/.test(out))", b"if(j.ok===false&&/KILLED/.test(out))"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor 5 found 0 times (want 1): this is not the file released",
                                                             r.stdout)
            self.assertNotIn(b"HOLD_2026_10_14", (t / "scripts" / "translate_passages.py").read_bytes(), "all or nothing")
            p.write_bytes(b"# an older dashboard\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry REDEEM_2026_10_14", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p, mark in ((SCRIPTS / "scholar_translate.py", b"SCHOLAR_2026_10_14"),
                        (SCRIPTS / "patch_scholar_2026_10_14.py", b"SCHOLAR_2026_10_14"), (Path(__file__), b"SCHOLAR_2026_10_14")):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(mark, b)
        for f in ("dashboard.py", "translate_passages.py"):
            b = (SCRIPTS / f).read_bytes()
            self.assertIn(b"SCHOLAR_2026_10_14", b, f); self.assertIn(b"HOLD_2026_10_14", b, f)
        s = (SCRIPTS / "scholar_translate.py").read_text(encoding="ascii")
        self.assertIn('JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z\'!\\"]{1,}")', s, "redeem.py's rule")
        self.assertIn(".replace(\"{title}\", meta[\"title\"])", s, "the prompts are not str.format()ed (their JSON "
                      "braces); CLAUDE_ENGINE_2026_10_15: in system_for, for every engine")


if __name__ == "__main__":
    unittest.main()
