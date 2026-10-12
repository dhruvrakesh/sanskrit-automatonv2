# -*- coding: ascii -*-
"""PATH_2026_10_12: one way forward for every text (scripts/text_path.py, read-only), and what the morning's runs
showed: a vision page that failed is written down and tried last (it no longer stops a repair before a page is
read), the repair's cap fits its estimate, a damaged text can be withdrawn from the site (the mirror retires it,
Ask leaves it out; --restore undoes it), and the dashboard's /path. Temp files only, never data/context.db."""
import importlib.util, json, math, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
import db_utils  # noqa: E402
import ingest_jsonl_fast as ij  # noqa: E402

W = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d"
     "\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d"
     "\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e"
     "\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 %s \u0965 %d \u0965")
WORDS = ["\u0938\u091e\u094d\u091c\u092f", "\u0905\u0930\u094d\u091c\u0941\u0928", "\u0915\u0943\u0937\u094d\u0923",
         "\u0926\u094d\u0930\u094b\u0923", "\u092d\u0940\u0937\u094d\u092e", "\u0915\u0930\u094d\u0923"]
JUNK = " af bates Prec wt "   # Latin letters in a Devanagari verse: Tesseract's debris


def verses(n, start=0, junk=""):
    return "\n".join((W % (WORDS[(start + i) % len(WORDS)], start + i + 1)) + junk for i in range(n))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TP = load("text_path_path", SCRIPTS / "text_path.py")
PR = {"vision_page": 0.0024, "vision_dear": 0.0111, "measured": ["N"], "passage": 0.00063, "passage_from": "usage_log"}


def facts(**kw):
    f = {"doc": "T", "state": None, "passages": 100, "english": 0, "hindi": 0, "below_quality": 0, "vision_pct": 0.0,
         "level": "material", "misread_letters_pct": 3.0, "pdfs": 0, "raw_pages": 0, "vision_pages": 0, "merged_pages": 0,
         "merged_complete": False, "cost_per_page": 0.0024, "db_pages": 0, "reviews": None, "vectors": 0,
         "price_from": "the corpus"}
    f.update(kw)
    return f


