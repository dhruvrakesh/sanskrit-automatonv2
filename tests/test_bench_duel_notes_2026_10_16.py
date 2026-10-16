# -*- coding: ascii -*-
"""BENCH_DUEL_NOTES_2026_10_16: BM3's check with the scholarly arm's notes withheld (they name it). With --no-notes the
judges see no notes; its readings are stored apart from duel-v1's and say notes_shown; its report has its own files
and BM3's stay as they were. Temp folders only; BM1 made with the stand-ins of test_bench_mitra; nothing is called."""
import json, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "tests"))

import bench_duel as D                      # noqa: E402
import bench_mitra as B                     # noqa: E402
import test_bench_duel_2026_10_16 as TU     # noqa: E402
import test_bench_mitra_2026_10_16 as TB    # noqa: E402

MARK = b"BENCH_DUEL_NOTES_2026_10_16"
APPLIED = MARK in (SCRIPTS / "bench_duel.py").read_bytes()
NOTE = "a note of the scholarly arm"


@unittest.skipUnless(APPLIED, "BENCH_DUEL_NOTES_2026_10_16 is not applied here")
class TheCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ds = TB.dataset(self.td)
        self.main = TB.ledger(self.td)
        self.bm1, self.out = self.td / "bm1", self.td / "bm3"
        args = ["--db", str(self.main), "--data", str(self.ds), "--out", str(self.bm1), "--files", ",".join(TB.KEYS)]
        self.assertEqual(B.main(args + ["--sample"]), 0)
        child = self.td / "child.py"
        child.write_text(TB.FAKE_CHILD, encoding="utf-8")
        self.saved = (B.arm_cmd, B.FILES, D.make_judge, D.NOTES_SHOWN, D.NAME)
        B.arm_cmd = lambda arm, f, bpath, work, logs, max_usd, n: [sys.executable, str(child), arm, str(bpath), f["code"],
                                                                     str(SCRIPTS)]
        B.FILES = tuple(f for f in B.FILES if f["key"] in TB.KEYS)
        D.make_judge = lambda engine, out, meta: TU.FakeAsker(engine, out, meta)
        TU.FakeAsker.msgs = []
        for arm in B.ARMS:
            self.assertEqual(B.main(args + ["--arm", arm, "--yes"]), 0, arm)
        con = sqlite3.connect(self.bm1 / "db" / "S.db")
        con.execute("UPDATE scholar_translations SET notes = ?", (json.dumps([{"anchor": "x", "kind": "term",
                                                                                "note": NOTE}]),))
        con.commit()
        con.close()
        self.args = ["--db", str(self.main), "--bm1", str(self.bm1), "--out", str(self.out), "--units", "4",
                     "--with-reference"]

    def tearDown(self):
        B.arm_cmd, B.FILES, D.make_judge, D.NOTES_SHOWN, D.NAME = self.saved
        self.tmp.cleanup()

    def test_the_notes_withheld_and_kept_apart(self):
        self.assertEqual(D.main(self.args + ["--yes", "--max-usd", "5"]), 0)
        self.assertEqual(len(TU.FakeAsker.msgs), 8)
        self.assertTrue(all(NOTE in m for _e, m in TU.FakeAsker.msgs), "duel-v1 as it is: the notes shown")
        self.assertTrue(D.NOTES_SHOWN)
        TU.FakeAsker.msgs = []
        self.assertEqual(D.main(self.args + ["--no-notes"]), 0, "the dry run")
        self.assertEqual(TU.FakeAsker.msgs, [])
        self.assertEqual(D.main(self.args + ["--no-notes", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(len(TU.FakeAsker.msgs), 8, "the same units again: the English the judges see differs")
        self.assertFalse(any(NOTE in m for _e, m in TU.FakeAsker.msgs), "no notes shown")
        rs = D.readings(self.out)
        self.assertEqual(sorted(r.get("notes_shown") for r in rs), [False] * 8 + [True] * 8)
        TU.FakeAsker.msgs = []
        self.assertEqual(D.main(self.args + ["--no-notes", "--yes", "--max-usd", "5"]), 0)
        self.assertEqual(TU.FakeAsker.msgs, [], "not bought twice")
        self.assertEqual(D.main(["--bm1", str(self.bm1), "--out", str(self.out), "--report", "--no-notes"]), 0)
        self.assertEqual(D.main(["--bm1", str(self.bm1), "--out", str(self.out), "--report"]), 0)
        s1 = json.loads((self.out / "BM3_summary.json").read_text(encoding="utf-8"))
        s0 = json.loads((self.out / "BM3_nonotes_summary.json").read_text(encoding="utf-8"))
        self.assertEqual((s1["notes_shown"], s0["notes_shown"]), (True, False))
        self.assertEqual((s1["scopes"]["all"]["units"], s0["scopes"]["all"]["units"]), (4, 4))
        self.assertIn("the scholarly arm's notes withheld", (self.out / "BM3_nonotes_report.html").read_text(encoding="utf-8"))
        self.assertNotIn("notes withheld", (self.out / "BM3_report.html").read_text(encoding="utf-8"))
        st = D.state(self.bm1, self.out, str(self.main), [TU.GEM, TU.CLA])
        self.assertEqual(st["read"], {TU.GEM: 4, TU.CLA: 4}, "the same units: the dashboard counts units")
        self.assertTrue(st["summary"]["notes_shown"], "the dashboard reads duel-v1's report")


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("bench_duel.py.bak_duelnotes_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the file")
        pat = [sys.executable, str(SCRIPTS / "patch_bench_duel_notes_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(baks[0], t / "scripts" / "bench_duel.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((t / "scripts" / "bench_duel.py").read_bytes(), (SCRIPTS / "bench_duel.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], t / "scripts" / "bench_duel.py")
            p = t / "scripts" / "bench_duel.py"
            p.write_bytes(p.read_bytes().replace(b'    global ME\n', b'    global ME  \n'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 11 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, p.read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_bench_duel_notes_2026_10_16.py", SCRIPTS / "bench_duel.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
