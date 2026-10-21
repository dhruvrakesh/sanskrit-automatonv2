# -*- coding: ascii -*-
"""CLAIMS_FIX_2026_10_21: a reply with the scan's own backslashes in a quotation (l\\Iahabharata) is read, its backslashes
kept; --reparse reads a failed page again from its stored reply, free, and only once; every attempt's cost stays on the
page's read; cites-v2 reads the scan's misread cites (Visht}u Puralfa, RamayaQ.a, 1\\fatsya), the Jatakas by name, the
modern works, Ibid, the place from its first number with its brackets balanced, and leaves unread a place the work cannot
have; --recite reads the stored cites again; --show puts the Purana Index first. The model is a stub. Temp files only."""
import contextlib, io, json, os, shutil, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "CLAIMS_FIX_2026_10_21"
HERE = MARK.encode() in (SCRIPTS / "scholar_claims.py").read_bytes()
PAGE = ("The Matsya Purana says (Mat. 50. 57) that Janamejaya, the son of Parikshit, was the king of the Kurus, and "
        "l\\Iahabharata (I. 95. 85) names his mother.")
BAD = ('{"claims": [{"subject": "Janamejaya", "relation": "son_of", "object": "Parik\\u1e63it", "claim": "Janamejaya was '
       'the son of Parikshit.", "quote": "and l\\Iahabharata (I. 95. 85) names his mother", "cites": ["1\\fatsya, 50. 57", '
       '"ib. 58"], "stance": "reports", "hedge": "", "who": ""}]}')


def ns(text, pin=1000, pout=800):
    n = types.SimpleNamespace
    return n(text=text, candidates=[n(finish_reason="STOP")],
             usage_metadata=n(prompt_token_count=pin, candidates_token_count=pout, thoughts_token_count=0,
                              total_token_count=pin + pout))


