# -*- coding: ascii -*-
"""MARK_PASSAGES_2026_10_16 (a person's text_type for the passages of some pages, logged, undoable) and
THINKING_PROBE_2026_10_16 (the judge with and without gemini-2.5-flash's thinking, metered). Temp files only; nothing
is called (a stub opener stands for the Gemini REST API)."""
import io, json, os, sqlite3, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import mark_passages as MP                      # noqa: E402
import gemini_thinking_probe as TP              # noqa: E402

ST = base.ST
SONNET = "anthropic:claude-sonnet-5-5"


def run(fn, *argv, **kw):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = fn(list(argv), **kw)
    return rc, out.getvalue()


class TheMarks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        self.log = self.td / "log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def types(self):
        con = sqlite3.connect(str(self.db))
        try:
            return [r[0] for r in con.execute("SELECT text_type FROM passages ORDER BY page_no, idx")]
        finally:
            con.close()

    def mp(self, *x):
        return run(MP.main, "--db", str(self.db), "--doc", "MBh01", "--log", str(self.log), *x)

    def test_a_dry_run_apply_and_undo(self):
        before = self.types()
        rc, o = self.mp("--pages", "1", "--idx", "1-2", "--type", "noise", "--reason", "a vision OCR of another text")
        self.assertEqual(rc, 0, o); self.assertIn("p1.1  mula -> noise", o); self.assertIn("2 passage(s) would change", o)
        self.assertEqual(self.types(), before, "a dry run writes nothing")
        self.assertFalse(self.log.exists())
        rc, o = self.mp("--pages", "1", "--idx", "1-2", "--type", "noise", "--reason", "a vision OCR of another text",
                        "--by", "Dhruv", "--apply")
        self.assertEqual(rc, 0, o)
        self.assertEqual(self.types()[:3], ["noise", "noise", "mula"])
        log = [json.loads(x) for x in self.log.read_text().splitlines()]
        self.assertEqual([(d["old"], d["new"], d["by"], d["mark"]) for d in log],
                         [("mula", "noise", "Dhruv", MP.MARK)] * 2)
        rc, o = self.mp("--pages", "1", "--idx", "1-2", "--type", "noise", "--reason", "again", "--apply")
        self.assertIn("nothing to change", o)
        rc, o = self.mp("--pages", "1", "--undo", "--apply")
        self.assertEqual(rc, 0, o); self.assertIn("2 passage(s) changed", o)
        self.assertEqual(self.types(), before, "put back")
        self.assertEqual(len(self.log.read_text().splitlines()), 4, "the undo is logged too")

    def test_refusals(self):
        rc, o = self.mp("--pages", "1", "--type", "noise")
        self.assertEqual(rc, 1); self.assertIn("--type and --reason are needed", o)
        rc, o = self.mp("--pages", "9", "--type", "noise", "--reason", "r")
        self.assertEqual(rc, 1); self.assertIn("has no passages on page(s) 9", o)
        self.assertEqual(MP.parse_list("17-19,21"), [17, 18, 19, 21])


class _Resp:
    def __init__(self, d):
        self.b = json.dumps(d).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.b


class StubOpener:
    """The Gemini REST API: with a thinking budget of 0, no thinking and fidelity 4; without one, 900 thinking tokens and
    fidelity 5."""

    def __init__(self):
        self.bodies, self.headers = [], []

    def open(self, req, timeout=None):
        body = json.loads(req.data.decode())
        self.bodies.append(body); self.headers.append(dict(req.header_items()))
        off = "thinkingConfig" in body["generationConfig"]
        text = '{"reason":"ok","fidelity":%d,"fluency":5}' % (4 if off else 5)
        return _Resp({"candidates": [{"content": {"parts": [{"text": "plan", "thought": True}, {"text": text}]},
                                      "finishReason": "STOP"}],
                      "usageMetadata": {"promptTokenCount": 400, "candidatesTokenCount": 20,
                                        "thoughtsTokenCount": 0 if off else 900, "totalTokenCount": 420 if off else 1320}})


class TheProbe(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["GEMINI_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        import db_utils, cost_tracker
        con = db_utils.connect(str(self.db))
        ST.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
        con.execute("UPDATE budget_state SET budget_usd = 100, spent_usd = 0, paused = 0 WHERE id = 1")
        allp = ST.load_text(con, "MBh01")
        for x in allp[:3]:
            ST.store(con, {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"],
                           "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]), "translation": "E //",
                           "critique": "[]", "status": "passed", "engine": SONNET, "judge_engine": ST.JUDGE,
                           "created_at": "2026-10-15T13:00:00+00:00"})
        con.commit(); con.close()

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()

    def test_a_dry_run_then_the_two_ways(self):
        before = base.md5(self.db)
        rc, o = run(TP.main, "--db", str(self.db), "--doc", "MBh01", "--n", "2")
        self.assertEqual(rc, 0, o)
        self.assertIn("MBh01: 2 verse(s) of %s; 4 call(s)" % SONNET, o); self.assertIn("the SDK: ", o)
        self.assertEqual(base.md5(self.db), before, "a dry run writes nothing")
        op = StubOpener()
        rc, o = run(TP.main, "--db", str(self.db), "--doc", "MBh01", "--n", "2", "--yes", opener=op)
        self.assertEqual(rc, 0, o)
        self.assertEqual(len(op.bodies), 4)
        self.assertEqual([("thinkingConfig" in b["generationConfig"]) for b in op.bodies], [False, True, False, True])
        self.assertEqual(op.bodies[1]["generationConfig"]["thinkingConfig"], {"thinkingBudget": 0})
        self.assertNotIn("key=", json.dumps(op.bodies), "the key travels in a header, not the URL or the body")
        self.assertIn("X-goog-api-key", op.headers[0])
        con = sqlite3.connect(str(self.db))
        rows = con.execute("SELECT kind, engine, in_tokens, out_tokens, cost_usd FROM usage_log ORDER BY id").fetchall()
        con.close()
        self.assertEqual([(r[0], r[1]) for r in rows], [("probe", "gemini:gemini-2.5-flash")] * 4)
        self.assertEqual([r[3] for r in rows], [920.0, 20.0, 920.0, 20.0], "the thinking billed as output")
        self.assertIn("its fidelity is the same in 0 of 2, within one in 2; pass or flag the same in 2", o)
        self.assertIn("with thinking: 2 call(s)", o); self.assertIn("900 thinking tokens a call", o)

    def test_without_a_key_nothing_is_sent(self):
        os.environ["GEMINI_API_KEY"] = ""
        op = StubOpener()
        rc, o = run(TP.main, "--db", str(self.db), "--doc", "MBh01", "--n", "1", "--yes", opener=op)
        self.assertEqual(rc, 1); self.assertIn("GEMINI_API_KEY is not set", o); self.assertEqual(op.bodies, [])


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p, m in ((SCRIPTS / "mark_passages.py", b"MARK_PASSAGES_2026_10_16"),
                     (SCRIPTS / "gemini_thinking_probe.py", b"THINKING_PROBE_2026_10_16")):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(m, b)
        self.assertTrue(all(x < 128 for x in Path(__file__).read_bytes()))


if __name__ == "__main__":
    unittest.main()
