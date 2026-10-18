# -*- coding: ascii -*-
"""QUALITY_2026_10_11: are we sure of the texts? The merge no longer takes Tesseract's garbage of a plate or a title
page (vision's line is kept, or the page is blank); the drift check counts a blank page; the Devanagari itself is
judged (glued letters, malformed words, stray marks, plausibility) by the witness and the benchmark; a damaged OCR
text is not made a witness; the Source desk loads .env and answers an archive.org error with a verdict.
Temp files only, never data/context.db, never the network."""
import argparse, importlib.util, json, os, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
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


def node():
    return shutil.which("node")


mg = load("merge_quality", SCRIPTS / "merge_ocr_sources.py")
ew = load("etext_witness_quality", SCRIPTS / "etext_witness.py")

PLATE = ("af 34 \u00a2 4 ba atk bates \u0967, ai ~ Prec \u096b! \u00a5 ; fy \u0915\u094d\u0937\u0940 | wt a \u2018 hy \u0967 (\u096f _ err 1 (| i ie\n"
         ": ea | 5 \u0965 \u096b\u096b *\u0939 Tint \u0967\u096e ^... ; | jet \u0914\u0930 \u091f\u093f\u0915\u0940 ~\n1 Ae 4. 2.4 vee 4 Ban \u096b. a 1 \"\u092d ioe 4 6 A aos\n") * 4
FRAGMENTS = ("4 \u0915 \u0938 ~ \u201c~ ~~~ -- ~=\n\u0928 ==> -\u00a3-- #\u0965 ` ~\u0924 ~=\n(\u0967 \u0928 \u091a\u094d\u092e .--\n{ ^ \u091f \u093f\n\u0964 | 01\n"
             "\u096b \u00a2\n` \u0967 \u0965\n\u0965 1 \u0965\n") * 5
ENGLISH = ("of a printed work. We need not say that we have used every material available so far. It is the duty of "
           "lovers of Vedic literature to search for more manuscripts and to bring them to light.\n") * 6
SANSKRIT = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 "
            "\u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 "
            "\u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 "
            "\u0938\u091e\u094d\u091c\u092f \u0965\n") * 8


class TheMerge(unittest.TestCase):
    def test_a_plate_is_blank_and_a_title_page_keeps_vision(self):
        self.assertTrue(mg.tesseract_garbage(PLATE)[0])
        src, why = mg.verdict("", PLATE)
        self.assertEqual(src, "blank"); self.assertIn("a plate or a blank page", why)
        src, why = mg.verdict("\u0938\u0942\u091a\u0940\u092a\u0924\u094d\u0930\u092e\u094d", PLATE)
        self.assertEqual(src, "vision", "vision's line, not Tesseract's garbage of the picture"); self.assertIn("vision's 10 chars kept", why)

    def test_fragments_among_marks_are_garbage(self):
        g, why = mg.tesseract_garbage(FRAGMENTS)
        self.assertTrue(g, why); self.assertIn("fragments", why)
        self.assertEqual(mg.verdict("", FRAGMENTS)[0], "blank")

    def test_english_and_sanskrit_that_tesseract_read_stay(self):
        self.assertFalse(mg.tesseract_garbage(ENGLISH)[0])
        self.assertEqual(mg.verdict("", ENGLISH), ("tesseract-fallback", "vision returned nothing"))
        self.assertFalse(mg.tesseract_garbage(SANSKRIT)[0])
        self.assertEqual(mg.verdict("", SANSKRIT)[0], "tesseract-fallback", "Shatapatha 0009: vision failed on real text")
        self.assertEqual(mg.verdict(SANSKRIT, SANSKRIT)[0], "vision")

    def test_apply_writes_a_blank_page(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for d in ("raw", "vision", "merged"):
                (t / d).mkdir()
            for pg, (v, tt) in {"0001": ("", PLATE), "0002": (SANSKRIT, SANSKRIT), "0003": ("", ENGLISH)}.items():
                (t / "raw" / ("D_%s.jsonl" % pg)).write_text(json.dumps({"text": tt}) + "\n", encoding="utf-8")
                (t / "vision" / ("D_%s.jsonl" % pg)).write_text(json.dumps({"text": v, "engine": "gemini-vision:x"}) + "\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "merge_ocr_sources.py"), "--doc", "D", "--vision-dir", str(t / "vision"),
                                "--tesseract-dir", str(t / "raw"), "--outdir", str(t / "merged"), "--apply"],
                               capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("1 page(s) are blank", r.stdout)
            rec = json.loads((t / "merged" / "D_0001.jsonl").read_text(encoding="utf-8"))
            self.assertEqual((rec["engine"], rec["text"], rec["meta"]["variants"]), ("blank", "", []))
            self.assertEqual(json.loads((t / "merged" / "D_0003.jsonl").read_text(encoding="utf-8"))["engine"], "tesseract-fallback")


class TheDrift(unittest.TestCase):
    def test_a_blank_page_is_current_without_rows_and_stale_with_them(self):
        oc = load("ocr_consensus_quality", SCRIPTS / "ocr_consensus.py")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); m = t / "merged"; m.mkdir()
            db = t / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, ocr_engine TEXT);"
                              "INSERT INTO docs VALUES(1,'D');")
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,ocr_engine) VALUES(1,2,1,?,'tesseract-fallback')", (PLATE,))
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,ocr_engine) VALUES(1,3,1,?,'gemini-vision')", (SANSKRIT,))
            con.commit(); con.close()
            for pg, rec in {"0001": {"engine": "blank", "text": ""}, "0002": {"engine": "blank", "text": ""},
                            "0003": {"engine": "gemini-vision", "text": SANSKRIT}}.items():
                (m / ("D_%s.jsonl" % pg)).write_text(json.dumps(rec) + "\n", encoding="utf-8")
            rows = {r["page"]: r["status"] for r in oc.drift(db, "D", oc.page_map(m, "D", "jsonl"))}
            self.assertEqual(rows, {"0001": "current", "0002": "stale", "0003": "current"})


