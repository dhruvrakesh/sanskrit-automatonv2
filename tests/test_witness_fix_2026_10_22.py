# -*- coding: ascii -*-
"""WITNESS_FIX_2026_10_22: (1) etext_witness.kept_out() leaves out what dotted_words() keeps in Latin (a reference in
brackets, a siglum, an English note), so the Latin guard no longer refuses GRETIL's Nirukta (16.5% of its verses
held some; the guard refuses above 10%), while Latin debris still counts; (2) source_fidelity.py: a witness in the
database (db:<doc>__w_<site>, an e-text) is not one of our readings: two readings of our print agreeing against it is
where the print reads otherwise, not its misreading; the patcher. Temp files only, never data/context.db."""
import json, os, random, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
PAT = SCRIPTS / "patch_witness_fix_2026_10_22.py"
MARK = "WITNESS_FIX_2026_10_22"
HERE = all(MARK.encode() in (SCRIPTS / f).read_bytes() for f in ("etext_witness.py", "source_fidelity.py"))

try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False

R = random.Random(2211)
C = [chr(c) for c in range(0x0915, 0x0939)]
V = ["", "\u093e", "\u093f", "\u0940", "\u0941", "\u0947", "\u094b"]


def word(k):
    return "".join(R.choice(C) + R.choice(V) for _ in range(k))


def verse():
    return " ".join(word(R.randint(2, 4)) for _ in range(8)) + " \u0965"


def slip(v: str, at: int, new: str) -> str:
    while at < len(v) and not ("\u0915" <= v[at] <= "\u0939"):
        at += 1
    return v[:at] + (new if v[at] != new else "\u0915") + v[at + 1:]


@unittest.skipUnless(HERE, "WITNESS_FIX_2026_10_22 is not here")
class TheLatinGuard(unittest.TestCase):
    def setUp(self):
        import etext_witness as EW
        self.EW = EW

    def test_what_is_kept_in_latin_is_not_debris(self):
        k = self.EW.kept_out
        for s in ("\u0907\u0924\u093f (\u1e5bV X,84,2; 106,3) \u0907\u0924\u093f", "\u0935\u093e (\u091a Bh) \u0905",
                  "\u090f\u0915 [i.e., from su] \u0926\u0926\u093e\u0924\u093f", "1.30a: \u0928\u092e\u0903 (B \u0930\u093e)"):
            self.assertIsNone(self.EW.ASCII_LETTER.search(k(s)), s)
        for s in ("\u0930\u093e\u092e rAma \u0907\u0924\u093f", "\u0907\u0924\u093f (abc) \u0907", "[\u0915 x]"):
            self.assertIsNotNone(self.EW.ASCII_LETTER.search(k(s)), "Latin debris still counts: " + s)

    @unittest.skipUnless(HAVE_IT, "indic_transliteration is not here")
    def test_a_dotted_witness_passes_the_guard(self):
        lines = ["``.agnir.iva.''.(\u1e5bV.X,84,2;.106,3).iti.vij\u00f1\u0101yate", "v\u0101.(ca.Bh).aneka.parvasu",
                 "eka.upasarg\u0101d.[i.e.,.from.su].dad\u0101ti", "sam\u0101mn\u0101ya\u1e25.sam\u0101mn\u0101ta\u1e25.sa"]
        verses = [{"text": self.EW.to_deva(s, "iast")} for s in lines]
        self.assertEqual(self.EW.leftover_latin(verses), 0.0)
        verses.append({"text": "\u0930\u093e\u092e rAma"})
        self.assertAlmostEqual(self.EW.leftover_latin(verses), 0.2)


@unittest.skipUnless(HERE, "WITNESS_FIX_2026_10_22 is not here")
class TheEtextReference(unittest.TestCase):
    def test_is_ours(self):
        import source_fidelity as sf
        for s, want in (("db:nirukta", True), ("db:nirukta__w_gretil", False), ("vision:nirukta", True),
                        ("raw:nirukta", True), ("pages:data/raw_vision_pro/nirukta", True), ("witness:x__w_gretil", False),
                        ("file:sources/x.txt", False), ("db:markandeya_purana__w_gretil", False)):
            self.assertEqual(sf.is_ours(s), want, s)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        etext = [verse() for _ in range(30)]
        printed = [slip(v, 8, "\u0928") if i % 3 == 0 else v for i, v in enumerate(etext)]   # the print's own readings
        tess = [slip(v, 20, "\u0918") if i % 2 == 0 else v for i, v in enumerate(printed)]
        vis = [slip(v, 30, "\u0927") if i % 5 == 1 else v for i, v in enumerate(printed)]
        for folder, vs in (("raw", tess), ("raw_vision", vis)):
            d = t / "data" / folder
            d.mkdir(parents=True)
            for p in range(3):
                (d / ("D_%04d.jsonl" % (p + 1))).write_text("".join(
                    json.dumps({"text": v}, ensure_ascii=False) + "\n" for v in vs[p * 10:(p + 1) * 10]), encoding="utf-8")
        import db_utils
        self.db = t / "context.db"
        con = db_utils.connect(str(self.db)); db_utils.ensure_schema(con); db_utils.migrate_schema(con)
        for code, vs in (("D", printed), ("D__w_gretil", etext)):
            did = db_utils.ensure_doc(con, code, category="vedanga")
            for i, v in enumerate(vs):
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(?,?,?,?,?,'mula')",
                            (did, i // 10 + 1, i % 10 + 1, v, ""))
        con.commit(); con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, ref):
        r = subprocess.run([sys.executable, str(SCRIPTS / "source_fidelity.py"), "--root", str(self.t), "--db", str(self.db),
                            "--out-dir", str(self.t / "out"), "--ref", ref, "--cand", "raw:D", "--cand", "vision:D",
                            "--pair", "raw:D,vision:D"], capture_output=True, text=True, encoding="utf-8", timeout=180,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        return r.returncode, r.stdout + r.stderr

    def test_an_etext_is_not_mended_by_our_print(self):
        rc, out = self.run_tool("db:D__w_gretil")
        self.assertEqual(rc, 0, out)
        self.assertIn("where the print reads otherwise than the e-text", out)
        verdict = [l for l in out.splitlines() if l.startswith("VERDICT:")][0]
        self.assertNotIn("outvoted by", verdict)
        self.assertNotIn("db:D__w_gretil:", verdict, "the e-text is the measure, not the measured")
        self.assertTrue(verdict.startswith(("VERDICT: raw:D:", "VERDICT: vision:D:")), verdict)

    def test_ours_is_still_mended(self):
        rc, out = self.run_tool("db:D")
        self.assertEqual(rc, 0, out)
        self.assertIn("the reference's likely misreadings", out)
        self.assertIn("outvoted by raw:D and vision:D", [l for l in out.splitlines() if l.startswith("VERDICT:")][0])


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "scripts/source_fidelity.py", "tests/test_etext_dots_2026_10_22.py",
             "tests/test_engines_2026_10_22.py")

    @unittest.skipUnless(HERE, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_witnessfix_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_witnessfix_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("CHECK OK: 4 file(s)", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:   # ETEXT_ANALYSIS_2026_10_22: etext_witness.py's later backup may be .bak_etextanalysis_
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextanalysis_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)

    def test_it_needs_etext_dots_and_engines(self):
        if not PAT.exists():
            self.skipTest("the patcher is not here")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                (t / f).write_text("# an older copy\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("Nothing written", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
