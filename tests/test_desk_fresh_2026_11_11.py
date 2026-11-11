# -*- coding: ascii -*-
"""DESK_FRESH_2026_11_11: the desk says what is so now. One text charted again (text_path.py --doc X --write puts its
row into data/text_path.json with its own time; its e-text witness charted with it; a duplicate refused; without
--write nothing written); the desk dates a text by its own row and says what changed since (translation_desk.row_at,
changed_since); the "Chart this text again (free)" button (/api/repair step path_doc); the Claude credit's settings
read again from .env when it changes (claude_engine.dotenv_credit; the dashboard's _credit_env_fresh, for the desk, the
Usage tab and the jobs it starts); the patcher. Temp folders only; nothing is called, data/context.db never opened."""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import translation_desk as TD     # noqa: E402
import claude_engine as CE        # noqa: E402

MARK = "DESK_FRESH_2026_11_11"
APPLIED = MARK.encode() in (SCRIPTS / "dashboard.py").read_bytes()
KEYS = ("SA_CLAUDE_CREDIT_USD", "SA_CLAUDE_CREDIT_SINCE", "SA_CLAUDE_CREDIT_EXPIRES")


def run_path(t: Path, db: Path, *more):
    return subprocess.run([sys.executable, str(SCRIPTS / "text_path.py"), "--db", str(db), "--inbox", str(t / "inbox"),
                           "--raw", str(t / "raw"), "--vision-dir", str(t / "vision"), "--merged-dir", str(t / "merged"),
                           "--work", str(t / "work"), "--verdicts", str(t / "v.jsonl"), "--source-desk", str(t / "desk"),
                           "--out", str(t / "out" / "p.json")] + list(more),
                          capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))


