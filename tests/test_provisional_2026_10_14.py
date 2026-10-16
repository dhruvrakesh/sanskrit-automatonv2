# -*- coding: ascii -*-
"""PROVISIONAL_2026_10_14: REDEEM_FIX_2026_10_14 (redeem.py --doc no longer calls every other text's spend gone);
PROVISIONAL_EN_2026_10_14 (the Srangam reader marks English made from a misread reading: its patcher, refusing
anything but the version main has); C15_READER_GUARD_2026_10_14 (the reader's meaning search leaves retired
passages out: the SQL's guard, marker and rollback agree). Temp files only, never data/context.db."""
import importlib.util, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TheRedeemFix(unittest.TestCase):
    def test_one_text_does_not_call_the_others_gone(self):
        import test_redeem_2026_10_14 as base
        with tempfile.TemporaryDirectory() as td:
            fx = base.corpus(Path(td))
            r = subprocess.run([sys.executable, str(SCRIPTS / "redeem.py"), "--db", str(fx["db"]), "--inbox",
                                str(fx["inbox"]), "--raw", str(fx["raw"]), "--verdicts", str(fx["verdicts"]), "--chart",
                                str(fx["chart"]), "--doc", "Mixed", "--out", str(Path(td) / "o.json")],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("no longer in the database", r.stdout)
            rd = load("redeem_provisional", SCRIPTS / "redeem.py")
            res = rd.ledger(base.args(fx, only="Mixed"))
            self.assertAlmostEqual(res["totals"]["spent_gone"], 0.003, places=6, msg="only Vanished is not in docs")
            self.assertEqual([t["doc"] for t in res["texts"]], ["Mixed"])
            con = sqlite3.connect(str(fx["db"]))
            con.execute("UPDATE docs SET code='Mixed-RETIRED' WHERE code='Mixed'")
            con.commit(); con.close()
            res = rd.ledger(base.args(fx))
            self.assertAlmostEqual(res["totals"]["spent_gone"], 0.003 + 0.075, places=6, msg="a retired text is gone")

    def test_the_patcher_replays_on_the_release(self):
        baks = sorted(SCRIPTS.glob("redeem.py.bak_redeemfix_*"))
        if not baks:
            self.skipTest("no pre-patch copy beside the script (the patcher's backup) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            shutil.copy2(baks[0], t / "scripts" / "redeem.py")
            pat = [sys.executable, str(SCRIPTS / "patch_redeem_fix_2026_10_14.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            later = sorted(SCRIPTS.glob("redeem.py.bak_readyprice_*"))   # READY_PRICE_2026_10_16 came after
            self.assertEqual((t / "scripts" / "redeem.py").read_bytes(),
                             (later[0] if later else SCRIPTS / "redeem.py").read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            p = t / "scripts" / "redeem.py"
            shutil.copy2(baks[0], p)
            p.write_bytes(p.read_bytes().replace(b"    if t.get(\"spent_gone\"):\n", b"    if t.get('spent_gone'):\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("this is not the file released", r.stdout)
            self.assertNotIn(b"REDEEM_FIX_2026_10_14", p.read_bytes(), "nothing written")
            p.write_bytes(b"# an older redeem.py\n")
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("does not carry REDEEM_2026_10_14", r.stdout)


class TheSrangamPatcher(unittest.TestCase):
    PAY = REPO / "docs" / "srangam" / "PROVISIONAL_EN_2026-10-14"
    PAT = SCRIPTS / "patch_srangam_provisional_2026_10_14.py"

    def root(self, td: Path, display=b"// READER_NAV_2026_10_08\nexport const x = 1;\n", audit=True):
        (td / "src" / "lib").mkdir(parents=True); (td / "src" / "components" / "reader").mkdir(parents=True)
        (td / "src" / "__tests__").mkdir(); (td / "docs").mkdir()
        (td / "src" / "App.tsx").write_text("x"); (td / "package.json").write_text("{}")
        (td / "src" / "lib" / "corpusDisplay.ts").write_bytes(display)
        (td / "src" / "components" / "reader" / "PassageBlock.tsx").write_bytes(b"export default 1;\n")
        if audit:
            (td / "docs" / "RELIABILITY_AUDIT.md").write_bytes(b"# Audit\r\n## Phase AE (CORNER_UX_U1_2026_10_10)\r\n")

    def run_(self, td, *a):
        return subprocess.run([sys.executable, str(self.PAT)] + list(a), cwd=str(td), capture_output=True, text=True)

    def test_it_refuses_what_main_does_not_have(self):
        with tempfile.TemporaryDirectory() as d:
            td = Path(d)
            self.assertEqual(self.run_(td, "--check").returncode, 2, "not the Srangam root")
            self.root(td, display=b"export const x = 1;\n")
            r = self.run_(td, "--check")
            self.assertEqual(r.returncode, 1); self.assertIn("has no READER_NAV_2026_10_08", r.stdout)
        with tempfile.TemporaryDirectory() as d:
            td = Path(d); self.root(td)
            r = self.run_(td)
            self.assertEqual(r.returncode, 1); self.assertIn("is not the version main had", r.stdout)
            self.assertFalse((td / "src" / "__tests__" / "reader-provisional.test.tsx").exists(), "all or nothing")

    def test_in_place_already_and_the_audit(self):
        with tempfile.TemporaryDirectory() as d:
            td = Path(d); self.root(td)
            for rel in ("src/lib/corpusDisplay.ts", "src/components/reader/PassageBlock.tsx"):
                data = (self.PAY / rel).read_bytes()
                (td / rel).write_bytes(data.replace(b"\n", b"\r\n") if rel.endswith("PassageBlock.tsx") else data)
            r = self.run_(td)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("skip src/components/reader/PassageBlock.tsx (already PROVISIONAL_EN_2026_10_14)", r.stdout)
            self.assertEqual((td / "src/__tests__/reader-provisional.test.tsx").read_bytes(),
                             (self.PAY / "src/__tests__/reader-provisional.test.tsx").read_bytes())
            a = (td / "docs" / "RELIABILITY_AUDIT.md").read_bytes()
            self.assertIn(b"\r\n## Phase AF - English made from a misread reading", a)
            self.assertEqual(a.count(b"\n"), a.count(b"\r\n"), "its CRLF kept")
            self.assertIn("Nothing to do", self.run_(td).stdout)

    def test_the_payload(self):
        d = (self.PAY / "src/lib/corpusDisplay.ts").read_text(encoding="utf-8")
        self.assertIn("PROVISIONAL_EN_2026_10_14", d)
        self.assertIn("const DEVANAGARI_SIGN = /[\\u0900-\\u097F]/g;", d)
        self.assertIn("const LATIN_WORD = /(^|[^A-Za-z])[A-Za-z][A-Za-z'!\"]+/;", d)
        self.assertIn(".length >= 8 && LATIN_WORD.test(s)", d)
        rd = (SCRIPTS / "redeem.py").read_text(encoding="ascii")
        self.assertIn("JUNK = re.compile(r\"(?<![A-Za-z])[A-Za-z][A-Za-z'!\\\"]{1,}\")", rd, "the same rule")
        self.assertIn("len(DEV.findall(text or \"\")) >= 8", rd)
        pb = (self.PAY / "src/components/reader/PassageBlock.tsx").read_text(encoding="utf-8")
        self.assertIn("provisional English", pb); self.assertIn("madeFromMisread(p.sanskrit)", pb)


class TheReaderGuard(unittest.TestCase):
    def test_the_sql(self):
        s = (REPO / "docs" / "cloud" / "C15_reader_retired_guard_2026-10-14.sql").read_text(encoding="ascii")
        self.assertIn("\nBEGIN;\n", s); self.assertTrue(s.rstrip().endswith("COMMIT;"))
        self.assertIn("'public.corpus_reader_similar(text, integer, integer, integer)'", s)
        self.assertIn("'public.corpus_reader_match(public.halfvec, integer, text[])'", s)
        mark = re.search(r"mark constant text := '(.*?)';", s).group(1)
        self.assertEqual(mark, "  -- C15_READER_GUARD_2026_10_14")
        self.assertIn("replace(def, ' AND p.retired_at IS NULL%s', '')" % mark, s, "the rollback undoes it exactly")
        old = re.search(r"old  constant text := '(.*?)';", s).group(1)
        c5 = (REPO / "docs" / "cloud" / "C5_corpus_reader_2026-10-08.sql").read_text(encoding="utf-8")
        for fn in ("corpus_reader_similar", "corpus_reader_match"):
            body = re.search(r"CREATE OR REPLACE FUNCTION public\.%s\(.*?END \$\$;" % fn, c5, re.S).group(0)
            self.assertEqual(body.count(old), 1, fn)
        c = (REPO / "docs" / "cloud" / "C15_checks_2026-10-14.sql").read_text(encoding="ascii")
        self.assertEqual(c.count("SELECT "), 4); self.assertNotIn("CREATE", c.replace("-- C15 checks", ""))


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for p, mark in ((SCRIPTS / "patch_redeem_fix_2026_10_14.py", b"REDEEM_FIX_2026_10_14"),
                        (SCRIPTS / "patch_srangam_provisional_2026_10_14.py", b"PROVISIONAL_EN_2026_10_14"),
                        (SCRIPTS / "redeem.py", b"REDEEM_FIX_2026_10_14"), (Path(__file__), b"PROVISIONAL_2026_10_14")):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(mark, b)


if __name__ == "__main__":
    unittest.main()
