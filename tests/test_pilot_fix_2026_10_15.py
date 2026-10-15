# -*- coding: ascii -*-
"""PILOT_FIX_2026_10_15: an OCR reading's verse_ref is not a reference (page.idx); --fill-engine (this engine's own rows
as done and as context); --compare-every N (the second judge on one sentence in N, not by parity); the head to head's
spans are their verses (the old names still picked) and its tally leaves a judge's own model out. Temp files only;
nothing is called (stubs; the CLI runs are dry runs)."""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import test_claude_engine_2026_10_15 as TCE     # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "compare_this")
HAYA, SONNET, OPUS, GEM = TCE.HAYA, TCE.SONNET, "anthropic:claude-opus-5-5", "gemini:gemini-2.5-pro"
if APPLIED:
    DUEL = TCE.DUEL


def rec(pid, eng, tr="E //", status="passed", text=None, at=None, page=21, idx=1):
    return {"passage_id": pid, "doc_code": HAYA, "page_no": page, "idx": idx, "verse_ref": "21.%d" % idx,
            "src_hash": ST.src_hash(text), "translation": tr, "notes": "[]", "status": status, "engine": eng,
            "judge_engine": ST.JUDGE, "prompt_version": "scholar-v2.1+scholar-critic-v2+agama-1", "cost_usd": 0.03,
            "created_at": at or ST.now()}


@unittest.skipUnless(APPLIED, "PILOT_FIX_2026_10_15 is not applied here")
class TheRef(unittest.TestCase):
    def test_a_reading_s_number_is_not_a_reference(self):
        r = ST.ref_of
        self.assertEqual(r({"ref": "1.1.8", "engine": "gretil-bori-etext", "page": 1, "idx": 3}), "1.1.8")
        self.assertEqual(r({"ref": "4", "engine": "gemini-vision:gemini-2.5-flash", "page": 20, "idx": 10}), "20.10")
        self.assertEqual(r({"ref": "9.45", "engine": "tesseract-fallback", "page": 1, "idx": 14}), "1.14")
        self.assertEqual(r({"ref": "1.1.8", "page": 1, "idx": 3}), "1.1.8", "no engine: a reference with a dot")
        self.assertEqual(r({"ref": "4", "page": 2, "idx": 1}), "2.1")
        self.assertEqual(r({"ref": None, "page": 2, "idx": 1}), "2.1")
        with tempfile.TemporaryDirectory() as d:
            con = sqlite3.connect(str(base.fixture(Path(d))))
            self.assertEqual([r(x) for x in ST.load_text(con, "MBh01")][:4], ["1.1.6", "1.1.7", "1.1.8", "1.1.9"],
                             "the e-text's references as before")
            con.close()


@unittest.skipUnless(APPLIED, "PILOT_FIX_2026_10_15 is not applied here")
class TheFill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = TCE.agama_fixture(Path(self.tmp.name))
        import db_utils
        con = db_utils.connect(str(self.db))
        ST.ensure_schema(con)
        self.allp = ST.load_text(con, HAYA)
        for k in (0, 1):   # engine A did 21.1 and 21.2, then it was stopped
            x = self.allp[k]
            ST.store(con, rec(x["id"], OPUS, "A's English of %d //" % k, text=x["text"], idx=k + 1))
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_this_engines_rows_count_as_done_and_as_context(self):
        con = sqlite3.connect(str(self.db))
        self.assertEqual(len(ST.latest_rows(con, HAYA)), 2)
        self.assertEqual(len(ST.latest_rows(con, HAYA, OPUS)), 2)
        self.assertEqual(ST.latest_rows(con, HAYA, SONNET), {})
        b_any = ST.context(self.allp, 2, ST.latest_rows(con, HAYA))[0]
        b_own = ST.context(self.allp, 2, ST.latest_rows(con, HAYA, SONNET))[0]
        self.assertEqual([e for _y, e in b_any], ["A's English of 0 //", "A's English of 1 //"])
        self.assertEqual([e for _y, e in b_own], ["", ""], "another engine's English is not Sonnet's context")
        con.close()

    def dry(self, *extra):
        e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
        r = subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(self.db), "--doc", HAYA]
                           + list(extra), capture_output=True, text=True, encoding="utf-8", cwd=self.tmp.name, env=e)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_the_dry_run_and_its_next_line(self):
        before = base.md5(self.db)
        o = self.dry("--engine", SONNET)
        self.assertIn("chosen: 1 verse(s), 21.3 to 21.3", o)
        self.assertIn("already done, the Sanskrit unchanged: 2", o)
        o = self.dry("--engine", SONNET, "--fill-engine", "--compare-every", "5")
        self.assertIn("chosen: 3 verse(s), 21.1 to 21.3", o)
        self.assertIn("--fill-engine: only %s's own rows count as done and as the context" % SONNET, o)
        self.assertIn("the second judge: one sentence in 5 (--compare-every)", o)
        self.assertIn("--engine %s --fill-engine --compare-every 5 --yes --max-usd" % SONNET, o)
        o = self.dry("--engine", OPUS, "--fill-engine")
        self.assertIn("chosen: 1 verse(s), 21.3 to 21.3", o)
        self.assertEqual(base.md5(self.db), before, "dry runs write nothing")


