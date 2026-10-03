# -*- coding: ascii -*-
"""OCR_CONSENSUS_2026_09_30 and LACUNA_MEASURE_2026_09_30.
Run from the repo root:  python -m unittest tests.test_ocr_consensus -v
Uses temp folders and a throwaway SQLite file only. Never touches
data/context.db, the network, the API or port 5057."""
import importlib.util, json, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", str(REPO / "scripts" / (name + ".py")))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def jl(path, rec):
    path.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")


SA = "\u0905\u0925\u093e\u0924\u094b \u0927\u0930\u094d\u092e\u091c\u093f\u091c\u094d\u091e\u093e\u0938\u093e \u092a\u0941\u0930\u0941\u0937\u093e\u0930\u094d\u0925"
SB = "\u0915\u0943\u0937\u094d\u0923\u093e\u092f \u0935\u093e\u0938\u0941\u0926\u0947\u0935\u093e\u092f \u0939\u0930\u092f\u0947 \u092a\u0930\u092e\u093e\u0924\u094d\u092e\u0928\u0947"


class Consensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("ocr_consensus")

    def test_marker(self):
        self.assertIn("OCR_CONSENSUS_2026_09_30", (REPO / "scripts" / "ocr_consensus.py").read_text(encoding="utf-8"))

    def test_page_map_ignores_other_docs_and_folders(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for n in ("X_0001.jsonl", "X_0002_norm.jsonl", "XY_0003.jsonl", "X__upload", "X_12.jsonl"):
                (d / n).write_text("{}", encoding="utf-8")
            self.assertEqual(sorted(self.m.page_map(d, "X", "jsonl")), ["0001", "0002"])

    def test_plan_vision_skips_done_and_empty_counts_as_todo(self):
        with tempfile.TemporaryDirectory() as t:
            v = Path(t)
            jl(v / "X_0001.jsonl", {"text": SA})
            jl(v / "X_0002.jsonl", {"text": "   "})
            todo, done = self.m.plan_vision(["inbox\\X_0001.pdf", "inbox\\X_0002.pdf", "inbox\\X_0003.pdf", ""], v)
            self.assertEqual(done, ["inbox\\X_0001.pdf"])
            self.assertEqual(todo, ["inbox\\X_0002.pdf", "inbox\\X_0003.pdf"])

    def test_similarity(self):
        self.assertEqual(self.m.similarity(SA, SA), 1.0)
        self.assertLess(self.m.similarity(SA, SB), 0.2)
        self.assertEqual(self.m.similarity("Latin only", "123"), 1.0)

    def test_drift_flags_stale_current_missing(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); mdir = d / "merged"; mdir.mkdir()
            db = d / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, ocr_engine TEXT);"
                              "INSERT INTO docs VALUES(1,'X');")
            con.execute("INSERT INTO passages VALUES(1,1,1,1,?, 'tesseract')", (SA,))
            con.execute("INSERT INTO passages VALUES(2,1,2,1,?, 'tesseract')", (SA,))
            con.commit(); con.close()
            jl(mdir / "X_0001.jsonl", {"engine": "tesseract-fallback", "page_no": 1, "text": SA})
            jl(mdir / "X_0002.jsonl", {"engine": "gemini-vision:x", "page_no": 2, "text": SB})
            jl(mdir / "X_0003.jsonl", {"engine": "gemini-vision:x", "page_no": 3, "text": SB})
            rows = {r["page"]: r for r in self.m.drift(db, "X", self.m.page_map(mdir, "X", "jsonl"))}
            self.assertEqual(rows["0001"]["status"], "current")
            self.assertEqual(rows["0002"]["status"], "stale")
            self.assertEqual(rows["0003"]["status"], "missing-in-db")

    def test_drift_opens_read_only(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            c = sqlite3.connect(db)  # Windows: an open handle blocks TemporaryDirectory cleanup
            c.executescript(
                "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT);")
            c.close()
            before = db.stat().st_mtime_ns
            self.m.drift(db, "X", {})
            self.assertEqual(before, db.stat().st_mtime_ns)

    def test_explain_reports_db_only_tokens(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); mdir = d / "merged"; mdir.mkdir()
            db = d / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, text_type TEXT, ocr_engine TEXT);"
                              "INSERT INTO docs VALUES(1,'X');")
            con.execute("INSERT INTO passages VALUES(1,1,7,1,?,'mula','v')", (SA,))
            con.execute("INSERT INTO passages VALUES(2,1,7,2,?,'noise','v')", (SB,))
            con.commit(); con.close()
            jl(mdir / "X_0007.jsonl", {"engine": "v", "page_no": 7, "text": SA})
            r = self.m.explain(db, "X", "0007", mdir / "X_0007.jsonl")
            self.assertEqual(r["sim_without_noise_frontmatter"], 1.0)
            self.assertLess(r["sim_all_rows"], 1.0)
            self.assertEqual(r["text_types"], {"mula": 1, "noise": 1})
            self.assertTrue(any(o["op"] == "delete" for o in r["ops"]), "the noise row is only in the DB")

    def test_drift_compares_what_ingest_stores(self):
        # OCR_CONSENSUS_NORM_2026_10_02: a word hyphenated across a line break in the
        # consensus is ONE word in the DB (normalize_sanskrit joins it). Not stale.
        w1, w2 = "\u091c\u093e\u0924\u0942", "\u0915\u0930\u094d\u0923\u094d\u092f\u093e\u091c\u094d\u091c\u093e\u0924\u0942\u0915\u0930\u094d\u0923\u094d\u092f\u094b"
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); mdir = d / "merged"; mdir.mkdir()
            db = d / "c.db"
            con = sqlite3.connect(db)
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, ocr_engine TEXT);"
                              "INSERT INTO docs VALUES(1,'X');")
            con.execute("INSERT INTO passages VALUES(1,1,9,1,?, 'v')", (SA + " " + w1 + w2,))
            con.commit(); con.close()
            jl(mdir / "X_0009.jsonl", {"engine": "v", "page_no": 9, "text": SA + " " + w1 + "-\n" + w2})
            rows = self.m.drift(db, "X", self.m.page_map(mdir, "X", "jsonl"))
            self.assertEqual(rows[0]["status"], "current")
            self.assertEqual(rows[0]["similarity"], 1.0)

    def test_plan_vision_skips_refused_pages_unless_asked(self):
        with tempfile.TemporaryDirectory() as t:
            v = Path(t)
            jl(v / "X_0001.jsonl", {"text": "", "meta": {"finish": "RECITATION"}})
            jl(v / "X_0002.jsonl", {"text": "", "meta": {"finish": "MAX_TOKENS"}})
            q = ["inbox\\X_0001.pdf", "inbox\\X_0002.pdf"]
            self.assertEqual(self.m.plan_vision(q, v), (["inbox\\X_0002.pdf"], ["inbox\\X_0001.pdf"]))
            self.assertEqual(self.m.plan_vision(q, v, True)[0], q)


