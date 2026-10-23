# -*- coding: ascii -*-
"""ENTITY_LINKS_2026_10_22: scripts/entity_links.py stores the links our texts make between the names (R1): "together"
(one passage) and "near" (two passages of one text no more than 5 apart); a list (more than 12 names) and a retired
text left out. A count writes nothing; --apply makes a backup first, rebuilds the table whole and refuses while the
dashboard runs a writer; the scholars' check reads each claim against the links. It agrees with relations_census.py.
A made-up database in a temp folder; the dashboard is a stub on a local port or none."""
import csv, hashlib, http.server, importlib.util, json, os, socket, sqlite3, subprocess, sys, tempfile, threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "entity_links.py"
CENSUS = REPO / "scripts" / "relations_census.py"
MARK = "ENTITY_LINKS_2026_10_22"
J, Y, V, U, A, F = 1, 2, 3, 4, 5, 6


def make_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
    CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, verse_ref TEXT, page_no INTEGER, idx INTEGER,
                           text TEXT, translation TEXT);
    CREATE TABLE entities (id INTEGER PRIMARY KEY, canonical TEXT, kind TEXT);
    CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
    """)
    con.executemany("INSERT INTO docs VALUES (?,?)", [(1, "sb"), (2, "mbh"), (3, "old-RETIRED")])
    ps = [(i, 1, "14.%d" % i, 1, i) for i in range(1, 10)]          # sb: nine passages in order
    ps += [(10, 2, "1.1", 1, 1), (30, 2, "1.2", 1, 2), (20, 3, "x", 1, 1)]
    con.executemany("INSERT INTO passages (id, doc_id, verse_ref, page_no, idx) VALUES (?,?,?,?,?)", ps)
    ents = [(J, "Janaka", "person"), (Y, "Y\u0101j\u00f1avalkya", "person"), (V, "Videha", "place"),
            (U, "Udd\u0101laka", "person"), (A, "Aj\u0101ta\u015batru", "person"), (F, "Far", "person")]
    ents += [(100 + i, "N%d" % i, "person") for i in range(13)]
    con.executemany("INSERT INTO entities VALUES (?,?,?)", ents)
    m = [(J, 1), (Y, 1), (J, 2), (Y, 2), (V, 2), (U, 5), (F, 9), (J, 10), (Y, 10), (J, 20), (A, 20)]
    m += [(100 + i, 30) for i in range(13)]                          # a list of 13: left out
    con.executemany("INSERT INTO entity_mentions (entity_id, passage_id) VALUES (?,?)", m)
    con.commit()
    con.close()


def make_claims(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript("""
    CREATE TABLE claims (id INTEGER PRIMARY KEY, read_id INTEGER, work TEXT, pdf_page INTEGER, printed TEXT, n INTEGER,
      subject TEXT, subject_printed TEXT, relation TEXT, object TEXT, claim TEXT, quote TEXT, quote_check TEXT,
      quote_score REAL, stance TEXT, hedge TEXT, who TEXT, at TEXT);
    CREATE TABLE claim_links (claim_id INTEGER NOT NULL, role TEXT, name TEXT, pkey TEXT, entity_id INTEGER NOT NULL,
      canonical TEXT, kind TEXT, how TEXT, cands INTEGER, linker TEXT, at TEXT);
    """)
    cl = [(1, "Yajnavalkya was a contemporary of Janaka."), (2, "Uddalaka was of Janaka's court."),
          (3, "Far knew Janaka."), (4, "Ajatasatru was a contemporary of Janaka."), (5, "Janaka ruled."),
          (6, "Janaka was Janaka.")]
    con.executemany("INSERT INTO claims (id, work, printed, relation, claim, stance) VALUES (?, 'phai1923', '17', "
                    "'contemporary_of', ?, 'asserts')", cl)
    ln = [(1, "subject", Y), (1, "object", J), (2, "subject", U), (2, "object", J), (3, "subject", F),
          (3, "object", J), (4, "subject", A), (4, "object", J), (5, "subject", J), (6, "subject", J), (6, "object", J)]
    con.executemany("INSERT INTO claim_links (claim_id, role, entity_id) VALUES (?,?,?)", ln)
    con.commit()
    con.close()


def content_md5(db: Path, tables=("docs", "passages", "entities", "entity_mentions")) -> str:
    con = sqlite3.connect(str(db))
    h = hashlib.md5()
    for t in tables:
        for r in con.execute("SELECT * FROM %s ORDER BY 1" % t):
            h.update(repr(r).encode())
    con.close()
    return h.hexdigest()


class Stub(http.server.BaseHTTPRequestHandler):
    jobs = []

    def do_GET(self):
        b = json.dumps({"running": self.jobs}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


class TheLinks(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data").mkdir()
        self.db = t / "data" / "context.db"
        self.claims = t / "claims.db"
        make_db(self.db)
        make_claims(self.claims)
        self.bk = t / "bk"

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a, url="http://127.0.0.1:9"):
        env = dict(os.environ, SA_DASHBOARD_URL=url, PYTHONIOENCODING="utf-8", SA_BACKUP_DIR=str(self.bk))
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t)] + list(a), capture_output=True,
                           text=True, encoding="utf-8", timeout=120, env=env)
        return r.returncode, r.stdout + r.stderr

    def links(self):
        con = sqlite3.connect(str(self.db))
        try:
            return {(a, b, rel): (n, t, json.loads(p)) for a, b, rel, n, t, p in con.execute(
                "SELECT a, b, rel, passages, texts, places FROM entity_links")}
        finally:
            con.close()

    def test_count_writes_nothing(self):
        before = hashlib.md5(self.db.read_bytes()).hexdigest()
        rc, out = self.run_tool("--name", "janaka")
        self.assertEqual(rc, 0, out)
        self.assertIn("3 named together in one passage, 7 named near", out)
        self.assertIn("1 lists of more than 12 names left out", out)
        self.assertIn("not built yet", out)
        self.assertNotIn("Aj\u0101ta\u015batru", out.split("janaka:")[1], "named only in a retired text")
        self.assertEqual(hashlib.md5(self.db.read_bytes()).hexdigest(), before, "a count writes nothing")
        self.assertFalse(self.bk.exists(), "no backup for a count")

    def test_apply_backup_then_rebuild(self):
        before = content_md5(self.db)
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(list(self.bk.glob("context_pre_links_*.db"))), 1, "the backup first")
        got = self.links()
        self.assertEqual(sum(1 for k in got if k[2] == "together"), 3)
        self.assertEqual(sum(1 for k in got if k[2] == "near"), 7)
        self.assertEqual(got[(J, Y, "together")][:2], (3, 2), "passages 1, 2 and 10; texts sb and mbh")
        self.assertEqual(got[(J, U, "near")][:2], (3, 1), "passages 1, 2 and 5: within 5 of one another")
        self.assertNotIn((J, F, "near"), got, "7 and 8 passages apart: not near")
        self.assertIn((U, F, "near"), got)
        self.assertFalse([k for k in got if k[0] >= 100 or k[1] >= 100], "a list is left out")
        self.assertFalse([k for k in got if A in k[:2]], "a retired text is left out")
        self.assertEqual(got[(J, Y, "together")][2][0], [1, "sb", "14.1"], "places: passage, text, reference")
        self.assertEqual(content_md5(self.db), before, "nothing else in the database is written")
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.links()), 10, "rebuilt whole, not added to")
        con = sqlite3.connect(str(self.db))
        self.assertEqual(con.execute("SELECT COUNT(*), MAX(together), MAX(near) FROM entity_link_runs").fetchone(),
                         (2, 3, 7))
        con.close()
        rc, out = self.run_tool()
        self.assertIn("holds 3 together, 7 near: as counted now", out)

    def test_refuses_while_a_writer_runs(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        Stub.jobs = [{"kind": "translate", "doc": "sb", "state": "running"}]
        srv = http.server.HTTPServer(("127.0.0.1", port), Stub)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            before = hashlib.md5(self.db.read_bytes()).hexdigest()
            rc, out = self.run_tool("--apply", url="http://127.0.0.1:%d" % port)
            self.assertEqual(rc, 1, out)
            self.assertIn("REFUSE: the dashboard runs a database writer (translate sb)", out)
            self.assertEqual(hashlib.md5(self.db.read_bytes()).hexdigest(), before)
            self.assertFalse(self.bk.exists(), "no backup: nothing was to be written")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_the_scholars_check(self):
        before = hashlib.md5(self.claims.read_bytes()).hexdigest()
        rc, out = self.run_tool("--claims", str(self.claims))
        self.assertEqual(rc, 0, out)
        self.assertIn("4 claims whose subject and object are both our names: named together 1; named near 1; "
                      "both named, never near 1; one not in our texts 1", out)
        with open(self.t / "exports" / "claims_in_our_texts.csv", encoding="utf-8-sig") as f:
            rows = {int(r["claim_id"]): r for r in csv.DictReader(f)}
        self.assertEqual({k: r["verdict"] for k, r in rows.items()},
                         {1: "named together", 2: "named near", 3: "both named, never near", 4: "one not in our texts"})
        self.assertEqual((rows[1]["passages"], rows[1]["texts"]), ("3", "2"))
        self.assertTrue(rows[1]["places"].startswith("sb 14.1"))
        j = json.loads((self.t / "exports" / "claims_in_our_texts.json").read_text(encoding="utf-8"))
        self.assertEqual(j["by_relation"]["contemporary_of"]["named near"], 1)
        self.assertEqual(hashlib.md5(self.claims.read_bytes()).hexdigest(), before, "the claims are only read")

    def test_agrees_with_the_census(self):
        spec = importlib.util.spec_from_file_location("relations_census_t", str(CENSUS))
        rc_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rc_mod)
        spec2 = importlib.util.spec_from_file_location("entity_links_t", str(TOOL))
        el = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(el)
        con = sqlite3.connect(str(self.db))
        try:
            census = rc_mod.census(con)
            mine = el.compute(con)
        finally:
            con.close()
        self.assertEqual(census["together"]["pairs"], mine["together"])
        self.assertEqual(census["mentions"], mine["mentions"])
        self.assertEqual(census["together"]["lists_left_out"], mine["lists_left_out"])
        self.assertEqual(el.MAX_NAMES, rc_mod.MAX_NAMES)

    def test_guards_ascii_and_mark(self):
        rc, out = self.run_tool("--db", str(self.db), "--immutable", "--apply")
        self.assertEqual(rc, 2, out)
        rc, out = self.run_tool("--db", str(self.t / "none.db"))
        self.assertEqual(rc, 2, out)
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
