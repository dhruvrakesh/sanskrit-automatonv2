# -*- coding: ascii -*-
"""TRIAGE_2026_10_16: the tiers of the verses not passed (rejected, source, serious, mild), --triage (a CSV for a
person; free, read-only), --only-flagged ENGINE [--serious], the tiers in --status, and the judge's price as measured.
Temp files only; nothing is called (the CLI runs are dry runs or read-only)."""
import argparse, csv, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "triage_of")
SONNET, OPUS = "anthropic:claude-sonnet-5-5", "anthropic:claude-opus-5-5"
ACC = {"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept"}
REV = {"fidelity": 4, "completeness": 4, "issues": [{"type": "style", "where": "w", "fix": "f", "severity": "minor"}],
       "verdict": "revise"}
AUD = {"fidelity": 2, "completeness": 5, "verdict": "revise", "by": "gemini:gemini-2.5-pro",
       "issues": [{"type": "misreading", "where": "w", "fix": "f", "severity": "major"}]}


def R(status="flagged", crit=(ACC,), fid=4, flu=4, cmp_=None, review=None):
    return {"status": status, "critique": json.dumps(list(crit)), "fidelity": fid, "fluency": flu,
            "compare": json.dumps(cmp_) if cmp_ else None, "review_verdict": review}


@unittest.skipUnless(APPLIED, "TRIAGE_2026_10_16 is not applied here")
class TheTiers(unittest.TestCase):
    def test_which_is_which(self):
        t = ST.triage_of
        self.assertEqual(t(R("passed", fid=5, flu=5)), ("", []))
        self.assertEqual(t(R(review="accept"))[0], "", "a person accepted it")
        self.assertEqual(t(R("passed", fid=5, flu=5, review="reject"))[0], "rejected")
        self.assertEqual(t(R("source_doubt"))[0], "source")
        self.assertEqual(t(R(crit=[None])), ("serious", ["the critic's answer was not read"]))
        self.assertEqual(t(R(crit=[ACC, AUD], fid=5, flu=5)), ("serious", ["the audit: a major misreading"]))
        self.assertEqual(t(R(fid=2, flu=5)), ("serious", ["the judge: fidelity 2"]))
        self.assertEqual(t(R(fid=None, flu=None)), ("serious", ["the judge did not answer"]))
        self.assertEqual(t(R(fid=3, flu=3)), ("mild", ["the judge: fidelity 3", "the judge: fluency 3"]))
        self.assertEqual(t(R(crit=[REV], fid=5, flu=5)), ("mild", ["the critic: revise, no major issue"]))
        cm = {"scholarly": {"fidelity": 3, "errors": [{"severity": "major", "what": "m"}]}, "working": {"errors": []},
              "better": "working"}
        self.assertEqual(t(R(fid=5, flu=5, cmp_=cm)), ("serious", ["the second judge: a major error"]))