class Lacunae(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("measure_lacunae")

    def test_classify(self):
        hi = "\u0930\u093e\u091c\u093e [\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0917\u092f\u093e"
        self.assertEqual(self.m.classify("The king [ILLEGIBLE] went"), (1, 1, 0))
        self.assertEqual(self.m.classify("[ILLEGIBLE] || 12 ||"), (1, 1, 1))
        self.assertEqual(self.m.classify(hi), (1, 1, 0))
        self.assertEqual(self.m.classify("[\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0964"), (1, 1, 1))
        self.assertEqual(self.m.classify("clean"), (0, 0, 0))
        self.assertEqual(self.m.classify("[???????]"), (0, 0, 0), "the PS5-mangled pattern is not a lacuna")

    def test_measure_groups_by_engine_and_counts_qmarks(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            con = sqlite3.connect(db)
            con.executescript(
                "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
                " translation TEXT, text_type TEXT, ocr_engine TEXT);"
                "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
                "INSERT INTO docs VALUES(1,'X');"
                "INSERT INTO passages VALUES(1,1,1,1,'s','a [ILLEGIBLE] b','mula','tesseract');"
                "INSERT INTO passages VALUES(2,1,1,2,'s','fine','mula','gemini-vision:x');"
                "INSERT INTO passages VALUES(3,1,1,3,'s','[ILLEGIBLE]','noise','tesseract');"
                "INSERT INTO translations_l10n VALUES(2,'hi','??????? x');")
            con.commit(); con.close()
            ro = self.m.open_ro(str(db))
            try:
                rows = {r["engine"]: r for r in self.m.measure(ro)}
            finally:
                ro.close()
            self.assertEqual(rows["tesseract"]["en_lac"], 1, "noise rows are out of scope")
            self.assertEqual(rows["gemini-vision:x"]["en_lac"], 0)
            self.assertEqual(rows["gemini-vision:x"]["hi_qmark"], 1)

    def test_breakdowns_paired_and_prompt(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "c.db"
            con = sqlite3.connect(db)
            con.executescript(
                "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
                " translation TEXT, translation_qa REAL, mt_prompt_version TEXT, text_type TEXT);"
                "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT, mt_prompt_version TEXT);"
                "INSERT INTO docs VALUES(1,'X');"
                "INSERT INTO passages VALUES(1,1,1,1,'s','ok',0.9,'v3','mula');"
                "INSERT INTO passages VALUES(2,1,1,2,'s','a [ILLEGIBLE]',0.9,'v3','mula');"
                "INSERT INTO passages VALUES(3,1,1,3,'s',NULL,NULL,NULL,'mula');")
            L = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
            con.executemany("INSERT INTO translations_l10n VALUES(?,?,?,?)",
                            [(1, "hi", "x " + L, "hi-v3"), (2, "hi", "y " + L, "hi-v3"), (3, "hi", "z", "hi-v1")])
            con.commit(); con.close()
            ro = self.m.open_ro(str(db))
            try:
                b = self.m.breakdowns(ro)
            finally:
                ro.close()
            self.assertEqual(b["paired"], {"pairs": 2, "both": 1, "en_only": 0, "hi_only": 1, "neither": 0})
            self.assertEqual(b["by_prompt_hi"]["hi-v3"], [2, 2])
            self.assertEqual(b["by_prompt_hi"]["hi-v1"], [1, 0])
            self.assertEqual(b["hi_by_anchor"]["no QA-passed English"], [1, 0])


class HindiAB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("diag_hindi_ab")

    def test_pick_sample_is_deterministic_and_spread(self):
        rows = list(range(100))
        self.assertEqual(self.m.pick_sample(rows, 4), [0, 25, 50, 75])
        self.assertEqual(self.m.pick_sample(rows[:3], 10), [0, 1, 2])

    def test_tatsama_share(self):
        self.assertEqual(self.m.tatsama_share(SA, SA), 1.0)
        self.assertEqual(self.m.tatsama_share(SA, SB), 0.0)
        self.assertEqual(self.m.tatsama_share(SA, "no devanagari"), 0.0)

    def test_unmarked_damage(self):
        self.assertTrue(self.m.unmarked("abc FOO def", "clean hindi"))
        self.assertFalse(self.m.unmarked("abc FOO def", "x \u27e8y\u27e9"))
        self.assertFalse(self.m.unmarked("\u0905\u0925", "clean hindi"), "no debris, nothing to mark")

    def test_parse_arms(self):
        self.assertEqual(self.m.parse_arms("", False), ["a", "b"])
        self.assertEqual(self.m.parse_arms("", True), ["a", "b", "c", "d"])
        self.assertEqual(self.m.parse_arms("b, d", True), ["b", "d"])
        with self.assertRaises(ValueError):
            self.m.parse_arms("c", False)
        with self.assertRaises(ValueError):
            self.m.parse_arms("z", True)

    def test_score_output_counts_lacuna_and_conjecture(self):
        L = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
        out = "x " + L + " \u27e8\u090b\u0937\u093f\u0936\u093e\u0930\u094d\u0926\u0942\u0932\u27e9 " + L
        r = self.m.score_output(SA, out, "x", None)
        self.assertTrue(r["lacuna"]); self.assertEqual(r["lacuna_tokens"], 2); self.assertEqual(r["conj"], 1)
        self.assertIn("vs_a", r); self.assertIsNone(r["qa"])

    def test_candidate_prompt_keeps_rules_1_to_9(self):
        p = REPO / "prompts" / "hi-v4-candidate.txt"
        if not p.exists():
            self.skipTest("prompts/hi-v4-candidate.txt not present")
        t = p.read_text(encoding="utf-8")
        for k in range(1, 12):
            self.assertIn("\n%d. " % k if k > 1 else "1. ", t)
        self.assertIn("\u27e8", t)

    def test_report_pools_by_doc_and_arm(self):
        L = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
        with tempfile.TemporaryDirectory() as td:
            f1 = Path(td) / "hindi_ref_X_20261001_000000.jsonl"
            f1.write_text(json.dumps({"sa": SA, "hi_a": "x " + L, "hi_b": "y"}) + "\n", encoding="utf-8")
            f2 = Path(td) / "hindi_ref_my_doc_20261002_000000.jsonl"
            f2.write_text(json.dumps({"sa": SA, "arms": ["c"], "hi_c": "\u27e8z\u27e9"}) + "\n", encoding="utf-8")
            r = self.m.report([str(f1), str(f2)])
        self.assertEqual(r["X"]["a"][:2], [1, 1]); self.assertEqual(r["X"]["b"][:2], [1, 0])
        self.assertEqual(len(r["X"]["a"]), 6, "unmarked count is the 6th field")
        self.assertEqual(r["my_doc"]["c"][3], 1, "doc codes with underscores survive")
        self.assertEqual(r["_all"]["a"][0], 1)


if __name__ == "__main__":
    unittest.main()