class TheDevanagari(unittest.TestCase):
    def test_glued_malformed_and_stray_marks(self):
        q = ew.quality(["\u0927\u0930\u094d\u092e\u0903 V\u0936\u0902\u0938\u0928\u094d\u0924\u0902 \u093e\u0915 + \u0915\u093e\u093e "
                        "\u092a\u093e\u0920\u0903\u2014B, \u0905\u0917\u094d\u0928\u093f\u092e\u0940\u0933\u0947\u0951 \u0965 \u0967\u0968 \u0965"])
        self.assertEqual(q["words"], 7)
        self.assertEqual((q["glued_pct"], q["malformed_pct"], q["symbols_pct"]), (round(100 / 7.0, 2), round(200 / 7.0, 2), round(100 / 7.0, 2)))
        self.assertEqual(q["glued_top"], ["V"])
        self.assertEqual(ew.quality([SANSKRIT])["noise_pct"], 0.0, "sandhi, conjuncts, dandas, numerals: no noise")

    def test_plausibility_against_a_reference(self):
        with tempfile.TemporaryDirectory() as td:
            ref = Path(td) / "R_0001.jsonl"
            ref.write_text("".join(json.dumps({"text": SANSKRIT}) + "\n" for _ in range(3)), encoding="utf-8")
            old, oldref = ew.QA_REF, list(ew._REF)
            ew.QA_REF, ew._REF[:] = str(Path(td) / "R_*.jsonl"), []
            try:
                self.assertEqual(ew.quality([SANSKRIT])["plausible_pct"], 100.0)
                garbled = ew.quality(["\u0915\u093f\u0916\u0941\u0917\u0947\u0918\u094b \u091a\u093e\u091b\u0940\u091c\u0948"])
                self.assertLess(garbled["plausible_pct"], 50.0)
            finally:
                ew.QA_REF, ew._REF[:] = old, oldref
        self.assertIsNone(ew.quality(["x"], plausible=False)["plausible_pct"])

    def test_the_thresholds_measured(self):
        # the GRETIL Adiparvan 0.0%, vision OCR of a clean print 0.06-0.86%, Tesseract 2.7-7.4%: a witness no cleaner
        # than Tesseract adds nothing
        self.assertEqual((ew.NOISY, ew.NOISE_WARN), (3.0, 1.5))

    def test_a_scan_too_damaged_to_read_is_measured_by_all_its_pages(self):
        m = {"scan_pages": 253, "readable": 3, "matched": 159, "matched_readable": 1, "coverage": 0.33, "order": 0.98}
        op = ew.opinion(m, "D")
        self.assertTrue(op.startswith("the same work, in the same order, by the scan's damaged pages"), op)
        self.assertIn("the scan reads 3 of its 253 pages, and the witness still finds 159 of them (63%", op)
        m2 = dict(m, readable=100, matched=80, matched_readable=70, coverage=0.7)
        self.assertIn("it reads 70 of the scan's 100 readable pages", ew.opinion(m2, "D"))


