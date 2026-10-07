# -*- coding: ascii -*-
"""VERIFY_NAMES_2026_10_07: three false failures of the story check found on 2026-10-07
(markandeya_purana #6 "Mount", #11 a quotation cut after "Alas!", #3 "Vapuh" inflected in the
passage) are fixed; the real failures (#5 a name the passages do not give, #10 sentences
without a citation) still fail. No network, no database."""
import importlib, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stories as S   # noqa: E402

FILL = (" The sages listened in silence while the forest grew dark around the hermitage, and the birds"
        " settled on the branches as the evening lamps were lit one by one. [1.1]") * 4


def given():
    return [
        (1, 1, "", "", "the sages listened in the forest at evening."),
        (29, 9, "", "", "after some time, the earth, oppressed by its burden, went to the peak of meru, "
                        "where the devas have their assembly hall. //"),
        (60, 10, "", "", "Alas! This is \u015aaivy\u0101, and this is that boy. So saying, he fell into a swoon. //"),
        (10, 3, "", "tasy\u0101\u1e43 sa janay\u0101m\u0101sa t\u0101c\u012b\u1e43 n\u0101ma | "
                    "muni\u015b\u0101p\u0101mivipru\u1e63\u1e6d\u0101\u1e43 vapumapsaras\u0101\u1e43 var\u0101\u1e43 ||",
         "he begot in her a daughter named taci, the best of apsarases, afflicted by a sage's curse. //"),
        (25, 8, "", "", "And why was that one daughter of Drupada, beautiful in form, the wife of the five sons of "
                        "P\u0101\u1e47\u1e0du? //"),
        (5, 5, "", "", "the city of parama\u015bobh\u0101 was bright. //"),
    ]


def run(text):
    importlib.reload(S)
    return S.verify({"story_en": text + FILL, "quote_sa": "", "quote_ref": ""}, given())["problems"]


def names(problems):
    return " ".join(p for p in problems if p.startswith("names not found"))


def uncited(problems):
    return [p for p in problems if "without a citation" in p]


class FalseFailuresFixed(unittest.TestCase):
    def test_title_word_is_not_a_name(self):
        p = run("The Earth went to Mount Meru and pleaded with the Devas for relief. [29.9]")
        self.assertNotIn("Mount", names(p), p)

    def test_quotation_is_not_cut_after_an_exclamation(self):
        p = run("Tormented by grief, he cried, \"Alas! This is \u015aaivy\u0101, and this is that boy,\" "
                "and fell into a swoon. [60.10]")
        self.assertEqual(uncited(p), [], p)

    def test_curly_quotation_too(self):
        p = run("Tormented by grief, he cried, \u201cAlas! This is \u015aaivy\u0101, and this is that boy,\u201d "
                "and fell into a swoon. [60.10]")
        self.assertEqual(uncited(p), [], p)

    def test_visarga_name_found_inflected(self):
        p = run("Her daughter T\u0101c\u012b was the Apsar\u0101 Vapu\u1e25 under a sage's curse. [10.3]")
        self.assertNotIn("Vapu", names(p), p)


class RealFailuresStay(unittest.TestCase):
    def test_name_the_passages_do_not_give(self):
        p = run("Jaimini asked why Draupad\u012b was the wife of five P\u0101\u1e47\u1e0du sons. [25.8]")
        self.assertIn("Draupad\u012b", names(p), p)

    def test_sentence_without_citation(self):
        p = run("King Hari\u015bcandra walked to the market and offered himself for sale before sunset. "
                "The sages listened in the forest at evening and said nothing at all. [1.1]")
        self.assertEqual(len(uncited(p)), 1, p)

    def test_visarga_stem_absent_or_inside_a_word(self):
        p = run("Then K\u1e5b\u1e63\u1e47a\u1e25 and R\u0101ma\u1e25 came to the bright city. [5.5]")
        n = names(p)
        self.assertIn("\u1e25", n, p)
        self.assertIn("R\u0101ma\u1e25", n, "a stem found only inside 'parama\u015bobh\u0101' must not count")

    def test_unbalanced_quote_does_not_hide_later_sentences(self):
        body = "He said \"go now to the forest and wait for me there. " + " ".join(
            "Then the king waited near the gate for a long time number %d." % i for i in range(6)) + " [1.1]"
        p = run(body)
        self.assertTrue(uncited(p), p)


if __name__ == "__main__":
    unittest.main()
