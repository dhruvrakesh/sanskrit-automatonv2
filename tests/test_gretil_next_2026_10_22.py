# -*- coding: ascii -*-
"""GRETIL_NEXT_2026_10_22: gretil_library.py --match prints the commands themselves (the extract and the preview) for
the strong matches without a witness, and points to ocr_benchmark.py when each has one; the patcher applies once,
from the copy it found. A made-up zip and made-up pages in a temp folder; never data/context.db, never the network."""
import json, random, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "gretil_library.py"
PAT = REPO / "scripts" / "patch_gretil_next_2026_10_22.py"
MARK = "GRETIL_NEXT_2026_10_22"
APPLIED = MARK.encode() in TOOL.read_bytes()
SYL = [("ka", "\u0915"), ("gi", "\u0917\u093f"), ("tu", "\u0924\u0941"), ("pe", "\u092a\u0947"), ("ro", "\u0930\u094b"),
       ("ma", "\u092e"), ("sa", "\u0938"), ("ha", "\u0939"), ("dhi", "\u0927\u093f"), ("ya", "\u092f"), ("va", "\u0935"),
       ("la", "\u0932"), ("ja", "\u091c"), ("ca", "\u091a"), ("da", "\u0926"), ("ba", "\u092c"), ("pha", "\u092b")]


def verses(seed, n=30):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        words = [[r.choice(SYL) for _ in range(r.randint(2, 4))] for _ in range(10)]
        out.append((" ".join("".join(s[0] for s in w) for w in words), " ".join("".join(s[1] for s in w) for w in words)))
    return out


def plain(title, lines):
    return ("%s\n\n# Header\n\n## Source: \n   - Ed. X, Poona 1998.\n\n## Licence:\n   Distributed under a Creative "
            "Commons Attribution-NonCommercial-ShareAlike 4.0 International License.\n\n# Text\n\n%s\n" % (
                title, "\n".join(lines)))


@unittest.skipUnless(APPLIED, "GRETIL_NEXT_2026_10_22 is not applied here")
class TheNext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "raw").mkdir(parents=True)
        with zipfile.ZipFile(t / "1_sanskr.zip", "w") as z:
            for k, (doc, stem) in enumerate((("D1", "sa_one"), ("D2", "sa_two"), ("D3", "sa_three"))):
                vs = verses(7 + k)
                z.writestr("1_sanskr/tei/transformations/plaintext/%s.txt" % stem, plain(stem, [i for i, _ in vs]))
                for p in range(3):
                    (t / "data" / "raw" / ("%s_%04d.jsonl" % (doc, p + 1))).write_text("".join(
                        json.dumps({"text": d}, ensure_ascii=False) + "\n" for _, d in vs[p * 10:(p + 1) * 10]),
                        encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_match(self):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t), "--zip", str(self.t / "1_sanskr.zip"),
                            "--out-dir", str(self.t / "out"), "--match", "--doc", "D1", "--doc", "D2", "--doc", "D3"],
                           capture_output=True,
                           text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_the_commands_themselves(self):
        out = self.run_match()
        self.assertIn("NEXT: python scripts\\gretil_library.py --extract 1_sanskr/tei/transformations/html/sa_one.htm "
                      "--doc D1", out)
        self.assertIn("python scripts\\etext_witness.py --doc D1 --file sources\\D1\\sa_one.htm   (the preview)", out)
        self.assertNotIn("MEMBER", out)
        (self.t / "data" / "raw_witness" / "D1__w_gretil").mkdir(parents=True)
        out = self.run_match()
        self.assertNotIn("--doc D1\n", out, "D1 has its witness now")
        self.assertIn("--extract 1_sanskr/tei/transformations/html/sa_two.htm --doc D2", out)
        for d in ("D2", "D3"):
            (self.t / "data" / "raw_witness" / (d + "__w_etext")).mkdir(parents=True)
        out = self.run_match()
        self.assertIn("every strong match has its witness", out)
        self.assertIn("ocr_benchmark.py", out)
        self.assertNotIn("--extract 1_sanskr", out)


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(TOOL.parent.glob(TOOL.name + ".bak_gretilnext_*"))
        if not baks:
            self.skipTest("no .bak_gretilnext_ copy here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(baks[0], t / "scripts" / TOOL.name)
            pat = [sys.executable, str(PAT)]
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((t / "scripts" / TOOL.name).read_bytes(), TOOL.read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
