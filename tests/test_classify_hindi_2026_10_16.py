# -*- coding: ascii -*-
"""CLASSIFY_HINDI_2026_10_16: an edition's own Hindi read by its words (scripts/edition_hindi.py) and tagged
'frontmatter' (scripts/classify_hindi.py): a dry run, the safe default, --with-english (archived, cleared, its search
row and vector), --reject-scholarly, --undo; scholar_translate's readiness, --status and --triage; the Library's count
and the reader; classify_doc's stage; the patcher's replay. Temp files only; nothing is called."""
import importlib.util, io, json, shutil, sqlite3, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import edition_hindi as EH                      # noqa: E402
import classify_hindi as CH                     # noqa: E402

ST = base.ST
MARK = b"CLASSIFY_HINDI_2026_10_16"
APPLIED = hasattr(ST, "edition_hindi")
SONNET = "anthropic:claude-sonnet-5-5"

# the Karanagama (15 Oct backup): its editor's Hindi, and its Sanskrit
HI_1 = "\u092d\u0938\u094d\u092e \u0926\u094d\u0935\u093e\u0930\u093e \u0915\u0930\u0915\u0947 \u0907\u0937\u094d\u091f, \u092a\u094d\u0930\u093e\u0923 \u0914\u0930 \u092d\u093e\u0935-\u0930\u0942\u092a\u0940 \u0924\u094d\u0930\u093f\u0935\u093f\u0927 \u0932\u093f\u0919\u094d\u0917\u094b\u0902 \u0915\u093e \u0909\u092a\u0926\u0947\u0936 \u0915\u0930\u0947 \u0965"
HI_2 = "\u092c\u094d\u0930\u093e\u0939\u094d\u092e\u0923, \u0915\u094d\u0937\u0924\u094d\u0930\u093f\u092f, \u0935\u0948\u0936\u094d\u092f, \u0936\u0942\u0926\u094d\u0930 \u092f\u093e \u0905\u0928\u094d\u0924\u094d\u092f\u091c; \u092f\u093e \u092a\u0941\u0930\u0941\u0937, \u0928\u093e\u0930\u0940 \u092f\u093e \u0928\u092a\u0941\u0902\u0938\u0915 \u0938\u092d\u0940 \u092e\u094b\u0915\u094d\u0937 \u0915\u0947 \u0905\u0927\u093f\u0915\u093e\u0930\u0940 \u0939\u0948\u0902 \u0965"
HI_3 = "\u092e\u0923\u094d\u0921\u092a \u092e\u0947\u0902 \u0928\u094c \u0905\u0925\u0935\u093e \u092a\u093e\u0902\u091a \u0905\u0925\u0935\u093e \u090f\u0915 \u0915\u0941\u0923\u094d\u0921 \u0915\u093e \u0928\u093f\u0930\u094d\u092e\u093e\u0923 \u0915\u0930\u093e\u090f\u0901 \u0964 (\u092f\u0926\u093f \u0928\u094c \u0915\u0941\u0923\u094d\u0921 \u092c\u0928\u093e\u0928\u0947 \u0939\u094b\u0902 \u0924\u092c) \u092a\u0942\u0930\u094d\u0935 \u092e\u0947\u0902 \u091a\u094c\u0915\u094b\u0930, \u0905\u0917\u094d\u0928\u093f \u0915\u094b\u0923 \u092e\u0947\u0902 \u092a\u0940\u092a\u0932 \u0915\u0947 \u0906\u0915\u093e\u0930 \u0915\u093e \u0965"
HI_WM = HI_2 + "\nDigitized by eGangotri\nJangamwadi Math Collection"
SA_1 = "\u0928\u093f\u0935\u0947\u0926\u092f\u093f\u0937\u094d\u092f\u0928\u094d\u0928\u091c\u094d\u091e\u093e\u0928\u0902 \u0926\u0926\u094d\u092f\u093e\u0926\u093e\u0926\u094c \u0936\u093f\u0930\u094b\u0935\u094d\u0930\u0924\u092e\u094d \u0964 \u0905\u0928\u094d\u092f\u0925\u093e \u0917\u0941\u0930\u0941\u0936\u093f\u0937\u094d\u092f\u094c \u0924\u094c \u092a\u0924\u0924\u094b \u0928\u0930\u0915\u093e\u092e\u094d\u092c\u0941\u0927\u094c \u0965"
SA_2 = "\u0936\u0930\u0940\u0930\u092a\u093e\u0924\u092a\u0930\u094d\u092f\u0928\u094d\u0924\u0902 \u0928 \u091c\u0939\u0940\u0939\u093f \u0935\u094d\u0930\u0924\u093e\u0928\u094d\u092f\u092a\u093f \u0964 \u0926\u0943\u0922\u0935\u094d\u0930\u0924\u093e\u092e\u093f\u0924\u093f \u092a\u094d\u0930\u094b\u0915\u094d\u0924\u094d\u0935\u093e \u0926\u0926\u093e\u0924\u094d \u092a\u091e\u094d\u091a\u0947\u0928\u094d\u0926\u094d\u0930\u093f\u092f\u093e\u0930\u094d\u092a\u0923\u093e\u092e\u094d \u0965"
SA_WEAK = "\u0915\u094b \u0928\u0941 \u0915\u0930\u0947 \u0917\u092f\u093e \u0924\u0938\u094d\u092f \u0935\u0928\u0902 \u0936\u0941\u092d\u0902 \u0917\u091a\u094d\u091b\u0924\u093f \u092a\u0941\u0930\u0902 \u092a\u094d\u0930\u0924\u093f \u0930\u093e\u091c\u093e"   # Sanskrit forms that are Hindi words too
INDEX = "\u0967\u0968 \u0938\u0941\u092d\u0926\u094d\u0930\u093e-\u0908\u096c \u0964 \u0967\u096a \u0938\u0942\u0915\u094d\u0937\u094d\u092e\u0902-\u0915\u093e"
DEBRIS = "\u092c\u093e \u096e Qo on wd \u096c \u092f\u0939 \u0939\u0948 trio \u092f\u0947 \u0928\u0939\u0940\u0902 \u0914\u0930 \u0915\u093f \u0915\u0947 \u0932\u093f\u090f"


