# -*- coding: ascii -*-
"""VAMSA_FINDINGS_2026_11_19 (R1 on the dynasties): the pack (its ids, the scholars ranked and capped, Law cited by id
and page); the reply read; the checks that keep a finding from a person's eyes (an id not in the pack, a new link of
one kind of source, a disagreement of one item, a run of 8 words of Law's, the length, the kind); a person's decision
kept; a run with a stand-in client (stored, metered, capped); the review page. No API is called: the client is made
up, the database an in-memory one."""
import io, json, os, sqlite3, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
MARK = "VAMSA_FINDINGS_2026_11_19"
import vamsa_findings as F   # noqa: E402

VAM = {"key": "kuru", "vamsa": "candra", "anchor": "Kuru", "father": "Samvarana", "title": "the Kurus from Kuru",
       "works": ["hv", "agni"], "counts": {"agree": 1, "most": 0, "differ": 1, "one": 0},
       "rows": [
           {"gen": 0, "status": "agree", "name": "Kuru",
            "cells": {"hv": {"name": "Kuru", "ref": "HV 23.107", "words": "kuruh samvaranat", "line": 3},
                      "agni": {"name": "Kuru", "ref": "AgP 277.26", "words": "kuruh samvaranat"}},
            "pui": {"person": "pui:10", "head": "Kuru (II)", "index": ""}},
           {"gen": 1, "status": "differ", "name": "Parikshit",
            "cells": {"hv": {"name": "Parikshit", "ref": "HV 23.109"}, "agni": {"name": "Pariksit"}},
            "pui": {"person": "pui:11", "head": "Pariksit (I)", "index": "agrees"}}]}
INP = {"vamsas": [VAM], "entity_of": {("pui", 10): 100, ("pui", 11): 101}, "canon": {100: "Kuru", 101: "Pariksit"},
       "claim_of": {"phai1923:20:1": {"key": "phai1923:20:1", "printed": "17", "pdf_page": 20, "claim": "Kuru ruled."},
                    "phai1923:21:1": {"key": "phai1923:21:1", "printed": "18", "pdf_page": 21,
                                      "claim": "Pariksit was a Kuru king."}},
       "ray_by_ent": {100: ["phai1923:20:1", "phai1923:21:1"], 101: ["phai1923:21:1"]},
       "law_by_ent": {100: [7], 101: [8]},
       "law_of": {7: {"page": "12", "claim": "The Kurus lived near the Pancalas."}, 8: {"page": "13", "claim": "x"}}}
LAW_PAGE = ("the kurus were a great people who dwelt in the land between the rivers and their kings were famous in "
            "the epic and in the brahmanas of the later vedic age")


class Reply:
    def __init__(self, text, out=900):
        self.content = [types.SimpleNamespace(type="text", text=text)]
        self.usage = types.SimpleNamespace(input_tokens=3000, output_tokens=out, cache_creation_input_tokens=0,
                                           cache_read_input_tokens=0, output_tokens_details=None)
        self.stop_reason = "end_turn"


class Client:
    def __init__(self, text):
        self.text, self.calls = text, []

    def create(self, system, user, max_tokens):
        self.calls.append((system, user, max_tokens))
        return Reply(self.text)


GOOD = json.dumps({"findings": [
    {"kind": "agreement", "text": "The Harivamsa and the Agnipurana both make Kuru the son of Samvarana, as the Purana "
                                  "Index does.", "cites": ["v:hv:HV 23.107", "v:agni:AgP 277.26", "pi:10"]},
    {"kind": "new_link", "text": "Raychaudhuri's Kuru kings and Law's Kurus beside the Pancalas meet the line the "
                                 "texts trace from Kuru.", "cites": ["r:phai1923:21:1", "l:7", "g:0"]},
    {"kind": "new_link", "text": "A tie that rests on one kind of source alone, which the checks must refuse here.",
     "cites": ["g:0", "v:hv:HV 23.107"]},
    {"kind": "disagreement", "text": "The kurus were a great people who dwelt in the land between the rivers, says one.",
     "cites": ["g:1", "l:8"]}]})


