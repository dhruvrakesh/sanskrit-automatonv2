# -*- coding: ascii -*-
"""LIVE_BUDGET_2026_10_08: /api/progress reports a progress file left behind by a run that died as
'interrupted' (not 'running ... Calling API'), and the spend cap can be set and resumed from the
dashboard with the value checked and every change logged. Imports scripts/dashboard.py as a module
(no server, no port); temp files only, never data/context.db."""
import datetime, importlib.util, json, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_live_budget", str(REPO / "scripts" / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def iso(minutes_ago):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
    return t.isoformat()


class LiveBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.d.PROGRESS_PATH = t / "translation_progress.json"
        cls.d.BUDGET_LOG_PATH = t / "budget_changes.jsonl"
        cls.db = str(t / "context.db")
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def progress(self, **kw):
        p = {"status": "running", "doc": "Ganita", "updated_at": iso(120), "verses_done": 242, "verses_total": 830,
             "current_page": 221, "current_idx": 2, "current_translation": "translating..."}
        p.update(kw)
        self.d.PROGRESS_PATH.write_text(json.dumps(p), encoding="utf-8")
        return self.c.get("/api/progress").get_json()

    def test_marker(self):
        self.assertIn("LIVE_BUDGET_2026_10_08", (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8"))

    def test_a_dead_run_is_reported_as_interrupted(self):
        r = self.progress()
        self.assertEqual(r["status"], "interrupted")
        self.assertIn("p221.2", r["message"]); self.assertIn("242 of 830", r["message"]); self.assertIn("2 h ago", r["message"])
        self.assertEqual(r["verses_done"], 242)
        self.assertEqual(self.progress(status="paused")["status"], "interrupted")

    def test_a_recent_file_or_a_live_job_is_left_alone(self):
        self.assertEqual(self.progress(updated_at=iso(2))["status"], "running")   # a terminal run writes it too
        self.assertEqual(self.progress(status="done")["status"], "done")
        job = self.d.Job(id="unit-live", kind="translate", doc="Ganita", cmd=[])
        with self.d.JOBS_LOCK:
            self.d.JOBS[job.id] = job
        try:
            self.assertEqual(self.progress()["status"], "running")
        finally:
            with self.d.JOBS_LOCK:
                self.d.JOBS.pop(job.id, None)

    def test_budget_set_resume_and_log(self):
        post = lambda body: self.c.post("/api/budget?db=" + self.db, json=body)
        r = post({"budget_usd": 30})
        self.assertEqual(r.status_code, 200, r.get_json())
        j = r.get_json()
        self.assertTrue(j["set"]); self.assertEqual(j["budget_usd"], 30.0); self.assertFalse(j["paused"])
        self.assertEqual(self.c.get("/api/budget?db=" + self.db).get_json()["budget_usd"], 30.0)
        for bad in ("abc", 0, -5, 5000, None):
            self.assertEqual(post({"budget_usd": bad}).status_code, 400, bad)
        self.assertEqual(post({}).status_code, 400)
        con = sqlite3.connect(self.db)
        con.execute("UPDATE budget_state SET spent_usd=12, paused=1 WHERE id=1"); con.commit(); con.close()
        j = post({"resume": True}).get_json()
        self.assertTrue(j["resumed"]); self.assertFalse(j["paused"]); self.assertEqual(j["remaining_usd"], 18.0)
        j = post({"budget_usd": 10}).get_json()
        self.assertIn("warning", j)
        log = [json.loads(x) for x in self.d.BUDGET_LOG_PATH.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([x["action"] for x in log], ["set", "resume", "set"])
        self.assertEqual((log[0]["cap_after"], log[2]["cap_before"], log[2]["cap_after"]), (30.0, 30.0, 10.0))

    def test_page_has_the_controls(self):
        h = (REPO / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        for s in ("function budgetHtml(b)", "budgetHtml(d.budget)", "function setBudget()", "function resumeBudget()",
                  "d.status === 'interrupted'", "/api/budget"):
            self.assertIn(s, h)


if __name__ == "__main__":
    unittest.main()
