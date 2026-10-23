# -*- coding: ascii -*-
"""ENTITY_LINKS_SCHED_2026_10_23: entity_links.py --scheduled, the hourly maintenance task's step d: it writes only when
the names changed since the last rebuild; the day's backup (under 26 hours old) stands for its own, else it makes one;
a writer in the dashboard leaves it to the next tick (exit 0); a missing claims database does not stop it. The
maintenance runner calls it after step c, then kin_index.py --check once kin.db is there, and a failure there is logged
and skipped. A made-up database in a temp folder; the dashboard a stub on a local port or none."""
import hashlib, http.server, json, os, socket, sqlite3, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "entity_links.py"
RUNNER = REPO / "scripts" / "maintenance_runner.ps1"
PAT = REPO / "scripts" / "patch_links_sched_2026_10_23.py"
MARK = "ENTITY_LINKS_SCHED_2026_10_23"
ON = TOOL.exists() and MARK.encode() in TOOL.read_bytes()


def make_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, verse_ref TEXT, page_no INTEGER, idx INTEGER);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    """)
    con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "sb")])
    con.executemany("INSERT INTO passages VALUES (?,?,?,?,?)", [(i, 1, None, 1, i) for i in range(1, 6)])
    con.executemany("INSERT INTO entities VALUES (?,?,?)", [(1, "Janaka", "person"), (2, "Videha", "place"),
                                                            (3, "Uddalaka", "person")])
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)", [(1, 1), (2, 1), (3, 4)])
    con.commit()
    con.close()


class Stub(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"running": [{"kind": "translate", "doc": "sb", "state": "running"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


@unittest.skipUnless(ON, "ENTITY_LINKS_SCHED_2026_10_23 is not applied here")
class TheScheduledStep(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data").mkdir()
        self.db = t / "data" / "context.db"
        make_db(self.db)
        self.bk = t / "bk"
        self.bk.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a, url="http://127.0.0.1:9"):
        env = dict(os.environ, SA_DASHBOARD_URL=url, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t), "--backup-dir", str(self.bk)] + list(a),
                           capture_output=True, text=True, encoding="utf-8", timeout=120, env=env)
        return r.returncode, r.stdout + r.stderr

    def runs(self):
        con = sqlite3.connect(str(self.db))
        try:
            return con.execute("SELECT backup, together, near FROM entity_link_runs ORDER BY id").fetchall()
        finally:
            con.close()

    def test_writes_only_when_the_names_change(self):
        rc, out = self.run_tool("--scheduled", "--claims", str(self.t / "no_claims.db"))
        self.assertEqual(rc, 0, out)
        self.assertIn("no claims database", out, "said, and the links rebuilt all the same")
        self.assertEqual(len(list(self.bk.glob("context_pre_links_*.db"))), 1, "no day's backup: one is made")
        self.assertEqual([r[1:] for r in self.runs()], [(1, 2)])
        rc, out = self.run_tool("--scheduled")
        self.assertEqual(rc, 0, out)
        self.assertIn("SCHEDULED: the names are as at the last rebuild", out)
        self.assertEqual(len(self.runs()), 1, "nothing written")
        con = sqlite3.connect(str(self.db))
        con.execute("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (3, 1)")
        con.commit()
        con.close()
        (self.bk / "context_daily.db").write_bytes(b"the 04:00 copy")
        rc, out = self.run_tool("--scheduled")
        self.assertEqual(rc, 0, out)
        self.assertIn("stands for this rebuild", out)
        self.assertEqual(len(list(self.bk.glob("context_pre_links_*.db"))), 1, "the day's backup stands for its own")
        runs = self.runs()
        self.assertEqual(len(runs), 2)
        self.assertTrue(runs[1][0].endswith("context_daily.db"), runs[1][0])
        self.assertEqual(runs[1][1], 3, "Uddalaka now named with Janaka and Videha")

    def test_an_old_daily_backup_does_not_count(self):
        d = self.bk / "context_daily.db"
        d.write_bytes(b"old")
        old = time.time() - 30 * 3600
        os.utime(d, (old, old))
        rc, out = self.run_tool("--scheduled")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(list(self.bk.glob("context_pre_links_*.db"))), 1, "older than 26 hours: a new backup")

    def test_a_writer_leaves_it_to_the_next_tick(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        srv = http.server.HTTPServer(("127.0.0.1", port), Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            before = hashlib.md5(self.db.read_bytes()).hexdigest()
            rc, out = self.run_tool("--scheduled", url="http://127.0.0.1:%d" % port)
            self.assertEqual(rc, 0, out)
            self.assertIn("SKIP: the dashboard runs a database writer (translate sb)", out)
            self.assertEqual(hashlib.md5(self.db.read_bytes()).hexdigest(), before)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_immutable_refused(self):
        rc, out = self.run_tool("--db", str(self.db), "--immutable", "--scheduled")
        self.assertEqual(rc, 2, out)


class TheRunner(unittest.TestCase):
    def test_step_d_after_step_c(self):
        b = RUNNER.read_bytes()
        if MARK.encode() not in b:
            self.skipTest("not applied here")
        self.assertTrue(all(x < 128 for x in b), "PowerShell 5.1 reads it in the system code page")
        s = b.decode("ascii")
        c = s.index("STEP c entities")
        d = s.index("scripts\\entity_links.py --scheduled --claims data\\shelf\\claims.db")
        self.assertLess(c, d)
        self.assertLess(d, s.index("scripts\\kin_index.py --check"))
        self.assertLess(d, s.index("DONE maintenance"))
        self.assertIn('if (Test-Path "data\\shelf\\kin.db")', s)
        self.assertIn("STEP d links SKIPPED", s, "a failure is logged and skipped")
        self.assertEqual(s.count("if (Test-Writer \"c\") { exit 0 }"), 1)

    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
