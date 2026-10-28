# -*- coding: ascii -*-
"""TAGS_2026_10_28: scripts/tags_2026_10_28.ps1 types the edition's own matter of the Hayasirsa and the Karanagama
through classify_apparatus.py and mark_passages.py only: a dry run unless -Apply; 68 listed passages of the
Hayasirsa's apparatus, each once, page 19 passage 12 left for a person; the types noise and frontmatter only; never
a command that writes otherwise. The file is read, nothing is run."""
import re, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PS = REPO / "scripts" / "tags_2026_10_28.ps1"


@unittest.skipUnless(PS.exists(), "tags_2026_10_28.ps1 is not here")
class TheTags(unittest.TestCase):
    def setUp(self):
        self.b = PS.read_bytes()
        self.s = self.b.decode("ascii")

    def test_ascii_and_marked(self):
        self.assertTrue(self.b.isascii())
        self.assertIn("TAGS_2026_10_28", self.s)

    def test_the_list(self):
        block = self.s[self.s.index("$P = @("):self.s.index(")", self.s.index("$P = @(") + 7)]
        pairs = re.findall(r'"(\d+) (\d+)"', block)
        self.assertEqual(len(pairs), 68)
        self.assertEqual(len(set(pairs)), 68)
        self.assertNotIn(("19", "12"), pairs, "half a verse, then the notes: a person's")

    def test_only_these_tools_and_types(self):
        cmds = [ln.strip() for ln in self.s.splitlines() if ln.strip().startswith("python ")]
        self.assertTrue(cmds)
        for c in cmds:
            self.assertRegex(c, r"^python scripts\\(classify_apparatus|mark_passages)\.py ")
            self.assertNotIn("--apply", c, "written only through -Apply ($A, $C)")
            self.assertNotIn("--undo", c)
        types = set(re.findall(r"--type (\w+)", self.s))
        self.assertEqual(types, {"noise", "frontmatter"})
        self.assertIn('if ($Apply) { $A = @("--apply"); $C = @("--apply") }', self.s)

    def test_the_texts(self):
        self.assertIn('$H = "HAYASHIRSHA_PANCARATRA"', self.s)
        self.assertIn('$K = "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi"', self.s)
        self.assertIn('--pages "1,3,4,8,17-25,153,155-181" --type frontmatter', self.s)
        self.assertIn('--pages "2,26,152,154,182" --type noise', self.s)


if __name__ == "__main__":
    unittest.main()