class ThePack(unittest.TestCase):
    def test_ids_and_order(self):
        p = F.pack_of(VAM, INP)
        for k in ("g:0", "g:1", "v:hv:HV 23.107", "v:agni:AgP 277.26", "v:hv:HV 23.109", "pi:10", "pi:11",
                  "r:phai1923:20:1", "r:phai1923:21:1", "l:7", "l:8"):
            self.assertIn(k, p["ids"], k)
        self.assertNotIn("v:agni:None", p["ids"], "a cell without a verse has no id")
        self.assertEqual(p["ids"]["l:7"], {"kind": "law", "page": "12"})
        self.assertEqual(p["ids"]["pi:11"], {"kind": "index"})
        t = p["text"]
        self.assertLess(t.index("r:phai1923:21:1"), t.index("r:phai1923:20:1"), "a claim naming two persons first")
        self.assertIn("the Index gives the same father", t)
        self.assertIn("in copyright: paraphrase only", t)
        self.assertEqual(p["counts"]["raychaudhuri"], 2); self.assertEqual(p["counts"]["law"], 2)

    def test_caps(self):
        old = F.RAY_MAX, F.LAW_MAX
        try:
            F.RAY_MAX, F.LAW_MAX = 1, 0
            p = F.pack_of(VAM, INP)
            self.assertEqual((p["counts"]["raychaudhuri"], p["counts"]["law"]), (1, 0))
            self.assertNotIn("LAW,", p["text"])
        finally:
            F.RAY_MAX, F.LAW_MAX = old


class TheChecks(unittest.TestCase):
    def setUp(self):
        self.ids = F.pack_of(VAM, INP)["ids"]
        self.law = F.grams([LAW_PAGE])

    def test_the_reply(self):
        self.assertEqual(len(F.parse_reply("```json\n" + GOOD + "\n```")), 4)
        self.assertEqual(len(F.parse_reply("Here: " + GOOD + " and a correction: {\"findings\": []}")), 0)
        with self.assertRaises(ValueError):
            F.parse_reply("no json")

    def test_each_rule(self):
        fs = F.checked(F.parse_reply(GOOD), self.ids, self.law)
        self.assertEqual([f["status"] for f in fs], ["proposed", "proposed", "refused", "refused"])
        self.assertIn("a new link cites two kinds of source", fs[2]["problems"])
        self.assertIn("a run of 8 words is Law's", fs[3]["problems"])
        p = F.problems({"kind": "agreement", "text": "x" * 50, "cites": ["r:phai1923:99:9"]}, self.ids, self.law)
        self.assertTrue(any(s.startswith("not in the pack") for s in p))
        self.assertIn("a disagreement cites two items",
                      F.problems({"kind": "disagreement", "text": "y" * 50, "cites": ["g:0"]}, self.ids, set()))
        self.assertTrue(F.problems({"kind": "guess", "text": "short", "cites": []}, self.ids, set()))

    def test_a_decision_kept(self):
        first = F.checked(F.parse_reply(GOOD), self.ids, self.law)
        first[0]["status"], first[0]["reviewed_at"] = "approved", "2026-11-19T10:00:00"
        again = F.checked(F.parse_reply(GOOD), self.ids, self.law, first)
        self.assertEqual(again[0]["status"], "approved"); self.assertEqual(again[1]["status"], "proposed")


class TheRun(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.a = types.SimpleNamespace(out=os.path.join(self.td.name, "f"), exports=os.path.join(self.td.name, "x"),
                                       model=F.MODEL, effort=F.EFFORT, max_usd=3.0, again=False, db=":memory:")
        self.con = sqlite3.connect(":memory:")
        self.packs = [F.pack_of(VAM, INP)]

    def tearDown(self):
        self.con.close(); self.td.cleanup()

    def run_it(self, client):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = F.do_run(self.a, self.packs, F.grams([LAW_PAGE]), client=client, con=self.con)
        return rc, buf.getvalue()

    def test_stored_metered_once(self):
        c = Client(GOOD)
        rc, out = self.run_it(c)
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(c.calls), 1); self.assertEqual(c.calls[0][0], F.SYSTEM)
        d = json.loads(Path(self.a.out, "kuru.json").read_text(encoding="utf-8"))
        self.assertEqual(d["prompt_version"], F.PROMPT_VERSION)
        self.assertEqual([f["status"] for f in d["findings"]], ["proposed", "proposed", "refused", "refused"])
        self.assertNotIn("The Kurus lived near the Pancalas.", json.dumps(d), "Law's claims are not stored")
        self.assertNotIn("dwelt in the land between the rivers", json.dumps(d), "nor a run of his words")
        self.assertTrue(d["findings"][3]["withheld"]); self.assertIsNone(d["reply"])
        self.assertEqual(d["findings"][3]["problems"], [F.LAW_RUN])
        self.assertEqual(d["ids"]["l:7"]["page"], "12")
        row = self.con.execute("SELECT kind, doc, engine FROM usage_log").fetchall()
        self.assertEqual(row, [("vamsa_findings", "kuru", "anthropic:" + F.MODEL)])
        self.assertIn("2 finding(s) proposed, 2 refused", out)
        rc, out = self.run_it(Client(GOOD))
        self.assertIn("nothing to read", out)

    def test_the_cap_refuses_up_front(self):
        self.a.max_usd = 0.001
        c = Client(GOOD)
        rc, out = self.run_it(c)
        self.assertEqual(rc, 1); self.assertIn("REFUSE", out); self.assertEqual(c.calls, [])

    def test_decide_and_report(self):
        self.run_it(Client(GOOD))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(F.decide(self.a.out, "kuru:1", "kuru:2"), 0)
            self.assertEqual(F.decide(self.a.out, "kuru:3", ""), 1, "a refused finding cannot be approved")
            F.do_report(self.a, ["kuru"], INP)
        d = json.loads(Path(self.a.out, "kuru.json").read_text(encoding="utf-8"))
        self.assertEqual([f["status"] for f in d["findings"]], ["approved", "dropped", "refused", "refused"])
        md = Path(self.a.exports, "vamsa_findings.md").read_text(encoding="utf-8")
        self.assertIn("1. [approved] agreement:", md)
        self.assertIn("l:7 (Law, p. 12): The Kurus lived near the Pancalas.", md)
        self.assertIn("1 approved, 1 dropped, 2 refused", buf.getvalue())


