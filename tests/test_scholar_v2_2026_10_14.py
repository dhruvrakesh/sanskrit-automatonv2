# -*- coding: ascii -*-
"""SCHOLAR_V2_2026_10_14: a Sanskrit sentence over several verses translated whole (the groups call, the segments, the
rows), the second judge (the order it is not told, its verdict, a major error flags), the notes rules in the prompt,
the price measured by prompt version, the columns added in place, the pages (a sentence as one block, the earlier
version, the prose view), the dashboard's prose route, the importer's missing --src, and the patcher. Temp files only;
no model is called."""
import hashlib, importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base   # its fixture: MBh01 1.1.6-1.1.9, a noise line, errata, debris

ST = base.ST


class Stub:
    """Scripted answers by kind; each ask $0.01, each judge $0.0002."""

    def __init__(self, drafts=(), critics=(), groups=(), compares=(), judges=()):
        self.q = {"draft": list(drafts), "critic": list(critics), "groups": list(groups), "compare": list(compares)}
        self.judges = list(judges)
        self.spent, self.msgs = 0.0, []

    def ask(self, kind, msg):
        self.msgs.append((kind, msg))
        self.spent += 0.01
        q = self.q.get(kind) or []
        return (q.pop(0) if q else None), 0.01

    def judge(self, src, iast, english):
        self.spent += 0.0002
        f, l = self.judges.pop(0) if self.judges else (5, 5)
        return f, l, "ok", 0.0002


ACCEPT = base.ACCEPT


def args(db, **kw):
    a = base.args(db, **kw)
    for k, v in (("groups", True), ("compare", True)):
        if not hasattr(a, k) or k not in kw:
            setattr(a, k, kw.get(k, v))
    return a


class TheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = base.fixture(Path(self.tmp.name))
        self.busy = ST.busy_with
        ST.busy_with = lambda doc: None

    def tearDown(self):
        ST.busy_with = self.busy
        self.tmp.cleanup()

    def go(self, stub, **kw):
        import db_utils
        a = args(self.db, **kw)
        con = db_utils.connect(str(self.db))
        try:
            ST.ensure_schema(con)
            allp = ST.load_text(con, "MBh01")
            done = ST.latest_rows(con, "MBh01")
            picked, _l, _s = ST.choose(a, allp, done)
            meta = ST.doc_meta(con, "MBh01", allp)
            price = {"typical": 0.03, "most": 0.06, "call": 0.01, "how": "test"}
            res = ST.run(a, allp, picked, meta, done, stub, con, price, None)
            cur = con.execute("SELECT * FROM scholar_translations ORDER BY id")
            names = [d[0] for d in cur.description]
            rows = [dict(zip(names, r)) for r in cur.fetchall()]
        finally:
            con.close()
        return res, rows

    def test_a_sentence_over_two_verses_is_one_passage(self):
        groups = {"groups": [["1.1.6"], ["1.1.7", "1.1.8"], ["1.1.9"]]}
        seg = {"translation": "x", "segments": [{"ref": "1.1.7", "english": "Where do you come from, Sauti,"},
                                                {"ref": "1.1.8", "english": "the s\u016bta was asked. //"}],
               "moved": "", "notes": [{"anchor": "Sauti", "kind": "name", "note": "the son of the s\u016bta"}],
               "glossary": [], "doubts": ""}
        cmp_major = {"A": {"fidelity": 3, "errors": [{"where": "x", "error": "a wrong person", "severity": "major"}]},
                     "B": {"fidelity": 5, "errors": []}, "better": "B", "reason": "B names him rightly"}
        cmp_ok = {"A": {"fidelity": 5, "errors": []}, "B": {"fidelity": 2, "errors": []}, "better": "A", "reason": "r"}
        stub = Stub(drafts=[base.draft("Then a sage saw him seated, //"), seg, base.draft("The stories. //")],
                    critics=[ACCEPT, ACCEPT, ACCEPT], groups=[groups], compares=[cmp_ok, cmp_ok, cmp_major])
        res, rows = self.go(stub)
        kinds = [k for k, _ in stub.msgs]
        self.assertEqual(kinds, ["groups", "draft", "critic", "compare", "draft", "critic", "compare", "draft", "critic",
                                 "compare"])
        g = stub.msgs[0][1]
        self.assertIn("THE VERSES:\n[1.1.6] " + base.V6, g); self.assertIn("[1.1.9] " + base.V9, g)
        m = stub.msgs[4][1]
        self.assertIn("CHAPTER: 1. VERSES: 1.1.7 to 1.1.8.", m)
        self.assertIn("THE VERSES TO TRANSLATE [1.1.7] to [1.1.8] (one Sanskrit sentence: give \"segments\"", m)
        self.assertIn("[1.1.8] " + base.V8 + "\n   IAST: " + base.I8, m)
        self.assertIn("[1.1.6] " + base.V6 + "\n   English: Then a sage saw him seated, //", m, "the verse before")
        self.assertIn("THE VERSES AFTER (Sanskrit only, for understanding only):\n[1.1.9] ", m)
        self.assertNotIn("THE VERSE TO TRANSLATE [", m)
        self.assertIn("- Janamejaya (person)", m, "the glossary of every verse of the sentence")
        self.assertEqual(res["grouped"], 1)
        by = {r["verse_ref"]: r for r in rows}
        r7, r8 = by["1.1.7"], by["1.1.8"]
        self.assertEqual((r7["group_ref"], r8["group_ref"]), ("1.1.7-1.1.8", "1.1.7-1.1.8"))
        self.assertEqual(r7["translation"], "Where do you come from, Sauti,")
        self.assertEqual(r8["translation"], "the s\u016bta was asked. //")
        self.assertEqual(r7["group_translation"], "Where do you come from, Sauti, the s\u016bta was asked. //")
        self.assertEqual(r7["created_at"], r8["created_at"]); self.assertEqual(r7["notes"], r8["notes"])
        self.assertAlmostEqual(r7["cost_usd"] + r8["cost_usd"], 0.0304, places=6, msg="the sentence's cost, split")
        self.assertEqual(by["1.1.6"]["group_ref"], None)
        p6 = by["1.1.6"]["passage_id"]
        self.assertEqual(p6 % 2, 1)
        self.assertEqual(by["1.1.6"]["compare_better"], "working", "pid odd: the scholarly English was B, and A won")
        c = json.loads(by["1.1.6"]["compare"])
        self.assertEqual((c["order"], c["version"]), ("scholarly as B", "scholar-compare-v1"))
        self.assertEqual(by["1.1.7"]["compare_better"], "scholarly", "pid even: the scholarly English was A")
        p9 = by["1.1.9"]["passage_id"]
        self.assertEqual(p9 % 2, 0)
        self.assertEqual(by["1.1.9"]["compare_better"], "working")
        self.assertEqual(by["1.1.9"]["status"], "flagged", "the second judge found a major error in the scholarly English")
        self.assertEqual(r7["prompt_version"], "scholar-v2+scholar-critic-v2")

    def test_the_groups_answer_must_fit_or_each_verse_stands_alone(self):
        idxs = [10, 11, 12]
        refs = ["a", "b", "c"]
        self.assertEqual(ST.parse_groups({"groups": [["a"], ["b", "c"]]}, refs, idxs), [[10], [11, 12]])
        for bad in (None, {}, {"groups": None}, {"groups": [["a"], ["c", "b"]]}, {"groups": [["a"], ["b"]]},
                    {"groups": [["a", "b", "c"]] * 1 + [[]]}, {"groups": "abc"}):
            self.assertEqual(ST.parse_groups(bad, refs, idxs), [[10], [11], [12]], bad)
        self.assertEqual(ST.parse_groups({"groups": [list("abcdefg")]}, list("abcdefg"), list(range(7))),
                         [[i] for i in range(7)], "seven verses is more than a sentence")
        u = ST.clean_unit({"translation": "whole", "segments": [{"ref": "b", "english": "two"}, {"ref": "a", "english": "one"}]},
                          ["a", "b"])
        self.assertIsNone(u["segments"]); self.assertEqual(u["translation"], "whole", "out of order: kept whole")
        u = ST.clean_unit({"translation": "whole", "segments": [{"ref": "a", "english": "one"}, {"ref": "b", "english": ""}]},
                          ["a", "b"])
        self.assertEqual(u["segments"], {"a": "one", "b": ""}); self.assertEqual(u["translation"], "one")

    def test_without_an_answer_the_sentence_stays_on_its_first_verse(self):
        groups = {"groups": [["1.1.6", "1.1.7"], ["1.1.8"], ["1.1.9"]]}
        stub = Stub(drafts=[base.draft("one passage for both //")] + [base.draft("x //")] * 2, critics=[ACCEPT] * 3,
                    groups=[groups])
        res, rows = self.go(stub, compare=False)
        by = {r["verse_ref"]: r for r in rows}
        self.assertEqual((by["1.1.6"]["translation"], by["1.1.7"]["translation"]), ("one passage for both //", ""))
        self.assertEqual(by["1.1.7"]["group_translation"], "one passage for both //")
        self.assertNotIn("compare", [k for k, _ in stub.msgs])

    def test_without_groups_or_compare_it_is_as_before(self):
        stub = Stub(drafts=[base.draft("a //")] * 4, critics=[ACCEPT] * 4)
        res, rows = self.go(stub, groups=False, compare=False)
        self.assertEqual([k for k, _ in stub.msgs], ["draft", "critic"] * 4)
        self.assertTrue(all(r["group_ref"] is None and r["compare"] is None for r in rows))

    def test_the_caps_hold_for_a_sentence(self):
        groups = {"groups": [["1.1.6", "1.1.7", "1.1.8", "1.1.9"]]}
        stub = Stub(groups=[groups])
        res, rows = self.go(stub, max_usd=0.1)
        self.assertEqual(rows, [])
        self.assertIn("--max-usd $0.10 is reached", res["stopped"], "4 verses at $0.03 pass $0.10")