@unittest.skipUnless(HERE, "CLAIMS_FIX_2026_10_21 is not here")
class TheReading(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C = C

    def test_the_scan_s_backslashes(self):
        got = self.C.parse_reply(BAD)
        self.assertEqual(got[0]["quote"], "and l\\Iahabharata (I. 95. 85) names his mother")
        self.assertEqual(got[0]["cites"][0], "1\\fatsya, 50. 57")
        self.assertEqual(got[0]["object"], "Parik\u1e63it", "a JSON escape is read as JSON means it")
        self.assertEqual(self.C.parse_reply('{"claims": [{"q": "a\\\\b \\"c\\" \\n"}]}')[0]["q"], 'a\\b "c" \n')

    def test_cites_v2(self):
        rc = lambda t, ctx="", prev="": self.C.read_cite(t, ctx, prev)
        V = "Vi\u1e63\u1e47u Pur\u0101\u1e47a"
        self.assertEqual((rc("Visht}u Puralfa IV. 3. 5")["work"], rc("Visht}u Puralfa IV. 3. 5")["locus"]), (V, "IV. 3. 5"))
        self.assertEqual(rc("VishJfU Puralfa IV. 20. I")["work"], V)
        self.assertEqual(rc("RamayaQ.a, II. 9. 22")["work"], "R\u0101m\u0101ya\u1e47a")
        self.assertEqual(rc("1\\fatsya, 50. 57")["work"], "Matsya Pur\u0101\u1e47a")
        self.assertEqual(rc("Vayu (89. 18-23)")["locus"], "89. 18-23", "the bracket it does not open taken away")
        self.assertEqual((rc("Ghata Jataka (No. 454)")["work"], rc("Ghata Jataka (No. 454)")["locus"]), ("J\u0101taka", "454"))
        r = rc("Satapatha BrahmaQ.as")
        self.assertEqual((r["work"], r["locus"]), ("\u015aatapatha Br\u0101hma\u1e47a", ""), "no number: no place")
        self.assertEqual(rc("Aitareya BrahmaQ.a (VIII. 21)")["locus"], "VIII. 21")
        self.assertEqual(rc("Carmichael Lee., p. 63")["work"], "D. R. Bhandarkar, Carmichael Lectures, 1918")
        self.assertEqual(rc("Majumdar, Corporate Life in Ancient India, p. 119")["work"],
                         "R. C. Majumdar, Corporate Life in Ancient India")
        r = rc("ib. 67", prev="Vedic Index")
        self.assertEqual((r["work"], r["how"], r["locus"]), ("Vedic Index", "ibid", "67"))
        self.assertEqual(rc("Matsyas and Chedis")["work"], "", "the Matsyas are a people")
        self.assertEqual(rc("II.68.13", "Panini names Hastinapura")["work"], "", "no sutra of Panini is numbered so")
        self.assertEqual(rc("VI. 2. 101", "Panini names Hastinapura")["work"], "A\u1e63\u1e6d\u0101dhy\u0101y\u012b")
        self.assertEqual(rc("Mbb. I. 63")["book"], "i")
        self.assertEqual(self.C.ours_of("M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a", "")[0], "markandeya_purana__w_gretil")
        self.assertEqual(rc("Sat. Br. XIII. 5. 4. 1-3")["how"], "cite")
        self.assertEqual(rc("Hopkins, The Great Epic of India, p. 385")["work"], "E. W. Hopkins, The Great Epic of India")


@unittest.skipUnless(HERE, "CLAIMS_FIX_2026_10_21 is not here")
class TheRun(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C, self.W = C, C.WORKS["phai1923"]
        self.tmp = Path(tempfile.mkdtemp(prefix="cfix_"))
        self.cdb, self.db = str(self.tmp / "claims.db"), str(self.tmp / "context.db")
        con = sqlite3.connect(self.db)
        con.executescript("CREATE TABLE shelf_entries(id INTEGER PRIMARY KEY, source TEXT, lnum INTEGER, page TEXT, "
                          "name TEXT, homonym TEXT, body TEXT);"
                          "INSERT INTO shelf_entries VALUES (1, 'vei', 1009, '1-273', 'Janamejaya', '1', 'a king');"
                          "INSERT INTO shelf_entries VALUES (2, 'pui', 4954, '1-623', 'Janamejaya', 'I', 'son of Pariksit');")
        con.commit(); con.close()
        con = C.open_store(self.cdb)
        C.store_pages(con, "phai1923", self.W, [(19, PAGE), (20, PAGE + " Again.")], "made-up")
        con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *args, stub=None):
        buf, cwd = io.StringIO(), os.getcwd()
        try:
            with contextlib.redirect_stdout(buf):
                rc = self.C.main(["--claims-db", self.cdb, "--db", self.db] + list(args), caller=stub)
        finally:
            os.chdir(cwd)
        return rc, buf.getvalue()

    def test_reparse_the_cost_and_recite(self):
        calls = []

        def stub(system, prompt):
            calls.append(prompt)
            page2 = "The page: 2 " in prompt
            return ns("not json at all {" if page2 and len(calls) < 4 else BAD)
        rc, out = self.run_main("--pages", "1-2", "--yes", stub=stub)
        self.assertEqual(rc, 0, out)
        con = sqlite3.connect(self.cdb)
        reads = con.execute("SELECT pdf_page, status, claims, round(cost_usd, 6), note FROM claim_reads ORDER BY id").fetchall()
        self.assertEqual([(r[0], r[1], r[2]) for r in reads], [(19, "ok", 1), (20, "ok", 1)], "the scan's backslashes read")
        one = round(1000 * 0.30 / 1e6 + 800 * 2.50 / 1e6, 6)
        self.assertEqual(reads[0][3], one)
        self.assertEqual(reads[1][3], round(3 * one, 6), "every attempt's cost on the page's read")
        self.assertEqual(reads[1][4], "after 3 attempt(s)")
        cites = con.execute("SELECT printed, work, locus, how, reader FROM claim_cites ORDER BY rowid").fetchall()
        self.assertEqual(cites[0][1:], ("Matsya Pur\u0101\u1e47a", "50. 57", "cite", "cites-v2"))
        self.assertEqual(cites[1][1:4], ("Matsya Pur\u0101\u1e47a", "58", "ibid"))
        con.execute("UPDATE claim_cites SET work = NULL, how = NULL, reader = NULL")
        con.execute("INSERT INTO claim_reads(work, pdf_page, page_sha256, prompt_version, engine, status, claims, cost_usd, raw, "
                    "error, at) SELECT work, pdf_page, sha256, 'claims-v1', 'gemini:gemini-2.5-flash', 'failed', 0, 0.01, ?, "
                    "'the reply is not the JSON asked for', 'x' FROM claim_pages WHERE pdf_page = 20", (BAD,))
        con.commit(); con.close()
        rc, out = self.run_main("--recite")
        self.assertIn("4 cite(s) read again", out, "the current reads: the last read of each page that is ok")
        rc, out = self.run_main("--reparse")
        self.assertIn("VERDICT: 1 page(s) read again from their stored replies, free; 0 left", out)
        rc, out = self.run_main("--reparse")
        self.assertIn("VERDICT: 0 page(s) read again", out, "only once")
        con = sqlite3.connect(self.cdb)
        last = con.execute("SELECT status, cost_usd, note FROM claim_reads ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        self.assertEqual(last[:2], ("ok", 0.0))
        self.assertIn("reparsed from read", last[2])
        rc, out = self.run_main("--show", "Janamejaya")
        self.assertLess(out.index("PUI 4954"), out.index("VEI 1009"), "the Purana Index first")
        self.assertIn("PUI: V. R. Ramachandra Dikshitar, The Purana Index", out)
        rc, out = self.run_main("--report")
        self.assertIn("the meter (usage_log, every call): 4 call(s)", out)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_claims_fix_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)

    FILES = ("scripts/scholar_claims.py", "tests/test_scholar_claims_2026_10_21.py")

    def test_it_applies_once_to_what_it_found(self):
        import subprocess
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimsfix_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_claimsfix_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_claims_fix_2026_10_21.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:   # CLAIMS_LINK_2026_10_21 came after: its backup is what this patch made
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimslink_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])
            p = t / "scripts" / "scholar_claims.py"
            p.write_bytes(p.read_bytes().replace(b"def read_cite(printed: str, context: str = \"\") -> dict:",
                                                 b"def read_cite(printed, context=\"\"):"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 1 found 0 times", r.stdout)

if __name__ == "__main__":
    unittest.main()