class TheRules(unittest.TestCase):
    def test_the_register_decides_first(self):
        o = TP.decide(facts(state="complete", reason="what is left is not Sanskrit"), PR)
        self.assertEqual(o["path"], "done")
        o = TP.decide(facts(state="withdrawn", at="2026-10-12", reason="damaged", pdfs=10, raw_pages=10), PR)
        self.assertEqual(o["path"], "source"); self.assertIn("withdrawn from the site on 2026-10-12", o["why"])
        self.assertTrue(o["next"][0].endswith("--find-source   (free; --ai lets the AI judge the editions, about $0.002)"))
        self.assertIn("--restore", o["also"][0])

    def test_a_duplicate_is_retired_with_its_keeper_named(self):
        o = TP.decide(facts(doc="shiva_dhanur_veda", english=19, dup_of=("dhanur_veda_shiva_dhanur_veda", 0.71),
                            keeper_left=18), PR)
        self.assertEqual(o["path"], "retire")
        self.assertEqual(o["next"], ["python scripts\\retire_doc.py --doc shiva_dhanur_veda --supersedes "
                                     "dhanur_veda_shiva_dhanur_veda --dry-run",
                                     "python scripts\\retire_doc.py --doc shiva_dhanur_veda --supersedes "
                                     "dhanur_veda_shiva_dhanur_veda --yes"])
        self.assertAlmostEqual(o["then"], 36 * 0.00063)

    def test_a_repair_not_in_the_database_goes_in_before_the_translation(self):
        # HAYASHIRSHA on 11 Oct: in repair, vision read 185 of 189 pages, the database still Tesseract's on 185
        f = facts(doc="H", state="in_repair", en_before=158, passages=1362, english=158, hindi=1174, pdfs=189,
                  raw_pages=189, vision_pages=185, merged_pages=189, merged_complete=True, db_pages=189, changed=185,
                  changed_en=158, changed_hi=1100, changed_say=True)
        o = TP.decide(f, PR)
        self.assertEqual(o["path"], "in_repair")
        self.assertIn("the database holds Tesseract's reading on 185 page(s)", o["why"])
        self.assertEqual(o["next"][0], "python scripts\\reingest_pages.py --doc H   (first: the 185 changed page(s) of the "
                                       "repair into the database; the plan, free)")
        self.assertEqual(o["next"][1], "python scripts\\reingest_pages.py --doc H --apply --replace 158   (a backup first; "
                                       "refused while a job writes)")
        self.assertTrue(o["next"][2].startswith("translate it")); self.assertIn("--release", o["next"][3])
        o = TP.decide(dict(f, changed=0, vision_pct=96.0), PR)
        self.assertTrue(o["next"][0].startswith("translate it"), "all in: translate, then publish")
        # a clean text with 7 garbage pages of its own repair not yet in (the Tantric Texts): those go in first
        o = TP.decide(facts(doc="Tt", passages=2946, vision_pct=95.8, level="cosmetic", misread_letters_pct=1.87, pdfs=212,
                            raw_pages=212, vision_pages=210, merged_pages=212, merged_complete=True, db_pages=212,
                            changed=7, changed_en=0, changed_hi=0, changed_say=False), PR)
        self.assertEqual(o["path"], "translate")
        self.assertEqual(o["next"][1], "python scripts\\reingest_pages.py --doc Tt --apply   (a backup first; refused while "
                                       "a job writes)")
        self.assertIn("7 page(s) of the repair are not in the database yet", o["why"])

    def test_pages_not_read_or_not_in(self):
        o = TP.decide(facts(passages=0, pdfs=5), PR)
        self.assertEqual(o["path"], "ingest"); self.assertIn("/api/ocr", o["next"][0])
        o = TP.decide(facts(passages=0, raw_pages=5), PR)
        self.assertIn("/api/ingest", o["next"][0])
        o = TP.decide(facts(passages=0), PR)
        self.assertEqual(o["path"], "retire"); self.assertIn("an empty record", o["why"])
        o = TP.decide(facts(pdfs=309, raw_pages=12, db_pages=12), PR)
        self.assertEqual(o["path"], "ingest"); self.assertIn("Tesseract read 12 of its 309 pages", o["why"])
        o = TP.decide(facts(pdfs=100, raw_pages=100, db_pages=50), PR)
        self.assertEqual(o["next"][1], "python scripts\\reingest_pages.py --doc T --merged-dir data\\raw --apply")

    def test_use_the_repair_says_what_it_removes(self):
        f = facts(doc="S", passages=16, english=16, pdfs=13, raw_pages=13, vision_pages=13, merged_pages=13,
                  merged_complete=True, db_pages=13, changed=13, changed_en=16, changed_say=True)
        o = TP.decide(f, PR)
        self.assertEqual(o["path"], "use_repair")
        self.assertEqual(o["next"][2], "python scripts\\reingest_pages.py --doc S --apply --replace 16")
        o = TP.decide(dict(f, changed=0), PR)
        self.assertNotEqual(o["path"], "use_repair", "the database already holds the repaired reading")

    def test_the_repair_of_the_scan_is_priced_and_capped(self):
        f = facts(doc="N", passages=2916, pdfs=546, raw_pages=546, vision_pages=268, db_pages=537, cost_per_page=0.0111,
                  price_from="this text")
        o = TP.decide(f, PR)
        self.assertEqual(o["path"], "repair")
        cap = max(1.0, math.ceil(278 * 0.0111 * 1.25 * 10) / 10.0)
        self.assertEqual(cap, 3.9)
        self.assertEqual(o["next"][0], "python scripts\\repair_text.py --doc N --repair --max-usd 3.90   (about 278 pages "
                                       "at $0.0111 a page, measured on this text)")
        self.assertAlmostEqual(o["cost"], 278 * 0.0111); self.assertAlmostEqual(o["cost_hi"], o["cost"])
        o = TP.decide(dict(f, cost_per_page=0.0024, price_from="the corpus"), PR)
        self.assertIn("the corpus price: not measured on this text yet; up to $3.09 at the dearest text's $0.0111", o["next"][0])
        self.assertAlmostEqual(o["cost_hi"], 278 * 0.0111)
        self.assertIn("--max-usd 1.00", o["next"][0], "the cap from the estimate; it stops at the cap")

    def test_no_scan_damaged_wants_a_source(self):
        o = TP.decide(facts(doc="B", passages=1677, english=824, misread_letters_pct=11.36, parent="B_old",
                            desk="Bodhicaryavatara (x), score 71.4"), PR)
        self.assertEqual(o["path"], "source"); self.assertIn("its scan is not here (0 page PDFs); 824 English on it", o["why"])
        self.assertTrue(any("--withdraw" in x and "824" in x for x in o["also"]))
        self.assertTrue(any("re-segmentation" in x for x in o["also"]))
        o = TP.decide(facts(doc="M", english=18, level="moderate"), PR)
        self.assertFalse(any("--withdraw" in x for x in o["also"]), "only a material debris is withdrawn")
        o = TP.decide(facts(doc="Nl", english=1380, level="material", misread_letters_pct=1.96), PR)
        self.assertFalse(any("--withdraw" in x for x in o["also"]), "1.96% misread: not withdrawn for it")
        o = TP.decide(facts(doc="Nl", english=1380, level="material", misread_letters_pct=1.96,
                            reviews={"n": 40, "fidelity": 3.4, "serious": 15}), PR)
        self.assertTrue(any("--withdraw" in x for x in o["also"]), "the judge finds 38% wrong")

    def test_an_etext_witness_and_the_text_it_reads(self):
        o = TP.decide(facts(doc="B__w_gretil", state="witness", of="B", passages=800, english=0, vision_pct=0.0,
                            level="-"), PR)
        self.assertEqual(o["path"], "in_repair"); self.assertIn("an e-text witness of B (800 passages", o["why"])
        self.assertTrue(o["next"][0].startswith("translate it"))
        self.assertEqual(o["next"][1], "python scripts\\repair_text.py --doc B__w_gretil --release   (adopts it: the next "
                                       "mirror run sends it to the site once it is translated)")
        o = TP.decide(facts(doc="B", english=824, misread_letters_pct=11.36,
                            etext={"doc": "B__w_gretil", "passages": 800, "english": 0, "witness": True}), PR)
        self.assertEqual(o["path"], "source")
        self.assertTrue(any(x.startswith("its e-text B__w_gretil is here (800 passages, 0 English; a witness, here only)")
                            and x.endswith('--withdraw "superseded by its e-text B__w_gretil"') for x in o["also"]), o["also"])

    def test_translate_judge_retranslate_done(self):
        o = TP.decide(facts(vision_pct=100.0, level="-", english=10), PR)
        self.assertEqual(o["path"], "translate")
        o = TP.decide(facts(vision_pct=100.0, level="cosmetic", english=100, hindi=100), PR)
        self.assertEqual(o["path"], "judge")
        self.assertEqual(o["next"][0], "python scripts\\judge_sample.py --doc T --sample-pct 40 --limit 40   (the dry run, "
                                       "free; then --yes)")
        o = TP.decide(facts(vision_pct=100.0, level="cosmetic", english=100, hindi=100,
                            reviews={"n": 40, "fidelity": 3.9, "serious": 5}), PR)
        self.assertEqual(o["path"], "retranslate")
        o = TP.decide(facts(vision_pct=100.0, level="cosmetic", english=100, hindi=100,
                            reviews={"n": 40, "fidelity": 4.6, "serious": 2}), PR)
        self.assertEqual(o["path"], "done")

    def test_the_money_line(self):
        self.assertEqual(TP.money_line({"cost": 12.02, "cost_hi": 25.62, "then": 67.98}),
                         "about $12.02 now (up to $25.62 at the dearest text's price); then about $67.98 to translate")
        self.assertEqual(TP.money_line({"cost": 7.77, "cost_hi": 7.77, "then": 0.0}), "about $7.77 now")
        self.assertEqual(TP.money_line({"cost": 0.0, "then": 0.211}), "then about $0.211 to translate")
        self.assertEqual(TP.money_line({"cost": 0.0, "then": 0.0}), "")


