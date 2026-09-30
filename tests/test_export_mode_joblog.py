# -*- coding: ascii -*-
"""EXPORT_MODE_JOBLOG_2026_09_30.
Run from the repo root:  python -m unittest tests.test_export_mode_joblog -v
Imports scripts/dashboard.py as a module (no server, no port). Jobs run a
trivial `python -c` child; the job log is redirected to a temp file. Never
touches data/context.db, data/jobs.jsonl, the network or port 5057.
Fails before the patch, passes after."""
import importlib.util, json, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_under_test", str(REPO / "scripts" / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve types through sys.modules
    spec.loader.exec_module(mod)
    return mod


def wait_done(d, jid, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with d.JOBS_LOCK:
            j = d.JOBS.get(jid)
        if j is not None and j.ok is not None:
            return j
        time.sleep(0.05)
    raise AssertionError("job %s did not finish" % jid)


class ExportModeJobLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.tmp.name) / "jobs.jsonl"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_marker(self):
        self.assertIn("EXPORT_MODE_JOBLOG_2026_09_30", (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8"))

    def test_mode_is_part_of_duplicate_identity(self):
        slow = [sys.executable, "-c", "import time; time.sleep(1.5)"]
        a = self.d.launch("export", "UNITTEST_DOC", slow, mode="hi")
        b = self.d.launch("export", "UNITTEST_DOC", slow, mode="tri")
        c = self.d.launch("export", "UNITTEST_DOC", slow, mode="tri")
        self.assertNotEqual(a, b, "tri export was swallowed by a running hi export")
        self.assertEqual(b, c, "same doc + same mode must still be de-duplicated")
        for jid in {a, b}:
            wait_done(self.d, jid)

    def test_mode_persisted_only_when_set(self):
        quick = [sys.executable, "-c", "pass"]
        e = self.d.launch("export", "UNITTEST_PERSIST", quick, mode="tri")
        o = self.d.launch("ocr", "UNITTEST_PERSIST", quick)
        wait_done(self.d, e); wait_done(self.d, o)
        time.sleep(0.3)
        recs = [json.loads(l) for l in self.d.JOBS_LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        by_id = {r["id"]: r for r in recs}
        self.assertEqual(by_id[e].get("mode"), "tri")
        self.assertNotIn("mode", by_id[o], "non-export records must keep their exact shape")

    def test_api_export_passes_mode(self):
        seen = {}
        real = self.d.launch
        def fake(kind, doc, argv, then=None, mode=""):
            seen.update(kind=kind, doc=doc, argv=argv, mode=mode); return "fake-id"
        self.d.launch = fake
        try:
            client = self.d.app.test_client()
            r = client.post("/api/export", json={"doc": "nilamata_seg", "mode": "tri"})
        finally:
            self.d.launch = real
        self.assertEqual(r.status_code, 200)
        self.assertEqual(seen.get("mode"), "tri")
        self.assertIn("--side-by-side", seen.get("argv", []))


if __name__ == "__main__":
    unittest.main()
