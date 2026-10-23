# -*- coding: ascii -*-
"""HEALTH_2026_10_23: scripts/health_watch.py reads the desk's health from what its tasks leave (the maintenance log,
the mirror's log, the daily backup's log, the disk, the cap, the links): ok, warn or fail, each with a short line;
read-only. corner_worker.py's heartbeat carries it only when its own round sets it, and cuts it first when the
heartbeat is too long. docs/cloud/C19 reads it on the site and mails the super admin, never raising. Made-up logs and
a made-up database in a temp folder; never data/context.db, never the network."""
import datetime, importlib.util, json, sqlite3, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "health_watch.py"
WORKER = REPO / "scripts" / "corner_worker.py"
C19 = REPO / "docs" / "cloud" / "C19_health_mail_2026-10-23.sql"
PAT = REPO / "scripts" / "patch_health_2026_10_23.py"
MARK = "HEALTH_2026_10_23"
NOW = datetime.datetime(2026, 10, 23, 18, 30, 0)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def stamp(dt: datetime.datetime, msg: str) -> str:
    return "[%s] %s\n" % (dt.strftime("%Y-%m-%d %H:%M:%S"), msg)


class TheHealth(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data").mkdir()
        self.bk = t / "bk"
        self.bk.mkdir()
        self.hw = load(TOOL, "health_watch_t")
        self.hw.DISK_WARN_GB, self.hw.DISK_FAIL_GB = 0, 0   # the test machine's disk is not the desk's
        h = datetime.timedelta(hours=1)
        (self.bk / "maintenance_log.txt").write_text(
            stamp(NOW - 2 * h, "TICK - maintenance runner started") + "some output\n" +
            stamp(NOW - 2 * h, "DONE maintenance - total 71s") + stamp(NOW - h, "TICK - maintenance runner started") +
            stamp(NOW - h, "SKIP: dashboard busy (1 job(s) running/queued)"), encoding="utf-8")
        (self.bk / "backup_log.txt").write_text(stamp(NOW - 14 * h, "OK     wrote D:\\backups\\context_20261023.db"),
                                                encoding="utf-8")
        (t / "data" / "corpus_sync_log.jsonl").write_text(json.dumps(
            {"ts": (NOW - 3 * h).isoformat(), "stopped": "done", "verified": {"groups_equal": 386, "groups_different": 0}})
            + "\n", encoding="utf-8")
        con = sqlite3.connect(str(t / "data" / "context.db"))
        con.executescript("""
        CREATE TABLE budget_state (id INTEGER PRIMARY KEY, budget_usd REAL, spent_usd REAL, paused INTEGER);
        INSERT INTO budget_state VALUES (1, 95.0, 89.5, 0);
        CREATE TABLE entity_mentions (id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER);
        CREATE TABLE entity_link_runs (id INTEGER PRIMARY KEY, at TEXT, mentions INTEGER);
        """)
        con.execute("INSERT INTO entity_link_runs (at, mentions) VALUES (?, 0)", ((NOW - 2 * h).isoformat(),))
        con.commit()
        con.close()

    def tearDown(self):
        self.td.cleanup()

    def health(self):
        return self.hw.health(self.t, str(self.bk), now=NOW)

    def test_all_well(self):
        h = self.health()
        self.assertEqual(h["status"], "ok", h)
        self.assertEqual(set(h["checks"]), {"maintenance", "mirror", "backup", "disk", "spend", "links"})
        self.assertIn("386 groups equal", h["checks"]["mirror"]["say"])
        self.assertEqual(h["problems"], [])

    def test_each_problem(self):
        h = datetime.timedelta(hours=1)
        with open(self.bk / "maintenance_log.txt", "a", encoding="utf-8") as f:
            f.write(stamp(NOW - 0.5 * h, "FAIL after 12s: the database is locked"))
        (self.t / "data" / "corpus_sync_log.jsonl").write_text(json.dumps(
            {"ts": (NOW - h).isoformat(), "stopped": "error", "verified": {"groups_different": 2}}) + "\n", encoding="utf-8")
        (self.bk / "backup_log.txt").write_text(stamp(NOW - 30 * h, "OK     wrote x"), encoding="utf-8")
        con = sqlite3.connect(str(self.t / "data" / "context.db"))
        con.execute("UPDATE budget_state SET spent_usd = 94.0")
        con.commit()
        con.close()
        r = self.health()
        self.assertEqual(r["status"], "fail")
        st = {k: v["state"] for k, v in r["checks"].items()}
        self.assertEqual((st["maintenance"], st["mirror"], st["backup"], st["spend"]), ("fail", "fail", "warn", "warn"))
        self.assertIn("maintenance: failed at", " ".join(r["problems"]))
        self.assertIn("2 groups different", " ".join(r["problems"]))
        c = self.hw.compact(r)
        self.assertEqual(set(c), {"status", "at", "problems"})
        self.assertLessEqual(len(json.dumps(c)), 1000)

    def test_a_task_that_stopped_firing(self):
        (self.bk / "maintenance_log.txt").write_text(stamp(NOW - datetime.timedelta(hours=9), "TICK - started") +
                                                    stamp(NOW - datetime.timedelta(hours=9), "DONE maintenance"),
                                                    encoding="utf-8")
        r = self.health()
        self.assertEqual(r["checks"]["maintenance"]["state"], "fail")
        self.assertIn("has not fired since", r["checks"]["maintenance"]["say"])

    def test_read_only_and_the_cli(self):
        db = self.t / "data" / "context.db"
        before = db.read_bytes()
        rc = self.hw.main(["--root", str(self.t), "--backup-dir", str(self.bk), "--log"])
        self.assertIn(rc, (0, 1))
        self.assertEqual(db.read_bytes(), before, "the database is only read")
        self.assertTrue((self.bk / "health_log.txt").read_text(encoding="utf-8").strip())


@unittest.skipUnless(WORKER.exists() and MARK.encode() in WORKER.read_bytes(), "HEALTH_2026_10_23 is not applied here")
class TheHeartbeat(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REPO / "scripts"))
        self.cw = load(WORKER, "corner_worker_t")

    def test_only_when_set_and_cut_first(self):
        cw = self.cw
        self.assertNotIn("health", cw.heartbeat_info(None), "a round without it is as before")
        self.assertIsNone(cw._health_now(), "only main() sets it")
        h = {"status": "warn", "at": "2026-10-23T18:30:00", "problems": ["backup: the last daily copy " + "x" * 300] * 6}
        info = cw.heartbeat_info(None, None, h)
        self.assertEqual(info["health"], h)
        with mock.patch.object(cw, "INFO_MAX_CHARS", 700):
            small = cw.heartbeat_info(None, None, h)
            self.assertEqual(small["health"]["status"], "warn")
            self.assertLessEqual(len(small["health"]["problems"]), 2)
            self.assertLessEqual(cw.info_chars(small), 700)
        with mock.patch.object(cw, "INFO_MAX_CHARS", 200):
            self.assertEqual(cw.heartbeat_info(None, None, h)["health"], {"status": "warn"})
        with mock.patch.object(cw, "HEALTH", lambda: 1 / 0):
            self.assertEqual(cw._health_now()["status"], "warn", "a failing check never fails the round")


class TheSiteSide(unittest.TestCase):
    def test_c19(self):
        if not C19.exists():
            self.skipTest("C19 is not here")
        s = C19.read_text(encoding="ascii")
        self.assertIn("HEALTH_MAIL_C19_2026_10_23", s)
        self.assertIn("AFTER UPDATE OF info ON corner.worker", s)
        self.assertIn("EXCEPTION WHEN OTHERS THEN\n    RAISE WARNING", s, "it never raises: the heartbeat goes through")
        self.assertIn("coalesce(corner._setting('mail_enabled'), 'false') = 'true'", s, "only with the Corner's mail on")
        self.assertIn("ur.role = 'super_admin'::public.app_role", s, "the super admin only")
        self.assertIn("interval '12 hours'", s)
        self.assertIn("Rollback", s)
        self.assertEqual(s.count("BEGIN;"), 2, "one transaction (and the rollback's)")

    def test_ascii_and_marks(self):
        for f in (TOOL, PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
