# -*- coding: ascii -*-
"""SCHOLAR_EDITION_2026_10_17: the scholarly English as an edition in export_html.py's format (--scholar): each verse's
current scholarly row, a sentence over several verses once, the notes and the doubts as the chapter's notes, a dagger
on what is flagged and not yet accepted, the working English (marked) where there is none or a person rejected it, a
stale row left out; the file gains _scholar and the working edition is untouched. The dashboard: /api/export mode
scholar, the desk's edition box and /desk/<doc>/edition; Export As on the main page; the patcher. Temp folders only;
nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MARK = b"SCHOLAR_EDITION_2026_10_17"
APPLIED = MARK in (SCRIPTS / "export_html.py").read_bytes()
NOTE = "Saunaka, the head of the sages of the forest."


def edition_fixture(td: Path) -> Path:
    """The MBh01 fixture of test_scholar_2026_10_14 with scholarly rows: 1.1.6 passed (a note, a doubt), 1.1.7 flagged,
    1.1.8 to 1.1.9 one sentence, 1.1.11 stale; and a second text whose one row a person rejected."""
    import test_scholar_2026_10_14 as base
    ST = base.ST
    db = base.fixture(td)
    con = sqlite3.connect(str(db))
    ST.ensure_schema(con)
    allp = {x["ref"]: x for x in ST.load_text(con, "MBh01")}

    def put(ref, tr, status="passed", notes=(), doubts="", group=None, gtr=None, stale=False):
        x = allp[ref]
        ST.store(con, {"passage_id": x["id"], "doc_code": "MBh01", "page_no": x["page"], "idx": x["idx"], "verse_ref": ref,
                       "src_hash": "0" * 16 if stale else ST.src_hash(x["text"]), "translation": tr,
                       "notes": json.dumps(list(notes)), "doubts": doubts, "critique": "[]", "status": status,
                       "engine": "anthropic:claude-sonnet-5-5", "judge_engine": ST.JUDGE, "prompt_version": "scholar-v2.1",
                       "cost_usd": 0.04, "group_ref": group, "group_translation": gtr,
                       "created_at": "2026-10-17T10:00:00+00:00"})
    put("1.1.6", "Then the sage, seeing him seated at ease, spoke. //",
        notes=[{"anchor": "the sage", "kind": "name", "note": NOTE}], doubts="The edition reads tatas.")
    put("1.1.7", "O son of a suta, where do you come from? //", status="flagged")
    whole = "The suta said: I was near Janamejaya and Pariksita, and heard the stories of Krsna Dvaipayana."
    put("1.1.8", "part one", group="g1", gtr=whole, notes=[{"anchor": "Krsna Dvaipayana", "kind": "name", "note": "Vyasa."}])
    put("1.1.9", "part two", group="g1", gtr=whole)
    put("1.1.11", "a stale row", stale=True)
    con.execute("INSERT INTO docs(code, category) VALUES ('Second', 'x')")
    did = con.execute("SELECT id FROM docs WHERE code = 'Second'").fetchone()[0]
    con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, verse_ref, chapter, text_type) "
                "VALUES (?, 1, 1, ?, 'The working one. //', '1.1', '1', 'mula')", (did, "\u0927\u0930\u094d\u092e\u0903"))
    pid = con.execute("SELECT id FROM passages WHERE doc_id = ?", (did,)).fetchone()[0]
    ST.store(con, {"passage_id": pid, "doc_code": "Second", "page_no": 1, "idx": 1, "verse_ref": "1.1",
                   "src_hash": ST.src_hash("\u0927\u0930\u094d\u092e\u0903"), "translation": "The rejected one. //",
                   "notes": "[]", "critique": "[]", "status": "passed", "engine": "anthropic:claude-sonnet-5-5",
                   "judge_engine": ST.JUDGE, "cost_usd": 0.04, "created_at": "2026-10-17T10:00:00+00:00"})
    con.execute("UPDATE scholar_translations SET review_verdict = 'reject', reviewed_by = 'Tester' WHERE passage_id = ?", (pid,))
    con.commit()
    con.close()
    return db


def export(db, out, doc, *extra):
    return subprocess.run([sys.executable, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", doc, "--out", str(out),
                           "--sanskrit", "--side-by-side", *extra], capture_output=True, text=True, cwd=str(REPO))


@unittest.skipUnless(APPLIED, "SCHOLAR_EDITION_2026_10_17 is not applied here")
class TheEdition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = edition_fixture(self.td)
        self.out = self.td / "exports"

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_scholarly_edition(self):
        r = export(self.db, self.out, "MBh01", "--scholar", "--title", "MBh01 - the scholarly English")
        self.assertEqual(r.returncode, 0, r.stderr)
        files = sorted(p.name for p in self.out.iterdir())
        self.assertEqual(files, ["MBh01_1-1_scholar.html"])
        h = (self.out / files[0]).read_text(encoding="utf-8")
        self.assertIn("The scholarly English, with the Sanskrit", h)
        self.assertIn("<b>Scholarly English:</b> 4 of 6 verses (passed 3, flagged 1", h)
        self.assertIn("1 left out, their Sanskrit changed since", h)
        self.assertIn("made by anthropic:claude-sonnet-5-5 (4)", h)
        self.assertIn("<b>Working English:</b>", h)
        self.assertIn("The scholarly English of the Sanskrit Automaton (scholar_translate.py)", h)
        self.assertNotIn("Machine translation produced by the Sanskrit", h, "its own methodology")
        self.assertIn("Then the sage<sup class='fn-ref' id='fnr-1'>", h, "the note after its anchor")
        self.assertIn("the sage: " + NOTE, h)
        self.assertIn("The reading: The edition reads tatas.", h)
        self.assertNotIn("//", re.sub(r"https?://", "", h), "the verse markers are not printed")
        self.assertIn("where do you come from?<span class='sch-flag' title='flagged: not yet read by a person'>&#8224;", h)
        self.assertIn("<span class='sch-rng'>1.1.8\u20139</span>The suta said", h)
        self.assertEqual(h.count("The suta said"), 1, "a sentence over two verses, once")
        self.assertIn("Its English is given with 1.1.8\u20139, above.", h)
        self.assertNotIn("part one", h)
        self.assertNotIn("a stale row", h)
        self.assertIn(".sch-flag", h, "its styles")

    def test_the_working_english_marked_and_the_plain_edition_untouched(self):
        r = export(self.db, self.out, "Second", "--scholar")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (self.out / "Second_1-1_scholar.html").read_text(encoding="utf-8")
        self.assertIn("<span class='sch-wk'>The working one.</span>", h, "rejected by a person: the working English, marked")
        self.assertNotIn("The rejected one", h)
        self.assertIn("none current for this text (1 rejected by a person)", h)
        r = export(self.db, self.out, "MBh01")
        self.assertEqual(r.returncode, 0, r.stderr)
        plain = (self.out / "MBh01_1-1.html").read_text(encoding="utf-8")
        self.assertNotIn("sch-", plain)
        self.assertNotIn("Scholarly English", plain)
        self.assertIn("Machine translation produced by the Sanskrit", plain)
        self.assertIn("The s\u016bta said: I was near Janamejaya", plain, "the working English, as before")


@unittest.skipUnless(APPLIED and MARK in (SCRIPTS / "dashboard.py").read_bytes(), "not applied here")
class TheDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_bench_desk_2026_10_16 as T
        cls.d = T.load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = edition_fixture(self.td)
        self.chart = self.td / "text_path.json"
        self.chart.write_text(json.dumps({"at": "2026-10-17T10:00:00", "texts": [
            {"doc": "MBh01", "path": "translate", "why": "no debris", "next": ["translate it: Finish EN"], "cost": 1.0}]}),
            encoding="utf-8")
        self.saved = (self.d.PATH_FILE, self.d.DESK_DB, self.d.ROOT)
        self.d.PATH_FILE, self.d.DESK_DB = self.chart, str(self.db)
        self.d._DESK_CACHE.update(res=None)
        self.d._SCHOLAR_COVER.update(key=None, at=0.0, res={})

    def tearDown(self):
        self.d.PATH_FILE, self.d.DESK_DB, self.d.ROOT = self.saved
        self.d._DESK_CACHE.update(res=None)
        self.tmp.cleanup()

    def test_export_mode_scholar(self):
        got, orig = [], self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j1")
        try:
            r = self.c.post("/api/export", json={"doc": "MBh01", "mode": "scholar"})
            r2 = self.c.post("/api/export", json={"doc": "MBh01", "mode": "tri"})
        finally:
            self.d.launch = orig
        self.assertEqual((r.status_code, r.get_json()["mode"]), (200, "scholar"))
        argv = got[0][2]
        for x in ("--scholar", "--sanskrit", "--side-by-side"):
            self.assertIn(x, argv)
        self.assertIn("MBh01 - the scholarly English", argv)
        self.assertNotIn("--scholar", got[1][2], "the trilingual edition as before")
        self.assertEqual(r2.status_code, 200)

    def test_the_desk_offers_the_edition_and_serves_it(self):
        h = self.c.get("/desk/MBh01").get_data(as_text=True)
        self.assertIn("The edition (HTML)", h)
        self.assertIn("deskEdition('MBh01', this)", h)
        self.assertIn('href="/desk/MBh01/edition"', h)
        self.assertIn("async function deskEdition(doc, btn)", h)
        self.d.ROOT = self.td
        r = self.c.get("/desk/MBh01/edition")
        self.assertEqual(r.status_code, 404)
        self.assertIn("No scholarly edition of MBh01 yet", r.get_data(as_text=True))
        (self.td / "exports").mkdir()
        (self.td / "exports" / "MBh01_1-1_scholar.html").write_text("<p>the edition</p>", encoding="utf-8")
        (self.td / "exports" / "MBh01_1-1.html").write_text("<p>the working one</p>", encoding="utf-8")
        r = self.c.get("/desk/MBh01/edition")
        self.assertEqual(r.status_code, 200)
        self.assertIn("the edition", r.get_data(as_text=True))
        r.close()
        self.assertEqual(self.c.get("/desk/..%2Fx/edition").status_code in (400, 404), True)


class ThePage(unittest.TestCase):
    @unittest.skipUnless(MARK in (SCRIPTS / "dashboard_static.html").read_bytes(), "not applied here")
    def test_export_as(self):
        s = (SCRIPTS / "dashboard_static.html").read_text(encoding="utf-8")
        self.assertIn('<option value="scholar"', s)
        self.assertIn("if (m === 'scholar') return '(scholarly)';", s)
        self.assertIn("body: JSON.stringify({doc, db: cfg.db, out: cfg.exports, mode})", s, "the contract of /api/export")


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/export_html.py", "scripts/dashboard.py", "scripts/dashboard_static.html")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_scholaredition_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_scholaredition_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_edition_2026_10_17.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_buttons_*"))   # BUTTONS_2026_10_17 came after
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "export_html.py"
            p.write_bytes(p.read_bytes().replace(b"        suffix += \"_img\"", b"        suffix += '_img'"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("export_html.py: anchor 9 found 0 times (want 1)", r.stdout)
            for f in self.FILES:
                self.assertNotIn(MARK, (t / f).read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_scholar_edition_2026_10_17.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p.name)
            self.assertIn(MARK, b, p.name)


if __name__ == "__main__":
    unittest.main()
