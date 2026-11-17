# -*- coding: ascii -*-
"""VAMSA_G6B_READY_2026_11_16. After the trial of 15 and 16 Nov (the Harivamsa 9-10, the Mahabharata 1.90), before the
whole reading of G6 is bought: the works of G6 are read with a second prompt (born_of the mother, begotten_by a begetter
whose child the text counts as another man's), G5a's three keep the first and are not read again, the first reading of a
part read again is kept beside it; a name is found by its words, through an avagraha and two verses back; a statement
whose words are in another verse takes that verse; a mother is never a father in a line; --chapters that name nothing
here is refused; every NEXT carries --work. A stubbed Claude: nothing is sent. Temp folders only."""
import argparse, io, json, sqlite3, subprocess, sys, tempfile, unittest, zipfile
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import vamsa_read as VR                    # noqa: E402
import claude_engine as CE                 # noqa: E402
import test_vamsa_read_2026_11_11 as T0    # noqa: E402  (its stubbed SDK, its message, its Visnu)
import test_vamsa_g6a_2026_11_15 as G      # noqa: E402  (its small texts in the files' shapes)

MARK = "VAMSA_G6B_READY_2026_11_16"


def st(ref, a, rel, b, words, check="verified"):
    return {"ref": ref, "a": a, "rel": rel, "b": b, "words": words, "doubt": False, "check": check, "chapter": 1}


class ThePrompts(unittest.TestCase):
    def test_g5a_keeps_the_first_g6_has_the_second(self):
        self.assertEqual(VR.prompt_of("vip4"), (VR.PROMPT_VERSION, VR.SYSTEM))
        self.assertEqual(VR.prompt_of("bhp9")[0], "vamsa-read-v1")
        self.assertEqual(VR.prompt_of("hv"), ("vamsa-read-v2", VR.SYSTEM_G6))
        self.assertEqual(VR.prompt_of("mbh1")[0], "vamsa-read-v2")
        for w in ("born_of", "begotten_by", "niyoga", "Never a mother", "Manu Vaivasvata"):
            self.assertIn(w, VR.SYSTEM_G6, w)
        self.assertNotIn("born_of", VR.SYSTEM)
        self.assertIn("born_of", VR.RELS); self.assertIn("begotten_by", VR.RELS)
        self.assertEqual(VR.RELS[:9], ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded",
                                       "descendant_of", "line_of", "other"), "the first nine as before")
        self.assertNotIn("\\u", VR.SYSTEM_G6, "its IAST is letters, not escapes")
        self.assertIn("Ik\u1e63v\u0101ku", VR.SYSTEM_G6)

    def test_spans(self):
        self.assertEqual(VR.spans([2, 3, 9, 10, 15, 23, 24, 25, 98, 99]), "2-3, 9-10, 15, 23-25, 98-99")
        self.assertEqual(VR.spans([]), "")


class TheChecks(unittest.TestCase):
    def setUp(self):
        self.u = {"verses": [
            ("R1", "manor vaivasvatasy\u0101san putr\u0101 vai nava tatsam\u0101\u1e25 ik\u1e63v\u0101ku\u015b caiva n\u0101bh\u0101ga\u015b ca"),
            ("R2", "kuval\u0101\u015bvasya putr\u0101\u1e47\u0101m ekavi\u1e43\u015batisahasrakam"),
            ("R3", "arugv\u0101n khalu m\u0101gadh\u012bm upayeme 'm\u1e5bt\u0101\u1e43 n\u0101ma"),
            ("R4", "tasya putr\u0101s traya\u1e25 \u015bi\u1e63\u1e6d\u0101 d\u1e5b\u1e0dh\u0101\u015bvo bhadr\u0101\u015bva eva ca"),
            ("R5", "anyad eva tu kathyate"),
            ("R6", "tasya putro mah\u0101bala\u1e25 sudhanv\u0101 n\u0101ma")]}
        self.refs = dict(self.u["verses"]); self.order = [r for r, _t in self.u["verses"]]

    def c(self, ref, a, b, words, rel="son_of"):
        return VR.check({"ref": ref, "a": a, "rel": rel, "b": b, "words": words}, self.refs, self.order)

    def test_a_name_with_the_word_that_tells_it_apart(self):
        self.assertEqual(self.c("R1", "Ik\u1e63v\u0101ku", "Manu Vaivasvata", "manor vaivasvatasy\u0101san putr\u0101"), "verified")
        self.assertEqual(self.c("R1", "Ik\u1e63v\u0101ku", "Manu S\u0101var\u1e47i", "manor vaivasvatasy\u0101san putr\u0101"), "verified",
                         "one word of the name is enough: the stem key of Manu")
        self.assertEqual(self.c("R1", "Ik\u1e63v\u0101ku", "R\u0101ma J\u0101madagnya", "manor vaivasvatasy\u0101san putr\u0101"), "words")

    def test_an_avagraha(self):
        self.assertEqual(self.c("R3", "Am\u1e5bt\u0101", "Arugv\u0101n", "arugv\u0101n khalu m\u0101gadh\u012bm upayeme 'm\u1e5bt\u0101\u1e43", "wife_of"), "verified")

    def test_a_pronoun_two_verses_back_not_three(self):
        self.assertEqual(self.c("R4", "D\u1e5b\u1e0dh\u0101\u015bva", "Kuval\u0101\u015bva", "tasya putr\u0101s traya\u1e25 \u015bi\u1e63\u1e6d\u0101 d\u1e5b\u1e0dh\u0101\u015bvo"), "verified")
        self.assertEqual(self.c("R6", "Sudhanvan", "Kuval\u0101\u015bva", "tasya putro mah\u0101bala\u1e25 sudhanv\u0101"), "words",
                         "four verses back is too far")

    def test_words_in_another_verse_take_it(self):
        got = VR.checked([{"ref": "R4", "a": "Am\u1e5bt\u0101", "rel": "wife_of", "b": "Arugv\u0101n",
                           "words": "arugv\u0101n khalu m\u0101gadh\u012bm upayeme 'm\u1e5bt\u0101\u1e43"}], self.u)[0]
        self.assertEqual((got["ref"], got.get("ref_cited"), got.get("ref_from"), got["check"]),
                         ("R3", "R4", "words", "verified"))
        got = VR.checked([{"ref": "R4", "a": "X", "rel": "son_of", "b": "Y", "words": "nowhere at all here"}], self.u)[0]
        self.assertEqual((got["ref"], got.get("ref_cited"), got["check"]), ("R4", None, "unsupported"))
        self.assertTrue(VR.words_at("tasya putr\u0101s traya\u1e25", self.refs, self.order, "R4"))
        self.assertFalse(VR.words_at("tasya putr\u0101s traya\u1e25", self.refs, self.order, "R9"))


