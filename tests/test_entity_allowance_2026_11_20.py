# -*- coding: ascii -*-
"""ENTITY_ALLOWANCE_2026_11_20: the scheduled entity extraction spends at most its allowance a day (usage_log, the UTC
day), a run at most its ceiling; past either it stops and asks with the count, about the cost and the one command; a
day's spend before today does not count; without the flags nothing changes; the maintenance runner passes $0.25 a day;
the patch replays once. Gemini is never called: the model's reading is stubbed."""
import datetime, importlib.util, io, os, re, sqlite3, sys, tempfile, types, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "extract_entities.py"
RUNNER = REPO / "scripts" / "maintenance_runner.ps1"
PAT = REPO / "scripts" / "patch_entity_allowance_2026_11_20.py"
MARK = "ENTITY_ALLOWANCE_2026_11_20"


def applied():
    return MARK in SCRIPT.read_text(encoding="utf-8")


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


@unittest.skipUnless(applied(), "ENTITY_ALLOWANCE is not applied here")
class TheAllowance(unittest.TestCase):
    COST = 0.001   # a verse, in the stub

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.td.name, "c.db")
        con = sqlite3.connect(self.db)
        con.executescript("""
            CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
            CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, iast TEXT, translation TEXT, text_type TEXT,
                                   ents TEXT);
            CREATE TABLE usage_log (id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, doc TEXT, engine TEXT, in_chars INTEGER,
                                    out_chars INTEGER, in_tokens REAL, out_tokens REAL, cost_usd REAL, duration_s REAL,
                                    passages INTEGER, ok INTEGER, token_source TEXT);
            INSERT INTO docs VALUES (1, 'MBh01');""")
        con.executemany("INSERT INTO passages (doc_id, iast, translation, text_type) VALUES (1, ?, ?, 'mula')",
                        [("v%d" % i, "verse %d" % i) for i in range(100)])
        con.commit(); con.close()
        self.saved = {k: sys.modules.get(k) for k in ("google", "google.generativeai", "usage_meter")}
        g = types.ModuleType("google"); gen = types.ModuleType("google.generativeai")
        gen.configure = lambda **k: None
        g.generativeai = gen
        um = types.ModuleType("usage_meter"); um.budget_ok = lambda con, next_cost=0.0: True
        sys.modules.update({"google": g, "google.generativeai": gen, "usage_meter": um})
        self.env = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-only-not-a-key"
        spec = importlib.util.spec_from_file_location("ee_test", str(SCRIPT))
        self.ee = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.ee)
        self.calls = []

        def stub(con, cur, genai, model, chunk, engine=None, doc=None, debug_raw=False):
            self.calls.append(len(chunk))
            now = iso(datetime.datetime.now(datetime.timezone.utc))
            for pid, _iast, _tr in chunk:
                con.execute("UPDATE passages SET ents = '[]' WHERE id = ?", (pid,))
            con.execute("INSERT INTO usage_log (ts, kind, doc, engine, cost_usd, passages) VALUES (?, 'entities', '', "
                        "'gemini:gemini-2.5-flash', ?, ?)", (now, self.COST * len(chunk), len(chunk)))
            con.commit()
            return len(chunk), 0, len(chunk)
        self.ee._extract_chunk = stub

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        if self.env is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self.env
        self.td.cleanup()

    def spend(self, when, usd):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO usage_log (ts, kind, doc, engine, cost_usd, passages) VALUES (?, 'entities', '', "
                    "'gemini:gemini-2.5-flash', ?, 1)", (iso(when), usd))
        con.commit(); con.close()

    def run_main(self, *extra):
        old, buf = sys.argv, io.StringIO()
        sys.argv = ["extract_entities.py", "--db", self.db, "--batch", "10", "--sleep", "0"] + list(extra)
        try:
            with redirect_stdout(buf):
                self.ee.main()
        finally:
            sys.argv = old
        return buf.getvalue()

    def test_stops_at_the_days_allowance_and_asks(self):
        out = self.run_main("--limit", "1500", "--per-day-usd", "0.05")
        self.assertEqual(sum(self.calls), 50, out)
        self.assertRegex(out, r"Stopping\. ASK \(allowance\): entity extraction waits: today's allowance is spent "
                              r"\(\$0\.05 of \$0\.05\); 50 verse\(s\) wait, about \$\d+\.\d\d; more: python "
                              r"scripts\\extract_entities\.py --db .+ --limit 50 --max-usd \d+\.\d\d")

    def test_spent_today_asks_before_reading(self):
        self.spend(datetime.datetime.now(datetime.timezone.utc), 0.30)
        out = self.run_main("--per-day-usd", "0.25")
        self.assertEqual(self.calls, [])
        self.assertIn("ASK (allowance): entity extraction waits: today's allowance is spent ($0.30 of $0.25); "
                      "100 verse(s) wait", out)
        self.assertNotIn("Extracting entities", out)

    def test_yesterday_does_not_count(self):
        self.spend(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1, hours=1), 5.0)
        out = self.run_main("--per-day-usd", "0.25")
        self.assertEqual(sum(self.calls), 100, out)
        self.assertNotIn("ASK", out)

    def test_the_runs_ceiling(self):
        out = self.run_main("--max-usd", "0.02")
        self.assertEqual(sum(self.calls), 20, out)
        self.assertIn("this run's ceiling is reached ($0.02 of $0.02); 80 verse(s) wait", out)

    def test_without_the_flags_as_before(self):
        out = self.run_main()
        self.assertEqual(sum(self.calls), 100, out)
        self.assertIn("Done. 100 verses processed this run", out)


class TheRunner(unittest.TestCase):
    def test_the_scheduled_run_has_its_allowance(self):
        t = RUNNER.read_text(encoding="ascii")
        if MARK not in t:
            self.skipTest("ENTITY_ALLOWANCE is not applied here")
        self.assertIn("scripts\\extract_entities.py --db data\\context.db --limit 1500 --per-day-usd 0.25", t)
        self.assertNotIn("--limit 1500 2>&1", t)


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def test_replays_once(self):
        spec = importlib.util.spec_from_file_location("pat_ea", str(PAT))
        files = None
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        files = mod.FILES
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for rel in files:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_entityallow_*"))
                if not bak:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(bak[0].read_bytes())
            old, buf = os.getcwd(), io.StringIO()
            try:
                os.chdir(str(t)); sys.argv = ["x"]
                with redirect_stdout(buf):
                    for name in ("pat_ea_a", "pat_ea_b"):
                        s2 = importlib.util.spec_from_file_location(name, str(PAT))
                        m2 = importlib.util.module_from_spec(s2); s2.loader.exec_module(m2); m2.main()
            finally:
                os.chdir(old)
            self.assertIn("Nothing to do", buf.getvalue())
            marks = lambda b: set(re.findall(rb"[A-Z][A-Z0-9_]*_20\d\d_\d\d_\d\d", b))
            for rel in files:
                now, got = (REPO / rel).read_bytes(), (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if marks(now) == marks(got):
                    self.assertEqual(got.replace(b"\r\n", b"\n"), now.replace(b"\r\n", b"\n"), rel)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if f.exists():
                b = f.read_bytes()
                self.assertTrue(all(x < 128 for x in b), f.name)
                self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
