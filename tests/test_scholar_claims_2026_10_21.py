# -*- coding: ascii -*-
"""CLAIMS_2026_10_21: scholar_claims.py reads a scholar's book into claims, page by page: the printed page numbers
(Part I's Foreword i-v, then pdf - 18), the quotation checked against the page's own text (exact, close for the OCR's
misreadings, none), the cites read into the works they name and whether our corpus holds that place (the
Mahabharata's book i only; the Satapatha's book xiv only), the Vedic Index's page, names keyed across the 1923
spellings; the plan sends nothing; a read is metered, stored and not made again; a failed page is read again on the
next run; --max-usd stops a run. The model is a stub: nothing is sent. Temp files only; made-up pages."""
import contextlib, io, json, os, shutil, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "CLAIMS_2026_10_21"
HERE = (SCRIPTS / "scholar_claims.py").exists()

PAGES = {
    19: "THE AGE OF THE PARIKSHITAS.\nWe have taken as our starting point the reign of Parikshit whose accession, "
        "according to tradition, took place shortly after the Bharata war.",
    20: "Janamejaya, the son of the Vedic Parikshit, is mentioned in the Satapatha Brahma1;1a as a performe'r of the "
        "Asvamedha (Sat. Br. XIII. 5. 4. 1-3). The priest who performed the sacrifice for him was Indrota Daivapa "
        "Saunaka.",
    21: "Yajnavalkya taught Janaka of Videha, as the Brihadaranyaka Upanishad tells (Brih. Up. III. 1. 1).",
}


def reply(claims):
    ns = types.SimpleNamespace
    return ns(text=json.dumps({"claims": claims}), candidates=[ns(finish_reason="STOP")],
              usage_metadata=ns(prompt_token_count=1000, candidates_token_count=500, thoughts_token_count=300,
                                total_token_count=1800))


CANNED = {
    "1 (as": [],
    "2 (as": [{"subject": "Janamejaya", "subject_printed": "Janamejaya", "relation": "performed", "object": "A\u015bvamedha",
               "claim": "Janamejaya, son of the Vedic Parik\u1e63it, performed the horse sacrifice, as the \u015aatapatha says.",
               "quote": "Janamejaya, the son of the Vedic Parikshit, is mentioned in the Satapatha Brahmana as a performer",
               "cites": ["Sat. Br. XIII. 5. 4. 1-3"], "stance": "reports", "hedge": "", "who": ""},
              {"subject": "Indrota Daivapa \u015aaunaka", "relation": "priest_of", "object": "Janamejaya",
               "claim": "Indrota Daivapa \u015aaunaka was the priest of Janamejaya's horse sacrifice.",
               "quote": "The priest who performed the sacrifice for him was Indrota Daivapa Saunaka",
               "cites": "Sat. Br. XIII. 5. 4. 1; Ved. Ind. I. 76", "stance": "asserted", "hedge": "", "who": ""},
              {"subject": "", "claim": "no subject: dropped"},
              {"subject": "Janamejaya", "relation": "conquered", "object": "Taxila", "claim": "He conquered Taxila.",
               "quote": "the king conquered the city of Taxila in the north with a great army", "cites": [],
               "stance": "doubts", "hedge": "", "who": ""}],
    "3 (as": [{"subject": "Y\u0101j\u00f1avalkya", "relation": "teacher_of", "object": "Janaka",
               "claim": "Y\u0101j\u00f1avalkya taught Janaka of Videha.", "quote": "Yajnavalkya taught Janaka of Videha, as the",
               "cites": ["Brih. Up. III. 1. 1", "Sat. Br. XIV. 6. 1. 1"], "stance": "asserts", "hedge": "", "who": ""}],
}


class Stub:
    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def __call__(self, system, prompt):
        page = prompt.split("The page: ", 1)[1].split(")", 1)[0] + ")"
        key = page.split(" ")[0] + " (as"
        self.calls.append(key)
        if key in self.fail:
            raise TimeoutError("timed out")
        return reply(CANNED[key])