@unittest.skipUnless(APPLIED, "TRIAGE_2026_10_16 is not applied here")
class TheTriage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        import db_utils
        self.con = db_utils.connect(str(self.db))
        ST.ensure_schema(self.con)
        self.allp = ST.load_text(self.con, "MBh01")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def row(self, i, engine=SONNET, at="2026-10-15T13:00:00+00:00", **kw):
        x = self.allp[i]
        r = {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"], "verse_ref": x["ref"],
             "src_hash": ST.src_hash(x["text"]), "translation": "E%d //" % i, "notes": "[]", "doubts": "d%d" % i,
             "critique": json.dumps([ACC]), "passes": 1, "fidelity": 5, "fluency": 5, "status": "passed",
             "engine": engine, "judge_engine": ST.JUDGE, "prompt_version": "scholar-v2.1+scholar-critic-v2",
             "cost_usd": 0.04, "created_at": at}
        r.update(kw)
        ST.store(self.con, r)
        return r

    def fill(self):
        self.row(0, status="flagged", fidelity=2)                    # serious, then a person rejects it
        self.row(1, status="flagged", fidelity=3)                    # mild
        self.row(2, status="flagged", fidelity=2)                    # serious
        self.row(3, status="source_doubt")                           # source
        self.row(6)                                                  # passed
        self.con.execute("UPDATE scholar_translations SET review_verdict = 'reject', reviewed_by = 'Dhruv' WHERE "
                         "passage_id = ?", (self.allp[0]["id"],))
        self.con.commit()

    def cli(self, *x):
        e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
        return subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(self.db), "--doc",
                               "MBh01"] + list(x), capture_output=True, text=True, encoding="utf-8", cwd=str(self.td),
                              env=e)

    def test_the_csv_for_a_person(self):
        self.fill()
        before = base.md5(self.db)
        r = self.cli("--engine", SONNET, "--triage", "--exports", str(self.td / "ex"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not passed: 4; rejected 1, source 1, serious 1, mild 1", r.stdout)
        p = self.td / "ex" / "scholar_triage_MBh01.csv"
        self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"), "a BOM, for Excel")
        rows = list(csv.reader(p.read_text(encoding="utf-8-sig").splitlines()))
        self.assertEqual(rows[0][:6], ["tier", "verse", "page", "idx", "status", "reasons"])
        self.assertEqual([x[0] for x in rows[1:]], ["rejected", "source", "serious", "mild"])
        self.assertEqual(rows[3][1], "1.1.8"); self.assertEqual(rows[3][5], "the judge: fidelity 2")
        self.assertEqual(rows[3][11], "E2 //"); self.assertEqual(rows[3][12], "d2")
        self.assertEqual(base.md5(self.db), before, "read-only")
        r = self.cli("--engine", SONNET, "--status")
        self.assertIn("    not passed: 1 serious, 1 mild, 1 source, 1 rejected by a person (--triage lists them)", r.stdout)

    def test_only_the_flagged_read_again(self):
        self.fill()
        self.row(2, engine=OPUS, at="2026-10-16T01:00:00+00:00")     # already read again by Opus, after the flag
        r = self.cli("--engine", OPUS, "--only-flagged", SONNET, "--serious")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--only-flagged: the verses %s did not pass (the rejected and the serious): 2, read again by %s "
                      "(1 of them already)" % (SONNET, OPUS), r.stdout)
        self.assertIn("chosen: 1 verse(s), 1.1.6 to 1.1.6", r.stdout)
        self.assertIn("--only-flagged %s --serious --yes --max-usd" % SONNET, r.stdout)
        r = self.cli("--engine", OPUS, "--only-flagged", SONNET)
        self.assertIn("chosen: 3 verse(s), 1.1.6 to 1.1.9", r.stdout, "every tier but the one read again")
        r = self.cli("--engine", OPUS, "--only-flagged", SONNET, "--redo")
        self.assertIn("chosen: 4 verse(s), 1.1.6 to 1.1.9", r.stdout)

    def test_choose_and_the_judge_price(self):
        a = argparse.Namespace(pages=None, from_ref=None, only_page=None, only_idx=None, limit=24, min_quality=0.35,
                               redo=False, only_ids={self.allp[1]["id"], self.allp[2]["id"]},
                               skip_ids={self.allp[2]["id"]})
        picked, left, skipped = ST.choose(a, self.allp, {})
        self.assertEqual(([self.allp[i]["ref"] for i in picked], [x["ref"] for x in skipped]), (["1.1.7"], ["1.1.8"]))
        self.assertEqual(ST.judge_price(self.con, ST.JUDGE), ST.JUDGE_COST_NOW, "nothing measured yet")
        import cost_tracker
        cost_tracker.ensure_usage_schema(self.con)
        for k in range(25):
            self.con.execute("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd, ok, token_source) VALUES "
                             "('2026-10-15T12:00:00Z', 'judge', 'D', ?, ?, 1, 'provider')", (ST.JUDGE, 0.002 + k * 0.0001))
        self.con.commit()
        self.assertAlmostEqual(ST.judge_price(self.con, ST.JUDGE), 0.0032, places=6)


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("scholar_translate.py.bak_triage_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        pat = [sys.executable, str(SCRIPTS / "patch_triage_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            p = t / "scripts" / "scholar_translate.py"
            shutil.copy2(baks[0], p)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("scholar_translate.py.bak_readyprice_*"))   # READY_PRICE_2026_10_16 came after
            self.assertEqual(p.read_bytes(), (later[0] if later else SCRIPTS / "scholar_translate.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"MARK_REJUDGE = \"REJUDGE_2026_10_15\"\n", b"MARK_REJUDGE = 'x'\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 14 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"TRIAGE_2026", p.read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry REJUDGE_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_triage_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"TRIAGE_2026_10_16", b)
        if APPLIED:
            b = (SCRIPTS / "scholar_translate.py").read_bytes()
            self.assertTrue(all(x < 128 for x in b)); self.assertIn(b"TRIAGE_2026_10_16", b)


if __name__ == "__main__":
    unittest.main()
