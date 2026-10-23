# -*- coding: ascii -*-
"""NAME_LINKS_SITE_2026_10_23 and NAME_LINKS_C20_2026_10_23: the Srangam patch for "Named together with" on a name's
page writes only over the exact version main had (else it refuses, writing nothing), adds its test once, appends Phase
AO to the audit once, and changes nothing when run again; docs/cloud/C20 counts the pairs on the site with the desk's
list rule, behind the reader gate, refreshed nightly. A made-up Srangam checkout in a temp folder."""
import hashlib, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_srangam_name_links_2026_10_23.py"
PAYLOAD = REPO / "docs" / "srangam" / "NAME_LINKS_SITE_2026-10-23"
C20 = REPO / "docs" / "cloud" / "C20_name_links_2026-10-23.sql"
MARK = "NAME_LINKS_SITE_2026_10_23"
FILES = ("src/lib/corpusLibrary.ts", "src/pages/corpus/CorpusNames.tsx")


@unittest.skipUnless(PAT.exists() and PAYLOAD.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        for d in ("src/lib", "src/pages/corpus", "src/__tests__", "docs"):
            (t / d).mkdir(parents=True)
        (t / "src" / "App.tsx").write_text("app\n")
        (t / "package.json").write_text("{}\n")
        (t / "src" / "lib" / "corpusMirror.ts").write_text("// SCHOLAR_READER_2026_10_18\n")
        (t / "docs" / "RELIABILITY_AUDIT.md").write_bytes(b"# audit\r\n## Phase AN (SEO_GSC_2026_10_22)\r\n")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_refuses_a_file_changed_since(self):
        for f in FILES:
            (self.t / f).write_text("// another version\n")
        r = self.run_pat()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("is not the version main had", r.stdout)
        self.assertFalse((self.t / "src" / "__tests__" / "corpus-name-links.test.tsx").exists(), "nothing written")

    def test_in_place_once(self):
        for f in FILES:   # as if main already had the payload: the files are skipped, the rest is written
            (self.t / f).write_bytes((PAYLOAD / f).read_bytes().replace(b"\n", b"\r\n"))
        r = self.run_pat("--check")
        self.assertIn("CHECK OK: 2 file(s)", r.stdout, r.stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.t / "src" / "__tests__" / "corpus-name-links.test.tsx").exists())
        a = (self.t / "docs" / "RELIABILITY_AUDIT.md").read_bytes()
        self.assertIn(b"## Phase AO - Named together", a)
        self.assertNotIn(b"\n", a.replace(b"\r\n", b""), "the audit keeps its CRLF")
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_the_payload(self):
        names = (PAYLOAD / "src/pages/corpus/CorpusNames.tsx").read_text(encoding="utf-8")
        self.assertIn(MARK, names)
        self.assertIn("lk.length > 0 && <NamedWith", names, "not shown until C20, nor when empty")
        self.assertIn("it does not say how they are related", names.replace("\n", " ").replace("        ", " "))
        lib = (PAYLOAD / "src/lib/corpusLibrary.ts").read_text(encoding="utf-8")
        self.assertIn("lib<NameLink>('corpus_reader_name_links', { p_canonical: canonical, k: Math.max(1, Math.min(50, k)) })", lib)
        self.assertTrue(PAT.read_bytes().isascii())


class TheView(unittest.TestCase):
    def test_c20(self):
        if not C20.exists():
            self.skipTest("C20 is not here")
        s = C20.read_text(encoding="ascii")
        self.assertIn("NAME_LINKS_C20_2026_10_23", s)
        self.assertIn("HAVING count(*) <= 12", s, "the desk's list rule")
        self.assertIn("PERFORM corpus._reader_gate();", s, "behind the readers' gate")
        self.assertIn("GRANT EXECUTE ON FUNCTION %s TO authenticated", s)
        self.assertIn("REVOKE ALL ON corpus.name_links FROM PUBLIC;", s)
        self.assertIn("CREATE UNIQUE INDEX corpus_name_links_pair", s, "REFRESH ... CONCURRENTLY needs it")
        self.assertIn("cron.schedule('srangam-corpus-name-links', '40 4 * * *'", s)
        self.assertIn("m.doc_code NOT LIKE '%-RETIRED'", s)


if __name__ == "__main__":
    unittest.main()
