# -*- coding: ascii -*-
"""MAINT_2026_10_04 - images approve keeps going; resegment keeps every passage of a page.
Fails before patch_maintenance_2026_10_04.py, passes after."""
import json, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

V1 = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u0967"
V2 = "\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0968"
V3 = "\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0969"


def _run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))


class Maint(unittest.TestCase):
    def setUp(self):
        import db_utils
        self.tmp = Path(tempfile.mkdtemp(prefix="maint_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES('SrcBook', 'upapurana')")
        did = con.execute("SELECT id FROM docs WHERE code='SrcBook'").fetchone()[0]
        # page 1 is held by TWO passages (a segmented source); page 2 by one
        for pg, ix, text in ((1, 0, V1 + "\n" + V2), (1, 1, V3), (2, 0, V1)):
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type) VALUES(?,?,?,?, 'mula')",
                        (did, pg, ix, text))
        import images
        images.ensure_schema(con)
        img = self.tmp / "a.jpg"; img.write_bytes(b"jpg")
        for st, path in (("approved", str(img)), ("draft", str(img)), ("brief", None), ("draft", str(img))):
            con.execute("INSERT INTO doc_images(doc_id, lineage_id, version, kind, status, path, anchor_page, anchor_idx)"
                        " VALUES(?, NULL, 1, 'generated', ?, ?, 1, 0)", (did, st, path))
        con.execute("UPDATE doc_images SET lineage_id = id")
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_resegment_keeps_every_passage_of_a_page(self):
        out = self.tmp / "raw"
        p = _run([str(SCRIPTS / "resegment_doc.py"), "--db", self.db, "--src-doc", "SrcBook",
                  "--new-doc", "SegBook", "--out", str(out), "--yes"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        recs = [json.loads(l) for l in (out / "SegBook_0001.jsonl").read_text(encoding="utf-8").splitlines() if l]
        self.assertEqual([r["verse_ref"] for r in recs], ["1", "2", "3"])
        recs2 = [json.loads(l) for l in (out / "SegBook_0002.jsonl").read_text(encoding="utf-8").splitlines() if l]
        self.assertEqual(len(recs2), 1)

    def test_approve_skips_and_continues(self):
        p = _run([str(SCRIPTS / "images.py"), "--db", self.db, "approve", "1", "2", "3", "4"])
        self.assertIn("skip #1: already approved", p.stdout, p.stdout + p.stderr)
        self.assertIn("#2 approved", p.stdout)
        self.assertIn("skip #3", p.stdout)
        self.assertIn("#4 approved", p.stdout, "the loop must go on past a skipped id")
        self.assertEqual(p.returncode, 1)   # #3 could not be approved
        con = sqlite3.connect(self.db)
        st = dict(con.execute("SELECT id, status FROM doc_images").fetchall()); con.close()
        self.assertEqual(st[2], "approved"); self.assertEqual(st[4], "approved"); self.assertEqual(st[3], "brief")


if __name__ == "__main__":
    unittest.main()
