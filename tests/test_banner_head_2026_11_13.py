# -*- coding: ascii -*-
"""BANNER_HEAD_2026_11_13 and DESK_SCHOLAR_NEXT_2026_11_13.

A publisher's running head at the front of a page's first passage ("MAHARISHI UNIVERSITY OF MANAGEMENT / VEDIC
LITERATURE COLLECTION", the Maharishi University's editions) made should_translate() call the whole passage front
matter, so each page's first verses were never translated (1,745 passages of 21 texts on the backup of 13 Nov). And the
desk called a text whose working English is done "nothing to do", never offering its scholarly English (Mallapurana)."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import text_filters as tf          # noqa: E402
import translation_desk as td      # noqa: E402

GANDHARVA = "\u0917\u0928\u094d\u0927\u0930\u094d\u0935\u0935\u0947\u0926"          # the work's name
VERSE1 = ("\u0935\u093f\u0937\u093e\u0926\u093e\u0936\u094d\u0930\u092e\u0928\u093f\u0930\u094d\u0935\u0947\u0926\u093e "
          "\u0917\u0930\u094d\u0935\u0935\u0947\u0917\u094c \u0927\u0943\u0924\u093f\u0903 \u0938\u094d\u092e\u0943\u0924"
          "\u093f\u0903")
VERSE2 = ("\u092e\u0924\u093f\u092e\u094b\u0939\u094b \u0935\u093f\u092c\u094b\u0927\u0936\u094d\u091a "
          "\u0938\u0941\u092a\u094d\u0924\u094c\u0924\u094d\u0938\u0941\u0915\u094d\u092f\u0935\u0930\u094d\u091c\u093f\u0924"
          "\u0947 \u0964")
KRSNA_YAJUR = "\u0915\u0943\u0937\u094d\u0923\u093e \u092f\u091c\u0941\u0930\u094d\u0935\u0947\u0926"   # two words
ATHA = ("\u0905\u0925 \u092a\u094d\u0930\u0925\u092e\u094b\u093d\u0927\u094d\u092f\u093e\u092f\u0903")  # atha prathamo'dhyayah
HEAD = "[Gandharva Veda]\n%s\nGANDHARVA VEDA\nMAHARISHI UNIVERSITY OF MANAGEMENT\nVEDIC LITERATURE COLLECTION\n\n" % GANDHARVA


class TheHead(unittest.TestCase):
    def test_the_gandharva_page(self):
        s = HEAD + VERSE1 + "\n" + VERSE2
        self.assertEqual(tf.strip_banner_head(s), VERSE1 + "\n" + VERSE2)
        self.assertTrue(tf.should_translate(s))
        mt = tf.clean_for_mt(s)
        self.assertNotIn("VEDIC LITERATURE", mt)
        self.assertNotIn("MAHARISHI", mt)
        self.assertTrue(mt.startswith(VERSE1))

    def test_the_yajurveda_page(self):
        s = "MAHARISHI UNIVERSITY OF MANAGEMENT\nVEDIC LITERATURE COLLECTION\n%s\n[Yajur Veda]\n\n%s" % (KRSNA_YAJUR, VERSE1)
        self.assertEqual(tf.strip_banner_head(s), VERSE1)
        self.assertTrue(tf.should_translate(s))

    def test_the_banner_alone_stays_front_matter(self):
        for s in ("MAHARISHI UNIVERSITY OF MANAGEMENT\nVEDIC LITERATURE COLLECTION",
                  HEAD + "Introduction\nThis volume presents the text with a preface.",
                  "VEDIC LITERATURE COLLECTION"):
            self.assertEqual(tf.strip_banner_head(s), s)
            self.assertFalse(tf.should_translate(s), s)

    def test_no_banner_no_change(self):
        for s in (VERSE1, GANDHARVA + "\n" + VERSE1, "[Gandharva Veda]\n" + VERSE1, ""):
            self.assertEqual(tf.strip_banner_head(s), s)

    def test_a_chapter_heading_after_the_banner_is_kept(self):
        s = "MAHARISHI UNIVERSITY OF MANAGEMENT\nVEDIC LITERATURE COLLECTION\n%s\n%s" % (ATHA, VERSE1)
        self.assertEqual(tf.strip_banner_head(s), ATHA + "\n" + VERSE1)

    def test_a_banner_in_the_middle_still_holds_it_back(self):
        s = VERSE1 + "\nVEDIC LITERATURE COLLECTION\n" + VERSE2
        self.assertEqual(tf.strip_banner_head(s), s)
        self.assertFalse(tf.should_translate(s))   # as before: a banner inside a passage is not a head

    def test_a_gretil_header_line(self):
        s = "GRETIL e-text\n" + VERSE1
        self.assertEqual(tf.strip_banner_head(s), VERSE1)
        self.assertTrue(tf.should_translate(s))

    def test_at_most_ten_lines_and_never_the_last(self):
        s = "\n".join(["VEDIC LITERATURE COLLECTION"] * 12 + [VERSE1])
        self.assertEqual(tf.strip_banner_head(s), s)

    def test_the_marker(self):
        self.assertIn(b"BANNER_HEAD_2026_11_13", (REPO / "scripts" / "text_filters.py").read_bytes())


class TheDesk(unittest.TestCase):
    def test_a_done_text_offers_its_scholarly_english(self):
        say = td.next_step("done", {"path": "done", "next": []}, {}, 976)
        self.assertIn("scholarly English", say)
        self.assertIn("not begun", say)
        self.assertIn("976 verses, about $25 to $44", say)
        self.assertIn("plan the first 250 (free)", say)

    def test_a_short_text(self):
        self.assertIn("plan the first 40 (free)", td.next_step("done", {"path": "done", "next": []}, {}, 40))

    def test_as_before_otherwise(self):
        self.assertEqual(td.next_step("done", {"path": "done", "next": []}, {}, 0), "nothing to do")
        self.assertEqual(td.next_step("done", {"path": "done", "next": ["python scripts\\x.py"]}, {}, 976),
                         "python scripts\\x.py")
        self.assertTrue(td.next_step("edition", {}, {"verses": 10}, 976).startswith("the scholarly English: plan"))

    def test_a_press_stays_under_the_cap(self):
        self.assertLessEqual(td.SCHOLAR_PRESS * max(td.SCHOLAR_PER_VERSE), td.MAX_USD)
        self.assertLessEqual(td.SCHOLAR_PRESS, td.MAX_VERSES)

    def test_the_dashboard_begins_a_new_text_with_a_press(self):
        src = (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('getattr(td, "SCHOLAR_PRESS", td.STEP_VERSES)),   # DESK_SCHOLAR_NEXT_2026_11_13', src)


PAT = REPO / "scripts" / "patch_banner_head_2026_11_13.py"
FILES = ("scripts/text_filters.py", "scripts/translation_desk.py", "scripts/dashboard.py",
         "tests/test_leak_guard_2026_10_19.py")


@unittest.skipUnless(PAT.exists(), "patch_banner_head_2026_11_13.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_bannerhead_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if b"BANNER_HEAD_2026_11_13" in srcb or b"DESK_SCHOLAR_NEXT_2026_11_13" in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 4 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
