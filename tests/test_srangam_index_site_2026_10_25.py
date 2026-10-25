# -*- coding: ascii -*-
"""INDEX_SITE_2026_10_25: the Srangam patch for the genealogies writes only over the exact version main had (else it
refuses, writing nothing), adds its new files once (the edge function corpus-index among them, the same as
docs/cloud/C21_corpus-index), appends Phase AQ to the audit once, and changes nothing when run again; the payload
reads the five reader functions of C21 and renders nothing from the database as HTML; C21's readers are behind the
gate and come as one row; the mirror task's patch adds the genealogies step once. Made-up checkouts in temp folders."""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
PAT = S / "patch_srangam_index_site_2026_10_25.py"
TASK_PAT = S / "patch_index_task_2026_10_25.py"
PAYLOAD = REPO / "docs" / "srangam" / "INDEX_SITE_2026-10-25"
FN = REPO / "docs" / "cloud" / "C21_corpus-index"
C21 = REPO / "docs" / "cloud" / "C21_index_site_2026-10-25.sql"
MARK = "INDEX_SITE_2026_10_25"
REPLACED = ("src/App.tsx", "src/components/corpus/CorpusNav.tsx", "src/components/navigation/CorpusMenu.tsx",
            "src/pages/corpus/CorpusNames.tsx")
NEW = ("supabase/functions/corpus-index/index.ts", "supabase/functions/corpus-index/lib.ts", "src/lib/indexSite.ts",
       "src/pages/corpus/CorpusGenealogies.tsx", "src/pages/corpus/CorpusGenealogy.tsx",
       "src/components/corpus/IndexCredits.tsx", "src/components/corpus/InTheIndexes.tsx",
       "src/__tests__/index-site.test.tsx")


