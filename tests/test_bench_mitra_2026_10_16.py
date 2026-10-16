# -*- coding: ascii -*-
"""BENCH_MITRA_2026_10_16: BM1, the three arms against published translations. chrF as sacrebleu 2.6.0 computes it;
the dataset's IAST written in Devanagari as passages are stored; the sample (a fixed window, its context, the
published English kept for the window only); the ledger (a step's calls into data/context.db as kind bench_<kind>,
doc BM1:<text>, the spend cap counting Google's part only, never twice); the arms, the judge and the report, end to
end, with stand-ins for the scripts and the judge. Temp folders only; a made-up dataset (not the Mitrasamgraha's
text); nothing is called."""
import hashlib, json, random, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bench_mitra as B          # noqa: E402
import cost_tracker              # noqa: E402
import scholar_translate as ST   # noqa: E402

MARK = b"BENCH_MITRA_2026_10_16"
try:
    import iast_utils
    HAVE_TR = iast_utils.is_library_available()
except ImportError:
    HAVE_TR = False

WORDS = ["dharma", "k\u1e63etre", "kuru", "samavet\u0101", "yuyutsava\u1e25", "m\u0101mak\u0101\u1e25", "p\u0101\u1e47\u1e0dav\u0101\u015b", "caiva", "kim", "akurvata",
         "sa\u00f1jaya", "r\u0101j\u0101", "vana\u1e43", "gacchati", "nitya\u1e43", "\u1e5b\u1e63aya\u1e25", "dev\u0101\u1e25", "agni\u1e43", "\u012b\u1e37e", "purohita\u1e43", "yaj\u00f1asya",
         "r\u0325tvijam", "sa\u1e41\u015baya\u1e25"]
KEYS = ("GSD36manu", "GV01rvh")


def dataset(root: Path, n: int = 40, odd_at=4) -> Path:
    """A made-up test set in the dataset's layout: IAST with the words split, a tab, an English line."""
    t = root / "ds" / "data" / "test"
    t.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    for k in KEYS:
        f = next(x for x in B.FILES if x["key"] == k)
        with open(t / f["file"], "w", encoding="utf-8", newline="\n") as fh:
            for i in range(1, n + 1):
                sa = (" ".join(rng.choice(WORDS) for _ in range(8)) + " / " + " ".join(rng.choice(WORDS) for _ in range(6))
                      + " //")
                if i == odd_at:
                    sa = "a\u00ef kuru"   # a sign the transliteration keeps as it is
                fh.write("%s\tPUBLISHED %s line %d: the king went to the forest with the sages.\n" % (sa, k, i))
    return root / "ds"


def ledger(root: Path) -> Path:
    """data/context.db's ledger as it is on 16 Oct: the credit's rows and the spend cap."""
    p = root / "main.db"
    con = sqlite3.connect(p)
    cost_tracker.ensure_usage_schema(con)
    ST.ensure_schema(con)
    con.execute("UPDATE budget_state SET budget_usd = 64.54, spent_usd = 58.93 WHERE id = 1")
    con.execute("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd, passages) VALUES "
                "('2026-10-15T10:00:00Z', 'scholar', 'X', 'anthropic:claude-sonnet-5-5', 110.37, 1)")
    con.execute("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd, passages) VALUES "
                "('2026-10-15T10:00:00Z', 'translation', 'X', 'gemini:gemini-2.5-flash', 0.247, 100)")
    con.commit()
    con.close()
    return p


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


