# -*- coding: ascii -*-
"""ETEXT_PROSE_2026_10_21: GRETIL's Satapatha is prose, each kandika under its own line "13.1.1.[1]"; etext_witness.py
reads it unit by unit, each with its reference and the adhyaya as its chapter, never cut at 12 lines nor at a blank
line, with no danda added; what stands outside a unit (a file's title and notes) is left out; a folder of files is one
text, a break between files, each file's sha256 kept; a new text takes --category; verse texts read as before. The
lines are GRETIL's (sb_13_u.htm, the first kandikas of kanda 13), the rest made up. Temp files only; nothing fetched."""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "ETEXT_PROSE_2026_10_21"
HERE = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes()

HEAD = ["SATAPATHA-BRAHMANA 13", "Data input by H.S. Ananthanarayana and W. P. Lehman.",
        "Bracketted numbering added mechanically.", "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY!", ""]
K13 = ["13.1.1.[1]",
       "brahmaudanam pacati reta eva taddhatte yad\u0101jyamuci\u1e63yate tena",
       "ra\u015ban\u0101mabhyajy\u0101datte tejo v\u0101 \u0101jyam pr\u0101j\u0101patyo'\u015bva\u1e25 praj\u0101patimeva tejas\u0101",
       "samardhayatyap\u016bto v\u0101 e\u1e63o'medhyo yada\u015bva\u1e25",
       "13.1.1.[2]",
       "darbhamay\u012b ra\u015ban\u0101 bhavati pavitra\u1e43 vai darbh\u0101\u1e25 pun\u0101tyevainam p\u016btamevainam",
       "medhyam\u0101labhate",
       "13.1.1.[3]",
       "a\u015bvasya v\u0101 \u0101labdhasya reta udakr\u0101mattatsuvar\u1e47a\u1e43 hira\u1e47yamabhavadyatsuvar\u1e47a\u1e43",
       "hira\u1e47ya\u1e43 dad\u0101tya\u015bvameva retas\u0101 samardhayati",
       "13.1.1.[4]",
       "praj\u0101patiryaj\u00f1amas\u1e5bjata tasya mahim\u0101p\u0101kr\u0101matsa mahartvija\u1e25 pr\u0101vi\u015battam"]
LONG = ["13.1.2.[1]"] + ["tejo v\u0101 \u0101jyam pr\u0101j\u0101patyo'\u015bva\u1e25 praj\u0101patimeva tejas\u0101 samardhayati"] * 15 + [
        "", "p\u016btamevainam medhyam\u0101labhate", "13.1.2.[2] darbhamay\u012b ra\u015ban\u0101 bhavati pavitra\u1e43 vai darbh\u0101\u1e25"]
K14 = ["SATAPATHA-BRAHMANA 14", "Bracketted numbering added mechanically.", "",
       "14.1.1.[1]", "dev\u0101\u015bca v\u0101 asur\u0101\u015bca ubhaye pr\u0101j\u0101paty\u0101\u1e25 pasp\u1e5bdhire",
       "14.1.1.[2]", "te dev\u0101 abruvan hant\u0101sur\u0101nyaj\u00f1a up\u0101ty\u0101meti k\u0101ry\u01013 iti"]


def page(lines, html=False):
    body = "\n".join(lines)
    return ("<html><body>\n" + body.replace("\n", "<br>\n") + "\n</body></html>\n") if html else body + "\n"


