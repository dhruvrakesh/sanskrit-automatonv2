# -*- coding: ascii -*-
"""CLAUDE_FIRST_2026_10_15: the checks of a Claude run by another Claude model (on the credit; never the translator's
own), a run with no Gemini engine not gated by Google's spend cap, and the engine anthropic: in infer_mt (the working
English and the Hindi on the Claude credit, never budget_state). Temp files only; nothing is called (a scripted SDK,
a stub for Gemini)."""
import argparse, importlib, io, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import test_scholar_v2_2026_10_14 as v2         # noqa: E402
import test_claude_engine_2026_10_15 as TCE     # noqa: E402
import claude_engine as CE                      # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "ClaudeCheck")
HAYA, SONNET = TCE.HAYA, TCE.SONNET
HAIKU, OPUS = "anthropic:claude-haiku-5-5", "anthropic:claude-opus-5-5"
msg = TCE.msg
DRAFT = json.dumps({"translation": "E //", "notes": [], "glossary": [], "doubts": ""})
ACCEPT = json.dumps({"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept"})
MAJOR = json.dumps({"fidelity": 2, "completeness": 5, "verdict": "revise",
                    "issues": [{"type": "misreading", "where": "w", "fix": "f", "severity": "major"}]})
JUDGED = '{"reason":"faithful","fidelity":5,"fluency":5}'


class FakeGem:
    """Gemini's half, as Checks builds it: the judge only."""
    made = []

    def __init__(self, a, meta, con):
        self.a, self.con, self.spent, self.judged = a, con, 0.0, 0
        FakeGem.made.append(a)

    def ask(self, kind, m):
        raise AssertionError("Gemini is not asked here")

    def judge(self, src, iast, english):
        self.judged += 1; self.spent += 0.0002
        return 5, 5, "ok", 0.0002


class _Env(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        os.environ["GEMINI_API_KEY"] = ""
        self.busy, self.gem, self.claude = ST.busy_with, ST.Gemini, ST.Claude
        ST.busy_with = lambda doc: []
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)

    def tearDown(self):
        ST.busy_with, ST.Gemini, ST.Claude = self.busy, self.gem, self.claude
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()
        FakeGem.made = []


