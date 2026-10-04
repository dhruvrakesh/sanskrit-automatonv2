# -*- coding: ascii -*-
"""STATUS_REPORT_2026_10_04 - one read-only status page."""
import os, shutil, sqlite3, subprocess, sys, tempfile, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e"


class StatusReport(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = Path(tempfile.mkdtemp(prefix="srep_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
        con.execute("INSERT INTO docs(code) VALUES('Book')")
        for i in range(25):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation,translated_at,ocr_engine)"
                        " VALUES(1,?,1,?, 'mula', 'The king.', '2026-10-04T05:00:00+00:00', 'gemini-vision:x')",
                        (i + 1, SA))
        con.execute("CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB,"
                    " updated_at TEXT)")
        con.execute("INSERT INTO passage_embeddings VALUES(1,'m',1,x'00000000','2026-10-01T00:00:00+00:00')")  # stale
        con.execute("INSERT INTO passage_embeddings VALUES(999,'m',1,x'00000000','2026-10-01T00:00:00+00:00')")  # orphan
        con.commit(); con.close()
        for d in ("raw", "raw_vision", "raw_merged", "inbox", "backups", "srangam/src/data", "out"):
            (self.tmp / d).mkdir(parents=True)
        (self.tmp / "backups" / "context_20261004.db").write_bytes(b"x" * 10)
        (self.tmp / "backups" / "context_pre_maint_20261004_104726.db").write_bytes(b"")
        (self.tmp / "backups" / "maintenance_log.txt").write_text(
            "[2026-10-04 12:00:55] STEP b embeddings   52s\n[2026-10-04 12:23:01] DONE maintenance - total 1,378s\n",
            encoding="utf-8")
        ps = self.tmp / "srangam" / "src" / "data" / "projectStatus.ts"
        ps.write_text("export {}", encoding="utf-8")
        old = time.time() - 10 * 86400
        os.utime(ps, (old, old))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_page(self):
        t = self.tmp
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "status_report.py"), "--db", self.db,
                            "--raw-dir", str(t / "raw"), "--vision-dir", str(t / "raw_vision"),
                            "--merged-dir", str(t / "raw_merged"), "--inbox", str(t / "inbox"),
                            "--backups", str(t / "backups"), "--maint-log", str(t / "backups" / "maintenance_log.txt"),
                            "--srangam", str(t / "srangam"), "--out", str(t / "out")],
                           capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        md = (t / "out" / "STATUS_latest.md").read_text(encoding="utf-8")
        self.assertIn("| Book |", md)
        self.assertIn("| Stale vectors (English re-translated after the vector) | 1 |", md)
        self.assertIn("| Orphaned vectors (passage deleted) | 1 |", md)
        self.assertIn("0-byte backup file", md)
        self.assertIn("DONE maintenance", md)
        self.assertIn("**Stale:**", md)


if __name__ == "__main__":
    unittest.main()
