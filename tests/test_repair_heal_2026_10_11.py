# -*- coding: ascii -*-
"""REPAIR_HEAL_2026_10_11: the repair path, healed after its first evening of use.
- ocr_consensus.py looks past the job that asked for the repair (it refused every "Repair the scan");
- repair_text.py judges the debris (furniture, notes, numbering, misread letters; vision agreement),
  offers "translate as is" when it is cosmetic, "accept as complete" when what is left is not Sanskrit,
  holds a text from the site after a re-ingest that replaced translations, and finds a better source;
- translate_passages.py's guard lets a text through when it is to be translated as is;
- corpus_sync.py leaves a text in repair alone, so the site keeps its last version;
- the dashboard: states in the Library, "Translate it now" after a repair, the texts with no English
  offered their translation, the Source desk, the job record's verdict in full, the Live tab's other jobs;
- source_desk.py ranks editions and fetches one, purity-gated.
Temp files only, never data/context.db, never the network."""
import http.server, importlib.util, json, os, re, shutil, socket, sqlite3, subprocess, sys, tempfile, textwrap
import threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "repair_text.py"
DEVA = "\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d \u0935\u093f\u0930\u093e\u091f\u0903 \u0927\u0930\u094d\u092e\u0903"
WATERMARK = "CC-0. Jangamwadi Math Collection. Digitized by eGangotri"
GARBLE = DEVA + " aa ON \u092f\u094b fan TAT \u0935\u093f AAT ee \u0927"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rt = load("repair_text_heal", TOOL)
sd = load("source_desk_heal", SCRIPTS / "source_desk.py")


