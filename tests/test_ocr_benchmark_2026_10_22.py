# -*- coding: ascii -*-
"""OCR_BENCHMARK_2026_10_22: scripts/ocr_benchmark.py reads source_fidelity's reports and sets our readings side by
side against their witnesses: the engine of each (raw: Tesseract, vision:, db: by the ledger, an archive.org text by its
name), the agreement weighted by aksharas, the own misreadings where two readings of one print exist, the gaps, the
commonest substitutions ("both" when two engines make one on the same text), and the cost of a vision pass for a text
read by Tesseract alone. Made-up reports in a temp folder; never data/context.db, never the network."""
import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "ocr_benchmark.py"
MARK = "OCR_BENCHMARK_2026_10_22"


def reading(agree, aks, conf, note="", units=100, found=90, gaps=5):
    return {"units": units, "found": found, "aksharas": aks, "errors": int(aks * (100 - agree) / 100), "agree_pct": agree, "unit_median_pct": agree,
            "ge95_pct": 1.0, "lt90_pct": 90.0, "missing_in_span": gaps, "confusions": conf, "note": note}


class TheBenchmark(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "source_fidelity").mkdir(parents=True)
        (t / "exports").mkdir()
        for d, n in (("alpha", 3), ("beta", 4)):
            (t / "data" / "raw").mkdir(exist_ok=True)
            for i in range(1, n + 1):
                (t / "data" / "raw" / ("%s_%04d.jsonl" % (d, i))).write_text("{}\n", encoding="utf-8")
        (t / "data" / "raw_vision").mkdir()
        for i in range(1, 4):
            (t / "data" / "raw_vision" / ("alpha_%04d.jsonl" % i)).write_text("{}\n", encoding="utf-8")
        with open(t / "exports" / "source_ledger.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["doc", "engines"])
            w.writerow(["alpha", "gemini-vision:gemini-2.5-flash 98%; tesseract-fallback 2%"])
            w.writerow(["beta", "? 100%"])
        (t / "data" / "source_fidelity" / "alpha__w_gretil__alpha.json").write_text(json.dumps({
            "at": "2026-10-22T10:00:00", "ref": "db:alpha__w_gretil",
            "readings": {"db:alpha": reading(90.0, 1000, [["\u0927", "\u0918", 5], ["\u0905", "", 9]]),
                         "raw:alpha": reading(70.0, 1000, [["\u0927", "\u0918", 40], ["\u0905", "", 8]],
                                              note="3 pages (tesseract 3)")},
            "pairs": [{"a": "db:alpha", "b": "raw:alpha", "aksharas": 900, "own_a_per100": 3.0, "own_b_per100": 18.0,
                       "shared_per100": 5.0}]}, ensure_ascii=False), encoding="utf-8")
        (t / "data" / "source_fidelity" / "beta__w_gretil__beta.json").write_text(json.dumps({
            "at": "2026-10-22T11:00:00", "ref": "db:beta__w_gretil",
            "readings": {"db:beta": reading(80.0, 3000, [["\u092e\u0941", "\u092e", 7]], gaps=40)}, "pairs": []},
            ensure_ascii=False), encoding="utf-8")
        same = reading(70.0, 500, [["\u0927", "\u0918", 3]], note="2 pages (tesseract 2)")
        (t / "data" / "source_fidelity" / "gamma__w_gretil__gamma.json").write_text(json.dumps({
            "at": "2026-10-22T12:00:00", "ref": "db:gamma__w_gretil",
            "readings": {"db:gamma": dict(same, note="9 passages on 2 pages"), "raw:gamma": same}, "pairs": []},
            ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t)] + list(a), capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_the_table(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        j = json.loads((self.t / "exports" / "ocr_benchmark.json").read_text(encoding="utf-8"))
        eng = {(r["text"], r["reading"]): (r["engine"], r["family"]) for r in j["rows"]}
        self.assertEqual(eng[("alpha", "db:alpha")], ("gemini-vision:gemini-2.5-flash", "vision"), "the ledger names it")
        self.assertEqual(eng[("alpha", "raw:alpha")], ("tesseract", "tesseract"))
        self.assertEqual(eng[("beta", "db:beta")][1], "unrecorded", "an engine not recorded is not guessed")
        g = [r for r in j["rows"] if r["text"] == "gamma"]
        self.assertEqual(sorted((r["engine"], r["dup"]) for r in g),
                         [("tesseract", False), ("tesseract (the database's text)", True)],
                         "the database holding Tesseract's very reading is named so, and counted once")
        self.assertEqual(j["summary"]["tesseract"]["aksharas"], 1500, "alpha's 1,000 and gamma's 500, not 2,000")
        self.assertEqual(j["summary"]["vision"]["own_per100"], 3.0)
        self.assertEqual(j["summary"]["tesseract"]["own_per100"], 18.0)
        self.assertEqual(j["summary"]["vision"]["agree_pct"], 90.0)
        self.assertEqual(j["tesseract_alone"], [{"text": "beta", "pages": 4, "usd": 0.02}], "alpha has its vision pages")
        with open(self.t / "exports" / "ocr_confusions.csv", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        both = {(r["family"], r["etext"], r["reading"]): r["two_engines_on_one_text"] for r in rows}
        self.assertEqual(both[("tesseract", "\u0927", "\u0918")], "yes", "two engines, one text: marked")
        self.assertEqual(both[("unrecorded", "\u092e\u0941", "\u092e")], "")
        self.assertIn("vision misreads 3.00 and Tesseract 18.00 aksharas in 100 on its own", out)

    def test_nothing_written_on_request_and_nothing_to_read(self):
        rc, out = self.run_tool("--no-write")
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.t / "exports" / "ocr_benchmark.csv").exists())
        for f in (self.t / "data" / "source_fidelity").glob("*.json"):
            f.unlink()
        rc, out = self.run_tool()
        self.assertEqual(rc, 1)
        self.assertIn("no reports", out)

    def test_ascii_and_mark(self):
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