class ThePrompts(unittest.TestCase):
    def test_the_rules(self):
        d = ST.SYSTEM_DRAFT
        self.assertIn("At most three a verse.", d); self.assertIn("No note for a common word", d)
        self.assertIn("Spell every Sanskrit word in a note exactly as the IAST given spells it.", d)
        self.assertIn('"segments", [{"ref": the verse, "english": its part}]', d)
        self.assertIn("12. SPEAKERS.", d); self.assertIn("uv\u0101ca", d)
        self.assertIn("Never quote or reconstruct any published translation.", d)
        self.assertIn("is an issue of type note", ST.SYSTEM_CRITIC)
        self.assertIn("at most 6 verses a group", ST.SYSTEM_GROUPS)
        self.assertIn("Who made each translation is not said.", ST.SYSTEM_COMPARE)
        for s_ in (ST.SYSTEM_CRITIC, ST.SYSTEM_GROUPS, ST.SYSTEM_COMPARE):
            json.loads(s_[s_.rindex("\n{"):])   # its reply format is JSON
        c = ST.clean_compare({"A": {"fidelity": "4", "errors": [{"error": "e", "severity": "MAJOR"}, {"error": ""}]},
                              "B": "x", "better": "b", "reason": "r"})
        self.assertEqual(c, {"A": {"fidelity": 4, "errors": [{"where": "", "error": "e", "severity": "major"}]},
                             "B": {"fidelity": None, "errors": []}, "better": "B", "reason": "r"})
        self.assertEqual(ST.clean_compare({"better": "neither"})["better"], "equal")
        self.assertIsNone(ST.clean_compare("no"))


class ThePrice(unittest.TestCase):
    def test_measured_by_prompt_version(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            pid = con.execute("SELECT id FROM passages LIMIT 1").fetchone()[0]
            for v in range(10):
                con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, engine, prompt_version, "
                            "cost_usd) VALUES (?, 'MBh01', 'h', ?, ?, 'scholar-v1+scholar-critic-v1', 0.01)",
                            (pid, v + 1, ST.ENGINE))
            con.commit()
            p = ST.prices(con, args(db), 1000)
            self.assertAlmostEqual(p["typical"], 0.015)
            self.assertEqual(p["how"], "measured on 10 scholar-v1 verses, with a compare call at half of it")
            self.assertAlmostEqual(ST.prices(con, args(db, compare=False), 1000)["typical"], 0.01)
            for v in range(10):
                con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, engine, prompt_version, "
                            "cost_usd) VALUES (?, 'MBh01', 'h', ?, ?, 'scholar-v2+scholar-critic-v2', 0.02)",
                            (pid, v + 11, ST.ENGINE))
            con.commit()
            p = ST.prices(con, args(db), 1000)
            self.assertAlmostEqual(p["typical"], 0.02); self.assertEqual(p["how"], "measured on 10 scholar-v2 verses")
            con.close()