class TheLines(unittest.TestCase):
    def names(self, statements):
        return [[n for n, _r, _w in ln] for ln in VR.lines_of(statements)]

    def test_a_mother_said_once_in_words_only(self):
        s = [st("R1", "Bh\u012bmasena", "son_of", "Suya\u015b\u0101", "x"), st("R1", "Suya\u015b\u0101", "wife_of", "Parik\u1e63it", "y", "words"),
             st("R2", "Parya\u015bravas", "son_of", "Bh\u012bmasena", "z")]
        self.assertFalse(any("Suya\u015b\u0101" in ln for ln in self.names(s)))

    def test_two_parents_in_one_verse(self):
        s = [st("R1", "Ilina", "son_of", "Ta\u1e43su", "a"), st("R2", "Du\u1e25\u1e63anta", "son_of", "Ilina", "b"),
             st("R2", "Du\u1e25\u1e63anta", "son_of", "Ratha\u1e43tar\u012b", "c"), st("R3", "Bharata", "son_of", "Du\u1e25\u1e63anta", "d")]
        lines = self.names(s)
        self.assertEqual(lines[0], ["Ta\u1e43su", "Ilina", "Du\u1e25\u1e63anta", "Bharata"])
        self.assertFalse(any("Ratha\u1e43tar\u012b" in ln for ln in lines))

    def test_born_of_and_begotten_by(self):
        s = [st("R1", "P\u0101\u1e47\u1e0du", "son_of", "Vicitrav\u012brya", "a"), st("R1", "P\u0101\u1e47\u1e0du", "begotten_by", "Dvaip\u0101yana", "a"),
             st("R1", "P\u0101\u1e47\u1e0du", "born_of", "Amb\u0101lik\u0101", "a"), st("R2", "Arjuna", "son_of", "P\u0101\u1e47\u1e0du", "b"),
             st("R2", "Arjuna", "begotten_by", "\u015aakra", "b"), st("R2", "Arjuna", "born_of", "Kunt\u012b", "b"),
             st("R3", "X", "son_of", "Kunt\u012b", "c")]
        lines = self.names(s)
        self.assertEqual(lines[0], ["Vicitrav\u012brya", "P\u0101\u1e47\u1e0du", "Arjuna"])
        self.assertFalse(any(n in ln for ln in lines for n in ("Dvaip\u0101yana", "\u015aakra", "Kunt\u012b", "Amb\u0101lik\u0101")))


