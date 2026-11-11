# -*- coding: ascii -*-
"""VAMSA_READ_2026_11_11 (G5a): the dynasties read from the Puranas verse by verse. GRETIL's plain text cut into its
verses (the markers, several on a line; the book and the chapters asked for; the colophons and the speakers' marks out),
in chapter parts; the plan and its estimate (free); a run with a stubbed Claude (nothing is sent): each statement
checked against its verse (verified, words, unsupported, bad), the reply stored, the call metered as kind vamsa_read;
the cap and the credit stop a run before it sends; a failed call is stored and read again later; --reparse, --report
(the CSV, the longest father-to-son line). Temp folders only."""
import argparse, csv, io, json, os, sqlite3, sys, tempfile, types, unittest, zipfile
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import vamsa_read as VR      # noqa: E402
import claude_engine as CE   # noqa: E402

MARK = "VAMSA_READ_2026_11_11"   # and VAMSA_HEAL_2026_11_11
S, M = "\u1e63", "\u0101"    # s with dot below, a with macron
IK, VI = "ik%sv%sku" % (S, M), "vikuk%si" % S
TEXT = "\n".join([
    "Vi%s%spur%s%sa" % (S, "\u1e47", M, "\u1e47"),
    "tato jayam udirayet // vip_3,18.104 //",
    "atha caturth%s%s%sa%s pr%srabhyate" % (M, "\u1e43", "\u015b", "\u1e25", M),
    "maitreya uv%sca" % M,
    "bhagavan va%s%sa%s r%sj%s%s%s bruhi me guro // vip_4,1.1 //" % ("\u1e43", "\u015b", "\u1e43", M, "\u00f1", M, "\u1e43"),
    "mano%s putra ik%sv%sku%s // vip_4,1.2 //tasya putro vikuk%si%s // vip_4,1.3 //" % (
        "\u1e25", S, M, "\u1e25", S, "\u1e25"),
    "iti %sr%svi%s%supur%s%se caturth%s%se prathamodhy%sya%s (1)" % ("\u015b", "\u012b", S, "\u1e47", M, "\u1e47", M,
                                                                 "\u015b", M, "\u1e25"),
    "vip_4,2.1/0 %sr%spar%s%sara uv%sca" % ("\u015b", "\u012b", M, "\u015b", M),
    "vikuk%se%s putra%s kakutstha%s // vip_4,2.1 //" % (S, "\u1e25", "\u1e25", "\u1e25"),
    "bhagavan &amp; vi%s%su%s // vip_5,1.1 //" % (S, "\u1e47", "\u1e25"),
])


def msg(text, inp=3000, out=2000, stop="end_turn"):
    return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=text)], stop_reason=stop,
                                 usage=types.SimpleNamespace(input_tokens=inp, output_tokens=out,
                                                             cache_creation_input_tokens=0, cache_read_input_tokens=0,
                                                             output_tokens_details=types.SimpleNamespace(thinking_tokens=0)))


class FakeSDK:
    """anthropic, as far as claude_engine.Client uses it."""

    def __init__(self, answers):
        self.answers, self.requests = list(answers), []
        sdk = self

        class _Stream:
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
                return _Stream()

        class Anthropic:
            def __init__(self, **kw):
                self.messages = _Messages()

        self.Anthropic = Anthropic


R1 = json.dumps({"statements": [
    {"ref": "ViP 4,1.2", "a": "Ik%sv%sku" % (S, M), "rel": "son_of", "b": "Manu", "words": "mano\u1e25 putra ik%sv%sku\u1e25"
     % (S, M), "doubt": False},
    {"ref": "ViP 4,1.3", "a": "Vikuk%si" % S, "rel": "son_of", "b": "Ik%sv%sku" % (S, M), "words": "tasya putro vikuk%si\u1e25"
     % S, "doubt": False},
    {"ref": "ViP 4,1.3", "a": "Kakutstha", "rel": "son_of", "b": "Vikuk%si" % S, "words": "putra\u1e25 kakutstha\u1e25"},
    {"ref": "ViP 9,9.9", "a": "X", "rel": "son_of", "b": "Y", "words": "x"},
    {"ref": "ViP 4,1.2", "a": "Iksvaku", "rel": "son_of", "b": "Manu", "words": "putra ik%sv%sku\u1e25" % (S, M)}]},
    ensure_ascii=False)
