# -*- coding: ascii -*-
"""LEGACY_TESTS_2026_10_22: scripts/normalize_text.py, which ingest_jsonl_fast.py and the heal and witness scripts call:
the dandas are kept (spaced, never made full stops), a lone | is a danda, invisible characters go, quotes and dashes
are plain, a verse ends at its double danda. The pytest function before ran normalize_text.py --json, a command line
the module no longer has; `python -m unittest` never ran it."""
import sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import normalize_text as nt  # noqa: E402

D, DD = "\u0964", "\u0965"
RAMAH, SITA = "\u0930\u093e\u092e\u0903", "\u0938\u0940\u0924\u093e"


class TheSanskrit(unittest.TestCase):
    def test_the_dandas_are_kept(self):
        self.assertEqual(nt.normalize_sanskrit(RAMAH + D), RAMAH + " " + D)
        self.assertEqual(nt.normalize_sanskrit(RAMAH + " | " + SITA), RAMAH + " " + D + " " + SITA, "a lone | is a danda")
        self.assertEqual(nt.count_dandas(RAMAH + " " + D + " " + SITA + " " + DD), (1, 1))

    def test_invisible_and_typographic(self):
        self.assertEqual(nt.normalize_sanskrit("a\u200bb\u00a0 c"), "ab c")
        self.assertEqual(nt.normalize_english("a\u2014b  \u201cc\u201d"), 'a-b "c"')

    def test_verses_end_at_the_double_danda(self):
        self.assertEqual(nt.split_on_double_danda("\u0915 " + DD + " \u0916 " + DD + " \u0917"),
                         ["\u0915 " + DD, "\u0916 " + DD, "\u0917"])
        self.assertEqual(nt.frac_devanagari("\u0915a"), 0.5)


if __name__ == "__main__":
    unittest.main()
