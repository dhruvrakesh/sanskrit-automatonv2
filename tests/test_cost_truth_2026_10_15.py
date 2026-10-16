# -*- coding: ascii -*-
"""COST_TRUTH_2026_10_15: the meter counts the thinking that Google bills as output even where the SDK does not name it
(total_token_count - prompt_token_count); the scholarly English's price counts only rows metered so, and a job that only
adds working English does not stop it; a dashboard job stopped while queued never starts. Temp files only; nothing is
called."""
import json, shutil, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import usage_meter            # noqa: E402
import infer_mt               # noqa: E402
import test_scholar_2026_10_14 as base      # noqa: E402
import test_scholar_v2_2026_10_14 as v2     # noqa: E402

ST = base.ST


def resp(**um):
    return types.SimpleNamespace(usage_metadata=types.SimpleNamespace(**um))


class TheMeter(unittest.TestCase):
    def test_the_thinking_is_counted_where_the_sdk_does_not_name_it(self):
        # 14 Oct 21:34 (UTC 16:04): a draft cut off by its thinking, metered as its input alone
        self.assertEqual(usage_meter.usage_from_response(resp(prompt_token_count=3012, candidates_token_count=0,
                                                              total_token_count=11204)), (3012.0, 8192.0))
        self.assertEqual(usage_meter.usage_from_response(resp(prompt_token_count=3012, candidates_token_count=1235,
                                                              total_token_count=12000)), (3012.0, 8988.0))

    def test_as_before_where_it_is_named_or_there_is_no_total(self):
        self.assertEqual(usage_meter.usage_from_response(resp(prompt_token_count=100, candidates_token_count=40,
                                                              thoughts_token_count=60, total_token_count=200)),
                         (100.0, 100.0))
        self.assertEqual(usage_meter.usage_from_response(resp(prompt_token_count=100, candidates_token_count=40)),
                         (100.0, 40.0))
        self.assertEqual(usage_meter.usage_from_response(resp(prompt_token_count=100, candidates_token_count=40,
                                                              total_token_count=0)), (100.0, 40.0))
        self.assertEqual(usage_meter.usage_from_response(types.SimpleNamespace()), (None, None))

    def test_the_translation_meter_too(self):
        infer_mt._usage_reset() if hasattr(infer_mt, "_usage_reset") else infer_mt._USAGE.update(
            {"in": 0.0, "out": 0.0, "calls": 0})
        infer_mt._usage_add(resp(prompt_token_count=1000, candidates_token_count=200, total_token_count=2500))
        infer_mt._usage_add(resp(prompt_token_count=1000, candidates_token_count=200))
        self.assertEqual((infer_mt._USAGE["in"], infer_mt._USAGE["out"], infer_mt._USAGE["calls"]), (2000.0, 1700.0, 2))
        import cost_tracker
        self.assertAlmostEqual(cost_tracker.estimate_cost_from_tokens("gemini:gemini-2.5-pro", 3012, 8192),
                               3012 * 1.25e-6 + 8192 * 10e-6, places=6)


class TheScholar(unittest.TestCase):
    def test_the_price_counts_only_rows_metered_with_the_thinking(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            pid = con.execute("SELECT id FROM passages LIMIT 1").fetchone()[0]
            ins = lambda v, at: con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, "
                                            "engine, prompt_version, cost_usd, created_at) VALUES (?, 'MBh01', 'h', ?, ?, "
                                            "?, 0.0107, ?)", (pid, v, ST.ENGINE, ST.PROMPT_VERSION + "+x", at))
            for v in range(10):
                ins(v + 1, "2026-10-14T16:00:00+00:00")   # the run of 14 Oct, metered without the thinking
            con.commit()
            p = ST.prices(con, v2.args(db), 1000)
            self.assertTrue(p["how"].startswith("a prior until 10 verses are measured (output 3000 tokens a call"), p)
            self.assertGreater(p["typical"], 0.05, "the prior with the thinking")
            for v in range(10):
                ins(v + 11, "2026-10-15T05:00:00+00:00")
            con.commit()
            p = ST.prices(con, v2.args(db), 1000)
            self.assertEqual(p["how"], "measured on 10 %s verses" % ST.PROMPT_VERSION)
            self.assertAlmostEqual(p["typical"], 0.0107)
            con.close()

    def test_a_job_that_adds_working_english_does_not_stop_a_run(self):
        import repair_text as rt
        keep = rt.dashboard_jobs
        try:
            rt.dashboard_jobs = lambda: [{"doc": "MBh01", "kind": "translate_both", "state": "queued"},
                                         {"doc": "MBh01", "kind": "translate", "state": "running"},
                                         {"doc": "Other", "kind": "repair_use", "state": "running"}]
            self.assertEqual(ST.busy_with("MBh01"), [])
            rt.dashboard_jobs = lambda: [{"doc": "MBh01", "kind": "repair_use", "state": "queued"}]
            self.assertEqual([j["kind"] for j in ST.busy_with("MBh01")], ["repair_use"], "the Sanskrit may change")
        finally:
            rt.dashboard_jobs = keep


class TheDashboard(unittest.TestCase):
    def test_a_job_stopped_while_queued_never_starts(self):
        d = base.load("dashboard_cost_truth", SCRIPTS / "dashboard.py")
        saved = []
        keep = (d._persist_job, d.subprocess.Popen)
        d._persist_job = saved.append
        def no_popen(*a, **k):
            raise AssertionError("a killed job was started")
        d.subprocess.Popen = no_popen
        try:
            job = d.Job(id="j1", kind="translate_both", doc="MBh01", cmd=["python", "x.py"])
            with d.JOBS_LOCK:
                d.JOBS[job.id] = job
            r = d.app.test_client().post("/api/job/j1/kill")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(json.loads(r.get_data(as_text=True))["queued"], True)
            d._run_job(job)
            self.assertIs(job.ok, False)
            self.assertEqual(job.err, "[KILLED by user] while queued: it never started")
            self.assertIsNotNone(job.end); self.assertEqual(saved, [job])
        finally:
            d._persist_job, d.subprocess.Popen = keep
            with d.JOBS_LOCK:
                d.JOBS.pop("j1", None)


class ThePatcher(unittest.TestCase):
    FILES = ("usage_meter.py", "infer_mt.py", "source_desk.py", "scholar_translate.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_costtruth_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_cost_truth_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_claude_*"))   # CLAUDE_ENGINE_2026_10_15 came after (scholar_translate.py)
                later = later or sorted(SCRIPTS.glob(f + ".bak_claudefirst_*"))   # CLAUDE_FIRST_2026_10_15 (infer_mt.py)
                later = later or sorted(SCRIPTS.glob(f + ".bak_libsch_*"))   # LIBRARY_SCHOLAR_2026_10_16 (dashboard.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "infer_mt.py"
            p.write_bytes(p.read_bytes().replace(b'_USAGE["out"] += float((out or 0) + think)', b'_USAGE["out"] += 0'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("infer_mt.py: anchor 1 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"COST_TRUTH", (t / "scripts" / "usage_meter.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_cost_truth_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"COST_TRUTH_2026_10_15", b)
        for f in ThePatcher.FILES:
            self.assertIn(b"COST_TRUTH_2026_10_15", (SCRIPTS / f).read_bytes(), f)


if __name__ == "__main__":
    unittest.main()