def make_db(path: Path, docs: dict):
    """docs: {code: (engine, {page: text})}."""
    con = db_utils.connect(str(path))
    db_utils.ensure_schema(con)
    ij._ensure_provenance(con)
    ids = {}
    for code, (engine, pages) in docs.items():
        did = ids[code] = db_utils.ensure_doc(con, code)
        for pg, text in sorted(pages.items()):
            ij.upsert_passages(con, did, pg, [{"text": text, "engine": engine}])
    con.commit()
    return con, ids


class ThePrices(unittest.TestCase):
    def test_measured_texts_and_the_dearest(self):
        import cost_tracker
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con = sqlite3.connect(str(db))
            con.execute("CREATE TABLE usage_log(id INTEGER PRIMARY KEY, kind TEXT, doc TEXT, engine TEXT, in_tokens REAL, "
                        "out_tokens REAL, passages INTEGER, token_source TEXT, cost_usd REAL)")
            eng = "gemini-vision:gemini-2.5-flash"
            for doc, n, tout in (("Cheap", 25, 1000), ("Dear", 25, 8000), ("Few", 5, 90000), ("(backfill)", 30, 10)):
                for _ in range(n):
                    con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, passages, token_source) "
                                "VALUES('ocr_vision', ?, ?, 1000, ?, 1, 'provider')", (doc, eng, tout))
            for _ in range(10):
                con.execute("INSERT INTO usage_log(kind, doc, passages, cost_usd) VALUES('translation', 'Cheap', 10, 0.0063)")
            con.commit(); con.close()
            pr = TP.prices(str(db), {"Cheap", "Dear", "Few"})
        pin, pout = cost_tracker._get_pricing(eng)
        self.assertEqual(pr["measured"], ["Cheap", "Dear"], "20 or more pages of its own, and a text in the database")
        self.assertAlmostEqual(pr["vision_dear"], round((1000 * pin + 8000 * pout) / 1e6, 5), places=5)
        self.assertAlmostEqual(pr["passage"], 0.00063, places=6); self.assertEqual(pr["passage_from"], "usage_log")