def run(fn, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = fn(list(argv))
    return rc, out.getvalue()


class TheReading(unittest.TestCase):
    def test_hindi_and_sanskrit(self):
        for t in (HI_1, HI_2, HI_3, HI_WM):
            self.assertTrue(EH.is_hindi(t), EH.hindi_of(t))
        for t in (SA_1, SA_2, SA_WEAK, base.V6, base.V7, base.V8, base.V9, INDEX, DEBRIS, "", None):
            self.assertFalse(EH.is_hindi(t), (t, EH.hindi_of(t)))
        self.assertEqual(EH.hindi_of(INDEX), (False, "fewer than 6 words"))
        self.assertEqual(EH.hindi_of(DEBRIS)[1], "OCR debris (Latin words)")
        self.assertTrue(all(ord(c) < 128 for c in Path(EH.__file__).read_text(encoding="utf-8")))


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        self.log = self.td / "log.jsonl"
        import db_utils
        con = db_utils.connect(str(self.db))
        ST.ensure_schema(con)
        con.execute("CREATE TABLE IF NOT EXISTS passage_embeddings(passage_id INTEGER, model TEXT, dim INTEGER, vec BLOB, "
                    "updated_at TEXT)")
        con.execute("INSERT INTO docs(code, category) VALUES ('Karan', 'agama')")
        did = con.execute("SELECT id FROM docs WHERE code = 'Karan'").fetchone()[0]
        rows = [(SA_1, "", "mula"), (HI_1, "", "mula"), (SA_2, "Until the body falls. //", "mula"),
                (HI_2, "Brahmins, Kshatriyas ... all are entitled to liberation. //", "mula"), (HI_WM, "", "mula"),
                (HI_3, "", "noise")]
        for k, (t, en, tt) in enumerate(rows, 1):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, verse_ref, text_type, quality_score, "
                        "engine, translated_at) VALUES (?, 2, ?, ?, ?, ?, ?, 0.9, ?, ?)",
                        (did, k, t, en, "2.%d" % k, tt, "gemini:gemini-2.5-flash" if en else None,
                         "2026-10-15T10:00:00+00:00" if en else None))
        con.commit()
        self.k = ST.load_text(con, "Karan")
        for x in self.k:
            if x["english"]:
                con.execute("INSERT INTO passage_embeddings VALUES (?, 'm', 4, X'00000000', '2026-10-15')", (x["id"],))
        if "passages_fts" in {r[0] for r in con.execute("SELECT name FROM sqlite_master")}:
            for x in self.k:
                con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES (?, ?, '', ?)",
                            (x["id"], x["text"], x["english"] or ""))
        con.execute("INSERT INTO translations_l10n(passage_id, lang, translation) VALUES (?, 'hi', 'h')", (self.k[3]["id"],))
        for x in self.k[:4]:
            ST.store(con, {"passage_id": x["id"], "doc_code": "Karan", "page_no": x["page"], "idx": x["idx"],
                           "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]), "translation": "S%s //" % x["ref"],
                           "notes": "[]", "critique": "[]", "status": "passed", "fidelity": 5, "fluency": 5,
                           "engine": SONNET, "judge_engine": ST.JUDGE, "cost_usd": 0.05,
                           "created_at": "2026-10-15T13:00:00+00:00"})
        con.commit(); con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def q(self, sql, *a):
        con = sqlite3.connect(str(self.db))
        try:
            return con.execute(sql, a).fetchall()
        finally:
            con.close()

    def types(self):
        return [r[0] for r in self.q("SELECT COALESCE(text_type, 'mula') FROM passages p JOIN docs d ON d.id = p.doc_id "
                                     "WHERE d.code = 'Karan' ORDER BY idx")]

    def ch(self, *x):
        return run(CH.main, "--db", str(self.db), "--log", str(self.log), *x)


