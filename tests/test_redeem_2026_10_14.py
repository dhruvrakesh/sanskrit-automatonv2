# -*- coding: ascii -*-
"""REDEEM_2026_10_14 and T2_2026_10_14: what of the translation already paid for is kept, and what is not, text by
text (scripts/redeem.py, read-only); the passages the judge marks translated again with the stronger engine and judged
again (scripts/retranslate_marked.py; a dry run by default); the Library card's line, the /redeem page and the
"Count again" step (dashboard.py); the chart's T2 NEXT (text_path.py). Temp files only, never data/context.db."""
import argparse, hashlib, importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RD = load("redeem_redeem", SCRIPTS / "redeem.py")
RM = load("retranslate_marked_redeem", SCRIPTS / "retranslate_marked.py")

DEV = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 "
       "\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947")
CLEAN = DEV + " \u0964\u0964 %d \u0964\u0964"
DIRTY = DEV + " af bates Prec \u0964\u0964 %d"     # Latin letters in a Devanagari verse: Tesseract's debris
SCHEMA = """
CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);
CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, iast TEXT, translation TEXT,
  translated_at TEXT, ocr_engine TEXT, text_type TEXT, translation_qa REAL);
CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);
CREATE TABLE mt_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, passage_id INTEGER NOT NULL, lang TEXT NOT NULL DEFAULT 'en',
  engine TEXT, prompt_version TEXT, score_fidelity INTEGER, score_fluency INTEGER, comment TEXT, created_at TEXT);
CREATE TABLE usage_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT NOT NULL, doc TEXT, engine TEXT,
  in_chars INTEGER DEFAULT 0, out_chars INTEGER DEFAULT 0, in_tokens REAL DEFAULT 0, out_tokens REAL DEFAULT 0,
  cost_usd REAL DEFAULT 0, duration_s REAL DEFAULT 0, passages INTEGER DEFAULT 0, ok INTEGER DEFAULT 1);
"""


def add(con, code, rows):
    """rows: (text, translation, ocr_engine, text_type); one verse a row on page 1. {idx: passage id}"""
    did = con.execute("INSERT INTO docs(code, category) VALUES(?, 'purana')", (code,)).lastrowid
    ids = {}
    for i, (text, tr, eng, tt) in enumerate(rows):
        ids[i] = con.execute("INSERT INTO passages(doc_id, page_no, idx, text, iast, translation, translated_at, ocr_engine, "
                             "text_type) VALUES(?,?,?,?,?,?,?,?,?)",
                             (did, 1, i, text % i if "%d" in text else text, "dharmaksetre", tr,
                              "2026-10-01T10:00:00+00:00" if tr else None, eng, tt)).lastrowid
    return ids


def review(con, pid, fid, why, at="2026-10-11T12:00:00+00:00", pv="judge-v1"):
    con.execute("INSERT INTO mt_reviews(passage_id, lang, engine, prompt_version, score_fidelity, score_fluency, comment, "
                "created_at) VALUES(?, 'en', 'gemini:gemini-2.5-flash', ?, ?, 4, ?, ?)", (pid, pv, fid, why, at))


