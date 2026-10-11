# -*- coding: ascii -*-
"""JUDGE_DESK_2026_10_11: the debris judged, shown where it is needed. repair_text.py caches each
assessment (data/source_judged/<doc>.json) and --judge-all judges every text that needs it; --release
waits for the translation; the Library's cards and the repair page show the judgement; /sources lists
every text whose scan stops its translation with the best edition found. Temp files only."""
import importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "repair_text.py"
DEVA = "\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d \u0935\u093f\u0930\u093e\u091f\u0903 \u0927\u0930\u094d\u092e\u0903"
GARBLE = DEVA + " aa ON \u092f\u094b fan TAT \u0935\u093f AAT ee \u0927"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def node():
    return shutil.which("node")


class Tool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        for d in ("inbox", "data/raw"):
            (t / d).mkdir(parents=True)
        self.db = t / "data" / "context.db"
        con = sqlite3.connect(self.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT,"
            " text_type TEXT, quality_score REAL, ocr_engine TEXT);")
        con.executemany("INSERT INTO docs VALUES(?,?)", [(1, "M"), (2, "Done"), (3, "R-RETIRED")])
        for pg in range(1, 5):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(1,?,1,?,'','mula',0.9,'tesseract')", (pg, GARBLE))
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(2,?,1,?,'done','mula',0.9,'tesseract')", (pg, DEVA))
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                        "VALUES(3,?,1,?,'','mula',0.9,'tesseract')", (pg, GARBLE))
            (t / "inbox" / ("M_%04d.pdf" % pg)).write_bytes(b"%PDF")
        con.commit(); con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args):
        t = self.t
        base = ["--db", str(self.db), "--inbox", str(t / "inbox"), "--raw", str(t / "data/raw"),
                "--vision-dir", str(t / "data/raw_vision"), "--merged-dir", str(t / "data/raw_merged"),
                "--work", str(t / "data/ocr_consensus"), "--verdicts", str(t / "data/source_verdicts.jsonl"),
                "--judged-dir", str(t / "data/source_judged")]
        code = ("import sys; import importlib.util as u; s=u.spec_from_file_location('rt', %r); m=u.module_from_spec(s); "
                "s.loader.exec_module(m); m.ROOT=__import__('pathlib').Path(%r); sys.exit(m.main(%r))"
                % (str(TOOL), str(t), base + list(args)))
        env = dict(os.environ, SA_DASHBOARD_URL="http://127.0.0.1:9", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(t), capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_an_assessment_is_cached(self):
        rc, out = self.tool("--doc", "M")
        self.assertEqual(rc, 0, out)
        j = json.loads((self.t / "data/source_judged/M.json").read_text(encoding="utf-8"))
        self.assertEqual(j["level"], "material"); self.assertTrue(j["held"])
        self.assertIn("--repair", j["next"]); self.assertTrue(j["judged"].startswith("material"))
        self.assertEqual(j["mark"], "JUDGE_DESK_2026_10_11")

    def test_judge_all(self):
        (self.t / "data").mkdir(exist_ok=True)
        (self.t / "data/source_verdicts.jsonl").write_text(json.dumps({"doc": "Done", "status": "complete"}) + "\n")
        rc, out = self.tool("--judge-all")
        self.assertEqual(rc, 0, out)
        self.assertIn("judged 2 text(s)", out); self.assertIn("1 material", out); self.assertIn("1 held by the guard", out)
        self.assertEqual(sorted(p.name for p in (self.t / "data/source_judged").glob("*.json")), ["Done.json", "M.json"],
                         "a retired text is left out; a text in the register is judged though it is translated")

    def test_release_waits_for_the_translation(self):
        rc, out = self.tool("--doc", "M", "--hold")
        rec = json.loads((self.t / "data/source_verdicts.jsonl").read_text().splitlines()[-1])
        self.assertEqual((rec["en_before"], rec["hi_before"]), (0, 0))
        rc, out = self.tool("--doc", "M", "--release")
        self.assertEqual(rc, 1); self.assertIn("not yet: English 0 of 4", out)
        rc, out = self.tool("--doc", "M", "--release", "--force")
        self.assertEqual(rc, 0); self.assertIn("published", out)


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load("dashboard_judge_desk", SCRIPTS / "dashboard.py")
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
        for i, code in enumerate(["Mat", "Cos", "Zero"], 1):
            con.execute("INSERT INTO docs VALUES(?,?,?)", (i, code, "agama"))
            for k in range(4):
                tr = "" if code == "Zero" or k >= 2 else "x"
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation) VALUES(?,?,?,?,?)", (i, 1, k, "s", tr))
        con.commit(); con.close()
        held = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py "
                "--doc %s --threshold 101 --include-unassessed\r\n")
        recs = [{"id": "j%d" % i, "kind": "translate", "doc": d, "start": i, "end": i + 1, "ok": False, "rc": 3,
                 "out_tail": held % d, "err_preview": ""} for i, d in enumerate(["Mat", "Zero"], 1)]
        cls.d.JOBS_LOG_PATH.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
        jd = t / "source_judged"; jd.mkdir()
        base = {"at": "2026-10-11T20:00:00", "passages": 4, "english": 2, "hindi": 0, "guard": True, "held": True,
                "debris_pct": 60.0, "verdict": "held by the OCR-debris guard; the scan can be repaired",
                "next": "python scripts\\repair_text.py --doc X --repair   (capped at --max-usd 1.00)"}
        (jd / "Mat.json").write_text(json.dumps(dict(base, doc="Mat", level="material", misread_pct=50.0, agree_median=0.777,
                                                     agree_pages=37, judged="material: misread letters in 50% of verses")))
        (jd / "Cos.json").write_text(json.dumps(dict(base, doc="Cos", level="cosmetic", misread_pct=2.0, held=False, guard=False,
                                                     debris_pct=3.0, verdict="nothing holds it", next="")))
        (jd / "Zero.json").write_text(json.dumps(dict(base, doc="Zero", level="moderate", misread_pct=12.0, english=0)))
        (jd / "bad.json").write_text("{not json")
        cls.d.SOURCE_DESK_DIR.mkdir()
        (cls.d.SOURCE_DESK_DIR / "Mat.json").write_text(json.dumps({"doc": "Mat", "candidates": [
            {"identifier": "in.ernet.dli.1", "title": "the one you have", "current_scan": True, "score": 10},
            {"identifier": "crit", "title": "Mat critical edition", "score": 71, "why": ["says critical edition"],
             "details_url": "https://archive.org/details/crit"}]}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_judged_reads_the_folder(self):
        j = self.d._judged(self.t)
        self.assertEqual(sorted(j), ["Cos", "Mat", "Zero"])
        self.assertEqual(self.d._judged(self.t / "none"), {})

    def test_the_cards_show_the_judgement(self):
        h = self.c.get("/library?db=" + self.db).get_data(as_text=True)
        m = re.search(r'<div class="card-wrap" data-doc="Mat">(.*?)<div class="bsacts"', h, re.S).group(1)
        self.assertIn("Debris judged MATERIAL (2026-10-11): misread letters in 50% of verses; vision agreement 0.78", m)
        c = re.search(r'<div class="card-wrap" data-doc="Cos">(.*?)<div class="bsacts"', h, re.S).group(1)
        self.assertNotIn("Debris judged", c, "cosmetic, and nothing stopped it: no line")
        tail = h[h.index("Not yet readable"):]
        self.assertIn("Debris judged MODERATE", tail)
        self.assertIn('href="/sources"', h)
        self.assertIn(".cardnote.judged[data-level=material]", h)

    def test_the_sources_page(self):
        r = self.c.get("/sources?db=" + self.db)
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        self.assertLess(h.index('href="/repair/Mat"'), h.index('href="/repair/Zero"'), "material first")
        self.assertNotIn('href="/repair/Cos"', h, "nothing holds a cosmetic, translated text")
        self.assertIn("Mat critical edition", h); self.assertNotIn("the one you have", h)
        self.assertIn("repair the scan", h); self.assertIn("vision 0.78", h)
        self.assertIn("Judge the texts again", h); self.assertIn('id="rp-corpus"', h)
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "s.js"; p.write_text(js, encoding="utf-8")
            res = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_judge_all_needs_no_text(self):
        got = []
        orig = self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            r = self.c.post("/api/repair", json={"step": "judge_all"})
            self.assertEqual(r.status_code, 200)
            kind, doc, argv, mode = got[0]
            self.assertEqual((kind, doc, mode, argv[-1]), ("repair", "corpus", "judge_all", "--judge-all"))
        finally:
            self.d.launch = orig

    def test_the_repair_page_shows_it(self):
        h = self.c.get("/repair/Mat?db=" + self.db).get_data(as_text=True)
        self.assertIn("Debris judged MATERIAL", h)
        self.assertNotIn("__", h.replace("__name__", ""))

    def test_the_dashboard_page_links_to_sources(self):
        h = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertIn('href="/sources"', h); self.assertIn("JUDGE_DESK_2026_10_11", h)


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_judgedesk_*")) for f in ("dashboard.py", "dashboard_static.html")}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            shutil.copy2(TOOL, t / "scripts" / "repair_text.py")
            pat = [sys.executable, str(SCRIPTS / "patch_judge_desk_2026_10_11.py")]
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in baks:
                self.assertEqual((t / "scripts" / f).read_bytes(), (SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_ascii_and_marks(self):
        for p in (TOOL, SCRIPTS / "patch_judge_desk_2026_10_11.py"):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"JUDGE_DESK_2026_10_11", b)


if __name__ == "__main__":
    unittest.main()