@unittest.skipUnless(PAT.exists() and PAYLOAD.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        for d in ("src/lib", "src/pages/corpus", "src/components/corpus", "src/components/navigation", "src/__tests__",
                  "docs"):
            (t / d).mkdir(parents=True)
        (t / "package.json").write_text("{}\n")
        (t / "src" / "lib" / "scholarSite.ts").write_text("// SCHOLAR_SITE_2026_10_25\n")
        (t / "docs" / "RELIABILITY_AUDIT.md").write_bytes(b"# audit\r\n## Phase AP (SCHOLAR_SITE_2026_10_25)\r\n")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_refuses_a_file_changed_since(self):
        for f in REPLACED:
            (self.t / f).write_text("// another version\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("is not the version main had", r.stdout)
        self.assertFalse((self.t / "src" / "lib" / "indexSite.ts").exists(), "nothing written")

    def test_refuses_without_the_scholar_site(self):
        for f in REPLACED:
            (self.t / f).write_bytes((PAYLOAD / f).read_bytes())
        (self.t / "src" / "lib" / "scholarSite.ts").write_text("// older\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1)
        self.assertIn("apply that release first", r.stdout)

    def test_in_place_once(self):
        for f in REPLACED:   # as if main already had the payload: those are skipped, the rest is written
            (self.t / f).write_bytes((PAYLOAD / f).read_bytes().replace(b"\n", b"\r\n"))
        r = self.run_pat("--check")
        self.assertIn("CHECK OK: %d file(s)" % (len(NEW) + 1), r.stdout, r.stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout)
        for f in NEW:
            self.assertEqual((self.t / f).read_bytes(), (PAYLOAD / f).read_bytes(), f)
        a = (self.t / "docs" / "RELIABILITY_AUDIT.md").read_bytes()
        self.assertIn(b"## Phase AQ - The genealogies of the indexes", a)
        self.assertIn(b"66. A step of a genealogy", a)
        self.assertNotIn(b"\n", a.replace(b"\r\n", b""), "the audit keeps its CRLF")
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_the_edge_function_is_the_tested_one(self):
        for f in ("index.ts", "lib.ts"):
            self.assertEqual((PAYLOAD / "supabase/functions/corpus-index" / f).read_bytes(), (FN / f).read_bytes(), f)
        self.assertTrue((FN / "lib_test.ts").exists())
        self.assertTrue((FN / "_test" / "handler_test.ts").exists())


@unittest.skipUnless(PAYLOAD.exists(), "the payload is not here")
class ThePayload(unittest.TestCase):
    def read(self, f):
        return (PAYLOAD / f).read_text(encoding="utf-8")

    def test_marked_and_never_html(self):
        for f in REPLACED + NEW:
            t = self.read(f)
            self.assertIn(MARK if not f.startswith("supabase") else "C21_INDEX_SITE_2026_10_25", t, f)
            self.assertNotIn("dangerouslySetInnerHTML", t, f)
            self.assertNotIn("innerHTML", t, f)

    def test_the_five_readers_and_the_routes(self):
        lib = self.read("src/lib/indexSite.ts")
        for fn in ("corpus_reader_index_overview", "corpus_reader_index_lines", "corpus_reader_index_find",
                   "corpus_reader_index_tree", "corpus_reader_index_of_name"):
            self.assertIn("'%s'" % fn, lib)
        self.assertIn("p_down: Math.max(0, Math.min(4, down))", lib)
        self.assertIn(".normalize('NFKD').toLowerCase().replace(/\\p{M}/gu, '').replace(/[^a-z0-9]+/g, '')", lib)
        app = self.read("src/App.tsx")
        self.assertIn('<Route path="/corpus/genealogies" element={<CorpusGenealogies />} />', app)
        self.assertIn('<Route path="/corpus/genealogies/:source/:entry" element={<CorpusGenealogy />} />', app)
        self.assertLess(app.index('path="/corpus/genealogies"'), app.index('path="/corpus/:docCode"'))
        nav = self.read("src/components/corpus/CorpusNav.tsx")
        self.assertIn("label: 'Genealogies'", nav)
        self.assertIn("|scholarly|genealogies)$/", nav, "Library does not claim the genealogies")
        self.assertIn("href: '/corpus/genealogies'", self.read("src/components/navigation/CorpusMenu.tsx"))
        self.assertIn("<InTheIndexes canonical={canonical} />", self.read("src/pages/corpus/CorpusNames.tsx"))

    def test_credits_and_caution(self):
        lib = self.read("src/lib/indexSite.ts")
        self.assertIn("CC BY-NC-SA 3.0", lib)
        self.assertIn("https://creativecommons.org/licenses/by-nc-sa/3.0/", lib)
        self.assertIn("it does not by itself prove the relation", lib)
        self.assertIn("<IndexCredits", self.read("src/pages/corpus/CorpusGenealogy.tsx"))
        self.assertIn("<IndexCredits", self.read("src/pages/corpus/CorpusGenealogies.tsx"))
        self.assertTrue(PAT.read_bytes().isascii())


@unittest.skipUnless(C21.exists(), "C21 is not here")
class TheSql(unittest.TestCase):
    def test_c21(self):
        s = C21.read_text(encoding="utf-8")
        readers = re.findall(r"CREATE OR REPLACE FUNCTION public\.(corpus_reader_index_\w+)", s)
        self.assertEqual(sorted(readers), ["corpus_reader_index_find", "corpus_reader_index_lines",
                                           "corpus_reader_index_of_name", "corpus_reader_index_overview",
                                           "corpus_reader_index_tree"])
        self.assertEqual(s.count("PERFORM corpus._reader_gate();   -- C21_INDEX_SITE_2026_10_25"), 5)
        self.assertEqual(s.count("RETURNS TABLE (result jsonb)"), 3, "one row each, as callMirror reads a list")
        self.assertIn("EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f)", s)
        self.assertIn("EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO authenticated', f)", s)
        self.assertIn("ORDER BY key COLLATE \"C\"", s, "the digest in the desk's byte order")
        self.assertIn("'source', s.source, 'stated_in', s.head", s)
        self.assertNotIn("supabase_migrations", s)


@unittest.skipUnless(TASK_PAT.exists(), "the task patch is not here")
class TheTaskPatch(unittest.TestCase):
    def test_replays_once(self):
        task = S / "corpus_mirror_task.ps1"
        bak = sorted(S.glob("corpus_mirror_task.ps1.bak_indextask_*"))
        src = bak[0] if bak else task
        if MARK.encode() in src.read_bytes():
            self.skipTest("only a patched task to replay against")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir()
            shutil.copy2(src, t / "scripts" / "corpus_mirror_task.ps1")
            shutil.copy2(S / "index_sync.py", t / "scripts" / "index_sync.py")
            run = lambda *a: subprocess.run([sys.executable, str(TASK_PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            raw = (t / "scripts" / "corpus_mirror_task.ps1").read_bytes()
            self.assertTrue(raw.isascii())
            self.assertIn(b"& $py scripts\\index_sync.py --apply --if-configured", raw)
            self.assertIn(b"if ($rcm -ne 0) { exit $rcm }", raw)
            self.assertEqual(raw.count(b"\r\n") > 0, src.read_bytes().count(b"\r\n") > 0, "line endings kept")
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
