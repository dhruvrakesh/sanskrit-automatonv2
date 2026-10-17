# -*- coding: ascii -*-
"""BENCH_DUEL_2026_10_16: BM3 on the dashboard. The Benchmarks page's BM3 section (it waits for BM1; the pilot as a
capped button; the button withheld when the spend cap cannot hold its Google part; the last report's pairs), the
steps posted to /api/bench (a job of kind bench3, doc BM3, with --units --with-reference --yes --max-usd), the private
report served here, the page's script, the Usage tab's name for bench_duel, the patcher. A made-up dataset and temp
folders; BM1's scripts and BM3's judges are stand-ins; nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_duel as BD                       # noqa: E402
import bench_mitra as B                       # noqa: E402
import test_bench_desk_2026_10_16 as TD       # noqa: E402
import test_bench_duel_2026_10_16 as TU       # noqa: E402
import test_bench_mitra_2026_10_16 as TB      # noqa: E402

MARK = b"BENCH_DUEL_2026_10_16"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()
KEYS = TB.KEYS


@unittest.skipUnless(APPLIED and TB.HAVE_TR, "BENCH_DUEL_2026_10_16 is not applied here, or no transliterator")
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
        self.bm1, self.bm3 = self.td / "bm1", self.td / "bm3"
        self.args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.bm1), "--files", ",".join(KEYS)]
        self.saved = (B.FILES, B.arm_cmd, BD.make_judge, self.d.BM1_DIR, self.d.BM3_DIR, self.d.BM1_LEDGER)
        B.FILES = tuple(f for f in B.FILES if f["key"] in KEYS)
        self.d.BM1_DIR, self.d.BM3_DIR, self.d.BM1_LEDGER = self.bm1, self.bm3, str(self.main)
        self.d._BM1_CACHE.update(res=None)
        self.d._BM3_CACHE.update(res=None)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        BD.make_judge = lambda engine, out, meta: TU.FakeAsker(engine, out, meta)
        TU.FakeAsker.msgs = []

    def tearDown(self):
        B.FILES, B.arm_cmd, BD.make_judge, self.d.BM1_DIR, self.d.BM3_DIR, self.d.BM1_LEDGER = self.saved
        self.d._BM1_CACHE.update(res=None)
        self.d._BM3_CACHE.update(res=None)
        self.tmp.cleanup()

    def page(self):
        r = self.c.get("/benchmarks")
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def post(self, body):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j3")
        try:
            r = self.c.post("/api/bench", json=body)
        finally:
            self.d.launch = orig
        return r, got

    def make_bm1(self):
        self.assertEqual(B.main(self.args + ["--sample"]), 0)
        for arm in B.ARMS:
            self.assertEqual(B.main(self.args + ["--arm", arm, "--yes"]), 0, arm)

    def test_it_waits_for_bm1(self):
        h = self.page()
        self.assertIn("The blind side-by-side: BM3", h)
        self.assertIn("BM3 waits for BM1: BM1 has no sample.", h)
        self.assertNotIn('data-box="bm3"', h)

    def test_the_section_the_steps_and_the_report(self):
        self.make_bm1()
        h = self.page()
        self.assertIn("Read so far: gemini-2.5-pro 0, Claude Opus 5.5 0, of 48 units", h)
        self.assertIn("<b>Next:</b> the pilot: the first 40 units, 80 readings", h)
        self.assertIn('data-box="bm3" data-step="duel"', h)
        self.assertIn('data-units="40"', h)
        self.assertIn("the published English among the translations (sent to both judges: a private evaluation)", h)
        self.assertEqual(self.c.get("/benchmarks/bm3/report").status_code, 404)
        self.assertEqual(BD.main(["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.bm3), "--units", "6",
                                  "--with-reference", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(BD.main(["--bm1", str(self.bm1), "--out", str(self.bm3), "--report"]), 0)
        self.d._BM3_CACHE.update(res=None)
        h = self.page()
        self.assertIn("Read so far: gemini-2.5-pro 6, Claude Opus 5.5 6, of 48 units", h)
        self.assertIn("<b>Next:</b> the units up to 46, 80 readings", h)
        self.assertIn("The last report (", h)
        self.assertIn("both, where they agree", h)
        self.assertIn("<b>1.00 [1.00, 1.00]</b>", h)
        self.assertNotIn("PUBLISHED", h, "the page holds numbers, not the dataset's English")
        r = self.c.get("/benchmarks/bm3/report")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")
        self.assertIn("Private evaluation.", r.get_data(as_text=True))
        if TD.node():
            for k, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
                p = self.td / ("b%d.js" % k)
                p.write_text(js, encoding="utf-8")
                res = subprocess.run([TD.node(), "--check", str(p)], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("_BM_BOX = btn.getAttribute('data-box') || 'bm1';", h)
        self.assertIn("document.getElementById(_BM_BOX + 'log')", h)
        self.assertIn("document.getElementById('bm3running')", h)

    def test_the_cap_withholds_the_button(self):
        self.make_bm1()
        con = sqlite3.connect(self.main)
        con.execute("UPDATE budget_state SET budget_usd = spent_usd + 0.5 WHERE id = 1")
        con.commit()
        con.close()
        h = self.page()
        self.assertIn("The spend cap has $0.500 left: fewer units by hand", h)
        self.assertNotIn('data-step="duel"', h)
        self.assertIn('data-step="duel_report"', h)

    def test_the_posts(self):
        r, got = self.post({"step": "duel", "units": 40, "max_usd": 5.9})
        self.assertEqual(r.status_code, 200)
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("bench3", "BM3", "duel 40"))
        self.assertTrue(str(argv[-7]).endswith("bench_duel.py"))
        self.assertEqual(argv[-6:], ["--units", "40", "--with-reference", "--yes", "--max-usd", "5.90"])
        r, got = self.post({"step": "duel_report"})
        self.assertEqual(got[0][2][-1], "--report")
        r, got = self.post({"step": "duel_settle"})
        self.assertEqual(got[0][2][-1], "--settle")
        for body, why in (({"step": "duel", "units": 40, "max_usd": 13}, "run it by hand"),
                          ({"step": "duel", "max_usd": 2}, "units (a whole number) are needed"),
                          ({"step": "duel", "units": 0, "max_usd": 2}, "units must be between"),
                          ({"step": "duel", "units": 40, "max_usd": 0}, "outside what one press may spend")):
            r, got = self.post(body)
            self.assertEqual(r.status_code, 400, body)
            self.assertIn(why, r.get_json()["error"])
            self.assertEqual(got, [])
        r, got = self.post({"step": "arm", "arm": "flash", "max_usd": 0.4})
        self.assertEqual(got[0][0], "bench", "BM1's steps as before")


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_the_usage_names_bm3(self):
        h = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertIn("bench_duel: 'BM3: the side-by-side'", h)
        self.assertIn("bench_judge: 'BM1: the judge',", h)
        if TD.node():
            with tempfile.TemporaryDirectory() as td:
                for k, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
                    p = Path(td) / ("s%d.js" % k)
                    p.write_text(js, encoding="utf-8")
                    r = subprocess.run([TD.node(), "--check", str(p)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_doc_says_what_was_measured(self):
        d = (REPO / "docs" / "BENCH_MITRA_2026-10-16.md").read_text(encoding="utf-8")
        if "BENCH_DUEL_2026_10_16" not in d:
            self.skipTest("not applied here")
        self.assertIn("the test marks none of the 200", d)
        self.assertIn("line 156's published English renders lines 155 and 156 together", d)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/dashboard_static.html", "docs/BENCH_MITRA_2026-10-16.md")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_benchduel_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the files")
        pat = [sys.executable, str(SCRIPTS / "patch_bench_duel_desk_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in self.FILES:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, "without bench_duel.py")
            self.assertIn("scripts/bench_duel.py (this release) is not there", r.stdout)
            shutil.copy2(SCRIPTS / "bench_duel.py", t / "scripts" / "bench_duel.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_benchgold_*"))   # BENCH_GOLD_2026_10_16 came after
                later = later or sorted((REPO / f).parent.glob(Path(f).name + ".bak_transdesk_*"))   # TRANSLATION_DESK_2026_10_17
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "dashboard.py"
            p.write_bytes(p.read_bytes().replace(b"  if (usd) body.max_usd = usd;", b"  if (usd) body.max = usd;"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("dashboard.py: anchor 6 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_bench_duel_desk_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p)
            self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
