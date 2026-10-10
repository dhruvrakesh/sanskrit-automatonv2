# -*- coding: ascii -*-
"""LIVE_LOG_2026_10_10: the dashboard reads a job's output while it runs (not only at its end), and the
page's Log follows every job wherever it was started, writes each outcome as what it is (held, nothing,
N of M, stopped, failed), catches runs that start and end between two looks, keeps showing new lines
past 6,000 characters, and the Live tab no longer shows NaN. Imports scripts/dashboard.py as a module (no
server, no port); runs small python children only; temp files only, never data/context.db."""
import importlib.util, json, re, shutil, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KARAN = "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi"
HELD = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc "
        + KARAN + " --threshold 101 --include-unassessed\r\n  Translate anyway: add --allow-debris (dashboard: set "
        "SA_ALLOW_DEBRIS=1).\r\n")


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_live_log", str(REPO / "scripts" / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class RunJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.tmp.name) / "jobs.jsonl"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def job(self, code, jid):
        return self.d.Job(id=jid, kind="translate", doc="T", cmd=[sys.executable, "-u", "-c", code])

    def run_in_thread(self, job):
        t = threading.Thread(target=self.d._run_job, args=(job,), daemon=True)
        t.start()
        return t

    def wait_for(self, cond, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            if cond():
                return True
            time.sleep(0.05)
        return False

    def test_marker(self):
        for rel in ("scripts/dashboard.py", "scripts/dashboard_static.html"):
            src = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn("LIVE_LOG_2026_10_10", src, rel)
            self.assertIn("DESK_HEAL_2026_10_10", src, rel)

    def test_output_is_seen_while_the_job_runs(self):
        j = self.job("import sys,time; print('first line'); sys.stderr.write('a warning\\n'); time.sleep(1.5); "
                     "print('second line')", "lv1")
        t = self.run_in_thread(j)
        self.assertTrue(self.wait_for(lambda: "first line" in (j.out or ""), 1.2), "the first line arrives while it runs")
        self.assertIsNone(j.ok, "still running")
        self.assertNotIn("second line", j.out)
        t.join(10)
        self.assertTrue(j.ok); self.assertEqual(j.rc, 0)
        self.assertIn("first line", j.out); self.assertIn("second line", j.out)
        self.assertIn("a warning", j.err)
        rec = json.loads(self.d.JOBS_LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(rec["id"], "lv1"); self.assertIn("second line", rec["out_tail"])

    def test_much_output_on_both_pipes_does_not_block(self):
        j = self.job("import sys\nfor i in range(4000):\n print('out %d' % i)\n sys.stderr.write('err %d\\n' % i)", "lv2")
        t = self.run_in_thread(j)
        t.join(30)
        self.assertFalse(t.is_alive(), "no deadlock")
        self.assertTrue(j.ok)
        self.assertEqual(len(j.out.splitlines()), 4000, "every line is kept for the end")
        self.assertIn("err 3999", j.err)

    def test_a_job_stopped_by_hand_keeps_what_it_did(self):
        j = self.job("import time; print('began'); time.sleep(30)", "lv3")
        t = self.run_in_thread(j)
        self.assertTrue(self.wait_for(lambda: "began" in (j.out or "") and j.proc is not None, 5))
        j.killed = True
        j.proc.kill()       # the dashboard uses _kill_proc (taskkill /T); kill() is enough for one process
        t.join(15)
        self.assertFalse(t.is_alive())
        self.assertFalse(j.ok); self.assertEqual(j.err, "[KILLED by user]"); self.assertIn("began", j.out)

    def test_a_failure_keeps_its_reason(self):
        j = self.job("import sys; print('x'); sys.exit('it broke')", "lv4")
        t = self.run_in_thread(j); t.join(10)
        self.assertFalse(j.ok); self.assertEqual(j.rc, 1); self.assertIn("it broke", j.err)

    def test_api_job_shows_the_live_lines(self):
        j = self.job("import time; print('hello from the job'); time.sleep(1.5)", "lv5")
        with self.d.JOBS_LOCK:
            self.d.JOBS["lv5"] = j
        t = self.run_in_thread(j)
        c = self.d.app.test_client()
        try:
            self.assertTrue(self.wait_for(lambda: "hello from the job" in c.get("/api/job/lv5").get_json()["out"], 1.2))
            self.assertTrue(c.get("/api/job/lv5").get_json()["running"])
        finally:
            t.join(10)
            with self.d.JOBS_LOCK:
                self.d.JOBS.pop("lv5", None)


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        cls.html = (REPO / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_changes_are_in_place(self):
        h = self.html
        for s in ("function jobVerdict(ok, out)", "async function watchFinished()", "setInterval(watchFinished, 8000);",
                  "if (!activeJobs[sj.id]) {", "started outside this page", "_newLines(lastLine, lines)",
                  "_isoMs(d.started_at)", ".log-line-held{"):
            self.assertIn(s, h)
        self.assertNotIn("lastOutLen", h)
        self.assertNotIn("new Date(d.started_at + 'Z')", h)

    def test_the_scripts_parse(self):
        if not self.node:
            self.skipTest("node is not installed")
        for i, js in enumerate(re.findall(r"<script>(.*?)</script>", self.html, re.S)):
            p = Path(self.tmp.name) / ("p%d.js" % i)
            p.write_text(js, encoding="utf-8")
            r = subprocess.run([self.node, "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verdicts_lines_and_times(self):
        if not self.node:
            self.skipTest("node is not installed")
        h = self.html
        parts = []
        for name in ("_isoMs", "_outLines", "_newLines", "jobVerdict"):
            m = re.search(r"(function %s\(.*?\n\})" % re.escape(name), h, re.S)
            self.assertIsNotNone(m, name)
            parts.append(m.group(1))
        cases = [
            [False, HELD, "held", "--doc " + KARAN],
            [False, "[KILLED by user]", "stopped", "stopped by hand"],
            [False, "Traceback ...", "failed", "History"],
            [True, "[NOTHING] doc 'x': 0 translatable verses", "nothing to do", "nothing to translate"],
            [True, "Done. 1/1 translated | 1 quality-skipped | 0 errors\n[translate_both] ...\n"
                   "Done. 7/186 translated | 185 quality-skipped | 0 errors", "done",
             "1 of 1 translated, 1 below the OCR quality bar; 7 of 186 translated, 185 below the OCR quality bar"],
            [True, "Done. 0/5 translated | 5 quality-skipped | 0 errors", "nothing sent", "0 of 5"],
            [True, "ok", "done", "done"],
        ]
        prog = "\n".join(parts) + "\nconst C=" + json.dumps(cases) + r""";
let bad = 0;
for (const [ok, out, word, frag] of C) {
  const v = jobVerdict(ok, out);
  if (v.word !== word || v.text.indexOf(frag) < 0) { console.log('verdict', word, '->', JSON.stringify(v)); bad++; }
}
const L = ['a', 'b', 'c', 'd'];
if (JSON.stringify(_newLines('', L)) !== JSON.stringify(L)) { console.log('newLines empty'); bad++; }
if (JSON.stringify(_newLines('b', L)) !== JSON.stringify(['c', 'd'])) { console.log('newLines after b'); bad++; }
if (JSON.stringify(_newLines('d', L)) !== '[]') { console.log('newLines nothing new'); bad++; }
if (JSON.stringify(_newLines('gone', L)) !== JSON.stringify(L)) { console.log('newLines window moved'); bad++; }
if (JSON.stringify(_outLines('x\r\n\r\ny\n')) !== JSON.stringify(['x', 'y'])) { console.log('outLines'); bad++; }
const a = _isoMs('2026-10-10T10:59:08.439756+00:00'), b = _isoMs('2026-10-10T10:59:08.439756'), z = _isoMs('2026-10-10T10:59:08Z');
if (isNaN(a) || a !== b || isNaN(z)) { console.log('isoMs', a, b, z); bad++; }
process.exit(bad ? 1 : 0);
"""
        p = Path(self.tmp.name) / "v.js"; p.write_text(prog, encoding="utf-8")
        r = subprocess.run([self.node, str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
