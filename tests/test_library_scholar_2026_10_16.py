# -*- coding: ascii -*-
"""LIBRARY_SCHOLAR_2026_10_16: the Library's cards and the reader show the scholarly English (scholar_translations)
beside the working English: the verses, passed, flagged, source doubts, a person's verdicts, stale; a text with
scholarly English and no working English is listed; the reader shows each verse's scholarly English above its working
English, with a link to its checks. Imports scripts/dashboard.py as a module (no server, no port); temp files only,
never data/context.db; nothing is called."""
import importlib.util, json, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402

ST = base.ST
MARK = b"LIBRARY_SCHOLAR_2026_10_16"
APPLIED = MARK in (SCRIPTS / "dashboard.py").read_bytes()
SONNET, OPUS = "anthropic:claude-sonnet-5-5", "anthropic:claude-opus-5-5"


def load_dashboard():
    spec = importlib.util.spec_from_file_location("dashboard_libsch", str(SCRIPTS / "dashboard.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(APPLIED, "LIBRARY_SCHOLAR_2026_10_16 is not applied here")
class TheLibraryAndTheReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_dashboard()
        cls.jt = tempfile.TemporaryDirectory()
        cls.d.JOBS_LOG_PATH = Path(cls.jt.name) / "jobs.jsonl"
        cls.c = cls.d.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.jt.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = base.fixture(self.td)
        self.d._SCHOLAR_COVER.update(key=None, at=0.0, res={})
        import db_utils
        con = db_utils.connect(str(self.db))
        ST.ensure_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES ('Agama2', 'agama')")
        did = con.execute("SELECT id FROM docs WHERE code = 'Agama2'").fetchone()[0]
        for k in (1, 2):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, verse_ref, text_type, quality_score) "
                        "VALUES (?, 1, ?, ?, '', ?, 'mula', 0.9)", (did, k, base.V7 if k == 1 else base.V9, "1.%d" % k))
        con.commit()
        self.allp = ST.load_text(con, "MBh01")
        self.ag = ST.load_text(con, "Agama2")
        self.row(con, self.allp[0], status="passed")
        self.row(con, self.allp[1], status="flagged", translation="The *s\u016bta* asked. //")
        self.row(con, self.allp[2], status="source_doubt")
        self.row(con, self.allp[3], status="flagged")
        self.row(con, self.allp[3], status="passed", engine=OPUS, created_at="2026-10-16T01:00:00+00:00")
        con.execute("UPDATE scholar_translations SET review_verdict = 'accept', reviewed_by = 'Dhruv' WHERE passage_id = ? "
                    "AND engine = ?", (self.allp[3]["id"], OPUS))
        self.row(con, self.allp[6], status="passed", src="another reading")      # stale: the Sanskrit changed since
        self.row(con, self.ag[0], status="passed", translation="From where do you come? //")
        con.commit(); con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, con, x, status="passed", engine=SONNET, created_at="2026-10-15T13:00:00+00:00", translation=None,
            src=None):
        ST.store(con, {"passage_id": x["id"], "doc_code": "Agama2" if x in self.__dict__.get("ag", []) else "MBh01",
                       "page_no": x["page"], "idx": x["idx"], "verse_ref": x["ref"],
                       "src_hash": ST.src_hash(src if src is not None else x["text"]),
                       "translation": translation or ("S%s //" % x["ref"]), "notes": "[]", "critique": "[]",
                       "status": status, "engine": engine, "judge_engine": ST.JUDGE, "cost_usd": 0.05,
                       "created_at": created_at})

    def get(self, url):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        return r

    def test_the_cards(self):
        h = self.get("/library?db=%s" % self.db).get_data(as_text=True)
        self.assertIn('SC 4</span>', h)
        self.assertIn("Scholarly English: <b>4</b> verses by claude-sonnet-5-5 and 1 other; 2 passed, 1 flagged, "
                      "1 source doubts, 1 accepted and 0 rejected by a person, 1 stale (the Sanskrit changed).", h)
        self.assertIn('<a href="/scholar/MBh01">Verse by verse</a> &middot; <a href="/scholar/MBh01/prose">as prose</a>', h)
        self.assertIn("5 verses in scholarly English</a>", h, "the header counts every text's")
        self.assertIn('data-doc="Agama2"', h, "listed, though it has no working English")
        self.assertIn('EN 0/2</span><span class="badge sc"', h)
        self.assertIn("$0.30 spent on all its rows", h)

    def test_the_cover_follows_the_rows_and_fails_quiet(self):
        con = sqlite3.connect(str(self.db))
        try:
            c = self.d._scholar_cover(con)
            self.assertEqual({k: c["MBh01"][k] for k in ("verses", "passed", "flagged", "source_doubt", "accepted",
                                                          "rejected", "stale")},
                             {"verses": 4, "passed": 2, "flagged": 1, "source_doubt": 1, "accepted": 1, "rejected": 0,
                              "stale": 1})
            self.assertEqual(c["MBh01"]["engines"], {SONNET: 3, OPUS: 1}, "each verse's latest row")
            self.row(con, self.allp[5], status="passed")
            con.commit()
            self.assertEqual(self.d._scholar_cover(con)["MBh01"]["verses"], 5, "a new row is counted at once")
        finally:
            con.close()
        bare = Path(self.td / "bare"); bare.mkdir()
        db2 = base.fixture(bare)
        con = sqlite3.connect(str(db2))
        try:
            self.assertEqual(self.d._scholar_cover(con), {}, "no scholar_translations: nothing, no error")
        finally:
            con.close()
        self.d._SCHOLAR_COVER.update(key=None)
        h = self.get("/library?db=%s" % db2).get_data(as_text=True)
        self.assertNotIn('class="badge sc"', h)
        self.assertEqual(self.d._scholar_cover(object()), {}, "any error: nothing")

    def test_the_reader(self):
        j = self.get("/api/passages/MBh01?db=%s&page=1&limit=50" % self.db).get_json()
        self.assertEqual(j["scholar_count"], 4)
        by = {p["verse_ref"]: p.get("scholar") for p in j["passages"]}
        self.assertEqual(sorted(k for k, v in by.items() if v), ["1.1.6", "1.1.7", "1.1.8", "1.1.9"])
        self.assertIsNone(by["1.1.11"], "stale: not shown")
        s = by["1.1.9"]
        self.assertEqual((s["status"], s["engine"], s["review"], s["translation"]), ("passed", OPUS, "accept", "S1.1.9 //"))
        self.assertEqual(by["1.1.6"]["href"], "/scholar/MBh01?offset=0#v-1.1.6")
        self.assertEqual(by["1.1.7"]["translation"], "The *s\u016bta* asked. //")
        self.assertEqual(by["1.1.6"]["translation"], "S1.1.6 //")
        self.assertEqual(j["passages"][0]["translation"], "Then a sage, seeing him seated. //", "the working English as it was")
        j = self.get("/api/passages/MBh01?db=%s&page=1&limit=2" % self.db).get_json()
        self.assertEqual(len([p for p in j["passages"] if p.get("scholar")]), 2, "the page's verses only")
        j = self.get("/api/passages/MBh01?db=%s&page=1&limit=50&lang=hi" % self.db).get_json()
        self.assertEqual(j["scholar_count"], 0)
        self.assertFalse(any(p.get("scholar") for p in j["passages"]), "English only")
        h = self.get("/reader/MBh01").get_data(as_text=True)
        self.assertIn("function scholarHtml(p){", h)
        self.assertIn("esc(s.translation).replace(/\\*([^*\\n]{1,80})\\*/g, '<em>$1</em>')", h)
        self.assertIn("scholarHtml(p) +", h)
        self.assertIn("' in scholarly English'", h)

    def test_the_working_english_is_not_changed(self):
        before = base.md5(self.db)
        self.get("/library?db=%s" % self.db)
        self.get("/api/passages/MBh01?db=%s&page=1&limit=50" % self.db)
        self.assertEqual(base.md5(self.db), before, "read-only")


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("dashboard.py.bak_libsch_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        pat = [sys.executable, str(SCRIPTS / "patch_library_scholar_2026_10_16.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            p = t / "scripts" / "dashboard.py"
            shutil.copy2(baks[0], p)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("dashboard.py.bak_hindi_*"))   # CLASSIFY_HINDI_2026_10_16 came after
            self.assertEqual(p.read_bytes(), (later[0] if later else SCRIPTS / "dashboard.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"function looksEnglish(t){{", b"function looksEnglish2(t){{"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 12 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(MARK, p.read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry REDEEM_2026_10_14", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_library_scholar_2026_10_16.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(MARK, b)


if __name__ == "__main__":
    unittest.main()
