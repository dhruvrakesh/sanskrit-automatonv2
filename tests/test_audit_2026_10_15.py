# -*- coding: ascii -*-
"""AUDIT_2026_10_15: --audit-every (in a Claude run, Gemini's critic reads the last version of one sentence in N, and
its reading decides the status) and --status (what a text has, per engine; free, read-only). Temp files only; nothing
is called (stubs; the CLI runs are dry runs or read-only)."""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_scholar_2026_10_14 as base          # noqa: E402
import test_claude_engine_2026_10_15 as TCE     # noqa: E402

ST = base.ST
APPLIED = hasattr(ST, "audit_this")
HAYA, SONNET, GEM = TCE.HAYA, TCE.SONNET, "gemini:gemini-2.5-pro"
MAJOR = {"fidelity": 3, "completeness": 5, "issues": [{"type": "misreading", "where": "w", "fix": "f", "severity": "major"}],
         "verdict": "revise", "by": GEM}
ACCEPT = {"fidelity": 5, "completeness": 5, "issues": [], "verdict": "accept", "by": GEM}
SOURCE = {"fidelity": 4, "completeness": 4, "issues": [{"type": "source", "where": "w", "fix": "f", "severity": "major"}],
          "verdict": "revise", "by": GEM}


class Auditing(base.Stub):
    """A Claude run's asker: the draft and the critic scripted; audit() gives what it is told (an Exception raises)."""

    def __init__(self, audit, *a):
        super().__init__(*a)
        self.audits, self.answer = 0, audit

    def audit(self, b, cur):
        self.audits += 1
        self.spent += 0.03
        return dict(self.answer) if isinstance(self.answer, dict) else self.answer


@unittest.skipUnless(APPLIED, "AUDIT_2026_10_15 is not applied here")
class TheChoice(unittest.TestCase):
    def test_one_in_n_by_its_own_hash(self):
        self.assertFalse(ST.audit_this(types.SimpleNamespace(audit_every=0), {"id": 5}))
        self.assertFalse(ST.audit_this(types.SimpleNamespace(), {"id": 5}), "off unless asked")
        self.assertTrue(all(ST.audit_this(types.SimpleNamespace(audit_every=1), {"id": i}) for i in range(30)))
        a = types.SimpleNamespace(audit_every=5, compare_every=5)
        au = {i for i in range(1, 1001) if ST.audit_this(a, {"id": i})}
        cm = {i for i in range(1, 1001) if ST.compare_this(a, {"id": i})}
        self.assertTrue(140 < len(au) < 260, len(au))
        self.assertLess(len(au & cm), 0.5 * len(au), "not the same sentences as the second judge's")


@unittest.skipUnless(APPLIED, "AUDIT_2026_10_15 is not applied here")
class TheAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = base.fixture(Path(self.tmp.name))
        import db_utils
        self.con = db_utils.connect(str(self.db))
        ST.ensure_schema(self.con)
        self.allp = ST.load_text(self.con, "MBh01")
        self.meta = ST.doc_meta(self.con, "MBh01", self.allp)
        self.i = next(k for k, x in enumerate(self.allp) if x["ref"] == "1.1.8")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def unit(self, asker, every=1):
        a = base.args(self.db, compare=False, audit_every=every, engine=SONNET)
        return ST.one_unit(a, self.allp, [self.i], self.meta, {}, asker, self.con, 0.01)[0]

    def stub(self, audit):
        return Auditing(audit, [base.draft("The suta said. //")], [base.ACCEPT], [(5, 5), (5, 5)])

    def test_its_reading_decides_the_status(self):
        s = self.stub(MAJOR)
        r = self.unit(s)
        self.assertEqual((s.audits, r["status"], r["_audit"]), (1, "flagged", "revise"))
        crit = json.loads(r["critique"])
        self.assertEqual(len(crit), 2); self.assertEqual(crit[-1]["by"], GEM)
        self.assertEqual(r["passes"], 1, "it does not revise")
        self.assertEqual(self.unit(self.stub(ACCEPT))["status"], "passed")
        self.assertEqual(self.unit(self.stub(SOURCE))["status"], "source_doubt")
        r = self.unit(self.stub(None))
        self.assertEqual((r["status"], r["_audit"]), ("passed", None), "no answer: the critic's reading stands")
        self.assertAlmostEqual(r["cost_usd"], 0.01 + 0.01 + 0.03 + 0.0004, places=6, msg="its cost is the row's")

    def test_only_when_asked_and_only_a_claude_run(self):
        s = self.stub(MAJOR)
        self.assertEqual(self.unit(s, every=0)["status"], "passed"); self.assertEqual(s.audits, 0)
        g = base.Stub([base.draft("The suta said. //")], [base.ACCEPT], [(5, 5), (5, 5)])
        self.assertEqual(self.unit(g, every=1)["status"], "passed", "a Gemini run has no audit")

    def test_claude_audit_asks_gemini_s_critic(self):
        class Gem:
            a = types.SimpleNamespace(engine=GEM)
            def __init__(self, answer):
                self.answer, self.kinds = answer, []
            def ask(self, kind, m):
                self.kinds.append(kind)
                if isinstance(self.answer, Exception):
                    raise self.answer
                return self.answer, 0.03
        c = object.__new__(ST.Claude)
        c.gem = Gem({"fidelity": 4, "completeness": 5, "issues": [], "verdict": "accept"})
        got = c.audit("BASE", {"translation": "T //", "notes": [], "doubts": ""})
        self.assertEqual((got["verdict"], got["by"], c.gem.kinds), ("accept", GEM, ["critic"]))
        c.gem = Gem(ST.CallFailed("down"))
        self.assertIsNone(c.audit("BASE", {"translation": "T //", "notes": [], "doubts": ""}))

    def test_the_pages_name_the_audit(self):
        r = self.unit(self.stub(MAJOR))
        ST.store(self.con, r)
        page = ST.render_doc(self.con, "MBh01", limit=None)
        self.assertIn("The audit by %s" % GEM, page)
        self.assertIn("Critic, reading 1", page)