class TheNoisyWitness(unittest.TestCase):
    def test_a_damaged_ocr_text_is_not_made_a_witness(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "data").mkdir(); (t / "sources" / "D").mkdir(parents=True)
            noisy = t / "sources" / "D" / "x_djvu.txt"
            good = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 "
            bad = "\u093e\u0915 ^ \u0915\u093e\u093e "
            noisy.write_text("".join((good * 3 + bad) + "\u0964 " + (good * 2) + "\u0965 %d \u0965\n" % i for i in range(40)), encoding="utf-8")
            base = ["--db", str(t / "data/none.db"), "--sources", str(t / "sources"), "--out-dir", str(t / "data/raw_witness"),
                    "--witnesses", str(t / "data/witnesses.jsonl"), "--verdicts", str(t / "data/v.jsonl"), "--doc", "D",
                    "--file", str(noisy)]
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "etext_witness.py")] + base + list(x), capture_output=True,
                                            text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("the witness is itself a damaged OCR text", r.stdout)
            self.assertIn("it should not be made a witness of this text: its own text is damaged", r.stdout)
            self.assertIn("quality: the witness: noise in", r.stdout)
            r = run("--write")
            self.assertEqual(r.returncode, 1); self.assertIn("refused: the witness is itself a damaged OCR text", r.stdout)
            r = run("--write", "--force")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            meta = json.loads((t / "data/raw_witness/D__w_archive/witness.json").read_text(encoding="utf-8"))
            self.assertGreater(meta["quality"]["noise_pct"], 10.0)
            self.assertGreater(json.loads((t / "data/witnesses.jsonl").read_text().splitlines()[-1])["noise_pct"], 10.0)


class TheBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bs = load("benchmark_quality", SCRIPTS / "benchmark_sources.py")

    def a(self, td):
        return argparse.Namespace(verdicts=str(Path(td) / "v.jsonl"), source_desk=str(Path(td) / "sd"))

    def reading(self, label, kind, mis, noise, plaus, **kw):
        return dict({"label": label, "kind": kind, "pages": 100, "letters": 50000, "misread_letters_pct": mis,
                     "pages_misread_pct": 10.0, "noise_pct": noise, "plausible_pct": plaus, "glued_pct": 0.0, "glued_top": []}, **kw)

    def test_compare_uses_the_devanagari_too(self):
        arch = self.reading("file x_djvu.txt", "archive-ocr", 0.0, 13.0, 80.3)
        ours = self.reading("database", "ours", 11.54, 4.8, 87.1)
        sc, why = self.bs.compare(arch, ours)
        self.assertEqual(sc, -1, why)
        res = {"doc": "B", "readings": [self.reading("tesseract", "ocr", 11.54, 4.8, 87.1), ours, arch], "reference": None,
               "lines": [], "translations": {"now": {"passages": 1561, "english": 824, "hindi": 835, "translated_misread_pct": 82.0,
                                                     "translated_noise_pct": 30.0}, "before": {}}}
        with tempfile.TemporaryDirectory() as td:
            lines = " ".join(self.bs.opine(res, "B", self.a(td))["lines"])
        self.assertIn("ours is the less damaged by these measures, but it is damaged too (misread 11.5%, noise 4.8%): neither "
                      "is clean", lines)
        self.assertNotIn("make it a witness", lines); self.assertNotIn("ours is the better one", lines)
        self.assertIn("archive.org's Latin misread 0.0% against 11.5%", lines)
        self.assertIn("not a reading of the meaning; no LLM judge has read it yet", lines)
        self.assertIn("30% had noise in a tenth of their Devanagari words or more: material", lines)
        # ours clean, archive.org's noisy: ours is the better one; archive.org's clean, ours damaged: a witness
        clean = self.reading("database", "ours", 0.2, 0.5, 93.0)
        res3 = dict(res, readings=[clean, self.reading("file z_djvu.txt", "archive-ocr", 0.0, 9.4, 80.3)], lines=[])
        res4 = dict(res, readings=[ours, self.reading("file w_djvu.txt", "archive-ocr", 0.0, 0.5, 93.0)], lines=[])
        with tempfile.TemporaryDirectory() as td:
            self.assertIn("ours is the better one", " ".join(self.bs.opine(res3, "B", self.a(td))["lines"]))
            self.assertIn("archive.org's reading is the better one here: make it a witness",
                          " ".join(self.bs.opine(res4, "B", self.a(td))["lines"]))
        # less damaged than ours, but noise of its own: neither is clean
        res2 = dict(res, readings=[ours, self.reading("file y_djvu.txt", "archive-ocr", 0.0, 6.0, 90.0)], lines=[])
        with tempfile.TemporaryDirectory() as td:
            lines = " ".join(self.bs.opine(res2, "B", self.a(td))["lines"])
        self.assertIn("neither is clean", lines)

    def test_the_repair_against_vision_alone_and_glued_letters(self):
        res = {"doc": "T", "reference": None, "lines": [], "merged_engines": {"vision": 203, "tesseract-fallback": 9},
               "readings": [self.reading("tesseract", "ocr", 5.81, 7.6, 82.4), self.reading("vision", "ocr", 0.17, 1.2, 87.0),
                            self.reading("consensus", "ours", 1.90, 4.2, 86.7, glued_pct=4.2, glued_top=["V"])],
               "translations": {"now": {"passages": 2946, "english": 0}, "before": {}}}
        with tempfile.TemporaryDirectory() as td:
            lines = " ".join(self.bs.opine(res, "T", self.a(td))["lines"])
        self.assertIn("The repair misreads more than vision alone: 1.90% of the letters against 0.17%. 9 of its pages", lines)
        self.assertIn('glued to them (most often "V")', lines)

    def test_a_database_read_from_vision_is_not_unrepaired(self):
        res = {"doc": "S", "reference": None, "lines": [], "readings": [self.reading("tesseract", "ocr", 3.74, 6.0, 85.0),
               self.reading("database", "ours", 0.01, 0.2, 93.0)], "translations": {"now": {}, "before": {}}}
        with tempfile.TemporaryDirectory() as td:
            lines = " ".join(self.bs.opine(res, "S", self.a(td))["lines"])
        self.assertIn("already a better reading than Tesseract's (it was ingested from vision)", lines)

    def test_translated_noise_is_counted(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT, text_type TEXT);"
                              "INSERT INTO docs VALUES(1,'D');")
            for i in range(10):
                text = SANSKRIT if i < 7 else "\u093e\u0915 ^ \u0915\u093e\u093e \u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(1,1,?,?,'x','mula')", (i, text))
            con.commit(); con.close()
            pages, facts = self.bs.db_reading(db, "D")
        self.assertEqual((facts["english"], facts["translated_noise_pct"]), (10, 30.0))