def node():
    return shutil.which("node")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Judge(unittest.TestCase):
    def rows(self, texts, eng="tesseract", tr=False, q=0.9):
        return [(i // 3 + 1, t, eng, tr, q) for i, t in enumerate(texts)]

    def test_a_watermark_is_furniture_not_damage(self):
        rows = self.rows([DEVA + " " + WATERMARK] * 30 + [DEVA] * 30)
        j = rt.judge(rows, Path("/nonexistent"), "D", max_pages=0)
        self.assertGreater(j["furniture_pct"], 40)
        self.assertEqual(j["misread_pct"], 0.0)
        self.assertEqual(j["level"], "cosmetic")
        self.assertIn("jangamwadi", j["furniture_top"][0])

    def test_misread_letters_are_material(self):
        j = rt.judge(self.rows([GARBLE] * 20 + [DEVA] * 20), Path("/nonexistent"), "D", max_pages=0)
        self.assertEqual(j["misread_pct"], 50.0)
        self.assertEqual(j["level"], "material")
        self.assertIn("aa", j["misread_top"])

    def test_notes_and_numbering_are_not_damage(self):
        rows = self.rows([DEVA + " This line omitted in the B text"] * 5 + [DEVA + " XI"] * 5 + [DEVA] * 10)
        j = rt.judge(rows, Path("/nonexistent"), "D", max_pages=0)
        self.assertGreater(j["notes_pct"], 0); self.assertGreater(j["numbering_pct"], 0)
        self.assertEqual(j["misread_pct"], 0.0); self.assertEqual(j["level"], "cosmetic")

    def test_vision_agreement_decides_when_it_is_measured(self):
        with tempfile.TemporaryDirectory() as td:
            v = Path(td)
            for pg in range(1, 6):
                other = "\u0915\u0916\u0917 \u0918\u0919\u091a \u091b\u091c\u091d " * 12
                (v / ("D_%04d.jsonl" % pg)).write_text(json.dumps({"text": other}) + "\n", encoding="utf-8")
            rows = [(pg, DEVA * 4, "tesseract", False, 0.9) for pg in range(1, 6)]
            j = rt.judge(rows, v, "D", max_pages=40)
            self.assertEqual(j["agree_pages"], 5)
            self.assertLess(j["agree_median"], 0.9)
            self.assertEqual(j["level"], "material", "the text itself differs from vision, though no Latin is in it")

    def test_leftovers_that_are_not_sanskrit(self):
        rows = [(1, "\u092a\u093d \u090f\u092a1197\u096c\u0924 2004 \u00a9 [\u0924\u094d", "t", False, 0.2),
                (2, "\u0965", "t", False, 0.1), (3, "Index of the verses and words", "t", False, 0.2),
                (4, DEVA, "t", True, 0.9)]
        lo = rt.leftovers(rows)
        self.assertEqual((lo["below"], lo["misread_english"], lo["punctuation"], lo["latin"]), (3, 1, 1, 1))


STUB_CONSENSUS = r'''
import json, os, sys, pathlib
a = sys.argv[1:]
doc = a[a.index("--doc") + 1]
pathlib.Path("calls.txt").open("a").write("ocr_consensus self=%%s %%s\n" %% (os.environ.get("SA_CONSENSUS_SELF_KIND", ""), " ".join(a)))
if os.environ.get("STUB_REFUSE"):
    print("  REFUSING: stop them first (a running ingest/translate reads these files)."); sys.exit(1)
if "--drift-only" in a:
    sys.exit(0)
for d in ("data/raw_vision", "data/raw_merged"):
    pathlib.Path(d).mkdir(parents=True, exist_ok=True)
for pg in ("0001", "0002"):
    rec = {"page": int(pg), "text": %r, "engine": "gemini-vision:gemini-2.5-flash"}
    for d in ("data/raw_vision", "data/raw_merged"):
        pathlib.Path(d, "%%s_%%s.jsonl" %% (doc, pg)).write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
pathlib.Path("data/ocr_consensus").mkdir(parents=True, exist_ok=True)
pathlib.Path("data/ocr_consensus/%%s.json" %% doc).write_text(json.dumps({"summary": {"current": 0, "stale": 2, "missing-in-db": 0}, "at": "2026-10-11T17:00:00"}))
sys.exit(3)
''' % DEVA
STUBS = {
    "ocr_consensus.py": STUB_CONSENSUS,
    "db_backup.py": "import sqlite3, sys, pathlib\ns = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()\n",
    "wipe_doc.py": ("import sqlite3, sys\na = sys.argv[1:]\ncon = sqlite3.connect(a[a.index('--db') + 1])\n"
                    "con.execute('DELETE FROM passages WHERE doc_id=(SELECT id FROM docs WHERE code=?)', (a[a.index('--doc') + 1],)); con.commit()\n"),
    "ingest_jsonl_fast.py": ("import glob, json, sqlite3, sys\na = sys.argv[1:]\ncon = sqlite3.connect(a[a.index('--db') + 1]); doc = a[a.index('--doc') + 1]\n"
                             "did = con.execute('SELECT id FROM docs WHERE code=?', (doc,)).fetchone()[0]\n"
                             "for p in sorted(glob.glob('data/raw_merged/%s_*.jsonl' % doc)):\n"
                             "    r = json.loads(open(p, encoding='utf-8').readline())\n"
                             "    con.execute('INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) VALUES(?,?,?,?,?,?,?,?)', (did, r['page'], 1, r['text'], '', 'mula', 0.9, r['engine']))\n"
                             "con.commit()\n"),
    "classify_doc.py": "pass\n",
    "source_desk.py": "import sys\nprint('VERDICT: 3 candidate(s); the best is stub (' + ' '.join(sys.argv[1:]) + ')')\nprint('NEXT: open the Source desk')\n",
}


class Path_(unittest.TestCase):
    """repair_text.py end to end on a temp tree, with stand-ins for the steps it runs."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        (t / "stubs").mkdir()
        for name, code in STUBS.items():
            (t / "stubs" / name).write_text(code, encoding="utf-8")
        for d in ("inbox", "data/raw", "backups"):
            (t / d).mkdir(parents=True)
        self.db = t / "data" / "context.db"
        con = sqlite3.connect(self.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT,"
            " text_type TEXT, quality_score REAL, ocr_engine TEXT);"
            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);")
        # W: watermark only (cosmetic); G: misread (material, with translations); Q: leftovers not Sanskrit
        con.executemany("INSERT INTO docs VALUES(?,?)", [(1, "W"), (2, "G"), (3, "Q")])
        for pg in range(1, 7):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(1,?,1,?,'','mula',0.9,'tesseract')", (pg, DEVA + " " + WATERMARK))
        for pg in (1, 2):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(2,?,1,?,'an English line','mula',0.9,'tesseract')", (pg, GARBLE))
        con.execute("INSERT INTO translations_l10n SELECT id,'hi','h' FROM passages WHERE doc_id=2")
        con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                    "VALUES(3,1,1,?,'done','mula',0.9,'tesseract')", (DEVA,))
        for pg, txt in ((2, "\u0965"), (3, "Index of the verses and words of the text")):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(3,?,1,?,'','mula',0.1,'tesseract')", (pg, txt))
        con.commit(); con.close()
        for doc, n in (("W", 6), ("G", 2)):
            for pg in range(1, n + 1):
                (t / "inbox" / ("%s_%04d.pdf" % (doc, pg))).write_bytes(b"%PDF")
                (t / "data" / "raw" / ("%s_%04d.jsonl" % (doc, pg))).write_text("{}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args, url=None, **extra):
        env = dict(os.environ, SA_REPAIR_SCRIPTS=str(self.t / "stubs"), SA_BACKUP_DIR=str(self.t / "backups"),
                   SA_DASHBOARD_URL=url or "http://127.0.0.1:%d" % free_port(), PYTHONIOENCODING="utf-8", **extra)
        t = self.t
        base = ["--db", str(self.db), "--inbox", str(t / "inbox"), "--raw", str(t / "data/raw"),
                "--vision-dir", str(t / "data/raw_vision"), "--merged-dir", str(t / "data/raw_merged"),
                "--work", str(t / "data/ocr_consensus"), "--verdicts", str(t / "data/source_verdicts.jsonl")]
        code = ("import sys; import importlib.util as u; s=u.spec_from_file_location('rt', %r); m=u.module_from_spec(s); "
                "s.loader.exec_module(m); m.ROOT=__import__('pathlib').Path(%r); sys.exit(m.main(%r))"
                % (str(TOOL), str(t), base + list(args)))
        r = subprocess.run([sys.executable, "-c", code], cwd=str(t), capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def line(self, out, key, last=True):
        ls = [l[len(key) + 1:].strip() for l in out.splitlines() if l.startswith(key + ":")]
        return (ls[-1] if last else ls) if ls else ("" if last else [])

    def calls(self):
        p = self.t / "calls.txt"
        return p.read_text().splitlines() if p.exists() else []

    def test_cosmetic_debris_is_translated_as_is(self):
        rc, out = self.tool("--doc", "W")
        self.assertEqual(rc, 0, out)
        self.assertIn("held by the OCR-debris guard", self.line(out, "VERDICT"))
        self.assertIn("the debris is cosmetic", self.line(out, "VERDICT"))
        self.assertTrue(self.line(out, "JUDGED").startswith("cosmetic"), out)
        self.assertIn('--as-is "debris judged cosmetic"', self.line(out, "NEXT"))
        self.assertIn("--repair", " ".join(self.line(out, "ALSO", last=False)))
        rc, out = self.tool("--doc", "W", "--as-is", "debris judged cosmetic")
        self.assertIn("translated as is", self.line(out, "VERDICT"))
        rc, out = self.tool("--doc", "W")
        self.assertIn("to be translated as is", self.line(out, "VERDICT"))
        self.assertIn("Finish EN", self.line(out, "NEXT"))
        # the guard reads the same register
        import translate_passages as tp
        os.environ["SA_SOURCE_VERDICTS"] = str(self.t / "data/source_verdicts.jsonl")
        try:
            con = sqlite3.connect(self.db)
            con.execute("ATTACH ':memory:' AS x")
            self.assertIsNone(tp._debris_guard(con, "W", 30.0, inbox=self.t / "inbox"), "let through")
            self.assertIsNotNone(tp._debris_guard(con, "G", 30.0, inbox=self.t / "inbox"), "G is still held")
            con.close()
        finally:
            os.environ.pop("SA_SOURCE_VERDICTS", None)

    def test_the_repair_names_itself_to_ocr_consensus(self):
        rc, out = self.tool("--doc", "G", "--repair")
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.calls()[0].startswith("ocr_consensus self=repair "), self.calls())
        rc, out = self.tool("--doc", "W", "--repair", STUB_REFUSE="1")
        self.assertEqual(rc, 1)
        self.assertIn("REPAIR_HEAL_2026_10_11", self.line(out, "VERDICT"))

    def test_a_reingest_that_replaces_translations_holds_the_text_from_the_site(self):
        self.tool("--doc", "G", "--repair")
        rc, out = self.tool("--doc", "G", "--use-repaired", "--replace", "2")
        self.assertEqual(rc, 0, out)
        self.assertIn("the site keeps its last version", self.line(out, "VERDICT"))
        self.assertIn("--release", " ".join(self.line(out, "ALSO", last=False)))
        recs = [json.loads(l) for l in (self.t / "data/source_verdicts.jsonl").read_text().splitlines()]
        self.assertEqual(recs[-1]["status"], "in_repair"); self.assertEqual((recs[-1]["en_before"], recs[-1]["hi_before"]), (2, 2))
        self.assertIn("self=repair,repair_use", [c for c in self.calls() if "--drift-only" in c][0])
        rc, out = self.tool("--doc", "G")
        self.assertIn("in repair since", self.line(out, "VERDICT")); self.assertIn("Finish EN", self.line(out, "NEXT"))
        self.assertIn("--release", " ".join(self.line(out, "ALSO", last=False)))
        rc, out = self.tool("--doc", "G", "--release")   # JUDGE_DESK_2026_10_11: not before the translation is back
        self.assertEqual(rc, 1); self.assertIn("still in repair", self.line(out, "VERDICT"))
        rc, out = self.tool("--doc", "G", "--release", "--force")
        self.assertIn("published", self.line(out, "VERDICT"))
        rc, out = self.tool("--doc", "G")
        self.assertIn("nothing holds it", self.line(out, "VERDICT"))

    def test_hold_by_hand_records_what_the_site_has(self):
        rc, out = self.tool("--doc", "G", "--hold")
        self.assertIn("held from the site", self.line(out, "VERDICT"))
        rec = json.loads((self.t / "data/source_verdicts.jsonl").read_text().splitlines()[-1])
        self.assertEqual((rec["status"], rec["en_before"], rec["hi_before"]), ("in_repair", 2, 2))
        rc, out = self.tool("--list")
        self.assertIn("in_repair", out); self.assertIn("1 text(s) not in the ordinary state", out)

    def test_not_while_this_text_is_being_repaired(self):
        self.tool("--doc", "G", "--repair")
        jobs = {"running": [{"kind": "repair", "mode": "repair", "doc": "G", "state": "running"}]}

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(jobs).encode())

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = "http://127.0.0.1:%d" % srv.server_address[1]
            rc, out = self.tool("--doc", "G", "--use-repaired", "--replace", "2", "--from-dashboard", url=url)
            self.assertEqual(rc, 1); self.assertIn("a vision repair of this text: repair G", out)
            jobs["running"][0]["mode"] = "assess"
            rc, out = self.tool("--doc", "G", "--use-repaired", "--replace", "2", "--from-dashboard", url=url)
            self.assertEqual(rc, 0, "an assessment is no writer: " + out)
        finally:
            srv.shutdown()

    def test_what_is_left_is_not_sanskrit(self):
        rc, out = self.tool("--doc", "Q")
        self.assertIn("what is left is not Sanskrit", self.line(out, "VERDICT"), out)
        self.assertIn('--accept "what is left is not Sanskrit"', self.line(out, "NEXT"))
        self.tool("--doc", "Q", "--accept", "what is left is not Sanskrit")
        rc, out = self.tool("--doc", "Q")
        self.assertIn("accepted as complete", self.line(out, "VERDICT"))
        self.tool("--doc", "Q", "--restore")
        rc, out = self.tool("--doc", "Q")
        self.assertIn("what is left is not Sanskrit", self.line(out, "VERDICT"))

    def test_find_a_better_source(self):
        rc, out = self.tool("--doc", "G", "--find-source", "--ai")
        self.assertEqual(rc, 0, out)
        self.assertIn("--doc G", self.line(out, "VERDICT")); self.assertIn("--ai", self.line(out, "VERDICT"))


class Consensus(unittest.TestCase):
    def test_dashboard_jobs_looks_past_the_named_kinds(self):
        oc = load("ocr_consensus_heal", SCRIPTS / "ocr_consensus.py")
        body = json.dumps({"running": [{"kind": "repair", "doc": "K", "state": "running"},
                                       {"kind": "translate", "doc": "K", "state": "queued"},
                                       {"kind": "repair", "doc": "Z", "state": "running"}]}).encode()

        class R:
            def read(self):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class O:
            def open(self, url, timeout=2):
                return R()
        orig = oc.urllib.request.build_opener
        oc.urllib.request.build_opener = lambda *a: O()
        try:
            self.assertEqual([j["kind"] for j in oc.dashboard_jobs("K")], ["repair", "translate"])
            os.environ["SA_CONSENSUS_SELF_KIND"] = "repair"
            self.assertEqual([j["kind"] for j in oc.dashboard_jobs("K")], ["translate"])
        finally:
            oc.urllib.request.build_opener = orig
            os.environ.pop("SA_CONSENSUS_SELF_KIND", None)


ct = load("test_corpus_sync_for_heal", REPO / "tests" / "test_corpus_sync_2026_10_08.py")


class SyncHold(ct.Base):
    def test_a_text_in_repair_is_left_alone(self):
        s1 = self.sync()
        self.assertEqual(s1["verified"]["groups_different"], 0)
        reg = Path(self.tmp.name) / "source_verdicts.jsonl"
        reg.write_text(json.dumps({"doc": "markandeya_purana", "status": "in_repair"}) + "\n", encoding="utf-8")
        os.environ["SA_SOURCE_VERDICTS"] = str(reg)
        try:
            con = self.rw()
            con.execute("UPDATE passages SET translation=NULL WHERE doc_id=1")   # the re-ingest emptied it
            con.commit()
            s2 = self.sync()
            self.assertEqual(s2["tables"]["passages"]["upsert"], 0, "nothing of it is sent")
            self.assertTrue(any("markandeya_purana: in repair" in h for h in s2["held"]), s2["held"])
            self.assertEqual(s2["verified"]["groups_different"], 0)
            with open(reg, "a", encoding="utf-8") as f:
                f.write(json.dumps({"doc": "markandeya_purana", "status": "released"}) + "\n")
            s3 = self.sync()
            self.assertGreater(s3["tables"]["passages"]["upsert"], 0, "released: it is sent")
        finally:
            os.environ.pop("SA_SOURCE_VERDICTS", None)


def load_dashboard():
    return load("dashboard_repair_heal", SCRIPTS / "dashboard.py")


def rec(kind, doc, ok, rc, tail, t, **kw):
    r = {"id": "j%d" % t, "kind": kind, "doc": doc, "start": t, "end": t + 1, "ok": ok, "rc": rc,
         "duration_s": 1.0, "out_lines": 3, "err_preview": "", "out_tail": tail}
    r.update(kw)
    return r


HELD = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc %s "
        "--threshold 101 --include-unassessed\r\n  Translate anyway: add --allow-debris (dashboard: set SA_ALLOW_DEBRIS=1).\r\n")


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.d.SOURCE_DESK_DIR = t / "source_desk"
        cls.c = cls.d.app.test_client()
        cls.db = str(t / "context.db")
        con = sqlite3.connect(cls.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
            " translation TEXT, translation_qa REAL, text_type TEXT);"
            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);")
        # Karan: repaired, no English now; AsIs: held then as-is; Done: complete; Hold: in repair; Aside: set aside
        for i, code in enumerate(["Karan", "AsIs", "Done", "Hold", "Aside"], 1):
            con.execute("INSERT INTO docs VALUES(?,?,?)", (i, code, "agama"))
            for k in range(4):
                tr = "" if code in ("Karan", "Aside") or k >= 2 else "x"
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation) VALUES(?,?,?,?,?)", (i, 1, k, "s", tr))
        con.commit(); con.close()
        jobs = [rec("translate", "Karan", False, 3, HELD % "Karan", 100),
                rec("repair_use", "Karan", True, 0, "...", 200, mode="use",
                    verdict="the repaired text is in the database; backup D:\\backups\\x.db"),
                rec("translate", "AsIs", False, 3, HELD % "AsIs", 300),
                rec("translate", "Done", True, 0, "Done. 1/180 translated | 180 quality-skipped | 0 errors", 400),
                rec("translate", "Aside", False, 3, HELD % "Aside", 500)]
        cls.d.JOBS_LOG_PATH.write_text("".join(json.dumps(r) + "\n" for r in jobs), encoding="utf-8")
        st = lambda doc, s, **kw: json.dumps(dict({"doc": doc, "status": s, "reason": "why " + doc, "at": "2026-10-11T19:00:00"}, **kw))
        (t / "source_verdicts.jsonl").write_text("\n".join([
            st("AsIs", "translate_as_is"), st("Done", "complete"), st("Hold", "in_repair", en_before=1603, hi_before=1425),
            st("Aside", "set_aside")]) + "\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.launched = []
        self._launch = self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (self.launched.append((kind, doc, argv, mode)) or "jid1")

    def tearDown(self):
        self.d.launch = self._launch

    def library(self):
        r = self.c.get("/library?db=" + self.db)
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def card(self, h, code):
        m = re.search(r'<div class="card-wrap" data-doc="%s">(.*?)<div class="bsacts"' % code, h, re.S)
        self.assertIsNotNone(m, code)
        return m.group(1)

    def test_a_repaired_text_is_offered_its_translation(self):
        n = self.d._library_notes()
        self.assertEqual([x["kind"] for x in n["Karan"]], ["repaired"], "the hold before the repair is gone")
        h = self.library()
        i = h.index("Not yet readable")
        tail = h[i:]
        self.assertIn('id="rp-Karan"', tail)
        self.assertIn("Translate it now: English, then Hindi", tail)
        self.assertIn("translateRest(this.dataset.doc,&#39;en&#39;,this)", tail, "Finish EN on a card with no English")
        self.assertNotIn("English held", tail[:tail.index("Aside") if "Aside" in tail else None])

    def test_the_states_change_the_cards(self):
        h = self.library()
        a = self.card(h, "AsIs")
        self.assertIn("To be translated as is", a); self.assertNotIn("English held", a)
        d = self.card(h, "Done")
        self.assertIn("Accepted as complete", d); self.assertNotIn("1 of 180", d)
        hd = self.card(h, "Hold")
        self.assertIn("In repair since 2026-10-11", hd); self.assertIn("1603 English", hd)
        self.assertIn("Publish it to the site", hd)
        tail = h[h.index("Not yet readable"):]
        self.assertIn("Set aside on 2026-10-11", tail); self.assertIn(">Restore</button>", tail)
        self.assertIn("Find a better source", tail)

    def test_the_new_steps(self):
        cases = [
            ({"step": "as_is"}, ["--as-is", "debris judged cosmetic"]),
            ({"step": "as_is", "reason": "watermark only"}, ["--as-is", "watermark only"]),
            ({"step": "accept"}, ["--accept", "what is left is not Sanskrit"]),
            ({"step": "hold"}, ["--hold", "re-translating after the repair"]),
            ({"step": "release"}, ["--release"]),
            ({"step": "find"}, ["--find-source"]),
            ({"step": "find", "ai": True}, ["--find-source", "--ai"]),
        ]
        for body, tail in cases:
            self.launched.clear()
            r = self.c.post("/api/repair", json=dict(body, doc="Karan"))
            self.assertEqual(r.status_code, 200, body)
            kind, doc, argv, mode = self.launched[0]
            self.assertEqual((kind, mode), ("repair", body["step"]))
            self.assertEqual(argv[-len(tail):], tail, body)
        self.launched.clear()
        r = self.c.post("/api/repair", json={"doc": "Karan", "step": "fetch", "identifier": "in.ernet.dli.2015.1", "kind": "pdf"})
        self.assertEqual(r.status_code, 200)
        argv = self.launched[0][2]
        self.assertTrue(argv[[i for i, x in enumerate(argv) if x.endswith("source_desk.py")][0] + 1:] ==
                        ["--doc", "Karan", "--fetch", "in.ernet.dli.2015.1", "--kind", "pdf"], argv)
        for bad in ({"identifier": "../x", "kind": "pdf"}, {"identifier": "a b", "kind": "pdf"}, {"identifier": "ok", "kind": "exe"}):
            self.assertEqual(self.c.post("/api/repair", json=dict(bad, doc="Karan", step="fetch")).status_code, 400, bad)

    def test_sources_endpoint(self):
        self.assertTrue(self.c.get("/api/repair/sources?doc=Karan").get_json()["missing"])
        self.d.SOURCE_DESK_DIR.mkdir(parents=True, exist_ok=True)
        (self.d.SOURCE_DESK_DIR / "Karan.json").write_text(json.dumps({"doc": "Karan", "candidates": [{"identifier": "x"}]}))
        self.assertEqual(self.c.get("/api/repair/sources?doc=Karan").get_json()["candidates"][0]["identifier"], "x")
        self.assertEqual(self.c.get("/api/repair/sources?doc=../x").status_code, 400)

    def test_the_repair_page_has_the_source_desk(self):
        h = self.c.get("/repair/Karan?db=" + self.db).get_data(as_text=True)
        for s in ('id="rpjudge-Karan"', 'id="srclist-Karan"', 'id="srcai-Karan"', "_rpSources('Karan');",
                  "Translate it now: English, then Hindi", "Source desk"):
            self.assertIn(s, h)
        self.assertNotIn("__", h.replace("__name__", ""))
        a = self.c.get("/repair/Aside?db=" + self.db).get_data(as_text=True)
        self.assertEqual(a.count('class="repairbar"'), 1, "one bar on a set-aside text's page")
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "page.js"; p.write_text(js, encoding="utf-8")
            r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_script_reads_every_next_step(self):
        if not node():
            self.skipTest("node is not installed")
        js = self.d._REPAIR_JS
        q = "python scripts\\repair_text.py --doc K"
        cases = [
            (q + ' --as-is "debris judged cosmetic"', {"step": "as_is", "reason": "debris judged cosmetic"}),
            (q + ' --accept "what is left is not Sanskrit"', {"step": "accept", "reason": "what is left is not Sanskrit"}),
            (q + " --release   (publish it to the site when translated)", {"step": "release"}),
            (q + " --find-source", {"step": "find"}),
            (q + " --repair   (for the critical edition)", {"step": "repair", "max_usd": 1}),
            ("translate it: Finish EN and Add Hindi in the Library", {"step": "translate"}),
            (q + " --use-repaired --replace 1603", {"step": "use", "replace": 1603}),
        ]
        out = ("JUDGED: cosmetic: misread letters in 0% of verses\nVERDICT: held, but cosmetic\nNEXT: " + cases[0][0]
               + "\nALSO: " + q + " --repair\nDone. 5/7 translated | 2 quality-skipped | 0 errors\n")
        prog = ("var document={getElementById:function(){return null;}};\n" + js +
                "\nconst C=" + json.dumps(cases) + ";\nfor (const [n, want] of C){ const s=_rpNext(n);"
                " for (const k in want){ if (s[k]!==want[k]){ console.log(n+': '+k+' '+s[k]); process.exit(1);} } }\n"
                "const v=_rpVerdict(" + json.dumps(out) + ");\n"
                "if (v.judged.indexOf('cosmetic')!==0 || v.also.length!==1 || _rpNext(v.also[0]).step!=='repair' "
                "|| v.done[0]!=='5 of 7 translated, 2 below the OCR bar'){ console.log(JSON.stringify(v)); process.exit(1);}\n")
        p = self.t / "next.js"; p.write_text(prog, encoding="utf-8")
        r = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_jobs_running_says_the_mode_and_the_record_keeps_the_verdict(self):
        d = self.d
        self.d.launch = self._launch
        cmd = [sys.executable, "-c", "print('x'*900); print('VERDICT: the long verdict ' + 'y'*300); print('NEXT: do this')"]
        jid = d.launch("repair", "ModeT", [sys.executable, "-c", "import time; time.sleep(1.5)"], mode="assess")
        r = self.c.get("/api/jobs/running").get_json()
        self.assertIn("assess", [j.get("mode") for j in r["running"] if j["id"] == jid])
        j2 = d.launch("repair", "VerdT", cmd, mode="find")
        t0 = time.time()
        while d.JOBS[j2].ok is None and time.time() - t0 < 15:
            time.sleep(0.05)
        recs = [json.loads(l) for l in d.JOBS_LOG_PATH.read_text(encoding="utf-8").splitlines() if '"VerdT"' in l]
        self.assertTrue(recs[-1]["verdict"].startswith("the long verdict yyy")); self.assertEqual(recs[-1]["next"], "do this")
        self.assertNotIn("VERDICT", recs[-1]["out_tail"][:5])
        t0 = time.time()
        while d.JOBS[jid].ok is None and time.time() - t0 < 15:
            time.sleep(0.05)


class Page(unittest.TestCase):
    def test_the_dashboard_page(self):
        h = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        for s in ("REPAIR_HEAL_2026_10_11", "async function _liveOthers()", "_liveOthers();",
                  "(r.verdict ? '\\nVERDICT: ' + r.verdict : '')", "setInterval(watchFinished, 8000);"):
            self.assertIn(s, h)
        if node():
            js = "\n".join(re.findall(r"<script>(.*?)</script>", h, re.S))
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "p.js"; p.write_text(js, encoding="utf-8")
                r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)


class SourceDesk(unittest.TestCase):
    def test_words_from_the_code(self):
        self.assertEqual(sd.title_words("2015_368408_Natyasastra-With"), ["natyasastra"])
        self.assertEqual(sd.title_words("Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi")[:2],
                         ["karan", "aagama"])
        self.assertEqual(sd.scan_numbers("2015_368408_Natyasastra-With"), ["368408"])
        self.assertEqual(sd.norm("N\u0101\u1e6dya\u015b\u0101stra"), sd.norm("Natyashastra"))

    def test_the_ranking(self):
        words, nums = ["natyasastra"], ["368408"]
        crit = {"identifier": "NatyaShastraBORI", "title": "Natyasastra of Bharatamuni, critical edition",
                "publisher": "Oriental Institute, Baroda (Gaekwad's Oriental Series)", "language": "san", "imagecount": 600,
                "downloads": 900, "purity": 0.93}
        pop = {"identifier": "natya-hindi", "title": "Natyashastra (Hindi)", "language": "hin", "imagecount": 80}
        have = {"identifier": "in.ernet.dli.2015.368408", "title": "Natyasastra With Abhinavabharati", "language": "san"}
        s = {c["identifier"]: sd.score(c, words, nums) for c in (crit, pop, have)}
        self.assertGreater(s["NatyaShastraBORI"][0], s["natya-hindi"][0])
        self.assertIn("says critical edition", s["NatyaShastraBORI"][1])
        self.assertIn("the scan you have", s["in.ernet.dli.2015.368408"][1]); self.assertTrue(have["current_scan"])
        self.assertLess(s["in.ernet.dli.2015.368408"][0], s["NatyaShastraBORI"][0])

    def test_find_writes_the_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            arch = t / "wl" / "pages" / "p1"; arch.mkdir(parents=True)
            (arch / "meta.json").write_text(json.dumps({"url": "https://www.wisdomlib.org/hinduism/book/natyashastra/d/doc1.html",
                                                        "title": "Natyashastra (English)"}))
            orig = (sd.archive_search, sd.analyse_top, sd.WISDOMLIB_ARCHIVE)
            sd.archive_search = lambda words, rows: [
                {"identifier": "in.ernet.dli.2015.368408", "title": "Natyasastra", "language": "san"},
                {"identifier": "natyaGOS", "title": "Natyasastra critical edition", "language": "san", "imagecount": 500}]
            sd.analyse_top = lambda cands, errors: [c.update(pdf_url="https://x/y.pdf", pdf_mb=40.0) for c in cands[:1]]
            sd.WISDOMLIB_ARCHIVE = t / "wl"
            try:
                out = t / "desk"
                import io, contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = sd.main(["--doc", "2015_368408_Natyasastra-With", "--db", str(t / "none.db"), "--out", str(out)])
                self.assertEqual(rc, 0)
                d = json.loads((out / "2015_368408_Natyasastra-With.json").read_text())
                self.assertEqual(d["candidates"][0]["identifier"], "natyaGOS")
                self.assertTrue(d["candidates"][1]["current_scan"])
                self.assertEqual(d["candidates"][0]["embed_url"], "https://archive.org/embed/natyaGOS")
                self.assertEqual(d["wisdomlib_local"][0]["book"], "natyashastra")
                self.assertTrue(any("GRETIL" in l["name"] for l in d["links"]))
                self.assertIn("VERDICT: 2 candidate(s); the best is Natyasastra critical edition", buf.getvalue())
            finally:
                sd.archive_search, sd.analyse_top, sd.WISDOMLIB_ARCHIVE = orig

    def test_fetch_refuses_an_impure_text(self):
        import archive_source_finder as asf
        with tempfile.TemporaryDirectory() as td:
            orig = (asf.analyse, sd._http)
            asf.analyse = lambda ident: {"txt_url": "https://x/t.txt", "pdf_url": None, "title": "t"}
            sd._http = lambda url, timeout=40, rng=None: ("Latin text " * 50).encode()
            try:
                import io, contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = sd.main(["--doc", "D", "--fetch", "someid", "--kind", "text", "--dest", td])
                self.assertEqual(rc, 1); self.assertIn("refused", buf.getvalue())
                self.assertEqual(os.listdir(td), [])
                with contextlib.redirect_stdout(buf):
                    rc = sd.main(["--doc", "D", "--fetch", "someid", "--kind", "pdf", "--dest", td])
                self.assertEqual(rc, 1); self.assertIn("has no PDF", buf.getvalue())
                self.assertEqual(sd.main(["--doc", "D", "--fetch", "../x", "--dest", td]), 2)
            finally:
                asf.analyse, sd._http = orig

    def test_ascii_and_marks(self):
        for p, m in ((SCRIPTS / "source_desk.py", b"SOURCE_DESK_2026_10_11"), (TOOL, b"REPAIR_HEAL_2026_10_11"),
                     (SCRIPTS / "patch_repair_heal_2026_10_11.py", b"REPAIR_HEAL_2026_10_11")):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(m, b)


class ThePatcher(unittest.TestCase):
    FILES = ("dashboard.py", "dashboard_static.html", "ocr_consensus.py", "translate_passages.py", "corpus_sync.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_repairheal_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            for f in ("repair_text.py", "source_desk.py"):
                shutil.copy2(SCRIPTS / f, t / "scripts" / f)
            pat = [sys.executable, str(SCRIPTS / "patch_repair_heal_2026_10_11.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                # the patches that came after, in order: the first later backup of a file is this patch's result
                later = []
                for tag in ("judgedesk", "etextwitness", "benchmark", "quality", "reingest", "path", "scholar"):
                    later = later or sorted(SCRIPTS.glob(f + ".bak_%s_*" % tag))
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            # a REPAIR_PATH block that is not the released one is not replaced, and nothing is written
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b"_REPAIR_MAX_USD = 5.0", b"_REPAIR_MAX_USD = 6.0"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("not the one released", r.stdout)
            self.assertNotIn(b"REPAIR_HEAL", (t / "scripts" / "ocr_consensus.py").read_bytes(), "all or nothing")


if __name__ == "__main__":
    unittest.main()