class TheTool(_Fixture):
    def test_a_dry_run_then_the_safe_default(self):
        before = base.md5(self.db)
        rc, o = self.ch()
        self.assertEqual(rc, 0, o)
        self.assertIn("Karan: 3 passage(s) read as Hindi; 1 carry English (made from the Hindi; 1 vector(s)); 2 scholarly "
                      "English; 1 a Hindi translation (translations_l10n: not touched); 2 to tag", o)
        self.assertNotIn("MBh01:", o, "nothing in the Sanskrit-only text")
        self.assertIn("VERDICT: 2 passage(s) would be tagged frontmatter, 1 left (they carry English: --with-english)", o)
        self.assertEqual(base.md5(self.db), before, "a dry run writes nothing")
        rc, o = self.ch("--doc", "Karan", "--apply")
        self.assertEqual(rc, 0, o)
        self.assertEqual(self.types(), ["mula", "frontmatter", "mula", "mula", "frontmatter", "noise"])
        self.assertIn("VERDICT: 2 tagged frontmatter; 0 English archived and cleared (0 vector(s) removed); 0 scholarly "
                      "row(s) rejected, 1 left (they carry English)", o)
        rc, o = self.ch("--doc", "Karan", "--reject-scholarly", "--with-english")
        self.assertEqual(rc, 1); self.assertIn("--by is needed", o)

    def test_with_english_reject_and_undo(self):
        k3 = self.k[3]["id"]
        rc, o = self.ch("--doc", "Karan", "--with-english", "--reject-scholarly", "--by", "Dhruv", "--apply")
        self.assertEqual(rc, 0, o)
        self.assertIn("VERDICT: 3 tagged frontmatter; 1 English archived and cleared (1 vector(s) removed); 2 scholarly "
                      "row(s) rejected;", o)
        self.assertEqual(self.types()[3], "frontmatter")
        self.assertEqual(self.q("SELECT translation, translated_at FROM passages WHERE id = ?", k3)[0], ("", None))
        h = self.q("SELECT translation, engine, reason FROM translation_history WHERE passage_id = ?", k3)
        self.assertEqual(h, [("Brahmins, Kshatriyas ... all are entitled to liberation. //", "gemini:gemini-2.5-flash",
                              "edition-hindi CLASSIFY_HINDI_2026_10_16")])
        self.assertEqual(self.q("SELECT COUNT(*) FROM passage_embeddings WHERE passage_id = ?", k3), [(0,)])
        if self.q("SELECT name FROM sqlite_master WHERE name = 'passages_fts'"):
            self.assertEqual(self.q("SELECT translation FROM passages_fts WHERE rowid = ?", k3), [("",)])
        self.assertEqual(self.q("SELECT translation FROM translations_l10n WHERE passage_id = ?", k3), [("h",)],
                         "translations_l10n is not touched")
        rv = self.q("SELECT review_verdict, reviewed_by, review_note FROM scholar_translations WHERE passage_id = ?", k3)
        self.assertEqual(rv[0][:2], ("reject", "Dhruv")); self.assertIn("edition's own Hindi", rv[0][2])
        self.assertEqual(self.q("SELECT review_verdict FROM scholar_translations WHERE passage_id = ?", self.k[1]["id"]),
                         [("reject",)])
        self.assertIsNone(self.q("SELECT review_verdict FROM scholar_translations WHERE passage_id = ?",
                                 self.k[0]["id"])[0][0], "the Sanskrit's row is not touched")
        self.assertEqual(self.q("SELECT translation FROM passages WHERE id = ?", self.k[2]["id"]),
                         [("Until the body falls. //",)], "the Sanskrit's English is kept")
        rc, o = self.ch("--doc", "Karan", "--undo")
        self.assertIn("VERDICT: 3 passage(s) would be put back; nothing written", o)
        rc, o = self.ch("--doc", "Karan", "--undo", "--apply", "--by", "Dhruv")
        self.assertEqual(rc, 0, o); self.assertIn("VERDICT: 3 passage(s) put back", o)
        self.assertEqual(self.types(), ["mula", "mula", "mula", "mula", "mula", "noise"])
        self.assertEqual(self.q("SELECT translation, engine, translated_at FROM passages WHERE id = ?", k3),
                         [("Brahmins, Kshatriyas ... all are entitled to liberation. //", "gemini:gemini-2.5-flash",
                           "2026-10-15T10:00:00+00:00")])
        self.assertIsNone(self.q("SELECT review_verdict FROM scholar_translations WHERE passage_id = ?", k3)[0][0])
        acts = [json.loads(x)["action"] for x in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(acts, ["tag"] * 3 + ["undo"] * 3)


@unittest.skipUnless(APPLIED, "CLASSIFY_HINDI_2026_10_16 is not applied here")
class TheScholarAndTheDashboard(_Fixture):
    def test_readiness_status_and_triage(self):
        self.assertEqual(ST.readiness(HI_1, "mula", 0.9), "Hindi prose (the edition's own Hindi), not Sanskrit",
                         "two words of the old list only: the old rule missed it")
        self.assertIsNone(ST.readiness(SA_1, "mula", 0.9))
        import argparse
        con = sqlite3.connect(str(self.db))
        con.execute("UPDATE scholar_translations SET status = 'flagged', fidelity = 2 WHERE passage_id = ?", (self.k[1]["id"],))
        con.commit()
        self.assertEqual(len(ST.triage_rows(con, "Karan", SONNET, ST.load_text(con, "Karan"))), 1)
        con.close()
        self.ch("--doc", "Karan", "--with-english", "--apply")
        con = sqlite3.connect(str(self.db))
        try:
            allp = ST.load_text(con, "Karan")
            lines = ST.status_lines(con, "Karan", allp, argparse.Namespace(pages=None, min_quality=0.35))
            self.assertIn("  %s: 2 of 2 verses (100%%)" % SONNET, lines[0])
            self.assertIn("  set aside: 2 row(s) on passages that are not verse (front matter, noise, an edition's own "
                          "Hindi)", lines)
            self.assertEqual(ST.triage_rows(con, "Karan", SONNET, allp), [])
        finally:
            con.close()

    def test_the_library_and_the_reader(self):
        spec = importlib.util.spec_from_file_location("dashboard_hindi", str(SCRIPTS / "dashboard.py"))
        d = importlib.util.module_from_spec(spec); sys.modules[spec.name] = d; spec.loader.exec_module(d)
        d.JOBS_LOG_PATH = self.td / "jobs.jsonl"
        self.ch("--doc", "Karan", "--with-english", "--apply")
        d._SCHOLAR_COVER.update(key=None)
        con = sqlite3.connect(str(self.db))
        try:
            c = d._scholar_cover(con)["Karan"]
            self.assertEqual((c["verses"], c["set_aside"]), (2, 2))
            self.assertIn("2 set aside (not Sanskrit verse: front matter, noise, the edition&#x27;s own Hindi)",
                          d._scholar_line("Karan", {"Karan": c}))
            rows, n = d._scholar_rows(con, "Karan", "", (), 50, 0)
            self.assertEqual((sorted(k[1] for k in rows), n), ([1, 3], 2), "none on the Hindi")
        finally:
            con.close()
        h = d.app.test_client().get("/reader/Karan").get_data(as_text=True)
        self.assertIn("The edition&#39;s own matter (front matter, noise, or its translation or commentary in a modern "
                      "language): not the Sanskrit, so not translated", h)


class TheStageAndThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "CLASSIFY_HINDI_2026_10_16 is not applied here")
    def test_the_stage(self):
        b = (SCRIPTS / "classify_doc.py").read_bytes()
        self.assertIn(b'("frontmatter", "classify_hindi.py",', b); self.assertIn(MARK, b)

    def test_it_applies_once_to_what_it_found(self):
        files = ("classify_doc.py", "scholar_translate.py", "dashboard.py")
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_hindi_*")) for f in files}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_classify_hindi_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in files:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("edition_hindi.py and scripts/classify_hindi.py are needed", r.stdout)
            for f in ("edition_hindi.py", "classify_hindi.py"):
                shutil.copy2(SCRIPTS / f, t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in files:
                later = sorted(SCRIPTS.glob(f + ".bak_ornament_*"))   # ORNAMENT_2026_10_16 came after (scholar_translate.py)
                later = later or sorted(SCRIPTS.glob(f + ".bak_benchdesk_*"))   # BENCH_DESK_2026_10_16 (dashboard.py)
                self.assertEqual((t / "scripts" / f).read_bytes(), (later[0] if later else SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in files:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "classify_doc.py"
            p.write_bytes(p.read_bytes().replace(b"STAGES = [", b"STAGES = ["  b"  "))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("classify_doc.py: anchor 1 found 0 times (want 1): this is not the file released", r.stdout)
            for f in files:
                self.assertNotIn(MARK, (t / "scripts" / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "edition_hindi.py", SCRIPTS / "classify_hindi.py", SCRIPTS / "patch_classify_hindi_2026_10_16.py",
                  Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
