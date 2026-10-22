# -*- coding: ascii -*-
"""FIDELITY_2026_10_22: source_fidelity.py reads a text's letters against an e-text, akshara by akshara, read-only and
free. The folding (what editions and typesetting disturb and the meaning does not), the aksharas, finding a unit and
aligning it (a substitution is one error; a unit the print gives twice is read where it agrees best), one print read
twice (own errors and shared ones), the readers (the database, a witness, the page JSONL), the report, the ledger, and
that the database is never written. The verses are the Bhagavad Gita's first four."""
import contextlib, hashlib, io, json, os, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "FIDELITY_2026_10_22"
SRC = SCRIPTS / "source_fidelity.py"
HERE = SRC.exists() and MARK.encode() in SRC.read_bytes()

V1 = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u0902\u091c\u092f \u0965 \u0967 \u0965"
V2 = "\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938\u094d\u0924\u0926\u093e \u0964 \u0906\u091a\u093e\u0930\u094d\u092f\u092e\u0941\u092a\u0938\u0902\u0917\u092e\u094d\u092f \u0930\u093e\u091c\u093e \u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d \u0965 \u0968 \u0965"
V3 = "\u092a\u0936\u094d\u092f\u0948\u0924\u093e\u0902 \u092a\u093e\u0923\u094d\u0921\u0941\u092a\u0941\u0924\u094d\u0930\u093e\u0923\u093e\u092e\u093e\u091a\u093e\u0930\u094d\u092f \u092e\u0939\u0924\u0940\u0902 \u091a\u092e\u0942\u092e\u094d \u0964 \u0935\u094d\u092f\u0942\u0922\u093e\u0902 \u0926\u094d\u0930\u0941\u092a\u0926\u092a\u0941\u0924\u094d\u0930\u0947\u0923 \u0924\u0935 \u0936\u093f\u0937\u094d\u092f\u0947\u0923 \u0927\u0940\u092e\u0924\u093e \u0965 \u0969 \u0965"
V4 = "\u0905\u0924\u094d\u0930 \u0936\u0942\u0930\u093e \u092e\u0939\u0947\u0937\u094d\u0935\u093e\u0938\u093e \u092d\u0940\u092e\u093e\u0930\u094d\u091c\u0941\u0928\u0938\u092e\u093e \u092f\u0941\u0927\u093f \u0964 \u092f\u0941\u092f\u0941\u0927\u093e\u0928\u094b \u0935\u093f\u0930\u093e\u091f\u0936\u094d\u091a \u0926\u094d\u0930\u0941\u092a\u0926\u0936\u094d\u091a \u092e\u0939\u093e\u0930\u0925\u0903 \u0965 \u096a \u0965"
V2_SPLIT = "\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935 \u0905\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0903 \u0924\u0926\u093e \u0964 \u0906\u091a\u093e\u0930\u094d\u092f\u092e\u094d \u0909\u092a\u0938\u0902\u0917\u092e\u094d\u092f \u0930\u093e\u091c\u093e \u0935\u091a\u0928\u092e\u094d \u0905\u092c\u094d\u0930\u0935\u0940\u0924\u094d"


def sf():
    import source_fidelity
    return source_fidelity