R2 = "```json\n" + json.dumps({"statements": [
    {"ref": "ViP 4,2.1", "a": "Kakutstha", "rel": "son_of", "b": "Vikuk%si" % S,
     "words": "vikuk%se\u1e25 putra\u1e25 kakutstha\u1e25" % S}]}, ensure_ascii=False) + "\n```"


class Base(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-not-a-key"
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.zip = t / "g.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("1_sanskr/tei/transformations/plaintext/sa_viSNupurANa.txt", TEXT)
        import cost_tracker
        self.db = t / "u.db"
        con = sqlite3.connect(str(self.db))
        cost_tracker.ensure_usage_schema(con)
        con.close()
        self.a = argparse.Namespace(work="vip4", chapters="", yes=True, max_usd=8.0, model=VR.MODEL, effort="medium",
                                    db=str(self.db), zip=str(self.zip), out=str(t / "out"), exports=str(t / "ex"),
                                    reparse=False, report=False)

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()

    def run_with(self, answers, a=None):
        a = a or self.a
        sdk = FakeSDK(answers)
        client = CE.Client(a.model, a.effort, sdk=sdk)
        con = sqlite3.connect(str(self.db))
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = VR.do_run(a, VR.plan_units(a), client=client, con=con)
        finally:
            con.close()
        return rc, buf.getvalue(), sdk

    def cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = VR.main(["--zip", str(self.zip), "--db", str(self.db), "--out", self.a.out, "--exports", self.a.exports,
                          "--work", "vip4"] + list(argv))
        return rc, buf.getvalue()


class TheText(Base):
    def test_the_verses_of_the_book(self):
        vs = VR.verses_of("vip4", TEXT)
        self.assertEqual([r for _c, _v, r, _t in vs], ["ViP 4,1.1", "ViP 4,1.2", "ViP 4,1.3", "ViP 4,2.1"])
        last = vs[-1][3]
        self.assertTrue(last.endswith("kakutstha\u1e25"), last)
        self.assertNotIn("iti ", last); self.assertNotIn("vip_4,2.1/0", last)
        self.assertEqual(vs[2][3], "tasya putro vikuk%si\u1e25" % S, "the second marker on one line")
        us = VR.chunks(vs)
        self.assertEqual([(u["chapter"], u["part"], len(u["verses"])) for u in us], [(1, 0, 3), (2, 0, 1)])
        small = VR.chunks(vs, size=30)
        self.assertEqual([VR.unit_name(u) for u in small], ["01_1", "01_2", "01_3", "02"])
        self.assertIn("[ViP 4,1.2] mano\u1e25 putra", VR.user_message("vip4", us[0]))

    def test_the_plan_is_free(self):
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 2 part(s) to read, about $", out)
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work vip4 --chapters 1-2 --yes", out)
        self.assertFalse(Path(self.a.out).exists(), "nothing written")
        rc, out = self.cli("--chapters", "2")
        self.assertIn("VERDICT: 1 part(s) to read", out)
        rc, out = self.cli("--chapters", "two")
        self.assertEqual(rc, 1); self.assertIn("REFUSE: chapters", out)


class TheRun(Base):
    def test_read_checked_stored_metered(self):
        rc, out, sdk = self.run_with([msg(R1), msg(R2)])
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(sdk.requests), 2)
        self.assertEqual(sdk.requests[0]["system"], VR.SYSTEM)
        self.assertIn("[ViP 4,1.3] tasya putro", sdk.requests[0]["messages"][0]["content"])
        self.assertEqual(sdk.requests[0]["output_config"], {"effort": "medium"})
        d = json.loads((Path(self.a.out) / "vip4" / "01.json").read_text(encoding="utf-8"))
        self.assertEqual([s["check"] for s in d["statements"]], ["verified", "verified", "unsupported", "bad", "verified"])
        self.assertEqual(d["prompt_version"], VR.PROMPT_VERSION)
        self.assertIn("CC BY-NC-SA 4.0", d["source"])
        self.assertEqual(d["refs"], ["ViP 4,1.1", "ViP 4,1.2", "ViP 4,1.3"])
        d2 = json.loads((Path(self.a.out) / "vip4" / "02.json").read_text(encoding="utf-8"))
        self.assertEqual([s["check"] for s in d2["statements"]], ["verified"], "a fenced reply is read")
        con = sqlite3.connect(str(self.db))
        rows = con.execute("SELECT kind, doc, engine, passages FROM usage_log ORDER BY id").fetchall()
        con.close()
        self.assertEqual(rows, [("vamsa_read", "vip4", "anthropic:" + VR.MODEL, 3), ("vamsa_read", "vip4", "anthropic:" + VR.MODEL, 1)])
        self.assertIn("VERDICT: 2 part(s) read, 6 statements, 4 verified (66%)", out)
        rc, out, sdk = self.run_with([])
        self.assertEqual(sdk.requests, [], "read once")
        self.assertIn("VERDICT: nothing to read", out)

    def test_the_report_and_the_line(self):
        self.run_with([msg(R1), msg(R2)])
        rc, out = self.cli("--report")
        self.assertEqual(rc, 0, out)
        self.assertIn("a line of 4: Manu > Ik%sv%sku > Vikuk%si > Kakutstha" % (S, M, S), out)
        with open(Path(self.a.exports) / "vamsa_read_vip4.csv", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["chapter", "ref", "a", "rel", "b", "words", "doubt", "check"])
        self.assertEqual(len(rows), 7)

    def test_reparse_is_free_and_the_same(self):
        self.run_with([msg(R1), msg(R2)])
        p = Path(self.a.out) / "vip4" / "01.json"
        before = json.loads(p.read_text(encoding="utf-8"))["statements"]
        rc, out = self.cli("--reparse")
        self.assertIn("VERDICT: 2 stored repl(ies) parsed and checked again, 0 not read (free)", out)
        self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["statements"], before)

    def test_the_cap_and_the_credit_stop_it_before_it_sends(self):
        a = argparse.Namespace(**dict(vars(self.a), max_usd=0.0001))
        rc, out, sdk = self.run_with([msg(R1)], a)
        self.assertEqual(rc, 1); self.assertIn("REFUSE: the estimate is $", out); self.assertEqual(sdk.requests, [])
        os.environ["SA_CLAUDE_CREDIT_USD"] = "0.0001"
        rc, out, sdk = self.run_with([msg(R1)])
        self.assertEqual(sdk.requests, []); self.assertIn("stopped: the Claude credit", out)
        self.assertIn("VERDICT: 0 part(s) read", out)

    def test_a_failed_call_is_kept_and_read_again(self):
        rc, out, sdk = self.run_with([RuntimeError("overloaded")])
        self.assertIn("the API did not answer (RuntimeError: overloaded)", out)
        d = json.loads((Path(self.a.out) / "vip4" / "01.json").read_text(encoding="utf-8"))
        self.assertIn("overloaded", d["error"])
        rc, out, sdk = self.run_with([msg("I cannot help with that."), msg(R2)])
        self.assertEqual(len(sdk.requests), 2, "the failed part asked again")
        d = json.loads((Path(self.a.out) / "vip4" / "01.json").read_text(encoding="utf-8"))
        self.assertIn("no JSON object", d["error"])
        self.assertFalse(VR.done(self.a.out, "vip4", VR.plan_units(self.a)["vip4"][0]))

    def test_the_checks(self):
        u = {"verses": [("R1", "mano\u1e25 putra ik%sv%sku\u1e25" % (S, M)), ("R2", "tasya putro vikuk%si\u1e25" % S)]}
        order = ["R1", "R2"]
        refs = dict(u["verses"])
        ok = {"ref": "R2", "a": VI, "rel": "son_of", "b": IK, "words": "putro vikuk%si\u1e25" % S}
        self.assertEqual(VR.check(ok, refs, order), "verified", "the father named in the verse before")
        self.assertEqual(VR.check(dict(ok, rel="cousin_of"), refs, order), "bad")
        self.assertEqual(VR.check(dict(ok, b="Rama"), refs, order), "words")
        self.assertEqual(VR.check(dict(ok, words="ramasya putra"), refs, order), "unsupported")
        self.assertEqual(VR.check(dict(ok, ref="R1", words="putra ik%sv%sku\u1e25 tasya" % (S, M)), refs, order),
                         "verified", "words running into the next verse")