class TheColumns(unittest.TestCase):
    def test_a_v1_table_gains_them_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            con = sqlite3.connect(str(Path(d) / "c.db"))
            con.execute("CREATE TABLE scholar_translations(id INTEGER PRIMARY KEY AUTOINCREMENT, passage_id INTEGER NOT NULL, "
                        "doc_code TEXT NOT NULL, page_no INTEGER, idx INTEGER, verse_ref TEXT, src_hash TEXT NOT NULL, "
                        "version INTEGER NOT NULL, translation TEXT, notes TEXT, doubts TEXT, draft TEXT, critique TEXT, "
                        "passes INTEGER, fidelity INTEGER, fluency INTEGER, judge_reason TEXT, working_fidelity INTEGER, "
                        "working_fluency INTEGER, status TEXT, engine TEXT, judge_engine TEXT, prompt_version TEXT, "
                        "cost_usd REAL, created_at TEXT, reviewed_by TEXT, reviewed_at TEXT, review_verdict TEXT, "
                        "review_note TEXT, UNIQUE(passage_id, version))")
            con.execute("INSERT INTO scholar_translations(passage_id, doc_code, src_hash, version, translation) VALUES "
                        "(1, 'D', 'h', 1, 'kept')")
            con.commit()
            ST.ensure_schema(con)
            ST.ensure_schema(con)
            cols = [r[1] for r in con.execute("PRAGMA table_info(scholar_translations)")]
            for c in ("group_ref", "group_translation", "moved", "compare", "compare_better"):
                self.assertEqual(cols.count(c), 1, c)
            self.assertEqual(con.execute("SELECT translation FROM scholar_translations").fetchone()[0], "kept")
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
                                                  "prompt_version": "scholar-v1+scholar-critic-v1"}, **kw))
        put(allp[0], translation="The s\u016bta said: Then a sage saw him seated, //")
        put(allp[1], translation="old one //")
        cmp_ = json.dumps({"scholarly": {"fidelity": 5, "errors": []},
                           "working": {"fidelity": 2, "errors": [{"where": "p\u0101rik\u1e63itasya", "error": "two men",
                                                                  "severity": "major"}]},
                           "better": "scholarly", "reason": "it names one man", "order": "scholarly as A"})
        notes = json.dumps([{"anchor": "Janamejaya", "kind": "name", "note": "the son of Parik\u1e63it"}])
        for x, t in ((allp[1], "Where have you been, *Sauti*,"), (allp[2], "said Janamejaya. //")):
            put(x, translation=t, group_ref="1.1.7-1.1.8", group_translation="Where have you been, *Sauti*, said Janamejaya. //",
                notes=notes, compare=cmp_, compare_better="scholarly", created_at="t2",
                prompt_version="scholar-v2+scholar-critic-v2", draft="first draft")
        put(allp[3], translation="The stories. //", status="flagged")
        con.commit()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_a_sentence_is_one_block_and_the_earlier_version_is_kept(self):
        h = ST.render_doc(self.con, "MBh01", nav=True)
        self.assertEqual(h.count('<article class="v">'), 3, "1.1.6, the sentence 1.1.7-1.1.8, 1.1.9")
        self.assertIn('<a class="ref" id="v-1.1.7" href="#v-1.1.7">1.1.7 to 1.1.8</a><span>one sentence</span>', h)
        self.assertIn('<span class="vr">7</span>Where have you been, <em>Sauti</em>, <span class="vr">8</span>said '
                      'Janamejaya<sup>1</sup>. //', h)
        self.assertIn("Scholarly English, one sentence over 2 verses", h)
        self.assertIn('<span class="cmp better" title="the second judge: it names one man">more faithful than the working '
                      'English</span>', h)
        self.assertIn("The second judge on the working English: fidelity 2", h); self.assertIn("major, at p\u0101rik", h)
        self.assertIn('The earlier version (scholar-v1+scholar-critic-v1)</div><p class="wk"><span class="vr">1.1.7</span>'
                      'old one //', h)
        self.assertIn("the second judge: the scholarly English more faithful <b>2</b>", h)
        self.assertIn('<a href="/scholar/MBh01/prose" style="color:var(--gold)">Read it as prose</a>', h)
        self.assertIn('href="scholar_MBh01_prose.html"', ST.render_doc(self.con, "MBh01"))

    def test_as_prose(self):
        h = ST.render_prose(self.con, "MBh01", nav=True)
        self.assertIn("<title>MBh01 as prose</title>", h)
        self.assertIn('<section class="prose"><h2>Chapter 1</h2><p>', h)
        self.assertIn('<span class="vr">6</span>The s\u016bta said: Then a sage saw him seated,', h)
        self.assertNotIn("//", h[h.index('<main class="sch">'):], "the verse ends are not shown")
        self.assertIn('<span class="vr">7</span>Where have you been, <em>Sauti</em>, <span class="vr">8</span>said '
                      'Janamejaya<sup>1</sup>.', h)
        self.assertIn('<span class="fl" title="flagged: a person reads it"><span class="vr">9</span>The stories.</span>', h)
        self.assertIn('<ol class="fn"><li><span class="r">1.1.7</span> <b>Janamejaya</b>: the son of Parik\u1e63it</li></ol>', h)
        self.con.execute("UPDATE passages SET text = 'changed' WHERE id = ?", (self.allp[3]["id"],))
        self.con.commit()
        h = ST.render_prose(self.con, "MBh01")
        self.assertIn("1 verse(s) whose Sanskrit has changed since are left out.", h); self.assertNotIn("The stories", h)
        self.assertIn('href="scholar_MBh01.html"', h)
        e = sqlite3.connect(":memory:")
        self.assertIn("No current scholarly English for <b>MBh01</b> yet", ST.render_prose(e, "MBh01"))
        e.close()

    def test_a_speaker_opens_a_paragraph(self):
        self.con.execute("UPDATE scholar_translations SET translation = 'The sages said: tell us. //' WHERE verse_ref = '1.1.9'")
        self.con.commit()
        h = ST.render_prose(self.con, "MBh01")
        self.assertIn('</p><p><span class="fl" title="flagged: a person reads it"><span class="vr">9</span>The sages said:', h)


