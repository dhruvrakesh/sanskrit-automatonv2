# -*- coding: ascii -*-
"""SCHOLAR_REF_2026_10_18: --from-ref begins at the verse whose own reference it is (an e-text's), not at a passage
without one whose page.idx happens to read the same (page 81, passage 1 of the GRETIL Markandeya, for MarkP_81.1 on
page 627); the page.idx fallback stays for a reading without references; --rejudge reads again the verses whose judge
did not answer (the flash judge's "ResourceExhausted"), whoever the judge was; the patcher. Temp files only; nothing is
called (a stub judge)."""
import argparse, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_rejudge_2026_10_15 as TJ        # noqa: E402  (its fixture and stub judge)
import test_redeem_2026_10_14 as TR         # noqa: E402  (a Devanagari verse)

ST = TJ.ST
MARK = b"SCHOLAR_REF_2026_10_18"
APPLIED = MARK in (SCRIPTS / "scholar_translate.py").read_bytes()


def p(pid, page, idx, ref, engine="etext:gretil"):
    return {"id": pid, "page": page, "idx": idx, "text": TR.DEV + " \u0964\u0964", "iast": "", "english": "",
            "ref": ref, "chapter": "", "type": "mula", "quality": 0.95, "engine": engine}


def a(from_ref, limit=2):
    return argparse.Namespace(pages=None, from_ref=from_ref, only_page=None, only_idx=None, min_quality=0.35,
                              redo=False, limit=limit)


@unittest.skipUnless(APPLIED, "SCHOLAR_REF_2026_10_18 is not applied here")
class TheStart(unittest.TestCase):
    def test_an_e_texts_own_reference_comes_first(self):
        allp = [p(1, 81, 1, None), p(2, 81, 2, "19.1"), p(3, 627, 1, "81.1"), p(4, 627, 2, "81.2")]
        picked, _left, _skipped = ST.choose(a("81.1"), allp, {})
        self.assertEqual([allp[i]["id"] for i in picked], [3, 4], "MarkP_81.1 on page 627, not page 81 passage 1")
        self.assertEqual(ST.own_ref(allp[0]), "")
        self.assertEqual(ST.ref_of(allp[0]), "81.1", "ref_of's fallback is as it was")

    def test_a_reading_without_references_keeps_page_idx(self):
        allp = [p(1, 2, 2, "4", engine="tesseract"), p(2, 2, 3, "5", engine="tesseract"), p(3, 2, 4, None, "tesseract")]
        picked, _l, _s = ST.choose(a("2.3"), allp, {})
        self.assertEqual([allp[i]["id"] for i in picked], [2, 3])
        picked, _l, _s = ST.choose(a("9.9"), allp, {})
        self.assertEqual(picked, [], "not found: nothing")


@unittest.skipUnless(APPLIED, "SCHOLAR_REF_2026_10_18 is not applied here")
class TheUnanswered(unittest.TestCase):
    setUp = TJ.TheRejudge.setUp
    tearDown = TJ.TheRejudge.tearDown
    row = TJ.TheRejudge.row
    args = TJ.TheRejudge.args

    def unscore(self, i, english=None):
        sql = "UPDATE scholar_translations SET fidelity = NULL, fluency = NULL, status = 'flagged', judge_reason = ?"
        args = ["[judge failed: ResourceExhausted]"]
        if english is not None:
            sql += ", translation = ?"
            args.append(english)
        self.con.execute(sql + " WHERE passage_id = ?", args + [self.allp[i]["id"]])
        self.con.commit()

    def test_a_verse_no_judge_answered_is_read_again(self):
        for i in (0, 3, 5):
            self.row(i, judge=ST.JUDGE)
        self.unscore(0)
        self.unscore(5, english="")
        u = ST.rejudge_targets(self.con, self.args(), self.allp)
        self.assertEqual([[r["verse_ref"] for r in x] for x in u], [[self.allp[0]["ref"]]],
                         "the unanswered verse; not the one Gemini scored, nor one without English")
        recs = ST.rejudge_unit(TJ.StubJudge(self.args(), answers=[(5, 5), (5, 5)]), u[0], self.byid)
        self.assertEqual((recs[0]["status"], recs[0]["fidelity"], recs[0]["judge_engine"]), ("passed", 5, ST.JUDGE))
        self.assertTrue(recs[0]["judge_reason"].startswith("[re-judged; was %s None/None, flagged]" % ST.JUDGE),
                        recs[0]["judge_reason"])


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("scholar_translate.py.bak_scholarref_*"))
        if not baks:
            self.skipTest("no .bak_scholarref_ copy here")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_ref_2026_10_18.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            f = t / "scripts" / "scholar_translate.py"
            shutil.copy2(baks[0], f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(f.read_bytes(), (SCRIPTS / "scholar_translate.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], f)
            f.write_bytes(f.read_bytes().replace(b"    started = not a.from_ref\n", b"    started = a.from_ref is None\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("scholar_translate.py: anchor 3 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, f.read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_scholar_ref_2026_10_18.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)
        if APPLIED:
            self.assertTrue(all(x < 128 for x in (SCRIPTS / "scholar_translate.py").read_bytes()))


if __name__ == "__main__":
    unittest.main()
