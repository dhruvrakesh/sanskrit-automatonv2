# -*- coding: ascii -*-
"""REINGEST_2026_10_12 (R3): the repaired text into the database page by page. Only the pages that changed are
touched; a passage whose text is unchanged keeps its row, translations, vector and reviews (and moves with its
pictures and stories); the passages it leaves are those a full re-ingest makes; a backup first; a translation
lost must be said; refused while the dashboard runs a writer. Temp files only, never data/context.db."""
import http.server, json, os, shutil, sqlite3, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
import db_utils  # noqa: E402
import ingest_jsonl_fast as ij  # noqa: E402

DEAD = "http://127.0.0.1:9"     # no dashboard answers here (on the real machine one runs at 5057)
W = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d"
     "\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d"
     "\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e"
     "\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 %s \u0965 %d \u0965")
WORDS = ["\u0938\u091e\u094d\u091c\u092f", "\u0905\u0930\u094d\u091c\u0941\u0928", "\u0915\u0943\u0937\u094d\u0923",
         "\u0926\u094d\u0930\u094b\u0923", "\u092d\u0940\u0937\u094d\u092e", "\u0915\u0930\u094d\u0923",
         "\u0935\u093f\u0926\u0941\u0930", "\u0915\u0941\u0928\u094d\u0924\u0940", "\u0928\u0915\u0941\u0932",
         "\u0938\u0939\u0926\u0947\u0935"]
KEYS = ["A1", "A2", "A3", "B1", "B2", "C1", "C2", "C3", "X9", "Z7", "Z1"]
NAME = {k: WORDS[i % len(WORDS)] + ("\u0903" if i >= len(WORDS) else "") for i, k in enumerate(KEYS)}   # every verse its own text


def verses(*keys):
    return "\n".join(W % (NAME[k], i + 1) for i, k in enumerate(keys))


GARBAGE = "af 34 \u00a2 4 ba atk bates \u0967, ai ~ Prec \u096b! \u00a5 ; fy \u0915\u094d\u0937\u0940 | wt a"
OLD = {1: verses("A1", "A2", "A3"), 2: GARBAGE, 3: verses("B1", "B2"), 4: verses("C1", "C2", "C3"), 5: verses("Z1")}
NEW = {1: verses("A1", "A2", "A3"), 2: "", 3: verses("X9", "B1", "B2"), 4: verses("C1", "Z7", "C3")}

EXTRA = """
CREATE TABLE IF NOT EXISTS passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB, updated_at TEXT);
CREATE TABLE IF NOT EXISTS mt_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, passage_id INTEGER NOT NULL, lang TEXT NOT NULL
  DEFAULT 'en', engine TEXT, prompt_version TEXT, score_fidelity INTEGER, score_fluency INTEGER, comment TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER, surface TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS footnotes(id INTEGER PRIMARY KEY, passage_id INTEGER, entity_id INTEGER, note TEXT, author TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS doc_images(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER NOT NULL, status TEXT, title TEXT,
  anchor_page INTEGER, anchor_idx INTEGER);
CREATE TABLE IF NOT EXISTS doc_stories(id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, title TEXT, from_page INTEGER,
  from_idx INTEGER, to_page INTEGER, to_idx INTEGER);
""" + "".join("CREATE TRIGGER IF NOT EXISTS trg_passages_delete_cascade_%s AFTER DELETE ON passages BEGIN DELETE FROM %s "
              "WHERE passage_id = OLD.id; END;\n" % (t, t) for t in (
                  "entity_mentions", "footnotes", "mt_reviews", "passage_embeddings", "translation_history",
                  "translations_l10n"))


def page_file(folder: Path, doc: str, pg: int, text: str, engine: str):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ("%s_%04d.jsonl" % (doc, pg))).write_text(json.dumps({"text": text, "engine": engine}, ensure_ascii=False)
                                                       + "\n", encoding="utf-8")


def make_db(path: Path, pages: dict, doc="R"):
    con = db_utils.connect(str(path))
    db_utils.ensure_schema(con)
    ij._ensure_provenance(con)   # the order of ingest_jsonl_fast.main: ocr_engine and ocr_variants
    con.executescript(EXTRA)
    did = db_utils.ensure_doc(con, doc)
    for pg, text in sorted(pages.items()):
        ij.upsert_passages(con, did, pg, [{"text": text, "engine": "tesseract" if pg in (2, 5) else "gemini-vision"}])
    con.commit()
    return con, did


