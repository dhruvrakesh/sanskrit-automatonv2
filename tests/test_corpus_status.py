# -*- coding: ascii -*-
"""CORPUS_STATUS_2026_10_04 + CORPUS_STATUS2_2026_10_04 - read-only per-text currency report.
v2 judges source damage from source DEBRIS (not lacuna rates), knows derived docs from
their page files, and never sends a Tesseract text to translation."""
import json, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903"
DEBRIS = SA + " CHARA IATA"          # Latin OCR debris inside Devanagari
OTHER = "\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u091e\u094d\u091c\u092f"
HI = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u092e\u0947\u0902"
HI_LAC = "\u0935\u0939 [\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0939\u0948"
EN_VER, HI_VER = "v3-2026-09-27", "hi-file-abc"
VIS = "gemini-vision:gemini-2.5-flash"


class CorpusStatus(unittest.TestCase):
    def setUp(self):
        import corpus_status, db_utils
        self.cs = corpus_status
        self._cv = corpus_status.current_versions
        corpus_status.current_versions = lambda: (EN_VER, HI_VER, "test")
        self.tmp = Path(tempfile.mkdtemp(prefix="cstat_"))
        self.db = str(self.tmp / "t.db")
        for d in ("raw", "raw_vision", "raw_merged", "inbox"):
            (self.tmp / d).mkdir()
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")   # as ingest_jsonl_fast adds it
        con.execute("CREATE TABLE usage_log(kind TEXT, cost_usd REAL, passages INTEGER, ok INTEGER)")
        con.execute("INSERT INTO usage_log VALUES('translation', 1.0, 1000, 1)")   # $0.001 / passage
        # doc: (n, stored text, ocr engine, en (text, ver) or None, hi (text, ver) or None)
        specs = {
            "Damaged":  (30, DEBRIS, "tesseract", ("a [ILLEGIBLE] b", EN_VER), (HI_LAC, HI_VER)),
            "RawTess":  (30, DEBRIS, None, None, None),              # v1 sent this to translation
            "NoPdf":    (30, DEBRIS, "tesseract", None, None),
            "Seg":      (30, DEBRIS, "resegment-devnum", ("fine", EN_VER), (HI, HI_VER)),
            "HiOnly":   (30, SA, None, ("fine", EN_VER), (HI_LAC, "hi-v3-2026-09-27")),   # v1 sent this to OCR
            "Behind":   (30, SA, VIS, ("fine", EN_VER), (HI, HI_VER)),
            "NoHindi":  (30, SA, VIS, ("fine", EN_VER), None),
            "Current":  (30, SA, VIS, ("fine", EN_VER), (HI, HI_VER + "+noref")),
            "Aged":     (30, SA, VIS, ("fine", "v2-2026-07-20"), (HI, "hi-v3-2026-09-27")),
            "Tiny":     (3, SA, "tesseract", None, None),
            "Mixed":    (30, SA, "resegment-devnum", ("fine", EN_VER), None),   # took Mixed_seg's files
            "Mixed_seg": (30, SA, "resegment-devnum", ("fine", EN_VER), (HI, HI_VER)),
        }
        for code, (n, text, eng, en, hi) in specs.items():
            con.execute("INSERT INTO docs(code, category) VALUES(?, 'upapurana')", (code,))
            did = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()[0]
            for i in range(n):
                cur = con.execute(
                    "INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation,mt_prompt_version,"
                    "translated_at,ocr_engine) VALUES(?,?,?,?,?,?,?,?,?)",
                    (did, 1 + i // 3, i % 3, text, "mula", en[0] if en else "", en[1] if en else None,
                     "2026-10-01T00:00:00", eng))
                if hi:
                    con.execute("INSERT INTO translations_l10n(passage_id,lang,translation,mt_prompt_version,"
                                "translated_at) VALUES(?,?,?,?,?)",
                                (cur.lastrowid, "hi", hi[0], hi[1], "2026-10-02T00:00:00"))
        con.commit(); con.close()

        def put(folder, name, rec):
            (self.tmp / folder / name).write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        for pg in range(1, 11):
            for code in ("Damaged", "RawTess", "NoPdf"):
                put("raw", "%s_%04d.jsonl" % (code, pg), {"engine": "tesseract", "text": DEBRIS})
            (self.tmp / "inbox" / ("series_NoPdf_%04d.pdf" % pg)).write_bytes(b"%PDF-1.4")   # alias hint
            for code in ("Damaged", "RawTess", "SrcBook"):
                (self.tmp / "inbox" / ("%s_%04d.pdf" % (code, pg))).write_bytes(b"%PDF-1.4")
            put("raw", "Seg_%04d.jsonl" % pg, {"engine": "resegment-devnum", "text": DEBRIS, "page_no": pg,
                                                "meta": {"src_doc": "SrcBook", "src_page": pg}})
            put("raw", "SrcBook_%04d.jsonl" % pg, {"engine": "tesseract", "text": DEBRIS})
            put("raw", "Mixed_%04d.jsonl" % pg, {"engine": "tesseract", "text": DEBRIS})
            put("raw", "Mixed_seg_%04d.jsonl" % pg, {"engine": "resegment-devnum", "text": SA, "page_no": pg,
                                                    "meta": {"src_doc": "Mixed", "src_page": pg}})
            put("raw_merged", "Behind_%04d.jsonl" % pg, {"engine": "gemini-vision", "text": OTHER})
            put("raw_merged", "Current_%04d.jsonl" % pg, {"engine": "gemini-vision", "text": "\n".join([SA] * 3)})
        for pg in range(1, 4):   # RawTess: 3 pages already have vision
            put("raw_vision", "RawTess_%04d.jsonl" % pg, {"engine": VIS, "text": SA})

    def tearDown(self):
        self.cs.current_versions = self._cv
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stats(self):
        st, _, peers, cpp = self.cs.collect(self.db, None, self.tmp / "raw", self.tmp / "raw_vision",
                                            self.tmp / "raw_merged", self.tmp / "inbox", True, 20)
        by = {s["doc"]: s for s in st}
        for s in st:
            sd = s.get("src_doc")
            peer = (by.get(sd) or peers.get(sd)) if sd else None
            s["verdict"], s["reasons"], s["commands"] = self.cs.verdict(s, 5.0, 5.0, cpp, {sd: peer} if peer else {})
        return by, peers, cpp

    def test_verdicts(self):
        s, _, _ = self.stats()
        self.assertNotIn("Tiny", s)
        want = {"Mixed": "CONTAMINATED", "Damaged": "NEEDS-OCR", "RawTess": "NEEDS-OCR", "NoPdf": "NO-SOURCE-PDF",
                "Seg": "DERIVED-NEEDS-OCR", "HiOnly": "NEEDS-TRANSLATION", "Behind": "NEEDS-REINGEST",
                "NoHindi": "NEEDS-TRANSLATION", "Current": "CURRENT", "Aged": "AGED"}
        self.assertEqual({k: s[k]["verdict"] for k in want}, want)

    def test_no_translation_on_debris(self):
        s, _, _ = self.stats()
        for code in ("Damaged", "RawTess", "NoPdf", "Seg"):
            self.assertFalse(any("translate_passages" in c for c in s[code]["commands"]), code)
        self.assertTrue(any("--threshold 101 --include-unassessed --yes --max-usd" in c and "~7 pages" in c
                            for c in s["RawTess"]["commands"]), s["RawTess"]["commands"])   # 10 inbox - 3 done

    def test_derived_follows_the_retirement_policy(self):
        s, peers, _ = self.stats()
        c = "\n".join(s["Seg"]["commands"])
        self.assertIn("ocr_consensus.py --doc SrcBook --threshold 101", c)
        self.assertIn('--doc SrcBook_v2 --glob "data\\raw_merged\\SrcBook_*.jsonl"', c)
        self.assertIn("resegment_doc.py --src-doc SrcBook_v2 --new-doc Seg_v2 --yes", c)
        self.assertIn("diag_retire_check.py --src Seg --keep Seg_v2", c)
        self.assertNotIn("wipe_doc", c, "a derived doc (it may hold grafts) is never wiped in place")
        self.assertFalse(peers["SrcBook"]["in_db"])

    def test_contaminated_source_is_sent_to_retirement_check(self):
        s, _, _ = self.stats()
        self.assertEqual(s["Mixed"]["verdict"], "CONTAMINATED")
        c = "\n".join(s["Mixed"]["commands"])
        self.assertIn("diag_retire_check.py --src Mixed --keep Mixed_seg", c)
        self.assertNotIn("ocr_consensus", c)

    def test_alias_is_a_hint_with_a_copy_command(self):
        s, _, _ = self.stats()
        self.assertEqual(s["NoPdf"]["inbox_alias"], ["series_NoPdf"])
        self.assertTrue(any("possible source in inbox: series_NoPdf" in r for r in s["NoPdf"]["reasons"]))
        self.assertTrue(any("Copy-Item" in c and "'NoPdf_'" in c for c in s["NoPdf"]["commands"]))

    def test_hindi_only_lacunae_go_to_the_prompt(self):
        s, _, _ = self.stats()
        self.assertTrue(any("--lang hi --reference none --only-lacuna" in c for c in s["HiOnly"]["commands"]))

    def test_counts_and_costs(self):
        s, _, cpp = self.stats()
        self.assertAlmostEqual(cpp, 0.001)
        self.assertEqual(s["Damaged"]["debris_rows"], 30)
        self.assertEqual(s["Current"]["debris_rows"], 0)
        self.assertEqual(s["Current"]["hi_current"], 30)          # +noref is current
        self.assertEqual(s["Behind"]["drift_stale"], 10)
        self.assertEqual(s["RawTess"]["pages_vision"], 3)
        self.assertEqual(s["Seg"]["src_doc"], "SrcBook")
        self.assertAlmostEqual(s["NoHindi"]["est_usd"], 0.03, places=4)   # 30 Hindi rows x $0.001

    def test_cli_is_read_only(self):
        before = Path(self.db).stat().st_mtime_ns
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "corpus_status.py"), "--db", self.db,
                            "--raw-dir", str(self.tmp / "raw"), "--vision-dir", str(self.tmp / "raw_vision"),
                            "--merged-dir", str(self.tmp / "raw_merged"), "--inbox", str(self.tmp / "inbox"),
                            "--commands"], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("# --- Damaged  [NEEDS-OCR]", p.stdout)
        self.assertEqual(Path(self.db).stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
