# -*- coding: ascii -*-
"""LEGACY_TESTS_2026_10_22: scripts/sandhi_split.py --json reads Devanagari on stdin and gives its splits (in safe
mode, the default: deterministic, never a crash). It was a pytest function, which `python -m unittest` never ran."""
import json, os, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORD = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"


class TheSplit(unittest.TestCase):
    def test_json_gives_the_splits(self):
        p = subprocess.run([sys.executable, str(REPO / "scripts" / "sandhi_split.py"), "--json"], input=WORD.encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO), timeout=120,
                           env=dict(os.environ, SA_SAFE_MODE="1", PYTHONIOENCODING="utf-8"))
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = json.loads(p.stdout.decode("utf-8"))
        self.assertIn("splits", out)
        self.assertTrue(out["splits"] and all(isinstance(s, list) for s in out["splits"]))


if __name__ == "__main__":
    unittest.main()