@unittest.skipUnless(HERE, "FIDELITY_2026_10_22 is not here")
class TheFolding(unittest.TestCase):
    def test_spaces_punctuation_numbers_and_latin_go(self):
        S = sf()
        self.assertEqual(S.norm("\u0930\u093e\u092e: \u0964 \u0965 \u0967\u0968 abc 3"), S.norm("\u0930\u093e\u092e\u0903"))

    def test_nasal_final_m_candrabindu_are_the_anusvara(self):
        S = sf()
        self.assertEqual(S.norm("\u092a\u093e\u0923\u094d\u0921\u0935"), S.norm("\u092a\u093e\u0902\u0921\u0935"))
        self.assertEqual(S.norm("\u0924\u092e\u094d \u0915\u0930\u094b\u0924\u093f"), S.norm("\u0924\u0902 \u0915\u0930\u094b\u0924\u093f"))
        self.assertEqual(S.norm("\u0939\u0901\u0938"), S.norm("\u0939\u0902\u0938"))

    def test_final_m_before_a_vowel_is_joined_not_the_anusvara(self):
        S = sf()
        self.assertEqual(S.norm("\u0935\u091a\u0928\u092e\u094d \u0905\u092c\u094d\u0930\u0935\u0940\u0924\u094d"), S.norm("\u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d"))
        self.assertEqual(S.norm("\u092a\u094d\u0930\u093e\u0917\u094d \u0905\u0938\u094d\u0924\u092e\u094d \u0909\u0926\u0947\u0924\u093f"), S.norm("\u092a\u094d\u0930\u093e\u0917\u0938\u094d\u0924\u092e\u0941\u0926\u0947\u0924\u093f"))

    def test_accents_avagraha_nukta_go(self):
        S = sf()
        self.assertEqual(S.norm("\u0905\u0952\u0917\u094d\u0928\u093f\u092e\u0940\u0951\u0933\u0947"), S.norm("\u0905\u0917\u094d\u0928\u093f\u092e\u0940\u0933\u0947"))
        self.assertEqual(S.norm("\u0938\u094b\u093d\u092f\u092e\u094d"), S.norm("\u0938\u094b\u092f\u092e\u094d"))
        self.assertEqual(S.norm("\u0921\u093c"), S.norm("\u0921"))

    def test_ch_folds_only_when_asked(self):
        S = sf()
        self.assertEqual(S.norm("\u0917\u091a\u094d\u091b\u0924\u093f", True), S.norm("\u0917\u091a\u0924\u093f", True))
        self.assertEqual(S.norm("\u091b\u093e\u092f\u093e", True), S.norm("\u091a\u093e\u092f\u093e", True))
        self.assertNotEqual(S.norm("\u0917\u091a\u094d\u091b\u0924\u093f"), S.norm("\u0917\u091a\u0924\u093f"))

    def test_aksharas(self):
        S = sf()
        self.assertEqual(S.aksharas(S.norm("\u0915\u094d\u0937\u0924\u094d\u0930\u093f\u092f\u0903")), ["\u0915\u094d\u0937", "\u0924\u094d\u0930\u093f", "\u092f\u0903"])
        self.assertEqual(S.aksharas(S.norm("\u0938\u0902\u091c\u092f")), ["\u0938\u0902", "\u091c", "\u092f"])
        self.assertEqual(S.aksharas("\u093e"), ["\u093e"])          # a vowel sign alone is an akshara of its own