def rows(con, did):
    return [tuple(r) for r in con.execute("SELECT page_no, idx, text FROM passages WHERE doc_id=? ORDER BY page_no, idx", (did,))]


def pid(con, did, pg, idx):
    r = con.execute("SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?", (did, pg, idx)).fetchone()
    return r[0] if r else None


STUB = ("import sys, json, os\n"
        "open(os.environ['SA_STUB_LOG'], 'a').write(json.dumps([os.path.basename(sys.argv[0])] + sys.argv[1:]) + '\\n')\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.db = t / "context.db"
        con, did = make_db(self.db, OLD)
        self.did = did
        # translations, Hindi, a vector and a review on what moves and on what goes; a picture and a story
        for pg, idx in ((1, 1), (1, 2), (3, 1), (3, 2), (4, 1), (4, 2), (4, 3)):
            con.execute("UPDATE passages SET translation=? WHERE id=?", ("English %d.%d" % (pg, idx), pid(con, did, pg, idx)))
        for pg, idx in ((3, 1), (4, 2)):
            i = pid(con, did, pg, idx)
            con.execute("INSERT INTO translations_l10n(passage_id, lang, translation) VALUES(?, 'hi', ?)", (i, "Hindi %d" % i))
            con.execute("INSERT INTO passage_embeddings(passage_id, model, dim) VALUES(?, 'm', 3)", (i,))
            con.execute("INSERT INTO mt_reviews(passage_id, lang, score_fidelity, score_fluency) VALUES(?, 'en', 4, 5)", (i,))
        con.execute("INSERT INTO doc_images(doc_id, status, title, anchor_page, anchor_idx) VALUES(?, 'approved', 'moves', 3, 1)", (did,))
        con.execute("INSERT INTO doc_images(doc_id, status, title, anchor_page, anchor_idx) VALUES(?, 'draft', 'loses', 4, 2)", (did,))
        con.execute("INSERT INTO doc_stories(doc_id, title, from_page, from_idx, to_page, to_idx) VALUES(?, 'tale', 3, 1, 4, 3)", (did,))
        con.commit()
        self.ids = {k: pid(con, did, *k) for k in ((1, 1), (3, 1), (3, 2), (4, 1), (4, 2), (4, 3), (5, 1))}
        con.close()
        self.merged = t / "raw_merged"
        for pg, text in NEW.items():
            page_file(self.merged, "R", pg, text, "blank" if not text else "gemini-vision")
        self.steps = t / "steps"; self.steps.mkdir()
        shutil.copy2(SCRIPTS / "db_backup.py", self.steps / "db_backup.py")
        for s in ("classify_doc.py", "ocr_consensus.py"):
            (self.steps / s).write_text(STUB)
        self.log = t / "stub.log"

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args, url=DEAD):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_REINGEST_SCRIPTS=str(self.steps), SA_STUB_LOG=str(self.log),
                   SA_DASHBOARD_URL=url)
        r = subprocess.run([sys.executable, str(SCRIPTS / "reingest_pages.py"), "--doc", "R", "--db", str(self.db),
                            "--merged-dir", str(self.merged), "--backup-dir", str(self.t / "backups"),
                            "--log-dir", str(self.t / "reingest")] + list(args),
                           capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(self.t))
        return r.returncode, r.stdout + r.stderr

    def con(self):
        return sqlite3.connect(str(self.db))

    @staticmethod
    def last(out, key):
        return [l for l in out.splitlines() if l.startswith(key + ":")][-1]


