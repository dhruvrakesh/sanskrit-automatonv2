# -*- coding: ascii -*-
"""REPAIR_PARTIAL_2026_10_28: the repair rounds no longer stall behind a text whose pages left cost more than a round.
ocr_consensus.py --partial reads the pages that fit under --max-usd (the first of its order), not none; without it
the refusal is as before. repair_text.py --repair --partial passes it on and its refusal says so; repair_auto.py's
vision step asks for it. A made-up data folder and a stand-in repair_text.py: no model, no network."""
import importlib.util, json, re, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
sys.path.insert(0, str(REPO))
from tests.test_auto_repair_2026_10_25 import Base  # noqa: E402

MARK = "REPAIR_PARTIAL_2026_10_28"


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_partial", str(S / (name + ".py")))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FitPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oc = load("ocr_consensus")

    def test_without_partial_it_refuses_as_before(self):
        todo = ["p%d" % i for i in range(146)]
        part, est, said = self.oc.fit_pages(todo, 0.0087, 0.10, False)
        self.assertEqual((part, est), ([], 0.0))
        self.assertIn("REFUSING: estimate $1.2702 exceeds --max-usd 0.1000", said)

    def test_with_partial_the_first_pages_that_fit(self):
        todo = ["p%d" % i for i in range(146)]
        part, est, said = self.oc.fit_pages(todo, 0.0087, 0.10, True)
        self.assertEqual(part, todo[:11])
        self.assertLessEqual(est, 0.10)
        self.assertIn("PARTIAL", said)
        self.assertIn("11 of 146 page(s)", said)
        part, est, said = self.oc.fit_pages(todo, 0.02, 0.10, True)
        self.assertEqual(len(part), 5, "exactly at the cap counts")

    def test_not_one_page_fits(self):
        part, _e, said = self.oc.fit_pages(["a", "b"], 0.25, 0.10, True)
        self.assertEqual(part, [])
        self.assertIn("REFUSING", said)
        self.assertEqual(self.oc.fit_pages(["a"], 0.0, 0.10, True)[0], [], "no measured price: no guess")

    def test_wired(self):
        src = (S / "ocr_consensus.py").read_text(encoding="ascii")
        self.assertIn('ap.add_argument("--partial"', src)
        self.assertIn("todo, est, said_ = fit_pages(todo, cpp, args.max_usd, args.partial)", src)
        rt = (S / "repair_text.py").read_text(encoding="ascii")
        self.assertIn('+ (["--partial"] if a.partial else [])', rt)
        self.assertIn("--partial (REPAIR_PARTIAL_2026_10_28)", rt)
        for f in ("ocr_consensus.py", "repair_text.py", "repair_auto.py"):
            self.assertTrue((S / f).read_bytes().isascii(), f)
            self.assertIn(MARK.encode(), (S / f).read_bytes(), f)

    def test_repair_text_accepts_it(self):
        r = subprocess.run([sys.executable, str(S / "repair_text.py"), "--help"], capture_output=True, text=True,
                           timeout=60, cwd=str(REPO))
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertIn("--partial", r.stdout)


class TheRound(Base):
    def test_the_vision_step_asks_for_a_part(self):
        self.auto("--round")                       # the day's judgement
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        rep = [x for x in self.calls_made() if "--repair" in x]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0][:2], ["--doc", "A"])
        self.assertIn("--partial", rep[0])
        self.assertEqual(rep[0][rep[0].index("--max-usd") + 1], "0.10")


PAT = S / "patch_repair_partial_2026_10_28.py"
PFILES = ('scripts/ocr_consensus.py', 'scripts/repair_text.py', 'scripts/repair_auto.py', 'tests/test_read_in_2026_10_13.py',
          'tests/test_repair_next_2026_10_17.py')


def as_left(rel: str) -> bytes:
    """The file as the patch left it: the oldest later backup that carries MARK, else the file now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*") if ".bak_repairpartial_" not in b.name and MARK.encode() in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


@unittest.skipUnless(PAT.exists(), "patch_repair_partial_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in PFILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_repairpartial_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            for rel in ():
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes((REPO / rel).read_bytes())
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(PFILES), r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in PFILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual(got, as_left(rel), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
