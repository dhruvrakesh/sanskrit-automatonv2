# -*- coding: ascii -*-
"""KIN_ALSO_2026_10_24: after the plan of the full run (--per-source 0) with entries unread, kin_index.py's ALSO line
gives the command that reads them (--yes --per-source 0 and a --max-usd); after the trial's plan it is as before. A
made-up database and a stub model in a temp folder; never data/context.db, never the network."""
import contextlib, importlib.util, io, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "kin_index.py"
BASE_TEST = REPO / "tests" / "test_kin_index_2026_10_23.py"
PAT = REPO / "scripts" / "patch_kin_also_2026_10_24.py"
MARK = "KIN_ALSO_2026_10_24"
ON = TOOL.exists() and MARK.encode() in TOOL.read_bytes() and BASE_TEST.exists()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@unittest.skipUnless(ON, "KIN_ALSO_2026_10_24 is not applied here")
class TheAlso(unittest.TestCase):
    def setUp(self):
        self.B = load(BASE_TEST, "kin_base_also_t")
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "shelf").mkdir(parents=True)
        self.B.make_db(t / "data" / "context.db")
        self.B.make_claims(t / "data" / "shelf" / "claims.db")
        self.m = load(TOOL, "kin_also_t")

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        buf = io.StringIO()
        calls = []
        with contextlib.redirect_stdout(buf):
            rc = self.m.main(["--root", str(self.t)] + list(a), caller=self.B.stub(calls))
        return rc, buf.getvalue(), calls

    def test_the_full_plan_names_its_run(self):
        rc, out, calls = self.run_main("--yes", "--per-source", "1")     # one entry of each index read
        self.assertEqual(rc, 0, out)
        rc, out, calls = self.run_main("--per-source", "0")
        self.assertEqual((rc, calls), (0, []), out)
        also = [ln for ln in out.splitlines() if ln.startswith("ALSO:")]
        self.assertEqual(len(also), 1, out)
        self.assertIn("entries in all are not read yet: python scripts\\kin_index.py --yes --per-source 0 --max-usd",
                      also[0])

    def test_the_trial_as_before(self):
        rc, out, calls = self.run_main("--yes", "--per-source", "1")
        rc, out, calls = self.run_main()
        also = [ln for ln in out.splitlines() if ln.startswith("ALSO:")]
        self.assertEqual(also, ["ALSO: 1 entries of the trial are not read yet: python scripts\\kin_index.py --yes"]
                         if also else [], out)

    def test_ascii_and_mark(self):
        for f in (TOOL, PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