class ThePlan(Base):
    def test_the_plan_writes_nothing_and_says_what_goes(self):
        con = self.con(); before = rows(con, self.did); con.close()
        rc, out = self.tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("PLAN (nothing written)", out)
        self.assertIn("unchanged 1 | changed 3 | only in the database 1 (not touched)", out)
        self.assertIn("page 0003  kept 2 (moved 2)  new 1  gone 0", out)
        self.assertIn("page 0004  kept 2 (moved 0)  new 1  gone 1  English lost 1", out)
        self.assertIn("what goes with them: English 1, Hindi 1, reviews 1, vectors 1", out)
        self.assertIn("(approved, page 3 passage 1): moves to passage 2", out)
        self.assertIn("(draft, page 4 passage 2): loses its passage", out)
        self.assertTrue(self.last(out, "NEXT").endswith("--doc R --apply --replace 1"), out)
        con = self.con(); self.assertEqual(rows(con, self.did), before); con.close()
        self.assertFalse((self.t / "backups").exists())

    def test_only_the_pages_asked_for(self):
        rc, out = self.tool("--pages", "3")
        self.assertEqual(rc, 0, out)
        self.assertIn("changed 1", out); self.assertNotIn("page 0004", out)
        self.assertTrue(self.last(out, "NEXT").endswith("--pages 3 --apply"), "nothing translated is lost on page 3")


