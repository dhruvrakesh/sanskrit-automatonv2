# -*- coding: ascii -*-
"""ETEXT_PROSE2_2026_10_22: GRETIL's Satapatha in full numbers its kandikas in more shapes than 13.1.1.[1]: brackets put
in wrongly (1.1.3[.1]1, 1.1.3[[.]]5, 4.5.7.[9]]), none (14.4.1.1), a brahmana's own number over a brahmana of one
kandika (14.6.4.) or as a heading (2.1.1.), a number glued to its text and mistyped (11.7.4.2 between 1.7.4.1 and
1.7.4.3), and an appendix after a line of asterisks that repeats earlier kandikas. Each is read as its own unit with
its number; a repeat word for word is left out; the appendix is marked; a separator in a file's header, or one before a
higher number, marks nothing; verse texts read as before. The shapes are GRETIL's; the words made up from its lines."""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "ETEXT_PROSE2_2026_10_22"
HERE = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes()

A = "dev\u0101 ha vai sattra\u1e43 ni\u1e63edu\u1e25 | agni\u1e25"
B = "agnirindra\u1e25 somo makho vi\u1e63\u1e47urvi\u015bve dev\u0101"
C = "praj\u0101patirha vai sv\u0101\u1e43 duhitaramabhidadhyau"
D = "sarve\u1e63\u0101m v\u0101 e\u1e63a bh\u016bt\u0101n\u0101m sarve\u1e63\u0101\u1e43 dev\u0101n\u0101m"

K1 = ["SATAPATHA-BRAHMANA 1", "****************************************", "header notes", "****************",
      "1.1.3.[4]", A, "1.1.3[[.]]5", B, "1.1.3.[10]", C, "1.1.3[.1]1", D,
      "1.7.4.[1]", A + " " + B, "11.7.4.2" + C, "1.7.4.[3]", D]
K4 = ["4.5.7.[8]", A, "4.5.7.[9]]", B]
K14 = ["14.3.2.[1]", D, "14.3.2.[2]", A,
       "*************************", "14.4.1.1", B, "14.4.1.2", C,
       "14.6.3.[2]", A, "14.6.4.", C + " " + D, "14.6.5", B + " " + A, "14.6.7.[1]", D + " " + C,
       "14.8.2.", "14.8.2.[1]", B,
       "****************************************************",
       "14.3.1.", "ath\u0101to dak\u1e63i\u1e47\u0101n\u0101m suvar\u1e47a\u1e43 hira\u1e47ya\u1e43", "14.3.2.1", D, "14.3.2.2", A + " " + C]


