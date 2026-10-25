# -*- coding: ascii -*-
"""AUTO_TRANSLATE_2026_10_25: repair_auto.py's rounds look past the texts waiting on a decision or ready to translate
(the dry run of 25 Oct was "blocked" by five of them), remember them for the day, price a text ready to translate,
translate (English, then Hindi) only the texts opted in with --allow-translate and within their allowance, write down
a refusal (exit 3 or 4) once, ask for a spent allowance, leave a release to you, count the swaps a day and report the
pre-repair backups; health_watch.py says what is ready and warns of a spent allowance. The made-up data folder and
stand-in repair_text.py of test_auto_repair_2026_10_25, and a stand-in translate_passages.py: no model, no network."""
import datetime, json, os, sqlite3, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_auto_repair_2026_10_25 as T  # noqa: E402

APPLIED = b"AUTO_TRANSLATE_2026_10_25" in T.AUTO.read_bytes()

FAKE_TR = r'''
import json, os, sqlite3, sys
a = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps(["translate"] + a) + "\n")
rc = int(os.environ.get("FAKE_TR_RC") or 0)
if rc:
    print("REFUSED: 41% of the passages are scanner debris"); sys.exit(rc)
doc, n = a[a.index("--doc") + 1], int(a[a.index("--limit") + 1])
lang = a[a.index("--lang") + 1] if "--lang" in a else "en"
con = sqlite3.connect(os.environ["FAKE_DB"])
did = con.execute("SELECT id FROM docs WHERE code = ?", (doc,)).fetchone()[0]
if lang == "en":
    ids = [r[0] for r in con.execute("SELECT id FROM passages WHERE doc_id = ? AND COALESCE(translation, '') = '' "
                                     "ORDER BY id LIMIT ?", (did, n))]
    con.executemany("UPDATE passages SET translation = 'the English' WHERE id = ?", [(i,) for i in ids])
else:
    ids = [r[0] for r in con.execute("SELECT p.id FROM passages p WHERE p.doc_id = ? AND p.translation <> '' AND NOT "
                                     "EXISTS (SELECT 1 FROM translations_l10n l WHERE l.passage_id = p.id) ORDER BY id "
                                     "LIMIT ?", (did, n))]
    con.executemany("INSERT INTO translations_l10n (passage_id, lang, translation) VALUES (?, 'hi', 'the Hindi')",
                    [(i,) for i in ids])
con.execute("UPDATE budget_state SET spent_usd = spent_usd + 0.004 WHERE id = 1")
con.commit(); con.close()
print("translated %d passage(s) of %s (%s)" % (len(ids), doc, lang))
'''
READY = "translate it: Finish EN and Add Hindi in the Library (the translation cache answers unchanged passages at no cost)"


