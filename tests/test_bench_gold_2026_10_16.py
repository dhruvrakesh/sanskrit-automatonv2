# -*- coding: ascii -*-
"""BENCH_GOLD_2026_10_16: BM2, a person's blind reading of BM3's units. The units in BM3's order; what the page is
given before the pick (no names, no notes); the pick checked and stored, then who made each and what each judge chose;
the report's numbers (the person's best, the pairs, each judge against the person) with no text in the summary; the
state for the dashboard. Temp folders only; BM1 and BM3 made with stand-ins; nothing is called."""
import json, re, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "tests"))

import bench_duel as D                      # noqa: E402
import bench_gold as G                      # noqa: E402
import bench_mitra as B                     # noqa: E402
import test_bench_duel_2026_10_16 as TU     # noqa: E402
import test_bench_mitra_2026_10_16 as TB    # noqa: E402

MARK = b"BENCH_GOLD_2026_10_16"
GEM, CLA = "gemini:gemini-2.5-pro", "anthropic:claude-opus-5-5"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = TB.dataset(self.td)
        self.main = TB.ledger(self.td)
        self.bm1, self.bm2, self.bm3 = self.td / "bm1", self.td / "bm2", self.td / "bm3"
        args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.bm1), "--files", ",".join(TB.KEYS)]
        self.assertEqual(B.main(args + ["--sample"]), 0)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        self.saved = (B.arm_cmd, B.FILES, D.make_judge)
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        B.FILES = tuple(f for f in B.FILES if f["key"] in TB.KEYS)
        D.make_judge = lambda engine, out, meta: TU.FakeAsker(engine, out, meta)
        for arm in B.ARMS:
            self.assertEqual(B.main(args + ["--arm", arm, "--yes"]), 0, arm)
        self.assertEqual(D.main(["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "4",
                                 "--with-reference", "--yes", "--max-usd", "5"]), 0)

    def tearDown(self):
        B.arm_cmd, B.FILES, D.make_judge = self.saved
        self.tmp.cleanup()

    def pick(self, by, best_arm, wrong=(), note=""):
        """Pick the arm best_arm (or "equal") on the next unit; mark the arms in wrong."""
        nx = G.next_for(self.bm1, self.bm2, by)
        u = nx["unit"]
        arms = G.order_for(u["key"], u["unit"], ["flash", "reference", "scholar", "sonnet1"])
        best = "equal" if best_arm == "equal" else arms.index(best_arm) + 1
        return u, G.record(self.bm1, self.bm2, self.bm3, by, u["key"], u["unit"], u["token"], best,
                           [arms.index(a) + 1 for a in wrong], note)


