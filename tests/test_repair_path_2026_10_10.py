# -*- coding: ascii -*-
"""REPAIR_PATH_2026_10_10: a translation that stops because of its scan offers its repair path there and
then. /api/repair starts the right run of repair_text.py for each step (the re-ingest under the
translate lock); the Library shows the repair bar under a hold or a quality note, a text set aside with
why and Restore instead of its translate buttons, and the texts with no English yet at the end;
/repair/<doc> is the text's page; the dashboard page's Log points at the path. Imports
scripts/dashboard.py as a module (no server, no port); temp files only, never data/context.db."""
import importlib.util, json, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELD = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc %s "
        "--threshold 101 --include-unassessed\r\n  Translate anyway: add --allow-debris (dashboard: set SA_ALLOW_DEBRIS=1).\r\n")


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_repair_path", str(REPO / "scripts" / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def rec(kind, doc, ok, rc, tail, t):
    return {"id": "j%d" % t, "kind": kind, "doc": doc, "start": t, "end": t + 1, "ok": ok, "rc": rc,
            "duration_s": 1.0, "out_lines": 3, "err_preview": "", "out_tail": tail}


def node():
    return shutil.which("node")


class RepairPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        cls.d.JOBS_LOG_PATH = t / "jobs.jsonl"
        cls.c = cls.d.app.test_client()
        cls.db = str(t / "context.db")
        con = sqlite3.connect(cls.db)
        con.executescript(
            "CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
            "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT,"
            " translation TEXT, translation_qa REAL, text_type TEXT);"
            "CREATE TABLE translations_l10n(passage_id INT, lang TEXT, translation TEXT);")
        # Held: some English, held; Zero: no English, held; Aside: set aside; Ganita: most below the bar
        for i, code in enumerate(["Held", "Zero", "Aside", "Ganita", "Fine"], 1):
            con.execute("INSERT INTO docs VALUES(?,?,?)", (i, code, "agama"))
            for k in range(4):
                tr = "x" if (code != "Zero" and k < 2) else ""
                con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation) VALUES(?,?,?,?,?)", (i, 1, k, "s", tr))
        con.execute("INSERT INTO translations_l10n SELECT id,'hi','h' FROM passages WHERE doc_id=1 AND translation='x'")
        con.commit(); con.close()
        jobs = [rec("translate", "Held", False, 3, HELD % "Held", 100),
                rec("translate_hi", "Zero", False, 3, HELD % "Zero", 200),
                rec("translate", "Aside", False, 3, HELD % "Aside", 300),
                rec("translate", "Ganita", True, 0, "\r\nDone. 1/180 translated | 180 quality-skipped | 0 errors\r\n", 400)]
        cls.d.JOBS_LOG_PATH.write_text("".join(json.dumps(r) + "\n" for r in jobs), encoding="utf-8")
        (t / "source_verdicts.jsonl").write_text(
            json.dumps({"doc": "Aside", "status": "set_aside", "reason": "pages 40-60 are unreadable",
                        "at": "2026-10-10T18:00:00"}) + "\n"
            + json.dumps({"doc": "Held", "status": "set_aside", "reason": "x", "at": "2026-10-10T18:01:00"}) + "\n"
            + "not json\n"
            + json.dumps({"doc": "Held", "status": "restored", "reason": "", "at": "2026-10-10T18:02:00"}) + "\n",
            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.launched = []
        self._launch = self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (self.launched.append((kind, doc, argv, mode)) or "jid1")

    def tearDown(self):
        self.d.launch = self._launch

    def post(self, **body):
        return self.c.post("/api/repair", json=body)

    # ---- /api/repair -----------------------------------------------------------------------
    def test_get_says_the_path_is_there(self):
        r = self.c.get("/api/repair").get_json()
        self.assertEqual(r["mark"], "REPAIR_PATH_2026_10_10"); self.assertEqual(r["max_usd"], 5.0)

    def test_each_step_starts_its_run(self):
        cases = [
            ({"step": "assess"}, "repair", []),
            ({"step": "repair"}, "repair", ["--repair", "--max-usd", "1.00"]),
            ({"step": "repair", "max_usd": 2.46}, "repair", ["--repair", "--max-usd", "2.46"]),
            ({"step": "repair", "max_usd": 0.001}, "repair", ["--repair", "--max-usd", "0.05"]),
            ({"step": "use"}, "repair_use", ["--use-repaired"]),
            ({"step": "use", "replace": 1603}, "repair_use", ["--use-repaired", "--replace", "1603"]),
            ({"step": "set_aside", "reason": "  pages\n40-60\tunreadable "}, "repair", ["--set-aside", "pages 40-60 unreadable"]),
            ({"step": "set_aside"}, "repair", ["--set-aside", "needs a better scan"]),
            ({"step": "restore"}, "repair", ["--restore"]),
        ]
        for body, kind, tail in cases:
            self.launched.clear()
            r = self.post(doc="Karan_Aagama-4", **body)
            self.assertEqual(r.status_code, 200, body)
            self.assertEqual(r.get_json()["job"], "jid1")
            k, doc, argv, mode = self.launched[0]
            self.assertEqual((k, doc, mode), (kind, "Karan_Aagama-4", body["step"]), body)
            i = [x.replace("\\", "/") for x in argv].index(str(REPO / "scripts" / "repair_text.py").replace("\\", "/"))
            self.assertIn("-u", argv[:i], "unbuffered, so the Log follows it")
            self.assertEqual(argv[i + 1:i + 4], ["--doc", "Karan_Aagama-4", "--from-dashboard"])
            self.assertEqual(argv[i + 4:], tail, body)

    def test_refusals(self):
        self.assertEqual(self.post(doc="../x", step="assess").status_code, 400)
        self.assertEqual(self.post(step="assess").status_code, 400)
        self.assertEqual(self.post(doc="K", step="rm").status_code, 400)
        r = self.post(doc="K", step="repair", max_usd=7.5)
        self.assertEqual(r.status_code, 400); self.assertIn("--max-usd 7.50", r.get_json()["error"])
        self.assertEqual(self.post(doc="K", step="repair", max_usd="lots").status_code, 400)
        self.assertEqual(self.post(doc="K", step="use", replace="all").status_code, 400)
        self.assertEqual(self.launched, [], "nothing starts on a refusal")

    # ---- the Library ------------------------------------------------------------------------
    def library(self):
        r = self.c.get("/library?db=" + self.db)
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def card(self, h, code):
        m = re.search(r'<div class="card-wrap" data-doc="%s">(.*?)<div class="bsacts"' % code, h, re.S)
        self.assertIsNotNone(m, code)
        return m.group(1)

    def test_the_library_offers_the_path(self):
        h = self.library()
        held = self.card(h, "Held")
        self.assertIn('id="rp-Held"', held); self.assertIn("Repair path: what now?", held)
        self.assertIn("English held", held, "DESK_HEAL's note is kept"); self.assertIn("Finish EN", held)
        self.assertIn('href="/repair/Held"', held)
        g = self.card(h, "Ganita")
        self.assertIn("1 of 180", g); self.assertIn('id="rp-Ganita"', g, "a quality note offers the path too")
        self.assertNotIn("repairbar", self.card(h, "Fine"))
        aside = self.card(h, "Aside")
        self.assertIn("Set aside on 2026-10-10: pages 40-60 are unreadable", aside)
        self.assertIn(">Restore</button>", aside)
        self.assertNotIn("Finish EN", aside); self.assertNotIn("Add Hindi", aside)
        self.assertNotIn("English held", aside, "the register is the newer word")
        self.assertNotIn("Set aside on", held, "restored after it was set aside")
        self.assertEqual(h.count('class="cardnote"'), 3, "Held and Ganita in the grid, Zero at the end")

    def test_texts_with_no_english_wait_at_the_end(self):
        h = self.library()
        i = h.index("Not yet readable")   # REPAIR_HEAL_2026_10_11 renamed it
        self.assertGreater(i, h.index('data-doc="Held"'))
        tail = h[i:]
        self.assertIn('id="rp-Zero"', tail); self.assertIn("EN 0/4", tail); self.assertIn("Hindi held", tail)
        self.assertNotIn('class="card-wrap" data-doc="Zero"', h, "not a Booksmith card")

    def test_the_library_script_parses_and_reads_the_next_step(self):
        if not node():
            self.skipTest("node is not installed")
        h = self.library()
        js = "\n".join(re.findall(r"<script>(.*?)</script>", h, re.S))
        p = self.t / "lib.js"; p.write_text(js, encoding="utf-8")
        r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        fn = re.search(r"(var _RP_NL = .*?)\nfunction _rpBox", h, re.S).group(1)
        q = "python scripts\\repair_text.py --doc K"
        cases = [
            (q + " --repair   (capped at --max-usd 1.00)", {"step": "repair", "max_usd": 1}),
            (q + " --repair --max-usd 2.46", {"step": "repair", "max_usd": 2.46}),
            (q + " --use-repaired", {"step": "use", "replace": None}),
            (q + " --use-repaired --replace 1603", {"step": "use", "replace": 1603}),
            (q + ' --set-aside "needs a better scan"   (or --repair again for the pages that failed)', {"step": "set_aside"}),
            (q + " --restore   (when a better scan is in the inbox)", {"step": "restore"}),
            ("translate it: Finish EN and Add Hindi in the Library", {"step": "translate"}),   # REPAIR_HEAL_2026_10_11
            ("", None),
        ]
        out = ("doc  REPAIR_PATH_2026_10_10\r\n  passages 4\r\nVERDICT: held by the guard; the scan can be repaired\r\n"
               "NEXT: " + q + " --repair   (capped at --max-usd 1.00)\r\n")
        prog = (fn + "\nconst C=" + json.dumps(cases) + ";\nfor (const [n, want] of C){ const s=_rpNext(n);"
                " if (want===null){ if (s!==null){ console.log('want null for '+n); process.exit(1);} continue; }"
                " for (const k in want){ if (s[k]!==want[k]){ console.log(n+': '+k+' '+s[k]); process.exit(1);} } }\n"
                "const v=_rpVerdict(" + json.dumps(out) + ");"
                " if (v.verdict!=='held by the guard; the scan can be repaired' || _rpNext(v.next).step!=='repair'){"
                " console.log(JSON.stringify(v)); process.exit(1);}\n")
        p = self.t / "next.js"; p.write_text(prog, encoding="utf-8")
        r = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # ---- /repair/<doc> ----------------------------------------------------------------------
    def test_the_repair_page(self):
        r = self.c.get("/repair/Held?db=" + self.db)
        self.assertEqual(r.status_code, 200)
        h = r.get_data(as_text=True)
        for s in ("Repair path", "4 passages", "English 2", "Hindi 2", 'id="rp-Held"', 'id="rplog-Held"',
                  "English held", "repairStep('Held', 'assess', null);", "function _watchRepair"):
            self.assertIn(s, h)
        self.assertNotIn("__", h.replace("__name__", ""), "every placeholder is filled")
        a = self.c.get("/repair/Aside?db=" + self.db).get_data(as_text=True)
        self.assertIn(">Restore</button>", a); self.assertIn("pages 40-60 are unreadable", a)
        self.assertEqual(self.c.get("/repair/a%20b").status_code, 400)
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "page.js"; p.write_text(js, encoding="utf-8")
            r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_source_verdicts(self):
        v = self.d._source_verdicts(self.t)
        self.assertEqual(sorted(v), ["Aside"])
        self.assertEqual(self.d._source_verdicts(self.t / "nowhere"), {})


class TheLock(unittest.TestCase):
    """The re-ingest is a database writer: it waits for the translate lock. The other steps do not."""
    @classmethod
    def setUpClass(cls):
        cls.d = sys.modules.get("dashboard_repair_path") or load_dashboard()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.tmp.name) / "jobs.jsonl"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def wait(self, cond, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            if cond():
                return True
            time.sleep(0.05)
        return False

    def test_use_waits_for_the_translate_lock(self):
        d = self.d
        cmd = [sys.executable, "-c", "print('VERDICT: ok')"]
        self.assertTrue(d._TRANSLATE_SEM.acquire(timeout=5))
        try:
            u = d.launch("repair_use", "LockT", cmd, mode="use")
            a = d.launch("repair", "LockT", cmd, mode="assess")
            self.assertTrue(self.wait(lambda: d.JOBS[a].ok is not None, 15), "an assessment does not wait")
            time.sleep(0.4)
            self.assertIsNone(d.JOBS[u].ok); self.assertFalse(d.JOBS[u].active, "queued behind the lock")
        finally:
            d._TRANSLATE_SEM.release()
        self.assertTrue(self.wait(lambda: d.JOBS[u].ok is not None, 15))
        self.assertTrue(d.JOBS[u].ok); self.assertIn("VERDICT: ok", d.JOBS[u].out)


class ThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO / "scripts" / "dashboard_static.html").read_text(encoding="utf-8")
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_marks_and_changes(self):
        for rel in ("scripts/dashboard.py", "scripts/dashboard_static.html"):
            src = (REPO / rel).read_text(encoding="utf-8")
            for m in ("REPAIR_PATH_2026_10_10", "LIVE_LOG_2026_10_10", "DESK_HEAL_2026_10_10"):
                self.assertIn(m, src, rel)
        for s in ("function addLog(line, cls, href)", "class=\"log-act\"", "function _repairHint(v, doc, past)",
                  "await _repairProbe;", "setInterval(watchFinished, 8000);", "_repairHint(v, activeJobs[jid].doc || v.doc, false);"):
            self.assertIn(s, self.html)
        b = (REPO / "scripts" / "repair_text.py").read_bytes()
        self.assertTrue(all(x < 128 for x in b))
        b = (REPO / "scripts" / "patch_repair_path_2026_10_10.py").read_bytes()
        self.assertTrue(all(x < 128 for x in b))

    def test_the_page_script_parses_and_reads_the_outcomes(self):
        if not node():
            self.skipTest("node is not installed")
        js = "\n".join(re.findall(r"<script>(.*?)</script>", self.html, re.S))
        p = Path(self.tmp.name) / "page.js"; p.write_text(js, encoding="utf-8")
        r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        fn = re.search(r"(function jobVerdict\(ok, out\) \{.*?\n\})", self.html, re.S).group(1)
        cases = [
            [False, HELD % "Natya_1", {"word": "held", "doc": "Natya_1"}],
            [True, "Done. 7/186 translated | 185 quality-skipped | 0 errors", {"word": "done", "stuck": True}],
            [True, "Done. 70/86 translated | 16 quality-skipped | 0 errors", {"word": "done", "stuck": False}],
            [True, "N  REPAIR_PATH_2026_10_10\r\nVERDICT: held; the scan can be repaired\r\nNEXT: x --repair\r\n",
             {"word": "repair", "tag": "[REPAIR]", "text": "held; the scan can be repaired"}],
            [False, "$ python ocr_consensus.py\nVERDICT: the repair stopped (ocr_consensus.py exit 1)\nNEXT: y\n",
             {"word": "repair: not done", "tag": "[REPAIR]"}],
            [False, "VERDICT: x\n[KILLED by user]", {"word": "stopped"}],
        ]
        prog = (fn + "\nconst C=" + json.dumps(cases) + ";\nfor (const [ok, out, want] of C){ const v=jobVerdict(ok, out);"
                " for (const k in want){ if (v[k]!==want[k]){ console.log(k+': want '+want[k]+' got '+v[k]); process.exit(1);} } }\n")
        p = Path(self.tmp.name) / "verdict.js"; p.write_text(prog, encoding="utf-8")
        r = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ThePatcher(unittest.TestCase):
    """It applies to the files as LIVE_LOG left them, once, keeping CRLF; and refuses without them."""
    PRE = {"scripts/dashboard.py": "82fe67599cadb1039b95168bda98b630",
           "scripts/dashboard_static.html": "427cfa378ab450a8d644facae064666c"}

    def test_it_applies_once_and_refuses_without_its_prerequisites(self):
        import hashlib
        bak = sorted((REPO / "scripts").glob("dashboard.py.bak_repairpath_*"))
        if not bak:
            self.skipTest("no pre-patch copy beside dashboard.py (the patcher's backup) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for rel in self.PRE:
                src = sorted((REPO / "scripts").glob(Path(rel).name + ".bak_repairpath_*"))[0]
                shutil.copy2(src, t / rel)
            (t / "scripts" / "repair_text.py").write_text("# stand-in\n")
            pat = [sys.executable, str(REPO / "scripts" / "patch_repair_path_2026_10_10.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("CHECK OK: 2 file(s)", r.stdout)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in self.PRE:
                later = sorted((REPO / "scripts").glob(Path(rel).name + ".bak_repairheal_*"))   # REPAIR_HEAL_2026_10_11
                want = later[0] if later else (REPO / rel)
                self.assertEqual((t / rel).read_bytes(), want.read_bytes(), rel)
                b = (t / rel).read_bytes()
                self.assertEqual(b.count(b"\r\n"), b.count(b"\n"), "CRLF kept")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertIn("Nothing to do", r.stdout)
            p = t / "scripts" / "dashboard_static.html"
            p.write_bytes(b"no marks\r\n")
            (t / "scripts" / "dashboard.py").write_bytes(sorted((REPO / "scripts").glob("dashboard.py.bak_repairpath_*"))[0].read_bytes())
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry", r.stdout)
            self.assertNotIn(b"REPAIR_PATH", (t / "scripts" / "dashboard.py").read_bytes(), "all or nothing")


if __name__ == "__main__":
    unittest.main()