def corpus(td: Path) -> dict:
    """The fixture: a database, its page folders, the register and the chart."""
    td.mkdir(parents=True, exist_ok=True)
    db = td / "context.db"
    con = sqlite3.connect(str(db))
    con.executescript(SCHEMA)
    ids = {}
    ids["Clean"] = add(con, "Clean", [(CLEAN, "the field of dharma", "gemini-vision", "mula")] * 40)
    ids["Mixed"] = add(con, "Mixed", [(CLEAN, "kept", "tesseract", "mula")] * 10 + [(DIRTY, "from debris", "tesseract",
                                                                                     None)] * 10
                       + [(CLEAN, None, "tesseract", "mula")] * 5 + [(DIRTY, "noise", "tesseract", "noise")])
    ids["Debris"] = add(con, "Debris", [(CLEAN, "kept", None, "mula")] * 2 + [(DIRTY, "from debris", None, "mula")] * 8)
    ids["Gone"] = add(con, "Gone", [(CLEAN, "kept", "tesseract", "mula")] + [(DIRTY, "from debris", "tesseract", "mula")] * 9)
    ids["Bod"] = add(con, "Bod", [(CLEAN, "kept here", "gemini-vision", "mula")] * 5)
    ids["Judged"] = add(con, "Judged", [(CLEAN, "english %d" % i, "gemini-vision", "mula") for i in range(40)])
    ids["Old-RETIRED"] = add(con, "Old-RETIRED", [(DIRTY, "x", None, "mula")] * 3)
    ids["Empty"] = add(con, "Empty", [(CLEAN, None, None, "mula")] * 3)
    ids["Karan"] = add(con, "Karan", [(CLEAN, None, "gemini-vision", "mula")] * 4)    # in repair: its English replaced
    ids["Wiped"] = add(con, "Wiped", [(CLEAN, None, "tesseract", "mula")] * 3)        # re-ingested: its English gone
    j = ids["Judged"]
    for k in range(8):
        review(con, j[k], 4, "faithful")
    review(con, j[8], 1, "the meaning is wrong: it reads a battle as a sacrifice")
    review(con, j[9], 2, "the source text is garbled OCR")
    review(con, j[10], 1, "wrong", at="2026-10-10T12:00:00+00:00")
    review(con, j[10], 5, "faithful now")                  # the latest verdict counts
    review(con, j[11], None, "no answer")                   # not a verdict
    u = "INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, cost_usd, passages) VALUES(?,?,?,?,?,?,?)"
    con.execute(u, ("translation", "Mixed", "gemini:gemini-2.5-flash", 100000, 10000, 999.0, 100))   # repriced
    con.execute(u, ("translation", "Mixed", "legacy", 0, 0, 0.02, 20))                              # as recorded
    con.execute(u, ("translation", "Vanished", "gemini:gemini-2.5-flash", 10000, 0, 0.5, 10))       # no longer here
    con.execute(u, ("translation", "Judged", "gemini:gemini-2.5-pro", 20000, 2000, 1.0, 40))
    con.execute(u, ("translation", "Karan", "gemini:gemini-2.5-pro", 0, 0, 0.01, 4))                # as recorded
    con.execute(u, ("translation", "Wiped", "gemini:gemini-2.5-pro", 0, 0, 0.004, 3))
    con.execute(u, ("ocr", "Mixed", "gemini:gemini-2.5-flash", 900000, 900000, 9.0, 0))             # not translation
    con.commit()
    con.close()
    inbox, raw = td / "inbox", td / "raw"
    inbox.mkdir(); raw.mkdir()
    for code, pdfs, pages in (("Mixed", 3, 3), ("Debris", 2, 2), ("Gone", 1, 3), ("Judged", 1, 1)):
        for k in range(1, pages + 1):
            (raw / ("%s_%04d.jsonl" % (code, k))).write_text("{}\n", encoding="utf-8")
        for k in range(1, pdfs + 1):
            (inbox / ("%s_%04d%s.pdf" % (code, k, "_norm" if k == 2 else ""))).write_bytes(b"%PDF")
    reg = td / "source_verdicts.jsonl"
    reg.write_text(json.dumps({"doc": "Bod", "status": "in_repair"}) + "\n" + "not json\n"
                   + json.dumps({"doc": "Bod", "status": "withdrawn"}) + "\n"
                   + json.dumps({"doc": "Karan", "status": "in_repair", "at": "2026-10-11"}) + "\n", encoding="utf-8")
    chart = td / "text_path.json"
    chart.write_text(json.dumps({"texts": [{"doc": "Debris", "path": "repair", "facts": {"changed_en": 3}}]}),
                     encoding="utf-8")
    return {"db": db, "inbox": inbox, "raw": raw, "verdicts": reg, "chart": chart, "ids": ids}


def args(fx, **kw):
    a = argparse.Namespace(db=str(fx["db"]), only=None, inbox=str(fx["inbox"]), raw=str(fx["raw"]),
                           verdicts=str(fx["verdicts"]), chart=str(fx["chart"]))
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


class TheLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fx = corpus(Path(cls.tmp.name))
        cls.res = RD.ledger(args(cls.fx))
        cls.by = {t["doc"]: t for t in cls.res["texts"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_text_has_one_verdict(self):
        self.assertEqual([(t["doc"], t["verdict"]) for t in self.res["texts"]],
                         [("Clean", "redeemed"), ("Mixed", "mostly"), ("Judged", "mostly"), ("Debris", "redo"),
                          ("Gone", "source"), ("Karan", "replaced"), ("Wiped", "replaced"), ("Bod", "withdrawn")])
        self.assertEqual(self.res["by_verdict"], {"redeemed": 1, "mostly": 2, "redo": 1, "source": 1, "replaced": 2,
                                                  "withdrawn": 1})
        self.assertNotIn("Old-RETIRED", self.by)
        self.assertNotIn("Empty", self.by, "no English and nothing spent: nothing to redeem")

    def test_the_classes(self):
        m = self.by["Mixed"]
        self.assertEqual((m["passages"], m["english"], m["keep"], m["redo_debris"]), (25, 20, 10, 10),
                         "the noise verse is not counted; the untranslated count as passages only")
        self.assertEqual(m["classes"], {"judged_sound": 0, "judged_wrong": 0, "vision": 0, "no_debris": 10, "debris": 10})
        j = self.by["Judged"]
        self.assertEqual(j["classes"], {"judged_sound": 9, "judged_wrong": 2, "vision": 29, "no_debris": 0, "debris": 0},
                         "the latest verdict of a passage counts; a verdict without a score is not one")
        self.assertEqual((j["judged"], j["blamed"], j["redo_wrong"], j["wrong_pct"], j["kept_pct"]), (11, 1, 1, 18.2, 95.0))
        self.assertEqual([(x["where"], x["fidelity"], x["source_blamed"]) for x in j["marked"]],
                         [("1.8", 1, False), ("1.9", 2, True)])
        self.assertEqual(self.by["Debris"]["classes"]["no_debris"], 2, "an ingest older than the engine's record")

    def test_the_lines(self):
        self.assertEqual(self.by["Clean"]["line"], "Redeemed: 40 of 40 English kept")
        self.assertEqual(self.by["Mixed"]["line"], "Mostly redeemed: 10 of 20 English kept (50%); 10 made from misread "
                                                   "Sanskrit, translated again after the repair (about $0.0060)")
        self.assertEqual(self.by["Judged"]["line"], "Mostly redeemed: 38 of 40 English kept (95%); the judge marks 2 of 11 "
                                                    "sampled (18%): translate them again (T2, about $0.0010), then judge more")
        self.assertEqual(self.by["Debris"]["line"], "To translate again: 2 of 10 English kept; 8 made from misread Sanskrit, "
                                                    "translated again after the repair (about $0.0048)")
        self.assertEqual(self.by["Gone"]["line"], "Not redeemable as it is: 9 of 10 English made from misread Sanskrit, and "
                                                  "its scan is not here: a better source first")
        self.assertEqual(self.by["Bod"]["line"], "Withdrawn: off the site; its 5 English stay here (5 made from a clean "
                                                 "reading) until a better source replaces it")
        self.assertEqual(self.by["Karan"]["line"], "Replaced by the repair: its English ($0.010) was made from the old "
                                                   "reading; the 4 verses of the repaired reading are here, not yet "
                                                   "translated; the site keeps the old English until they are translated "
                                                   "and released (about $0.0024)")
        self.assertEqual(self.by["Wiped"]["line"], "No English now: $0.0040 was spent on English that is no longer here (its "
                                                   "passages were ingested again); its 3 verses can be translated again "
                                                   "(about $0.0018)")
        self.assertEqual((self.by["Karan"]["at_risk"], self.by["Karan"]["english"], self.by["Karan"]["state"]),
                         (0.01, 0, "in_repair"))
        self.assertTrue(self.by["Mixed"]["scan_here"]); self.assertTrue(self.by["Debris"]["scan_here"])
        self.assertFalse(self.by["Gone"]["scan_here"], "1 PDF of 3 pages is not the scan")
        self.assertEqual((self.by["Debris"]["path"], self.by["Debris"]["changed_en"]), ("repair", 3), "from the chart")

    def test_the_money(self):
        self.assertEqual(self.res["prices"], {"flash": 0.0006, "pro": RD.PRO_DEFAULT},
                         "flash: $0.078 over 130 passages; pro: 40 passages are too few to measure")
        self.assertAlmostEqual(self.by["Mixed"]["spent"], 0.075, places=6)    # 0.03 + 0.025 repriced, + 0.02 recorded
        self.assertAlmostEqual(self.by["Mixed"]["at_risk"], 0.0375, places=6)
        self.assertAlmostEqual(self.by["Judged"]["spent"], 0.045, places=6)
        self.assertEqual(self.by["Judged"]["redo_cost"], 0.0016, "$0.00099 (pro) + $0.0006 (flash), to 4 places")
        t = self.res["totals"]
        self.assertEqual((t["english"], t["keep"], t["debris"], t["judged_wrong"], t["blamed"]), (125, 96, 27, 2, 1))
        self.assertAlmostEqual(t["spent"], 0.134, places=6); self.assertAlmostEqual(t["spent_all"], 0.137, places=6)
        self.assertAlmostEqual(t["spent_gone"], 0.003, places=6)
        self.assertAlmostEqual(t["spent_replaced"], 0.014, places=6); self.assertEqual(t["replaced"], 2)

    def test_the_verdict_edges(self):
        r = dict({k: 0 for k in RD.CLASSES}, n=100, en=100, marked=[], blamed=0)
        j = lambda **kw: RD.judge("T", dict(r, **kw), {}, True, 0.0, 0.0006, 0.001, {})["verdict"]
        self.assertEqual(j(vision=97, debris=3), "redeemed")
        self.assertEqual(j(vision=96, debris=4), "mostly")
        self.assertEqual(j(judged_sound=9, judged_wrong=1, vision=90), "mostly", "the judge marks 10% of its sample")
        self.assertEqual(j(judged_sound=19, judged_wrong=1, vision=80), "redeemed", "5%: kept")
        self.assertEqual(j(vision=50, debris=50), "mostly")
        self.assertEqual(j(vision=49, debris=51), "redo")
        self.assertEqual(RD.judge("T", dict(r, vision=49, debris=51), {}, False, 0, 0, 0, {})["verdict"], "source")
        self.assertEqual(RD.judge("T", dict(r, vision=100), {"T": {"status": "withdrawn"}}, True, 0, 0, 0, {})["verdict"],
                         "withdrawn")

    def test_spend_without_a_ledger(self):
        con = sqlite3.connect(":memory:")
        self.assertEqual(RD.spend_by_doc(con), ({}, RD.FLASH_DEFAULT, RD.PRO_DEFAULT))
        con.close()


class TheScript(unittest.TestCase):
    def test_it_writes_the_ledger_and_leaves_the_database_alone(self):
        with tempfile.TemporaryDirectory() as td:
            fx = corpus(Path(td))
            before = md5(fx["db"])
            out, h, c = Path(td) / "data" / "redeem.json", Path(td) / "x" / "r.html", Path(td) / "x" / "r.csv"
            base = [sys.executable, str(SCRIPTS / "redeem.py"), "--db", str(fx["db"]), "--inbox", str(fx["inbox"]),
                    "--raw", str(fx["raw"]), "--verdicts", str(fx["verdicts"]), "--chart", str(fx["chart"]),
                    "--out", str(out)]
            r = subprocess.run(base + ["--html", str(h), "--csv", str(c)], capture_output=True, text=True,
                               encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(md5(fx["db"]), before, "read-only")
            self.assertFalse(Path(str(fx["db"]) + "-wal").exists())
            self.assertIn("== MOSTLY REDEEMED: 2 text(s)", r.stdout)
            self.assertIn("VERDICT: 125 English in 6 text(s): 96 kept (77%)", r.stdout)
            self.assertIn("and $0.0030 was spent on texts no longer in the database", r.stdout)
            self.assertIn(", $0.014 on English a better reading replaced (2 text(s), no English here now); translating",
                          r.stdout)
            self.assertEqual(r.stdout.strip().splitlines()[-1],
                             "NEXT: python scripts\\retranslate_marked.py   (the passages the judge marks: the dry run, free)")
            res = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(res["mark"], "REDEEM_2026_10_14"); self.assertEqual(len(res["texts"]), 8)
            self.assertFalse(out.with_suffix(".tmp").exists())
            page = h.read_text(encoding="utf-8")
            self.assertIn("<title>What is redeemed</title>", page); self.assertIn("<h2>Not redeemable as it is <span>1", page)
            rows = c.read_text(encoding="utf-8").splitlines()
            self.assertTrue(rows[0].startswith("doc,verdict,english,kept,")); self.assertEqual(len(rows), 9)
            r = subprocess.run(base + ["--doc", "Judged", "--out", str(Path(td) / "one.json")], capture_output=True,
                               text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("marked 1.9  fidelity 2  (the judge blames the Sanskrit): the source text is garbled OCR", r.stdout)
            self.assertFalse((Path(td) / "one.json").exists(), "one text: the ledger is not rewritten")
            r = subprocess.run([sys.executable, str(SCRIPTS / "redeem.py"), "--db", str(Path(td) / "none.db")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("REFUSE:", r.stdout)


class TheMarked(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        td = Path(self.tmp.name)
        self.fx = corpus(td)
        con = sqlite3.connect(str(self.fx["db"]))
        j, b = self.fx["ids"]["Judged"], self.fx["ids"]["Bod"]
        con.execute("UPDATE passages SET translation='' WHERE id=?", (j[12],))
        review(con, j[12], 1, "wrong")                                                   # no English now
        con.execute("UPDATE passages SET translated_at='2026-10-12T09:00:00+00:00' WHERE id=?", (j[13],))
        review(con, j[13], 2, "wrong")                                                   # translated again since
        review(con, j[14], 2, "wrong, and the verse is Ramayana")                         # to do
        review(con, b[0], 1, "wrong")                                                    # withdrawn
        did = con.execute("SELECT doc_id FROM passages WHERE id=?", (j[0],)).fetchone()[0]
        pid = con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, translated_at, ocr_engine) "
                          "VALUES(?, 2, 0, ?, 'from debris', '2026-10-01T10:00:00+00:00', 'tesseract')",
                          (did, DIRTY % 7)).lastrowid
        review(con, pid, 1, "wrong")                                                     # debris
        review(con, j[15], 3, "fair")                                                    # not marked at 2
        con.commit(); con.close()
        self.gone = RM.withdrawn(self.fx["verdicts"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_which_and_why_left_out(self):
        con = RM.open_ro(str(self.fx["db"]))
        try:
            todo, left = RM.marked(con, None, 2, self.gone)
            todo3, _ = RM.marked(con, "Judged", 3, self.gone)
        finally:
            con.close()
        self.assertEqual(self.gone, {"Bod"})
        self.assertEqual([x["where"] for x in todo], ["1.8", "1.14"])
        self.assertEqual(sorted((x["doc"], x["where"], x["left"]) for x in left),
                         [("Bod", "1.0", "withdrawn from the site"),
                          ("Judged", "1.12", "no English now"),
                          ("Judged", "1.13", "translated again since the judge read it"),
                          ("Judged", "1.9", "the judge blames the Sanskrit: the source first"),
                          ("Judged", "2.0", "its Sanskrit carries OCR debris: the source first")])
        self.assertEqual([x["where"] for x in todo3], ["1.8", "1.14", "1.15"], "--max-fidelity 3")

    def test_the_dry_run_is_free(self):
        before = md5(self.fx["db"])
        logs = Path(self.tmp.name) / "logs"
        r = subprocess.run([sys.executable, str(SCRIPTS / "retranslate_marked.py"), "--db", str(self.fx["db"]),
                            "--verdicts", str(self.fx["verdicts"]), "--log-dir", str(logs)], capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(md5(self.fx["db"]), before); self.assertFalse(logs.exists())
        self.assertIn("DRY RUN (nothing called, nothing written)", r.stdout)
        self.assertIn("Judged" + " " * 46 + " 2 to translate again", r.stdout)
        self.assertIn("left out: 1 (withdrawn from the site)", r.stdout)
        self.assertIn("VERDICT: 2 passage(s) to translate again and judge again, about $0.0037; 5 left out", r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "NEXT: python scripts\\retranslate_marked.py --yes --max-usd 0.10")
        r = subprocess.run([sys.executable, str(SCRIPTS / "retranslate_marked.py"), "--db", str(self.fx["db"]), "--doc",
                            "Bod", "--verdicts", str(self.fx["verdicts"])], capture_output=True, text=True,
                           encoding="utf-8")
        self.assertIn("VERDICT: nothing the judge marked can be translated again now; 1 left out", r.stdout)
        self.assertIn("NEXT: python scripts\\judge_review.py", r.stdout)

    def test_without_a_key_nothing_is_called(self):
        # a copy of the script away from the repo's .env, with no key in its environment (and --max-usd 0 besides)
        s = Path(self.tmp.name) / "copy" / "scripts"
        s.mkdir(parents=True)
        for f in ("retranslate_marked.py", "redeem.py"):
            shutil.copy2(SCRIPTS / f, s / f)
        env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
        logs = Path(self.tmp.name) / "logs"
        r = subprocess.run([sys.executable, str(s / "retranslate_marked.py"), "--db", str(self.fx["db"]),
                            "--verdicts", str(self.fx["verdicts"]), "--log-dir", str(logs), "--yes", "--max-usd", "0"],
                           capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(s.parent))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("REFUSE: GEMINI_API_KEY is not set", r.stdout); self.assertFalse(logs.exists())


class TheRun(unittest.TestCase):
    """run() with a stand-in for the translator and the judge: what is mended, what is not, what stops it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = corpus(Path(self.tmp.name))
        con = sqlite3.connect(str(self.fx["db"]))
        rows = con.execute("SELECT p.id, p.idx FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code='Judged' "
                           "AND p.idx IN (20, 21, 22, 23)").fetchall()
        for pid, idx in rows:
            review(con, pid, 1, "wrong %d" % idx)
        con.commit(); con.close()
        con = RM.open_ro(str(self.fx["db"]))
        try:
            self.todo, _ = RM.marked(con, "Judged", 2, set())
        finally:
            con.close()
        self.calls = []
        self.orig_busy, self.orig_um = RM.busy_with, sys.modules.get("usage_meter")
        RM.busy_with = lambda doc: []
        self.budget = True
        um = types.ModuleType("usage_meter")
        um.budget_ok = lambda db, next_cost=0.0: self.budget
        sys.modules["usage_meter"] = um

    def tearDown(self):
        RM.busy_with = self.orig_busy
        if self.orig_um is not None:
            sys.modules["usage_meter"] = self.orig_um
        else:
            sys.modules.pop("usage_meter", None)
        self.tmp.cleanup()

    def a(self, **kw):
        a = argparse.Namespace(db=str(self.fx["db"]), only="Judged", engine=RM.ENGINE, judge_engine=RM.JUDGE,
                               no_hindi=False, max_usd=1.0, log_dir=str(Path(self.tmp.name) / "logs"))
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def translate(self, a, x, lang, cost=0.001):
        """A stand-in for translate_passages.py: 20 is mended, 21 is not, 22 comes back the same, 23 fails."""
        self.calls.append((x["where"], lang))
        con = sqlite3.connect(a.db)
        con.execute("INSERT INTO usage_log(kind, doc, engine, cost_usd, passages) VALUES('translation', ?, ?, ?, 1)",
                    (x["doc"], a.engine, cost))
        if x["idx"] == 23:
            con.commit(); con.close(); return 1
        if lang == "en" and x["idx"] != 22:
            con.execute("UPDATE passages SET translation=?, translated_at='2026-10-14T10:00:00+00:00' WHERE id=?",
                        ("new english %d" % x["idx"], x["id"]))
        con.commit(); con.close()
        return 0

    def judge(self, a, model, x, english, con):
        self.calls.append((x["where"], "judge", english))
        return (4, 4, "faithful") if x["idx"] == 20 else (2, 3, "still wrong")

    def test_mended_not_mended_unchanged_failed(self):
        self.assertEqual([x["where"] for x in self.todo], ["1.8", "1.20", "1.21", "1.22", "1.23"])
        todo = [x for x in self.todo if x["idx"] >= 20]
        out = RM.run(self.a(), todo, 0.00099, 0.00025, translate=self.translate, judge=self.judge)
        self.assertEqual((out["mended"], out["not_mended"], out["failed"], out["stopped"]),
                         (["Judged 1.20"], ["Judged 1.21"], ["Judged 1.22", "Judged 1.23"], ""))
        self.assertEqual(self.calls, [("1.20", "en"), ("1.20", "judge", "new english 20"), ("1.20", "hi"),
                                      ("1.21", "en"), ("1.21", "judge", "new english 21"), ("1.22", "en"), ("1.23", "en")],
                         "the Hindi of a mended passage is made again; nothing is judged that did not change")
        recs = [json.loads(x) for x in Path(out["log"]).read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["result"] for r in recs], ["mended", "not mended", "unchanged", "failed"])
        self.assertEqual((recs[0]["old_english"], recs[0]["new_english"], recs[0]["old_fidelity"], recs[0]["new_fidelity"],
                          recs[0]["hindi_rc"], recs[0]["mark"]), ("english 20", "new english 20", 1, 4, 0, "T2_2026_10_14"))
        self.assertTrue(Path(out["log"]).name.endswith("_Judged.jsonl"))

    def test_no_hindi(self):
        todo = [x for x in self.todo if x["idx"] == 20]
        RM.run(self.a(no_hindi=True), todo, 0.00099, 0.00025, translate=self.translate, judge=self.judge)
        self.assertNotIn(("1.20", "hi"), self.calls)

    def test_it_stops_at_its_cap_the_spend_cap_and_a_busy_text(self):
        todo = [x for x in self.todo if x["idx"] in (20, 21, 22)]
        tr = lambda a, x, lang: self.translate(a, x, lang, cost=0.01)
        out = RM.run(self.a(max_usd=0.02, no_hindi=True), todo, 0.00099, 0.00025, translate=tr, judge=self.judge)
        self.assertEqual(len(out["mended"]) + len(out["not_mended"]), 2, out)
        self.assertEqual(out["stopped"], "this run's --max-usd $0.02 is reached ($0.0200 spent)")
        self.calls.clear(); self.budget = False
        out = RM.run(self.a(), todo, 0.00099, 0.00025, translate=self.translate, judge=self.judge)
        self.assertEqual(self.calls, []); self.assertIn("the spend cap is reached", out["stopped"])
        self.budget = True
        RM.busy_with = lambda doc: [{"kind": "translate_hi", "doc": doc}]
        out = RM.run(self.a(), todo, 0.00099, 0.00025, translate=self.translate, judge=self.judge)
        self.assertEqual(self.calls, [])
        self.assertEqual(out["stopped"], "the dashboard writes Judged now (translate_hi): run this when it is done")

    def test_the_judge_replaces_its_verdict(self):
        js = load("judge_sample", SCRIPTS / "judge_sample.py")
        orig = js._judge_one
        js._judge_one = lambda model, lang, src, iast, tr: (4, 5, "faithful now")
        x = next(x for x in self.todo if x["idx"] == 20)
        con = sqlite3.connect(str(self.fx["db"]))
        review(con, x["id"], 3, "another prompt", pv="judge-v0")
        con.commit()
        try:
            got = RM.judge_one(self.a(), None, x, "new english", con)
        finally:
            js._judge_one = orig
        rows = con.execute("SELECT prompt_version, score_fidelity, comment, engine FROM mt_reviews WHERE passage_id=? "
                           "ORDER BY id", (x["id"],)).fetchall()
        con.close()
        self.assertEqual(got, (4, 5, "faithful now"))
        self.assertEqual(rows, [("judge-v0", 3, "another prompt", "gemini:gemini-2.5-flash"),
                                ("judge-v1", 4, "faithful now", RM.JUDGE)])


class TheChart(unittest.TestCase):
    def test_a_marked_text_gets_t2(self):
        tp = load("text_path_redeem", SCRIPTS / "text_path.py")
        pr = {"vision_page": 0.0024, "vision_dear": 0.0111, "measured": ["N"], "passage": 0.00063, "passage_from": "x"}
        f = {"doc": "T", "state": None, "passages": 100, "english": 100, "hindi": 100, "below_quality": 0,
             "vision_pct": 100.0, "level": "cosmetic", "misread_letters_pct": 0.5, "pdfs": 0, "raw_pages": 0,
             "vision_pages": 0, "merged_pages": 0, "merged_complete": False, "cost_per_page": 0.0024, "db_pages": 0,
             "reviews": {"n": 40, "fidelity": 3.9, "serious": 5}, "vectors": 0, "price_from": "the corpus"}
        o = tp.decide(f, pr)
        self.assertEqual(o["path"], "retranslate")
        self.assertEqual(o["next"], ["python scripts\\judge_review.py --doc T   (read what it marks)",
                                     "python scripts\\retranslate_marked.py --doc T   (T2: the marked passages again with "
                                     "the stronger engine, then judged again; the dry run, free)"])
        self.assertEqual(o["also"], ["the judge read 40 of 100 English: judge more to find the rest: python scripts\\"
                                     "judge_sample.py --doc T --sample-pct 80 --limit 40   (the dry run, free)"])
        self.assertAlmostEqual(o["cost"], 5 * tp.T2_PER_PASSAGE)


class TheDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load("dashboard_redeem", SCRIPTS / "dashboard.py")
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.d.SOURCE_DESK_DIR = t / "source_desk"
        cls.fx = corpus(t / "fx")
        cls.res = RD.ledger(args(cls.fx))
        cls.res["texts"][1]["line"] += " <b>"
        cls.orig = cls.d.REDEEM_FILE
        cls.d.REDEEM_FILE = t / "redeem.json"
        cls.d.REDEEM_FILE.write_text(json.dumps(cls.res), encoding="utf-8")
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.d.REDEEM_FILE = cls.orig
        cls.tmp.cleanup()

    def test_the_card_says_what_is_kept(self):
        h = self.c.get("/library?db=" + str(self.fx["db"])).get_data(as_text=True)
        m = re.search(r'<div class="card-wrap" data-doc="Mixed">(.*?)<div class="bsacts"', h, re.S)
        self.assertIsNotNone(m, h[:400])
        self.assertIn('<a class="rdm r-mid" href="/redeem#r-mostly" title="judged sound 0, vision 0, no debris seen 10, '
                      'debris 10, judged wrong 0; translation spent $0.075, of it $0.037 on English', m.group(1))
        self.assertIn("Mostly redeemed: 10 of 20 English kept (50%)", m.group(1)); self.assertIn("&lt;b&gt;", m.group(1))
        g = re.search(r'<div class="card-wrap" data-doc="Gone">(.*?)<div class="bsacts"', h, re.S).group(1)
        self.assertIn('class="rdm r-lo" href="/redeem#r-source"', g)
        self.assertIn(">96 kept</a>", h); self.assertIn("&#9878; What is redeemed", h); self.assertIn(".rdm.r-ok{", h)
        w = h[h.index("Not yet readable"):]
        k = re.search(r'<div class="card-wrap waiting">(?:(?!card-wrap).)*?<div class="code">Karan</div>(.*?)</div>\s*'
                      r'(?:<div class="card-wrap|</div>)', w, re.S)
        self.assertIsNotNone(k, w[:600])
        self.assertIn('<a class="rdm r-mid" href="/redeem#r-replaced"', w)
        self.assertIn("Replaced by the repair: its English ($0.010)", w)

    def test_the_redeem_page(self):
        r = self.c.get("/redeem")
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        self.assertIn("<title>What is redeemed</title>", h)
        self.assertIn('<a class="pchip r-mid" href="#r-mostly">Mostly redeemed <b>2</b></a>', h)
        self.assertIn('<h2 id="r-source" class="ph">Not redeemable as it is <span>1</span></h2>', h)
        self.assertIn("<b>125</b> English; <b>96</b> kept (77%); 27 made from misread Sanskrit; 2 judged wrong", h)
        self.assertIn("on English that cannot be kept as it is, $0.014 on English a better reading replaced; translating", h)
        self.assertIn('<a class="pchip r-mid" href="#r-replaced">Replaced by a better reading <b>2</b></a>', h)
        self.assertLess(h.index('href="/repair/Clean"'), h.index('href="/repair/Mixed"'))
        self.assertIn("repairStep(this.dataset.doc,&#39;redeem_all&#39;,this)", h)
        self.assertIn("&lt;b&gt;", h)
        old = self.d.REDEEM_FILE
        self.d.REDEEM_FILE = self.t / "none.json"
        try:
            self.assertIn("Not counted yet", self.c.get("/redeem").get_data(as_text=True))
            self.assertEqual(self.d._redeem(), {})
        finally:
            self.d.REDEEM_FILE = old
        if shutil.which("node"):
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "r.js"; p.write_text(js, encoding="utf-8")
            res = subprocess.run([shutil.which("node"), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_the_file_is_read_again_only_when_it_changes(self):
        self.d._REDEEM_CACHE.update(key=None, res=None)
        a = self.d._redeem()
        self.assertIs(self.d._redeem(), a)
        self.d.REDEEM_FILE.write_text(json.dumps(dict(self.res, at="2026-10-14T23:59:59")) + " ", encoding="utf-8")
        self.assertEqual(self.d._redeem()["at"], "2026-10-14T23:59:59")
        self.d.REDEEM_FILE.write_text(json.dumps(self.res), encoding="utf-8")

    def test_count_again_needs_no_text(self):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            self.assertEqual(self.c.post("/api/repair", json={"step": "redeem_all"}).status_code, 200)
        finally:
            self.d.launch = orig
        kind, doc, argv, mode = got[0]
        self.assertEqual((doc, mode, argv[-1]), ("corpus", "redeem_all", "--from-dashboard"))
        self.assertTrue(any(str(x).endswith("redeem.py") for x in argv), argv)
        self.assertIn("redeem_all", self.d._REPAIR_STEPS)
        self.assertIn("redeem_all: 'counting what of the translation is kept", self.d._REPAIR_JS)


class ThePatcher(unittest.TestCase):
    FILES = ("dashboard.py", "text_path.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_redeem_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            (t / ".gitignore").write_bytes(b"data/text_path.json\r\n")
            pat = [sys.executable, str(SCRIPTS / "patch_redeem_2026_10_14.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("redeem.py (REDEEM_2026_10_14) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "redeem.py", t / "scripts" / "redeem.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("retranslate_marked.py (T2_2026_10_14) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "retranslate_marked.py", t / "scripts" / "retranslate_marked.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / "scripts" / f).read_bytes(), (SCRIPTS / f).read_bytes(), f)
            g = (t / ".gitignore").read_bytes()
            self.assertIn(b"data/text_path.json\r\n# REDEEM_2026_10_14", g)
            self.assertIn(b"data/redeem.json\r\ndata/retranslate/\r\n", g, "its line endings kept")
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "text_path.py"
            p.write_bytes(p.read_bytes().replace(b'"python scripts\\\\judge_review.py --doc %s   (read what it marks)" % doc',
                                                 b'"python scripts\\\\judge_review.py --doc %s" % doc'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"REDEEM_2026_10_14", (t / "scripts" / "dashboard.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p, mark in ((SCRIPTS / "redeem.py", b"REDEEM_2026_10_14"), (SCRIPTS / "retranslate_marked.py", b"T2_2026_10_14"),
                        (SCRIPTS / "patch_redeem_2026_10_14.py", b"REDEEM_2026_10_14"), (Path(__file__), b"T2_2026_10_14")):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(mark, b)
        self.assertIn(b"REDEEM_2026_10_14", (SCRIPTS / "dashboard.py").read_bytes())
        self.assertIn(b"REDEEM_2026_10_14", (SCRIPTS / "text_path.py").read_bytes())


if __name__ == "__main__":
    unittest.main()
