# -*- coding: ascii -*-
"""LEGACY_TESTS_2026_10_22: scripts/morph_parse.py --json reads Devanagari on stdin and names the engine that parsed
it (in safe mode, the default, the heuristic one: no network, no model). It was a pytest function, which
`python -m unittest` never ran ("NO TESTS RAN" on the PC, 22 Oct)."""
import json, os, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORD = "\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"


class TheMorph(unittest.TestCase):
    def test_json_names_the_engine(self):
        p = subprocess.run([sys.executable, str(REPO / "scripts" / "morph_parse.py"), "--json"], input=WORD.encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO), timeout=120,
                           env=dict(os.environ, SA_SAFE_MODE="1", PYTHONIOENCODING="utf-8"))
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = json.loads(p.stdout.decode("utf-8"))
        self.assertIn("engine", out)
        self.assertEqual(out.get("tokens"), [WORD])


if __name__ == "__main__":
    unittest.main()
