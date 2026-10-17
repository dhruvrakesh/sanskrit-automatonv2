# -*- coding: ascii -*-
"""BENCH_GOLD_FAIR_2026_10_17: BM2's report sets the reader beside the judges as the reader read, the scholarly arm's
notes withheld (BM3's check), as well as beside BM3's pilot (the notes shown). The pilot's numbers are as before; the
summary carries judges_as_read; the report and the command say both; the Benchmarks page too; the patcher. Temp
folders only; BM1 and BM3 made with stand-ins; nothing is called."""
import json, shutil, sqlite3, subprocess, sys, tempfile, unittest
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

MARK = b"BENCH_GOLD_FAIR_2026_10_17"
APPLIED = MARK in (SCRIPTS / "bench_gold.py").read_bytes()
GEM, CLA = "gemini:gemini-2.5-pro", "anthropic:claude-opus-5-5"


@unittest.skipUnless(APPLIED and TB.HAVE_TR, "BENCH_GOLD_FAIR_2026_10_17 is not applied here, or no transliterator")
class TheJudgesAsRead(unittest.TestCase):
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
        self.saved = (B.arm_cmd, B.FILES, D.make_judge, D.NOTES_SHOWN, D.NAME)
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        B.FILES = tuple(f for f in B.FILES if f["key"] in TB.KEYS)
        D.make_judge = lambda engine, out, meta: TU.FakeAsker(engine, out, meta)
        for arm in B.ARMS:
            self.assertEqual(B.main(args + ["--arm", arm, "--yes"]), 0, arm)
        con = sqlite3.connect(self.bm1 / "db" / "S.db")
        con.execute("UPDATE scholar_translations SET notes = ?", (json.dumps([{"anchor": "x", "kind": "term",
                                                                                "note": "a note"}]),))
        con.commit()
        con.close()
        a3 = ["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "4", "--with-reference"]
        self.assertEqual(D.main(a3 + ["--yes", "--max-usd", "5"]), 0)
        self.assertEqual(D.main(a3 + ["--no-notes", "--yes", "--max-usd", "5"]), 0)
        D.NOTES_SHOWN, D.NAME = self.saved[3], self.saved[4]   # bench_gold reads the notes shown, as its own process does
        p = self.bm3 / "duel.jsonl"   # the check's Claude judge chose sonnet1 where the pilot's chose scholar
        rs = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        for r in rs:
            if r.get("notes_shown") is False and r.get("judge") == CLA:
                r["best"] = "sonnet1"
        p.write_text("".join(json.dumps(r) + "\n" for r in rs), encoding="utf-8")

    def tearDown(self):
        B.arm_cmd, B.FILES, D.make_judge, D.NOTES_SHOWN, D.NAME = self.saved
        self.tmp.cleanup()

    def pick(self, by, best_arm):
        nx = G.next_for(self.bm1, self.bm2, by)
        u = nx["unit"]
        arms = G.order_for(u["key"], u["unit"], ["flash", "reference", "scholar", "sonnet1"])
        rev, err = G.record(self.bm1, self.bm2, self.bm3, by, u["key"], u["unit"], u["token"], arms.index(best_arm) + 1)
        self.assertIsNone(err)
        return rev

    def test_both_comparisons(self):
        for _k in range(4):
            self.pick("Tester", "sonnet1")
        self.assertEqual(G.main(["--bm1", str(self.bm1), "--bm3", str(self.bm3), "--out", str(self.bm2), "--report"]), 0)
        s = json.loads((self.bm2 / "BM2_summary.json").read_text(encoding="utf-8"))
        p = s["scopes"]["all"]["by_person"]["Tester"]
        self.assertEqual(p["judges"][CLA]["same_best"], 0.0, "the pilot's Claude judge chose scholar")
        self.assertEqual(p["judges_as_read"][CLA]["same_best"], 1.0, "the check's chose sonnet1, as the reader did")
        self.assertEqual((p["judges"][CLA]["units"], p["judges_as_read"][CLA]["units"]), (4, 4))
        self.assertEqual(set(p["judges_as_read"]), {GEM, CLA})
        page = (self.bm2 / "BM2_report.html").read_text(encoding="utf-8")
        self.assertIn("Judge, the notes withheld", page)
        self.assertIn("the notes withheld from them as from the reader", page)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/bench_gold.py", "scripts/dashboard.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_goldfair_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_goldfair_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_bench_gold_fair_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "bench_gold.py"
            p.write_bytes(p.read_bytes().replace(b"        got.append(dict(u, p=p, j=j))", b"        got.append(dict(u, j=j, p=p))"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("bench_gold.py: anchor 2 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_bench_gold_fair_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