@unittest.skipUnless(HERE, "FIDELITY_2026_10_22 is not here")
class TheAlignment(unittest.TestCase):
    def units(self, *vs):
        S = sf()
        return [S.norm(v) for v in vs]

    def test_exact_reading_and_one_substitution(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        pages = [(1, V1 + "\n" + V2), (2, V3.replace("\u0927\u0940\u092e\u0924\u093e", "\u0927\u0940\u092e\u0928\u093e") + "\n" + V4)]
        res = S.measure(units, pages, False)
        self.assertEqual([r["err"] for r in res], [0, 0, 1, 0])
        self.assertEqual([r["page"] for r in res], [1, 1, 2, 2])

    def test_one_substitution_in_an_akshara_is_one_error(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        res = S.measure(units, [(1, V1.replace("\u0938\u0902\u091c\u092f", "\u0938\u0902\u091a\u092f")), (2, V2 + V3 + V4)], False)
        self.assertEqual(res[0]["err"], 1)
        self.assertIn(("\u091c", "\u091a"), res[0]["diffs"])

    def test_text_beyond_the_unit_is_not_counted(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        page = "\u092d\u0942\u092e\u093f\u0915\u093e \u0907\u0924\u093f \u0917\u094d\u0930\u0928\u094d\u0925\u0938\u094d\u092f \u0906\u0930\u092e\u094d\u092d\u0903 " + V1 + " \u0905\u0925 \u091f\u0940\u0915\u093e \u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0907\u0924\u093f " + V2 + V3 + V4
        res = S.measure(units, [(1, page)], False)
        self.assertEqual(res[0]["err"], 0)

    def test_a_unit_given_twice_is_read_where_it_agrees(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        pages = [(1, V1), (2, V2_SPLIT + "\n" + V4), (3, V2), (4, V3)]
        res = S.measure(units, pages, False)
        self.assertEqual(res[1]["err"], 0)
        self.assertEqual(res[1]["page"], 3)

    def test_a_unit_not_there_is_not_found(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        res = S.measure(units, [(1, V1 + V2 + V4)], False)
        self.assertIsNone(res[2])
        s = S.summarize(["1.1", "1.2", "1.3", "1.4"], units, res, 1, 2)
        self.assertEqual((s["found"], s["missing_in_span"], s["missing_refs"]), (3, 1, ["1.3"]))
        self.assertEqual(s["exact_pct"], 100.0)

    def test_one_print_two_readings(self):
        S = sf()
        units = self.units(V1, V2, V3, V4)
        rest = V2 + V3 + V4
        a = V1.replace("\u092e\u093e\u092e\u0915\u093e\u0903", "\u092e\u093e\u092e\u0915\u0903").replace("\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947", "\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0924\u094d\u0930\u0947")
        b = V1.replace("\u092e\u093e\u092e\u0915\u093e\u0903", "\u092e\u093e\u092e\u0915\u0903").replace("\u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903", "\u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u093e")
        ra = S.measure(units, [(1, a), (2, rest)], False)
        rb = S.measure(units, [(1, b), (2, rest)], False)
        p = S.pair(units, ra, rb)
        self.assertEqual((p["own_a"], p["own_b"], p["shared"]), (1, 1, 1))
        self.assertEqual(p["units"], 4)

    def test_the_steps(self):
        S = sf()
        self.assertEqual(S.step_of(own=0.5), "faithful")
        self.assertEqual(S.step_of(own=3.6), "close")
        self.assertEqual(S.step_of(own=24.6), "damaged")
        self.assertEqual(S.step_of(agree=98.0), "faithful")
        self.assertEqual(S.step_of(agree=85.0), "differs")     # without a second reading: misreading or edition
        self.assertEqual(S.step_of(agree=78.0), "damaged")
        self.assertEqual(S.step_of(), "not measured")


def _db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
        CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT, category TEXT, src_path TEXT, glossary TEXT, created_at TEXT);
        CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT,
            translation TEXT, verse_ref TEXT, text_type TEXT, ocr_engine TEXT);
    """)
    con.execute("INSERT INTO docs (id, code, category) VALUES (1, 'gita_scan', 'itihasa'), (2, 'gita_scan__w_gretil', 'itihasa')")
    rows = [(1, 1, 1, V1, "Dhritarashtra said", None, "mula", "gemini-vision:gemini-2.5-flash"),
            (1, 1, 2, V2.replace("\u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d", "\u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0926\u094d"), "", None, "mula", "gemini-vision:gemini-2.5-flash"),
            (1, 2, 1, V3, "", None, "mula", "gemini-vision:gemini-2.5-flash"),
            (1, 2, 2, "Introduction by the editor", "", None, "frontmatter", "gemini-vision:gemini-2.5-flash"),
            (1, 2, 3, V4, "", None, "mula", "gemini-vision:gemini-2.5-flash")]
    for i, v in enumerate([V1, V2, V3, V4]):
        rows.append((2, 1, i + 1, v, "", "1.%d" % (i + 1), "mula", "etext:gretil"))
    con.executemany("INSERT INTO passages (doc_id, page_no, idx, text, translation, verse_ref, text_type, ocr_engine) "
                    "VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


@unittest.skipUnless(HERE, "FIDELITY_2026_10_22 is not here")
class TheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fid_"))
        self.cwd = os.getcwd()
        (self.tmp / "data" / "raw").mkdir(parents=True)
        (self.tmp / "data" / "raw_vision").mkdir(parents=True)
        w = self.tmp / "data" / "raw_witness" / "gita__w_gretil"
        w.mkdir(parents=True)
        recs = [{"text": v, "engine": "etext:gretil", "page_no": 1, "verse_ref": "1.%d" % (i + 1), "text_type": "mula",
                 "meta": {}} for i, v in enumerate([V1, V2, V3, V4])]
        recs.append({"text": V1, "engine": "etext:gretil", "page_no": 2, "verse_ref": "1.1", "text_type": "mula",
                     "meta": {"after_separator": True}})
        (w / "gita__w_gretil_0001.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs),
                                                       encoding="utf-8")
        tess = {1: V1.replace("\u0927\u0930\u094d\u092e", "\u0918\u0930\u094d\u092e") + "\n" + V2.replace("\u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928", "\u0926\u0941\u092f\u094b\u0927\u0928"),
                2: V3.replace("\u092a\u0941\u0924\u094d\u0930\u0947\u0923", "\u092a\u0941\u091a\u0947\u0923") + "\n" + V4}
        for p, t in tess.items():
            (self.tmp / "data" / "raw" / ("gita_scan_%04d.jsonl" % p)).write_text(
                json.dumps({"engine": "tesseract", "page_no": p, "text": t}, ensure_ascii=False), encoding="utf-8")
            (self.tmp / "data" / "raw_vision" / ("gita_scan_%04d.jsonl" % p)).write_text(
                json.dumps({"engine": "gemini-vision:gemini-2.5-flash", "page_no": p,
                            "text": t.replace("\u0918\u0930\u094d\u092e", "\u0927\u0930\u094d\u092e").replace("\u0926\u0941\u092f\u094b\u0927\u0928", "\u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928").replace("\u092a\u0941\u091a\u0947\u0923", "\u092a\u0941\u0924\u094d\u0930\u0947\u0923")},
                           ensure_ascii=False), encoding="utf-8")
        self.db = self.tmp / "data" / "context.db"
        _db(self.db)
        self.out = self.tmp / "out"

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def main(self, *args):
        S = sf()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(["--root", str(self.tmp), "--out-dir", str(self.out)] + list(args))
        os.chdir(self.cwd)
        return rc, buf.getvalue()

    def md5(self):
        return hashlib.md5(self.db.read_bytes()).hexdigest()

    def test_witness_against_the_database_and_both_ocrs(self):
        before = self.md5()
        rc, out = self.main("--ref", "witness:gita__w_gretil", "--cand", "db:gita_scan", "--cand", "raw:gita_scan",
                            "--cand", "vision:gita_scan", "--pair", "db:gita_scan,raw:gita_scan")
        self.assertEqual(rc, 0)
        self.assertIn("its appendix left out", out)
        self.assertIn("found 4 of 4 units", out)
        self.assertIn("VERDICT: db:gita_scan: faithful", out)
        rep = json.loads((self.out / "gita__w_gretil__gita_scan.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["mark"], MARK)
        self.assertEqual(rep["units"], 4)
        self.assertEqual(rep["readings"]["vision:gita_scan"]["errors"], 0)
        self.assertEqual(rep["readings"]["db:gita_scan"]["errors"], 1)          # vacanamabravId, its only slip
        self.assertEqual(rep["readings"]["raw:gita_scan"]["errors"], 3)
        p = rep["pairs"][0]
        self.assertEqual((p["own_a"], p["own_b"], p["shared"]), (1, 3, 0))
        self.assertEqual(self.md5(), before)                                     # never written

    def test_the_database_as_the_reference_leaves_front_matter_out(self):
        rc, out = self.main("--ref", "db:gita_scan__w_gretil", "--cand", "db:gita_scan", "--no-write")
        self.assertEqual(rc, 0)
        self.assertIn("4 units", out)
        self.assertFalse(self.out.exists())                                      # --no-write

    def test_a_prefix(self):
        rc, out = self.main("--ref", "witness:gita__w_gretil", "--prefix", "1.3", "--cand", "db:gita_scan", "--no-write")
        self.assertIn("1 units", out)

    def test_a_file_reading(self):
        try:
            import etext_witness  # noqa: F401
        except Exception:
            self.skipTest("etext_witness.py is not importable here")
        f = self.tmp / "sources" / "gita_djvu.txt"
        f.parent.mkdir(parents=True)
        f.write_text(V1 + "\n\n" + V2 + "\n\n" + V3.replace("\u091a\u092e\u0942\u092e\u094d", "\u091a\u092e\u0942\u0938\u094d") + "\n\n" + V4, encoding="utf-8")
        rc, out = self.main("--ref", "witness:gita__w_gretil", "--cand", "file:sources/gita_djvu.txt", "--no-write")
        self.assertEqual(rc, 0)
        self.assertIn("found 4 of 4 units", out)

    def test_the_ledger(self):
        (self.tmp / "data" / "source_judged").mkdir(parents=True)
        (self.tmp / "data" / "source_judged" / "gita_scan.json").write_text(json.dumps({"level": "cosmetic"}))
        (self.tmp / "data" / "source_verdicts.jsonl").write_text(
            json.dumps({"doc": "gita_scan__w_gretil", "status": "witness"}) + "\n")
        self.main("--ref", "witness:gita__w_gretil", "--cand", "db:gita_scan", "--cand", "raw:gita_scan",
                  "--pair", "db:gita_scan,raw:gita_scan")
        csv_path = self.tmp / "ledger.csv"
        rc, out = self.main("--ledger", "--csv", str(csv_path))
        self.assertEqual(rc, 0)
        self.assertIn("2 texts with passages", out)
        import csv
        rows = {r["doc"]: r for r in csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8-sig")))}
        self.assertEqual(rows["gita_scan"]["source"], "vision")
        self.assertTrue(0.0 < float(rows["gita_scan"]["own_per100"]) < 1.0)                # one slip in 4 verses
        self.assertTrue(rows["gita_scan"]["reading"].startswith("faithful"))
        self.assertEqual(rows["gita_scan__w_gretil"]["reading"], "an e-text witness, local only")
        self.assertEqual(rows["gita_scan"]["english_pct"], "20.0")


@unittest.skipUnless(HERE, "FIDELITY_2026_10_22 is not here")
class TheHouseStyle(unittest.TestCase):
    def test_ascii_and_free(self):
        b = SRC.read_bytes()
        self.assertTrue(all(c < 128 for c in b))
        for word in (b"urllib", b"requests", b"anthropic", b"genai", b"INSERT ", b"UPDATE ", b"DELETE "):
            self.assertNotIn(word, b)
        self.assertIn(b"mode=ro", b)

    def test_this_test_is_ascii(self):
        self.assertTrue(all(c < 128 for c in Path(__file__).read_bytes()))


if __name__ == "__main__":
    unittest.main()
