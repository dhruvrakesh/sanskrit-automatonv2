# -*- coding: ascii -*-
"""ETEXT_PAGE_2026_10_18: etext_witness.py's ALSO line names a page that exists (the first the witness reads, else the
first it offers, else the scan's first), not the placeholder "--page N" that was run as it stood on 18 Oct; with no
scan to compare, no such line; the line it prints runs; the patcher. Temp files only, never data/context.db, never the
network."""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_etext_witness_2026_10_11 as TE   # noqa: E402  (its fixture: a scan of 20 pages and its e-text)

ew = TE.ew
MARK = b"ETEXT_PAGE_2026_10_18"
APPLIED = MARK in (SCRIPTS / "etext_witness.py").read_bytes()
ALSO_PAGE = re.compile(r"^ALSO: (python scripts\\etext_witness\.py .*) --page (\d+)   \(", re.M)


@unittest.skipUnless(APPLIED, "ETEXT_PAGE_2026_10_18 is not applied here")
class ThePage(unittest.TestCase):
    def test_the_first_page_the_witness_reads(self):
        m = {"pages": {3: {"status": "weak"}, 7: {"status": "match"}, 5: {"status": "match"}}, "offers": []}
        self.assertEqual(ew.page_example(m), [5])
        self.assertEqual(ew.also_page("q", m, "why"), ["q --page 5   (why)"])

    def test_else_an_offered_page_else_the_first(self):
        m = {"pages": {3: {"status": "weak"}, 9: {"status": "missing"}},
             "offers": [{"page": 9, "text": "a verse"}, {"page": 4, "text": ""}]}
        self.assertEqual(ew.page_example(m), [9], "an offer with text")
        m["offers"] = []
        self.assertEqual(ew.page_example(m), [3], "the scan's first page")

    def test_no_scan_no_line(self):
        for m in (None, {}, {"pages": {}, "offers": []}):
            self.assertEqual(ew.page_example(m), [], m)
            self.assertEqual(ew.also_page("q", m, "why"), [], m)

    def test_the_placeholder_is_gone(self):
        src = (SCRIPTS / "etext_witness.py").read_text(encoding="ascii")
        self.assertNotIn(" --page N   (", src, "no line prints the placeholder (its docstring names it)")


@unittest.skipUnless(APPLIED, "ETEXT_PAGE_2026_10_18 is not applied here")
class TheLineRuns(unittest.TestCase):
    setUp = TE.Tool.setUp
    tearDown = TE.Tool.tearDown
    tool = TE.Tool.tool

    def test_the_preview_and_the_write_name_a_page_that_runs(self):
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src))
        self.assertEqual(rc, 0, out)
        self.assertNotIn("--page N", out)
        hit = ALSO_PAGE.search(out)
        self.assertIsNotNone(hit, out)
        rc2, out2 = self.tool("--doc", "Scan", "--file", str(self.src), "--page", hit.group(2))
        self.assertEqual(rc2, 0, out2)
        self.assertIn("page %s of Scan, as the witness reads it" % hit.group(2), out2)
        self.assertIn("page %s: the witness reads it" % hit.group(2), out2, "the first page it reads")
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src), "--write")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("--page N", out)
        self.assertIsNotNone(ALSO_PAGE.search(out), out)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "tests/test_quality_2026_10_11.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextpage_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextpage_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_etext_page_2026_10_18.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "etext_witness.py"
            p.write_bytes(p.read_bytes().replace(b"def show_page(m: dict, verses: list, page: int):",
                                                 b"def show_page(m, verses, page):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 1 found 0 times", r.stdout)
            self.assertNotIn(MARK, (t / "tests" / "test_quality_2026_10_11.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_etext_page_2026_10_18.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)
        if APPLIED:
            self.assertTrue(all(x < 128 for x in (SCRIPTS / "etext_witness.py").read_bytes()))


if __name__ == "__main__":
    unittest.main()