@unittest.skipUnless(HERE, "scholar_claims.py is not here")
class TheHelpers(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C, self.W = C, C.WORKS["phai1923"]

    def test_the_pages(self):
        C, W = self.C, self.W
        self.assertEqual([C.printed_of(W, n) for n in (13, 14, 18, 19, 112)], ["", "i", "v", "1", "94"])
        self.assertEqual(C.parse_pages(W, "1-3"), [19, 20, 21])
        self.assertEqual(C.parse_pages(W, "i-v,94"), [14, 15, 16, 17, 18, 112])
        with self.assertRaises(ValueError):
            C.parse_pages(W, "vi")

    def test_the_quotation(self):
        C = self.C
        self.assertEqual(C.quote_check("names Tura Kavasheya as his priest", "the Aitareya names Tura Kavasheya as his "
                                       "priest. 'l'he")[0], "exact")
        chk, score = C.quote_check("mentioned in the Satapatha Brahmana as a performer of the Asvamedha", PAGES[20])
        self.assertEqual(chk, "close")
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(C.quote_check("the king conquered the city of Taxila in the north", PAGES[20])[0], "none")
        self.assertEqual(C.quote_check("too short", PAGES[20])[0], "short")
        self.assertEqual(C.quote_check("the son of Abhimanyu says", "the son of Abhi\u00ad\nmanyu, says")[0], "exact")

    def test_the_cites(self):
        C = self.C
        r = C.read_cite("Sat. Br. XIII. 5. 4. 1-3")
        self.assertEqual((r["work"], r["locus"], r["book"]), ("\u015aatapatha Br\u0101hma\u1e47a", "XIII. 5. 4. 1-3", "xiii"))
        self.assertEqual(C.ours_of(r["work"], r["book"])[0], "", "ours is book xiv only")
        self.assertEqual(C.ours_of("\u015aatapatha Br\u0101hma\u1e47a", "xiv")[0], "2015_405693_Shatpath-Brahmanam")
        self.assertEqual(C.ours_of("Mah\u0101bh\u0101rata", "i")[0], "MBh01")
        self.assertEqual(C.ours_of("Mah\u0101bh\u0101rata", "xii")[0], "", "ours is the critical edition's book 1")
        self.assertEqual(C.vei_page(C.read_cite("Ved. Ind., Vol. II, p. 12")), "2-012")
        self.assertEqual(C.read_cite("Asvalayana Grihya Sutra III. 4")["locus"], "III. 4")
        self.assertEqual(C.read_cite("I. 95. 85", "the Mahabharata says")["how"], "sentence")
        self.assertEqual(C.read_cite("Hopkins, The Great Epic of India, p. 385", "the Mahabharata says")["work"], "",
                         "a modern work, not the text the sentence names")
        self.assertEqual(C.read_cite("Mat. 50. 57")["work"], "Matsya Pur\u0101\u1e47a")
        self.assertEqual(C.read_cite("Matsyas and Chedis", "")["work"], "", "the Matsyas are a people")

    def test_the_names_and_the_reply(self):
        C = self.C
        for a_, b_ in (("Parikshit", "Parik\u1e63it"), ("Chhandogya", "Ch\u0101ndogya"), ("Rig-Veda", "\u1e5agveda"),
                       ("Panchala", "Pa\u00f1c\u0101la"), ("Krishna", "K\u1e5b\u1e63\u1e47a")):
            self.assertEqual(C.pkey(a_), C.pkey(b_), a_)
        self.assertNotEqual(C.pkey("Janaka"), C.pkey("Janamejaya"))
        self.assertEqual(C.parse_reply('Here: {"claims": [{"subject": "x"}]} done'), [{"subject": "x"}])
        self.assertIsNone(C.parse_reply("no json"))
        c = C.clean_claim({"subject": "Kuru", "claim": "x", "relation": "ruled", "stance": "?", "cites": "A. 1; B. 2"})
        self.assertEqual((c["relation"], c["stance"], c["cites"]), ("other", "asserts", ["A. 1", "B. 2"]))
        self.assertIsNone(C.clean_claim({"subject": "", "claim": "x"}))
        self.assertIn("son_of", C.SYSTEM)
        self.assertNotIn("RELATIONS", C.SYSTEM)


@unittest.skipUnless(HERE, "scholar_claims.py is not here")
class TheRun(unittest.TestCase):
    def setUp(self):
        import scholar_claims as C
        self.C, self.W = C, C.WORKS["phai1923"]
        self.tmp = Path(tempfile.mkdtemp(prefix="claims_"))
        self.cdb = str(self.tmp / "claims.db")
        self.db = str(self.tmp / "context.db")
        sqlite3.connect(self.db).close()
        con = C.open_store(self.cdb)
        C.store_pages(con, "phai1923", self.W, sorted(PAGES.items()), "made-up")
        con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *args, stub=None):
        buf = io.StringIO()
        cwd = os.getcwd()
        try:
            with contextlib.redirect_stdout(buf):
                rc = self.C.main(["--claims-db", self.cdb, "--db", self.db] + list(args), caller=stub)
        finally:
            os.chdir(cwd)
        return rc, buf.getvalue()

    def test_the_plan_sends_nothing_and_yes_reads(self):
        stub = Stub()
        rc, out = self.run_main("--pages", "1-3", stub=stub)
        self.assertEqual(rc, 0, out)
        self.assertIn("pages asked: 3 (printed 1 to 3); read already 0; to read 3", out)
        self.assertIn("3 page(s) of Raychaudhuri", out)
        self.assertEqual(stub.calls, [])
        rc, out = self.run_main("--pages", "1-3", "--yes", stub=stub)
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 3 page(s) of Raychaudhuri, Political History of Ancient India (1923) read: 4 claim(s); 0 failed", out)
        con = sqlite3.connect(self.cdb)
        rows = con.execute("SELECT printed, subject, relation, stance, quote_check FROM claims ORDER BY pdf_page, n").fetchall()
        self.assertEqual([(r[0], r[2], r[3], r[4]) for r in rows],
                         [("2", "performed", "reports", "close"), ("2", "priest_of", "asserts", "exact"),
                          ("2", "other", "doubts", "none"), ("3", "teacher_of", "asserts", "exact")])
        cites = con.execute("SELECT x.printed, x.work, x.book, x.ours, x.vei_page FROM claim_cites x ORDER BY x.claim_id, x.n").fetchall()
        self.assertIn(("Ved. Ind. I. 76", "Vedic Index", "i", None, "1-076"), cites)
        self.assertIn(("Sat. Br. XIV. 6. 1. 1", "\u015aatapatha Br\u0101hma\u1e47a", "xiv", "2015_405693_Shatpath-Brahmanam", None), cites)
        self.assertIn(("Sat. Br. XIII. 5. 4. 1-3", "\u015aatapatha Br\u0101hma\u1e47a", "xiii", None, None), cites)
        reads = con.execute("SELECT pdf_page, status, claims, cost_usd > 0 FROM claim_reads ORDER BY pdf_page").fetchall()
        self.assertEqual(reads, [(19, "ok", 0, 1), (20, "ok", 3, 1), (21, "ok", 1, 1)])
        con.close()
        m = sqlite3.connect(self.db)
        self.assertEqual(m.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'claims'").fetchone()[0], 3, "metered")
        m.close()
        n = len(stub.calls)
        rc, out = self.run_main("--pages", "1-3", "--yes", stub=stub)
        self.assertIn("every page asked is read already", out)
        self.assertEqual(len(stub.calls), n, "a page read is not read again")
        rc, out = self.run_main("--show", "Janamejaya")
        self.assertIn("p. 2 (pdf 20) [reports] Janamejaya performed A\u015bvamedha", out)
        self.assertIn("quote (close", out)
        self.assertIn("VERDICT: 3 claim(s) on Janamejaya on 1 page(s) (2)", out)
        rc, out = self.run_main("--show", "Parikshit")
        self.assertIn("no claim of", out)
        rc, out = self.run_main("--report")
        self.assertIn("claims: 4 from 3 page(s) read (2 with a claim); quotations exact 2, close 1, not on the page 1", out)
        self.assertIn("to check against our texts (2):", out)
        self.assertIn("quotations not on the page", out)
        csvp = self.tmp / "c.csv"
        rc, out = self.run_main("--csv", str(csvp))
        self.assertEqual(len(csvp.read_text(encoding="utf-8-sig").splitlines()), 5)

    def test_a_failed_page_is_read_again(self):
        stub = Stub(fail={"2 (as"})
        rc, out = self.run_main("--pages", "1-3", "--yes", stub=stub)
        self.assertEqual(rc, 1, out)
        self.assertIn("1 failed", out)
        self.assertEqual(stub.calls.count("2 (as"), 4, "tried four times")
        con = sqlite3.connect(self.cdb)
        self.assertEqual(con.execute("SELECT status FROM claim_reads WHERE pdf_page = 20").fetchone()[0], "failed")
        con.close()
        m = sqlite3.connect(self.db)
        self.assertEqual(m.execute("SELECT COUNT(*) FROM usage_log WHERE kind = 'claims'").fetchone()[0], 2,
                         "a call that failed is not billed")
        m.close()
        stub2 = Stub()
        rc, out = self.run_main("--pages", "1-3", "--yes", stub=stub2)
        self.assertEqual(rc, 0, out)
        self.assertEqual(stub2.calls, ["2 (as"])

    def test_the_limits(self):
        stub = Stub()
        rc, out = self.run_main("--pages", "1-3", "--yes", "--max-usd", "0", stub=stub)
        self.assertEqual(rc, 1, out)
        self.assertIn("stopped: --max-usd 0.00 reached", out)
        self.assertEqual(stub.calls, [])
        rc, out = self.run_main("--pages", "1-3", "--yes", "--model", "claude-sonnet-5-5", stub=stub)
        self.assertEqual(rc, 2)
        rc, out = self.run_main("--pages", "vi", stub=stub)
        self.assertIn("not a page the book prints: vi", out)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "scholar_claims.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
