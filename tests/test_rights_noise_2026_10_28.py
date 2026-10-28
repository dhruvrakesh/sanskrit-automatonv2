# -*- coding: ascii -*-
"""RIGHTS_NOISE_2026_10_28: of a text whose edition is listed in configs/edition_rights.json with
"withhold_frontmatter": true, a passage typed 'noise' (the edition's apparatus of variant readings, or a page's
debris) is sent as the frontmatter is: its place and type, a notice for its words, nothing else; its Sanskrit beside
it as before; a text not listed as before; the patch replays once. Temp files only, never data/context.db."""
import json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import make_fixture  # noqa: E402

MARK = "RIGHTS_NOISE_2026_10_28"
PAT = REPO / "scripts" / "patch_rights_noise_2026_10_28.py"
FILES = ("scripts/corpus_sync.py",)
APP = "12 tatra-B,C. 13 omitted in A. 14 ca-D."


@unittest.skipUnless(hasattr(cs, "WITHHELD_TYPES"), "corpus_sync.py without RIGHTS_NOISE_2026_10_28")
class Withheld(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = Path(self.td.name)
        self.db = t / "c.db"
        make_fixture(str(self.db))
        con = sqlite3.connect(str(self.db))
        con.execute("UPDATE passages SET text_type='noise', text=? WHERE doc_id=2 AND page_no=1 AND idx=1", (APP,))
        con.commit(); con.close()
        self.reg = t / "rights.json"
        self.old = os.environ.get("SA_EDITION_RIGHTS")

    def tearDown(self):
        cs._RIGHTS.clear()
        if self.old is None:
            os.environ.pop("SA_EDITION_RIGHTS", None)
        else:
            os.environ["SA_EDITION_RIGHTS"] = self.old
        self.td.cleanup()

    def groups(self, texts):
        self.reg.write_text(json.dumps({"mark": "RIGHTS_FRONTMATTER_2026_10_28", "texts": texts}), encoding="utf-8")
        os.environ["SA_EDITION_RIGHTS"] = str(self.reg)
        cs._RIGHTS.clear()
        con = sqlite3.connect(str(self.db))
        try:
            doc = con.execute("SELECT id, code FROM docs WHERE code='AphorismsOfSandilya'").fetchone()
            return cs.build_doc_groups(con, doc, set(cs.PER_DOC_TABLES), {"Indra", "Meru"})
        finally:
            con.close()

    def test_listed_its_apparatus_stays_on_the_desk(self):
        g = self.groups({"AphorismsOfSandilya": {"notice": "(c) A Press, 1990", "withhold_frontmatter": True}})
        p = g["passages"].rows["1|1"]
        self.assertEqual(p["text"], "[The edition's own matter, not shown on the site: (c) A Press, 1990.]")
        self.assertEqual(p["text_type"], "noise")
        for k in ("iast", "translation", "translated_at"):
            self.assertIsNone(p[k], k)
        self.assertNotIn("1|1|hi", g["translations"].rows)
        self.assertNotIn("1|1", g["vectors"].rows)
        self.assertEqual(g["passages"].rows["1|2"]["text_type"], "mula", "the Sanskrit beside it: as before")
        self.assertIn("1|2|hi", g["translations"].rows)

    def test_not_listed_as_before(self):
        g = self.groups({})
        self.assertEqual(g["passages"].rows["1|1"]["text"], APP)

    def test_the_types(self):
        self.assertEqual(cs.WITHHELD_TYPES, ("frontmatter", "noise"))


@unittest.skipUnless(PAT.exists(), "patch_rights_noise_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())
        self.assertTrue((REPO / "scripts" / "corpus_sync.py").read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_rightsnoise_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 1 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                now = (REPO / rel).read_bytes()
                later = [b for b in (REPO / rel).parent.glob(Path(rel).name + ".bak_*")
                         if ".bak_rightsnoise_" not in b.name and MARK.encode() in b.read_bytes()]
                want = min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else now
                if MARK.encode() in now:
                    self.assertEqual(got, want, rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
