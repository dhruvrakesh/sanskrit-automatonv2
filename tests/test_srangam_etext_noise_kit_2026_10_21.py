# -*- coding: ascii -*-
"""ETEXT_NOISE_2026_10_21: the Srangam kit (docs/srangam/ETEXT_NOISE_2026-10-21/,
scripts/patch_srangam_etext_noise_2026_10_21.py) is whole: every file it writes is in the payload, LF, with the marker;
the reader names an e-text's noise by its reading (readingOf: not a scan) and keeps a scan's as it was; the patcher
leaves a tree that has the kit as it is and refuses a file changed since. The kit's run on Srangam's own files, and its
2 tests, are the user's (they need that repo)."""
import importlib.machinery, importlib.util, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "docs" / "srangam" / "ETEXT_NOISE_2026-10-21"
PAT = REPO / "scripts" / "patch_srangam_etext_noise_2026_10_21.py"
MARK = "ETEXT_NOISE_2026_10_21"


@unittest.skipUnless(PAT.exists() and KIT.exists(), "the kit is not here")
class TheKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loader = importlib.machinery.SourceFileLoader("patch_srangam_etext_noise", str(PAT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.p = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.p)

    def test_every_file_is_in_the_payload_with_the_marker(self):
        self.assertEqual(sorted(self.p.REPLACE), ["src/components/reader/PassageBlock.tsx"])
        self.assertEqual(self.p.NEW, ["src/__tests__/reader-etext-noise.test.tsx"])
        for rel in list(self.p.REPLACE) + self.p.NEW + [self.p.AUDIT_APPEND]:
            f = KIT / rel
            self.assertTrue(f.exists(), rel)
            t = f.read_text(encoding="utf-8")
            self.assertIn(MARK, t, rel)
            self.assertNotIn("\r\n", t, rel + ": the payload is LF; the patcher keeps each file's own endings")
        self.assertEqual(self.p.PREREQ, ("src/components/reader/PassageBlock.tsx", "SCHOLAR_READER_2026_10_18"))

    def test_the_reader_names_it_by_its_reading(self):
        t = (KIT / "src/components/reader/PassageBlock.tsx").read_text(encoding="utf-8")
        self.assertIn("const typed = readingOf(p.reading);   // ETEXT_NOISE_2026_10_21: an e-text has no scanner", t)
        self.assertIn("const etext = !!typed && !typed.scan;", t)
        self.assertIn("{etext ? \"Not the text: the e-text's own header or notes.\" : 'Scanner noise, not text.'}", t)
        self.assertIn("noise: 'Scanner noise: marks on the page that are not text.',", t, "a scan's note as it was")
        self.assertIn("SCHOLAR_READER_2026_10_18", t, "built on the version main has")
        self.assertIn("60. The reader names what it folds", (KIT / self.p.AUDIT_APPEND).read_text(encoding="utf-8"))

    def test_a_tree_with_the_kit_is_left_and_a_changed_file_refused(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "src").mkdir()
            (t / "package.json").write_text("{}\n", encoding="ascii")
            (t / "src" / "App.tsx").write_text("// app\n", encoding="ascii")
            for rel in list(self.p.REPLACE) + self.p.NEW:
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(KIT / rel, t / rel)
            r = subprocess.run([sys.executable, str(PAT)], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Nothing to do: %s is in place." % MARK, r.stdout)
            p = t / "src/components/reader/PassageBlock.tsx"
            p.write_text("// SCHOLAR_READER_2026_10_18 another version\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSE: src/components/reader/PassageBlock.tsx is not the version main had", r.stdout)
            p.write_text("// before the scholarly reader\n", encoding="ascii")
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=td, capture_output=True, text=True)
            self.assertIn("REFUSE: src/components/reader/PassageBlock.tsx has no SCHOLAR_READER_2026_10_18", r.stdout)

    def test_the_patcher(self):
        b = PAT.read_bytes()
        self.assertTrue(all(x < 128 for x in b))
        self.assertIn(MARK.encode(), b)


if __name__ == "__main__":
    unittest.main()
