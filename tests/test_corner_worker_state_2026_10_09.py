# -*- coding: ascii -*-
"""CORNER_STATE_C10A_2026_10_09: scripts/corner_worker.py 1.1 (where the desk is with a request, and
what it says of the mirror). The small context.db, the fake site queue and the fake scripts are those
of tests/test_corner_worker_2026_10_09.py; a fake clock stands in for the 5-second rule. The log lines
are written by corpus_sync.py's and corpus_media.py's own log_run, into a temporary folder. The last
class runs against PostgreSQL with C9 and C10a (CORPUS_TEST_DSN, a throwaway database).
  python -m unittest tests.test_corner_worker_state_2026_10_09 -v
"""
import json, os, shutil, sqlite3, sys, tempfile, textwrap, time, unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import corner_worker as cw                    # noqa: E402
import corpus_media as cm                     # noqa: E402
import corpus_sync as cs                      # noqa: E402
import test_corner_worker_2026_10_09 as base  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")
DOC = base.DOC


def sync_summary(stopped="done", error=None, verified=None):
    """A corpus_sync.py Run.execute() summary, as its main() logs it."""
    return {"run_id": "r1", "sink": "edge", "apply": True, "stopped": stopped, "error": error, "seconds": 41.2,
            "bytes": 123456, "tables": {"docs": {"groups_changed": 0, "upsert": 0, "changed": 0, "retire": 0, "held": 0,
                                                 "skipped": 0, "bytes": 0}},
            "held": [], "verified": verified, "client": cs.CLIENT}


def media_summary(stopped="done", needed=10, on_drive=8, uploaded=2, skipped=0, pictures=5):
    """A corpus_media.py Run.execute() summary."""
    return {"apply": True, "sink": "edge", "stopped": stopped, "error": None,
            "here": {"pictures": pictures, "approved": 3, "novels": 1, "novel_pictures": 2, "briefs": 0, "stale_pages": 0},
            "files": {"needed": needed, "on_drive": on_drive, "to_upload": needed - on_drive, "uploaded": uploaded,
                      "skipped": skipped, "bytes": 99},
            "media": {"upsert": 1, "changed": 1, "retire": 0, "retired": 0},
            "novels": {"upsert": 0, "changed": 0, "retire": 0, "retired": 0},
            "held": [], "notes": [], "bytes": 99, "seconds": 3.0, "drive_folder": "f"}


class Clock:
    def __init__(self):
        self.t, self.slept = 1000.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 3))
        self.t += s


class ProgressDesk(base.FakeDesk):
    def progress(self, rid):
        """[(step, of, note)] of the progress reports for that request, in order."""
        out = []
        for r in self.reports:
            if r["id"] == rid and r["status"] == "running" and r["result"] is not None:
                p = r["result"]["progress"]
                self_check = (set(r["result"]) == {"progress"} and set(p) == {"step", "of", "note"}
                              and r["message"] == p["note"] and r["cost"] is None and r["log"] is None)
                assert self_check, r
                out.append((p["step"], p["of"], p["note"]))
        return out


class TimedScripts(base.FakeScripts):
    """The fake scripts; each takes `took` seconds of the fake clock. novel.py draw prints one line per page
    it draws, as novel.py draw_pages does, through on_line when it is given."""

    def __init__(self, db, clock, took=10.0, page_gap=20.0):
        super().__init__(db)
        self.clock, self.took, self.page_gap = clock, took, page_gap
        self.streamed, self.pages = [], []

    def __call__(self, args, timeout, on_line=None):
        self.clock.t += self.took
        if args[0] == "scripts/novel.py" and args[3] == "draw":
            self.calls.append(list(args))
            self.streamed.append(on_line is not None)
            lines = ["draw novel #1: %d picture(s) with gemini at 1K, about $0.18" % len(self.pages)]
            for n in self.pages:
                self.clock.t += self.page_gap
                lines.append("  page %d: data/images/%s/novel_1/page_%02d_v1.png (%.1f s)" % (n, DOC, n, self.page_gap))
                if on_line:
                    on_line(lines[-1])
            lines.append("%d picture(s) made." % len(self.pages))
            return 0, "\n".join(lines)
        return super().__call__(args, timeout)


