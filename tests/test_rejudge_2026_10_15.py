# -*- coding: ascii -*-
"""REJUDGE_2026_10_15 (CF2): --rejudge: the Gemini judge reads again the verses of a Claude run that a Claude judge
read; their status is decided again as a run decides it; a new version of each, the same English. Temp files only;
nothing is called (a stub judge; the CLI runs are dry runs)."""
import argparse, io, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "rejudge_main")
SONNET, HAIKU, OPUS = "anthropic:claude-sonnet-5-5", "anthropic:claude-haiku-5-5", "anthropic:claude-opus-5-5"
ACC = {"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept"}
MAJ = {"fidelity": 2, "completeness": 5, "verdict": "revise", "by": OPUS,
       "issues": [{"type": "misreading", "where": "w", "fix": "f", "severity": "major"}]}


class StubJudge:
    """Gemini, as --rejudge uses it: the judge only. answers: (fidelity, fluency) in turn; None: no answer."""
    made = []

    def __init__(self, a, meta=None, con=None, answers=None, on_judge=None):
        self.a, self.con, self.spent, self.calls = a, con, 0.0, []
        self.answers = list(answers if answers is not None else StubJudge.script)
        self.on_judge = on_judge or StubJudge.hook
        StubJudge.made.append(self)

    script, hook = [], None

    def judge(self, src, iast, english):
        self.calls.append(english)
        if self.on_judge:
            self.on_judge(self)
        a = self.answers.pop(0) if self.answers else (5, 5)
        if a is None:
            return None, None, "[judge failed: X]", 0.0
        self.spent += 0.0002
        return a[0], a[1], "fine", 0.0002