class TheHeal(unittest.TestCase):
    """VAMSA_HEAL_2026_11_11: what the first run of 11 Nov showed."""

    def test_a_reply_that_corrects_itself(self):
        r = ('{"statements": [{"ref": "R1", "a": "X", "rel": "son_of", "b": "Y", "words": "x"}]}\n\nCorrection: the '
             'last is not valid. A corrected reply follows.\n\n{"statements": [{"ref": "R1", "a": "Z"}]}')
        self.assertEqual([s["a"] for s in VR.parse_reply(r)], ["Z"])
        self.assertEqual(VR.parse_reply(r + '\n\nFinal answer:\n\n{"statements": []}'), [])
        self.assertRaises(ValueError, VR.parse_reply, "no JSON here")
        self.assertRaises(ValueError, VR.parse_reply, '{"other": 1}')

    def test_a_statement_without_its_reference(self):
        u = {"verses": [("R1", "mano\u1e25 putra ik%sv%sku\u1e25" % (S, M)), ("R2", "tasya putro vikuk%si\u1e25" % S)]}
        got = VR.checked([{"a": VI, "rel": "son_of", "b": IK, "words": "tasya putro vikuk%si\u1e25" % S}], u)
        self.assertEqual((got[0]["ref"], got[0].get("ref_from"), got[0]["check"]), ("R2", "words", "verified"))
        got = VR.checked([{"verse": "R1", "a": IK, "rel": "son_of", "b": "Manu", "words": "putra ik%sv%sku" % (S, M)}], u)
        self.assertEqual((got[0]["ref"], got[0]["check"]), ("R1", "verified"))

    def test_sandhi_and_words_left_out(self):
        L = VR.letters
        v = "tato da\u015b\u0101rho n\u0101mn\u0101bh\u016bt tasya vyoma\u1e25 sutastata\u1e25"
        self.assertTrue(VR.words_in("tasya vyoma\u1e25 suta\u1e25", L(v)))
        v2 = ("paurav\u012b rohi\u1e47\u012b bhadr\u0101 madir\u0101 rocan\u0101 il\u0101 / devak\u012bpramukh"
              "\u0101\u015bc\u0101san patnya \u0101nakadundubhe\u1e25")
        self.assertTrue(VR.words_in("madir\u0101 rocan\u0101 ... patnya \u0101nakadundubhe\u1e25", L(v2)))
        self.assertFalse(VR.words_in("patnya \u0101nakadundubhe\u1e25 ... madir\u0101 rocan\u0101", L(v2)), "in order")
        self.assertFalse(VR.words_in("r\u0101masya putra\u1e25", L(v)))
        self.assertFalse(VR.words_in("x", L(v)), "too short to tell")

    def test_homonyms_kept_apart_and_a_mother_is_no_father(self):
        sr = "S\u1e5b\u00f1jaya"
        st = [dict(ref="R1", a="Dh\u016bmr\u0101k\u1e63a", rel="son_of", b="Candra", check="verified", chapter=1),
              dict(ref="R2", a=sr, rel="son_of", b="Dh\u016bmr\u0101k\u1e63a", check="verified", chapter=1),
              dict(ref="R3", a="Sahadeva", rel="son_of", b=sr, check="verified", chapter=1),
              dict(ref="R9", a="Pura\u00f1jaya", rel="son_of", b=sr, check="verified", chapter=19),
              dict(ref="R10", a="\u1e5ak\u1e63a", rel="son_of", b="Pura\u00f1jaya", check="verified", chapter=19),
              dict(ref="R11", a="Pur\u016bravas", rel="son_of", b="Il\u0101", check="verified", chapter=1),
              dict(ref="R12", a="Il\u0101", rel="wife_of", b="Budha", check="verified", chapter=1),
              dict(ref="R13", a="X", rel="son_of", b="Y", check="unsupported", chapter=1)]
        lines = [[n for n, _r, _w in ln] for ln in VR.lines_of(st)]
        self.assertEqual(lines[0], ["Candra", "Dh\u016bmr\u0101k\u1e63a", sr, "Sahadeva"])
        self.assertIn([sr, "Pura\u00f1jaya", "\u1e5ak\u1e63a"], lines, "the Srnjaya of chapter 19 is another")
        self.assertFalse(any("Il\u0101" in ln for ln in lines), "a mother is not a father")
        self.assertFalse(any("X" in ln for ln in lines), "only verified statements")
        by_name = VR.longest_lines_by_name(st)
        self.assertEqual(len(by_name[0]), 5, "the first report merged them: Candra > ... > Srnjaya > Puranjaya > Rksa")


class TheFile(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "vamsa_read.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(b.isascii(), p.name)
            self.assertIn(MARK.encode(), b, p.name)


if __name__ == "__main__":
    unittest.main()
