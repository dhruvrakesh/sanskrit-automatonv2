# -*- coding: ascii -*-
"""CLAUDE_ENGINE_2026_10_15: scripts/claude_engine.py (the prices, the meter, the credit and its cap, the request's
shape), Claude as the scholarly English's engine in scripts/scholar_translate.py (its asker, the Gemini judges, the
Agamas' rule, the apparatus, the Hindi words, --held-ok, --no-glossary-adds), scripts/scholar_duel.py (the spans, the
blind reading, the person's pick, the page) and the patcher. Temp files only; nothing is called: the SDK, the client and
the judges are stubs, and the one CLI call that could send is made without a key."""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_engine as CE                    # noqa: E402
import test_scholar_2026_10_14 as base        # noqa: E402
import test_scholar_v2_2026_10_14 as v2       # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "SYSTEMS")
if APPLIED:
    DUEL = base.load("scholar_duel_t", SCRIPTS / "scholar_duel.py")
    DUEL.ST = ST
    ST.SYSTEMS["duel"] = DUEL.SYSTEM_DUEL

# the Hayasirsa's second patala, as its vision reading has it (with the edition's footnote numbers), and its apparatus
H1 = ("\u0936\u094d\u0930\u0940\u092d\u0917\u0935\u093e\u0928\u094d \u0909\u0935\u093e\u091a- \u092f\u0924\u094d "
      "\u0924\u094d\u0935\u092f\u093e \u092a\u0943\u0937\u094d\u091f\u092e\u0916\u093f\u0932\u0902 \u0924\u0924\u094d "
      "\u0938\u0930\u094d\u0935\u0902 \u0915\u0925\u092f\u093e\u092e\u093f \u0924\u0947 \u0964")
H2 = ("\u0907\u092e\u0947 \u092d\u093e\u0917\u0935\u0924\u093e\u0928\u093e\u0902 \u0924\u0941" "5 "
      "\u0924\u0925\u093e \u0938\u093e\u092e\u093e\u0928\u094d\u092f\u0938\u0902\u0939\u093f\u0924\u093e \u0965")
H3 = ("\u0935\u094d\u092f\u093e\u0938\u094b\u0915\u094d\u0924\u093e \u0938\u0902\u0939\u093f\u0924\u093e "
      "\u091a\u093e\u0928\u094d\u092f\u093e" "6 \u0924\u0925\u093e \u092a\u0930\u092e\u0938\u0902\u0939\u093f\u0924\u093e \u0965")
APP = "5 \u091a-B. 6 \u091a\u0935-B,C. 7 \u092f\u0924\u094d (?)-B,C. 8 \u0938\u0902\u0938\u094d\u0925\u093f\u0924\u0903-B,C."
# the Karanagama's Hindi under its verse 30.7 (two of the old Hindi words only)
KARAN_HI = ("\u092e\u0928\u0941\u0937\u094d\u092f \u0915\u0947 \u0926\u0938 \u092f\u093e \u092c\u093e\u0930\u0939 "
            "\u0939\u093e\u0925 \u0915\u0947 \u092a\u0930\u093f\u092e\u093e\u0923 \u0935\u093e\u0932\u093e "
            "\u092e\u0923\u094d\u0921\u092a \u0926\u0940\u0915\u094d\u0937\u093e \u0926\u0947\u0928\u0947 \u0915\u0947 "
            "\u0932\u093f\u090f \u092c\u0928\u0935\u093e\u090f, \u0907\u0938 \u092e\u0923\u094d\u0921\u092a \u092e\u0947\u0902 "
            "\u0938\u094b\u0932\u0939 \u0916\u092e\u094d\u092d\u0947 \u0939\u094b\u0928\u0947 \u091a\u093e\u0939\u093f\u090f")
HAYA = "HAYASHIRSHA_PANCARATRA"
SONNET = "anthropic:claude-sonnet-5-5"


def agama_fixture(td: Path, register=None) -> Path:
    db = base.fixture(td, register)
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO docs(code, category) VALUES (?, 'agama')", (HAYA,))
    did = con.execute("SELECT id FROM docs WHERE code = ?", (HAYA,)).fetchone()[0]
    for k, (t, tt) in enumerate(((H1, "mula"), (H2, "mula"), (H3, "mula"), (APP, "prose")), 1):
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, iast, translation, verse_ref, chapter, text_type, "
                    "quality_score, ocr_engine) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (did, 21, k, t, "", "", None, None, tt, 0.77, "gemini-vision:gemini-2.5-flash"))
    con.commit(); con.close()
    return db


class Usage(types.SimpleNamespace):
    pass


def msg(text, stop="end_turn", inp=4000, out=1500, think=1000, thinking_block=True):
    blocks = ([types.SimpleNamespace(type="thinking", thinking="...")] if thinking_block else []) + [
        types.SimpleNamespace(type="text", text=text)]
    return types.SimpleNamespace(content=blocks, stop_reason=stop, usage=Usage(
        input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0, cache_read_input_tokens=0,
        output_tokens_details=types.SimpleNamespace(thinking_tokens=think)))


