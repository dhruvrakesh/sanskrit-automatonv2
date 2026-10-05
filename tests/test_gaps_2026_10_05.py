# -*- coding: ascii -*-
"""GAPS_2026_10_05: corpus_status counts untranslatable passages as gaps (not todo), and
classify_noise --running-heads. Read-only checks except the one --apply on a temp DB."""
import importlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903"
HI = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u092e\u0947\u0902"
EN_VER, HI_VER = "v3-2026-09-27", "hi-file-abc"
VIS = "gemini-vision:gemini-2.5-flash"
HEAD = "\u092e\u093e\u0930\u094d\u0915\u0923\u094d\u0921\u0947\u092f\u092a\u0941\u0930\u093e\u0923\u092e\u094d"   # markandeyapuranam
UVACA = "\u092e\u093e\u0930\u094d\u0915\u0923\u094d\u0921\u0947\u092f \u0909\u0935\u093e\u091a"           # markandeya uvaca
DEVNUM = "\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f"


def devnum(n):
    return "".join(DEVNUM[int(c)] for c in str(n))


class Gaps(unittest.TestCase):
    """100 passages per doc, pages of 4. Before the patch every missing row is 'todo'."""
    def setUp(self):
        import corpus_status, db_utils
        importlib.reload(corpus_status)
        self.cs = corpus_status
        self._cv = corpus_status.current_versions
        corpus_status.current_versions = lambda: (EN_VER, HI_VER, "test")
        self.tmp = Path(tempfile.mkdtemp(prefix="gaps_"))
        self.db = str(self.tmp / "context.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
        con.execute("CREATE TABLE usage_log(kind TEXT, cost_usd REAL, passages INTEGER, ok INTEGER)")
        con.execute("INSERT INTO usage_log VALUES('translation', 1.0, 1000, 1)")
        # doc -> {i: (has_en, has_hi, quality)} exceptions; everything else translated, quality 0.9
        self.missing = {
            "Gappy": {1: (0, 1, .9), 2: (0, 1, .9), 3: (0, 0, .2), 4: (1, 0, .9), 5: (1, 0, .9)},
            "Salv":  {1: (0, 1, .9)},
            "Holey": {i: (0, 1, .9) for i in range(10)},
            "OtherLang": {1: (0, 1, .9)},
        }
        for code, miss in self.missing.items():
            con.execute("INSERT INTO docs(code, category) VALUES(?, 'purana')", (code,))
            did = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()[0]
            for i in range(100):
                en, hi, q = miss.get(i, (1, 1, .9))
                cur = con.execute(
                    "INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation,mt_prompt_version,"
                    "translated_at,ocr_engine,quality_score) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (did, 1 + i // 4, i % 4, SA, "mula", "fine" if en else "", EN_VER if en else None,
                     "2026-10-01T00:00:00", VIS, q))
                if hi:
                    con.execute("INSERT INTO translations_l10n(passage_id,lang,translation,mt_prompt_version,"
                                "translated_at) VALUES(?,?,?,?,?)",
                                (cur.lastrowid, "hi", HI, HI_VER + "+noref", "2026-10-02T00:00:00"))
        con.commit(); con.close()
        recs = [{"doc": "Gappy", "lang": "en", "page": 1, "idx": 1, "cause": "echo-filter"},
                {"doc": "Gappy", "lang": "en", "page": "1", "idx": "2", "cause": "refusal-filter"},  # strings too
                {"doc": "Gappy", "lang": "hi", "page": 2, "idx": 0, "cause": "echo-filter"},
                {"doc": "Gappy", "lang": "hi", "page": 2, "idx": 1, "cause": "model-empty"},
                {"doc": "Salv", "lang": "en", "page": 1, "idx": 1, "cause": "salvaged", "kept": "x"},
                {"doc": "OtherLang", "lang": "hi", "page": 1, "idx": 1, "cause": "echo-filter"}]
        recs += [{"doc": "Holey", "lang": "en", "page": 1 + i // 4, "idx": i % 4, "cause": "echo-filter"}
                 for i in range(10)]
        lines = [json.dumps(r) for r in recs] + ["not json", "{\"doc\": \"Gappy\"}"]
        (self.tmp / "translate_outcomes.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def tearDown(self):
        self.cs.current_versions = self._cv
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stats(self, **kw):
        st, _, _, cpp = self.cs.collect(self.db, None, self.tmp / "raw", self.tmp / "rv", self.tmp / "rm",
                                        self.tmp / "inbox", False, 20, **kw)
        by = {s["doc"]: s for s in st}
        for s in st:
            s["verdict"], s["reasons"], s["commands"] = self.cs.verdict(s, 5.0, 5.0, cpp, {})
        return by

    def test_gaps_within_allowance_are_current(self):
        s = self.stats()["Gappy"]
        self.assertEqual((s["en_gap"], s["en_gap_tried"], s["en_gap_lowq"]), (3, 2, 1))
        self.assertEqual((s["hi_gap"], s["hi_gap_tried"], s["hi_gap_lowq"]), (3, 2, 1))
        self.assertEqual(s["verdict"], "CURRENT", s["reasons"])
        self.assertEqual(s["commands"], [])
        self.assertTrue(any(r.startswith("note: 3 passage(s) without English") for r in s["reasons"]), s["reasons"])

    def test_salvaged_and_other_language_are_still_work(self):
        by = self.stats()
        for code in ("Salv", "OtherLang"):
            self.assertEqual(by[code]["en_gap"], 0, code)
            self.assertEqual(by[code]["verdict"], "NEEDS-TRANSLATION", code)
            self.assertTrue(any("translate_passages.py" in c and "--lang" not in c for c in by[code]["commands"]))

    def test_gaps_over_allowance_point_at_the_source_and_cost_nothing(self):
        s = self.stats()["Holey"]
        self.assertEqual(s["en_gap"], 10)
        self.assertEqual(s["verdict"], "NEEDS-TRANSLATION")
        self.assertFalse(any("translate_passages.py" in c for c in s["commands"]), s["commands"])
        self.assertTrue(any("classify_noise.py --doc Holey --running-heads" in c for c in s["commands"]))
        self.assertEqual(s["est_usd"], 0.0)

    def test_outcomes_path_and_columns(self):
        s = self.stats(outcomes=self.tmp / "absent.jsonl")["Gappy"]
        self.assertEqual((s["en_gap"], s["hi_gap"]), (1, 1), "only the low-quality row without a ledger")
        self.assertEqual(s["verdict"], "NEEDS-TRANSLATION")
        self.assertIn("en_gap", self.cs.COLS)
        self.assertIn("hi_gap", self.cs.row_for(s))


class RunningHeads(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = Path(tempfile.mkdtemp(prefix="heads_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('M')")
        self.heads, self.keep = [], []
        for pg in range(1, 7):
            rows = [(HEAD + " " + devnum(40 + pg), "", "head")]
            if pg <= 4:
                rows.append((UVACA, "", "keep"))           # speaker line: real text
            rows += [(SA + " \u0964", "fine", "keep"), (SA + " \u0965" + devnum(pg) + "\u0965", "", "keep")]   # a refrain
            if pg <= 2:
                rows.append(("\u0905\u0927\u094d\u092f\u093e\u092f\u0903 \u096b", "", "keep"))  # only 2 pages
            for i, (t, en, kind) in enumerate(rows):
                pid = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation) "
                                  "VALUES(1,?,?,?,'mula',?)", (pg, i, t, en)).lastrowid
                (self.heads if kind == "head" else self.keep).append(pid)
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *a):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "classify_noise.py"), "--db", self.db, *a],
                              capture_output=True, text=True, encoding="utf-8", timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING="utf-8"))

    def noise(self):
        con = sqlite3.connect(self.db)
        try:
            return {r[0] for r in con.execute("SELECT id FROM passages WHERE text_type='noise'")}
        finally:
            con.close()

    def test_finds_only_the_running_head(self):
        import classify_noise
        importlib.reload(classify_noise)
        con = sqlite3.connect(self.db)
        hits, groups = classify_noise.running_heads(con, "M", 3, 60)
        con.close()
        self.assertEqual(sorted(h[0] for h in hits), sorted(self.heads))
        self.assertEqual([(g[0], g[2], g[3], g[4]) for g in groups], [("M", 6, 6, 0)])

    def test_dry_run_then_apply(self):
        r = self.run_cli("--doc", "M", "--running-heads", "--show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Total: 6", r.stdout)
        self.assertNotIn("OCR fragments", r.stdout)
        self.assertEqual(self.noise(), set(), "dry run writes nothing")
        r = self.run_cli("--doc", "M", "--running-heads", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.noise(), set(self.heads))

    def test_default_mode_unchanged(self):
        r = self.run_cli("--doc", "M")
        self.assertIn("none found", r.stdout)


if __name__ == "__main__":
    unittest.main()