@unittest.skipUnless(APPLIED, "PILOT_FIX_2026_10_15 is not applied here")
class TheCompareSample(unittest.TestCase):
    def test_one_in_n_by_hash_not_by_parity(self):
        a1, a4 = types.SimpleNamespace(compare_every=1), types.SimpleNamespace(compare_every=4)
        self.assertTrue(all(ST.compare_this(a1, {"id": i}) for i in range(50)))
        self.assertTrue(ST.compare_this(types.SimpleNamespace(), {"id": 7}), "no option: every one, as before")
        got = [i for i in range(1, 801) if ST.compare_this(a4, {"id": i})]
        self.assertTrue(0.17 < len(got) / 800 < 0.33, len(got))
        even = sum(1 for i in got if i % 2 == 0) / len(got)
        self.assertTrue(0.35 < even < 0.65, "the order A/B (by parity) stays mixed: %.2f" % even)
        self.assertEqual(got, [i for i in range(1, 801) if ST.compare_this(a4, {"id": i})], "the same each time")

    def test_one_unit_asks_the_second_judge_only_where_chosen(self):
        with tempfile.TemporaryDirectory() as d:
            db = base.fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            allp = ST.load_text(con, "MBh01")
            meta = ST.doc_meta(con, "MBh01", allp)
            i = next(k for k, x in enumerate(allp) if x["ref"] == "1.1.8")
            calls = []
            keep = ST.compare
            ST.compare = lambda asker, b, s, w, pid: calls.append(pid) or None
            try:
                for every, want in ((1, 1), (10 ** 6, 0)):
                    n = 1 if every == 1 else next(k for k in range(10 ** 6, 10 ** 6 + 50)
                                                  if not ST.compare_this(types.SimpleNamespace(compare_every=k), allp[i]))
                    a = base.args(db, compare=True, compare_every=n)
                    s = base.Stub([base.draft("The suta said. //")], [base.ACCEPT], [(5, 5), (4, 4)])
                    calls.clear()
                    ST.one_unit(a, allp, [i], meta, {}, s, con, 0.01)
                    self.assertEqual(len(calls), want, every)
            finally:
                ST.compare = keep
            con.close()