class FakeSDK:
    """anthropic, as far as Client uses it: Anthropic(max_retries, timeout).messages.stream(**kw) -> get_final_message."""

    def __init__(self, answers):
        self.answers, self.requests, self.kw = list(answers), [], None
        sdk = self

        class _Stream:
            def __init__(self, kw):
                self.kw = kw

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get_final_message(self):
                a = sdk.answers.pop(0)
                if isinstance(a, Exception):
                    raise a
                return a

        class _Messages:
            def stream(self, **kw):
                sdk.requests.append(kw)
                return _Stream(kw)

        class Anthropic:
            def __init__(self, **kw):
                sdk.kw = kw
                self.messages = _Messages()

        self.Anthropic = Anthropic


def usage_db(td: Path) -> sqlite3.Connection:
    import cost_tracker
    con = sqlite3.connect(str(td / "u.db"))
    cost_tracker.ensure_usage_schema(con)
    return con


class ThePrices(unittest.TestCase):
    def test_names(self):
        self.assertEqual(CE.parse_engine("anthropic:claude-sonnet-5-5@medium"), ("claude-sonnet-5-5", "medium"))
        self.assertEqual(CE.parse_engine("anthropic:claude-opus-5-5"), ("claude-opus-5-5", None))
        self.assertRaises(ValueError, CE.parse_engine, "anthropic:claude-opus-5-5@adaptive")
        self.assertTrue(CE.is_claude(SONNET)); self.assertFalse(CE.is_claude("gemini:gemini-2.5-pro"))
        self.assertEqual(CE.engine_name("claude-haiku-5-5", "low"), "anthropic:claude-haiku-5-5@low")

    def test_what_an_answer_costs(self):
        u = {"input_tokens": 4600, "output_tokens": 2000}
        self.assertAlmostEqual(CE.price("claude-sonnet-5-5", u), 4600 * 2e-6 + 2000 * 10e-6)
        self.assertAlmostEqual(CE.price("claude-opus-5-5", u), 4600 * 4e-6 + 2000 * 20e-6)
        self.assertAlmostEqual(CE.price("claude-sonnet-5-5", u, batch=True), (4600 * 2e-6 + 2000 * 10e-6) / 2)
        c = {"input_tokens": 100, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 3000, "output_tokens": 10}
        self.assertAlmostEqual(CE.price("claude-sonnet-5-5", c), (100 * 2 + 1000 * 2.5 + 3000 * 0.10 + 10 * 10) / 1e6)
        self.assertAlmostEqual(CE.price("claude-haiku-5-5", {"input_tokens": 1000, "output_tokens": 1000}), 0.0006)
        self.assertAlmostEqual(CE.price("claude-haiku-5-5", {"input_tokens": 120000, "output_tokens": 1000}),
                               (120000 * 0.50 + 1000 * 2.50) / 1e6, msg="a prompt over 100,000 tokens")
        self.assertAlmostEqual(CE.price("claude-sonnet-9", u), CE.price("claude-sonnet-5-5", u), msg="by its family")
        self.assertAlmostEqual(CE.price("claude-x", u), CE.price("claude-opus-5-5", u), msg="else the dearest")

    def test_the_tokens_as_the_sdk_or_the_batch_api_gives_them(self):
        self.assertEqual(CE.tokens(msg("x").usage)["thinking"], 1000)
        self.assertEqual(CE.tokens({"input_tokens": 5, "output_tokens": 7, "output_tokens_details": {"thinking_tokens": 3}}),
                         {"input": 5, "cache_write": 0, "cache_read": 0, "output": 7, "thinking": 3})
        self.assertEqual(CE.tokens(None)["output"], 0)

    def test_the_price_table_knows_them_by_name(self):
        import cost_tracker
        if not hasattr(ST, "SYSTEMS"):
            self.skipTest("not applied")
        self.assertEqual(cost_tracker._get_pricing("anthropic:claude-sonnet-5-5"), (2.00, 10.00))
        self.assertEqual(cost_tracker._get_pricing("anthropic:claude-opus-5-5@high"), (4.00, 20.00), "the effort after @")
        self.assertEqual(cost_tracker._get_pricing("anthropic:claude-haiku-5-5"), (0.10, 0.50))


