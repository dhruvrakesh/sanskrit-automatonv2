# -*- coding: ascii -*-
"""SINGLE_INSTANCE / MT_TIMEOUT / HUB_SINGLE (2026-09-27).
Run from the repo root:  python -m unittest tests.test_ops_guard -v
No network, no API key; never touches data/context.db or the real port 5057."""
import importlib, importlib.util, os, socket, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
HUB = Path(os.environ.get("SRANGAM_HUB", str(REPO.parent / "srangam-hub"))) / "hub.py"


class FakeWithOpts:
    def __init__(self): self.calls = []
    def generate_content(self, msg, request_options=None):
        self.calls.append((msg, request_options)); return "ok"


class FakeOld:
    def __init__(self): self.calls = []
    def generate_content(self, msg):
        self.calls.append(msg); return "ok"


class BoundedModelCall(unittest.TestCase):
    def setUp(self):
        import infer_mt
        self.m = importlib.reload(infer_mt)

    def test_timeout_passed_when_supported(self):
        self.m._REQ_OPTS_OK = None
        self.m._REQ_TIMEOUT = 120.0
        g = FakeWithOpts()
        self.assertEqual(self.m._gen(g, "x"), "ok")
        self.assertEqual(g.calls, [("x", {"timeout": 120.0})])

    def test_old_sdk_called_plainly_once(self):
        self.m._REQ_OPTS_OK = None
        g = FakeOld()
        self.m._gen(g, "y")
        self.assertEqual(g.calls, ["y"])

    def test_zero_disables(self):
        self.m._REQ_OPTS_OK = None
        self.m._REQ_TIMEOUT = 0.0
        g = FakeWithOpts()
        self.m._gen(g, "z")
        self.assertEqual(g.calls, [("z", None)])

    def test_no_direct_generate_calls_left(self):
        src = (REPO / "scripts" / "infer_mt.py").read_text(encoding="utf-8")
        self.assertNotIn("resp = gm.generate_content(", src)   # every call goes through _gen


class SecondDashboardRefuses(unittest.TestCase):
    def test_refuses_when_port_taken(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(5)
        port = s.getsockname()[1]
        tmp = Path(tempfile.mkdtemp())
        try:
            r = subprocess.run([sys.executable, str(REPO / "scripts" / "dashboard.py"), "--port", str(port),
                                "--inbox", str(tmp / "in"), "--raw", str(tmp / "raw"),
                                "--exports", str(tmp / "ex"), "--db", str(tmp / "c.db")],
                               cwd=str(tmp), capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        finally:
            s.close()
        self.assertEqual(r.returncode, 3, r.stdout[-500:] + r.stderr[-500:])
        self.assertIn("[REFUSED]", r.stdout)


@unittest.skipUnless(HUB.exists(), "srangam-hub not beside the repo")
class HubStartGuard(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("hub_under_test", str(HUB))
        self.hub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hub)

    def test_port_open(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1)
        port = s.getsockname()[1]
        self.assertTrue(self.hub._port_open("127.0.0.1", port))
        s.close()
        self.assertFalse(self.hub._port_open("127.0.0.1", port))

    def test_busy_dashboard_is_not_started_twice(self):
        h = self.hub
        act = h.ACTIONS["start-automaton"]
        h.ACTIONS["start-automaton"] = (Path(tempfile.mkdtemp()),) + tuple(act[1:])
        h._port_open = lambda *a, **k: True                   # port 5057 taken
        h.check = lambda *a, **k: {"up": False}               # but /api/status too slow
        from unittest import mock
        with mock.patch.object(h.subprocess, "Popen", side_effect=AssertionError("Popen must not be called")) as pm:
            r = h.app.test_client().post("/api/run/start-automaton")
        self.assertFalse(pm.called)
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
