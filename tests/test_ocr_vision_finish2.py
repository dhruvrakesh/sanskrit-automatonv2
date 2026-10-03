# -*- coding: ascii -*-
"""VISION_FINISH2_2026_10_03. python -m unittest tests.test_ocr_vision_finish2 -v
Drives transcribe_robust() with a FAKE transcribe and synthetic PIL images. No
network, no API key, no database. Fails before the patch, passes after."""
import importlib.util, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("ocr_vision2_under_test", str(REPO / "scripts" / "ocr_vision.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


class _FR:
    def __init__(self, name): self.name = name


class _Resp:
    def __init__(self, finish):
        self.candidates = [type("C", (), {"finish_reason": _FR(finish)})()] if finish else []


class Fake:
    def __init__(self, script, band_script=None):
        self.script = list(script); self.band_script = list(band_script or []); self.calls = []

    def __call__(self, img, model, temperature=0.0, max_tokens=8192):
        is_band = img is not None and getattr(img, "height", 0) < 1000
        self.calls.append(("band" if is_band else "page", temperature, max_tokens))
        text, finish = (self.band_script if is_band else self.script).pop(0)
        return text, _Resp(finish), len(text)


def page_image():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 1200), "white")
    d = ImageDraw.Draw(im)
    for y in list(range(40, 560, 30)) + list(range(640, 1160, 30)):   # text lines; white gap 560-640
        d.rectangle((20, y, 380, y + 14), fill="black")
    return im


class VisionFinish2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_marker(self):
        self.assertIn("VISION_FINISH2_2026_10_03", (REPO / "scripts" / "ocr_vision.py").read_text(encoding="utf-8"))

    def test_max_tokens_with_two_chars_climbs_ladder(self):
        f = Fake([("ab", "MAX_TOKENS"), ("full page text", "STOP")])
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "full page text")
        self.assertEqual([c[2] for c in f.calls], [8192, 16384])
        self.assertEqual(len(disc), 1)

    def test_near_empty_stop_is_retried(self):
        f = Fake([("ab", "STOP"), ("now readable", "STOP")])
        text, resp, n, disc = self.m.transcribe_robust(None, "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "now readable")
        self.assertEqual(f.calls[1][1], 0.3, "temperature ladder used")

    def test_cut_rows_land_in_the_white_gap(self):
        im = page_image()
        cuts = self.m._cut_rows(im, 2)
        self.assertEqual(len(cuts), 1)
        row = [im.getpixel((x, cuts[0])) for x in range(0, 400, 10)]
        self.assertTrue(all(px == (255, 255, 255) for px in row), "the cut must fall on a blank row, not through a line")
        self.assertTrue(504 <= cuts[0] <= 696, cuts)

    def setUp(self):
        self.m.RECITATION_TILES = (2, 3)   # opt-in since VISION_FINISH3 (OCR_RECITATION_TILES)

    def test_recitation_is_tiled_and_joined(self):
        f = Fake([("", "RECITATION")] * 3, band_script=[("top half", "STOP"), ("bottom half", "STOP")])
        text, resp, n, disc = self.m.transcribe_robust(page_image(), "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "top half\nbottom half")
        self.assertEqual(self.m.LAST_TILES[0], 2)
        self.assertEqual(len(disc), len(f.calls) - 1, "every paid call except the kept one is metered")

    def test_partial_tiling_never_replaces_the_page(self):
        bands = [("top half", "STOP"), ("", "RECITATION"),                   # n=2: band 2 refused
                 ("one third", "STOP"), ("two third", "STOP"), ("", "RECITATION")]  # n=3: band 3 refused
        f = Fake([("", "RECITATION")] * 3, band_script=bands)
        text, resp, n, disc = self.m.transcribe_robust(page_image(), "m", "p", tfn=f, sleep_s=0)
        self.assertEqual(text, "", "a half page must not reach merge; Tesseract stays")
        self.assertEqual(self.m.LAST_TILES[0], 0)


if __name__ == "__main__":
    unittest.main()
