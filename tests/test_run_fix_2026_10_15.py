# -*- coding: ascii -*-
"""RUN_FIX_2026_10_15: an answer's first whole JSON object is read whatever follows it; a Claude critic not answering in
JSON is asked once more, and an answer still unread is kept (unparsed_<doc>.jsonl beside the run's log) and named in
the row's doubts; a dashboard pipeline past its ingest (translating, exporting) does not stop a run. Temp files only;
nothing is called (a scripted SDK; a dashboard of our own on 127.0.0.1, never the one on 5057)."""
import http.server, json, os, shutil, subprocess, sys, tempfile, threading, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import test_claude_engine_2026_10_15 as TCE     # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "first_object")
HAYA, SONNET = TCE.HAYA, TCE.SONNET
CRIT = '{"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept"}'
DRAFT = '{"translation": "The suta said. //", "notes": [], "glossary": [], "doubts": ""}'


@unittest.skipUnless(APPLIED, "RUN_FIX_2026_10_15 is not applied here")
class TheAnswers(unittest.TestCase):
    def test_the_first_whole_object_whatever_follows_it(self):
        p = ST.parse_json
        self.assertEqual(p('{"a": 1}\n\nNote: the {b} of it.'), {"a": 1}, "the old greedy match read no object here")
        self.assertEqual(p('```json\n{"a": 1}\n```\nI hope this helps {x}.'), {"a": 1})
        self.assertEqual(p('The critique {as asked}:\n{"a": 2, "b": {"c": 3}} and more }'), {"a": 2, "b": {"c": 3}})
        self.assertEqual(p('{"a": {"b": 1}}'), {"a": {"b": 1}}, "whole JSON as before")
        self.assertEqual(p('```json\n{"a": 1}\n```'), {"a": 1})
        for s in ("", None, "no braces", "[1, 2]", '{"cut": "of'):
            self.assertIsNone(p(s), s)

    def test_first_object_tries_a_few_braces_only(self):
        self.assertEqual(ST.first_object('x {y} {"a": 1}'), {"a": 1})
        self.assertIsNone(ST.first_object("{" * 30 + '{"a": 1}'), "20 tries")
        self.assertEqual(ST.first_object("{" * 30 + '{"a": 1}', tries=40), {"a": 1})
        self.assertIsNone(ST.first_object('{"a": 1'))


