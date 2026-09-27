# -*- coding: ascii -*-
"""TRANSLATION_FILTERS2_2026_09_27 - lacuna tokens inside a translation are kept."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import text_filters as tf
import infer_mt

KEEP, EMPTY, CUT = 1, 0, 2
CASES = [
    ('en', 'She said: "O venerable Brahmanas, you should greatly esteem that very thing, that from us [ILLEGIBLE]. This Aksara, O Gargi, is unseen, yet it is the Seer." //', 1),
    ('en', '[ILLEGIBLE] Whoever would accept that much, he would obtain this third pada of her. //', 1),
    ('en', '[ILLEGIBLE]', 0),
    ('en', '[ILLEGIBLE].', 0),
    ('en', '[ILLEGIBLE] [ILLEGIBLE] //', 0),
    ('en', '[ ILLEGIBLE ]', 0),
    ('en', 'The king went to the forest. The rest of the text is illegible.', 2),
    ('en', 'The text is illegible OCR noise.', 0),
    ('en', 'I cannot translate this [ILLEGIBLE] passage.', 0),
    ('hi', '[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]', 0),
    ('hi', '[\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0915\u094d\u092f\u094b\u0902\u0915\u093f \u092d\u0942\u0937\u094d\u092f (\u092a\u094d\u0930\u0915\u091f \u0935\u0938\u094d\u0924\u0941\u0913\u0902) \u0915\u0940 \u0935\u094d\u092f\u093e\u092a\u0915\u0924\u093e \u0939\u0948\u0964', 1),
    ('hi', '\u0930\u093e\u091c\u093e \u0935\u0928 \u0915\u094b \u0917\u092f\u093e\u0964 [ILLEGIBLE]', 1),
    ('hi', '\u092f\u0939 \u092a\u093e\u0920 \u0913\u0938\u0940\u0906\u0930 \u0924\u094d\u0930\u0941\u091f\u093f \u0915\u0947 \u0915\u093e\u0930\u0923 \u0905\u092a\u0920\u0928\u0940\u092f \u0939\u0948\u0964', 0),
]


class Lacuna(unittest.TestCase):
    def test_cases(self):
        for lang, text, want in CASES:
            got = tf.salvage_translation(text, lang=lang)
            kind = KEEP if got == text else (EMPTY if got == "" else CUT)
            self.assertEqual(kind, want, "%s %r -> %r" % (lang, text, got))

    def test_bare_token_is_boilerplate_inline_is_not(self):
        self.assertTrue(tf.is_translation_boilerplate("[ILLEGIBLE]"))
        self.assertFalse(tf.is_translation_boilerplate("The king [ILLEGIBLE] went to the forest."))


class Prompts(unittest.TestCase):
    def test_versions_and_rules(self):
        self.assertEqual(infer_mt.PROMPT_VERSIONS["en"], "v3-2026-09-27")
        self.assertEqual(infer_mt.PROMPT_VERSIONS["hi"], "hi-v3-2026-09-27")
        self.assertIn("ONLY when no part of the text can be read", infer_mt._SYSTEM_PROMPT_BASE)
        self.assertIn("\u0906\u0902\u0936\u093f\u0915 \u0915\u094d\u0937\u0924\u093f", infer_mt._SYSTEM_PROMPT_HI)
        self.assertNotIn("\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928 \u0928\u0947", infer_mt._SYSTEM_PROMPT_HI)


if __name__ == "__main__":
    unittest.main()
