# -*- coding: ascii -*-
"""COST_RATIO_2026_10_05. Fails before patch_cost_ratio_2026_10_05.py, passes after."""
import importlib, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
V = "gemini-vision:gemini-2.5-flash"


def _db(d):
    import db_utils, cost_tracker
    db = str(Path(d) / "t.db")
    con = sqlite3.connect(db); db_utils.ensure_schema(con); cost_tracker.ensure_usage_schema(con)
    ins = ("INSERT INTO usage_log(kind, doc, engine, in_tokens, out_tokens, cost_usd, passages, ok, token_source)"
           " VALUES('ocr_vision', ?, ?, ?, ?, 0, ?, 1, 'provider')")
    for _ in range(20):                                   # BIG: 20 delivered pages, dear
        con.execute(ins, ("BIG", V, 2000, 2000, 1))
    for _ in range(10):                                   # BIG: 10 ladder attempts, billed, no page
        con.execute(ins, ("BIG", V, 400, 1000, 0))
    for _ in range(25):                                   # SMALL: cheap pages
        con.execute(ins, ("SMALL", V, 1000, 300, 1))
    con.commit(); con.close()
    return db


def usd(i, o):
    return (i * 0.30 + o * 2.50) / 1e6


class Ratio(unittest.TestCase):
    def test_zero_page_calls_count_and_each_text_has_its_own_rate(self):
        import ocr_consensus as oc
        importlib.reload(oc)
        with tempfile.TemporaryDirectory() as d:
            db = _db(d)
            big = (20 * usd(2000, 2000) + 10 * usd(400, 1000)) / 20
            small = usd(1000, 300)
            self.assertAlmostEqual(oc.measured_cost_per_page(db, doc="BIG"), big, places=9)
            self.assertAlmostEqual(oc.measured_cost_per_page(db, doc="SMALL"), small, places=9)
            corpus = (20 * usd(2000, 2000) + 10 * usd(400, 1000) + 25 * small) / 45
            self.assertAlmostEqual(oc.measured_cost_per_page(db), corpus, places=9)
            self.assertAlmostEqual(oc.measured_cost_per_page(db, doc="NEW"), corpus, places=9,
                                   msg="a text with no history is priced at the corpus figure")

    def test_corpus_status_prices_each_text_at_its_own_rate(self):
        import ocr_consensus as oc, corpus_status as cs
        importlib.reload(oc); importlib.reload(cs)
        with tempfile.TemporaryDirectory() as d:
            db = _db(d)
            cs.vision_cost_per_page(db)
            s = {"pages_inbox": 100, "pages_vision": 0, "pages_refused": 0}
            _, est_big = cs.consensus_cmds("BIG", s)
            _, est_small = cs.consensus_cmds("SMALL", s)
            self.assertAlmostEqual(est_big, 100 * oc.measured_cost_per_page(db, doc="BIG"), places=9)
            self.assertAlmostEqual(est_small, 100 * usd(1000, 300), places=9)

    def test_ocr_vision_preflight_reads_the_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            db = _db(d)
            pdf = Path(d) / "BIG_0001.pdf"; pdf.write_bytes(b"%PDF-1.4\n")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ocr_vision.py"), "--pdf", str(pdf),
                                "--out", str(Path(d) / "o.jsonl"), "--doc", "BIG", "--db", db],
                               capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
            import ocr_consensus as oc
            importlib.reload(oc)
            want = "at $%.5f/page" % oc.measured_cost_per_page(db, doc="BIG")
            self.assertIn(want, r.stdout, r.stdout + r.stderr)

    def test_spend_audit_names_the_prepaid_credit(self):
        s = (ROOT / "scripts" / "spend_audit.py").read_text(encoding="utf-8")
        self.assertTrue("PREPAID" in s and "COST_RATIO_2026_10_05" in s)


if __name__ == "__main__":
    unittest.main()
