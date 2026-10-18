# -*- coding: ascii -*-
"""DOCS76_2026_10_18: the night of 18 Oct recorded (PLATFORM 79, RUNBOOK, ENTERPRISE_PATH 66, STATE 11), adhyayas 19
to 31 on in configs/editions.json (with a subtitle from their own first verses), the editions test following it, and a
title for the GRETIL Markandeya. The patcher applies once to what it found, all or nothing. Temp folders only."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
PAT = SCRIPTS / "patch_docs76_2026_10_18.py"
MARK = "DOCS76_2026_10_18"
FILES = ("docs/PLATFORM_2026-10-04.md", "RUNBOOK.md", "docs/ENTERPRISE_PATH_2026-10-04.md", "docs/STATE_2026-10-18.md",
         "configs/editions.json", "tests/test_publish_editions_2026_10_18.py", "configs/doc_titles.json")
APPLIED = (REPO / "configs" / "editions.json").exists() and MARK in (REPO / "configs" / "editions.json").read_text(encoding="utf-8")


class TheConfig(unittest.TestCase):
    @unittest.skipUnless(APPLIED, "DOCS76_2026_10_18 is not applied here")
    def test_adhyayas_19_to_31_are_on(self):
        import publish_editions as P
        c = json.loads((REPO / "configs" / "editions.json").read_text(encoding="utf-8"))
        on = [e for e in c["editions"] if e.get("enabled", True)]
        self.assertEqual([e["slug"] for e in on], ["devimahatmya", "markandeya-purana-19-31"])
        e = on[1]
        self.assertEqual((e["doc"], e["pages"]), ("markandeya_purana__w_gretil", [81, 124]))
        self.assertIn("Mad\u0101las\u0101's teaching of Alarka", e["subtitle"])
        self.assertNotIn("why_off", e)
        for x in c["editions"]:
            self.assertEqual(P.check_entry(x, {}), "", x["slug"])
        t = json.loads((REPO / "configs" / "doc_titles.json").read_text(encoding="utf-8"))
        self.assertTrue(t["titles"].get("markandeya_purana__w_gretil"), "a title for the GRETIL Markandeya")
        self.assertEqual(t["titles"]["markandeya_purana"], "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a", "the others kept")
        for f in FILES[:4]:
            self.assertIn(MARK, (REPO / f).read_text(encoding="utf-8"), f)


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_docs76_*")) for f in FILES}
        if not APPLIED or not all(baks.values()):
            self.skipTest("no .bak_docs76_ copies here")
        pat = [sys.executable, str(PAT)]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for d in ("scripts", "docs", "configs", "tests"):
                (t / d).mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in FILES:
                shutil.copy2(baks[f][0], t / f)
            e = t / "configs" / "editions.json"
            e.write_bytes(e.read_bytes().replace(b'"pages": [81, 124]', b'"pages": [81, 125]'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("configs/editions.json: its anchor is there 0 times", r.stdout.replace("\\", "/"))
            self.assertNotIn(MARK.encode(), (t / "RUNBOOK.md").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
