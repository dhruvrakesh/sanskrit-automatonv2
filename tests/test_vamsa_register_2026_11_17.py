# -*- coding: ascii -*-
"""VAMSA_REGISTER_2026_11_17 (G6d). One register of the persons of every work read: one person in two works joined
when his names, his father and (where both give him) his grandfather meet; never two whose grandfathers differ, nor
through a third; a son named by "words" taken as a father when a verified statement names him so, so that one name of
two persons stays two (the two Parikshits of the Adiparvan); two names said in a verse give one entry both; two names
in one generation between one father and one son are proposed, never joined. Free and read-only. Temp folders only."""
import hashlib, io, json, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vamsa_align as VA        # noqa: E402
import vamsa_register as R      # noqa: E402

MARK = "VAMSA_REGISTER_2026_11_17"
PK = "Parik\u1e63it"


def st(a, rel, b, ch=90, ref=None, check="verified", words="tasya putra\u1e25"):
    return {"ref": ref or "R %d" % ch, "a": a, "rel": rel, "b": b, "words": words, "doubt": False, "check": check,
            "chapter": ch}


ADI = [st(PK, "son_of", "Arugv\u0101n", ref="M 43"), st("Bh\u012bmasena", "son_of", PK, ref="M 44"),
       st("Abhimanyu", "son_of", "Arjuna", ref="M 85"),
       st(PK, "son_of", "Abhimanyu", ref="M 90", check="words", words="tasy\u0101m asya par\u0101sur garbho 'j\u0101yata"),
       st("Janamejaya", "son_of", PK, ref="M 93")]
BHP = [st("Abhimanyu", "son_of", "Arjuna", ch=22, ref="B 33"), st("Par\u012bk\u1e63it", "son_of", "Abhimanyu", ch=22, ref="B 34"),
       st("Janamejaya", "son_of", "Par\u012bk\u1e63it", ch=22, ref="B 35")]
VIP = [st("Par\u012bk\u1e63it", "son_of", "Kuru", ch=20, ref="V 1"), st("Janamejaya", "son_of", "Par\u012bk\u1e63it", ch=20, ref="V 2")]
LONE = [st("Janamejaya", "son_of", "Par\u012bk\u1e63it", ch=5, ref="L 1")]


class TheWork(unittest.TestCase):
    def test_the_two_parikshits_stay_two(self):
        n = R.nodes_of("mbh1", ADI)
        jan = [x for x in n.values() if x["name"] == "Janamejaya"][0]
        self.assertEqual(jan["grand"], "Abhimanyu", "Abhimanyu's Parikshit, not Arugvan's")
        lifted = [x for x in n.values() if x["father"] == "Abhimanyu"][0]
        self.assertEqual(lifted["rests"], "words")
        self.assertEqual(len([x for x in n.values() if x["name"] == PK]), 2)

    def test_words_alone_make_no_person(self):
        n = R.nodes_of("mbh1", [ADI[2], ADI[3]])
        self.assertFalse([x for x in n.values() if x["father"] == "Abhimanyu"], "no son named him a father")


class TheRegister(unittest.TestCase):
    def build(self, works, extra=None):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "data" / "vamsa_read"
            for w, sts in works.items():
                (out / w).mkdir(parents=True)
                by = {}
                for s in sts:
                    by.setdefault(s["chapter"], []).append(s)
                for ch, ss in by.items():
                    (out / w / ("%02d_1.json" % ch)).write_text(json.dumps({"chapter": ch, "statements": ss},
                                                                         ensure_ascii=False), encoding="utf-8")
            return R.build(out, list(works))

    def entry(self, reg, name, father):
        return [e for e in reg["entries"] if VA.same(e["name"], name) and any(
            VA.same(p["father"], father) for p in e["persons"])]

    def test_joined_by_grandfather_and_kept_apart(self):
        reg = self.build({"mbh1": ADI, "bhp9": BHP, "vip4": VIP})
        jan = [e for e in reg["entries"] if e["name"] == "Janamejaya"]
        self.assertEqual(len(jan), 2)
        a = [e for e in jan if "mbh1" in e["works"]][0]
        self.assertEqual(sorted(a["works"]), ["bhp9", "mbh1"])
        self.assertEqual({j["how"] for j in a["joins"]}, {"name, father and grandfather"})
        self.assertEqual([e for e in jan if e is not a][0]["works"], ["vip4"])
        self.assertTrue(reg["homonyms"], "the two Janamejayas named")
        self.assertIn("grandfathers", reg["homonyms"][0]["why"])

    def test_never_through_a_third(self):
        reg = self.build({"mbh1": ADI, "bhp9": BHP, "vip4": VIP, "hv": LONE})
        for e in reg["entries"]:
            gs = {VA.nkey(p["grand"]) for p in e["persons"] if p["grand"]}
            self.assertLessEqual(len(gs), 1, e)
        lone = [e for e in reg["entries"] if "hv" in e["works"]][0]
        self.assertGreater(len(lone["works"]), 1, "joined, by name and father")
        self.assertFalse("vip4" in lone["works"] and "bhp9" in lone["works"], "to one of the two, not both")
        self.assertIn("name and father", {j["how"] for j in lone["joins"]})

    def test_two_names_said(self):
        e1 = [st("Parya\u015bravas", "son_of", "Bh\u012bmasena", ref="E 45"),
              st("Parya\u015bravas", "other", "Prat\u012bpa", ref="E 45", words="yam \u0101hu\u1e25 prat\u012bpa\u1e43 n\u0101ma"),
              st("\u015aa\u1e43tanu", "son_of", "Prat\u012bpa", ref="E 46")]
        f1 = [st("Prat\u012bpa", "son_of", "Bh\u012bmasena", ch=23, ref="H 114"),
              st("\u015a\u0101ntanu", "son_of", "Prat\u012bpa", ch=23, ref="H 115")]
        reg = self.build({"mbh1": e1, "hv": f1})
        p = [e for e in reg["entries"] if "Prat\u012bpa" in e["names"]][0]
        self.assertEqual(sorted(p["works"]), ["hv", "mbh1"])
        self.assertIn("Parya\u015bravas", p["names"])
        self.assertEqual(p["aka"][0]["ref"], "E 45")
        s = [e for e in reg["entries"] if VA.same(e["name"], "\u015a\u0101ntanu")][0]
        self.assertEqual(sorted(s["works"]), ["hv", "mbh1"])
        self.assertEqual(reg["counts"]["two_names_said"], 1)

    def test_a_grandfather_by_his_other_name(self):
        e1 = [st("Parya\u015bravas", "son_of", "Bh\u012bmasena", ref="E 45"),
              st("Parya\u015bravas", "other", "Prat\u012bpa", ref="E 45", words="yam \u0101hu\u1e25 prat\u012bpa\u1e43 n\u0101ma"),
              st("\u015aa\u1e43tanu", "son_of", "Prat\u012bpa", ref="E 46"), st("Devavrata", "son_of", "\u015aa\u1e43tanu", ref="E 50")]
        f1 = [st("Prat\u012bpa", "son_of", "Dil\u012bpa", ch=20, ref="V 8"), st("\u015aantanu", "son_of", "Prat\u012bpa", ch=20, ref="V 9"),
              st("Devavrata", "son_of", "\u015aantanu", ch=20, ref="V 10")]
        reg = self.build({"mbh1": e1, "vip4": f1})
        d = [e for e in reg["entries"] if e["name"] == "Devavrata"]
        self.assertEqual(len(d), 1, "Paryasravas is Pratipa: one grandfather")
        self.assertEqual(sorted(d[0]["works"]), ["mbh1", "vip4"])


