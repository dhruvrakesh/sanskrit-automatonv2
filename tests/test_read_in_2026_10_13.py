# -*- coding: ascii -*-
"""READ_IN_2026_10_13: a scan vision has read (80% of its pages, 95% merged; the merge leaves out blank pages) goes in
now, in place; the pages vision failed on twice (left to Tesseract) are not counted as pages to read; the drift
check offers the in-place re-ingest before the whole text again. Temp files only, never data/context.db."""
import importlib.util, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


PR = {"vision_page": 0.0040, "vision_dear": 0.0070, "vision_median": 0.0022, "measured": ["N"], "passage": 0.00048,
      "passage_from": "usage_log"}
NATYA = {"doc": "N", "state": None, "passages": 2916, "english": 0, "hindi": 0, "below_quality": 121, "vision_pct": 0.0,
         "level": "material", "misread_letters_pct": 3.42, "pdfs": 546, "raw_pages": 546, "vision_pages": 513,
         "merged_pages": 538, "merged_complete": False, "cost_per_page": 0.0070, "db_pages": 537, "reviews": None,
         "vectors": 0, "price_from": "this text", "changed": 505, "changed_en": 0, "changed_hi": 0, "changed_say": False,
         "vision_gave_up": 22}


class TheChart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tp = load("text_path_readin", SCRIPTS / "text_path.py")

    def test_the_natyasastra_is_read_and_goes_in(self):
        o = self.tp.decide(dict(NATYA), PR)
        self.assertEqual(o["path"], "use_repair", o)
        self.assertEqual(o["next"][1], "python scripts\\reingest_pages.py --doc N   (the plan, free)")
        self.assertEqual(o["next"][2], "python scripts\\reingest_pages.py --doc N --apply")
        self.assertTrue(any(x.startswith("11 page(s) vision has not read yet (22 more left to Tesseract): python scripts"
                                         "\\repair_text.py --doc N --repair --max-usd 1.00") for x in o["also"]), o["also"])

    def test_a_merge_too_small_still_repairs_and_the_given_up_pages_are_not_priced(self):
        o = self.tp.decide(dict(NATYA, merged_pages=400, vision_pages=300), PR)
        self.assertEqual(o["path"], "repair")
        self.assertIn("about 224 pages at $0.0070 a page", o["next"][0], "546 - 300 read - 22 left to Tesseract")
        o = self.tp.decide(dict(NATYA, merged_pages=400, vision_pages=524), PR)   # every page left failed twice
        self.assertEqual(o["path"], "source"); self.assertIn("failed twice on the other 22", o["why"])
        o = self.tp.decide(dict(NATYA, merged_pages=400, vision_pages=546, vision_gave_up=0), PR)
        self.assertNotEqual(o["path"], "source", "all read: not a scan that resists")

    def test_complete_as_before(self):
        o = self.tp.decide(dict(NATYA, merged_pages=546, merged_complete=True, vision_gave_up=0, vision_pages=546), PR)
        self.assertEqual(o["path"], "use_repair")
        self.assertFalse(any("vision has not read yet" in x for x in o["also"]))


class TheAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rt = load("repair_text_readin", SCRIPTS / "repair_text.py")

    def r(self, **kw):
        r = {"state": None, "judged": {}, "untranslated": 2916, "held": True, "debris_pct": 71.2, "vision_pct": 0.0,
             "pdfs": 546, "raw_pages": 546, "consensus": {"stale": 504}, "merged_complete": False, "merged_pages": 538,
             "queued": 537, "vision_pages": 513, "cost_per_page": 0.0070, "english": 0, "hindi": 0, "passages": 2916,
             "quality_stuck": False, "vision_gave_up": 22}
        r.update(kw)
        return r

    def test_the_read_scan_goes_in_in_place(self):
        v, nxt, also = self.rt.advise(self.r(), "N")
        self.assertIn("vision has read 513 of its 546 pages (22 left to Tesseract: vision failed on them twice) and 538 "
                      "are merged: they can go in now", v)
        self.assertTrue(nxt.startswith("python scripts\\reingest_pages.py --doc N   (only the pages that changed"), nxt)
        self.assertTrue(also[0].startswith("python scripts\\repair_text.py --doc N --repair --max-usd 1.00   (the 2 "
                                           "page(s) vision has not read yet; after)"), also)

    def test_not_yet_read_is_a_repair_as_before(self):
        v, nxt, also = self.rt.advise(self.r(vision_pages=268, merged_pages=537, vision_gave_up=0), "N")
        self.assertIn("vision OCR on about 269 page(s), about $1.88 ($0.0070 a page)", v)
        self.assertEqual(nxt, "python scripts\\repair_text.py --doc N --repair --max-usd 2.40   (it stops before spending "
                              "more)")

    def test_the_ledger_is_counted(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            (w / "N_vision_failed.json").write_text(json.dumps({"N_0002": {"fails": 2}, "N_0003": {"fails": 1},
                                                                "N_0005": {"fails": 3}}), encoding="utf-8")
            self.assertEqual(self.rt.vision_gave_up(w, "N"), 2)
            self.assertEqual(self.rt.vision_gave_up(w, "none"), 0)


class TheDriftBlock(unittest.TestCase):
    def test_in_place_first(self):
        oc = load("ocr_consensus_readin", SCRIPTS / "ocr_consensus.py")
        lines = oc.reingest_commands("N").splitlines()
        self.assertTrue(lines[1].startswith("python scripts\\reingest_pages.py --doc N "), lines[:3])
        self.assertTrue(lines[2].startswith("python scripts\\reingest_pages.py --doc N --apply"))
        i = next(k for k, x in enumerate(lines) if "wipe_doc.py" in x)
        self.assertGreater(i, 4); self.assertIn("translations, vectors and reviews are deleted", " ".join(lines[:i]))


class ThePatcher(unittest.TestCase):
    FILES = ("repair_text.py", "text_path.py", "ocr_consensus.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_readin_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            shutil.copy2(SCRIPTS / "dashboard.py", t / "scripts" / "dashboard.py")
            pat = [sys.executable, str(SCRIPTS / "patch_read_in_2026_10_13.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_redeem_*"))   # REDEEM_2026_10_14 came after (text_path.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "ocr_consensus.py"
            p.write_bytes(p.read_bytes().replace(b'    stamp = "$(Get-Date -Format yyyyMMdd_HHmmss)"\n',
                                                 b'    stamp = "$(Get-Date -Format %Y%m%d)"\n'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"READ_IN_2026_10_13", (t / "scripts" / "repair_text.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_mark(self):
        for p in (SCRIPTS / "patch_read_in_2026_10_13.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"READ_IN_2026_10_13", b)


if __name__ == "__main__":
    unittest.main()
