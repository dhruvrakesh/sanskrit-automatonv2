# -*- coding: ascii -*-
"""HEAL_ENGLISH_2026_10_19: heal_english.py finds the English a T2 run emptied (its log says failed, the passage has no
English, mt_cache still holds the old answer) and the translations that hold the model's words to us, plans them for
free, and with --yes mends each through translate_passages.py (the echo engine; every answer served from mt_cache as on
the PC): the lost English back, a preamble dropped, reasoning archived and emptied, a Hindi row of reasoning taken away.
The plan writes nothing. Temp files only; nothing is called."""
import hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "heal_english.py"
MARK = b"HEAL_ENGLISH_2026_10_19"
READY = TOOL.exists() and b"LEAK_GUARD_2026_10_19" in (SCRIPTS / "translate_passages.py").read_bytes()

A = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d"
     "\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d"
     "\u0938\u0935\u0903 \u0965")
B = ("\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 "
     "\u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u091e\u094d\u091c\u092f \u0965")
C = ("\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928"
     "\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938"
     "\u094d\u0924\u0926\u093e \u0965")
OLD = "On the field of dharma, at Kuruksetra, gathered and eager to fight. //"
PRE = "Here is the translation of the verse, adhering to your specified principles:\n\nMine and the sons of Pandu. //"
WHY = "Seeing the army.\n    I will translate `vyudham` as \"arrayed\". No, wait."
HI = "Let's refine the translation of this word.\n    If it is a noun, then ..."