class TheProposals(unittest.TestCase):
    def test_one_father_one_son_two_names(self):
        L = lambda *ns: [(n, "R%d" % i, "w") for i, n in enumerate(ns)]
        lines = {"a": L("Kuru", "Jahnu", "Suratha"), "b": L("Kuru", "Par\u012bk\u1e63it", "Suratha")}
        t = VA.table(lines)
        d = {"slug": "kuru", "lines": lines, "rows": t["rows"]}
        got = R.proposed([d], set())
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["father"], got[0]["son"]), ("Kuru", "Suratha"))
        self.assertEqual(R.proposed([d], {tuple(sorted((VA.nkey("Jahnu"), VA.nkey("Par\u012bk\u1e63it"))))}), [],
                         "not when a verse said it")


class TheDesk(unittest.TestCase):
    def make(self, t):
        out = Path(t) / "data" / "vamsa_read"
        for w, sts in {"mbh1": ADI, "bhp9": BHP, "vip4": VIP}.items():
            (out / w).mkdir(parents=True)
            (out / w / "01_1.json").write_text(json.dumps({"chapter": sts[0]["chapter"], "statements": sts},
                                                          ensure_ascii=False), encoding="utf-8")
        return out

    def test_main(self):
        with tempfile.TemporaryDirectory() as t:
            out = self.make(t); ex = Path(t) / "exports"
            before = {p.name + p.parent.name: hashlib.md5(p.read_bytes()).hexdigest() for p in out.rglob("*.json")}
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(R.main(["--out", str(out), "--exports", str(ex), "--name", "Janamejaya"]), 0)
                self.assertEqual(R.main(["--out", str(out), "--exports", str(ex), "--stats"]), 0)
            self.assertFalse(ex.exists(), "--name and --stats write nothing")
            self.assertIn("VERDICT: 2 entries named Janamejaya", buf.getvalue())
            with redirect_stdout(buf):
                self.assertEqual(R.main(["--out", str(out), "--exports", str(ex)]), 0)
            self.assertIn("NEXT: open exports", buf.getvalue())
            j = json.loads((out / "register.json").read_text(encoding="utf-8"))
            self.assertEqual(j["mark"], MARK)
            self.assertTrue((ex / "vamsa_register.csv").exists())
            md = (ex / "vamsa_register.md").read_text(encoding="utf-8")
            self.assertIn("One name kept as two", md)
            after = {p.name + p.parent.name: hashlib.md5(p.read_bytes()).hexdigest() for p in out.rglob("*.json")}
            after.pop("register.jsonvamsa_read")
            self.assertEqual(before, after, "the readings untouched")

    def test_nothing_read(self):
        with tempfile.TemporaryDirectory() as t:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(R.main(["--out", str(Path(t) / "none"), "--exports", str(Path(t) / "ex")]), 1)
            self.assertIn("REFUSE: nothing read", buf.getvalue())


class TheFile(unittest.TestCase):
    def test_ascii_mark_and_free(self):
        text = (SCRIPTS / "vamsa_register.py").read_bytes().decode("ascii")
        self.assertIn(MARK, text)
        for w in ("claude_engine", "anthropic", "google.genai", "requests", "sqlite3", "context.db"):
            self.assertNotIn(w, text, w)
        Path(__file__).read_bytes().decode("ascii")


if __name__ == "__main__":
    unittest.main()
