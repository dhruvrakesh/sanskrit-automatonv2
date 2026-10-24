# -*- coding: ascii -*-
"""MAINT_GUARD_2026_10_24: scripts/maintenance_runner.ps1 never stops in silence: the API check's own error is a
logged SKIP, and any error no step catches is a logged FAIL with exit 1 (health_watch.py reads it). The rest of the
runner (the steps, step d, the guards between steps) is as it was. Text only; PowerShell is not run here."""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "maintenance_runner.ps1"
PAT = REPO / "scripts" / "patch_maint_guard_2026_10_24.py"
MARK = "MAINT_GUARD_2026_10_24"


class TheRunner(unittest.TestCase):
    def setUp(self):
        b = RUNNER.read_bytes()
        if MARK.encode() not in b:
            self.skipTest("MAINT_GUARD_2026_10_24 is not applied here")
        self.assertTrue(all(x < 128 for x in b), "PowerShell 5.1 reads it in the system code page")
        self.s = b.decode("ascii")

    def test_the_guards(self):
        s = self.s
        t = s.index("trap {")
        self.assertLess(s.index("function Log($m)"), t, "the trap logs through Log")
        self.assertLess(t, s.index('Log "TICK - maintenance runner started'))
        self.assertIn('Log ("FAIL: the runner stopped on an error no step caught: " + $_.Exception.Message)', s)
        self.assertIn("exit 1", s[t:t + 200])
        c = s.index("$net = Test-NetConnection generativelanguage.googleapis.com")
        self.assertLess(s.rindex("try {", 0, c), c)
        self.assertIn('Log ("SKIP: the API check failed: " + $_.Exception.Message); exit 0', s)
        self.assertLess(s.index('if (-not $net) { Log "SKIP: no API connectivity"; exit 0 }'), s.index('Log "START maintenance"'))

    def test_the_rest_kept(self):
        s = self.s
        for x in ('Log "START maintenance"', "STEP d links", "scripts\\entity_links.py --scheduled --claims data\\shelf\\claims.db",
                  'if (Test-Path "data\\shelf\\kin.db")', "DONE maintenance"):
            self.assertIn(x, s, x)
        self.assertEqual(s.count('if (Test-Writer "c") { exit 0 }'), 1)

    def test_ascii_and_mark(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
