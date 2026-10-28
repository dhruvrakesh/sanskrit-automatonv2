# -*- coding: ascii -*-
"""RIGHTS_FRONTMATTER_2026_10_28: a text whose edition is listed in configs/edition_rights.json with
"withhold_frontmatter": true sends its own matter (passages typed 'frontmatter': preface, notes, its editor's
translation) with its place and type only; its words, IAST, English, Hindi, names, vector and scholarly rows stay on
the desk; its Sanskrit goes as before; a text not listed, listed false, or a missing register, as before. The
register itself: every entry names its edition, its notice and the evidence on the scan's own pages. Temp files only,
never data/context.db."""
import json, os, sqlite3, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import corpus_sync as cs  # noqa: E402
from tests.test_corpus_sync_2026_10_08 import make_fixture  # noqa: E402

REG = REPO / "configs" / "edition_rights.json"
MARK = "RIGHTS_FRONTMATTER_2026_10_28"


class Withheld(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = Path(self.td.name)
        self.db = t / "c.db"
        make_fixture(str(self.db))
        con = sqlite3.connect(str(self.db))
        # the second text's page 1, passage 1 is its editor's preface (with a Hindi row, a vector and a name on it)
        con.execute("UPDATE passages SET text_type='frontmatter', text='PREFACE by the editor' "
                    "WHERE doc_id=2 AND page_no=1 AND idx=1")
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
        if texts is None:
            os.environ["SA_EDITION_RIGHTS"] = str(self.reg.with_name("none.json"))
        else:
            self.reg.write_text(json.dumps({"mark": MARK, "texts": texts}), encoding="utf-8")
            os.environ["SA_EDITION_RIGHTS"] = str(self.reg)
        cs._RIGHTS.clear()
        con = sqlite3.connect(str(self.db))
        try:
            doc = con.execute("SELECT id, code FROM docs WHERE code='AphorismsOfSandilya'").fetchone()
            return cs.build_doc_groups(con, doc, set(cs.PER_DOC_TABLES), {"Indra", "Meru"})
        finally:
            con.close()

    def test_listed_its_own_matter_stays_on_the_desk(self):
        g = self.groups({"AphorismsOfSandilya": {"notice": "(c) A Press, 1990", "withhold_frontmatter": True}})
        p = g["passages"].rows["1|1"]
        self.assertEqual(p["text"], "[The edition's own matter, not shown on the site: (c) A Press, 1990.]")
        self.assertEqual(p["text_type"], "frontmatter")
        for k in ("iast", "translation", "sandhi", "morph", "translated_at"):
            self.assertIsNone(p[k], k)
        self.assertNotIn("1|1|hi", g["translations"].rows)
        self.assertNotIn("1|1|Indra", g["mentions"].rows)
        self.assertNotIn("1|1", g["vectors"].rows)
        m = g["passages"].rows["1|2"]                       # the Sanskrit beside it: as before
        self.assertEqual((m["text_type"], m["iast"]), ("mula", "sloka 2"))
        self.assertIn("1|2|hi", g["translations"].rows)
        self.assertIn("2|1|Indra", g["mentions"].rows)

    def test_not_listed_false_or_no_register_as_before(self):
        base = self.groups(None)
        self.assertEqual(base["passages"].rows["1|1"]["text"], "PREFACE by the editor")
        self.assertIn("1|1|hi", base["translations"].rows)
        for texts in ({}, {"AphorismsOfSandilya": {"notice": "x", "withhold_frontmatter": False}},
                      {"markandeya_purana": {"notice": "x", "withhold_frontmatter": True}}):
            g = self.groups(texts)
            self.assertEqual(g["passages"].hashes, base["passages"].hashes, texts)
            self.assertEqual(g["translations"].hashes, base["translations"].hashes, texts)

    def test_a_bad_register_is_no_register(self):
        self.reg.write_text("{not json", encoding="utf-8")
        os.environ["SA_EDITION_RIGHTS"] = str(self.reg)
        cs._RIGHTS.clear()
        self.assertEqual(cs.edition_rights(), {})
        self.assertEqual(cs.withheld_notice("AphorismsOfSandilya"), "")


@unittest.skipUnless(REG.exists(), "configs/edition_rights.json is not here")
class TheRegister(unittest.TestCase):
    def test_every_entry_names_its_evidence(self):
        j = json.loads(REG.read_text(encoding="utf-8"))
        self.assertEqual(j["mark"], MARK)
        self.assertTrue(REG.read_bytes().isascii())
        for code, e in j["texts"].items():
            for k in ("edition", "notice", "evidence"):
                self.assertTrue(str(e.get(k) or "").strip(), (code, k))
            self.assertIsInstance(e.get("withhold_frontmatter"), bool, code)
        for code in ("HAYASHIRSHA_PANCARATRA", "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi",
                     "Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V"):
            self.assertTrue(j["texts"][code]["withhold_frontmatter"], code)
            self.assertIn("(c)", j["texts"][code]["notice"], code)

    def test_corpus_sync_marked(self):
        src = (REPO / "scripts" / "corpus_sync.py").read_bytes()
        self.assertTrue(src.isascii())
        self.assertIn(MARK.encode(), src)


PAT = REPO / "scripts" / "patch_rights_frontmatter_2026_10_28.py"
PFILES = ('scripts/corpus_sync.py', 'tests/test_scholar_mirror_2026_10_18.py')


def as_left(rel: str) -> bytes:
    """The file as the patch left it: the oldest later backup that carries MARK, else the file now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*") if ".bak_rightsfront_" not in b.name and MARK.encode() in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


@unittest.skipUnless(PAT.exists(), "patch_rights_frontmatter_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in PFILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_rightsfront_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            for rel in ('configs/edition_rights.json',):
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes((REPO / rel).read_bytes())
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(PFILES), r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in PFILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual(got, as_left(rel), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
