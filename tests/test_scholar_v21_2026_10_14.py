# -*- coding: ascii -*-
"""SCHOLAR_V21_2026_10_14: a sentence's passage is kept as the draft wrote it (its segments say which words render which
verse); a sentence whose draft fails goes verse by verse; an answer cut off at the token limit is asked again with room
and a failure says how it ended; scholar-v2.1 is priced by scholar-v2's rows until it has its own; the pages order the
rows by the passage's place now and show such a passage whole after its verse range; the importer counts the
appendix passages; the patcher. Temp files only; no model is called."""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base        # its fixture: MBh01 1.1.6-1.1.9
import test_scholar_v2_2026_10_14 as v2       # its Stub and args
import test_mbh_prose_2026_10_14 as mp        # its BOOK

ST = base.ST
ACCEPT = base.ACCEPT


class TheRun(unittest.TestCase):
    setUp = v2.TheRun.setUp
    tearDown = v2.TheRun.tearDown
    go = v2.TheRun.go

    def test_the_passage_is_kept_as_written(self):
        groups = {"groups": [["1.1.6"], ["1.1.7", "1.1.8"], ["1.1.9"]]}
        whole = "Janamejaya asked the s\u016bta: where do you come from, Sauti, and where have you been? //"
        seg = {"translation": whole,
               "segments": [{"ref": "1.1.7", "english": "where do you come from, Sauti, and where have you been?"},
                            {"ref": "1.1.8", "english": "Janamejaya asked the s\u016bta: //"}],
               "moved": "The speaker of 1.1.8 opens the sentence.", "notes": [], "glossary": [], "doubts": ""}
        stub = v2.Stub(drafts=[base.draft("Then a sage saw him seated, //"), seg, base.draft("The stories. //")],
                       critics=[ACCEPT] * 3, groups=[groups])
        res, rows = self.go(stub, compare=False)
        by = {r["verse_ref"]: r for r in rows}
        self.assertEqual(by["1.1.7"]["group_translation"], whole, "the passage, in the order English needs")
        self.assertEqual(by["1.1.7"]["translation"], "where do you come from, Sauti, and where have you been?")
        self.assertEqual(by["1.1.8"]["translation"], "Janamejaya asked the s\u016bta: //")
        self.assertEqual(by["1.1.7"]["moved"], "The speaker of 1.1.8 opens the sentence.")
        crit = [m for k, m in stub.msgs if k == "critic"][1]
        self.assertIn("THE DRAFT TRANSLATION:\n" + whole, crit, "the critic reads the passage, not the parts joined")
        self.assertEqual(by["1.1.7"]["prompt_version"], "scholar-v2.1+scholar-critic-v2")

    def test_a_passage_that_is_no_passage_gives_way_to_its_segments(self):
        u = ST.clean_unit({"translation": "x", "segments": [{"ref": "a", "english": "the first part,"},
                                                           {"ref": "b", "english": "the second. //"}]}, ["a", "b"])
        self.assertEqual(u["translation"], "the first part, the second. //")
        u = ST.clean_unit({"translation": "The second, then the first part. //",
                           "segments": [{"ref": "a", "english": "the first part,"}, {"ref": "b", "english": "the second. //"}]},
                          ["a", "b"])
        self.assertEqual(u["translation"], "The second, then the first part. //")
        self.assertEqual(u["segments"], {"a": "the first part,", "b": "the second. //"})

    def test_a_sentence_that_fails_goes_verse_by_verse(self):
        groups = {"groups": [["1.1.6", "1.1.7"], ["1.1.8"], ["1.1.9"]]}
        stub = v2.Stub(drafts=[None] + [base.draft("v%d //" % k) for k in range(4)], critics=[ACCEPT] * 4, groups=[groups])
        stub.last = {"kind": "draft", "finish": "MAX_TOKENS", "chars": 31204, "json": False}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            res, rows = self.go(stub, compare=False)
        self.assertIn("1.1.6 to 1.1.7: the sentence failed (the draft came back without a translation (it ended MAX_TOKENS, "
                      "31,204 characters, not JSON)); each verse alone", out.getvalue())
        self.assertEqual(res["split"], 1); self.assertEqual(res["failed"], [])
        self.assertEqual([(r["verse_ref"], r["group_ref"], r["translation"]) for r in rows],
                         [("1.1.6", None, "v0 //"), ("1.1.7", None, "v1 //"), ("1.1.8", None, "v2 //"), ("1.1.9", None, "v3 //")])
        self.assertEqual([k for k, _ in stub.msgs], ["groups", "draft"] + ["draft", "critic"] * 4)

    def test_a_verse_that_fails_alone_is_failed(self):
        stub = v2.Stub(drafts=[None] + [base.draft("v //")] * 3, critics=[ACCEPT] * 3)
        with contextlib.redirect_stdout(io.StringIO()):
            res, rows = self.go(stub, groups=False, compare=False)
        self.assertEqual(res["failed"], ["1.1.6"]); self.assertEqual(res["split"], 0); self.assertEqual(len(rows), 3)


