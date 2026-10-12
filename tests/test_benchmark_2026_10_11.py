# -*- coding: ascii -*-
"""BENCHMARK_2026_10_11: a text's readings benchmarked (benchmark_sources.py): Tesseract, vision, the repair,
the database, the text before its repair, archive.org's OCR, the witnesses and a critical e-text, on the same
pages; the debris's effect on the translation before and after; shown on the repair page and on /benchmarks.
Also: repair_text.py --release refuses a text that is not in the database; etext_witness.py --write always
marks a witness local. Temp files only, never data/context.db, never the network."""
import importlib.util, json, os, random, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "benchmark_sources.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def node():
    return shutil.which("node")


DOC_STUB = ("var document={getElementById:function(){return null;},createElement:function(){var o={_t:''};"
            "Object.defineProperty(o,'textContent',{set:function(v){this._t=String(v);}});"
            "Object.defineProperty(o,'innerHTML',{get:function(){return this._t.replace(/&/g,'&amp;')"
            ".replace(/</g,'&lt;').replace(/>/g,'&gt;');}});return o;}};\n")


R = random.Random(11)
C = [chr(c) for c in range(0x0915, 0x093a)]
V = ["", "\u093e", "\u093f", "\u0940", "\u0941", "\u0947", "\u094b", "\u0948"]


def word(k):
    return "".join(R.choice(C) + R.choice(V) for _ in range(k))


def verse():
    line = lambda: " ".join(word(R.randint(2, 4)) for _ in range(5))
    return line() + " \u0964\n" + line() + " \u0965"


VERSES = [verse() for _ in range(200)]


def slip(t, rate=0.02):
    return "".join(R.choice(C) if ("\u0915" <= ch <= "\u0939" and R.random() < rate) else ch for ch in t)


def tess(t):
    """Tesseract's way: every fourth word read as Latin letters (the Devanagari is lost, not kept)."""
    out = []
    for i, w in enumerate(t.split(" ")):
        out.append(("aa", "ee", "oe", "ie")[i % 4] if (i % 4 == 1 and "\u0915" <= w[:1] <= "\u0939") else w)
    return " ".join(out)


def page_lines(p, fn):
    return [fn(v) for v in VERSES[(p - 1) * 10:p * 10]]


def jsonl(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"text": text}, ensure_ascii=False) + "\n", encoding="utf-8")


def make_db(path, doc, fn, translated):
    import db_utils
    con = db_utils.connect(str(path)); db_utils.ensure_schema(con); db_utils.migrate_schema(con)
    did = db_utils.ensure_doc(con, doc, category="agama")
    for p in range(1, 21):
        for i, t in enumerate(page_lines(p, fn), 1):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(?,?,?,?,?,'mula')",
                        (did, p, i, t, "x" if translated else ""))
    con.commit(); con.close()


