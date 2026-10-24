# -*- coding: ascii -*-
"""KIN_CLOSE_2026_10_24: scripts/kin_index.py closes its store (data/shelf/kin.db) when main() returns or raises, so
Windows can delete, move or back up the file. Before the fix the two reading tests of RELATIONS_INDEX_2026_10_23 left
two handles open each, and on Windows the temp folder's cleanup raised (errors=2). Here: after every kind of run no
handle into the temp folder is left (counted in /proc on Linux; on Windows the move and the cleanup are the test), and a
run that raises closes its store too. A made-up database and a stub model in a temp folder; never data/context.db,
never the network."""
import contextlib, importlib.util, io, os, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "kin_index.py"
PAT = REPO / "scripts" / "patch_kin_close_2026_10_24.py"
BASE_TEST = REPO / "tests" / "test_kin_index_2026_10_23.py"
MARK = "KIN_CLOSE_2026_10_24"
ON = TOOL.exists() and MARK.encode() in TOOL.read_bytes() and BASE_TEST.exists()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def held(root: Path) -> list:
    """The files under root this process still has open (Linux: /proc/self/fd); [] where that cannot be read."""
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return []
    r, out = str(root.resolve()), []
    for fd in os.listdir(str(fd_dir)):
        try:
            p = os.readlink(str(fd_dir / fd))
        except OSError:
            continue
        if p.startswith(r):
            out.append(p)
    return out


@unittest.skipUnless(ON, "KIN_CLOSE_2026_10_24 is not applied here")
class TheStoreIsClosed(unittest.TestCase):
    def setUp(self):
        self.B = load(BASE_TEST, "kin_base_t")
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "shelf").mkdir(parents=True)
        self.db = t / "data" / "context.db"
        self.B.make_db(self.db)
        self.B.make_claims(t / "data" / "shelf" / "claims.db")
        self.m = load(TOOL, "kin_close_t")
        self.calls = []
        self.kin = t / "data" / "shelf" / "kin.db"

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.m.main(["--root", str(self.t)] + list(a), caller=self.B.stub(self.calls))
        return rc, buf.getvalue()

    def assert_free(self, what: str):
        self.assertEqual(held(self.t), [], "%s: a file of the temp folder is still open" % what)
        self.assertEqual(self.m._STORES, [], "%s: a store is still listed" % what)
        if self.kin.exists():
            moved = self.kin.with_name("kin.db.moved")
            os.replace(str(self.kin), str(moved))     # Windows refuses this while the file is open
            os.replace(str(moved), str(self.kin))

    def test_every_kind_of_run(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        self.assert_free("the plan")
        rc, out = self.run_main("--yes")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls), 3, out)
        self.assert_free("the read")
        rc, out = self.run_main("--check")
        self.assertEqual(rc, 0, out)
        self.assertIn("relations read", out)
        self.assert_free("the check")
        rc, out = self.run_main("--show", "Janamejaya")
        self.assertEqual(rc, 0, out)
        self.assertIn("relation(s) name Janamejaya", out)
        self.assert_free("the show")
        rc, out = self.run_main("--yes", "--max-usd", "0.0001")
        self.assertEqual(rc, 0, out)
        self.assert_free("a read stopped at --max-usd")

    def test_a_run_that_raises(self):
        def boom(*a, **k):
            raise RuntimeError("the check broke")
        self.m.check = boom
        with self.assertRaises(RuntimeError):
            self.run_main("--yes")
        self.assert_free("a run that raised")
        self.assertEqual(len(self.calls), 3, "the read before the raise was stored")

    def test_the_same_output(self):
        rc, out = self.run_main("--yes")
        self.assertIn("read: 3 call(s), 4 entries", out)
        self.assertTrue((self.t / "exports" / "kin_edges.csv").exists())
        self.assertTrue(callable(self.m.run), "the run itself, main() its wrapper")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (TOOL, PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            if f != TOOL or MARK.encode() in b:
                self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
