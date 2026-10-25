# -*- coding: ascii -*-
"""AUTO_REPAIR_2026_10_25: the scans' repair kept going by itself (scripts/repair_auto.py), the maintenance task's
steps d (vamsa_check.py --scheduled) and e (repair_auto.py --round), and health_watch.py's repair check. A made-up
data folder and a stand-in repair_text.py in a temp folder: no model, no network (the dashboard's address is a closed
port), never data/context.db."""
import datetime, importlib.util, json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
AUTO = S / "repair_auto.py"
RUNNER = S / "maintenance_runner.ps1"
HEALTH = S / "health_watch.py"
PAT = S / "patch_auto_repair_2026_10_25.py"
MARK = "AUTO_REPAIR_2026_10_25"

FAKE = r'''
import json, os, sqlite3, sys
a = sys.argv[1:]
calls = os.environ["FAKE_CALLS"]
with open(calls, "a", encoding="utf-8") as f:
    f.write(json.dumps(a) + "\n")
if "--judge-all" in a:
    print("VERDICT: judged 3 text(s)"); print("NEXT: "); sys.exit(0)
doc = a[a.index("--doc") + 1]
if "--repair" in a:
    con = sqlite3.connect(os.environ["FAKE_DB"])
    con.execute("UPDATE budget_state SET spent_usd = spent_usd + 0.03 WHERE id = 1"); con.commit(); con.close()
    print("VERDICT: vision read 40 pages of %s" % doc); print("NEXT: python scripts\\repair_text.py --doc %s" % doc)
    sys.exit(0)
if "--use-repaired" in a:
    print("VERDICT: the repaired text is in the database"); print("NEXT: translate it"); sys.exit(0)
nxt = json.load(open(os.environ["FAKE_NEXT"], encoding="utf-8")).get(doc, "")
print("VERDICT: assessed %s" % doc); print("NEXT: " + nxt)
'''