class TheCli(unittest.TestCase):
    def run_(self, db, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc", "MBh01"]
                              + list(extra), capture_output=True, text=True, encoding="utf-8", cwd=str(Path(db).parent),
                              env=dict(os.environ, PYTHONIOENCODING="utf-8"))

    def test_the_dry_run_says_it_and_the_report_writes_both(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            o = self.run_(db, "--pages", "1").stdout
            self.assertIn("sentences: one over several verses is translated whole (scholar-groups-v1); the second judge: "
                          "the scholarly and the working English side by side (scholar-compare-v1)   (SCHOLAR_V2_2026_10_14)", o)
            self.assertRegex(o, r"NEXT: python scripts\\scholar_translate\.py --doc MBh01 --pages 1 --limit 24 --yes "
                                r"--max-usd \d+\.\d\d\n")
            o = self.run_(db, "--pages", "1", "--no-groups", "--no-compare", "--redo").stdout
            self.assertIn("sentences: every verse alone; the second judge: none", o)
            self.assertIn("--limit 24 --redo --no-groups --no-compare --yes --max-usd", o)
            r = self.run_(db, "--report", "--exports", str(Path(d) / "ex"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("and as prose", r.stdout)
            self.assertTrue((Path(d) / "ex" / "scholar_MBh01_prose.html").exists())


class TheDashboard(unittest.TestCase):
    def test_the_prose_route(self):
        d = base.load("dashboard_scholar_v2", SCRIPTS / "dashboard.py")
        with tempfile.TemporaryDirectory() as t:
            db = base.fixture(Path(t))
            c = d.app.test_client()
            r = c.get("/scholar/MBh01/prose?db=" + str(db))
            self.assertEqual(r.status_code, 200)
            self.assertIn("No current scholarly English for <b>MBh01</b> yet", r.get_data(as_text=True))
            self.assertEqual(c.get("/scholar/bad doc/prose").status_code, 400)
            self.assertEqual(c.get("/scholar/MBh01?db=" + str(db)).status_code, 200, "the verses as before")


class TheImporter(unittest.TestCase):
    def test_a_missing_src_is_said(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPTS / "import_mbh_gretil.py"), "--book", "1", "--src",
                                str(Path(d) / "none.htm"), "--dry-run"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSE: %s not found. Save the book's e-text there first" % (Path(d) / "none.htm"), r.stderr)
            self.assertNotIn("Traceback", r.stderr)


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "dashboard.py", "import_mbh_gretil.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_scholarv2_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_v2_2026_10_14.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / "scripts" / f).read_bytes(), (SCRIPTS / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "scholar_translate.py"
            p.write_bytes(p.read_bytes().replace(b'CRITIC_VERSION = "scholar-critic-v1"', b'CRITIC_VERSION = "x"'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor 2 found 0 times (want 1): this is not the file released",
                                                             r.stdout)
            self.assertNotIn(b"SCHOLAR_V2", (t / "scripts" / "dashboard.py").read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry SCHOLAR_2026_10_14", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_scholar_v2_2026_10_14.py", Path(__file__), SCRIPTS / "scholar_translate.py"):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"SCHOLAR_V2_2026_10_14", b)
        for f in ("dashboard.py", "import_mbh_gretil.py"):
            self.assertIn(b"SCHOLAR_V2_2026_10_14", (SCRIPTS / f).read_bytes(), f)


if __name__ == "__main__":
    unittest.main()