class TheV2(unittest.TestCase):
    """VAMSA_FINDINGS_V2_2026_11_19: the texts' titles and second names in the pack; the warnings; the three rules."""
    def test_titles_and_second_names(self):
        inp = dict(INP, titles={"hv": "Harivamsa", "agni": "Agnipurana"},
                   aliases={"hv": [(23, "Parikshit", "Pariksita", "HV 23.111", "yam ahuh pariksitam")],
                            "agni": [(1, "Somebody", "Else", "AgP 1.1", "words")]})
        p = F.pack_of(VAM, inp)
        self.assertIn("a:hv:HV 23.111 Parikshit is also called Pariksita: yam ahuh pariksitam", p["text"])
        self.assertEqual(p["ids"]["a:hv:HV 23.111"], {"kind": "text"})
        self.assertNotIn("a:agni:AgP 1.1", p["ids"], "a second name of no one in this dynasty")
        self.assertIn("THE TEXTS: hv = Harivamsa; agni = Agnipurana", p["text"])
        self.assertNotIn("SECOND NAMES", F.pack_of(VAM, INP)["text"])

    def test_warnings(self):
        w = F.warnings({"text": "The Garuda and the Harivamsa make Kuru the son of Samvarana.", "cites": ["v:hv:HV 23.107"]})
        self.assertEqual(w, ["names the garuda but cites none of its verses"])
        self.assertEqual(F.warnings({"text": "The Brahmanda says so.", "cites": ["v:bndp2:BndP 2.3"]}), [])
        self.assertEqual(F.warnings({"text": "The Brahmanda says so.", "cites": ["g:0"]}),
                         ["names the brahmanda but cites none of its verses"])
        self.assertEqual(F.warnings({"text": "The Visnu Purana, book 4, agrees.", "cites": ["a:vipc4:ViPc 4,20.3"]}), [])
        fs = F.checked([{"kind": "agreement", "text": "The Garuda and the Harivamsa make Kuru the son of Samvarana.",
                         "cites": ["v:hv:HV 23.107", "pi:10"]}], F.pack_of(VAM, INP)["ids"], set())
        self.assertEqual((fs[0]["status"], len(fs[0]["warnings"])), ("proposed", 1), "a warning is not a refusal")

    def test_the_rules(self):
        self.assertEqual(F.PROMPT_VERSION, "vamsa-findings-v2")
        for k in ("only when you cite at least one of its verses", 'never say that a scholar "only" or "never"',
                  "the two names are one person"):
            self.assertIn(k, F.SYSTEM, k)


class TheGuards(unittest.TestCase):
    def test_refuses_without_the_alignment(self):
        with tempfile.TemporaryDirectory() as t:
            for f in ("c.db", "k.db"):
                Path(t, f).write_bytes(b"")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = F.main(["--db", str(Path(t, "c.db")), "--kin-db", str(Path(t, "k.db")), "--vamsa-read", t,
                             "--out", str(Path(t, "o"))])
            self.assertEqual(rc, 1); self.assertIn("G6c's alignment", buf.getvalue())

    def test_ascii_and_mark(self):
        for f in (REPO / "scripts" / "vamsa_findings.py", Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name); self.assertIn(MARK.encode(), b)
        self.assertIn("law1926", F.LAW_WORK); self.assertEqual(F.RUN, 8)


if __name__ == "__main__":
    unittest.main()