class Steps(base.Base):
    def setUp(self):
        super().setUp()
        self.clock = Clock()
        for name, fn in (("clock", self.clock.now), ("sleep", self.clock.sleep)):
            p = mock.patch.object(cw.Progress, name, staticmethod(fn))
            p.start()
            self.addCleanup(p.stop)
        self.scripts = TimedScripts(self.db, self.clock)
        self.said = []
        self.worker = cw.Worker(self.db, runner=self.scripts, ledger=self.tmp / "made.jsonl", say=self.said.append)

    def run_desk(self, desk, limit=10):
        return cw.run_once(desk, self.worker, limit, progress=True,
                           logs=(self.tmp / "corpus_sync_log.jsonl", self.tmp / "corpus_media_log.jsonl"))

    def do(self, *reqs, limit=10, desk_class=ProgressDesk):
        desk = desk_class([dict({"est_usd": 0.01, "attempts": 1}, **r) for r in reqs])
        return desk, self.run_desk(desk, limit)

    def plan_novel(self, drawn=(1, 2, 3, 4, 5, 6), stale=(7,), pages=8):
        imgs = {str(n): {"path": "p%d" % n, "status": "draft"} for n in drawn}
        imgs.update({str(n): {"path": "s%d" % n, "status": "stale"} for n in stale})
        plan = {"title": "T", "cast": [], "pages": [{"n": n, "scene": "s", "caption": "c"} for n in range(1, pages + 1)]}
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_novels SET plan=?, page_images=? WHERE id=1", (json.dumps(plan), json.dumps(imgs)))
        con.commit()
        con.close()

    # ---- the steps of a request

    def test_story_range_tells_its_three_steps(self):
        desk, s = self.do({"id": 7, "kind": "story_range", "doc_code": DOC,
                           "params": {"from": "25.2", "to": "25.9", "title": "Vitasta flows"}})
        self.assertEqual(desk.final(7)["status"], "done", desk.final(7))
        self.assertEqual(desk.progress(7), [(1, 3, "Passages 25.2 to 25.9 chosen"), (2, 3, "Writing the story"),
                                            (3, 3, "Sending it to the site")])
        self.assertEqual([r["status"] for r in desk.reports], ["running"] * 4 + ["done"])
        self.assertEqual(desk.reports[0]["result"], None)                      # the first 'running' report, as in 1.0
        self.assertEqual(self.clock.slept, [5.0])                              # step 2 waited out the 5 seconds
        self.assertEqual(desk.final(7)["result"]["story_id"], self.q("SELECT max(id) FROM doc_stories")[0][0])

    def test_picture_passage_tells_its_four_steps(self):
        desk, s = self.do({"id": 9, "kind": "picture_passage", "doc_code": DOC, "params": {
            "at": "25.3", "title": "The river", "brief": "Show the river goddess flowing to the sea"}})
        self.assertEqual(desk.final(9)["status"], "done", desk.final(9))
        self.assertEqual(desk.progress(9), [(1, 4, "The idea is stored"), (2, 4, "The idea is approved"),
                                            (3, 4, "Drawing the picture"), (4, 4, "Sending it to Drive")])

    def test_quick_steps_are_held_but_the_first_and_the_last_go(self):
        self.scripts.took, self.scripts.page_gap = 0.0, 0.0
        self.plan_novel(drawn=(1, 2, 3, 4, 5), stale=())                    # pages 6, 7, 8 to draw
        self.scripts.pages = [6, 7, 8]
        desk, s = self.do({"id": 5, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1}})
        self.assertEqual(desk.final(5)["status"], "done", desk.final(5))
        self.assertEqual(desk.progress(5), [(1, 5, "3 pages to draw"), (2, 5, "Drawing page 1 of 3"),
                                            (5, 5, "Sending it to Drive")])   # pages 2 and 3 came within 5 s
        self.assertEqual(self.clock.slept, [5.0])
        desk, s = self.do({"id": 6, "kind": "picture_redraw", "doc_code": DOC, "params": {"image_id": 3}})
        self.assertEqual(desk.progress(6), [(1, 2, "Drawing picture #3 again"), (2, 2, "Sending it to Drive")])

    def test_the_other_kinds(self):
        desk, s = self.do({"id": 1, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}},
                          {"id": 2, "kind": "story_mine", "doc_code": DOC, "params": {"max": 2}},
                          {"id": 3, "kind": "story_illustrate", "doc_code": DOC, "params": {"story_id": 34}},
                          {"id": 4, "kind": "novel_plan", "doc_code": DOC, "params": {"story_id": 34, "pages": 10}},
                          {"id": 5, "kind": "novel_cast", "doc_code": DOC, "params": {"novel_id": 1}},
                          {"id": 6, "kind": "story_approve", "doc_code": DOC, "params": {"story_id": 35}},
                          {"id": 7, "kind": "novel_page_approve", "doc_code": DOC, "params": {"novel_id": 1, "page": 2}})
        self.assertEqual([desk.final(i)["status"] for i in range(1, 8)], ["done"] * 7)
        self.assertEqual(desk.progress(1), [(1, 2, "Writing the story"), (2, 2, "Sending it to the site")])
        self.assertEqual(desk.progress(2), [(1, 2, "Reading 14 translated passages for episodes"),
                                            (2, 2, "Sending it to the site")])
        self.assertEqual(desk.progress(3), [(1, 3, "Writing the idea for the picture"), (2, 3, "Drawing the picture"),
                                            (3, 3, "Sending it to Drive")])
        self.assertEqual(desk.progress(4), [(1, 2, "Planning the graphic novel (10 pages)"), (2, 2, "Sending it to the site")])
        self.assertEqual(desk.progress(5), [(1, 2, "Drawing the cast"), (2, 2, "Sending it to Drive")])
        self.assertEqual(desk.progress(6), [(1, 2, "Approving story #35"), (2, 2, "Sending it to the site")])
        self.assertEqual(desk.progress(7), [(1, 2, "Approving page 2 of graphic novel #1"), (2, 2, "Sending it to the site")])

    def test_a_refused_request_tells_no_steps(self):
        desk, s = self.do({"id": 1, "kind": "story_range", "doc_code": DOC,
                           "params": {"from": "25.15", "to": "25.15", "title": "abc"}})
        self.assertEqual(desk.final(1)["status"], "failed")
        self.assertEqual(desk.progress(1), [])
        self.assertEqual([r["status"] for r in desk.reports], ["running", "failed"])

    # ---- novel_draw, page by page

    def test_novel_draw_tells_each_page_as_novel_py_prints_it(self):
        self.plan_novel()                                                      # 1-6 drawn, 7 stale, 8 missing
        self.scripts.pages = [7, 8]
        desk, s = self.do({"id": 5, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1}})
        r = desk.final(5)
        self.assertEqual(r["status"], "done", r)
        self.assertEqual(desk.progress(5), [(1, 4, "2 pages to draw"), (2, 4, "Drawing page 1 of 2"),
                                            (3, 4, "Drawing page 2 of 2"), (4, 4, "Sending it to Drive")])
        draws = [c for c in self.scripts.calls if c[0] == "scripts/novel.py"]
        self.assertEqual(draws, [["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--yes"]])   # one call
        self.assertEqual(self.scripts.streamed, [True])
        self.assertEqual(r["result"], {"novel_id": 1, "pages": "all missing"})
        self.assertIn("page 8:", r["log"])
        desk, s = self.do({"id": 6, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "5-8"}})
        self.assertEqual(desk.progress(6)[0], (1, 4, "2 pages to draw"))
        self.assertIn(["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--pages", "5-8", "--yes"], self.scripts.calls)

    def test_nothing_to_draw(self):
        self.plan_novel()
        before = len(self.scripts.calls)
        desk, s = self.do({"id": 1, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "1-4"}},
                          {"id": 2, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "13-16"}})
        self.assertEqual(self.scripts.calls[before:], [])                      # neither novel.py nor corpus_media.py
        self.assertEqual((desk.final(1)["status"], desk.final(1)["message"], desk.final(1)["cost"]),
                         ("done", "Nothing to draw for graphic novel #1: every page asked for has a picture.", 0.0))
        self.assertEqual(desk.progress(1), [(2, 2, "Nothing to draw: every page asked for has a picture")])
        self.assertEqual(desk.final(2)["message"], "Nothing to draw for graphic novel #1: its plan has no page 13-16.")

    def test_a_novel_whose_plan_cannot_be_read_is_drawn_as_before(self):
        desk, s = self.do({"id": 1, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1, "pages": "1-4"}})
        self.assertEqual(desk.final(1)["status"], "done")                      # plan NULL: novel.py decides, as in 1.0
        self.assertIn(["scripts/novel.py", "--db", self.db, "draw", "--id", "1", "--pages", "1-4", "--yes"], self.scripts.calls)
        self.assertEqual([p[:2] for p in desk.progress(1)], [(1, 3), (2, 3), (3, 3)])
        con = sqlite3.connect(self.db)
        con.execute("UPDATE doc_novels SET plan='not json', page_images='[1]' WHERE id=1")
        con.commit()
        con.close()
        desk, s = self.do({"id": 2, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1}})
        self.assertEqual((desk.final(2)["status"], desk.progress(2)[1]), ("done", (2, 3, "Drawing the pages")))

    def test_the_count_follows_novel_py(self):
        self.plan_novel(drawn=(1, 2), stale=(2,), pages=4)                     # 2 is stale (the later status wins)
        con = sqlite3.connect(self.db)
        try:
            self.assertEqual(self.worker.pages_to_draw(con, 1, ""), ([2, 3, 4], 4))
            self.assertEqual(self.worker.pages_to_draw(con, 1, "1,3"), ([3], 2))
            self.assertEqual(self.worker.pages_to_draw(con, 1, "9-12"), ([], 0))
            self.assertEqual(self.worker.pages_to_draw(con, 99, ""), (None, None))
        finally:
            con.close()

    # ---- best effort

    def test_a_progress_report_that_fails_does_not_fail_the_request(self):
        class Flaky(ProgressDesk):
            def report(self, rid, status, result=None, message=None, cost=None, log=None):
                if result and "progress" in result:
                    raise cw.SinkError("corpus-desk unreachable: timed out")
                return super().report(rid, status, result, message, cost, log)
        desk, s = self.do({"id": 7, "kind": "story_range", "doc_code": DOC,
                           "params": {"from": "25.2", "to": "25.9", "title": "Vitasta flows"}}, desk_class=Flaky)
        self.assertEqual((s["done"], s["failed"]), (1, 0))
        self.assertEqual([r["status"] for r in desk.reports], ["running", "done"])
        self.assertTrue(any("progress report failed" in m for m in self.said), self.said)

        def boom(*a, **k):
            raise ZeroDivisionError("bug in a step")
        with mock.patch.object(cw.Progress, "__call__", boom):
            desk, s = self.do({"id": 8, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}})
        self.assertEqual(desk.final(8)["status"], "done")

    def test_after_a_failed_progress_report_no_more_are_tried(self):
        tries = []

        class Down(ProgressDesk):
            def report(self, rid, status, result=None, message=None, cost=None, log=None):
                if result and "progress" in result:
                    tries.append(result["progress"]["step"])
                    raise cw.SinkError("corpus-desk unreachable: timed out")
                return super().report(rid, status, result, message, cost, log)
        self.plan_novel()
        desk, s = self.do({"id": 9, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1}}, desk_class=Down)
        self.assertEqual(desk.final(9)["status"], "done", desk.final(9))
        self.assertEqual(len(tries), 1, tries)                                 # the first failure ends progress

    def test_a_runner_without_on_line_still_runs(self):
        old = base.FakeScripts(self.db)                                        # called as runner(args, timeout)
        self.worker.run = old
        self.plan_novel()
        desk, s = self.do({"id": 5, "kind": "novel_draw", "doc_code": DOC, "params": {"novel_id": 1}})
        self.assertEqual(desk.final(5)["status"], "done", desk.final(5))
        self.assertEqual([p[2] for p in desk.progress(5)], ["2 pages to draw", "Drawing page 1 of 2", "Sending it to Drive"])
        self.assertFalse(cw.takes_on_line(old))
        self.assertTrue(cw.takes_on_line(cw.run_script))
        self.assertTrue(cw.takes_on_line(lambda args, timeout, **kw: None))

    def test_without_progress_a_round_is_as_in_1_0(self):
        desk = ProgressDesk([{"id": 7, "kind": "story_write", "doc_code": DOC, "params": {"story_id": 36}, "est_usd": 0.01}])
        cw.run_once(desk, self.worker, 3)
        self.assertEqual([r["status"] for r in desk.reports], ["running", "done"])
        self.assertEqual(desk.beats[0]["sync"], {"every_min": 10, "mirror": None, "media": None})


