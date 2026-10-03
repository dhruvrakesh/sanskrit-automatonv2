# -*- coding: ascii -*-
"""VISION_FINISH3_2026_10_03. python -m unittest tests.test_ocr_vision_finish3 -v
Fake transcribe only. Fails before the patch, passes after."""
import importlib.util, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("ocr_vision3_under_test", str(REPO / "scripts" / "ocr_vision.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


class _FR:
    def __init__(self, n): self.name = n


class _Resp:
    def __init__(self, f): self.candidates = [type("C", (), {"finish_reason": _FR(f)})()]


class DeadlineExceeded(Exception):
    pass


class VisionFinish3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.m.RECITATION_TILES = ()   # the default

    def test_marker(self):
        self.assertIn("VISION_FINISH3_2026_10_03", (REPO / "scripts" / "ocr_vision.py").read_text(encoding="utf-8"))

    def test_recitation_costs_one_call_by_default(self):
        calls = []
        def f(img, model, temperature=0.0, max_tokens=8192):
            calls.append(temperature); return "", _Resp("RECITATION"), 0
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual((text, calls, disc, self.m.LAST_TILES[0]), ("", [0.0], [], 0))

    def test_transient_error_is_retried_once(self):
        state = {"n": 0}
        def f(img, model, temperature=0.0, max_tokens=8192):
            state["n"] += 1
            if state["n"] == 1:
                raise DeadlineExceeded("504 Deadline Exceeded")
            return "page text ok", _Resp("STOP"), 12
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual((text, state["n"]), ("page text ok", 2))

    def test_other_errors_still_raise(self):
        def f(img, model, temperature=0.0, max_tokens=8192):
            raise ValueError("bad image")
        with self.assertRaises(ValueError):
            self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)


if __name__ == "__main__":
    unittest.main()