class TheDuplicates(unittest.TestCase):
    def test_the_vision_copy_is_kept(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con, _ = make_db(db, {"sdv": ("tesseract", {1: verses(4, junk=JUNK)}),
                                  "dv_sdv": ("gemini-vision", {1: verses(4)}),
                                  "other": ("tesseract", {1: "\u0915\u0916\u0917\u0918 \u0965 1 \u0965"})})
            con.close()
            d = TP.duplicates(str(db), ["sdv", "dv_sdv", "other"], {"sdv": 0.0, "dv_sdv": 100.0, "other": 0.0})
        self.assertEqual(list(d), ["sdv"]); self.assertEqual(d["sdv"][0], "dv_sdv"); self.assertGreaterEqual(d["sdv"][1], 0.5)


class TheChart(unittest.TestCase):
    def test_every_text_charted_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            db = t / "c.db"
            con, ids = make_db(db, {"Ts": ("tesseract", {pg: verses(2, pg, JUNK) for pg in (1, 2, 3)}),
                                    "Vs": ("gemini-vision", {1: verses(3)}),
                                    "Wd": ("tesseract", {1: verses(2, junk=JUNK)}),
                                    "Ts__w_gretil": ("etext", {1: verses(2, 1)})})
            pids = [r[0] for r in con.execute("SELECT id FROM passages WHERE doc_id=? ORDER BY idx", (ids["Vs"],))]
            for i in pids:
                con.execute("UPDATE passages SET translation='English' WHERE id=?", (i,))
            con.execute("INSERT INTO translations_l10n(passage_id, lang, translation) VALUES(?, 'hi', 'Hindi')", (pids[0],))
            con.commit(); con.close()
            for sub in ("inbox", "raw", "vision", "merged", "work", "desk"):
                (t / sub).mkdir()
            for pg in (1, 2, 3):
                (t / "inbox" / ("Ts_%04d.pdf" % pg)).write_bytes(b"%PDF-1.4\n")
                (t / "raw" / ("Ts_%04d.jsonl" % pg)).write_text(json.dumps({"text": verses(2, pg, JUNK)}) + "\n", encoding="utf-8")
            for pg in (1, 2):
                (t / "inbox" / ("New_%04d.pdf" % pg)).write_bytes(b"%PDF-1.4\n")
            (t / "v.jsonl").write_text(json.dumps({"doc": "Wd", "status": "withdrawn", "reason": "damaged",
                                                   "at": "2026-10-12T09:00:00"}) + "\n" + json.dumps(
                {"doc": "Ts__w_gretil", "status": "witness", "of": "Ts", "at": "2026-10-12T09:01:00"}) + "\n", encoding="utf-8")
            before = db.read_bytes()
            r = subprocess.run([sys.executable, str(SCRIPTS / "text_path.py"), "--db", str(db), "--inbox", str(t / "inbox"),
                                "--raw", str(t / "raw"), "--vision-dir", str(t / "vision"), "--merged-dir", str(t / "merged"),
                                "--work", str(t / "work"), "--verdicts", str(t / "v.jsonl"), "--source-desk", str(t / "desk"),
                                "--out", str(t / "out" / "p.json"), "--html", str(t / "out" / "p.html")],
                               capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(db.read_bytes(), before, "read-only")
            res = json.loads((t / "out" / "p.json").read_text(encoding="utf-8"))
            h = (t / "out" / "p.html").read_text(encoding="utf-8")
        got = {x["doc"]: x for x in res["texts"]}
        self.assertEqual(got["Ts"]["path"], "repair")
        self.assertTrue(got["Ts"]["next"][0].startswith("python scripts\\repair_text.py --doc Ts --repair --max-usd 1.00"))
        self.assertIn("not measured on this text yet", got["Ts"]["next"][0])
        self.assertTrue(any("its e-text Ts__w_gretil is here (2 passages)" in x and "benchmark_sources.py --doc Ts" in x
                            for x in got["Ts"]["also"]), got["Ts"]["also"])
        self.assertEqual(got["Ts__w_gretil"]["path"], "in_repair"); self.assertIn("e-text witness of Ts", got["Ts__w_gretil"]["why"])
        self.assertEqual(got["Vs"]["path"], "judge")
        self.assertEqual(got["Wd"]["path"], "source"); self.assertIn("withdrawn from the site", got["Wd"]["why"])
        self.assertEqual(got["New"]["path"], "ingest"); self.assertTrue(got["New"].get("new"))
        self.assertEqual(res["mark"], "PATH_2026_10_12")
        self.assertIn("VERDICT: 5 text(s) charted", r.stdout)
        self.assertIn("<title>The path</title>", h); self.assertIn("Ts", h)


class TheVisionLedger(unittest.TestCase):
    def setUp(self):
        self.oc = load("ocr_consensus_path", SCRIPTS / "ocr_consensus.py")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.v = self.t / "vision"; self.v.mkdir()
        self.calls = []

    def tearDown(self):
        self.td.cleanup()

    def runner(self, good, after=None):
        def run(argv):
            out = Path(argv[argv.index("--out") + 1])
            self.calls.append(out.stem)
            if out.stem in good:
                out.write_text(json.dumps({"text": "\u0915\u0916\u0917"}) + "\n", encoding="utf-8")
            if after:
                after(out.stem)
            return 0     # ocr_vision.py exits 0 even when it delivers nothing
        return run

    def pdfs(self, *stems):
        return [str(self.t / "inbox" / (s + ".pdf")) for s in stems]

    def test_the_failed_pages_go_last_and_twice_failed_are_left(self):
        led = {"N_0001": {"fails": 1}, "N_0002": {"fails": 1}, "N_0003": {"fails": 2}}
        todo = self.pdfs("N_0001", "N_0002", "N_0003", "N_0004", "N_0005")
        order, gave = self.oc.order_vision(todo, led)
        self.assertEqual([Path(x).stem for x in order], ["N_0004", "N_0005", "N_0001", "N_0002"])
        self.assertEqual([Path(x).stem for x in gave], ["N_0003"])
        order, gave = self.oc.order_vision(todo, led, retry=True)
        self.assertEqual(gave, []); self.assertEqual(Path(order[-1]).stem, "N_0003")

    def test_the_natyasastra_case_reads_the_pages_it_can(self):
        # five pages failed the night before, then three good ones: the old loop stopped after the five, reading none
        led = {s: {"fails": 1} for s in ("N_0026", "N_0032", "N_0038", "N_0040", "N_0044")}
        todo = self.pdfs("N_0026", "N_0032", "N_0038", "N_0040", "N_0044", "N_0050", "N_0051", "N_0052")
        ok, fails, stopped = self.oc.run_vision(todo, self.v, "N", led, runner=self.runner({"N_0050", "N_0051", "N_0052"}))
        self.assertEqual((ok, fails, stopped), (3, 5, ""))
        self.assertEqual(led["N_0026"]["fails"], 2); self.assertNotIn("N_0050", led)
        self.oc.write_failed(self.t / "work", "N", led)
        self.assertEqual(self.oc.read_failed(self.t / "work", "N"), led)
        self.assertEqual(self.oc.failed_ledger(self.t / "work", "N").name, "N_vision_failed.json")
        self.assertEqual(self.oc.read_failed(self.t / "work", "none"), {})

    def test_five_new_failures_in_a_row_stop_it_and_a_success_clears_a_page(self):
        led = {"N_0009": {"fails": 1}}
        todo = self.pdfs("N_0009", *("N_%04d" % i for i in range(10, 17)))
        ok, fails, stopped = self.oc.run_vision(todo, self.v, "N", led, runner=self.runner({"N_0009"}))
        self.assertEqual(ok, 1); self.assertNotIn("N_0009", led, "read at last: off the ledger")
        self.assertEqual(fails, 5); self.assertIn("5 vision failures in a row", stopped)
        self.assertEqual(len(self.calls), 6, "it stops at the fifth new failure")

    def test_the_cap_stops_the_run_and_marks_no_page(self):
        ok, fails, stopped = self.oc.run_vision(self.pdfs("N_0001"), self.v, "N", {}, budget=lambda: False,
                                                runner=self.runner(set()))
        self.assertEqual((ok, fails, self.calls), (0, 0, [])); self.assertIn("the spend cap is reached", stopped)
        state = {"ok": True}
        led = {}
        ok, fails, stopped = self.oc.run_vision(self.pdfs("N_0001", "N_0002"), self.v, "N", led,
                                                budget=lambda: state["ok"],
                                                runner=self.runner(set(), after=lambda s: state.update(ok=False)))
        self.assertEqual((ok, fails, led), (0, 0, {}), "refused for the cap: not the page's fault")
        self.assertIn("the spend cap is reached", stopped)

    def test_the_pages_that_failed_before_the_ledger_existed(self):
        for pg in (1, 2, 4, 297):
            (self.v / ("N_%04d.jsonl" % pg)).write_text(json.dumps({"text": "\u0915\u0916\u0917"}) + "\n", encoding="utf-8")
        (self.v / "N_0300.jsonl").write_text("", encoding="utf-8")   # an empty reading is no reading
        self.assertEqual(self.oc.last_read_page(self.v, "N"), 297)
        self.assertEqual(self.oc.last_read_page(self.t / "none", "N"), 0)
        led = {"N_0026": {"fails": 1, "last": "x"}}
        todo = self.pdfs("N_0003", "N_0026", "N_0298", "N_0300")
        self.assertEqual(self.oc.seed_failed(todo, led, 297), 1)
        self.assertEqual(led["N_0003"]["fails"], 1); self.assertEqual(led["N_0026"]["last"], "x", "a written failure kept")
        self.assertNotIn("N_0298", led)
        order, gave = self.oc.order_vision(todo, led)
        self.assertEqual([Path(x).stem for x in order], ["N_0298", "N_0300", "N_0003", "N_0026"])

    def test_main_uses_it(self):
        s = (SCRIPTS / "ocr_consensus.py").read_text(encoding="utf-8")
        self.assertIn("seeded = seed_failed(todo, led, last_read_page(vdir, doc))", s)
        self.assertIn("todo, gave = order_vision(todo, led, args.retry_refused)", s)
        self.assertIn("n_ok, fails, stopped = run_vision(todo, vdir, doc, led, args.model, _budget", s)
        self.assertIn("write_failed(work, doc, led)", s)


class TheRegister(unittest.TestCase):
    def test_withdraw_and_restore(self):
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "v.jsonl"
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "repair_text.py"), "--doc", "Bod", "--verdicts",
                                             str(v)] + list(x), capture_output=True, text=True, encoding="utf-8",
                                            env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            r = run("--withdraw", "its text is damaged: a better source is wanted")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("VERDICT: Bod withdrawn from the site: its text is damaged", r.stdout)
            self.assertIn("NEXT: python scripts\\repair_text.py --doc Bod --find-source", r.stdout)
            recs = [json.loads(x) for x in v.read_text(encoding="utf-8").splitlines()]
            self.assertEqual((recs[-1]["status"], recs[-1]["doc"]), ("withdrawn", "Bod"))
            r = run("--restore")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(json.loads(v.read_text(encoding="utf-8").splitlines()[-1])["status"], "restored")

    def test_the_advice(self):
        rt = load("repair_text_path", SCRIPTS / "repair_text.py")
        self.assertIn("withdrawn", rt.STATES)
        v, nxt, also = rt.advise({"state": {"status": "withdrawn", "at": "2026-10-12T10:00:00", "reason": "damaged"}}, "B")
        self.assertIn("withdrawn from the site on 2026-10-12: damaged", v)
        self.assertEqual(nxt, "python scripts\\repair_text.py --doc B --find-source")
        self.assertIn("--restore", also[0])
        r = {"state": None, "judged": {}, "untranslated": 10, "held": True, "debris_pct": 71.2, "vision_pct": 0.0, "pdfs": 546,
             "consensus": {}, "merged_complete": False, "queued": 537, "vision_pages": 268, "cost_per_page": 0.0111,
             "english": 0, "hindi": 0, "passages": 10, "quality_stuck": False}
        v, nxt, also = rt.advise(r, "N")
        self.assertIn("vision OCR on about 269 page(s), about $2.99 ($0.0111 a page)", v)
        self.assertEqual(nxt, "python scripts\\repair_text.py --doc N --repair --max-usd 3.80   (it stops before spending more)")
        v, nxt, also = rt.advise(dict(r, vision_pages=0, queued=20, cost_per_page=0.0004), "N")
        self.assertIn("--repair --max-usd 1.00", nxt)


