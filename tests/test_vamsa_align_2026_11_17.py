# -*- coding: ascii -*-
"""VAMSA_ALIGN_2026_11_17 (G6c). One dynasty side by side in every work that has it, generation by generation: names
compared with the diacritics, the visarga and the nasals set aside (a short name only when equal); one person by two
names within a work (a verified "other" whose words say he was called so); a founder found by his name and father, or
as a root; his line the one with the most names the other works share, then the longest; the lines aligned together,
each generation agree / most / differ / one, each two works how often they agree. Free and read-only: no call, the
readings untouched. Temp folders only."""
import hashlib, io, json, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vamsa_read as VR      # noqa: E402
import vamsa_align as VA     # noqa: E402

MARK = "VAMSA_ALIGN_2026_11_17"
KURU = ("kuru", "Kuru", "Sa\u1e43vara\u1e47a", "the Kurus from Kuru")


def st(a, rel, b, words="tasya putra\u1e25", ch=1, ref=None, check="verified"):
    return {"ref": ref or "R%d" % ch, "a": a, "rel": rel, "b": b, "words": words, "doubt": False, "check": check,
            "chapter": ch}


def names(line):
    return [n for n, _r, _w in line]


class TheNames(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(VA.nkey("Du\u1e25\u1e63anta"), "dusanta")
        self.assertEqual(VA.nkey("\u015aa\u1e43tanu"), VA.nkey("\u015a\u0101ntanu"))
        self.assertEqual(VA.nkey("Kur\u016b"), "kuru")

    def test_one_and_two(self):
        self.assertTrue(VA.same("Du\u1e25\u1e63anta", "Du\u1e63yanta"))
        self.assertTrue(VA.same("Vid\u016bratha", "Vi\u1e0d\u016bratha"))
        self.assertTrue(VA.same("Jayatsena", "Jayasena"))
        self.assertFalse(VA.same("Anu", "Manu"), "a short name only when equal")
        self.assertFalse(VA.same("Jahnu", "Par\u012bk\u1e63it"))
        self.assertTrue(VA.same("Kuru", "Kur\u016b"))

    def test_fathers(self):
        self.assertTrue(VA.father_is("Manu", "Manu Vaivasvata"))
        self.assertTrue(VA.father_is("Vasu", "Vasu Caidyoparicara"))
        self.assertTrue(VA.father_is("Yay\u0101ti", "Yay\u0101ti"))
        self.assertFalse(VA.father_is("Yay\u0101ti", "Yadu"))
        self.assertFalse(VA.father_is("Vasu", "Tigma"))


class TheAliases(unittest.TestCase):
    def sts(self, other_words="\u015ba\u015b\u0101dasa\u1e43j\u00f1\u0101m av\u0101pa", far=2):
        return [st("Vikuk\u1e63i", "son_of", "Ik\u1e63v\u0101ku", ch=2),
                st("Vikuk\u1e63i", "other", "\u015aa\u015b\u0101da", other_words, ch=2),
                st("Pura\u00f1jaya", "son_of", "\u015aa\u015b\u0101da", ch=2),
                st("Anenas", "son_of", "Pura\u00f1jaya", ch=2),
                st("Kakutstha", "son_of", "\u015aa\u015b\u0101da", ch=2 + far)]

    def test_a_second_name_is_the_first(self):
        al = VA.aliases(self.sts())
        self.assertEqual(al, [(2, "\u015aa\u015b\u0101da", "Vikuk\u1e63i")])
        ps, kids = VA.tree(self.sts())
        pk = [k for k, p in ps.items() if p["name"] == "Pura\u00f1jaya"][0]
        self.assertEqual(ps[ps[pk]["up"]]["name"], "Vikuk\u1e63i", "Sasada's son is Vikukshi's")
        line = VA.line_from("Ik\u1e63v\u0101ku", ps, kids, (), "")
        self.assertEqual(names(line), ["Ik\u1e63v\u0101ku", "Vikuk\u1e63i", "Pura\u00f1jaya", "Anenas"])
        said = [s for s in VA.renamed(self.sts()) if s.get("b_said")]
        self.assertTrue(said and said[0]["b_said"] == "\u015aa\u015b\u0101da", "the verse's name is kept")

    def test_not_far_and_not_without_the_words(self):
        r = VA.renamed(self.sts(far=5))
        self.assertEqual(r[-1]["b"], "\u015aa\u015b\u0101da", "five chapters on: not renamed")
        self.assertEqual(VA.aliases(self.sts(other_words="yayau vanam")), [], "an other that names no one")


class TheLines(unittest.TestCase):
    def test_the_line_most_shared_then_longest(self):
        sts = [st("Jahnu", "son_of", "Kuru"), st("Par\u012bk\u1e63it", "son_of", "Kuru"),
               st("Sudhanvan", "son_of", "Jahnu"), st("Suhotra", "son_of", "Sudhanvan"), st("Cyavana", "son_of", "Suhotra"),
               st("Suratha", "son_of", "Par\u012bk\u1e63it"), st("Vid\u016bratha", "son_of", "Suratha")]
        ps, kids = VA.tree(sts)
        self.assertEqual(names(VA.line_from("Kuru", ps, kids)), ["Kuru", "Jahnu", "Sudhanvan", "Suhotra", "Cyavana"],
                         "the longest")
        self.assertEqual(names(VA.line_from("Kuru", ps, kids, ["Suratha", "Vi\u1e0d\u016bratha"])),
                         ["Kuru", "Par\u012bk\u1e63it", "Suratha", "Vid\u016bratha"], "the most shared")
        self.assertEqual(VA.line_from("Manu", ps, kids), [], "no such person")

    def test_the_founder_by_his_father(self):
        sts = [st("B\u1e5bhadratha", "son_of", "Vasu Caidyoparicara"), st("Ku\u015b\u0101gra", "son_of", "B\u1e5bhadratha"),
               st("B\u1e5bhadratha", "son_of", "Devar\u0101ta", ch=9), st("Mah\u0101v\u012brya", "son_of", "B\u1e5bhadratha", ch=9),
               st("Sudh\u1e5bti", "son_of", "Mah\u0101v\u012brya", ch=9)]
        ps, kids = VA.tree(sts)
        self.assertEqual(names(VA.line_from("B\u1e5bhadratha", ps, kids, (), "Vasu")), ["B\u1e5bhadratha", "Ku\u015b\u0101gra"])
        self.assertEqual(names(VA.line_from("B\u1e5bhadratha", ps, kids))[1], "Mah\u0101v\u012brya", "no father: the longest")

    def test_a_root(self):
        ps, kids = VA.tree([st("Janamejaya", "son_of", "P\u016bru"), st("Pr\u0101cinv\u0101n", "son_of", "Janamejaya")])
        self.assertEqual(names(VA.line_from("P\u016bru", ps, kids, (), "Yay\u0101ti")),
                         ["P\u016bru", "Janamejaya", "Pr\u0101cinv\u0101n"])


class TheTable(unittest.TestCase):
    def test_align(self):
        self.assertEqual(VA.align(["Kuru", "Jahnu", "Suratha"], ["Kuru", "Suratha"]), [(0, 0), (1, None), (2, 1)])

    def test_agree_differ_one_and_pairs(self):
        L = lambda *ns: [(n, "R", "w") for n in ns]
        t = VA.table({"w1": L("Kuru", "Jahnu", "Suratha", "Vid\u016bratha"),
                      "w2": L("Kuru", "Par\u012bk\u1e63it", "Suratha", "Vi\u1e0d\u016bratha"),
                      "w3": L("Kuru", "Suratha", "Vid\u016bratha")})
        self.assertEqual([r["status"] for r in t["rows"]], ["agree", "differ", "agree", "agree"])
        self.assertEqual(t["pairs"]["w1 & w2"], [3, 4])
        self.assertEqual(t["pairs"]["w1 & w3"], [3, 3])

    def test_most(self):
        L = lambda *ns: [(n, "R", "w") for n in ns]
        t = VA.table({"a": L("Kuru", "Jahnu", "Suratha"), "b": L("Kuru", "Jahnu", "Suratha"),
                      "c": L("Kuru", "Par\u012bk\u1e63it", "Suratha")})
        r = t["rows"][1]
        self.assertEqual((r["status"], r["name"], r["n"]), ("most", "Jahnu", 2))

    def test_a_name_the_longest_has_not_is_one_row(self):
        L = lambda *ns: [(n, "R", "w") for n in ns]
        t = VA.table({"w1": L("Kuru", "Jahnu", "Suratha", "Vid\u016bratha", "S\u0101rvabhauma"),
                      "w2": L("Kuru", "Jahnu", "Janamejaya", "Suratha"),
                      "w3": L("Kuru", "Janamejaya", "Suratha")})
        jan = [r for r in t["rows"] if any(c[0] == "Janamejaya" for c in r["cells"].values())]
        self.assertEqual(len(jan), 1)
        self.assertEqual(sorted(jan[0]["cells"]), ["w2", "w3"])
        self.assertEqual(jan[0]["status"], "agree")


class TheDesk(unittest.TestCase):
    def make(self, root):
        out = Path(root) / "data" / "vamsa_read"
        kuru = {"vip4": ["Jahnu", "Suratha", "Vid\u016bratha", "S\u0101rvabhauma"],
                "hv": ["Par\u012bk\u1e63it", "Janamejaya", "Suratha", "Vid\u016bratha"],
                "matsya": ["Jahnu", "Suratha", "Vi\u1e0d\u016bratha", "S\u0101rvabhauma"]}
        for w, line in kuru.items():
            (out / w).mkdir(parents=True)
            sts = [st("Kuru", "son_of", "Sa\u1e43vara\u1e47a")]
            up = "Kuru"
            for n in line:
                sts.append(st(n, "son_of", up)); up = n
            (out / w / "01_1.json").write_text(json.dumps({"chapter": 1, "statements": sts}, ensure_ascii=False),
                                               encoding="utf-8")
        return out

    def digest(self, out):
        return {p.name + p.parent.name: hashlib.md5(p.read_bytes()).hexdigest() for p in out.rglob("*.json")}

    def test_the_kurus(self):
        with tempfile.TemporaryDirectory() as t:
            out = self.make(t)
            d = VA.dynasties(out, [KURU])
            self.assertEqual(len(d), 1)
            self.assertEqual(d[0]["order"][0] in ("vip4", "hv", "matsya"), True)
            self.assertEqual(d[0]["counts"]["agree"], 4, d[0]["rows"])   # Kuru, Suratha, Viduratha, Sarvabhauma
            self.assertEqual(d[0]["counts"]["most"], 1)                  # Jahnu 2 of 3
            self.assertEqual(VA.dynasties(out, [("x", "Manu", "", "none")]), [])

    def test_main_writes_three_files_and_reads_only(self):
        with tempfile.TemporaryDirectory() as t:
            out = self.make(t); ex = Path(t) / "exports"
            before = self.digest(out)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = VA.main(["--out", str(out), "--exports", str(ex), "--anchor", "Kuru", "--list"])
            self.assertEqual(rc, 0); self.assertFalse(ex.exists(), "--list writes nothing")
            with redirect_stdout(buf):
                rc = VA.main(["--out", str(out), "--exports", str(ex)])
            self.assertEqual(rc, 0)
            text = buf.getvalue()
            self.assertIn("VERDICT: 1 dynasties aligned", text)
            self.assertIn("NEXT: open exports", text)
            self.assertTrue((ex / "vamsa_align_kuru.csv").exists())
            md = (ex / "vamsa_align.md").read_text(encoding="utf-8")
            self.assertIn("| Dynasty |", md); self.assertIn(MARK, md); self.assertIn("Where they part", md)
            j = json.loads((out / "aligned.json").read_text(encoding="utf-8"))
            self.assertEqual(j["mark"], MARK)
            self.assertEqual(j["dynasties"][0]["slug"], "kuru")
            after = self.digest(out); after.pop("aligned.jsonvamsa_read", None)
            self.assertEqual(before, after, "the readings untouched")

    def test_nothing_read(self):
        with tempfile.TemporaryDirectory() as t:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = VA.main(["--out", str(Path(t) / "none"), "--exports", str(Path(t) / "ex")])
            self.assertEqual(rc, 1)
            self.assertIn("REFUSE: nothing read", buf.getvalue())
            self.assertIn("NEXT: python scripts\\vamsa_read.py --work g6", buf.getvalue())


class TheFile(unittest.TestCase):
    def test_ascii_mark_and_free(self):
        src = (SCRIPTS / "vamsa_align.py").read_bytes()
        src.decode("ascii")
        text = src.decode("ascii")
        self.assertIn(MARK, text)
        for w in ("claude_engine", "anthropic", "google.genai", "requests", "sqlite3", "context.db"):
            self.assertNotIn(w, text, w)
        self.assertEqual(len(VA.ANCHORS), 12)
        self.assertTrue(all(len(a) == 4 for a in VA.ANCHORS))

    def test_this_file_ascii(self):
        Path(__file__).read_bytes().decode("ascii")


if __name__ == "__main__":
    unittest.main()