class TheMeterAndTheCredit(unittest.TestCase):
    def test_recorded_in_usage_log_not_in_the_spend_cap(self):
        with tempfile.TemporaryDirectory() as d:
            con = usage_db(Path(d))
            before = con.execute("SELECT spent_usd FROM budget_state").fetchone()[0]
            cost = CE.meter(con, "scholar", HAYA, "claude-sonnet-5-5", msg("x").usage, 12.5)
            self.assertAlmostEqual(cost, 4000 * 2e-6 + 1500 * 10e-6)
            r = con.execute("SELECT kind, doc, engine, in_tokens, out_tokens, cost_usd, token_source, ok FROM usage_log").fetchone()
            self.assertEqual(r[:5], ("scholar", HAYA, "anthropic:claude-sonnet-5-5", 4000.0, 1500.0))
            self.assertAlmostEqual(r[5], cost); self.assertEqual(r[6:], ("provider", 1))
            self.assertEqual(con.execute("SELECT spent_usd FROM budget_state").fetchone()[0], before, "the credit pays it")
            self.assertEqual(con.execute("SELECT total_calls FROM usage_totals WHERE engine = ?",
                                         ("anthropic:claude-sonnet-5-5",)).fetchone()[0], 1)
            self.assertAlmostEqual(CE.meter(None, "scholar", HAYA, "claude-sonnet-5-5", msg("x").usage), cost,
                                   msg="priced even when it cannot be recorded")
            con.close()

    def test_the_credit_counts_the_claude_rows_since_its_day_and_stops_at_its_cap(self):
        with tempfile.TemporaryDirectory() as d:
            con = usage_db(Path(d))
            ins = lambda eng, cost, ts: con.execute("INSERT INTO usage_log(ts, kind, engine, cost_usd) VALUES (?, 'scholar', "
                                                    "?, ?)", (ts, eng, cost))
            ins("anthropic:claude-opus-5-5", 50.0, "2026-10-14T23:00:00.000Z")   # before the credit
            ins("gemini:gemini-2.5-pro", 70.0, "2026-10-15T09:00:00.000Z")       # Google's
            ins("anthropic:claude-sonnet-5-5", 100.0, "2026-10-15T09:00:00.000Z")
            con.commit()
            c = CE.credit(con, today=__import__("datetime").date(2026, 10, 20))
            self.assertEqual((c["spent"], c["calls"], c["cap"], c["left"], c["expired"]), (100.0, 1, 190.0, 90.0, False))
            self.assertIn("$100.00 spent of $190.00 since 2026-10-15", CE.credit_line(c))
            day = __import__("datetime").date(2026, 10, 20)
            self.assertTrue(CE.budget_ok(con, 89.0, today=day))
            self.assertFalse(CE.budget_ok(con, 91.0, today=day))
            self.assertFalse(CE.budget_ok(con, 0.0, today=__import__("datetime").date(2026, 11, 11)), "expired")
            keep = dict(os.environ)
            try:
                os.environ["SA_CLAUDE_CREDIT_USD"] = "100"
                self.assertFalse(CE.budget_ok(con, 0.01, today=day), "the cap from .env")
            finally:
                os.environ.clear(); os.environ.update(keep)
            con.close()
            bad = sqlite3.connect(":memory:")
            bad.close()
            self.assertFalse(CE.budget_ok(bad, 0.0), "fails closed")


class TheClient(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)

    def test_the_request_has_no_sampling_and_the_effort_in_output_config(self):
        sdk = FakeSDK([msg('{"ok": 1}')])
        c = CE.Client("claude-sonnet-5-5", "medium", sdk=sdk)
        m = c.create("SYS", "USER", 16000)
        kw = sdk.requests[0]
        self.assertEqual(kw["model"], "claude-sonnet-5-5"); self.assertEqual(kw["max_tokens"], 16000)
        self.assertEqual(kw["system"], "SYS"); self.assertEqual(kw["messages"], [{"role": "user", "content": "USER"}])
        self.assertEqual(kw["output_config"], {"effort": "medium"})
        for k in ("temperature", "top_p", "top_k", "thinking"):
            self.assertNotIn(k, kw)
        self.assertEqual(sdk.kw["max_retries"], CE.MAX_RETRIES)
        self.assertEqual(CE.text_of(m), '{"ok": 1}', "the thinking block is left out")
        self.assertEqual(CE.stop_of(m), "end_turn")
        sdk2 = FakeSDK([msg("x")])
        CE.Client("claude-opus-5-5", None, sdk=sdk2).create("S", "U", 10)
        self.assertNotIn("output_config", sdk2.requests[0], "the model's own effort")

    def test_without_the_key_nothing_is_built(self):
        del os.environ["ANTHROPIC_API_KEY"]
        self.assertRaises(RuntimeError, CE.Client, "claude-sonnet-5-5", None, sdk=FakeSDK([]))
        os.environ["ANTHROPIC_API_KEY"] = "x"
        self.assertRaises(RuntimeError, CE.Client, "claude-sonnet-5-5", "huge", sdk=FakeSDK([]))

    def test_the_cli_reads_the_credit_free_and_the_probe_needs_the_key(self):
        with tempfile.TemporaryDirectory() as d:
            con = usage_db(Path(d)); con.close()
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            r = subprocess.run([sys.executable, str(SCRIPTS / "claude_engine.py"), "--db", str(Path(d) / "u.db"), "--credit"],
                               capture_output=True, text=True, env=env, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("VERDICT: the Claude credit: $0.00 spent of $190.00", r.stdout)
            r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import claude_engine as c; "
                                "sys.exit(c.main(['--db', %r, '--probe']))" % (str(SCRIPTS), str(Path(d) / "u.db"))],
                               capture_output=True, text=True, env=env, cwd=d)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("REFUSE: ANTHROPIC_API_KEY is not set", r.stdout)
            con = sqlite3.connect(str(Path(d) / "u.db"))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM usage_log").fetchone()[0], 0, "nothing sent, nothing written")
            con.close()