class TheSourceDesk(unittest.TestCase):
    def test_an_archive_error_is_a_verdict_and_the_links(self):
        sd = load("source_desk_quality", SCRIPTS / "source_desk.py")
        self.assertIn("load_env()", (SCRIPTS / "source_desk.py").read_text(encoding="utf-8"))
        self.assertIn("Digital Sanskrit Buddhist Canon", [l["name"] for l in sd.links(["bodhicaryavatara"])])
        fake = types.ModuleType("archive_source_finder")
        fake.analyse = lambda ident: {"txt_url": "https://archive.org/download/x/x_djvu.txt", "pdf_url": None}
        fake.dev_ratio = lambda s: 1.0
        old = sys.modules.get("archive_source_finder")
        sys.modules["archive_source_finder"] = fake
        orig = sd._http

        def boom(*a, **k):
            raise OSError("HTTP Error 500: Internal Server Error")
        sd._http = boom
        try:
            with tempfile.TemporaryDirectory() as td:
                import io, contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = sd.fetch(argparse.Namespace(fetch="in.ernet.dli.2015.368408", dest=td, kind="text", doc="N", force=True))
            self.assertEqual(rc, 1)
            self.assertIn("VERDICT: archive.org did not give in.ernet.dli.2015.368408's OCR text (HTTP Error 500", buf.getvalue())
            self.assertIn("--kind pdf", buf.getvalue())
        finally:
            sd._http = orig
            if old is None:
                sys.modules.pop("archive_source_finder", None)
            else:
                sys.modules["archive_source_finder"] = old
        self.assertIn("dsbcproject.org", ew.HOSTS)


class TheDashboard(unittest.TestCase):
    def test_the_noise_on_the_pages(self):
        d = load("dashboard_quality", SCRIPTS / "dashboard.py")
        bench = {"doc": "K", "at": "2026-10-11T23:00:00", "reference": None, "readings": [
            {"label": "tesseract", "kind": "ocr", "pages": 3, "letters": 9, "misread_letters_pct": 0.86, "pages_misread_pct": 2,
             "level": "cosmetic", "noise_pct": 7.1},
            {"label": "consensus", "kind": "ours", "pages": 3, "letters": 9, "misread_letters_pct": 0.33, "pages_misread_pct": 2,
             "level": "cosmetic", "noise_pct": 4.7, "plausible_pct": 88.2}], "translations": {}, "lines": []}
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            old = d.BENCH_DIR
            d.BENCH_DIR = t
            try:
                (t / "K.json").write_text(json.dumps(bench), encoding="utf-8")
                h = d.app.test_client().get("/benchmarks").get_data(as_text=True)
            finally:
                d.BENCH_DIR = old
            self.assertIn("0.86% / 7.1%", h); self.assertIn("0.33% / 4.7%", h); self.assertIn("misreads / noise", h)
            if not node():
                return
            stub = ("var document={getElementById:function(){return null;},createElement:function(){var o={_t:''};"
                    "Object.defineProperty(o,'textContent',{set:function(v){this._t=String(v);}});"
                    "Object.defineProperty(o,'innerHTML',{get:function(){return this._t;}});return o;}};\n")
            js = stub + d._REPAIR_JS + "\nconsole.log(_rpBench('K', {benchmark: %s}));\n" % json.dumps(bench)
            p = t / "b.js"; p.write_text(js, encoding="utf-8")
            r = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<th>Noise</th><th>Plausible</th>", r.stdout); self.assertIn("<td>4.7%</td><td>88.2%</td>", r.stdout)
        self.assertIn("<td>7.1%</td><td>-</td>", r.stdout, "no plausibility measured: a dash")


class ThePatcher(unittest.TestCase):
    FILES = ("etext_witness.py", "benchmark_sources.py", "merge_ocr_sources.py", "ocr_consensus.py", "source_desk.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_quality_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            pat = [sys.executable, str(SCRIPTS / "patch_quality_2026_10_11.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                # REINGEST_2026_10_12 came after, then PATH_2026_10_12: the first later backup is this patch's result
                later = sorted(SCRIPTS.glob(f + ".bak_reingest_*")) or sorted(SCRIPTS.glob(f + ".bak_path_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_costtruth_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_etextpage_*"))   # COST_TRUTH_2026_10_15; ETEXT_PAGE_2026_10_18
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "ocr_consensus.py"
            p.write_bytes(p.read_bytes().replace(b'status="missing-in-db")', b'status="missing")'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"QUALITY_2026_10_11", (t / "scripts" / "merge_ocr_sources.py").read_bytes(), "all or nothing")

    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_quality_2026_10_11.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"QUALITY_2026_10_11", b)


if __name__ == "__main__":
    unittest.main()
