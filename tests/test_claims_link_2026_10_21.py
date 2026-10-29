# -*- coding: ascii -*-
"""CLAIMS_LINK_2026_10_21: --link ties the names of the current claims to our entities, in tiers (exact by the shelf's
key, a variant our texts record, a vowel's length, a 1923 spelling without diacritics, a numbered namesake, an English
plural), never a common English word, never Arittha to Artha, Vajji to Vaji or the Gandharis to Gandhari; a name that
could be more than one of ours keeps each, and our own doubles are listed; a run replaces the work's ties; --show,
--report and --csv use them; the context database is only read. Nothing is called. Temp files only; made-up rows."""
import contextlib, hashlib, io, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "CLAIMS_LINK_2026_10_21"
HERE = MARK.encode() in (SCRIPTS / "scholar_claims.py").read_bytes()

ENTS = [(1, "Parik\u1e63it", "person"), (2, "\u1e5agveda", "other"), (3, "\u015aatapatha Br\u0101hma\u1e47a", "other"),
        (4, "\u015aatapathabr\u0101hma\u1e47a", "other"), (5, "Malla", "people"), (6, "Hari\u015bcandra", "person"),
        (7, "Artha", "other"), (8, "K\u0101\u015b\u012b", "place"), (9, "Bh\u012bmasena", "person"),
        (10, "G\u0101ndh\u0101r\u012b", "person"), (11, "V\u0101j\u012b", "other"), (12, "Kaca", "person"),
        (13, "Janamejaya", "person"), (14, "K\u0101\u015bi", "place")]
VARIANTS = [(6, "king"), (1, "Par\u012bk\u1e63ita")]
PAGE = "Parikshit was the father of Janamejaya, and Kasi was a kingdom; the king is named in the Satapatha Brahmana."


def context_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("CREATE TABLE entities(id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT, notes TEXT, created_at TEXT);"
                      "CREATE TABLE entity_variants(entity_id INTEGER, variant TEXT);"
                      "CREATE TABLE entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER);")
    con.executemany("INSERT INTO entities(id, canonical, kind) VALUES (?,?,?)", ENTS)
    con.executemany("INSERT INTO entity_variants VALUES (?,?)", VARIANTS)
    con.executemany("INSERT INTO entity_mentions(entity_id) VALUES (?)", [(1,), (1,), (1,), (13,)])
    con.commit()
    con.close()


def claim(subject, obj, text="a claim"):
    return {"subject": subject, "subject_printed": "", "relation": "other", "object": obj, "claim": text,
            "quote": "Parikshit was the father of Janamejaya, and Kasi was a kingdom", "cites": [], "stance": "asserts",
            "hedge": "", "who": ""}


