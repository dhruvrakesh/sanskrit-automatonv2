# -*- coding: ascii -*-
"""ASK_HOMONYM_2026_10_24: the Professor's instruction says what an index's numbered name means (one of several
persons of that name) and keeps them apart; the rest of the instruction (ASK_PROF_2026_10_23) is as it was. The
patcher writes once, line endings kept. Temp folders only."""
import ast, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "scripts" / "dashboard.py"
PAT = REPO / "scripts" / "patch_ask_homonym_2026_10_24.py"
MARK = "ASK_HOMONYM_2026_10_24"
ON = DASH.exists() and MARK.encode() in DASH.read_bytes()


def instruction(src: str) -> str:
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_ASK_SYSTEM_PROF" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("no _ASK_SYSTEM_PROF")


@unittest.skipUnless(ON, "ASK_HOMONYM_2026_10_24 is not applied to scripts/dashboard.py here")
class TheInstruction(unittest.TestCase):
    def test_numbered_persons_kept_apart(self):
        s = instruction(DASH.read_text(encoding="utf-8"))
        for x in ("A name with a number, as Janamejaya (II) or Jaratkaru[2], is one of several persons",
                  "keep each numbered person apart", "never join two of them into one life or one line of descent",
                  "say which person a statement is about"):
            self.assertIn(x, s)
        for x in ("USING ONLY the evidence given", "do not speak as any real person",
                  "never quote or paraphrase a scholar from memory", "Sanskrit names in IAST."):
            self.assertIn(x, s, "ASK_PROF's instruction kept")

    def test_the_patcher_writes_once_and_keeps_crlf(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        baks = sorted(DASH.parent.glob("dashboard.py.bak_ask_homonym_*"))
        if not baks:
            self.skipTest("no backup of the file before the patch here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            raw = baks[0].read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            (t / "scripts" / "dashboard.py").write_bytes(raw)
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = (t / "scripts" / "dashboard.py").read_bytes()
            self.assertIn(MARK.encode(), out)
            self.assertNotIn(b"\n", out.replace(b"\r\n", b""), "CRLF kept")
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
