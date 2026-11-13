# -*- coding: ascii -*-
"""SOURCE_PICK_2026_11_13. Asked on 13 Nov: "are we able to choose the best available from etext and our own ocr+vision
text for translation and then get to the scholarly prose and edition for each?" The benchmark measured the scan's
reading and the e-text witnesses and said nothing of which to use; now it picks the reading to make the scholarly English
and its prose from, and the desk shows the pick."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import benchmark_sources as bs     # noqa: E402
import translation_desk as td      # noqa: E402

OURS = {"label": "consensus", "kind": "ours", "misread_letters_pct": 0.10, "level": "cosmetic", "letters": 281635}
GRETIL = {"label": "witness gretil", "kind": "etext", "site": "gretil", "f1_ours": 0.759, "ours_pages": 378,
          "misread_letters_pct": 0.0, "letters": 296911}


class ThePick(unittest.TestCase):
    def test_the_same_text_as_an_etext_takes_the_etext(self):
        p = bs.pick_reading({"readings": [OURS, GRETIL]}, "gandharva_veda_natya_shastra")
        self.assertEqual(p["doc"], "gandharva_veda_natya_shastra__w_gretil")
        self.assertIn("F1 0.76", p["why"])
        self.assertIn("scholar_translate.py --doc gandharva_veda_natya_shastra__w_gretil --status", p["then"])

    def test_another_recension_keeps_ours(self):
        w = dict(GRETIL, f1_ours=0.31)
        p = bs.pick_reading({"readings": [OURS, w]}, "x")
        self.assertEqual(p["doc"], "x")
        self.assertIn("another recension", p["why"])
        self.assertEqual(p["then"], "")

    def test_another_recension_and_a_misread_scan(self):
        w = dict(GRETIL, f1_ours=0.31)
        o = dict(OURS, misread_letters_pct=1.84, level="moderate")
        p = bs.pick_reading({"readings": [o, w]}, "x")
        self.assertEqual(p["doc"], "x")
        self.assertIn("repair it first", p["why"])
        self.assertIn("repair_text.py --doc x", p["then"])

    def test_an_etext_that_misreads_more_is_not_taken(self):
        w = dict(GRETIL, misread_letters_pct=0.5)
        self.assertEqual(bs.pick_reading({"readings": [OURS, w]}, "x")["doc"], "x")

    def test_of_two_etexts_the_nearer(self):
        far = dict(GRETIL, site="etext", label="witness etext", f1_ours=0.65)
        p = bs.pick_reading({"readings": [OURS, far, GRETIL]}, "x")
        self.assertEqual(p["doc"], "x__w_gretil")

    def test_no_etext(self):
        p = bs.pick_reading({"readings": [OURS]}, "Mallapurana")
        self.assertEqual(p["doc"], "Mallapurana")
        self.assertIn("ready for its scholarly", p["why"])
        o = dict(OURS, misread_letters_pct=1.84, level="moderate")
        p = bs.pick_reading({"readings": [o]}, "Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V")
        self.assertIn("repair it first", p["why"])
        self.assertIn("repair_text.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V", p["then"])

    def test_nothing_read(self):
        self.assertEqual(bs.pick_reading({"readings": []}, "x")["reading"], "")

    def test_the_benchmark_prints_and_keeps_it(self):
        src = (REPO / "scripts" / "benchmark_sources.py").read_text(encoding="utf-8")
        self.assertIn('res["pick"] = pick_reading(res, doc)   # SOURCE_PICK_2026_11_13', src)
        self.assertIn('print("PICK: for the scholarly English and its prose:', src)


class TheDesk(unittest.TestCase):
    def test_pick_of(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "jyotish_surya_siddhanta.json").write_text(json.dumps(
                {"at": "2026-11-13T20:00:00", "pick": {"doc": "jyotish_surya_siddhanta__w_etext", "reading": "witness etext",
                                                       "why": "w", "then": ""}}), encoding="utf-8")
            (Path(d) / "old.json").write_text(json.dumps({"at": "x", "verdict": "no pick then"}), encoding="utf-8")
            (Path(d) / "bad.json").write_text("{", encoding="utf-8")
            p = td.pick_of("jyotish_surya_siddhanta", d)
            self.assertEqual(p["doc"], "jyotish_surya_siddhanta__w_etext")
            self.assertEqual(p["at"], "2026-11-13T20:00:00")
            self.assertEqual(p["of"], "jyotish_surya_siddhanta")
            self.assertEqual(td.pick_of("jyotish_surya_siddhanta__w_etext", d)["doc"], "jyotish_surya_siddhanta__w_etext")
            for doc in ("old", "bad", "none", ""):
                self.assertIsNone(td.pick_of(doc, d), doc)

    def test_the_page_shows_it(self):
        src = (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('_pk = td.pick_of(r["doc"], BENCH_DIR) if hasattr(td, "pick_of") else None   # SOURCE_PICK_2026_11_13', src)
        self.assertIn("The reading to make the edition from (the benchmark of %s)", src)


PAT = REPO / "scripts" / "patch_source_pick_2026_11_13.py"
FILES = ("scripts/benchmark_sources.py", "scripts/translation_desk.py", "scripts/dashboard.py",
         "tests/test_banner_head_2026_11_13.py", "tests/test_bench_letters_2026_10_22.py")


@unittest.skipUnless(PAT.exists(), "patch_source_pick_2026_11_13.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_sourcepick_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if b"SOURCE_PICK_2026_11_13" in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 5 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