@unittest.skipUnless(APPLIED, "CLAUDE_FIRST_2026_10_15 is not applied here")
class TheChecks(_Env):
    def unit(self, answers, **kw):
        d = Path(tempfile.mkdtemp(dir=str(self.td)))
        db = TCE.agama_fixture(d)
        import db_utils
        con = db_utils.connect(str(db))
        ST.ensure_schema(con)
        allp = ST.load_text(con, HAYA)
        meta = ST.doc_meta(con, HAYA, allp)
        kw.setdefault("judge_engine", HAIKU); kw.setdefault("compare_engine", OPUS)
        a = v2.args(db, doc=HAYA, engine=SONNET, groups=False, compare=False, audit_every=1, **kw)
        sdk = TCE.FakeSDK(answers)
        c = ST.Claude(a, meta, con, sdk=sdk)
        r = ST.one_unit(a, allp, [0], meta, {}, c, con, 0.01)[0]
        return con, c, sdk, r

    def test_another_claude_model_checks_it_on_the_credit(self):
        con, c, sdk, r = self.unit([msg(DRAFT), msg(ACCEPT), msg(ACCEPT), msg(JUDGED)])
        try:
            self.assertEqual([q["model"] for q in sdk.requests],
                             ["claude-sonnet-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
                             "the draft and the critic by Sonnet, the audit by Opus, the judge by Haiku")
            self.assertIn("Reply with one JSON object", sdk.requests[2]["system"], "the audit is the critic's prompt")
            self.assertIn("strict, fair Sanskrit-translation quality judge", sdk.requests[3]["system"])
            self.assertEqual((r["status"], r["fidelity"], r["fluency"]), ("passed", 5, 5))
            self.assertEqual(json.loads(r["critique"])[-1]["by"], OPUS)
            rows = con.execute("SELECT engine, kind FROM usage_log ORDER BY id").fetchall()
            self.assertEqual(rows, [(SONNET, "scholar"), (SONNET, "scholar"), (OPUS, "scholar"), (HAIKU, "judge")])
            self.assertFalse(con.execute("SELECT COUNT(*) FROM usage_log WHERE engine LIKE 'gemini%'").fetchone()[0])
            self.assertEqual(FakeGem.made, [], "no Gemini built")
            self.assertAlmostEqual(c.spent, sum(x[0] for x in con.execute("SELECT cost_usd FROM usage_log")), places=9)
            self.assertAlmostEqual(r["cost_usd"], c.spent, places=6)
        finally:
            con.close()

    def test_its_reading_decides_and_a_judge_that_fails_flags(self):
        con, c, sdk, r = self.unit([msg(DRAFT), msg(ACCEPT), msg(MAJOR), msg(JUDGED)])
        con.close()
        self.assertEqual((r["status"], r["_audit"]), ("flagged", "revise"))
        con, c, sdk, r = self.unit([msg(DRAFT), msg(ACCEPT), msg(ACCEPT), RuntimeError("overloaded")])
        con.close()
        self.assertEqual((r["status"], r["fidelity"]), ("flagged", None))
        self.assertIn("judge failed", r["judge_reason"])
        con, c, sdk, r = self.unit([msg(DRAFT), msg(ACCEPT), msg(ACCEPT), msg("no json", stop="max_tokens"),
                                    msg(JUDGED)])
        con.close()
        self.assertEqual(r["status"], "passed", "a judge cut off is asked again with room")
        self.assertEqual(sdk.requests[-1]["max_tokens"], 2 * ST.CLAUDE_JUDGE_MAX_TOKENS)

    def test_the_two_families_mixed(self):
        ST.Gemini = FakeGem
        con, c, sdk, r = self.unit([msg(DRAFT), msg(ACCEPT), msg(ACCEPT)], judge_engine=ST.JUDGE)
        try:
            self.assertEqual(len(FakeGem.made), 1)
            self.assertEqual(FakeGem.made[0].judge_engine, ST.JUDGE)
            self.assertIsInstance(c.gem.asker, ST.ClaudeCheck); self.assertIsInstance(c.gem.judger, FakeGem)
            self.assertEqual(c.gem.judger.judged, 1)
            self.assertEqual(r["status"], "passed")
            c.con = "X"; self.assertEqual((c.gem.asker.con, c.gem.judger.con), ("X", "X"))
        finally:
            con.close()

    def test_the_rules(self):
        ns = lambda **kw: argparse.Namespace(**dict({"engine": SONNET, "judge_engine": ST.JUDGE,
                                                     "compare_engine": ST.COMPARE_ENGINE}, **kw))
        self.assertFalse(ST.claude_checks(ns())); self.assertFalse(ST.no_gemini(ns()))
        self.assertTrue(ST.claude_checks(ns(compare_engine=OPUS))); self.assertFalse(ST.no_gemini(ns(compare_engine=OPUS)))
        self.assertTrue(ST.no_gemini(ns(compare_engine=OPUS, judge_engine=HAIKU)))
        self.assertEqual(ST.own_model_check(ns(judge_engine=SONNET + "@low")), SONNET + "@low")
        self.assertEqual(ST.own_model_check(ns(compare_engine=OPUS, judge_engine=HAIKU)), "")
        self.assertRaises(ValueError, ST.own_model_check, ns(judge_engine=HAIKU + "@huge"))
        self.assertEqual(ST.checks_line(ns()), "the judge %s and the second judge %s: Google's bill, in the spend cap"
                         % (ST.JUDGE, ST.COMPARE_ENGINE), "as before")
        self.assertEqual(ST.checks_line(ns(compare_engine=OPUS, judge_engine=HAIKU)),
                         "the judge %s (the Claude credit); the second judge and the audit %s (the Claude credit); no "
                         "Gemini call: Google's spend cap is not consulted" % (HAIKU, OPUS))


@unittest.skipUnless(APPLIED, "CLAUDE_FIRST_2026_10_15 is not applied here")
class TheGate(_Env):
    def main(self, db, *extra, google=False):
        import usage_meter
        keep = usage_meter.budget_ok
        usage_meter.budget_ok = lambda con, need=0.0: google   # Google's spend cap: reached unless google
        sdk = TCE.FakeSDK([msg(DRAFT), msg(ACCEPT), msg(JUDGED)])
        real = self.claude
        ST.Claude = lambda a, meta, con: real(a, meta, con, sdk=sdk)
        ST.Gemini = FakeGem
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                rc = ST.main(["--db", str(db), "--doc", HAYA, "--engine", SONNET, "--limit", "1", "--no-groups",
                              "--no-compare", "--log-dir", str(self.td / "logs"), "--yes"] + list(extra))
        finally:
            usage_meter.budget_ok = keep
        return rc, out.getvalue(), sdk

    def test_a_run_with_no_gemini_is_not_stopped_by_google_s_cap(self):
        db = TCE.agama_fixture(self.td)
        rc, o, sdk = self.main(db, "--judge-engine", HAIKU, "--compare-engine", OPUS)
        self.assertEqual(rc, 0, o)
        self.assertIn("(1/1) 21.1", o); self.assertIn("passed", o)
        self.assertNotIn("STOPPED", o)
        self.assertEqual(FakeGem.made, [])
        rc, o, sdk = self.main(db, "--compare-engine", OPUS, "--redo")
        self.assertIn("STOPPED: the spend cap is reached", o, "Gemini's judge: Google's cap stands")
        self.assertEqual(sdk.requests, [])

    def test_the_dry_run_and_the_refusals(self):
        db = TCE.agama_fixture(self.td)
        e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
        run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc",
                                         HAYA] + list(x), capture_output=True, text=True, encoding="utf-8",
                                        cwd=str(self.td), env=e)
        before = base.md5(db)
        r = run("--engine", SONNET, "--judge-engine", HAIKU, "--compare-engine", OPUS, "--audit-every", "10")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("the judge %s (the Claude credit); the second judge and the audit %s (the Claude credit); no "
                      "Gemini call: Google's spend cap is not consulted" % (HAIKU, OPUS), r.stdout)
        self.assertIn("--audit-every 10 --judge-engine %s --compare-engine %s --yes --max-usd" % (HAIKU, OPUS), r.stdout)
        r = run("--engine", SONNET, "--judge-engine", SONNET)
        self.assertEqual(r.returncode, 1); self.assertIn("is the translator's own model", r.stdout)
        r = run("--engine", SONNET, "--judge-engine", HAIKU + "@huge")
        self.assertEqual(r.returncode, 1); self.assertIn("REFUSE: --judge-engine / --compare-engine", r.stdout)
        r = run("--judge-engine", HAIKU)
        self.assertEqual(r.returncode, 1); self.assertIn("are for a Claude run", r.stdout)
        r = run("--engine", SONNET, "--judge-engine", HAIKU, "--compare-engine", OPUS, "--yes")
        self.assertEqual(r.returncode, 1); self.assertIn("ANTHROPIC_API_KEY is not set", r.stdout)
        self.assertEqual(base.md5(db), before, "nothing written")