class Unit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cwstate_"))
        self.mirror, self.media = self.tmp / "corpus_sync_log.jsonl", self.tmp / "corpus_media_log.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- the heartbeat's sync

    def test_the_heartbeat_carries_sync_from_the_last_lines(self):
        cs.log_run(sync_summary("error", "corpus-ingest HTTP 422: statement timeout"), self.mirror)
        cs.log_run(sync_summary(verified={"groups_equal": 120, "groups_different": 0, "different": []}), self.mirror)
        cm.log_run(media_summary(), self.media)
        info = cw.heartbeat_info({"cap": 10.0, "spent": 1.0, "left": 9.0, "paused": False}, (self.mirror, self.media))
        self.assertEqual(sorted(info), ["at", "budget", "client", "sync"])
        self.assertEqual(info["client"], cw.CLIENT)   # WORKER_TEST_CLIENT_2026_10_09
        sync = info["sync"]
        at_m, at_p = sync["mirror"].pop("at"), sync["media"].pop("at")
        self.assertRegex(at_m, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertRegex(at_p, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(sync, {"every_min": 10,
                                "mirror": {"ok": True, "stopped": "done", "error": None, "equal": 120, "different": 0,
                                           "client": cs.CLIENT[:60]},
                                "media": {"ok": True, "stopped": "done", "error": None, "files_needed": 10,
                                          "files_on_drive": 10, "pictures": 5}})
        self.assertLess(len(json.dumps(info)), 4000)

    def test_errors_differences_and_the_error_lines(self):
        long = "corpus-ingest HTTP 422: " + "x" * 600
        cs.log_run(sync_summary("error", long), self.mirror)
        cm.log_run({"sink": "edge", "apply": True, "stopped": "error", "error": "corpus-media HTTP 500: key AIzaSyA1234567890abcdefghijklmnop"},
                   self.media)                                                 # corpus_media.py's own error line
        s = cw.sync_state(self.mirror, self.media)
        self.assertEqual((s["mirror"]["ok"], s["mirror"]["stopped"], len(s["mirror"]["error"]), s["mirror"]["equal"],
                          s["mirror"]["different"]), (False, "error", 160, None, None))
        self.assertEqual((s["media"]["ok"], s["media"]["stopped"], s["media"]["files_needed"], s["media"]["files_on_drive"],
                          s["media"]["pictures"]), (False, "error", None, None, None))
        self.assertNotIn("AIzaSyA", s["media"]["error"])
        cs.log_run(sync_summary(verified={"groups_equal": 118, "groups_different": 2, "different": ["a/b", "c/d"]}), self.mirror)
        self.assertEqual(cw.sync_state(self.mirror)["mirror"]["ok"], False)    # a group is different
        cs.log_run(sync_summary(verified={"groups_equal": 0, "groups_different": None, "different": [],
                                          "error": "corpus-ingest unreachable"}), self.mirror)
        m = cw.sync_state(self.mirror)["mirror"]
        self.assertEqual((m["ok"], m["error"], m["different"]), (True, "verify: corpus-ingest unreachable", None))
        cm.log_run(media_summary(stopped="budget", needed=40, on_drive=10, uploaded=12, skipped=3), self.media)
        p = cw.sync_state(None, self.media)["media"]
        self.assertEqual((p["ok"], p["stopped"], p["files_needed"], p["files_on_drive"]), (False, "budget", 40, 25))

    def test_a_missing_empty_or_broken_log_says_null(self):
        self.assertEqual(cw.sync_state(self.mirror, self.media), {"every_min": 10, "mirror": None, "media": None})
        self.mirror.write_text("")
        self.media.mkdir()                                                     # unreadable: a folder
        self.assertEqual(cw.sync_state(self.mirror, self.media), {"every_min": 10, "mirror": None, "media": None})
        self.mirror.write_text("[1, 2]\n\"text\"\n")
        self.assertIsNone(cw.sync_state(self.mirror)["mirror"])
        cs.log_run(sync_summary(verified={"groups_equal": 3, "groups_different": 0, "different": []}), self.mirror)
        with open(self.mirror, "a", encoding="utf-8") as fh:
            fh.write('{"run_id": "r2", "stopped": "do')                      # a line still being written
        self.assertEqual(cw.sync_state(self.mirror)["mirror"]["equal"], 3)   # the last whole line
        self.mirror.write_text('{"stopped": "done", "verified": "odd", "ts": 5}\n')
        self.assertEqual(cw.sync_state(self.mirror)["mirror"],
                         {"at": "5", "ok": True, "stopped": "done", "error": None, "equal": None, "different": None,
                          "client": ""})

    def test_only_the_end_of_a_log_is_read(self):
        with open(self.mirror, "wb") as fh:
            fh.write(b'{"stopped": "error"}\n' * 200000)                      # about 4 MB of older runs
        cs.log_run(sync_summary(verified={"groups_equal": 7, "groups_different": 0, "different": []}), self.mirror)
        reads = []
        real_open = open

        class Counting:
            def __init__(self, fh):
                self.fh = fh

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.fh.close()

            def seek(self, *a):
                return self.fh.seek(*a)

            def read(self, n=-1):
                data = self.fh.read(n)
                reads.append(len(data))
                return data
        with mock.patch("builtins.open", lambda path, mode="r", *a, **k: Counting(real_open(path, mode, *a, **k))):
            rec = cw.last_json_line(self.mirror)
        self.assertEqual(rec["verified"]["groups_equal"], 7)
        self.assertLessEqual(sum(reads), 65536)
        with open(self.media, "wb") as fh:
            fh.write(b'{"stopped": "done", "note": "' + b"n" * (cw.LOG_TAIL_MAX_BYTES + 10) + b'"}\n')
        self.assertIsNone(cw.last_json_line(self.media))                    # a last line too long to read

    def test_the_info_stays_under_4000_characters(self):
        rec = sync_summary("error", "e" * 5000)
        rec["client"], rec["stopped"], rec["ts"] = "c" * 5000, "s" * 5000, "t" * 5000
        with open(self.mirror, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        mrec = media_summary()
        mrec.update({"error": "\u0915" * 3000, "stopped": "error", "ts": "\u0916" * 3000})
        with open(self.media, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(mrec, ensure_ascii=False) + "\n")
        info = cw.heartbeat_info({"cap": 1, "spent": 0, "left": 1, "paused": False}, (self.mirror, self.media))
        self.assertLessEqual(cw.info_chars(info), cw.INFO_MAX_CHARS)
        self.assertLess(len(json.dumps(info, ensure_ascii=False)), 4000)      # as jsonb prints it
        m, p = info["sync"]["mirror"], info["sync"]["media"]
        self.assertEqual((len(m["error"]), len(m["client"]), len(m["stopped"]), len(m["at"])), (160, 60, 20, 40))
        self.assertEqual(len(p["error"]), 160)
        with mock.patch.object(cw, "INFO_MAX_CHARS", 1000):                  # 1822 as it is, 982 cut
            small = cw.heartbeat_info(None, (self.mirror, self.media))         # the errors are cut first
            self.assertLessEqual(cw.info_chars(small), 1000)
            self.assertEqual((len(small["sync"]["mirror"]["error"]), len(small["sync"]["media"]["error"])), (40, 40))
        with mock.patch.object(cw, "INFO_MAX_CHARS", 500):
            smaller = cw.heartbeat_info(None, (self.mirror, self.media))       # then the channels
            self.assertEqual(smaller["sync"], {"every_min": 10, "mirror": None, "media": None})
        with mock.patch.object(cw, "INFO_MAX_CHARS", 120):
            self.assertIsNone(cw.heartbeat_info(None, (self.mirror, self.media))["sync"])

    # ---- the 5-second rule

    def test_progress_holds_quick_steps_and_keeps_the_first_and_the_last(self):
        clock, sent = Clock(), []
        with mock.patch.object(cw.Progress, "clock", staticmethod(clock.now)), \
                mock.patch.object(cw.Progress, "sleep", staticmethod(clock.sleep)):
            p = cw.Progress(lambda *a: sent.append(a))
            p(1, 5, "one")
            p(2, 5, "two")
            p(3, 5, "three")
            self.assertEqual(p.held, (3, 5, "three"))
            p(5, 5, "five")                                                     # the last goes at once
            self.assertEqual((sent, p.held), ([(1, 5, "one"), (5, 5, "five")], None))
            q = cw.Progress(lambda *a: sent.append(a))
            q(1, 3, "a")
            clock.t += 2
            q(2, 3, "b")
            q.flush()                                                           # before a script: waits out the gap
            self.assertEqual((sent[-1], clock.slept), ((2, 3, "b"), [3.0]))
            q.flush()
            self.assertEqual(clock.slept, [3.0])                               # nothing held, no wait
            clock.t += 5
            q(9, 0, "x" * 300)                                                  # made safe: of >= 1, step <= of
            self.assertEqual(sent[-1], (1, 1, "x" * 200))
            q(-4, 7, None)
            self.assertEqual(sent[-1], (1, 1, "x" * 200))                      # within 5 s: held
            self.assertEqual(q.held, (0, 7, ""))
            said = []
            bad = cw.Progress(lambda *a: 1 / 0, say=said.append)
            bad(1, 2, "x")
            self.assertTrue(said and "progress report failed" in said[0])

    # ---- run_script with on_line, for real

    def test_run_script_streams_the_lines_as_they_come(self):
        prog = self.tmp / "emit.py"
        prog.write_text(textwrap.dedent("""\
            import sys, time
            for n in (1, 2, 3):
                print("  page %d: p%d.png (0.1 s)" % (n, n))
                time.sleep(0.4)
            sys.stderr.write("a warning\\n")
            sys.exit(3)
            """))
        seen = []
        t0 = time.monotonic()

        def on_line(line):
            seen.append((line, time.monotonic() - t0))
            if len(seen) == 2:
                raise ValueError("a broken callback")                          # never stops the script
        rc, out = cw.run_script([str(prog)], 30, on_line=on_line)
        total = time.monotonic() - t0
        self.assertEqual(rc, 3)
        self.assertEqual([s[0] for s in seen], ["  page 1: p1.png (0.1 s)", "  page 2: p2.png (0.1 s)",
                                                "  page 3: p3.png (0.1 s)"])
        self.assertLess(seen[0][1], total - 0.6)                               # line 1 came before the end
        self.assertEqual(out, "  page 1: p1.png (0.1 s)\n  page 2: p2.png (0.1 s)\n  page 3: p3.png (0.1 s)\n\na warning\n")
        self.assertEqual(cw.run_script([str(prog)], 30), (3, out))             # the same answer without on_line

    def test_run_script_streaming_keeps_the_timeout(self):
        prog = self.tmp / "slow.py"
        prog.write_text("import time\nprint('started', flush=True)\ntime.sleep(20)\n")
        t0 = time.monotonic()
        rc, out = cw.run_script([str(prog)], 1, on_line=lambda line: None)
        self.assertLess(time.monotonic() - t0, 10)
        self.assertEqual((rc, out), (124, "started\n\n[timed out after 1 s]"))


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class PgEndToEnd(base.Base):
    """Worker 1.1 against C9 + C10a: the progress lands in corner.requests.progress, one event per
    change, and the heartbeat's sync in corner.worker.info."""

    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        if cls.pg.execute("SELECT 1 FROM pg_attribute WHERE attrelid = to_regclass('corner.requests') "
                          "AND attname = 'progress' AND NOT attisdropped").fetchone() is None:
            cls.pg.close()
            raise unittest.SkipTest("C10a is not applied in this test database (run tests.test_corner_state_pg_2026_10_09 first)")

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def test_pull_do_report_with_progress(self):
        x = self.pg.execute
        x("TRUNCATE corner.requests, corner.events RESTART IDENTITY")
        x("UPDATE corner.worker SET last_seen = NULL, info = NULL")
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.stories, corpus.passages, corpus.docs CASCADE")
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES (%s, 'Nilamata', 'x')", (DOC,))
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, row_hash) VALUES (%s, 36, 'candidate', 'C', 'x')", (DOC,))
        with self.pg.transaction():
            x("SET LOCAL ROLE authenticated")
            x("SELECT set_config('request.jwt.claim.sub', '44444444-4444-4444-4444-444444444444', true)")
            rid = x("SELECT request_id FROM public.corner_request_create('story_write', %s, '{\"story_id\": 36}', NULL)",
                    (DOC,)).fetchone()[0]
        mirror, media = self.tmp / "corpus_sync_log.jsonl", self.tmp / "corpus_media_log.jsonl"
        cs.log_run(sync_summary(verified={"groups_equal": 9, "groups_different": 0, "different": []}), mirror)
        cm.log_run(media_summary(), media)
        desk = cw.PgDesk(DSN)
        try:
            s = cw.run_once(desk, self.worker, 3, "test-desk", progress=True, logs=(mirror, media))
        finally:
            desk.con.close()
        self.assertEqual((s["taken"], s["done"]), (1, 1), s)
        row = x("SELECT status, result ->> 'story_id', progress, message, started_at IS NOT NULL FROM corner.requests "
                "WHERE id = %s", (rid,)).fetchone()
        self.assertEqual((row[0], row[1], row[2]["step"], row[2]["of"], row[2]["note"], row[4]),
                         ("done", "36", 2, 2, "Sending it to the site", True))
        self.assertEqual(row[3], "Story #36 written.")
        ev = [r[0] for r in x("SELECT action FROM corner.events WHERE request_id = %s AND action LIKE 'desk%%' ORDER BY id",
                              (rid,))]
        self.assertEqual(ev, ["desk_running", "desk_done"])
        info = x("SELECT info, length(info::text) FROM corner.worker").fetchone()
        self.assertEqual((info[0]["client"], info[0]["sync"]["mirror"]["ok"], info[0]["sync"]["mirror"]["equal"],
                          info[0]["sync"]["media"]["files_on_drive"]), (cw.CLIENT, True, 9, 10))   # WORKER_TEST_CLIENT_2026_10_09
        self.assertLess(info[1], 4000)


if __name__ == "__main__":
    unittest.main()
