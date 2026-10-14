# -*- coding: ascii -*-
"""ETEXT_META_2026_10_14: an e-text's passages get its engine and the ingest's e-text quality (0.98); only where the
page file's record has the same verse and text; a plan writes nothing; --apply backs up first and logs the values
before; --undo puts them back. Temp files only."""
import hashlib, json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

A = "\u0928\u093e\u0930\u093e\u092f\u0923\u0902 \u0928\u092e\u0938\u094d\u0915\u0943\u0924\u094d\u092f \u0928\u0930\u0902 \u091a\u0948\u0935 \u0928\u0930\u094b\u0924\u094d\u0924\u092e\u092e\u094d"
B = "\u0926\u0947\u0935\u0940\u0902 \u0938\u0930\u0938\u094d\u0935\u0924\u0940\u0902 \u091a\u0948\u0935 \u0924\u0924\u094b \u091c\u092f\u092e\u094d \u0909\u0926\u0940\u0930\u092f\u0947\u0924\u094d"
C = "\u0938\u092e\u093e\u0938\u0940\u0928\u093e\u0928\u094d \u0905\u092d\u094d\u092f\u0917\u091a\u094d\u091b\u0926\u094d \u092c\u094d\u0930\u0939\u094d\u092e\u0930\u094d\u0937\u0940\u0928\u094d"


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def fixture(td: Path) -> Path:
    import db_utils
    from normalize_text import normalize_sanskrit
    db = td / "context.db"
    con = sqlite3.connect(str(db)); db_utils.ensure_schema(con)
    if "ocr_engine" not in {r[1] for r in con.execute("PRAGMA table_info(passages)")}:
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
    con.execute("INSERT INTO docs(code) VALUES ('E')")
    for k, (ref, t, q, eng) in enumerate((("1.1.0", A, 0.52, None), ("1.1.2", B, 0.48, None), ("1.1.3", C, 0.99, None),
                                          ("1.1.4", A + " x", 0.5, None)), 1):
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, verse_ref, quality_score, ocr_engine, translation) "
                    "VALUES (1, 1, ?, ?, ?, ?, ?, 'kept //')", (k, normalize_sanskrit(t), ref, q, eng))
    con.commit(); con.close()
    raw = td / "raw"; raw.mkdir()
    recs = [{"engine": "gretil-bori-etext", "page_no": 1, "verse_ref": r, "text": t}
            for r, t in (("1.1.0", A), ("1.1.2", B), ("1.1.3", C), ("1.1.4", A))]
    (raw / "E_0001.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    (raw / "Other_0001.jsonl").write_text(json.dumps({"engine": "tesseract", "verse_ref": "1"}) + "\n", encoding="utf-8")
    return db


def run(db, *extra, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPTS / "heal_etext_meta.py"), "--doc", "E", "--db", str(db)] + list(extra),
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd or Path(db).parent),
                          env=dict(os.environ, PYTHONIOENCODING="utf-8", SA_DASHBOARD_URL="http://127.0.0.1:9"))


class TheHeal(unittest.TestCase):
    def test_plan_apply_undo(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            db = fixture(t)
            before = md5(db)
            r = run(db)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PLAN (nothing written)", r.stdout)
            self.assertIn("to set: the engine on 3, the quality (0.98) on 2 (1 of them below 0.5", r.stdout)
            self.assertIn("left as they are: 1 whose text is not the record's, 0 with no e-text record", r.stdout)
            self.assertIn("NEXT: python scripts\\heal_etext_meta.py --doc E --apply", r.stdout)
            self.assertEqual(md5(db), before)
            r = run(db, "--apply", "--backup-dir", str(t / "bk"), "--log-dir", str(t / "heal"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(list((t / "bk").glob("context_pre_etextmeta_E_*.db")), "a backup first")
            con = sqlite3.connect(str(db))
            got = con.execute("SELECT verse_ref, quality_score, ocr_engine, translation FROM passages ORDER BY idx").fetchall()
            con.close()
            self.assertEqual(got, [("1.1.0", 0.98, "gretil-bori-etext", "kept //"), ("1.1.2", 0.98, "gretil-bori-etext", "kept //"),
                                   ("1.1.3", 0.99, "gretil-bori-etext", "kept //"), ("1.1.4", 0.5, None, "kept //")])
            self.assertIn("VERDICT: nothing to change", run(db).stdout, "again: nothing")
            log = list((t / "heal").glob("etext_meta_E_*.jsonl"))[0]
            rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 3); self.assertEqual(rows[0]["quality_before"], 0.52)
            r = run(db, "--undo", str(log), "--backup-dir", str(t / "bk"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            con = sqlite3.connect(str(db))
            got = con.execute("SELECT quality_score, ocr_engine FROM passages ORDER BY idx").fetchall()
            con.close()
            self.assertEqual(got, [(0.52, None), (0.48, None), (0.99, None), (0.5, None)])

    def test_files(self):
        for p in (SCRIPTS / "heal_etext_meta.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"ETEXT_META_2026_10_14", b)


if __name__ == "__main__":
    unittest.main()