class Tree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        for p in range(1, 21):
            jsonl(t / "data" / "raw" / ("D_%04d.jsonl" % p), "\n".join(page_lines(p, tess)))
            jsonl(t / "data" / "raw_merged" / ("D_%04d.jsonl" % p), "\n".join(page_lines(p, slip)))
            if p <= 18:
                jsonl(t / "data" / "raw_vision" / ("D_%04d.jsonl" % p), "\n".join(page_lines(p, slip)))
        (t / "backups").mkdir()
        self.db = t / "data" / "context.db"
        make_db(self.db, "D", slip, translated=False)
        make_db(t / "backups" / "context_pre_repair_D_20261011_185037.db", "D", tess, translated=True)
        make_db(t / "backups" / "context_pre_repair_D_other_20261010_000000.db", "D", slip, translated=False)   # another text's
        src = t / "sources" / "D"; src.mkdir(parents=True)
        pages = ["\n".join(slip(v, 0.04) for v in VERSES[(p - 1) * 10:p * 10]) for p in range(1, 21)]
        (src / "D_djvu.txt").write_text("\f".join(pages), encoding="utf-8")
        (src / "D_djvu.txt.json").write_text(json.dumps({"url": "https://archive.org/download/x/D_djvu.txt"}))
        ref = "\n".join(v.replace(" \u0965", " \u0965 %d \u0965" % (i + 1)) for i, v in enumerate(VERSES))
        (src / "sa_text_gretil.txt").write_text(ref, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, script=TOOL, base=True):
        t = self.t
        b = ["--db", str(self.db), "--raw", str(t / "data/raw"), "--vision-dir", str(t / "data/raw_vision"),
             "--merged-dir", str(t / "data/raw_merged"), "--sources", str(t / "sources"),
             "--source-desk", str(t / "data/source_desk"), "--out-dir", str(t / "data/raw_witness"),
             "--witnesses", str(t / "data/witnesses.jsonl"), "--verdicts", str(t / "data/source_verdicts.jsonl"),
             "--bench-dir", str(t / "data/benchmarks"), "--backup-dir", str(t / "backups")] if base else []
        env = dict(os.environ, SA_DASHBOARD_URL="http://127.0.0.1:9", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(script)] + b + list(args), cwd=str(t), capture_output=True, text=True,
                           env=env, timeout=180, encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def test_the_readings_and_the_opinion(self):
        rc, out = self.run_tool("--doc", "D")
        self.assertEqual(rc, 0, out)
        res = json.loads((self.t / "data/benchmarks/D.json").read_text(encoding="utf-8"))
        by = {x["label"]: x for x in res["readings"]}
        self.assertEqual(sorted(by), sorted(["tesseract", "vision", "consensus", "database", "before repair",
                                             "file D_djvu.txt", "file sa_text_gretil.txt"]))
        self.assertEqual(res["reference"], "file sa_text_gretil.txt", "the critical e-text, not archive.org's OCR")
        self.assertEqual(by["file D_djvu.txt"]["kind"], "archive-ocr")
        self.assertGreater(by["tesseract"]["misread_letters_pct"], 2.0)
        self.assertEqual(by["consensus"]["misread_letters_pct"], 0.0)
        self.assertGreater(by["consensus"]["f1_ref"], by["tesseract"]["f1_ref"], "ours reads the critical text better")
        self.assertGreater(by["consensus"]["f1_ref"], by["file D_djvu.txt"]["f1_ref"])
        self.assertEqual(by["vision"]["pages"], 18)
        b = res["translations"]["before"]
        self.assertEqual((b["english"], b["translated_misread_pct"]), (200, 100.0))
        self.assertTrue(b["backup"].endswith("context_pre_repair_D_20261011_185037.db"))
        lines = " ".join(res["lines"])
        self.assertIn("the repair", lines); self.assertIn("removed 100% of the misreading", lines)
        self.assertIn("archive.org's OCR (file D_djvu.txt)", lines); self.assertIn("ours is the better one", lines)
        self.assertIn("Against the critical e-text (file sa_text_gretil.txt)", lines)
        self.assertIn("Translation before the repair: 200 English", lines); self.assertIn("MATERIAL", lines)
        self.assertIn("none of its 200 passages has English yet", lines)
        self.assertIn("NEXT: translate it: Finish EN and Add Hindi in the Library", out)
        self.assertIn("consensus", out)

    def test_a_text_set_aside_is_not_offered_its_translation(self):
        (self.t / "data/source_verdicts.jsonl").write_text(json.dumps({"doc": "D", "status": "set_aside"}) + "\n")
        rc, out = self.run_tool("--doc", "D")
        self.assertEqual(rc, 0, out); self.assertIn("NEXT: \n", out.replace("\r", ""))

    def test_archive_ocr_of_the_scan_is_suggested(self):
        (self.t / "sources/D/D_djvu.txt").unlink()
        sd = self.t / "data/source_desk"; sd.mkdir(parents=True)
        (sd / "D.json").write_text(json.dumps({"candidates": [{"identifier": "in.ernet.dli.2015.368408", "current_scan": True}]}))
        rc, out = self.run_tool("--doc", "D")
        self.assertIn("ALSO: python scripts\\source_desk.py --doc D --fetch in.ernet.dli.2015.368408 --kind text --force", out)

    def test_all(self):
        rc, out = self.run_tool("--all")
        self.assertEqual(rc, 0, out)
        self.assertIn("benchmarked 1 text(s); the repair cut the misread letters in 1 of them", out)
        s = json.loads((self.t / "data/benchmarks/_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["rows"][0]["doc"], "D"); self.assertEqual(s["rows"][0]["en_before"], 200)

    def test_nothing_to_benchmark(self):
        rc, out = self.run_tool("--doc", "Nothing")
        self.assertEqual(rc, 0, out); self.assertIn("nothing to benchmark", out)

    def test_release_refuses_a_text_that_is_not_there(self):
        args = ["--db", str(self.db), "--verdicts", str(self.t / "data/source_verdicts.jsonl"), "--doc", "Bodhi__w_gretil",
                "--release"]
        rc, out = self.run_tool(*args, script=SCRIPTS / "repair_text.py", base=False)
        self.assertEqual(rc, 1, out); self.assertIn("not published", out)
        self.assertFalse((self.t / "data/source_verdicts.jsonl").exists(), "nothing written")
        rc, out = self.run_tool(*(args + ["--force"]), script=SCRIPTS / "repair_text.py", base=False)
        self.assertEqual(rc, 0, out)

    def test_a_stale_release_does_not_make_a_witness_public(self):
        v = self.t / "data/source_verdicts.jsonl"
        v.write_text(json.dumps({"doc": "D__w_gretil", "status": "released"}) + "\n")
        args = ["--db", str(self.db), "--sources", str(self.t / "sources"), "--out-dir", str(self.t / "data/raw_witness"),
                "--witnesses", str(self.t / "data/witnesses.jsonl"), "--verdicts", str(v),
                "--doc", "D", "--file", str(self.t / "sources/D/sa_text_gretil.txt"), "--write"]
        rc, out = self.run_tool(*args, script=SCRIPTS / "etext_witness.py", base=False)
        self.assertEqual(rc, 0, out)
        last = json.loads(v.read_text().splitlines()[-1])
        self.assertEqual((last["doc"], last["status"]), ("D__w_gretil", "witness"))
        rc, out = self.run_tool("--doc", "D")
        res = json.loads((self.t / "data/benchmarks/D.json").read_text(encoding="utf-8"))
        labels = [x["label"] for x in res["readings"]]
        self.assertIn("witness gretil", labels)
        self.assertNotIn("file sa_text_gretil.txt", labels, "the file a witness was written from is read once")


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load("dashboard_benchmark", SCRIPTS / "dashboard.py")
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        d = cls.d
        d.JOBS_LOG_PATH = t / "jobs.jsonl"
        d.SOURCE_DESK_DIR = t / "source_desk"
        d.SOURCES_DIR = t / "sources"
        d.WITNESS_DIR = t / "raw_witness"
        d.WITNESSES_LOG = t / "witnesses.jsonl"
        d.BENCH_DIR = t / "benchmarks"
        d.BENCH_DIR.mkdir()
        (d.BENCH_DIR / "Karan.json").write_text(json.dumps({
            "doc": "Karan", "at": "2026-10-11T23:00:00", "reference": None,
            "readings": [{"label": "tesseract", "kind": "ocr", "pages": 183, "letters": 90000, "misread_letters_pct": 0.29,
                          "pages_misread_pct": 4.0, "level": "cosmetic"},
                         {"label": "consensus", "kind": "ours", "pages": 183, "letters": 95000, "misread_letters_pct": 0.05,
                          "pages_misread_pct": 0.0, "level": "cosmetic", "f1_ours": None},
                         {"label": "file x_djvu.txt", "kind": "archive-ocr", "pages": 150, "letters": 70000,
                          "misread_letters_pct": 4.1, "pages_misread_pct": 40.0, "level": "material", "f1_ours": 0.41}],
            "translations": {"before": {"english": 1603, "hindi": 1425, "translated_misread_pct": 2.4},
                             "now": {"passages": 1935, "english": 0, "hindi": 0}},
            "lines": ["OCR: Tesseract misread 0.29% of the letters", "Translation before the repair: 1603 English"]}))
        (d.BENCH_DIR / "_summary.json").write_text("{}")
        cls.c = d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def post(self, body):
        got = []
        orig = self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            r = self.c.post("/api/repair", json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_the_steps(self):
        r, got = self.post({"doc": "Karan", "step": "benchmark"})
        self.assertEqual(r.status_code, 200)
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("repair", "Karan", "benchmark"))
        self.assertTrue(str(argv[-4]).endswith("benchmark_sources.py")); self.assertEqual(argv[-3:], ["--doc", "Karan", "--from-dashboard"])
        r, got = self.post({"step": "benchmark_all"})
        self.assertEqual(r.status_code, 200); self.assertEqual(got[0][1], "corpus"); self.assertIn("--all", got[0][2])

    def test_the_sources_answer_holds_the_benchmark(self):
        j = self.c.get("/api/repair/sources?doc=Karan").get_json()
        self.assertEqual(j["benchmark"]["readings"][1]["label"], "consensus")
        self.assertIsNone(self.c.get("/api/repair/sources?doc=Other").get_json()["benchmark"])

    def test_the_benchmarks_page(self):
        r = self.c.get("/benchmarks")
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        self.assertIn('href="/repair/Karan"', h); self.assertIn("0.29%", h); self.assertIn("0.05%", h)
        self.assertIn("file x_djvu.txt 4.10%", h); self.assertIn("1603 EN; 2% of it from damaged text", h)
        self.assertIn("0 of 1935 EN", h); self.assertIn("the repair cut the misreading in 1", h)
        self.assertIn("Benchmark every text again", h)
        self.assertIn('href="/benchmarks"', self.c.get("/sources").get_data(as_text=True))
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "b.js"; p.write_text(js, encoding="utf-8")
            res = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_the_repair_page(self):
        h = self.c.get("/repair/Karan").get_data(as_text=True)
        self.assertIn("Benchmark the readings (free)", h); self.assertIn("function _rpBench", h)
        self.assertNotIn("__", h.replace("__name__", "").replace("__w_", ""))
        if not node():
            return
        js = self.d._REPAIR_JS + "\nconsole.log(_rpBench('Karan', {benchmark: %s}));\n" % json.dumps(
            json.loads((self.d.BENCH_DIR / "Karan.json").read_text()))
        p = self.t / "bench.js"; p.write_text(DOC_STUB + js, encoding="utf-8")
        res = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("<td>consensus</td>", res.stdout); self.assertIn('data-level="material"', res.stdout)
        self.assertIn("Translation before the repair: 1603 English", res.stdout)


class ThePatcher(unittest.TestCase):
    FILES = ("repair_text.py", "etext_witness.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_benchmark_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            shutil.copy2(TOOL, t / "scripts" / "benchmark_sources.py")
            (t / ".gitignore").write_bytes(b"sources/\r\n")
            pat = [sys.executable, str(SCRIPTS / "patch_benchmark_2026_10_11.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                # QUALITY_2026_10_11 came after, then REINGEST_2026_10_12: the first later backup is this patch's result
                later = sorted(SCRIPTS.glob(f + ".bak_quality_*")) or sorted(SCRIPTS.glob(f + ".bak_reingest_*"))
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn(b"data/benchmarks/\r\n", (t / ".gitignore").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b"function _rpPreview(doc, i){", b"function _rpPreviewX(doc, i){"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor", r.stdout)
            self.assertNotIn(b"BENCHMARK_2026_10_11", (t / "scripts" / "repair_text.py").read_bytes(), "all or nothing")

    def test_ascii_and_marks(self):
        for p in (TOOL, SCRIPTS / "patch_benchmark_2026_10_11.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"BENCHMARK_2026_10_11", b)


if __name__ == "__main__":
    unittest.main()
