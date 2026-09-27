# -*- coding: ascii -*-
"""TRANSLATION_FILTERS_2026_09_27 - fixtures for text_filters refusal / echo tests.
Run: python -m unittest tests.test_translation_filters -v   (from the repo root)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import text_filters as tf

KEEP, EMPTY, CUT = 1, 0, 2
SALVAGE_CASES = [
    ('en', 'In an etymological explanation (nirvacana), the remainder of the sentence that is to be repeated does not cause modification, [so holds] Bh\u0101radv\u0101ja. //', 1),
    ('en', 'The remainder of the sentence (v\u0101kya\u015be\u1e63a) is not modified, says Bh\u0101radv\u0101ja. //', 1),
    ('en', "He said: 'I am sorry, O king, for I have sinned.' //", 1),
    ('en', 'Then Indra said to V\u1e5btra: "I cannot identify you among the gods." //', 1),
    ('en', 'The rest of the text of the mantra is recited silently. //', 1),
    ('en', '[ILLEGIBLE]', 0),
    ('en', "I'm sorry, but I cannot translate this snippet.", 0),
    ('en', 'This does not appear to be Sanskrit.', 0),
    ('en', 'This appears to be a list of page numbers.', 0),
    ('en', 'The provided text is garbled.', 0),
    ('en', 'The first line means: the king went to the forest. The remainder of the text is illegible OCR.', 2),
    ('en', 'The king went to the forest. The rest of the text is garbled.', 2),
    ('en', 'Indra slew V\u1e5btra. The remainder of the passage is unclear due to OCR errors.', 2),
    ('hi', '[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]', 0),
    ('hi', '\u0907\u0938 \u092a\u094d\u0930\u0915\u093e\u0930 \u092d\u0915\u094d\u0924\u093f \u0915\u093e \u0905\u0927\u093f\u0915\u093e\u0930 \u0938\u0941\u0938\u094d\u092a\u0937\u094d\u091f \u0939\u0948\u0964 [\u0905\u0938\u094d\u092a\u0937\u094d\u091f]', 1),
    ('hi', '[\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0964', 0),
    ('hi', '[\u0905\u0938\u094d\u092a\u0937\u094d\u091f] [\u0905\u0938\u094d\u092a\u0937\u094d\u091f]', 0),
    ('hi', '\u0930\u093e\u091c\u093e [\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0935\u0928 \u0915\u094b \u0917\u092f\u093e\u0964', 1),
    ('hi', '\u092f\u0939 \u092a\u093e\u0920 \u092d\u093e\u0930\u0926\u094d\u0935\u093e\u091c \u0915\u0947 \u092e\u0924 \u092e\u0947\u0902 \u0935\u093f\u0915\u093e\u0930 \u0928\u0939\u0940\u0902 \u0915\u0930\u0924\u093e \u0939\u0948\u0964 //', 1),
    ('hi', '\u0936\u0947\u0937 \u092a\u093e\u0920 \u092e\u0947\u0902 \u0935\u093e\u0915\u094d\u092f\u0936\u0947\u0937 \u0915\u093e \u0935\u093f\u0915\u093e\u0930 \u0928\u0939\u0940\u0902 \u0939\u094b\u0924\u093e \u2014 \u0910\u0938\u093e \u092d\u093e\u0930\u0926\u094d\u0935\u093e\u091c \u0915\u0939\u0924\u0947 \u0939\u0948\u0902\u0964 //', 1),
    ('hi', '\u092f\u0939\u093e\u0901 \u092f\u0939 \u0938\u094d\u092a\u0937\u094d\u091f \u0928\u0939\u0940\u0902 \u0915\u093f\u092f\u093e \u0917\u092f\u093e \u0915\u093f \u0915\u094c\u0928-\u0938\u093e \u092a\u0926 \u0935\u093f\u0915\u0943\u0924 \u0939\u094b\u0924\u093e \u0939\u0948, \u0915\u093f\u0928\u094d\u0924\u0941 \u092d\u093e\u0930\u0926\u094d\u0935\u093e\u091c \u0915\u093e \u092e\u0924 \u0939\u0948\u0964 //', 1),
    ('hi', '\u0930\u093e\u091c\u093e \u0928\u0947 \u0915\u0939\u093e \u2014 \u092e\u0941\u091d\u0947 \u0915\u094d\u0937\u092e\u093e \u0915\u0930\u094b, \u092e\u0948\u0902\u0928\u0947 \u0905\u092a\u0930\u093e\u0927 \u0915\u093f\u092f\u093e \u0939\u0948\u0964 //', 1),
    ('hi', '\u0930\u093e\u091c\u093e \u0935\u0928 \u0915\u094b \u0917\u092f\u093e\u0964 \u0936\u0947\u0937 \u092a\u093e\u0920 \u0905\u0938\u094d\u092a\u0937\u094d\u091f \u0939\u0948\u0964', 2),
    ('hi', '\u092f\u0939 \u092a\u093e\u0920 \u0913\u0938\u0940\u0906\u0930 \u0924\u094d\u0930\u0941\u091f\u093f \u0915\u0947 \u0915\u093e\u0930\u0923 \u0905\u092a\u0920\u0928\u0940\u092f \u0939\u0948\u0964', 0),
    ('hi', '\u092e\u0941\u091d\u0947 \u0915\u094d\u0937\u092e\u093e \u0915\u0930\u0947\u0902, \u092e\u0948\u0902 \u0907\u0938 \u092a\u093e\u0920 \u0915\u093e \u0905\u0928\u0941\u0935\u093e\u0926 \u0928\u0939\u0940\u0902 \u0915\u0930 \u0938\u0915\u0924\u093e\u0964', 0),
]
ECHO_CASES = [
    ('This is stated in the \u015aatapatha (\u092e\u093e. \u0936. \u092a. \u092c\u094d\u0930\u093e. \u096d \u0964 \u0968 \u0964 \u0967 \u0964 \u0968\u096a). //', False),
    ('The first ka\u1e47\u1e0dik\u0101 ends here. \u0965 \u0967 \u0965', False),
    ('This is stated in the \u015aatapatha (M\u0101. \u015aa. Pa. Br\u0101. 7.2.1.24). //', False),
    ('\u0905\u0925 \u0924\u0943\u0924\u0940\u092f\u093e \u0915\u0923\u094d\u0921\u093f\u0915\u093e \u0964 \u0965 \u0969 \u0965', True),
    ('tatra \u096f sa gacchati', True),
    ('(\u092e\u093e. \u0936. \u092a. \u092c\u094d\u0930\u093e. \u096d \u0964 \u0968 \u0964 \u0967 \u0964 \u0968\u096a)', True),
    ('\u0930\u093e\u092e\u094b \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f', True),
]


class Salvage(unittest.TestCase):
    def test_cases(self):
        for lang, text, want in SALVAGE_CASES:
            got = tf.salvage_translation(text, lang=lang)
            kind = KEEP if got == text else (EMPTY if got == "" else CUT)
            self.assertEqual(kind, want, "%s %r -> %r" % (lang, text, got))
            if kind == CUT:
                self.assertTrue(got.endswith(" [\u2026]"), got)

    def test_every_hard_phrase_still_counts_anywhere(self):
        for ph in tf.JUNK_PHRASES:
            if ph in tf._AMBIGUOUS_EN:
                continue
            out = "Word " + ph + " here"
            self.assertEqual(tf.salvage_translation(out), "", ph)
            self.assertTrue(tf.is_translation_boilerplate(out), ph)

    def test_ambiguous_phrase_counts_with_a_cue(self):
        for ph in sorted(tf._AMBIGUOUS_EN):
            out = "Word " + ph + " the text; it is illegible OCR"
            self.assertEqual(tf.salvage_translation(out), "", ph)

    def test_hindi_token_is_boilerplate(self):
        self.assertTrue(tf.is_translation_boilerplate("[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]", lang="hi"))

    def test_clean_text_unchanged(self):
        s = "Vai\u015bamp\u0101yana said: the king went to the forest. //"
        self.assertEqual(tf.salvage_translation(s), s)
        self.assertFalse(tf.is_translation_boilerplate(s))


class Echo(unittest.TestCase):
    def test_cases(self):
        for text, want in ECHO_CASES:
            self.assertEqual(tf.is_source_echo("", text, "en"), want, repr(text))


if __name__ == "__main__":
    unittest.main()
