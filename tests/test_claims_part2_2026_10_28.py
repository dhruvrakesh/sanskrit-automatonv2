# -*- coding: ascii -*-
"""CLAIMS_PART2_2026_10_28: scholar_claims.py knows Raychaudhuri's Part II (pdf 113-328, pp. 95-310) and the Appendix
(pdf 329-332), as the scan's pages show them; the plan of --part 2 sends nothing and prices the pages at the rate
measured on Part I ($0.009 a page). Made-up pages in a temp folder; the model is never called."""
import contextlib, io, os, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
SC = SCRIPTS / "scholar_claims.py"
PAT = SCRIPTS / "patch_claims_part2_2026_10_28.py"
MARK = "CLAIMS_PART2_2026_10_28"
ON = SC.exists() and MARK.encode() in SC.read_bytes()


@unittest.skipUnless(ON, "CLAIMS_PART2_2026_10_28 is not applied to scripts/scholar_claims.py here")
class TheParts(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C, self.W = C, C.WORKS["phai1923"]

    def test_the_parts(self):
        P = self.W["parts"]
        self.assertEqual(P["1"][:2], (14, 112), "Part I as it was")
        self.assertEqual(P["2"][:2], (113, 328))
        self.assertEqual(P["app"][:2], (329, 332))
        self.assertIn("Extinction of the Gupta Dynasty", P["2"][2])
        spans = sorted(v[:2] for v in P.values())
        self.assertTrue(all(a[1] < b[0] for a, b in zip(spans, spans[1:])), "the parts do not overlap")
        self.assertEqual([self.C.printed_of(self.W, n) for n in (113, 328, 329, 332)], ["95", "310", "311", "314"])
        self.assertEqual(self.C.PER_PAGE, 0.009)

    def test_the_plan_of_part_2_sends_nothing(self):
        tmp = Path(tempfile.mkdtemp(prefix="part2_"))
        try:
            cdb, db = str(tmp / "claims.db"), str(tmp / "context.db")
            sqlite3.connect(db).close()
            con = self.C.open_store(cdb)
            self.C.store_pages(con, "phai1923", self.W, [(n, "page %d of the made-up book" % n) for n in
                                                         range(110, 335)], "made-up")
            con.close()
            calls = []
            buf, cwd = io.StringIO(), os.getcwd()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = self.C.main(["--claims-db", cdb, "--db", db, "--part", "2"],
                                     caller=lambda *a: calls.append(a))
            finally:
                os.chdir(cwd)
            out = buf.getvalue()
            self.assertEqual(rc, 0, out)
            self.assertEqual(calls, [], "the plan sends nothing")
            self.assertIn("pages asked: 216 (printed 95 to 310)", out)
            self.assertIn("about $1.94", out)
            self.assertIn("NEXT: python scripts\\scholar_claims.py --part 2 --yes", out)
            with contextlib.redirect_stdout(io.StringIO()) as b2:
                rc = self.C.main(["--claims-db", cdb, "--db", db, "--part", "9"], caller=lambda *a: calls.append(a))
            os.chdir(cwd)
            self.assertEqual(rc, 2)
            self.assertIn("the parts defined: 1, 2, app", b2.getvalue())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    def test_the_patcher_writes_once(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        files = ("scripts/scholar_claims.py", "tests/test_claims_link_2026_10_21.py")
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimspart2_*")) for f in files}
        if not all(baks.values()):
            self.skipTest("no backups of the files before the patch here")
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in files:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                (t / f).write_bytes(baks[f][0].read_bytes())
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in files:
                self.assertIn(MARK.encode(), (t / f).read_bytes(), f)
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r.stdout)


if __name__ == "__main__":
    unittest.main()
