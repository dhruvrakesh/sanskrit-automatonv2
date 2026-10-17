# -*- coding: ascii -*-
"""JUDGE_SCREEN_2026_10_17: judge-v1 by a Claude model (scripts/judge_sample.py --engine anthropic:...), metered on the
Claude credit and stopped by it; the screen's filters (--skip-judged, --clean-only, --only-ids) and its cap
(--max-usd); a calibration beside another judge's verdicts (--calibrate), which writes its files and nothing in
mt_reviews, and a third judge's sides; retranslate_marked.py with Claude's engines (the judge, the prices, the credit,
the spend cap left alone when nothing bills Google, the dry run's NEXT); the patcher. Temp files only; the model and
its SDK are stand-ins; nothing is called."""
import argparse, io, json, os, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_redeem_2026_10_14 as TR         # noqa: E402  (its fixture: corpus(), review(), load())

MARK = b"JUDGE_SCREEN_2026_10_17"
APPLIED = MARK in (SCRIPTS / "judge_sample.py").read_bytes() and MARK in (SCRIPTS / "retranslate_marked.py").read_bytes()
HAIKU, OPUS, SONNET = "anthropic:claude-haiku-5-5", "anthropic:claude-opus-5-5", "anthropic:claude-sonnet-5-5"
FLASH = "gemini:gemini-2.5-flash"


def answer(fid, flu=4, why="r"):
    return types.SimpleNamespace(text=json.dumps({"reason": why, "fidelity": fid, "fluency": flu}),
                                 candidates=[types.SimpleNamespace(finish_reason="end_turn")])


class FakeJudge:
    """A stand-in for judge_sample.ClaudeJudge: it marks (fidelity 2) the English that ends with one of MARKS."""
    credit_metered = True
    credit = True
    cost = 0.001
    MARKS = ("english 3", "english 9")
    made = []

    def __init__(self, engine, lang_name="English", con=None, sdk=None):
        self.engine, self.con, self.doc, self.spent, self.docs = engine, con, "", 0.0, []
        self.ce = types.SimpleNamespace(budget_ok=lambda con, c: FakeJudge.credit)
        FakeJudge.made.append(self)

    def generate_content(self, prompt):
        self.spent += FakeJudge.cost
        self.docs.append(self.doc)
        return answer(2 if prompt.endswith(FakeJudge.MARKS) else 4)