@unittest.skipUnless(APPLIED, "PILOT_FIX_2026_10_15 is not applied here")
class TheDuel(unittest.TestCase):
    def duel_row(self, con, sref, pids, judge, rid, best, verdict=None):
        DUEL.ensure_schema(con)
        DUEL.store(con, HAYA, sref, pids, judge, list(rid), rid, verdict or {"best": best, "ranking": list(rid)}, best, 0.01)

    def test_a_span_is_its_verses(self):
        with tempfile.TemporaryDirectory() as d:
            con = sqlite3.connect(str(Path(d) / "x.db"))
            rid = {GEM: [1, 2], SONNET: [3, 4]}
            self.duel_row(con, "20.7-4", [11, 12], GEM, rid, SONNET)
            self.assertTrue(DUEL.already(con, HAYA, "20.7-20.10", GEM, rid), "the same rows, whatever the name")
            self.assertFalse(DUEL.already(con, HAYA, "20.7-20.10", OPUS, rid))
            self.assertFalse(DUEL.already(con, HAYA, "20.7-20.10", GEM, {GEM: [1, 2], SONNET: [3, 5]}))
            self.duel_row(con, "20.7-20.10", [11, 12], OPUS, rid, SONNET)
            alias = {}
            c = DUEL.canonical(con, HAYA, alias)
            self.assertEqual(list(c), ["20.7-20.10"], "one span on the page")
            self.assertEqual(alias, {"20.7-4": "20.7-20.10", "20.7-20.10": "20.7-20.10"})
            a = types.SimpleNamespace(doc=HAYA, pick="20.7-4=1", by="D")
            self.assertEqual(DUEL.pick(con, a), 1, "its old name is picked too")
            row = con.execute("SELECT span_ref, best FROM scholar_duels WHERE judge_engine = 'person:D'").fetchone()
            self.assertEqual(row, ("20.7-20.10", DUEL.person_order(HAYA, "20.7-20.10", rid)[0]))
            con.close()

    def test_the_best_with_the_judge_s_own_model_left_out(self):
        v = {"best": OPUS, "ranking": [OPUS + "@high", OPUS, SONNET, GEM]}
        self.assertEqual(DUEL.best_without_own(v, OPUS), SONNET, "any effort of its own model")
        self.assertEqual(DUEL.best_without_own(v, GEM), OPUS + "@high")
        self.assertIsNone(DUEL.best_without_own({"best": "equal", "ranking": [OPUS, SONNET]}, GEM))
        self.assertIsNone(DUEL.best_without_own({"best": OPUS, "ranking": [OPUS]}, OPUS))

    def test_the_tally_counts_it(self):
        with tempfile.TemporaryDirectory() as d:
            db, allp = TCE.TheDuel.fixture(None, d)
            judges = {}
            keep = DUEL.make_judge
            DUEL.make_judge = lambda eng, a, meta: judges.setdefault(eng, TCE.StubJudge())
            cwd = os.getcwd(); os.chdir(d)
            try:
                self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--yes", "--max-usd", "1"]), 0)
                self.assertEqual(DUEL.main(["--db", str(db), "--doc", HAYA, "--report", "--named"]), 0)
            finally:
                os.chdir(cwd)
                DUEL.make_judge = keep
            page = (Path(d) / "exports" / ("scholar_duel_%s.html" % HAYA)).read_text(encoding="utf-8")
            self.assertIn("best, its own model left out", page)
            row = re.search(r"<tr><td>%s</td>(.*?)</tr>" % re.escape(SONNET), page).group(1)
            nums = re.findall(r'<td class="num">([^<]*)</td>', row)
            # judges sorted: claude-opus-5-5 (not a contestant: its best stands), then gemini-2.5-pro (its own left out)
            con = sqlite3.connect(str(db))
            rows = con.execute("SELECT judge_engine, verdict FROM scholar_duels ORDER BY id").fetchall()
            con.close()
            want = {j: sum(1 for jj, v in rows if jj == j and DUEL.best_without_own(json.loads(v), j) == SONNET)
                    for j in (OPUS, GEM)}
            self.assertEqual(want[GEM], 2, "the Gemini judge's own left out: Sonnet is its best in both spans")
            self.assertEqual((int(nums[6]), int(nums[11])), (want[OPUS], want[GEM]))


class ThePatcher(unittest.TestCase):
    FILES = ("scholar_translate.py", "scholar_duel.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_pilotfix_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts")
        pat = [sys.executable, str(SCRIPTS / "patch_pilot_fix_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                later = sorted(SCRIPTS.glob(f + ".bak_audit_*"))   # AUDIT_2026_10_15 came after (scholar_translate.py)
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f, b in baks.items():
                shutil.copy2(b[0], t / "scripts" / f)
            p = t / "scripts" / "scholar_duel.py"
            p.write_bytes(p.read_bytes().replace(b"def Counter_(it) -> dict:", b"def Counter2(it) -> dict:"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("scholar_duel.py: anchor 9 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"PILOT_FIX", (t / "scripts" / "scholar_translate.py").read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry CLAUDE_ENGINE_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_pilot_fix_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"PILOT_FIX_2026_10_15", b)
        if APPLIED:
            for f in ThePatcher.FILES:
                b = (SCRIPTS / f).read_bytes()
                self.assertTrue(all(x < 128 for x in b), f); self.assertIn(b"PILOT_FIX_2026_10_15", b)


if __name__ == "__main__":
    unittest.main()