@unittest.skipUnless(APPLIED, "CLAUDE_FIRST_2026_10_15 is not applied here")
class TheWorkingEnglish(unittest.TestCase):
    SA = "dharmakshetre kurukshetre samaveta yuyutsavah"

    def setUp(self):
        import db_utils, cost_tracker
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
        con.execute("UPDATE budget_state SET budget_usd=45, spent_usd=45, paused=1 WHERE id=1")   # Google's: reached
        con.commit(); con.close()
        import infer_mt
        self.mt = importlib.reload(infer_mt)
        self.mt.SLEEP = 0

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()

    def fake(self, answers, engine="claude-haiku-5-5", effort=None):
        sdk = TCE.FakeSDK(answers)
        self.mt._ANTHROPIC[(engine, effort)] = CE.Client(engine, effort, sdk=sdk)
        return sdk

    def tr(self, texts, engine=HAIKU):
        con = sqlite3.connect(self.db)
        try:
            return self.mt.translate_batch(con, texts, engine=engine, doc_code="D")
        finally:
            con.close()

    def q(self, sql):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()

    def test_on_the_credit_never_google_s_cap(self):
        sdk = self.fake([msg("On the field of dharma.")])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tr([self.SA]), ["On the field of dharma."])
        self.assertEqual(len(sdk.requests), 1)
        req = sdk.requests[0]
        self.assertEqual(req["model"], "claude-haiku-5-5")
        self.assertNotIn("temperature", req)
        self.assertIn(self.SA, req["messages"][0]["content"])
        self.assertTrue(req["system"].strip(), "the same system prompt as Gemini's")
        self.assertEqual(req["max_tokens"], self.mt.ANTHROPIC_MAX_TOKENS)
        rows = self.q("SELECT kind, engine, token_source, in_tokens, out_tokens, cost_usd, passages FROM usage_log")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:5], ("translation", HAIKU, "provider", 4000.0, 1500.0))
        self.assertAlmostEqual(rows[0][5], (4000 * 0.10 + 1500 * 0.50) / 1e6, places=9)
        self.assertEqual(self.q("SELECT spent_usd, paused FROM budget_state"), [(45.0, 1)], "budget_state untouched")
        self.assertEqual(self.q("SELECT engine, output FROM mt_cache"), [(HAIKU, "On the field of dharma.")])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tr([self.SA]), ["On the field of dharma."])
        self.assertEqual(len(sdk.requests), 1, "the cache answers the second time")

    def test_cut_off_refused_and_honest_gaps(self):
        sdk = self.fake([msg("half", stop="max_tokens"), msg("The whole verse.")])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tr([self.SA + " 1"]), ["The whole verse."])
        self.assertEqual([r["max_tokens"] for r in sdk.requests], [self.mt.ANTHROPIC_MAX_TOKENS,
                                                                   2 * self.mt.ANTHROPIC_MAX_TOKENS])
        self.fake([msg("a", stop="max_tokens"), msg("b", stop="max_tokens"), msg("no", stop="refusal")])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tr([self.SA + " 2", self.SA + " 3"]), ["", ""])
        self.assertEqual(self.q("SELECT COUNT(*) FROM mt_cache WHERE output IN ('', 'a', 'b', 'no')"), [(0,)],
                         "an empty answer is never cached")
        self.assertEqual(self.q("SELECT COUNT(*) FROM usage_log WHERE engine = '%s'" % HAIKU), [(5,)], "each call metered")

    def test_it_stops_when_it_cannot_go_on(self):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO usage_log(ts, kind, engine, cost_usd, ok, token_source) VALUES "
                    "(strftime('%Y-%m-%dT%H:%M:%fZ','now'), 'scholar', 'anthropic:claude-sonnet-5-5', 190.0, 1, 'provider')")
        con.commit(); con.close()
        sdk = self.fake([msg("x")])
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(self.mt.BudgetBlocked):
                self.tr([self.SA + " 4"])
        self.assertEqual(sdk.requests, [], "the credit is asked first")
        self.assertTrue(issubclass(self.mt.BudgetBlocked, self.mt.QuotaExhausted), "the run stops")

    def test_no_key_a_refusal_to_bill_a_lasting_rate_limit(self):
        os.environ["ANTHROPIC_API_KEY"] = ""
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(self.mt.ClaudeUnavailable):
                self.tr([self.SA + " 5"], engine="anthropic:claude-haiku-5-5@low")
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.fake([RuntimeError("Your credit balance is too low to access the Anthropic API")])
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(self.mt.ClaudeUnavailable):
                self.tr([self.SA + " 6"])
        self.fake([RuntimeError("429 rate_limit_error")] * 3)
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(self.mt.QuotaExhausted):
                self.tr([self.SA + " 7"])
        self.fake([RuntimeError("500 server error")] * 3)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.tr([self.SA + " 8"]), [""], "one verse failed: empty, the run goes on")

    def test_the_default_is_still_gemini(self):
        self.assertEqual(self.mt.DEFAULT_ENGINE, os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"))


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "infer_mt.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_claudefirst_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_claude_first_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_rejudge_*"))   # REJUDGE_2026_10_15 came after (scholar_translate.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "infer_mt.py"
            p.write_bytes(p.read_bytes().replace(b'        elif engine.startswith("echo"):', b'        elif engine == "echo":'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("infer_mt.py: anchor 4 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"CLAUDE_FIRST", (t / "scripts" / "scholar_translate.py").read_bytes(), "all or nothing")
            (t / "scripts" / "scholar_translate.py").write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry RUN_FIX_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_claude_first_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"CLAUDE_FIRST_2026_10_15", b)
        if APPLIED:
            for f in ThePatcher.FILES:
                self.assertIn(b"CLAUDE_FIRST_2026_10_15", (SCRIPTS / f).read_bytes(), f)
            self.assertTrue(all(x < 128 for x in (SCRIPTS / "scholar_translate.py").read_bytes()))


if __name__ == "__main__":
    unittest.main()