@unittest.skipUnless(APPLIED, "JUDGE_SCREEN_2026_10_17 is not applied here")
class TheScreen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.fx = TR.corpus(self.td / "fx")
        self.JS = TR.load("judge_sample", SCRIPTS / "judge_sample.py")
        self.saved = (self.JS.ClaudeJudge, sys.modules.get("usage_meter"), FakeJudge.credit, FakeJudge.cost)
        self.JS.ClaudeJudge = FakeJudge
        FakeJudge.made = []
        self.metered = []
        um = types.ModuleType("usage_meter")
        um.budget_ok = lambda db, next_cost=0.0: True
        um.meter = lambda **kw: (self.metered.append(kw) or 0.0)
        sys.modules["usage_meter"] = um

    def tearDown(self):
        self.JS.ClaudeJudge, um, FakeJudge.credit, FakeJudge.cost = self.saved
        if um is not None:
            sys.modules["usage_meter"] = um
        else:
            sys.modules.pop("usage_meter", None)
        self.tmp.cleanup()

    def main(self, *argv):
        buf, old = io.StringIO(), sys.argv
        sys.argv = ["judge_sample.py", "--db", str(self.fx["db"]), "--sleep", "0"] + list(argv)
        try:
            with redirect_stdout(buf):
                try:
                    self.JS.main()
                except SystemExit:
                    pass
        finally:
            sys.argv = old
        return buf.getvalue()

    def reviews(self, where=""):
        con = sqlite3.connect(str(self.fx["db"]))
        try:
            return con.execute("SELECT m.passage_id, m.engine, m.score_fidelity FROM mt_reviews m JOIN passages p ON "
                               "p.id = m.passage_id JOIN docs d ON d.id = p.doc_id %s ORDER BY m.id" % where).fetchall()
        finally:
            con.close()

    def test_the_dry_run_leaves_out_and_prices(self):
        before = self.reviews()
        out = self.main("--doc", "Judged", "--sample-pct", "100", "--limit", "100", "--skip-judged", "--engine", HAIKU)
        self.assertIn("sample=29 verses", out, out)
        self.assertIn("left out: 11 (a verdict (judge-v1) newer than its English: --skip-judged)", out)
        self.assertIn("$0.00025 a verdict (JUDGE_SCREEN_2026_10_17", out)
        self.assertIn("the Claude credit", out)
        self.assertIn("Nothing was called or written.", out)
        self.assertEqual(self.reviews(), before)
        self.assertEqual(FakeJudge.made, [], "no judge is built for a dry run")

    def test_a_claude_screen_writes_its_verdicts(self):
        out = self.main("--doc", "Mixed", "--sample-pct", "100", "--clean-only", "--engine", HAIKU, "--yes")
        self.assertIn("left out: 11 (its Sanskrit carries OCR debris: the source first (--clean-only))", out)
        got = self.reviews("WHERE d.code = 'Mixed'")
        self.assertEqual(len(got), 10, out)
        self.assertEqual({e for _p, e, _f in got}, {HAIKU})
        self.assertEqual(FakeJudge.made[0].docs, ["Mixed"] * 10, "each verdict metered under its text")
        self.assertEqual(self.metered, [], "a Claude judge meters itself, on the credit")
        self.assertIn("MEASURED spend this run: $0.0100", out)

    def test_it_stops_at_its_cap_and_the_credit(self):
        FakeJudge.cost = 0.01
        out = self.main("--doc", "Judged", "--sample-pct", "100", "--engine", HAIKU, "--yes", "--max-usd", "0.025")
        self.assertIn("graded=3 ", out)
        self.assertIn("STOPPED: this run's --max-usd", out)
        FakeJudge.credit = False
        out = self.main("--doc", "Clean", "--sample-pct", "100", "--engine", HAIKU, "--yes")
        self.assertIn("STOPPED: the Claude credit is spent or expired", out)
        self.assertEqual(self.reviews("WHERE d.code = 'Clean'"), [])

    def test_the_calibration_and_a_third_judge(self):
        before = self.reviews()
        out_dir = self.td / "screen"
        out = self.main("--all", "--calibrate", "--engine", HAIKU, "--yes", "--out-dir", str(out_dir))
        self.assertEqual(self.reviews(), before, "nothing in mt_reviews")
        self.assertIn("CALIBRATION (judge-v1): anthropic:claude-haiku-5-5 beside gemini:gemini-2.5-flash on 11 passage(s)", out)
        self.assertIn("by both 1; by the other only 1; by this one only 1; by neither 8", out)
        self.assertIn("of the other's 2 mark(s), this one finds 1 (50%)", out)
        rows = [json.loads(x) for x in (out_dir / "calibrate_claude-haiku-5-5.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 11)
        dis = out_dir / "calibrate_claude-haiku-5-5_disagree.jsonl"
        d = [json.loads(x) for x in dis.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(r["english"] for r in d), ["english 3", "english 8"])
        self.assertEqual(len(list(out_dir.glob("calibrate_claude-haiku-5-5_2*.jsonl"))), 1, "a dated copy")
        out = self.main("--all", "--calibrate", "--engine", OPUS, "--yes", "--out-dir", str(out_dir), "--only-ids", str(dis))
        self.assertIn("on 2 passage(s)", out)
        self.assertIn("where gemini:gemini-2.5-flash and anthropic:claude-haiku-5-5 disagree (2): this one sides with "
                      "gemini:gemini-2.5-flash in 0, with anthropic:claude-haiku-5-5 in 2", out)
        self.assertEqual(self.reviews(), before)

    def test_nothing_to_calibrate_on(self):
        out = self.main("--doc", "Clean", "--calibrate", "--engine", HAIKU)
        self.assertIn("REFUSE: nothing to calibrate on", out)

    def test_the_price_is_measured(self):
        con = sqlite3.connect(str(self.fx["db"]))
        for _k in range(20):
            con.execute("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd) VALUES('2026-10-16T10:00:00Z', 'judge', 'x', ?, "
                        "0.003)", (FLASH,))
        con.commit()
        self.assertAlmostEqual(self.JS.judge_price(con, FLASH), 0.003)
        self.assertEqual(self.JS.judge_price(con, HAIKU + "@low"), 0.00025)
        self.assertEqual(self.JS.judge_price(con, "anthropic:claude-x"), 0.047, "the dearest for one not there")
        con.close()


@unittest.skipUnless(APPLIED, "JUDGE_SCREEN_2026_10_17 is not applied here")
class TheClaudeJudge(unittest.TestCase):
    """judge_sample.ClaudeJudge itself, with a stand-in for the SDK: its prompt, the second ask, the meter."""

    def test_it_reads_as_judge_v1_and_meters(self):
        JS = TR.load("judge_sample", SCRIPTS / "judge_sample.py")
        asked = []

        class Stream:
            def __init__(self, kw):
                self.kw = kw

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get_final_message(self):
                asked.append(self.kw)
                cut = len(asked) == 1
                txt = '{"reason":"cut' if cut else '{"reason":"fine","fidelity":4,"fluency":5}'
                return types.SimpleNamespace(content=[{"type": "text", "text": txt}],
                                             stop_reason="max_tokens" if cut else "end_turn",
                                             usage={"input_tokens": 600, "output_tokens": 300})

        sdk = types.SimpleNamespace(Anthropic=lambda max_retries, timeout: types.SimpleNamespace(
            messages=types.SimpleNamespace(stream=lambda **kw: Stream(kw))))
        old = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "stand-in-not-a-key"
        with tempfile.TemporaryDirectory() as td:
            con = sqlite3.connect(str(Path(td) / "u.db"))
            try:
                j = JS.ClaudeJudge(HAIKU, "English", con, sdk=sdk)
                j.doc = "T"
                got = JS._judge_one(j, "English", "SRC", "iast", "the English")
                rows = con.execute("SELECT kind, doc, engine, cost_usd FROM usage_log ORDER BY id").fetchall()
            finally:
                con.close()
                if old is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = old
        self.assertEqual(got, (4, 5, "fine"))
        self.assertEqual([k["max_tokens"] for k in asked], [4000, 8000], "asked again with twice the room")
        self.assertEqual(asked[0]["system"], JS._SYS.format(lang_name="English"))
        self.assertIn("ENGLISH TRANSLATION:\nthe English", asked[0]["messages"][0]["content"])
        self.assertEqual([(k, d, e) for k, d, e, _c in rows], [("judge", "T", HAIKU)] * 2)
        self.assertAlmostEqual(j.spent, 2 * (600 * 0.10 + 300 * 0.50) / 1e6)


@unittest.skipUnless(APPLIED, "JUDGE_SCREEN_2026_10_17 is not applied here")
class TheRetranslation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = TR.corpus(Path(self.tmp.name) / "fx")
        self.JS = TR.load("judge_sample", SCRIPTS / "judge_sample.py")
        self.RM = TR.load("retranslate_marked_screen", SCRIPTS / "retranslate_marked.py")
        self.saved = (self.JS.ClaudeJudge, sys.modules.get("usage_meter"), FakeJudge.credit)
        self.JS.ClaudeJudge = FakeJudge
        self.metered, self.budget = [], False
        um = types.ModuleType("usage_meter")
        um.budget_ok = lambda db, next_cost=0.0: self.budget
        um.meter = lambda **kw: (self.metered.append(kw) or 0.0)
        sys.modules["usage_meter"] = um
        self.RM.busy_with = lambda doc: []

    def tearDown(self):
        self.JS.ClaudeJudge, um, FakeJudge.credit = self.saved
        if um is not None:
            sys.modules["usage_meter"] = um
        else:
            sys.modules.pop("usage_meter", None)
        self.tmp.cleanup()

    def a(self, **kw):
        a = argparse.Namespace(db=str(self.fx["db"]), only="Judged", engine=SONNET, judge_engine=HAIKU, no_hindi=True,
                               max_usd=1.0, log_dir=str(Path(self.tmp.name) / "logs"), max_fidelity=2, limit=200)
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def test_the_claude_judge_replaces_the_verdict_and_meters_itself(self):
        m = self.RM.judge_model(HAIKU)
        self.assertIsInstance(m, FakeJudge)
        con = self.RM.open_ro(str(self.fx["db"]))
        try:
            todo, _left = self.RM.marked(con, "Judged", 2, set())
        finally:
            con.close()
        x = todo[0]
        con = sqlite3.connect(str(self.fx["db"]))
        try:
            got = self.RM.judge_one(self.a(), m, x, "new english", con)
            rows = con.execute("SELECT engine, score_fidelity FROM mt_reviews WHERE passage_id = ?", (x["id"],)).fetchall()
        finally:
            con.close()
        self.assertEqual(got[0], 4)
        self.assertEqual(rows, [(HAIKU, 4)], "the verdict replaced, under its judge")
        self.assertEqual((m.doc, self.metered), ("Judged", []), "metered on the credit, not by usage_meter")

    def test_the_prices(self):
        con = sqlite3.connect(str(self.fx["db"]))
        try:
            pro, judge = self.RM.claude_prices(con, SONNET, HAIKU, 0.00099, 0.00025)
            self.assertAlmostEqual(pro, (1584 * 2.0 + 202 * 10.0) / 1e6)
            self.assertEqual(judge, 0.00025)
            for _k in range(20):
                con.execute("INSERT INTO usage_log(ts, kind, doc, engine, cost_usd) VALUES('2026-10-17T10:00:00Z', "
                            "'translation', 'x', ?, 0.006)", (SONNET,))
            self.assertAlmostEqual(self.RM.claude_prices(con, SONNET, FLASH, 0.00099, 0.00025)[0], 0.006)
            self.assertEqual(self.RM.claude_prices(con, self.RM.ENGINE, self.RM.JUDGE, 0.00099, 0.0003), (0.00099, 0.0003),
                             "Gemini's as they were")
        finally:
            con.close()

    def test_the_gates(self):
        con = self.RM.open_ro(str(self.fx["db"]))
        try:
            todo, _left = self.RM.marked(con, "Judged", 2, set())
        finally:
            con.close()
        calls = []

        def tr(a, x, lang):
            calls.append((x["where"], lang))
            c = sqlite3.connect(a.db)
            c.execute("UPDATE passages SET translation = ?, translated_at = '2026-10-17T10:00:00+00:00' WHERE id = ?",
                      ("new %s" % x["where"], x["id"]))
            c.commit(); c.close()
            return 0
        judge = lambda a, model, x, english, con: (4, 4, "faithful")
        saved = self.RM.credit_ok
        try:
            self.RM.credit_ok = lambda con, c: True
            out = self.RM.run(self.a(), todo, 0.0052, 0.00025, translate=tr, judge=judge, model=object())
            self.assertEqual((len(out["mended"]), out["stopped"]), (len(todo), ""), "the spend cap is not asked: nothing bills Google")
            calls.clear()
            out = self.RM.run(self.a(no_hindi=False), todo, 0.0052, 0.00025, translate=tr, judge=judge, model=object())
            self.assertIn("the spend cap is reached", out["stopped"], "the Hindi bills Google")
            self.RM.credit_ok = lambda con, c: False
            self.budget = True
            out = self.RM.run(self.a(), todo, 0.0052, 0.00025, translate=tr, judge=judge, model=object())
            self.assertEqual(calls, [])
            self.assertIn("the Claude credit is spent or expired", out["stopped"])
        finally:
            self.RM.credit_ok = saved

    def test_the_dry_run_carries_its_options(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "retranslate_marked.py"), "--db", str(self.fx["db"]), "--verdicts",
                            str(self.fx["verdicts"]), "--engine", SONNET, "--judge-engine", HAIKU, "--no-hindi"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DRY RUN (nothing called, nothing written)", r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "NEXT: python scripts\\retranslate_marked.py --engine "
                         "anthropic:claude-sonnet-5-5 --judge-engine anthropic:claude-haiku-5-5 --no-hindi --yes --max-usd 0.10")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/judge_sample.py", "scripts/retranslate_marked.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_judgescreen_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_judgescreen_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_judge_screen_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
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
            p = t / "scripts" / "retranslate_marked.py"
            p.write_bytes(p.read_bytes().replace(b"def spent_since(db: str, doc: str, mark: int) -> float:",
                                                 b"def spent_since(db, doc, mark):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("retranslate_marked.py: anchor 4 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_judge_screen_2026_10_17.py", Path(__file__)):
            if not p.exists():
                self.skipTest("the patcher is not here")
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)
        if APPLIED:
            self.assertTrue(all(x < 128 for x in (SCRIPTS / "retranslate_marked.py").read_bytes()))


if __name__ == "__main__":
    unittest.main()
