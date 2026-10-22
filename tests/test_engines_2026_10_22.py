# -*- coding: ascii -*-
"""ENGINES_2026_10_22: scripts/source_fidelity.py reads any engine's OCR of our scan from a folder of page JSONL
(pages:<dir>/<doc>), relative to --root or absolute, and measures it by the same checks as ours (agreement, own
misreadings beside a second reading); a missing folder is said so; pages: counts as one of our readings. Temp files
only, never data/context.db, never the network."""
import json, random, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
TOOL = SCRIPTS / "source_fidelity.py"
PAT = SCRIPTS / "patch_engines_2026_10_22.py"
MARK = "ENGINES_2026_10_22"
HERE = MARK.encode() in TOOL.read_bytes()

R = random.Random(2210)
C = [chr(c) for c in range(0x0915, 0x0939)]
V = ["", "\u093e", "\u093f", "\u0940", "\u0941", "\u0947", "\u094b"]


def word(k):
    return "".join(R.choice(C) + R.choice(V) for _ in range(k))


def verse():
    return " ".join(word(R.randint(2, 4)) for _ in range(8)) + " \u0965"


VERSES = [verse() for _ in range(30)]


def slip(v: str, at: int, new: str) -> str:
    """The akshara starting at character `at` read as another consonant."""
    while at < len(v) and not ("\u0915" <= v[at] <= "\u0939"):
        at += 1
    return v[:at] + (new if v[at] != new else "\u0915") + v[at + 1:]


def pages(t: Path, folder: str, verses: list):
    d = t / folder
    d.mkdir(parents=True, exist_ok=True)
    for p in range(3):
        rows = verses[p * 10:(p + 1) * 10]
        (d / ("D_%04d.jsonl" % (p + 1))).write_text(
            "".join(json.dumps({"text": v, "engine": folder}, ensure_ascii=False) + "\n" for v in rows), encoding="utf-8")


@unittest.skipUnless(HERE, "ENGINES_2026_10_22 is not here")
class AnotherEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        (t / "ref.txt").write_text("\n\n".join(VERSES) + "\n", encoding="utf-8")
        tess = [slip(v, 4, "\u0918") if i % 2 == 0 else slip(v, 20, "\u0927") for i, v in enumerate(VERSES)]
        other = [slip(v, 12, "\u092c") if i % 10 == 3 else v for i, v in enumerate(VERSES)]
        pages(t, "data/raw", tess)
        pages(t, "data/raw_engine_x", other)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t), "--out-dir", str(self.t / "out")]
                           + list(args), capture_output=True, text=True, encoding="utf-8", timeout=180)
        return r.returncode, r.stdout + r.stderr

    def report(self):
        return json.loads(next((self.t / "out").glob("*.json")).read_text(encoding="utf-8"))

    def test_measured_as_ours_are(self):
        x = "pages:data/raw_engine_x/D"
        rc, out = self.run_tool("--ref", "file:ref.txt", "--cand", x, "--cand", "raw:D", "--pair", x + ",raw:D")
        self.assertEqual(rc, 0, out)
        r = self.report()
        self.assertGreater(r["readings"][x]["agree_pct"], r["readings"]["raw:D"]["agree_pct"])
        self.assertGreater(r["readings"][x]["agree_pct"], 98.0)
        self.assertIn(x, out)

    def test_an_absolute_folder(self):
        x = "pages:" + str(self.t / "data" / "raw_engine_x").replace("\\", "/") + "/D"
        rc, out = self.run_tool("--ref", "file:ref.txt", "--cand", x)
        self.assertEqual(rc, 0, out)
        self.assertIn(x, self.report()["readings"])

    def test_a_missing_folder_is_said(self):
        rc, out = self.run_tool("--ref", "file:ref.txt", "--cand", "pages:data/nothing/D")
        self.assertNotEqual(rc, 0)
        self.assertIn("no pages", out)
        rc, out = self.run_tool("--ref", "file:ref.txt", "--cand", "pages:D")
        self.assertNotEqual(rc, 0)
        self.assertIn("pages: wants a folder and a doc", out)

    def test_it_is_one_of_ours(self):
        sys.path.insert(0, str(SCRIPTS))
        import source_fidelity as sf
        self.assertIn("pages", sf.OUR_READINGS)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/source_fidelity.py",)

    @unittest.skipUnless(HERE, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("source_fidelity.py.bak_engines_*"))
        if not baks:
            self.skipTest("no .bak_engines_ copy here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(baks[0], t / "scripts" / "source_fidelity.py")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("source_fidelity.py.bak_witnessfix_*"))   # WITNESS_FIX_2026_10_22
            self.assertEqual((t / "scripts" / "source_fidelity.py").read_bytes(), (later[0] if later else TOOL).read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_it_needs_triangulate(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "scripts").mkdir()
            (Path(td) / "scripts" / "source_fidelity.py").write_text("# FIDELITY_2026_10_22\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("TRIANGULATE_2026_10_22", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
