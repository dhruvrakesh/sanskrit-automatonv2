# -*- coding: ascii -*-
"""MBH_PROSE_2026_10_14: import_mbh_gretil.py reads the critical edition's prose (a capital last letter: 01,003.001A
and 01003001A), which it passed over before; reingest_pages.py --no-segment compares an e-text one record a passage,
as it went in. Temp files only; nothing is downloaded."""
import importlib.util, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


BOOK = "\n".join([
    "<html><body><pre>",
    "01,001.000*0001_01 a star passage, rejected by the editors",
    "01,001.001A lomahar\u1e63a\u1e47aputra ugra\u015brav\u0101\u1e25 sauti\u1e25 paur\u0101\u1e47iko naimi\u1e63\u0101ra\u1e47ye",
    "01,001.001B \u015baunakasya kulapater dv\u0101da\u015bav\u0101r\u1e63ike satre",
    "01,001.002a sam\u0101s\u012bn\u0101n abhyagacchad brahmar\u1e63\u012bn sa\u1e43\u015bitavrat\u0101n",
    "01,001.002c vinay\u0101vanato bh\u016btv\u0101 kad\u0101 cit s\u016btanandana\u1e25",
    "01,003.001  s\u016bta uv\u0101ca",
    "01,003.001A janamejaya\u1e25 p\u0101rik\u1e63ita\u1e25 saha bhr\u0101t\u1e5bbhi\u1e25 kuruk\u1e63etre d\u012brghasatram up\u0101ste",
    "01003002A tasya bhr\u0101taras traya\u1e25",
    "01,003.003a",
    "01,003.004ab two letters",
    "</pre></body></html>"])


@unittest.skipUnless(HAVE_IT, "indic_transliteration is not installed")
class TheImport(unittest.TestCase):
    def test_the_prose_is_read_now(self):
        m = load("import_mbh_prose", SCRIPTS / "import_mbh_gretil.py")
        ch = m.parse(BOOK, 1)
        self.assertEqual(sorted(ch), [1, 3])
        self.assertEqual(sorted(ch[1]), [1, 2], "1.1.1 is prose: it is read")
        self.assertEqual(len(ch[1][1]), 2)
        self.assertEqual(ch[3][1][0], "s\u016bta uv\u0101ca", "the speaker's line stays with its passage")
        self.assertEqual(ch[3][2], ["tasya bhr\u0101taras traya\u1e25"], "the BORI form of the reference")
        self.assertEqual(m.PROSE, {(1, 1), (3, 1), (3, 2)})
        with tempfile.TemporaryDirectory() as d:
            m.write_jsonl(ch, 1, Path(d), "MBh01", False)
            rows = [json.loads(x) for x in (Path(d) / "MBh01_0001.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([(r["verse_ref"], r["text_type"]) for r in rows], [("1.1.1", "prose"), ("1.1.2", "verse")])
            rows = [json.loads(x) for x in (Path(d) / "MBh01_0002.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([(r["verse_ref"], r["text_type"]) for r in rows], [("1.3.1", "prose"), ("1.3.2", "prose")])

    def test_it_says_what_it_did_not_read(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "mbh_01_u.htm"
            src.write_text(BOOK, encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "import_mbh_gretil.py"), "--book", "1", "--src", str(src),
                                "--out", str(Path(d) / "out"), "--dry-run"], capture_output=True, text=True,
                               encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("of them prose: 4 lines in 3 passages (MBH_PROSE_2026_10_14)", r.stdout)
            self.assertIn("NOT READ: 2 lines that look like a reference (the first: 01,003.003a)", r.stdout)
            self.assertFalse((Path(d) / "out" / "MBh01_0001.jsonl").exists(), "a dry run")

    def test_before_the_patch_the_prose_was_lost(self):
        baks = sorted(SCRIPTS.glob("import_mbh_gretil.py.bak_mbhprose_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        with tempfile.TemporaryDirectory() as d:
            shutil.copy2(baks[0], Path(d) / "import_mbh_old.py")
            old = load("import_mbh_old", Path(d) / "import_mbh_old.py")
        ch = old.parse(BOOK, 1)
        self.assertEqual(sorted(ch[1]), [2], "1.1.1 was passed over")
        self.assertEqual(ch[3], {1: ["s\u016bta uv\u0101ca"]}, "the speaker's line was kept, its prose was not")


@unittest.skipUnless(HAVE_IT, "indic_transliteration is not installed")
class TheReingest(unittest.TestCase):
    def test_no_segment_keeps_the_verses_and_brings_the_prose_in(self):
        m = load("import_mbh_prose2", SCRIPTS / "import_mbh_gretil.py")
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            old_book = "\n".join(l for l in BOOK.splitlines() if "001.001" not in l)   # as it went in: no prose
            (t / "a").mkdir(); (t / "b").mkdir()
            m.write_jsonl(m.parse(old_book, 1), 1, t / "a", "MBhT", False)
            m.write_jsonl(m.parse(BOOK, 1), 1, t / "b", "MBhT", False)
            import db_utils
            db = t / "context.db"
            con = sqlite3.connect(str(db)); db_utils.ensure_schema(con); con.close()
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "ingest_jsonl_fast.py"), "--doc", "MBhT", "--db", str(db),
                                "--glob", str(t / "a" / "MBhT_*.jsonl"), "--no-segment", "--no-iast"],
                               capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(t))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            con = sqlite3.connect(str(db))
            con.execute("UPDATE passages SET translation = 'kept English //' WHERE verse_ref = '1.1.2'")
            con.commit()
            before = con.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
            con.close()
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "reingest_pages.py"), "--doc", "MBhT", "--db",
                                             str(db), "--merged-dir", str(t / "b")] + list(a), capture_output=True,
                                            text=True, encoding="utf-8", env=env, cwd=str(t))
            r = run("--no-segment")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("VERDICT: 1 of 2 pages differ from the database: 0 passages go (English 0, Hindi 0), 1 come in "
                          "untranslated, 1 stay (1 moved on their page)", r.stdout)
            self.assertIn("--merged-dir %s --no-segment" % (t / "b"), r.stdout, "the NEXT line says where it read")
            con = sqlite3.connect(str(db))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM passages").fetchone()[0], before, "a plan writes nothing")
            con.close()


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_mbh_prose_2026_10_14.py", Path(__file__), SCRIPTS / "reingest_pages.py"):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"MBH_PROSE_2026_10_14", b)
        self.assertIn(b"MBH_PROSE_2026_10_14", (SCRIPTS / "import_mbh_gretil.py").read_bytes())


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_mbhprose_*")) for f in ("import_mbh_gretil.py", "reingest_pages.py")}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_mbh_prose_2026_10_14.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in baks:
                self.assertEqual((t / "scripts" / f).read_bytes(), (SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "import_mbh_gretil.py"
            p.write_bytes(p.read_bytes() + b"\r\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("is not the file this patch was made for", r.stdout)
            self.assertNotIn(b"MBH_PROSE", (t / "scripts" / "reingest_pages.py").read_bytes(), "all or nothing")


if __name__ == "__main__":
    unittest.main()
