# -*- coding: ascii -*-
"""IMAGES_QUEUE_2026_10_04 - image jobs are listed, queued one at a time, with progress.
Fails before patch_images_queue_2026_10_04.py, passes after. No network."""
import importlib.util, json, sqlite3, sys, tempfile, threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

# The fake dashboard state. images_web reads these through launch.__globals__,
# exactly as it reads dashboard.py's when dashboard.py runs as __main__.
JOBS = {}
JOBS_LOCK = threading.Lock()
_KIND_SEM = {"translate": threading.Semaphore(1)}
LAUNCHED = []


class FakeJob:
    def __init__(self, jid, kind, doc, mode, active):
        self.id, self.kind, self.doc, self.mode = jid, kind, doc, mode
        self.start, self.end, self.ok, self.active, self.killed = time.time(), None, None, active, False
        self.out, self.err = "", ""


def fake_launch(kind, doc, argv, then=None, mode=""):
    LAUNCHED.append((kind, doc, list(argv), mode))
    jid = "job-%d" % len(LAUNCHED)
    with JOBS_LOCK:
        JOBS[jid] = FakeJob(jid, kind, doc, mode, active=(len(JOBS) == 0))
    return jid


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(REPO / "scripts" / (name + ".py")))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


class ImagesQueue(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        JOBS.clear(); LAUNCHED.clear(); _KIND_SEM.pop("images_gen", None); _KIND_SEM.pop("images_brief", None)
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name); self.t = t
        self.db = t / "c.db"
        c = sqlite3.connect(self.db)
        c.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                        "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, verse_ref TEXT,"
                        " text TEXT, translation TEXT, text_type TEXT);"
                        "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);"
                        "INSERT INTO docs VALUES(1,'X');"
                        "INSERT INTO passages VALUES(1,1,10,1,NULL,'sa','The wrestler stands.','mula');")
        c.commit(); c.close()
        self.lib = load("images"); self.web = load("images_web")
        con = self.lib._connect(str(self.db)); self.lib.ensure_schema(con)
        self.ids = self.lib.store_briefs(con, "X", [{"page": 10, "idx": 1, "title": "A", "brief": "b"}], {(10, 1)}, 6, "m")
        con.close()
        app = Flask("t")
        self.web.register(app, launch=fake_launch, root=t, py=lambda *a: ["py", *a], script=lambda n: n, db=str(self.db))
        app.view_functions["images_page"] = lambda: "page"
        self.c = app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_shared_semaphore_for_image_jobs(self):
        self.assertIn("images_gen", _KIND_SEM)
        self.assertIs(_KIND_SEM["images_gen"], _KIND_SEM["images_brief"])
        self.assertIsNot(_KIND_SEM["images_gen"], _KIND_SEM["translate"])

    def test_progress_flag_and_jobs_listing(self):
        self.c.post("/api/images/brief", json={"doc": "X", "max": 3})
        self.c.post("/api/images/generate", json={"doc": "X", "id": self.ids[0]})
        argv = LAUNCHED[0][2]
        self.assertIn("--progress", argv)
        pf = Path(argv[argv.index("--progress") + 1])
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(json.dumps({"phase": "asking", "step": 0, "total": 1}), encoding="utf-8")
        js = self.c.get("/api/images/jobs?doc=X").get_json()
        self.assertTrue(js["available"])
        by = {j["kind"]: j for j in js["jobs"]}
        self.assertEqual(by["images_brief"]["state"], "running")
        self.assertEqual(by["images_brief"]["progress"]["phase"], "asking")
        self.assertEqual(by["images_gen"]["state"], "queued")
        self.assertEqual(by["images_gen"]["position"], 1)
        JOBS["job-1"].ok = True; JOBS["job-1"].end = time.time(); JOBS["job-1"].out = "a\nstored 2 brief(s): [5, 6]"
        js = self.c.get("/api/images/jobs?doc=X").get_json()
        done = [j for j in js["jobs"] if j["id"] == "job-1"][0]
        self.assertEqual(done["state"], "done"); self.assertIn("stored 2", done["tail"])

    def test_images_py_writes_progress(self):
        pf = self.t / "p.json"
        con = self.lib._connect(str(self.db))
        con.execute("UPDATE doc_images SET status='brief-approved' WHERE id=?", (self.ids[0],)); con.commit(); con.close()
        calls = []
        def fake_generate(con, row, model, root, code, db, http=None):
            calls.append(row["id"])
            self.assertTrue(json.loads(pf.read_text(encoding="utf-8"))["current"].startswith("#%d" % row["id"]))
            return row["id"]
        self.lib.generate_one = fake_generate
        argv0 = sys.argv
        sys.argv = ["images.py", "--db", str(self.db), "--progress", str(pf), "generate", "--doc", "X", "--yes"]
        try:
            rc = self.lib.main()
        finally:
            sys.argv = argv0
        self.assertEqual(rc, 0); self.assertEqual(calls, [self.ids[0]])
        p = json.loads(pf.read_text(encoding="utf-8"))
        self.assertTrue(p["done"]); self.assertEqual((p["step"], p["total"]), (1, 1)); self.assertEqual(p["phase"], "finished")

    def test_page_has_the_tray(self):
        h = (REPO / "scripts" / "images_static.html").read_text(encoding="utf-8")
        self.assertIn("IMAGES_QUEUE_2026_10_04", h)
        self.assertIn("/api/images/jobs", h)
        self.assertNotIn("watch(j.job", h)


if __name__ == "__main__":
    unittest.main()