FAKE_CHILD = r'''
import sqlite3, sys
sys.path.insert(0, sys.argv[4])
import scholar_translate as ST
arm, db, code = sys.argv[1], sys.argv[2], sys.argv[3]
con = sqlite3.connect(db)
rows = con.execute("SELECT p.id, p.idx, p.text, p.page_no FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ? "
                   "AND p.page_no = 2 ORDER BY p.idx", (code,)).fetchall()
def spend(kind, engine, cost):
    con.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, cost_usd, passages) VALUES (?,?,?,?,?,?,1)",
                (kind, code, engine, 100.0, float(len(rows)), cost))
if arm in ("flash", "sonnet1"):
    for pid, idx, text, pg in rows:
        con.execute("UPDATE passages SET translation = ? WHERE id = ?", ("%s %s English of verse %d //" % (arm, code, idx), pid))
        spend("translation", "gemini:gemini-2.5-flash" if arm == "flash" else "anthropic:claude-sonnet-5-5", 0.002 if arm == "flash" else 0.01)
else:
    ST.ensure_schema(con)
    for pid, idx, text, pg in rows:
        g = "2.3-2.4" if idx in (3, 4) else None
        ST.store(con, {"passage_id": pid, "doc_code": code, "page_no": pg, "idx": idx, "verse_ref": "2.%d" % idx,
                       "src_hash": ST.src_hash(text), "translation": "scholar %s segment %d //" % (code, idx),
                       "notes": "[]", "critique": "[]", "status": "flagged" if idx == 5 else "passed",
                       "engine": "anthropic:claude-sonnet-5-5", "judge_engine": ST.JUDGE, "fidelity": 5, "fluency": 4,
                       "cost_usd": 0.04, "created_at": "2026-10-16T12:00:00+00:00", "group_ref": g,
                       "group_translation": ("scholar %s the sentence of verses 3 and 4 //" % code) if g else None})
        spend("scholar", "anthropic:claude-sonnet-5-5", 0.0373)
        spend("judge", "gemini:gemini-2.5-flash", 0.0027)
con.commit()
'''


class FakeGemini:
    """judge-v1's stand-in: a score by the English's arm, metered as Gemini meters (cost_tracker.log_api_call)."""
    calls = []

    def __init__(self, a, meta, con):
        self.a, self.meta, self.con = a, meta, con

    def judge(self, src, iast, english):
        FakeGemini.calls.append(english)
        cost = cost_tracker.log_api_call(self.con, kind="judge", doc=self.meta["doc"], engine=self.a.judge_engine,
                                         in_tokens=1000.0, out_tokens=976.0)
        fid = 5 if english.startswith("scholar") else 3 if english.startswith("flash") else 4
        return fid, 4, "a stand-in", cost


class TheChrF(unittest.TestCase):
    PAIRS = [("The king went to the forest.", "The king went into the forest.", 80.733256),
             ("Having heard this, the sage spoke to him.", "Hearing these words the ascetic replied.", 20.462004),
             ("O Agni, we praise thee.", "Agni, the priest of the sacrifice, I praise.", 24.980214),
             ("a", "completely different", 0.0), ("", "something", 0.0)]

    def test_as_sacrebleu(self):
        for h, r, want in self.PAIRS:   # sacrebleu 2.6.0, CHRF() (chrF2), 16 Oct
            self.assertAlmostEqual(B.chrf(B.chrf_stats(h, r)), want, places=5)
        self.assertAlmostEqual(B.corpus_chrf([B.chrf_stats(h, r) for h, r, _w in self.PAIRS]), 30.767924, places=5)

    def test_what_is_compared(self):
        self.assertEqual(B.clean("The *s\u016bta* asked. //  He said:"), "The s\u016bta asked. He said:")
        self.assertEqual(B.fold("S\u0101tav\u0101hana and Sat\u00e1v\u00e1hana"), "satavahana and satavahana")
        self.assertEqual(B.unit_name([3]), "2.3")
        self.assertEqual(B.unit_name([3, 4]), "2.3-2.4")

    def test_a_pair_that_seems_shifted(self):
        refs = {1: "The king went to the forest with his sons.", 2: "The sage spoke of dharma to the gods.",
                3: "The queen wept by the river, alone."}
        t = {"flash": "The queen wept alone by the river.", "scholar": "Alone, the queen wept by the river."}
        self.assertEqual(B.misaligned([2], refs, t, ["flash", "scholar"]), "the line after")
        t = {"flash": "The sage spoke to the gods of dharma.", "scholar": "The sage told the gods of dharma."}
        self.assertIsNone(B.misaligned([2], refs, t, ["flash", "scholar"]))
        self.assertIsNone(B.misaligned([3], refs, {"flash": "The king went to the forest."}, ["flash"]),
                          "only the neighbours that exist")