def judged(d: Path, doc: str, level: str, nxt: str, pdfs=100, vp=40, english=0):
    (d / "source_judged").mkdir(parents=True, exist_ok=True)
    (d / "source_judged" / (doc + ".json")).write_text(json.dumps({
        "doc": doc, "level": level, "next": nxt, "pdfs": pdfs, "vision_pages": vp, "english": english,
        "passages": 200, "at": "2026-10-25T01:00:00"}), encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        self.data = t / "data"
        self.fake = t / "fake"
        self.fake.mkdir()
        (self.fake / "repair_text.py").write_text(FAKE, encoding="utf-8")
        self.data.mkdir()
        self.db = self.data / "context.db"
        con = sqlite3.connect(str(self.db))
        con.execute("CREATE TABLE budget_state (id INTEGER PRIMARY KEY, budget_usd REAL, spent_usd REAL, paused INTEGER)")
        con.execute("INSERT INTO budget_state VALUES (1, 115.0, 100.0, 0)")
        con.commit(); con.close()
        q = "python scripts\\repair_text.py --doc %s"
        judged(self.data, "A", "material", q % "A" + " --repair --max-usd 1.00", vp=40)
        judged(self.data, "B", "material", q % "B" + " --use-repaired --replace 12", vp=100, english=12)
        judged(self.data, "C", "material", q % "C" + " --use-repaired", vp=100)
        judged(self.data, "Daivat-Sanhita", "material", q % "Daivat-Sanhita" + " --repair --max-usd 5.30", vp=0)
        judged(self.data, "E", "material", q % "E" + " --repair", vp=0)
        (self.data / "source_verdicts.jsonl").write_text(json.dumps({"doc": "E", "status": "withdrawn"}) + "\n",
                                                         encoding="utf-8")
        self.next = t / "next.json"
        self.next.write_text(json.dumps({"A": q % "A" + " --repair --max-usd 1.00   (it stops before spending more)",
                                         "B": q % "B" + " --use-repaired --replace 12",
                                         "C": q % "C" + " --use-repaired"}), encoding="utf-8")
        self.calls = t / "calls.jsonl"
        self.env = dict(os.environ, SA_REPAIR_SCRIPTS=str(self.fake), SA_DASHBOARD_URL="http://127.0.0.1:9",
                        FAKE_CALLS=str(self.calls), FAKE_DB=str(self.db), FAKE_NEXT=str(self.next),
                        PYTHONDONTWRITEBYTECODE="1")

    def tearDown(self):
        self.td.cleanup()

    def auto(self, *args):
        r = subprocess.run([sys.executable, str(AUTO), "--data", str(self.data), "--backup-dir", str(self.t)] +
                           list(args), capture_output=True, text=True, env=self.env, timeout=120)
        return r.returncode, r.stdout + r.stderr

    def state(self):
        return json.loads((self.data / "auto_repair_state.json").read_text(encoding="utf-8"))

    def calls_made(self):
        if not self.calls.exists():
            return []
        return [json.loads(x) for x in self.calls.read_text(encoding="utf-8").splitlines() if x.strip()]


class TestPlan(Base):
    def test_queue(self):
        rc, out = self.auto()
        self.assertEqual(rc, 0, out)
        self.assertIn("C ", out)
        self.assertIn("A ", out)
        self.assertNotIn("Daivat", out)                       # its rights: never
        self.assertNotIn(" E ", out)                          # withdrawn
        self.assertLess(out.index(" C "), out.index(" A "))   # one step from done comes first
        self.assertLess(out.index(" A "), out.index(" B "))   # a decision last
        self.assertFalse((self.data / "auto_repair_state.json").exists())
        self.assertEqual(self.calls_made(), [])


class TestRounds(Base):
    def test_first_round_judges_then_vision(self):
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.calls_made(), [["--judge-all"]])
        self.assertEqual(self.state()["did"]["step"], "judge")
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        c = self.calls_made()
        # C is ready to go in, but the dashboard does not answer: no swap; A's vision runs, within the round's limit
        self.assertNotIn("--use-repaired", sum(c, []))
        rep = [x for x in c if "--repair" in x]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0][:2], ["--doc", "A"])
        self.assertEqual(rep[0][rep[0].index("--max-usd") + 1], "0.10")
        st = self.state()
        self.assertEqual((st["did"]["step"], st["did"]["doc"]), ("vision", "A"))
        self.assertAlmostEqual(st["did"]["spent"], 0.03, places=4)
        log = [json.loads(x) for x in (self.data / "auto_repair_log.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["step"] for r in log], ["judge", "vision"])

    def test_allowance_off_and_decisions(self):
        self.auto("--round")                                   # the day's judgement
        rc, out = self.auto("--allow", "0")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((self.data / "auto_repair.json").read_text(encoding="utf-8"))["usd_per_day"], 0)
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        self.assertFalse(any("--repair" in x for x in self.calls_made()))
        st = self.state()
        self.assertEqual(st["status"], "off")
        self.assertTrue(any(a["kind"] == "decision" and a["doc"] == "B" for a in st["asks"]))

    def test_cap_reserve_blocks_and_health_warns(self):
        self.auto("--round")
        con = sqlite3.connect(str(self.db))
        con.execute("UPDATE budget_state SET spent_usd = 114.5 WHERE id = 1"); con.commit(); con.close()
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        self.assertFalse(any("--repair" in x for x in self.calls_made()))
        st = self.state()
        self.assertEqual(st["status"], "blocked")
        self.assertTrue(any(a["kind"] == "cap" for a in st["asks"]))
        h = load_health()
        if not hasattr(h, "check_repair"):
            self.skipTest("patch_auto_repair_2026_10_25.py not applied yet")
        c = h.check_repair(self.data / "auto_repair_state.json", datetime.datetime.now())
        self.assertEqual(c["state"], "warn")
        self.assertIn("cap", c["say"])

    def test_dry_run_and_lock(self):
        self.auto("--round")
        before = (self.data / "auto_repair_log.jsonl").read_text(encoding="utf-8")
        rc, out = self.auto("--round", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertIn("would run", out)
        self.assertEqual((self.data / "auto_repair_log.jsonl").read_text(encoding="utf-8"), before)
        self.assertFalse(any("--repair" in x for x in self.calls_made()))
        (self.data / "auto_repair.lock").write_text(json.dumps({"pid": 1, "at": datetime.datetime.now().isoformat()}),
                                                     encoding="utf-8")
        rc, out = self.auto("--round")
        self.assertIn("stands aside", out)


def load_health():
    spec = importlib.util.spec_from_file_location("health_watch_t", str(HEALTH))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestWiring(unittest.TestCase):
    def test_ascii_and_marked(self):
        for p in (AUTO, PAT):
            raw = p.read_bytes()
            self.assertTrue(all(b < 128 for b in raw), p.name)
            self.assertIn(MARK.encode(), raw, p.name)

    def test_gitignore(self):
        g = (REPO / ".gitignore").read_text(encoding="utf-8")
        if MARK not in g:
            self.skipTest("patch_auto_repair_2026_10_25.py not applied yet")
        for f in ("data/auto_repair.json", "data/auto_repair_log.jsonl", "data/auto_repair_state.json",
                  "data/auto_repair.lock"):
            self.assertIn(f, g)

    def test_runner_and_health(self):
        r = RUNNER.read_text(encoding="utf-8")
        if MARK not in r:
            self.skipTest("patch_auto_repair_2026_10_25.py not applied yet")
        self.assertIn("scripts\\repair_auto.py --round", r)
        self.assertIn("scripts\\vamsa_check.py --scheduled", r)
        self.assertLess(r.index("STEP e repair"), r.index("DONE maintenance"))
        h = load_health()
        now = datetime.datetime.now()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            self.assertIsNone(h.check_repair(p, now))
            p.write_text(json.dumps({"at": now.isoformat(timespec="seconds"), "status": "working", "allowance": 0.25,
                                     "did": {"step": "vision", "doc": "A"}}), encoding="utf-8")
            self.assertEqual(h.check_repair(p, now)["state"], "ok")
            old = (now - datetime.timedelta(hours=40)).isoformat(timespec="seconds")
            p.write_text(json.dumps({"at": old, "status": "idle", "allowance": 0.25}), encoding="utf-8")
            self.assertEqual(h.check_repair(p, now)["state"], "warn")

    def test_patch_replays(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for f in ("maintenance_runner.ps1", "health_watch.py"):
                bak = sorted(S.glob(f + ".bak_autorepair_*"))
                (t / "scripts" / f).write_bytes((bak[0] if bak else S / f).read_bytes())
            bak = sorted(REPO.glob(".gitignore.bak_autorepair_*"))
            (t / ".gitignore").write_bytes((bak[0] if bak else REPO / ".gitignore").read_bytes())
            for f in ("repair_auto.py", "vamsa_check.py"):
                (t / "scripts" / f).write_bytes((S / f).read_bytes())
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=str(t), capture_output=True, text=True)
            if "CHECK OK" not in r.stdout:
                self.skipTest("only patched copies to replay against: " + r.stdout[-200:])
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r2 = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r2.stdout)


if __name__ == "__main__":
    unittest.main()