class StubGem:
    """The Gemini half of a Claude run: the judge and the second judge."""

    def __init__(self):
        self.spent, self.con, self.asked, self.judged = 0.0, None, [], 0

    def ask(self, kind, m):
        self.asked.append(kind); self.spent += 0.03
        return {"A": {"fidelity": 5, "errors": []}, "B": {"fidelity": 4, "errors": []}, "better": "A", "reason": "r"}, 0.03

    def judge(self, src, iast, english):
        self.judged += 1; self.spent += 0.0002
        return 5, 5, "ok", 0.0002


def claude_asker(answers, meta, con=None):
    c = object.__new__(ST.Claude)
    c.ce, c.a, c.meta = CE, types.SimpleNamespace(engine=SONNET), meta
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-a-key")
    c.client = CE.Client("claude-sonnet-5-5", None, sdk=FakeSDK(answers))
    c.gem, c.own, c.meter_kind = StubGem(), 0.0, "scholar"
    c.con = con
    return c


@unittest.skipUnless(APPLIED, "CLAUDE_ENGINE_2026_10_15 is not applied here")
class TheScholar(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.busy = ST.busy_with
        ST.busy_with = lambda doc: []   # the dashboard, if one runs here, is not asked

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)
        ST.busy_with = self.busy

    def test_one_system_for_every_engine_and_the_agamas_rule(self):
        plain = {"title": "the Mah\u0101bh\u0101rata, Book 1"}
        ag = {"title": "the Haya\u015b\u012br\u1e63a Pa\u00f1car\u0101tra", "agama": True}
        self.assertEqual(ST.system_for("draft", plain), ST.SYSTEM_DRAFT.replace("{title}", plain["title"]))
        d = ST.system_for("draft", ag)
        self.assertIn("13. AGAMA AND TANTRA.", d)
        self.assertLess(d.index("13. AGAMA AND TANTRA."), d.index("Reply with one JSON object"), "before the reply's shape")
        self.assertIn("never translated", d)
        for k in ("critic", "compare"):
            self.assertIn("footnote number", ST.system_for(k, ag))
        self.assertNotIn("AGAMA", ST.system_for("groups", ag))
        self.assertIn("footnote number", ST.system_for("duel", ag))
        self.assertTrue(all(ord(c) < 128 for c in Path(ST.__file__).read_text(encoding="utf-8")))

    def test_the_texts_names_and_their_tradition(self):
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d))
            con = sqlite3.connect(str(db))
            m = ST.doc_meta(con, HAYA, ST.load_text(con, HAYA))
            self.assertTrue(m["agama"]); self.assertIn("Haya\u015b\u012br\u1e63a Pa\u00f1car\u0101tra", m["title"])
            m1 = ST.doc_meta(con, "MBh01", ST.load_text(con, "MBh01"))
            self.assertFalse(m1["agama"]); self.assertEqual(m1["title"], "the Mah\u0101bh\u0101rata, Book 1")
            con.close()
        self.assertTrue(ST.AGAMA.search(" Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi"))
        self.assertTrue(ST.AGAMA.search("tantra tantric_texts_series_edited_by_arthur_av"))
        self.assertFalse(ST.AGAMA.search(" 476948-Rgveda-samhita_Vol-ii"))

    def test_the_apparatus_goes_with_its_page_and_hindi_is_hindi(self):
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d))
            con = sqlite3.connect(str(db))
            allp = ST.load_text(con, HAYA)
            con.close()
            self.assertEqual(ST.apparatus_of(allp, [allp[1]]), APP)
            self.assertEqual(ST.apparatus_of(allp, [allp[3]]), "", "not itself")
            b = ST.with_apparatus("BASE", allp, [allp[1]])
            self.assertTrue(b.startswith("BASE\n\nTHE EDITION'S APPARATUS ON THIS PAGE")); self.assertTrue(b.endswith(APP))
            self.assertEqual(ST.with_apparatus("BASE", allp[:3], [allp[1]]), "BASE")
            self.assertIn("numbers among the words", ST.readiness(APP, "prose", None), "it is not sent itself")
        self.assertIn("Hindi prose", ST.readiness(KARAN_HI, "mula", 0.63))
        self.assertIsNone(ST.readiness(base.SANSKRIT_KE, "mula"), "Sanskrit stays Sanskrit")
        self.assertIsNone(ST.readiness(H3, "mula", 0.77))

    def test_the_claude_asker(self):
        good = msg('{"translation": "T //", "notes": [], "glossary": [], "doubts": ""}')
        with tempfile.TemporaryDirectory() as d:
            con = usage_db(Path(d))
            c = claude_asker([msg('{"translation": "cut'), good], {"doc": HAYA, "title": "t"}, con)
            c.client.sdk.answers[0].stop_reason = "max_tokens"
            dd, cost = c.ask("draft", "M")
            self.assertEqual(dd["translation"], "T //")
            reqs = c.client.sdk.requests
            self.assertEqual([r["max_tokens"] for r in reqs], [ST.CLAUDE_MAX_TOKENS, 2 * ST.CLAUDE_MAX_TOKENS])
            self.assertEqual(con.execute("SELECT COUNT(*), MIN(engine) FROM usage_log").fetchone(),
                             (2, "anthropic:claude-sonnet-5-5"))
            self.assertAlmostEqual(cost, 2 * (4000 * 2e-6 + 1500 * 10e-6))
            c2 = claude_asker([msg("not json"), good], {"doc": HAYA, "title": "t"}, con)
            self.assertEqual(c2.ask("draft", "M")[0]["translation"], "T //", "a draft not JSON is asked once more")
            c3 = claude_asker([msg("not json")], {"doc": HAYA, "title": "t"}, con)
            self.assertIsNone(c3.ask("critic", "M")[0], "a critic is not")
            self.assertEqual(c3.last, {"kind": "critic", "finish": "end_turn", "chars": 8, "json": False})
            c4 = claude_asker([msg("I cannot", stop="refusal")], {"doc": HAYA, "title": "t"}, con)
            self.assertIsNone(c4.ask("draft", "M")[0]); self.assertEqual(len(c4.client.sdk.requests), 1)
            c5 = claude_asker([RuntimeError("overloaded")], {"doc": HAYA, "title": "t"}, con)
            self.assertRaises(ST.CallFailed, c5.ask, "draft", "M")
            c6 = claude_asker([], {"doc": HAYA, "title": "t"}, con)
            c6.ask("compare", "M"); c6.judge("s", "i", "e")
            self.assertEqual((c6.gem.asked, c6.gem.judged, c6.client.sdk.requests), (["compare"], 1, []),
                             "a Claude English is judged by Gemini")
            self.assertAlmostEqual(c6.spent, 0.0302)
            c6.con = "X"; self.assertEqual(c6.gem.con, "X")
            con.close()

    def test_a_claude_run_stores_its_engine_and_the_agamas_version_and_keeps_the_glossary(self):
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            allp = ST.load_text(con, HAYA)
            meta = ST.doc_meta(con, HAYA, allp)
            a = v2.args(db, doc=HAYA, engine=SONNET, groups=False, compare=True, no_glossary_adds=True)
            ans = []
            for _ in range(3):
                ans += [msg(json.dumps({"translation": "E //", "notes": [], "doubts": "",
                                        "glossary": [{"term": "Haya\u015b\u012br\u1e63a", "rendering": "H", "kind": "deity",
                                                      "note": ""}]})),
                        msg(json.dumps({"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept"}))]
            c = claude_asker(ans, meta, con)
            picked, left, _s = ST.choose(a, allp, {})
            self.assertEqual(len(picked), 3)
            res = ST.run(a, allp, picked, meta, {}, c, con, {"typical": 0.01, "most": 0.02, "call": 0.01, "how": ""}, None)
            self.assertEqual(len(res["passed"]), 3, res)
            rows = con.execute("SELECT engine, prompt_version, judge_engine FROM scholar_translations").fetchall()
            self.assertEqual({r[0] for r in rows}, {SONNET})
            self.assertEqual({r[1] for r in rows}, {"scholar-v2.1+scholar-critic-v2+agama-1"})
            self.assertEqual(con.execute("SELECT COUNT(*) FROM scholar_glossary").fetchone()[0], 0, "--no-glossary-adds")
            sent = c.client.sdk.requests[0]
            self.assertIn("13. AGAMA AND TANTRA.", sent["system"])
            self.assertIn("THE EDITION'S APPARATUS ON THIS PAGE", c.client.sdk.requests[2]["messages"][0]["content"])
            self.assertEqual(c.gem.asked, [], "no working English: no second judge")
            con.close()

    def test_the_credit_stops_a_run_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            import cost_tracker
            cost_tracker.ensure_usage_schema(con)
            con.execute("INSERT INTO usage_log(kind, engine, cost_usd) VALUES ('scholar', ?, 189.999)", (SONNET,))
            con.commit()
            allp = ST.load_text(con, HAYA)
            meta = ST.doc_meta(con, HAYA, allp)
            a = v2.args(db, doc=HAYA, engine=SONNET, groups=False)
            c = claude_asker([], meta, con)
            gate = ST.CreditGate(CE, None)
            picked, _l, _s = ST.choose(a, allp, {})
            res = ST.run(a, allp, picked, meta, {}, c, con, {"typical": 0.05, "most": 0.1, "call": 0.05, "how": ""}, gate)
            self.assertIn("the Claude credit is spent or expired", res["stopped"])
            self.assertEqual(c.client.sdk.requests, [], "nothing sent")
            con.close()

    def test_two_runs_numbering_one_verse_at_once(self):
        class Racy:
            """The database as a run sees it when another run stores the same verse between its count and its write."""
            def __init__(self, con):
                self.con, self.n = con, 0
            def execute(self, sql, *a):
                if sql.startswith("SELECT MAX(version)") and self.n == 0:
                    self.n += 1
                    return self.con.execute("SELECT 0")
                return self.con.execute(sql, *a)
            def commit(self):
                self.con.commit()
            def rollback(self):
                self.con.rollback()
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            pid = ST.load_text(con, HAYA)[0]["id"]
            rec = lambda eng: {"passage_id": pid, "doc_code": HAYA, "src_hash": "h", "translation": "t", "status": "flagged",
                               "engine": eng, "created_at": ST.now()}
            self.assertEqual(ST.store(con, rec("gemini:gemini-2.5-pro")), 1)
            self.assertEqual(ST.store(Racy(con), rec(SONNET)), 2, "numbered again, not lost")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM scholar_translations").fetchone()[0], 2)
            con.close()

    def run_cli(self, db, *extra, env=None):
        e = dict(os.environ, PYTHONIOENCODING="utf-8", **(env or {}))
        return subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db)] + list(extra),
                              capture_output=True, text=True, encoding="utf-8", cwd=str(Path(db).parent), env=e)

    def test_held_ok_and_the_dry_run_of_a_claude_engine(self):
        with tempfile.TemporaryDirectory() as d:
            db = agama_fixture(Path(d), register=[{"doc": HAYA, "status": "in_repair", "reason": "re-translating after the "
                                                   "repair", "at": "2026-10-11T22:50:02"}])
            before = base.md5(db)
            r = self.run_cli(db, "--doc", HAYA, "--engine", SONNET)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("ALSO: --held-ok translates it while it is held from the site", r.stdout)
            r = self.run_cli(db, "--doc", HAYA, "--engine", SONNET + "@medium", "--held-ok", "--no-glossary-adds",
                             "--show-prompt")
            o = r.stdout
            self.assertEqual(r.returncode, 0, o + r.stderr)
            self.assertIn("NOTE: %s is held from the site" % HAYA, o)
            self.assertIn("chosen: 3 verse(s), 21.1 to 21.3", o)
            self.assertIn("the Agamas and Tantras: one rule more (agama-1)", o)
            self.assertIn("the Claude credit: $0.00 spent of $190.00", o)
            self.assertIn("the judge gemini:gemini-2.5-flash and the second judge gemini:gemini-2.5-pro", o)
            self.assertIn("13. AGAMA AND TANTRA.", o)
            self.assertIn("THE EDITION'S APPARATUS ON THIS PAGE", o)
            self.assertIn("NEXT: python scripts\\scholar_translate.py --doc %s --limit 24 --engine %s@medium --held-ok "
                          "--no-glossary-adds --yes --max-usd" % (HAYA, SONNET), o)
            self.assertEqual(base.md5(db), before, "the dry run writes nothing")
            r = self.run_cli(db, "--doc", HAYA, "--engine", SONNET, "--held-ok", "--compare-engine", "anthropic:claude-opus-5-5")
            self.assertEqual(r.returncode, 1); self.assertIn("it is not judged by Claude", r.stdout)
            r = self.run_cli(db, "--doc", HAYA, "--engine", SONNET + "@huge", "--held-ok")
            self.assertEqual(r.returncode, 1); self.assertIn("REFUSE: --engine", r.stdout)
            r = self.run_cli(db, "--doc", HAYA, "--engine", SONNET, "--held-ok", "--yes",
                             env={"ANTHROPIC_API_KEY": "", "GEMINI_API_KEY": ""})
            self.assertEqual(r.returncode, 1, r.stdout); self.assertIn("REFUSE: ANTHROPIC_API_KEY is not set", r.stdout)
            self.assertEqual(base.md5(db), before, "without a key nothing is written")
            r = self.run_cli(db, "--doc", "MBh01", "--pages", "1")
            self.assertNotIn("Claude credit", r.stdout); self.assertNotIn("Agamas", r.stdout)
            self.assertIn("NEXT: python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --yes --max-usd",
                          r.stdout, "the default engine's line as before")


