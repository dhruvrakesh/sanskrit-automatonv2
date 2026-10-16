# -*- coding: ascii -*-
"""BENCH_DUEL_2026_10_16: BM3, the blind side-by-side of BM1's English. The order of reading (balanced: any prefix
takes the texts in turn); a run end to end with stand-in judges (one of each family, each preferring its own family's
English): the readings stored once, the calls into the ledger as kind bench_duel, doc BM3:<text>, the spend cap
counting Google's part only; the report's numbers (each judge's pairs, the agreement, the splits by family) with no
text in the summary; the refusals. Temp folders only; BM1 made with the stand-ins of test_bench_mitra; nothing is
called."""
import hashlib, json, re, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "tests"))

import bench_duel as D                      # noqa: E402
import bench_mitra as B                     # noqa: E402
import cost_tracker                         # noqa: E402
import test_bench_mitra_2026_10_16 as TB    # noqa: E402

MARK = b"BENCH_DUEL_2026_10_16"
GEM, CLA = "gemini:gemini-2.5-pro", "anthropic:claude-opus-5-5"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


class FakeAsker:
    """A judge's stand-in: it ranks by who made each translation, its own family first, and meters as a call does."""
    msgs = []

    def __init__(self, engine, out, meta):
        self.engine, self.meta, self.spent, self.con = engine, dict(meta), 0.0, None

    def ask(self, kind, msg):
        assert kind == "duel", kind
        FakeAsker.msgs.append((self.engine, msg))
        parts = re.findall(r"TRANSLATION ([A-D]):\n(.*?)\nITS NOTES:", msg, re.S)
        cost = cost_tracker.log_api_call(self.con, kind="duel", doc=self.meta["doc"], engine=self.engine,
                                         in_tokens=2000.0, out_tokens=800.0)
        self.spent += cost
        pref = (["flash", "scholar", "sonnet1", "PUBLISHED"] if self.engine.startswith("gemini:")
                else ["scholar", "sonnet1", "flash", "PUBLISHED"])
        who = lambda t: next(i for i, p in enumerate(pref) if t.startswith(p))
        ranked = sorted(parts, key=lambda lt: who(lt[1]))
        d = {L: {"fidelity": 5 - who(t), "prose": 4, "notes": 3,
                 "errors": [{"where": "x", "error": "y", "severity": "major"}] if t.startswith("PUBLISHED") else []}
             for L, t in parts}
        d.update(ranking=[L for L, _t in ranked], best=ranked[0][0], reason="a stand-in")
        return d, cost


class TheOrder(unittest.TestCase):
    def test_balanced_and_fixed(self):
        items = [{"f": {"key": "K%d" % i}, "units": [[j] for j in range(1, 6 + i)]} for i in range(3)]
        o = D.order_of(items)
        self.assertEqual(len(o), 5 + 6 + 7)
        self.assertEqual(len(set(o)), len(o))
        self.assertEqual(o, D.order_of(items), "the same order every time")
        first = o[:6]
        self.assertEqual(sorted(ti for ti, _u in first), [0, 0, 1, 1, 2, 2], "any prefix takes the texts in turn")


class TheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = TB.dataset(self.td)
        self.main = TB.ledger(self.td)
        self.bm1 = self.td / "bm1"
        self.out = self.td / "bm3"
        args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.bm1), "--files", ",".join(TB.KEYS)]
        self.assertEqual(B.main(args + ["--sample"]), 0)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        self.saved = (B.arm_cmd, B.FILES, D.make_judge)
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        self.bm1args = args
        B.FILES = tuple(f for f in B.FILES if f["key"] in TB.KEYS)
        D.make_judge = lambda engine, out, meta: FakeAsker(engine, out, meta)
        FakeAsker.msgs = []
        self.args = ["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.out)]

    def tearDown(self):
        B.arm_cmd, B.FILES, D.make_judge = self.saved
        self.tmp.cleanup()

    def arms(self):
        for arm in B.ARMS:
            self.assertEqual(B.main(self.bm1args + ["--arm", arm, "--yes"]), 0, arm)

    def test_it_waits_for_bm1(self):
        self.assertEqual(D.main(self.args), 1, "BM1's arms are not complete")
        self.assertFalse(D.state(self.bm1, self.out, str(self.main))["ready"])

    def test_never_inside_a_repository(self):
        self.assertEqual(D.main(["--out", str(REPO / "bm3")]), 1)

    def test_end_to_end(self):
        self.arms()
        before = md5(self.main)
        self.assertEqual(D.main(self.args + ["--units", "6", "--with-reference"]), 0, "the dry run")
        self.assertEqual(md5(self.main), before, "the dry run writes nothing")
        self.assertFalse((self.out / "duel.jsonl").exists())
        self.assertEqual(FakeAsker.msgs, [])
        self.assertEqual(D.main(self.args + ["--units", "6", "--with-reference", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(len(FakeAsker.msgs), 12, "six units, two judges")
        self.assertEqual({e for e, _m in FakeAsker.msgs}, {GEM, CLA})
        for _e, msg in FakeAsker.msgs:
            self.assertEqual(len(re.findall(r"TRANSLATION [A-D]:", msg)), 4, "three arms and the published English")
            self.assertEqual(msg.count("PUBLISHED"), 1, "the published English once, as a translation")
            self.assertIn("THE VERSE TO TRANSLATE", msg)
            self.assertNotIn("flash", msg.split("TRANSLATION A:")[0], "no arm's English in the context")
        keys = {(m.split("TRANSLATION A:")[0]) for _e, m in FakeAsker.msgs}
        self.assertEqual(len(keys), 6)
        rs = D.readings(self.out)
        self.assertEqual(len(rs), 12)
        self.assertEqual(sorted({r["key"] for r in rs}), sorted(TB.KEYS), "the six units take the texts in turn")
        con = sqlite3.connect(self.main)
        n, docs = con.execute("SELECT COUNT(*), GROUP_CONCAT(DISTINCT doc) FROM usage_log WHERE kind = 'bench_duel'"
                              ).fetchone()
        self.assertEqual(n, 12)
        self.assertEqual(set(docs.split(",")), {"BM3:Manusmrti", "BM3:Rgveda"})
        self.assertEqual(con.execute("SELECT COUNT(*) FROM usage_log WHERE doc LIKE 'BM1:BM3%'").fetchone()[0], 0)
        g = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE kind = 'bench_duel' AND engine LIKE "
                        "'gemini:%'").fetchone()[0]
        spent = con.execute("SELECT spent_usd FROM budget_state WHERE id = 1").fetchone()[0]
        con.close()
        self.assertAlmostEqual(spent, 58.93 + 50 * 0.002 + 50 * 0.0027 + g, places=6, msg="Google's part only, once")
        FakeAsker.msgs = []
        self.assertEqual(D.main(self.args + ["--units", "6", "--with-reference", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(FakeAsker.msgs, [], "a reading is not bought twice")
        self.assertEqual(D.main(self.args + ["--units", "10", "--with-reference", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(len(FakeAsker.msgs), 8, "four units more")
        self.assertEqual(D.main(self.args + ["--report"]), 0)
        s = json.loads((self.out / "BM3_summary.json").read_text(encoding="utf-8"))
        al = s["scopes"]["all"]
        self.assertEqual(al["units"], 10)
        self.assertEqual(s["judges"], [GEM, CLA])
        gj, cj = al["by_judge"][GEM], al["by_judge"][CLA]
        self.assertEqual(gj["pairs"]["scholar>flash"]["share"], 0.0, "the Gemini stand-in puts flash first")
        self.assertEqual(cj["pairs"]["scholar>flash"]["share"], 1.0)
        self.assertEqual(cj["pairs"]["scholar>sonnet1"]["share"], 1.0)
        self.assertEqual(gj["pairs"]["flash>reference"]["share"], 1.0)
        self.assertEqual(cj["means"]["reference"]["major_per_10"], 10.0 * 10 / al["verses"])
        self.assertEqual(cj["means"]["scholar"]["first"], 1.0)
        b = al["both"]
        self.assertEqual(b["units"], 10)
        self.assertEqual(b["pairs"]["scholar>sonnet1"]["agree"], 1.0)
        self.assertEqual(b["pairs"]["scholar>sonnet1"]["consensus"], 1.0)
        self.assertEqual(b["pairs"]["scholar>flash"]["agree"], 0.0)
        self.assertEqual(b["pairs"]["scholar>flash"]["consensus"], 0.5)
        self.assertEqual(b["pairs"]["scholar>flash"]["split_own_family"], 10, "each judge its own family's")
        self.assertEqual(b["pairs"]["scholar>flash"]["split_other_family"], 0)
        self.assertNotIn("split_own_family", b["pairs"]["scholar>sonnet1"], "one family: no split to tell")
        raw = (self.out / "BM3_summary.json").read_text(encoding="utf-8")
        self.assertNotIn("PUBLISHED", raw, "numbers only: no published English")
        self.assertNotIn("English of verse", raw, "no arm's English")
        self.assertNotIn("\u0927", raw, "no Sanskrit")
        page = (self.out / "BM3_report.html").read_text(encoding="utf-8")
        self.assertIn("Private evaluation.", page)
        self.assertIn("Both judges", page)
        st = D.state(self.bm1, self.out, str(self.main), [GEM, CLA])
        self.assertTrue(st["ready"])
        self.assertEqual(st["units_total"], 48)
        self.assertEqual(st["read"], {GEM: 10, CLA: 10})
        self.assertEqual(st["plans"]["pilot"]["calls"], 2 * 30)
        self.assertEqual(st["plans"]["all"]["calls"], 2 * 38)
        self.assertEqual((st["plans"]["next"]["units"], st["plans"]["next"]["calls"]), (48, 2 * 38), "40 more, at most all")
        self.assertFalse(st["stale"])
        self.assertEqual(D.main(self.args + ["--settle"]), 0)
        con = sqlite3.connect(self.main)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'bench_duel'").fetchone()[0], 20,
                         "settled once")
        con.close()

    def test_the_caps_refuse_up_front(self):
        self.arms()
        con = sqlite3.connect(self.main)
        con.execute("UPDATE budget_state SET budget_usd = spent_usd + 0.01 WHERE id = 1")
        con.commit()
        con.close()
        self.assertEqual(D.main(self.args + ["--units", "40", "--yes", "--max-usd", "9"]), 1)
        self.assertEqual(FakeAsker.msgs, [])


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "bench_duel.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)

    def test_duel_v1_unchanged(self):
        import scholar_duel as SD
        self.assertIs(D.SD, SD)
        self.assertEqual(SD.DUEL_VERSION, "duel-v1")
        self.assertEqual(SD.JUDGES, (GEM, CLA))


if __name__ == "__main__":
    unittest.main()