@unittest.skipUnless(HERE, "ETEXT_PROSE_2026_10_21 is not here")
class TheProse(unittest.TestCase):
    def setUp(self):
        import etext_witness as W
        self.W = W

    def test_units_by_their_reference_lines(self):
        p = self.W.parse(page(HEAD + K13 + LONG))
        vs = p["verses"]
        self.assertEqual([v["ref"] for v in vs], ["13.1.1.1", "13.1.1.2", "13.1.1.3", "13.1.1.4", "13.1.2.1", "13.1.2.2"])
        self.assertEqual({v["chapter"] for v in vs}, {"13.1"}, "the adhyaya")
        self.assertEqual({v["type"] for v in vs}, {"prose"})
        self.assertIn("\u090f\u0937\u094b\u093d\u092e\u0947\u0927\u094d\u092f\u094b", vs[0]["text"], "eso'medhyo: the avagraha")
        self.assertNotIn("\u0964", "".join(v["text"] for v in vs), "no danda added")
        self.assertEqual(vs[4]["text"].count("\n") + 1, 16, "16 lines, one unit: not cut at 12, nor at the blank line")
        self.assertIn("\u0926\u0930\u094d\u092d\u092e\u092f\u0940", vs[5]["text"], "the unit's first words on its line")
        self.assertEqual(p["stats"]["prose_units"], 6)
        self.assertGreaterEqual(p["stats"]["outside"], 1, "the file's title is not the text")
        self.assertEqual(self.W.leftover_latin(vs), 0.0)
        self.assertTrue(vs[0]["roman"].startswith("brahmaudanam pacati"), "GRETIL's IAST kept beside it")

    def test_a_folder_is_one_text(self):
        td = Path(tempfile.mkdtemp(prefix="prose_"))
        try:
            d = td / "satapatha_gretil"
            d.mkdir()
            (d / "sb_13_u.htm").write_text(page(HEAD + K13 + LONG, html=True), encoding="utf-8")
            (d / "sb_14_u.htm").write_text(page(K14, html=True), encoding="utf-8")
            (d / "sb_13_u.htm.json").write_text("{}", encoding="utf-8")
            text, info = self.W.read_source(d)
            self.assertEqual([f["name"] for f in info["files"]], ["sb_13_u.htm", "sb_14_u.htm"])
            self.assertEqual(len(info["files"][0]["sha256"]), 64)
            vs = self.W.parse(text)["verses"]
            self.assertEqual(vs[-2]["ref"], "14.1.1.1")
            self.assertNotIn("SATAPATHA", "".join(v.get("roman") or "" for v in vs))
            self.assertTrue(vs[-1]["text"].endswith("\u0915\u093e\u0930\u094d\u092f\u093e\u0969 \u0907\u0924\u093f"),
                            "kaarya3 iti: the pluti's 3")
            self.assertEqual(vs[5]["ref"], "13.1.2.2", "kanda 14's title did not join the last kandika of 13")
            self.assertNotIn("\u0938\u0924\u092a\u0925", vs[5]["text"])
            buf, cwd = io.StringIO(), os.getcwd()
            args = ["--doc", "satapatha_madhyandina", "--file", str(d), "--db", str(td / "none.db"), "--per-page", "4",
                    "--out-dir", str(td / "raw"), "--witnesses", str(td / "w.jsonl"), "--verdicts", str(td / "v.jsonl")]
            try:
                with contextlib.redirect_stdout(buf):
                    rc = self.W.main(args)
                    rc2 = self.W.main(args + ["--write", "--category", "brahmana"])
            finally:
                os.chdir(cwd)
            out = buf.getvalue()
            self.assertEqual((rc, rc2), (0, 0), out)
            self.assertIn("files: 2, read in this order: sb_13_u.htm, sb_14_u.htm", out)
            self.assertIn("prose: 8 units by their reference lines", out)
            self.assertIn("WITNESS: the scan is not in the database: nothing to measure; the witness can still be its own text", out)
            meta = json.loads((td / "raw" / "satapatha_madhyandina__w_gretil" / "witness.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["category"], "brahmana")
            self.assertEqual(len(meta["files"]), 2)
            recs = [json.loads(l) for f in sorted((td / "raw" / "satapatha_madhyandina__w_gretil").glob("*.jsonl"))
                    for l in f.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["verse_ref"] for r in recs][:2], ["13.1.1.1", "13.1.1.2"])
            self.assertEqual({r["text_type"] for r in recs}, {"prose"})
            self.assertEqual(json.loads((td / "v.jsonl").read_text(encoding="utf-8").splitlines()[-1])["status"], "witness")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_verses_as_before_and_a_bad_category(self):
        v = self.W.parse(page(["dharmak\u1e63etre kuruk\u1e63etre samavet\u0101 yuyutsava\u1e25 |",
                               "m\u0101mak\u0101\u1e25 p\u0101\u1e47\u1e0dav\u0101\u015b caiva kim akurvata sa\u00f1jaya // BhG_1.1 //"]))
        self.assertEqual([x["ref"] for x in v["verses"]], ["1.1"])
        self.assertNotIn("prose_units", v["stats"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.W.main(["--doc", "x", "--file", "y", "--category", "Brahmana!"])
        self.assertEqual(rc, 2)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_etext_prose_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    FILES = ("scripts/etext_witness.py", "tests/test_etext_refs_2026_10_21.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextprose_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_etext_prose_2026_10_21.py")]
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
            p.write_bytes(p.read_bytes().replace(b"    chap = [1]\n", b"    chap = [0]\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 4 found 0 times", r.stdout)
            self.assertIn("Nothing written.", r.stdout)


if __name__ == "__main__":
    unittest.main()