@unittest.skipUnless(APPLIED, "AUDIT_2026_10_15 is not applied here")
class TheStatus(unittest.TestCase):
    def test_what_a_text_has_per_engine(self):
        with tempfile.TemporaryDirectory() as d:
            db = TCE.agama_fixture(Path(d))
            import db_utils
            con = db_utils.connect(str(db))
            ST.ensure_schema(con)
            allp = ST.load_text(con, HAYA)
            mk = lambda x, eng, st, crit="[]", h=None: ST.store(con, {
                "passage_id": x["id"], "doc_code": HAYA, "page_no": x["page"], "idx": x["idx"], "verse_ref": ST.ref_of(x),
                "src_hash": h or ST.src_hash(x["text"]), "translation": "E //", "status": st, "engine": eng,
                "critique": crit, "cost_usd": 0.04, "created_at": "2026-10-15T12:00:00+00:00"})
            mk(allp[0], SONNET, "passed")
            mk(allp[1], SONNET, "flagged", json.dumps([base.ACCEPT, MAJOR]))
            mk(allp[2], GEM, "passed", h="0" * 16)
            con.close()
            before = base.md5(db)
            e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
            r = subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc", HAYA,
                                "--status"], capture_output=True, text=True, encoding="utf-8", cwd=d, env=e)
            o = r.stdout
            self.assertEqual(r.returncode, 0, o + r.stderr)
            self.assertIn("  %s: 2 of 3 verses (67%%); passed 1, flagged 1, source doubts 0, stale 0; audited 1; $0.080 "
                          "spent" % SONNET, o)
            self.assertIn("  %s: 1 of 3 verses (33%%); passed 0, flagged 0, source doubts 0, stale 1; audited 0" % GEM, o)
            self.assertIn("the Claude credit: $0.00 spent of $190.00", o)
            self.assertIn("VERDICT: 2 engine(s) here", o)
            self.assertEqual(base.md5(db), before, "read-only")

    def test_the_dry_run_and_its_next_line(self):
        with tempfile.TemporaryDirectory() as d:
            db = TCE.agama_fixture(Path(d))
            e = dict(os.environ, PYTHONIOENCODING="utf-8", ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "scholar_translate.py"), "--db", str(db), "--doc",
                                             HAYA] + list(x), capture_output=True, text=True, encoding="utf-8", cwd=d,
                                            env=e).stdout
            o = run("--engine", SONNET, "--audit-every", "10", "--min-quality", "0.5")
            self.assertIn("the audit: %s reads one sentence in 10 after the critic; its reading decides the status" % GEM, o)
            self.assertIn("--engine %s --audit-every 10 --min-quality 0.50 --yes --max-usd" % SONNET, o)
            o = run("--audit-every", "10")
            self.assertIn("--audit-every is for a Claude engine: nothing is audited", o)


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = sorted(SCRIPTS.glob("scholar_translate.py.bak_audit_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script")
        pat = [sys.executable, str(SCRIPTS / "patch_audit_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            p = t / "scripts" / "scholar_translate.py"
            shutil.copy2(baks[0], p)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("scholar_translate.py.bak_runfix_*"))   # RUN_FIX_2026_10_15 came after
            self.assertEqual(p.read_bytes(), (later[0] if later else SCRIPTS / "scholar_translate.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"    if a.review or a.term:\n", b"    if a.review:\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 11 found 0 times (want 1): this is not the file released", r.stdout)
            self.assertNotIn(b"AUDIT_2026", p.read_bytes(), "all or nothing")
            p.write_bytes(b"# an older one\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry PILOT_FIX_2026_10_15", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p in (SCRIPTS / "patch_audit_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"AUDIT_2026_10_15", b)
        if APPLIED:
            b = (SCRIPTS / "scholar_translate.py").read_bytes()
            self.assertTrue(all(x < 128 for x in b)); self.assertIn(b"AUDIT_2026_10_15", b)


if __name__ == "__main__":
    unittest.main()
