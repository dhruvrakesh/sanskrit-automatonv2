# -*- coding: ascii -*-
"""HEAL_2026_10_28: (1) vamsa_view.py draws the same line in every run: a choice between two parents (or children) that
tie on everything else is made by the entry, never by a set's order, and every list ordered by head word ends with
the entry, as the site orders it; (2) test_edition_refs replays against the file as its patch left it, not as later
patches made it. The patcher replays on the copies from before it and does nothing the second time."""
import ast, importlib.util, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
PAT = S / "patch_heal_2026_10_28.py"
MARK = "HEAL_2026_10_28"
FILES = ("scripts/vamsa_view.py", "tests/test_edition_refs_2026_10_18.py")


def load(path: Path, name: str):
    if str(S) not in sys.path:
        sys.path.insert(0, str(S))
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def as_left(rel: str) -> bytes:
    """The file as this patch left it: the oldest later backup that carries MARK, else the file now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*") if ".bak_heal_" not in b.name and MARK.encode() in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


def graph(parents_order, children_order):
    """A child with two name-only parents of one name, tied on sex, strength and depth; a parent with two such children."""
    s = "inm"
    g = {"par": {(s, 1): [(s, e) for e in parents_order]}, "chi": {(s, 5): [(s, e) for e in children_order]},
         "sex": {}, "edges": {}, "up": {}, "down": {}, "shown": {(s, -10): "Diti", (s, -20): "Diti", (s, 1): "Asuras",
                                                                  (s, 5): "Kasyapa", (s, -30): "Daityas", (s, -40): "Daityas"}}
    return g


class TestTies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vv = load(S / "vamsa_view.py", "vamsa_view_heal")

    def test_the_same_parent_whatever_the_order(self):
        if MARK.encode() not in (S / "vamsa_view.py").read_bytes():
            self.skipTest("patch_heal_2026_10_28.py not applied yet")
        a = self.vv._main_up(graph([-10, -20], []), "inm", 1)
        b = self.vv._main_up(graph([-20, -10], []), "inm", 1)
        self.assertEqual(a, b)
        self.assertEqual(a, [-20, 1], "the tie goes to the lower entry")

    def test_the_same_child_whatever_the_order(self):
        if MARK.encode() not in (S / "vamsa_view.py").read_bytes():
            self.skipTest("patch_heal_2026_10_28.py not applied yet")
        a = self.vv._main_down(graph([], [-30, -40]), "inm", 5)
        b = self.vv._main_down(graph([], [-40, -30]), "inm", 5)
        self.assertEqual(a, b)
        self.assertEqual(a, [-40])

    def test_every_sort_by_head_ends_with_the_entry(self):
        src = (S / "vamsa_view.py").read_text(encoding="ascii")
        if MARK not in src:
            self.skipTest("patch_heal_2026_10_28.py not applied yet")
        self.assertNotIn("key=lambda z: _head(g, src, z))", src)
        self.assertEqual(src.count("key=lambda z: (_head(g, src, z), z)"), 4)
        self.assertIn("_head(g, s, n[1]), n[1]))", src)


class TestEditionRefsReplay(unittest.TestCase):
    def test_compares_with_the_file_as_its_patch_left_it(self):
        t = (REPO / "tests" / "test_edition_refs_2026_10_18.py").read_text(encoding="ascii")
        if MARK not in t:
            self.skipTest("patch_heal_2026_10_28.py not applied yet")
        self.assertIn("self.assertEqual((t / f).read_bytes(), as_left(f), f)", t)
        tree = ast.parse(t)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "as_left")
        ns = {"Path": Path, "MARK": b"EDITION_REFS_2026_10_18"}
        exec(ast.get_source_segment(t, fn), ns)   # the test's own as_left, without importing its module
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "scripts").mkdir()
            f = d / "scripts" / "x.py"
            (d / "scripts" / "x.py.bak_editionrefs_20261018").write_bytes(b"before\n")
            later = d / "scripts" / "x.py.bak_proseedition_20261025"
            later.write_bytes(b"after EDITION_REFS_2026_10_18\n")
            f.write_bytes(b"after EDITION_REFS_2026_10_18 and PROSE_EDITION\n")
            ns["REPO"] = d
            self.assertEqual(ns["as_left"]("scripts/x.py"), b"after EDITION_REFS_2026_10_18\n")
            later.unlink()
            self.assertEqual(ns["as_left"]("scripts/x.py"), f.read_bytes(), "no later patch: the file as it is")


class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_heal_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 2 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual(got, as_left(rel), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
