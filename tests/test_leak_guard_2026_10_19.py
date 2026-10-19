# -*- coding: ascii -*-
"""LEAK_GUARD_2026_10_19 and KEEP_ON_EMPTY_2026_10_19.

The guard (text_filters.model_chatter / strip_model_chatter) on the 14 cases found on 19 Oct and on the Sanskrit's own
words that look like them; translate_passages.py (run on a temp database with the echo engine, answers served from
mt_cache as on the PC): a re-translation that comes back empty keeps the English it had; an answer with a preamble or a
second version keeps only the translation, the old one archived; English or Hindi that is the model reasoning is
archived and taken away; infer_mt never caches the model's words. Temp files only; nothing is called."""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

MARK = b"LEAK_GUARD_2026_10_19"
APPLIED = MARK in (SCRIPTS / "text_filters.py").read_bytes() and MARK in (SCRIPTS / "translate_passages.py").read_bytes()

A = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d"
     "\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d"
     "\u0938\u0935\u0903 \u0965")
B = ("\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 "
     "\u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u091e\u094d\u091c\u092f \u0965")
C = ("\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928"
     "\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938"
     "\u094d\u0924\u0926\u093e \u0965")

CHATTER = [   # (as stored on the PC, shortened; what the guard keeps; what is left that talks to us)
    ("Here is the translation of the verse, adhering to your specified principles:\n\nThe Rbhu, worthy of praise. //",
     "The Rbhu, worthy of praise. //", ""),
    ("Okay, here is the translation of the verse, applying your principles:\n\nTo the god, the perceiver of thoughts. //",
     "To the god, the perceiver of thoughts. //", ""),
    ("The following is the English translation of the provided Sanskrit verses, adhering to the specified principles:"
     "\n\nIndeed, all the gods move together for Manu. //", "Indeed, all the gods move together for Manu. //", ""),
    ("Let's translate the legible verses according to the specified principles.\n\nThere are four bones. //",
     "There are four bones. //", ""),
    ("Without performing sinful action, a person remains... //\n\nLet me give a cleaner rendering:\n\nWhatever suffering"
     " a person obtains, he remains. //", "Whatever suffering a person obtains, he remains. //", ""),
    ("By strength and skill. //\n\nFinal rendering:\n\nWhen the opponent has been thrown down, victory is won. //",
     "When the opponent has been thrown down, victory is won. //", ""),
    ("In the ecliptic circle. //\n\nNote: the text reads *drkksepa*, and I have rendered it as it stands.\n\nCorrection"
     " to the above, giving only the translation:\n\nIn the ecliptic circle this is the greatest interval. //",
     "In the ecliptic circle this is the greatest interval. //", ""),
    ("pepper. This is a medicinal drink.\n    I will translate `dagdham` as \"milk\" and note it.", None,
     "I will translate `"),
    ("    *   `vidhijna` - one who knows the rules. Let's re-examine the reading.", None, "Let's re-examine"),
]
SANSKRIT_OWN = [
    "This protector is honored. Let this be blameworthy, and let me be suffering. //",
    "Certainly, O son, neither any Ksatriyas nor the seven worlds defile ours. //",
    "I shall certainly undertake the performance of the marriage according to the rules. //",
    "Or if you consider this Raksasa a burden in battle, I will provide you assistance. //",
    "Let me reconsider, O king, what you have said. //",
    "Following the instructions of his teacher, he went to the forest.\n\nThere he dwelt. //",
    "The commentary: the translation of a word is its meaning in another tongue. //",
]


@unittest.skipUnless(APPLIED, "LEAK_GUARD_2026_10_19 is not applied here")
class TheGuard(unittest.TestCase):
    def test_what_the_model_said_to_us(self):
        import text_filters as tf
        for raw, keep, left in CHATTER:
            self.assertTrue(tf.model_chatter(raw), raw[:40])
            t, what = tf.strip_model_chatter(raw)
            if keep is not None:
                self.assertEqual(t, keep, raw[:40]); self.assertTrue(what)
            self.assertEqual(tf.model_chatter(t)[:len(left)], left, raw[:40])

    def test_the_sanskrits_own_words_are_left_alone(self):
        import text_filters as tf
        for t in SANSKRIT_OWN:
            self.assertEqual(tf.model_chatter(t), "", t)
            self.assertEqual(tf.strip_model_chatter(t), (t, ""), t)
        self.assertEqual(tf.strip_model_chatter(""), ("", ""))

    def test_it_is_never_cached(self):
        import infer_mt, db_utils
        with tempfile.TemporaryDirectory() as td:
            con = sqlite3.connect(str(Path(td) / "c.db"))
            db_utils.ensure_schema(con)
            infer_mt._cache_insert_many(con, "echo", "sa", "en", [
                (A, "Here is the translation of the verse, adhering to your specified principles:\n\nX. //"),
                (B, "The kings, eager to fight. //")])
            self.assertEqual([r[0] for r in con.execute("SELECT output FROM mt_cache")], ["The kings, eager to fight. //"])
            con.close()