class TheApply(Base):
    def test_a_loss_must_be_said(self):
        rc, out = self.tool("--apply")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE: this removes 1 English and 1 Hindi translations, and a picture or a story loses its passage", out)
        self.assertFalse((self.t / "backups").exists(), "nothing done: no backup either")

    def test_the_changed_pages_only_and_what_a_full_ingest_makes(self):
        rc, out = self.tool("--apply", "--replace", "1")
        self.assertEqual(rc, 0, out)
        self.assertTrue(list((self.t / "backups").glob("context_pre_reingest_R_*.db")), "a backup first")
        con = self.con()
        # the same passages as a wipe and a full ingest of the repaired text (page 5 is not in it: kept)
        fresh, fdid = make_db(self.t / "fresh.db", {**NEW, 5: OLD[5]})
        self.assertEqual(rows(con, self.did), rows(fresh, fdid))
        cols = "page_no, idx, text, norm, iast, verse_ref, chapter, text_type, chandas, padas, quality_score, ocr_engine, ocr_variants"
        q = "SELECT %s FROM passages WHERE doc_id=? ORDER BY page_no, idx" % cols
        self.assertEqual(con.execute(q, (self.did,)).fetchall(), fresh.execute(q, (fdid,)).fetchall())
        fresh.close()
        # unchanged rows keep their ids and what hangs on them; moved ones move
        self.assertEqual(pid(con, self.did, 1, 1), self.ids[(1, 1)])
        self.assertEqual(pid(con, self.did, 3, 2), self.ids[(3, 1)], "B1 moved from 1 to 2, the same row")
        self.assertEqual(pid(con, self.did, 3, 3), self.ids[(3, 2)])
        self.assertEqual(pid(con, self.did, 5, 1), self.ids[(5, 1)], "a page not in the repaired text is not touched")
        b1 = self.ids[(3, 1)]
        self.assertEqual(con.execute("SELECT translation FROM passages WHERE id=?", (b1,)).fetchone()[0], "English 3.1")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM translations_l10n WHERE passage_id=?", (b1,)).fetchone()[0], 1)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM passage_embeddings WHERE passage_id=?", (b1,)).fetchone()[0], 1)
        # what went took its children; the new passages are untranslated
        c2 = self.ids[(4, 2)]
        self.assertIsNone(con.execute("SELECT id FROM passages WHERE id=?", (c2,)).fetchone())
        for t in ("translations_l10n", "passage_embeddings", "mt_reviews"):
            self.assertEqual(con.execute("SELECT COUNT(*) FROM %s WHERE passage_id=?" % t, (c2,)).fetchone()[0], 0, t)
        self.assertEqual(con.execute("SELECT translation FROM passages WHERE doc_id=? AND page_no=4 AND idx=2",
                                     (self.did,)).fetchone()[0], "")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM passages WHERE doc_id=? AND page_no=2", (self.did,)).fetchone()[0], 0,
                         "the plate is blank")
        self.assertEqual(con.execute("SELECT translation FROM passages WHERE id=?", (self.ids[(4, 3)],)).fetchone()[0], "English 4.3")
        # the search index follows every row, and nothing else
        fts = dict(con.execute("SELECT rowid, text FROM passages_fts"))
        self.assertEqual(fts, dict(con.execute("SELECT id, text FROM passages")))
        # the picture and the story move with their passage
        self.assertEqual(con.execute("SELECT anchor_idx FROM doc_images WHERE title='moves'").fetchone()[0], 2)
        self.assertEqual(con.execute("SELECT anchor_idx FROM doc_images WHERE title='loses'").fetchone()[0], 2)
        self.assertEqual(con.execute("SELECT from_idx, to_idx FROM doc_stories").fetchone(), (2, 3))
        con.close()
        # what went is written down; the classification and the drift check ran
        log = [json.loads(l) for f in (self.t / "reingest").glob("R_*.jsonl") for l in f.read_text(encoding="utf-8").splitlines()]
        gone = {g["gone"]: g for g in log if "gone" in g}
        self.assertEqual(gone[c2]["translation"], "English 4.2"); self.assertEqual(gone[c2]["l10n"][0]["lang"], "hi")
        self.assertEqual(log[-1]["status"], "applied")
        calls = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertEqual([c[0] for c in calls], ["classify_doc.py", "ocr_consensus.py"])
        self.assertIn("--drift-only", calls[1])
        self.assertIn("only the 2 new passages need it", self.last(out, "NEXT"))
        # and again: nothing to do
        rc, out = self.tool("--apply", "--replace", "1")
        self.assertEqual(rc, 0, out); self.assertIn("nothing to do", self.last(out, "VERDICT"))

    def test_refused_while_the_dashboard_writes(self):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                b = json.dumps({"running": [{"kind": "translate_both", "doc": "Q", "state": "running"}]}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(b)

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
        try:
            rc, out = self.tool("--apply", "--replace", "1", url="http://127.0.0.1:%d" % srv.server_port)
        finally:
            srv.shutdown(); srv.server_close()
        self.assertEqual(rc, 1); self.assertIn("the dashboard runs a database writer: translate_both Q", out)
        con = self.con(); self.assertEqual(pid(con, self.did, 3, 1), self.ids[(3, 1)], "nothing changed"); con.close()

    def test_unknown_text_and_no_pages(self):
        rc, out = self.tool("--doc", "R")   # the same text twice is harmless
        self.assertEqual(rc, 0, out)
        r = subprocess.run([sys.executable, str(SCRIPTS / "reingest_pages.py"), "--doc", "Nope", "--db", str(self.db),
                            "--merged-dir", str(self.merged)], capture_output=True, text=True,
                           env=dict(os.environ, SA_DASHBOARD_URL=DEAD))
        self.assertEqual(r.returncode, 1); self.assertIn("Nope is not in the database", r.stdout)


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ThePatch(unittest.TestCase):
    def test_the_merge_pattern_says_no_warning_and_is_the_same(self):
        import warnings
        src = (SCRIPTS / "merge_ocr_sources.py").read_text(encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compile(src, "merge_ocr_sources.py", "exec")
        self.assertEqual([str(x.message) for x in w if "escape" in str(x.message)], [])
        mg = load("merge_reingest", SCRIPTS / "merge_ocr_sources.py")
        self.assertEqual(mg.STRAY.findall("a[b]c{d}e~f"), ["[", "]", "{", "}", "~"])

    def test_the_repair_prices_vision_from_what_it_cost(self):
        rt = load("repair_text_reingest", SCRIPTS / "repair_text.py")
        import cost_tracker
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con = sqlite3.connect(str(db))
            con.execute("CREATE TABLE usage_log(id INTEGER PRIMARY KEY, kind TEXT, doc TEXT, engine TEXT, in_tokens REAL, "
                        "out_tokens REAL, passages INTEGER, token_source TEXT)")
            for _ in range(25):
                con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, passages, token_source) VALUES"
                            "('ocr_vision', 'N', 'gemini-vision:gemini-2.5-flash', 2000, 4000, 1, 'provider')")
            con.commit(); con.close()
            pin, pout = cost_tracker._get_pricing("gemini-vision:gemini-2.5-flash")
            want = (2000 * pin + 4000 * pout) / 1e6
            self.assertAlmostEqual(rt.measured_cost_per_page(str(db), "N"), want, places=9)
            self.assertEqual(rt.measured_cost_per_page(str(Path(td) / "none.db"), "N"), rt.COST_PER_PAGE)
        r = {"state": None, "judged": {}, "untranslated": 10, "held": True, "debris_pct": 71.2, "vision_pct": 0.0, "pdfs": 546,
             "consensus": {}, "merged_complete": False, "queued": 537, "vision_pages": 268, "cost_per_page": 0.0111,
             "english": 0, "hindi": 0, "passages": 10, "quality_stuck": False}
        v, nxt, also = rt.advise(r, "N")
        self.assertIn("vision OCR on about 269 page(s), about $2.99 ($0.0111 a page)", v)
        r.update(merged_complete=True, vision_pages=537, consensus={"stale": 7}, nothing_to_lose=False, english=1333,
                 vectors=0, pictures=0, stories=0)
        v, nxt, also = rt.advise(r, "N")
        self.assertTrue(nxt.endswith("--use-repaired --replace 1333"))
        self.assertTrue(also[0].startswith("python scripts\\reingest_pages.py --doc N   (only the pages that changed"), also)

    def test_the_judge_says_how_many_meanings_are_wrong(self):
        bs = load("benchmark_reingest", SCRIPTS / "benchmark_sources.py")
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con, did = make_db(db, {1: verses("A1", "A2", "A3")})
            ids = [r[0] for r in con.execute("SELECT id FROM passages ORDER BY idx")]
            for i in ids:
                con.execute("UPDATE passages SET translation='x', text_type='mula' WHERE id=?", (i,))
            for i, f in zip(ids, (5, 2, 1)):
                con.execute("INSERT INTO mt_reviews(passage_id, lang, score_fidelity, score_fluency) VALUES(?, 'en', ?, 5)", (i, f))
            con.commit(); con.close()
            pages, facts = bs.db_reading(db, "R")
        self.assertEqual(facts["reviews"], {"n": 3, "fidelity": 2.67, "fluency": 5.0, "serious": 2})
        res = {"doc": "R", "reference": None, "lines": [], "readings": [{"label": "database", "kind": "ours", "pages": 1,
               "letters": 100, "misread_letters_pct": 0.1, "pages_misread_pct": 0.0, "noise_pct": 0.1, "plausible_pct": 93.0}],
               "translations": {"now": {"passages": 3, "english": 3, "hindi": 0, "reviews": facts["reviews"]}, "before": {}}}
        a = types_ns(verdicts=str(Path(td) / "v.jsonl"), source_desk=str(Path(td) / "sd"))
        lines = " ".join(bs.opine(res, "R", a)["lines"])
        self.assertIn("2 of them (67%) have a serious error of meaning (fidelity 2 or less", lines)
        self.assertIn(": material.", lines)

    def test_the_dashboard_steps_and_the_page(self):
        d = load("dashboard_reingest", SCRIPTS / "dashboard.py")
        got = []
        orig = d.launch
        d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            c = d.app.test_client()
            self.assertEqual(c.post("/api/repair", json={"doc": "Karan", "step": "reingest_plan"}).status_code, 200)
            self.assertEqual(c.post("/api/repair", json={"doc": "Karan", "step": "reingest", "replace": 0,
                                                         "pages": "2,8-9"}).status_code, 200)
            self.assertEqual(c.post("/api/repair", json={"doc": "Karan", "step": "reingest", "pages": "2;rm"}).status_code, 400)
            self.assertEqual(c.post("/api/repair", json={"doc": "Karan", "step": "use", "replace": 0}).status_code, 200)
        finally:
            d.launch = orig
        (k1, _, a1, m1), (k2, _, a2, m2), (k3, _, a3, _) = got
        self.assertEqual((k1, m1), ("repair", "reingest_plan")); self.assertNotIn("--apply", a1)
        self.assertTrue(any(str(x).endswith("reingest_pages.py") for x in a1)); self.assertEqual(a1[-3:], ["--doc", "Karan", "--from-dashboard"])
        self.assertEqual(k2, "repair_use"); self.assertEqual(a2[-6:], ["--from-dashboard", "--pages", "2,8-9", "--apply", "--replace", "0"])
        self.assertIn("--apply", a2); self.assertEqual(a2[a2.index("--replace") + 1], "0"); self.assertIn("2,8-9", a2)
        self.assertEqual(a3[-2:], ["--replace", "0"])
        self.assertIn("opt.replace != null", d._REPAIR_JS)
        with tempfile.TemporaryDirectory() as td:
            d.BENCH_DIR = Path(td)
            (Path(td) / "S.json").write_text(json.dumps({"doc": "S", "readings": [{"label": "tesseract", "kind": "ocr",
                "misread_letters_pct": 4.8}], "lines": [], "translations": {"now": {"passages": 2259, "english": 2230,
                "hindi": 2247, "reviews": {"n": 45, "fidelity": 4.51, "fluency": 4.8, "serious": 5}}}}))
            h = d.app.test_client().get("/benchmarks").get_data(as_text=True)
        self.assertIn("2230 of 2259 EN, 2247 HI; judged 4.51 of 5 on 45, 11% a wrong meaning", h)
        if shutil.which("node"):
            js = d._REPAIR_JS + "\nconsole.log(JSON.stringify([%s]));\n" % ", ".join("_rpNext(%s)" % json.dumps(x) for x in (
                "python scripts\\reingest_pages.py --doc K   (only the pages that changed)",
                "python scripts\\reingest_pages.py --doc K --apply --replace 12",
                "python scripts\\reingest_pages.py --doc K --pages 2,8 --apply"))
            stub = "var document={getElementById:function(){return null;}};\n"
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "n.js"; p.write_text(stub + js, encoding="utf-8")
                r = subprocess.run([shutil.which("node"), str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            a, b, c3 = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(a["step"], "reingest_plan")
            self.assertEqual((b["step"], b["replace"]), ("reingest", 12)); self.assertIn("removes 12 English", b["label"])
            self.assertEqual((c3["pages"], c3["replace"]), ("2,8", None))


class TheJudgeReview(unittest.TestCase):
    def test_the_figures_and_the_marked_passages(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con, did = make_db(db, {1: verses("A1", "A2", "A3")})
            ids = [r[0] for r in con.execute("SELECT id FROM passages ORDER BY idx")]
            for i in ids:
                con.execute("UPDATE passages SET translation='English of %d' WHERE id=?" % i, (i,))
            for i, f, why in zip(ids, (5, 2, 1), ("Accurate.", "Omits the negation 'na'.", "Sanskrit is garbled; invents meaning.")):
                con.execute("INSERT INTO mt_reviews(passage_id, lang, score_fidelity, score_fluency, comment) VALUES(?, 'en', ?, 4, ?)",
                            (i, f, why))
            con.commit(); con.close()
            before = db.read_bytes()
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "judge_review.py"), "--db", str(db)] + list(x),
                                            capture_output=True, text=True, encoding="utf-8",
                                            env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("2 (67%); 1 of them blame the Sanskrit", r.stdout)
            self.assertIn("VERDICT: 3 passage(s) judged; 2 (67%) with a wrong meaning", r.stdout)
            r = run("--doc", "R", "--html", str(Path(td) / "out" / "j.html"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Omits the negation 'na'.", r.stdout); self.assertNotIn("Accurate.", r.stdout)
            h = (Path(td) / "out" / "j.html").read_text(encoding="utf-8")
            self.assertIn("the judge blames the Sanskrit", h); self.assertIn(NAME["A2"], h); self.assertIn("Omits the negation &#x27;na&#x27;.", h)
            self.assertEqual(db.read_bytes(), before, "read-only")


def types_ns(**kw):
    import argparse
    return argparse.Namespace(**kw)


class ThePatcher(unittest.TestCase):
    FILES = ("merge_ocr_sources.py", "repair_text.py", "benchmark_sources.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_reingest_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            pat = [sys.executable, str(SCRIPTS / "patch_reingest_2026_10_12.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("reingest_pages.py (REINGEST_2026_10_12) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "reingest_pages.py", t / "scripts" / "reingest_pages.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_path_*"))   # PATH_2026_10_12 came after
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "repair_text.py"
            p.write_bytes(p.read_bytes().replace(b'LEVELS = ("cosmetic", "moderate", "material")', b'LEVELS = ()'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"REINGEST_2026_10_12", (t / "scripts" / "merge_ocr_sources.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "reingest_pages.py", SCRIPTS / "patch_reingest_2026_10_12.py", SCRIPTS / "judge_review.py",
                  Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"REINGEST_2026_10_12", b)


if __name__ == "__main__":
    unittest.main()
