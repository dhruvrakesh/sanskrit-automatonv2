# -*- coding: ascii -*-
"""DESK_HEAL_2026_10_10: /api/status is worked out once at a time and kept a few seconds (the Srangam
Hub and the page asked it every 5 s each and the reads overlapped); /api/health answers from memory;
the Library says what the last run of a text did when it could not do the work, and follows the run a
button starts; History tells held and nothing-to-do from a failure; Usage reads cost_tracker's summary;
the maintenance task runs beside an OCR job. Imports scripts/dashboard.py as a module (no server, no
port); temp files only, never data/context.db."""
import importlib.util, json, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
KARAN = "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi"

HELD_TAIL = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): 41.0% of " + KARAN + "'s passages carry Tesseract "
             "debris ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc " + KARAN +
             " --threshold 101 --include-unassessed\r\n  Translate anyway: add --allow-debris (dashboard: set "
             "SA_ALLOW_DEBRIS=1).\r\n")


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_desk_heal", str(REPO / "scripts" / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def rec(kind, doc, ok, rc, tail, t):
    return {"id": "j%d" % t, "kind": kind, "doc": doc, "start": t, "end": t + 1, "ok": ok, "rc": rc,
            "duration_s": 1.0, "out_lines": 3, "err_preview": "", "out_tail": tail}