class StubJudge:
    """A judge: reads the letters in the message, ranks them A, B, ... and calls A the best; or answers None."""

    def __init__(self, none=False):
        self.spent, self.con, self.msgs, self.none = 0.0, None, [], none

    def ask(self, kind, m):
        self.msgs.append((kind, m)); self.spent += 0.02
        if self.none:
            return None, 0.02
        import re
        labs = re.findall(r"^TRANSLATION ([A-H]):$", m, re.M)
        return ({L: {"fidelity": 5 - k, "prose": 4, "notes": 3, "errors": []} for k, L in enumerate(labs)}
                | {"ranking": labs, "best": labs[0], "reason": "r"}), 0.02


@unittest.skipUnless(APPLIED, "CLAUDE_ENGINE_2026_10_15 is not applied here")
class TheDuel(unittest.TestCase):
    def fixture(self, d):
        db = agama_fixture(Path(d))
        import db_utils
        con = db_utils.connect(str(db))
        ST.ensure_schema(con)
        allp = ST.load_text(con, HAYA)
        ids = [x["id"] for x in allp[:3]]
        texts = [x["text"] for x in allp[:3]]
        def row(pid, i, eng, tr, g=None, gt=None, at="2026-10-15T10:00:00+00:00", h=None):
            rec = {"passage_id": pid, "doc_code": HAYA, "page_no": 21, "idx": i + 1, "verse_ref": "21.%d" % (i + 1),
                   "src_hash": h or ST.src_hash(texts[i]), "translation": tr, "notes": json.dumps(
                       [{"anchor": "x", "kind": "term", "note": "a note"}]), "doubts": "", "draft": tr, "critique": "[]",
                   "passes": 1, "fidelity": 5, "fluency": 5, "status": "passed", "engine": eng,
                   "judge_engine": ST.JUDGE, "prompt_version": "scholar-v2.1+scholar-critic-v2+agama-1",
                   "cost_usd": 0.05, "created_at": at, "group_ref": g, "group_translation": gt}
            ST.store(con, rec)
        G = "gemini:gemini-2.5-pro"
        row(ids[0], 0, G, "The Lord said: //")
        row(ids[1], 1, G, "These [are] of the Bh\u0101gavatas,", "21.2-21.3", "These are of the Bh\u0101gavatas, and the other. //")
        row(ids[2], 2, G, "and the other. //", "21.2-21.3", "These are of the Bh\u0101gavatas, and the other. //")
        row(ids[0], 0, SONNET, "The Blessed Lord said: //", at="2026-10-15T11:00:00+00:00")
        row(ids[1], 1, SONNET, "These belong to the Bh\u0101gavatas. //", at="2026-10-15T11:00:00+00:00")
        row(ids[2], 2, SONNET, "The other sa\u1e43hit\u0101. //", at="2026-10-15T11:00:00+00:00")
        row(ids[0], 0, "anthropic:claude-opus-5-5", "stale //", at="2026-10-15T12:00:00+00:00", h="0" * 16)
        con.close()
        return db, allp

    def args(self, db, **kw):
        a = types.SimpleNamespace(db=str(db), doc=HAYA, pages=None, from_ref=None, only_page=None, limit=12, engines=None,
                                  judges=",".join(DUEL.JUDGES), max_usd=1.0, redo=False)
        a.__dict__.update(kw)
        return a

    def test_the_spans_follow_the_sentences_and_leave_out_what_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            db, allp = self.fixture(d)
            con = sqlite3.connect(str(db))
            er = DUEL.engine_rows(con, HAYA)
            pos = {x["id"]: i for i, x in enumerate(allp)}
            counts = DUEL.group_counts(con, HAYA)
            engs = sorted(er)
            ub = {e: DUEL.units_for(e, er[e], counts, pos) for e in engs}
            picked = DUEL.pick_verses(self.args(db), allp, er, engs)
            self.assertEqual(picked, [0, 1, 2])
            spans = DUEL.spans_of(picked, allp, ub, engs)
            self.assertEqual(spans, [(0, 0), (1, 2)], "Gemini's sentence 21.2-21.3 is one span for both")
            xs = allp[1:3]
            g = DUEL.engine_text("gemini:gemini-2.5-pro", xs, er, ub)
            s = DUEL.engine_text(SONNET, xs, er, ub)
            self.assertEqual(g["text"], "These are of the Bh\u0101gavatas, and the other. //")
            self.assertEqual(s["text"], "These belong to the Bh\u0101gavatas. // The other sa\u1e43hit\u0101. //")
            self.assertIsNone(DUEL.engine_text("anthropic:claude-opus-5-5", allp[0:1], er, ub), "stale: left out")
            self.assertIsNone(DUEL.engine_text("gemini:gemini-2.5-pro", allp[1:2], er, ub), "half a sentence: not whole")
            self.assertEqual(DUEL.span_ref(xs), "21.2-21.3")
            con.close()

    def test_the_judges_answer_cleaned_and_blind(self):
        c = DUEL.clean_duel({"A": {"fidelity": 4, "prose": 5, "notes": 3, "errors": [{"where": "w", "error": "e",
                                                                                      "severity": "MAJOR"}]},
                             "B": {"fidelity": 5}, "ranking": ["b", "x"], "best": "zz"}, "AB")
        self.assertEqual((c["ranking"], c["best"]), (["B", "A"], "B"))
        self.assertEqual(c["sides"]["A"]["errors"][0]["severity"], "major")
        self.assertIsNone(DUEL.clean_duel({"A": {}, "B": {}}, "AB")); self.assertIsNone(DUEL.clean_duel("x", "AB"))
        self.assertEqual(DUEL.clean_duel({"A": {"fidelity": 4}, "B": {"fidelity": 4}, "best": "Equal"}, "AB")["best"], "equal")
        j = StubJudge()
        texts = {"gemini:gemini-2.5-pro": {"text": "G //", "notes": []}, SONNET: {"text": "S //", "notes": []}}
        v = DUEL.duel_one(j, "gemini:gemini-2.5-pro", "BASE", texts, "seed")
        m = j.msgs[0][1]
        self.assertEqual(j.msgs[0][0], "duel")
        self.assertNotIn("gemini", m); self.assertNotIn("claude", m); self.assertNotIn("anthropic", m)
        self.assertEqual(set(v["labels"].values()), set(texts)); self.assertEqual(v["best"], v["labels"]["A"])
        self.assertEqual(v["ranking"][0], v["labels"]["A"])
        self.assertEqual(DUEL.order_for(texts, "s1"), DUEL.order_for(texts, "s1"), "the same order for the same seed")
        orders = {tuple(DUEL.order_for(texts, "s%d" % k)) for k in range(12)}
        self.assertEqual(len(orders), 2, "both orders occur")

    def test_the_judges_message_has_no_glossary_a_run_grew(self):
        with tempfile.TemporaryDirectory() as d:
            db, allp = self.fixture(d)
            con = sqlite3.connect(str(db))
            con.execute("INSERT INTO scholar_glossary(doc_code, term, rendering, kind, note, source, created_at) VALUES "
                        "(?, 'bh\u0101gavat', 'Bhagavata-SPELLING', 'people', '', 'scholar', 'x')", (HAYA,))
            con.commit()
            allp = [dict(x, iast="bh\u0101gavat\u0101n\u0101\u1e43") for x in allp]
            b = DUEL.judge_base(con, self.args(db), allp, 1, 2, ST.doc_meta(con, HAYA, allp))
            self.assertNotIn("Bhagavata-SPELLING", b)
            self.assertIn("THE VERSES TO TRANSLATE [21.2] to [21.3]", b)
            self.assertIn("THE EDITION'S APPARATUS ON THIS PAGE", b)
            con.close()

    def test_a_run_the_page_and_the_persons_pick(self):
        with tempfile.TemporaryDirectory() as d:
            db, allp = self.fixture(d)
            judges = {}
            keep = DUEL.make_judge
            DUEL.make_judge = lambda eng, a, meta: judges.setdefault(eng, StubJudge())
            os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-a-key")
            try:
                cwd = os.getcwd(); os.chdir(d)
                try:
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA]), 0)            # the dry run
                    con = sqlite3.connect(str(db))
                    self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name='scholar_duels'").fetchone())
                    con.close()
                    self.assertEqual(judges, {}, "the dry run builds no judge")
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--yes", "--max-usd", "1"]), 0)
                    con = sqlite3.connect(str(db))
                    rows = con.execute("SELECT span_ref, judge_engine, best, engines FROM scholar_duels ORDER BY id").fetchall()
                    self.assertEqual([(r[0], r[1]) for r in rows], [("21.1", "gemini:gemini-2.5-pro"),
                                                                    ("21.1", "anthropic:claude-opus-5-5"),
                                                                    ("21.2-21.3", "gemini:gemini-2.5-pro"),
                                                                    ("21.2-21.3", "anthropic:claude-opus-5-5")])
                    self.assertNotIn("anthropic:claude-opus-5-5", rows[0][3], "the stale Opus row is not read")
                    con.close()
                    n = sum(len(j.msgs) for j in judges.values())
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--yes"]), 0)
                    self.assertEqual(sum(len(j.msgs) for j in judges.values()), n, "the same rows are not read again")
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--report"]), 0)
                    page = (Path(d) / "exports" / ("scholar_duel_%s.html" % HAYA)).read_text(encoding="utf-8")
                    self.assertIn("Translation 1", page); self.assertIn("Who made which", page)
                    vis = page.split("<details>")[0]
                    self.assertNotIn("claude-sonnet", vis); self.assertNotIn("gemini-2.5-pro", vis.split("Translation 1")[1])
                    self.assertIn("written by Claude, one of the contestants", page)
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--pick", "21.2-21.3=2,21.9=1", "--by", "D"]), 0)
                    con = sqlite3.connect(str(db))
                    p = con.execute("SELECT judge_engine, best FROM scholar_duels WHERE judge_engine LIKE 'person:%'").fetchall()
                    order = DUEL.person_order(HAYA, "21.2-21.3", json.loads(con.execute(
                        "SELECT row_ids FROM scholar_duels WHERE span_ref='21.2-21.3' ORDER BY id DESC LIMIT 1").fetchone()[0]))
                    self.assertEqual(p, [("person:D", order[1])])
                    con.close()
                    self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--report", "--named"]), 0)
                    page = (Path(d) / "exports" / ("scholar_duel_%s.html" % HAYA)).read_text(encoding="utf-8")
                    self.assertIn("picked</span> by D", page)
                    self.assertIn("The tally (open it after reading)", page)
                finally:
                    os.chdir(cwd)
            finally:
                DUEL.make_judge = keep


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "cost_tracker.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_claude_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_claude_engine_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("scripts/claude_engine.py (CLAUDE_ENGINE_2026_10_15) is not there",
                                                             r.stdout)
            for f in ("claude_engine.py", "scholar_duel.py"):
                shutil.copy2(SCRIPTS / f, t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("CHECK OK: 2 file(s) to write", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_pilotfix_*"))   # PILOT_FIX_2026_10_15 came after (scholar_translate.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "scholar_translate.py"
            p.write_bytes(p.read_bytes().replace(b"            budget_ok = None\n", b"            budget_ok = 0\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("scholar_translate.py: anchor 26 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"CLAUDE_ENGINE", (t / "scripts" / "cost_tracker.py").read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry COST_TRUTH_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "claude_engine.py", SCRIPTS / "scholar_duel.py", SCRIPTS / "patch_claude_engine_2026_10_15.py",
                  Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"CLAUDE_ENGINE_2026_10_15", b)
        if APPLIED:
            for f in ("scholar_translate.py", "cost_tracker.py"):
                self.assertIn(b"CLAUDE_ENGINE_2026_10_15", (SCRIPTS / f).read_bytes(), f)
        self.assertNotIn(b"sk-ant", b"".join((SCRIPTS / f).read_bytes() for f in ("claude_engine.py", "scholar_duel.py")))


if __name__ == "__main__":
    unittest.main()