@unittest.skipUnless(APPLIED, "REJUDGE_2026_10_15 is not applied here")
class TheRejudge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        import db_utils
        self.con = db_utils.connect(str(self.db))
        ST.ensure_schema(self.con)
        self.allp = ST.load_text(self.con, "MBh01")
        self.byid = {x["id"]: x for x in self.allp}
        self.gem, self.keep_hook, self.keep_script = ST.Gemini, StubJudge.hook, StubJudge.script
        StubJudge.made, StubJudge.hook, StubJudge.script = [], None, []

    def tearDown(self):
        ST.Gemini, StubJudge.hook, StubJudge.script = self.gem, self.keep_hook, self.keep_script
        self.con.close()
        self.tmp.cleanup()

    def row(self, i, judge=HAIKU, status="passed", crit=None, group=None, at="2026-10-15T13:20:00+00:00", h=None,
            engine=SONNET, cmp_=None):
        x = self.allp[i]
        r = {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"], "verse_ref": x["ref"],
             "src_hash": h or ST.src_hash(x["text"]), "translation": "E%d //" % i, "notes": "[]", "doubts": "",
             "draft": "D", "critique": json.dumps(crit if crit is not None else [ACC]), "passes": 1, "fidelity": 4,
             "fluency": 4, "judge_reason": "r", "working_fidelity": 4 if x.get("english") else None,
             "working_fluency": 4 if x.get("english") else None, "status": status, "engine": engine,
             "judge_engine": judge, "prompt_version": "scholar-v2.1+scholar-critic-v2+agama-1", "cost_usd": 0.04,
             "created_at": at, "group_ref": group, "group_translation": "G //" if group else None, "moved": None,
             "compare": json.dumps(cmp_) if cmp_ else None, "compare_better": None}
        ST.store(self.con, r)
        return r

    def args(self, **kw):
        return argparse.Namespace(**dict({"doc": "MBh01", "engine": SONNET, "judge_engine": ST.JUDGE, "pages": None,
                                          "limit": 100, "db": str(self.db), "yes": True}, **kw))

    def fill(self):
        self.row(0, judge=ST.JUDGE, at="2026-10-15T12:00:00+00:00")   # an older version, judged by Gemini
        self.row(0)                                                    # the latest: a Claude judge's
        self.row(1, group="1.1.7-1.1.8"); self.row(2, group="1.1.7-1.1.8")
        self.row(3, judge=ST.JUDGE)                                    # Gemini's: not read again
        self.row(4)
        self.con.execute("UPDATE scholar_translations SET review_verdict = 'accept', reviewed_by = 'Dhruv' "
                         "WHERE passage_id = ?", (self.allp[4]["id"],))   # a person read it: it stands
        self.con.commit()
        self.row(5, h="0" * 16)                                        # stale: its Sanskrit changed
        self.row(6, engine=OPUS)                                       # another run
        self.row(6)

    def test_what_is_read_again(self):
        self.fill()
        u = ST.rejudge_targets(self.con, self.args(), self.allp)
        self.assertEqual([[r["verse_ref"] for r in x] for x in u], [["1.1.6"], ["1.1.7", "1.1.8"], ["1.1.11"]])
        self.assertEqual(ST.rejudge_targets(self.con, self.args(pages="2"), self.allp), [])
        self.assertEqual([[r["verse_ref"] for r in x] for x in ST.rejudge_targets(self.con, self.args(engine=OPUS),
                                                                                  self.allp)], [["1.1.11"]],
                         "each run its own rows")

    def test_one_sentence_read_again(self):
        self.fill()
        u = ST.rejudge_targets(self.con, self.args(), self.allp)
        j = StubJudge(self.args(), answers=[(5, 5), (4, 5)])
        recs = ST.rejudge_unit(j, u[0], self.byid)
        self.assertEqual(j.calls, ["E0 //", self.allp[0]["english"]], "the scholarly, then the working English")
        r = recs[0]
        self.assertEqual((r["status"], r["fidelity"], r["fluency"], r["working_fidelity"], r["working_fluency"],
                          r["judge_engine"]), ("passed", 5, 5, 4, 5, ST.JUDGE))
        self.assertTrue(r["judge_reason"].startswith("[re-judged; was %s 4/4, passed] fine" % HAIKU), r["judge_reason"])
        self.assertEqual((r["translation"], r["critique"], r["engine"]), ("E0 //", json.dumps([ACC]), SONNET))
        self.assertAlmostEqual(r["cost_usd"], 0.0004)
        g = ST.rejudge_unit(StubJudge(self.args(), answers=[(2, 5), (5, 5)]), u[1], self.byid)
        self.assertEqual([x["status"] for x in g], ["flagged", "flagged"], "a sentence whole")
        self.assertEqual(len({x["created_at"] for x in g}), 1)
        self.assertEqual(StubJudge.made[-1].calls[0], "G //", "the sentence's English, whole")
        self.assertEqual(ST.rejudge_unit(StubJudge(self.args(), answers=[None]), u[0], self.byid), [],
                         "no answer: nothing to store")

    def test_its_status_as_a_run_decides_it(self):
        self.row(0, crit=[ACC, MAJ], status="flagged")
        self.row(1, cmp_={"scholarly": {"fidelity": 3, "errors": [{"severity": "major", "what": "m"}]},
                          "working": {"fidelity": 5, "errors": []}, "better": "working"})
        u = ST.rejudge_targets(self.con, self.args(), self.allp)
        self.assertEqual(ST.rejudge_unit(StubJudge(self.args()), u[0], self.byid)[0]["status"], "flagged",
                         "the audit's reading stands")
        self.assertEqual(ST.rejudge_unit(StubJudge(self.args()), u[1], self.byid)[0]["status"], "flagged",
                         "the second judge's major error stands")

    def run_main(self, *extra, budget=True):
        import usage_meter
        keep = usage_meter.budget_ok
        usage_meter.budget_ok = lambda con, need=0.0: budget
        ST.Gemini = StubJudge
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                rc = ST.main(["--db", str(self.db), "--doc", "MBh01", "--engine", SONNET, "--rejudge", "--limit", "50"]
                             + list(extra))
        finally:
            usage_meter.budget_ok = keep
        return rc, out.getvalue()

    def test_the_run_appends_and_leaves_a_redone_verse_alone(self):
        self.fill()
        before = self.con.execute("SELECT COUNT(*) FROM scholar_translations").fetchone()[0]
        p11 = self.allp[6]["id"]
        con2 = sqlite3.connect(str(self.db))

        def redo_meanwhile(j):   # a window redoes 1.1.11 while 1.1.6 is read again
            if len(j.calls) == 1 and not con2.execute("SELECT COUNT(*) FROM scholar_translations WHERE passage_id = ? "
                                                      "AND judge_reason = 'redone'", (p11,)).fetchone()[0]:
                v = con2.execute("SELECT MAX(version) FROM scholar_translations WHERE passage_id = ?", (p11,)).fetchone()[0]
                con2.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, translation, "
                             "status, engine, judge_engine, judge_reason, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (p11, "MBh01", ST.src_hash(self.allp[6]["text"]), v + 1, "NEW //", "passed", SONNET,
                              HAIKU, "redone", "2026-10-15T13:30:00+00:00"))
                con2.commit()
        StubJudge.hook = redo_meanwhile
        StubJudge.script = [(5, 5), (5, 5), (2, 4), (5, 5)]
        try:
            rc, o = self.run_main("--yes")
        finally:
            con2.close()
        self.assertEqual(rc, 0, o)
        self.assertIn("VERDICT: 2 sentence(s) read again; 1 changed status (1.1.7-1.1.8 passed->flagged); 1 redone "
                      "meanwhile, left alone; 0 not answered", o)
        after = self.con.execute("SELECT COUNT(*) FROM scholar_translations").fetchone()[0]
        self.assertEqual(after - before, 1 + 3, "the redo, and three verses read again; nothing overwritten")
        latest = ST.latest_rows(self.con, "MBh01", SONNET)
        self.assertEqual(latest[self.allp[0]["id"]]["judge_engine"], ST.JUDGE)
        self.assertEqual(latest[self.allp[0]["id"]]["translation"], "E0 //")
        self.assertEqual(latest[p11]["translation"], "NEW //", "the redo stands")
        self.assertEqual(latest[self.allp[4]["id"]]["judge_engine"], HAIKU, "the reviewed row stands")
        rc, o = self.run_main()
        self.assertIn("1 sentence(s), 1 verse(s)", o, "only the redone verse is left (its judge was Claude's)")

    def test_the_spend_cap_and_the_refusals(self):
        self.fill()
        before = self.con.execute("SELECT COUNT(*) FROM scholar_translations").fetchone()[0]
        rc, o = self.run_main("--yes", budget=False)
        self.assertIn("STOPPED: the spend cap is reached", o)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM scholar_translations").fetchone()[0], before)
        e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
        run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(self.db),
                                         "--doc", "MBh01"] + list(x), capture_output=True, text=True, encoding="utf-8",
                                        cwd=str(self.td), env=e)
        md5 = base.md5(self.db)
        r = run("--engine", SONNET, "--rejudge")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DRY RUN", r.stdout)
        self.assertIn("MBh01: 3 sentence(s), 4 verse(s); about $0.0012 (Google's bill, in the spend cap)", r.stdout)
        self.assertIn("NEXT: python scripts\\scholar_translate.py --doc MBh01 --engine %s --rejudge --limit 24 --yes"
                      % SONNET, r.stdout)
        r = run("--rejudge")
        self.assertEqual(r.returncode, 1); self.assertIn("reads the rows of a Claude run", r.stdout)
        r = run("--engine", SONNET, "--judge-engine", HAIKU, "--rejudge")
        self.assertEqual(r.returncode, 1); self.assertIn("is a Gemini judge's", r.stdout)
        r = run("--engine", SONNET, "--rejudge", "--yes")
        self.assertEqual(r.returncode, 1); self.assertIn("GEMINI_API_KEY is not set", r.stdout)
        self.assertEqual(base.md5(self.db), md5, "nothing written")


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("scholar_translate.py.bak_rejudge_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        pat = [sys.executable, str(SCRIPTS / "patch_rejudge_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            p = t / "scripts" / "scholar_translate.py"
            shutil.copy2(baks[0], p)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.read_bytes(), (SCRIPTS / "scholar_translate.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"    if a.review or a.term:\n", b"    if a.review:\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 4 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"REJUDGE_2026", p.read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry CLAUDE_FIRST_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_rejudge_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"REJUDGE_2026_10_15", b)
        if APPLIED:
            b = (SCRIPTS / "scholar_translate.py").read_bytes()
            self.assertTrue(all(x < 128 for x in b)); self.assertIn(b"REJUDGE_2026_10_15", b)


if __name__ == "__main__":
    unittest.main()
