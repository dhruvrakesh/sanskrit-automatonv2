# -*- coding: ascii -*-
"""HUB_V2_1_2026_10_10: the hub shows the dashboard's last runs and what each did (from data/jobs.jsonl),
the texts held for an OCR repair, and how far a running OCR has got (its page files against its inbox
pages). Loads docs/hub/HUB_V2_1_2026-10-10/hub.py with its folders pointed at a temp tree; no network,
no port."""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAYLOAD = REPO / "docs" / "hub" / "HUB_V2_1_2026-10-10"
HELD = ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): ...\r\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc K "
        "--threshold 101 --include-unassessed\r\n  Translate anyway: add --allow-debris (dashboard: set SA_ALLOW_DEBRIS=1).\r\n")


def rec(i, kind, doc, ok, rc, tail, end):
    return {"id": "j%d" % i, "kind": kind, "doc": doc, "start": end - 1, "end": end, "ok": ok, "rc": rc,
            "duration_s": 1.0, "out_lines": 2, "err_preview": "", "out_tail": tail}


class HubV21(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpd = tempfile.TemporaryDirectory()
        t = Path(cls.tmpd.name)
        data = t / "automaton" / "data"
        (data / "raw").mkdir(parents=True)
        (t / "automaton" / "inbox").mkdir()
        (t / "backups").mkdir()
        now = time.time()
        rows = [
            rec(1, "translate", "K", False, 3, HELD, now - 900),                 # an old hold for K ...
            rec(2, "translate", "K", True, 0, "Done. 5/5 translated | 0 quality-skipped | 0 errors", now - 800),  # ... then it ran
            rec(3, "translate_hi", "N", False, 3, HELD.replace("--doc K", "--doc N"), now - 700),
            rec(4, "translate_both", "G", True, 0, "Done. 1/1 translated | 1 quality-skipped | 0 errors\n"
                "Done. 7/186 translated | 185 quality-skipped | 0 errors", now - 600),
            rec(5, "translate", "D", True, 0, "[NOTHING] doc 'D': 0 translatable verses", now - 500),
            rec(6, "export", "E", False, 1, "Traceback: boom", now - 400),
            rec(7, "ocr", "Y", False, 1, "[KILLED by user]", now - 300),
            rec(8, "translate", "T", False, 3, HELD.replace("--doc K", "--doc T"), now - 200),
        ]
        (data / "jobs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n", encoding="utf-8")
        for i in range(1, 11):
            (t / "automaton" / "inbox" / ("Y_%04d.pdf" % i)).write_bytes(b"%PDF")
        for i in range(1, 4):
            (data / "raw" / ("Y_%04d.jsonl" % i)).write_text("{}", encoding="utf-8")
        (data / "raw" / "Y_0004_norm.jsonl").write_text("{}", encoding="utf-8")
        (data / "raw" / "Yother_0001.jsonl").write_text("{}", encoding="utf-8")   # another text, not counted
        os.environ["SYMPHONY_AUTOMATON"] = str(t / "automaton")
        os.environ["SYMPHONY_BACKUPS"] = str(t / "backups")
        os.environ["SYMPHONY_WISDOMLIB"] = str(t / "wisdomlib")
        spec = importlib.util.spec_from_file_location("hub_v21_test", str(PAYLOAD / "hub.py"))
        cls.h = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.h
        spec.loader.exec_module(cls.h)
        cls.c = cls.h.app.test_client()

    @classmethod
    def tearDownClass(cls):
        for k in ("SYMPHONY_AUTOMATON", "SYMPHONY_BACKUPS", "SYMPHONY_WISDOMLIB"):
            os.environ.pop(k, None)
        cls.tmpd.cleanup()

    def test_payload(self):
        for name in ("hub.py", "hub.html"):
            b = (PAYLOAD / name).read_bytes()
            self.assertTrue(all(x < 128 for x in b), name)
            self.assertIn(b"HUB_V2_1_2026_10_10", b)
            self.assertIn(b"HUB_V2_2026_10_10", b, "v2's changes are kept")
            self.assertNotIn(b"\r\n", b)

    def test_the_installer_carries_this_payload(self):
        spec = importlib.util.spec_from_file_location("patch_hub_v21", str(REPO / "scripts" / "patch_hub_v2_1_2026_10_10.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        for name in ("hub.py", "hub.html"):
            self.assertEqual(mod.md5n((PAYLOAD / name).read_bytes()), mod.V21[name], name)
            v2 = (REPO / "docs" / "hub" / "HUB_V2_2026-10-10" / name).read_bytes()
            self.assertEqual(mod.md5n(v2), mod.V2[name], "it upgrades exactly the released v2")

    def test_verdicts(self):
        v = self.h._verdict
        self.assertEqual(v({"ok": False, "rc": 3, "kind": "translate", "out_tail": HELD})[0], "held")
        self.assertEqual(v({"ok": False, "rc": 1, "kind": "ocr", "out_tail": "[KILLED by user]"})[0], "stopped")
        self.assertEqual(v({"ok": False, "rc": 1, "kind": "export", "out_tail": "x"}), ("failed", "failed (exit 1)"))
        self.assertEqual(v({"ok": True, "kind": "translate", "out_tail": "[NOTHING] doc"})[0], "nothing")
        w, t = v({"ok": True, "kind": "translate_both", "out_tail": "Done. 1/1 translated | 1 quality-skipped | 0 errors\n"
                  "Done. 7/186 translated | 185 quality-skipped | 0 errors"})
        self.assertEqual(w, "done")
        self.assertEqual(t, "1 of 1 translated, 1 below the OCR bar; 7 of 186 translated, 185 below the OCR bar")
        self.assertEqual(v({"ok": True, "kind": "translate", "out_tail": "Done. 0/5 translated | 5 quality-skipped | 0 errors"})[0],
                         "nothing sent")
        self.assertEqual(v({"ok": False, "rc": 3, "kind": "export", "out_tail": "x"})[0], "failed", "exit 3 holds only translations")

    def test_online_carries_the_runs_the_held_texts_and_the_ocr(self):
        self.h._SERVICES.update(at=time.time(), data={"automaton": {"jobs": {"running": [
            {"kind": "ocr", "doc": "Y", "state": "running", "elapsed_s": 100}]}}})
        o = self.c.get("/api/online").get_json()
        self.assertEqual(o["mark"], "HUB_V2_1_2026_10_10")
        r = o["runs"]
        self.assertEqual([x["id"] for x in r["runs"]], ["j8", "j7", "j6", "j5", "j4", "j3", "j2", "j1"], "newest first")
        self.assertEqual([x["verdict"] for x in r["runs"][:5]], ["held", "stopped", "failed", "nothing", "done"])
        self.assertEqual(sorted(x["doc"] for x in r["held"]), ["N", "T"], "K ran after its hold; G, D are not held")
        self.assertEqual(sum(r["today"].values()), 8)
        self.assertEqual(o["ocr"], {"Y": {"pages_done": 4, "pages_total": 10}})

    def test_no_ocr_running_counts_nothing(self):
        self.h._SERVICES.update(at=time.time(), data={"automaton": {"jobs": {"running": []}}})
        self.assertEqual(self.h._ocr_progress(), {})

    def test_page(self):
        h = (PAYLOAD / "hub.html").read_text(encoding="utf-8")
        for s in ('id="f-runs"', "function runs(r)", "OCR = o.ocr || {};", "setInterval(online, 30000);",
                  "Held for an OCR repair"):
            self.assertIn(s, h)
        node = shutil.which("node")
        if not node:
            return
        js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
        p = Path(self.tmpd.name) / "hub.js"; p.write_text(js, encoding="utf-8")
        r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