@unittest.skipUnless(HAVE_TR, "indic-transliteration is not installed")
class TheText(unittest.TestCase):
    def test_iast_as_the_project_writes_it(self):
        self.assertEqual(B.norm_iast("  r\u0325tvijam   sa\u1e41\u015bayah\u0323 "), "\u1e5btvijam sa\u1e43\u015baya\u1e25")
        self.assertEqual(B.to_dev("bhr\u0101mar\u012b ca / unmatto 'ndha\u015b ca //"),
                         "\u092d\u094d\u0930\u093e\u092e\u0930\u0940 \u091a \u0964 \u0909\u0928\u094d\u092e\u0924\u094d\u0924\u094b \u093d\u0928\u094d\u0927\u0936\u094d \u091a \u0965")
        self.assertEqual(B.to_dev("agnim \u012b\u1e37e"), "\u0905\u0917\u094d\u0928\u093f\u092e\u094d \u0908\u0933\u0947",
                         "the Vedic consonant, not the vowel")
        self.assertEqual(B.to_dev("k\u1e37ptam"), "\u0915\u0962\u092a\u094d\u0924\u092e\u094d", "the vowel stays")
        self.assertEqual(B.to_dev("evam || 77 ||"), "\u090f\u0935\u092e\u094d \u0965 \u096d\u096d \u0965")

    def test_what_is_left_out(self):
        self.assertEqual(B.why_not(B.to_dev("a\u00ef kuru"), "an English line here"),
                         "a sign the transliteration did not convert")
        self.assertTrue(B.why_not(B.to_dev("kuru"), "an English line").startswith("scholar_translate.py would leave it out"))
        v = B.to_dev("dharmak\u1e63etre kuruk\u1e63etre samavet\u0101 yuyutsava\u1e25")
        self.assertIsNone(B.why_not(v, "On the field of dharma"))
        self.assertEqual(B.why_not(v, "Kurukshetra."), "the published English is too short")


