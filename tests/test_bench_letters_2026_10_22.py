# -*- coding: ascii -*-
"""BENCH_LETTERS_2026_10_22: benchmark_sources.py reads each reading against ours akshara by akshara on a sample of
pages, and Tesseract beside each other OCR reading: each one's own misreadings, and where the two agree against ours
(ours' likely misreadings, its mends); two columns, lines in the opinion, res["letters"]; --letters-pages 0 leaves it
out; the patcher. Temp files only, never data/context.db, never the network."""
import json, os, random, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "benchmark_sources.py"
PAT = SCRIPTS / "patch_bench_letters_2026_10_22.py"
MARK = "BENCH_LETTERS_2026_10_22"
HERE = MARK.encode() in TOOL.read_bytes()

R = random.Random(22)
C = [chr(c) for c in range(0x0915, 0x0939)]
V = ["", "\u093e", "\u093f", "\u0940", "\u0941", "\u0947", "\u094b"]


def word(k):
    return "".join(R.choice(C) + R.choice(V) for _ in range(k))


def verse():
    line = lambda: " ".join(word(R.randint(2, 4)) for _ in range(5))
    return line() + " \u0964\n" + line() + " \u0965"


VERSES = [verse() for _ in range(60)]
PAGES = {p: VERSES[(p - 1) * 10:p * 10] for p in range(1, 7)}


def swap_first(v: str, new: str) -> str:
    """The verse's first akshara's consonant read as another."""
    return new + v[1:]


def jsonl(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"text": text}, ensure_ascii=False) + "\n", encoding="utf-8")


def make_db(path, doc, pages):
    import db_utils
    con = db_utils.connect(str(path)); db_utils.ensure_schema(con); db_utils.migrate_schema(con)
    did = db_utils.ensure_doc(con, doc, category="agama")
    for p, vs in pages.items():
        for i, t in enumerate(vs, 1):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type) VALUES(?,?,?,?,?,'mula')",
                        (did, p, i, t, ""))
    con.commit(); con.close()


@unittest.skipUnless(HERE, "BENCH_LETTERS_2026_10_22 is not here")
class TheLetters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        ours = {p: list(vs) for p, vs in PAGES.items()}
        ours[2][0] = swap_first(ours[2][0], "\u0939" if ours[2][0][0] != "\u0939" else "\u0915")   # ours' slip
        tess = {p: list(vs) for p, vs in PAGES.items()}
        for p in (1, 2, 3, 5, 6):
            tess[p][1] = swap_first(tess[p][1], "\u0918" if tess[p][1][0] != "\u0918" else "\u0915")  # Tesseract's own
        vis = {p: list(vs) for p, vs in PAGES.items()}
        for p in (2, 4, 6):
            vis[p][3] = swap_first(vis[p][3], "\u0927" if vis[p][3][0] != "\u0927" else "\u0915")      # vision's own
        self.ours, self.vis = ours, vis
        for p in PAGES:
            jsonl(t / "data" / "raw" / ("D_%04d.jsonl" % p), "\n".join(tess[p]))
            jsonl(t / "data" / "raw_vision" / ("D_%04d.jsonl" % p), "\n".join(vis[p]))
        (t / "backups").mkdir()
        self.db = t / "data" / "context.db"
        make_db(self.db, "D", ours)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        t = self.t
        b = ["--db", str(self.db), "--raw", str(t / "data/raw"), "--vision-dir", str(t / "data/raw_vision"),
             "--merged-dir", str(t / "data/raw_merged"), "--sources", str(t / "sources"),
             "--source-desk", str(t / "data/source_desk"), "--out-dir", str(t / "data/raw_witness"),
             "--witnesses", str(t / "data/witnesses.jsonl"), "--verdicts", str(t / "data/source_verdicts.jsonl"),
             "--bench-dir", str(t / "data/benchmarks"), "--backup-dir", str(t / "backups")]
        env = dict(os.environ, SA_DASHBOARD_URL="http://127.0.0.1:9", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(TOOL)] + b + list(args), cwd=str(t), capture_output=True, text=True,
                           env=env, timeout=180, encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def test_letter_by_letter(self):
        rc, out = self.run_tool("--doc", "D")
        self.assertEqual(rc, 0, out)
        res = json.loads((self.t / "data/benchmarks/D.json").read_text(encoding="utf-8"))
        by = {x["label"]: x for x in res["readings"]}
        self.assertEqual(res["letters"]["ours"], "database", "no repair here: the database is ours")
        self.assertEqual(res["letters"]["pages"], 6)
        self.assertLess(by["vision"]["aksharas_ours"], 99.9)
        pv = next(p for p in res["letters"]["pairs"] if p["b"] == "vision")
        self.assertEqual(pv["outvoted"], 1, "Tesseract and vision agree against ours once: ours' slip")
        self.assertEqual(pv["mends"][0]["page"], 2)
        self.assertTrue(pv["independent"], "Tesseract's slips and vision's are not alike")
        self.assertGreater(by["tesseract"]["own_per100"], by["vision"]["own_per100"])
        lines = " ".join(res["lines"])
        self.assertIn("Letter by letter, on 6 of ours' pages", lines)
        self.assertIn("Tesseract and vision, letter by letter", lines)
        self.assertIn("aksh%", out)

    def test_the_repairs_sources_are_no_witnesses(self):
        for p in PAGES:   # a repair made from vision: then vision and the database are ours' own text
            jsonl(self.t / "data" / "raw_merged" / ("D_%04d.jsonl" % p), "\n".join(self.ours[p]))
        rc, out = self.run_tool("--doc", "D")
        self.assertEqual(rc, 0, out)
        res = json.loads((self.t / "data/benchmarks/D.json").read_text(encoding="utf-8"))
        self.assertEqual(res["letters"]["ours"], "consensus")
        self.assertEqual(sorted(res["letters"]["same_as_ours"]), ["database", "vision"])
        self.assertEqual(res["letters"]["pairs"], [])
        self.assertIn("No two independent readings of the scan beside ours", " ".join(res["lines"]))

    def test_none_when_asked(self):
        rc, out = self.run_tool("--doc", "D", "--letters-pages", "0")
        self.assertEqual(rc, 0, out)
        res = json.loads((self.t / "data/benchmarks/D.json").read_text(encoding="utf-8"))
        self.assertNotIn("letters", res)
        self.assertNotIn("Letter by letter", " ".join(res["lines"]))


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/benchmark_sources.py", "tests/test_reingest_2026_10_12.py")

    @unittest.skipUnless(HERE, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_benchletters_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_benchletters_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, "source_fidelity.py must carry TRIANGULATE_2026_10_22 first")
            self.assertIn("TRIANGULATE_2026_10_22", r.stdout)
            shutil.copy2(SCRIPTS / "source_fidelity.py", t / "scripts" / "source_fidelity.py")
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)


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