class TheMirror(unittest.TestCase):
    def test_a_withdrawn_text_is_not_live_until_restored(self):
        cs = load("corpus_sync_path", SCRIPTS / "corpus_sync.py")
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "v.jsonl"
            con = sqlite3.connect(":memory:")
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
                              "INSERT INTO docs(code) VALUES('Bod'),('Kept');")
            old = os.environ.get("SA_SOURCE_VERDICTS")
            os.environ["SA_SOURCE_VERDICTS"] = str(v)
            try:
                v.write_text(json.dumps({"doc": "Bod", "status": "withdrawn"}) + "\n")
                self.assertEqual([d[1] for d in cs.live_docs(con)], ["Kept"])
                with open(v, "a") as f:
                    f.write(json.dumps({"doc": "Bod", "status": "restored"}) + "\n")
                self.assertEqual([d[1] for d in cs.live_docs(con)], ["Bod", "Kept"])
            finally:
                if old is None:
                    os.environ.pop("SA_SOURCE_VERDICTS", None)
                else:
                    os.environ["SA_SOURCE_VERDICTS"] = old


class TheDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load("dashboard_path", SCRIPTS / "dashboard.py")

    def test_the_steps(self):
        d, got = self.d, []
        orig = d.launch
        d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            c = d.app.test_client()
            self.assertEqual(c.post("/api/repair", json={"doc": "Bod", "step": "withdraw", "reason": "damaged"}).status_code, 200)
            self.assertEqual(c.post("/api/repair", json={"doc": "Bod", "step": "withdraw"}).status_code, 200)
            self.assertEqual(c.post("/api/repair", json={"doc": "corpus", "step": "path_all"}).status_code, 200)
        finally:
            d.launch = orig
        (_, _, a1, _), (_, _, a2, _), (_, doc3, a3, _) = got
        self.assertEqual(a1[-2:], ["--withdraw", "damaged"])
        self.assertEqual(a2[-2:], ["--withdraw", "its text is damaged: a better source is wanted"])
        self.assertTrue(str(a3[0]).endswith("text_path.py") or any(str(x).endswith("text_path.py") for x in a3))
        self.assertIn("--from-dashboard", a3); self.assertEqual(doc3, "corpus")
        self.assertIn("withdraw", d._REPAIR_STEPS); self.assertIn("withdrawn", d._REPAIR_STATES)

    def test_the_path_page(self):
        d = self.d
        with tempfile.TemporaryDirectory() as td:
            old = d.PATH_FILE
            d.PATH_FILE = Path(td) / "none.json"
            try:
                h = d.app.test_client().get("/path").get_data(as_text=True)
                self.assertIn("Not charted yet", h)
                res = {"mark": "PATH_2026_10_12", "at": "2026-10-12T10:00:00", "paths": [list(p) for p in TP.PATHS],
                       "prices": {"vision_page": 0.0024, "vision_dear": 0.0111, "measured": ["N"], "passage": 0.00063},
                       "totals": {"repair": {"texts": 1, "cost": 0.67, "cost_hi": 3.09, "then": 3.58}},
                       "texts": [{"doc": "N", "path": "repair", "why": "Tesseract's text: debris material",
                                  "next": ["python scripts\\repair_text.py --doc N --repair --max-usd 1.00"],
                                  "also": ["x <b>"], "cost": 0.67, "then": 3.58}]}
                d.PATH_FILE = Path(td) / "p.json"
                d.PATH_FILE.write_text(json.dumps(res), encoding="utf-8")
                h = d.app.test_client().get("/path").get_data(as_text=True)
            finally:
                d.PATH_FILE = old
        self.assertIn("<title>The path</title>", h)
        self.assertIn("about $0.670 now (up to $3.09 at the dearest text's price) &middot; then $3.58 to translate", h)
        self.assertIn("NEXT python scripts\\repair_text.py --doc N --repair --max-usd 1.00", h)
        self.assertIn("ALSO x &lt;b&gt;", h); self.assertIn('href="/repair/N"', h)
        self.assertIn("repairStep(this.dataset.doc,&#39;path_all&#39;,this)", h)
        self.assertIn("1 text(s) priced from their own calls", h)

    def test_ask_leaves_a_withdrawn_text_out(self):
        d = self.d
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "c.db"
            con, ids = make_db(db, {"Bod": ("tesseract", {1: verses(1)}), "Kept": ("gemini-vision", {1: verses(1, 2)})})
            con.execute("UPDATE passages SET translation='the field of dharma'")
            con.commit()
            db_utils.rebuild_fts(con)
            (Path(td) / "source_verdicts.jsonl").write_text(json.dumps({"doc": "Bod", "status": "withdrawn"}) + "\n",
                                                            encoding="utf-8")
            self.assertEqual(d._ask_withdrawn(con), {"Bod"})
            got = [r[0] for r in d._ask_retrieve(con, "the field of dharma")]
            con.close()
        self.assertEqual(got, ["Kept"])

    def test_the_next_line_becomes_a_button(self):
        if not shutil.which("node"):
            self.skipTest("node is not here")
        js = self.d._REPAIR_JS + "\nconsole.log(JSON.stringify([%s]));\n" % ", ".join("_rpNext(%s)" % json.dumps(x) for x in (
            'python scripts\\repair_text.py --doc B --withdraw "its text is damaged: a better source is wanted"   (takes '
            'its 824 English off the site until then; --restore brings them back)',
            "python scripts\\repair_text.py --doc N --repair --max-usd 3.80   (it stops before spending more)"))
        stub = "var document={getElementById:function(){return null;}};\n"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "n.js"; p.write_text(stub + js, encoding="utf-8")
            r = subprocess.run([shutil.which("node"), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((a["step"], a["reason"]), ("withdraw", "its text is damaged: a better source is wanted"))
        self.assertEqual((b["step"], b["max_usd"]), ("repair", 3.8))


class ThePatcher(unittest.TestCase):
    FILES = ("ocr_consensus.py", "repair_text.py", "corpus_sync.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_path_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            (t / ".gitignore").write_bytes(b"data/reingest/\r\n")
            pat = [sys.executable, str(SCRIPTS / "patch_path_2026_10_12.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("text_path.py (PATH_2026_10_12) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "text_path.py", t / "scripts" / "text_path.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_mirrorcap_*"))   # MIRROR_CAP_2026_10_12 came after
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn(b"data/reingest/\r\n# PATH_2026_10_12", (t / ".gitignore").read_bytes())
            self.assertIn(b"data/text_path.json\r\n", (t / ".gitignore").read_bytes(), "its line endings kept")
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "corpus_sync.py"
            p.write_bytes(p.read_bytes().replace(b"        if code in witness:\n", b"        if code in witness:  # x\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"PATH_2026_10_12", (t / "scripts" / "ocr_consensus.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "text_path.py", SCRIPTS / "patch_path_2026_10_12.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"PATH_2026_10_12", b)


if __name__ == "__main__":
    unittest.main()