class TheAsk(unittest.TestCase):
    def asker(self, answers):
        g = object.__new__(ST.Gemini)
        g.calls = []
        def once(kind, msg, maxtok):
            g.calls.append((kind, maxtok))
            return answers.pop(0)
        g._once = once
        return g

    def test_cut_off_is_asked_again_with_room(self):
        g = self.asker([('{"translation": "cut', types.SimpleNamespace(name="MAX_TOKENS"), 0.01),
                        ('{"translation": "ok"}', 1, 0.02)])
        d, cost = g.ask("draft", "m")
        self.assertEqual(d, {"translation": "ok"}); self.assertAlmostEqual(cost, 0.03)
        self.assertEqual(g.calls, [("draft", 8192), ("draft", 16384)])
        self.assertEqual(g.last, {"kind": "draft", "finish": "STOP", "chars": 21, "json": True})

    def test_a_draft_not_json_is_asked_once_more_and_a_critic_is_not(self):
        g = self.asker([("not json", 1, 0.01), ("still not", "4", 0.01)])
        d, cost = g.ask("draft", "m")
        self.assertIsNone(d); self.assertEqual(g.calls, [("draft", 8192), ("draft", 16384)])
        self.assertEqual(g.last, {"kind": "draft", "finish": "RECITATION", "chars": 9, "json": False})
        g = self.asker([("not json", 1, 0.01)])
        self.assertIsNone(g.ask("critic", "m")[0]); self.assertEqual(g.calls, [("critic", 8192)])
        g = self.asker([("{", 2, 0.01), ("{", 2, 0.01), ("{", 2, 0.01)])
        self.assertIsNone(g.ask("draft", "m")[0]); self.assertEqual(len(g.calls), 3, "three calls at most")
        self.assertEqual(ST._finish_name("FinishReason.SAFETY"), "SAFETY"); self.assertEqual(ST._finish_name(None), "?")


class ThePrice(unittest.TestCase):
    def test_v21_is_priced_by_v2_until_it_has_its_own(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            pid = con.execute("SELECT id FROM passages LIMIT 1").fetchone()[0]
            ins = lambda v, pv, c: con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, "
                                               "engine, prompt_version, cost_usd, created_at) VALUES (?, 'MBh01', 'h', ?, "
                                               "?, ?, ?, '2026-10-15T01:00:00+00:00')", (pid, v, ST.ENGINE, pv, c))
            for v in range(10):
                ins(v + 1, "scholar-v2+scholar-critic-v2", 0.012)
            con.commit()
            p = ST.prices(con, v2.args(db), 1000)
            self.assertAlmostEqual(p["typical"], 0.012); self.assertEqual(p["how"], "measured on 10 scholar-v2 verses")
            for v in range(10):
                ins(v + 11, "scholar-v2.1+scholar-critic-v2", 0.02)
            con.commit()
            p = ST.prices(con, v2.args(db), 1000)
            self.assertAlmostEqual(p["typical"], 0.02); self.assertEqual(p["how"], "measured on 10 scholar-v2.1 verses")
            con.close()


