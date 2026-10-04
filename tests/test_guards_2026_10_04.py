# -*- coding: ascii -*-
"""INGEST_SOURCE_2026_10_04 + TRANSLATE_DEBRIS_GUARD_2026_10_04.
Fails before patch_guards_2026_10_04.py, passes after."""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

A = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0965"
B = "\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u091e\u094d\u091c\u092f \u0965"
C = "\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938\u094d\u0924\u0926\u093e \u0965"


def _run(args, env=None):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", **(env or {}))
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8",
                          cwd=str(ROOT), env=e)


def _put(p: Path, text: str, page: int, engine: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"engine": engine, "page_no": page, "text": text}, ensure_ascii=False) + "\n",
                 encoding="utf-8")


class IngestSource(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard_"))
        self.db = str(self.tmp / "t.db")
        import db_utils   # ingest_jsonl_fast expects an existing DB (it adds ocr_engine before ensure_schema)
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con); con.close()
        d = self.tmp / "data"
        for pg in (1, 2):
            _put(d / "raw" / ("Book_%04d.jsonl" % pg), A, pg, "tesseract")
            _put(d / "raw" / ("Book_seg_%04d.jsonl" % pg), B, pg, "resegment-devnum")   # another doc
            _put(d / "raw_merged" / ("Book_%04d.jsonl" % pg), C, pg, "gemini-vision:x")
        _put(d / "raw" / ("Part_0001.jsonl"), A, 1, "tesseract")
        _put(d / "raw" / ("Part_0002.jsonl"), A, 2, "tesseract")
        _put(d / "raw_merged" / ("Part_0001.jsonl"), C, 1, "gemini-vision:x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ingest(self, doc, *extra):
        return _run([str(SCRIPTS / "ingest_jsonl_fast.py"), "--doc", doc, "--db", self.db, "--no-iast",
                     "--glob", str(self.tmp / "data" / "raw" / ("%s_*.jsonl" % doc))] + list(extra))

    def texts(self, doc):
        con = sqlite3.connect(self.db)
        try:
            return [r[0] for r in con.execute("SELECT p.text FROM passages p JOIN docs d ON d.id=p.doc_id "
                                              "WHERE d.code=? ORDER BY page_no, idx", (doc,))]
        finally:
            con.close()

    def test_complete_consensus_wins_and_other_docs_are_skipped(self):
        p = self.ingest("Book")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("ingesting those instead of data/raw", p.stdout)
        self.assertIn("belong to another doc", p.stdout)
        t = "\n".join(self.texts("Book"))
        self.assertIn(C[:10], t); self.assertNotIn(A[:10], t); self.assertNotIn(B[:10], t)

    def test_source_raw_is_tesseract_but_still_this_doc_only(self):
        p = self.ingest("Book", "--source", "raw")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        t = "\n".join(self.texts("Book"))
        self.assertIn(A[:10], t); self.assertNotIn(B[:10], t)

    def test_partial_consensus_refuses_and_writes_nothing(self):
        p = self.ingest("Part")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("1 of 2 page(s)", p.stdout)
        self.assertEqual(self.texts("Part"), [])


class DebrisGuard(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = Path(tempfile.mkdtemp(prefix="dguard_"))
        self.db = str(self.tmp / "t.db")
        self.inbox = self.tmp / "inbox"; self.inbox.mkdir()
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
        for code, text, eng in (("Junk", A + " CHARA IATA", "tesseract"), ("Clean", A, "tesseract"),
                                ("VisJunk", A + " Plate I", "gemini-vision:x"), ("NoPdf", A + " CHARA", None)):
            con.execute("INSERT INTO docs(code) VALUES(?)", (code,))
            did = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()[0]
            for i in range(10):
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,ocr_engine) "
                            "VALUES(?,?,?,?, 'mula', ?)", (did, i + 1, 1, text, eng))
            if code != "NoPdf":
                for i in range(3):
                    (self.inbox / ("%s_%04d.pdf" % (code, i + 1))).write_bytes(b"%PDF")
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def guard(self, doc):
        import translate_passages as tp
        con = sqlite3.connect(self.db)
        try:
            return tp._debris_guard(con, doc, 30.0, inbox=self.inbox)
        finally:
            con.close()

    def test_rules(self):
        self.assertIn("REFUSING", self.guard("Junk") or "")
        self.assertIsNone(self.guard("Clean"))
        self.assertIsNone(self.guard("VisJunk"), "mostly-vision text is not sent back to OCR")
        self.assertIsNone(self.guard("NoPdf"), "no source PDF: nothing to repair with")

    def test_cli_refuses_before_any_call(self):
        args = [str(SCRIPTS / "translate_passages.py"), "--db", self.db, "--doc", "Junk",
                "--progress", str(self.tmp / "p.json"), "--config", str(self.tmp / "c.json")]
        p = _run(args, {"SA_INBOX_DIR": str(self.inbox)})
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("TRANSLATE_DEBRIS_GUARD_2026_10_04", p.stdout)
        self.assertIn("--include-unassessed", p.stdout)


if __name__ == "__main__":
    unittest.main()
