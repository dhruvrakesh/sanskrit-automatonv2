# -*- coding: ascii -*-
"""TRIANGULATE_2026_10_22: source_fidelity.py --pair counts where the two readings agree with each other against the
reference ("outvoted"): with one of our own readings as the reference, where it is most likely misread, kept as the
mends to read beside the page; the verdict then judges the reference by that rate and each other reading by its own;
with an e-text as the reference, the line says the print reads otherwise there. The patcher. Temp files only."""
import contextlib, io, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
SRC = SCRIPTS / "source_fidelity.py"
PAT = SCRIPTS / "patch_triangulate_2026_10_22.py"
MARK = "TRIANGULATE_2026_10_22"
HERE = MARK.encode() in SRC.read_bytes()

V1 = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u0902\u091c\u092f \u0965 \u0967 \u0965"
V2 = "\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938\u094d\u0924\u0926\u093e \u0964 \u0906\u091a\u093e\u0930\u094d\u092f\u092e\u0941\u092a\u0938\u0902\u0917\u092e\u094d\u092f \u0930\u093e\u091c\u093e \u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d \u0965 \u0968 \u0965"
V3 = "\u092a\u0936\u094d\u092f\u0948\u0924\u093e\u0902 \u092a\u093e\u0923\u094d\u0921\u0941\u092a\u0941\u0924\u094d\u0930\u093e\u0923\u093e\u092e\u093e\u091a\u093e\u0930\u094d\u092f \u092e\u0939\u0924\u0940\u0902 \u091a\u092e\u0942\u092e\u094d \u0964 \u0935\u094d\u092f\u0942\u0922\u093e\u0902 \u0926\u094d\u0930\u0941\u092a\u0926\u092a\u0941\u0924\u094d\u0930\u0947\u0923 \u0924\u0935 \u0936\u093f\u0937\u094d\u092f\u0947\u0923 \u0927\u0940\u092e\u0924\u093e \u0965 \u0969 \u0965"
V4 = "\u0905\u0924\u094d\u0930 \u0936\u0942\u0930\u093e \u092e\u0939\u0947\u0937\u094d\u0935\u093e\u0938\u093e \u092d\u0940\u092e\u093e\u0930\u094d\u091c\u0941\u0928\u0938\u092e\u093e \u092f\u0941\u0927\u093f \u0964 \u092f\u0941\u092f\u0941\u0927\u093e\u0928\u094b \u0935\u093f\u0930\u093e\u091f\u0936\u094d\u091a \u0926\u094d\u0930\u0941\u092a\u0926\u0936\u094d\u091a \u092e\u0939\u093e\u0930\u0925\u0903 \u0965 \u096a \u0965"


def sf():
    import source_fidelity
    return source_fidelity


@unittest.skipUnless(HERE, "TRIANGULATE_2026_10_22 is not here")
class TheVote(unittest.TestCase):
    def test_two_readings_against_the_reference(self):
        S = sf()
        ours = V1.replace("\u0938\u0902\u091c\u092f", "\u0938\u0902\u091a\u092f")                   # our reading misread ja as ca
        units = [S.norm(v) for v in (ours, V2, V3, V4)]
        a = V1.replace("\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947", "\u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0924\u094d\u0930\u0947")        # the first reading's own slip; it has ja
        b = V1.replace("\u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903", "\u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u093e")             # the second's own; it has ja too
        rest = V2 + "\n" + V3 + "\n" + V4
        ra = S.measure(units, [(1, a), (2, rest)], False)
        rb = S.measure(units, [(1, b), (2, rest)], False)
        p = S.pair(units, ra, rb, ["1.1", "1.2", "1.3", "1.4"])
        self.assertEqual((p["own_a"], p["own_b"], p["shared"], p["outvoted"]), (1, 1, 1, 1))
        m = p["mends"][0]
        self.assertEqual((m["ref"], m["page"], m["reference"], m["readings"]), ("1.1", 1, "\u091a", "\u091c"))
        self.assertTrue(m["before"].endswith("\u0938\u0902"))
        self.assertGreater(p["outvoted_per100"], 0)
        self.assertTrue(p["independent"], (p["own_overlap"], p["outvoted_overlap"]))

    def test_both_lacking_it_differently_is_shared_not_outvoted(self):
        S = sf()
        units = [S.norm(v) for v in (V1, V2, V3, V4)]
        rest = V2 + "\n" + V3 + "\n" + V4
        ra = S.measure(units, [(1, V1.replace("\u0938\u0902\u091c\u092f", "\u0938\u0902\u091a\u092f")), (2, rest)], False)
        rb = S.measure(units, [(1, V1.replace("\u0938\u0902\u091c\u092f", "\u0938\u0902\u0917\u092f")), (2, rest)], False)
        p = S.pair(units, ra, rb)
        self.assertEqual((p["shared"], p["outvoted"], p["mends"]), (1, 0, []))

    def test_two_readings_with_the_same_mistakes_are_not_two_witnesses(self):
        S = sf()
        units = [S.norm(v) for v in (V1, V2, V3, V4)]
        a = V1.replace("\u0927\u0930\u094d\u092e", "\u0918\u0930\u094d\u092e") + "\n" + V2   # dha read gha in V1
        b = V1 + "\n" + V2.replace("\u0927\u0928", "\u0918\u0928")                              # and in V2
        rest = V3 + "\n" + V4
        ra = S.measure(units, [(1, a), (2, rest)], False)
        rb = S.measure(units, [(1, b), (2, rest)], False)
        p = S.pair(units, ra, rb)
        self.assertEqual((p["own_a"], p["own_b"]), (1, 1))
        self.assertEqual(p["own_overlap"], 1.0)
        self.assertFalse(p["independent"])
        p.update(a="raw:x", b="file:y")
        v = S.verdict_of_ours("db:x", [p])
        self.assertTrue(v.startswith("db:x: not measured: raw:x and file:y make the same mistakes"), v)

    def test_the_verdict_on_our_own_reading(self):
        S = sf()
        v = S.verdict_of_ours("db:x", [{"a": "raw:x", "b": "vision:x", "outvoted_per100": 3.4, "outvoted": 120,
                                       "own_a_per100": 24.5, "own_b_per100": 1.2, "independent": True}])
        self.assertTrue(v.startswith("db:x: close"))
        self.assertIn("outvoted by raw:x and vision:x in 3.4 aksharas per 100", v)
        self.assertIn("120 to read beside the page", v)