@unittest.skipUnless(APPLIED, "AUTO_TRANSLATE_2026_10_25 is not applied here")
class TheTranslations(T.Base):
    def setUp(self):
        super().setUp()
        (self.fake / "translate_passages.py").write_text(FAKE_TR, encoding="utf-8")
        con = sqlite3.connect(str(self.db))
        con.executescript("""
        CREATE TABLE docs (id INTEGER PRIMARY KEY, code TEXT);
        CREATE TABLE passages (id INTEGER PRIMARY KEY, doc_id INTEGER, translation TEXT, text_type TEXT);
        CREATE TABLE translations_l10n (passage_id INTEGER, lang TEXT, translation TEXT);
        """)
        docs = ["T1", "T2", "T3", "T4", "T5", "Y"]
        for i, d in enumerate(docs, 1):
            con.execute("INSERT INTO docs VALUES (?, ?)", (i, d))
            for k in range(6):
                con.execute("INSERT INTO passages (doc_id, translation, text_type) VALUES (?, '', ?)",
                            (i, "noise" if k == 5 else "mula"))   # a scanner's noise is never counted
        con.commit(); con.close()
        q = "python scripts\\repair_text.py --doc %s --use-repaired"
        nxt = json.loads(self.next.read_text(encoding="utf-8"))
        for d in docs[:5]:   # the morning's judgement: ready to go into the database; now: ready to translate
            T.judged(self.data, d, "material", q % d, vp=100)
            nxt[d] = READY
        self.next.write_text(json.dumps(nxt), encoding="utf-8")
        with open(self.data / "source_verdicts.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"doc": "Y", "status": "in_repair"}) + "\n")
        (self.t / "context_pre_repair_x_20261025_150138.db").write_bytes(b"x" * 1000)
        self.auto("--round")   # the day's judgement

    def tr_calls(self):
        return [c for c in self.calls_made() if c and c[0] == "translate"]

    def asks(self, kind):
        return [a for a in self.state()["asks"] if a["kind"] == kind]

    def test_ready_texts_are_not_tries_and_are_priced(self):
        rc, out = self.auto("--round")
        self.assertEqual(rc, 0, out)
        st = self.state()
        self.assertEqual((st["did"]["step"], st["did"]["doc"]), ("vision", "A"),
                         "five texts ready to translate do not fill the round's tries")
        ready = self.asks("translate")
        self.assertEqual(sorted(a["doc"] for a in ready), ["T1", "T2", "T3", "T4", "T5"])
        self.assertEqual((ready[0]["english"], ready[0]["hindi"]), (5, 5), "its Hindi too, after its English")
        self.assertAlmostEqual(ready[0]["usd"], 10 * 0.00048, places=4)
        self.assertIn("--allow-translate", ready[0]["say"])
        self.assertEqual(st["status"], "working")
        self.assertEqual(self.tr_calls(), [], "nothing is translated unless asked")
        self.assertEqual(st["backups"]["n"], 1)
        self.assertIn("pre-repair backup", out)
        looks = sum(1 for c in self.calls_made() if c[:1] == ["--doc"] and len(c) == 2)
        self.auto("--round")   # the same day, the same judgements: the five are not asked again
        self.assertEqual(sum(1 for c in self.calls_made() if c[:1] == ["--doc"] and len(c) == 2), looks + 2,
                         "only C and A again (A's vision, C's swap waiting on the dashboard)")
        h = T.load_health().check_repair(self.data / "auto_repair_state.json", datetime.datetime.now())
        self.assertEqual(h["state"], "ok")
        self.assertIn("ready to translate: T", h["say"])

    def test_opted_in_english_then_hindi_then_the_release_is_yours(self):
        rc, out = self.auto("--allow-translate", "Y", "--usd", "1.00")
        self.assertEqual(rc, 0, out)
        self.assertIn("up to $1.00 in all", out)
        self.assertIn("5 passage(s) to English and 0 to Hindi now", out)
        self.auto("--round")
        c = self.tr_calls()
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0][c[0].index("--doc") + 1], "Y")
        self.assertEqual(c[0][c[0].index("--engine") + 1], "gemini:gemini-2.5-flash")
        self.assertEqual(c[0][c[0].index("--limit") + 1], "5")
        self.assertNotIn("--lang", c[0])
        st = self.state()
        self.assertEqual(st["did_translate"]["lang"], "en")
        self.assertAlmostEqual(st["did_translate"]["spent"], 0.004, places=4)
        self.auto("--round")
        st = self.state()
        self.assertAlmostEqual(st["spent_today"], 0.03, places=4, msg="the repair's allowance does not pay for it")
        self.assertAlmostEqual(st["spent_translating_today"], 0.004, places=4)
        c = self.tr_calls()
        self.assertEqual(c[-1][c[-1].index("--lang") + 1], "hi")
        self.auto("--round")
        self.assertEqual(len(self.tr_calls()), 2, "done: nothing more")
        cfg = json.loads((self.data / "auto_repair.json").read_text(encoding="utf-8"))
        self.assertTrue(cfg["translate"]["Y"].get("done"))
        rel = [a for a in self.asks("decision") if a["doc"] == "Y"]
        self.assertTrue(rel and "--release" in rel[0]["say"], "a text in repair: its release stays yours")

    def test_a_refusal_is_written_once_and_an_allowance_spent_is_asked(self):
        self.auto("--allow-translate", "T1", "--usd", "1.00")
        self.env["FAKE_TR_RC"] = "3"
        self.auto("--round")
        self.assertEqual(len(self.tr_calls()), 1)
        self.assertTrue(any("debris guard" in a["say"] for a in self.asks("decision")))
        self.auto("--round")
        self.assertEqual(len(self.tr_calls()), 1, "not asked again until you allow it again")
        self.env.pop("FAKE_TR_RC")
        rc, out = self.auto("--allow-translate", "T1", "--usd", "0.01")
        self.auto("--round")
        self.assertEqual(len(self.tr_calls()), 1)
        al = self.asks("allowance")
        self.assertTrue(al and "--allow-translate T1 --usd" in al[0]["say"])
        h = T.load_health().check_repair(self.data / "auto_repair_state.json", datetime.datetime.now())
        self.assertEqual(h["state"], "warn")
        self.assertIn("allowance is spent", h["say"])

    def test_refused(self):
        rc, out = self.auto("--allow-translate", "Daivat-Sanhita", "--usd", "1")
        self.assertEqual(rc, 2); self.assertIn("never translated", out)
        rc, out = self.auto("--allow-translate", "E", "--usd", "1")
        self.assertEqual(rc, 2); self.assertIn("withdrawn", out)
        rc, out = self.auto("--allow-translate", "nothing_here", "--usd", "1")
        self.assertEqual(rc, 2); self.assertIn("no text nothing_here", out)
        rc, out = self.auto("--allow-translate", "T1", "--usd", "25")
        self.assertEqual(rc, 2)
        rc, out = self.auto("--allow-translate", "T1")
        self.assertEqual(rc, 2)

    def test_dry_run_says_both(self):
        self.auto("--allow-translate", "T2", "--usd", "1.00")
        rc, out = self.auto("--round", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: the round would run: ", out)
        self.assertIn("and would translate: ", out)
        self.assertEqual(self.tr_calls(), [])


if __name__ == "__main__":
    unittest.main()
