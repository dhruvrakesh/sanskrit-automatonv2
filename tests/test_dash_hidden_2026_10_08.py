# -*- coding: utf-8 -*-
"""DASH_HIDDEN_2026_10_08 (ENTERPRISE_PATH D3): the hidden, logged dashboard launcher.

  python -m unittest tests.test_dash_hidden_2026_10_08

The launcher itself runs only on Windows; these tests check what can be checked anywhere:
the launcher text the patch writes, the patch's refusals, line endings and idempotency, and that
SA_QUIET_REQUESTS leaves werkzeug's request lines out while errors are still logged.
"""
from __future__ import annotations
import importlib.util, os, re, shutil, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts" / "patch_dash_hidden_2026_10_08.py"


def load_patch():
    spec = importlib.util.spec_from_file_location("patch_dash_hidden", PATCH)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


P = load_patch()


def original_dashboard() -> str:
    """scripts/dashboard.py as it was before the patch (LF), whether or not it is applied here."""
    text = (ROOT / "scripts" / "dashboard.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
    return text.replace(P.INSERT, "", 1)


def run_patch(cwd: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(PATCH), *args], cwd=str(cwd), capture_output=True, text=True)


class Launcher(unittest.TestCase):
    def test_ascii_marker_and_param_first(self):
        s = P.NEW_PS1
        self.assertTrue(s.isascii())
        self.assertIn(P.MARK, s)
        first = next(l for l in s.splitlines() if l.strip() and not l.lstrip().startswith("#"))
        self.assertTrue(first.startswith("param("), first)     # PowerShell: param() before anything

    def test_runs_with_no_window_and_logs_in_utf8(self):
        s = P.NEW_PS1
        self.assertIn("$psi.CreateNoWindow = $true", s)
        self.assertIn("$psi.UseShellExecute = $false", s)
        self.assertIn("'/d /s /c \"' + $line + '\"'", s)          # cmd keeps the quoted line as written
        self.assertIn('-u scripts\\dashboard.py 1>>"', s)
        self.assertIn('$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8:backslashreplace"', s)
        self.assertIn('$psi.EnvironmentVariables["SA_QUIET_REQUESTS"] = "1"', s)
        self.assertIn('[string]$LogDir = "D:\\backups\\dashboard_logs"', s)

    def test_refuses_while_jobs_run_unless_forced(self):
        s = P.NEW_PS1
        self.assertIn("/api/jobs/running", s)
        self.assertIn("if ($busy -gt 0 -and -not $Force)", s)
        guard = s.index("if ($busy -gt 0 -and -not $Force)")
        self.assertLess(guard, s.index("Stop-Process -Id $procId"))   # the guard comes before any stop
        for sw in ("[switch]$Status", "[switch]$Stop", "[switch]$Window", "[switch]$NoNewWindow", "[switch]$Force"):
            self.assertIn(sw, s)

    def test_balanced(self):
        s = P.NEW_PS1
        for a, b in ("{}", "()", "[]"):
            self.assertEqual(s.count(a), s.count(b), a + b)
        # "$name:" inside a double-quoted string would be read as a scoped variable
        for lit in re.findall(r'"[^"\n]*"', s):
            self.assertIsNone(re.search(r"\$[A-Za-z_]+:", lit), lit)


class Patch(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()); (self.d / "scripts").mkdir()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, name, text, crlf=True):
        data = text.replace("\n", "\r\n") if crlf else text
        (self.d / "scripts" / name).write_bytes(data.encode("utf-8"))

    def test_unknown_launcher_is_refused_and_nothing_written(self):
        self.write("restart_dashboard.ps1", "# someone else's launcher\nparam()\n")
        self.write("dashboard.py", original_dashboard())
        before = sorted(p.name for p in (self.d / "scripts").iterdir())
        r = run_patch(self.d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("not the version this patch replaces", r.stdout)
        self.assertEqual(sorted(p.name for p in (self.d / "scripts").iterdir()), before)
        self.assertNotIn(P.MARK, (self.d / "scripts" / "dashboard.py").read_text(encoding="utf-8"))

    def test_dashboard_patched_once_crlf_kept_and_compiles(self):
        self.write("restart_dashboard.ps1", P.NEW_PS1)          # launcher already done: skipped
        self.write("dashboard.py", original_dashboard())
        r = run_patch(self.d, "--check")
        self.assertEqual(r.returncode, 0, r.stdout); self.assertIn("CHECK OK: 1 file(s)", r.stdout)
        self.assertNotIn(P.MARK.encode(), (self.d / "scripts" / "dashboard.py").read_bytes())
        r = run_patch(self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        raw = (self.d / "scripts" / "dashboard.py").read_bytes()
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"))
        self.assertEqual(raw.count(P.MARK.encode()), 1)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        self.assertLess(text.index("SA_QUIET_REQUESTS"), text.index(P.ANCHOR))
        compile(text, "dashboard.py", "exec")
        self.assertTrue(list((self.d / "scripts").glob("dashboard.py.bak_dashhidden_*")))
        r = run_patch(self.d)
        self.assertEqual(r.returncode, 0); self.assertIn("Nothing to do.", r.stdout)
        self.assertEqual((self.d / "scripts" / "dashboard.py").read_bytes(), raw)

    def test_a_moved_anchor_is_refused(self):
        self.write("restart_dashboard.ps1", P.NEW_PS1)
        self.write("dashboard.py", original_dashboard().replace(P.ANCHOR, P.ANCHOR + P.ANCHOR, 1))
        r = run_patch(self.d)
        self.assertEqual(r.returncode, 2); self.assertIn("occurs 2 times", r.stdout)


class QuietRequests(unittest.TestCase):
    def test_request_lines_left_out_errors_kept(self):
        try:
            import flask  # noqa: F401
        except ImportError:
            self.skipTest("flask not installed")
        try:
            from werkzeug._internal import _log  # noqa: F401  (how the dev server logs a request)
        except ImportError:
            self.skipTest("werkzeug._internal._log not available")
        code = (
            "from flask import Flask\n"
            "from werkzeug._internal import _log\n"
            "import os\n"
            "app = Flask('t')\n"
            "@app.get('/boom')\n"
            "def boom(): raise RuntimeError('boom-dash-hidden')\n"
            + textwrap.dedent(P.INSERT)
            + "_log('info', '127.0.0.1 - - \"GET /ok HTTP/1.1\" 200 -')\n"
            "app.test_client().get('/boom')\n"
        )
        env = dict(os.environ, SA_QUIET_REQUESTS="1")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        self.assertIn("boom-dash-hidden", r.stderr)            # the traceback is still written
        self.assertNotIn("GET /ok", r.stderr)                  # the request line is not
        env.pop("SA_QUIET_REQUESTS")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        self.assertIn("GET /ok", r.stderr)                     # without the flag, nothing changes


if __name__ == "__main__":
    unittest.main()