@unittest.skipUnless(MARK.encode() in (SCRIPTS / "text_path.py").read_bytes(), "not applied here")
class OneTextChartedAgain(unittest.TestCase):
    def setUp(self):
        import test_path_2026_10_12 as P
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.db = t / "c.db"
        con, ids = P.make_db(self.db, {"Ts": ("tesseract", {pg: P.verses(2, pg, P.JUNK) for pg in (1, 2, 3)}),
                                       "Vs": ("gemini-vision", {1: P.verses(3)}),
                                       "Ts__w_gretil": ("etext", {1: P.verses(2, 1)})})
        con.close()
        for sub in ("inbox", "raw", "vision", "merged", "work", "desk"):
            (t / sub).mkdir()
        for pg in (1, 2, 3):
            (t / "inbox" / ("Ts_%04d.pdf" % pg)).write_bytes(b"%PDF-1.4\n")
            (t / "raw" / ("Ts_%04d.jsonl" % pg)).write_text(json.dumps({"text": P.verses(2, pg, P.JUNK)}) + "\n",
                                                             encoding="utf-8")
        (t / "v.jsonl").write_text(json.dumps({"doc": "Ts__w_gretil", "status": "witness", "of": "Ts",
                                               "at": "2026-10-12T09:01:00"}) + "\n", encoding="utf-8")
        r = run_path(t, self.db)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.out = t / "out" / "p.json"
        d = json.loads(self.out.read_text(encoding="utf-8"))
        for x in d["texts"]:   # the chart of a fortnight before: Ts said done, and the chart is old
            if x["doc"] == "Ts":
                x.update(path="done", why="the old chart", next=[], also=[])
        d["at"] = "2026-10-28T17:48:02"
        self.out.write_text(json.dumps(d), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_its_row_written_with_its_time_and_its_witness_note(self):
        before = json.loads(self.out.read_text(encoding="utf-8"))
        dbb = self.db.read_bytes()
        r = run_path(self.t, self.db, "--doc", "Ts", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.db.read_bytes(), dbb, "read-only")
        self.assertIn("VERDICT: Ts: repair", r.stdout)
        self.assertIn("the chart of the others is of 2026-10-28T17:48:02", r.stdout)
        d = json.loads(self.out.read_text(encoding="utf-8"))
        got = {x["doc"]: x for x in d["texts"]}
        self.assertEqual(got["Ts"]["path"], "repair")
        self.assertTrue(got["Ts"]["at"] > "2026-10-28T17:48:02", got["Ts"].get("at"))
        self.assertTrue(any("its e-text Ts__w_gretil is here" in x for x in got["Ts"]["also"]), got["Ts"]["also"])
        self.assertEqual(d["at"], "2026-10-28T17:48:02", "the chart's own time as it was")
        old = {x["doc"]: x for x in before["texts"]}
        for k in ("Vs", "Ts__w_gretil", "New") if "New" in old else ("Vs", "Ts__w_gretil"):
            self.assertEqual(got[k], old[k], k)
        self.assertEqual(set(got), set(old))
        self.assertEqual(d["totals"].get("repair", {}).get("texts"), 1)
        self.assertEqual(set(d["totals"]), {x["path"] for x in d["texts"] if not x.get("retired")})
        self.assertEqual(TD.load_path(self.out)["texts"]["Ts"]["path"], "repair")
        self.assertEqual(TD.row_at(TD.load_path(self.out)["texts"]["Ts"], "2026-10-28T17:48:02"), got["Ts"]["at"])

    def test_without_write_nothing_is_written(self):
        b = self.out.read_bytes()
        r = run_path(self.t, self.db, "--doc", "Ts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.out.read_bytes(), b)

    def test_a_duplicate_waits_for_the_whole_chart(self):
        d = json.loads(self.out.read_text(encoding="utf-8"))
        for x in d["texts"]:
            if x["doc"] == "Ts":
                x["path"] = "retire"
        self.out.write_text(json.dumps(d), encoding="utf-8")
        b = self.out.read_bytes()
        r = run_path(self.t, self.db, "--doc", "Ts", "--write")
        self.assertEqual(r.returncode, 1)
        self.assertIn("VERDICT: Ts's path is retire", r.stdout)
        self.assertEqual(self.out.read_bytes(), b)

    def test_merge_row_adds_keeps_and_reads(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("text_path_fresh", str(SCRIPTS / "text_path.py"))
        tp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tp)
        p = self.t / "m.json"
        self.assertEqual(tp.merge_row(p, None), {"at": "", "rows": {}})
        self.assertFalse(p.exists(), "read only")
        got = tp.merge_row(p, {"doc": "A", "path": "translate", "cost": 1.0, "at": "2026-11-11T09:00:00"})
        self.assertEqual(got["at"], "2026-11-11T09:00:00")
        tp.merge_row(p, {"doc": "B", "path": "repair", "cost": 2.0, "at": "2026-11-11T09:05:00"})
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual([x["doc"] for x in d["texts"]], ["B", "A"], "the chart's order: repair before translate")
        self.assertEqual(d["totals"]["repair"]["texts"], 1)
        self.assertEqual(d["at"], "2026-11-11T09:00:00")


class TheDesksRules(unittest.TestCase):
    def test_a_rows_own_time(self):
        self.assertEqual(TD.row_at({"at": "2026-11-11T09:00:00"}, "2026-10-28T17:48:02"), "2026-11-11T09:00:00")
        self.assertEqual(TD.row_at({"doc": "x"}, "2026-10-28T17:48:02"), "2026-10-28T17:48:02")
        self.assertEqual(TD.row_at(None, ""), "")
        prow = {"doc": "R", "path": "repair", "why": "Tesseract's text", "next": ["python scripts\\repair_text.py --doc R"],
                "at": "2026-11-11T09:00:00"}
        g = TD.guard(prow, None, TD.row_at(prow, "2026-10-01T10:00:00"),
                     time.mktime(time.strptime("2026-11-11T10:00:00", "%Y-%m-%dT%H:%M:%S")))
        self.assertIn("(the chart of 2026-11-11)", g["say"])

    def test_what_changed_since(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "ocr_consensus").mkdir()
            (d / "raw_merged").mkdir()
            at = "2026-10-28T17:48:02"
            t0 = time.mktime(time.strptime(at, "%Y-%m-%dT%H:%M:%S"))
            self.assertEqual(TD.changed_since("G", at, d), [])
            w = d / "raw_merged" / "G__w_gretil_0001.jsonl"
            w.write_text("{}", encoding="utf-8")
            os.utime(w, (t0 + 86400, t0 + 86400))
            old = d / "raw_merged" / "G_0001.jsonl"
            old.write_text("{}", encoding="utf-8")
            os.utime(old, (t0 - 86400, t0 - 86400))
            self.assertEqual(TD.changed_since("G", at, d), [], "a witness's pages are not the text's; older pages nothing")
            c = d / "ocr_consensus" / "G.json"
            c.write_text("{}", encoding="utf-8")
            os.utime(c, (t0 + 2 * 86400, t0 + 2 * 86400))
            os.utime(old, (t0 + 2 * 86400, t0 + 2 * 86400))
            (d / "source_verdicts.jsonl").write_text("\n".join(json.dumps(x) for x in (
                {"doc": "G", "status": "in_repair", "at": "2026-10-20T10:00:00"},
                {"doc": "H", "status": "withdrawn", "at": "2026-11-10T10:00:00"},
                {"doc": "G", "status": "translate_as_is", "at": "2026-11-10T10:00:00"})) + "\nnot json\n", encoding="utf-8")
            got = TD.changed_since("G", at, d)
            self.assertEqual([w for w, _ in got], ["the OCR consensus (vision) written", "its merged pages written",
                                                   "the register: translate_as_is"])
            self.assertEqual(got[2][1], "2026-11-10 10:00")
            self.assertEqual(TD.changed_since("G", "not a time", d), [])
            self.assertEqual(TD.changed_since("G", "2026-11-11T00:00:00", d)[:1], [], "nothing after a later chart")


class TheCreditsSettings(unittest.TestCase):
    def test_only_the_three_keys_are_read(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text("# SA_CLAUDE_CREDIT_USD=1\nSA_CLAUDE_CREDIT_USD=200\nexport SA_CLAUDE_CREDIT_SINCE=\"2026-11-09\"\n"
                         "SA_CLAUDE_CREDIT_EXPIRES=2026-12-11  # a month\nOTHER_SETTING=not-read\nSA_CLAUDE_CREDIT_X=1\n",
                         encoding="utf-8")
            self.assertEqual(CE.dotenv_credit(p), {"SA_CLAUDE_CREDIT_USD": "200", "SA_CLAUDE_CREDIT_SINCE": "2026-11-09",
                                                   "SA_CLAUDE_CREDIT_EXPIRES": "2026-12-11"})
            self.assertEqual(CE.dotenv_credit(Path(td) / "none.env"), {})

    def test_settings_still_read_the_environment_only(self):
        saved = {k: os.environ.pop(k, None) for k in KEYS}
        try:
            s = CE.settings()
            self.assertEqual((s["cap"], s["expires"]), (CE.CREDIT_USD, CE.CREDIT_EXPIRES))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


@unittest.skipUnless(APPLIED, "DESK_FRESH_2026_11_11 is not applied here")
class TheDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_translation_desk_2026_10_17 as TDT
        cls.TDT = TDT
        TDT.TheDesk.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        self.TDT.TheDesk.setUp(self)
        rows = self.TDT.chart_rows()
        for r in rows:
            if r["doc"] == "RepairText":
                r["at"] = "2026-11-11T09:00:00"
        self.chart.write_text(json.dumps({"mark": "PATH_2026_10_12", "at": "2026-10-01T10:00:00", "texts": rows}),
                              encoding="utf-8")
        self.d._DESK_CACHE.update(res=None)

    def tearDown(self):
        self.TDT.TheDesk.tearDown(self)

    def launched(self, url, body):
        return self.TDT.TheDesk.launched(self, url, body)

    def test_a_text_is_dated_by_its_own_row(self):
        h = self.c.get("/desk/RepairText").get_data(as_text=True)
        self.assertIn("(charted 2026-11-11 09:00)", h)
        self.assertIn("(the chart of 2026-11-11", h)
        self.assertIn("deskChartOne('RepairText', this)", h)
        self.assertIn("Chart this text again (free)", h)
        self.assertIn("Nothing has changed this text since its path was charted.", h)
        h = self.c.get("/desk/ReadyText").get_data(as_text=True)
        self.assertIn("(charted 2026-10-01 10:00)", h)
        s = self.d._desk_state(fresh=True)
        self.assertEqual({r["doc"]: r["at"] for r in s["rows"]}["RepairText"], "2026-11-11T09:00:00")
        if self.node():
            p = self.td / "desk1.js"
            p.write_text(re.findall(r"<script>(.*?)</script>", h, re.S)[0], encoding="utf-8")
            res = subprocess.run([self.node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_what_changed_since_its_chart(self):
        data = Path(self.d.DESK_DB).parent
        (data / "ocr_consensus").mkdir(exist_ok=True)
        (data / "ocr_consensus" / "ReadyText.json").write_text("{}", encoding="utf-8")
        h = self.c.get("/desk/ReadyText").get_data(as_text=True)
        self.assertIn("Changed since its path was charted (2026-10-01 10:00): the OCR consensus (vision) written", h)
        self.assertIn('class="warn" id="dkfresh"', h)

    def test_the_button_charts_that_text(self):
        r, got = self.launched("/api/repair", {"step": "path_doc", "doc": "RepairText"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("repair", "RepairText", "path_doc"))
        self.assertTrue(argv[-5].endswith("text_path.py"), argv)
        self.assertEqual(argv[-4:], ["--doc", "RepairText", "--write", "--from-dashboard"])
        r, got = self.launched("/api/repair", {"step": "path_doc", "doc": "../x"})
        self.assertEqual((r.status_code, got), (400, []))
        self.assertIn("path_doc", self.c.get("/api/repair").get_json()["steps"])

    def test_the_credit_as_env_has_it_now(self):
        d = self.d
        saved_env = {k: os.environ.get(k) for k in KEYS}
        saved = (d.ROOT, set(d._CREDIT_SHELL), dict(d._CREDIT_ENV_SEEN))
        try:
            root = self.td / "root"
            root.mkdir()
            env = root / ".env"
            env.write_text("SA_CLAUDE_CREDIT_USD=200\nSA_CLAUDE_CREDIT_SINCE=2026-11-09\nSA_CLAUDE_CREDIT_EXPIRES=2026-12-11\n",
                           encoding="utf-8")
            d.ROOT = root
            d._CREDIT_SHELL.clear()
            d._CREDIT_ENV_SEEN["key"] = None
            for k in KEYS:
                os.environ.pop(k, None)
            d._credit_env_fresh()
            self.assertEqual([os.environ.get(k) for k in KEYS], ["200", "2026-11-09", "2026-12-11"])
            self.assertEqual(CE.settings()["expires"], "2026-12-11")
            env.write_text("SA_CLAUDE_CREDIT_USD=250\nSA_CLAUDE_CREDIT_SINCE=2026-11-09\n", encoding="utf-8")
            os.utime(env, (time.time() + 5, time.time() + 5))
            ch = d._child_env()
            self.assertEqual((ch.get("SA_CLAUDE_CREDIT_USD"), ch.get("SA_CLAUDE_CREDIT_EXPIRES")), ("250", None),
                             "a job started now bills the credit as .env has it")
            d._CREDIT_SHELL.add("SA_CLAUDE_CREDIT_USD")
            os.environ["SA_CLAUDE_CREDIT_USD"] = "5"
            env.write_text("SA_CLAUDE_CREDIT_USD=300\n", encoding="utf-8")
            os.utime(env, (time.time() + 9, time.time() + 9))
            d._credit_env_fresh()
            self.assertEqual(os.environ.get("SA_CLAUDE_CREDIT_USD"), "5", "the shell's own setting wins, as at start")
            d.ROOT = self.td / "nowhere"
            d._credit_env_fresh()   # no .env: nothing changes, nothing raised
            self.assertEqual(os.environ.get("SA_CLAUDE_CREDIT_USD"), "5")
        finally:
            d.ROOT = saved[0]
            d._CREDIT_SHELL.clear(); d._CREDIT_SHELL.update(saved[1])
            d._CREDIT_ENV_SEEN.clear(); d._CREDIT_ENV_SEEN.update(saved[2])
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/dashboard.py", "scripts/text_path.py", "scripts/translation_desk.py", "scripts/claude_engine.py",
             "tests/test_claude_engine_2026_10_15.py", "tests/test_tier_r_2026_10_17.py", "tests/test_redeem_2026_10_14.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_deskfresh_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the files")

        def expected(f):
            mine = baks[f][0].stat().st_mtime
            later = sorted((p for p in (REPO / f).parent.glob(Path(f).name + ".bak_*")
                            if ".bak_deskfresh_" not in p.name and p.stat().st_mtime > mine), key=lambda p: p.stat().st_mtime)
            return later[0] if later else REPO / f
        pat = [sys.executable, str(SCRIPTS / "patch_desk_fresh_2026_11_11.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for f in self.FILES:
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), expected(f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "text_path.py"
            p.write_bytes(p.read_bytes().replace(b"    res = chart(a)\n", b"    res = chart(a)  \n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("text_path.py: anchor", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK.encode(), (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_desk_fresh_2026_11_11.py", SCRIPTS / "text_path.py", SCRIPTS / "translation_desk.py",
                  SCRIPTS / "claude_engine.py", Path(__file__)):
            if not p.exists():
                continue
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK.encode(), b, p.name)


if __name__ == "__main__":
    unittest.main()
