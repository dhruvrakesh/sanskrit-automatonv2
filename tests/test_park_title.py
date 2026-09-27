# -*- coding: ascii -*-
"""PARK_ILLEGIBLE_2026_09_27 + PUBLISH_TITLE2_2026_09_27.
Run from the repo root:  python -m unittest tests.test_park_title -v
No network, no API key, never touches data/context.db (temp files only)."""
import json, os, sqlite3, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import text_filters as tf

HI_TOKEN = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
SRC = "\u0930\u093e\u092e\u094b \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f \u0965"
LATE = "2026-09-27T09:40:00+00:00"
EARLY = "2026-09-27T06:00:00+00:00"


def rec(pid=1, lang="en", cause="refusal-filter", raw="[ILLEGIBLE] //", src=SRC, ts=LATE, prompt=None):
    r = {"doc": "D", "lang": lang, "passage_id": pid, "page": 1, "idx": 1, "quality": 0.7,
         "cause": cause, "raw": raw, "source": src, "ts": ts}
    if prompt is not None:
        r["prompt"] = prompt
    return r


def write_ledger(path, recs):
    with open(path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


class BareIllegible(unittest.TestCase):
    def test_bare(self):
        for s in ("[ILLEGIBLE]", "[ILLEGIBLE] //", "[ILLEGIBLE]\n[ILLEGIBLE] // 8",
                  "[ILLEGIBLE] 12 //", HI_TOKEN + " \u0965", HI_TOKEN + " \u0967\u0968 //"):
            self.assertTrue(tf.is_bare_illegible(s), repr(s))

    def test_not_bare(self):
        for s in ("", None, "//", "Rama [ILLEGIBLE] goes. //", "[ILLEGIBLE] medicine, O Harita. // 8",
                  "I cannot read this.", "\u0930\u093e\u092e [ILLEGIBLE]"):
            self.assertFalse(tf.is_bare_illegible(s), repr(s))


class LoadParked(unittest.TestCase):
    def setUp(self):
        self.p = Path(tempfile.mkdtemp()) / "translate_outcomes.jsonl"

    def parked(self, recs, lang="en", prompt="v3-2026-09-27", n=2):
        write_ledger(self.p, recs)
        return tf.load_parked(self.p, lang, prompt, n)

    def test_two_bare_answers_park(self):
        self.assertEqual(self.parked([rec(), rec()]), {(1, SRC): 2})

    def test_one_answer_does_not_park(self):
        self.assertEqual(self.parked([rec()]), {})

    def test_other_prompt_or_old_legacy_does_not_count(self):
        self.assertEqual(self.parked([rec(prompt="v2"), rec(prompt="v2")]), {})
        self.assertEqual(self.parked([rec(ts=EARLY), rec(ts=EARLY)]), {})
        self.assertEqual(self.parked([rec(prompt="v3-2026-09-27"), rec()]), {(1, SRC): 2})

    def test_changed_source_unparks(self):
        self.assertEqual(self.parked([rec(), rec(src=SRC + " x")]), {})

    def test_other_causes_and_langs_ignored(self):
        self.assertEqual(self.parked([rec(cause="echo-filter"), rec(cause="echo-filter")]), {})
        self.assertEqual(self.parked([rec(raw="Rama [ILLEGIBLE] goes."), rec(raw="Rama [ILLEGIBLE] goes.")]), {})
        self.assertEqual(self.parked([rec(), rec()], lang="hi", prompt="hi-v3-2026-09-27"), {})

    def test_missing_or_broken_ledger(self):
        self.assertEqual(tf.load_parked(self.p.parent / "nope.jsonl", "en", "v3", 2), {})
        self.p.write_text('{"bad json\n' + json.dumps(rec()) + "\n" + json.dumps(rec()) + "\n", encoding="utf-8")
        self.assertEqual(tf.load_parked(self.p, "en", "v3-2026-09-27", 2), {(1, SRC): 2})


class TranslateRunParks(unittest.TestCase):
    """End to end: translate_passages with the model stubbed to answer '[ILLEGIBLE] //'.
    Run 1 and 2 ask (and log with a prompt field); run 3 parks; --retry-illegible asks."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        self.db = self.tmp / "data" / "context.db"
        import db_utils
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con)
        db_utils.migrate_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES ('T_doc', 'bhakti')")
        did = con.execute("SELECT id FROM docs WHERE code='T_doc'").fetchone()[0]
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, quality_score) VALUES (?,?,?,?,?)",
                    (did, 1, 1, SRC, 0.8))
        con.commit(); con.close()
        self.calls = 0

    def run_tp(self, *extra):
        import translate_passages as tp
        def fake(*a, **k):
            self.calls += 1
            return ["[ILLEGIBLE] //"]
        tp.translate_batch = fake
        old = sys.argv
        sys.argv = ["translate_passages.py", "--db", str(self.db), "--doc", "T_doc", "--sleep", "0",
                    "--progress", str(self.tmp / "data" / "translation_progress.json"),
                    "--config", str(self.tmp / "data" / "translation_config.json")] + list(extra)
        try:
            tp.main()
        finally:
            sys.argv = old

    def test_parks_after_two(self):
        self.run_tp(); self.run_tp()
        self.assertEqual(self.calls, 2)
        led = [json.loads(l) for l in open(self.tmp / "data" / "translate_outcomes.jsonl", encoding="utf-8")]
        self.assertEqual([r["cause"] for r in led], ["refusal-filter"] * 2)
        self.assertTrue(all(r.get("prompt") == "v3-2026-09-27" for r in led))
        self.run_tp()
        self.assertEqual(self.calls, 2, "third run must not pay for the same answer")
        self.run_tp("--retry-illegible")
        self.assertEqual(self.calls, 3)
        con = sqlite3.connect(self.db)
        self.assertEqual(con.execute("SELECT COALESCE(translation,'') FROM passages").fetchone()[0], "")
        con.close()


class Title(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = os.environ.get("BOOKSMITH_ROOT")
        os.environ["BOOKSMITH_ROOT"] = str(self.tmp / "bs")
        import publish_srangam
        self.ps = publish_srangam

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BOOKSMITH_ROOT", None)
        else:
            os.environ["BOOKSMITH_ROOT"] = self.old

    def book(self, slug, title):
        d = self.tmp / "bs" / "projects" / slug
        d.mkdir(parents=True)
        (d / "book.yaml").write_text("schema_version: '1.0'\ntitle: %s\nsubtitle: x\n" % title, encoding="utf-8")

    def test_camelcase_split(self):
        self.assertEqual(self.ps.doc_title("AphorismsOfSandilya"), "Aphorisms Of Sandilya")
        self.assertEqual(self.ps.doc_title("2015_405693_Shatpath-Brahmanam"), "Shatpath Brahmanam")
        self.assertEqual(self.ps.doc_title("markandeya_purana"), "Markandeya Purana")

    def test_resolution_order(self):
        title = "\u015a\u0101\u1e47\u1e0dilya Bhakti S\u016btra"
        self.book("aphorismsofsandilya", title)
        self.assertEqual(self.ps.resolve_title("AphorismsOfSandilya"), (title, "book.yaml"))
        self.assertEqual(self.ps.resolve_title("AphorismsOfSandilya", "X"), ("X", "--title"))
        self.book("2015-405693-shatpath-brahmanam", "2015 405693 Shatpath Brahmanam")
        self.assertEqual(self.ps.resolve_title("2015_405693_Shatpath-Brahmanam"),
                         ("Shatpath Brahmanam", "derived"))
        self.book("q-doc", "'It''s quoted'")
        self.assertEqual(self.ps.resolve_title("Q_doc")[0], "It's quoted")

    def _emit(self, *argv):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_publish_bridge import fixture
        if not (self.tmp / "c.db").exists():
            fixture(self.tmp / "c.db")
        old = sys.argv
        sys.argv = ["publish_srangam.py", "--db", str(self.tmp / "c.db"), "--doc", "T_doc",
                    "--emit-sql", str(self.tmp / "sql")] + list(argv)
        try:
            self.ps.main()
        finally:
            sys.argv = old
        return (self.tmp / "sql" / "T_doc" / "00_text.sql").read_text(encoding="utf-8")

    def test_site_title_kept_unless_override(self):
        self.book("t-doc", "The Test Book")
        t = self._emit()
        self.assertIn("'T_doc', 'The Test Book', 'bhakti'", t)
        self.assertIn("ON CONFLICT (doc_code) DO UPDATE SET category = EXCLUDED.category", t)
        self.assertNotIn("title = EXCLUDED.title", t)
        man = (self.tmp / "sql" / "T_doc" / "MANIFEST.txt").read_text(encoding="utf-8")
        self.assertIn("title: The Test Book  (from book.yaml", man)
        t2 = self._emit("--title", "Chosen")
        self.assertIn("'T_doc', 'Chosen', 'bhakti'", t2)
        self.assertIn("DO UPDATE SET title = EXCLUDED.title, category", t2)


class PlannerSkipsParked(unittest.TestCase):
    def test_plan(self):
        tmp = Path(tempfile.mkdtemp())
        db = tmp / "context.db"
        import db_utils
        con = sqlite3.connect(db)
        db_utils.ensure_schema(con); db_utils.migrate_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES ('T_doc', 'bhakti')")
        did = con.execute("SELECT id FROM docs").fetchone()[0]
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, quality_score) VALUES (?,1,1,?,0.8)", (did, SRC))
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, quality_score, translation) "
                    "VALUES (?,1,2,?,0.8,'Rama goes. //')", (did, SRC + " \u0930\u093e\u092e\u0903"))
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, quality_score) VALUES (?,1,0,?,0.8)",
                    (did, "\u0938\u0940\u0924\u093e \u0917\u091a\u094d\u091b\u0924\u093f \u0965"))
        pid = con.execute("SELECT id FROM passages WHERE idx=1").fetchone()[0]
        con.commit(); con.close()
        import plan_empty_retries as pe
        from normalize_text import normalize_sanskrit
        src = tf.clean_for_mt(normalize_sanskrit(SRC))
        def run(*extra):
            out = tmp / "plan.json"
            old = sys.argv
            sys.argv = ["plan_empty_retries.py", "--db", str(db), "--out", str(out), "--langs", "en"] + list(extra)
            try:
                pe.main()
            finally:
                sys.argv = old
            return json.loads(out.read_text(encoding="utf-8"))
        before = run()
        self.assertEqual(sum(x["verses"] for x in before["plan"]), 2)   # idx 0 and idx 1
        write_ledger(tmp / "translate_outcomes.jsonl", [rec(pid=pid, src=src), rec(pid=pid, src=src)])
        after = run()
        self.assertEqual(sum(x["verses"] for x in after["plan"]), 1)
        self.assertEqual(after["parked"], {"T_doc|en": 1})
        self.assertEqual(sum(x["verses"] for x in run("--include-parked")["plan"]), 2)


if __name__ == "__main__":
    unittest.main()
