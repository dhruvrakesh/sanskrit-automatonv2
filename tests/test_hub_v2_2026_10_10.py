# -*- coding: ascii -*-
"""HUB_V2_2026_10_10: the Srangam Hub asks the dashboard's light /api/health (or /api/jobs/running)
instead of the heavy /api/status, calls a dashboard that holds its port but answers slowly "busy",
shares one round of checks between pages, starts the dashboard with restart_dashboard.ps1, and shows
what the mirror, the pictures, the Corner desk and the maintenance task last did (/api/online), with
the database counted read-only in the background. Loads docs/hub/HUB_V2_2026-10-10/hub.py with its
folders pointed at a temp tree; no network, no port, never data/context.db."""
import importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
PAYLOAD = REPO / "docs" / "hub" / "HUB_V2_2026-10-10"


class FakeResp:
    def __init__(self, code=200, body=None):
        self.status_code = code
        self._body = body
        self.content = json.dumps(body).encode() if body is not None else b""
        self.headers = {"Content-Type": "application/json"}
        self.text = self.content.decode()

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def load_hub(tmp: Path):
    os.environ["SYMPHONY_AUTOMATON"] = str(tmp / "automaton")
    os.environ["SYMPHONY_BACKUPS"] = str(tmp / "backups")
    os.environ["SYMPHONY_WISDOMLIB"] = str(tmp / "wisdomlib")
    spec = importlib.util.spec_from_file_location("hub_v2_test", str(PAYLOAD / "hub.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_db(path: Path):
    con = sqlite3.connect(str(path))
    con.executescript(
        "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
        "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, translation TEXT, text_type TEXT, translated_at TEXT);"
        "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
        "CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, updated_at TEXT);"
        "CREATE TABLE brain_items(id INTEGER PRIMARY KEY);"
        "CREATE TABLE entities(id INTEGER PRIMARY KEY);"
        "CREATE TABLE entity_mentions(id INTEGER PRIMARY KEY);"
        "CREATE TABLE doc_stories(id INTEGER PRIMARY KEY, status TEXT);"
        "CREATE TABLE doc_images(id INTEGER PRIMARY KEY, status TEXT);")   # no doc_novels: an older database
    con.executemany("INSERT INTO docs VALUES(?,?)", [(1, "A"), (2, "B-RETIRED")])
    rows = [(1, 1, "x", "mula", "2026-10-01"), (2, 1, "y", None, "2026-10-09"), (3, 1, "", "mula", None),
            (4, 1, "z", "noise", None), (5, 2, "w", "mula", None), (6, 1, "v", "mula", None)]
    con.executemany("INSERT INTO passages VALUES(?,?,?,?,?)", rows)
    con.execute("INSERT INTO translations_l10n VALUES(1,'hi','h')")
    # 1 is current, 2 was retranslated after its vector, 6 has none
    con.executemany("INSERT INTO passage_embeddings VALUES(?,?,?)",
                    [(1, "m", "2026-10-02"), (2, "m", "2026-10-02"), (5, "m", "2026-10-02")])
    con.execute("INSERT INTO brain_items VALUES(1)")
    con.executemany("INSERT INTO entities VALUES(?)", [(1,), (2,)])
    con.executemany("INSERT INTO doc_stories(status) VALUES(?)", [("approved",), ("approved",), ("candidate",)])
    con.executemany("INSERT INTO doc_images(status) VALUES(?)", [("brief",), ("approved",)])
    con.commit(); con.close()


class HubV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpd = tempfile.TemporaryDirectory()
        t = Path(cls.tmpd.name)
        data = t / "automaton" / "data"; data.mkdir(parents=True)
        (t / "automaton" / "scripts").mkdir()
        (t / "backups").mkdir()
        make_db(data / "context.db")
        tables = {"docs": {"changed": 2}, "passages": {"changed": 5}}
        sync = [{"ts": "2026-10-10T03:02:59Z", "stopped": "done", "error": None, "seconds": 63.9, "client": "corpus_sync.py 4.3",
                 "tables": tables, "verified": {"groups_equal": 392, "groups_different": 0}},
                {"ts": "2026-10-10T05:02:15Z", "stopped": "error", "verified": None, "tables": {},
                 "error": "corpus-ingest unreachable: <urlopen error [Errno 11001] getaddrinfo failed>", "client": "corpus_sync.py 4.3"}]
        (data / "corpus_sync_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sync) + "not json\n", encoding="utf-8")
        media = [{"ts": "2026-10-10T03:03:02Z", "stopped": "done", "files": {"needed": 114, "on_drive": 100,
                  "uploaded": 12, "skipped": 2}, "here": {"pictures": 57, "approved": 18, "novels": 2}}]
        (data / "corpus_media_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in media), encoding="utf-8")
        day = time.strftime("%Y-%m-%d", time.gmtime())
        corner = [{"ts": day + "T05:28:21Z", "stopped": "done", "taken": 1, "done": 1, "failed": 0, "queued": 0,
                   "mail": {"configured": True, "sent": 1}, "client": "corner_worker.py 1.2"},
                  {"ts": day + "T05:38:18Z", "stopped": "done", "taken": 0, "done": 0, "failed": 0, "queued": 0,
                   "mail": {"configured": True, "sent": 0}, "client": "corner_worker.py 1.2"}]
        (data / "corner_worker_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in corner), encoding="utf-8")
        (t / "backups" / "maintenance_log.txt").write_text(
            "[2026-10-09 11:59:59] TICK - maintenance runner started (user=dhruv)\n"
            "[2026-10-09 12:00:00] START maintenance\n"
            "Done. 449 verses processed this run\n"
            "[2026-10-09 12:14:23] DONE maintenance - total 861s\n"
            "[2026-10-09 15:00:02] TICK - maintenance runner started (user=dhruv)\n"
            "[2026-10-09 15:00:02] SKIP: dashboard busy (5 job(s) running/queued)\n"
            "[2026-10-10 09:00:01] TICK - maintenance runner started (user=dhruv)\n"
            "[2026-10-10 09:00:02] SKIP: dashboard busy (1 job(s) running/queued)\n"
            "[2026-10-10 12:00:01] TICK - maintenance runner started (user=dhruv)\n"
            "[2026-10-10 12:00:02] dashboard runs 1 OCR job(s) only (page files, not the database) - ok to maintain\n"
            "[2026-10-10 12:00:03] START maintenance\n"
            "  40/449 seen -+ 40 marked\n", encoding="utf-8")
        cls.h = load_hub(t)
        cls.c = cls.h.app.test_client()
        cls.data = data

    @classmethod
    def tearDownClass(cls):
        for k in ("SYMPHONY_AUTOMATON", "SYMPHONY_BACKUPS", "SYMPHONY_WISDOMLIB"):
            os.environ.pop(k, None)
        cls.tmpd.cleanup()

    def setUp(self):
        self.h._SERVICES.update(at=0.0, data=None)

    # ---- the files -------------------------------------------------------------------------
    def test_payload_is_ascii_and_marked(self):
        for name in ("hub.py", "hub.html"):
            b = (PAYLOAD / name).read_bytes()
            self.assertTrue(all(x < 128 for x in b), name)
            self.assertIn(b"HUB_V2_2026_10_10", b)
            self.assertNotIn(b"\r\n", b, name + " is LF, as the hub repo keeps it")

    def test_the_installer_carries_this_payload(self):
        spec = importlib.util.spec_from_file_location("patch_hub_v2", str(REPO / "scripts" / "patch_hub_v2_2026_10_10.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        for name in ("hub.py", "hub.html"):
            self.assertEqual(mod.md5n((PAYLOAD / name).read_bytes()), mod.V2[name], name)
        self.assertIn("HUB_V2_2026_10_10", mod.README_SECTION)

    def test_page_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        h = (PAYLOAD / "hub.html").read_text(encoding="utf-8")
        js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
        p = Path(self.tmpd.name) / "hub.js"; p.write_text(js, encoding="utf-8")
        r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for k in ("engine", "db", "brain", "mirror", "media", "corner", "srangam", "panchang", "booksmith"):
            self.assertIn('id="d-%s"' % k, h)
            self.assertIn('id="f-%s"' % k, h)
        self.assertEqual(len(re.findall(r'id="f-(srangam|automaton|panchang|booksmith)-frame"', h)), 4)

    # ---- the dashboard's health ------------------------------------------------------------
    def test_health_from_api_health(self):
        body = {"ok": True, "mark": "DESK_HEAL_2026_10_10",
                "jobs": {"count": 1, "active": 1, "queued": 0,
                         "running": [{"kind": "ocr", "doc": "Yoga", "state": "running", "elapsed_s": 72000}]}}
        with mock.patch.object(self.h.requests, "get", return_value=FakeResp(200, body)) as g:
            a = self.h.automaton_health()
        self.assertEqual(g.call_args[0][0], "http://127.0.0.1:5057/api/health")
        self.assertEqual((a["up"], a["state"], a["jobs"]["count"], a["mark"]), (True, "up", 1, "DESK_HEAL_2026_10_10"))
        self.assertEqual(a["jobs"]["running"][0]["kind"], "ocr")

    def test_an_older_dashboard_is_asked_its_jobs(self):
        seen = []

        def get(url, **kw):
            seen.append(url)
            if url.endswith("/api/health"):
                return FakeResp(404, {"error": "not found"})
            return FakeResp(200, {"running": [], "count": 0, "active": 0, "queued": 0})
        with mock.patch.object(self.h.requests, "get", side_effect=get):
            a = self.h.automaton_health()
        self.assertEqual([u.rsplit("/", 2)[-2] + "/" + u.rsplit("/", 1)[-1] for u in seen], ["api/health", "jobs/running"])
        self.assertEqual((a["up"], a["state"], a["jobs"]["count"]), (True, "up", 0))

    def test_slow_but_holding_its_port_is_busy_not_down(self):
        exc = self.h.requests.ReadTimeout("slow")
        with mock.patch.object(self.h.requests, "get", side_effect=exc), \
                mock.patch.object(self.h, "_port_open", return_value=True):
            a = self.h.automaton_health()
        self.assertEqual((a["up"], a["state"], a["error"]), (True, "busy", "ReadTimeout"))
        with mock.patch.object(self.h.requests, "get", side_effect=self.h.requests.ConnectionError("no")), \
                mock.patch.object(self.h, "_port_open", return_value=False):
            a = self.h.automaton_health()
        self.assertEqual((a["up"], a["state"]), (False, "down"))

    def test_one_round_of_checks_serves_every_page(self):
        calls = []

        def get(url, **kw):
            calls.append(url)
            return FakeResp(200, {"ok": True, "jobs": {"count": 0, "running": []}})
        with mock.patch.object(self.h.requests, "get", side_effect=get):
            a = self.c.get("/api/services").get_json()
            n = len(calls)
            b = self.c.get("/api/services").get_json()
        self.assertEqual(len(calls), n, "the second page is served from the same round")
        self.assertEqual(a, b)
        self.assertEqual(a["mark"], "HUB_V2_2026_10_10")
        self.assertFalse(any(u.endswith("/api/status") for u in calls), "never the heavy /api/status")

    # ---- starting it -----------------------------------------------------------------------
    def test_start_uses_the_detached_launcher(self):
        cwd, argv, long_running = self.h.ACTIONS["start-automaton"]
        self.assertEqual(argv[:5], ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
        self.assertTrue(argv[5].endswith("restart_dashboard.ps1"))
        self.assertNotIn("run.bat", " ".join(argv))

    def test_never_started_twice(self):
        with mock.patch.object(self.h, "_port_open", return_value=True), \
                mock.patch.object(self.h.subprocess, "Popen") as po:
            r = self.c.post("/api/run/start-automaton")
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.get_json()["already"])
        po.assert_not_called()

    def test_the_proxy_never_forwards_the_heavy_status(self):
        self.assertEqual(self.c.get("/proxy/automaton/api/status").status_code, 403)
        with mock.patch.object(self.h.requests, "get", return_value=FakeResp(200, {"budget_usd": 8})) as g:
            r = self.c.get("/proxy/automaton/api/budget")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(g.call_args[0][0], "http://127.0.0.1:5057/api/budget")

    # ---- what the desk did -----------------------------------------------------------------
    def test_online(self):
        self.h._DB.update(at=None, data=None, running=False)
        with mock.patch.object(self.h, "tasks_snapshot", return_value={}):
            self.h.db_snapshot()                            # starts the count in the background
            for _ in range(100):
                if self.h._DB["at"]:
                    break
                time.sleep(0.05)
            o = self.c.get("/api/online").get_json()
        db = o["db"]
        self.assertEqual(db["texts"], 1)
        self.assertEqual(db["verses"], {"all": 4, "english": 3})   # noise and the retired text are not verses
        self.assertEqual(db["hindi"], 1)
        self.assertEqual(db["vectors"], 3)
        self.assertEqual(db["to_embed"], 2, "6 has no vector and 2 was retranslated after its vector")
        self.assertEqual(db["stories"], {"approved": 2, "candidate": 1})
        self.assertIn("novels", db["missing"], "a table the database does not have is reported, not fatal")
        m = o["mirror"]
        self.assertEqual(m["last"]["stopped"], "error"); self.assertIn("getaddrinfo", m["last"]["error"])
        self.assertEqual((m["last_ok"]["equal"], m["last_ok"]["different"], m["last_ok"]["changed"]), (392, 0, 7))
        self.assertEqual(o["media"]["last_ok"]["files"]["on_drive_after"], 114, "before the run, plus what it sent or found")
        self.assertEqual(o["corner"]["today"], {"rounds": 2, "done": 1, "failed": 0})
        mt = o["maintenance"]
        self.assertEqual(mt["last_done"]["at"], "2026-10-09 12:14:23")
        self.assertEqual(mt["skips_since_done"], 2)
        self.assertEqual(mt["last_tick"], "2026-10-10 12:00:01")
        self.assertEqual(mt["unfinished_start"], "2026-10-10 12:00:03", "a START with nothing after it")

    def test_a_failed_final_check_is_not_a_clean_run(self):
        rows = [{"ts": "2026-10-10T07:02:00Z", "stopped": "done", "error": None, "tables": {"passages": {"changed": 3}},
                 "verified": {"groups_equal": 0, "groups_different": None, "different": [], "error": "timed out"}}]
        log = self.data / "corpus_sync_log.jsonl"
        keep = log.read_bytes()
        try:
            log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            m = self.h._mirror_state()
        finally:
            log.write_bytes(keep)
        self.assertEqual(m["last"]["verify_error"], "timed out")
        self.assertIsNone(m["last"]["different"])
        h = (PAYLOAD / "hub.html").read_text(encoding="utf-8")
        self.assertIn("L.verify_error", h); self.assertIn("L.different === 0", h)

    def test_the_task_check_survives_any_error(self):
        self.h._TASKS.update(at=None, data=None, running=True)
        with mock.patch.object(self.h.subprocess, "run", side_effect=RuntimeError("boom")):
            self.h._tasks_refresh()
        self.assertEqual(self.h._TASKS["data"], {"error": "RuntimeError"})
        self.assertFalse(self.h._TASKS["running"])

    def test_a_finished_start_makes_the_next_look_fresh(self):
        self.h._SERVICES.update(at=time.time(), data={"x": 1})
        proc = mock.Mock(); proc.wait.return_value = 0; proc.returncode = 0
        proc.stdout = iter([])
        proc.stdout = mock.Mock(); proc.stdout.readline.return_value = ""
        self.h.JOBS["t-start"] = {"proc": proc, "started": time.time(), "lines": [], "done": False, "rc": None}
        self.h.reader_thread("t-start", proc)
        for _ in range(50):
            if self.h._SERVICES["at"] == 0.0:
                break
            time.sleep(0.02)
        self.assertEqual(self.h._SERVICES["at"], 0.0)
        self.assertTrue(self.h.JOBS["t-start"]["done"])

    def test_the_database_is_opened_read_only(self):
        db = self.data / "context.db"
        before = (db.stat().st_mtime, db.stat().st_size)
        self.h._count_db()
        self.assertEqual((db.stat().st_mtime, db.stat().st_size), before)
        self.assertIn("mode=ro", (PAYLOAD / "hub.py").read_text(encoding="ascii"))

    def test_corpus_stats_never_queries_in_the_request(self):
        with mock.patch.object(self.h, "_count_db", side_effect=AssertionError("queried in the request")):
            self.h._DB.update(at=time.time(), data={"texts": 5, "passages": {"all": 9, "english": 4}, "hindi": 2},
                              running=False)
            r = self.c.get("/api/corpus-stats").get_json()
        self.assertEqual(r["db"], {"docs": 5, "passages": 9, "translated": 4, "by_lang": {"hi": 2}})
        self.assertIn("error", r["crawl"])


if __name__ == "__main__":
    unittest.main()
