# -*- coding: ascii -*-
"""REPAIR_LOOP_2026_11_15. On 13 Nov the Ganita Yuktibhasa's repair, started from the desk, ran for 4.5 seconds and read
nothing: --repair sent the scan to ocr_consensus.py with the triage's threshold of 72, which let through only the 112
pages of low confidence (vision had read them already), while the assessment counted the other 227 pages and asked for
the same repair again. Now --repair reads the pages the assessment counts: when the text needs "repair first", every
page is queued (threshold 101) and vision skips the pages it has read."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import repair_text as rt   # noqa: E402

GANITA = {"doc": "Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V", "judged": {"level": "moderate"}, "vision_pct": 3.8,
          "pdfs": 339, "raw_pages": 339, "vision_pages": 112, "vision_gave_up": 0, "guard": False}


class TheCount(unittest.TestCase):
    def test_the_ganita(self):
        self.assertEqual(rt.repair_todo(GANITA), 227)

    def test_not_when_the_repair_is_not_asked(self):
        for change in ({"judged": {"level": "cosmetic"}}, {"vision_pct": 60.0}, {"pdfs": 0}, {"pdfs": 100},
                       {"vision_pages": 339}):
            self.assertEqual(rt.repair_todo(dict(GANITA, **change)), 0, change)

    def test_pages_vision_gave_up_on_are_not_counted(self):
        self.assertEqual(rt.repair_todo(dict(GANITA, vision_gave_up=7)), 220)


class TheRepair(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.saved = (rt.assess, rt.run, rt.report)
        self.calls = []
        rt.report = lambda r, doc, a=None: 0
        rt.run = lambda argv, keep=None, env_extra=None: (self.calls.append([str(x) for x in argv]), 0)[1]

    def tearDown(self):
        rt.assess, rt.run, rt.report = self.saved
        os.chdir(self.cwd)

    def threshold(self, r, *extra):
        rt.assess = lambda a: dict(r)
        self.calls.clear()
        self.assertEqual(rt.main(["--doc", r["doc"], "--repair", "--max-usd", "1.00"] + list(extra)), 0)
        argv = next(c for c in self.calls if c[1].endswith("ocr_consensus.py"))
        return argv[argv.index("--threshold") + 1]

    def test_the_pages_the_assessment_counts_go_to_vision(self):
        self.assertEqual(float(self.threshold(GANITA)), 101.0)

    def test_as_before_when_no_repair_is_asked(self):
        self.assertEqual(float(self.threshold(dict(GANITA, judged={"level": "cosmetic"}))), 72.0)

    def test_the_guard_and_an_explicit_threshold_as_before(self):
        self.assertEqual(float(self.threshold(dict(GANITA, guard=True, judged={"level": "cosmetic"}))), 101.0)
        self.assertEqual(float(self.threshold(GANITA, "--threshold", "80")), 80.0)


PAT = REPO / "scripts" / "patch_repair_loop_2026_11_15.py"


@unittest.skipUnless(PAT.exists(), "patch_repair_loop_2026_11_15.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        rel = "scripts/repair_text.py"
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            p = REPO / rel
            bak = sorted(p.parent.glob(p.name + ".bak_repairloop_*"))
            srcb = (bak[0] if bak else p).read_bytes()
            if b"REPAIR_LOOP_2026_11_15" in srcb:
                self.skipTest("only patched copies to replay against")
            (t / rel).parent.mkdir(parents=True, exist_ok=True)
            (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 1 file(s)", r.stdout, r.stdout + r.stderr)
            self.assertEqual(run().returncode, 0)
            self.assertEqual((t / rel).read_bytes(), p.read_bytes())
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
