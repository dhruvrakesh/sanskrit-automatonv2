# -*- coding: ascii -*-
"""B2_SITE_2026_10_28 and X1C_SITE_2026_10_28: the Srangam patch for the historian's view and the search in the
scholarly English writes only over the exact version main had (else it refuses, writing nothing), adds its new files
once, appends Phase AR to the audit once (its line endings kept), and changes nothing when run again; the edge
function is the tested one (docs/cloud/C23_corpus-index); the payload reads C23's and C24's functions, renders
nothing from the database as HTML, credits the work apart from GRETIL's texts and says before C24 that the search is
not switched on; C23 keeps the tree's texts as C21 gave them and C24's reader is behind the gate. Made-up checkouts
in temp folders."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
PAT = S / "patch_srangam_b2_site_2026_10_28.py"
PAYLOAD = REPO / "docs" / "srangam" / "B2_SITE_2026-10-28"
FN = REPO / "docs" / "cloud" / "C23_corpus-index"
C23 = REPO / "docs" / "cloud" / "C23_index_claims_2026-10-28.sql"
C24 = REPO / "docs" / "cloud" / "C24_scholar_search_2026-10-28.sql"
MARK = "B2_SITE_2026_10_28"
X1C = "X1C_SITE_2026_10_28"
REPLACED = ("src/lib/indexSite.ts", "src/pages/corpus/CorpusGenealogy.tsx", "src/pages/corpus/CorpusGenealogies.tsx",
            "src/components/corpus/InTheIndexes.tsx", "src/components/corpus/IndexCredits.tsx", "src/lib/scholarSite.ts",
            "src/pages/corpus/CorpusHome.tsx", "src/pages/corpus/CorpusScholarly.tsx",
            "supabase/functions/corpus-index/lib.ts", "supabase/functions/corpus-index/index.ts")
NEW = ("src/components/corpus/ScholarClaims.tsx", "src/components/corpus/ScholarSearch.tsx",
       "src/__tests__/b2-site.test.tsx")


@unittest.skipUnless(PAT.exists() and PAYLOAD.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        for d in ("src/lib", "src/pages/corpus", "src/components/corpus", "src/__tests__", "docs",
                  "supabase/functions/corpus-index"):
            (t / d).mkdir(parents=True)
        (t / "package.json").write_text("{}\n")
        (t / "src" / "App.tsx").write_text("// app\n")
        (t / "docs" / "RELIABILITY_AUDIT.md").write_bytes(b"# audit\r\n## Phase AQ (INDEX_SITE_2026_10_25)\r\n")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_refuses_a_file_changed_since(self):
        for f in REPLACED:
            (self.t / f).write_text("// another version SCHOLAR_SITE_2026_10_25\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("is not the version main had", r.stdout)
        self.assertFalse((self.t / "src" / "components" / "corpus" / "ScholarClaims.tsx").exists(), "nothing written")

    def test_refuses_without_the_scholar_site(self):
        for f in REPLACED:
            (self.t / f).write_text("// older\n")
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
        self.assertIn(b"## Phase AR - The historian's view beside the genealogies", a)
        self.assertIn(b"67. A scholar's view is shown only from a work in the public domain", a)
        self.assertIn(b"68. A search in the scholarly English", a)
        self.assertNotIn(b"\n", a.replace(b"\r\n", b""), "the audit keeps its CRLF")
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_the_edge_function_is_the_tested_one(self):
        for f in ("index.ts", "lib.ts"):
            self.assertEqual((PAYLOAD / "supabase/functions/corpus-index" / f).read_bytes(), (FN / f).read_bytes(), f)
        self.assertIn('"claims"', (FN / "lib.ts").read_text(encoding="utf-8"))
        self.assertTrue((FN / "lib_test.ts").exists())
        self.assertTrue((FN / "_test" / "handler_test.ts").exists())


@unittest.skipUnless(PAYLOAD.exists(), "the payload is not here")
class ThePayload(unittest.TestCase):
    def read(self, f):
        return (PAYLOAD / f).read_text(encoding="utf-8")

    def test_marked_and_never_html(self):
        for f in REPLACED + NEW:
            t = self.read(f)
            want = "C23_INDEX_CLAIMS_2026_10_28" if f.startswith("supabase") else (
                X1C if f in ("src/lib/scholarSite.ts", "src/pages/corpus/CorpusHome.tsx",
                             "src/pages/corpus/CorpusScholarly.tsx", "src/components/corpus/ScholarSearch.tsx") else MARK)
            self.assertIn(want, t, f)
            self.assertNotIn("dangerouslySetInnerHTML", t, f)
            self.assertNotIn("innerHTML", t, f)

    def test_the_functions_and_the_quiet_before(self):
        site = self.read("src/lib/scholarSite.ts")
        self.assertIn("SCHOLAR_SEARCH = 'corpus_reader_scholar_search'", site)
        self.assertIn("functionMissing(r, SCHOLAR_SEARCH)", site)
        self.assertIn("k: Math.max(1, Math.min(50, k))", site)
        lib = self.read("src/lib/indexSite.ts")
        for k in ("scholars?: ScholarView[]", "scholar?: string", "claims?: Record<string, Claim>", "claims_n?: number",
                  "works?: WorkInfo[]"):
            self.assertIn(k, lib, "optional: before C23 nothing changes")
        self.assertIn("'In the scholarly English'", self.read("src/pages/corpus/CorpusHome.tsx"))
        self.assertIn("<ScholarSearch docs={r.rows} />", self.read("src/pages/corpus/CorpusScholarly.tsx"))
        g = self.read("src/pages/corpus/CorpusGenealogy.tsx")
        self.assertIn("queryKey: ['mirror', 'names', 'exact', c]", g, "the name page's own key")
        self.assertIn("queryKey: ['mirror', 'index-of-name', c]", g, "InTheIndexes' own key")
        self.assertIn("<IndexCredits texts={texts} works={works} />", g)
        self.assertIn("being named together is not a kinship", g)

    def test_credits_and_rights(self):
        lib = self.read("src/lib/indexSite.ts")
        self.assertIn("Only works in the public domain are shown", lib)
        self.assertIn("The historians:", self.read("src/components/corpus/IndexCredits.tsx"))
        self.assertTrue(PAT.read_bytes().isascii())


DENO = shutil.which("deno")


@unittest.skipUnless(DENO and FN.exists(), "deno is not on PATH (npm i -g deno, or https://deno.com)")
class TheEdgeFunctionTests(unittest.TestCase):
    """The function's own Deno tests: no network (--no-remote), the database and gateway faked."""
    def deno(self, *a):
        return subprocess.run([DENO, "test", "--no-remote", "--allow-env"] + list(a), cwd=str(FN), capture_output=True,
                              text=True, timeout=300)

    def test_lib(self):
        r = self.deno("lib_test.ts")
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])

    def test_handler(self):
        r = self.deno("--import-map=_test/import_map.json", "_test/handler_test.ts")
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])