class ThePages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = base.fixture(Path(self.tmp.name))
        import db_utils
        con = self.con = db_utils.connect(str(self.db))
        ST.ensure_schema(con)
        allp = self.allp = ST.load_text(con, "MBh01")
        put = lambda x, **kw: ST.store(con, dict({"passage_id": x["id"], "doc_code": "MBh01", "page_no": 1, "idx": x["idx"],
                                                  "verse_ref": x["ref"], "src_hash": ST.src_hash(x["text"]),
                                                  "status": "passed", "cost_usd": 0.01, "created_at": "t1",
                                                  "prompt_version": "scholar-v2.1+scholar-critic-v2"}, **kw))
        put(allp[0], translation="Then a sage saw him seated. //")
        whole = "Said Janamejaya: where have you been, *Sauti*? //"
        for x, t in ((allp[1], "where have you been, *Sauti*?"), (allp[2], "Said Janamejaya: //")):
            put(x, translation=t, group_ref="1.1.7-1.1.8", group_translation=whole, created_at="t2",
                moved="The speaker first.")
        put(allp[3], translation="The stories. //")
        con.commit()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_a_passage_not_its_parts_is_shown_whole(self):
        h = ST.render_doc(self.con, "MBh01", nav=True)
        self.assertIn('<span class="vr">7\u20138</span>Said Janamejaya: where have you been, <em>Sauti</em>? //', h)
        self.assertIn("<summary>Verse by verse: the words of the passage that render each verse</summary>", h)
        self.assertIn('<p class="wk"><span class="vr">1.1.7</span>where have you been, *Sauti*?</p>', h)
        self.assertIn("Moved between the verses: The speaker first.", h)
        p = ST.render_prose(self.con, "MBh01")
        self.assertIn('<span class="vr">7\u20138</span>Said Janamejaya: where have you been, <em>Sauti</em>?', p)
        self.assertNotIn('<span class="vr">8</span>', p)

    def test_rows_follow_the_passage_place_now(self):
        self.con.execute("UPDATE scholar_translations SET idx = 100 - idx")   # as if a re-ingest moved them
        self.con.commit()
        h = ST.render_doc(self.con, "MBh01", nav=True)
        self.assertLess(h.index('id="v-1.1.6"'), h.index('id="v-1.1.7"'))
        self.assertLess(h.index('id="v-1.1.7"'), h.index('id="v-1.1.9"'))
        p = ST.render_prose(self.con, "MBh01")
        self.assertLess(p.index("Then a sage"), p.index("The stories"))


class ThePrompt(unittest.TestCase):
    def test_rule_ten(self):
        d = ST.SYSTEM_DRAFT
        self.assertIn("the main clause may come first, as English wants it", d)
        self.assertIn("The segments need not read as the passage, nor in its order", d)
        self.assertNotIn("joined with spaces the segments must read as that passage", d)
        self.assertEqual((ST.PROMPT_VERSION, ST.CRITIC_VERSION), ("scholar-v2.1", "scholar-critic-v2"))


class TheCli(unittest.TestCase):
    def test_the_header_names_the_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            o = subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc", "MBh01",
                                "--pages", "1"], capture_output=True, text=True, encoding="utf-8", cwd=d,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout
            self.assertIn("scholar_translate.py  SCHOLAR_V21_2026_10_14 (scholar-v2.1)  DRY RUN (nothing called, nothing "
                          "written)", o)


@unittest.skipUnless(mp.HAVE_IT, "indic_transliteration is not installed")
class TheImporter(unittest.TestCase):
    def test_appendix_lines_are_counted_not_unread(self):
        book = mp.BOOK.replace("</pre>", "01,001.002c@001_0001 k\u1e5b\u1e63\u1e47advaip\u0101yana\u1e43 vy\u0101sa\u1e43 "
                                         "viddhi\n01,001.002c@001_0002 n\u0101r\u0101ya\u1e47am\n</pre>")
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "mbh_01_u.htm"
            src.write_text(book, encoding="utf-8")
            out = Path(d) / "out"
            r = subprocess.run([sys.executable, str(SCRIPTS / "import_mbh_gretil.py"), "--book", "1", "--src", str(src),
                                "--out", str(out)], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("appendix passages excluded: 2 lines (the edition prints them in its appendix", r.stdout)
            self.assertIn("NOT READ: 2 lines that look like a reference (the first: 01,003.003a)", r.stdout)
            self.assertIn('--glob "%s/MBh01_*.jsonl"' % out.as_posix(), r.stdout)
            self.assertIn("python scripts/reingest_pages.py --doc MBh01 --merged-dir %s --no-segment" % out, r.stdout)
            recs = [json.loads(x) for x in (out / "MBh01_0001.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([x["verse_ref"] for x in recs], ["1.1.1", "1.1.2"], "the appendix is not in the text")


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "import_mbh_gretil.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_scholarv21_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_v21_2026_10_14.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_costtruth_*"))   # COST_TRUTH_2026_10_15 came after
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "scholar_translate.py"
            p.write_bytes(p.read_bytes().replace(b'PROMPT_VERSION = "scholar-v2" ', b'PROMPT_VERSION = "x" '))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor 3 found 0 times (want 1): this is not the file released",
                                                             r.stdout)
            self.assertNotIn(b"SCHOLAR_V21", (t / "scripts" / "import_mbh_gretil.py").read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry SCHOLAR_V2_2026_10_14", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_scholar_v21_2026_10_14.py", Path(__file__), SCRIPTS / "scholar_translate.py"):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"SCHOLAR_V21_2026_10_14", b)
        self.assertIn(b"SCHOLAR_V21_2026_10_14", (SCRIPTS / "import_mbh_gretil.py").read_bytes())


if __name__ == "__main__":
    unittest.main()
