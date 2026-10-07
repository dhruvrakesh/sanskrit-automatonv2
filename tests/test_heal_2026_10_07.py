# -*- coding: ascii -*-
"""Heal set of 2026-10-07 (afternoon):
  BRAIN_ENV       brain_items.py loads the repo .env (a CLI / maintenance run said "GEMINI_API_KEY not set")
  STORY_RECHECK   stories.py verify-all and POST /api/stories/verify-all re-run stale checks, approve nothing
  GAPS2           corpus_status counts the rows translate_passages never sends as gaps, not as work
No network."""
import importlib, json, shutil, sqlite3, subprocess, sys, tempfile, types, unittest, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_story_books_2026_10_07 import _fixture   # noqa: E402

SA = ("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915"
      "\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941"
      "\u0924\u094d\u0938\u0935\u0903")
HI = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u092e\u0947\u0902"
EN_VER, HI_VER = "v3-2026-09-27", "hi-file-abc"


class BrainEnv(unittest.TestCase):
    def test_brain_items_loads_the_env_file(self):
        called = []
        fake = types.ModuleType("env_loader")
        fake.load_env = lambda: called.append(1)
        saved = sys.modules.get("env_loader")
        sys.modules["env_loader"] = fake
        try:
            import brain_items
            importlib.reload(brain_items)
        finally:
            if saved is None:
                sys.modules.pop("env_loader", None)
            else:
                sys.modules["env_loader"] = saved
        self.assertTrue(called, "brain_items must call env_loader.load_env() at import")


class Recheck(unittest.TestCase):
    def setUp(self):
        import stories
        importlib.reload(stories)
        self.s = stories
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        con = sqlite3.connect(self.db)
        stale = json.dumps({"ok": False, "problems": ["names not found in the cited passages: Later"], "words": 150})
        con.execute("UPDATE doc_stories SET verify=? WHERE id IN (2, 3)", (stale,))   # written before the fix
        con.execute("UPDATE doc_stories SET story_en=story_en || ' Then Mrnjiga flew away with them to Lanka.' "
                    "WHERE id=3")                                                     # a real problem
        con.commit(); con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_verify_all_updates_stale_results_and_approves_nothing(self):
        con = sqlite3.connect(self.db)
        r = self.s.verify_all(con, "M")
        self.assertEqual((r["checked"], r["ok"], r["failed"]), (3, 2, 1))
        self.assertEqual(r["now_ok"], [2])
        self.assertEqual([i for i, _p in r["still_failing"]], [3])
        st = dict(con.execute("SELECT id, status FROM doc_stories").fetchall())
        self.assertEqual(st[2], "draft", "re-checking approves nothing")
        self.assertTrue(json.loads(con.execute("SELECT verify FROM doc_stories WHERE id=2").fetchone()[0])["ok"])
        con.close()

    def test_cli_and_route(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "stories.py"), "--db", self.db, "verify-all", "--doc", "M"],
                           capture_output=True, text=True, encoding="utf-8", timeout=60,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("now passing (read, then approve): #2", r.stdout)
        self.assertIn("still failing #3", r.stdout)
        import stories_web
        importlib.reload(stories_web)
        tmp = Path(tempfile.mkdtemp(prefix="heal_"))
        try:
            (tmp / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts" / "stories_static.html", tmp / "scripts" / "stories_static.html")
            from flask import Flask
            app = Flask("t")
            stories_web.register(app, launch=lambda *a, **k: "j", root=tmp, py=lambda *a: list(a),
                                 script=lambda n: n, db=self.db)
            c = app.test_client()
            res = c.post("/api/stories/verify-all", json={"doc": "M"}).get_json()
            self.assertEqual((res["checked"], res["failed"]), (3, 1))
            self.assertEqual(c.post("/api/stories/verify-all", json={"doc": "x;y"}).status_code, 400)
            page = c.get("/stories"); h = page.data.decode("utf-8"); page.close()
            for k in ("Check all again", "draft-ok", "data-go", "nextStep"):
                self.assertIn(k, h)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class NeverSent(unittest.TestCase):
    """60 passages, all translated except one whose printed text has no translatable Sanskrit (a lone danda)
    and one on page 0: translate_passages skips both silently, so they are gaps, not work."""
    def setUp(self):
        import corpus_status, db_utils
        importlib.reload(corpus_status)
        self.cs = corpus_status
        self._cv = corpus_status.current_versions
        corpus_status.current_versions = lambda: (EN_VER, HI_VER, "test")
        self.tmp = Path(tempfile.mkdtemp(prefix="never_"))
        self.db = str(self.tmp / "context.db")
        con = sqlite3.connect(self.db); db_utils.ensure_schema(con)
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
        con.execute("CREATE TABLE usage_log(kind TEXT, cost_usd REAL, passages INTEGER, ok INTEGER)")
        con.execute("INSERT INTO usage_log VALUES('translation', 1.0, 1000, 1)")
        con.execute("INSERT INTO docs(code, category) VALUES('Never', 'purana')")
        for i in range(60):
            page, text, done = 1 + i // 4, SA, True
            if i == 5:
                text, done = "\u0964", False             # a lone danda: should_translate() refuses it
            if i == 6:
                page, done = 0, False                    # page 0 is never selected (--since-page 1)
            cur = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation,mt_prompt_version,"
                              "translated_at,ocr_engine,quality_score) VALUES(1,?,?,?,'mula',?,?,?,?,0.9)",
                              (page, i % 4, text, "fine" if done else "", EN_VER if done else None,
                               "2026-10-01T00:00:00", "gemini-vision:x"))
            if done:
                con.execute("INSERT INTO translations_l10n(passage_id,lang,translation,mt_prompt_version,translated_at) "
                            "VALUES(?,?,?,?,?)", (cur.lastrowid, "hi", HI, HI_VER + "+noref", "2026-10-02T00:00:00"))
        con.commit(); con.close()

    def tearDown(self):
        self.cs.current_versions = self._cv
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_never_sent_rows_are_gaps(self):
        st, _, _, cpp = self.cs.collect(self.db, None, self.tmp / "raw", self.tmp / "rv", self.tmp / "rm",
                                        self.tmp / "inbox", False, 20)
        s = st[0]
        s["verdict"], s["reasons"], s["commands"] = self.cs.verdict(s, 5.0, 5.0, cpp, {})
        self.assertEqual((s["en_gap"], s["en_gap_never"], s["hi_gap"], s["hi_gap_never"]), (2, 2, 2, 2))
        self.assertEqual(s["verdict"], "CURRENT", s["reasons"])
        self.assertTrue(any("2 never sent" in r for r in s["reasons"]), s["reasons"])


if __name__ == "__main__":
    unittest.main()
