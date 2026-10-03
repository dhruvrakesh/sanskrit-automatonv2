# -*- coding: ascii -*-
"""VISION_FINISH_2026_10_03. python -m unittest tests.test_ocr_vision_finish -v
Imports scripts/ocr_vision.py and drives transcribe_robust() with a FAKE
transcribe. No image, no network, no API key, no database. Fails before the
patch (no transcribe_robust / _finish_name), passes after."""
import importlib.util, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("ocr_vision_under_test", str(REPO / "scripts" / "ocr_vision.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


class _FR:
    def __init__(self, name): self.name = name


class _Cand:
    def __init__(self, fr): self.finish_reason = fr


class _Resp:
    def __init__(self, finish): self.candidates = [_Cand(_FR(finish))] if finish else []


class Fake:
    """Scripted transcribe(): returns the next (text, finish) and records the call."""
    def __init__(self, script):
        self.script = list(script); self.calls = []

    def __call__(self, img, model, temperature=0.0, max_tokens=8192):
        self.calls.append((temperature, max_tokens))
        text, finish = self.script.pop(0)
        return text, _Resp(finish), len(text)


class VisionFinish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_marker_and_cost(self):
        src = (REPO / "scripts" / "ocr_vision.py").read_text(encoding="utf-8")
        self.assertIn("VISION_FINISH_2026_10_03", src)
        self.assertEqual(self.m.COST_PER_PAGE, 0.00028)

    def test_finish_name(self):
        self.assertEqual(self.m._finish_name(_Resp("MAX_TOKENS")), "MAX_TOKENS")
        self.assertIsNone(self.m._finish_name(_Resp(None)))
        self.assertIsNone(self.m._finish_name(None))

    def test_first_call_success_is_unchanged(self):
        f = Fake([("page text", "STOP")])
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual((text, f.calls, disc), ("page text", [(0.0, 8192)], []))

    def test_max_tokens_climbs_the_budget_ladder_first(self):
        f = Fake([("", "MAX_TOKENS"), ("", "MAX_TOKENS"), ("page text", "STOP")])
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "page text")
        self.assertEqual(f.calls, [(0.0, 8192), (0.0, 16384), (0.0, 32768)])
        self.assertEqual(len(disc), 2, "both empty attempts were paid for and must be metered")

    def test_empty_for_another_reason_uses_temperature_ladder(self):
        # (2026-10-03: RECITATION now stops the ladder - VISION_FINISH3 - so use another reason here)
        f = Fake([("", "OTHER"), ("", "OTHER"), ("", "OTHER")])
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "")
        self.assertEqual(f.calls, [(0.0, 8192), (0.3, 8192), (0.7, 8192)])
        self.assertEqual(self.m._finish_name(resp), "OTHER")
        self.assertEqual(len(disc), 2)


if __name__ == "__main__":
    unittest.main()