@unittest.skipUnless(C23.exists() and C24.exists(), "C23 or C24 is not here")
class TheSql(unittest.TestCase):
    def test_c23_keeps_the_texts_apart(self):
        s = C23.read_text(encoding="utf-8")
        self.assertNotIn("kind IN ('text', 'work')", s)
        self.assertIn("'works', coalesce((SELECT jsonb_object_agg(t.code", s)
        self.assertEqual(s.count("CREATE OR REPLACE FUNCTION"), 10)
        self.assertNotIn("supabase_migrations", s)

    def test_c24_behind_the_gate(self):
        s = C24.read_text(encoding="utf-8")
        self.assertIn("PERFORM corpus._reader_gate();   -- C24_SCHOLAR_SEARCH_2026_10_28", s)
        self.assertIn("LIMIT least(greatest(coalesce(k, 20), 1), 50)", s)
        self.assertIn("t.retired_at IS NULL", s)
        self.assertIn("d.retired_at IS NULL", s)
        self.assertIn("p.retired_at IS NULL", s)
        self.assertRegex(s, r"GRANT EXECUTE ON FUNCTION public\.corpus_reader_scholar_search\(text, integer, text\) TO authenticated")
        self.assertNotIn("supabase_migrations", s)


if __name__ == "__main__":
    unittest.main()