def _db(path: Path, ours: list):
    con = sqlite3.connect(str(path))
    con.executescript("""
        CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT, category TEXT);
        CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT,
            translation TEXT, verse_ref TEXT, text_type TEXT, ocr_engine TEXT);
    """)
    con.execute("INSERT INTO docs (id, code, category) VALUES (1, 'gita_scan', 'itihasa')")
    for i, (pg, t) in enumerate(ours):
        con.execute("INSERT INTO passages (doc_id, page_no, idx, text, translation, verse_ref, text_type, ocr_engine) "
                    "VALUES (1,?,?,?,'',NULL,'mula','gemini-vision:gemini-2.5-flash')", (pg, i + 1, t))
    con.commit()
    con.close()


@unittest.skipUnless(HERE, "TRIANGULATE_2026_10_22 is not here")
class TheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tri_"))
        self.cwd = os.getcwd()
        ours = [(1, V1.replace("\u0938\u0902\u091c\u092f", "\u0938\u0902\u091a\u092f")), (1, V2), (2, V3), (2, V4)]
        _db(self.tmp / "context.db", ours)
        tess = {1: V1.replace("\u0927\u0930\u094d\u092e", "\u0918\u0930\u094d\u092e") + "\n" + V2.replace("\u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928", "\u0926\u0941\u092f\u094b\u0927\u0928"), 2: V3 + "\n" + V4}
        vis = {1: V1 + "\n" + V2, 2: V3.replace("\u092a\u0941\u0924\u094d\u0930\u0947\u0923", "\u092a\u0941\u091a\u0947\u0923") + "\n" + V4}
        for name, pages in (("raw", tess), ("raw_vision", vis)):
            d = self.tmp / "data" / name
            d.mkdir(parents=True)
            for p, t in pages.items():
                (d / ("gita_scan_%04d.jsonl" % p)).write_text(json.dumps({"engine": name, "text": t}, ensure_ascii=False),
                                                             encoding="utf-8")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_three_readings_of_one_print(self):
        S = sf()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(["--root", str(self.tmp), "--db", str(self.tmp / "context.db"), "--no-write",
                         "--ref", "db:gita_scan", "--cand", "raw:gita_scan", "--cand", "vision:gita_scan",
                         "--pair", "raw:gita_scan,vision:gita_scan"])
        os.chdir(self.cwd)
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("aksharas of the reference), per 100 aksharas", out)
        self.assertIn("the two agree against the reference:", out)
        self.assertIn("(1 aksharas): the reference's likely misreadings", out)
        self.assertIn("[\u091a -> \u091c]", out)
        self.assertIn("VERDICT: db:gita_scan: faithful", out)
        self.assertIn("outvoted by raw:gita_scan and vision:gita_scan", out)


class ThePatcher(unittest.TestCase):
    @unittest.skipUnless(HERE, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("source_fidelity.py.bak_triangulate_*"))
        if not baks:
            self.skipTest("no .bak_triangulate_ copy here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(baks[0], t / "scripts" / "source_fidelity.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("source_fidelity.py.bak_*"))
            later = [x for x in later if ".bak_triangulate_" not in x.name]
            self.assertEqual((t / "scripts" / "source_fidelity.py").read_bytes(),
                             (later[0] if later else SRC).read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], t / "scripts" / "source_fidelity.py")
            g = t / "scripts" / "source_fidelity.py"
            g.write_bytes(g.read_bytes().replace(b"def pair(units: list, ra: list, rb: list)", b"def pair(units, ra, rb)"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor", r.stdout)
            self.assertNotIn(MARK.encode(), g.read_bytes(), "all or nothing")


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
