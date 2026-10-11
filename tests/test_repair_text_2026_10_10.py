# -*- coding: ascii -*-
"""REPAIR_PATH_2026_10_10: scripts/repair_text.py assesses a text that cannot be translated (held by the
OCR-debris guard, or below the OCR quality bar), repairs its scan, puts the repaired text in the database
only when nothing is lost (or with --replace N), and sets a text aside when its scan cannot be repaired.
Runs repair_text.py as a child process against a temp tree, with stand-ins for ocr_consensus.py,
db_backup.py, wipe_doc.py, ingest_jsonl_fast.py and classify_doc.py (SA_REPAIR_SCRIPTS); never
data/context.db, never the network (SA_DASHBOARD_URL points at a closed port unless a test serves it)."""
import http.server, json, os, socket, sqlite3, subprocess, sys, tempfile, textwrap, threading, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "repair_text.py"
DEBRIS = "\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d Tlie qnick \u0935\u093f\u0930\u093e\u091f"
CLEAN = "\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d \u0935\u093f\u0930\u093e\u091f\u0903"

STUBS = {
    "ocr_consensus.py": r'''
import json, sys, pathlib
a = sys.argv[1:]
doc = a[a.index("--doc") + 1]
pathlib.Path("calls.txt").open("a").write("ocr_consensus " + " ".join(a) + "\n")
if "--drift-only" in a:
    sys.exit(0)
import os
if os.environ.get("STUB_EST") and float(a[a.index("--max-usd") + 1]) < float(os.environ["STUB_EST"]):
    print("  REFUSING: estimate $%%s exceeds --max-usd %%s" %% (os.environ["STUB_EST"], a[a.index("--max-usd") + 1]))
    sys.exit(1)
for d in ("data/raw_vision", "data/raw_merged"):
    pathlib.Path(d).mkdir(parents=True, exist_ok=True)
for pg in ("0001", "0002"):
    rec = {"page": int(pg), "text": "%s", "engine": "gemini-vision:gemini-2.5-flash"}
    for d in ("data/raw_vision", "data/raw_merged"):
        pathlib.Path(d, "%%s_%%s.jsonl" %% (doc, pg)).write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
pathlib.Path("data/ocr_consensus").mkdir(parents=True, exist_ok=True)
pathlib.Path("data/ocr_consensus/%%s.json" %% doc).write_text(json.dumps({"summary": {"current": 0, "stale": 2, "missing-in-db": 0}, "at": "2026-10-10T17:00:00"}))
sys.exit(3)
''' % CLEAN,
    "db_backup.py": r'''
import sqlite3, sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
s = sqlite3.connect(src); d = sqlite3.connect(dst); s.backup(d); d.close(); s.close()
pathlib.Path("calls.txt").open("a").write("db_backup\n")
''',
    "wipe_doc.py": r'''
import sqlite3, sys, pathlib
a = sys.argv[1:]
con = sqlite3.connect(a[a.index("--db") + 1]); doc = a[a.index("--doc") + 1]
con.execute("DELETE FROM passages WHERE doc_id=(SELECT id FROM docs WHERE code=?)", (doc,)); con.commit()
pathlib.Path("calls.txt").open("a").write("wipe_doc\n")
''',
    "ingest_jsonl_fast.py": r'''
import glob, json, sqlite3, sys, pathlib
a = sys.argv[1:]
con = sqlite3.connect(a[a.index("--db") + 1]); doc = a[a.index("--doc") + 1]
did = con.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()[0]
for p in sorted(glob.glob("data/raw_merged/%s_*.jsonl" % doc)):
    r = json.loads(open(p, encoding="utf-8").readline())
    con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) VALUES(?,?,?,?,?,?,?,?)",
                (did, r["page"], 1, r["text"], "", "mula", 0.9, r["engine"]))
con.commit()
pathlib.Path("calls.txt").open("a").write("ingest " + a[a.index("--glob") + 1] + "\n")
''',
    "classify_doc.py": r'''
import pathlib
pathlib.Path("calls.txt").open("a").write("classify\n")
''',
}


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Repair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        (t / "stubs").mkdir()
        for name, code in STUBS.items():
            (t / "stubs" / name).write_text(textwrap.dedent(code), encoding="utf-8")
        for d in ("inbox", "data/raw", "backups"):
            (t / d).mkdir(parents=True)
        self.db = t / "data" / "context.db"
        con = sqlite3.connect(self.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT,"
            " text_type TEXT, quality_score REAL, ocr_engine TEXT);"
            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
            "CREATE TABLE doc_images(id INTEGER PRIMARY KEY, doc_id INT, status TEXT);"
            "CREATE TABLE doc_stories(id INTEGER PRIMARY KEY, doc_id INT);"
            "CREATE TABLE passage_embeddings(passage_id INT);")
        con.executemany("INSERT INTO docs VALUES(?,?)", [(1, "N"), (2, "K")])
        for did in (1, 2):
            for pg in (1, 2):
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation,text_type,quality_score,ocr_engine) "
                            "VALUES(?,?,?,?,?,?,?,?)", (did, pg, 1, DEBRIS, "", "mula", 0.2, "tesseract"))
        # K has translations to lose
        con.execute("UPDATE passages SET translation='an English line' WHERE doc_id=2")
        con.execute("INSERT INTO translations_l10n SELECT id,'hi','h' FROM passages WHERE doc_id=2")
        con.execute("INSERT INTO doc_images(doc_id,status) VALUES(2,'approved')")
        con.commit(); con.close()
        for doc in ("N", "K"):
            for pg in ("0001", "0002"):
                (t / "inbox" / ("%s_%s.pdf" % (doc, pg))).write_bytes(b"%PDF")
                (t / "data" / "raw" / ("%s_%s.jsonl" % (doc, pg))).write_text("{}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args, url=None, **extra):
        env = dict(os.environ, SA_REPAIR_SCRIPTS=str(self.t / "stubs"), SA_BACKUP_DIR=str(self.t / "backups"),
                   SA_DASHBOARD_URL=url or "http://127.0.0.1:%d" % free_port(), PYTHONIOENCODING="utf-8", **extra)
        t = self.t
        base = ["--db", str(self.db), "--inbox", str(t / "inbox"), "--raw", str(t / "data/raw"),
                "--vision-dir", str(t / "data/raw_vision"), "--merged-dir", str(t / "data/raw_merged"),
                "--work", str(t / "data/ocr_consensus"), "--verdicts", str(t / "data/source_verdicts.jsonl")]
        # the stand-ins write relative paths: run the tool with the temp tree as its root
        code = ("import os,sys,runpy; sys.argv=[%r]+%r; " % (str(TOOL), base + list(args)) +
                "import importlib.util as u; s=u.spec_from_file_location('rt', %r); m=u.module_from_spec(s); s.loader.exec_module(m); "
                "m.ROOT=__import__('pathlib').Path(%r); sys.exit(m.main(sys.argv[1:]))" % (str(TOOL), str(t)))
        r = subprocess.run([sys.executable, "-c", code], cwd=str(t), capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def last(self, out, key):
        lines = [l for l in out.splitlines() if l.startswith(key + ":")]
        return lines[-1][len(key) + 1:].strip() if lines else ""

    def calls(self):
        p = self.t / "calls.txt"
        return p.read_text().splitlines() if p.exists() else []

    def passages(self, did):
        con = sqlite3.connect(self.db)
        try:
            return con.execute("SELECT text, ocr_engine, translation FROM passages WHERE doc_id=? ORDER BY page_no", (did,)).fetchall()
        finally:
            con.close()

    def test_a_held_text_is_assessed_and_offered_its_repair(self):
        rc, out = self.tool("--doc", "N")
        self.assertEqual(rc, 0, out)
        self.assertIn("held by the OCR-debris guard", self.last(out, "VERDICT"))
        self.assertIn("--doc N --repair", self.last(out, "NEXT"))
        self.assertEqual(self.calls(), [], "assessing runs nothing")

    def test_repair_then_use_when_nothing_is_lost(self):
        rc, out = self.tool("--doc", "N", "--repair")
        self.assertEqual(rc, 0, out)
        self.assertIn("--threshold 101", self.calls()[0]); self.assertIn("--yes", self.calls()[0])
        self.assertIn("--max-usd 1.00", self.calls()[0])
        self.assertIn("nothing is lost", self.last(out, "VERDICT"))
        self.assertTrue(self.last(out, "NEXT").endswith("--doc N --use-repaired"))
        rc, out = self.tool("--doc", "N", "--use-repaired")
        self.assertEqual(rc, 0, out)
        self.assertEqual([c.split()[0] for c in self.calls()[1:]], ["db_backup", "wipe_doc", "ingest", "classify", "ocr_consensus"])
        self.assertTrue(list((self.t / "backups").glob("context_pre_repair_N_*.db")), "a backup first")
        rows = self.passages(1)
        self.assertEqual([r[0] for r in rows], [CLEAN, CLEAN]); self.assertTrue(all("vision" in r[1] for r in rows))
        self.assertIn("the repaired text is in the database", self.last(out, "VERDICT"))
        rc, out = self.tool("--doc", "N")
        self.assertIn("nothing holds it", self.last(out, "VERDICT"), "the guard no longer holds it: " + out)

    def test_translations_are_not_replaced_without_saying_so(self):
        self.tool("--doc", "K", "--repair")
        rc, out = self.tool("--doc", "K", "--use-repaired")
        self.assertEqual(rc, 1)
        self.assertIn("replaces 2 English translations", out)
        self.assertTrue(self.last(out, "NEXT").endswith("--use-repaired --replace 2"))
        self.assertNotIn("wipe_doc", self.calls()); self.assertNotIn("db_backup", self.calls())
        self.assertEqual(len(self.passages(2)), 2)
        rc, out = self.tool("--doc", "K", "--use-repaired", "--replace", "2")
        self.assertEqual(rc, 0, out)
        self.assertIn("wipe_doc", self.calls())

    def test_an_incomplete_or_unreadable_repair_changes_nothing(self):
        self.tool("--doc", "N", "--repair")
        (self.t / "data/raw/N_0003.jsonl").write_text("{}\n")          # a page the repair does not cover
        rc, out = self.tool("--doc", "N", "--use-repaired")
        self.assertEqual(rc, 1); self.assertIn("covers 2 of 3 pages", out)
        (self.t / "data/raw/N_0003.jsonl").unlink()
        (self.t / "data/raw_merged/N_0002.jsonl").write_text("{not json\n")
        rc, out = self.tool("--doc", "N", "--use-repaired")
        self.assertEqual(rc, 1); self.assertIn("does not read", out)
        self.assertNotIn("wipe_doc", self.calls()); self.assertNotIn("db_backup", self.calls())

    def test_not_while_the_dashboard_writes(self):
        self.tool("--doc", "N", "--repair")
        body = json.dumps({"running": [{"kind": "ocr", "doc": "Y", "state": "running"},
                                       {"kind": "translate_hi", "doc": "G", "state": "queued"}], "count": 2}).encode()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(body)

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = "http://127.0.0.1:%d" % srv.server_address[1]
            rc, out = self.tool("--doc", "N", "--use-repaired", url=url)
            self.assertEqual(rc, 1); self.assertIn("runs a database writer or a vision repair of this text: translate_hi G", out)
            rc, out = self.tool("--doc", "N", "--use-repaired", "--from-dashboard", url=url)
            self.assertEqual(rc, 0, "as the dashboard's own job, under its lock, a queued job waits for it: " + out)
        finally:
            srv.shutdown()

    def test_set_aside_restore_and_list(self):
        rc, out = self.tool("--doc", "N", "--set-aside", "needs a better scan")
        self.assertEqual(rc, 0)
        rc, out = self.tool("--doc", "N")
        self.assertIn("set aside on", self.last(out, "VERDICT")); self.assertIn("needs a better scan", self.last(out, "VERDICT"))
        rc, out = self.tool("--list")
        self.assertIn("(1 set aside)", out)
        self.tool("--doc", "N", "--restore")
        rc, out = self.tool("--doc", "N")
        self.assertIn("held by the OCR-debris guard", self.last(out, "VERDICT"))
        recs = [json.loads(l) for l in (self.t / "data/source_verdicts.jsonl").read_text().splitlines()]
        self.assertEqual([r["status"] for r in recs], ["set_aside", "restored"])

    def test_without_its_page_pdfs_the_scan_is_wanted(self):
        for p in (self.t / "inbox").glob("N_*.pdf"):
            p.unlink()
        con = sqlite3.connect(self.db); con.execute("UPDATE passages SET quality_score=0.9"); con.commit(); con.close()
        rc, out = self.tool("--doc", "N")
        self.assertIn("nothing holds it", self.last(out, "VERDICT"), "the guard holds only a text whose PDFs are there")
        con = sqlite3.connect(self.db); con.execute("UPDATE passages SET quality_score=0.1"); con.commit(); con.close()
        rc, out = self.tool("--doc", "N")
        self.assertIn("below the OCR quality bar", self.last(out, "VERDICT"))
        self.assertIn("cannot be repaired here", self.last(out, "VERDICT"))
        self.assertIn("--set-aside", self.last(out, "NEXT"))

    def test_a_repair_above_its_cap_spends_nothing_and_names_the_cap_it_needs(self):
        rc, out = self.tool("--doc", "N", "--repair", STUB_EST="2.2300")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSING: estimate $2.2300", out, "the meter's own line is shown")
        self.assertIn("estimates $2.23", self.last(out, "VERDICT")); self.assertIn("nothing was spent", self.last(out, "VERDICT"))
        self.assertTrue(self.last(out, "NEXT").endswith("--doc N --repair --max-usd 2.46"), out)
        self.assertFalse((self.t / "data/raw_merged").exists())
        rc, out = self.tool("--doc", "N", "--repair", "--max-usd", "2.46", STUB_EST="2.2300")
        self.assertEqual(rc, 0, out); self.assertIn("nothing is lost", self.last(out, "VERDICT"))

    def test_ascii_and_marker(self):
        b = TOOL.read_bytes()
        self.assertTrue(all(x < 128 for x in b)); self.assertIn(b"REPAIR_PATH_2026_10_10", b)


if __name__ == "__main__":
    unittest.main()
