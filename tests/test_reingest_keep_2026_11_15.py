# -*- coding: ascii -*-
"""REINGEST_KEEP_2026_11_15. Asked on 15 Nov: "i am tired of wasting our APIs on translating works that you then make me
drop". A repaired page changed most of its sentences by a few letters, and each such sentence was deleted with its
English and Hindi (the Ganita Yuktibhasa: 1,838 English). With --keep a sentence whose letters were mended keeps its
row and its translations; what is left in the database is still what a full ingest of the repair makes. And the
benchmark's pick no longer says "repair it first" when the repair is made. Temp files only, never data/context.db."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO))
import reingest_pages as rp          # noqa: E402
import benchmark_sources as bs       # noqa: E402
from tests import test_reingest_2026_10_12 as T   # noqa: E402  (its fixture: a small database and its repaired pages)

A = T.W % (T.NAME["C2"], 2)
B = T.W % (T.NAME["Z7"], 2)          # the same verse, one word mended
OTHER = ("\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d \u0964 "
         "\u092f\u094b\u0917\u0936\u094d\u091a\u093f\u0924\u094d\u0924\u0935\u0943\u0924\u094d\u0924\u093f\u0928\u093f"
         "\u0930\u094b\u0927\u0903 \u0964 \u0924\u0926\u093e \u0926\u094d\u0930\u0937\u094d\u091f\u0941\u0903")
THR = 0.8


def row(i, text, tr=""):
    return {"id": i, "idx": i, "text": text, "translation": tr, "ocr_engine": None, "ocr_variants": None}


class ThePairs(unittest.TestCase):
    def test_the_same_sentence_mended_is_one_passage(self):
        got = rp.mend_pairs([row(1, A, "English")], [row(9, B)], THR)
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0][0]["id"], got[0][1]["id"]), (1, 9))
        self.assertGreaterEqual(got[0][2], THR)
        self.assertLess(got[0][2], 1.0)

    def test_another_sentence_is_not(self):
        self.assertEqual(rp.mend_pairs([row(1, OTHER)], [row(9, B)], THR), [])

    def test_a_short_passage_is_not_paired(self):
        short = "\u0907\u0924\u093f \u0964"
        self.assertEqual(rp.mend_pairs([row(1, short)], [row(9, short + " ")], THR), [])

    def test_each_passage_once_the_best_first(self):
        got = rp.mend_pairs([row(1, A), row(2, B + " \u0964")], [row(9, B)], THR)
        self.assertEqual([(o["id"], n["id"]) for o, n, _r in got], [(2, 9)])

    def test_the_plan_of_a_page(self):
        old, new = [row(1, A, "English"), row(2, OTHER)], [dict(row(1, B), idx=1)]
        plain = rp.plan_page(old, new)
        self.assertEqual((len(plain["gone"]), len(plain["insert"]), plain["mend"]), (2, 1, []))
        kept = rp.plan_page(old, new, THR)
        self.assertEqual((len(kept["gone"]), len(kept["insert"]), len(kept["mend"])), (1, 0, 1))
        self.assertEqual(kept["gone"][0]["id"], 2)


class TheKeep(T.Base):
    def test_the_plan_says_what_keep_would_keep(self):
        rc, out = self.tool()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("mended", self.last(out, "VERDICT"))
        rc, out = self.tool("--keep", str(THR))
        self.assertEqual(rc, 0, out)
        self.assertIn("mended 1", out)
        self.assertIn("1 mended in place keep their English and Hindi", self.last(out, "VERDICT"))
        self.assertIn("--keep %.2f --apply" % THR, self.last(out, "NEXT"))
        self.assertNotIn("--replace", self.last(out, "NEXT"))

    def test_a_mended_sentence_keeps_its_row_and_its_translations(self):
        before = self.ids[(4, 2)]
        rc, out = self.tool("--keep", str(THR), "--apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("mended in place: 1 passage(s) kept their English and Hindi", out)
        con = self.con()
        fresh, fdid = T.make_db(self.t / "fresh.db", {**T.NEW, 5: T.OLD[5]})
        try:   # closed before tearDown: Windows cannot delete a database that is still open (WinError 32, 15 Nov)
            self.assertEqual(T.rows(con, self.did), T.rows(fresh, fdid), "the passages a full ingest of the repair makes")
            cols = "page_no, idx, text, norm, iast, verse_ref, chapter, text_type, chandas, padas, quality_score, ocr_engine, ocr_variants"
            q = "SELECT %s FROM passages WHERE doc_id=? ORDER BY page_no, idx" % cols
            self.assertEqual(con.execute(q, (self.did,)).fetchall(), fresh.execute(q, (fdid,)).fetchall())
            self.assertEqual(T.pid(con, self.did, 4, 2), before, "the same row")
            self.assertEqual(con.execute("SELECT translation FROM passages WHERE id=?", (before,)).fetchone()[0], "English 4.2")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM translations_l10n WHERE passage_id=?", (before,)).fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM passage_embeddings WHERE passage_id=?", (before,)).fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM mt_reviews WHERE passage_id=?", (before,)).fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT anchor_idx FROM doc_images WHERE title='loses'").fetchone()[0], 2,
                             "its picture stays with it")
            text = con.execute("SELECT text FROM passages WHERE id=?", (before,)).fetchone()[0]
            self.assertIn(T.NAME["Z7"], text)
            fts = con.execute("SELECT name FROM sqlite_master WHERE name='passages_fts'").fetchone()
            if fts:
                self.assertEqual(con.execute("SELECT text, translation FROM passages_fts WHERE rowid=?", (before,)).fetchone(),
                                 (text, "English 4.2"))
            log = list((self.t / "reingest").glob("R_*.jsonl"))[0].read_text(encoding="utf-8").splitlines()
            mended = [j for j in (json.loads(l) for l in log) if "mended" in j]
            self.assertEqual(len(mended), 1)
            self.assertEqual(mended[0]["mended"], before)
            self.assertIn(T.NAME["C2"], mended[0]["text"], "the reading its translation was made from")
        finally:
            con.close()
            fresh.close()

    def test_without_keep_as_before(self):
        rc, out = self.tool("--apply")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE: this removes 1 English and 1 Hindi translations", out)
        self.assertIn("--keep   (1 of the 1 English translations stay with their sentences", out)

    def test_a_share_out_of_range_is_refused(self):
        rc, out = self.tool("--keep", "0.2")
        self.assertEqual(rc, 2)


OURS = {"label": "consensus", "kind": "ours", "pages": 339, "misread_letters_pct": 1.53, "level": "moderate"}
VISION = {"label": "vision", "kind": "ocr", "pages": 290}


class ThePick(unittest.TestCase):
    def test_the_repair_made_and_not_in_the_database(self):
        db = {"label": "database", "kind": "db", "f1_ours": 0.87}
        p = bs.pick_reading({"readings": [VISION, OURS, db]}, "Ganita")
        self.assertIn("vision has read 290 of its 339 pages: the repair is made", p["why"])
        self.assertIn("bring the repair in", p["why"])
        self.assertNotIn("repair it first", p["why"])
        self.assertIn("reingest_pages.py --doc Ganita --keep", p["then"])

    def test_the_repair_in_the_database(self):
        db = {"label": "database", "kind": "db", "f1_ours": 1.0}
        p = bs.pick_reading({"readings": [VISION, OURS, db]}, "Ganita")
        self.assertIn("ready for its scholarly English", p["why"])
        self.assertEqual(p["then"], "")

    def test_not_yet_read_by_vision_as_before(self):
        p = bs.pick_reading({"readings": [dict(VISION, pages=112), OURS]}, "Ganita")
        self.assertIn("repair it first", p["why"])
        self.assertIn("repair_text.py --doc Ganita", p["then"])

    def test_beside_another_recension(self):
        w = {"label": "witness gretil", "kind": "etext", "site": "gretil", "f1_ours": 0.31, "misread_letters_pct": 0.0}
        db = {"label": "database", "kind": "db", "f1_ours": 0.87}
        p = bs.pick_reading({"readings": [VISION, OURS, db, w]}, "x")
        self.assertIn("another recension", p["why"])
        self.assertIn("bring the repair in", p["why"])


PAT = REPO / "scripts" / "patch_reingest_keep_2026_11_15.py"
FILES = ("scripts/reingest_pages.py", "scripts/benchmark_sources.py", "tests/test_source_pick_2026_11_13.py",
         "tests/test_mbh_prose_2026_10_14.py")


@unittest.skipUnless(PAT.exists(), "patch_reingest_keep_2026_11_15.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_reingestkeep_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if b"REINGEST_KEEP_2026_11_15" in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(FILES), r.stdout, r.stdout + r.stderr)
            self.assertEqual(run().returncode, 0)
            for rel in FILES:
                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
