# -*- coding: ascii -*-
"""BENCH_GOLD_2026_10_16: BM2 on the dashboard. The reading page (no dataset text in it: the units come from the API),
/api/bm2/next (blind) and /api/bm2/pick (checked, stored, revealed), the Benchmarks page's BM2 section and its report
step (a job of kind bench2), the private report served here, the page's scripts, the patcher. A made-up dataset and
temp folders; BM1's scripts and BM3's judges are stand-ins; nothing is called."""
import json, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_duel as BD                       # noqa: E402
import bench_gold as BG                       # noqa: E402
import bench_mitra as B                       # noqa: E402
import test_bench_desk_2026_10_16 as TD       # noqa: E402
import test_bench_duel_2026_10_16 as TU       # noqa: E402
import test_bench_mitra_2026_10_16 as TB      # noqa: E402

MARK = b"BENCH_GOLD_2026_10_16"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()
KEYS = TB.KEYS


@unittest.skipUnless(APPLIED and TB.HAVE_TR, "BENCH_GOLD_2026_10_16 is not applied here, or no transliterator")
class TheDesk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = TD.load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = TB.dataset(self.td)
        self.main = TB.ledger(self.td)
        self.bm1, self.bm2, self.bm3 = self.td / "bm1", self.td / "bm2", self.td / "bm3"
        self.args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.bm1), "--files", ",".join(KEYS)]
        self.saved = (B.FILES, B.arm_cmd, BD.make_judge, self.d.BM1_DIR, self.d.BM2_DIR, self.d.BM3_DIR,
                      self.d.BM1_LEDGER)
        B.FILES = tuple(f for f in B.FILES if f["key"] in KEYS)
        self.d.BM1_DIR, self.d.BM2_DIR, self.d.BM3_DIR, self.d.BM1_LEDGER = self.bm1, self.bm2, self.bm3, str(self.main)
        for c in (self.d._BM1_CACHE, self.d._BM2_CACHE, self.d._BM3_CACHE):
            c.update(res=None)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        BD.make_judge = lambda engine, out, meta: TU.FakeAsker(engine, out, meta)

    def tearDown(self):
        (B.FILES, B.arm_cmd, BD.make_judge, self.d.BM1_DIR, self.d.BM2_DIR, self.d.BM3_DIR,
         self.d.BM1_LEDGER) = self.saved
        for c in (self.d._BM1_CACHE, self.d._BM2_CACHE, self.d._BM3_CACHE):
            c.update(res=None)
        self.tmp.cleanup()

    def make_all(self):
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        for arm in B.ARMS:
            self.assertEqual(B.main(self.args + ["--arm", arm, "--yes"]), 0, arm)
        self.assertEqual(BD.main(["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "4",
                                  "--with-reference", "--yes", "--max-usd", "5"]), 0)

    def bench_page(self):
        r = self.c.get("/benchmarks")
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def test_it_waits_for_bm1(self):
        h = self.bench_page()
        self.assertIn("Your blind reading: BM2", h)
        self.assertIn("BM2 waits for BM1: BM1 has no sample.", h)

    def test_the_reading_end_to_end(self):
        self.make_all()
        r = self.c.get("/benchmarks/bm2")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")
        pg = r.get_data(as_text=True)
        self.assertIn("BM2: your blind reading", pg)
        self.assertNotIn("PUBLISHED", pg, "the page itself holds no dataset text")
        if TD.node():
            js = re.findall(r"<script>(.*?)</script>", pg, re.S)
            self.assertEqual(len(js), 1)
            p = self.td / "bm2.js"
            p.write_text(js[0], encoding="utf-8")
            res = subprocess.run([TD.node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.c.get("/api/bm2/next?by=").status_code, 400)
        self.assertEqual(self.c.get("/api/bm2/next?by=" + "x" * 41).status_code, 400)
        d = self.c.get("/api/bm2/next?by=Tester").get_json()
        self.assertEqual((d["read"], d["total"], d["done"]), (0, 48, False))
        u = d["unit"]
        self.assertNotIn("gemini-2.5-flash", json.dumps(u))
        r = self.c.post("/api/bm2/pick", json={"by": "Tester", "key": u["key"], "unit": u["unit"], "token": "stale",
                                               "best": 1})
        self.assertEqual(r.status_code, 400)
        self.assertIn("has changed since", r.get_json()["error"])
        r = self.c.post("/api/bm2/pick", json={"by": "Tester", "key": u["key"], "unit": u["unit"], "token": u["token"],
                                               "best": 2, "majors": [1], "note": "n"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        rev = r.get_json()["reveal"]
        self.assertEqual(len(rev["who"]), 4)
        self.assertEqual(len(rev["judges"]), 2)
        self.assertEqual(self.c.get("/api/bm2/next?by=Tester").get_json()["read"], 1)
        h = self.bench_page()
        self.assertIn("48 units; both judges have read 4. Read so far: Tester 1.", h)
        self.assertIn('href="/benchmarks/bm2"', h)
        self.assertIn('data-box="bm2" data-step="gold_report"', h)
        self.assertIn("document.getElementById('bm2running')", h)
        self.assertEqual(self.c.get("/benchmarks/bm2/report").status_code, 404)
        self.assertEqual(BG.main(["--bm1", str(self.bm1), "--bm3", str(self.bm3), "--out", str(self.bm2), "--report"]), 0)
        self.d._BM2_CACHE.update(res=None)
        h = self.bench_page()
        self.assertIn("The last report (", h)
        self.assertIn("Each judge against you", h)
        self.assertNotIn("PUBLISHED", h)
        r = self.c.get("/benchmarks/bm2/report")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Private evaluation.", r.get_data(as_text=True))
        if TD.node():
            for k, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
                p = self.td / ("b%d.js" % k)
                p.write_text(js, encoding="utf-8")
                res = subprocess.run([TD.node(), "--check", str(p)], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, res.stderr)

    def test_bm3s_check_the_notes_withheld(self):
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        for arm in B.ARMS:
            self.assertEqual(B.main(self.args + ["--arm", arm, "--yes"]), 0, arm)
        import sqlite3
        con = sqlite3.connect(self.bm1 / "db" / "S.db")
        con.execute("UPDATE scholar_translations SET notes = ?", (json.dumps([{"anchor": "x", "note": "a note"}]),))
        con.commit()
        con.close()
        self.assertEqual(BD.main(["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "4",
                                  "--with-reference", "--yes", "--max-usd", "5"]), 0)
        self.assertNotIn("The check: the scholarly arm's notes withheld", self.bench_page(), "after the pilot only")
        self.assertEqual(BD.main(["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "40",
                                  "--with-reference", "--yes", "--max-usd", "9"]), 0)
        self.assertEqual(BD.main(["--bm1", str(self.bm1), "--out", str(self.bm3), "--report"]), 0)
        self.d._BM3_CACHE.update(res=None)
        h = self.bench_page()
        self.assertIn("The check: the scholarly arm's notes withheld", h)
        self.assertIn('data-step="duel" data-units="40" data-nonotes="1"', h)
        self.assertIn("Read: gemini-2.5-pro 0 of 40, Claude Opus 5.5 0 of 40.", h,
                      "a reading with the notes shown is not taken for one without")
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j3")
        try:
            r = self.c.post("/api/bench", json={"step": "duel", "units": 40, "max_usd": 4.0, "no_notes": True})
            self.assertEqual(r.status_code, 200)
            r = self.c.post("/api/bench", json={"step": "duel_report", "no_notes": True})
            r = self.c.post("/api/bench", json={"step": "duel_report"})
        finally:
            self.d.launch = orig
        self.assertEqual(got[0][2][-7:], ["--units", "40", "--with-reference", "--yes", "--max-usd", "4.00", "--no-notes"])
        self.assertEqual(got[0][3], "duel 40 no notes")
        self.assertEqual(got[1][2][-2:], ["--report", "--no-notes"])
        self.assertEqual(got[2][2][-1], "--report")
        self.assertIn("if (btn.getAttribute('data-nonotes')) body.no_notes = true;", h)

    def test_the_report_step(self):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j2")
        try:
            r = self.c.post("/api/bench", json={"step": "gold_report"})
        finally:
            self.d.launch = orig
        self.assertEqual(r.status_code, 200)
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("bench2", "BM2", "report"))
        self.assertTrue(str(argv[-2]).endswith("bench_gold.py"))
        self.assertEqual(argv[-1], "--report")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py",)

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_benchgold_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the files")
        pat = [sys.executable, str(SCRIPTS / "patch_bench_gold_desk_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in self.FILES:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, "without bench_gold.py")
            self.assertIn("(this release), is not there", r.stdout)
            shutil.copy2(SCRIPTS / "bench_gold.py", t / "scripts" / "bench_gold.py")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, "without BENCH_DUEL_NOTES_2026_10_16 in bench_duel.py")
            shutil.copy2(SCRIPTS / "bench_duel.py", t / "scripts" / "bench_duel.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks["scripts/dashboard.py"][0], t / "scripts" / "dashboard.py")
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b"_bm1_html() + _bm3_html() + body", b"_bm1_html() + body"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard.py: anchor 3 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, p.read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_bench_gold_desk_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p)
            self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