@unittest.skipUnless(HAVE_TR, "indic-transliteration is not installed")
class TheSample(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = dataset(self.td)
        self.out = self.td / "bm1"
        self.specs = [f for f in B.FILES if f["key"] in KEYS]

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_window_and_its_context(self):
        sm = B.make_sample(self.ds, self.specs)
        self.assertEqual(sm, B.make_sample(self.ds, self.specs), "a fixed seed")
        for k in KEYS:
            w = [x for x in sm["lines"] if x["key"] == k and x["role"] == "window"]
            lead = [x for x in sm["lines"] if x["key"] == k and x["role"] == "lead"]
            tail = [x for x in sm["lines"] if x["key"] == k and x["role"] == "tail"]
            self.assertEqual(len(w), 25)
            self.assertEqual([x["idx"] for x in w], list(range(1, 26)))
            self.assertEqual({x["page"] for x in w}, {2})
            self.assertTrue(len(lead) <= 6 and len(tail) <= 2)
            self.assertEqual([x["line"] for x in w], list(range(w[0]["line"], w[0]["line"] + 25)), "lines in a row")
            self.assertNotIn(4, [x["line"] for x in w], "the line that does not convert is not in a window")
            self.assertTrue(all(x["ref"].startswith("PUBLISHED") for x in w))
            self.assertTrue(all(x["ref"] == "" for x in lead + tail), "the published English of the window only")
            self.assertEqual(sm["head"]["files"][k]["left_out"], {"a sign the transliteration did not convert": 1})

    def test_the_step_and_the_databases(self):
        args = ["--data", str(self.ds), "--out", str(self.out), "--files", ",".join(KEYS)]
        self.assertEqual(B.main(args + ["--sample"]), 0)
        before = md5(self.out / "sample.jsonl")
        con = sqlite3.connect(self.out / "db" / "S.db")
        n = con.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
        self.assertEqual(con.execute("SELECT COUNT(*) FROM passages WHERE page_no = 2").fetchone()[0], 50)
        self.assertEqual(con.execute("SELECT DISTINCT text_type, quality_score FROM passages").fetchall(), [("mula", 1.0)])
        self.assertEqual(sorted(r[0] for r in con.execute("SELECT code FROM docs")), ["Manusmrti", "Rgveda"])
        con.close()
        self.assertEqual(B.main(args + ["--sample"]), 0, "again: kept, the same")
        self.assertEqual(md5(self.out / "sample.jsonl"), before)
        con = sqlite3.connect(self.out / "db" / "S.db")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM passages").fetchone()[0], n)
        con.close()
        p = self.ds / "data" / "test" / "GSD36manu_test.tsv"
        p.write_text(p.read_text(encoding="utf-8").replace("PUBLISHED", "CHANGED"), encoding="utf-8")
        self.assertEqual(B.main(args + ["--sample"]), 1, "another dataset: refused")
        self.assertEqual(md5(self.out / "sample.jsonl"), before)

    def test_never_inside_a_repository(self):
        self.assertFalse(B.outside_repos(REPO / "data" / "bench"))
        self.assertFalse(B.outside_repos(REPO))
        self.assertTrue(B.outside_repos(self.out))
        self.assertEqual(B.main(["--out", str(REPO / "data" / "bm1"), "--sample"]), 1)
        self.assertFalse((REPO / "data" / "bm1").exists())


class TheLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.main = ledger(self.td)
        self.bench = self.td / "F.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_push_and_pull(self):
        import claude_engine as ce
        m = sqlite3.connect(self.main)
        b = B.connect(self.bench)
        try:
            self.assertEqual(B.pull(b, m), 1, "the credit's rows only")
            self.assertEqual(b.execute("SELECT budget_usd, spent_usd FROM budget_state").fetchone(), (64.54, 58.93))
            self.assertAlmostEqual(ce.credit(b)["left"], ce.credit(m)["left"])
            b.execute("INSERT INTO usage_log(kind, doc, engine, in_chars, out_chars, in_tokens, out_tokens, cost_usd, "
                      "passages) VALUES ('translation', 'Rgveda', 'gemini:gemini-2.5-flash', 10, 20, 100, 800, 0.0025, 1)")
            b.execute("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, cost_usd, passages) VALUES "
                      "('scholar', 'Rgveda', 'anthropic:claude-sonnet-5-5', 1500, 900, 0.04, 1)")
            b.commit()
            r = B.push(b, m, "flash", self.td / "spend.jsonl")
            self.assertEqual((r["rows"], round(r["google"], 4), round(r["claude"], 4)), (2, 0.0025, 0.04))
            got = m.execute("SELECT kind, doc, engine FROM usage_log WHERE kind LIKE 'bench_%' ORDER BY id").fetchall()
            self.assertEqual(got, [("bench_translation", "BM1:Rgveda", "gemini:gemini-2.5-flash"),
                                   ("bench_scholar", "BM1:Rgveda", "anthropic:claude-sonnet-5-5")])
            self.assertAlmostEqual(m.execute("SELECT spent_usd FROM budget_state").fetchone()[0], 58.9325,
                                   msg="the spend cap counts Google's part only")
            self.assertAlmostEqual(ce.credit(m)["spent"], 110.41)
            self.assertEqual(m.execute("SELECT total_calls FROM usage_totals WHERE engine = 'gemini:gemini-2.5-flash'")
                             .fetchone()[0], 1)
            self.assertEqual(B.push(b, m, "flash")["rows"], 0, "never twice")
            self.assertEqual(m.execute("SELECT COUNT(*) FROM usage_log").fetchone()[0], 4)
            B.pull(b, m)
            self.assertAlmostEqual(ce.credit(b)["left"], ce.credit(m)["left"], msg="the bench has the ledger again")
            b.execute("INSERT INTO usage_log(kind, doc, engine, cost_usd) VALUES ('judge', 'Rgveda', 'gemini:x', 0.001)")
            b.commit()
            with self.assertRaises(RuntimeError):
                B.pull(b, m)   # a call not yet in the ledger is never thrown away
            self.assertEqual(B.push(b, m, "flash")["rows"], 1)
            self.assertEqual(m.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'translation'").fetchone()[0], 1,
                             "the Library's price of a translation is not touched")
        finally:
            b.close()
            m.close()
        with self.assertRaises(RuntimeError):
            m = sqlite3.connect(self.main)
            try:
                B.pull(m, m)
            finally:
                m.close()


@unittest.skipUnless(HAVE_TR, "indic-transliteration is not installed")
class TheArmsTheJudgeAndTheReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = dataset(self.td)
        self.main = ledger(self.td)
        self.out = self.td / "bm1"
        self.args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.out), "--files", ",".join(KEYS)]
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        child = self.td / "child.py"
        child.write_text(FAKE_CHILD, encoding="utf-8")
        self.saved = (B.arm_cmd, B.ST.Gemini)
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        B.ST.Gemini = FakeGemini
        FakeGemini.calls = []

    def tearDown(self):
        B.arm_cmd, B.ST.Gemini = self.saved
        self.tmp.cleanup()

    def test_end_to_end(self):
        before = md5(self.main)
        self.assertEqual(B.main(self.args), 0, "the dry run")
        self.assertEqual(md5(self.main), before, "the dry run writes nothing")
        self.assertEqual(B.main(self.args + ["--score", "--yes"]), 1, "the judge waits for the three arms")
        for arm in B.ARMS:
            self.assertEqual(B.main(self.args + ["--arm", arm, "--yes"]), 0, arm)
            self.assertEqual(sum(B.todo_of(self.out, B.load_sample(self.out), [f for f in B.FILES if f["key"] in KEYS],
                                           arm).values()), 0)
        m = sqlite3.connect(self.main)
        kinds = dict(m.execute("SELECT kind, COUNT(*) FROM usage_log WHERE kind LIKE 'bench_%' GROUP BY kind").fetchall())
        self.assertEqual(kinds, {"bench_translation": 100, "bench_scholar": 50, "bench_judge": 50})
        self.assertEqual({d for (d,) in m.execute("SELECT DISTINCT doc FROM usage_log WHERE kind LIKE 'bench_%'")},
                         {"BM1:Manusmrti", "BM1:Rgveda"})
        self.assertAlmostEqual(m.execute("SELECT spent_usd FROM budget_state").fetchone()[0],
                               58.93 + 50 * 0.002 + 50 * 0.0027, places=6)
        m.close()
        self.assertEqual(B.main(self.args + ["--arm", "flash", "--yes"]), 0, "nothing left to send")
        self.assertEqual(B.main(self.args + ["--score"]), 0, "the dry run of the judge")
        self.assertEqual(FakeGemini.calls, [])
        self.assertEqual(B.main(self.args + ["--score", "--judge-reference", "--yes"]), 0)
        n = len(FakeGemini.calls)
        self.assertEqual(n, 2 * 24 * 4, "24 units a text (verses 3 and 4 one sentence), three arms and the reference")
        self.assertIn("scholar Manusmrti the sentence of verses 3 and 4 //", FakeGemini.calls)
        self.assertIn("flash Manusmrti English of verse 3 // flash Manusmrti English of verse 4 //", FakeGemini.calls)
        self.assertEqual(B.main(self.args + ["--score", "--judge-reference", "--yes"]), 0)
        self.assertEqual(len(FakeGemini.calls), n, "a judgement is not bought twice")
        m = sqlite3.connect(self.main)
        self.assertEqual(m.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'bench_judge' AND doc LIKE 'BM1:%'")
                         .fetchone()[0], 50 + n)
        m.close()
        self.assertEqual(B.main(self.args + ["--report"]), 0)
        s = json.loads((self.out / "BM1_summary.json").read_text(encoding="utf-8"))
        al = s["scopes"]["all"]
        self.assertEqual((al["units"], al["verses"]), (48, 50))
        self.assertEqual(set(al["chrf"]), set(B.ARMS))
        self.assertEqual(al["judge"]["scholar"]["fidelity"], 5.0)
        self.assertEqual(al["judge"]["flash"]["fidelity"], 3.0)
        self.assertEqual(al["judge"]["reference"]["fidelity"], 4.0)
        self.assertEqual(al["scholar_status"], {"passed": 46, "flagged": 2})
        self.assertEqual(al["misaligned"], 0)
        self.assertEqual(s["scopes"]["aligned"]["units"], 48)
        self.assertEqual(al["judge_again"]["units"], 48)
        self.assertEqual(sorted(al["diff"]), ["scholar-flash", "scholar-sonnet1", "sonnet1-flash"])
        self.assertEqual(al["diff"]["scholar-flash"]["fidelity"], 2.0)
        self.assertEqual(al["diff"]["scholar-flash"]["fidelity_ci"], [2.0, 2.0])
        self.assertIn("GSD36manu", s["scopes"])
        raw = (self.out / "BM1_summary.json").read_text(encoding="utf-8")
        self.assertNotIn("PUBLISHED", raw, "numbers only: no published English")
        self.assertNotIn("\u0927\u0930\u094d\u092e", raw, "no Sanskrit")
        page = (self.out / "BM1_report.html").read_text(encoding="utf-8")
        self.assertIn("Private evaluation.", page)
        self.assertIn("2.3-2.4", page)
        self.assertEqual(B.main(self.args + ["--settle"]), 0)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "bench_mitra.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p)
            self.assertIn(MARK, b)

    def test_the_bench_folder_is_outside_the_repository(self):
        o = B.OUT_DEFAULT.resolve()
        self.assertNotIn(REPO.resolve(), o.parents)
        self.assertFalse((REPO / "data" / "bm1").exists())


if __name__ == "__main__":
    unittest.main()