class DeskHeal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.c = cls.d.app.test_client()
        cls.db = str(t / "context.db")
        con = sqlite3.connect(cls.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
            " translation TEXT, translation_qa REAL, text_type TEXT);"
            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);")
        for i, code in enumerate([KARAN, "Ganita", "Dhanur", "Siddhanta", "Whole"], 1):
            con.execute("INSERT INTO docs VALUES(?,?,?)", (i, code, "agama"))
            for k in range(4):
                tr = "x" if (k < 2 or code in ("Dhanur", "Whole")) else ""
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation) VALUES(?,?,?,?,?)",
                            (i, 1, k, "s", tr))
        con.execute("INSERT INTO translations_l10n SELECT id,'hi','h' FROM passages WHERE doc_id=5")
        con.commit(); con.close()
        jobs = [
            rec("translate", KARAN, False, 3, HELD_TAIL, 100),
            rec("translate_hi", KARAN, False, 3, HELD_TAIL, 200),
            rec("translate", "Ganita", True, 0, "\r\nDone. 1/180 translated | 180 quality-skipped | 0 errors\r\n", 300),
            rec("translate_hi", "Dhanur", True, 0, "[NOTHING] doc 'Dhanur': 0 translatable verses\r\n", 400),
            rec("translate_both", "Siddhanta", False, 3, HELD_TAIL.replace(KARAN, "Siddhanta"), 500),
            rec("translate", "Whole", False, 3, HELD_TAIL, 50),           # an old hold ...
            rec("translate", "Whole", True, 0, "\r\nDone. 4/4 translated | 0 quality-skipped | 0 errors\r\n", 600),
            rec("translate", "Piped", False, 3, HELD_TAIL.replace(KARAN, "Piped"), 700),
            rec("pipeline", "Piped", True, 0, "  OCR         : OK\r\n  Ingest      : OK\r\n", 800),   # did not translate
            rec("translate_hi", "Piped2", False, 3, HELD_TAIL.replace(KARAN, "Piped2"), 700),
            rec("translate", "Piped2", False, 3, HELD_TAIL.replace(KARAN, "Piped2"), 701),
            rec("pipeline", "Piped2", True, 0, "  Ingest      : OK\r\n  Translate   : OK\r\n", 800),
        ]
        cls.d.JOBS_LOG_PATH.write_text("".join(json.dumps(j) + "\n" for j in jobs), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def tearDown(self):
        self.d._status_forget()

    # ---- the marker ------------------------------------------------------------------------
    def test_marker_in_every_file(self):
        for rel in ("scripts/dashboard.py", "scripts/dashboard_static.html", "scripts/maintenance_runner.ps1"):
            self.assertIn("DESK_HEAL_2026_10_10", (REPO / rel).read_text(encoding="utf-8"), rel)

    def test_powershell_file_is_ascii(self):
        self.assertTrue(all(b < 128 for b in (REPO / "scripts" / "maintenance_runner.ps1").read_bytes()))

    # ---- /api/status ----------------------------------------------------------------------
    def test_status_is_worked_out_once_for_callers_that_overlap(self):
        calls = []
        real = self.d.build_status

        def slow(*a):
            calls.append(1); time.sleep(0.4); return [{"doc": "x", "n": len(calls)}]
        self.d.build_status = slow
        try:
            out = []
            ths = [threading.Thread(target=lambda: out.append(self.c.get("/api/status").get_json())) for _ in range(5)]
            [t.start() for t in ths]; [t.join() for t in ths]
            self.assertEqual(len(calls), 1, "five callers that overlap share one read")
            self.assertTrue(all(o == [{"doc": "x", "n": 1}] for o in out))
            self.c.get("/api/status"); self.assertEqual(len(calls), 1, "kept STATUS_TTL_S")
            self.c.get("/api/status?fresh=1"); self.assertEqual(len(calls), 2, "?fresh=1 works it out again")
            self.d._status_forget(); self.c.get("/api/status"); self.assertEqual(len(calls), 3, "a job that ends clears it")
        finally:
            self.d.build_status = real

    def test_a_read_that_began_before_a_job_ended_is_not_kept(self):
        real = self.d.build_status
        n = []

        def build(*a):
            n.append(1)
            if len(n) == 1:
                self.d._status_forget()     # a job ends while this read is under way
            return [{"n": len(n)}]
        self.d.build_status = build
        try:
            self.assertEqual(self.c.get("/api/status").get_json(), [{"n": 1}])
            self.assertEqual(self.c.get("/api/status").get_json(), [{"n": 2}], "the older answer was not kept")
            self.assertEqual(self.c.get("/api/status").get_json(), [{"n": 2}], "the newer one is")
        finally:
            self.d.build_status = real

    def test_an_import_clears_the_status(self):
        src = (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        i = src.index("def _do_import(")
        j = src.index("return results", i)
        self.assertIn("_status_forget()", src[i:j])

    def test_a_job_that_ends_clears_the_status(self):
        src = (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        i = src.index("_persist_job(job)  # write to disk immediately")
        self.assertIn("_status_forget()", src[i:i + 200])

    # ---- /api/health ----------------------------------------------------------------------
    def test_health_answers_from_memory(self):
        J = self.d.Job
        j1 = J.__new__(J); j2 = J.__new__(J)
        for j, i, k, a in ((j1, "a1", "ocr", True), (j2, "a2", "translate_hi", False)):
            j.id, j.kind, j.doc, j.ok, j.active, j.start = i, k, "Yoga", None, a, time.time() - 30
        with self.d.JOBS_LOCK:
            self.d.JOBS.update({"a1": j1, "a2": j2})
        try:
            t0 = time.time(); r = self.c.get("/api/health").get_json()
            self.assertLess(time.time() - t0, 0.5)
            self.assertTrue(r["ok"]); self.assertEqual(r["mark"], "DESK_HEAL_2026_10_10")
            self.assertEqual(r["jobs"]["count"], 2); self.assertEqual(r["jobs"]["active"], 1)
            self.assertEqual(r["jobs"]["queued"], 1)
            self.assertEqual({x["kind"] for x in r["jobs"]["running"]}, {"ocr", "translate_hi"})
        finally:
            with self.d.JOBS_LOCK:
                self.d.JOBS.pop("a1", None); self.d.JOBS.pop("a2", None)

    # ---- the Library ----------------------------------------------------------------------
    def test_notes_from_the_job_history(self):
        n = self.d._library_notes()
        self.assertEqual([x["lang"] for x in n[KARAN]], ["both"])
        self.assertIn("English and Hindi held", n[KARAN][0]["text"])
        self.assertIn("Tesseract debris", n[KARAN][0]["text"])
        self.assertIn("ocr_consensus.py --doc " + KARAN + " --threshold 101 --include-unassessed", n[KARAN][0]["text"])
        self.assertIn("SA_ALLOW_DEBRIS=1", n[KARAN][0]["text"])
        self.assertEqual(n["Siddhanta"][0]["lang"], "both", "translate_both holds both languages")
        self.assertIn("1 of 180", n["Ganita"][0]["text"]); self.assertEqual(n["Ganita"][0]["lang"], "en")
        self.assertIn("nothing left", n["Dhanur"][0]["text"]); self.assertEqual(n["Dhanur"][0]["lang"], "hi")
        self.assertNotIn("Whole", n, "a newer run that worked replaces an old hold")
        self.assertEqual(n["Piped"][0]["lang"], "en", "a pipeline run that did not translate changes nothing")
        self.assertEqual([x["lang"] for x in n["Piped2"]], ["hi"], "one that translated English replaces the English hold")

    def test_library_shows_the_notes_and_follows_the_run(self):
        r = self.c.get("/library?db=" + self.db)
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        self.assertIn('class="cardnote"', h)
        self.assertIn("English and Hindi held", h)
        self.assertIn("1 of 180", h)
        self.assertIn("nothing left", h, "Dhanur lacks Hindi, and its last Hindi run found nothing to send")
        self.assertEqual(h.count('class="cardnote"'), 4, "Karan, Ganita, Dhanur, Siddhanta; not Whole")
        self.assertIn("_watchJob", h); self.assertIn("_jobVerdict", h)
        self.assertNotIn("queued \u2713", h)

    def test_library_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        h = self.c.get("/library?db=" + self.db).get_data(as_text=True)
        for i, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
            p = Path(self.tmp.name) / ("lib%d.js" % i)
            p.write_text(js, encoding="utf-8")
            r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verdicts_in_the_browser_script(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        h = self.c.get("/library?db=" + self.db).get_data(as_text=True)
        js = re.search(r"(function _jobVerdict\(j\)\{.*?\n\})", h, re.S).group(1)
        cases = [
            ({"ok": False, "out": HELD_TAIL}, "held"),
            ({"ok": False, "out": "KILLED by user"}, "stopped"),
            ({"ok": False, "out": "Traceback"}, "failed"),
            ({"ok": True, "out": "[NOTHING] doc 'x': 0 translatable verses"}, "nothing to do"),
            ({"ok": True, "out": "Done. 10/189 translated | 187 quality-skipped | 0 errors"}, "done: 10 of 189"),
            ({"ok": True, "out": "ok"}, "done"),
        ]
        prog = js + "\nconst C=" + json.dumps(cases) + ";\nfor (const [j,w] of C){ const v=_jobVerdict(j);" \
            " if(v.word!==w){ console.log('want '+w+' got '+v.word); process.exit(1);} }\n"
        p = Path(self.tmp.name) / "verdict.js"; p.write_text(prog, encoding="utf-8")
        r = subprocess.run([node, str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # ---- the dashboard page ----------------------------------------------------------------
    def test_page_script_parses_and_carries_the_changes(self):
        h = (REPO / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        for s in ("function histStatus(j)", "let _refreshing = false", "Object.keys(eng)",
                  "Loading the documents", "window._lastPipeRows", 'onclick="refresh(true)"', "&fresh=1",
                  "if (name === 'history') loadHistory();"):
            self.assertIn(s, h)
        self.assertNotIn("d.by_engine.length", h)
        node = shutil.which("node")
        if not node:
            return
        for i, js in enumerate(re.findall(r"<script>(.*?)</script>", h, re.S)):
            p = Path(self.tmp.name) / ("page%d.js" % i)
            p.write_text(js, encoding="utf-8")
            r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_maintenance_skips_only_for_jobs_that_write_the_database(self):
        ps = (REPO / "scripts" / "maintenance_runner.ps1").read_text(encoding="utf-8")
        self.assertIn('Where-Object { $_.kind -ne "ocr" }', ps)
        self.assertIn("OCR job(s) only", ps)
        self.assertIn('if ($writers.Count -gt 0) { Log "SKIP: dashboard busy', ps)


if __name__ == "__main__":
    unittest.main()