@unittest.skipUnless(HERE, "CLAIMS_LINK_2026_10_21 is not here")
class TheTies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import scholar_claims as C
        cls.C = C
        cls.tmp = Path(tempfile.mkdtemp(prefix="claimslink_"))
        context_db(cls.tmp / "context.db")
        cls.idx, cls.ents, cls.nvar = C.entity_index(str(cls.tmp / "context.db"), False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_1923_spelling_key(self):
        C = self.C
        self.assertEqual(C.skey("Rigveda"), C.skey("\u1e5agveda"))
        self.assertEqual(C.skey("Kurukshetra"), C.skey("Kuruk\u1e63etra"))
        self.assertEqual(C.skey("Chhandogya"), C.skey("Ch\u0101ndogya"))
        self.assertNotEqual(C.skey("Arittha"), C.skey("Artha"), "pkey has them one")
        self.assertNotEqual(C.skey("Vajji"), C.skey("V\u0101j\u012b"), "doubled letters kept")

    def test_the_tiers(self):
        t = lambda n: self.C.tie(n, self.idx)
        self.assertEqual(self.nvar, 2)
        self.assertEqual(t("Parik\u1e63it"), ("exact", [1]))
        self.assertEqual(t("Parik\u1e63it I"), ("numbered exact", [1]))
        self.assertEqual(t("Par\u012bk\u1e63ita"), ("variant", [1]))
        self.assertEqual(t("par\u012bk\u1e63ita"), ("", []), "a variant only for a name with a capital")
        self.assertEqual(t("Rigveda"), ("spelling", [2]))
        self.assertEqual(t("\u015aatapatha Br\u0101hma\u1e47a"), ("exact", [3, 4]), "each kept: our own doubles")
        self.assertEqual(t("Mallas"), ("plural exact", [5]))
        self.assertEqual(t("Bhimasena"), ("loose", [9]))
        self.assertEqual(t("Kasi"), ("spelling", [8, 14]))
        for n in ("king", "King", "Kings", "Arittha", "Gandharis", "Vajji", "Kachchha", "Brahmadatta", "Ki"):
            self.assertEqual(t(n), ("", []), n)


@unittest.skipUnless(HERE, "CLAIMS_LINK_2026_10_21 is not here")
class TheRun(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C, self.W = C, C.WORKS["phai1923"]
        self.tmp = Path(tempfile.mkdtemp(prefix="claimslink_"))
        self.cdb, self.db = str(self.tmp / "claims.db"), str(self.tmp / "context.db")
        context_db(Path(self.db))
        con = C.open_store(self.cdb)
        C.store_pages(con, "phai1923", self.W, [(19, PAGE)], "made-up")
        self.pg = con.execute("SELECT pdf_page, printed, text, sha256 FROM claim_pages WHERE pdf_page = 19").fetchone()
        C.save_read(con, "phai1923", self.W, self.pg, "gemini:stub", "ok",
                    [C.clean_claim(x) for x in (claim("Parik\u1e63it I", "Janamejaya"), claim("Parik\u1e63it", "Kasi"),
                                                claim("king", "\u015aatapatha Br\u0101hma\u1e47a"),
                                                claim("Brahmadatta", ""))], 0.0, None, "{}")
        con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *args):
        buf, cwd = io.StringIO(), os.getcwd()
        try:
            with contextlib.redirect_stdout(buf):
                rc = self.C.main(["--claims-db", self.cdb, "--db", self.db] + list(args))
        finally:
            os.chdir(cwd)
        return rc, buf.getvalue()

    def sha(self):
        return hashlib.sha256(Path(self.db).read_bytes()).hexdigest()

    def test_link_show_report_csv(self):
        before = self.sha()
        rc, out = self.run_main("--show", "Parikshit")
        self.assertIn("ours: entity 1 Parik\u1e63it (person), named 3 time(s) in our texts\n", out, "before --link: as before")
        rc, out = self.run_main("--report")
        self.assertIn("our names: not tied yet", out)
        rc, out = self.run_main("--link")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 5 of 7 name(s) on the claims of", out)
        self.assertIn("(7 tie row(s)), free; 2 untied", out)
        self.assertIn("\u015aatapatha Br\u0101hma\u1e47a [3] / \u015aatapathabr\u0101hma\u1e47a [4] (1 name(s))", out)
        self.assertIn("untied, most named: Brahmadatta 1, king 1", out)
        con = sqlite3.connect(self.cdb)
        links = con.execute("SELECT name, entity_id, how, cands FROM claim_links ORDER BY rowid").fetchall()
        self.assertEqual(links, [("Parik\u1e63it I", 1, "numbered exact", 1), ("Janamejaya", 13, "exact", 1),
                                 ("Parik\u1e63it", 1, "exact", 1), ("Kasi", 8, "spelling", 2), ("Kasi", 14, "spelling", 2),
                                 ("\u015aatapatha Br\u0101hma\u1e47a", 3, "exact", 2),
                                 ("\u015aatapatha Br\u0101hma\u1e47a", 4, "exact", 2)])
        run = con.execute("SELECT names, tied, many, max_claim, linker, mark FROM claim_link_runs").fetchall()
        top = con.execute("SELECT MAX(id) FROM claims").fetchone()[0]
        con.close()
        self.assertEqual(run, [(7, 5, 2, top, "link-v1", MARK)])
        rc, out = self.run_main("--link")
        con = sqlite3.connect(self.cdb)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM claim_links").fetchone()[0], 7, "a run replaces the ties")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM claim_link_runs").fetchone()[0], 2)
        con.close()
        rc, out = self.run_main("--show", "Parikshit")
        self.assertIn("ours: entity 1 Parik\u1e63it (person), named 3 time(s) in our texts; tied (exact) on 1 claim(s); "
                      "also tied: Parik\u1e63it I 1", out)
        rc, out = self.run_main("--report")
        self.assertIn("5 of 7 name(s) tied; 2 to more than one", out)
        self.assertIn("how: exact 3, numbered exact 1, spelling 1", out)
        self.assertIn("the most claimed of ours: Parik\u1e63it (person) 2, Janamejaya (person) 1", out)
        self.assertNotIn("read since the ties", out)
        csvp = self.tmp / "c.csv"
        rc, out = self.run_main("--csv", str(csvp))
        rows = csvp.read_text(encoding="utf-8-sig").splitlines()
        self.assertTrue(rows[0].endswith(",ours,our_names"))
        self.assertIn("Parik\u1e63it (1; numbered exact); Janamejaya (13; exact)", rows[1])
        self.assertEqual(self.sha(), before, "the context database only read")
        con = self.C.open_store(self.cdb)
        self.C.save_read(con, "phai1923", self.W, self.pg, "gemini:stub", "ok", [self.C.clean_claim(claim("Janaka", ""))],
                         0.0, None, "{}")
        con.close()
        rc, out = self.run_main("--report")
        self.assertIn("1 claim(s) read since the ties were made: python scripts\\scholar_claims.py --link", out)

    def test_no_context_db(self):
        os.remove(self.db)
        rc, out = self.run_main("--link")
        self.assertEqual(rc, 1)
        self.assertIn("not found: our entities live there", out)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_claims_link_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    FILES = ("scripts/scholar_claims.py", "tests/test_claims_fix_2026_10_21.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimslink_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_claimslink_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_claims_link_2026_10_21.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:   # CLAIMS_PART2_2026_10_28 came after: its backup is what this patch made
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimspart2_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])
            p = t / "scripts" / "scholar_claims.py"
            p.write_bytes(p.read_bytes().replace(b"def show_name(a, con, code: str, work: dict) -> int:",
                                                 b"def show_name(a, con, code, work):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 3 found 0 times", r.stdout)
            self.assertIn("Nothing written.", r.stdout)


if __name__ == "__main__":
    unittest.main()