@unittest.skipUnless(APPLIED, "LEAK_GUARD_2026_10_19 is not applied here")
class TheWritePath(unittest.TestCase):
    def setUp(self):
        import db_utils, infer_mt
        from normalize_text import normalize_sanskrit
        from text_filters import clean_for_mt
        self.tmp = Path(tempfile.mkdtemp(prefix="leak_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con); db_utils.migrate_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES ('Gita', 'epic')")
        did = con.execute("SELECT id FROM docs WHERE code='Gita'").fetchone()[0]
        self.ids = {}
        for idx, (text, en) in enumerate(((A, "The old English, judged wrong. //"),
                                          (B, "Here is the translation of the verse, adhering to your specified "
                                              "principles:\n\nMine and the sons of Pandu, what did they do? //"),
                                          (C, "Seeing the army. This is a drink.\n    I will translate `vyudham` as "
                                              "\"arrayed\". No, wait.")), 1):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type, quality_score, engine) "
                        "VALUES (?, 1, ?, ?, ?, 'mula', 0.9, 'echo')", (did, idx, text, en))
            self.ids[idx] = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        key = lambda t, lang: infer_mt._hash(clean_for_mt(normalize_sanskrit(t)), lang)
        for text in (B, C):   # the PC's mt_cache holds the answer that was stored
            out = con.execute("SELECT translation FROM passages WHERE text=?", (text,)).fetchone()[0]
            con.execute("INSERT INTO mt_cache(engine, lang_in, lang_out, text_hash, text, output) VALUES "
                        "('echo','sa','en',?,?,?)", (key(text, "en"), clean_for_mt(normalize_sanskrit(text)), out))
        hi = "Let's refine the translation of this word.\n    If it is a noun, then ..."
        con.execute("INSERT INTO translations_l10n(passage_id, lang, translation, engine) VALUES (?, 'hi', ?, 'echo')",
                    (self.ids[1], hi))
        con.execute("INSERT INTO mt_cache(engine, lang_in, lang_out, text_hash, text, output) VALUES "
                    "('echo','sa','hi',?,?,?)", (key(A, "hi"), clean_for_mt(normalize_sanskrit(A)), hi))
        con.commit(); con.close()
        (self.tmp / "verdicts.jsonl").write_text("", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_one(self, idx, lang="en"):
        args = [sys.executable, str(SCRIPTS / "translate_passages.py"), "--db", self.db, "--doc", "Gita",
                "--only-page", "1", "--only-idx", str(idx), "--retranslate", "--min-quality", "0", "--sleep", "0",
                "--lang", lang, "--engine", "echo", "--progress", str(self.tmp / "p.json"),
                "--config", str(self.tmp / "c.json")]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_SOURCE_VERDICTS=str(self.tmp / "verdicts.jsonl"))
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", cwd=str(REPO), env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def row(self, idx):
        con = sqlite3.connect(self.db)
        try:
            en = con.execute("SELECT translation FROM passages WHERE id=?", (self.ids[idx],)).fetchone()[0]
            hist = con.execute("SELECT translation, reason, coalesce(lang, 'en') FROM translation_history WHERE passage_id=? "
                               "ORDER BY id", (self.ids[idx],)).fetchall()
            hi = con.execute("SELECT translation FROM translations_l10n WHERE passage_id=? AND lang='hi'",
                             (self.ids[idx],)).fetchall()
            return en, hist, hi
        finally:
            con.close()

    def test_an_empty_attempt_keeps_the_english(self):
        out = self.run_one(1)   # the echo engine answers with the source: an echo, so nothing
        self.assertIn("[KEPT] p1.1", out)
        en, hist, _hi = self.row(1)
        self.assertEqual(en, "The old English, judged wrong. //")
        self.assertEqual(hist, [], "nothing replaced, nothing archived")

    def test_a_preamble_is_dropped_and_the_old_answer_archived(self):
        out = self.run_one(2)
        self.assertIn("[UNCHATTER] p1.2: dropped the model's preamble", out)
        en, hist, _hi = self.row(2)
        self.assertEqual(en, "Mine and the sons of Pandu, what did they do? //")
        self.assertEqual(len(hist), 1)
        self.assertTrue(hist[0][0].startswith("Here is the translation"))
        self.assertEqual(hist[0][1], "retranslate-overwrite")

    def test_reasoning_is_archived_and_taken_away(self):
        out = self.run_one(3)
        self.assertIn("[SKIP-CHATTER] p1.3", out)
        self.assertIn("[DROPPED] p1.3", out)
        en, hist, _hi = self.row(3)
        self.assertEqual(en, "")
        self.assertEqual([(h[1], h[2]) for h in hist], [("chatter-dropped", "en")])
        self.assertIn("I will translate", hist[0][0])

    def test_hindi_reasoning_is_archived_and_taken_away(self):
        out = self.run_one(1, "hi")
        self.assertIn("[DROPPED] p1.1: its hi was the model's words", out)
        _en, hist, hi = self.row(1)
        self.assertEqual(hi, [])
        self.assertEqual([(h[1], h[2]) for h in hist], [("chatter-dropped", "hi")])


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/text_filters.py", "scripts/translate_passages.py", "scripts/infer_mt.py",
             "tests/test_claude_first_2026_10_15.py", "tests/test_scholar_2026_10_14.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_leakguard_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_leakguard_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_leak_guard_2026_10_19.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "infer_mt.py"
            p.write_bytes(p.read_bytes().replace(b"continue  # never cache source-echoes (2026-08-02)", b"continue"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("infer_mt.py: anchor 2 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, (t / "scripts" / "text_filters.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_leak_guard_2026_10_19.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)


if __name__ == "__main__":
    unittest.main()