@unittest.skipUnless(READY, "HEAL_ENGLISH_2026_10_19 or LEAK_GUARD_2026_10_19 is not here")
class TheHealer(unittest.TestCase):
    def setUp(self):
        import db_utils, infer_mt
        from normalize_text import normalize_sanskrit
        from text_filters import clean_for_mt
        self.tmp = Path(tempfile.mkdtemp(prefix="heal_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con); db_utils.migrate_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES ('Gita', 'epic')")
        did = con.execute("SELECT id FROM docs WHERE code='Gita'").fetchone()[0]
        self.ids = {}
        for idx, (text, en) in enumerate(((A, ""), (B, PRE), (C, WHY)), 1):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, text_type, quality_score, engine) "
                        "VALUES (?, 1, ?, ?, ?, 'mula', 0.9, 'echo')", (did, idx, text, en))
            self.ids[idx] = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        put = lambda text, lang, out: con.execute(
            "INSERT INTO mt_cache(engine, lang_in, lang_out, text_hash, text, output) VALUES ('echo','sa',?,?,?,?)",
            (lang, infer_mt._hash(clean_for_mt(normalize_sanskrit(text)), lang), clean_for_mt(normalize_sanskrit(text)), out))
        put(A, "en", OLD); put(B, "en", PRE); put(C, "en", WHY); put(B, "hi", HI)
        con.execute("INSERT INTO translations_l10n(passage_id, lang, translation, engine) VALUES (?, 'hi', ?, 'echo')",
                    (self.ids[2], HI))
        con.commit(); con.close()
        self.logs = self.tmp / "retranslate"
        self.logs.mkdir()
        (self.logs / "20261018_192503_Gita.jsonl").write_text(
            json.dumps({"doc": "Gita", "passage_id": self.ids[1], "where": "1.1", "result": "failed", "rc": 0,
                        "old_english": OLD, "engine": "anthropic:claude-sonnet-5-5"}) + "\n", encoding="utf-8")
        (self.tmp / "verdicts.jsonl").write_text("", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_SOURCE_VERDICTS=str(self.tmp / "verdicts.jsonl"))
        r = subprocess.run([sys.executable, str(TOOL), "--db", self.db, "--log-dir", str(self.logs)] + list(args),
                           capture_output=True, text=True, encoding="utf-8", cwd=str(REPO), env=env)
        return r.returncode, r.stdout + r.stderr

    def state(self):
        con = sqlite3.connect(self.db)
        try:
            en = {i: con.execute("SELECT translation FROM passages WHERE id=?", (p,)).fetchone()[0] for i, p in self.ids.items()}
            hi = con.execute("SELECT count(*) FROM translations_l10n").fetchone()[0]
            hist = con.execute("SELECT passage_id, reason, coalesce(lang, 'en') FROM translation_history ORDER BY id").fetchall()
            return en, hi, hist
        finally:
            con.close()

    def test_the_plan_finds_them_and_writes_nothing(self):
        before = hashlib.md5(Path(self.db).read_bytes()).hexdigest()
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 4 to mend: 1 English a T2 run emptied; 3 translations with the model's words (1 kept "
                      "without them from the cache, 2 archived and emptied: nothing in them is a translation, 0 not in the "
                      "cache: a fresh translation with --fresh); 0 emptied earlier, waiting for a fresh translation", out)
        self.assertIn("its English back from the cache", out)
        self.assertIn("from the cache, keeps: 'Mine and the sons of Pandu. //'", out)
        import datetime
        self.assertIn("NEXT: python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_heal_%s.db ; "
                      "python scripts\\heal_english.py --yes ; then python scripts\\heal_english.py --yes --fresh   (2 "
                      "passage(s) by anthropic:claude-sonnet-5-5, about $0.01 each)" % datetime.date.today().strftime("%Y%m%d"),
                      out)
        self.assertEqual(hashlib.md5(Path(self.db).read_bytes()).hexdigest(), before)

    def test_yes_mends_each_through_the_translator(self):
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 2 mended, 2 emptied (archived; nothing in them was a translation), 0 failed", out)
        en, hi, hist = self.state()
        self.assertEqual(en[1], OLD, "the English the T2 run emptied, back")
        self.assertEqual(en[2], "Mine and the sons of Pandu. //", "the preamble dropped")
        self.assertEqual(en[3], "", "reasoning, not a translation")
        self.assertEqual(hi, 0, "the Hindi of reasoning taken away")
        self.assertIn((self.ids[2], "retranslate-overwrite", "en"), hist)
        self.assertIn((self.ids[3], "chatter-dropped", "en"), hist)
        self.assertIn((self.ids[2], "chatter-dropped", "hi"), hist)
        logs = sorted(self.logs.glob("heal_*.jsonl"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(logs[0].read_text(encoding="utf-8").splitlines()), 4)
        self.assertIn("NEXT: python scripts\\heal_english.py --yes --fresh   (2 passage(s) by anthropic:claude-sonnet-5-5, "
                      "about $0.01 each)", out)
        rc, out = self.run_tool()
        self.assertIn("VERDICT: 2 to mend: 0 English a T2 run emptied; 0 translations with the model's words (0 kept "
                      "without them from the cache, 0 archived and emptied: nothing in them is a translation, 0 not in the "
                      "cache: a fresh translation with --fresh); 2 emptied earlier, waiting for a fresh translation", out)
        self.assertIn("NEXT: python scripts\\heal_english.py --yes --fresh   (2 passage(s) by anthropic:claude-sonnet-5-5, "
                      "about $0.01 each)", out)
        rc, out = self.run_tool("--yes")
        self.assertIn("VERDICT: 0 mended, 0 emptied", out, "--yes alone asks no one")
        rc, out = self.run_tool("--yes", "--fresh", "--fresh-engine", "echo")   # the echo engine: still nothing to keep
        self.assertIn("VERDICT: 0 mended, 2 emptied (archived; nothing in them was a translation), 0 failed, 2 by echo", out)
        en, hi, _hist = self.state()
        self.assertEqual((en[1], en[2]), (OLD, "Mine and the sons of Pandu. //"), "the mended ones untouched")


class TheFiles(unittest.TestCase):
    def test_ascii_and_mark(self):
        for f in (TOOL, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)


if __name__ == "__main__":
    unittest.main()