@unittest.skipUnless(APPLIED, "RUN_FIX_2026_10_15 is not applied here")
class TheCritic(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.ucon = TCE.usage_db(self.td)
        self.logs = self.td / "logs"

    def tearDown(self):
        self.ucon.close()
        self.tmp.cleanup()
        os.environ.clear(); os.environ.update(self.keep)

    def asker(self, answers, doc=HAYA, log=True):
        c = TCE.claude_asker(answers, {"doc": doc, "title": "t"}, self.ucon)
        if log:
            c.a.log_dir = str(self.logs)
        return c

    def kept(self, doc=HAYA):
        p = self.logs / ("unparsed_%s.jsonl" % doc)
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def test_a_critic_not_json_is_asked_once_more(self):
        c = self.asker([TCE.msg("Here is my reading, not JSON."), TCE.msg(CRIT)])
        d, cost = c.ask("critic", "M")
        self.assertEqual(d["verdict"], "accept")
        self.assertEqual(len(c.client.sdk.requests), 2)
        self.assertEqual([r["max_tokens"] for r in c.client.sdk.requests], [ST.CLAUDE_MAX_TOKENS, 2 * ST.CLAUDE_MAX_TOKENS])
        self.assertAlmostEqual(cost, 2 * (4000 * 2e-6 + 1500 * 10e-6), msg="both calls are charged")
        self.assertEqual(self.kept(), [], "read the second time: nothing kept")
        c = self.asker([TCE.msg(CRIT + "\n\nI hope this helps {sic}.")])
        self.assertEqual(c.ask("critic", "M")[0]["verdict"], "accept")
        self.assertEqual(len(c.client.sdk.requests), 1, "trailing words are no reason to ask again")

    def test_an_answer_still_unread_is_kept(self):
        c = self.asker([TCE.msg("x" * 700), TCE.msg("y" * 400 + "END")])
        self.assertIsNone(c.ask("critic", "M")[0])
        k = self.kept()
        self.assertEqual(len(k), 1)
        self.assertEqual((k[0]["kind"], k[0]["stop"], k[0]["chars"], k[0]["engine"], k[0]["doc"], k[0]["mark"]),
                         ("critic", "end_turn", 403, "claude-sonnet-5-5", HAYA, "RUN_FIX_2026_10_15"))
        self.assertEqual((k[0]["head"], k[0]["tail"]), ("y" * 300, "y" * 297 + "END"))
        c = self.asker([TCE.msg("I will not", stop="refusal")])
        self.assertIsNone(c.ask("critic", "M")[0])
        self.assertEqual(len(c.client.sdk.requests), 1, "a refusal is not asked again")
        self.assertEqual(self.kept()[-1]["stop"], "refusal")
        c = self.asker([TCE.msg("not json"), TCE.msg("not json")])
        self.assertIsNone(c.ask("draft", "M")[0])
        self.assertEqual((len(self.kept()), self.kept()[-1]["kind"]), (3, "draft"))

    def test_without_a_log_folder_nothing_is_written_and_it_never_raises(self):
        c = self.asker([TCE.msg("x"), TCE.msg("y")], log=False)
        self.assertIsNone(c.ask("critic", "M")[0])
        self.assertFalse(self.logs.exists())
        f = self.td / "a_file"; f.write_text("x")
        a = types.SimpleNamespace(log_dir=str(f))
        self.assertIsNone(ST.keep_unparsed(a, {"doc": HAYA}, "critic", "end_turn", "txt", "m"), "not a folder")
        self.assertIsNone(ST.keep_unparsed(types.SimpleNamespace(), {"doc": HAYA}, "critic", "end_turn", "txt", "m"))
        p = ST.keep_unparsed(types.SimpleNamespace(log_dir=str(self.logs)), {"doc": "a/b c"}, "critic", None, None, "m")
        self.assertEqual(p.name, "unparsed_a_b_c.jsonl")

    def test_the_compare_and_the_judge_stay_gemini_s(self):
        c = self.asker([])
        c.ask("compare", "M"); c.judge("s", "i", "e")
        self.assertEqual((c.gem.asked, c.client.sdk.requests), (["compare"], []))


@unittest.skipUnless(APPLIED, "RUN_FIX_2026_10_15 is not applied here")
class TheRow(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        import db_utils
        self.con = db_utils.connect(str(self.db))
        ST.ensure_schema(self.con)
        self.allp = ST.load_text(self.con, "MBh01")
        self.meta = ST.doc_meta(self.con, "MBh01", self.allp)
        self.i = next(k for k, x in enumerate(self.allp) if x["ref"] == "1.1.8")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()
        os.environ.clear(); os.environ.update(self.keep)

    def unit(self, asker, **kw):
        a = base.args(self.db, compare=False, **kw)
        return a, ST.one_unit(a, self.allp, [self.i], self.meta, {}, asker, self.con, 0.01)[0]

    def test_its_doubts_say_the_critic_was_not_read(self):
        ucon = TCE.usage_db(self.td)
        try:
            c = TCE.claude_asker([TCE.msg(DRAFT), TCE.msg("no"), TCE.msg("still no")], self.meta, ucon)
            _a, r = self.unit(c, engine=SONNET)
        finally:
            ucon.close()
        self.assertEqual(r["status"], "flagged", "a person reads it")
        self.assertIn("the critic's answer could not be read", r["doubts"])
        self.assertNotIn("unparsed_", r["doubts"], "the asker had no log folder: nothing was kept")
        ucon = TCE.usage_db(self.td)
        try:
            c = TCE.claude_asker([TCE.msg(DRAFT), TCE.msg("no"), TCE.msg("still no")], self.meta, ucon)
            c.a.log_dir = str(self.td / "logs")
            _a, r = self.unit(c, engine=SONNET)
        finally:
            ucon.close()
        self.assertIn("(it is kept in unparsed_MBh01.jsonl beside the run's log)", r["doubts"])
        self.assertTrue((self.td / "logs" / "unparsed_MBh01.jsonl").exists())
        self.assertEqual(len(c.client.sdk.requests), 3, "the draft, the critic, the critic once more")

    def test_a_gemini_run_says_it_without_a_file(self):
        s = base.Stub([base.draft("The suta said. //")], [], [(5, 5)])
        _a, r = self.unit(s)
        self.assertEqual(r["status"], "flagged")
        self.assertIn("the critic's answer could not be read", r["doubts"])
        self.assertNotIn("unparsed_", r["doubts"])
        _a, r = self.unit(base.Stub([base.draft("The suta said. //")], [base.ACCEPT], [(5, 5), (5, 5)]))
        self.assertEqual((r["status"], r["doubts"]), ("passed", ""), "read: nothing said")


class _Dash(http.server.BaseHTTPRequestHandler):
    jobs, outs = [], {}

    def do_GET(self):
        if self.path == "/api/jobs/running":
            body, code = {"running": self.jobs}, 200
        elif self.path.startswith("/api/job/") and self.path[len("/api/job/"):] in self.outs:
            body, code = {"out": self.outs[self.path[len("/api/job/"):]]}, 200
        else:
            body, code = {"error": "unknown job"}, 404
        b = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


PIPE_INGEST = "\n####\n  Sanskrit Pipeline - %s\n####\n[OCR] Nothing to OCR\n\n====\n  Ingest %s\n  python ...\n====\n"
PIPE_TRANSLATE = PIPE_INGEST + "[OK] Ingest %s  (12.0s)\n\n====\n  Translate %s\n  python ...\n====\n"
PIPE_EXPORT = PIPE_TRANSLATE + "lots of lines\n[OK] Translate %s  (9000.0s)\n\n====\n  Export %s\n  python ...\n====\n"


@unittest.skipUnless(APPLIED, "RUN_FIX_2026_10_15 is not applied here")
class TheDashboard(unittest.TestCase):
    D = "Karan_Aagama_X"

    def setUp(self):
        import repair_text as rt
        self.rt, self.url = rt, rt.DASHBOARD
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Dash)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        rt.DASHBOARD = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def tearDown(self):
        self.rt.DASHBOARD = self.url
        self.srv.shutdown(); self.srv.server_close()
        _Dash.jobs, _Dash.outs = [], {}

    def busy(self, jobs, outs=None):
        _Dash.jobs, _Dash.outs = jobs, outs or {}
        b = ST.busy_with(self.D)
        return None if b is None else [j["id"] for j in b]

    def test_a_pipeline_past_its_ingest_does_not_stop_a_run(self):
        D = self.D
        j = lambda i, kind="pipeline", state="running", doc=D: {"id": i, "kind": kind, "doc": doc, "state": state}
        self.assertEqual(self.busy([j("p1")], {"p1": PIPE_TRANSLATE % (D, D, D, D)}), [], "translating")
        self.assertEqual(self.busy([j("p1")], {"p1": PIPE_EXPORT % ((D,) * 6)}), [], "exporting")
        self.assertEqual(self.busy([j("p1")], {"p1": PIPE_INGEST % (D, D)}), ["p1"], "still ingesting")
        self.assertEqual(self.busy([j("p1", state="queued")], {"p1": PIPE_TRANSLATE % (D, D, D, D)}), ["p1"], "queued")
        self.assertEqual(self.busy([j("p1")], {}), ["p1"], "the dashboard does not say: as before")
        self.assertEqual(self.busy([j("p1")], {"p1": PIPE_TRANSLATE % ("Other", "Other", "Other", "Other")}), ["p1"],
                         "another text's stage is not this one's")
        self.assertEqual(self.busy([j("p2", kind="repair")], {"p2": PIPE_TRANSLATE % (D, D, D, D)}), ["p2"],
                         "only a pipeline")
        self.assertEqual(self.busy([j("t1", kind="translate"), j("o1", kind="ocr"), j("x", kind="repair", doc="Other")]),
                         [], "as before: the quiet kinds and other texts")

    def test_a_dashboard_not_answering_is_none_as_before(self):
        self.rt.DASHBOARD = "http://127.0.0.1:9"
        self.assertIsNone(ST.busy_with(self.D))
        self.assertEqual(ST.job_out("p1"), "")
        self.assertFalse(ST.pipeline_past_ingest({"id": "p1", "state": "running"}, self.D))
        self.assertFalse(ST.pipeline_past_ingest({"state": "running"}, self.D), "no id")


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("scholar_translate.py.bak_runfix_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        pat = [sys.executable, str(SCRIPTS / "patch_run_fix_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            p = t / "scripts" / "scholar_translate.py"
            shutil.copy2(baks[0], p)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(p.read_bytes(), baks[0].read_bytes(), "--check writes nothing")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("scholar_translate.py.bak_claudefirst_*"))   # CLAUDE_FIRST_2026_10_15 came after
            self.assertEqual(p.read_bytes(), (later[0] if later else SCRIPTS / "scholar_translate.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"not in QUIET_KINDS]\n", b"not in QUIET_KINDS]  # changed\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 6 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"RUN_FIX_2026", p.read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry AUDIT_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_run_fix_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"RUN_FIX_2026_10_15", b)
        if APPLIED:
            b = (SCRIPTS / "scholar_translate.py").read_bytes()
            self.assertTrue(all(x < 128 for x in b)); self.assertIn(b"RUN_FIX_2026_10_15", b)


if __name__ == "__main__":
    unittest.main()
