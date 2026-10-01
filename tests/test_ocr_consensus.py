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
            sqlite3.connect(db).executescript(
                "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT);")
            before = db.stat().st_mtime_ns
            self.m.drift(db, "X", {})
            self.assertEqual(before, db.stat().st_mtime_ns)


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
            rows = {r["engine"]: r for r in self.m.measure(self.m.open_ro(str(db)))}
            self.assertEqual(rows["tesseract"]["en_lac"], 1, "noise rows are out of scope")
            self.assertEqual(rows["gemini-vision:x"]["en_lac"], 0)
            self.assertEqual(rows["gemini-vision:x"]["hi_qmark"], 1)


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


if __name__ == "__main__":
    unittest.main()
