# -*- coding: ascii -*-
"""SCHOLAR_READER_2026_10_18: the Srangam kit (docs/srangam/SCHOLAR_READER_2026-10-18/,
scripts/patch_srangam_scholar_reader_2026_10_18.py) is whole: every file it writes is in the payload, LF, with the
marker; the reader asks C18's two functions with the page window corpus_reader_page uses, and C18 defines them behind
the reader's gate; the patcher leaves a tree that has the kit as it is and refuses a file changed since. The kit's run
on Srangam's own files, and its 16 tests, are the user's (they need that repo)."""
import importlib.machinery, importlib.util, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "docs" / "srangam" / "SCHOLAR_READER_2026-10-18"
PAT = REPO / "scripts" / "patch_srangam_scholar_reader_2026_10_18.py"
C18 = REPO / "docs" / "cloud" / "C18_reader_scholar_2026-10-18.sql"
MARK = "SCHOLAR_READER_2026_10_18"


@unittest.skipUnless(PAT.exists() and KIT.exists(), "the kit is not here")
class TheKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loader = importlib.machinery.SourceFileLoader("patch_srangam_scholar_reader", str(PAT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.p = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.p)

    def test_every_file_is_in_the_payload_with_the_marker(self):
        self.assertEqual(sorted(self.p.REPLACE), ["src/components/reader/PassageBlock.tsx", "src/lib/corpusMirror.ts",
                                                  "src/pages/corpus/CorpusDoc.tsx"])
        for rel in list(self.p.REPLACE) + self.p.NEW + [self.p.AUDIT_APPEND]:
            f = KIT / rel
            self.assertTrue(f.exists(), rel)
            t = f.read_text(encoding="utf-8")
            self.assertIn(MARK, t, rel)
            self.assertNotIn("\r\n", t, rel + ": the payload is LF; the patcher keeps each file's own endings")
        self.assertEqual(self.p.PREREQ, ("src/lib/editions.ts", "EDITIONS_SITE_2026_10_18"))

    def test_the_reader_asks_c18_as_the_page_is_read(self):
        m = (KIT / "src/lib/corpusMirror.ts").read_text(encoding="utf-8")
        self.assertIn("rpc<MirrorScholarRow>('corpus_reader_scholar', {\n    p_doc: docCode, p_offset: (p - 1) * "
                      "PASSAGES_PER_PAGE, p_limit: PASSAGES_PER_PAGE,", m)
        self.assertIn("rpc<MirrorPassage>('corpus_reader_page', {\n    p_doc: docCode, p_offset: (p - 1) * "
                      "PASSAGES_PER_PAGE, p_limit: PASSAGES_PER_PAGE,", m)
        self.assertIn("rpc<MirrorScholarCount>('corpus_reader_scholar_count', { p_doc: docCode })", m)
        sql = C18.read_text(encoding="utf-8")
        for fn in ("public.corpus_reader_scholar(p_doc text, p_offset integer DEFAULT 0, p_limit integer DEFAULT 50)",
                   "public.corpus_reader_scholar_count(p_doc text)"):
            self.assertIn("CREATE OR REPLACE FUNCTION " + fn, sql)
        self.assertEqual(sql.count("PERFORM corpus._reader_gate();   -- C18_READER_SCHOLAR_2026_10_18"), 2)
        self.assertEqual(sql.count("SECURITY DEFINER SET search_path = ''"), 2)
        self.assertNotIn("dangerouslySetInnerHTML", (KIT / "src/components/reader/ScholarEnglish.tsx").read_text(encoding="utf-8"))

    def test_a_tree_with_the_kit_is_left_and_a_changed_file_refused(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "src" / "lib").mkdir(parents=True)
            (t / "package.json").write_text("{}\n", encoding="ascii")
            (t / "src" / "App.tsx").write_text("// app\n", encoding="ascii")
            (t / "src" / "lib" / "editions.ts").write_text("// EDITIONS_SITE_2026_10_18\n", encoding="ascii")
            for rel in list(self.p.REPLACE) + self.p.NEW:
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(KIT / rel, t / rel)
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Nothing to do: %s is in place." % MARK, r.stdout)
            (t / "src/lib/corpusMirror.ts").write_text("// another version\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSE: src/lib/corpusMirror.ts is not the version main had", r.stdout)
            (t / "src/lib/editions.ts").write_text("// before the editions\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=td, capture_output=True, text=True)
            self.assertIn("REFUSE: src/lib/editions.ts has no EDITIONS_SITE_2026_10_18", r.stdout)

    def test_the_patcher(self):
        b = PAT.read_bytes()
        self.assertTrue(all(x < 128 for x in b))
        self.assertIn(MARK.encode(), b)


if __name__ == "__main__":
    unittest.main()