class TheReading(Base):
    def test_blind_before_the_pick(self):
        nx = G.next_for(self.bm1, self.bm2, "Tester")
        self.assertEqual((nx["read"], nx["total"], nx["done"]), (0, 48, False))
        u = nx["unit"]
        _s, items = D.load(self.bm1)
        ti, ui = D.order_of(items)[0]
        self.assertEqual((u["key"], u["unit"]), (items[ti]["f"]["key"], B.unit_name(items[ti]["units"][ui])),
                         "BM3's order: the units the judges read first")
        self.assertEqual([t["n"] for t in u["translations"]], [1, 2, 3, 4])
        raw = json.dumps(u)
        for k in ('"arm"', '"notes"', '"who"', "gemini-2.5-flash", "the scholarly pipeline", "C. H. Tawney", "Buhler"):
            self.assertNotIn(k, raw, "nothing names a translation before the pick")
        self.assertTrue(u["verses"][0]["dev"] and u["verses"][0]["iast"])
        self.assertEqual(sum(1 for t in u["translations"] if t["text"].startswith("PUBLISHED")), 1)
        self.assertNotIn("PUBLISHED", json.dumps(u["before"] + u["after"]), "the context is Sanskrit only")
        a = G.order_for(u["key"], u["unit"], ["flash", "sonnet1", "scholar", "reference"])
        self.assertEqual(a, G.order_for(u["key"], u["unit"], ["reference", "scholar", "sonnet1", "flash"]), "fixed")

    def test_the_pick_checked_stored_and_revealed(self):
        u = G.next_for(self.bm1, self.bm2, "Tester")["unit"]
        for args, why in (((("x" * 50), u["key"], u["unit"], u["token"], 1), "say who is reading"),
                          (("Tester", u["key"], u["unit"], "stale", 1), "has changed since"),
                          (("Tester", u["key"], "9.9", u["token"], 1), "no such unit"),
                          (("Tester", u["key"], u["unit"], u["token"], 5), "pick the best"),
                          (("Tester", u["key"], u["unit"], u["token"], "two"), "pick the best")):
            rev, err = G.record(self.bm1, self.bm2, self.bm3, *args)
            self.assertIsNone(rev)
            self.assertIn(why, err)
        rev, err = G.record(self.bm1, self.bm2, self.bm3, "Tester", u["key"], u["unit"], u["token"], 1, [9])
        self.assertIn("a translation marked wrong", err)
        rev, err = G.record(self.bm1, self.bm2, self.bm3, "Tester", u["key"], u["unit"], u["token"], 1, [], "n" * 1001)
        self.assertIn("longer than", err)
        self.assertFalse((self.bm2 / "person.jsonl").exists(), "nothing stored by a refused pick")
        u, (rev, err) = self.pick("Tester", "scholar", wrong=["reference"], note="the reference paraphrases")
        self.assertIsNone(err)
        self.assertEqual(len(rev["who"]), 4)
        self.assertEqual({w["arm"] for w in rev["who"]}, {"flash", "sonnet1", "scholar", "reference"})
        self.assertEqual(set(rev["judges"]), {GEM, CLA}, "the first units are BM3's: both judges have read it")
        self.assertEqual(rev["judges"][CLA]["best"], "scholar")
        self.assertEqual(rev["judges"][GEM]["best"], "flash")
        num = {w["arm"]: w["n"] for w in rev["who"]}
        self.assertEqual(rev["judges"][CLA]["majors"], [num["reference"]])
        self.assertEqual(rev["scholar_n"], num["scholar"])
        r = G.picks(self.bm2)[-1]
        self.assertEqual((r["by"], r["best"], r["majors"], r["note"]), ("Tester", "scholar", ["reference"],
                                                                         "the reference paraphrases"))
        nx = G.next_for(self.bm1, self.bm2, "Tester")
        self.assertEqual(nx["read"], 1)
        self.assertNotEqual((nx["unit"]["key"], nx["unit"]["unit"]), (u["key"], u["unit"]), "the next unit")
        self.assertEqual(G.next_for(self.bm1, self.bm2, "Other")["read"], 0, "each reader apart")

    def test_the_report(self):
        for k in range(6):
            self.pick("Tester", "scholar" if k < 5 else "equal", wrong=["reference"])
        self.assertEqual(G.main(["--bm1", str(self.bm1), "--bm3", str(self.bm3), "--out", str(self.bm2), "--report"]), 0)
        s = json.loads((self.bm2 / "BM2_summary.json").read_text(encoding="utf-8"))
        p = s["scopes"]["all"]["by_person"]["Tester"]
        self.assertEqual(p["units"], 6)
        self.assertAlmostEqual(p["best"]["scholar"] + p["best"]["equal"], 1.0, places=3)
        self.assertEqual(p["pairs"]["scholar>flash"]["share"], 1.0)
        self.assertEqual(p["wrong_per_10"]["reference"], 10.0)
        cj, gj = p["judges"][CLA], p["judges"][GEM]
        self.assertEqual((cj["units"], gj["units"]), (4, 4), "the judges read four units")
        self.assertGreater(cj["same_best"], 0.5)
        self.assertEqual(gj["same_best"], 0.0, "the Gemini stand-in prefers flash")
        self.assertEqual((cj["wrong_marked"], cj["judge_caught"], cj["judge_major_anyway"]), (4, 4, 0))
        raw = (self.bm2 / "BM2_summary.json").read_text(encoding="utf-8")
        for x in ("PUBLISHED", "English of verse", chr(0x0927), "paraphrases"):
            self.assertNotIn(x, raw, "numbers only")
        page = (self.bm2 / "BM2_report.html").read_text(encoding="utf-8")
        self.assertIn("Private evaluation.", page)
        st = G.state(self.bm1, self.bm2, self.bm3)
        self.assertEqual((st["ready"], st["units_total"], st["read"], st["judged_both"]), (True, 48, {"Tester": 6}, 4))
        self.assertFalse(st["stale"])

    def test_never_inside_a_repository(self):
        self.assertEqual(G.main(["--out", str(REPO / "bm2")]), 1)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "bench_gold.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