@unittest.skipUnless(HERE, "ETEXT_PROSE2_2026_10_22 is not here")
class TheShapes(unittest.TestCase):
    def setUp(self):
        import etext_witness as W
        self.W = W

    def parse(self, *parts):
        return self.W.parse(("\n%s\n" % self.W.FILE_BREAK).join("\n".join(p) + "\n" for p in parts))

    def test_every_shape_has_its_number(self):
        p = self.parse(K1, K4, K14)
        vs, st = p["verses"], p["stats"]
        refs = [v["ref"] for v in vs]
        self.assertEqual(refs, ["1.1.3.4", "1.1.3.5", "1.1.3.10", "1.1.3.11", "1.7.4.1", "1.7.4.2", "1.7.4.3",
                                "4.5.7.8", "4.5.7.9", "14.3.2.1", "14.3.2.2", "14.4.1.1", "14.4.1.2", "14.6.3.2",
                                "14.6.4", "14.6.5", "14.6.7.1", "14.8.2.1", "14.3.1", "14.3.2.2"])
        self.assertEqual(st["repaired"], 1, "11.7.4.2 between 1.7.4.1 and 1.7.4.3 is 1.7.4.2")
        self.assertTrue(vs[5]["text"].startswith("\u092a\u094d\u0930\u091c\u093e\u092a\u0924\u093f\u0930\u094d\u0939"),
                        "the glued text is the unit's")
        self.assertEqual(st["repeats"], 1, "14.3.2.1 again, word for word: left out")
        self.assertEqual([v["ref"] for v in vs if v.get("appendix")], ["14.3.1", "14.3.2.2"],
                         "after the last separator, numbered below 14.8.2.1; the one before 14.4.1.1 marks nothing")
        self.assertEqual(st["separators"], 2, "the header's two, before any number, are not counted")
        self.assertEqual(st["headings"], 4, "14.6.4., 14.6.5, 14.8.2. and 14.3.1.")
        self.assertEqual(vs[14]["chapter"], "14.6")
        self.assertEqual({v["type"] for v in vs}, {"prose"}, "a kandika is prose, its danda or not")
        self.assertEqual({v["padas"] for v in vs}, {0})
        self.assertEqual(self.W.leftover_latin(vs), 0.0)
        self.assertNotIn("header notes", "".join(v.get("roman") or "" for v in vs))
        self.assertEqual(st["out_of_order"], 1, "the appendix's 14.3.1 after 14.8.2.1")

    def test_the_meta_says_appendix(self):
        p = self.parse(K14)
        recs = self.W.records(p, self.W.paginate(p["verses"], 50), "etext:gretil", "x", "sb_14_u.htm")
        flagged = [r["verse_ref"] for _n, rs in recs for r in rs if r["meta"].get("after_separator")]
        self.assertEqual(flagged, ["14.3.1", "14.3.2.2"])

    def test_verses_untouched_by_the_loose_shapes(self):
        v = self.W.parse("\n".join(["1.2.3.4", "dharmak\u1e63etre kuruk\u1e63etre samavet\u0101 yuyutsava\u1e25 |",
                                    "m\u0101mak\u0101\u1e25 p\u0101\u1e47\u1e0dav\u0101\u015b caiva kim akurvata "
                                    "sa\u00f1jaya // BhG_1.1 //", "**********"]) + "\n")
        self.assertEqual([x["ref"] for x in v["verses"]], ["1.1"])
        for k in ("prose_units", "headings", "separators", "repeats"):
            self.assertNotIn(k, v["stats"], k)

    def test_the_preview_counts_the_shapes(self):
        td = Path(tempfile.mkdtemp(prefix="prose2_"))
        try:
            d = td / "satapatha_gretil"
            d.mkdir()
            for name, lines in (("sb_01_u.htm", K1), ("sb_04_u.htm", K4), ("sb_14_u.htm", K14)):
                (d / name).write_text("<html><body>\n" + "<br>\n".join(lines) + "\n</body></html>\n", encoding="utf-8")
            buf, cwd = io.StringIO(), os.getcwd()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = self.W.main(["--doc", "satapatha_madhyandina", "--file", str(d), "--db", str(td / "none.db")])
            finally:
                os.chdir(cwd)
            out = buf.getvalue()
            self.assertEqual(rc, 0, out)
            self.assertIn("prose, the e-text's other shapes: 4 brahmana number(s)", out)
            self.assertIn("1 unit(s) repeated word for word left out; 1 number(s) mistyped", out)
            self.assertIn("2 separator line(s), 2 unit(s) after one", out)
        finally:
            shutil.rmtree(td, ignore_errors=True)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_etext_prose2_2026_10_22.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    FILES = ("scripts/etext_witness.py", "tests/test_etext_prose_2026_10_21.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose2_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextprose2_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_etext_prose2_2026_10_22.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])
            p = t / "scripts" / "etext_witness.py"
            p.write_bytes(p.read_bytes().replace(b'                r["meta"]["roman_source"] = v["roman"]\n',
                                                 b'                r["meta"]["roman"] = v["roman"]\n'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 6 found 0 times", r.stdout)
            self.assertIn("Nothing written.", r.stdout)


if __name__ == "__main__":
    unittest.main()