class TheDesk(G.TheDesk):
    """The fixture of G6a's desk: its small texts zipped, a usage database."""

    def test_the_plan_names_a_trial_that_exists(self):
        pass

    def test_a_group_reads_what_is_here_or_says_what_is_not(self):
        pass

    def test_show_and_verses_are_free(self):
        pass

    def test_a_reading_of_the_harivamsa_stubbed(self):
        pass

    def args(self, **kw):
        d = dict(work="hv", chapters="9", yes=True, max_usd=8.0, model=VR.MODEL, effort="medium", db=str(self.db),
                 zip=str(self.zip), out=self.out, exports=str(self.t / "ex"), reparse=False, report=False, show=0,
                 verses=False)
        d.update(kw)
        return argparse.Namespace(**d)

    def run_with(self, answers, a):
        sdk = T0.FakeSDK(answers)
        con = sqlite3.connect(str(self.db))
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = VR.do_run(a, VR.plan_units(a), client=CE.Client(a.model, a.effort, sdk=sdk), con=con)
        finally:
            con.close()
        return rc, buf.getvalue(), sdk

    def test_a_first_reading_is_read_again_and_kept(self):
        p = Path(self.out) / "hv" / "09.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"chapter": 9, "prompt_version": "vamsa-read-v1", "reply": "{}",
                                 "statements": [{"ref": "HV 9.1", "a": "A", "rel": "son_of", "b": "B", "words": "w",
                                                 "check": "words"}]}), encoding="utf-8")
        a = self.args()
        self.assertFalse(VR.done(self.out, "hv", VR.plan_units(a)["hv"][0]), "a v1 reading of a work of G6 is read again")
        reply = json.dumps({"statements": [
            {"ref": "HV 9.1", "a": "Ik\u1e63v\u0101ku", "rel": "son_of", "b": "Manu Vaivasvata",
             "words": "manor vaivasvatasy\u0101san putr\u0101"},
            {"ref": "HV 9.1", "a": "Ik\u1e63v\u0101ku", "rel": "born_of", "b": "\u015araddh\u0101", "words": "manor vaivasvatasy\u0101san"}]},
            ensure_ascii=False)
        rc, out, sdk = self.run_with([T0.msg(reply)], a)
        self.assertEqual(rc, 0, out)
        self.assertEqual(sdk.requests[0]["system"], VR.SYSTEM_G6)
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(d["prompt_version"], "vamsa-read-v2")
        self.assertEqual([s["check"] for s in d["statements"]], ["verified", "words"])
        kept = p.with_name("09.json.vamsa-read-v1")
        self.assertEqual(json.loads(kept.read_text(encoding="utf-8"))["prompt_version"], "vamsa-read-v1")
        self.assertEqual(len(VR.records(self.out, "hv")), 1, "the kept reading is not read as a record")
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv --report", out)
        rc, out, sdk = self.run_with([], a)
        self.assertEqual(sdk.requests, [], "read once")
        self.assertTrue(VR.done(self.out, "hv", VR.plan_units(a)["hv"][0]))

    def test_g5a_reading_is_not_read_again(self):
        u = {"chapter": 1, "part": 0}
        p = Path(self.out) / "vip4" / "01.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"prompt_version": "vamsa-read-v1", "statements": []}), encoding="utf-8")
        self.assertTrue(VR.done(self.out, "vip4", u))
        self.assertIsNone(VR.keep_before(self.out, "vip4", u, "vamsa-read-v1"))

    def test_chapters_that_are_not_there(self):
        rc, out = self.cli("--work", "hv", "--chapters", "1-2", "--yes")
        self.assertEqual(rc, 1, out)
        self.assertIn("REFUSE: chapters 1-2: none of them is here; the chapters: hv 9-10", out)
        self.assertNotIn("nothing to read", out)
        rc, out = self.cli("--work", "mbh1", "--chapters", "3-9", "--show", "2")
        self.assertIn("REFUSE: chapters 3-9: none of them is here; the chapters: mbh1 90", out)

    def test_next_carries_the_work(self):
        rc, out = self.cli("--work", "hv", "--report")
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv   (the plan: what is left to read)", out)
        p = Path(self.out) / "hv" / "09.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"chapter": 9, "prompt_version": "vamsa-read-v2", "statements": []}), encoding="utf-8")
        rc, out = self.cli("--work", "hv", "--chapters", "9", "--show", "1")
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv   (all that was asked is read: the plan of the whole)",
                      out)
        self.assertNotIn("--chapters 1-2", out)
        rc, out = self.cli("--work", "hv", "--chapters", "9", "--yes")
        self.assertIn("VERDICT: nothing to read: every part asked for is read", out)
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv --report", out)
        rc, out = self.cli("--work", "hv")
        self.assertIn("NEXT: python scripts\\vamsa_read.py --work hv --chapters 10 --yes   (a trial)", out)


PAT = REPO / "scripts" / "patch_vamsa_g6b_ready_2026_11_16.py"
FILES = ("scripts/vamsa_read.py", "tests/test_vamsa_g6a_2026_11_15.py")


@unittest.skipUnless(PAT.exists(), "patch_vamsa_g6b_ready_2026_11_16.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vamsag6b_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(FILES), r.stdout, r.stdout + r.stderr)
            self.assertEqual(run().returncode, 0)
            for rel in FILES:
                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


class TheFile(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "vamsa_read.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(b.isascii(), p.name)
            self.assertIn(MARK.encode(), b, p.name)


if __name__ == "__main__":
    unittest.main()
